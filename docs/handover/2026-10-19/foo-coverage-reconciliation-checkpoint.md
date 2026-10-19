# Foo global collection checkpoint — coverage reconciliation — 19 October 2026

## State and scope

This checkpoint follows the owner fetch/parse activity in `foo-fetch-owner-resolution.md` and does not supersede its authority or acquisition constraints. The current source worktree is the detached `f9acc09eeac340f82730409d4204a289265683eb` checkout. The existing authenticated private-publication route is `maldous/offmenu`; collection outputs and source bodies remain on Foo.

No fetch, parser, or child download process was active when checked. The stable `fixed-selection.lock` file remains; a nonblocking OS-lock probe succeeded, confirming no process held the exclusive lease at that observation. The latest parse result and checkpoint writes were completed at 16:45 UTC. The lock file itself is not proof of lease ownership: the supported launcher must acquire/check its exclusive OS lock before any future execution. Do not delete the lock file, receipts, or checkpoints.

## Verified parsed-output reconciliation

The offline builder and `scripts/reconcile-parsed-coverage.py` reconcile 12 already-existing normalized source releases. Each gzip JSONL stream was fully decompressed; record JSON, unique IDs, source/release provenance, row counts, and explicit country fields were checked. For available declared source files, SHA-256 was independently checked against the source manifest. The check created no network requests and changed no source originals or normalized corpora.

- Required matrix: 250 origin scopes (GLOBAL + 249 countries) × 13 taxonomy types = 3,250 cells.
- Unique discovery/parsed-output asset records: 6,068; parsed release outputs: 12; reused and verified local outputs: 12; new downloads: 0; fetches in this reconciliation: 0.
- 73,985 actual record-to-cell links over 508 asset-to-cell links; 148 cells have some parsed record evidence; 0 cells are complete.
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

The register is structurally valid under `build-origin-type-register.py`; recursive sanitization plus explicit filesystem-path scans passed, while legitimate URLs containing `/home/` remain URLs. Raw records, local original paths and normalized corpus bodies are not included. Deterministic `.gz` companions are included; the four compressed files total about 4.0 MiB and each decompresses byte-for-byte to its corresponding sanitized artifact. The compressed set is used for publication to fit within the existing 8 MiB publisher budget (compressed artifacts plus checkpoint: about 4.16 MB).

## Tests and repeatability

At the source checkout, these passed:

- `python3 -m unittest discover -s tests -p 'test_fetch_coverage.py' -v` — 31 tests.
- `python3 -m unittest discover -s tests -p 'test_global_coverage.py' -v` — 7 tests.
- `build-origin-type-register.py` validator accepted the reconciled register.

Before generating a fresh deterministic report, rerun `python3 scripts/reconcile-parsed-coverage.py` with `OFFMENU_DATA_ROOT` set to the private Foo data root if needed, then validate path sanitization and hashes again.

## Acquisition/parse blockers: do not replay unchanged work

Latest owner fetch result SHA-256: `72c2e83a752a7e526eb9cefe7ee778d911206665ab4f4524c4c38eb5b24dd795`. Latest parse result SHA-256: `8ff28274078a38326c116e1051cdbfc980081295caad9bf90332fece7c1b28a5`. Both were `complete-with-errors`, each performed zero network requests/body bytes, and each states `semanticParsingPerformed: false` and `normalizedOrGoldAdmitted: false`. The parse pass did preparation/readiness work; its 30 `ready` statuses are not semantic parser admission.

The operative selection is the reviewed 26-source whole-inventory successor, but its additive authority still states `automaticExecutionPermitted: false`, holds runner overlap, and prohibits resetting failed acquisition intents. The fetch result classified 4,753 inventory assets, verified 988/988 selected retained-original extents (28,437,595,507 bytes), and reused 7 local private originals; it downloaded no new source bodies. The newest parse receipt observed during continuation reports 32 `ready-nextstage` outcomes, 9 failed, and 11 unsupported; ten selected retained payloads were verified at 735,601 bytes. These are bounded structural-preparation outcomes, not semantic record parsing: the receipt still says `semanticParsingPerformed: false` and `normalizedOrGoldAdmitted: false`. Within the ten explicitly selected retained-structure rows, five produced ready receipts and five failed with `media-mismatch`; do not replay these unchanged. Error/unsupported classes also include inaccessible originals, uncertain private-save intents, archive expansion limits, missing member contracts, input-size caps, encrypted PDFs, and OCR-required PDFs. These latest-result figures are distinct from the 12 pre-existing national/global normalized releases reconciled above.

Exact owner action before any new transfer: provide an authorized current read-only full-request custody/claim snapshot for each selected source contract at all required readable roots, including a reviewed route for the inaccessible runner-owned claims root; disposition excluded/unresolved references in those contracts' metadata dependencies; retain the overlap hold until the runner owner reconciles actual outcomes; and issue fresh reviewed authority for any distinct eligible selection. Preserve all five terminal save-intent outcomes. Do not change permissions, assume inaccessible means empty, retry uncertain writes, or rerun unchanged blocked contracts.

Continuation check: no dependency-ready semantic parser task was established by the latest parse receipt; the existing selected stage is structural preparation only, and the held/error inputs lack a reviewed new contract or an evidenced repair. The installed launcher preflight was independently checked and rejects the selected source checkout as `source-checkout-changed` because the checkout contains the already-created untracked reconciliation scripts, sanitized artifacts, and checkpoint. Those local files were preserved; do not clean/reset the checkout or invoke collector internals to bypass the pin. Resume after providing a clean, exact pinned source installation through the supported setup, plus any required new source-specific parse contracts. Before running, recheck current selection, source permissions/holds, original identities, and the exclusive OS lease.

Dependency-ready work after that owner action: inventory successor work against the 3,250 matrix; acquire only newly authorized distinct releases once; checkpoint/hash-verify per asset; run source-specific parsers on confirmed originals and keep source-faithful extraction separate from normalization/translation; reconcile verified outputs back to this matrix without weakening source-specific terms.

## Publication

The existing `publish-manual-global-result.py` route is pinned to the earlier 2026-10-18 owner-manual handoff and rejects arbitrary envelopes. That handoff explicitly leaves a separate reviewed publication implementation pending; it is not authorized to bypass the signed envelope with direct GitHub blob/commit mutations. The private target `maldous/offmenu` was verified private with push permission, and its existing publication branch is fast-forward from the pinned anchor, but this is not authorization for an unrelated write. The compressed sanitized artifacts plus checkpoint total about 4.16 MB. They were published with the three reconciliation scripts to the verified private handoff branch at commit `c51234373964857668661e21738c98781ea3f9c4`; all eight files were read back from GitHub and matched their expected Git blob SHA-1 and SHA-256. The raw source bodies, normalized corpora and private logs remain on Foo; only sanitized register artifacts and metadata were published.
