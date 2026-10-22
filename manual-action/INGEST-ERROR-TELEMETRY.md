# Retained ingestion error telemetry

This is a reporting-only change. It does not restart a running process, fetch
anything, change the plan, revise adapter versions, modify acceptance rules,
migrate databases, reset cursors, or add source retries. Existing `./run` remains
the entry point; no separate diagnostic command is required.

## What the existing counters mean

- Recipe `UnsupportedSource` is reported through the adapter error callback even
  for an unrecognized/lead-only object. The adapter also increments `skipped`.
  Therefore `errors` is not a count of damaged recipes, and it is not a count of
  failed source assignments. Classification failures, malformed input, and
  storage/iterator failures previously shared this broad counter.
- Store cursors count **yielded adapter records**, not physical input lines.
  Resuming an incomplete stream can revisit earlier input and repeat callback
  observations while skipping already committed yielded records. Negative
  adapter-error ordinals are deduplicated in the existing `source_errors` table.
  Observed callback counts and durable error entries must not be added together.
- A source read to EOF with errors is stored as `complete_with_errors`, reported
  as `partial`, and requires review. It has no remaining source read. On the next
  unchanged invocation the store returns before entering its reader, preserving
  the errors without replaying completed ingestion. An incomplete/failed source
  retains the existing resume behavior; this patch does not change that policy.
- The old live `adapter_error` event had no source key and the coordinator only
  updated ordinary counters for keyed source events. Adapter classes could also
  disappear from the capped last-1,000 error sample, and `MalformedRecord` was
  missing from the engine's public allowlist. The new diagnostics are independent
  of both problems. Existing `read`/`written`/`errors` counter semantics remain
  unchanged and can lag until a batch/source checkpoint.

These are code and generated-fixture findings, **not an attribution of any
specific Foo error count to a particular class, reason, source, or damaged row**.
Actual attribution needs host-generated metadata evidence.

## Checkpoint fields and their scopes

Each domain gains optional `error_telemetry` in sanitized reports and receipts:

| Field | Meaning |
| --- | --- |
| `status` | `available`, `not_created`, or `unknown` for the durable metadata snapshot; unknown is not evidence of zero errors. |
| `durable_scope` | Always `all_retained_source_versions`; historical versions are included explicitly. |
| `class_counts` | Number of existing `source_errors` entries per allowlisted exception class. Unknown class names become `source_error`. |
| `origin_counts` | Negative stored ordinals are `adapter_callback`; other entries are `record_or_stream`. Neither is a count of distinct damaged recipes. |
| `reason_scope` | Always `current_run_adapter_callbacks`. |
| `reason_counts` | Counts of observed callbacks, including callbacks repeated during a normal incomplete-source resume. Only curated exact reason tokens pass; all other messages become `other_or_unavailable`. |
| `historical_reasons` | Always `not_recorded`; old exception messages were never stored and their reasons cannot be recovered honestly. |

Reason counts do not cover exceptions handled directly by the store, for which
durable class/origin counts remain available. Durable classes and current-run
reasons are different populations and need not equal each other or the legacy
domain `errors` counter. Diagnostics are sampled; they are not one cross-domain
transaction. Empty new-run reason counts do not mean historical failures lacked
causes. Existing `error_codes` also includes the allowlisted observed/durable
classes; finite reason enums stay in the explicitly scoped telemetry field.

No source key/version, filename, path, raw message, source value, URL, or payload
is permitted in public telemetry. The finite maps fit the existing 64 KiB receipt
and spool bound. Historical receipts without the extension still validate with
their original digest.

## Next natural run and private evidence

After normal source publication and at the next existing `./run`, the **first
checkpoint, before any workers start**, reads existing owned staging metadata
and reports historical classes. Completed and `complete_with_errors` inputs
retain their existing no-reader-replay shortcut. New callback reasons are
reported during work rather than only when the domain finishes. An already
running Python process is not hot-patched and will not gain these fields.

At each reporting checkpoint, the engine writes
`.git/offmenu-runner/ingest/source-errors.private.json` in a normal runner state
directory (or `state_dir/source-errors.private.json` for injected configurations).
This mode-0600 local file contains class/origin counts grouped by opaque source
key and source version, plus current-invocation callback class/reason counts per
opaque source key. It contains no raw messages or source payloads and is never
staged by the receipt publisher. It is a replaceable diagnostic snapshot, not a
new ingestion checkpoint or an append-only reason journal. Old reasons remain
unavailable; an interrupted invocation may have callback observations newer than
its last diagnostic snapshot.

The collector queries only `ingest_meta` and `source_errors`, through separate
read-only/query-only connections with ownership checks, symlink refusal and a
bounded query deadline. It never selects source paths or `records` payloads.
Unavailable diagnostics become unknown and do not stop independent ingestion.

## Synthetic verification

`tests/test_ingest_errors.py` covers exact enum filtering and privacy, historical
class recovery, unchanged-source no replay, `complete_with_errors` versus failed
assignments, running checkpoints, capped-sample rollover, existing resume
callback/durable-slot semantics, all-version scope, unchanged schema/cursors,
unknown metadata, optional diagnostic failure isolation, receipt compatibility,
strict rejection of injected fields/booleans, and bounded transport size.

One fixture has three lead-only objects and one supported recipe: one record is
written, three `UnsupportedSource` entries are retained, the assignment is
partial rather than failed, and a second invocation writes nothing. Another
fixture observes five callbacks across an interrupted run and resume, while
retaining three durable error entries. These synthetic outcomes demonstrate why
aggregate error counters alone cannot establish the cause of the live run.
