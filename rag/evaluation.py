def recall_at_k(
    retrieved_document_ids: list[str],
    relevant_document_ids: set[str],
    k: int = 5,
) -> float:
    """Measure how many relevant documents appear in the top-k results."""
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")

    if k < 1:
        raise ValueError("k must be positive")

    if not relevant_document_ids:
        raise ValueError("The query must have relevant-document labels")

    top_results = set(retrieved_document_ids[:k])
    matched_documents = top_results & relevant_document_ids

    return len(matched_documents) / len(relevant_document_ids)

def precision_at_k(
    retrieved_document_ids: list[str],
    relevant_document_ids: set[str],
    k: int = 5,
) -> float:
    """Measure the fraction of top-k positions that are relevant."""
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")

    if k < 1:
        raise ValueError("k must be positive")

    if not relevant_document_ids:
        raise ValueError("The query must have relevant-document labels")

    top_results = set(retrieved_document_ids[:k])
    matched_documents = top_results & relevant_document_ids

    return len(matched_documents) / k

def reciprocal_rank_at_k(
    retrieved_document_ids: list[str],
    relevant_document_ids: set[str],
    k: int = 5,
) -> float:
    """Return the reciprocal rank of the first relevant result within top-k."""
    if not isinstance(k, int) or isinstance(k, bool):
        raise TypeError("k must be an integer")

    if k < 1:
        raise ValueError("k must be positive")

    if not relevant_document_ids:
        raise ValueError("The query must have relevant-document labels")

    for rank, document_id in enumerate(
        retrieved_document_ids[:k], start=1
    ):
        if document_id in relevant_document_ids:
            return 1.0 / rank

    return 0.0