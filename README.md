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
