# Historical retained + acquired ingest pass (2026-10-22)

**Not the current `./run` operation.** The owner switched the next phase to
database-only normalization of already retained records. See
[DB-NORMALIZATION-RUN.md](DB-NORMALIZATION-RUN.md). The implementation and source
custody below are preserved for a future explicit reviewed ingest phase; no
backlog, original-file access or acquired-cache completion gates normalization.

## Installation boundary

This reviewed source is prepared on `integration/final-ingest-20261022`; its
installation target remains `integration/manual-actions-20261022`. It is **not**
an instruction to change a running checkout, start another concurrent run, or
execute the preparation branch against production state.

1. Let the current `./run` exit. Preserve all local receipt commits and the entire
   `.git/offmenu-runner` directory, including its pending receipt spool.
2. Reconcile the existing same-branch receipt history using the separately
   reviewed **after-exit** recovery procedure. A non-fast-forward pull is a stop,
   not permission to reset, force-push, stash, drop commits, or delete state.
3. After reviewed code is promoted to the normal manual-action branch and the
   existing receipts are preserved, the ordinary workflow remains `git pull
   --ff-only` followed by `./run` (or the existing command that invokes it).

The integration changes do not themselves perform a host fetch, modify file
permissions, switch a live branch, or copy source datasets into Git.

## What one run does

* Discovers retained sources and bridges the exact reviewed 50-file, six-family
  acquired manifest at
  `/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache`.
* Attempts the bounded acquired menu and recipe groups before the retained tail
  within each domain, so 50 new artifacts are not starved behind a large retained
  backlog. This is priority, not a promise the whole backlog fits one invocation.
* Ingests eight independent domains concurrently. A malformed/unreadable source
  does not cancel unrelated sources or domains. Acquired bindings never silently
  fall back to the generic retained parser.
* Retains `.git/offmenu-runner/ingest` and existing retained adapter/source
  fingerprints. Completed sources skip their readers; partial sources resume
  committed cursors. Specialized acquired adapter versions affect acquired
  bindings only. Unchanged, previously verified acquired files use exact
  stat/receipt/manifest identity rather than gratuitous full-file rehashing.
* Uses the existing staging databases and cached source assets. The standard
  `./run` does **not** automatically materialize another derived SQLite snapshot
  or copy stored payloads into that extra target. Receipt-branch selection does
  not enable derived writes. Existing snapshots, if any, are left untouched.
* Honors supplier catalog entries already marked `duplicate` from known inode
  identity or bounded small-file byte equality. It does not ingest those aliases
  again, purge historical rows, hash large files, or claim universal deduplication.
* Returns sanitized pre/checkpoint/post evidence, domain totals, bounded scoped
  error reasons, pending counts, schema availability, access blockers, and
  current-run resource-stop evidence automatically with the normal receipts.
  It does not report an optional derived phase as having run.

No new downloading or endless fetching is enabled. A reported resource limit or
source failure is not completion; the next ordinary run resumes owned work.

## Output and readiness are deliberately distinct

The eight source-faithful staging databases remain under the existing private
runner state, with binding `additive_staging_not_app_bound`. One retained cached
source asset plus its database representation is expected; this correction does
not merge domains, move databases, or remove existing assets or versions.

The explicit optional materializer remains available separately; if deliberately
invoked, it writes versioned targets under
`ingest/private-household/relational-targets/v1`, with binding
`versioned_derived_not_app_bound`. Neither staging nor optional derived targets
are bound application databases. They do not claim universal ingredient canonicalization, verified dietary
claims, populated household profiles/inventory, or an application-ready gold
schema. `app_binding: deferred`, exact blocker enums, and schema-only private
household domains remain visible. See `RELATIONAL-TARGETS.md` and
`RELATIONAL-READINESS.md` for the scope and exact target mappings.

## Permission boundary

The acquired cache was created for a separate runner identity. The invoking CLI
identity must actually be able to traverse the reviewed parent directories and
read the exact allowlisted files and custody receipts. If not, each affected
source reports `read_permission_denied` and unrelated retained ingestion still
proceeds. This code neither requests nor silently applies `sudo`, broad chmod,
recursive ownership changes, or wider cache access. A separately reviewed narrow
read-access handoff is required where those access rights are absent.

## Receipt transport and preservation

Plan version 2 opts into `isolated-branch-v1`. New sanitized receipts go to the
fixed `integration/ingest-receipts-20261022` branch using a private Git index and
Git object plumbing; source HEAD, its index, working files, and legacy control /
results branches are not changed by receipt publication. A concurrent source
branch advance therefore cannot strand receipts on an unrelated source tip.

Existing v1/v2 canonical receipt validation and recovery are preserved. Legacy
plans retain their original same-branch transport; existing pending v2 receipts
can migrate without rewriting their content. Push rejection retains local
receipt commits **and** the durable spool, and does not interrupt ingestion.
Divergent or unreviewed receipt histories stop publication rather than force a
merge or rewrite.

Detailed new evidence travels as one readable, sanitized JSON supplement (at
most 64 KiB), content-addressed beneath `manual-action/returns/run/evidence/`.
The main v2 receipt retains the existing 64 KiB bound and binds the supplement
schema, SHA-256, and exact canonical byte count. Receipt and supplement enter the
receipt branch in one atomic commit. A missing private supplement can be
recovered from an already validated local receipt commit; tampered bytes are
preserved and rejected, never silently regenerated or uploaded. There is no
base64/chunk protocol and no public raw-source upload.

Private spool/state must not be removed just because a push is temporarily
unavailable. A later ordinary run retries delivery before deciding whether
unchanged completed ingestion can be skipped.

## Verification

Synthetic tests use generated source-shaped records and temporary local bare
Git remotes only. They cover the full executable `./run`, all six acquired
families, a completed and partial retained-v1 upgrade in the same state directory,
source-error isolation, exact no-replay guards, atomic two-artifact receipts,
missing/tampered supplement recovery, push failure, legacy spool migration, and
concurrent code-branch advancement. They are not evidence that the real CLI can
currently read the cache or that real application binding is complete.
The standard-run regression also verifies no new derived target is created,
existing historical target files remain byte-identical, and normal ingestion,
resume and sanitized receipt/evidence delivery continue without the extra copy.

## Startup receipt batching and cancellation

Preserved startup checkpoints are returned in bounded batches (up to 512
receipts or 8 MiB of canonical receipt/evidence bytes), using one commit and
non-force push per batch instead of a push per checkpoint. Startup prints each
batch count before delivery and confirms it afterward. Canonical receipt and
supplement bytes are retained; spool entries are removed only after a successful
push. A transport failure retains local commits and the pending spool for retry.
Missing Git identity fields use one announced, per-invocation cached fallback;
configured identity is not replaced and no Git configuration is changed.

Ctrl-C during Git is cancellation, not a timeout or permission to continue into
ingestion. Startup cancellation exits without starting source ingestion. During
an active ingest, cancellation remains cooperative at durable batch boundaries.
Wait for the original process to exit before another pull/run; never delete the
lock, pending spool, caches, or database files to resolve a sync delay.
