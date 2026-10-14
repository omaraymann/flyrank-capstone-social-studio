# Embedding-model development comparison

Same 5,680 passages, 809 development queries, maximum chunk-score document ranking, exact cosine search and normalized vectors. Test labels were not read.

| Model | Dimensions | k | Precision | Recall | MRR |
|---|---:|---:|---:|---:|---:|
| intfloat/e5-small-v2 | 384 | 1 | 0.6094 | 0.5788 | 0.6094 |
| intfloat/e5-small-v2 | 384 | 3 | 0.2629 | 0.7179 | 0.6726 |
| intfloat/e5-small-v2 | 384 | 5 | 0.1716 | 0.7636 | 0.6808 |
| intfloat/e5-small-v2 | 384 | 10 | 0.0923 | 0.8133 | 0.6865 |
| intfloat/e5-small-v2 | 384 | 20 | 0.0492 | 0.8621 | 0.6892 |
| BAAI/bge-small-en-v1.5 | 384 | 1 | 0.6242 | 0.5951 | 0.6242 |
| BAAI/bge-small-en-v1.5 | 384 | 3 | 0.2781 | 0.7591 | 0.6965 |
| BAAI/bge-small-en-v1.5 | 384 | 5 | 0.1815 | 0.8098 | 0.7053 |
| BAAI/bge-small-en-v1.5 | 384 | 10 | 0.0986 | 0.8676 | 0.7121 |
| BAAI/bge-small-en-v1.5 | 384 | 20 | 0.0515 | 0.9044 | 0.7144 |
| intfloat/e5-base-v2 | 768 | 1 | 0.6378 | 0.6083 | 0.6378 |
| intfloat/e5-base-v2 | 768 | 3 | 0.2666 | 0.7359 | 0.6943 |
| intfloat/e5-base-v2 | 768 | 5 | 0.1768 | 0.7903 | 0.7040 |
| intfloat/e5-base-v2 | 768 | 10 | 0.0963 | 0.8504 | 0.7119 |
| intfloat/e5-base-v2 | 768 | 20 | 0.0509 | 0.8959 | 0.7145 |

Each model uses its documented query/passage formatting. Input lengths were checked without truncation. Model revisions, source hashes, library versions, array checksums and per-query results are saved. New-model CPU timings include inference only; model-loading timings include downloads. Baseline preparation timing includes cache reads and is not comparable to new-model encoding time. Vector-array bytes are storage size, not peak runtime memory. These are development results, not held-out estimates. Existing embedding config, cache, and PostgreSQL data were not changed.

Model cards: https://huggingface.co/intfloat/e5-base-v2 and https://huggingface.co/BAAI/bge-small-en-v1.5

## Observed choice for the next integration step

At k=5, BGE-small-en-v1.5 had the highest observed recall (80.98%) and precision (18.15%); MRR was 0.7053, close to E5-base-v2 at 0.7040. The E5-small baseline recall was 76.36%. This is a 4.62 percentage-point development recall improvement over the baseline, not a held-out claim. Recommend BGE-small as the next candidate for deployment-focused testing; do not automatically switch the current embedding configuration or database.

All 15 summary rows were verified against 12,135 per-query metric rows. Ranked document exports contain 48,540 rows. Both alternative vector-cache hashes were verified. All 97 project tests passed. The baseline encoding runtime was not measured again. Larger k increases recall but also increases evidence volume and must be selected with downstream generation in mind.
