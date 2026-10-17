# Worker 12 independent meal-preference helper review

Date: 2026-10-14 (Australia/Melbourne). Same permanent LOCAL Worker 12; no additional author task or reviewer session. **Status: READY FOR MORGAN REVIEW, with two P2 shape-validation findings.** Morgan owns final verdict/integration. This is not shipped preference functionality or acceptance approval.

## Immutable scope and evidence

- Candidate: `571cb01186b19184e7423dc9d032428009e0eae9`.
- Base: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.
- Exact `git diff --binary BASE CANDIDATE` SHA-256: `94f6dba4b36f9769b19d6cf15ef51b562c85ee51473677b7029a8eb85ec26ef5`; retained as `candidate.diff`.
- Three new files, 234 added lines: helper, six focused tests and adoption documentation. No validator/UI/server modifications in candidate or reviewer work.
- Reviewer branch supplied as `feature/meal-preference-review-20261014` at base. Successful fetch at `2026-10-14T07:26:19.832312+00:00` is dispatch-supplied evidence; not repeated or independently certified here. Baseline is provisional, not release-qualified.
- Selected immutable tracked-source snapshot: `/tmp/offmenu-worker12-meal-preference-cnbqe7iy`, 17 files comprising additions, package metadata and the focused tests' local source-import closure. Exact paths/hashes in `snapshot-manifest.json`. No corpus/provider/dependency copies or installs.

## Findings

### M12-01 — P2 / medium: sparse or custom array behavior bypasses term validation

Location: candidate `public/meal-preference-model.js:18` and `:21`.

Trigger: likes or textures is `new Array(1)`. Array `some` skips holes, so validation reports no invalid term. Spreading then converts the hole into an explicit undefined value. The result violates the promised list of strings and cannot survive a normal JSON save/restore.

Actually-run reproducer (`independent-probes.mjs`):

```js
const state = setMealPreferences(createMealPreferences(scope), scope,
  {likes: new Array(1)});
JSON.stringify(state); // likes becomes [null]
resetMealPreferences(JSON.parse(JSON.stringify(state)), scope); // throws
```

Observed: returned `likes[0]` is undefined; serialized likes is `[null]`; restored state is rejected. Additional same-path probe supplies `[42]` with an overridden `.some = () => false`; the helper accepts `[42]`. Validation should not trust a caller-overridable array method to establish element type. No network or storage write was used to reproduce either behavior.

Impact: the helper can produce invalid preference state that cannot be edited/reset after serialization. This is a proposed-helper defect; current cloud storage already drops preferences, so no shipped persistence failure is claimed.

Advice: capture a dense ordinary list while checking every indexed term, reject holes and non-string elements, and avoid caller-controlled iteration/validation hooks. Add sparse and overridden-array negatives plus dense boundary positives. No fix applied.

### M12-02 — P2 / medium: spice is re-read after validation and can change to an invalid value

Location: candidate `public/meal-preference-model.js:26` and `:27`, exposed by adapter `:64`.

Trigger: preference-state `spice` is an accessor returning `mild` during validation and `safe` on the final read. `values()` reads it up to three times instead of capturing the validated scalar once. `record()` accepts such accessor-bearing objects.

Actually-run reproducer (`independent-probes.mjs`):

```js
const state = createMealPreferences(scope);
let reads = 0;
Object.defineProperty(state, 'spice', {enumerable: true,
  get() { return ++reads <= 2 ? 'mild' : 'safe'; }});
const memberWithPreferences = withMealPreferences(member, state, scope);
```

Observed: three reads occur and `memberWithPreferences.mealPreferences.spice` is `safe`, outside null/none/mild/medium/hot. This is a JavaScript caller-object boundary, not a claim that plain parsed JSON can execute a getter or that taste fields make safety decisions.

Impact: validated adapter output can violate its own spice schema and then fail future helper validation. It also executes caller accessor logic despite being described as a pure preference transformation.

Advice: capture descriptor-backed JSON data or at least capture the scalar once and return exactly what was validated; explicitly reject accessors if the public contract is plain data. Add accessor and ordinary scalar positives. No fix applied.

## Reviewer actually-run checks

- `node --test --test-isolation=none tests-web/meal-preference-model.test.mjs`: exit 0; **6/6 passed**, `focused-tests.log`.
- Independent bounded probes: exit 0; **12/12 observation assertions passed**, `independent-probes.mjs`, `.json`, `.log`. Includes the two demonstrated defects; probe pass does not waive them.
- No broad suite was executed.

Independent coverage: ordinary JSON roundtrip; null versus explicit none; dense list size/term length boundaries and preserved spelling; cross-account/cross-member edit/reset/adapter rejection; same member ID under another account cannot reuse a preference envelope; forbidden ordinary own safety/scope/version fields; invalid schema version; reset preserving all other member metadata without input mutation; peanut-allergy blocking before and after reset; unknown ingredient evidence remaining `needs-check` with automatic selection false even when liked; independent caller/output arrays.

An explicit caller-schema negative uses the actual `mealPreferences` envelope, not only top-level likes/textures/spice: `validateState` strips `member.mealPreferences` while retaining the peanut allergy. This confirms the documented persistence gate. It does not fix the validator or claim it retains all additional helper metadata.

Reproduce using the selected snapshot as cwd, with all inherited environment names beginning `GIT_` removed. Run the command above and `node /absolute/path/to/independent-probes.mjs /absolute/path/to/snapshot /absolute/path/to/artifact-directory`. All fixtures are bounded synthetic JavaScript state; there are no Git-writing fixtures, servers or repository mutations. No temporary Git repository was necessary.

## Full requirement and caller qualification still pending

The helper covers explicit taste-state creation, edit, reset and scoped attachment only. It does not authenticate scope, verify account ownership of an arbitrary member object, grant consent, infer safety, map ingredient identity, rank menus, persist, restore across account switches or provide UI. The caller must provide authenticated account/member custody; matching caller-supplied IDs is not an authorization check.

Requirement P1-03 remains incomplete: household/UI owner must add explicit controls/reset intent; state/schema owner must retain the envelope and qualify save/restore/switch-account behavior; planning/ranking owner must define any taste use. P0-07 restriction certainty, actual-package evidence and eligibility remain independent review gates. Taste likes cannot waive allergies or turn unknown ingredient evidence into verified safety. Descriptive texture terms are not clinical/IDDSI evidence.

The unchanged current `cloud/state.mjs:24` projects household member fields without preferences. `public/household-model.js:8` continues using avoid/advisors/restrictions, without taste ranking. Candidate adds no production callsite or schema integration. No deployment, complete requirement acceptance, medical/allergy certification or physical-device proof is asserted.

## Preservation and custody

Before/after evidence in `custody-before.json`, `custody-after.json` and `preservation-and-custody.json`: reviewer HEAD/branch/index, main/develop refs and common primary HEAD/index hashes remain stable. Whole-pool branch snapshots separately record any unrelated branch movements. All 28 pre-existing workspace review files retain exact paths/hashes. The two external UIUX artifact manifests were also verified against their previously saved hashes; original reports/rechecks remain intact.

Only this authorized untracked review directory was written in the checkout. No author source/branch/receipt/data, primary index/ref, persistent Git identity, configuration, dependency, server or other session was changed. Every test child environment stripped all inherited `GIT_*`; Git reads used optional-lock suppression. No new agents/worktrees/workers, publishes/PRs/merges, providers, bulk or paid operations occurred.

Review-ready advice complete; Morgan final verdict pending. Worker 12 returns idle within fixed32.
