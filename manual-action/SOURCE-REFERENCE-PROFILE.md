# SR source-reference profile preparation

This branch prepares generated fixtures for a proposed trusted
`build_source_reference_subset(packet, *, qualifications)` API. It does not
implement that API, broaden an existing builder, qualify real data, or grant
publication, runtime or Gold admission. The generated fixture identifiers and
amounts are synthetic, including those using USDA-shaped property names.

Preparation is pinned to independently reviewed but unmerged PR #112 revision
`e9ddac9fd2b50bfdfcdacde4d1b33715038d006d`. Accepted develop remains
`1c4285260b90b63c84717b638865b4298942f236` at preparation. Worker05's six frozen
files, checkout and branch stay untouched. After that PR is accepted and merged,
reconcile this branch with the actual accepted develop, implement the separately
owned builder change, and obtain exact code review and required checks before
publication or real use. Passing these preparation tests is not that review.

## Intended narrow boundary

- Reuse registered `urn:offmenu:type:FoodPreparation` and
  `urn:offmenu:type:NutrientDefinition` with source-scoped identity in the existing
  ingredients domain. Preserve native FDC, NDB and nutrient identifier lexemes,
  release, original description, editorial English term, source rows and citations.
- An independently selected identifier must bind its own resource, assertion,
  occurrence, source kind, native ID and release. A label, shared citation,
  sibling record or unqualified English field cannot supply identity authority.
- Identity and literal vocabulary remain separate from numeric observations.
  Each observation needs its own source row, metric, native numerator unit,
  source-specific basis document and source-method review. A branded serving
  binding alone does not establish an SR basis. Prototype fixture binding fields
  still require a reviewed application contract; they are not accepted schema.
- Preserve literal amount lexemes, assumed zero versus unknown derivation,
  zero source observation counts, blanks, source country/language nulls, and
  publication/archive/origin dates separately from unknown assay dates. Publisher
  location does not establish food origin. IU activity remains held without
  component-specific semantics; no mass or RAE conversion is implied.
- The initial profile excludes every relationship and comparison. It supplies no
  GTIN, universal ingredient identity, current prepared-state fit, substitute,
  recipe quantity/nutrition transfer, automatic choice or planning authority.
  Any later contextual recipe-reference association needs its own reviewed
  predicate, endpoint and consumer contract. It is not a gate for initial source
  identity or separately qualified source numeric contexts.

## Executable preparation and limits

`tests/source_reference_fixture_cases.py` makes bounded, detached synthetic
packets and prototype qualifications. Two food references share the editorial
noun Carrot while retaining different raw/cooked descriptions and leading-zero
NDB lexemes. Six source nutrient definitions retain G, MG, UG, KCAL, kJ and IU
separately. Twelve finite cases cover missing/cross-resource identity, release,
source kind, rights, English field, basis, numerator and packet profile spoofing.
These examples are not a permanent food, row or packet-size cap.

`tests/test_source_reference_fixture_contract.py` checks Common validity,
actual legacy profile isolation, in-memory DDL roundtrips, held lookup output,
native lexemes, original/context retention, boundedness and nonfinite/boolean
negative controls. The existing default profile must keep these reference
entities and observations held; current retail/recipe source APIs reject them.
No future SR API behavior is labeled passed. No corpus, source DB, cache, network,
private profile or retained Gold snapshot is opened by these tests.

The real source review's 5,005 qualified numeric contexts, 99 held IU contexts
and 43 held range contexts remain separate; all 5,147 currently retain their
persistence gate. A source review is not real source serialization or admission.
Future actual packets and qualifications require measured 4 MiB limits,
proposals 8 MiB, and the existing depth/node bounds, with no dropped originals
or silent reuse of unresolved contexts. Exact written-data review precedes any
scoped admission. Main, production, normalization and all other standing holds
remain unchanged.
