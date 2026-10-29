# Offline reference candidate adapters

These adapters produce deterministic review candidates, not production admissions.
They do not read the clock, fetch anything, run historical code, write files, or
activate a source. The execution/acceptance owner must verify exact input pins,
source release, custody, expected records, licence notices and operation-specific
rights before using any candidate. `authorizedOperations` stays empty and
`rightsEvidenceStatus` requires review even when a known licence is present.

## Interfaces

`normalize_reference(source_id, release_id, payload: bytes, acquired_at=...)`
returns records. `candidate_bytes(records)` serializes `candidate.jsonl` singleton
packets. `candidate_manifest(...)` binds candidate bytes to explicit input hashes,
acquisition timestamp and externally reviewed rights/scope evidence digests. It
is a descriptor, not a verifier of the underlying files or evidence. Input size
is bounded to 64 MiB; eager parsing occurs in memory, not streaming. Emitted
canonical output is bounded to 64 MiB, 8 MiB per record and 100,000 records.
Execution process memory isolation remains the caller's responsibility. Large retained releases stay in Foo.

The explicit output schema is `schemas/reference-candidate.schema.json`.

## Supported retained input contracts

- Wikidata `2026-10-13-direct-types`: SPARQL result JSON object with
  `results.bindings` array, each with `entity` and `type` URI binding objects.
  Only the three historically queried direct business types are supported.
  Groups same-entity bindings while retaining every original binding and index.
  No remote label/country lookup or ownership/market inference occurs.
- Wikibooks `2026-10-13-live`: retained `revisions-N.json` page array, positive
  page IDs, Cookbook titles, exactly one revision with positive revision ID and
  `slots.main.content`. Whole page objects and exact content strings survive.
  Outputs recipe-discovery-reference; not quantity-resolved planning recipes.
- FoodOn `2026-09-20`: UTF-8 RDF/XML root with named own-namespace FOODON classes.
  Exact direct-child XML bytes, nested expressions, attributes and namespace
  declarations survive. Imported classes remain outside this adapter's scope.
  No food identity equivalence or ontology reasoning occurs. DTD/entities reject.
- QUDT `qudt-measurement-definitions-3.5.2-20261014`: historical lexical layout
  with explicit `unit:` prefix and column-zero named-unit Turtle blocks. Only
  the historically selected unit IDs emit. This is a lexical unit-reference
  adapter, not a complete Turtle parser or validated conversion engine. Full
  selected block and preamble survive; no decimal-to-float conversion occurs.
- Overture `2026-09-23.1`: JSON array of the historical Parquet projection's
  Python row objects: id, names, taxonomy, basic_category, sources, addresses,
  confidence, operating_status and version. Unknown projection fields reject.
  Historical food hierarchy include/exclude rules apply. Provider-specific
  licences remain paired with each source and additionally listed distinctly.
  This does NOT implement Parquet loading, acquisition, all-shard reconciliation,
  notice verification, menu coverage or production admission.

JSON fractional/exponent numbers are retained as tagged lexical objects
`{"sourceNumberLexical": "..."}` rather than rounded binary floats. Integers,
Unicode strings, nulls, booleans, original identifiers and raw references remain.
Duplicate JSON keys, nonfinite numbers, duplicate emitted identities, unknown
releases, empty selections and unsupported input layouts fail closed.

## Provenance and historical source evidence

Historical scripts were inspected as source evidence; none are dynamically
imported. The exact blobs retained in the repository are:

| Source | Script | Git blob |
| --- | --- | --- |
| Wikidata | scripts/collect-business-references.py | f5ea7f7675dd31edef2a3b65122f1853f0c2e486 |
| Wikibooks | scripts/collect-wikibooks-live.py | 5542c028f49ba35da2171809ee74f7a64cb3e9da |
| FoodOn | scripts/collect-foodon-definitions.py | fa232aabeb8162e2bbbd51ef71775e4b46193cb2 |
| QUDT | scripts/collect-measurement-terminology-20261014.py | 73a0dcbeea567f478fcf394870bc03ebbd728127 |
| Overture | scripts/collect-overture.py | 831a3123936c88a6dcddffdf12486bbd83477797 |

No source-wide licence is substituted for mixed Overture provider rights.
FoodOn own-namespace and QUDT reference rights are scoped separately; notices,
attribution and downstream obligations still require operation-specific review.
Known source licence metadata alone grants no operation.

## Explicit blockers and next work

Dietary guidelines `fao-directory-20261013` has no reviewed retained parser or
record schema. It remains unsupported; a directory link is not a certification.
Research should resume only against already-authorized retained directory/index
schema evidence, not invented scraping formats or fresh downloads.

Next integration task: register source-format-specific candidate execution with
reviewed exact bundle pins and test candidate-to-acceptance handoff using authored
fixtures. Keep QUDT lexical and Overture projection support distinct from full
release parsing in capability reports. Full-release acceptance requires actual
manifest/custody/rights evidence, not synthetic fixture success.

Tests are small authored synthetic objects embedded in
`tests/test_reference_adapters.py`, with schema validation on emitted candidates.
No retained raw dataset or production admission was created.
