# Next-batch committed overall staging totals

Baseline: `af99cdfb4bac3bce9f4badae34333921a0074a76` (publisher-confirmed immutable export).
Candidate is cloud-only. No Git writes/publication, Foo execution, current-run interruption, raw datasets, credentials, or host-database reads occurred.

## Correction

- Each existing domain writer reads its own `ingest_meta.record_count` once on opening its exclusively locked staging store. It captures that value as `stored_records_before`.
- After a successful batch COMMIT, the writer advances its cached count by actual newly inserted record keys, not write attempts. Updates, unchanged rows, skipped/reused input, validation failures and rolled-back batches do not increase the overall count. Previously retained source versions remain counted.
- Existing progress callbacks carry this baseline and committed current total. Sanitized local progress/report fields expose both per domain; writers that have not successfully opened remain null, not zero; a later failure preserves the last committed observed total. The local `stored_totals` aggregate is null until all eight domain totals are known and states that domain checkpoints are not atomic across domains.
- Existing evidence `stored_records` vector slots now carry the overall baseline/current/net growth while domains run. They remain separate from this invocation's `written`, `unchanged`, and `reused_rows` metrics. A baseline captured after the initial pre-worker report fills only the previously unknown stored baseline.
- Completed acquired-adapter groups emit bounded fixed-code diagnostic summaries immediately, allowing an active domain's acquired-parser counts to be seen while its retained tail continues. Defaults are at most 2,000 summaries / 50 ms per group; existing configuration bounds remain 10,000 / 250 ms. This is **completed-group visibility**, not live per-record parser progress. Terminal results replace these snapshots instead of being added to them.

## Boundaries and cost

No `COUNT(*)` scans, heartbeat database reads, extra database writer, source reopen, schema migration, cursor change, adapter identity/version change, or additional remote publication is introduced. The committed-count update is constant-time per committed batch. Parser summaries contain finite-vocabulary counts only; source keys, paths, payloads, free-form reasons, and exception text are excluded.

Counts mean additive staging source-provenance rows across **all retained source versions**. They are not globally distinct foods/recipes, accepted canonical entities, or application-bound database totals. Read-only external reused-store row counts remain separate and must not be added as if independently deduplicated. Stored reference/bridge rows already present in staging remain included.

The metadata counter is trusted as existing writer-owned durable metadata; this patch does not perform an expensive historical recount or repair stale counters. Values are snapshots of the last observed committed batch per domain, not a simultaneous cross-domain transaction. No historical run is rewritten.

Report/evidence schema identifiers, existing evidence vector columns, database schema, and resume semantics remain unchanged; local sanitized-report count fields are additive. `plan_runner` is unchanged: the remote evidence supplement exposes existing per-domain `stored_records` before/current/delta slots. The new local `stored_totals` aggregate is **not newly added to the remote receipt projection**.

## Verification

Generated-only focused tests: 6 passed. Existing directly affected engine tests: 19 passed. Existing evidence tests: 17 passed. Existing finite allowlist receipt/spool-size test: 1 passed. Total: **43 tests passed**, no full-suite run.

Coverage includes prior rows + new inserts + updates + unchanged replay + invalid row + retained version + external reuse; a real report callback observes the committed mid-run database count before the writer finishes; baseline/delta accuracy; COMMIT failure without false growth; unknown writer state; bounded active-domain completed-group diagnostics; privacy filtering; final replacement without duplicate counts. Existing engine tests cover concurrency, writer exclusion, crash/resume and idempotence.

Independent source review by `/root/publish_final_ingest_preparation/startup_review`: PASS against frozen source/test hashes; independently reran the six new tests. No blocking issue found. Source candidate hash is recorded in `CHANGED-FILES.json`.

## Next useful run

Compose this reviewed patch with other approved next-batch corrections. Resolve any disjoint shared-file hunks deliberately. Run only focused composed regressions plus the existing receipt/spool-size test before freezing the combined source. Keep all corrected evidence collection inside the next normal `./run`; do not interrupt or replace the current run, and do not start a diagnostic-only Foo run.

Standalone focused command from `manual-action`:

```sh
PYTHONPATH=tests:. python -m unittest test_ingest_stored_totals test_ingest_engine test_ingest_evidence test_ingest_errors.ErrorTelemetryTests.test_finite_allowlist_fits_existing_receipt_and_spool_size_limit -v
```
