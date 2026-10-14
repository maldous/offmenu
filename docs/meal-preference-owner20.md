# Worker 20 — persisted preference consumer proposal

READY FOR MORGAN REVIEW; independent review and central-owner adoption pending.
No production hook is installed, and this is not shipped household functionality.

Branch `feature/meal-preference-consumer-20-20261014` starts at fresh origin/develop
`908ca373dfc918f2e33fd5e44260879577bed5c5`. Fetch under
`/tmp/offmenu-develop-fetch.lock` began `2026-10-14T10:16:00.270399+00:00`, exit 0.
Requirement: P1-03 in `docs/recommendation-delivery-register.json`, with separate
P0-07 restriction certainty/actual-package evidence gate.

Preserved branches: TBCA candidate `ccbbabd36854dbd24f9b2bc0107ae474de76fbb2`
on `feature/dataset-brazil-tbca-20261014`; preference helper
`691f6f81cf3107a67a51641c2d7d9d9b5e85045e` on
`feature/preference-model-20261014`. Full helper pin was verified locally. Its
independent qualification remains required before adoption. This boundary does
not import or copy that helper; it independently implements the persisted envelope
contract, so independent review must check parity as well as this new candidate.
TBCA metadata is never automatic source admission. No prior untracked paths existed
at pickup; prior data and receipts remain in their original immutable branch.

## Concrete existing-source gap and actual entrypoint evidence

`cloud/state.mjs` projects members without mealPreferences. `cloud/handler.mjs`
private `/api/state` PUT uses that validator, while GET returns parsed saved data.
`public/app.js` member-form submit reconstructs members, discarding unhandled fields;
loadCloud/applySynced/loadProfile currently assign profiles without this scope check.

The focused test invokes the actual handler.fetch with a real Request and bounded
synthetic state. A fake identity response and DB object replace transport/storage;
no provider request or real write occurs. The actual PUT returns 200 and stores the
member without mealPreferences, while retaining the allergy. This is negative
production-entrypoint evidence, not proof that the proposed route delta is installed.

## Implemented boundary

`cloud/meal-preference-owner20.mjs` exports:

- validateMealPreferences(value, accountId, memberId): validates exact version-1
  envelope and exact account/member scope, dense bounded likes/textures and null,
  none, mild, medium or hot spice. Descriptor-backed capture rejects sparse/custom
  arrays and accessors without invoking hooks. Inputs are ordinary parsed JSON;
  proxies/class instances are unsupported. Source spelling remains unchanged.
- validateAccountMealState(value, accountId): runs the existing validateState and
  restores only independently validated envelopes by member identity; duplicate
  member IDs and foreign-account/member envelopes reject. Missing legacy preference
  remains absent. It is a replacement private-account validation entrypoint, not
  a shared-kitchen validator.
- updateAccountMealPreferences(value, context, action): invokes that real validator,
  checks caller account/member context and explicit consent, then edits/resets only
  taste fields for an existing member. Partial edits and selective/full reset preserve
  existing avoid/advisors/restrictions. A reset clears spice to unknown null; explicit
  none remains distinct. This returns state for the existing account save consumer.

The accountId must be server-authenticated on writes/restores; caller-supplied ID
equality is not authentication. consent:true is an explicit caller precondition,
not independently proven legal consent, session admission, or revocation fencing.
The API neither grants authority nor writes storage. It emits no suitability/safety
result, clinical texture interpretation, ranking, nutritional equivalence or origin.
Every other field remains subject to the existing validator's projection and
normalization; unsupported metadata may still be dropped by that validator. The
adapter does not claim lossless preservation of arbitrary profile/source metadata.

## Exact minimal central-owner integration delta — not applied

Worker 03 confirmed that central app.js/state validators belong to Worker 02;
03 will map this proposal, not perform preference writes. Worker 02 and Worker 04
were sent the envelope/consumer contract for account/session coordination. No
central route/schema path reservation or acceptance has been received.

After independent review, Worker 02's proposed private-state route delta is:

```diff
 // cloud/handler.mjs, alongside imports
+import {validateAccountMealState} from './meal-preference-owner20.mjs';
 // inside /api/state, after verifiedUser establishes user
-state=validateState(body.state);
+state=validateAccountMealState(body.state,user.id);
 // GET response's state expression
-state:row?JSON.parse(row.data):null
+state:row?validateAccountMealState(JSON.parse(row.data),user.id):null
```

Keep origin checks, request size, revision/CAS handling and authenticated user binding
intact. GET failures need an owner-selected recoverable response; do not rewrite
saved data on read. Keep unrelated validateState users/imports. No migration is
proposed: this envelope fits existing private JSON state; storage/schema owner must
explicitly accept that choice. Restore/account switches must reject foreign scoped
data before local storage/application, rather than migrate or silently clear it.

Worker 02's app delta must preserve the existing member's mealPreferences when
member-form submit rebuilds it, then use the consumer at an actual explicit taste
edit/reset control. Example call at that owner-selected control:

```js
// private signed-in account only; guest/demo/shared handling is an explicit gate
const next = updateAccountMealPreferences(currentState(), {
  accountId: user.id, memberId: editingMemberId, consent: confirmedTasteConsent
}, {type: 'edit', patch: {likes, textures, spice}});
// for reset: {type:'reset', fields:['likes','textures','spice']}
profile = next.profile;
persistProfile(); renderHousehold(); findMeals();
```

Validate restored/synced full account state with validateAccountMealState before
loadCloud/applySynced writes it. loadProfile needs an explicit private-account scope
policy before reading stored envelopes. Never invent account IDs for guests/demo;
never admit private preferences to kitchenProjection. Actual UI controls, consent
withdrawal/retention, conflict messaging and account-switch behavior require owner
qualification; there is no ranking delta in this slice. No central file is edited.

Worker 04's current session proposal is isolated synchronous SQLite, not an adopted
D1 transaction adapter. Its normalization-loss refusal would require this validator
as an explicitly selected dependency before preference snapshots can be admitted.
Session epoch, server subject, mutation admission, revocation, operation dedup/CAS
and lost acknowledgments remain 02/04/16 integration responsibilities. This module
does not prove those properties or bypass that gate.

## Actual focused checks and custody

With inherited GIT_* stripped, ran:
`node --test --test-isolation=none tests-web/meal-preference-owner20.test.mjs`.
Eight passed, zero failed, 40.458818 ms. Tests cover the real handler gap, real
validator wrapper and JSON roundtrip, private account/member mismatch, consent and
duplicate member rejection, selective/full reset, unchanged peanut-allergy blocking,
unknown ingredient evidence remaining needs-check, malformed shape/accessor rejection,
dense limits/scalars, and actual shared-kitchen projection/apply behavior.
Fake endpoint DB is a handler wiring probe, not D1, persistence durability or provider
authentication qualification. No servers, installs, source copies or broad tests ran.

Primary common-dir `/home/user/src/offmenu/.git`, HEAD/main
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d` and primary index SHA-256
`4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`
are checked before/after commit. Only this module, focused test and owned doc change.
Supplied controls remain unrestricted filesystem/danger-full-access, network enabled,
mandatory auto_review; separate approval policy unavailable. No settings changed.

Root must select an existing independent reviewer for the retained helper and this
exact result commit before adoption. Morgan owns final verdict. Pending owner wiring
and session qualification are explicit remaining contracts, not completion claims.
