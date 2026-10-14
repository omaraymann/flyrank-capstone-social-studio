"""One-time held-out SciFact test using the selected BGE retrieval setup."""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np
from sentence_transformers import SentenceTransformer

from rag.cache import file_hash
from rag.evaluation import precision_at_k, recall_at_k, reciprocal_rank_at_k
from rag.examples.retrieval_baseline import DATA_DIR


CHUNK_VARIANTS = {
    "bge_512_no_overlap_title": "BGE-tokenizer-aware 512-token chunks, sentence-based, no overlap, title included",
    "bge_256_overlap_title": "BGE-tokenizer-aware 256-token chunks, sentence-based, one-sentence overlap, title included",
}
MODEL = "BAAI/bge-small-en-v1.5"
MODEL_REVISION = "5c38ec7c405ec4b44b94cc5a9bb96e735b38267a"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
K = 5


def load_test_queries_and_labels(data_dir: Path):
    """Load only queries listed in test qrels, with their positive document labels."""
    with (data_dir / "queries.jsonl").open(encoding="utf-8") as stream:
        all_queries = {row["_id"]: row for row in map(json.loads, stream)}
    labels = {}
    with (data_dir / "qrels/test.tsv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            if int(row["score"]) > 0:
                labels.setdefault(row["query-id"], set()).add(row["corpus-id"])
    queries = [all_queries[query_id] for query_id in labels]
    if len(queries) != 300:
        raise ValueError(f"Expected 300 test queries, found {len(queries)}")
    return queries, labels


def validate_chunk_cache(chunk_dir: Path, variant: str):
    manifest = json.loads((chunk_dir / "manifest.json").read_text(encoding="utf-8"))
    if file_hash(chunk_dir / "vectors.npy") != manifest["sha256"]:
        raise ValueError("BGE chunk-vector checksum does not match its manifest")
    if file_hash(chunk_dir / "chunks.jsonl") != manifest["settings"]["chunk_sha256"]:
        raise ValueError("BGE chunk text checksum does not match its manifest")
    identity = manifest["settings"]
    expected_tokens = 256 if variant == "bge_256_overlap_title" else 512
    expected_overlap = variant == "bge_256_overlap_title"
    if (identity["model"] != MODEL or identity["model_revision"] != MODEL_REVISION
            or identity["max_tokens"] != expected_tokens or identity["sentence_overlap"] is not expected_overlap
            or identity["include_title"] is not True):
        raise ValueError("Cached passages do not match the selected test configuration")
    return manifest


def save_csv(path: Path, rows: list[dict]):
    if not rows:
        raise ValueError(f"Refusing to write an empty CSV: {path}")
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-variant", choices=CHUNK_VARIANTS, default="bge_512_no_overlap_title")
    variant = parser.parse_args().chunk_variant
    chunk_dir = DATA_DIR.parents[1] / "results/scifact_bge_chunking" / variant
    result_dir = DATA_DIR.parents[1] / "results" / f"scifact_test_{variant}"
    result_dir.mkdir(parents=True, exist_ok=True)
    chunk_manifest = validate_chunk_cache(chunk_dir, variant)
    queries, labels = load_test_queries_and_labels(DATA_DIR)
    source_hashes = {
        name: file_hash(DATA_DIR / name)
        for name in ("corpus.jsonl", "queries.jsonl", "qrels/test.tsv")
    }
    chunks = [json.loads(line) for line in (chunk_dir / "chunks.jsonl").open(encoding="utf-8") if line.strip()]
    passage_vectors = np.load(chunk_dir / "vectors.npy", allow_pickle=False)
    if passage_vectors.shape != (len(chunks), 384) or not np.isfinite(passage_vectors).all():
        raise ValueError("BGE passage-vector array has an invalid shape or values")
    if not np.allclose(np.linalg.norm(passage_vectors, axis=1), 1.0, atol=1e-5):
        raise ValueError("BGE passage vectors are not normalized")

    query_ids = [query["_id"] for query in queries]
    query_vectors_path = result_dir / "query_vectors.npy"
    query_manifest_path = result_dir / "query_manifest.json"
    query_identity = {
        "model": MODEL,
        "model_revision": MODEL_REVISION,
        "dimensions": 384,
        "query_prefix": QUERY_PREFIX,
        "normalized": True,
        "split": "test",
        "query_ids": query_ids,
        "source_hashes": source_hashes,
    }
    cached = json.loads(query_manifest_path.read_text(encoding="utf-8")) if query_manifest_path.exists() else None
    if (cached and cached["identity"] == query_identity and query_vectors_path.exists()
            and file_hash(query_vectors_path) == cached["sha256"]):
        query_vectors = np.load(query_vectors_path, allow_pickle=False)
        print("Reusing verified held-out query embeddings.", flush=True)
    else:
        print(f"Loading pinned BGE model and embedding {len(queries)} held-out queries...", flush=True)
        model = SentenceTransformer(MODEL, revision=MODEL_REVISION, device="cpu", local_files_only=True)
        model.default_prompt_name = None
        model.prompts = {}
        query_texts = [QUERY_PREFIX + query["text"] for query in queries]
        max_length = max(len(model.tokenizer(text, truncation=False, add_special_tokens=True)["input_ids"])
                         for text in query_texts)
        if max_length > model.max_seq_length:
            raise ValueError(f"A test query has {max_length} tokens; model limit is {model.max_seq_length}")
        query_vectors = model.encode(query_texts, batch_size=16, normalize_embeddings=True,
                                     convert_to_numpy=True, show_progress_bar=True)
        np.save(query_vectors_path, query_vectors)
        query_manifest_path.write_text(json.dumps({
            "identity": query_identity,
            "max_query_tokens": max_length,
            "sha256": file_hash(query_vectors_path),
        }, indent=2), encoding="utf-8")
        del model
    if query_vectors.shape != (len(queries), 384) or not np.isfinite(query_vectors).all():
        raise ValueError("Held-out query-vector array has an invalid shape or values")
    if not np.allclose(np.linalg.norm(query_vectors, axis=1), 1.0, atol=1e-5):
        raise ValueError("Held-out query vectors are not normalized")

    document_ids = list(dict.fromkeys(chunk["document_id"] for chunk in chunks))
    document_positions = {document_id: index for index, document_id in enumerate(document_ids)}
    chunk_document_positions = np.array([document_positions[chunk["document_id"]] for chunk in chunks])
    per_query = []
    rankings = []
    search_started = perf_counter()
    for query, query_vector in zip(queries, query_vectors):
        chunk_scores = passage_vectors @ query_vector
        document_scores = np.full(len(document_ids), -np.inf)
        np.maximum.at(document_scores, chunk_document_positions, chunk_scores)
        chunk_order = chunk_scores.argsort()[::-1]
        best_chunks = {}
        for index in chunk_order:
            best_chunks.setdefault(chunks[index]["document_id"], int(index))
        ordered_ids = list(best_chunks)
        relevant = labels[query["_id"]]
        retrieved = ordered_ids[:K]
        hits = len(set(retrieved) & relevant)
        per_query.append({
            "query_id": query["_id"],
            "query": query["text"],
            "relevant_count": len(relevant),
            "labelled_hits_at_5": hits,
            "precision_at_5": precision_at_k(retrieved, relevant, K),
            "recall_at_5": recall_at_k(retrieved, relevant, K),
            "reciprocal_rank_at_5": reciprocal_rank_at_k(retrieved, relevant, K),
            "retrieved_ids": retrieved,
        })
        for rank, document_id in enumerate(retrieved, 1):
            chunk_index = best_chunks[document_id]
            rankings.append({
                "query_id": query["_id"], "rank": rank, "document_id": document_id,
                "chunk_index": chunks[chunk_index]["chunk_index"],
                "similarity": float(document_scores[document_positions[document_id]]),
                "labelled_relevant": document_id in relevant,
            })
    search_seconds = perf_counter() - search_started
    summary = {
        "query_count": len(per_query),
        "document_count": len(document_ids),
        "chunk_count": len(chunks),
        "k": K,
        "precision_at_5": float(np.mean([row["precision_at_5"] for row in per_query])),
        "recall_at_5": float(np.mean([row["recall_at_5"] for row in per_query])),
        "mrr_at_5": float(np.mean([row["reciprocal_rank_at_5"] for row in per_query])),
        "queries_with_no_labelled_hit": sum(row["labelled_hits_at_5"] == 0 for row in per_query),
        "labelled_relevant_documents": sum(len(value) for value in labels.values()),
        "search_seconds": search_seconds,
    }
    result = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "split": "test",
        "settings": {
            "model": MODEL, "model_revision": MODEL_REVISION, "dimensions": 384,
            "query_prefix": QUERY_PREFIX, "chunking": CHUNK_VARIANTS[variant],
            "chunk_sha256": chunk_manifest["settings"]["chunk_sha256"],
            "normalized_embeddings": True, "retrieval": "maximum chunk cosine score per unique document",
            "k": K,
        },
        "source_hashes": source_hashes,
        "summary": summary,
        "per_query": per_query,
        "note": "This test split is being used to compare configurations after an earlier test run. Treat these scores as diagnostic comparison results, not as an untouched final estimate. Qrels contain positive relevance labels only; unlabelled retrieved documents are not confirmed irrelevant.",
    }
    (result_dir / "results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    save_csv(result_dir / "summary.csv", [summary])
    save_csv(result_dir / "per_query_metrics.csv", [
        {key: value for key, value in row.items() if key != "retrieved_ids"}
        for row in per_query
    ])
    save_csv(result_dir / "rankings.csv", rankings)
    report = [
        "# SciFact held-out test retrieval evaluation", "",
        "This result supports a diagnostic comparison across configurations. The test split was already evaluated for another setup, so it should not be treated as an untouched final estimate.", "",
        f"- Queries: {summary['query_count']}",
        f"- Corpus documents: {summary['document_count']}",
        f"- Chunks: {summary['chunk_count']}",
        f"- Model: {MODEL} ({MODEL_REVISION})",
        f"- Chunking: {CHUNK_VARIANTS[variant]}",
        "- Ranking: maximum cosine score over a document's chunks; unique documents returned",
        f"- k: {K}", "",
        "| Metric | Mean across queries |", "|---|---:|",
        f"| Precision@5 | {summary['precision_at_5']:.4f} |",
        f"| Recall@5 | {summary['recall_at_5']:.4f} |",
        f"| MRR@5 | {summary['mrr_at_5']:.4f} |", "",
        f"Queries with no labelled relevant document in the top 5: {summary['queries_with_no_labelled_hit']}/{summary['query_count']}.", "",
        "SciFact qrels provide positive relevance judgements only. A retrieved document without a positive label is unjudged, so precision here means the fraction of retrieved results with a recorded positive label; it does not prove every other result is irrelevant.", "",
        "Raw per-query metrics, top-five rankings, source checksums and query-vector cache are saved beside this report. Since multiple configurations have now been compared on this split, use a new untouched test set for a final unbiased estimate.",
    ]
    (result_dir / "REPORT.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
