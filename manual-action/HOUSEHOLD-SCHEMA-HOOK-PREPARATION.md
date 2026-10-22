# Root-run household schema preparation hook

This is **local preparation**, not a deployed application migration. The new
optional receipt evidence does not claim that application wiring, authorization,
D1 deployment, KMS/BYOC activation, or runtime encryption is implemented.

## Order and bounded operation

After startup recovery and replay of preserved receipt batches, but before source
discovery/ingestion, the current checkout's runner invokes the reviewed
`scripts/prepare_household_schema.py` with the current Python executable and
`-I -B`. It supplies no shell, no `--output-dir`, no stdin and no inherited
environment. The helper validates the reviewed schema in **in-memory SQLite**;
it does not open an existing database, request household input, fetch data,
copy private rows, load credentials, or create database/artifact files.

The subprocess has a 15-second deadline. Timeout kills its process group with a
bounded two-second cleanup wait. `KeyboardInterrupt` also kills the helper and
propagates, including when cleanup fails; cancellation does not start ingestion.
Missing/unsafe sources, mismatched reviewed dependencies, helper failure,
timeout, and malformed output produce finite non-ready evidence without blocking
independent public ingestion. Helper stdout is accepted only if it is at most
16 KiB and exactly matches the reviewed readiness contract; raw stdout, stderr,
paths and exception messages are never copied into public receipts.

The wrapper reads only the fixed helper, preparation plan, immutable baseline
`cloud/schema.sql`, and the two new security/household migration sources. Each
source is capped at 2 MiB and symlinks are refused. SQL order is baseline,
security, then household. The plan must match those current source digests; the
unchanged baseline must match the af99 source digest. Sources are checked again
after the helper finishes. Helper, plan, and SQL hashes are included in the
implementation binding; the sanitized preparation outcome also binds job
identity so a prior failure cannot masquerade as successful preparation.

## Receipt compatibility

`offmenu-ingest-supplement/1` gains optional `household_schema_preparation`, with
schema `offmenu-household-schema-preparation/1`. Existing receipt/supplement
schemas, canonicalization, historical bytes and the receipt branch transport
remain unchanged. The companion is still hash-bound from the main receipt and
uses the existing private spool and additive, non-force receipt publication.

The strict field permits only fixed enums, source SHA-256 values, fixed false
activation flags, nullable bounded preparation counts and fixed check outcomes.
A successful result is `schema_prepared_app_wiring_pending`, with 31 empty
prepared domain tables, zero private rows and passed SQLite checks. A missing or
failed preparation reports unknown (`null`) counts, not zero live data. In all
cases `application_wiring_verified=false`, `deployment_performed=false`, and
`security_activation=not_performed`. These temporary-schema counts are separate
from, and do not overwrite, actual per-domain stored ingestion totals.

No private-input solicitation or external private ingest is introduced. All
historical catalog assignments and existing staging/app data remain intact.
Legacy same-branch mode retains its historical receipt shape; this companion is
published only through the existing isolated receipt transport.

## Focused validation and composition

Twelve generated hook tests passed: exact no-output/no-shell command; source,
plan and baseline checks; symlink refusal; finite sanitized failures; bounded
timeout cleanup; cancellation propagation; startup batch replay before
preparation/discovery; continued ingestion on unavailable preparation; exact old
companion bytes; strict optional fields; implementation/job binding; and the
existing 64 KiB companion bound with worst finite evidence. No Git or Foo action
is used by those tests. One existing Git-backed receipt test's outcome assertion
now selects receipt objects explicitly because the new companion is present even
without ingestion evidence; that Git-backed test was not rerun for this patch.

The final reviewed household/security composition was also run once through the
wrapper's default in-memory path. It reported the expected prepared status and
31 empty domain tables; a before/after snapshot found every composition file
unchanged. This was not a live database or deployment test. The exact source
pins and prepared-base preimages are recorded in
`HOUSEHOLD-SCHEMA-HOOK-SOURCE-MANIFEST.json`.

Compose this hook with the separately reviewed household and BYOC preparation
overlays. The unchanged af99 `cloud/schema.sql` is a local test dependency and
must not be uploaded as a modified/new baseline source. This patch changes no
schema migration, raw data, host state, workflow, credentials, or remote branch.
