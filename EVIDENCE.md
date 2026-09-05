# Evidence

## Phase 1

- Architecture, data model, API surface, platform profiles, publisher interface, and non-goal are recorded in `DESIGN.md`.
- The automated authentication test proves signup and login.

## Phase 2

- Automated tests cover Markdown ingestion, mocked URL ingestion, distinct X/LinkedIn drafts, ownership isolation, and named length/tone failures.
- The variant regression test requires an X `Quick take` structure and a longer LinkedIn structure with key takeaways and a discussion prompt.

## Phase 3

- Lifecycle tests prove users can list, edit, approve, reject, and schedule their own variants.
- Draft and rejected variants cannot be scheduled; approved variants can.
- Tests cover named validation failures, invalid transitions, timezone/past-date rejection, rejection reasons, and ownership isolation.

## Phase 4

- Repeated-publish tests prove the same schedule invokes its adapter exactly once and returns the stored result thereafter.
- Tests prove Mock X and Mock LinkedIn share the same interface and can be selected without business-logic changes.
- Discord has a real webhook adapter; without a configured secret it fails safely and stores no secret in logs or responses.
- Live Discord proof: schedule `6` published successfully with message ID `1545609778934583326`; an immediate repeated request returned the same message ID with `already_published=true`, while the database retained one successful attempt.

## Phase 5

- The full automated suite has 21 passing tests, including due-schedule claiming, ownership, retry history, expired-lease recovery, and safe manual retry.
- Live automatic proof: schedule `7` was completed by the worker through Mock X without calling the manual publish endpoint; attempt 1 succeeded with external ID `mock-x-d6cfbf12d21258ce`.
- Live restart proof: schedule `8` remained pending with zero attempts while the worker was stopped, then completed through Mock LinkedIn after the worker restarted, with exactly one recorded successful attempt.
- Migration `0005_durable_worker` was applied to PostgreSQL and the API, database, and worker containers ran successfully together.

## Phase 6

- The full suite has 26 passing tests, including LLM campaign controls, few-shot prompting, structured output, deterministic validation, one-shot repair, safe provider failures, audit metadata, and ownership isolation.
- Migration `0006_llm_generation` was applied to PostgreSQL.
- A Compose startup test exposed simultaneous Alembic execution by API and worker; a single migration service now completes before either runtime service starts.
- Real-provider acceptance remains separate from automated tests and requires a locally configured `OPENROUTER_API_KEY`.
- Live OpenRouter acceptance: post `10` generated distinct X and LinkedIn variants through `google/gemini-2.5-flash`; both included the requested call to action. The successful audit recorded 261 input tokens, 138 output tokens, zero repairs, and 1,933 ms latency.

## React dashboard

- The Vite production build completes successfully with zero high-severity dependency vulnerabilities.
- The full suite has 28 passing tests, including dashboard CORS access and private schedule listing.
- Docker serves the dashboard on port `5173` alongside the healthy API, worker, migration service, and PostgreSQL database.
