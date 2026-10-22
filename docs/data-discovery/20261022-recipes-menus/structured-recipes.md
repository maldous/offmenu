# Structured and text recipe sources — researched 22 October 2026

## Findings that change the plan

**The best large additional lead is Foodista, not another relabelled Recipe1M scrape.** Its current website advertises **42,291 recipes** and explicitly licenses content under CC BY 4.0. Common Pile already distributes a machine-readable Foodista snapshot: **72,090 documents**, about **0.09 GB extracted text**, in JSONL.gz. Those documents include blogs and other non-recipes: **72,090 must not be reported as recipe count**, nor added to the website count. The commercially reusable, complete, deduplicated recipe subset remains uncounted. [Foodista](https://www.foodista.com/), [content terms](https://www.foodista.com/terms), [bulk dataset](https://huggingface.co/datasets/common-pile/foodista).

**ForkRecipe provides a second independent, explicitly content-licensed collection.** Its README advertises 916 recipes, but a bounded GitHub directory-metadata inspection found **964 non-template JavaScript recipe files** (965 files including `_template.js`), approximately 9.48 MB including the template. This is a file count, not a verified unique-recipe count. It has ingredient quantities as ratios and explicit procedural nodes. [Repository and content policy](https://github.com/futurechef/forkrecipe-recipes), [sample](https://github.com/futurechef/forkrecipe-recipes/blob/main/recipes/ackee-saltfish.js).

**Do not count the historical archive or UniTools again.** The existing retained baseline includes 6,192 cleared historical-archive recipes and 501 UniTools recipes. AdamBouhmad/open-recipe-archive currently advertises 54,843, but its checked HEAD is the **same revision already retained**, not a newly enlarged dataset. Most of the difference is a rights-review boundary, not additional supply. Current loaded database totals and retained source totals are separate questions.

This review also keeps substantial conditional sources visible: RecipeQA has per-recipe licenses rather than a blanket prohibition; Food.com, RecipeNLG, Recipe1M, RecipeDB and derivative dumps contain useful real text but have differing rights/access constraints. None is silently promoted to open commercial content because an uploader selected MIT or CC0.

## Scope, evidence and tiers

- Research only: primary documentation, license text, repository directory/commit metadata and a few representative records/pages. **No production bulk fetch, database import, account creation, payment or terms acceptance occurred.**
- **A** = credible content-level open/PD basis for a candidate pipeline, still requiring source provenance, completeness, deduplication and jurisdiction/use review. It does not mean already cleared or production-enabled.
- **B** = potentially useful with per-record selection, provenance clarification or a commercial agreement. Not a blanket rejection.
- **C** = explicit restriction incompatible with an unrestricted commercial corpus, or missing essential permission/access evidence; retain for separate permitted research or future clarification.
- CC BY-SA permits commercial reuse subject to its terms. Keep author/source/license/version and modifications; distribute covered adaptations under the required compatible share-alike license. Do not assume every separate database component automatically has identical obligations. These are source-audit findings, not legal advice.
- Counts below distinguish publisher claims, metadata counts, and accepted recipe counts. **No new unique total is defensible before filtering and cross-corpus matching.**

## Priority A candidates and existing-source deltas

### 1. Foodista through Common Pile — highest-volume open candidate

**Coverage/access.** Primarily English, global dishes; current site advertises 42,291 recipes. [Common Pile card](https://huggingface.co/datasets/common-pile/foodista) reports 72,090 mixed documents; the [README](https://huggingface.co/datasets/common-pile/foodista/blob/main/README.md) specifies `v0/documents/*.jsonl.gz`. The repository's roughly 951 MB includes multiple representations and is not the text-only size. Pin an immutable dataset revision and exact shard manifest before any future bulk acquisition; exact shard names/checksums were not resolved here.

**Real content.** The [bounded Foodista recipe sample](https://www.foodista.com/recipe/7SVL8NL4/no-bake-banana-oatmeal-cookies) contains quantified ingredients and ordered preparation. The [collector's preprocessing code](https://github.com/r-three/common-pile/blob/main/sources/food/preprocess.py) extracts ingredient and preparation containers, but appends comments. Its [example JSON](https://github.com/r-three/common-pile/blob/main/sources/food/examples/0.json) is a blog post, proving the need for a recipe filter. Stored fields: `id,text,source,added,created,metadata{license,url,authors}`. Extracted text needs section parsing; this is not a pristine structured ingredient database.

**Rights/handling.** Snapshot records identify CC BY 3.0; [current terms](https://www.foodista.com/terms), effective 23 January 2026, say CC BY 4.0. Preserve the actual snapshot license and evidence rather than silently upgrading it. Attribute original author, URL and collector; mark transformations. Initially omit images, comments, tools-only pages and linked third-party text. Require `/recipe/` plus nonempty ingredient and preparation sections; quarantine ambiguous flattening and null/unparseable dates. The `foodista_filtered` viewer currently fails timestamp conversion, so prefer original `v0` and preserve raw dates. [Filtered derivative](https://huggingface.co/datasets/common-pile/foodista_filtered).

**Overlap.** Foodista site, Common Pile original/filtered, legacy Kasabi RDF and downstream mirrors are one lineage, not additive corpora. Legacy RDF's advertised millions of triples are not recipe counts and full steps were not verified. [Legacy catalogue](https://old.datahub.io/dataset/foodista).

### 2. ForkRecipe — structured original/community content

[README](https://github.com/futurechef/forkrecipe-recipes), [license](https://github.com/futurechef/forkrecipe-recipes/blob/main/LICENSE), [template](https://github.com/futurechef/forkrecipe-recipes/blob/main/recipes/_template.js). Checked commit: `934319313379201f91ddccdd29abd054039a3ad6` (3 October 2026). Metadata count: **964 non-template `.js` files**, versus README claim 916. English prose with international cuisine/culture tags. Content, not merely code, is offered under CC BY-SA 4.0; the maintainer says recipes are originally authored for ForkRecipe or adapted from public-domain material. Retain ForkRecipe/FoodML and contributor attribution, notices, source/fork relationships, license and modification record; verify provenance exceptions. AI-assisted authoring and culinary accuracy need QA, not automatic rejection.

Mapping: `repoId`, `parentRepoId`, `slug`, `title`, `author`, `cuisine`, `culture`; `ingredients[].{name,ratioValue,defaultUnit,role}`; `processNodes[].instructions`; raw active/total time. The inspected sample has ingredient **parts/ratios**, not gram weights or an established serving yield. Preserve that distinction. **Never execute/import source JavaScript**: use an allowlisted static AST parser, rejecting calls, imports, spreads, getters and computed expressions. Skip template files; retain forks as related versions before deduplicating.

### 3. MedlinePlus Healthy Recipes — government text, EN/ES

[English index](https://medlineplus.gov/recipes/), [Spanish index](https://medlineplus.gov/spanish/recetas/), [NLM reuse policy](https://medlineplus.gov/about/using/usingcontent/). The policy expressly lists Healthy Recipes in both languages as public-domain content under U.S. law, and requests NLM attribution. Do not extend that statement to all MedlinePlus material or images. No recipe-specific bulk XML dump was verified; the general health-topic XML service must not be represented as a recipe dump.

HTML sample [Oatmeal Pecan Waffles](https://medlineplus.gov/recipes/oatmeal-pecan-waffles-or-pancakes/) contains ingredient groups, seven directions, prep/cook time, servings and nutrition, credited to NHLBI. Map language variants to a common work where explicit counterpart links exist. Recipe count is **unknown**, and category links can duplicate recipes. Text-only index discovery and semantic HTML parsing are appropriate after activation; no crawl performed.

### 4. Kerala traditional recipes — small, culturally useful structured source

[Maintainer dataset](https://huggingface.co/datasets/Fathi7ma/kerala-recipes) exposes **89 rows** in its viewer, with JSON/CSV/Parquet forms (repository about 323 kB). It claims CC BY 4.0 and traditional/home-cook provenance. English instructions and Malayalam dish names are not a fully Malayalam instruction corpus. Ingredients, amounts, steps, per-person scaling and context are present. Its meal-pairing links and feast templates are separate entities, **not additional recipe counts**. Tier A candidate subject to contributor/source review; preserve culturally specific names, uncertain scaling and attribution. Not a substitute for large-volume sources.

### 5. Public Domain Recipes — likely overlap, not an automatic addition

[Website](https://publicdomainrecipes.com/), [repository](https://github.com/ronaldl29/public-domain-recipes), [bounded full recipe](https://publicdomainrecipes.com/desert-roses/). The site declares recipes public domain/Unlicense, with ingredient and step text. It is a fork of based.cooking, whose 426 records are already retained. Count only a demonstrated commit/content delta after source-ID and text matching; no new unique count established. Images and copied source exceptions still need review.

### 6. Original-only CC0 staging project

[HoChiPants/open-recipe-archive](https://github.com/HoChiPants/open-recipe-archive) is **not** AdamBouhmad's historical archive. Its policy distinguishes MIT software from CC0 original recipe data and requires contributor rights. Published recipe JSON requires ingredients/instructions. Rights-pending `recipes-staging` is not covered by a blanket clearance: admit only final original records with verified provenance. No substantial count independently established; useful source/schema lead, not a claimed mass addition.

### 7. UniTools — useful structured retained data, zero demonstrated new count

[Repository](https://github.com/farcrak/unitools-recipes), [sample](https://github.com/farcrak/unitools-recipes/blob/main/sample.json), [content license](https://github.com/farcrak/unitools-recipes/blob/main/LICENSE). **501 recipes, 127 country tags**, bilingual English/Russian; JSON/CSV about 2.6 MB, version 2.0.0 generated 2 September 2026. Explicit CC BY-SA 4.0 content, commercial reuse allowed. Canonical [JSON endpoint](https://theunitools.com/data/unitools-recipes-v1.json) is documented, not bulk fetched. Quantified ingredients, base servings, bilingual steps, timing and nutrition exist. Preserve original scaling enums rather than coercing differing sample/documentation values. Commons photo licenses are separate. Existing accepted baseline already has 501 at `2f554073f7e730b18d707fe1164d18308f6ec16c`.

### 8. Historical open-recipe-archive — same revision, retained rights partition

[Maintainer](https://github.com/AdamBouhmad/open-recipe-archive), [commit history](https://github.com/AdamBouhmad/open-recipe-archive/commits/main/). Advertises **54,843 recipes / 31 collections**, Markdown/JSONL, but current HEAD `ae3bd2c009a8899dfe63b9166fa98ae3fa8041a8` (6 July 2026) equals the retained baseline revision. **6,192 already accepted** after work-level author/translator/date checks; the remainder is not automatically cleared by the repository's Unlicense. Historical ingredient/direction text and book/page provenance are useful, but original/translation rights vary by jurisdiction. This is primarily a retained-import and rights-partition issue, not a new-source victory.

## Large conditional and restricted collections — retain, distinguish, do not inflate

| Source | Scale / actual content / access | Rights and disposition |
|---|---|---|
| [RecipeQA](https://hucvl.github.io/recipeqa/) / [primary datasheet](https://hucvl.github.io/recipeqa/recipeqa-datasheet.pdf) | 19,779 English Instructables recipes; 36,786 QA pairs, **not** 36,786 recipes. JSON question sets (150/18/18 MB advertised); recipe archive about 400 MB. Per-step title/description/images; ingredients may be embedded, completeness unverified. | **B, per-record selection.** `recipes.json` carries individual licenses; not blanket NC. Separate commercially compatible CC variants from NC/ND/unknown, preserve authors/source. Initial narrative step was omitted in QA preprocessing; do not ingest QA contexts as complete recipes. Filter non-food how-to projects; unique eligible subset unknown. |
| [Food.com — irkaal](https://www.kaggle.com/irkaal/foodcom-recipes-and-reviews/metadata) | 522,517 recipes, 312 categories; recipes CSV about 704 MB, Parquet recommended. Quantities, ingredient parts and instructions; 1,401,982 reviews are a separate table, not recipes. | **B.** Uploader CC0 label is not evidence of permission from Food.com or recipe authors. Need underlying content grant/per-record rights before unrestricted redistribution. Omit reviews/user IDs/images by default. CSV list fields use R-like `c(...)`: never evaluate them as code. |
| [Food.com personalization](https://github.com/majumderb/recipe-personalization) / [creator dataset](https://www.kaggle.com/datasets/shuyangli94/food-com-recipes-and-user-interactions) | Commonly advertised 231,637 recipes plus interactions; CSV raw steps/ingredients and nutrition. Quantity completeness not established. | **B.** Same Food.com lineage, likely substantial overlap with irkaal. Treat count as advertised, not independently recounted; underlying rights unresolved. |
| [RecipeNLG](https://github.com/Glorf/recipenlg) / [source download terms](https://recipenlg.cs.put.poznan.pl/dataset) / [HF view](https://huggingface.co/datasets/mbien/recipe_nlg) | 2,231,142 recipes: title, ingredients, directions, source link, provenance flag and ingredient NER. Includes gathered and Recipe1M-derived records. | **C for unrestricted commercial corpus.** Indexed primary download terms specify noncommercial research/education; live page rendering was sparse, so current exact terms need revalidation. Do not accept terms or infer open rights from mirrors. |
| [ReciFine](https://huggingface.co/datasets/nuhuibrahim/recifine) / [3A2M paper](https://arxiv.org/abs/2303.16778) | ReciFine repeats 2,231,142 records with richer entities; 3A2M also derives from RecipeNLG. | **C/lineage.** Annotation improvements, not millions of new underlying recipes. Upstream restrictions/provenance remain relevant; verify derivative annotation license separately. |
| [Recipe1M/1M+](https://im2recipe.csail.mit.edu/) | Approximately one million recipes, ingredients/instructions and image associations; 1M+ expands images, not an independent million recipes. Layered JSON historically used. | **C pending exact current dataset terms.** Download/login endpoint was unavailable to this research tool; prior retained audit classified restricted research. Paper/software licenses do not establish scraped recipe rights. Do not represent 1M+ images as new recipes. |
| [FoodKG construction](https://foodkg.github.io/foodkg.html) | Recipe1M-related RDF/knowledge-graph construction, nutrition/ingredient links, public endpoint. | **B/C derivative.** Added semantic relations do not establish independently licensed recipe prose. Count only enrichment; verify underlying record license and whether full directions are actually exposed. |
| [Epicurious image recipe dataset](https://www.kaggle.com/pes12017000148/food-ingredients-and-recipe-dataset-with-images/activity) | 13,582 rows; CSV about 26.6 MB, images raise total to about 238.62 MB. Title, ingredients, instructions, image name, cleaned ingredients. | **B.** Uploader CC BY-SA 3.0 is not a demonstrated Epicurious/author content grant. SQLite mirrors are the same lineage. Image rights are separate. |
| [Zenodo Culinary Recipes](https://zenodo.org/records/15169428) | 50,510 advertised; CSV 110 MB, v1, 7 April 2025; description lists ingredients, instructions, nutrition and time. Published MD5 `986efafad65c7969fde13a46d2defba0`. | **B pending.** License field and actual column/sample evidence were not resolved by the rendered record. This means *not established*, not proof of no license. Request/inspect metadata and a bounded preview later, not bulk-download merely to discover rights. |
| [Indian recipes, Mendeley](https://data.mendeley.com/datasets/xsphgmmh7b/1) | 6,000+ advertised; CSV/XLS; Hindi names/text plus translated English, times, servings, cuisine/course/diet, ingredients and instructions. | **B.** Creator CC BY 4.0 label, but scraped Archana's Kitchen and machine translations require underlying rights verification. Translation variants are not additional dishes. |
| [RecipeDB](https://cosylab.iiitd.edu.in/recipedb/) / [FAQ](https://cosylab.iiitd.edu.in/recipedb/FAQ) | Over 118k recipes, 74 countries/26 regions; nutrition/ingredient database. Full procedural export not independently verified. | **C for unrestricted commercial reuse:** site states CC BY-NC-SA 3.0. Original scraped sources still matter. Useful permitted research/reference source, not blanket commercial feed. |
| [RecipeDB 2.0](https://cosylab.iiitd.edu.in/recipedb2/) / [primary paper](https://arxiv.org/abs/2609.22099) | 128,942 recipes, 35,474 ingredients, 99 countries/32 regions claimed. Current site renders as JS shell. | **B pending exact 2.0 terms/export.** Do not automatically inherit predecessor's license or add its count to RecipeDB. Need explicit content license, schema and bulk access evidence. |
| [Cooklang federation](https://cooklang.org/guides/recipe-discovery/) / [software](https://github.com/cooklang/federation) | Guide claims about 5,000 `.cook` recipes across about 80 collections/10 languages; search API and linked Git repositories. Ingredients, timers and steps can coexist in source text. | **B per-feed audit.** Federation/software license is not a license for every author's recipes. Discover and approve source repositories individually; preserve metadata and source license. Existing based.cooking/other mirrors may overlap. |
| [RecipeSource](https://www.recipesource.com/admin/faq.html) / [submission policy](https://www.recipesource.com/admin/submit.html) | Legacy MealMaster/MasterCook/plain-text archives, real ingredients and directions; complete count unverified. | **B per-record.** FAQ does not confer blanket republication rights; [sample](https://www.recipesource.com/main-dishes/meat/pork/06/rec0612.html) expressly credits copyrighted Food Network material. Text format does not equal public domain. |

## API and commercial routes (not bulk-license substitutes)

| Source | Availability and schema | Reuse/access boundary |
|---|---|---|
| [MyPlate.food API](https://myplate.food/api), [bulk partnerships](https://myplate.food/partners) | Independent preservation service, **1,072** advertised USDA recipes, JSON by slug/search; five language versions are not five times as many dishes. Docs permit no-key use at 20 requests/minute and 100 full recipes/day. | **B contract route.** Live commercial app calls allowed under terms; commercial reuse of enriched bulk JSON/CSV requires a separate license. Do not paginate API to evade that condition. Original federal content provenance is separate from enrichment, translations and images. No purchase/contact performed. |
| [TheMealDB](https://www.themealdb.com/), [API](https://www.themealdb.com/api.php), [terms](https://www.themealdb.com/terms_of_use.php) | Homepage **793 meals / 992 ingredients** claimed. Bounded [Arrabiata API response](https://www.themealdb.com/api/json/v1/1/search.php?s=Arrabiata) verified instructions plus 20 ingredient/measure slots, null/blank padding, area/country and tags. | **B service-terms route**, not generic CC0. Official API use permitted subject to conditions; no website scraping/reselling the API, preserve notices and third-party rights. App-store publication requires paid supporter access. Sample has `strCreativeCommonsConfirmed: null`, not proof of open content. |
| [Tiny Plates FAQ](https://www.tinyplates.dev/faq) | Thousands, EN/ES/SV, normalized quantities, steps, servings and nutrition. Keyed JSON API/MCP, OpenAPI documentation. Public website structured data is source material. | **B contract route.** Commercial runtime calls with credit/link allowed; bulk-copying index prohibited without agreement. Training/bulk requires contacting provider. Expiring request cache is not permission to build a corpus. No account/contact created. |

## Misleading aggregation and non-recipe exclusions

- [Global Recipe Database](https://github.com/drwjkirkpatrick-web/global-recipe-db/blob/main/README.md) advertises 75,321, but its 276 MB SQLite database is **not in Git**. Most records are attributed to [dpapathanasiou/recipes](https://github.com/dpapathanasiou/recipes); other rows repeat TheMealDB, Wikibooks and Food.com. Its table's MIT/“fair use” shorthand is not independent source-content clearance. The repository itself distinguishes script MIT from source data rights. Do not import unsupported blood-type-diet compatibility scores or inferred country labels as facts. This is a conditional aggregator, not 75k newly cleared recipes.
- Legacy Foodista RDF triples, nutrition databases, ingredient lists, image-only datasets, QA pair counts, review counts and recipe URL indexes are not interchangeable with full recipes. Require nonempty ingredients **and** actionable directions before counting a full recipe.
- An open parser or scraper (MIT/GPL) is useful tooling, not a license for all websites it can read. Schema.org markup describes structure, not reuse permission.

## Existing retained-corpus crosswalk

The published baseline at `maldous/offmenu`, commit `52b6a50a59b458bdb49fe7ea090b72c63a4b1a30`, `docs/world-recipe-research-20261014.json`, records:

| Existing accepted family | Records |
|---|---:|
| Wikibooks, 32 editions | 17,379 |
| Historical archive, work-level cleared subset | 6,192 |
| UniTools | 501 |
| based.cooking | 426 |
| HowToCook | 362 |
| Smithsonian OCR candidates | 256 |
| Taco Fancy | 18 |
| OpenRecipe specification example | 1 |
| **Total retained accepted scope** | **25,135** |

This comprises 24,879 full records plus 256 OCR candidates; neither equals current loaded production rows. Separate Wikibooks references are not extra full recipes. Foodista and ForkRecipe are not named accepted families in that baseline, but cross-row duplication remains possible. Full delta matching is deliberately deferred; these research artifacts do not claim that every candidate is new.

## Disabled preparation and future acceptance gates

`structured-recipes.json` is a **source-only, disabled declarative manifest**, not an executable fetch queue. Companion files under `fetch-preparation/structured-recipes/` contain a local validator, mocked records and adapter requirements; no network client or functioning acquisition path is installed. Every source is disabled. Global production permission is hard-false, and neither file existence nor eight booleans constitutes database readiness. **Any eventual production acquisition must execute on Foo only, after all eight databases are provisioned and verified relationally fit for the existing data.**

After the parent workstream supplies evidence-backed provisioning and relational-fitness readiness for all eight named databases on Foo **and** explicit activation, a separately reviewed acquisition layer would:

1. Validate scope/purpose, immutable source revision, exact approved URL inventory, content-license evidence and per-source conditions; no unbounded recursive discovery.
2. Prefer archived, checksum-pinned JSONL/JSON/CSV/Parquet to a new site crawl; enforce response/download limits, rate limits and declared budgets.
3. Preserve source ID, original URL, raw title/ingredient/step text, authors, language, license/version, collection timestamp, work/fork/translation lineage, raw date and transformation history. Keep licensed recipe prose partitioned from independently derived normalized facts.
4. Fail closed on unknown licenses, missing provenance, missing ingredients/steps, invalid URLs, unexpected executable syntax, or excessive expansion. Do not execute JS, Python/R-looking CSV values or repository scripts.
5. Deduplicate first by canonical source identity, then normalized content signatures; retain language variants/forks as linked records. Compare against retained—not just loaded—corpora.
6. Record offered, fetched, parseable, full, rights-eligible, deduplicated-new and accepted counts separately. Omit images/reviews/comments by default. Nutritional, allergen and safety assertions require independent quality controls.

### Exact pending issues (not permission denials)

- **Foodista/Common Pile:** recipe-only count, exact current shard names/checksums, section extraction success and row-level license exceptions remain unverified. Documentation and bounded samples completed; production acquisition pending eight-database readiness and activation.
- **ForkRecipe:** static JS parser and source-attribution/culinary review remain to implement; metadata count and one full sample completed.
- **Zenodo:** rendered record did not expose definitive license/sample schema; metadata clarification pending. No assertion that license is absent.
- **Recipe1M, RecipeDB2, filtered HF viewer:** endpoints rendered unavailable/sparse or erroring; do not work around access restrictions. Primary published documentation retained; exact terms/export unresolved.
- **Commercial APIs:** agreement/key/payment needs are not approvals already granted by this research request; nothing bought or accepted.

No platform permission-denial bypass was attempted. Sources whose pages failed were retained as uncertain, not described as successfully acquired.
