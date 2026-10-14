"""Inspect SciFact document lengths before retrieval evaluation."""

import json, numpy as np
from pathlib import Path
import csv

from rag.cache import load_embedding_cache, save_embedding_cache
from rag.config import PASSAGE_PREFIX
from rag.embeddings import load_model, embed_documents, embed_queries
from rag.chunking import chunk_document, count_passage_tokens
from rag.retrieval import retrieve_top_documents
from rag.evaluation import (
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


DATA_DIR = Path(__file__).resolve().parents[1] / "data/raw/scifact"


def load_documents(data_dir: Path) -> list[dict]:
    """Read document records from corpus.jsonl."""
    corpus_path = Path(data_dir) / "corpus.jsonl"

    with corpus_path.open(encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def inspect_document_lengths(documents: list[dict], model) -> dict:
    """Measure prepared inputs without truncating or embedding them."""
    token_counts = {}
    token_limit = model.max_seq_length

    for document in documents:
        passage = f"{document['title']}\n{document['text']}"
        prepared_text = PASSAGE_PREFIX + passage

        tokens = model.tokenizer(
            prepared_text,
            truncation=False,
            add_special_tokens=True,
            verbose=False,
        )["input_ids"]

        token_counts[document["_id"]] = len(tokens)

    oversized_documents = {
        document_id: count
        for document_id, count in token_counts.items()
        if count > token_limit
    }

    return {
        "document_count": len(documents),
        "token_limit": token_limit,
        "longest_input": max(token_counts.values(), default=0),
        "token_counts": token_counts,
        "oversized_documents": oversized_documents,
    }


def print_length_report(report: dict) -> None:
    """Display the document-length inspection results."""
    oversized = report["oversized_documents"]

    print(f"Documents: {report['document_count']}")
    print(f"Model token limit: {report['token_limit']}")
    print(f"Longest input: {report['longest_input']} tokens")
    print(f"Documents within limit: {report['document_count'] - len(oversized)}")
    print(f"Documents over limit: {len(oversized)}")

    if oversized:
        print("\nFive longest oversized documents:")
        for document_id, count in sorted(
            oversized.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:5]:
            print(f"  {document_id}: {count} tokens")

def prepare_document_chunks(documents: list[dict], model) -> list[dict]:
    """Create model-sized passages while preserving document IDs."""
    chunks = []

    for document in documents:
        passages = chunk_document(
            text=document["text"],
            title=document.get("title"),
            tokenizer=model.tokenizer,
            max_tokens=model.max_seq_length,
        )

        for chunk_index, passage in enumerate(passages):
            token_count = count_passage_tokens(passage, model.tokenizer)

            if token_count > model.max_seq_length:
                raise ValueError(
                    f"Document {document['_id']}, chunk {chunk_index} "
                    f"exceeds the token limit: {token_count}"
                )

            chunks.append({
                "document_id": document["_id"],
                "chunk_index": chunk_index,
                "text": passage,
                "token_count": token_count,
            })

    return chunks

def create_and_save_chunk_embeddings(chunks: list[dict], output_dir: Path) -> np.ndarray:
    """Embed passages and save vectors with their matching chunk records."""
    try:
        _, vectors = load_embedding_cache(output_dir, expected_chunks=chunks)
        print("Reusing verified embedding cache:", vectors.shape)
        return vectors
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(f"Cache unavailable or outdated: {error}", flush=True)

    print(f"Embedding {len(chunks)} chunks...", flush=True)
    vectors = embed_documents([chunk["text"] for chunk in chunks])
    save_embedding_cache(output_dir, chunks, vectors)
    print("Embedding shape:", vectors.shape)
    print("Saved verified cache to:", output_dir)
    return vectors

def load_training_queries(data_dir: Path) -> tuple[list[dict], dict]:
    """Load training queries and their positive document relevance labels."""
    with (data_dir / "queries.jsonl").open(encoding="utf-8") as file:
        queries_by_id = {
            record["_id"]: record
            for record in map(json.loads, file)
        }

    relevant_documents = {}

    with (data_dir / "qrels/train.tsv").open(
        encoding="utf-8", newline=""
    ) as file:
        for label in csv.DictReader(file, delimiter="\t"):
            if int(label["score"]) > 0:
                query_id = label["query-id"]

                relevant_documents.setdefault(query_id, set()).add(
                    label["corpus-id"]
                )

    training_queries = [
        queries_by_id[query_id]
        for query_id in relevant_documents
    ]

    return training_queries, relevant_documents

def evaluate_training_queries(queries: list[dict], relevant_documents: dict, chunks: list[dict], chunk_vectors: np.ndarray, k: int = 5) -> dict:
    """Evaluate retrieval against training relevance labels."""
    if not queries:
        raise ValueError("No queries to evaluate")

    print(f"Embedding {len(queries)} training queries...", flush=True)
    query_vectors = embed_queries([query["text"] for query in queries])

    totals = {
        "precision": 0.0,
        "recall": 0.0,
        "reciprocal_rank": 0.0,
    }

    for query, query_vector in zip(queries, query_vectors):
        retrieved_ids = retrieve_top_documents(
            query_vector,
            chunk_vectors,
            chunks,
            top_k=k,
        )
        relevant_ids = relevant_documents[query["_id"]]

        totals["precision"] += precision_at_k(
            retrieved_ids, relevant_ids, k
        )
        totals["recall"] += recall_at_k(
            retrieved_ids, relevant_ids, k
        )
        totals["reciprocal_rank"] += reciprocal_rank_at_k(
            retrieved_ids, relevant_ids, k
        )

    count = len(queries)

    return {
        "query_count": count,
        f"precision@{k}": totals["precision"] / count,
        f"recall@{k}": totals["recall"] / count,
        f"mrr@{k}": totals["reciprocal_rank"] / count,
    }

def main() -> None:
    documents = load_documents(DATA_DIR)
    print(f"Loaded {len(documents)} documents.", flush=True)

    model = load_model()
    report = inspect_document_lengths(documents, model)
    print_length_report(report)

    chunks = prepare_document_chunks(documents, model)

    print(f"\nPrepared chunks: {len(chunks)}")
    print(
        "Longest chunk:",
        max((chunk["token_count"] for chunk in chunks), default=0),
        "tokens",
    )
    print("All chunks fit within the model limit.")

    output_dir = DATA_DIR.parents[1] / "processed/scifact"

    vectors = create_and_save_chunk_embeddings(chunks, output_dir)

    training_queries, relevant_documents = load_training_queries(DATA_DIR)

    print("Training queries:", len(training_queries))
    print(
        "Positive relevance labels:",
        sum(len(ids) for ids in relevant_documents.values()),
    )

    metrics = evaluate_training_queries(
        training_queries,
        relevant_documents,
        chunks,
        vectors,
        k=5,
    )

    print("\nTraining retrieval evaluation:")
    for name, value in metrics.items():
        print(f"{name}: {value}")


if __name__ == "__main__":
    main()