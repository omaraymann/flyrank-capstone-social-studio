# Social Media Studio design

## Problem

Turn one stored article into validated platform-specific drafts, require human approval, and publish safely through interchangeable adapters.

## Data model

- `User` owns source posts.
- `SourcePost` stores the immutable generation source.
- `PlatformVariant` stores one draft per source and platform.
- `ScheduleSlot` stores approved publishing times.
- `PublishAttempt` records every delivery attempt.

## API surface

- `POST /auth/signup`, `POST /auth/login`
- Source post ingestion and retrieval endpoints
- Variant generation and review endpoints
- Scheduling and publish-history endpoints
- `GET /health`

## Platform profiles

- X: concise, at most 280 characters and 3 hashtags.
- LinkedIn: professional, at most 3,000 characters and 5 hashtags.

## Publisher interface

Every adapter implements `publish(content, idempotency_key)` and returns an external identifier and optional URL. Business logic depends only on this interface.

## Non-goal

Image generation and engagement analytics are outside the base capstone.
