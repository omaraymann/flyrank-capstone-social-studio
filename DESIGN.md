# Social Media Studio design

## Problem

Turn one stored article into validated platform-specific drafts, require human approval, and publish safely through interchangeable adapters.

## Data model

- `User` owns source posts.
- `SourcePost` stores the immutable generation source.
- `PlatformVariant` stores one draft per source and platform.
- `ScheduleSlot` stores approved publishing times.
- `PublishDelivery` stores one idempotent delivery result per schedule.
- `PublishAttempt` records every actual adapter call and its outcome.

## API surface

- `POST /auth/signup`, `POST /auth/login`
- Source post ingestion and retrieval endpoints
- Variant generation and review endpoints
- Scheduling and publish-history endpoints
- `GET /health`

## Platform profiles

- X: concise, at most 280 characters and 3 hashtags.
- LinkedIn: professional, at most 3,000 characters and 5 hashtags.
- Discord: approved text delivered through a configured webhook.

## Publisher interface

Every adapter implements `publish(content, idempotency_key)` and returns an external identifier and optional URL. Business logic depends only on this interface.

## Durable worker

The worker polls PostgreSQL for due schedules and claims them with a time-limited lease using `FOR UPDATE SKIP LOCKED`. Attempt history is committed around each adapter call. Retryable failures use exponential backoff; an expired Discord call is marked uncertain for manual reconciliation because the remote API cannot guarantee idempotency.

## Non-goal

Image generation and engagement analytics are outside the base capstone.
