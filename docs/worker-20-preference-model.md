# Worker 20 — explicit meal preferences

Status: READY FOR MORGAN REVIEW after the focused checks below pass. This is an
independent module proposal, not an integrated feature or release certification.

Requirement: [P1-03, Household likes, texture/spice preferences and reset](recommendation-delivery-register.json),
dependent on P0-07, Restriction certainty and actual-package evidence. Both entries
are unassessed at the supplied base; Worker 14's draft is not acceptance evidence.

Branch: `feature/preference-model-20261014`. Exact base:
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.
Dispatch supplies a successful origin/develop fetch at
`2026-10-14T06:40:44.146472+00:00`; local origin/develop and HEAD matched that SHA.
Baseline verdict: PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE.

## Existing-source gap and bounded negative example

`public/household-model.js` memberSuitability handles avoid/advisors/restrictions;
rankedMenus scores coverage, suitability and advisor nutrients. Neither reads
likes, textures or spice. `public/app.js` openMember/onsubmit (lines 152–154)
has no taste fields or taste reset. `cloud/state.mjs` member projection (line 24)
does not retain taste fields. Existing household/journey tests cover dislikes,
restrictions and package uncertainty, not this lifecycle.

Executed a single synthetic member through validateState before implementation:
likes `['rice']`, textures `['crunchy']`, spice `'mild'` were all returned as
undefined, while `{type:'allergy',term:'peanut'}` remained. The focused test retains
this negative example as evidence of the pending schema integration, not a claim
that the existing validator is fixed.

## Independent slice and adoption contract

`public/meal-preference-model.js` exports createMealPreferences,
setMealPreferences, resetMealPreferences and withMealPreferences. It holds only
explicit taste terms, bounded to 32 terms per list and 100 characters per term.
Spice is null (unknown/unset), none, mild, medium or hot. Descriptive texture terms
are taste inputs, never clinical texture/IDDSI evidence. Terms retain their spelling;
no ingredient identity, safety, nutrient or quantity mapping occurs.

Each state carries exact account/member identifiers. Edits, selective/full reset,
and the member adapter reject mismatched scope. This equality check does not
authenticate or authorize an account. The caller supplies its authenticated scope
after consent and access checks. Functions have no clock, storage, transport,
randomness or side effects; no injected dependencies are needed.

Input contract: records (including the member's preserved metadata) must contain
acyclic plain JSON data: ordinary or null-prototype records, dense ordinary arrays,
strings, booleans, finite numbers and null. Capture uses own data descriptors;
accessors, symbols, hidden fields, custom array properties/iteration hooks,
undefined, functions, class instances and cycles are rejected. A missing field is
different from a present undefined value. Proxies are unsupported: reflection may
execute proxy traps, so callers must supply ordinary data, not proxy objects.
No getter or custom array method is used to establish the supported input shape.

An existing household caller could adopt this pattern after its owner approves:

```js
const scope = {accountId: authenticatedUser.id, memberId: member.id};
const initial = member.mealPreferences ?? createMealPreferences(scope);
const edited = setMealPreferences(initial, scope, {
  likes: ['rice'], textures: ['crunchy'], spice: 'mild'
});
const nextMember = withMealPreferences(member, edited, scope);
const resetTaste = withMealPreferences(nextMember,
  resetMealPreferences(edited, scope), scope);
// Owner persists only after account/consent checks and schema support.
// P0-07 independently controls restriction certainty and selection eligibility.
```

Owner-controlled integration dependencies: household/UI owner adds controls and
explicit reset intent; private-state/schema owner retains the scoped envelope and
handles restore/switch-account conflicts; P0-07 owner/reviewer qualifies restrictions.
The adapter preserves all other member fields, including avoid, advisors,
restrictions, uncertainty, consent, source identities, quantities and rights.
No allergy certainty or selection eligibility is emitted. Likes cannot override
restrictions. Do not store this via the current cloud validator: it drops the new
envelope too. No recipe ranking, inference from feedback, persistence, UI, schema,
provider access or source/data modification is included.

## Focused validation and custody

Run `node --test --test-isolation=none tests-web/meal-preference-model.test.mjs`.
Six bounded tests cover existing-source loss, partial edits/unknown versus none,
selective/idempotent reset, scope/version rejection, invalid/unbounded/safety-field
inputs, preserved metadata and unchanged peanut-allergy blocking before/after reset.
Actual run: six passed, zero failed; reported duration 23.346735 ms. The negative
example and test runner used two Node processes total (test isolation disabled).
Only synthetic fixtures are used; no Git-writing fixtures or disposable repos.

Before/after assertions verify common-dir `/home/user/src/offmenu/.git`, primary
checkout HEAD and main ref at the base SHA, primary branch `main`, and primary
index SHA-256 `4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`.
The result commit changes only the three reserved new files. Worker 20's own
branch/ref/index necessarily change when committing; shared Git object storage
receives that commit. No primary ref/index or other owner's files are changed.

Focused checks do not establish shipping, integration, medical safety, allergy
certainty, complete requirement acceptance or release qualification. Morgan review
and the owner-controlled dependencies remain required.

## Worker 12 review follow-through — M12-01 and M12-02

Original immutable candidate `571cb01186b19184e7423dc9d032428009e0eae9`
remains in this branch's history. Both P2 findings were reproduced before edits:
sparse likes returned undefined and serialized to `[null]`; `[42]` with overridden
some was accepted; the spice accessor was read three times and returned invalid
`safe` through the adapter. These are helper shape defects, not shipped storage or
safety decisions.

The new change captures plain JSON data via descriptors before validating state,
patch, scope, reset fields and member metadata. Dense arrays are captured by index,
rejecting holes/custom properties and never using caller iteration hooks. Spice is
captured once as a scalar and the output returns precisely that validated scalar.
Nested member accessors are rejected before the adapter copies metadata. The
plain-data contract above narrows unsupported caller objects explicitly.

Actual post-fix focused run: `node --test --test-isolation=none
tests-web/meal-preference-model.test.mjs`, nine passed, zero failed, 27.066366 ms.
Three added tests cover sparse/custom-some/custom-iterator/index-getter rejection,
state/patch/scope/nested-member accessor rejection with zero getter calls, and
dense 32-by-100-character list positives plus every ordinary spice value through
JSON restore/reset. Original six tests still pass. Test-runner environment stripped
all inherited `GIT_*`, with no test children spawned; fixtures write no Git state.
`git diff --check` passed. Only the helper, focused test and this owned usage doc
change. Existing UI/schema/ranking and P0-07 gates remain pending and unchanged.

This correction is READY FOR MORGAN REVIEW; Worker 12 targeted recheck must use
the new exact commit pin. No acceptance or integration verdict is asserted.
