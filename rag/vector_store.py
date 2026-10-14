"""Store RAG documents, chunks, and embeddings in PostgreSQL."""

import os
from threading import Lock

import numpy as np

import psycopg
from psycopg.types.json import Jsonb

_studio_schema_ready = False
_studio_schema_lock = Lock()

def connect_rag_database(password: str | None = None):
    """Open a connection to the configured RAG database."""
    try:
        from app.config import settings
    except ImportError:
        settings = None

    password = password or (settings.rag_db_password if settings else None) or os.environ.get("RAG_DB_PASSWORD")

    if not password:
        raise ValueError("RAG_DB_PASSWORD is not set")

    return psycopg.connect(
        host=os.environ.get("RAG_DB_HOST", settings.rag_db_host if settings else "127.0.0.1"),
        port=int(os.environ.get("RAG_DB_PORT", str(settings.rag_db_port if settings else 5433))),
        dbname="flyrank_rag",
        user="flyrank_rag",
        password=password,
    )


def ensure_studio_tables(connection) -> None:
    """Create additive tables used by the campaign document workspace."""
    global _studio_schema_ready
    if _studio_schema_ready:
        return
    with _studio_schema_lock:
        if _studio_schema_ready:
            return
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            cursor.execute("CREATE SCHEMA IF NOT EXISTS rag")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag.documents (
                dataset TEXT NOT NULL,
                document_id TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                PRIMARY KEY (dataset, document_id)
            )
            """)
            cursor.execute("ALTER TABLE rag.documents ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now()")
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag.chunks (
                id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                dataset TEXT NOT NULL,
                document_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL CHECK (chunk_index >= 0),
                chunking_version TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                FOREIGN KEY (dataset, document_id) REFERENCES rag.documents(dataset, document_id),
                UNIQUE (dataset, document_id, chunking_version, chunk_index)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag.embeddings (
                chunk_id BIGINT NOT NULL REFERENCES rag.chunks(id),
                model_id TEXT NOT NULL,
                dimensions INTEGER NOT NULL CHECK (dimensions > 0),
                embedding VECTOR NOT NULL,
                CHECK (vector_dims(embedding) = dimensions),
                PRIMARY KEY (chunk_id, model_id)
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag.studio_ingestion_jobs (
                id TEXT PRIMARY KEY,
                owner_id INTEGER NOT NULL,
                filename TEXT NOT NULL,
                status TEXT NOT NULL,
                step TEXT NOT NULL,
                document_id TEXT,
                chunk_count INTEGER NOT NULL DEFAULT 0,
                embedding_count INTEGER NOT NULL DEFAULT 0,
                memory_mb DOUBLE PRECISION,
                peak_memory_mb DOUBLE PRECISION,
                error_message TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """)
        connection.commit()
        _studio_schema_ready = True

def store_documents(connection, documents: list[dict], dataset: str) -> int:
    """Insert documents or update existing records with the same IDs."""
    rows = [
        (
            dataset,
            document["_id"],
            document.get("title") or "",
            document["text"],
            Jsonb(document.get("metadata") or {}),
        )
        for document in documents
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO rag.documents (
                dataset, document_id, title, content, metadata
            )
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (dataset, document_id)
            DO UPDATE SET
                title = EXCLUDED.title,
                content = EXCLUDED.content,
                metadata = EXCLUDED.metadata
            """,
            rows,
        )

    return len(rows)

def store_chunks(
    connection,
    chunks: list[dict],
    dataset: str,
    chunking_version: str,
) -> list[int]:
    """Store chunks and return their database IDs in input order."""
    chunk_ids = []

    with connection.cursor() as cursor:
        for chunk in chunks:
            cursor.execute(
                """
                INSERT INTO rag.chunks (
                    dataset,
                    document_id,
                    chunk_index,
                    chunking_version,
                    content,
                    metadata
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (
                    dataset, document_id, chunking_version, chunk_index
                )
                DO UPDATE SET
                    content = EXCLUDED.content,
                    metadata = EXCLUDED.metadata
                RETURNING id
                """,
                (
                    dataset,
                    chunk["document_id"],
                    chunk["chunk_index"],
                    chunking_version,
                    chunk["text"],
                    Jsonb({"token_count": chunk["token_count"]}),
                ),
            )

            chunk_ids.append(cursor.fetchone()[0])

    return chunk_ids

def store_embeddings(
    connection,
    chunk_ids: list[int],
    vectors: np.ndarray,
    model_id: str,
) -> int:
    """Store vectors linked to their matching chunk IDs."""
    if vectors.ndim != 2:
        raise ValueError("vectors must be a 2D array")

    if len(chunk_ids) != vectors.shape[0]:
        raise ValueError("Each chunk ID must have one matching vector")

    if vectors.shape[1] < 1:
        raise ValueError("Vectors must have at least one dimension")

    if not np.isfinite(vectors).all():
        raise ValueError("Vectors must contain only finite values")

    dimensions = vectors.shape[1]

    # Convert each vector into pgvector's text format: [0.1,0.2,...]
    rows = [
        (
            chunk_id,
            model_id,
            dimensions,
            "[" + ",".join(str(float(value)) for value in vector) + "]",
        )
        for chunk_id, vector in zip(chunk_ids, vectors)
    ]

    with connection.cursor() as cursor:
        cursor.executemany(
            """
            INSERT INTO rag.embeddings (
                chunk_id, model_id, dimensions, embedding
            )
            VALUES (%s, %s, %s, %s::vector)
            ON CONFLICT (chunk_id, model_id)
            DO UPDATE SET
                dimensions = EXCLUDED.dimensions,
                embedding = EXCLUDED.embedding
            """,
            rows,
        )

    return len(rows)
