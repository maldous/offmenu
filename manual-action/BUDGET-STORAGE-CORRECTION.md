# Global-budget fanout correction and bounded storage visibility

## Scope and evidence

This is a narrow incremental correction over the frozen 48-path next-run
preparation. It does not alter that original candidate, any historical receipt,
source/catalog disposition, database schema, source row, or retained error.

The verified prior terminal receipt stopped at a disk reserve. The coordinator's
adapter-group `except Exception` treated a propagated `BudgetExceeded` as an
adapter failure and reported that failure against every remaining selected
source. This amplified callback errors and failed-assignment reporting even when
those sources were never read. Callback errors are **not** evidence that the same
number of durable SQL error rows or corresponding disk bytes exist. This patch
makes no retrospective disk-growth attribution and performs no history repair,
cleanup, deletion, or compaction.

## Coordinator correction

A dedicated `BudgetExceeded` branch preserves the completed/partial summaries
already returned by the owning store, marks the domain partial, and stops later
adapter groups without inventing failures for the unread tail. Global budget
checks run before group construction, before missing/unreadable descriptor error
bookkeeping, and before each group dispatch. A context-level ingest boundary
also checks before fingerprinting/opening/registering the next source, including
custom test handlers which omit their own boundary check.

The first latched `disk_reserve`, `wall_time_cap`, or `cancelled` observation keeps
its existing sanitized report semantics, separate from source/row errors.
Accepted batches and source-version cursors remain resumable. Existing durable
errors and source statuses in untouched tails remain unchanged. Real non-budget
adapter failures retain the existing independent-group behavior.

The store's **per-source row cap is unchanged**: it returns a partial source
summary without latching a global stop, allowing subsequent sources to run.
Adapters, cursor rules, ownership checks, row counters, catalog identities and
source ordering have not been changed.

## Metadata-only storage field

The existing `offmenu-ingest-supplement/1` gains optional `storage_sizes`, schema
`offmenu-storage-sizes/1`. Old fields and canonical receipt/supplement bytes remain
valid and unmodified. Every engine publication samples at most the fixed 24
staging paths: database, WAL and SHM for each of the eight domains. Private-domain
paths use the existing private-household staging layout. Only `lstat` metadata
and cached ancestor checks are used: no content opens, SQLite/COUNT queries,
file copies, directory enumeration, recursion through data trees, or cache/source
scans are added. No path, source identifier, exception text or private data enters
the field.

The field explicitly states `fixed_runner_staging_database_paths_only`,
`independent_file_metadata_not_atomic`, and `lstat_only_no_content_reads`.
Per-domain arrays follow the declared `files` and `metrics` labels:

- `logical_bytes` is the observed `st_size`.
- `allocated_bytes` is the observed `st_blocks * 512`, when available.
- An absent fixed file is known zero. Denied, symlinked, nonregular, or unavailable
  observations are unknown (`null`), never guessed from logical size.
- Totals are present only when all relevant observations are known and within
  the bounded integer range. Known-file counts distinguish unknown from zero.
- Cache logical and allocated bytes are always `null`, with scope `not_measured`.

Allocated-byte sums are **not deduplicated or exclusive physical disk usage**,
not a filesystem-wide total, not cache coverage, and not attribution of ingest
growth. SQLite checkpoints may change files between observations; these sizes do
not assert an atomic snapshot or inspect database ownership/content. The scope
is the runner's fixed staging path layout, not arbitrary filesystem files.
Telemetry failure produces unknown observations and does not block independent
ingestion. This module is included by the runner's existing `ingest_*.py`
implementation binding. The existing companion size cap remains 64 KiB.

## Focused validation

Eighteen generated/local focused tests passed, without a broad suite:

- Seven new coordinator tests, including actual barcodes/citations/dietary
  adapters with 1,000-descriptor tails; committed partial-prefix resume;
  completed-prefix and historical-error preservation; custom handlers;
  pre-dispatch/missing-source checks; later-group suppression; time/cancellation;
  ordinary failure isolation; and continued per-source-cap processing.
- Six new telemetry tests prohibit content/SQLite opens and enumeration, verify
  exactly 24 fixed leaf metadata observations plus bounded cached ancestors,
  sparse files and sidecars, denied/symlink/unknown semantics, strict optional
  schema and old canonical bytes, worst finite companion size, and nonblocking
  observation failures.
- Five selected existing regressions cover supplier cursor resume and per-source
  cap behavior, budget/error evidence separation, acquired-first source ordering,
  and ordinary missing/acquired-source isolation.

The verified prior terminal receipt and supplement also passed the new validators
without changing their canonical bytes. Their hashes and exact base preimages
are in `BUDGET-STORAGE-CORRECTION-SOURCE-MANIFEST.json`. Tests used generated
sources/temporary stores; no Foo, remote repository, live database, cleanup,
restart, or deployment action was performed for this patch.
