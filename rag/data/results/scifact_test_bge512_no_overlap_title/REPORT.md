# SciFact held-out test retrieval evaluation

This is a one-time evaluation of the configuration selected using development data.

- Queries: 300
- Corpus documents: 5183
- Chunks: 5658
- Model: BAAI/bge-small-en-v1.5 (5c38ec7c405ec4b44b94cc5a9bb96e735b38267a)
- Chunking: BGE-tokenizer-aware 512-token chunks, sentence-based, no overlap, title included
- Ranking: maximum cosine score over a document's chunks; unique documents returned
- k: 5

| Metric | Mean across queries |
|---|---:|
| Precision@5 | 0.1687 |
| Recall@5 | 0.7615 |
| MRR@5 | 0.6743 |

Queries with no labelled relevant document in the top 5: 65/300.

SciFact qrels provide positive relevance judgements only. A retrieved document without a positive label is unjudged, so precision here means the fraction of retrieved results with a recorded positive label; it does not prove every other result is irrelevant.

Raw per-query metrics, top-five rankings, source checksums and query-vector cache are saved beside this report. The scores are the final test estimate for this selected setup; any further tuning should use development data, not this test split.
