# Worker26 recall consumer handoff

Pickup root: 01a137cf-2242-761d-8fd7-6e6fc5658013. Unique branch feature/recall-binding-consumer-26-20261014.
Locked fresh origin/develop fetch at 2026-10-14T10:16:55Z, exit0, base908ca373dfc918f2e33fd5e44260879577bed5c5.
Prior dataset branch feature/dataset-pacific-pndb-20261014 remains pinned at4c17ad172a6fc3067e5e94b07e9be7023d5377bf, with CSV/receipt/note preserved as tracked blobs there. Prior checkout was clean with no untracked entries; no files were deleted/cleaned/reset. Normal branch switch selects the new baseline; retrieve prior artifacts from their retained branch. Recall helper branch/pin643c130eed6d4d64a7e755d6c233128fa978aaa8 verified unchanged. No extra worker/worktree.

## Delivered boundary

public/recall-binding-owner26.mjs exports createRecallConsumer and its callable decideInventoryRecalls entrypoint. It imports actual existing rights admission rather than duplicating source permissions. Inject the retained scope evaluator after independent review; it is absent from current develop and is not copied/adopted here. The factory dependency gate requires the exact retained pin and independentlyReviewed acknowledgement; this acknowledgement is a trusted integration precondition, not proof of a review by itself.

Owner-reviewed plain JSON envelopes carry notice, sourceVersion, recordVersion, policy, assertion and review. Review must bind sourceId/sourceVersion/recordId/recordVersion/noticeId/productId/productVersion/lotId, accepted status, complete scope, no unresolved conflicts, checkedAt and freshUntil. Policies/assertions bind the same source edition/record and permit public display; active, verified, explicitly nonpersonal assertions only. Current evaluation and review times admit UTC Z with at most millisecond precision. Source authentication and matching review are upstream owner duties, not fabricated from a CSV, feed label or display permission.

Inventory projections require actual id, productId and productVersion plus barcode/market/lot/date/label fields used by the helper. Missing identities produce needs-review. Do not invent product versions from barcode, generic names or catalog coverage. Source/record corrections invalidate review through exact version mismatch. An accepted matched current recall yields recall-match-review with source evidence; exclusion yields outside-this-notice only. Mixed unknowns retain review decisions. No notice yields no-applicable-notice-established, safety unknown, exhaustiveCoverage false, automaticSelection false. No result is a food safety assurance or selection permit.

## Exact minimal caller-owner delta (not applied)

Worker03 owns browser integration/reservation; Worker02 owns cloud handler/schema paths. No production path reservation was supplied. Existing setupData in public/data-ui.js has getData returning profile/inventory, signed-user/session refresh and generation guards. public/app.js passes lots there. Central app/handler/model paths are unchanged.

After independent helper and adapter review, caller owner must adopt the retained helper in its separately reserved integration and add these imports to the selected reserved consumer module:

```js
import {createRecallConsumer, RECALL_HELPER_PIN} from './recall-binding-owner26.mjs';
import {evaluateRecallScope} from './recall-scope-model.js';
const decideInventoryRecalls = createRecallConsumer({
  evaluateScope: evaluateRecallScope,
  helperPin: RECALL_HELPER_PIN,
  independentlyReviewed: true, // only after exact-pin review verdict
});
```

In the owner-reserved read-only notice rendering action, after trusted source admission and inventory projection:

```js
const decisions = decideInventoryRecalls({
  lots: reviewedInventoryProjection,
  notices: admittedRecallEnvelopes,
  asOf: new Date().toISOString(),
});
```

Render decisions as review/source-link information. Preserve caller generation checks before/after any asynchronous source load; clear outputs on account/profile/session change. Do not retain private inventory in a module singleton or publish it with source data. This adapter itself has no persistence/network/session state. Worker04 must review any future account-bound caching/acknowledgement/persistence; Worker02 must reserve and implement schema/endpoint changes if trusted product-version and lot bindings are not already available. Current app inventory read alone does not establish those projections. Notice conflicts and raw-scope completeness remain Dataset01 authority. A caller must not pass arbitrary CSV metadata as admitted envelopes.

## Validation and remaining gates

Six focused tests passed via node --test tests-web/recall-binding-owner26.test.mjs. Tests exercise the actual exported consumer entrypoint and actual rights function, with synthetic .invalid source references and in-memory execution of the exact retained Git helper blob. Only its relative evidence-model import is redirected to the current checkout for execution; original helper bytes/branch remain untouched. Git read subprocess strips inherited GIT_*; no Git-writing fixtures, corpus copies or provider calls. Tests set the independent-review acknowledgement synthetically to exercise behavior, not to assert real acceptance.

Coverage: source/record/product/lot binding mismatches, withdrawn/personal/denied assertions, stale/incomplete/conflicting review, missing market, historical evidence, excess timestamp precision, empty/excluded notices, mixed unresolved notices and independent output snapshots. This is adapter entrypoint evidence, not actual UI/cloud caller acceptance. Independent retained-helper and new-candidate review, Worker03 production-map/reservation, Worker02/04 projection/state acceptance and actual caller exercise remain outstanding. No shipped/adopted/release claim. No shared develop changes, push, PR, production or settings changes. Mandatory auto_review and supplied unrestricted filesystem/network controls preserved; separate approval policy unavailable.
