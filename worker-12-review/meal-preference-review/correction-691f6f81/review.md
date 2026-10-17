# Worker 12 meal-preference correction follow-through

Date: 2026-10-14, Australia/Melbourne. Same existing review deliverable and permanent Worker 12. Original candidate, report, source reproducers and untracked artifacts remain preserved. **M12-01 and M12-02 resolved for the reported boundaries; no new reportable defect found in this exact correction delta.** READY FOR MORGAN REVIEW; final verdict/wiring pending, not shipped or accepted.

## Exact pins

- Prior candidate / delta base: `571cb01186b19184e7423dc9d032428009e0eae9`.
- Corrected candidate: `691f6f81cf3107a67a51641c2d7d9d9b5e85045e`.
- `git diff --binary PRIOR CORRECTED` SHA-256: `67ec3fb4ecfefaff2608502fa14bf5a266cdc2dea404acfa053913314a0ca58b`, matches supplied hash; exact bytes in `correction.diff`.
- Only the helper, focused tests and owned adoption document change. Selected 17-file tracked source/test import closure at `/tmp/offmenu-worker12-meal-correction-uikjj8cu`, with exact hashes in `snapshot-manifest.json`. No dependency/corpus/provider copies or installations.

## Resolutions

M12-01 (prior P2): `public/meal-preference-model.js:8` captures plain data; descriptor checks at `:20` and dense indexed-array checks at `:28`/`:32` reject sparse arrays, own custom array properties/iteration hooks and index accessors before term validation. The original `new Array(1)` likes input now throws rather than yielding undefined / serialized null. The original `[42]` with overridden `some` now throws without invoking the override. Independent custom iterator and index getter cases also reject with zero calls. Dense ordinary arrays still retain spelling and boundary lengths.

M12-02 (prior P2): all state/patch/scope/member records are captured as plain descriptor data. Accessor `spice` from the original changing-getter fixture is rejected with zero reads. `values` at `:63` captures a scalar and `:64`/`:65` validates/returns that same scalar. Patch/scope/nested-member accessors likewise reject without invocation. Ordinary null and none/mild/medium/hot pass the focused roundtrip/adapter/reset positives.

No author source was written by the reviewer. The corrected contract explicitly requires acyclic plain JSON for records and preserved member metadata, excluding proxies/accessors, hidden/symbol fields, custom arrays, undefined and class instances. Ordinary/null-prototype records, dense lists, finite numbers, booleans, strings and null remain supported. Unsupported proxies can execute reflection traps and are not claimed safe to inspect.

## Actually-run proof

- Corrected focused suite: `node --test --test-isolation=none tests-web/meal-preference-model.test.mjs`, exit 0, **9/9 passed**, `focused-tests.log`.
- The unchanged original reviewer script was run against corrected source. It exited 1 at the first sparse input because that input now throws the dense-array error. This is an expected failure of its old defect-observation assertions, **not** reported as a passing suite. Exact outcome and stderr retained in `unchanged-original-reproducer-outcome.json` / `.log`. The old script was not edited.
- Original input cases were then rechecked with corrected expectations, alongside preserved and added boundaries: exit 0, **16/16 independent assertions passed**, `independent-probes.mjs`, `.json`, `.log`.

Independent positives/negatives cover: original sparse/custom-some/changing-spice inputs; custom iterator/index getter rejection without calls; cycles/hidden fields/symbols/present undefined; null-prototype records and dense 32-by-100-character lists; patch/scope/nested member accessors; plain JSON roundtrip/null-versus-none; account/member mismatch; forbidden fields/version; metadata-preserving reset, unchanged peanut blocking, unknown ingredient needs-check/automatic-selection false; actual validator envelope stripping; caller/output array independence.

No broad suite repeated. All test child environments removed every inherited `GIT_*` variable. Fixtures are synthetic JavaScript state with no Git-writing or remote effects. No temporary Git repository was needed; selected snapshot has no `.git`.

Reproduction: use the snapshot as cwd for the focused command; run `node /absolute/path/to/independent-probes.mjs /absolute/path/to/snapshot /absolute/path/to/this/artifact-directory`, with inherited `GIT_*` removed. The prior script is preserved one directory above and retains its old expectation of defective behavior.

## Custody and remaining caller gates

Full follow-through before/after evidence in `custody-before.json`, `custody-after.json`, `preservation-and-custody.json`: own HEAD/branch/index, main/develop refs and primary common HEAD/index hashes unchanged. All 40 prior workspace artifacts retain their exact paths/hashes; whole-pool ref changes are separately recorded. Only the new authorized correction review artifacts were written. No branch reuse/reset, owner edits, shared merge, PR/publish, deploy, install, server, device, provider, external write, agent/session/worktree or new worker occurred.

Current `validateState` still drops the actual mealPreferences envelope; the independent negative remains true. State schema/persistence/restore/switch-account, authenticated member custody, UI/reset controls and any taste ranking remain owner-reviewed integration gates. The plain-JSON contract must be qualified against the real caller's full member data, including optional metadata; rich objects/present undefined are not silently preserved. Scope equality still is not authentication.

P0-07 restriction/actual-package certainty remains independent. Likes/reset do not waive allergies or unknowns in the tested pure scenarios, but no medical/allergy certification or complete P1-03 acceptance is claimed. Same Worker 12 idle; Morgan final verdict pending.
