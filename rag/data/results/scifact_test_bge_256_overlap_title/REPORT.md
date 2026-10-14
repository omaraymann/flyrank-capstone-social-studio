# SciFact held-out test retrieval evaluation

This result supports a diagnostic comparison across configurations. The test split was already evaluated for another setup, so it should not be treated as an untouched final estimate.

- Queries: 300
- Corpus documents: 5183
- Chunks: 10470
- Model: BAAI/bge-small-en-v1.5 (5c38ec7c405ec4b44b94cc5a9bb96e735b38267a)
- Chunking: BGE-tokenizer-aware 256-token chunks, sentence-based, one-sentence overlap, title included
- Ranking: maximum cosine score over a document's chunks; unique documents returned
- k: 5

| Metric | Mean across queries |
|---|---:|
| Precision@5 | 0.1713 |
| Recall@5 | 0.7665 |
| MRR@5 | 0.6823 |

Queries with no labelled relevant document in the top 5: 65/300.

SciFact qrels provide positive relevance judgements only. A retrieved document without a positive label is unjudged, so precision here means the fraction of retrieved results with a recorded positive label; it does not prove every other result is irrelevant.

Raw per-query metrics, top-five rankings, source checksums and query-vector cache are saved beside this report. Since multiple configurations have now been compared on this split, use a new untouched test set for a final unbiased estimate.
