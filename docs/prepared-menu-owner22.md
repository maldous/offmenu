# Worker 22 NORM-06 prepared-menu source adapter

## PR 8 provider-review correction (fresh exact review pending)

Previous accepted composition4d2541834cb3101ea59cb36d0762e562fa313c37 remains
immutable, but its provider review reported two P2 findings. The corrected adapter
is no longer byte-identical to the standalone pin; earlier byte-equality statements
below describe the previous composition only and do not qualify this correction.

Provider findings: https://github.com/maldous/offmenu/pull/8#discussion_r4273387129
and https://github.com/maldous/offmenu/pull/8#discussion_r4273387136.
JSON serialization made quantity comparison key-order dependent and collapsed
nonfinite numbers to null. Replaced it with bounded structural comparison of plain,
finite data, preserving null distinctions and rejecting unsupported/sparse shapes.
Conflict verdicts now require the same exact binding, scope and provenance gates as
supported verdicts; stale/unrelated conflicts remain unknown for both substitutions
and portions. These changes confer no source admission, nutrient or identity equivalence.

Before correction: eight passed/two failing regressions. After correction:
ten passed/zero failed, exit0, 48.305096ms. A fresh declared-files-only portability
run and existing13 exact-pin review/root acceptance are required. Provider review
must also be read at the corrected head. No merge attempted at the old accepted pin.
Only owner adapter/tests/docs change; no shared hook or production activation.


## Current-develop composition (15 October 2026)

Branch: feature/prepared-menu-composition22-20261015; base: 148fec8102ee64ec6801d4df96dfeb9a946ac619.
Fresh shared-lock fetch exit 0 at 2026-10-14T16:08:19.805156+00:00.
Standalone source: 2f5111e22473410fd2b72d5af473801cf499eb1b; dispatch reports existing35
scoped PASS, not root integration acceptance. Different existing13 composition review
and root acceptance remain pending before normal PR gates. No PR/merge/activation here.

All three incoming paths were absent on this develop pin; no owner file was overwritten.
Adapter SHA-256 041188b19ec5395497fe21edd5fb14677d0d7fb12941e0d88a1f8c2ea8246de9
is byte-identical to the reviewed standalone adapter. Tests/docs alone change for
portability and current-base receipts. The recipe caller dependency closure was compared
with standalone base5f5bdb6ae716cbf80fab1e174d1af2e354468ead and is unchanged.

Current tests have NO retained-corpus absolute path, hidden Git refs, network or source
acquisition dependency. A labelled synthetic source-shape fixture exercises the same
actual recipeForReview loss/default behavior; it is not passed off as retained source
content. The real existing authored public/recipes.json starter remains a published-file
fixture. Historical Cake source checks below belong only to the original standalone pin.

Declared portability files: package.json (ES module configuration),
public/prepared-menu-owner22.mjs, tests-web/prepared-menu-owner22.test.mjs,
public/recipe-review.js, public/model.js, public/record-policy.js, public/i18n.js,
public/ingredients.js, public/locale-negotiation.js, public/locales/ar.js,
public/recipes.json. No historical corpus, object alternates or Git repository is needed
by the exported focused suite. Only the three owner22 files are authored/committed.

Working-checkout focused rerun: eight passed/zero failed, exit0, 35.707154ms.
Separate declared-files-only export: eight passed/zero failed, exit0, 36.23878ms.
No .git, node_modules, historical refs, external corpus or provider access were
available/required. Export removed after execution; manifest/output hashes are
retained in the composition preservation receipt. Output SHA-256:
5b059c22b3900eab5513f0189f14b27b37a37993f20c0655d6366cd867975429.
Final head/tree/patch/private-origin exact readback and review state are external
receipts so the artifact cannot self-reference its final commit SHA.
Prior workspacea14382e, standalone2f5111e, dataset7d1905a and sourcehelperbeebcce
refs/artifacts stay intact. Main HEAD/index remain protected. Recipe production STOP,
source admission hold and whole105 acceptance remain; no shared application hook.

## Historical standalone evidence (preserved; not current portability requirements)

Candidate only; independent review and owner02 adoption remain required. Whole105
acceptance and recipe production STOP remain. No cooking, source admission or
nutrient calculation is authorized by this projection.

Owner/thread: Worker22 / 01a138fa-1d15-7701-94a1-39bdf19ffb22.
Fixed checkout: /home/user/src/offmenu-workers/worker-22.
Task branch: feature/prepared-menu-owner22-20261015.
Fresh locked origin/develop base: 5f5bdb6ae716cbf80fab1e174d1af2e354468ead; fetch exit0 at 2026-10-14T14:16:08.544011+00:00.
Prior workspace branch feature/reference-view-consumer-22-20261014, exact head a14382e4e2a9f5e85c5829759530dbbe4dff30d6, is retained.
Pre-switch status clean; excluded untracked material: none. Old dataset/helper refs
and their immutable artifacts remain intact. Main HEAD 8652b312ce7989c5e4f2d49ae765d5d8daf5841d and
index SHA-256 4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389 are protected before/after checkpoint.

## Requirements and source evidence

NORM-06 register: docs/recommendation-delivery-register.json (prepared recipe/menu/
portion and substituted-ingredient calculations). This is a bounded evidence-preserving
slice, not full NORM-06 completion. Read report01 PDF pp2–13, report02 pp6–9 and
report05 pp4–5: distinguish source quantity, edible/cooked basis, yield and serving;
yield alone supplies no retention factors; substitution needs fresh composition and
specific qualifications. Private recipe access is not redistribution authority.

Actual retained source fixture (read-only, no corpus copying):
/home/user/src/offmenu-data/world-recipes-global-checked-20261014/normalized.jsonl.gz,
first bounded JSON line SHA-256
8f5def1c8e7c6b8e6f42dfee77e2aca150f4a9240bde218a4e597265ab4a9972.
The first record is world-recipes:recipe:f5a6fefcb72aac1d15f771ee, source
https://en.wikibooks.org/wiki/Cookbook:1-2-3-4_Cake, revisionId 4608393,
CC BY-SA 4.0 / English Wikibooks contributors. Licence evidence:
https://en.wikibooks.org/wiki/Wikibooks:Copyrights. This is retained source evidence,
not a fresh source acquisition or current release acceptance. The original standalone test read only
the first line (<32KiB), checked its digest and destroyed both file/decompression streams.
The composed portable suite does not depend on this external file.

Second fixture: existing public/recipes.json first authored starter, offmenu-starter-01,
version1.0, CC0-1.0, Offmenu original content2026. An explicit test-only source-shape
bridge retains its existing ingredient quantities; declared two portions are not
measured final cooked mass and water is not assumed fully consumed.

## Concrete existing caller gap

Actual public/recipe-review.js recipeForReview(record) uses yield>0 ? yield : 1,
sets servingsUnknown, and maps ingredient amount/unit without sourceQuantity, source
ranges or preparation/basis metadata. The retained Cake yield is null and its cup
quantities remain unresolved. The focused test invokes this actual legacy caller:
its kitchen projection uses1 and drops sourceQuantity, while the new projection retains
null sourceYield plus original cup notation and source metadata. Existing needsReview
is preserved; no claim that the legacy recipe is cookable is made.

## Adapter contract and owner02 delta

New public/prepared-menu-owner22.mjs exports preparedMenuComposition(record, options).
Input is an admitted native kind=recipe record (source data.ingredients bounded to1000).
Return is a detached evidence projection containing original recipe/provenance, source
recipe version (explicit version or source revisionId; release ID is not recipe version),
yield, finalBatchYield, source serving/preparation/form/basis, original quantities,
parsed quantities/status, and untouched sourceScaling. Missing data is null; no default
portion, grams, density, edible fraction, retention, identity or nutrient result is created.
Original nutrient observations remain in original evidence; no original nutrient amount
is transferred to a replacement. NutrientComposition and compositionAfterSubstitution
are null; cookingEligible is always false.

Substitution proposals use unique lineIndex and explicit replacement ID/version/form/
basis/quantity/provenance. Default status is unknown, with selected=null. Only an injected
owner-controlled synchronous resolver can support exact culinary-function scope; its
binding includes source recipe/version, line, original and replacement identities,
forms/bases and both quantities, plus explicit evidence provenance. Source aliases are
not independently qualified by the adapter. The resolver must establish that eligibility.
Status flags in a client proposal cannot qualify it. Wrong scope/version/quantity binding,
unknown source/form/basis or missing evidence stays unknown; conflict remains conflict.
Supported culinary scope neither certifies identity/nutrition equivalence nor enables
planning/cooking. An optional exact owner-qualified portion fraction is retained as
qualifiedFraction; it does not scale amounts or infer prepared mass/nutrients.

Exact minimal owner02 integration delta at native record review selection (after its
rights/account-scope admission gate, BEFORE lossy kitchen projection):

```js
import {preparedMenuComposition} from './prepared-menu-owner22.mjs';
const preparedEvidence = preparedMenuComposition(admittedNativeRecipe, {
  serving: proposedServing,
  substitutions: proposedSubstitutions,
  resolveScope: ownerQualifiedPreparedScopeResolver,
});
// Return/display this separately alongside recipeForReview(admittedNativeRecipe).
// Preserve existing needsReview and the recipe production STOP; do not pass this
// projection to cookMeal or infer servings from null sourceYield.
```

Owner02 owns the shared application/caller hook, snapshot/version invalidation and
admission checks. No shared app, handler, schema or basket file is edited here.
Worker15 quantity/importer and Worker19 attendance/cooking owners were contacted;
this projection does not parse measures, allocate stock, compute attendance, create
plans, scale ingredient quantities, perform cooking or record intake. Current coordination
responses remain pending; no ownership release is inferred.

## Checks, review and preservation

Focused command: node --test --test-concurrency=1 tests-web/prepared-menu-owner22.test.mjs.
Eight passed, zero failed, exit0, 44.783269ms. Actual retained fixture and actual legacy
caller are exercised; additional scope tests are labelled synthetic-only and are not
producer/admission qualification. No provider calls, servers, installs, broad suites,
raw corpus commits or shared model changes. Independent exact-pin review is pending
root-selected existing reviewer. No unreviewed merge or production action.

GitHub connector get_repo verified maldous/offmenu visibility=private. gh CLI auth is
unavailable; no credentials/settings changed. Existing SSH Git workflow is eligible
for nonforced checkpoint backup. Local checkpoint, private-origin backup exact SHA,
independent reviewer/verdict and develop merge are separate states. Final checkpoint
and independent ls-remote receipt will be reported externally (self SHA is not embedded).
Only this task branch is backed up; older branch remote backups are not inferred.

Supplied controls unchanged: unrestricted filesystem/danger-full-access, network enabled,
mandatory auto_review; separate approval policy unavailable. Routine preservation follows
/home/user/Documents/Codex/2026-10-14/task-2/offmenu-preservation-workflow.md. Safe explicit
file list: public/prepared-menu-owner22.mjs, tests-web/prepared-menu-owner22.test.mjs,
docs/prepared-menu-owner22.md. Recovery: checkout this branch/pin and rerun the focused
checks against the retained checksum fixture. No new worker/coordinator/session.

Correction declared-files export: 10 passed/0 failed, 39.483177ms; output SHA-256
a847da300f2714d908df8a80ab64dc8afc473289eca327ff98cdb2c3f40be648.
