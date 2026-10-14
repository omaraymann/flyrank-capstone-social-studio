# SciFact development retrieval comparison

809 training-labelled queries against all 5,183 documents. Exact cosine search; document score is maximum chunk score. Test labels were not read.

| Configuration | Chunks | k | Precision | Recall | MRR |
|---|---:|---:|---:|---:|---:|
| baseline_512_overlap_title | 5680 | 1 | 0.6094 | 0.5788 | 0.6094 |
| baseline_512_overlap_title | 5680 | 3 | 0.2629 | 0.7179 | 0.6726 |
| baseline_512_overlap_title | 5680 | 5 | 0.1716 | 0.7636 | 0.6808 |
| baseline_512_overlap_title | 5680 | 10 | 0.0923 | 0.8133 | 0.6865 |
| baseline_512_overlap_title | 5680 | 20 | 0.0492 | 0.8621 | 0.6892 |
| 512_no_overlap_title | 5671 | 1 | 0.6044 | 0.5739 | 0.6044 |
| 512_no_overlap_title | 5671 | 3 | 0.2629 | 0.7177 | 0.6700 |
| 512_no_overlap_title | 5671 | 5 | 0.1718 | 0.7639 | 0.6785 |
| 512_no_overlap_title | 5671 | 10 | 0.0922 | 0.8120 | 0.6840 |
| 512_no_overlap_title | 5671 | 20 | 0.0491 | 0.8609 | 0.6868 |
| 256_overlap_title | 10585 | 1 | 0.5921 | 0.5629 | 0.5921 |
| 256_overlap_title | 10585 | 3 | 0.2604 | 0.7126 | 0.6613 |
| 256_overlap_title | 10585 | 5 | 0.1708 | 0.7622 | 0.6710 |
| 256_overlap_title | 10585 | 10 | 0.0930 | 0.8174 | 0.6774 |
| 256_overlap_title | 10585 | 20 | 0.0493 | 0.8609 | 0.6800 |
| 512_overlap_no_title | 5556 | 1 | 0.5933 | 0.5627 | 0.5933 |
| 512_overlap_no_title | 5556 | 3 | 0.2588 | 0.7054 | 0.6562 |
| 512_overlap_no_title | 5556 | 5 | 0.1696 | 0.7581 | 0.6667 |
| 512_overlap_no_title | 5556 | 10 | 0.0915 | 0.8085 | 0.6727 |
| 512_overlap_no_title | 5556 | 20 | 0.0486 | 0.8518 | 0.6752 |

Higher k increases evidence volume as well as recall; these retrieval metrics do not establish generation quality. Precision uses a fixed denominator k and incomplete relevance judgments. Timing includes cache reads where reused, so it is not a controlled embedding-speed comparison. All experiments keep model revision, prefixes, and normalization fixed. Existing production cache and PostgreSQL data were not replaced.
