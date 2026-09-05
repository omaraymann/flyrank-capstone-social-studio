# Social Media Studio

A backend that ingests a published article, creates platform-specific social drafts, sends them through human review, and publishes approved content reliably.

## Current phase

Phases 1–3 are complete. Phase 4 is implemented with interchangeable publishers and idempotent manual delivery; its final live-delivery proof requires a Discord webhook URL.

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
