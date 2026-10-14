-- RAG experiment storage, separate from campaign data.
BEGIN;
CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS rag;

CREATE TABLE IF NOT EXISTS rag.documents (
    dataset TEXT NOT NULL,
    document_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (dataset, document_id)
);
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
);
CREATE TABLE IF NOT EXISTS rag.embeddings (
    chunk_id BIGINT NOT NULL REFERENCES rag.chunks(id),
    model_id TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    embedding VECTOR NOT NULL,
    CHECK (vector_dims(embedding) = dimensions),
    PRIMARY KEY (chunk_id, model_id)
);
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
);
CREATE TABLE IF NOT EXISTS rag.queries (
    dataset TEXT NOT NULL,
    query_id TEXT NOT NULL,
    content TEXT NOT NULL,
    PRIMARY KEY (dataset, query_id)
);
CREATE TABLE IF NOT EXISTS rag.relevance_labels (
    dataset TEXT NOT NULL,
    split TEXT NOT NULL CHECK (split IN ('train', 'validation', 'test')),
    query_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0),
    FOREIGN KEY (dataset, query_id) REFERENCES rag.queries(dataset, query_id),
    FOREIGN KEY (dataset, document_id) REFERENCES rag.documents(dataset, document_id),
    PRIMARY KEY (dataset, split, query_id, document_id)
);
COMMIT;
