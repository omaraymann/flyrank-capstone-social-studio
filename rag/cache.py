"""Validated, reproducible embedding cache shared by experiments and imports."""

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import numpy as np

from rag import config


def file_hash(path: Path) -> str:
    """Return a SHA-256 digest without loading a whole file into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cache_settings() -> dict:
    """Settings that identify the embedding experiment."""
    return {
        "format_version": 1,
        "model": config.EMBEDDING_MODEL,
        "model_revision": config.EMBEDDING_REVISION,
        "dimensions": config.EMBEDDING_DIMENSIONS,
        "normalized": config.NORMALIZE_EMBEDDINGS,
        "passage_prefix": config.PASSAGE_PREFIX,
        "chunking_version": config.CHUNKING_VERSION,
        "chunking_code_sha256": file_hash(Path(__file__).with_name("chunking.py")),
        "embedding_code_sha256": file_hash(Path(__file__).with_name("embeddings.py")),
        "libraries": {name: version(name) for name in
                      ("sentence-transformers", "transformers", "torch")},
    }


def serialize_chunks(chunks: list[dict]) -> bytes:
    return "".join(json.dumps(chunk, ensure_ascii=False, sort_keys=True) + "\n"
                   for chunk in chunks).encode("utf-8")


def validate_vectors(vectors: np.ndarray, count: int) -> None:
    if vectors.shape != (count, config.EMBEDDING_DIMENSIONS):
        raise ValueError("Cached vector shape does not match chunks and dimensions")
    if not np.issubdtype(vectors.dtype, np.floating) or not np.isfinite(vectors).all():
        raise ValueError("Cached vectors must contain finite floating-point values")
    if config.NORMALIZE_EMBEDDINGS and not np.allclose(
        np.linalg.norm(vectors, axis=1), 1.0, atol=1e-5
    ):
        raise ValueError("Cached embeddings are not normalized")


def load_embedding_cache(output_dir: Path, expected_chunks: list[dict] | None = None):
    """Reject missing, mismatched, or modified files before returning aligned data."""
    manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
    if manifest["settings"] != cache_settings():
        raise ValueError("Embedding cache settings changed; rerun retrieval_baseline")
    if set(manifest["files"]) != {"chunks.jsonl", "chunk_embeddings.npy"}:
        raise ValueError("Cache manifest has an unexpected file list")
    for name, digest in manifest["files"].items():
        if file_hash(output_dir / name) != digest:
            raise ValueError(f"Cache checksum mismatch: {name}")
    chunk_bytes = (output_dir / "chunks.jsonl").read_bytes()
    if expected_chunks is not None and chunk_bytes != serialize_chunks(expected_chunks):
        raise ValueError("Prepared chunks changed; rebuild embeddings")
    chunks = [json.loads(line) for line in chunk_bytes.decode("utf-8").splitlines() if line]
    if len(chunks) != manifest["chunk_count"]:
        raise ValueError("Cache chunk count mismatch")
    vectors = np.load(output_dir / "chunk_embeddings.npy", allow_pickle=False)
    validate_vectors(vectors, len(chunks))
    return chunks, vectors


def save_embedding_cache(output_dir: Path, chunks: list[dict], vectors: np.ndarray) -> None:
    """Publish data files first and the manifest last, using atomic replacements."""
    validate_vectors(vectors, len(chunks))
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output_dir) as temporary:
        staging = Path(temporary)
        (staging / "chunks.jsonl").write_bytes(serialize_chunks(chunks))
        np.save(staging / "chunk_embeddings.npy", vectors)
        manifest = {
            "settings": cache_settings(),
            "chunk_count": len(chunks),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "files": {name: file_hash(staging / name) for name in
                      ("chunks.jsonl", "chunk_embeddings.npy")},
        }
        (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        for name in ("chunks.jsonl", "chunk_embeddings.npy", "manifest.json"):
            os.replace(staging / name, output_dir / name)
