# Foo global collection checkpoint — coverage reconciliation — 19 October 2026

## Handover for the next agent — 20 October 2026

This section is the current publication checkpoint. It supersedes nothing below:
the 19 October evidence record remains authoritative for its own measurements.

### Objective, branch and source commit

- Objective: a configuration-driven `fetch → parse → normalize → translate`
pipeline covering GLOBAL plus 249 countries across 13 data types. Immediate
priority is actual fetched originals and usable parsed records with provenance.
The catalogue is not being rebuilt and the project is not being restarted.
- Approved private integration/publication route: branch
`integration/foo-owner-custody-snapshot-20261018` of the private
`maldous/offmenu` repository (verified push permission; fast-forward commits
only, no force-push, no unrelated merges).
- Source checkout: detached `f9acc09eeac340f82730409d4204a289265683eb`
("Install reviewed whole-inventory fetch amendment"), which is the head of
`origin/integration/runner-global-parallel-20261018`.
- This document's own commit is the tip of the publication branch; identify it
with `git log -1 --format='%H %cI %s' -- docs/handover/2026-10-19/foo-coverage-reconciliation-checkpoint.md`.

### Implemented, executed and verified in this checkpoint session (20 October 2026)

Verified here, offline, against real local artifacts:

- `python3 -m unittest discover -s tests -p 'test_fetch_coverage.py'` → 31 tests OK.
- `python3 -m unittest discover -s tests -p 'test_global_coverage.py'` → 7 tests OK.
- `python3 -m unittest discover -s tests -p 'test_origin_type_status.py'` → 8 tests OK.

Test-run scope, stated precisely: all three suites were run in the source checkout
(`f9acc09...`). This publication branch is a handoff bundle whose tree does not
contain `tests/test_fetch_coverage.py` or the local register inputs, so a clean
checkout of this branch reproduces only the 7 `test_global_coverage` and 8
`test_origin_type_status` tests (both verified here). Re-run the 31-test suite in
the source checkout shown in the command list below.
- All four published `.gz` artifacts decompress byte-for-byte to their local
uncompressed counterparts (SHA-256 equality checked for all four), and the local
uncompressed artifacts are unchanged since publication.
- `scripts/gzip-coverage-artifacts.py` reproduces the published `.gz` bytes
exactly (`cmp` equal on `origin-type-coverage.jsonl.gz`).
- `scripts/verify-bulk-prices-slice.py` → `schema-validation-passed`: 317,898 Open
Prices packets validated, 317,898 resources, 1,896,978 assertions, 317,898
citations, 0 relations, 0 translations, 319 partition files read, 16.5 s.
- `scripts/verify-common-packets.py $OFFMENU_DATA_ROOT/common-bulk-food-20261014`
→ `all-output-packets-schema-validated` (full run, 9,796,656 packets across 9,797
packet files; 9,796,656 resources, 137,295,959 assertions, 2,915,727 relations,
0 translations; source records off 5,452,981 + usda-files 4,025,777 + prices
317,898). Every file digest, packet count and per-source count was checked
against the manifest and matched; mismatch anywhere would have raised. This
confirms the bulk release's schema/identity/citation claims, not its semantic
normalization.
- Publication-state reconciliation: the four `.gz` artifacts,
`scripts/build-origin-type-register.py`, `scripts/publish-coverage-register.py`
and this checkpoint were already byte-identical to the publication branch, so
they were not re-uploaded.
- Reconciliation of local vs origin: 556 remote branches fetched; only
differences found were the updated `scripts/reconcile-parsed-coverage.py` and the
never-published `tests/test_origin_type_status.py`, plus the four `/tmp` scripts
captured this session.

Implemented but **not executed or not yet verified**:

- `scripts/reconcile-parsed-coverage.py` (486-line local revision) adds the
`prices-2026-10-12` / `price-observations` corpus and partitioned-output digest
verification. The register has **not** been regenerated with it: the current
register still contains 0 `price-observations` rows. Treat the prices
reconciliation as pending, not as delivered coverage.
- `scripts/align-prices-common.py` would create
`$OFFMENU_DATA_ROOT/common-alignment-20261019/prices`; that directory does not
exist, so no prices packet release has been produced from the retained original.
No other verification was left outstanding at publication time.

### Fetch results (unchanged this session; no new transfers)

- New downloads in this checkpoint session: 0. Network requests: 0. No fetch job
was run or restarted.
- Last owner fetch result: SHA-256
`72c2e83a752a7e526eb9cefe7ee778d911206665ab4f4524c4c38eb5b24dd795`, status
`complete-with-errors`, zero network requests and zero body bytes. It classified
4,753 inventory assets, verified 988/988 selected retained-original extents
(28,437,595,507 bytes) and reused 7 local private originals; no new source bodies
were downloaded.
- Newest acquisition receipts on Foo: `$OFFMENU_DATA_ROOT/owner-collection-runtime/collection/private-original-result-*.json`
(0600, private), latest batch written 19 October 2026 22:35 local (+11:00);
observed statuses in that batch include `verified-private-original` and `blocked`.
Nothing was written there during this session and a 15-second re-check showed no
ongoing writes.
- Holds remain exactly as recorded below (overlap hold, uncertain save intents,
inaccessible runner-owned claims root).

### Parse results (actual assets and counts)

- Twelve pre-existing source-faithful normalized releases are reconciled in the
register (mext-2023, afcd-3, cofid-2021, germany-bls-4.0, ciqual-2025,
matvaretabellen-2026, frida-5.5, cnf-2015, fineli-20.0, sweden-food-2026-07-01,
foodfiles-2024-v01, world-recipes-global-20261014). 63 declared original files
independently hash-verified, 0 mismatches, 0 unavailable among declared files.
- `common-bulk-food-20261014` manifest (`status: full-schema-identity-citation-public-scope-checked`):
9,796,656 packets / 9,796,656 resources / 137,295,959 assertions / 2,915,727
relations from source records off 5,452,981 + usda-files 4,025,777 + prices
317,898; translations 0.
- Open Prices source release `prices-2026-10-12` (`status: normalized`, 256
partitions): raw 326,767 → accepted 317,898, excluded 8,869, quarantined 0,
duplicates 0.
- Latest structural parse receipt (see SHA in the blocker section): 32
`ready-nextstage`, 9 failed, 11 unsupported; 10 selected retained payloads
verified at 735,601 bytes; `semanticParsingPerformed: false`,
`normalizedOrGoldAdmitted: false`. Rejected/unsupported classes: `media-mismatch`
(5 of the 10 selected rows), inaccessible originals, uncertain private-save
intents, archive expansion limits, missing member contracts, input-size caps,
encrypted PDFs, OCR-required PDFs.
- Register cell evidence (do not confuse with completeness): 3,250/3,250 cells
carry an explicit status — 148 `parsed-evidence-partial`, 133
`explicit-type-binding-no-records`, 659 `discovery-candidates-unbound`, 2,310
`no-candidate-in-reconciled-inputs`; **0 cells complete**; 73,985 record-to-cell
links over 508 asset-to-cell links.

### Normalize and translate status

- Everything counted above is source-faithful structural normalization plus
schema/identity/citation validation only. It is **not** semantic gold-standard
normalization and **not** translation.
- Translation: 0 translations in the bulk manifest, no translation outputs
located under the data root. Normalization: no `gold`/semantic admission is
claimed anywhere (`normalizedOrGoldAdmitted: false` in the latest receipts).
- Recorded as `unknown`, not as absent: whether any country/type cell is truly
unserved beyond the reconciled inputs.

### Current jobs and how to inspect them safely

- No OffMenu fetch, parse or reconcile process is running. A nonblocking OS-lock
probe on `$OFFMENU_DATA_ROOT/owner-collection-runtime/collection/fixed-selection.lock`
succeeded (FREE), so no process holds the exclusive lease. Do not delete that
lock file, receipts or checkpoints.
- Long-running unrelated services are present (dev-preview workerd/wiremock
instances, the local GitHub actions runner service, other Codex
sessions). None of them is an OffMenu acquisition job; leave them alone.
- Inspect safely: read `private-original-result-*.json` and the parse/fetch
receipts as data (0600, keep local); probe locks with a nonblocking `flock`; never
rerun a blocked contract to "check" it.
- Jobs started this session: one read-only verification,
`scripts/verify-common-packets.py $OFFMENU_DATA_ROOT/common-bulk-food-20261014`,
which completed successfully (result recorded above) and wrote no files. Nothing
is running now.

### Remaining blockers, evidence and required action

1. **Genuine access/licence restriction** — FAO INFOODS originals are retained as
private noncommercial research/reference with attribution, no redistribution,
no translation/adaptation. Evidence: `originals/owner37-global-fao-20261018/*/receipt.json`
`rightsBasis`. Action: keep originals on Foo; publish only sanitized manifests.
2. **Missing owner authority (permission, not a bug)** — an authorized current
read-only full-request custody/claim snapshot for each selected source contract
is still required, including a reviewed route for the inaccessible runner-owned
claims root, plus fresh reviewed authority for any distinct eligible selection.
Evidence: the owner-action paragraph below. Action: owner issues the snapshot
and authority; do not change permissions and do not assume inaccessible = empty.
3. **Internal workflow selection** — the reviewed 26-source whole-inventory
successor still states `automaticExecutionPermitted: false` and holds runner
overlap; failed acquisition intents must not be reset. Action: runner owner
reconciles actual outcomes before any new acquisition.
4. **Technical (launcher pin)** — installed launcher preflight rejects the
checkout as `source-checkout-changed` because of local untracked files. This
session published those files through the integration branch; the supported
setup must still install an exact pinned source before `fetch`/`parse` will run.
Evidence: preflight message recorded below. Action: rerun the reviewed
`--install COMMIT TREE` setup against a clean pinned installation.
5. **Technical (parse)** — 5 of 10 selected retained rows fail with
`media-mismatch`; unsupported classes include encrypted and OCR-required PDFs,
archive expansion limits, missing member contracts, input-size caps. Action:
source-specific repair contracts; do not replay unchanged.
6. **Technical (unfinished work)** — prices reconciliation into the register and
the prices packet release are implemented but not executed (see above). Action:
run the two scripts in the command list below, then republish.
7. **Technical (publication authorization)** —
`scripts/publish-manual-global-result.py` remains pinned to the earlier
2026-10-18 owner-manual handoff and rejects arbitrary envelopes; a separately
reviewed publication implementation is still pending for anything outside that
envelope. Action: owner reviews/extends the publisher rather than mutating
GitHub objects directly.
8. **Environment (resolved locally)** — plain `git fetch` failed with
`fatal: could not read Username for 'https://github.com'`. Fixed in this checkout
with `git config credential.helper '!gh auth git-credential'`; the next agent must
set it again in any fresh clone.

### Outstanding work, priority order

1. Usable fetch/parse output first: run the updated
`scripts/reconcile-parsed-coverage.py` (adds `price-observations`, verifies
partitioned digests), regenerate the register, `gzip-coverage-artifacts.py`,
validate with `build-origin-type-register.py --check`, then publish the sanitized
bundle through the reviewed route.
2. Execute `scripts/align-prices-common.py` to produce the Open Prices packet
release from the retained original, verify it with `verify-common-packets.py`,
and reconcile it — this is the fastest path to new parsed records with provenance.
3. Owner action (blockers 2 and 3) to unblock acquisition for the 3,102 cells that
currently have no parsed record evidence.
4. Source-specific semantic parsers on confirmed originals, kept separate from
normalization; only then normalization, then translation.
Exhaustive source discovery is **not** a prerequisite for processing eligible
sources that already exist locally.

### Exact commands for the owner or next agent

```bash
cd ~/offmenu-global-collection/sources/f9acc09eeac340f82730409d4204a289265683eb
git config credential.helper '!gh auth git-credential'    # required in a fresh clone
export OFFMENU_DATA_ROOT=~/src/offmenu-data   # default data root on Foo

# offline tests (31 / 7 / 8 tests)
python3 -m unittest discover -s tests -p 'test_fetch_coverage.py'
python3 -m unittest discover -s tests -p 'test_global_coverage.py'
python3 -m unittest discover -s tests -p 'test_origin_type_status.py'

# verification helpers (jsonschema-rs lives in the tools venv; deps are declared in pyproject.toml)
~/offmenu-global-collection/.venv-tools/bin/python scripts/verify-bulk-prices-slice.py
~/offmenu-global-collection/.venv-tools/bin/python scripts/verify-common-packets.py "$OFFMENU_DATA_ROOT/common-bulk-food-20261014"

# regenerate + publish the sanitized register (step 1 of the priority list)
python3 scripts/reconcile-parsed-coverage.py
python3 scripts/gzip-coverage-artifacts.py
python3 scripts/build-origin-type-register.py --check

# publication (fast-forward only)
git push origin HEAD:integration/foo-owner-custody-snapshot-20261018
```

Durable acquisition launcher (installed, reviewed; only runs when the pinned
source passes preflight):

```bash
~/offmenu-global-collection/fetch     # stage: fetch
~/offmenu-global-collection/parse     # stage: parse (explicit only)
~/offmenu-global-collection/run       # alias of fetch
~/offmenu-global-collection/fetch --publish-only   # publication recovery only
```

See `docs/fetch-parse-owner-launcher.md` for the launcher contract.

## State and scope

This checkpoint follows the owner fetch/parse activity in `foo-fetch-owner-resolution.md` and does not supersede its authority or acquisition constraints. The current source worktree is the detached `f9acc09eeac340f82730409d4204a289265683eb` checkout. The existing authenticated private-publication route is `maldous/offmenu`; collection outputs and source bodies remain on Foo.

No fetch, parser, or child download process was active when checked. The stable `fixed-selection.lock` file remains; a nonblocking OS-lock probe succeeded, confirming no process held the exclusive lease at that observation. The latest parse result and checkpoint writes were completed at 16:45 UTC. The lock file itself is not proof of lease ownership: the supported launcher must acquire/check its exclusive OS lock before any future execution. Do not delete the lock file, receipts, or checkpoints.

## Verified parsed-output reconciliation

The offline builder and `scripts/reconcile-parsed-coverage.py` reconcile 12 already-existing normalized source releases. Each gzip JSONL stream was fully decompressed; record JSON, unique IDs, source/release provenance, row counts, and explicit country fields were checked. For available declared source files, SHA-256 was independently checked against the source manifest. The check created no network requests and changed no source originals or normalized corpora.

- Required matrix: 250 origin scopes (GLOBAL + 249 countries) × 13 taxonomy types = 3,250 cells.
- Unique discovery/parsed-output asset records: 6,068; parsed release outputs: 12; reused and verified local outputs: 12; new downloads: 0; fetches in this reconciliation: 0.
- 73,985 actual record-to-cell links over 508 asset-to-cell links; 148 cells have some parsed record evidence; 0 cells are complete.
- Every cell now has an explicit evidence-derived `status` and `statusBasis`: 3,250/3,250 known-status rows comprise 148 `parsed-evidence-partial`, 133 `explicit-type-binding-no-records`, 659 `discovery-candidates-unbound`, and 2,310 `no-candidate-in-reconciled-inputs`. The last class means only that no candidate appears in the reconciled inputs; it does not assert no source exists. The taxonomy has seven possible statuses, and the unresolved/reference variants remain available as evidence changes.
- 63 declared original files independently verified; 0 source-file hash mismatches; 0 unavailable among declared files. Parsed output files and manifests were also hash-pinned.
- National food-composition records are linked only to the explicit country codes in their records, as availability of a national reference—not as the origin of each food. Recipe links require the explicit country list to agree with the source cuisine-country field. No absent/global field is fanned out to any country.
- Ingredient identity is represented separately from food composition and recipe ingredient expressions. No claim is made that recipe strings are canonical ingredient identifiers. The other ten taxonomy types remain independent requirements.

Release-level identities require source ID + exact release ID + normalized-output SHA-256. No URL-only joining or release merging is used. The complete sanitized machine-readable artifacts are in `docs/coverage-register/2026-10-19/`:

| File | Bytes | SHA-256 |
|---|---:|---|
| `coverage-register.json` | 35,349,121 | `a77e071b9628368768f17edd478d52bc7c1f0bace86101a182b3547076e78c64` |
| `origin-type-coverage.jsonl` | 9,377,619 | `baf8c9c9177b8b0f26ce02b18c94ccf583bc2a824cb40cf65eb6dc21a27ef7cf` |
| `unique-assets.jsonl` | 17,673,715 | `46877de12b20bdd99badd8d97bf87be035dd8414747ef57d436817344109b3e7` |
| `source-blockers.jsonl` | 9,636,860 | `2a3bdf729fa1b2dbeef8341c0f0092af63dca7f8ee8c14ded2bd23f180ff5bbb` |

The register is structurally valid under `build-origin-type-register.py`; recursive sanitization plus explicit filesystem-path scans passed, while legitimate URLs containing `/home/` remain URLs. Raw records, local original paths and normalized corpus bodies are not included. Deterministic `.gz` companions are included; the four compressed files total about 4.0 MiB and each decompresses byte-for-byte to its corresponding sanitized artifact. The compressed set is used for publication to fit within the existing 8 MiB publisher budget (compressed artifacts plus checkpoint: about 4.2 MB).

## Tests and repeatability

At the source checkout, these passed:

- `python3 -m unittest discover -s tests -p 'test_fetch_coverage.py' -v` — 31 tests.
- `python3 -m unittest discover -s tests -p 'test_global_coverage.py' -v` — 7 tests.
- `build-origin-type-register.py` validator accepted the reconciled register.
- `python3 -m unittest discover -s tests -p 'test_origin_type_status.py' -v` — 8 tests for all status classes and their evidence basis.
- Publisher bundle validation requires all 3,250 cells to carry an allowed status and basis and reconciles the status histogram.

Before generating a fresh deterministic report, rerun `python3 scripts/reconcile-parsed-coverage.py` with `OFFMENU_DATA_ROOT` set to the private Foo data root if needed, then validate path sanitization and hashes again.

## Acquisition/parse blockers: do not replay unchanged work

Latest owner fetch result SHA-256: `72c2e83a752a7e526eb9cefe7ee778d911206665ab4f4524c4c38eb5b24dd795`. Latest parse result SHA-256: `8ff28274078a38326c116e1051cdbfc980081295caad9bf90332fece7c1b28a5`. Both were `complete-with-errors`, each performed zero network requests/body bytes, and each states `semanticParsingPerformed: false` and `normalizedOrGoldAdmitted: false`. The parse pass did preparation/readiness work; its 30 `ready` statuses are not semantic parser admission.

The operative selection is the reviewed 26-source whole-inventory successor, but its additive authority still states `automaticExecutionPermitted: false`, holds runner overlap, and prohibits resetting failed acquisition intents. The fetch result classified 4,753 inventory assets, verified 988/988 selected retained-original extents (28,437,595,507 bytes), and reused 7 local private originals; it downloaded no new source bodies. The newest parse receipt observed during continuation reports 32 `ready-nextstage` outcomes, 9 failed, and 11 unsupported; ten selected retained payloads were verified at 735,601 bytes. These are bounded structural-preparation outcomes, not semantic record parsing: the receipt still says `semanticParsingPerformed: false` and `normalizedOrGoldAdmitted: false`. Within the ten explicitly selected retained-structure rows, five produced ready receipts and five failed with `media-mismatch`; do not replay these unchanged. Error/unsupported classes also include inaccessible originals, uncertain private-save intents, archive expansion limits, missing member contracts, input-size caps, encrypted PDFs, and OCR-required PDFs. These latest-result figures are distinct from the 12 pre-existing national/global normalized releases reconciled above.

Exact owner action before any new transfer: provide an authorized current read-only full-request custody/claim snapshot for each selected source contract at all required readable roots, including a reviewed route for the inaccessible runner-owned claims root; disposition excluded/unresolved references in those contracts' metadata dependencies; retain the overlap hold until the runner owner reconciles actual outcomes; and issue fresh reviewed authority for any distinct eligible selection. Preserve all five terminal save-intent outcomes. Do not change permissions, assume inaccessible means empty, retry uncertain writes, or rerun unchanged blocked contracts.

Continuation check: no dependency-ready semantic parser task was established by the latest parse receipt; the existing selected stage is structural preparation only, and the held/error inputs lack a reviewed new contract or an evidenced repair. The installed launcher preflight was independently checked and rejects the selected source checkout as `source-checkout-changed` because the checkout contains the already-created untracked reconciliation scripts, sanitized artifacts, and checkpoint. Those local files were preserved; do not clean/reset the checkout or invoke collector internals to bypass the pin. Resume after providing a clean, exact pinned source installation through the supported setup, plus any required new source-specific parse contracts. Before running, recheck current selection, source permissions/holds, original identities, and the exclusive OS lease.

Dependency-ready work after that owner action: inventory successor work against the 3,250 matrix; acquire only newly authorized distinct releases once; checkpoint/hash-verify per asset; run source-specific parsers on confirmed originals and keep source-faithful extraction separate from normalization/translation; reconcile verified outputs back to this matrix without weakening source-specific terms.

## Publication

The existing `publish-manual-global-result.py` route is pinned to the earlier 2026-10-18 owner-manual handoff and rejects arbitrary envelopes. That handoff explicitly leaves a separate reviewed publication implementation pending; it is not authorized to bypass the signed envelope with direct GitHub blob/commit mutations. The private target `maldous/offmenu` was verified private with push permission, and its existing publication branch is fast-forward from the pinned anchor, but this is not authorization for an unrelated write. The compressed sanitized artifacts plus checkpoint total about 4.16 MB. They were published with the three reconciliation scripts to the verified private handoff branch at commit `80e699a8cfa48bf101bc8e06b73562e9b7ef90e7`; all eight files were read back from GitHub and matched their expected Git blob SHA-1 and SHA-256. This historical publication predates the explicit cell-status fields; publish the updated status-bearing bundle through the same pinned publisher after its validation passes. The raw source bodies, normalized corpora and private logs remain on Foo; only sanitized register artifacts and metadata were published.
