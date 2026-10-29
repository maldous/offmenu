# OffMenu complete research delivery programme

**Architecture amendment, 13 October 2026:** Full source releases and their
normalized copies stay LOCAL. Publish only OffMenu curation and indexes as static
Netlify files; Cloudflare performs read-only queries and caching. No Netlify
runtime functions or hosted source corpus database. The user's later instruction
supersedes contrary bulk-hosting sections below. See `curation-architecture.md`
for implementation, publication gates and exact cleanup state.

13 October 2026. Owner: Matt Aldous. Baseline: private `maldous/offmenu` main `c1b2bec`; deployed functional source `e57db23`. This plan replaces the assumption that building a directory or importer completes data delivery. It is a plan, not evidence that the following collection has run. Preserve existing account data, authentication, the provider vault and working product. UI/UX refinement remains a later feedback run; accessibility and reliable task completion are acceptance requirements now.

## 1. The outcome and the meaning of “full datasets”

Deliver the recommendations in all five research PDFs and all four registers as usable product capabilities backed by exercised data flows. Every recommendation receives a requirement ID, source reference, dependency, implementation, verification evidence and explicit disposition. Every one of the 1,303 research source entries and 249 ISO entries receives a delivery decision. No discovered source disappears because it is inconvenient or credentialed.

**Full means every eligible record in the named, versioned source release or every accessible page/cursor in the contracted endpoint scope.** It does not mean an arbitrary sample, the first 20 search results, a connector logo, or every food/product/menu in the world. Include the source's complete related tables and dictionaries needed to interpret those records. Historical versions, image assets and geographically restricted editions are separate scoped datasets with separate rights.

For a bulk source, acquire the whole permitted release, reconcile every row, retain permitted originals and expose useful normalized projections. For a query-only or private subscription service, fully exercise its documented capabilities, pagination and permitted representative workflows; do not pretend that query coverage is a bulk mirror. For a reference standard or discovery directory, implement or link the reference and record that it is not an ingestible product dataset. For an inaccessible source, retain the exact access/rights blocker and a concrete fallback. Unknown commercial reuse rights never become permission merely through normalisation, consent or anonymisation.

Programme completion has two separate statements: (1) all feasible work implemented and exercised; (2) every recommendation/source/country accounted for, including external blockers. A blocked source is not counted as delivered. Complete worldwide menus, quantities, ownership or certified suitability cannot be promised from the current research.

## 2. Current evidence and the gap

| Current baseline | What remains to deliver |
|---|---|
| 249 indexed countries; 1,303 source entries; 1,400 applicability links | Source-by-source access verification and collection; field-level operational coverage per country |
| 15,312 composition records across AFCD/Ciqual/CoFID/BLS | Reconcile each against its actual full release; identify missing tables/fields/releases; expand eligible national datasets |
| Live barcode lookup and dated prices | Full permitted OFF product release, supporting taxonomies and refresh; complete eligible price/retailer releases |
| 70 recipes, 31 quantified concepts | Independently reviewed starter pack, full licensed recipe acquisition, quantified ingredient mappings, prepared-state composition and publishable projections |
| GLEIF/Wikidata live candidates and warm cache | Bulk identity/relationship evidence, dated product-brand-company joins, origin/certification/recall/regulatory sources |
| Basket arithmetic and privacy/scoping controls | Real source-defined quantities, reviewed food matches, full metric/food-group/cost/reference workflows |
| Private health import, cooking/leftovers and scoped APIs | Native bridges and vendor adapters; real two-device/offline, external-client and independent review acceptance |
| 106 JavaScript / 7 Python tests and live selected workflows | Collection-to-feature acceptance for each delivered source, complete-release reconciliation, refresh/deletion/recovery tests and coverage reporting |

Existing counts are checkpoint evidence, not proof that every national release or nutrient table is complete. Do not replay existing imports until this comparison identifies an actual delta.

## 3. Dependency order and release gates

| Stage | Work and concrete output | Completion gate |
|---|---|---|
| A — Traceability and source decisions | Recommendation register; source delivery ledger; country matrix; deduplicated provider/endpoints without losing original IDs | All five PDFs and four registers mapped; every source/country has an owner, role, scope and next action |
| B — Collection platform and rights | Versioned policies, grants, quota budgets, raw-release metadata, resumable collectors, staging/quarantine, run accounting and refresh/invalidation | Live small run, interruption/resume, full-run accounting, idempotent replay, withdrawn source and cross-account tests pass |
| C — Open foundations | Full permitted barcode/product, price, composition, vocabulary and identity releases; related tables; normalized indexed projections | Whole releases acquired/reconciled; original and normalized lineage retained; lookup/scan/food-entry workflows use the imported records |
| D — Meals, menus and household use | Reviewed recipes; authorized venue/POS menu feeds; quantities, modifiers, suppliers and actual stock/consumption linkage | Source → recipe/menu → servings → stock gaps → cook → eat/save/waste → history/export works on real collected data |
| E — Enrichment, qualifications and comparisons | Brand/company/control, origin, certifications, recalls, regulatory rules, country baskets, dietary definitions, compatible nutrition/cost comparisons | Known, missing, expired and contradictory evidence behave correctly; strict unknowns cannot be selected automatically |
| F — Credentialed and native integrations | BYOC/partner adapters, merchant feeds, retailer handoff, OCR/receipts, vendor health and native bridges | Real issued credentials and authorized devices exercise each advertised capability; disconnect and downstream invalidation pass |
| G — Broad country coverage and product maturity | Every country's national/local leads processed; localization, accessibility, recovery, care/creator/governed sharing and promotion recommendations | Coverage and blocked work published accurately; independent pilots/review; source and deployment checkpoints retained |

Release useful increments throughout one programme. Do not wait for inaccessible commercial providers to finish open-data lanes. A single run may span resumable bulk jobs; it must not restart from zero after interruption.

## 4. Dataset delivery by domain

| Domain | Collection scope and sources to process | Normalized output and actual OffMenu use |
|---|---|---|
| Barcodes and product versions | Entire eligible Open Food Facts release; product/ingredient/allergen/label taxonomies and translations; USDA branded foods; approved GS1 NPC/Trusted Content/DataKart/member feeds; licensed manufacturer/retailer releases | Original barcode + canonical GTIN, market/pack/label revision, ingredient/allergen observations. Scanner/manual lookup, fridge inventory and food matching use locally served records; unknown codes remain usable |
| Generic food composition | Reconcile full AFCD, Ciqual, CoFID and BLS releases; full eligible USDA Foundation/FNDDS/SR Legacy/Experimental and supporting tables; AUSNUT/CNF and every national lead in the 249-country register after rights review | Source food IDs, 45 canonical metrics, all additional original nutrients, analytical method, qualifiers, state, portions, densities/yields/retention. Loose foods, actual-lot recipe estimates, health history and basket comparisons |
| Food identity and vocabularies | Complete eligible FoodOn/ChEBI/INFOODS reference resources; source taxonomies, Unicode names and regional aliases; original 337 proposed concepts reviewed and expanded | Many-to-many concept/source/product mappings with evidence and locale. Search, ingredient substitution and composition matching; ambiguous candidates stay unresolved |
| Recipes and prepared meals | Full permitted Wikibooks recipe release and other rights-cleared creator/manufacturer packs; original recipes; licensed recipe APIs through approved grants | Recipe versions, original instructions/attribution, quantified ingredients, optional substitutions, process, measured yield and portions. Default recommendations include only feature-ready recipes; incomplete recipes remain searchable review work |
| Restaurant menus and venue/provider data | Authorized merchant exports and Shopify/WooCommerce/Open Food Network/POS routes; approved Clover/Lightspeed/merchant/platform APIs; permitted menu/Recipe JSON-LD; licensed business directories | Venue/operator/site IDs, menu-item/version, recipe/portion/modifiers/allergens, supplier links and availability dates. Restaurant meal selection, intake logging, dietary checks and equivalent shopping/cooking options. Unspecified ingredients remain unknown |
| Retailers, prices and availability | Complete eligible Open Prices tables; contracted regional product/offer feeds; reviewed personal receipts and browser imports; approved WhichGrocer/Kroger/Instacart/merchant integrations | Separate product, store, SKU, offer/observation, dated price, currency/tax/loyalty/pack/delivery conditions. Shopping gaps, pack rounding, unit price, budget comparison and retailer handoff; observed price is not current availability |
| Companies, providers and ownership | Full GLEIF Level 1, Level 2 and reporting-exception releases; full permitted Wikidata release with relevant business projections; national registries/filings/trademarks, approved establishment lists, cooperatives/grower directories and licensed vendors | Business/brand/site/producer identities, dated control/consolidation/minority/franchise/licence edges, fiscal-year size/background assertions. Explain product-to-owner paths, independent/local preferences and supplier evidence; name matches stay candidates |
| Origin and supply chain | Package/manufacturer declarations; licensed traceability/EPCIS/Digital Link or supplier data; producer/site/commodity certificates; independently obtained official evidence | Separate grown/raised/caught, manufactured, processed, packed, distributor, ingredient-origin and headquarters fields, scoped to market/product/lot/date. Origin filters never use a barcode prefix or aggregate trade pattern as proof |
| Diets, allergens and qualifications | Country guidance and rule definitions; scheme/certifier/operator/product directories for halal/kosher/organic/non-GMO/gluten-free and supplier safety; actual labels/menu disclosures | Versioned dietary preference versus legal/certified claim; scheme/issuer/scope/validity, contains/may-contain/absence and cross-contact distinctions. Household meal filters, substitutions and pass/fail/unknown/conflict with visible evidence |
| Recalls and regulatory provisions | Full eligible official country feeds/releases, including FSA/RappelConso and reviewed AU/NZ/Canada/EU routes; historical openFDA kept separate; primary additive/legal texts and transitions | Regulator/event/product/GTIN/lot/market dates and action links; jurisdiction/category/substance/limit/exceptions/effective interval. Inventory warnings and qualification invalidation; history is not a live alert service |
| Country baskets and reference comparisons | Every country's published basket/source; original 2,523 editorial and 707 published-example lines; available primary quantity tables; authorized statistical/price/guideline data | Separate editorial, published price/basic-needs, acquisition, consumption and food-supply tracks. Review quantities/state/population/period; match foods/products/menus, calculate nutrient/group/cost views and create actual shopping plans |
| Health, activity and personal evidence | Consented manual/file imports; approved vendor OAuth/export paths; Android Health Connect and Apple HealthKit companion bridges; clinical-entered plans only with separate governance | Account-private dated measurements and sources, deduplication, overlapping device periods, source consent and exports/deletion. Descriptive trends and chosen goals; no treatment/dosing or child deficit prescriptions |

“Full” does not discard unsupported fields: preserve permitted original values even when they do not yet have a canonical mapping. Every unresolved field or record has a reason and a review route. Images, label photos, proofs and personal payloads have independent permission/retention decisions; a data licence is not an automatic image licence.

## 5. Collection and storage architecture

Retain the existing Worker/D1 serving layer, identity provider and encrypted vault. Add a dedicated collection plane; do not parse worldwide releases inside an interactive HTTP request or place every raw global record into a single operational D1 database.

Use long-running resumable batch workers on available compute for downloads, streaming decompression, schema discovery and normalization. Store only permitted immutable raw releases and compressed normalized partitions in object storage, with checksums, source/release IDs and access partitions. Use D1 for policies, grants, jobs, release manifests, review decisions, fast operational indexes and demanded feature projections. Select an additional catalogue/search database or partitioned query service only after measured sizes/query needs show it is necessary. Record this decision before a platform change; object storage is not itself a search engine.

Queues carry opaque job/source/grant IDs and cursor references, not credential values or unapproved raw personal payloads. Public/licence partitions remain separate from account/organization/private entitlements. Physical deduplication must not merge access rights. Store quota/spend budgets per actual provider/grant; honor rate limits, conditional requests and release/delta feeds. Do not rotate users' keys to evade quotas.

Every collector implements discover release → preflight permissions → live dry run → whole-scope acquisition → resumable staging → validation/quarantine → normalization → indexed publication → product exercise → refresh/withdrawal. Save progress at file/partition/page boundaries. An expired grant stops work and output publication, including queued jobs.

## 6. Normalization contracts

Keep existing schema compatibility through additive migrations and versioned adapters. Core joins are:

`source release → source record → field assertion → product/food/recipe/menu version → lot/serving → offer/provider → qualification → calculation/history`

Preserve original names/IDs and leading zeros; validate GTIN checksums without treating them as authenticity. Keep country of source, market, legal jurisdiction and manufacturing origin distinct. Use stable internal IDs plus source-specific aliases, not one universal food name.

For nutrition, preserve source code/value/unit, per-100g/ml/portion basis, raw/cooked/drained/reconstituted state, analytical definition and method, source dates/version, fortification, edible fraction, density, unit mass, yield and nutrient-specific retention. Preserve missing/not-tested/not-detected/trace/below-quantification/rounded-zero/conflict separately. Do not silently map carbohydrate definitions, vitamin A RE/RAE/IU, folate/DFE or incompatible fibre/energy methods into one number.

Dietary, certification, company, origin and safety assertions carry subject identity, predicate, evidence class, issuer, scope, market, effective/fresh/retention dates, rights revision, input dependencies and review. Derived outputs inherit every required input restriction and invalidation dependency. User assertions do not become independently verified simply by import.

Baskets support totals, per-100g, per-1,000 kcal, analytical 2,000-kcal equivalent, documented person-days, declared servings and named versioned reference profiles. Food-group fractions are evidenced, non-overlapping and versioned; missing mass remains unallocated. Cost comparisons retain date, currency, geography, outlet, tax, fees and promotion; FX and PPP are separately named methods. No overall healthiest-country ranking or invented national quantities.

## 7. What “fully exercised” requires

A delivered source needs a retained evidence package. Do not accept a mocked adapter, a single API response or a count of registered URLs as completion.

| Gate | Required proof |
|---|---|
| Access and rights | Real endpoint/release retrieved; edition, market, entitlement, permitted actions/audiences/fields/retention and required attribution recorded |
| Whole-scope collection | Exhaust all eligible files/pages/cursors; record byte checksums and source totals. If provider reports no authoritative total, mark completeness as traversal-verified, not independently count-verified |
| Reconciliation | `raw records = accepted + duplicates + quarantined + explicitly excluded`; every category has reason codes. Validate every required relational file and orphan join |
| Repeatability | Same release re-run makes no duplicate facts/stock events; deterministic normalized output; source/schema drift produces review rather than silent field loss |
| Recovery and freshness | Interrupt/resume succeeds; next release/delta updates correct records; deletes/withdrawals/retention expiry and dependency invalidation tested |
| Functional use | At least one real domain-specific consumer workflow uses collected normalized records and preserves lineage, unknowns and source rights |
| Isolation and export | Two account/grant/market scopes cannot cross-read; consent/disconnect/revocation works on reads, exports, search and derivatives |
| Operational evidence | Measured parsing time, memory, storage, ingest cost, lookup latency, cache effect, failure/quota behavior and last successful refresh; release/source/deployment IDs retained |

Run quantitative fixtures and full-record structural validation as appropriate. Test boundary cases deliberately: leading-zero GTIN; duplicate packs; raw versus prepared food; unknown vitamin C; compound allergen/cross-contact; inconsistent ownership dates; all-batch versus lot-specific recall; personal loyalty price; expired certificate; revoked grant; multilingual names; offline duplicate receipt; concurrent cooking/serving. Physical devices, recipes and medical/nutrition interpretation require independent human/device acceptance in addition to automation.

## 8. Product recommendations beyond collection

| Workstream | Recommendations included and functional acceptance |
|---|---|
| Capture and reliable inventory | Produce/manual/unknown foods; front/rear camera and hardware-scanner alternatives; reviewed receipt/label OCR; duplicate receipt handling; opened/frozen/thawed and partial/decanter lots; private labels; location-aware review/cleanup and undo. Received stock remains distinct from shopping intentions |
| Meal and household planning | 30 independently reviewed quantified starter meals and at least 100 useful mappings as the initial floor, followed by complete rights-cleared packs; attendance, lunchboxes, reusable weeks, swaps, batch cooking, equipment/time/budget, preferences/feedback and explicit substitutions. Quantities and safety unknowns are visible |
| Cooking and observed consumption | Actual ingredient-lot allocation and substitutions; measured batch/yield; per-diner serving, eaten/saved/shared/discarded/unknown events; useful leftovers; date-aware reservations. No duplicated raw deductions or misleading zero-intake entries |
| Collaboration and continuity | Independent owner/editor/viewer accounts, household and individual scope, multiple kitchens/homes/care handover, deterministic conflicts, durable offline queue/recovery, revocation, shared-device logout and account lifecycle/deletion |
| Statistics and comparison | Nutrition coverage, drinks/snacks/manual/restaurant history, frozen provenance, explicit personal goals, variety/organization rewards, waste quantity/value with methodology, budgets/unit prices/pack leftovers and dated basket alternatives. No rewards for children finishing food or unsupported savings/environmental claims |
| Portability and assistants | Versioned JSON/CSV, Recipe/ItemList JSON-LD, print/EPUB, calendar/reminders exports, QR/hardware input, documented REST/MCP, actual external-client tests. Any future write capability gets a separate scoped preview/confirmation/audit contract |
| Accessibility/localization | Keyboard/screen-reader/reflow/contrast/large-target/reduced-motion/quiet alternatives; actual imperial and regional cup/spoon conversion; Unicode/locale strings, RTL, language metadata and country packs; Android/iPhone/older phones/tablets; poor network and denied camera |
| Trust and governed sharing | Support, issue reporting, status/recovery, attribution/licences, truthful availability, consent and contribution management, retention/deletion/withdrawal, account/organization/profile controls. Field-level promotion only after source/privacy gates; behavioral aggregates require their own approved release rules |
| Promotion and partnerships | Five-food-to-dinner demonstration, supported-device/market statements, creator packs with rights, household invitation, factual search content, waste/budget pilots, technical MCP demonstration and disclosed referrals/sponsorship. Measure activation, repeated meal outcomes, reliability, effort and operating margin |
| Expansion and governed care | Taste/culture/texture/spice, seasonal menus, producer background/size, care/professional time-limited sharing, vendor health/native bridges and moderated creator/community features. Clinical/IDDSI/disease workflows need separate qualified validation and intended-purpose assessment |

The research explicitly recommends deferring automatic purchases, glucose/medication dosing, disease treatment, smart-fridge dependence and a full social network. Record these recommendations as deferred by design, rather than silently dropping them or declaring them delivered. Paid contracts, clinical approvals, native permissions and partner access are genuine dependencies, not completed integrations.

## 9. Country delivery and honest coverage

Maintain one row for every ISO entry, including territories. For each domain record: applicable sources, collection scope, verified access/rights, release IDs, ingested and usable records, field completeness, language/mapping state, freshness, feature exercises and blockers. Global feed applicability is not local completeness. Source country, destination market and jurisdiction do not substitute for one another.

Start all open global foundations first, then process national/local leads in evidence/access order across the entire 249-entry matrix. Ship country packs only after local food matches, units, licensed data, diet/retailer capabilities and workflow acceptance pass. No-country-specific source becomes a explicit gap with the best permitted fallback, labelled proxy where appropriate. Preserve AQ/BV/GS/HM/IO/TF/UM as special provisioning contexts without fictional household defaults.

The country starter and published basket tracks must remain separate. Extract exact primary quantities where available; otherwise maintain unresolved fields. A local review of alternatives, preparation and edible basis precedes nutritional comparison. Obtain quantities rather than manufacturing them to fill a dashboard.

## 10. Eight execution lanes and scheduling

This is a delivery organization, not a claim that eight agents are running. Use available workers within measured shared-resource and provider limits; refill lanes with useful independent work.

| Lane | Primary output | Dependency |
|---|---|---|
| 1 — Requirements/rights/operations | Complete recommendation/source/country registers; decisions; quota/resource scheduling | Starts immediately; ongoing gates for all lanes |
| 2 — Products/barcodes/prices | Full open product/offer acquisition, identifier and retailer projections | Collection platform; source policies |
| 3 — Composition/vocabulary | Full eligible nutrient releases, multilingual identity, state/quantity conversions | Collection platform; source policies |
| 4 — Recipes/menus/providers | Rights-cleared recipe/menu packs, venue feeds, quantities and supplier links | Identities; composition; permissions |
| 5 — Companies/origin/qualifications | Full identity/relationship evidence and regulatory/certification/recall pipelines | Policies; identifiers; dated evidence |
| 6 — Household/use/statistics | All collected data exercised through planning, stock, cooking, consumption, baskets and exports | Incremental outputs from lanes 2–5 |
| 7 — BYOC/native/country integration | Credentialed adapters, device bridges and remaining country leads/locales | Issued access, device permission, established contracts |
| 8 — Independent acceptance/release | Full reconciliation, source-to-feature checks, privacy/recovery, device/reviewer coordination and deployment evidence | Every publishable increment; review independent of implementation |

Do not impose arbitrary “first N countries/records” stopping rules. Use resumable partitions and evidence-driven ordering. Heavy download/parse/index jobs share a measured capacity queue; independent source research, policy work and product integration proceed concurrently. An external blocker moves its lane to an unblocked source/capability while retaining the blocked item and exact owner action.

## 11. First execution batch and estimates

The first batch must (1) freeze the requirement/source/country registers, (2) benchmark release sizes and processing/storage costs, (3) complete source policies for the first full open releases, (4) build the reusable job/reconciliation/normalization platform, and (5) execute full OFF + USDA releases and reconciliation of the four existing national composition sources. Start recipe/menu, ownership and country permission work alongside it. Immediately connect completed records to scanner, loose-food entry, cooking, menus and comparisons; do not postpone consumer use until the end.

Estimate effort after live dry runs and access checks: give separate engineering, download/compute, review and external wait estimates per work package. There is no defensible fixed date for all 1,303 leads before this triage. Publish a critical-path forecast after the first full-release and provider-credential exercises; update it with measured throughput. Record prospective paid compute/provider spend before committing to a paid agreement. No work in this planning request changes production or starts bulk collection.

## 12. Reporting and final acceptance

Use statuses: **unassessed → scope/rights review → access ready → collector exercised → full scope reconciled → normalized → feature exercised → independently accepted → maintained**, with explicit blocked/deferred/reference-only/not-applicable alternatives. Preserve historical research discovery status separately.

At each checkpoint report release IDs, raw/accepted/quarantined/excluded counts, field and country coverage, actual feature exercises, refresh state, costs, active jobs and exact blockers. Every “delivered” claim must name the source/release and workflow proof. Keep source files, policies, schemas, transformations and result versions in Git; large licensed payloads stay in the appropriate data store; no credentials or private snapshots in Git.

Final acceptance requires all applicable recommendation IDs resolved, all sources/countries accounted for, all delivered collections reconciled and used, and all unresolved access/licensing/native/clinical/device constraints explicitly stated. Keep the live acceptance register and operational coverage dashboard authoritative. The earlier directory/workspace release is the foundation for this programme, not the completion of it.

## Research traceability and current bulk-source references

- `docs/research/reports/01-OffMenu_Basket_Normalization_Addendum.pdf`: quantity/state/edible basis, 45 metrics, 17 groups, seven comparison views, costs, qualifications and reproducibility.
- `docs/research/reports/02-OffMenu_Product_Review_and_Plan-1-.pdf`: P0/P1/P2 feature portfolio, datasets/integrations, household routine, privacy/safety, accessibility/locales and promotion/pilots.
- `docs/research/reports/03-OffMenu_Enrichment_Discovery_249_Countries.pdf`: identity, companies/growers/providers, origin, ownership, certification, regulatory and recall evidence; all country leads.
- `docs/research/reports/04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf`: field-level rights, resolver partitions, grants, refresh/invalidation, contribution, privacy and collection/reuse acceptance.
- `docs/research/reports/05-OffMenu_Global_Shopping_Baskets.pdf`: all country findings and separation of editorial/statistical/basic-needs/meal-planning baskets.
- All four `docs/research/OffMenu*.json` registers and `docs/research/manifest.json` remain the original evidence baseline; the accompanying delivery ledger adds status without rewriting research.

Primary documentation checked 13 October 2026:
- [Open Food Facts API/reuse guidance](https://github.com/openfoodfacts/openfoodfacts-server/blob/main/docs/api/index.md): use bulk exports for large acquisition; verify database, contents and image rights separately.
- [USDA complete datasets](https://fdc.nal.usda.gov/download-datasets/): select current complete releases and their related tables, rather than query samples.
- [Open Prices public exports](https://openfoodfacts.github.io/open-prices/guides/import-data/): prices, locations and proofs are separate export inputs; assets/privacy still need their own admission.
- [GLEIF Golden Copy and deltas](https://www.gleif.org/en/lei-data/gleif-golden-copy/download-the-golden-copy): collect Level 1, Level 2 and reporting exceptions; relationships describe accounting-consolidating parents.
- [Wikidata dumps](https://www.wikidata.org/wiki/Wikidata:Database_download): release and incremental acquisition, followed by scoped feature projections and temporal evidence review.
