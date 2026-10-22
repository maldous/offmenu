# Acquired recipe adapters — source-faithful staging, not corpus acceptance

## Entry point and boundaries

`ingest_acquired_recipes.run_domain(domain, sources, context)` supports `recipes`,
`ingredients`, and `citations` under the existing `ingest_api` / `DomainStore`
contract. It requires the catalog's **explicit** `acquired_adapter` and
`metadata.acquisition.verified == true`. Source file/receipt verification is the
catalog bridge's responsibility; this adapter does not claim an unperformed
checksum check. Holds, restricted records, and loaded-source markers are not
bypassed. No generic extension fallback can select an acquired adapter.

| Family | Acquired input | Projection |
|---|---|---|
| `foodista_common_pile` | Five gzip JSONL shards; `format=jsonl`, `compression=gz` | Explicit `/recipe/` documents with ingredient and preparation sections only |
| `forkrecipe` | Official pinned tar.gz; `format=archive`, `compression=gz` | Supported static literal objects in direct `recipes/*.js` members, excluding templates |
| `medlineplus_healthy_recipes` | Twelve inert HTML files; `format=html` | Heading/list-based recipe body; each EN/ES source variant remains independent |

There is **no fetch, source-code execution, archive extraction, package install,
translation, nutrient calculation, food matching, semantic acceptance or gold
review** in these modules. Original sources and all resulting staging databases
stay in private local custody. They are not intended for raw GitHub publication.
The currently running user's `./run` is not changed or restarted by this code.

## Source fidelity

### Foodista / Common Pile

- The collector's source schema is `id,text,source,added,created,metadata` with
  per-record URL/license/authors. The adapter streams bounded JSONL records,
  skips blogs/questions/tool pages, and isolates malformed lines/ambiguous
  sections without dropping later records. The 72,090 published mixed-document
  count is **not** a recipe count.
- Explicit Ingredients plus Preparation/Directions/Instructions sections are
  required. Tools/About/Information and appended Comments/Answers never become
  projected ingredients or directions. Exact original JSON/text remains inert
  source evidence; retaining it privately is not admission of comments as recipe
  content. Ambiguous missing/repeated section boundaries are quarantined.
- The snapshot's per-record license is retained independently of the catalog's
  current-site policy. CC BY 3.0 is never silently relabeled CC BY 4.0.
- Collector `metadata.authors` can include commenters. It stays unchanged;
  published `By:` text is carried separately and is not reconstructed from that
  array. Unparseable/null dates stay verbatim with explicit review flags; they
  are not repaired, dated, or counted as reviewed recipes.
- Projection units are source ingredient lines and source procedural text, not
  canonical foods or a claim that every upstream flattened text boundary is
  trustworthy. Actual shard inspections remain necessary.

The bounded implementation review checked the primary
[collector preprocessing code](https://github.com/r-three/common-pile/blob/main/sources/food/preprocess.py)
and [Dolma conversion schema](https://github.com/r-three/common-pile/blob/main/sources/food/to_dolma.py).
No shard data was downloaded into this development workspace.

### ForkRecipe

`acquired_recipe_js.py` implements a closed literal grammar: objects, arrays,
strings, finite numbers, booleans/null, literal keys, comments and trailing
commas; exact default/CommonJS export wrappers and a single const/export wrapper.
Plain template strings are supported only with **no interpolation**. It rejects
imports/calls, spreads, getters, computed expressions, duplicate/prototype keys,
unknown identifiers, trailing statements and resource-cap violations. It never
uses eval, exec, JavaScript runtimes, source imports, or code repair.

Source-shaped fields include `repoId`, `parentRepoId`, `slug`, `title`, `author`,
`ingredients[].{ingId,name,ratioValue,defaultUnit,role}` and
`processNodes[].{nodeId,action,instructions,...}`. All original fields and exact
JavaScript text remain intact, including exact numeric spelling. Ratios/parts
are exposed as **source ratios**, not gram quantities or implied serving yield.
Process-node visual/tactile cues remain source evidence; they are not invented
steps. Fork relationships remain unresolved source-native assertions, not
fabricated canonical recipe links. The
[bounded primary sample schema](https://github.com/futurechef/forkrecipe-recipes/blob/main/recipes/ackee-saltfish.js)
was inspected; this does not certify the downloaded archive's entire syntax.

The archive is streamed twice: a bounded notice/contributor-evidence pass then
recipe members. LICENSE, NOTICE, README and `data/users.js` remain inert
provenance. Unsupported/malformed recipe members, unsafe paths, symlinks, and
duplicate member names are isolated. No member is extracted to the filesystem.
Limits cover **actual decompressed bytes**, member count, per-member bytes, DOM
or literal nesting and tokens; gzip footer checks are consumed at stream end.
A corrupted container or resource cap can stop that source while other sources
continue, with already committed batches resumable.

All recipe families also cap 512 ingredient mentions, 1,024 procedural units,
and (for ForkRecipe) 512 process nodes per recipe. A 4 MiB aggregate JSON bound
is checked incrementally before identity hashing and again after projection,
including independent citation/provenance bounds. Oversized records are
quarantined whole with finite diagnostic reasons; cooking meaning is never
silently truncated. Their original acquired artifact remains in private custody.
Complete notices, rights and author arrays are retained on recipe provenance;
ingredient mentions retain their own source values plus exact recipe/citation
IDs and a provenance hash instead of multiplying that large context per mention.

### MedlinePlus

The parser uses stdlib HTML parsing; scripts/images/subresources are never
executed/fetched. It accepts English Ingredients/Directions and Spanish
Ingredientes/Preparación/**Direcciones**, preserves ingredient group headings,
and takes procedural list items only. Inline whitespace is retained; notes and
nutrition text remain source evidence and are not turned into steps or
calculated nutrients. NLM/provider attribution and policy lineage are retained.

Only the **known exact Spanish toast URL** has a headingless-ingredient
exception, and only when there is exactly one unambiguous unordered list before
the procedural heading. Other missing headings are quarantined, not guessed.
The [publisher's toast page](https://medlineplus.gov/spanish/recetas/tostada-francesa-con-pure-de-manzana/)
was checked as bounded structural evidence, not as a local corpus fixture.

Explicit catalog work/counterpart assertions and observed links are retained,
but independent EN/ES quantities are not overwritten, merged, or declared
semantically equivalent. The known waffles quantity mismatch gets a review
flag. Twelve acquired pages do not establish twelve unique dishes, a complete
Medline corpus, or twelve accepted recipes. Images and unrelated health content
are not covered by the recipe-specific public-domain assertion.

## Exact cross-domain relationships

All three domain streams use the **same source ID/path/fingerprint and adapter
version** `offmenu-acquired-recipe-ingest/1`.

- Recipe IDs use the existing source/content identity function.
- Ingredient mention IDs are `recipe_id + ':ingredient:' + ordinal` and retain
  `ingredient_of` → the exact recipe ID. Recipes emit `has_ingredient_mention`.
- Citation IDs are `recipe-citation:` plus the stable hash of the recipe ID.
  Recipes/mentions emit `cites`; citations emit `cites_record` → the exact recipe
  ID. Citations contain metadata, rights and notice hashes, **not recipe bodies**.
- Exact duplicate source copies share logical IDs but preserve distinct custody
  rows. Content versions remain distinct; culinary/cross-corpus deduplication is
  not silently performed.

## Counts, resume and verification

The standard read/written/unchanged/error/skipped counts describe staging
**source provenance rows**, not accepted unique recipes. Per-source record-kind
counters distinguish examined documents, non-recipes, quarantined records,
projections, ingredient mentions, citations, templates and nonrecipe members.
Counters reflect this attempt; a completed-source shortcut does not invent a new
inspection count. Parse failures remain durably partial on unchanged rerun.
Source budgets retain committed prefixes; later runs replay deterministically
and resume according to `DomainStore` checkpoints.
Per-source `diagnostics.reason_counts` uses the finite `REASONS` vocabulary for
this attempt only, including isolated parser errors and source-stream failures.
Unknown exception messages become `acquired_recipe_source_error`; no exception
text enters this histogram. The supplemental receipt can carry these reasons
without expanding the fixed legacy receipt envelope. Historical reasons are not
invented on completed-source shortcuts.

All recipe projections are explicitly `qualification_status=unreviewed`,
`automaticPlanningEligible=false`, `gold_review_performed=false`, with no
normalization/translation claim. Structurally parsed source facts are not
production acceptance.

Generated-fixture verification (no actual acquired cache access):

```sh
python -m unittest discover -s manual-action/tests -p 'test*acquired*recipe*.py' -v
```

Tests cover source-shaped fields, static grammar attacks, gzip/size caps, unsafe
archive paths, member/source isolation, source notices, Foodista mixed documents
and license lineage, Medline groups/headingless Spanish/variant discrepancies,
exact cross-domain IDs, duplicate copies, partial resume and unchanged errors.
Additional adversarial fixtures cover structural/aggregate projection caps,
pre-hash bound enforcement, notice de-amplification and sanitized reason counts.
They establish implementation behavior only, not real-corpus acceptance.

## Outstanding evidence — action / target / reason / status

| Action | Target | Reason | Status |
|---|---|---|---|
| Inspect actual acquired record samples privately after current run exits | All three source families on Foo | Generated tests and primary schema examples cannot prove local acquired-byte compatibility | Pending; no Foo execution requested here |
| Measure per-source projection/rejection counts and inspect representative rejects | All five Foodista shards, ForkRecipe archive, twelve Medline HTML pages | Download success/file counts are not recipe acceptance | Pending authorized later ingestion |
| Verify contributor exceptions, ambiguous flattening, dates, language quantities and culinary fidelity | Staged source projections | Source-specific QA remains necessary; no fabricated AI review or translation | Pending |
| Validate exact relational resolution and target binding with the final runner | Recipe/ingredient/citation outputs | Additive staging is not proof of app-bound production loading | Integration-owned |
