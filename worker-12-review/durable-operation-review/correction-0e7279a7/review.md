# Worker 12 corrected durable-operation review

Date: 2026-10-14 (Australia/Melbourne). Same permanent Worker 12, same existing review deliverable. Original report and reproducers remain preserved in the parent directory. Morgan final verdict and wiring approval pending.

**D12-01 and D12-02 are resolved for the reported boundaries. No new reportable finding was identified in this exact correction delta.** This is independent source/synthetic regression evidence, not server integration, autosync shipment, physical two-device proof or release acceptance.

## Exact pins

- Prior candidate / correction base: `d0e84e16884d4be893620c73556f45892c61671a`.
- Corrected candidate: `0e7279a7b3ba9e8d68f5aba546d2404fc3fc99a9`.
- Exact `git diff --binary PRIOR CORRECTED` SHA-256: `2ef3a73831e48fefd36d8bdeefa02fb2c44360c4253274e10fcafb5cf20cd3d2`; matches dispatch; retained as `correction.diff`.
- Delta changes only `public/durable-operation-queue.js` and its test file.
- Selected immutable tracked-source snapshot: `/tmp/offmenu-worker12-durable-correction-gwub0dhe`; same 27-file related source/test/schema closure as prior review, extracted by read-only Git object reads. Exact files/hashes retained in `snapshot-manifest.json`. No dependencies/corpora/providers copied or installed.

## Precise resolutions

D12-01 (prior P2 / medium, valid ACK rejected by property order): corrected `public/durable-operation-queue.js:31` validates exactly the account/resource/grant field set and emits canonical field order. Transport ACK matching now normalizes the captured ACK scope before comparison; persisted record scope is also normalized for comparison. Independent original reordered-key transport reproducer now returns `{status:'acknowledged',operationId:'deduct1'}` and persists acknowledged. An additional explicit reconciliation with reordered keys succeeds and flushes idle. Wrong account/resource/grant values and an extra scope field remain unknown on transport and fail explicit acknowledgment. Extra-field rejection is now part of the documented contract, not silently ignored identity input.

D12-02 (prior P2 / medium, payload transformed after validation): corrected `public/durable-operation-queue.js:38` builds a fresh tree from data descriptors; `:51` obtains descriptors, `:59` rejects accessors/hidden/symbol fields and `:61` defines validated captured values without serialization hooks. `copy` at `:25` uses this capture path. The original nonenumerable `toJSON` and getter reproducers now throw the JSON-data error before persistence or sending, with **zero hook/getter invocations**. Independent positive fixture preserves own benign `__proto__`, `constructor`, string-valued `toJSON`, nested objects and arrays in persisted AND sent payloads. Candidate tests additionally reject nested hooks/accessors, cycles, custom prototypes, sparse arrays and function/symbol payload fields.

No fixes or author source writes were made by this reviewer.

## Actually-run proof

| Invocation / probe | Result | Artifact |
| --- | --- | --- |
| `node --test tests-web/durable-operation-queue.test.mjs` | Exit 0; 17/17 pass | `focused-tests.log` |
| `node --test tests-web/durable-operation-queue.test.mjs tests-web/journey.test.mjs tests-web/household.test.mjs tests-web/kitchens.test.mjs` | Exit 0; 41/41 pass | `41-tests.log` |
| Updated original reviewer reproducers + boundaries | Exit 0; 15/15 assertions pass | `independent-probes.mjs`, `.json`, `.log` |

The 41 comprise 17 corrected helper tests plus the same 24 related journey/household/kitchen tests used in the original review. The original 37-test evidence remains preserved. This is the reviewer-run invocation, not reliance on the author's reported 41.

Independent probes retain positive canonical ACK, isolated mismatched account/resource/grant rejection, uncertainty-save failure/no send, expired unknown FIFO/reconciliation, acknowledgment-save failure/same-ID replay, in-memory revocation after failed durable revoke, and serialized concurrent flush boundaries. The three additions directly verify preserved benign reserved JSON fields, extra-scope rejection, and reordered explicit reconciliation.

Reproduce with all inherited environment names starting `GIT_` removed. Test commands use the snapshot as cwd. Reviewer probe invocation is `node /absolute/path/to/independent-probes.mjs /absolute/path/to/snapshot /absolute/path/to/this/artifact-directory`. It uses synthetic in-memory storage and transports. No Git-writing fixture ran; no repository was initialized in the disposable snapshot, which has no `.git`.

## Custody and retained limits

`custody-before.json`, `custody-after.json` and `custody-comparison.json` confirm full-follow-through stability of own HEAD/branch/index, real main/develop refs and common primary HEAD/index hashes. Whole-pool branch snapshots show no unrelated ref changes during this follow-through. Status remains only `?? worker-12-review/`; prior untracked artifacts preserved. No tracked source, author branch, receipt/data, main/develop or index was changed. This follow-through captured shared hashes before tests, unlike the explicitly limited shared sampling in the original report.

No servers, browsers, physical devices, remote providers, paid services, publish/PR/merge, new sessions/agents/worktrees or settings changes occurred. Review is restricted to the immutable correction and regressions.

Existing cloud state APIs still lack atomic operation deduplication/effect/explicit ACK integration; the candidate remains a pure helper. Durable atomic storage and exclusive per-key cross-tab ownership are separate adapter gates. A declaration `idempotent:true` does not qualify a real server. Failed durable revocation still requires caller custody handling, new-grant scoping and remote authorization. No shipped autosync or physical two-device claim is made.

Review-ready correction advice complete. Morgan owns final verdict and wiring. Same Worker 12 returns idle within fixed32.
