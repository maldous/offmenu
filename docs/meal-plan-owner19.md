# Worker 19 meal-plan consumer candidate

READY FOR MORGAN REVIEW. Not adopted, integrated, shipped or release-certified.

## Independent review correction

Worker17 reviewed exact adapter pin 460ee375bf1da2b5a9a4032a3451cf44b9bdecf1
and retained helper 38dcb3f8a542a0c8d3f1d3341c1e4a4a779a1d18. Existing focused
checks passed independently (adapter 9/9, helper 6/6), but review verdict was changes
required before adoption. The adapter could generate a cooked inventory lot whose
ID collided with unrelated stock. A bounded regression reproduced the finding:
before correction, 9 tests passed and the new collision test failed. The adapter
now checks the generated cooked-lot identity before calling cookMeal and validates
unique inventory output before an owner commit. After correction, all 10 tests pass.
The original adapter commit remains the correction's parent. Worker17 exact-pin
recheck of this correction is requested; no adoption is claimed.

The helper's hole-only memberIds array could bypass attendance bounds. Its old
pin remains preserved and unadopted; this adapter's descriptor capture already
rejects sparse arrays, covered by its tests. No retained-helper file was changed
in this adapter-only correction. Helper correction/review remains a separate gate.

## Pickup and scope

Same permanent Worker 19, host foo, cwd /home/user/src/offmenu-workers/worker-19,
thread 01a138f8-5f61-78b0-a899-7ec31a611daa. Fresh fetch under
/tmp/offmenu-develop-fetch.lock exited 0 at 2026-10-14T10:16:19.952123+00:00.
Branch feature/meal-plan-consumer-19-20261014; exact base
908ca373dfc918f2e33fd5e44260879577bed5c5.

Retained helper pin verified as a commit:
38dcb3f8a542a0c8d3f1d3341c1e4a4a779a1d18. It remains on its original branch;
the new module does not import or adopt it. Independent review of both the
helper and this candidate was requested from setup/root before adoption. This
worker's source inspection and tests are implementation evidence, not independent
review. Week-wide attendance/equipment/lunchbox template approval is still the
retained helper's separate scope; this adapter handles individual editable copies
and actual cooking lifecycle. Do not conflate a copy proposal with approval.

Dataset branch feature/dataset-germany-bls-20261014 at
9e077eebec180b2f200e617ce723af2449de6a33 remains intact. Its CSV/receipt/note
stay in that immutable branch; no corpus copies or metadata admission occurred.
Pickup tracked/staged/untracked state was clean and there were no symlinks.

Supplied controls: unrestricted filesystem, danger-full-access sandbox, network
enabled, mandatory reviewer auto_review. Separate approval policy unavailable.
CODEX_PERMISSION_PROFILE was previously read as unset; no named profile inferred.
No settings changed. All task Git writes/custody subprocesses strip inherited GIT_*;
only command-scoped Worker 19 bot attribution is supplied for the result commit.

## Concrete source gap and implementation

Requirements: P1-02 reusable planning, P0-06 cooking/serving/leftovers and P0-05
durable state, in docs/recommendation-delivery-register.json. Existing source:

- public/app.js renderPlan (line 145) looks up profile.plan recipe/cookBatchId;
  setupJourney wiring (line 173) persists a mutated profile and separate inventory.
- public/journey-ui.js cook-confirm mutates selectedPlan/profile.batches and only
  links a plan on nonduplicate cooking. serve-form appends r.log even when the
  underlying serveBatch returns duplicate:true with no log. Undo mutates batches
  and deletes live plan links.
- public/cooking-model.js already owns actual allocations, cooking, serving and
  undo rules; the new adapter calls these functions and does not duplicate them.
- cloud/state.mjs projects known plan fields and validateBatches does not retain
  the new sourceEvidence; no owner-controlled schema change has been made.

public/meal-plan-owner19.mjs captures bounded plain data without invoking
accessors, rejects sparse/custom arrays and nonfinite values, and returns a new
whole state. Individual copy/edit actions retain original recipe quantities,
units, uncertainty, licence/provenance and original plan evidence; they do not
rewrite recipes, scale publisher quantities, admit source data or claim safety.
Copies get explicit fresh IDs and clear their active cookBatchId. Historical
cookBatchId within immutable sourceEvidence remains an archival source fact.

Cooking deducts raw stock through the existing cookMeal and records source recipe
evidence in the new batch. Replay repairs a missing plan link without deduction;
stale stock/mismatched active batches and reused undone identities reject. Serving
uses serveBatch, keeps unknown completion unknown, and does not append duplicate
or undefined history. Changed replay payloads reject. Undo uses undoCook and clears
live links in a new state; served batches remain protected by existing rules.
Cooked plans cannot be edited until undone; copying them leaves the original intact.

## Actual entrypoint and remaining integration contract

`createMealPlanOwner19({read,commit,scope,clock})` returns an async UI action
entrypoint. It captures intent before awaiting state, serializes its UI operations,
checks account scope before/after read and before commit, and passes
`{accountId,expectedRevision,state}` to one owner-controlled commit. read returns
`{accountId,revision,state,preservesPlanEvidence:true}`. Clock is explicitly
injected; identities are supplied in actions. No provider, transport, storage,
purchase or new session is created by this module.

Commit must enforce the account/session authority and revision at the actual write,
atomically persist profile/inventory/history, and return `{committed:true}` only
after the matching durable acknowledgment. A scope string is not authentication.
Local snapshots, offline queue state and server durable state must remain distinct;
do not claim a queued local write is a server acknowledgment. Unknown commit outcome
requires the owner queue's reconciliation, not an automatic fresh action/ID.

Worker03 confirmed reservations: docs/production-integration-owner03.json,
public/integration-owner03.mjs, its tests and a narrow insights hook. It will map
this candidate but owns no plan edit hooks. Worker02 alone owns central app.js
and shared validators. No such file was edited. Worker04 is building its isolated
session-state protocol; the bridge requires its reviewed final pin plus Worker16
operation/retry contract. Mutable owner04 bytes were not imported or treated as
qualified evidence. Root was asked to select an existing independent reviewer.

Exact minimal adoption delta, to be applied by the reserved owners after review:

1. Owner02 app.js: import createMealPlanOwner19 from ./meal-plan-owner19.mjs;
   instantiate once with the selected account-bound read/commit adapter and clock.
   A read snapshot must include inventory/products/recipes/profile/selections and
   the owner revision; use authenticated scope including the session binding at
   the commit boundary. Do not fabricate preservesPlanEvidence:true.
2. Owner02 app.js setupJourney: add a `planAction` callback invoking the entrypoint.
   Owner-reserved journey-ui.js cook-confirm calls
   `await planAction({type:'cook',planId:selectedPlan.id,date:cookDate,
   reviewed:confirmedForThisRevision,mutationId:stableOperationId})`; remove the
   direct selectedPlan/profile/batches/inventory mutations for planned meals.
   Serve calls `{type:'serve',planId:batch.planId,eventId:stableEventId,date,
   portions,completion,remainder,memberId}`; undo calls `{type:'undo',planId}`.
   Keep unplanned cooking on its existing path unless separately reserved/reviewed.
   Return acknowledged owner state to the caller and refresh both batches and plan.
3. Owner02 renderPlan: Copy opens an editable target proposal using
   `{type:'copy',planId,newPlanId,changes:{date,slot,servings,memberIds,adjustments}}`;
   Edit uses `{type:'edit',planId,changes}`. Both return requiresReview:true.
   The owner UI must review current target attendance, equipment, portability,
   source rights, recipe quantities and actual packages before later cooking.
   No equivalent safety or nutrient claims follow from unknown source metadata.
4. Owner02 validators: retain a bounded, validated account-private sourceEvidence
   structure on plan and batches, preserving source lexemes/units/qualifiers and
   publisher rights fields. Never simply spread arbitrary client objects into
   persisted authorization state. Whole-state capture here limits arrays to 10,000,
   depth to 30, nodes to 200,000, total string characters to 2,000,000; larger
   catalogues need an owner-designed boundary without dropping unrelated state.
5. Owner02 sharing/sync projection: current kitchenProjection spreads nested plan
   metadata; sourceEvidence.sourcePlan contains private memberIds. Omit the entire
   account-private sourceEvidence from shared plan/batch projections before any
   adoption (or separately qualify consent/rights and an explicit public projection).
   A top-level memberIds reset alone is insufficient. This privacy gap is a source
   trace finding; no shared caller was changed.
6. Owner04/16 bridge: map expectedRevision to reviewed expectedVersion and stable
   operationId; map a committed, acknowledged response with exact authenticated
   subject/session/realm/epoch/resource, operation/digest/revision binding to
   committed:true. Denials, conflict, STATE_NORMALIZATION_REQUIRED, mismatched or
   lost acknowledgment must not produce a successful adapter result. Owner04's
   SQLite-only slice does not qualify a D1 route; handler/schema/transport remain
   owner02 integration gates.

## Verification and custody

Actual focused command: `node --test tests-web/meal-plan-owner19.test.mjs`.
Initial eight tests passed; after asynchronous intent-capture coverage, final nine
passed, zero failed. Two focused runs, no broad suites/installs/servers/Actions.
Tests invoke the actual cooking-model cook/serve/undo and existing planSummary;
the exported async entrypoint is exercised with a revision-bound commit harness.
The production app/journey UI has not been wired or browser-exercised. The real
cloud validateState test proves the current sourceEvidence loss, explicitly gating
adoption. Fixtures are small synthetic objects; no Git-writing fixtures or corpora.

Shared primary HEAD/index/main-ref SHA-256 custody baselines:

- HEAD: 28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80
- index: 4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389
- main: 4b9c51c3f104ae9af331274450d8d1fa2cf3b06df913f45339abc4a5536e408e

The result command asserts these and retained dataset/helper refs, as well as the
dataset's immutable blob hashes, before and after committing only this module,
focused test and note. Actual result commit/diff and assertion outcome are reported
with the handoff. No merge/push/deploy or independent acceptance is claimed.
