# Conditional arithmetic from selected product labels

`gold_recipe_label_scenario.mjs` is a pure, private-local adapter around the
existing `public/basket-model.js` calculator (`basket/1.1`). It does not add a
calculator, database reader, schema, endpoint or product-selection mechanism.
The existing barcode consumer and generated-menu outputs remain unchanged.

The caller must independently select and verify the admitted snapshot, establish
the permitted source operation, and supply its qualified recipe quantities,
source-product observations, definitions, supports and citation bodies. Matching
hash strings or accepted-looking input do not establish admission. This function
evaluates the supplied record bindings and arithmetic; it cannot verify source
files, independently review a label, or clear an existing hold.

```js
import {evaluateLabelScenario} from './gold_recipe_label_scenario.mjs';
const result = evaluateLabelScenario(input, ownerSelectedSnapshot);
```

The input version is `offmenu.source-label-input-scenario/1`. Its `snapshot` must
exactly match the separately supplied `databaseSha256` and `admissionSha256`.
`recipe` specifies an exact `recipe-actions:<64-hex>` run, `repeatCount: 1` and the
complete unique set of ingredient IDs. Each `lines[]` item has an ingredient ID,
positive `massG`, `massUnit: 'g'` and its admitted exact, factor-one gram allocation
under `quantityEvidence`. That evidence must include `slotName`, the complete
supplied native `ingredientRecord`, and `ingredientSupport`. The record's exact
run/action/slot/source-ingredient ID and ingredient entity ID must agree with the
line (`ingredientEntityId`) and its evidence. Parsed `allocation_json` must match
the supplied factor-one allocation, whose normalized dimension is explicitly
`mass`, whose original/normalized-original unit and value agree, and whose exact
amount agrees with input grams. Each quantity citation must have exactly one
matching run/action/slot support with the same nonempty Unicode evidence as the
record. Source pointer, offsets and codepoint length must be coherent; malformed,
missing, duplicate or foreign support holds that line's contributions while
healthy siblings remain available. These checks bind supplied records only: they
do not open source files, authenticate evidence or establish actual product
choice. Native JSON fields are bounded at 64 KiB and 64 evidence spans.

Later references to the same ingredient are not new
inputs; duplicate or omitted ingredient IDs fail the entire request.

Each line explicitly supplies `selection.origin: 'GENERATED'`, its exact source
`productId`, a `variantAssumption` and a `massStateAssumption`. These are declared
hypothetical choices. A generic product-to-class-to-mention path establishes no
actual product choice, brand identity or variant equivalence. `product` must be a
verified public source `barcode-product`, with its own citations and rights.
Source-reference food preparations and ingredient-class nutrient records cannot
contribute. No lookup, first match, fallback or SR transfer occurs here.

`observations[]` retain the source observation ID, entity/metric IDs, state,
`original` numeric/unit/basis payload, complete `context`, assertion `claim` and
field `supportRecords`. Only one qualifying observation per line/metric is used;
duplicates are ambiguous, and no winner is chosen. The claim must bind the exact
product and metric. Native units must match the selected definition without
conversion; the original and contextual basis must agree on 100 g. This scoped
adapter supports mass units g/mg/µg and energy kcal/kJ, and the admitted publisher
label derivations LCCS/LCCD. Unknown values, units, methods or bindings are held.
It retains label rounding and method uncertainty; publisher calculations are not
independent analytical measurements.

`metrics[]` supply unique explicit nutrient IDs, names, units, dimensions,
verified states, definition citation IDs and definition supports. Every cited
assertion and definition needs its own matching support, nonempty license and
attribution. Shape checks of persisted evidence hashes are not artifact-content
review. `citations` preserves complete bodies, including distinct definition
rights. `admissionLimits` and all other supplied source metadata survive in
`inputs`; the adapter interprets none of these fields as new source permission.

The adapter uses the existing calculator for each line's contribution and the
combined input arithmetic. For each requested nutrient, `contributions` show
source values, input grams, observation IDs, formula, value or explicit hold
reasons. `conditionalInputSum` is nonnull only when all required ingredients
contribute. `knownSubtotal` is partial when some contribute and null when none do.
A source-recorded zero remains a supported zero; missing observations never
become zero. Coverage is explicitly over the supplied ingredient inputs and
requested definitions, not a complete nutritional profile. Results use the
existing JavaScript floating-point arithmetic; displayed precision does not
improve source-label accuracy.

`ACTUAL_RECIPE_COMPOSITION` mode is always held by this evaluator. It has no
contract admitting observed product/variant bindings. Generated selections never
become actual choice. Both modes retain null `actualRecipeNutrition`, `yieldG`,
`servings`, `perServing` and `per100gPreparedFood`. The calculator's basket mass,
density, rank and serving projections are not exposed: 60 g plus 30 g of inputs
does not establish 90 g of prepared output. Cooking losses, retention, storage,
soup/sauce application, dietary adequacy, safety and automatic planning remain
outside this calculation. Previously held source recipe nutrition stays held.

Inputs are capped at eight distinct ingredients, 64 explicit metrics, 64
observations per line, 256 citation bodies, 512 KiB, depth20 and 20,000 JSON nodes.
Nutrient values and input gram amounts are capped at 1,000,000; outputs have a
1 MiB cap. Errors fail the call without partial output. Qualification gaps retain
explicit held contributions and healthy siblings. The function performs no I/O,
mutates no inputs and returns a detached copy of the supplied provenance.

Generated tests cover arithmetic, actual/absent/foreign selection, missing versus
recorded zero, complete once-only ingredient coverage, quantities, product types,
source-reference rejection, exact native record/support/citation/Unicode/mass
bindings, context, units, definitions, methods, citation rights,
ambiguous observations, snapshot selection and bounds:

```sh
node --test tests-web/gold-recipe-label-scenario.test.mjs
```

Actual demonstrations remain in the worker's private retained evidence packet.
Independent Worker56 review and Worker00 integration are separate requirements.
No country completion, source admission, normalization or runtime activation is
implied by a conditional arithmetic result.
