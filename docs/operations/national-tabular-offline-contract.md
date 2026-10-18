# Retained national tabular candidate contracts

Scope: authored synthetic tests for CNF **2015**, and FOODfiles **2024 Version 01**. No dataset download, archive extraction, installer execution, live endpoint, new rights decision, production admission, or accepted-record claim. CNF 2026 discovery is still a different release. FOODfiles newer online search data is not covered. Fineli/Frida holds and NO/FR native-crash no-retry restrictions are unchanged.

## Exact historical code

| Path | Git blob SHA |
| --- | --- |
| scripts/collect-cnf.py | 14e9dba1ad15e17c6eee039d74f53e887b3cbb7d |
| scripts/collect-next-national.py | b3767cddda8a7cb710d6fe4c3612068a3197eb37 |
| scripts/import-national-tables.py | fb4b6c304ff1c4f3cf28210e815c652c3635a814 |

The existing worker checks exact source bytes, ignores source bytecode, prohibits unreviewed script dependencies, and uses fixed call targets. ADMISSIONS remains empty. Production data, rights/custody evidence, scope, acquisition time, qualification and acceptance contracts remain pending.

## Bundle semantics

Every original archive, acquisition receipt, and extracted input has an independent size/SHA-256 admission pin. Bundle inventory must match exactly. Canonical relative POSIX names allow nested files but reject traversal, aliases, absolute paths, backslashes, colons, links, special files, and empty directories. No archive is extracted by this code.

CNF: cnf-2015-csv.zip plus twelve csv/*.csv inputs. Only four table schemas are semantically interpreted by the pinned collector: FOOD NAME, NUTRIENT NAME, NUTRIENT SOURCE and NUTRIENT AMOUNT. The eight other CSV tables are parsed as well-formed, individually pinned, **uninterpreted companion tables**. Their count does not establish canonical companion names, schema validity, complete source coverage or archive/extraction correspondence. Those are pending scope-review obligations. Authored fixtures intentionally label these companions synthetic.

FOODfiles: nz-foodfiles-2024.msi, acquisition.json, nz-extracted/ExcelFilesNamesx (workbook), UnabridgedCodes and UnabridgedDataFT (UTF-8 tilde-separated tables with one pre-header line). The three semantic inputs do not prove custody/completeness of all thirty installer components. The acquisition receipt pins the MSI, while admission independently pins its reviewed extracted projection.

## Values, units, and rights

Historical source fields and attribution are retained. CNF NutrientID and NutrientCode remain distinct; unresolved NutrientID produces a source-specific key with unknown unit, not an invented canonical mapping. Unknown-unit facts require later qualification and cannot establish accepted canonical nutrient observations. Preflight rejects unresolved food/source joins, duplicate definitions, duplicate observations, canonical-key collisions and nonfinite numeric observations.

FOODfiles preserves sourceValue lexical text, source units and qualifiers. Whole-food W matrix observations use the retained fixed mapping; F/N matrices stay source-specific with explicit source-matrix basis. Less-than and unknown values remain qualified. Source-specific energy/carbohydrate/fibre definitions are not collapsed. Source terms, attribution and downstream terms remain in provenance. No new release equivalence, diet qualification or publisher endorsement is claimed.

Original pinned bytes remain immutable. Legacy parsing uses Python numeric values; this is not a new arbitrary-precision numeric representation or a certified lossless decimal round-trip. FOODfiles keeps lexical sourceValue; CNF original lexical values remain in the pinned CSV bundle. Candidate records are not permission to distribute source data.

## Limits and failure behavior

This lane reuses the existing worker's **64 MiB combined input**, **1 GiB address-space**, **120 second wall / 110 second CPU**, **256 MiB total output** ceilings. Parsers and preflight eagerly materialize tables; no streaming or production-scale adequacy is claimed. Large original archives may exceed this ceiling and must stay in Foo; this implementation does not relax limits or substitute an unpinned small derivative.

Failures return explicit contract errors before launch or generic execution-worker-failed for guarded collector/preflight failures. A failed candidate directory is never represented as a successful receipt, admission or accepted result. Global peer stages remain independent. Successful output uses deterministic candidate JSONL and gzip, evidence-derived acquisition timestamps, neutralized historical manifests, and no acceptance count.

## Integration and verification

Owned additions: offmenu/refresh/national_tabular.py, tests/test_national_tabular.py and this document. The separate integration patch imports the static adapter additions and relative-name/inventory helpers into execution.py and calls preflight inside execution_worker.py after handler pin verification. It updates existing tests to preserve the five-workbook fixture scope while recognizing the now-implemented CNF parser and its unchanged discovery mismatch. No existing shared baseline file was edited.

Synthetic checks: deterministic outputs from both retained handlers; immutable provenance/release/time; CNF unit normalization, unknown value and unresolved-component retention; FOODfiles sourceValue/qualifier/non-W matrix/terms; release mismatch; extra files; symlinks and unsafe names; duplicate definitions; nonfinite CNF values; failed worker without success receipt; no cross-family admission. The composed PR38 test suite passes 90 tests. This is code qualification with authored fixtures, not production payload validation.

### Reviewed canonical semantic hook

`national_semantic_errors(source_id, row, *, allowed_units=(), basis_units=())` is a non-mutating diagnostic hook compatible with `SourceContract.semantic_validator` via `functools.partial`. It covers these seven retained executable national families only: CNF, FOODfiles, AFCD, MEXT, CoFID, BLS and Sweden. The caller must supply reviewed per-release units and basis allowlists; empty defaults fail closed and do not guess a production schema from fixtures. The hook checks exact retained release/source identity, profile schema/basis, numeric finiteness, qualified unknowns and censoring limits. CNF unresolved definitions and unknown units, and source-matrix observations, cannot establish canonical semantic completion. They remain intact as source evidence. This is a strict canonical hook, not a filter that removes such observations or a source-completeness assertion.

Inventory traversal is bounded to 4,096 entries and 16 levels. During admission verification, expected file paths and their allowed directory prefixes are derived from the declared pins; any unexpected directory/file is rejected immediately rather than recursively scanned. The updated composed suite passes **92 tests**, including six national-specific test methods.
