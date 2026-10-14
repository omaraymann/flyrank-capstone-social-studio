# SciFact test configuration comparison

Both configurations were evaluated on the same 300 held-out queries and 5,183-document corpus with BGE-small and k=5.

| Configuration | Chunks | Precision@5 | Recall@5 | MRR@5 | No labelled hit |
|---|---:|---:|---:|---:|---:|
| BGE 512, no overlap | 5,658 | 0.1687 | 0.7615 | 0.6743 | 65/300 |
| BGE 256, one-sentence overlap | 10,470 | 0.1713 | 0.7665 | 0.6823 | 65/300 |

256/overlap minus 512/no-overlap: precision +0.0027, recall +0.0050, MRR +0.0081; 4,812 additional chunks (85.0% more).

The test split has now been used to compare two configurations, so these results are diagnostic and should not be presented as an untouched final test estimate. SciFact labels positive matches only; unlabelled results are not confirmed irrelevant. Detailed per-configuration reports, query metrics, rankings and checksums are stored in the adjacent scifact_test_bge_* folders.
