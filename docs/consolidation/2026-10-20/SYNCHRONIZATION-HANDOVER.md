# Foo synchronization checkpoint — 20 October 2026

UTC source checkpoint: 2026-10-20T07:49:05.331348+00:00. Prepared by current consolidation root, native thread `01a15825-0d6e-7c51-a1e8-d1ad155a8b58`. Existing ledger/store and worker ownership remain authoritative; this directory is evidence, not another controller or tracker.

## Delivered source and develop

- Original parser branch: `integration/foo-parse-records-20261020`, `000bef28ba4ba2883971eedd4a224dbfcfd4aea2`.
- Reviewed integration branch: `integration/foo-synchronization-20261020`, final source `70d2426baff500e8b35406a9f52b53a65fb5f81c` (initial composition `530dceb9c666ae14f4b75835b2b3addac6f112f4`).
- Starting develop: `801d05b5aec4a127767c78641d995cbfb74d3198`.
- Delivered source develop: `a0ba9a08cd557e08442deec067c2c1919114b96e`, normal merge [PR55](https://github.com/maldous/offmenu/pull/55). Parents are the starting develop and reviewed source. Tree `67f1c98069b474ddc8a1a2ded755bab85cf21136` exactly equals the reviewed candidate tree.
- The final follow-up documentation branch is `integration/foo-sync-checkpoint-20261020`. The original documentation branch `integration/foo-sync-handover-20261020` at `62bcf3bb33cb57563a731e552c32cde58ab75ab9` remains preserved with PR56. GitGuardian flagged two source checksums keyed by browser-authentication filenames there; exact source-byte verification confirms both are SHA-256 checksums, not credentials. This successor uses explicit path/algorithm/sha256 records and reruns the unchanged scanners. No finding was dismissed or suppressed; see `gitguardian-hash-disposition.json`. Its containing Git commit identifies the handover revision; the later normal merge/readback identifies the final documentation-bearing origin/develop tip. Final merge/readback receipts remain in `/home/user/src/offmenu-preservation-20261020/final-checkpoint-receipt.json` and the PR timeline, avoiding a self-referential commit ID.
- The single checkout to use next is **`/home/user/src/offmenu-dev/develop`**, on `develop` after the documentation PR fast-forward. Main remains `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; no promotion or deployment.

Delivered functionality: reusable source-faithful HTML recipe/menu parsing, source-local ingredient/step/quantity and citation records, guarded assistant extraction cache/replay, processing provenance and source-inventory lineage reconciliation. Installed wheels include the required schema and declared parser dependencies. Source bodies, responses and parsed records remain private. No acquisition, model call, new real-data parsing, normalization, translation or country completion was performed.

Independent review found two P2 issues in the first composition. The final source rejects JSON-LD fields absent from visible source text instead of inventing offset zero, and locates actual whitespace-separated spans across inline HTML. Parser `1.3.1` and transform `1.0.1` distinguish corrected cache interpretation. Regression tests verify actual byte ranges/hashes and full cache/replay. Original and correction reviews are committed alongside this handover. The owner-specific launcher stays on the original parser branch: it hardcodes private receipt paths and needs input/output pin revalidation before checkpoint reuse. Historical local parser results in the source documentation are not fresh acceptance.

## Verification

- Exact source candidate: independent correction PASS; 16 focused parser/provenance/cache tests. Independently built/installed wheel exercised outside checkout, including schema loading, non-ASCII/inline spans, cache hit/lookup/replay, invisible JSON-LD rejection and old-transform rejection.
- Local combined tree: dependency installation succeeds; `npm ci` reports no vulnerabilities; all 677 web tests, build, i18n check and all 11 locale-edge checks pass. Build-generated tracked popup bytes were returned to the pre-build Git version, with no source change hidden.
- Broader local Python run: 1,704 tests, 5 failures, 3 skips before the two correction regressions. The same five owner-projector `reported`/`unverified` assertions reproduce in 51 tests on an untouched archive of starting develop `801d05b5`. These tests consume Foo-specific retained projector state while mocking its process outcome; they remain an environment-dependent baseline limitation, not an introduced parser regression. No check was weakened.
- Hosted push and PR CI passed for exact source `70d2426b`, including full Python, web/build/i18n/locale and portable OCR checks. GitGuardian passed; optional Snyk/Sonar scans skipped under existing conditions.
- Hosted CI also passed on source merge **`a0ba9a08`**, [run39388340041](https://github.com/maldous/offmenu/actions/runs/39388340041). Exact run links/commit pins are in `source-checkpoint-ci.json`. The documentation checkpoint's own final CI is read back separately in the final receipt.
- Git object audit: four unreachable commits recovered, pinned locally and published without changing original IDs. Shared-repo fsck exits2 for three pre-existing null `refs/codex/turn-diffs/captures/.../base` refs; the other ten inspected independent stores pass. A further 288 unique unreachable commits observed across those stores are all recoverable through exact advertised remote descendants, recorded in `all-unreachable-dispositions.json`; their original IDs and local custody refs remain. Raw object diagnostics and other unreferenced blob/tree IDs remain privately retained. No gc, ref repair or deletion was selected.

This is a verified development synchronization checkpoint, not release certification. Foo baseline failures, remaining feature reviews and source/access qualifications remain explicit.

## Every branch/worktree and unique change

`reconciliation.json` records every original inspected checkout and local branch across the eleven independent object stores, plus every advertised origin head, against delivered source develop. Each record gives exact original ref/commit, ancestry, source-relative equal/differing paths, disposition, remote custody and next action. The audit contains 1,489 ref records across 565 unique tips: 226 integrated, 137 equivalent, 1126 preserved-unmerged; the custody snapshot is historically remotely reachable as well as locally backed up. Counts include aliases across repositories and origin; they are not counts of independent features. “Equivalent” means all original changed paths match mode/object content, not just a matching title or patch label. Ancestry and content remain distinct. Differing path lists are not a claim that every preserved feature is complete.

Extended depth4 discovery also found standalone worker37 staging-bind clone `66c366b744995ecfe0b6fce89b9fdf4099233c4c`, clean source with11 hashed bytecode cache files and no additional unreachable commits. Its original four-file source commit is now preserved at `archive/foo-worker37-source-20261020` with exact remote readback; source equality/differences are recorded without automatic integration.

The 92 linked shared-repository worktrees remain the same original census; separate collection/runner checkouts and the discovered standalone worker59 normalizer bring the inspected total to **104**. No checkout was removed in this pass. The previous removal ledger's 53 rows were cumulative: 39 earlier removals plus 14 follow-ups. They were not 53 removals in the follow-up pass.

Key dispositions:

| Original work | Disposition and next action |
| --- | --- |
| Worker57 two JSON-stat source/test files | Already byte-equivalent on develop. Preserve original base and new source snapshot `archive/foo-worker57-source-20261020` (`6d03328073654e0f40a22a93fe6777f2ea8a13ce`); no duplicate merge. |
| Worker62 gateway/poller, 31 source/config/test files | Preserved at `archive/foo-worker62-source-20261020` (`6d36e2fc4e4b8c2547aac994200ec1e05258eb94`). Unactivated artifact; exact review, current supported access and runtime qualification required. Original checkout/private state retained. |
| Parser original | Selected reusable source delivered via PR55 with corrections; original full history retained. Owner launchers, older acquisition composition, snapshots and handover trees are not wholesale application-code merges. |
| Preview extension and 52 preview source changes | Separate preservation branches in `additional-source-preservation.json`. Active runtime remains on original paths. Large generated landing CSS, art masters/media and generated data stay in private archive/original custody; UI remains held. |
| Worker58 browser QA scripts | Source preserved separately; existing browser/access and denied-action holds remain. Review before any execution. |
| Whole-register fetch/coverage scripts/tests | Eight source files preserved at `archive/foo-coverage-tooling-20261020` (`533b559a5289e5ac386d5494363c7b22c8c7d37c`); generated register/corpus outputs excluded. Original branch/pipeline stays separate pending dependency and source-permission qualification. |
| Standalone worker59 retained WFP normalizer | Discovered unique clone `1c4c981e04fd4fe39b79234885f3c6376d5a3cc3`; original four-file commit published as `archive/foo-worker59-normalizer-20261020`. Current-base exact independent review and retained-input/output qualification precede integration. |
| Four unreachable original commits | Original source/review/synthetic fixture IDs published in `recovered-commit-remote-receipts.json`; disconnected synthetic fixture history must not be merged into application history. |
| Google IDP, delivery-price, third-party and remaining owner/staging branches | Original histories remotely recoverable as recorded. WIP or differing source requires current-base composition and latest exact owner/reviewer binding; preservation does not imply acceptance. |
| Open PRs9,11,49,50,54 | Retained unchanged. They have distinct older review/base or draft qualifications; current combined-tree gate reconciliation remains. Do not infer merge approval from preservation. PR54's generated-bundle drift stays explicit; no generated asset rewrite was selected. |
| `integration/foo-owner-custody-snapshot-20261018`, `434c7b3ae76aa4116a2c8b70abd2668e0a748ba5` | Snapshot includes coverage/custody material and is already historically reachable through advertised remote descendant `7522b07c97445f99be08e5900dc1607640af890d` on the same branch; ancestry verified. The complete-history Foo bundle is additional backup, not exclusive local custody. No new wholesale snapshot publication occurred here. Retain existing history; review/redact eligible paths before any new publication. |
| PR31, `offmenu-runner-jobs`, `offmenu-runner-results`, completion publisher and existing automation | Preserved operational infrastructure; no merge, close, branch rotation, dispatch or deletion. Exact observed operational heads retained in local receipt. |

New preservation branches were pushed to the existing private maldous/offmenu origin and exact SHAs read back. `worker-source-preservation.json`, `additional-source-preservation.json` and recovered-commit receipts name source files and hashes. Original commits remain unchanged. No stash was present in the inspected repositories.

## Local custody and coordination

Private custody root: **`/home/user/src/offmenu-preservation-20261020`**. `local-custody-pins.json` binds exact evidence locations and hashes. The private census records every observed changed/ignored file's SHA256 or symlink target, size and owner/mode where available. It covers 118,667 ignored files in the initial census (about9.29GB) plus the standalone worker59 metadata separately; ignored content was inspected and hashed, never treated as disposable.

- `uncommitted-custody-private.tar.gz`: 1,439 original changed/untracked/symlink entries, 56,768,643bytes, SHA256 `20b70954ad211b1baccdc6ca7ae757b83975df299dc9210a4a98744c69319678`; no mismatch against initial pins. Mode0600. Includes local evidence/data and must not be uploaded wholesale.
- `owner-custody-local-only.bundle`: verified complete history for private snapshot434c7b3a. Mode0600; original object store and branch remain too.
- `unreferenced-objects-private.tar.gz`: 3,638 original unreachable Git objects (all types), each rehashed to its original Git ID; private archive SHA256 `06b0661d228a56b81727e1c25da42aac41d705da204f65c55f5eff6c21d35bf1`. This also preserves pathless blob/tree evidence outside the original stores before any future gc. No gc was run.
- Original six earlier private tar archives and mode0600 manifest remain. Raw inputs under `/home/user/src/offmenu-data/originals`, parsed outputs and AI caches under `offmenu-data`, private runtime/control/credential files, logs, datasets and generated corpora remain local with original owner/source/rights holds.
- Shared primary `offmenu/node_modules`, worker06 WireMock jar and preview paths remain because live processes reference them. Collection source pins/wrappers and `.venv`/`.venv-tools` remain in `/home/user/offmenu-global-collection`; checkpoint verification venv is in the private custody root. No runtime dependency was moved or replaced.
- Recovery observed Freebuff PIDs3247547/3653544. The current client was working on an unrelated TV task; the older OffMenu client had no active execution child. Their records were read without injecting input/restarting either client. Preserved mutable owner paths were not written; the consolidation author used only the canonical develop path and temporary Git indexes for source snapshots. No competing collector/parser was started. Subsequent owner edits require a fresh census before cleanup.
- CIX execution and production stay paused. Memory is recall; existing permanent ledger remains authority. Source rights, ownership, actual permissions and denied-action holds remain.

## Priority continuation

1. Use only the canonical develop checkout, verify the final readback receipt and fast-forward:
   ```sh
   cd /home/user/src/offmenu-dev/develop
   git fetch origin --no-tags
   git switch develop
   git merge --ff-only origin/develop
   git status --short --branch
   git ls-remote origin refs/heads/develop
   ```
2. Select one preserved candidate through existing exact review: inspect the original source-relative differing paths in `reconciliation.json`, its prerequisite and current owner/reviewer packet. Prioritize reusable collection/coverage tools and the WFP normalizer; preserve source/acquisition/data permissions separately. Do not merge acquisition/control/snapshot branches wholesale.
3. For the local Python baseline limitation, reproduce from `baseline-validation` and compare actual projector inventory versus mocked exit status before proposing a separate bounded correction. No production grant or source read is authorized by a failing test.
4. Before any cleanup, re-read current Freebuff activity, Git status, ignored custody, source pins and runtime references. Remove only redundant checkouts whose unique work is remotely recoverable or intentionally retained in verified private data custody. Preserve original branches and active infrastructure. The per-checkout next actions distinguish runtime, dependency/evidence, local-change and redundant candidates; cleanliness alone is not runtime clearance. The only census-clean candidate is the runner setup clone; retain it until active runner source/dependency pins are qualified, even though its Git history is preserved. No cleanup should delay this checkpoint.
