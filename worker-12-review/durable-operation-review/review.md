# Worker 12 independent durable-operation review

Date: 2026-10-14 (Australia/Melbourne). Reviewer: same permanent LOCAL Worker 12, thread `01a138ee-5252-7f63-8b43-cf730ecd7e05`. Morgan owns the final verdict/integration. Prior UIUX reviews remain untouched.

**Review-ready advice: correct two P2 helper defects before wiring this queue into autosync.** The helper's crash/replay and storage-failure contracts are substantially covered by synthetic tests, but those tests do not establish a shipped sync feature, server deduplication or physical two-device proof. This is not integration or acceptance approval.

## Exact scope

- Base: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.
- Candidate: `d0e84e16884d4be893620c73556f45892c61671a`.
- `git diff --binary BASE CANDIDATE` SHA-256: `c44cc12a86b678653e1f484106bb45e7f89f980bedf153868eeca0fe8c7eede6`, exact bytes in `candidate.diff`. Matches supplied Worker 16 immutable receipt.
- Delta: only `public/durable-operation-queue.js` (141 added lines) and `tests-web/durable-operation-queue.test.mjs` (174 added lines).
- Current reviewer branch was supplied as `feature/durable-operation-review-20261014`, based at the exact base above. Fetch exit 0 at `2026-10-14T06:57:49.252077+00:00` is dispatch-supplied evidence, not repeated or independently qualified here. Baseline remains provisional, not release-qualified.
- Selected immutable-source snapshot: `/tmp/offmenu-worker12-durable-review-zfqit4mp`. 27 tracked files: the two additions, package metadata, three related test files and their local import/schema closure. File-level hashes in `snapshot-manifest.json`. No corpus/provider/dependency copies, installs, worktrees, agents or servers. Existing Node runtime sufficed.

## Findings

### D12-01 — P2 / medium: field-equivalent acknowledgments depend on JSON property order

Candidate location: `public/durable-operation-queue.js:25`, consumed by `:80` and `:136`; explicit reconciliation also reaches `:109`.

Trigger: the transport returns the correct operation ID, `acknowledged: true` and identical account/resource/grant values, but constructs scope keys in a different order. `equal()` compares serialized bytes rather than field values. JSON object member order should not become an authorization/acknowledgment protocol requirement; the documented scope contract does not require serialization order.

Actually-run reproducer: `independent-probes.mjs`, probe “P2 D12-01 reordered correct scope ACK remains unknown”. Queue scope is `{accountId:'alice',resourceId:'kitchen',grantId:'grant1'}`; transport ACK uses `{grantId:'grant1',resourceId:'kitchen',accountId:'alice'}` with the same ID. Observed flush result: `{status:'unknown',operationId:'deduct1'}`; persisted operation stays unknown. The canonical-key-order positive control acknowledges and then idles with one send.

Impact: valid server acknowledgments can cause repeated same-ID delivery and block subsequent FIFO work until expiry/reconciliation. Required remote deduplication prevents repeated effects only if separately implemented; the helper cannot resolve this valid response as written. Manual acknowledge uses the same defective comparator.

Advice: validate and normalize acknowledgment scope into the captured three-field schema, then compare each identity value (with an explicit extra-field policy). Add reordered-scope positives and account/resource/grant mismatch negatives. Preserve strict isolation. No fix applied.

### D12-02 — P2 / medium: checked payload differs from the JSON payload actually persisted/sent

Candidate location: `public/durable-operation-queue.js:24`, `:40`, `:46`, with captured result consumed by `:84` and transport at `:133`.

Trigger: plain object has an own nonenumerable `toJSON` function, or an accessor whose value changes between validation and serialization. `Object.values()` validates one set of values; `JSON.stringify()` subsequently invokes hooks/getters and can produce different data. A plain prototype does not prevent those behaviors. This contradicts the comment that lossy/function-bearing/custom data is rejected and the pending-envelope capture promise.

Actually-run reproducer: `independent-probes.mjs`, probe “P2 D12-02 nonenumerable toJSON silently replaces captured payload”:

```js
const payload = {deduct: 2};
Object.defineProperty(payload, 'toJSON', {value: () => ({deduct: 999})});
await queue.enqueue({operationId:'deduct1', payload, expiresAt:10000});
await queue.flush();
```

Caller property remains `deduct:2`; returned persisted operation and transport envelope both contain `deduct:999`. Additional accessor probe returns 2 on validation and 999 on the second read; two reads occur and 999 is persisted. Both are synthetic, no remote effect executed.

Impact: the durable ID is bound to a silently transformed payload rather than the checked caller data. A quantity deduction can therefore change before first persistence/send even though ordinary post-enqueue caller mutation is protected. This is a helper correctness defect, not proof of malicious production data or current UI exposure.

Advice: build a fresh JSON tree during validation and reject accessor/function-bearing/non-JSON descriptors before serializing that tree. Do not re-read the caller object or execute serialization hooks after validation. Add these boundary cases while retaining the existing NaN/undefined/date/function checks. No fix applied.

## Reviewer actually-run evidence

| Check | Result | Evidence |
| --- | --- | --- |
| Candidate helper suite alone | Exit 0, 13/13 pass | `focused-tests.log` |
| Candidate + related regression suites | Exit 0, 37/37 pass | `37-tests.log`, `37-tests-command.json` |
| Reviewer independent probes | Exit 0, 12/12 reproducer assertions pass, including two demonstrated defects | `independent-probes.mjs`, `.json`, `.log` |

The 37-test invocation was `node --test tests-web/durable-operation-queue.test.mjs tests-web/journey.test.mjs tests-web/household.test.mjs tests-web/kitchens.test.mjs`. Counts are 13 new, 14 journey, 8 household, 2 kitchen. The supplied author receipt reports 37 but does not identify the exact invocation; this is a reconstructed relevant 37-test scope, not a claim that the author's invocation was recovered. All files executed came from candidate.

Independent cases also verified: wrong account/resource/grant ACKs retain unknown and cannot explicitly reconcile; failure to persist uncertainty prevents transport; expired unknown evidence blocks FIFO and a correct scoped explicit ACK releases the successor; failed acknowledgment persistence preserves same-ID replay; simultaneous flushes on one instance serialize to acknowledged/idle with one send; failed revocation persistence rejects and the existing instance stays revoked. Probe success means expected observations were asserted, not that defects are acceptable.

Reproduce from the selected snapshot with all inherited environment names beginning `GIT_` removed. The reviewer script runs as `node /absolute/path/to/independent-probes.mjs /absolute/path/to/snapshot /absolute/path/to/artifact-directory`. It uses in-memory storage and synthetic transports only. No Git-writing fixture exists in these suites, so no disposable Git repository was needed and none was initialized. Snapshot has no `.git`; every child test environment strips inherited `GIT_*`.

## Contracts and gates retained

Positive author cases reproduce lost-response-after-effect with one synthetic deduction when transport atomically deduplicates `(scope, operationId)`. Uncertainty is committed before sending; crashes/restarts retain ID/payload and backoff; ACK persistence failure leaves unknown; HTTP-like success alone does not acknowledge; account/resource/grant keying isolates records; expiry preserves evidence and blocks FIFO; tombstones are retained at capacity. These are adapter/server assumptions tested with synthetic implementations, not verified production guarantees.

A single live writer per scoped key and durable atomic storage commit are required. Serializing one helper instance does not establish cross-tab locking. No storage adapter, scheduler, authenticated transport, server dedup ledger or atomic server effect/ACK endpoint was supplied by the candidate.

Revocation sets the instance flag immediately, suppressing in-flight ACK acceptance, but a failed durable save is explicitly an error: our probe confirms the persisted record can still say `revoked:false`. Callers must treat that failure as unresolved custody, use a new scope for a new login/grant, and require remote authorization to reject the old grant. Neither a hung transport nor an already-sent effect can be undone by this helper. This boundary is not a shipped logout guarantee.

Immutable integration context in `integration-context.json`: current `public/sync-ui.js:12` regenerates checkpoint mutationId and `:15` PUTs only revision/state; `cloud/kitchens.mjs:12` returns revision for state PUT. Candidate adds no callsites to the new helper. Existing cloud APIs lack this helper's durable dedup/explicit acknowledgment protocol. Server deduplication must be atomic with the effect and acknowledged identity; simply setting `idempotent:true` is a caller declaration, not remote qualification.

No production/provider traffic, paid access, physical devices, browser acceptance or two-device proof occurred. No author receipt/data/branch was written. Morgan must review any future adapter/server wiring and integration separately.

## Custody and limits

Before/after own HEAD/main/develop/index identity is recorded. Only the authorized `worker-12-review/durable-operation-review` artifacts are created in this checkout; no tracked source changed. Whole-pool branch snapshots are retained and concurrent unrelated branch movement is reported separately rather than attributed to this review. No branch/ref/index write command or Git-writing fixture ran.

Shared primary `.git/HEAD` and `.git/index` were first hashed after test execution; before-finalization and after-finalization hashes are retained. This proves that finalization window, not a full-turn before/after shared-index hash claim. Primary index SHA-256 at first sample is `4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`, also matches the supplied immutable author receipt; main remains base. This sampling limitation is explicit.

Completion means review-ready advice. Morgan verdict pending; Worker 12 returns idle within existing fixed32.
