"""Demonstrate retrieval over five SciFact documents."""

import csv
import json
from pathlib import Path

from rag.embeddings import embed_documents, embed_queries
from rag.retrieval import retrieve_topk


DATA_DIR = Path(__file__).resolve().parents[1] / "data/raw/scifact"


def main():
    # Load documents and queries, indexed by their IDs.
    with (DATA_DIR / "corpus.jsonl").open(encoding="utf-8") as file:
        documents = {
            record["_id"]: record
            for record in map(json.loads, file)
        }

    with (DATA_DIR / "queries.jsonl").open(encoding="utf-8") as file:
        queries = {
            record["_id"]: record
            for record in map(json.loads, file)
        }

    # Pick one query using the first test relevance label.
    with (DATA_DIR / "qrels/test.tsv").open(
        encoding="utf-8", newline=""
    ) as file:
        labels = list(csv.DictReader(file, delimiter="\t"))

    query_id = labels[0]["query-id"]
    query = queries[query_id]

    relevant_ids = {
        label["corpus-id"]
        for label in labels
        if label["query-id"] == query_id and int(label["score"]) > 0
    }

    relevant_documents = [
        doc for doc in documents.values()
        if doc["_id"] in relevant_ids
    ]

    # Add four other candidates. Unlabelled does not mean irrelevant.
    other_documents = [
        doc for doc in documents.values()
        if doc["_id"] not in relevant_ids
    ][:4]

    candidates = other_documents + relevant_documents

    print("Query:", query["text"])
    print("Labelled relevant IDs:", sorted(relevant_ids))
    print("Candidate count:", len(candidates))

    # Prepare one title + abstract per candidate.
    passages = [
        f"{doc['title']}\n{doc['text']}"
        for doc in candidates
    ]

    # Check input lengths before allowing the model to truncate text.
    from rag.config import PASSAGE_PREFIX, QUERY_PREFIX
    from rag.embeddings import load_model

    model = load_model()
    prepared_inputs = [QUERY_PREFIX + query["text"]] + [
        PASSAGE_PREFIX + passage for passage in passages
    ]

    for text in prepared_inputs:
        token_count = len(
            model.tokenizer(
                text,
                truncation=False,
                add_special_tokens=True,
            )["input_ids"]
        )
        if token_count > model.max_seq_length:
            raise ValueError(
                f"Input has {token_count} tokens; "
                f"model limit is {model.max_seq_length}. "
                "Split the oversized input before embedding."
            )

    print("\nCreating embeddings...", flush=True)
    query_vector = embed_queries([query["text"]])[0]
    document_vectors = embed_documents(passages)

    top_k_indices, scores = retrieve_topk(query_vector, document_vectors, top_k=5)

    print("\nRetrieval ranking:")
    relevant_ranks = []

    for rank, (index, score) in enumerate(zip(top_k_indices, scores), start=1):
        doc = candidates[index]
        is_relevant = doc["_id"] in relevant_ids

        if is_relevant:
            relevant_ranks.append(rank)

        marker = " [LABELLED RELEVANT]" if is_relevant else ""
        print(f"{rank}. {doc['_id']} | {float(score):.3f}{marker}")
        print(f"   {doc['title']}")

    print("\nLabelled relevant document ranks:", relevant_ranks)


if __name__ == "__main__":
    main()