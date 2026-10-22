# OffMenu — one-command database-only normalization

The current reviewed operation is **normalization of retained database records**,
not further fetching, extraction or the ingestion backlog. In the existing normal
user checkout on `integration/manual-actions-20261022`, after the previous run
has exited and the reviewed source has been published:

```sh
git pull --ff-only && ./run
```

The launcher also performs its own fast-forward-only refresh under the existing
exclusive lock. It preserves `.git/offmenu-runner`, source databases, original
assets, source-version history and exact pending receipts. Do not reset, force,
stash, delete state, switch a running checkout or start a second concurrent run.

See **[DB-NORMALIZATION-RUN.md](DB-NORMALIZATION-RUN.md)** for the current plan,
source-only installation boundary, counters, limits and recovery semantics.

- Six public staging DBs are read-only inputs. No raw-source existence/read gate,
  catalog discovery, fetch, extraction or ingest adapter runs.
- Cached rules use bounded CPU worker processes with one coordinated DB writer;
  compact normalized projections and queue references avoid full raw copies.
- Missing stored fields/provenance remain per-record unresolved. Existing
  versions are distinct occurrences, not automatically deduplicated entities.
- Actual recipe/menu AI review remains mandatory and pending an approved route;
  no credentials, external calls, packet export or invented review is enabled.
  Rules completion is not gold or application acceptance.
- Profiles/inventory remain app-managed. The in-memory household-schema check
  prepares and validates empty schemas only; it does not deploy or open private DBs.
- Version3 sanitized progress/final receipts share the isolated receipt branch
  with unchanged historical ingestion receipts. Both old/new spools recover in
  bounded batches. Source/control/results branches remain separate.
- Disk/time/cancel limits preserve committed cache/cursors. Git delivery failure
  leaves exact sanitized local retry evidence and does not discard data.

The lower-level retained-ingestion APIs remain available for a future reviewed
phase; they are **not** automatically dispatched now. Historical ingestion and
source-access details are retained in [FINAL-INGEST-RUN.md](FINAL-INGEST-RUN.md).
Raw data, source paths, full errors, review packets, credentials and private state
must never be uploaded through the sanitized receipt protocol.

## Historical reference — legacy explicit diagnostics / source handoff

> **Everything below is scoped to the older `foo_manual.py` diagnostic commands only.** Statements that no import occurs or an operation remains STOP do not describe the current root `./run` database-normalization plan above. These historical commands are optional and are not prerequisites for ingestion.


**Runnable diagnostics and supplier source-review preparation, not a data importer.** Python 3.10+ on Linux/POSIX, standard library only. No Codex worker, package installation, Actions rehearsal or per-run CI gate. The current Foo data/capsule have not been inspected by this cloud publication.

## 1. New isolated checkout (once) [legacy diagnostic only]

Use an unused directory; never switch/reset/clean a live checkout:

```sh
git clone --single-branch --branch integration/manual-actions-20261022 \
  git@github.com:maldous/offmenu.git offmenu-manual-actions
cd offmenu-manual-actions
```

The publisher bases this action branch on the current accepted develop, preserving existing source. The CLI does not import application modules or represent all recipe/supplier callers as accepted. Use your existing private GitHub access; no credentials in commands/results.

## 2. Run — usually seconds [legacy diagnostic only]

From the checkout root:

```sh
mkdir -p manual-action/.local-results manual-action/returns
RUN_ID=$(date -u +%Y%m%dT%H%M%SZ)-$$
printf 'Run ID: %s\n' "$RUN_ID"
sh manual-action/run.sh collect \
  --output "manual-action/.local-results/$RUN_ID.private.json" \
  --return-output "manual-action/returns/$RUN_ID.json"
```

Exit **0**: selected checks completed (supplier still requires human source review). Exit **2**: a check was blocked or an output could not be created. Read the private JSON after either outcome. Missing files/wrong capsule identity are recorded, never repaired by deleting, downloading or restarting. Outputs are exclusive/new, mode 0600; repeat with a new run ID. These lower-level commands do not retry/resume existing jobs; root `./run` provides the idempotent pending-job rhythm described above.

`collect` performs:

- **Preflight:** metadata of the fixed archive/known roots, available disk space, bounded Linux PID/short process-name/state snapshot. No process arguments, environment, signals, locks, job control or database connection.
- **Metadata discovery:** default roots `/home/user/src/offmenu-data` and the exact supplier archive parent. Names matching OSM/planet/recipe/inventory/receipt/manifest/custody/acquisition/progress/cache are returned with type/size/mtime only. No receipt/dataset bodies or dataset hashes. At most 1,000 entries, three descendant levels, 200 matches and ten seconds; incomplete scans say `truncated`. Exact current OSM file/receipt path is **unknown**: discovery does not establish global absence, transfer completion or checksum acceptance.
- **Supplier source inspection:** only `/home/user/Documents/Codex/2026-10-22/worker19-supplier11529-resolution/portable-supplier-review.tar.gz`; required SHA-256 prefix **`e2508555`**, full archive digest and member digests recorded. Caps: compressed 16 MiB, expanded 32 MiB, member 2 MiB, 256 members. Every regular member's bytes are inspected as UTF-8 source/metadata with common secret-pattern checks. Refuses traversal, symlinks/hardlinks/special files, duplicate paths, raw-dataset-looking names, non-source extensions, binary content and ambiguous JSON row arrays. Nothing extracted, executed, copied or uploaded. Prefix agreement is historical identity evidence, **not full-digest authentication**. Heuristics cannot prove every embedded secret/disguised dataset absent: human review remains required.

Only the observed `supplier-review/source/schema.sql` member may additionally pass a conservative schema-DDL text check; other SQL members and active row/dump statements are refused. SQL is never executed. Blocked low-level CLI private reports retain the computed archive digest and safe failed-member metadata; sanitized returns omit member names/paths. The one-command runner keeps its sanitized-only receipt policy. Fixture success does not certify the unseen actual schema/source capsule.

Observation phase: 30-second alarm; exclusive final JSON writes/fsync occur afterward and are not timer-bounded. A stalled kernel/mount may delay signal handling; the tool does not kill jobs or repair mounts. Directory traversal uses pinned directory FDs and refuses symlink components. Metadata may change during observation; this is not an atomic snapshot.

### Select one operation or known narrow roots

Replace `collect` with `preflight`, `inventory` or `supplier`. For a known current recipe inventory/receipt directory, supply its exact narrow path explicitly, e.g.:

```sh
sh manual-action/run.sh inventory \
  --inventory-root /home/user/src/offmenu-data \
  --output "manual-action/.local-results/$RUN_ID.inventory.private.json" \
  --return-output "manual-action/returns/$RUN_ID.inventory.json"
```

Up to eight explicit roots replace defaults. Broad/sensitive roots are rejected; no symlinks followed. Do not guess an OSM path or widen to a full filesystem crawl. Return candidate path information privately if a bounded scan is incomplete.

## 3. Return the small sanitized result [legacy diagnostic only]

`*.private.json` contains local paths/PIDs/process names/member manifest: **keep local; never commit it.** Separate `returns/$RUN_ID.json` has fixed status/count fields and archive checksum/size only: no paths, PIDs/names, source bodies, command lines or dataset records.

Fastest: paste/attach the sanitized summary here. Alternatively, inspect it and commit **only that exact file** to the private action branch:

```sh
cat "manual-action/returns/$RUN_ID.json"
git add -f -- "manual-action/returns/$RUN_ID.json"
git diff --cached --name-only
# Continue only if the staged list contains exactly your one sanitized result.
git diff --cached -- "manual-action/returns/$RUN_ID.json"
git commit -m "Return manual Foo diagnostic summary $RUN_ID [skip ci]"
git push origin HEAD:integration/manual-actions-20261022
```

Never `git add -A`, stage `.local-results`, add raw receipts/datasets, paste credentials or force-push. If the branch advanced and push is rejected, preserve the commit and attach the sanitized JSON instead; no reset/rebase/merge needed. No per-result Actions test is required.

## 4. Return the actual supplier review source (not just metadata) [legacy diagnostic only]

**The cloud still needs the archive's source bytes to review the missing caller.** The manifest alone does not supply them.

Proceed only when `supplier.status` is `inspection_pass_manual_review_required` **and** you have reviewed the archive's listed source locally and confirmed it contains only review source/tests/docs/generated fixtures, no credentials/private controls/raw datasets/retained payloads. Do not run archived code. Prefer manually attaching the existing archive plus full digest/member manifest in this private conversation. Do not upload a rejected/unreviewed capsule.

An alternative under the approved private source-only handoff is to copy and commit the one unchanged reviewed source archive. After human review, these are explicit user-run steps (not automated by the tool):

```sh
cp -n -- \
  /home/user/Documents/Codex/2026-10-22/worker19-supplier11529-resolution/portable-supplier-review.tar.gz \
  "manual-action/returns/$RUN_ID.supplier-source.tar.gz"
sha256sum -- "manual-action/returns/$RUN_ID.supplier-source.tar.gz"
# STOP unless the full 64-character digest equals observed_sha256 in the private result.
# STOP unless all members were manually reviewed as source-only, without secrets/raw data.
git add -f -- "manual-action/returns/$RUN_ID.supplier-source.tar.gz"
git diff --cached --name-only
# Continue only if exactly this reviewed source archive is staged.
git commit -m "Return reviewed supplier source capsule $RUN_ID [skip ci]"
git push origin HEAD:integration/manual-actions-20261022
```

No bulk extraction/staging. If anything is ambiguous, return the sanitized blocked reason/checksum and do not upload source. Do not waive a rejection/change the expected prefix/substitute another archive. Source transfer unblocks cloud caller review; it does **not** authorize execution or establish import readiness.

## What remains STOP [legacy diagnostic only]

No HTML, PDF/cache, UniTools or supplier load subcommands exist. Exact accepted caller/source pins, current input/custody/rights, resource limits, exclusive output and terminal load receipt have not been supplied together. Success here means no retained import occurred. Datasets, working scanner, healthy jobs, main and production stay unchanged. The observation CLI has no network, download, external AI, arbitrary shell execution or database writes. The root `./run` orchestrator uses Git network access only to pull reviewed code and push sanitized receipts.

## Developer verification (not required on each user run) [legacy diagnostic only]

```sh
python3 -B -m unittest discover -s manual-action/tests -v
```

Generated temporary fixtures only: bounds, traversal/links/secrets/data rejection, checksum/manifest, malformed gzip, timeout propagation, missing files, sanitized return and exclusive writes; plus local bare-Git pull/self-update/commit/push, repeat idempotency, staged/dirty preservation, locks, blocked results and remote conflict recovery. No real Foo paths or GitHub writes are used by the fixtures. Optional hosted workflow runs only those tests, never Foo paths. See `PROVENANCE.md`.
