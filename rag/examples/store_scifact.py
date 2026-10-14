"""Import SciFact documents, chunks, and saved vectors into PostgreSQL."""

import json
import os
import numpy as np
from pathlib import Path


from rag.config import CHUNKING_VERSION, EMBEDDING_MODEL
from rag.cache import load_embedding_cache
from rag.vector_store import (
    connect_rag_database,
    store_chunks,
    store_documents,
    store_embeddings,
)

from psycopg.rows import dict_row

RAG_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = RAG_DIR / "data/raw/scifact"
PROCESSED_DIR = RAG_DIR / "data/processed/scifact"

DATASET = "scifact"



def load_jsonl(path: Path) -> list[dict]:
    """Read JSON records from a JSONL file."""
    with path.open(encoding="utf-8") as file:
        return [
            json.loads(line)
            for line in file
            if line.strip()
        ]


def load_database_password() -> None:
    """Use the environment password, or read our local Docker env file."""
    if os.environ.get("RAG_DB_PASSWORD"):
        return

    with (RAG_DIR / ".env").open(encoding="utf-8") as file:
        for line in file:
            if line.startswith("RAG_DB_PASSWORD="):
                password = line.split("=", 1)[1].strip()
                if password:
                    os.environ["RAG_DB_PASSWORD"] = password
                    return

    raise ValueError("RAG_DB_PASSWORD was not found in rag/.env")

def search_similar_chunks(connection, query_vector: np.ndarray, dataset: str, model_id: str, chunking_version: str, top_k: int = 5,) -> list[dict]:
    """Return the most similar chunks from the selected collection."""
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")

    if top_k < 1:
        raise ValueError("top_k must be positive")

    if query_vector.ndim != 1 or query_vector.size == 0:
        raise ValueError("query_vector must be a non-empty 1D array")

    if not np.isfinite(query_vector).all():
        raise ValueError("query_vector must contain only finite values")

    if not np.any(query_vector):
        raise ValueError("Cosine similarity requires a non-zero vector")

    vector_text = (
        "[" + ",".join(str(float(value)) for value in query_vector) + "]"
    )

    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            SELECT
                c.id AS chunk_id,
                c.document_id,
                c.chunk_index,
                d.title,
                c.content,
                1 - (e.embedding <=> %s::vector) AS similarity
            FROM rag.embeddings AS e
            JOIN rag.chunks AS c ON c.id = e.chunk_id
            JOIN rag.documents AS d
                ON d.dataset = c.dataset
                AND d.document_id = c.document_id
            WHERE c.dataset = %s
                AND e.model_id = %s
                AND c.chunking_version = %s
                AND e.dimensions = %s
            ORDER BY e.embedding <=> %s::vector, c.id
            LIMIT %s
            """,
            (
                vector_text,
                dataset,
                model_id,
                chunking_version,
                query_vector.size,
                vector_text,
                top_k,
            ),
        )

        return cursor.fetchall()

def main() -> None:
    documents = load_jsonl(RAW_DIR / "corpus.jsonl")
    chunks, vectors = load_embedding_cache(PROCESSED_DIR)

    load_database_password()

    print("Importing into PostgreSQL...", flush=True)

    # Success commits all steps; an exception rolls them back.
    with connect_rag_database() as connection:
        document_count = store_documents(
            connection, documents, DATASET
        )

        chunk_ids = store_chunks(
            connection, chunks, DATASET, CHUNKING_VERSION
        )

        embedding_count = store_embeddings(
            connection, chunk_ids, vectors, EMBEDDING_MODEL
        )

    print("Import committed.")
    print("Documents processed:", document_count)
    print("Chunks processed:", len(chunk_ids))
    print("Embeddings processed:", embedding_count)


if __name__ == "__main__":
    main()