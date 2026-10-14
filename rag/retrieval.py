import numpy as np

def retrieve_topk(query_vector, document_vectors, top_k: int=5):
    """
    Retrieve the top-k most similar documents to a given query vector.

    Args:
        query_vector (np.ndarray): The vector representation of the query.
        document_vectors (np.ndarray): The matrix of document vectors.
        top_k (int): The number of top documents to retrieve.

    Returns:
        tuple: Document row indices and their similarity scores,
               ordered from highest to lowest.
    """

    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")

    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    if query_vector.ndim != 1:
        raise ValueError("query_vector must be a 1D array")

    if document_vectors.ndim != 2:
        raise ValueError("document_vectors must be a 2D array")

    if query_vector.shape[0] != document_vectors.shape[1]:
        raise ValueError("Query and document dimensions must match")

    if not np.isfinite(query_vector).all():
        raise ValueError("query_vector must contain only finite values")

    if not np.isfinite(document_vectors).all():
        raise ValueError("document_vectors must contain only finite values")

    # Compute the dot product between the query vector and all document vectors.
    scores = document_vectors @ query_vector

    # Get the indices of the top-k scores.
    top_k_indices = scores.argsort()[::-1][:top_k]

    # Return document indices and their matching scores.
    return top_k_indices, scores[top_k_indices]

def retrieve_top_documents(query_vector: np.ndarray, chunk_vectors: np.ndarray, chunks: list[dict], top_k: int = 5,) -> list[str]:
    """Rank unique documents by their highest-scoring chunk."""
    if not isinstance(top_k, int) or isinstance(top_k, bool):
        raise TypeError("top_k must be an integer")
    if top_k < 1:
        raise ValueError("top_k must be positive")
    if len(chunks) != len(chunk_vectors):
        raise ValueError("Chunks and vectors must have matching counts")

    # Reuse validation and score every chunk.
    indices, scores = retrieve_topk(
        query_vector,
        chunk_vectors,
        top_k=max(1, len(chunks)),
    )

    document_ids = []
    seen = set()

    for index in indices:
        document_id = chunks[index]["document_id"]

        if document_id not in seen:
            seen.add(document_id)
            document_ids.append(document_id)

        if len(document_ids) == top_k:
            break

    return document_ids
