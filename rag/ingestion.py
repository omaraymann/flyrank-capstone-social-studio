"""Upload processing for campaign documents stored in the separate pgvector DB."""
from __future__ import annotations

import resource
import uuid

from rag.pipeline import PLATFORM_CHUNKING, PLATFORM_MODEL, chunk_text, embed_passages
from rag.vector_store import connect_rag_database, ensure_studio_tables, store_chunks, store_documents, store_embeddings


def memory_mb() -> float:
    try:
        import psutil
        import os
        return round(psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024), 1)
    except ImportError:
        # macOS reports bytes; Linux reports KiB.
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return round(peak / (1024 * 1024) if peak > 10_000_000 else peak / 1024, 1)


def extract_document(filename: str, raw: bytes) -> tuple[str, str]:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in {"txt", "md", "markdown"}:
        text = raw.decode("utf-8-sig", errors="replace")
        title = filename.rsplit(".", 1)[0]
    elif suffix == "pdf":
        import fitz
        with fitz.open(stream=raw, filetype="pdf") as pdf:
            text = "\n".join(page.get_text("text") for page in pdf)
        title = filename.rsplit(".", 1)[0]
    else:
        raise ValueError("Upload a PDF, TXT, or Markdown file")
    text = text.strip()
    if len(text) < 20:
        raise ValueError("Could not extract at least 20 characters of text")
    if len(text) > 100_000:
        text = text[:100_000]
    return title[:300], text


def _update_job(connection, job_id: str, *, step: str, status: str = "processing", **values) -> None:
    allowed = {"document_id", "chunk_count", "embedding_count", "memory_mb", "peak_memory_mb", "error_message"}
    assignments = ["step=%s", "status=%s", "updated_at=now()"]
    params: list = [step, status]
    for key, value in values.items():
        if key in allowed:
            assignments.append(f"{key}=%s")
            params.append(value)
    params.append(job_id)
    with connection.cursor() as cursor:
        cursor.execute(f"UPDATE rag.studio_ingestion_jobs SET {', '.join(assignments)} WHERE id=%s", params)
    connection.commit()


def start_job(owner_id: int, filename: str, password: str | None) -> str:
    job_id = str(uuid.uuid4())
    with connect_rag_database(password) as connection:
        ensure_studio_tables(connection)
        connection.execute(
            "INSERT INTO rag.studio_ingestion_jobs (id, owner_id, filename, status, step) VALUES (%s,%s,%s,'queued','uploaded')",
            (job_id, owner_id, filename),
        )
        connection.commit()
    return job_id


def process_upload(job_id: str, owner_id: int, filename: str, raw: bytes, password: str | None,
                   source_url: str = "", reuse_notes: str = "", document_title: str = "") -> None:
    connection = None
    peak = memory_mb()
    try:
        connection = connect_rag_database(password)
        ensure_studio_tables(connection)
        _update_job(connection, job_id, step="extracting", memory_mb=memory_mb())
        title, text = extract_document(filename, raw)
        title = document_title.strip()[:300] or title
        peak = max(peak, memory_mb())
        document_id = str(uuid.uuid4())
        dataset = f"social_studio_user_{owner_id}"
        _update_job(connection, job_id, step="chunking", document_id=document_id, memory_mb=memory_mb(), peak_memory_mb=peak)
        model = __import__("rag.pipeline", fromlist=["load_platform_model"]).load_platform_model()
        chunks = chunk_text(text, title, model.tokenizer)
        if not chunks:
            raise ValueError("The document did not contain usable text")
        for chunk in chunks:
            chunk["document_id"] = document_id
        peak = max(peak, memory_mb())
        _update_job(connection, job_id, step="embedding", chunk_count=len(chunks), memory_mb=memory_mb(), peak_memory_mb=peak)
        vectors = embed_passages([chunk["text"] for chunk in chunks])
        peak = max(peak, memory_mb())
        _update_job(connection, job_id, step="indexing", memory_mb=memory_mb(), peak_memory_mb=peak)
        store_documents(connection, [{
            "_id": document_id, "title": title, "text": text,
            "metadata": {"original_filename": filename, "owner_id": owner_id,
                         "source_url": source_url or None, "reuse_notes": reuse_notes or None},
        }], dataset)
        chunk_ids = store_chunks(connection, chunks, dataset, PLATFORM_CHUNKING)
        store_embeddings(connection, chunk_ids, vectors, PLATFORM_MODEL)
        connection.commit()
        _update_job(connection, job_id, step="complete", status="succeeded", chunk_count=len(chunks),
                    embedding_count=len(chunk_ids), memory_mb=memory_mb(), peak_memory_mb=max(peak, memory_mb()))
    except Exception as exc:
        if connection:
            connection.rollback()
            try:
                _update_job(connection, job_id, step="failed", status="failed", error_message=str(exc)[:500],
                            memory_mb=memory_mb(), peak_memory_mb=max(peak, memory_mb()))
            except Exception:
                pass
    finally:
        if connection:
            connection.close()


def get_job(job_id: str, owner_id: int, password: str | None) -> dict | None:
    with connect_rag_database(password) as connection:
        ensure_studio_tables(connection)
        row = connection.execute(
            "SELECT id, filename, status, step, document_id, chunk_count, embedding_count, memory_mb, peak_memory_mb, error_message, created_at "
            "FROM rag.studio_ingestion_jobs WHERE id=%s AND owner_id=%s", (job_id, owner_id),
        ).fetchone()
    if not row:
        return None
    keys = ["id", "filename", "status", "step", "document_id", "chunk_count", "embedding_count", "memory_mb", "peak_memory_mb", "error_message", "created_at"]
    return dict(zip(keys, row))


def list_user_jobs(owner_id: int, password: str | None) -> list[dict]:
    with connect_rag_database(password) as connection:
        ensure_studio_tables(connection)
        rows = connection.execute(
            "SELECT id, filename, status, step, document_id, chunk_count, embedding_count, memory_mb, peak_memory_mb, error_message, created_at "
            "FROM rag.studio_ingestion_jobs WHERE owner_id=%s ORDER BY created_at DESC LIMIT 20", (owner_id,),
        ).fetchall()
    keys = ["id", "filename", "status", "step", "document_id", "chunk_count", "embedding_count", "memory_mb", "peak_memory_mb", "error_message", "created_at"]
    return [dict(zip(keys, row)) for row in rows]


def list_user_documents(owner_id: int, password: str | None) -> list[dict]:
    dataset = f"social_studio_user_{owner_id}"
    with connect_rag_database(password) as connection:
        ensure_studio_tables(connection)
        rows = connection.execute(
            """
            SELECT d.document_id, d.title, d.metadata, d.created_at,
                   count(DISTINCT c.id) AS chunk_count,
                   count(DISTINCT e.chunk_id) AS embedding_count,
                   coalesce(sum(length(c.content)),0) AS indexed_characters
            FROM rag.documents d
            LEFT JOIN rag.chunks c ON c.dataset=d.dataset AND c.document_id=d.document_id AND c.chunking_version=%s
            LEFT JOIN rag.embeddings e ON e.chunk_id=c.id AND e.model_id=%s
            WHERE d.dataset=%s GROUP BY d.document_id, d.title, d.metadata, d.created_at
            ORDER BY d.created_at DESC
            """, (PLATFORM_CHUNKING, PLATFORM_MODEL, dataset),
        ).fetchall()
    return [{"document_id": r[0], "title": r[1], "metadata": r[2], "created_at": r[3], "chunk_count": r[4],
             "embedding_count": r[5], "indexed_characters": r[6]} for r in rows]
