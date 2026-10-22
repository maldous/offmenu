# Bounded database reconciliation — next selected `./run` phase

This source preparation is based on published rules-stage commit
`062dc707679e3b7eb726a9a5fe64277758b54573`. It must not replace a running checkout.
The selected candidate plan is `offmenu-run-plan/4`, job
`retained-six-domain-reconciliation`, operation `reconcile_normalized_cache`.
After reviewed publication and confirmation that the previous process has exited,
the normal-user checkout uses the usual `git pull --ff-only && ./run`. Source
publication does not execute Foo. No credentials or additional host route is added.

## Inputs and substantive scope

Only already committed keys from the six public `compact-<domain>.sqlite3` caches
select work. The matching owned staging-DB record and stored provenance are read
through fixed paths to verify the exact cached artifact. Existing rules projections
are revalidated for integrity; **this is not zero parsing/validation CPU work**.
It does not dispatch a new rules-generation stage or write existing caches.
No original downloaded file is read or required. Missing/stale stored information
is isolated as private key-bound quarantine, not a missing-file acquisition gate.

The candidate layer records exact identifier associations, explicit lexical aliases,
canonical units/bases and source-bound relationships. It is not a full ontology or
authoritative entity merge. Only `gs1:gtin14` is global in the default reviewed
registry; even valid GTIN aliases remain syntax-only candidates. Unregistered
namespaces remain scoped. Names such as USDA are not inferred to mean a specific
identifier contract. Exact term observations do not imply synonymy or translation.
Conflict holds preserve both pieces of evidence. See
[EXACT-RECONCILIATION.md](EXACT-RECONCILIATION.md) for the precise semantics.

## Capacity admission, not speculative corpus indexing

The default invocation samples at most 32 new facts, then uses the actual owned
SQLite logical-page growth to admit only another bounded amount of work. Limits:

- at most 50000 discovered keys per invocation;
- at most 128 MiB additional logical output database growth;
- at most 30 minutes, checking time/cancel/resource limits between bounded chunks;
- at least 2 GiB free disk space, plus the component's conservative batch allowance;
- at most 128 keys and 16 MiB transient artifact content per transaction;
- one coordinated database writer, not 24 competing SQLite writers.

Admission can be lower than these ceilings, and may stop at the sample. The sample
is not a forecast that all retained records fit. There is no whole-corpus COUNT,
all-pairs graph, preallocated index, raw-data copy, staging snapshot, or semantic
acceptance claim. SQLite hard page limits and precommit checks bound logical
growth; filesystem journals/metadata also need space, so logical bytes are not an
exclusive physical-disk measurement. Existing output size and current free bytes
are reported explicitly. No automatic deletion, compaction or cleanup occurs.

## Durable resume and incremental changes

Facts, exact cache receipts, cursor/counters and private quarantine evidence commit
in one SQLite transaction. A rejected sample or commit leaves its cursor unchanged.
The cursor uses indexed cache-key order, never mutable rowids. Unchanged snapshots
resume their completed prefix. Changed caches/sources or retry policy start a new
bounded discovery epoch so newly inserted keys sorting below an old cursor are
not lost. Exact successful graph receipts skip repeated projection work; this is
historical reuse, not a claim that a source occurrence is current authoritative truth.

All retained source versions remain distinct. No lexical-latest winner is chosen.
A malformed batch is split into bounded singleton checks. Bad keys retain finite,
private snapshot/retry evidence; resource faults stop globally and never mark the
unread tail as failed. Private retry generation can be changed only through the
reviewed engine configuration, not arbitrary public receipt data. The current
source, compact caches, previous graph facts and quarantine history stay intact.

## Counts, receipts and honest completion

`offmenu-db-reconciliation-report/1` reports only fixed counters/enums/hashes:

- per domain: scanned, indexed_new, indexed_reused, quarantined,
  quarantine_retries, exhausted and a checkpoint digest;
- `scanned = indexed_new + indexed_reused + quarantined`;
- selected-key totals remain **unknown/null** rather than triggering a count scan;
- actual bounded sample rows/bytes, admitted rows, current output logical bytes,
  invocation rows, elapsed seconds, one writer and current free disk bytes.

Snapshot counters are durable, while `invocation_rows` and sample/admission are
bounded to the current invocation. Quarantined counts mean invalid/stale cached
artifacts, **not every unresolved semantic relationship or missing citation**.
`cache_complete` means all six selected cache snapshots are exhausted without
quarantine. It does not prove every staging record was normalized or that future
cache entries are covered. A row/output/time/capacity stop is `partial`, not failure
of every remaining record. A domain without an owned usable cache is unavailable,
not silently treated as empty or complete.

Version4 canonical sanitized receipts and bounded metadata-only supplements use
the existing isolated receipt branch. Historical v2 ingestion and v3 rules receipts
remain byte-for-byte intact. All three private pending spools recover in bounded
Git batches; Ctrl-C during recovery does not start this stage. Transport failure
retains exact local receipt bytes and data, without advancing the code branch.
Household schema readiness remains an in-memory check only. Staging-size evidence
is fixed-path metadata, not a scan of original caches or source text.

## Pipeline still pending

The full pipeline remains fetch → parse → ingest → normalize → translate → English
gold. This exact candidate layer is substantive normalization work, but it does
not invent missing authority, reconcile all terminology globally, or replace
mandatory per-occurrence recipe/menu AI review. Actual native-AI review awaits an
approved executable route; no AI request or packet export occurs here. English
translation with preserved originals, rights/citation qualification, gold acceptance
and application binding have not run. Profiles/inventory are app-managed and are
never external-data blockers or opened by this stage.
