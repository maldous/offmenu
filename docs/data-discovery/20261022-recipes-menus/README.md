# Recipe and menu source discovery — 22 October 2026

**There are substantial non-PDF sources worth pursuing. This bundle is source-only research and disabled preparation, not a fetched corpus or an active acquisition queue.**

## Most promising routes

| Route | Evidence and scale | What remains open |
|---|---|---|
| **Foodista / Common Pile** | Content-licensed recipe text; Foodista advertises 42,291 recipes, while Common Pile contains 72,090 **mixed documents** in JSONL.gz. | Recipe-only filtering, full ingredient/step completeness, exact snapshot license and deduplicated-new count. The two totals are not additive. |
| **Koch-Wiki** | Publisher advertises 11,434 German recipes; quantified ingredient/direction sample and CC BY-SA 3.0 content policy verified. | API/discovery verification, attribution and cross-source deduplication. |
| **ForkRecipe** | Content explicitly CC BY-SA 4.0; metadata inspection found 964 non-template JavaScript files, versus README claim 916 recipes. | Static parsing only—never execute source JavaScript. File count is not unique recipe count; preserve ratio quantities. |
| **Government and multilingual recipes** | MedlinePlus EN/ES text, Korean MFDS structured ingredients/steps, licensed Cuisine-libre subsets and non-PDF historical originals offer real content. Eleven non-English Wikibooks editions were sample-checked. | MFDS service approval, source/record-specific rights and completeness; Wikibooks already has extensive retained multilingual coverage, so identify actual deltas. |
| **Institutional menus** | Taiwan school-lunch study reports 12,688,008 deduplicated **dish observations**; Konstanz archive reports 3,753,180 **meal options**. Korean NEIS, French CNOUS/municipal and Japanese school feeds provide JSON/XML/CSV routes. | Original endpoint access, payload schemas, attribution and upstream rights. Published study counts are not independently acquired counts, full menus or recipes. |

The linked reports carry primary evidence, exact access failures and restrictions. Tier A means a plausible explicitly licensed scope, **not production clearance**. Tier B preserves conditional leads rather than declaring them unusable. Tier C identifies restricted or non-equivalent scopes. API access, software licenses, uploader labels and publicly readable text are not substitutes for content rights.

## Reports and machine-readable registries

- [Structured/text recipes](structured-recipes.md) · [JSON](structured-recipes.json): 26 review rows; bulk formats, rights, lineage and safe handler proposals.
- [Multilingual recipes](multilingual-recipes.md) · [JSON](multilingual-recipes.json): 23 source/scope rows, including language editions and restricted subsets.
- [Menus](menus.md) · [JSON](menus.json): 31 source families; menu hierarchies, dates, currencies, price kinds and item observations.
- [Offline preparation](fetch-preparation/structured-recipes/README.md): conservative mock inspection functions, manifest validator and tests. No downloader, credentials or database writer.

These **80 review rows are not 80 independent datasets**. Translations, mirrors, editions, forks and derivative annotations require reconciliation. No combined new-recipe or new-menu total is claimed. Menu items, ingredient relations, QA pairs, images and documents must retain their own units; a dish name is not a recipe. Menu-to-recipe links stay unknown unless explicitly evidenced.

## Retained overlap: pinned snapshot, not current database inventory

The [14 October catalog report at commit `52b6a50`](https://github.com/maldous/offmenu/blob/52b6a50a59b458bdb49fe7ea090b72c63a4b1a30/docs/world-recipe-research-20261014.json) reports **25,135 records across all source families**: 24,879 full recipe records plus 256 OCR candidates. This includes **17,379 Wikibooks records across 32 editions** (3,309 English), 6,192 historical-archive records, 501 UniTools, 426 based.cooking and other families. It is not a 25,135-record historical-book-only corpus.

Those are the pinned report's historical catalog counts—not a fresh audit of current staged, normalized, accepted or loaded rows and not an independently deduplicated unique-work count. The historical archive's advertised 54,843 records is the same retained source revision; its wider rights-pending partition is not new supply. UniTools and based.cooking-derived material also overlap retained sources. Compare canonical source IDs, work/edition, revisions, translations and content signatures before reporting growth.

## Production boundary

**No production fetching until all eight databases are provisioned and evidence shows they are relationally fit for the existing data. Any eventual production acquisition runs on Foo only.** Source-specific rights/access approval, bounded fixtures, schema/provenance/dedup tests and a separately reviewed activation remain required. Eight filenames, empty schemas or readiness booleans are not sufficient evidence.

All three registries remain disabled. The included `production_fetch` function unconditionally refuses execution, including with eight apparent ready flags. This publication changes no active fetch configuration, normalization/ingestion implementation, database, production service or project plan. It includes no raw dataset, credentials, source archive, images or internal scratch notes.

## Reproduce offline checks

From this directory, using Python's standard library only:

```sh
PYTHONDONTWRITEBYTECODE=1 python fetch-preparation/validate_registry_bundle.py
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s fetch-preparation -p 'test_registry_bundle.py' -v
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s fetch-preparation/structured-recipes -p 'test_*.py' -v
PYTHONDONTWRITEBYTECODE=1 python fetch-preparation/structured-recipes/validate_manifest.py structured-recipes.json
```

Publication checks: three JSON registries parsed; 26/23/31 unique source IDs; all acquisition flags disabled and Foo-only; menu recipe references unknown/null; offline mock and negative-gate tests passed. These checks validate the preparation boundary, not external licenses, live source availability or database readiness.
