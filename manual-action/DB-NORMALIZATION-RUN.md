# Database-only rules normalization — retained preceding phase

**Historical phase contract, not the selected default plan.** The next selected
phase is [bounded cache reconciliation](DB-RECONCILIATION-RUN.md). This rules stage
remains available for a future reviewed plan selection; the reconciliation stage
does not automatically invoke it or create new normalization cache rows.

The reviewed rules plan is `offmenu-run-plan/3`, job
`retained-six-domain-normalization`, operation `normalize_staged_databases`.
Only when that rules plan is explicitly selected, after publication and after any
old run has exited, use the existing normal-user checkout and usual command:

```sh
git pull --ff-only && ./run
```

Source publication does not itself start Foo. The launcher retains the same
exclusive lock, fast-forward-only refresh, private state and isolated sanitized
receipt branch. Never reset, force, delete state, or start a second concurrent run.

## What runs, and what does not

The only data inputs are the six existing owned SQLite databases under
`.git/offmenu-runner/ingest/staging/`: barcodes, ingredients, recipes, dietary,
suppliers and citations. Records and DB-held source provenance are read-only.
All retained source versions remain distinct; these are source occurrences, not
unique final entities. Missing source provenance or fields remain unresolved per
record. Missing original files are **not** checked and are not a prerequisite.

There is no source discovery, download, extraction, ingest-adapter invocation,
original-file read, automatic relational snapshot, AI-provider call or raw-data
export in this plan. Originals are preserved so separately authorized acquisition
and extraction can resume later as capacity permits. Profiles and inventory are
app-managed and excluded from external corpus work; their schemas/data remain.
The bounded in-memory household-schema preparation and fixed-file staging-size
observations remain included, without copying databases or scanning raw caches.

## Pass 1: cached rules, not inferred truth

Existing conservative `normalization_core.run_rules` and the domain/recipe
validators supply the transformation. Ordered recipe/menu source content,
quantities, units, language uncertainty, lineage and missing evidence are
preserved. They do not guess missing ingredients, equipment, amounts, temperatures,
relationships, rights clearance or canonical entity identity.

Private compact caches under `ingest/normalization-private/` (one
`compact-<domain>.sqlite3` per public domain) store actual normalized projections
and source/content/version bindings. It does not store another complete
`source_original` JSON copy or a full review-packet copy per queue entry. The
unchanged source JSON remains in its existing staging database. Compact review
entries point to their immutable projection and exact DB source reference.
These are new normalized outputs, so they still require real disk space; this is
not a zero-storage promise or a claim that every output value is physically unique.

The coordinator owns database reads, transactional output batches and cursor
advancement. Pure rule projection uses a bounded spawn-process pool: default 16
workers on the owner's 24-CPU host, configurable through a reviewed plan up to 22.
It does not create competing SQLite writers or eagerly queue 16 million records.
Default batches are at most 128 rows and 4 MiB; large/invalid records stay isolated.
Runtime worker counts report actual pool use, not a speedup claim.

The indexed `(source_key, source_version, record_id)` cursor avoids an unindexed
row-number sort. Output/cache insertion and checkpoint advancement are committed
together. An unchanged snapshot resumes without replaying its completed prefix.
Changed DB/content/version identity creates a new bounded scan, reusing immutable
matching rule results and retaining history; it does not silently miss records
inserted below the old cursor. Changes in one domain do not reset other domains.
No source database is writable through this stage.

The normal plan has a six-hour wall bound and retains the existing 2 GiB free-space
reserve. Global time/disk/cancellation stops are resumable, not millions of new
source failures. Source-specific malformed/unsupported records do not stop
unrelated records. Ctrl-C propagates as cancellation; no interrupted startup
transport failure is treated as permission to begin normalization.

## Pass 2: mandatory actual interpretation, honestly pending

Every recipe/menu occurrence still requires actual evidence-bound AI review of
all required item/section coverage. Cached templates or a batch success cannot
waive that review. See [RECIPE-SEMANTIC-REVIEW.md](RECIPE-SEMANTIC-REVIEW.md).
The current runtime prepares private queue references only: no approved route
for sending Foo records to an actual reviewer is activated, and model/prompt pins
remain `unconfigured`. Accepted/rejected/needs-changes counts remain zero rather
than fabricating a review. Source text is data, never instructions to the reviewer.

A later authorized review workflow can hydrate bounded local packets from exact
DB-bound source references, validate genuine receipts and reuse exact-equivalent
interpretations with explicit per-occurrence evidence. Missing originals are not
a dependency. Translation follows accepted review and reuses contextual grammar
and lexical units; it is not silently run over every raw string here. Neither
rules nor review alone imply gold, application binding, rights or final entities.

## Progress and recovery

Version3 receipts report each public domain's selected metadata total (null when
unavailable), scanned rows, new/reused rules, pending review, unresolved and failed
counts, bounded disk/time/worker observations and checkpoint digests. Counters are
cumulative for the current domain snapshot, not database-unique entities or
current-invocation writes. `unresolved` counts structural rule issues or missing
bounded provider/license/custody metadata; it is not an exhaustive gold-blocker
count. Rights remain unverified and absent citation evidence is not invented.
No COUNT scan is introduced merely for progress.

`rules_complete` means the selected DB rules pass finished without failed rows;
review remains pending and gold/app binding blocked. Exit 0 additionally means
receipt synchronization succeeded; it does not mean the full two-pass process,
translation or application acceptance is complete. Exit 2 preserves partial work
or pending sync; exit 130 preserves work on interruption.

The runner batches any old ingestion and new normalization receipt spool before
new work, without restarting ingestion. New immutable v3 filenames include a
progress digest even for completed rules, so repeat resource observations cannot
collide with an older completion. Existing v1/v2 canonical bytes and histories
are retained unchanged. Only independently validated summaries and bound schema/
storage supplements go to `integration/ingest-receipts-20261022`; source, control
and result branches are not modified by receipt delivery. Exact local spools
remain after a failed push and are removed only after confirmed delivery.
