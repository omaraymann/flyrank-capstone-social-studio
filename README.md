# Social Media Studio

A backend that ingests a published article, creates platform-specific social drafts, sends them through human review, and publishes approved content reliably.

## Current phase

Phases 1–4 are complete: the project has an authenticated content workflow, deterministic review rules, approved-only schedules, interchangeable publishers, idempotent delivery, and a verified real Discord integration.

Phase 4 includes Mock X, Mock LinkedIn, and a real Discord adapter. Set `DISCORD_WEBHOOK_URL` in `.env`, restart the API, and publish a Discord variant to a channel you own.

## Run

```bash
copy .env.example .env
docker compose up --build
```

Open `http://localhost:8000/docs` for the API documentation.

## Test

```bash
python -m pip install -r requirements-dev.txt
pytest
```

## Planned architecture

```text
Article → stored source → variant generation → validation → human review
       → durable scheduler → publisher adapter → publish history
```

## Current non-goal

Image generation and engagement analytics are outside the official base scope.
