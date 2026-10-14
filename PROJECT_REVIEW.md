# Social Media Studio: review and portfolio roadmap

## What the project does

An authenticated user imports an article or pastes Markdown, generates social drafts, reviews them, schedules approved variants, and observes publishing attempts. Generation supports local templates and optional OpenRouter calls. X and LinkedIn publishing are mocks; Discord has a real webhook adapter.

The stack is Python, FastAPI, SQLAlchemy, Alembic, PostgreSQL, JWT authentication with Argon2 password hashing, React, Vite, and Docker Compose. The API, migration runner, dashboard, and polling worker are separate processes. SQLite is used in automated tests.

## Architecture

```text
React dashboard -> authenticated FastAPI routes -> service layer -> SQLAlchemy
                                               |                   |
                                               |                   PostgreSQL
                                               v                   |
                                      LLM provider interface        v
                                      OpenRouter adapter      polling worker
                                                                  |
                                                         publisher interface
                                                         mocks / Discord
```

`SourcePost` preserves the input article. `PlatformVariant` holds one draft per platform and its review state. `ScheduleSlot` represents the durable job. `PublishDelivery` records the latest outcome and stable idempotency key, while `PublishAttempt` preserves individual attempts. `GenerationRun` records AI configuration, usage, repair count, latency, and outcome.

Important code paths:

- `app/api/posts.py`: ownership checks, ingestion, generation, and generation history.
- `app/services/review.py`: permitted review transitions and content validation.
- `app/services/llm_generation.py`: generation, one repair per invalid platform draft, and usage audit.
- `app/services/worker.py`: claims, lease recovery, and exponential retry backoff.
- `app/services/publishing.py`: delivery records, adapter calls, and attempt history.
- `frontend/src/App.jsx`: authentication, composition, review, scheduling, and observability.

## Strengths already demonstrated

- A complete product workflow, including human approval before scheduling.
- Owner-scoped access across posts, variants, schedules, and delivery history.
- Provider and publisher interfaces that support dependency injection in tests.
- Structured LLM output plus deterministic validation and bounded repair.
- Database-backed jobs, attempt history, lease recovery, and stable delivery keys.
- Separate migration service to avoid startup migration races.

These are useful portfolio foundations. The code is not yet evidence of production-scale reliability or of training an ML model.

## Review findings to address next

| Priority | Finding and evidence | Suggested change |
|---|---|---|
| High | Discord network failures become ordinary `PublisherError` exceptions in `app/publishers/discord.py`; the worker retries them. A timeout can happen after Discord accepts the message. Lease expiry has an uncertain-outcome path, but request failures do not. The manual publish route also bypasses the retry endpoint's uncertainty guard. | Introduce explicit uncertain outcomes, persist them, and block both automatic and manual redispatch until reconciliation. Test response loss after remote acceptance. |
| High | Claim selection uses PostgreSQL row locks, but lease recovery reads and updates expired rows without locks. Manual publish does not claim the schedule through the worker's lease protocol. SQLite tests cannot establish PostgreSQL concurrency guarantees. | Use a common atomic claim protocol and locked recovery, then test simultaneous workers, manual publication, and lease expiry against PostgreSQL. |
| High | `fetch_article` buffers the complete response before checking its size. Host DNS is checked separately from the HTTP connection. | Enforce the byte limit while streaming; use destination enforcement or controlled egress to close DNS rebinding gaps. Add fetch timeout, size, redirect, and address tests. |
| Medium | `generate_variant` bounds X's excerpt but can exceed the LinkedIn and Discord limits; even X can overflow with a long source URL. `create_variants` leaves deterministic validation errors unhandled. | Budget all draft sections, handle oversized links explicitly, and return a safe validation response rather than an internal server error. |
| Medium | OpenRouter handles timeouts and HTTP status errors but not all `httpx.RequestError` failures. Concurrent generation requests can race on the unique source/platform constraint. | Normalize transport failures into audited errors; handle generation conflicts with rollback and an explicit API response. |
| Medium | Posts and delivery history are unbounded. History fetches attempts once per delivery. The dashboard reloads the full collections. | Add pagination, batch attempt loading, and appropriate query indexes. Measure query counts and response times with larger datasets. |
| Medium | The dashboard defaults to paid generation, lacks regeneration controls for imported campaigns, and does not automatically reflect worker updates. | Add provider availability, recovery after generation failure, and polling or streamed status updates. |
| Medium | Compose runs development servers; there is no committed CI pipeline, production readiness check, or worker heartbeat. JWT secrets have a development fallback. | Add CI, production configuration validation, health/readiness checks, structured logs, and worker monitoring. |

These findings are from code inspection; they are not all demonstrated failures. Historical live-run claims in `EVIDENCE.md` were not rerun during this review.

## First feature added: workspace analytics

`GET /analytics/summary` aggregates only the authenticated owner's data. It returns campaign totals, variant/schedule/delivery counts by status, delivery success rate, AI run outcomes, recorded tokens, repair count, reported cost coverage, and average recorded latency.

The React dashboard displays the summary and now counts drafts across the workspace rather than using only the selected campaign's variants. Existing action refreshes also refresh analytics; a manual refresh updates worker results.

Metric definitions:

- All metrics are lifetime workspace totals.
- Delivery success is successful deliveries divided by successful plus failed deliveries; processing deliveries are excluded. This measures latest delivery outcomes, not first-attempt reliability.
- Tokens and cost include recorded usage from failed runs and repairs.
- Unknown cost remains `null`; a reported zero cost remains zero. Cost coverage tells the user how many runs reported a cost.
- Average latency excludes missing values. A failed run's recorded latency is included.
- These metrics describe operations, not impressions, clicks, or engagement.

The feature requires no schema migration or paid provider calls. SQL aggregation avoids loading every record to compute the summary. Regression tests cover authentication, empty data, mixed outcomes, ownership isolation, and zero-versus-missing cost.

Validation on October 9, 2026: all 33 backend tests passed using a temporary Python 3.12 environment, and the frontend production build passed using Node 22 and the committed package lock. One upstream Starlette/AnyIO deprecation warning remains. PostgreSQL concurrency, live providers, and browser layout were not tested in this pass. The existing Windows virtual environment and pre-existing tracked edits were preserved.

## Roadmap across all three target roles

Complete each slice with a demo, meaningful tests, and measured evidence before moving on.

| Order | Feature | Product result | Skills demonstrated |
|---|---|---|---|
| 1 | Publishing reliability fixes and PostgreSQL integration tests | Safe behavior under response loss, competing workers, and restarts | Backend engineering, transactions, concurrency, fault injection, idempotency |
| 2 | CI and reproducible deployment | Every change runs backend tests, frontend build, and migration checks | CI/CD, Docker, deployment configuration, automated validation |
| 3 | Versioned brand profiles and retrieval of approved examples | Drafts reflect each user's brand and cite the internal examples used | AI engineering, retrieval, embeddings, tenant isolation, prompt versioning |
| 4 | Offline AI evaluation suite | Compare prompts/models on platform rules, CTA inclusion, fidelity, cost, and latency | ML/AI evaluation, dataset design, experiment tracking, regression analysis |
| 5 | Calendar with cancel/reschedule and live job updates | Users manage and observe planned campaigns | Full-stack engineering, state management, accessible UI, timezone handling |
| 6 | Per-user platform connections and real publishing | Users publish through their own accounts or webhook configuration | OAuth where supported, encrypted credential storage, adapter contracts, external APIs |
| 7 | Engagement ingestion and experiments | Users compare post performance using real platform data | Data ingestion, analytics, experiment design, visualization |

Retrieval should start with a small curated collection and a measured baseline. Add a vector store only when retrieval quality or scale justifies it. Model evaluation provides stronger ML/AI evidence than merely adding another model provider. Engagement work depends on actual platform access; do not substitute fabricated metrics.

## CV wording supported by the implementation

Use only bullets for work you personally implemented and can explain. Do not present this review or a generated change as proof of personal mastery without walking through it and validating it yourself.

- Built a social content workflow using FastAPI, SQLAlchemy, PostgreSQL, and React, with JWT authentication, owner-scoped access, and human approval before scheduled publishing.
- Integrated structured LLM generation through a provider abstraction, with platform validation, bounded repair, and token, cost, and latency auditing.
- Implemented a database-backed publishing worker with leases, exponential backoff, adapter-based delivery, and persisted attempt history.
- Added authenticated workspace analytics using SQL aggregation and React, including publishing outcomes and AI usage with explicit handling of missing cost data.

The publisher bullet needs qualification in interviews: X/LinkedIn delivery is mocked, Discord cannot guarantee remote idempotency, and concurrent PostgreSQL behavior still needs integration coverage. Do not claim exactly-once delivery.

Current skill inventory: Python, FastAPI, REST APIs, Pydantic, SQLAlchemy, PostgreSQL, Alembic, JWT, Argon2, React, JavaScript, Vite, Docker Compose, pytest, LLM integration, structured outputs, prompt engineering, and background-job design. Add retrieval, ML evaluation, OAuth, CI/CD, and observability only after completing the corresponding work.
