# BGE-small chunking development comparison

All 809 training-labelled queries, all 5183 documents, same pinned model and cached query vectors. Native BGE token counting includes special tokens and no passage prefix. The original fixed-chunk model-comparison result is retained separately as a reference. Test labels were not read.

| Configuration | Chunks | k | Precision | Recall | MRR |
|---|---:|---:|---:|---:|---:|
| original_fixed_chunks_reference | 5680 | 1 | 0.6242 | 0.5951 | 0.6242 |
| original_fixed_chunks_reference | 5680 | 3 | 0.2781 | 0.7591 | 0.6965 |
| original_fixed_chunks_reference | 5680 | 5 | 0.1815 | 0.8098 | 0.7053 |
| original_fixed_chunks_reference | 5680 | 10 | 0.0986 | 0.8676 | 0.7121 |
| original_fixed_chunks_reference | 5680 | 20 | 0.0515 | 0.9044 | 0.7144 |
| bge_512_overlap_title | 5669 | 1 | 0.6230 | 0.5939 | 0.6230 |
| bge_512_overlap_title | 5669 | 3 | 0.2781 | 0.7591 | 0.6961 |
| bge_512_overlap_title | 5669 | 5 | 0.1815 | 0.8098 | 0.7049 |
| bge_512_overlap_title | 5669 | 10 | 0.0986 | 0.8676 | 0.7117 |
| bge_512_overlap_title | 5669 | 20 | 0.0515 | 0.9044 | 0.7140 |
| bge_256_overlap_title | 10470 | 1 | 0.6267 | 0.5977 | 0.6267 |
| bge_256_overlap_title | 10470 | 3 | 0.2785 | 0.7601 | 0.7005 |
| bge_256_overlap_title | 10470 | 5 | 0.1829 | 0.8180 | 0.7111 |
| bge_256_overlap_title | 10470 | 10 | 0.0981 | 0.8667 | 0.7165 |
| bge_256_overlap_title | 10470 | 20 | 0.0513 | 0.9015 | 0.7186 |
| bge_512_no_overlap_title | 5658 | 1 | 0.6279 | 0.5988 | 0.6279 |
| bge_512_no_overlap_title | 5658 | 3 | 0.2794 | 0.7637 | 0.7011 |
| bge_512_no_overlap_title | 5658 | 5 | 0.1817 | 0.8119 | 0.7092 |
| bge_512_no_overlap_title | 5658 | 10 | 0.0989 | 0.8701 | 0.7159 |
| bge_512_no_overlap_title | 5658 | 20 | 0.0515 | 0.9044 | 0.7180 |
| bge_512_overlap_no_title | 5549 | 1 | 0.5970 | 0.5721 | 0.5970 |
| bge_512_overlap_no_title | 5549 | 3 | 0.2748 | 0.7496 | 0.6776 |
| bge_512_overlap_no_title | 5549 | 5 | 0.1802 | 0.8035 | 0.6869 |
| bge_512_overlap_no_title | 5549 | 10 | 0.0974 | 0.8613 | 0.6937 |
| bge_512_overlap_no_title | 5549 | 20 | 0.0513 | 0.9024 | 0.6961 |

Native 512-token overlap/title is the controlled baseline for the three new variants. Original E5 chunks reserve prefix tokens, so their partition differs slightly from native BGE chunks; compare controlled variants against the native BGE baseline. Identical texts reuse vectors, therefore preparation timing is not a pure inference benchmark. All scores are development-set measurements. Application settings and PostgreSQL data were not changed.

## Findings and verification

At k=5, 256-token title/overlap chunks had the highest observed recall (81.80%) and MRR (0.7111), compared with 80.98% and 0.7049 for the native 512-token baseline. This modest 0.82 percentage-point recall gain increases chunks from 5669 to 10470 (about 85% more). The 512-token no-overlap variant reached 81.19% recall and 0.7092 MRR with 5658 chunks. Removing titles reduced recall to 80.35% and MRR to 0.6869. These are development comparisons, not proof of statistically significant improvements or downstream generation quality.

All 25 CSV summary means match 20225 per-query metric rows, with 80900 ranked-document rows exported. All four alternative vector and chunk-file checksums were verified. All configurations contain every one of the 5183 source documents and all chunk token counts fit their budgets. All 100 project tests passed. Existing model configuration and PostgreSQL data remain unchanged; select the intended configuration before evaluating the held-out split.
