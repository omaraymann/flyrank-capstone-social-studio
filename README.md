# Social Media Studio

A backend that ingests a published article, creates platform-specific social drafts, sends them through human review, and publishes approved content reliably.

## Current phase

Phase 1 establishes the documented architecture, authenticated FastAPI foundation, PostgreSQL migrations, and reproducible local environment. Content ingestion and generation are implemented in Phase 2.

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
