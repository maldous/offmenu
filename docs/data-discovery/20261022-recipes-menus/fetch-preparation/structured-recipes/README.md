# Offline structured-recipe preparation

These files are **not a production fetcher**. They contain no HTTP client, subprocess, repository execution, credential handling or database writer. Tests use invented fixtures only. The source registry is `../../structured-recipes.json`.

Production acquisition must run **on Foo only**, and only after all eight databases are provisioned and evidence-backed checks establish that they are relationally fit for the existing data. Presence of eight files, eight flags, empty schemas, or this preparation directory is not readiness. This module stays unconditionally disabled even if someone passes an apparently complete readiness object. Activation requires a separately reviewed integration; no activation switch is implemented here.

## Run local tests

`python -m unittest discover -s . -p 'test_*.py' -v`

`python validate_manifest.py ../../structured-recipes.json`

## Proposed acquisition interfaces (design only)

1. `SourceApproval`: exact source ID, permitted purpose, content-license evidence, original-source exceptions, immutable revision, signed approved URL inventory, maximum bytes/records, supported content type, rate limits, and provenance retention obligations.
2. `FooReadinessEvidence`: all eight named databases; provisioning identity/revision; successful cross-database relation, key/reference, schema/migration, integrity and retained-data compatibility results; timestamps and reviewer evidence; no synthetic readiness booleans.
3. `AcquisitionPlan`: chosen approved artifacts only, expected checksums, staging destination isolated from active databases, bounded retry budget and stop conditions. Abort on unexpected host/redirect, authentication barrier, license change, schema change, oversized expansion, or unsupported executable data. Honor service terms and no-scrape restrictions.
4. `StagedRecord`: source/work IDs, original/canonical URL, raw title/ingredients/instructions, language, contributors and their roles, original license/version/evidence, collection time, revision, upstream lineage and all transformations. Candidate is not accepted merely because a parser succeeds.
5. Acceptance is a separate transaction: complete ingredients and steps, eligible rights, safe/accurate culinary metadata review, retained-corpus deduplication, and database-level relational validation. Record offered/fetched/parsed/full/eligible/new/accepted counts independently.

## Handler boundaries

| Handler | Required design before integration |
|---|---|
| `dolma_jsonl_recipe_sections` | Stream gzip with compressed/decompressed limits, line-size bound and JSON-only parsing. Allow exact Foodista hosts and recipe path; require unambiguous Ingredients/Preparation sections; remove comments, retain authors with roles unverified if collector conflated them. Preserve unknown dates. Quarantine instead of guessing damaged sections. |
| `static_js_ast_recipe` | Parse only a single static object export with an audited JS parser and an allowlist of literal/object/array syntax. Never evaluate/import the source. Reject calls, property getters, dynamic expressions, imports, computed keys and prototype pollution. Preserve ratio units; do not invent grams/yield. Handler remains design-only here. |
| `semantic_html_recipe` | Source-specific HTML selectors, bounded approved URL discovery, no JS execution. Require ingredients and ordered directions. Separate image rights and link EN/ES versions. MedlinePlus general XML is not a verified recipe feed. |
| `json_recipe_fields`, `unitools_json` | Preserve arrays, original quantity/unit/scaling, multilingual fields, contributors, license and source exceptions. Unknown enums survive as raw values or quarantine, never silent normalization. |
| `safe_list_csv`, `foodcom_parquet` | Prefer Parquet with bounded schema, no unsafe deserialization. CSV list cells use strict grammar or `ast.literal_eval` only for an explicitly approved compatible grammar with bounds; never `eval`, R evaluation, shell or language interpreter execution. |
| `recipeqa_per_record_license` | Join full recipe records to per-record license before use; inspect ingredients omitted from QA preprocessing; remove non-food projects; QA pairs do not create new recipes. |
| `themealdb_slots` | Pair ingredient/measure slots by index, retain missing quantities, skip wholly empty slots; keep instructions verbatim until separate segmentation. API terms and third-party rights remain an independent gate. |
| `historical_jsonl_work_rights` | Join retained work-level rights table before accepting any record; repository Unlicense never replaces original/translation checks. |
| `cooklang_source_feed` | Approve source repository content license individually; pin commit; bounded parsing of text annotations; retain source and author. |

The included two inspection functions demonstrate conservative transformations on already supplied records, not live collectors. They deliberately return `candidate_not_accepted` and never certify rights, nutrition, allergens, or food safety.
