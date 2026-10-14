# Adaptive selection development comparison

Document-level adaptation: one highest-scoring chunk per unique document. Token counts are BGE-tokenizer estimates including special tokens, not generation-model token counts. Paper-style uses the published gap rule on documents; this is not a reproduction of its passage-level benchmark.

| Method | Precision | Recall | MRR | Mean documents | Mean estimated tokens | Maximum documents |
|---|---:|---:|---:|---:|---:|---:|
| fixed_k10 | 0.0989 | 0.8701 | 0.7159 | 10.00 | 3354 | 10 |
| paper_style_document_adaptive | 0.1419 | 0.8422 | 0.7132 | 6.86 | 2288 | 37 |
| bounded_adaptive_cap5 | 0.3478 | 0.7504 | 0.6947 | 2.53 | 826 | 5 |
| fixed_k5_control | 0.1817 | 0.8119 | 0.7092 | 5.00 | 1653 | 5 |
| bounded_cap5_buffer2 | 0.2631 | 0.7762 | 0.7028 | 3.32 | 1082 | 5 |
| bounded_cap5_buffer3 | 0.2318 | 0.7904 | 0.7053 | 3.88 | 1249 | 5 |

Precision divides by actual selected count per query; empty selections score zero. Fixed k=5 is an additional control to distinguish adaptation from simply returning fewer documents. Scores use only positive qrels; unlabelled results are not confirmed irrelevant. All variants share the same model, query vectors and document rankings. No labels influence the selection rule. Test labels were not read. No generation or judge calls were made. Existing application defaults and PostgreSQL data were not changed.

Paper-style: largest gap among top 90% of documents, followed by a five-document buffer. Bounded: top-30 candidate documents, one-document buffer, cap of five and 1500 estimated BGE tokens. Buffers of two and three are additional development comparisons with the same cap and token estimate budget. These parameters are not proven optimal. The corpus-wide method can still select a large context; a relative score gap does not guarantee relevance or detect an unanswerable query.

Reference: https://aclanthology.org/2025.emnlp-main.1017.pdf

## Interpretation and validation

Paper-style document adaptation raises labelled precision from 9.89% to 14.19%, reduces mean selected documents from 10 to 6.86 and reduces estimated context tokens from 3354 to 2288, but lowers recall from 87.01% to 84.22%. It selected as many as 37 documents for one query, so it is not a hard-budget policy.

The bounded policy with buffer 3 selects at most five documents and stays within 1500 estimated BGE tokens. It averages 3.88 documents and 1249 estimated tokens, with 23.18% precision and 79.04% recall. Smaller buffers reduce context further but lose more recall. The fixed-k=5 control achieves 81.19% recall with five documents and 1653 estimated tokens, so adaptation has not demonstrated a quality improvement over a small fixed count; its demonstrated benefit is reducing context volume, with a recall tradeoff. No generated-answer or draft factuality evaluation was performed.

Every mean was checked against the per-query data, bounded limits were verified for all queries, and the fixed-k=10 result reproduces the earlier baseline. All 106 project tests passed. All six method variants (three requested policies plus fixed-k=5 and two bounded-buffer controls) are saved for graphs. Held-out labels remain untouched.
