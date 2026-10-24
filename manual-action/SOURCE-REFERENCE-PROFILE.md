# SR source-reference subset

`build_source_reference_subset(packet, *, qualifications)` is a pure trusted
caller API in `gold_builder.py`. It proposes source-scoped SR food identities,
nutrient vocabulary and separately qualified source numeric observations. It
never performs I/O or admits Gold. A packet field cannot select this profile.
Runs have a distinct `source-reference-subset/1` identity and zero core
recipe-chain seeds. Publication, runtime and production rights are separate.

The implementation is a local candidate requiring independent exact code review
and normal integration checks. PR #112 was accepted as develop merge
`b626448c051245794adbe397052cc08ff3eaaa29`; this candidate must reconcile with
that accepted baseline before review or publication. Its earlier `cf8ee1fb3`
fixture-only acceptance does not accept this API or real source use.

## Own source identity

Only the existing registered `urn:offmenu:type:FoodPreparation` and
`urn:offmenu:type:NutrientDefinition` types are allowed, in the ingredients
domain. Each needs source-scoped identity, qualified record rights, scoped
citations, qualified English fields and one independently selected
`source_reference_identifier_bindings` entry. It binds its own resource,
assertion, occurrence, native ID, source kind, identifier system and release.

The sole source occurrence must name only that resource, use the corresponding
`usda-files:sr_legacy_food` or `usda-files:nutrient` source key, and retain an
original object matching its content digest. The selected identifier assertion
must match its own original JSON pointer, not another valid assertion. Food
references additionally require their source `sr_legacy_food` type and a
qualified native NDB string, retaining leading zeros. Both native `food.fdc_id`
and `sr_legacy_food.fdc_id` must equal the selected own food ID. Identity claims
must use their native ID, NDB and type fields rather than a same-valued alias.
Missing evidence holds
the affected resource; a label, shared citation or sibling cannot seed it. Full
native descriptions and separate editorial English terms remain intact.
Matching nouns do not merge raw/cooked or other source variants.

Each source resource, assertion and citation needs explicit `reuseScope` text
in addition to public-source visibility. Independent qualification and the
actual writer remain responsible for the exact permitted source purpose.
Food assertions are limited to native FDC/NDB/type fields and numeric properties
identified by a source nutrient-definition resource. Definition assertions are
limited to native nutrient ID and unit. Other properties, including GTINs, remain
held with their original payload; they cannot acquire reference-profile authority.

## Separate numeric context

Identity and literal vocabulary can qualify with no numeric observations or
with every observation held. Each numeric observation additionally requires:

- Its own `observation_basis_bindings` entry with a qualified source-reference
  disposition, food occurrence/release, exact native row digest, amount lexeme,
  nutrient definition, source unit, method and derivation ID, basis document
  digest and independent evidence pin. A legacy branded basis entry is insufficient.
- The definition's qualified own identity and original unit field. Metric and
  quantity property IDs must be that source definition's resource ID, preventing
  label-based merging into a legacy or different nutrient metric. Native G, MG,
  UG, KCAL and kJ map to g, mg, µg, kcal and kJ, with unchanged source numbers
  and exact dimensions. IU remains held.
- A finite numeric value, excluding booleans and null, equal to the native
  amount lexeme, and the same documented 100 g mass basis in claim, context
  and qualification. The full source pointer must select the row's actual
  `amount` field and resolve to that lexeme; another field with the same value
  cannot substitute. Comparable conversions are excluded.
- Exact original row fields in context, a recognized source-method category,
  and the native derivation ID. Missing derivation remains explicitly unknown.
  Context states source reporting only, no independently verified assay and no
  recipe transfer. Country and assay date remain unknown in this initial scope.

Literal zero, assumed zero, zero source observation counts, blanks, unknown
methods and publication/archive/origin dates stay distinct. Qualification does
not establish physical absence, current composition or reproduced assays. A
typed numeric claim without one qualified observation stays held, including
nested unbound numeric values. Source originals remain unchanged.

## Excluded paths and actual use

All relationships and comparisons are excluded. This creates no GTIN, global
ingredient identity, product fit, preparation producer, current-state fit,
substitute, automatic choice, cooking, safety, recipe quantity/nutrition transfer
or planning authority. Later contextual recipe-reference associations need a
separate predicate, endpoint and consumer contract. They do not gate this
initial no-edge profile.

The real source review's 5,005 qualified contexts, 99 held IU contexts and 43
held range contexts are separate from code tests and persistence. This candidate
does not serialize or admit those real rows or clear their persistence gate.
Actual packet/qualification limits remain 4 MiB, proposals 8 MiB, with the
existing depth/node limits. Measure and partition actual outputs without
losing originals. Independent source, contract, proposal and written-data review
precede scoped admission. Original snapshots stay unchanged.

## Generated verification

`tests/source_reference_fixture_cases.py` supplies generated identity-only and
numeric packets plus finite counterexamples. Factory metadata is not a test
verdict. `tests/test_gold_source_reference.py` invokes the actual new API and
tests identity, sibling isolation, source pointer/row/definition/method/unit/basis
guards, held numeric claims, profile isolation, deterministic immutable output,
schema bindings and in-memory DDL. `test_source_reference_fixture_contract.py`
preserves the preparation and legacy-profile boundaries. Tests do not open
corpus/source/cache/Gold databases or call external services. No fixed food-count
cap or real-data acceptance follows from the example packet sizes.
