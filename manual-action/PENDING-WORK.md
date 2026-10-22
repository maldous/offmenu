# What remains to load

The normal `./run` continues best-effort ingestion. Before work, at report
checkpoints, and at the end, its dashboard reports current **source/domain
assignments**: completed, verified native-store reuse, not yet read, partial,
failed, unsupported, held, and unqualified external-ingest assignments.
`user_profiles` and `inventory` are app-managed at application runtime, not
external-data requirements; no household-input request or fetch is appropriate.
A file assigned to several domains contributes several assignments; totals are
not unique physical files, distinct entities, or eight application-bound stores.
The binding remains `additive_staging_not_app_bound`.

## Exact local queue (no rerun required)

For normal `./run`, the private ingest state directory is
`.git/offmenu-runner/ingest/`. Direct `python3 manual-action/ingest_all.py` uses
`manual-action/.local-results/ingest/` unless `--state-dir` overrides it:

- `pending-work.private.json`: per-assignment source path, provider, disposition,
  current metadata version, durable cursor/writes/errors, status, fixed next
  reason, and known size/remaining-count evidence. Unassigned catalog entries and
  app-managed catalog assignments remain explicitly retained. App-managed rows
  have `scope: app_managed`, `status: schema_only`, and
  `excluded_from_pending: true`; they are not missing external work. Keep this
  file local; do not commit it.
- `pending-work.json`: allowlisted public counters only, also attached as
  `pending_work` in ordinary callback/progress/final reports and eligible returns.

For example, inspect pending assets already recorded in the local queue:

```sh
python3 - <<'PY'
import json
from pathlib import Path
p = Path('.git/offmenu-runner/ingest/pending-work.private.json')
for row in json.loads(p.read_text())['sources']:
    if not row.get('excluded_from_pending') and row['status'] not in ('completed', 'reused'):
        print(row.get('domain'), row['status'], row.get('path'), row['next_reason'])
PY
```

Use the configured state directory instead if the command used another one.
Snapshots may become stale after external changes; they are timestamped by the
surrounding progress report, not a claim of a live filesystem watch.

## Honest remaining counts

- `files_remaining` counts discovered source/domain reads still required,
  excluding held/unqualified/awaiting-input assignments and proven EOF reads.
  Unsupported assignments remain visible separately and need an adapter or a
  source correction; this report does not introduce a new ingestion gate.
- `records_remaining` is the remaining **adapter-output ordinal stream**, not raw
  input rows, ingredients implied by recipes, relations, successful writes, or
  unique records. It is `null` (unknown) if any contributing assignment lacks a
  reliable total. `records_remaining_known` and `records_remaining_unknown`
  expose the known subtotal and number of unknown assignments without guessing.
- Reliable expected totals must explicitly be descriptor `expected_records`:
  `{count: nonnegative_integer, reliable: true, unit: 'adapter_records',
  domain: exact_domain, source_version: exact_current_version}`. Cursor and total
  must agree in units/version. Zero is a known count; historical row/byte hints
  and raw input counts never qualify. Current adapters generally have no such
  exact expected totals, so remaining counts normally stay unknown.
- `records_to_write` remains unknown for unfinished work: deduplication, errors,
  filtering, and one-to-many projections prevent equating reads with writes.
  It is zero only for fully completed/reused known assignments. `processed_bytes`
  is unknown because byte progress is not tracked. Known bytes describe whole
  source sizes and are not processed or remaining bytes.
- `catalog_complete: false` means discovery has an **unknown unscanned remainder**;
  global remaining-read/write totals stay unknown even if discovered work is
  complete. New snapshots keep `awaiting_input_domains` empty. The optional
  `scope` extension records policy `external_ingest_only` and exact retained
  `app_managed_assignments` counts for profiles/inventory, outside pending totals.
  Historical snapshots/receipts remain valid and are not rewritten.

## Evidence and limitations

Reporting reads only source checkpoints, ownership markers, and indexed tiny
native-reference metadata rows from existing SQLite staging stores. It never
counts all records, hashes a dataset, reruns an adapter, or mutates a source DB.
A loaded catalog flag is not proof of native-store reuse. The current source
metadata version must match a verified read-only native reference.

Identity uses path/device/inode/size/mtime plus SQLite WAL metadata and adapter
version; it is **not full-content verification**. Completion shortcuts also check
output ownership/ID/count markers and recorded output file/WAL metadata, catching
ordinary replacement or modification even if copied DB IDs and counters persist.
Adversarial changes preserving all metadata are outside this inexpensive check.

Missing/corrupt reporting metadata becomes `status: unknown`, not an ingestion
blocker. Source exceptions remain isolated and accepted batches remain durable.
Public summaries contain only fixed keys, enums, counters, booleans and nulls;
source paths, provider strings, payloads, credentials and exception text stay out.

Python API: `ingest_engine.pending_snapshot(prepared, persist=True)` refreshes a
snapshot without starting ingestion; `collect_pending_work(...)` in
`ingest_pending` returns the safe `summary` and private `sources` detail. Normal
`run_ingest` callbacks already refresh the snapshot, so wrappers need not repeat
SQLite reads at the same checkpoint.

## App-managed scope is not an application-schema deployment

The existing `schema_only` status describes this ingestion path: it creates no
private source rows and preserves existing staging schemas and rows. It does not
assert that typed application migrations have been deployed or that a populated
private store is empty. Actual `stored_records_before`/`stored_records` remain
reported for all eight domains, including nonzero historical private stores and
observed zero counts. App schema/encryption work is a separate deliverable.
