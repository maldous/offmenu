# Worker 20 — persisted preference consumer proposal

Historical standalone acceptance record follows. See the 18 October 2026
current-source candidate section below for the bounded private-state integration.
Independent review and publication are pending; no production deployment occurred.

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

## Standalone composition candidate — 15 October 2026

Current branch: `feature/meal-preference-standalone-integration-20-20261015`.
Fresh locked develop fetch exit 0 at `2026-10-14T14:30:29.514832+00:00`, base
`5f5bdb6ae716cbf80fab1e174d1af2e354468ead`. Only this owned doc, the cloud module
and focused test are carried from original candidate `8e07cffbb2889729ca7195a76757279b29a19e11`.
Original branch, completed TBCA branch and all local review artifacts remain retained.

Root confirms Worker13 scoped PASS on the original (8 author checks plus 6 independent
probe groups) and selects DECLARED STANDALONE adapter code scope only. That receipt
is dispatch-supplied, not a generic adoption approval. Different-reviewer fresh
composition qualification remains required before PR/eligible develop progression.
No PR, merge, handler/state/UI activation or production action is part of this turn.

Full relative-import closure of module and focused test was rebound against the
original exact pin: all captured file hashes match, including handler/state, source
normalizers, catalogue and sync/household dependencies. No changed dependency was
found in that closure. Node/runtime/provider/D1 hermeticity is not established by
source hashes. Captured bindings are retained in the local preservation packet.
Fresh inherited-GIT_*-stripped focused run: eight passed, zero failed, 45.127864 ms.
Actual handler negative still proves preference loss, so adoption remains held.
Below is the retained original implementation contract and historical pickup evidence.

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



## Current-source private state candidate — 18 October 2026

Baseline: `72a8a74919773238e402b2a6f5a089bf8a4cefa2`. Recovered this document,
the adapter and focused tests before changes. Retrieved all 46 files in the
focused test's static relative-import closure at that exact immutable pin.
The historical eight tests passed, including its negative actual-handler PUT
probe: HTTP 200 with the preference envelope silently omitted from stored JSON.
That is now fresh synthetic evidence, not merely a historical reported gap.

The offline candidate selects the existing authenticated `user.id` for private
PUT validation through `validateAccountMealState`. No identity, session mapping,
origin, request-size, revision/CAS, database schema or shared kitchen path changes.
GET uses `validateStoredAccountMealPreferences` as a nonprojecting check: account,
member, envelope and duplicate identity validation when preferences exist, while
returning the exact parsed saved state. It does not run the generic state projector,
normalize legacy metadata or perform writes. A failed stored preference check
returns 409 with `invalid_saved_meal_preferences`, no state body, and a message to
keep the local copy/contact support. It does not silently clear or repair data.
Legacy states without preferences retain their prior read behavior.

Focused actual-handler tests now cover initial and revision-update preservation,
GET exact metadata retention, legacy/empty reads, foreign account/member and
malformed envelope rejection, no-write reads, duplicate identities, authentication,
origin, revision and CAS gates, alongside the retained adapter/allergy/kitchen
checks. Candidate: 14 passed, zero failed. The same regression suite against the
unchanged baseline fails four groups and passes ten; the retained historical suite
passes eight. Test transport and storage are synthetic identity responses and a
fake DB, never real accounts, provider calls, or persisted user data. These checks
are wiring evidence, not native D1 durability or provider-authentication evidence.

This candidate does not ship household preference functionality end to end. The
actual UI editor still reconstructs members and has no adopted taste controls;
client restore/account-switch custody, explicit consent withdrawal/retention,
session integration and whole-product acceptance remain separate open work.
No preference ranking or safety/clinical inference is introduced. Existing
allergy/restriction behavior remains independently tested. No production action,
source permission change, migration, or runtime diagnostic occurred.
