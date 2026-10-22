# Supplier global-budget stop correction — 2026-10-22

## Result
Generated regression suite: **593 tests, zero failures/errors, two environment skips** (fixture filesystem has no POSIX ACL support; optional pyarrow is not installed). Ten new focused tests are included. This is implementer verification; independent review is recorded separately against the frozen hashes.

## Exact scope
Five changed/new source and test files are frozen under `files/`; `CHANGED-FILES.json` records each before/after SHA-256 and the accompanying patch. The original published source manifest is not rewritten. Baseline source preimages match the frozen publication package byte for byte.

- Suppliers check global budgets before each eligible source, so an exhausted run does not manufacture zero-cursor partial checkpoints for its unread tail.
- When the store returns `resource_cap`, suppliers recheck only the global budget and stop if it is exhausted. The source-local row limit still permits later sources; malformed-source isolation remains intact.
- The first global stop is latched per domain/invocation: `cancelled`, `wall_time_cap`, or `disk_reserve`. A temporary disk recovery cannot restart a domain after its recorded stop.
- Stop evidence records contemporaneous elapsed milliseconds, free bytes when observable, effective reserve, wall-time limit, and source-row limit without incrementing row-error counts. Null free bytes explicitly mean unavailable observation.
- Effective defaults are visible: reserve **2,147,483,648 bytes**, `max_seconds=0` (unlimited), and `max_rows_per_source=0` (unlimited). Fractional wall-time limits remain exact finite values.
- Evidence uses bounded fixed enums/numbers, no paths, source identities, exception text, or rows. The optional `budget_stops` extension preserves old evidence/1 receipt validation and survives supplement validation.

## Resume and compatibility evidence
- Pre-exhausted disk/time/cancellation with 2,000 eligible generated descriptors: zero source checkpoint rows and all 2,000 assignments remain `not_yet_read`.
- Mid-batch disk/time/cancellation: one active checkpoint at committed cursor 2; one buffered record remains uncommitted; the other 1,999 assignments remain `not_yet_read`. Resuming writes exactly the remaining three records with the same source fingerprint/version.
- Source-local row caps continue across three sources; malformed rows still allow later sources and completed-with-errors reuse remains unchanged.
- Domain-boundary global-stop exceptions report zero invented row errors; private-text and invalid-number telemetry is removed.
- Existing supplier, engine, evidence, receipt, pending-work, and generated end-to-end integration regressions are included in the full suite. Receipt tests use generated temporary repositories, never a project remote.

## Unchanged boundaries
No adapter version, store schema, fingerprint construction, cursor, existing live state, prior manifest, or raw dataset is changed. No live Foo ingest, retained-data deletion, filesystem scan, code-branch mutation, acquisition, or network publication was performed by this correction. This does not repair already-created historical zero-cursor checkpoints or retrospectively prove the previous run's exact stop cause. The next authorized ingest can resume with the correction after independent review and publication.

## Verification artifacts
- `generated-regression-results.json`: exact test count, skips, duration.
- `generated-regression-tests.log`: local generated-fixture runner log (not required for source publication).
- `supplier-global-budget-stop.patch`: narrow patch against the frozen published package.
- `CHANGED-FILES.json`: five-file source/test allowlist and hashes; self-hash intentionally excluded.
