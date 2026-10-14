# RAG development database

Independent PostgreSQL 16 + pgvector database for retrieval experiments. The existing campaign database and dashboard are not migrated or modified.

## Start and initialize

Run from the repository root, with Docker Desktop running:

```bash
docker compose --env-file rag/.env -f rag/docker-compose.yml up -d --wait
docker compose --env-file rag/.env -f rag/docker-compose.yml exec -T db psql -U flyrank_rag -d flyrank_rag -v ON_ERROR_STOP=1 < rag/sql/init.sql
```

Copy `rag/.env.example` to `rag/.env` and replace its password for a new checkout. The local password file is ignored by Git. Host connections use `127.0.0.1:5433`, database and user `flyrank_rag`, and the password from `rag/.env`.

Stop without deleting data:

```bash
docker compose --env-file rag/.env -f rag/docker-compose.yml stop
```

## Tables

- `rag.documents`: original documents and source metadata.
- `rag.chunks`: passages and their chunking version.
- `rag.embeddings`: vectors, model identifiers and dimensions.
- `rag.queries`: benchmark search inputs.
- `rag.relevance_labels`: expected relevant documents per benchmark split.
- `rag.studio_ingestion_jobs`: owner-scoped document-processing status, chunk/vector counts, and sampled worker memory.

The starter campaign sources are under `data/raw/social_studio_eval/`; they are separate from the SciFact benchmark. The dashboard stores uploaded documents in the `social_studio_user_<id>` collection, uses BGE-small with a 256-token sentence-overlap/title chunker, and filters retrieval by collection, model revision, and chunking version. Embeddings use a variable-dimension vector column so model selection can follow database setup. Search currently uses exact cosine ranking, which is appropriate for the small campaign library. The API adds its document-job table and any missing base RAG tables idempotently; the SQL initialization file also defines them for a fresh database.

## Embedding cache

Run `python -u -m rag.examples.retrieval_baseline` in the embedding environment. It prepares current chunks, then reuses `data/processed/scifact/` only when its manifest, ordered chunk text, dimensions, normalization and SHA-256 checksums match. Missing, corrupt or outdated caches are rebuilt; a failed embedding run leaves existing files untouched. Data files are replaced atomically and the manifest is published last, so partial updates are rejected on load. Run only one cache writer per directory at a time.

`manifest.json` records model name and pinned revision, embedding dimensions, passage prefix, normalization, chunking version, implementation hashes, library versions, chunk count, UTC creation time and hashes of both saved files. Batch size is a processing setting and does not invalidate this cache. The importer validates the manifest before connecting to the database; run the baseline again when it rejects an old cache. Do not attach a manifest to legacy vectors by guessing their provenance.

## Controlled retrieval experiments

Run `python -u -m rag.examples.retrieval_experiments` to evaluate all training-labelled queries against the full corpus with k values 1, 3, 5, 10 and 20. Compare the existing 512-token sentence-overlap baseline with no overlap, a 256-token budget, and omitted titles. Model revision, E5 prefixes and normalization stay fixed. These settings are for retrieval development, not model training.

Results are saved under `data/results/scifact_development/`: one JSON per configuration with full per-query rankings and relevance IDs, `comparison.json`, and `REPORT.md`. Source hashes and model settings are recorded. Query vectors and experimental passage vectors have separate checksum-validated caches; the original passage cache and database are not changed. The script reuses embeddings for identical passage text within a run. Keep test labels held out while selecting development settings.

Export graph-ready CSV files after a run:

```bash
python -m rag.examples.export_retrieval_results
```

- `summary.csv`: one row per configuration and k, including averaged metrics, chunk counts and run settings.
- `per_query_metrics.csv`: individual query metrics at each k for distributions and paired comparisons.
- `rankings.csv`: ordered document IDs and relevance indicators for each query and configuration.

Metric values are fractions from 0 to 1. Multiply precision/recall by 100 for percentage charts. Full per-query JSON retains query text and all positive relevance IDs. The completed first comparison has 20 summary rows, 16,180 query-metric rows and 64,720 ranking rows. All summary means were verified against the per-query CSV, and 94 project tests passed. At k=5, no tested chunking variant clearly improved on the baseline; larger k improves recall but increases evidence volume. No held-out accuracy or downstream post quality claim follows from these development results.

## Embedding-model comparison

Run `python -u -m rag.examples.embedding_model_comparison`. This compares the verified E5-small-v2 baseline with BGE-small-en-v1.5 (384 dimensions) and E5-base-v2 (768 dimensions) on the same 5,680 passages and 809 development queries. Required input prefixes are model-specific; normalized exact cosine search and document aggregation remain fixed. Inputs exceeding a model's token limit cause an error instead of truncation.

Each alternative has its own pinned revision and checksum-validated vector cache under `data/results/scifact_models/`. CSV summaries, per-query metrics, rankings, raw JSON and a report are exported automatically. Test labels are never read. No alternative is automatically promoted into the application or PostgreSQL. New-model encoding timings are measured on CPU, while the baseline's existing preparation time includes cache reads and must not be used as an inference-speed comparison.

If Hugging Face's Xet transfer stalls in this environment, run with `HF_HUB_DISABLE_XET=1` to use standard HTTP downloads of the same model files.

## BGE chunking comparison

Run `python -u -m rag.examples.bge_chunking_experiments` after the model comparison. It reuses verified BGE query and passage vectors and creates new embeddings only for changed texts. Four native BGE configurations compare 512-token overlap/title, 256-token overlap/title, 512-token no-overlap/title, and 512-token overlap/no-title. Token budgets count BGE special tokens without an E5 passage prefix. The previous fixed-chunk BGE score is retained as a separate reference because those chunks reserved E5 prefix space.

Results, per-query metrics, document rankings, graph-ready CSVs and per-configuration vector caches are stored under `data/results/scifact_bge_chunking/`. The original fixed-chunk reference plus four native configurations produce 25 summary rows across five k values. Development queries are unchanged; test labels remain held out. Configuration changes are experimental and do not alter the existing database or embedding defaults.

## Adaptive result-count experiments

Run `python -u -m rag.examples.adaptive_retrieval_experiments`. It reuses validated BGE vectors and compares fixed-k=10, the published largest-gap rule applied to document rankings, and bounded variants using 30 candidates, a five-document cap, a 1500 BGE-token estimate budget, and buffers of 1, 2 or 3. Fixed-k=5 is a compact control. Results, selected document/chunk IDs, similarity scores, per-query metrics and graph-ready CSVs live under `data/results/scifact_adaptive/`.

Precision uses each query's actual selected count, and empty selections score zero. Context sizes are estimates based on BGE token counts including special tokens; actual generation prompts require their own tokenizer budget. This is document-level adaptation, not an exact reproduction of the paper's passage-level benchmark. The selection rule never reads relevance labels. All 106 tests passed; fixed-k=10 reproduces the previous development metrics. Current defaults and database contents are unchanged.

## Experiment plots

Run `python -m rag.examples.plot_retrieval_results` to render existing result CSVs without rerunning retrieval. Eight figure groups are saved as PNG and SVG under `data/results/plots/`, with a Markdown gallery and source-hash manifest. Figures cover model and chunking comparisons across k, adaptive metrics, context tradeoffs, per-query distributions, and chunk counts. All figures were visually inspected, including legends, labels and distribution outliers. The shareable `retrieval_plots.zip` includes the figures, gallery, manifest and source CSVs.

## Repository data policy

The SciFact benchmark inputs, processed chunk/vector cache, and per-query rankings are intentionally excluded from Git to keep the repository lightweight. To rerun retrieval experiments, download the [official BEIR SciFact archive](https://public.ukp.informatik.tu-darmstadt.de/thakur/BEIR/datasets/scifact.zip) and extract it under `rag/data/raw/`; generated caches are recreated by the baseline script. Compact reports, summary tables, and plots are included. The small campaign-source examples in `data/raw/social_studio_eval/` are also included with their provenance notes.
