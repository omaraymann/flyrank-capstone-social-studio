"""Load the embedding model for our RAG experiments."""

from functools import lru_cache

from rag.config import EMBEDDING_REVISION, EMBEDDING_DEVICE, EMBEDDING_MODEL, QUERY_PREFIX, PASSAGE_PREFIX, EMBEDDING_BATCH_SIZE, NORMALIZE_EMBEDDINGS


@lru_cache(maxsize=1)
def load_model():
    """Load on first use and reuse the model for later calls in this process."""
    # Import here so reading this module doesn't load the ML libraries yet.
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL, device=EMBEDDING_DEVICE, revision=EMBEDDING_REVISION)

def embed_queries(texts: list[str]):
    model = load_model()
    prepared_texts = [QUERY_PREFIX + text for text in texts]
    embeddings = model.encode(prepared_texts, batch_size=EMBEDDING_BATCH_SIZE, normalize_embeddings=NORMALIZE_EMBEDDINGS, convert_to_numpy=True)
    return embeddings

def embed_documents(texts: list[str]):
    model = load_model()
    prepared_texts = [PASSAGE_PREFIX + text for text in texts]

    embeddings = model.encode(prepared_texts, batch_size=EMBEDDING_BATCH_SIZE, normalize_embeddings=NORMALIZE_EMBEDDINGS, convert_to_numpy=True)
    return embeddings