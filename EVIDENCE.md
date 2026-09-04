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
