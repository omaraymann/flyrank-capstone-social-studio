"""Score-gap selection; labels are never used to choose the cutoff."""
import math
import numpy as np


def largest_gap_count(scores: np.ndarray, search_fraction: float = 0.9) -> int:
    """Return items before the largest adjacent drop in descending scores."""
    scores = np.asarray(scores)
    if scores.ndim != 1 or not np.isfinite(scores).all():
        raise ValueError('Scores must be a finite 1D array')
    if not 0 < search_fraction <= 1:
        raise ValueError('search_fraction must be in (0, 1]')
    if len(scores) == 0: return 0
    if np.any(np.diff(scores) > 0): raise ValueError('Scores must be sorted descending')
    if len(scores) == 1: return 1
    search_count = min(len(scores), max(2, math.ceil(len(scores) * search_fraction)))
    gaps = scores[:search_count - 1] - scores[1:search_count]
    # +1 converts the zero-based gap index to the number of retained items.
    return int(np.argmax(gaps)) + 1


def adaptive_count(scores, buffer=5, candidate_limit=None, max_selected=None):
    """Apply largest-gap selection and optional explicit count limits."""
    if not isinstance(buffer, int) or isinstance(buffer, bool) or buffer < 0:
        raise ValueError('buffer must be a nonnegative integer')
    for limit in (candidate_limit, max_selected):
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
            raise ValueError('Limits must be positive integers')
    scores = np.asarray(scores)
    candidates = scores if candidate_limit is None else scores[:candidate_limit]
    count = min(len(candidates), largest_gap_count(candidates) + buffer)
    return count if max_selected is None else min(count, max_selected)


def apply_token_budget(token_counts, selected_count, budget):
    """Keep a ranked prefix within the estimated passage-token budget."""
    if budget < 1: raise ValueError('Token budget must be positive')
    total, count = 0, 0
    for tokens in token_counts[:selected_count]:
        if tokens < 0: raise ValueError('Token counts must be nonnegative')
        if total + tokens > budget: break
        total += tokens
        count += 1
    return count, total
