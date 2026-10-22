# Evidence collected by the next natural run

The normal `./run` now collects the evidence needed to decide the following
iteration. There is no separate diagnostic command, new fetch, mandatory
diagnostic pass, source replay, database migration, writer lock, or permission
repair. Reporting failures do not stop ingestion. This is source/test work;
it is **not evidence that a live ingestion has run or completed**.

## Current process versus next-source capabilities

The immutable engine at **5a00c8fbfc5c4372580d8fae7593d92300132a7d** (Git blob
`190f5e94e22aaf34cff8fb6e9e3a5ee4f2f871d9`) was directly inspected. It emits
pre-worker/checkpoint/final pending-work counts and broad
read/written/unchanged/errors/skipped/reuse counters. Its adapter-error callback
has no source key, the public allowlist omits `MalformedRecord`, and its private
last-1,000 error sample is not a complete histogram. It does **not** emit the
later error-telemetry or evidence extensions.

The engine at **c792d3b71bc7907e96b6688242e090ede100b6ab** (Git blob
`5593fdbef159331e328538381827e760a0da82c9`) adds durable class/origin counts and
current-invocation callback reason counts. Those populations differ; do not add
them or equate either to distinct damaged rows. See `INGEST-ERROR-TELEMETRY.md`.
Neither immutable revision contains `ingest_evidence.py`. A Python process
already running the older revision is not hot-patched by publishing new source.

## Optional integration contract

```python
collector = EvidenceCollector(sources, config, catalog=None)
evidence = collector.capture("pre", report,
    results=private_results, pending_private=already_collected_pending_snapshot)
# Same call with "checkpoint" during normal publication; "post" at the end.
```

Construct once per invocation. Put the returned strict `offmenu-ingest-evidence/1`
object under the optional `ingest_evidence` report field. The engine passes its
already-obtained pending snapshot directly; the helper never opens SQLite or a
source file. Optional import/constructor failures must also be caught by the
engine. `sanitize_evidence` strips unapproved values and `validate_evidence`
strictly rejects extra keys, boolean counts, wrong enums and count mismatches.

The main receipt binds a reviewed readable sanitized supplemental by SHA-256
and byte count; the receipt publisher owns atomic transport/recovery of both.
The supplemental is bounded by 64 KiB, not silently shortened to fit the former
12-KiB Actions-output budget. Finite-enum worst-case generated fixtures exercise
all populated histograms and 16-digit counters. No base64/raw-data channel is
introduced. A missing/tampered supplemental is not successful evidence delivery.

## What the next output contains

* **Catalog coverage:** exact inspected/remaining descriptor counts, format,
  eligibility and finite reason histograms. Counts describe the inspected subset
  until `remaining == 0`; complete evidence does not imply complete discovery.
* **Source-to-adapter/domain mapping:** fixed engine dispatcher names plus a
  finite reviewed acquired-adapter route matrix. Parallel eligibility vectors
  have explicit column names. These are routing/qualification observations, not
  proof that the adapter accepted the source or populated an application DB.
* **Schema shape:** finite shape and shape-basis histograms, allowlisted field
  presence counts, unknown-field counts, omitted-field counts, and types only
  when existing descriptors explicitly supplied types. All other types are
  `unknown`; field-name recognition is not successful parsing. Reviewed manifest
  capabilities are explicitly distinct from sampled field observations.
* **Before/current/delta:** the existing counters plus failed-source assignment
  counts. Accepted rows, stored rows, unresolved references, deduplication and
  coverage remain `null` unless the owning worker supplied the exact metric.
  `written + unchanged` is deliberately **not** relabelled accepted/unique: the
  unchanged shortcut can describe previously completed source versions. Legacy
  counters retain their original semantics; deltas can be negative when a
  report revises a provisional count and are not silently clamped.
* **Error and parser attribution:** existing scoped class/origin/reason telemetry
  is referenced without duplicating it. The supplemental separately carries
  finite acquired-adapter source-summary reason/schema-needed histograms.
  Those cover completed source summaries in this invocation, not all durable
  historical errors or still-running source readers. Unrecognized labels
  coalesce into `other`, preserving their counts without exposing messages.
  Parser input/emission/non-recipe/quarantine/archive/duplicate counters are
  exposed when supported, explicitly scoped to observed parser projections;
  they are not store acceptance, cross-source entity deduplication, or app writes.
* **Checkpoint coverage:** timestamped sampled cursor totals from the existing
  metadata snapshot, read-complete versus resumable counts, and explicit detail
  rows inspected/total. Cursor units are yielded adapter-output ordinals, not
  physical lines, compressed bytes, or remaining entity counts. Synthetic empty
  household requirements are not source assignments. The original pending-work
  summary still carries full aggregate coverage outside the bounded sample.
* **Resources:** engine worker/time/limit observations, free disk metadata, and
  process-lifetime CPU/high-water RSS when supported. No shell command is run.
* **Next action codes:** continue existing ingest/catalog/evidence scan; review
  unsupported schemas, source errors or held inputs; restore required source
  read access; repair report delivery; supply genuine private input; or verify
  application binding. These are decisions, not permission grants or commands
  to escalate access. `retained_ingest_complete` still does not mean app-bound.

Every snapshot says `independent_observations_not_atomic`. Engine counters,
separate database metadata snapshots, descriptor sampling and resource values
cannot honestly represent one cross-domain transaction. The observation time
is the capture time, not a fabricated common database transaction timestamp.

## Local-only detail and finite cost

`state_dir/ingest-evidence.private.json` is a mode-0600 replaceable diagnostic
checkpoint. It holds the descriptor-scan position and catalog identity so later
natural checkpoints/runs continue the same catalog rather than repeatedly
scanning only its prefix. A changed catalog restarts this **diagnostic** scan,
never ingestion cursors or receipts.

Unrecognized structures receive up to 32 local schema-only representatives in
`ingest-schema.private.json`: descriptor index, opaque key, bounded field names,
finite required-action/reason, and explicit no-source-rows status. The public
report exposes only the fixed artifact name, SHA-256, representative count and
coverage status. The existing private catalog resolves the source provenance.
A missing/replaced schema artifact is reported unavailable; a hash is not a
claim that its contents are accessible remotely. These representatives help
local follow-through, but field absence/type ambiguity still requires adapter
evidence: the cloud cannot reconstruct an unseen schema from its digest.

No raw source rows or exception text are collected. Household field names and
individual identifiers are excluded even from schema representatives. No raw
catalog, private artifact, pathname, source URL or arbitrary field name enters
public reports. A public known-field/type counter is not a household record.

Each descriptor, checkpoint, and adapter-summary slice is independently capped
at 2,000 items and 50 ms by default (hard maxima 10,000 items/250 ms). Existing
metadata is reused; the collector does not add dataset scans, metadata database
queries, source hashes, locks or worker waits. Its own private files are regular
files only, bounded to 1 MiB and read nonblocking; symlink/FIFO refusals and
write failures become fixed quality codes. The bounded private serialization
and resource-stat calls are additional small I/O, not an absolute hard realtime
promise. Diagnostics may remain partial; this is never an ingest prerequisite.

## Generated verification

`python3 -B -m unittest discover -s manual-action/tests -p test_ingest_evidence.py -v`
covers resume/budget accounting, pre/post semantics, no source/SQLite reads,
privacy/household redaction, private schema digest/availability, parser reason
histograms, permission blockers, acquired routing, EOF-versus-resume cursors,
strict transport rejection, FIFO/symlink/failure isolation, current-versus-next
source distinctions and worst-case readable supplemental size. Fixtures create
only temporary synthetic files; they do not touch Foo, real datasets, live DBs,
fetch caches, credentials, Actions, or any published branch.

## Invocation timing (coordinator-owned)

The fixed six-column `performance` projection uses only existing engine progress
events and monotonic clocks. It reports domain wall-clock milliseconds, active
source age, time since its latest event, known active source catalog file size,
number of timed ingest calls, and their cumulative elapsed milliseconds. Timers
stop when a domain completes; cached completed-cursor checks are included in
timed calls. Unknown values are null. File size is not bytes consumed (and may
be compressed), elapsed time is not CPU time, and no ETA is inferred. Per-source
operation timings and known source sizes also remain in private domain summaries.
No source or database body is reread to obtain these metrics.

The fixed `source_order` field declares acquired adapter groups before retained
work in each domain, while retaining one writer per domain and unchanged source
identities/cursors. Bounded new inputs cannot starve behind the retained catalog;
this does not assert that all remaining retained work finishes in one invocation.
