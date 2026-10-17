# OffMenu lossless repository handover — 2026-10-17

Sanitized operational handover for Morgan's cloud agents. Prepared by the Freebuff worker
(Worker 05 identity, worktree slot 62, task `MORGAN-OFFMENU-20261015-0255-W02`) when
implementation work was stopped and this preservation handover was ordered.

Every statement below is labelled **[verified]** (rerun/inspected during this handover) or
**[historical]** (preserved claim from existing artifacts, requiring reconciliation).
No raw private conversations are reproduced; task decisions and technical evidence are
summarized only.

## 1. Preservation manifest and remote verification

Full machine-readable manifest: `manifest.json` in this directory (101 checkouts, 17
preservation commits, 3 detached-HEAD branches, 4 orphan branches, 201 republished local
branches, 78 prior-namespace refs, 69 Codex snapshot refs, 10 exception classes).
Raw tables: `manifest-refs.tsv`, `manifest-preservation-commits.tsv`.

- **[verified]** Destination: `https://github.com/maldous/offmenu` (`git@github.com:maldous/offmenu.git`),
  verified as the actual `origin` of the shared repository (101 worktrees, one object store).
- **[verified]** 348 explicit refs pushed under `refs/heads/handover/2026-10-17/**` in 5
  batches, no force, nothing merged to `main`, no existing ref overwritten, no deletions.
- **[verified]** Remote custody: `git ls-remote` shows 348/348 exact SHA matches; an
  independent fresh bare clone fetched all 348 refs; 8/8 representative file SHA-256
  comparisons equal the source worktree files; orphan and Codex-wrapper commits retrievable.
- **[verified]** Method: isolated-index Git plumbing (`GIT_INDEX_FILE` temp index +
  `read-tree`/`add`/`write-tree`/`commit-tree`/`update-ref`). No working tree, real index,
  HEAD, branch, reflog or stash was modified; no `gc`/`prune`/`reset`/`clean` ran.
- **[verified]** Secret review before push: 299 unique commits' diffs scanned (0 forbidden
  filenames; only synthetic test fixtures such as `fixture-password` matched); the 1,504
  newly-reachable Codex snapshot blobs scanned (10 pattern hits, all synthetic test
  bindings like `'a'.repeat(64)` vault keys); the 4 recovered orphan commits scanned clean.

## 2. Branch inventory: unique work, overlap, suggested review order

**[verified]** 404 local branches across 101 worktrees; 201 carry commits not on the remote
and are republished at their original SHAs as `handover/2026-10-17/branch/<original-name>`.
78 earlier-preservation refs (`refs/preservation/offmenu-sync-20261015/*` (62),
`refs/offmenu-private/*` (12), `refs/checkpoints/*` (2), `refs/worker05/*` (2)) are
republished under `handover/2026-10-17/prior/**` at unchanged SHAs.

Substantive unique work (review first):

1. `handover/2026-10-17/worktree-wip/worker62-relay-gateway-poller` — Freebuff transport
   bridge: gateway (queue, receipts, OAuth/Access auth, allowlist) + verified poller and
   adapter with native-`seq` paging. This session's own work. See section 4.
2. `…/offmenu-main-aldi-delivery-corpus` — ALDI local datasource + DoorDash delivery
   pricing modules/tests + corpus mission docs + `knowledge.md` on `main` @ 8652b312.
3. `…/offmenu-google-idp-identity` — Google identity integration (docs, callback policy,
   identity flow UI, edge/web tests).
4. `…/devpreview-worker05-production-app` (112 files) and `…/devpreview-worker05-live-dev-popup`
   — country progress/data-browser/perf harness and retailer-extension popup. **Active-writer
   checkpoints, not final snapshots** (section 10).
5. `…/worker48-afcd-normalization` — AFCD normalization/conflicts/verify-packets + fixtures.
6. Review evidence packages `worker10/12/20/21/25-review-evidence`, `worker63-review-evidence`,
   `worker58-authed-browser-qa`, `worker01-source-reconciliation`, `worker17-origin-gitflow-report`,
   `worker06-demo-recipe-catalogue-deploy-evidence`, `worker64-ci-portability-patch`.
7. `handover/2026-10-17/orphan/ui-stock-quantity-fix-{a,b}-20261017` — **[verified]** two
   divergent lost fix sets for stock quantity / review readiness / expired duration stock
   (2026-10-17 02:02 and 02:04, both children of `ac2df940`); preserved separately, never merged.

Overlap: most integration worktrees share base `f6cb92aef52a…` (43 refs) and `/tmp`
integration worktrees are disposable previews of the same feature branches — treat as
duplicates of the named feature branches. Suggested merge order for review:
worker-62 relay → main ALDI/corpus → google-idp identity → worker-48 AFCD → dev-preview
apps (after runner custody is settled) → orphan UI fixes A/B (reconcile against each
other first) → documentation/review evidence last.

## 3. Tests and recorded results

**[verified — rerun during this handover]** (2026-10-17, Node on this host):
- gateway unit (`npm run test:unit`): 17/17 pass, exit 0.
- poller (`npm test`): 44/44 pass, exit 0.
- Earlier in the session: `npm ci` exit 0; local API probes and adapter contract checks
  (read-only) completed.

**[historical]** Worker review packages (e.g. `worker-10-review/**`) contain author test
logs, independent-review JSON and correction snapshots; worker-58 QA scripts and
worker-64 CI-portability patch results. Claims inside those files were not rerun here and
must be re-verified before acceptance.

## 4. Gateway source, adapter, pagination repair, config, startup

**[verified]** Latest source is in `handover/2026-10-17/worktree-wip/worker62-relay-gateway-poller`
(`gateway/` + `poller/`), from worktree `offmenu-workers/worker-62` on
`bugfix/62/freebuff-repair-diagnosis-20261015` @ 894313bc.

- Gateway: Cloudflare Worker + SQLite Durable Object queue; exactly five MCP tools
  (`bridge_status`, `list_sessions`, `read_messages`, `enqueue_message`, `get_receipt`);
  fail-closed pause/unknown/stale handling; ≤3 allowlisted existing sessions; 32
  accepted/uncertain + 10,000 receipts; single non-reissued leases; `uncertain` only
  reconciled by exact readback; 7-day expiry. Architecture/limits: `gateway/README.artifact.md`.
- Poller: outbound-only Node 24 CLI; state dir 0700 with single-instance lock; durable
  send-intent journal; always `now:false`. Provenance and the two deliberate reviewed
  changes (`x-freebuff-launch-id` credential allowlist; `PROJECT_PATH` target binding):
  `poller/VENDORING.md`.
- Pagination repair **[verified in source]**: the loopback API's unpaged thread reads now
  exceed the 1 MiB transport bound on live sessions; verified paged reads
  (`page=true&before=…`) expose native stable `seq` message IDs and bounded bodies; the
  verified adapter uses native `seq` IDs with temp-id fallback (`msg-<ts>-<role>`;
  cross-role same-ms pairs kept, only true collisions reject). Incremental `after=`
  reads are small and bounded.
- Config/startup: `poller/config.example.json` documents the private config shape (real
  config lives only at `/home/user/.local/state/freebuff-relay/poller-config.json`, 0600).
  Gateway deploy metadata `dist/bootstrap-metadata.json` ships `ENABLED=false`, empty
  allowlists. Reproduce: `npm ci --ignore-scripts && npm run typecheck && npm test &&
  npm run build && npm run test:runtime` in `gateway/` (Node 24).

## 5. Cloudflare deployed revision vs local; settings completed vs pending

**[historical]** Account `7edd51038e07b5b84a635b3ff7e11144`; gateway origin
`https://freebuff-gateway.aldous.info`; Access app `a4d06e5c-…`; KV `OAUTH_KV`;
DO `BRIDGE`/`BridgeQueue` (migration `v1`) provisioned by the parent session.

**[verified]** The reviewed bundle was **not deployed** by this worker; bootstrap metadata
keeps the bridge disabled. Completed: source, tests, verified adapter, deploy metadata,
Access/AUD facts. Pending (blocked): `OWNER_SUB` setup via `/authorize?setup=1`; OAuth
redirect URI(s) — **awaiting Morgan's approval of the plugin OAuth redirect**; 1–3
approved session IDs in both allowlists; poller token provisioning (hash-only in Worker);
`ENABLED=true`; one live enqueue round-trip; user-service installation.
**[historical]** worker-64 report records a separate Cloudflare redeploy blocked pending
final source-polling configuration.

## 6. Session control, mode fencing, three-slot capacity, model/quota, work queue

**[verified in source]** three-slot session capacity (allowlist schema rejects >3 distinct
sessions), durable queue lifecycle (accepted/delivered/started/completed/failed/uncertain),
delivered receipts free pending capacity, retention/purge, idempotent retries. Unit-tested
(gateway 17/17).
**[partial]** mode fencing (DIRECT_CODEX/FREEBUFF lease with transitional/blocked states):
drafted this session (`gateway/src/control.ts`), not covered by the deployed bundle.
**[not implemented]** session-control tools (pause≠stop semantics), model/quota accounting,
budget refusal, two-route Codex fallback gate, 64-session durable work-queue mapping.
These were planned implementation work stopped by this handover.

## 7. 64-session OffMenu reconciliation

**[historical]** Retained in `/home/user/Documents/Codex/2026-10-15/task/freebuff-runtime-migration-20261015/worker-02-handover.json`
and the receipts lane: pickup `MORGAN-OFFMENU-20261015-0255-W02`; Morgan-scoped correction
acceptance with `notFullCorpusAcceptance=true` (full corpus acceptance NOT granted);
accepted RS-P2 items carry explicit limits (intermediate checkpoint states not retained;
no invented historical bytes). Uncertain sends: none — no live enqueue was ever performed.
Unresolved: the 64-session legacy mapping/queue work (section 6) and the full corpus
acceptance. Source/artifact references: `docs/FREEBUFF_HANDOVER.txt`, `docs/FREEBUFF_CORPUS_MISSION.txt`,
`.morgan-status/*` (preserved in `offmenu-main-aldi-delivery-corpus`).

## 8. "Design independent corpus refresh" and continuation material

**[historical, preserved]** Mandate: `docs/FREEBUFF_CORPUS_MISSION.txt` (15 Oct 2026 —
staged delivery A collection (249 ISO country ledger) → B per-dataset baseline → semantic
validation → multilingual alignment → golden English journal → translation to all supported
languages; zero-cost-model-only constraint; per-source rights/archives). Custody/restart
constraints: `docs/FREEBUFF_HANDOVER.txt`. Related code preserved here:
`offmenu-main-aldi-delivery-corpus` (delivery partners, ALDI/DoorDash pricing),
`worker48-afcd-normalization` (AFCD pipeline), `devpreview-worker05-production-app`
(country progress + data browser), corpus-manager branch
`handover/2026-10-17/branch/ben-v6-corpus-manager-draft-20261015`, source registers under
`research/` **[historical]**. Dataset originals remain in `offmenu-data` (section 9).

## 9. Outstanding approvals, blockers, locally retained artifacts

Approvals needed from Morgan: plugin OAuth redirect URI(s); gateway enablement +
session allowlist; poller token provisioning route; destination for the nested
`offmenu-data/dev-preview-20261014/source` repository; separate transfer route for
`offmenu-data` datasets (171 GB); disposition of the six worker-06 deploy readbacks
containing a live Cloudflare skew-protection token (rotate before any transfer).

Locally retained exceptions (never published; details + retrieval steps in `manifest.json`):
worker-06 `.local` readbacks (token), `index.sqlite` (runtime DB), `proposed-preview/`
(bulk dataset build output), dependency caches (`node_modules`/`.venv`/`.wrangler`),
`offmenu-data` datasets, private host state (`poller-config.json`, `api-session.json`,
raw poller token). Two broken Codex turn-diff refs (missing tip objects) are recorded and
left in place; content unrecoverable.

## 10. Active processes and writer status

**[verified at capture]** No relay poller installed or running (service file inert).
**[verified]** Freebuff Worker 05 implementation work: **stopped** — no new implementation
started after the handover order; this document closes the session's work.
**[unverified-paused]** Codex desktop app-server daemons were running but produced no file
changes in any dirty tree within 60 minutes before capture; they cannot be controlled from
this session and are recorded as writers whose pause state is unverified.
**[running, not stopped]** dev-preview runner/wiremock/workerd processes under
`offmenu-data/dev-preview-20261014/` may still write the two worker-05 trees; those
preservation commits are labelled checkpoints, not final snapshots.

Morgan's cloud agents can take sole implementation ownership once this checkpoint is
verified. All local checkouts and backups remain in place until Morgan verifies the remote
handover.

## 11. Non-worktree related locations (rev 2 addition)

- `/home/user/src/offmenu_worker_instructions` — **[verified]** 64-worker instruction corpus
  (372 KB, not a Git repository): `instructions-all64.json`, `MANIFEST.json`/`ALL64-MANIFEST.json`,
  `queue_all64_instructions.py`, `CURRENT-APPROVAL-BLOCKERS.md` (approval-blocker ledger with
  exact bounded authorization wording), `queue-log/` receipts, `TEST-RESULTS.json`.
  Scan-clean; preserved at `docs/handover/2026-10-17/offmenu-worker-instructions/` on this branch.
- `worker-02-handover.json` — the 64-session reconciliation task state, preserved at
  `docs/handover/2026-10-17/worker-02-handover.json` on this branch.
- `/home/user/src/offmenu-data` (171 GB) and nested `dev-preview/source` repo: unchanged
  local exceptions per section 9.

## 12. Operational ledger and latest backlog state (rev 3)

**[verified]** The latest operational ledger was located and preserved (scan-clean):
`docs/handover/2026-10-17/operational-ledger/` holds the append-only `events.jsonl`
(5,271 events), `management-summary.json`, `base-initial-copy.json`, `authority.json`,
`handover.json` and the ledger's `baseRevision` target `interim-obligation-index.json`;
`docs/handover/2026-10-17/morgan-batches-20261017/` holds B01–B03 preflight/admissions,
custodian R1–R3 admissions, recipient packets v1/v2, routing plan, ledger-evidence and
current checkpoints, `transport-checkpoint-current.json` (64 admissions/64 starts,
28 response transfers at cut, 6 blocked identity/actor cases, M005 only M-series admitted),
M003/M004 dispositions and returned-evidence admissions.
`freebuff-gateway-offmenu-restore-readiness-20261017.json` (same directory) is the
companion routing reconciliation: 58/64 workers returned at the cut; pending sends
enumerated; M-006 NL extraction preserved as a failed-turn record and NOT re-executed.
Source: `/home/user/Documents/Codex/2026-10-13/task-3/…`. The 64-worker instruction corpus
alone did not contain this backlog state.

## 13. Gateway deployed baseline vs newer local changes (rev 3)

**[verified, read-only]** Deployed baseline (Morgan: `morgan-freebuff-gateway` at
freebuff-gateway.aldous.info, dispatch disabled) corresponds to the reviewed artifact
bundle: `dist/index.js` 869,325 bytes, SHA-256 `8e42da8d7c6d31cb37d84fe197349d92e5d367e777a6ea5824cab0ead8094702`,
`bootstrap-metadata.json` with `ENABLED=false` and empty allowlists. Newer local changes
NOT deployed: `gateway/src/control.ts`, `poller/src/contracts.mjs` (two deliberate reviewed
changes), `poller/adapters/freebuff-verified.mjs` + tests, `poller/test` additions. All
other gateway sources/tests are identical to the baseline. No deploy, enablement,
credential change or resource creation was performed. **Limitation:** a live
`wrangler deployments list` requires a Cloudflare API token that does not exist on this
host and was not created; the deployed script name appears in no local file — the
baseline identity rests on the artifact hashes plus Morgan's statement.

## 14. Verification round 2 — nested repo, writers, token evidence (rev 3)

- Nested `dev-preview/source`: HEAD `94cc5c67d451601091760add6d0e9075d3858b5c`
  (`dev/isolated-preview-20261014`), origin = `/home/user/src/offmenu` (local path),
  52 commits with zero shared history with the parent repository, only untracked
  `node_modules` dirty; its content (dev-server/smoke/stop tooling, corpus schema, docs)
  is absent from every preserved parent ref. **Not pushed** — destination and content
  scope unresolved (manifest `nested_repo_analysis`).
- Writer status: the two worker-05 checkpoints are **byte-identical** to their
  preservation commits (0 drift / 797 files); no deltas existed to preserve. No
  source-writing jobs running. Preview processes remain running (delivery runner,
  3 wiremock, 2 workerd) — unchanged policy: not killed, checkpoints stay non-final.
- Skew-protection token: contained in exactly the six excluded worker-06 readback/baseline
  files. Evidence: never in Git (path log empty; `git log -S` over the whole history since
  2026-10-01 finds no commit introducing the string), never in any request payload or
  outbound file; it arrived from Cloudflare inside authenticated deploy readbacks. No
  evidence of onward publication or transmission. No value is printed anywhere and no
  credential was rotated.
