# Social Media Studio

A backend that turns one published article into platform-specific social drafts, sends them through human review, schedules approved content, and publishes it reliably.

## Baseline status

The five baseline phases are complete. Phase 6 adds optional LLM-powered campaign generation through OpenRouter while preserving deterministic generation for offline and zero-cost use.

```text
Article -> source post -> X/LinkedIn variants -> validation -> approval
        -> schedule -> durable worker -> publisher adapter -> attempt history
```

The included adapters are Mock X, Mock LinkedIn, and a real Discord webhook. The mocks make the complete workflow testable without external accounts; Discord demonstrates a real platform delivery.

## Run locally

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Then open the React dashboard at `http://localhost:5173`. Swagger remains available at `http://localhost:8000/docs`. The dashboard, API, background worker, and migration runner operate as separate services against PostgreSQL.

## Campaign knowledge base (RAG)

Start the separate pgvector database and initialize its schema before using document upload:

```bash
[ -f rag/.env ] || cp rag/.env.example rag/.env
# Set the same RAG_DB_PASSWORD in rag/.env and the root .env
docker compose --env-file rag/.env -f rag/docker-compose.yml up -d --wait
docker compose --env-file rag/.env -f rag/docker-compose.yml exec -T db psql -U flyrank_rag -d flyrank_rag -v ON_ERROR_STOP=1 < rag/sql/init.sql
```

Install the updated Python dependencies and restart the API. In the dashboard, upload PDF, TXT, or Markdown files in **Campaign knowledge**. The live job panel reports text extraction, BGE-small chunking, embedding, pgvector indexing, and worker RAM. Documents are isolated by authenticated user in the RAG database. In the campaign composer, turn on **Use retrieved knowledge (RAG)**, optionally select documents, and preview matching passages before generation. Leaving it off keeps the existing source-only campaign flow. The API container connects through `host.docker.internal`; a local API process uses `127.0.0.1` from the root `.env`.

The starter source corpus and provenance manifest are in [rag/data/raw/social_studio_eval](rag/data/raw/social_studio_eval/README.md). The generation model receives retrieved passages as supporting context; the dashboard shows each passage and similarity, while human review remains part of campaign approval.

To create a ready-to-review demo campaign:

```powershell
python scripts/seed_demo.py
```

## Main API workflow

| Step | Endpoint | Result |
|---|---|---|
| Sign up | `POST /auth/signup` | Creates the campaign owner |
| Add content | `POST /posts` | Stores the source article |
| Generate | `POST /posts/{id}/variants` | Produces distinct X and LinkedIn drafts |
| Audit AI | `GET /posts/{id}/generations` | Shows model settings, tokens, cost, latency, repairs, and outcome |
| Review | `PATCH /variants/{id}`, `POST /variants/{id}/approve` | Human edits and approves each draft |
| Schedule | `POST /variants/{id}/schedule` | Queues approved content for a UTC time |
| Observe | `GET /schedules/{id}/history` | Shows every processing attempt and outcome |
| Retry | `POST /schedules/{id}/retry` | Safely requeues a failed delivery when allowed |

## Reliability behaviour

- A database lease lets only one worker claim a due schedule.
- Every real adapter call receives a stable idempotency key and creates an attempt record.
- Transient failures are retried with exponential backoff up to the configured limit.
- Expired mock-platform claims can be recovered automatically.
- An interrupted Discord request is marked uncertain instead of being blindly repeated, because Discord webhooks do not offer an idempotency-key guarantee.
- Restarting the worker does not lose pending schedules because the queue is stored in PostgreSQL.

## Test

```powershell
python -m pip install -r requirements-dev.txt
pytest
```

## Configuration

Copy `.env.example` to `.env`. Discord is optional: set `DISCORD_WEBHOOK_URL` only when publishing to a webhook channel you control. Never commit `.env` or a webhook URL.

For LLM generation, set `OPENROUTER_API_KEY` in `.env` and submit:

```json
{
  "platforms": ["x", "linkedin"],
  "generation_mode": "llm",
  "audience": "data engineers",
  "goal": "traffic",
  "tone": "educational",
  "call_to_action": "Read the full guide"
}
```

The provider is `google/gemini-2.5-flash` by default. Sampling and token limits are backend configuration, prompts include versioned platform examples, and an invalid draft receives one low-temperature repair attempt. Automated tests never call the paid provider.

## Baseline limitations

The scheduler polls PostgreSQL rather than using a separate queue broker, and image generation and engagement analytics remain future extension points.

## Workspace analytics and next steps

The dashboard includes lifetime workspace analytics backed by `GET /analytics/summary`: campaign and status counts, delivery success, and recorded AI tokens, cost coverage, and latency. All metrics are scoped to the authenticated owner. Missing provider cost is displayed as unknown. These are operational metrics; engagement analytics still require platform data.

See [PROJECT_REVIEW.md](PROJECT_REVIEW.md) for the architecture review, known reliability gaps, a prioritized feature roadmap, and CV wording grounded in the implementation.

## On-demand fact checks

Each saved platform draft has a **Check facts** button. It checks source agreement using the shared service in `app/services/factuality.py`: Flash extracts factual spans, then the configured audit model checks evidence and qualifiers. `JUDGE_AUDIT_MODEL` defaults to `google/gemini-2.5-pro`. Each click can make two paid requests through the configured OpenRouter account; generation remains unchanged.

The panel shows **Needs review**, **No issues detected**, **No factual claims found**, or **Evaluation failed**, plus claim reasons, exact source evidence, available cost, and completion time. No issues detected is not a guarantee of accuracy. Save edits before checking; unsaved edits and changed source/draft snapshots mark old checks outdated. Approval remains a manual choice. Model judgments can still miss claims or overflag mixed promotional wording.

Owner-scoped endpoints:

- `POST /variants/{id}/fact-check`: evaluates the saved snapshot and persists success or failure.
- `GET /variants/{id}/fact-check`: returns the latest check, or null if never checked.

The `fact_checks` table preserves all attempts, source/draft snapshots, version/model metadata, full judge results and usage. Concurrent checks for the same draft are rejected; interrupted checks become retryable after a timeout. Failed stages are never reported as passing checks, and missing usage is unknown.

Apply migrations through `0009_rag_generation_audit` with `alembic upgrade head` before running the updated API. The existing Docker migration service applies it automatically on startup. The migration adds RAG mode, model, k, and retrieved-passage snapshots to generation audits. Workspace usage totals cover generation; judge costs are shown on draft cards.


## Optional AI fix suggestions

On a saved draft with a current successful fact check containing unsupported or contradicted claims, click **Suggest a fix**. One additional model call proposes a minimal revision using the source, draft and flagged claims. Review the **Before / Suggested** comparison, then choose **Apply suggestion** or **Dismiss**. Suggestions and available costs persist across reloads.

Applying saves an editable draft and makes the previous fact check outdated. Approval is blocked until a successful fresh check finishes against the revised draft and current source. **Recheck facts** uses the existing two-stage judge; it does not approve automatically. Review any findings before approving. Failed or outdated checks cannot unlock approval. Concurrent edits, source changes, newer checks and repeated application invalidate the proposal; concurrent approval cannot bypass the recheck gate.

- `POST /variants/{id}/fix-suggestions` with `{"fact_check_id": <latest check id>}` creates a proposal.
- `GET /variants/{id}/fix-suggestions/latest` returns the latest proposal or null.
- `POST /variants/{id}/fix-suggestions/{suggestion_id}/apply` explicitly saves it.

The `revision_suggestions` table records the original snapshot, hashes, associated check, full proposed revision, model/prompt version, usage, latency, failures and application time. Platform limits are validated before offering or applying a revision. A generation run's original call to action is validated verbatim when it is still present in the draft; older template/imported drafts without generation metadata rely on the preservation instruction in the revision prompt. The model can still make errors, so the comparison and fresh check remain necessary. Suggestion costs appear separately on draft cards and are excluded from generation analytics.
