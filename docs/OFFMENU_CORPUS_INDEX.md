# OffMenu corpus and research index

## Source catalogue

This is the navigation point for OffMenu's **whole recorded source programme**, not just the early CLI importers. It brings together the existing discovery registers, retained-release mappings, app directory and later recipe/country evidence without replacing their source IDs or creating another delivery ledger. This navigation was reconciled against repository commit `0f518f5a75a30d1fd49aed8e524a751bc5ace941` on 25 October 2026; the underlying records retain their own dates.

The inventories overlap. A provider can have several releases, endpoints or country records, and a source can appear in several inventories. There is not yet one reconciled, deduplicated total covering every discovery, later portfolio and private holding. **Do not add the counts below or describe them as the number of collected, qualified or live datasets.**

### Registers and evidence layers

| Existing catalogue or record | What it covers | What it does not establish |
| --- | --- | --- |
| [Canonical source delivery ledger](source-delivery-ledger.json) | 1,303 named discovery entries, original IDs, URLs, research references and access-check evidence. | All 1,303 carry `landing-page-access-checked`; the inherited defaults leave collection, normalization and feature use unverified. An accessible page is not a collected dataset. |
| [Global data-source register](../research/OffMenu_Global_Data_Source_Register.json) | 365 source records, 36 global-provider summaries and country-specific discovery routes. | The records include directories, commercial services, authorities and leads, not only downloadable databases. |
| [Enrichment register](../research/OffMenu_Enrichment_Source_Register_249.json) and [country basket register](../research/OffMenu_Country_Basket_Register.json) | The original country-by-country research behind product enrichment, ownership, certification, safety and shopping-basket work. The enrichment register records 78 global entries and 947 country source/gap entries, with 938 URL references; its recorded integration-tested flags are all false. | A route assigned to a country is not evidence of national completeness or permitted collection. |
| [Common-source mappings](../corpus/common-source-mappings.json) | 22 named historical release mappings, listed below, with original types and historical counts. | Declarative mapping and historical counts do not verify today's payload, semantic acceptance, current publication or runtime use. |
| [Historical handler capabilities](../offmenu/refresh/capabilities.py) and [coverage assessment](global-coverage-assessment.md) | Bounded links between those releases, discovery IDs and historical collector/normalizer implementations. | A source-family match is not an exact release/format match. This compact registry is not all later portfolio code. |
| [App source directory](../public/sources.js) | 54 entries covering data sources, optional personal services, user imports and formats; all names are indexed below. | Its existing labels such as “Live lookup” or “Integrated” are not an independent current-runtime verification. Formats and personal imports are not external providers. |
| [World recipe report](world-recipe-research-20261014.json), [recipe expansion](recipe-expansion-20261014.json) and [later recipe discovery](global-recipe-source-discovery-20261014.json) | Named repositories, language editions, book collections, exclusions, historical output and later metadata-only leads. | They have different dates and stages; their source sets are not completely represented by the original discovery ledger. |
| Later country catalogues and bindings, indexed below | Source/release declarations, retained-evidence references, parser boundaries and explicit holds for country portfolios. | Metadata in code is not a new acquisition, a fresh body-integrity check, a permission grant or production admission. |
| [Operation-specific permissions evidence](source-release-permissions-evidence.json) and [source acceptance contract](source-acceptance-contract.md) | Conditions and evidence for discovering, fetching, retaining, parsing, transforming, serving and redistributing a particular release. | The 22 permissions records explicitly do not verify acceptance, payload digests or executable admission. A known licence label alone is insufficient. |

### How to read source status

- **Documented candidate:** a named source, reference or route has been recorded. No collection follows from a URL or successful landing-page check.
- **Historically collected:** a dated receipt or manifest records acquisition of a particular asset set. This catalogue preserves that claim; it has not re-read private source bodies or reverified their hashes.
- **Parsed or mapped:** keep adapter availability, an actual historical parser run and a declarative schema mapping distinct. Each has a narrower scope than a usable product feature.
- **Qualified candidate:** a dated report can establish bounded structural/rights checks for a named local package. That is not universal semantic correctness, current publication, or live app acceptance.
- **Restricted, held or excluded:** an independent condition, not a step to skip. Metadata may be retained while collection, transformation or redistribution is prohibited or unresolved.
- **Verified live:** requires separate current deployment, authorization and feature evidence. This documentation reconciliation grants no source that status.

### The 22 historical mapped releases

All rows below come from the existing common-source mappings. Names and releases identify historical evidence, not fresh downloads or universal coverage. Original count and qualification details remain in the linked records rather than being presented as today's corpus size.

| Source | Stable source ID | Historical release |
| --- | --- | --- |
| Open Food Facts | `off` | `2026-10-12` |
| USDA FoodData Central downloads | `usda-files` | `usda-2026-04` |
| Open Prices | `prices` | `2026-10-12` |
| Australian Food Composition Database | `afcd` | `3` |
| ANSES CIQUAL | `ciqual` | `2025` |
| UK CoFID | `cofid` | `2021` |
| Germany BLS | `germany-bls` | `4.0` |
| Norwegian Food Composition Table | `matvaretabellen` | `2026` |
| DTU Frida | `frida` | `5.5` |
| Wikidata food-business references | `wikidata-food-businesses` | `2026-10-13-direct-types` |
| FAO national dietary-guideline directory references | `dietary-guidelines` | `fao-directory-20261013` |
| Wikibooks retained revisions | `wikibooks` | `2026-10-13-live` |
| Canadian Nutrient File | `cnf` | `2015` |
| Japan MEXT food composition | `mext` | `2023-corrected-20260327-main` |
| Overture food places | `overture-food-places` | `2026-09-23.1` |
| Fineli | `fineli` | `20.0` |
| New Zealand FOODfiles | `foodfiles` | `2024-v01` |
| Swedish Food Composition Database | `sweden-food` | `2026-07-01` |
| Worldwide recipe collection (several publishers) | `world-recipes` | `world-recipes-common-20261014` |
| FoodOn | `foodon` | `2026-09-20` |
| QUDT selected measurement definitions | `qudt-measurement-definitions` | `qudt-measurement-definitions-3.5.2-20261014` |
| Additional recipe repositories (qualified local package) | `recipe-expansion-20261014` | `recipe-expansion-qualified-20261014` |

### App-directory names

These are all 54 entries in the current source-directory file, grouped for reading rather than promoted to a common delivery status. Country editions, public downloads and personal APIs remain distinct.

- **Products:** Open Food Facts (`off`); GS1 India DataKart (`india-datakart`); GS1 Russia (`russia-gs1`).
- **Nutrition and composition:** Swedish Food Composition Database (`sweden-food`); Norwegian Food Composition Table (`matvaretabellen`); USDA FoodData Central (`usda`); USDA downloadable datasets (`usda-files`); Australian Food Composition Database (`afcd`); AUSNUT (`ausnut`); UK CoFID (`cofid`); Canadian Nutrient File (`cnf`); ANSES CIQUAL (`ciqual`); New Zealand FOODfiles (`foodfiles`); Fineli (`fineli`); DTU Frida (`frida`); RIVM NEVO (`nevo`); MEXT food composition (`mext`); TBCA (`tbca`); China CDC food composition (`china-cdc`); ICMR-NIN IFCT (`india-ifct`); Indonesia TKPI (`indonesia-tkpi`); Russian nutrition composition centre (`russia-nutrition`); Germany BLS 4.0 (`germany-bls`).
- **Recipes:** Worldwide recipe library (`world-recipes`); Wikibooks Cookbook (`wikibooks`).
- **Prices and shopping:** Open Prices (`prices`); WhichGrocer (`whichgrocer`); Instacart (`instacart`); ALDI country portals (`aldi`); DoorDash (`doordash`); Kroger (`kroger`).
- **Places, companies and guidance:** Overture food shops and venues (`overture-food-places`); Wikidata food business references (`wikidata-food-businesses`); National dietary guideline references (`dietary-guidelines`); FAO / INFOODS directory (`infoods`).
- **Food notices and inspections:** China SAMR food inspections (`china-samr`); Indonesia BPOM (`indonesia-bpom`); France RappelConso (`france-rappelconso`); UK FSA food alerts (`fsa-alerts`); UK food hygiene ratings (`fsa-ratings`); openFDA food enforcement (`openfda`); FSANZ recalls (`fsanz-notices`); Canada recalls (`canada-notices`); EU RASFF (`rasff`).
- **Optional food APIs:** Spoonacular (`spoonacular`); Edamam (`edamam`).
- **Personal health/activity connections:** Google Health (`google-health`); Android Health Connect (`health-connect`); Apple HealthKit (`healthkit`); Strava (`strava`); Garmin Health (`garmin`).
- **Private imports and formats:** Your retailer browser session (`retailer-browser`); Open document & data formats (`schema`); Your files & receipts (`personal-import`).

### Wider research and enrichment names

The full named lists and country associations remain in the discovery/enrichment registers above. Their additional global routes include GS1 GDSN/certified pools (including 1WorldSync and Syndigo), GS1 Australia Trusted Content/National Product Catalogue/Smart Media, NIQ Label Insight/Brandbank, fatsecret, Nutritics, EFSA's EU Food Composition Database, EuroFIR FoodEXplorer/EMR, SPC's Pacific Nutrient Database, West African and Congo Basin tables, INCAP and Caribbean tables, FAO FPMA, WFP/HDX, Square, Toast, Deliverect, Uber Eats, Wolt, OpenStreetMap, Google Places, FAO AGROVOC, USDA FoodKeeper and Withings. These are recorded routes with source-specific conditions, not a list of connected services.

Enrichment research also names GLEIF, OpenCorporates, Companies House, Open Ownership, ChEBI, Codex/FAO JECFA and regulator additive references; USDA Organic INTEGRITY, EU TRACES and national organic registers; FLOCERT/Fairtrade, Rainforest Alliance, RSPO, ASC, Soil Association, BioGro and Bio Suisse; JAKIM, MUIS and BPJPH halal registers; OU Kosher; Vegan Action and Vegan Australia. The underlying country records preserve the remaining national authorities and issuers. None of these names alone establishes an ingredient equivalence, product certification, ownership chain, origin or safety conclusion.

### Recipe collections and explicit exclusions

- The [world recipe report](world-recipe-research-20261014.json) names `Anduin2017/HowToCook`, `LukeSmithxyz/based.cooking`, `sinker/tacofancy`, `recipecommons/openrecipe-spec`, `farcrak/unitools-recipes` (UniTools), `AdamBouhmad/open-recipe-archive`, Wikibooks and Smithsonian archived book texts. It records historical acquired scope and accepted/excluded counts, not exhaustive worldwide or current coverage. Wikibooks language/edition counts are not country coverage.
- The [expansion report](recipe-expansion-20261014.json) separately names `lvisintini/recetasdemami`, `Remarknl/Indisch-eten`, `chefdelakarma/libre_cuisine`, `clicat/Ricette` and `rochacbruno/vegan_recipes`. Its status is historically **qualified locally, not published**; the last source contributed zero accepted recipes in that report. Quantity and semantic suggestions remain candidates.
- The [later discovery report](global-recipe-source-discovery-20261014.json) records acquired Wellcome **metadata and IIIF manifests** for *The Indian cookery book* and *The English-Chinese cookery book*, not acquired recipe text. Library of Congress leads include *Mandarin chop suey cook book* and *California Mexican-Spanish cookbook*; those works were not acquired by that report.
- The historical source notes and reports explicitly hold or exclude RecipeNLG, Usenet `alt.gourmand`, `rec.food.recipes`, Recipe1M/unlicensed Kaggle collections and `Gar-b-age/CookLikeHOC` for their stated restrictions or unresolved rights. `bbbenji/awesome-recipes`, `jzarca01/awesome-food` and `fictive-kin/openrecipes` are discovery/bookmark routes, not admitted recipe corpora. Wikipedia dish articles are identification references, not recipe instructions. Archive access or a repository wrapper does not clear third-party text or images.

### Later country-source evidence

Later portfolios extend beyond the early ledger and 22-release map. Examples include Brazil TACO; Portugal PortFIR; Czech NutriDatabaze; Cyprus composition tables; country recipe books, school menus and individual restaurant menus; OpenDOSM PriceCatcher and national CPI/household-budget publications. The retained metadata also names Statistics Canada, Luxembourg STATEC, St Helena inflation, Colombia DANE/SIPSA and TCAC, Sweden Konsumentverket, Kiribati NSO, Réunion INSEE, Maldives MBS and World Bank Sudan price estimates. This is evidence of a broader programme, not a claim that every listed input is parsed or permitted for reuse.

The following links navigate existing declarations and evidence guides. They are **code/document files, not dataset counts**. Preserve their source IDs, recorded acquisition dates, denied operations and review holds; do not substitute a fresh blanket “collected” label. Mirrored catalogues and configuration files can describe the same source. The small synthetic fixture registry is not a universal source registry.

<details>
<summary>Named additions from later country declarations</summary>

| Recorded source names | Existing evidence | Boundary in that evidence |
| --- | --- | --- |
| Bahrain BFM recipe catalogue/cookbook lead; Kiribati NSO CPI; Live & Learn recipe lead; Réunion INSEE | [`offmenu/portfolio_worker09_sources.py`](../offmenu/portfolio_worker09_sources.py) | Metadata/reference-only; source retention/use unknown; recipe lead403 and INSEE no-original holds remain. |
| PortFIR; O Sargo menu; Sint Maarten CPI; Turkish fruit-composition research; Bagatelle menu | [`offmenu/refresh/portfolios/worker38_sources.py`](../offmenu/refresh/portfolios/worker38_sources.py) | Source-use, exact selectors and release applicability unqualified; PortFIR original-not-acquired explicitly held. |
| Konsumentverket Hushållskostnader2026; Malawi historical IYCN recipe; Senegal IRD digital edition; Palau paper leads | [`offmenu/refresh/portfolio_owner51.json`](../offmenu/refresh/portfolio_owner51.json) | All productionAccepted/goldAdmitted false; Palau access denied; Swedish amounts are household reference costs, not merchant offers or nutrient composition. |
| Maldives MBS CPI August2026; World Bank Sudan market food-price estimates; San Marino CPI; Puerto Rico laboratory-table lead | [`offmenu/portfolio50/profiles.py`](../offmenu/portfolio50/profiles.py) | Metadata-only; source-body operation not selected, use not qualified. Sudan estimates and receipt market-count conflict retained. |
| Liechtenstein Statistik agriculture; ATNI Lao CPCF; Lebanon CAS CPI; Cayman discovery references | [`offmenu/refresh/portfolio47_sources.json`](../offmenu/refresh/portfolio47_sources.json) | Explicit no real source admission, runtime registry enablement or SourceContract construction. |
| DOSM Malaysia cpi_2d; Botswana/Gabon/Cambodia held source references | [`offmenu/refresh/portfolio55.json`](../offmenu/refresh/portfolio55.json) | Malaysia aggregate CPI; other country/type bindings unqualified. Not physical basket quantities or prices. |
| Côte d'Ivoire ANADER farmgate years2021–2023; Cook Islands tourism standards and menu; Chile INE CPI manual; Cameroon Pélé/Le Berre | [`offmenu/refresh/portfolios/worker23.json`](../offmenu/refresh/portfolios/worker23.json) | Retained-metadata-staging-only; Cameroon printed1966/embedded1967 conflict retained. |
| WFP Ghana and Guinea Food Prices; Gambia Statistical Abstract2024; Ghana recipe thesis; Gibraltar discovery | [`offmenu/refresh/worker33_portfolio.json`](../offmenu/refresh/worker33_portfolio.json) | Retained metadata identities; no full-country/category or current retail-stock claim. |
| Bhutan DAMC vegetable-price report and MoESD dietary assessment; China MOA commodity supply/demand; Afghanistan ministry report; Armenia annex | [`offmenu/refresh/owner19_bindings.json`](../offmenu/refresh/owner19_bindings.json) | Unparsed/incomplete originals, title-only editions and scope holds; application configuration is not acquisition/rights/admission contract. |
| Nomaada Awari Restaurant Week; Panama MEF basic-food-basket; Philippine DepEd Catanduanes feeding; Palm Sugar Honiara menu | [`offmenu/refresh/owner20_bindings.json`](../offmenu/refresh/owner20_bindings.json) | NG/PA missing, PH held, SB derived-input-only; event/menu scope never national coverage. |
| Nepal NAST traditional foods; Pakistan Pakwan menu; Palestine P5071642025; Slovak HICP | [`offmenu/refresh/portfolio37_bindings.json`](../offmenu/refresh/portfolio37_bindings.json) | Authored metadata binding only; local IDs not publisher identifiers, no body read/acceptance, countryComplete false. |
| Haiti IHSI CPI methodology and Karibe Hotel menu; Hungarian GYERE booklet/KSH STADAT ara0004; Ireland AHM05 and HSE healthy-meal recipebook | [`research/portfolio40/bindings.json`](../research/portfolio40/bindings.json) | Explicit unreviewed metadata configuration; raw bytes not read/passed/committed by configuration authoring. |
| Spain composition catalogue, REGOE and recipe challenge; Nicaragua BCN; Tokelau Pasifika/fisheries; Wallis/Futuna reports | [`config/portfolio56/retained-metadata.json`](../config/portfolio56/retained-metadata.json) | Metadata catalog/edition claims only; no country acceptance, no staging execution authorization, source bodies must not be read. |
| Japan CAA JSFA10th edition2024; Kenya FCT2018/recipe leads; Kyrgyzstan figshare20237163v2; Fineli20.0 | [`docs/operations/owner49-staging-catalog.json`](operations/owner49-staging-catalog.json) | Source-linked retained metadata, no processing/admission; JP binding missing, KE no qualified original, KG original missing, Fineli held. |
| Christmas Island IOT price index; Sabores da Zambézia; IITA booklet; Venezuela Cavendes-INN and Pestana Caracas menu | [`offmenu/portfolio39/sources.py`](../offmenu/portfolio39/sources.py) | Receipt metadata only; publisher editions unverified; all real operations held. |
| Mexico INEGI INPC weights; Singapore SingStat food-establishment counts; Serbia SORS market prices; South Sudan BOSS bulletin | [`offmenu/refresh/portfolio52_bindings.py`](../offmenu/refresh/portfolio52_bindings.py) | MX/SG binding-ready-pending-review but datasetExecutionAllowed/accepted false; weights are expenditure shares, establishments aggregate counts; RS/SS held. |
| Myanmar World Bank RTFP; Macao DSEC bulletin; Mali and Mongolia retained source leads | [`docs/operations/worker12-staging-bindings.md`](operations/worker12-staging-bindings.md) | Myanmar model estimates not observed offers; Macao historical values; Mali print-only/no digital exception and Mongolia unresolved custody/use. |
| Rwanda IITA Citizen-H2D3 and Wellspring; Thailand PeerJ13:e19606; US FNS430; Vietnam composition2017 | [`docs/operations/worker46-source-bindings.md`](operations/worker46-source-bindings.md) | Rwanda descriptor not participant consent; Thai table not national composition; recipe body/use and Vietnamese original held. |
| Ecuador gastronomic map/USFQ/El Pulpo; WAFCT2019; Tajik Al Mandi; Vanuatu nutrition analysis2015 | [`docs/portfolio48-staging-bindings.md`](portfolio48-staging-bindings.md) | Metadata-only; NC/source-use/selector holds; Tajik image PDF identity not extracted records; Vanuatu not live prices/composition. |
| New Zealand Cheap Eats; Slovenia recipe/statistics; Syria World Bank/WFP; Uganda HarvestPlus/USAID/UBOS/UNBS | [`docs/portfolio17/binding-contract.md`](portfolio17/binding-contract.md) | Retained metadata, qualified originals/use often absent; explicit403/DNS/TLS no-retry holds. |
| Guatemala INE CBA; Guam UOG CNEP; BEAC BES N27; BAS South Georgia survey | [`docs/operations/portfolio34-staging-bindings.md`](operations/portfolio34-staging-bindings.md) | CBA expenditure basket semantics require qualification; Guam acquisition inventory not parsed recipes; BAS survey is not human-food composition. |
| Comoros PLOS0323506.s002; Saint Kitts/Nevis CPI; North Korea GIEWS; Korean FAO guideline profile | [`docs/source-bindings/worker54.md`](source-bindings/worker54.md) | Research/reference metadata only; original guidelines, units/bases, scope or input coordinates remain unresolved. |
| Guinea-Bissau regional WAFCT2019; Peru INS; Tuvalu CPI2026Q2; Zambia Leeds DOI10.5518/1111 | [`docs/worker63-staging-bindings.md`](worker63-staging-bindings.md) | Regional rows do not establish country membership; Peru edition/rights conflict; Zambia historical waste-adjusted supply is not intake/composition. |
| Guadeloupe Insee; Niue agriculture census/CPI; Tonga nutrition policy; Mayotte education-venue menu | [`docs/worker61-staging-bindings.md`](worker61-staging-bindings.md) | References/metadata; workbook absent, agricultural aggregates not producers, historical policy not current advice, venue menu not recipes. |

</details>

<details>
<summary>Later source catalogues</summary>

- [`docs/operations/owner49-staging-catalog.json`](operations/owner49-staging-catalog.json)
- [`offmenu/portfolio32/catalog.json`](../offmenu/portfolio32/catalog.json)
- [`offmenu/portfolio43_catalogue.py`](../offmenu/portfolio43_catalogue.py)
- [`offmenu/portfolio60/catalog.py`](../offmenu/portfolio60/catalog.py)
- [`offmenu/portfolio_owner02_catalog.py`](../offmenu/portfolio_owner02_catalog.py)
- [`offmenu/portfolio_worker62_catalogue.py`](../offmenu/portfolio_worker62_catalogue.py)
- [`offmenu/refresh/_portfolio08_catalogue.py`](../offmenu/refresh/_portfolio08_catalogue.py)
- [`offmenu/refresh/_portfolio36_catalogue.py`](../offmenu/refresh/_portfolio36_catalogue.py)
- [`offmenu/refresh/_worker27_catalog.py`](../offmenu/refresh/_worker27_catalog.py)
- [`offmenu/refresh/bv_lu_sh_catalog.py`](../offmenu/refresh/bv_lu_sh_catalog.py)
- [`offmenu/refresh/portfolio04_catalogue.py`](../offmenu/refresh/portfolio04_catalogue.py)
- [`offmenu/refresh/portfolio15_catalogue.py`](../offmenu/refresh/portfolio15_catalogue.py)
- [`offmenu/refresh/portfolio16_catalogue.py`](../offmenu/refresh/portfolio16_catalogue.py)
- [`offmenu/refresh/portfolio18_catalogue.py`](../offmenu/refresh/portfolio18_catalogue.py)
- [`offmenu/refresh/portfolio26_catalogue.py`](../offmenu/refresh/portfolio26_catalogue.py)
- [`offmenu/refresh/portfolio28_catalogue.py`](../offmenu/refresh/portfolio28_catalogue.py)
- [`offmenu/refresh/portfolio31_catalogue.py`](../offmenu/refresh/portfolio31_catalogue.py)
- [`offmenu/refresh/portfolio41_catalogue.py`](../offmenu/refresh/portfolio41_catalogue.py)
- [`offmenu/refresh/portfolio44_catalog.py`](../offmenu/refresh/portfolio44_catalog.py)
- [`offmenu/refresh/portfolio45_catalog.py`](../offmenu/refresh/portfolio45_catalog.py)
- [`offmenu/refresh/portfolio53_catalogue.py`](../offmenu/refresh/portfolio53_catalogue.py)
- [`offmenu/refresh/portfolio_58_catalogue.py`](../offmenu/refresh/portfolio_58_catalogue.py)
- [`offmenu/refresh/portfolio_au_ir_pn_catalogue.py`](../offmenu/refresh/portfolio_au_ir_pn_catalogue.py)
- [`offmenu/refresh/worker06_catalog.py`](../offmenu/refresh/worker06_catalog.py)
- [`offmenu/refresh/worker10_catalogue.py`](../offmenu/refresh/worker10_catalogue.py)
- [`offmenu/refresh/worker24_catalogue.py`](../offmenu/refresh/worker24_catalogue.py)

</details>

<details>
<summary>Additional source metadata declarations</summary>

- [`bindings/worker61-gp-nu-to-yt.json`](../bindings/worker61-gp-nu-to-yt.json)
- [`bindings/worker61-public-documentation.json`](../bindings/worker61-public-documentation.json)
- [`config/portfolio04-official-document-observations.json`](../config/portfolio04-official-document-observations.json)
- [`config/portfolio04-staging-bindings.json`](../config/portfolio04-staging-bindings.json)
- [`config/portfolio08-source-bindings.json`](../config/portfolio08-source-bindings.json)
- [`config/portfolio26-bindings.json`](../config/portfolio26-bindings.json)
- [`config/portfolio28-staging.json`](../config/portfolio28-staging.json)
- [`config/portfolio42/in-reference-binding.json`](../config/portfolio42/in-reference-binding.json)
- [`config/portfolio43.json`](../config/portfolio43.json)
- [`config/portfolio56/public-documentation.json`](../config/portfolio56/public-documentation.json)
- [`config/portfolio56/retained-metadata.json`](../config/portfolio56/retained-metadata.json)
- [`config/portfolio59-staging-bindings.json`](../config/portfolio59-staging-bindings.json)
- [`config/portfolios/bm-lc-sc.json`](../config/portfolios/bm-lc-sc.json)
- [`config/portfolios/worker27-staging.json`](../config/portfolios/worker27-staging.json)
- [`config/portfolios/worker41.json`](../config/portfolios/worker41.json)
- [`config/portfolios/worker53-staging.json`](../config/portfolios/worker53-staging.json)
- [`config/refresh/portfolio-w07.json`](../config/refresh/portfolio-w07.json)
- [`config/source-bindings/owner36.json`](../config/source-bindings/owner36.json)
- [`config/source-bindings/portfolio16.json`](../config/source-bindings/portfolio16.json)
- [`config/staging/portfolio58.json`](../config/staging/portfolio58.json)
- [`config/staging/worker63-bindings.json`](../config/staging/worker63-bindings.json)
- [`config/worker10-staging-bindings.json`](../config/worker10-staging-bindings.json)
- [`docs/operations/portfolio-au-ir-pn.json`](operations/portfolio-au-ir-pn.json)
- [`docs/operations/portfolio13/source-bindings.json`](operations/portfolio13/source-bindings.json)
- [`docs/operations/worker24/bindings.json`](operations/worker24/bindings.json)
- [`docs/portfolio17/bindings.json`](portfolio17/bindings.json)
- [`docs/portfolios/worker31-input-bindings.json`](portfolios/worker31-input-bindings.json)
- [`docs/portfolios/worker62-inputs.json`](portfolios/worker62-inputs.json)
- [`docs/source-bindings/owner15.json`](source-bindings/owner15.json)
- [`offmenu/portfolio21/bindings.py`](../offmenu/portfolio21/bindings.py)
- [`offmenu/portfolio39/sources.py`](../offmenu/portfolio39/sources.py)
- [`offmenu/portfolio50/profiles.py`](../offmenu/portfolio50/profiles.py)
- [`offmenu/portfolio_worker09_sources.py`](../offmenu/portfolio_worker09_sources.py)
- [`offmenu/refresh/owner19_bindings.json`](../offmenu/refresh/owner19_bindings.json)
- [`offmenu/refresh/owner20_bindings.json`](../offmenu/refresh/owner20_bindings.json)
- [`offmenu/refresh/portfolio05_sources.py`](../offmenu/refresh/portfolio05_sources.py)
- [`offmenu/refresh/portfolio12_bindings.py`](../offmenu/refresh/portfolio12_bindings.py)
- [`offmenu/refresh/portfolio34_bindings.py`](../offmenu/refresh/portfolio34_bindings.py)
- [`offmenu/refresh/portfolio37_bindings.json`](../offmenu/refresh/portfolio37_bindings.json)
- [`offmenu/refresh/portfolio42.py`](../offmenu/refresh/portfolio42.py)
- [`offmenu/refresh/portfolio47_sources.json`](../offmenu/refresh/portfolio47_sources.json)
- [`offmenu/refresh/portfolio48/_bindings.py`](../offmenu/refresh/portfolio48/_bindings.py)
- [`offmenu/refresh/portfolio52_bindings.py`](../offmenu/refresh/portfolio52_bindings.py)
- [`offmenu/refresh/portfolio54_config.py`](../offmenu/refresh/portfolio54_config.py)
- [`offmenu/refresh/portfolio55.json`](../offmenu/refresh/portfolio55.json)
- [`offmenu/refresh/portfolio_01_contract.py`](../offmenu/refresh/portfolio_01_contract.py)
- [`offmenu/refresh/portfolio_owner51.json`](../offmenu/refresh/portfolio_owner51.json)
- [`offmenu/refresh/portfolio_w35.json`](../offmenu/refresh/portfolio_w35.json)
- [`offmenu/refresh/portfolios/worker23.json`](../offmenu/refresh/portfolios/worker23.json)
- [`offmenu/refresh/portfolios/worker29.py`](../offmenu/refresh/portfolios/worker29.py)
- [`offmenu/refresh/portfolios/worker38_sources.py`](../offmenu/refresh/portfolios/worker38_sources.py)
- [`offmenu/refresh/worker33_portfolio.json`](../offmenu/refresh/worker33_portfolio.json)
- [`offmenu/refresh/worker46_bindings.py`](../offmenu/refresh/worker46_bindings.py)
- [`research/portfolio40/bindings.json`](../research/portfolio40/bindings.json)
- [`research/portfolio40/snapshots.json`](../research/portfolio40/snapshots.json)

</details>

<details>
<summary>Related implementation entrypoints — not evidence of execution</summary>

- [`offmenu/portfolio32/binding.py`](../offmenu/portfolio32/binding.py)
- [`offmenu/portfolio39/binding.py`](../offmenu/portfolio39/binding.py)
- [`offmenu/portfolio40/binding.py`](../offmenu/portfolio40/binding.py)
- [`offmenu/portfolio43.py`](../offmenu/portfolio43.py)
- [`offmenu/portfolio50/bindings.py`](../offmenu/portfolio50/bindings.py)
- [`offmenu/portfolio60/bindings.py`](../offmenu/portfolio60/bindings.py)
- [`offmenu/portfolio60/worker.py`](../offmenu/portfolio60/worker.py)
- [`offmenu/portfolio_bm_lc_sc.py`](../offmenu/portfolio_bm_lc_sc.py)
- [`offmenu/portfolio_owner02.py`](../offmenu/portfolio_owner02.py)
- [`offmenu/portfolio_worker09.py`](../offmenu/portfolio_worker09.py)
- [`offmenu/portfolio_worker62.py`](../offmenu/portfolio_worker62.py)
- [`offmenu/portfolios/worker61.py`](../offmenu/portfolios/worker61.py)
- [`offmenu/refresh/owner19_bindings.py`](../offmenu/refresh/owner19_bindings.py)
- [`offmenu/refresh/owner20_binding.py`](../offmenu/refresh/owner20_binding.py)
- [`offmenu/refresh/owner49_staging.py`](../offmenu/refresh/owner49_staging.py)
- [`offmenu/refresh/portfolio04_binding.py`](../offmenu/refresh/portfolio04_binding.py)
- [`offmenu/refresh/portfolio05.py`](../offmenu/refresh/portfolio05.py)
- [`offmenu/refresh/portfolio08_bindings.py`](../offmenu/refresh/portfolio08_bindings.py)
- [`offmenu/refresh/portfolio12.py`](../offmenu/refresh/portfolio12.py)
- [`offmenu/refresh/portfolio13_bindings.py`](../offmenu/refresh/portfolio13_bindings.py)
- [`offmenu/refresh/portfolio15.py`](../offmenu/refresh/portfolio15.py)
- [`offmenu/refresh/portfolio16_binding.py`](../offmenu/refresh/portfolio16_binding.py)
- [`offmenu/refresh/portfolio17.py`](../offmenu/refresh/portfolio17.py)
- [`offmenu/refresh/portfolio18.py`](../offmenu/refresh/portfolio18.py)
- [`offmenu/refresh/portfolio26.py`](../offmenu/refresh/portfolio26.py)
- [`offmenu/refresh/portfolio28.py`](../offmenu/refresh/portfolio28.py)
- [`offmenu/refresh/portfolio31.py`](../offmenu/refresh/portfolio31.py)
- [`offmenu/refresh/portfolio34.py`](../offmenu/refresh/portfolio34.py)
- [`offmenu/refresh/portfolio36.py`](../offmenu/refresh/portfolio36.py)
- [`offmenu/refresh/portfolio37.py`](../offmenu/refresh/portfolio37.py)
- [`offmenu/refresh/portfolio41.py`](../offmenu/refresh/portfolio41.py)
- [`offmenu/refresh/portfolio44.py`](../offmenu/refresh/portfolio44.py)
- [`offmenu/refresh/portfolio45.py`](../offmenu/refresh/portfolio45.py)
- [`offmenu/refresh/portfolio47_bindings.py`](../offmenu/refresh/portfolio47_bindings.py)
- [`offmenu/refresh/portfolio52.py`](../offmenu/refresh/portfolio52.py)
- [`offmenu/refresh/portfolio53.py`](../offmenu/refresh/portfolio53.py)
- [`offmenu/refresh/portfolio54_binding.py`](../offmenu/refresh/portfolio54_binding.py)
- [`offmenu/refresh/portfolio55.py`](../offmenu/refresh/portfolio55.py)
- [`offmenu/refresh/portfolio56.py`](../offmenu/refresh/portfolio56.py)
- [`offmenu/refresh/portfolio59_bindings.py`](../offmenu/refresh/portfolio59_bindings.py)
- [`offmenu/refresh/portfolio_01.py`](../offmenu/refresh/portfolio_01.py)
- [`offmenu/refresh/portfolio_58.py`](../offmenu/refresh/portfolio_58.py)
- [`offmenu/refresh/portfolio_au_ir_pn.py`](../offmenu/refresh/portfolio_au_ir_pn.py)
- [`offmenu/refresh/portfolio_owner51.py`](../offmenu/refresh/portfolio_owner51.py)
- [`offmenu/refresh/portfolio_w07.py`](../offmenu/refresh/portfolio_w07.py)
- [`offmenu/refresh/portfolio_w35.py`](../offmenu/refresh/portfolio_w35.py)
- [`offmenu/refresh/portfolio_worker27.py`](../offmenu/refresh/portfolio_worker27.py)
- [`offmenu/refresh/portfolios/worker23.py`](../offmenu/refresh/portfolios/worker23.py)
- [`offmenu/refresh/portfolios/worker38.py`](../offmenu/refresh/portfolios/worker38.py)
- [`offmenu/refresh/worker06_bindings.py`](../offmenu/refresh/worker06_bindings.py)
- [`offmenu/refresh/worker10_bindings.py`](../offmenu/refresh/worker10_bindings.py)
- [`offmenu/refresh/worker24_bindings.py`](../offmenu/refresh/worker24_bindings.py)
- [`offmenu/refresh/worker24_metadata_diagnostic.py`](../offmenu/refresh/worker24_metadata_diagnostic.py)
- [`offmenu/refresh/worker33_bindings.py`](../offmenu/refresh/worker33_bindings.py)
- [`scripts/worker63_staging_bindings.py`](../scripts/worker63_staging_bindings.py)

</details>

<details>
<summary>Country portfolio and source-binding guides</summary>

- [`docs/operations/owner49-staging-binding.md`](operations/owner49-staging-binding.md)
- [`docs/operations/portfolio-01-staging-binding.md`](operations/portfolio-01-staging-binding.md)
- [`docs/operations/portfolio-au-ir-pn.md`](operations/portfolio-au-ir-pn.md)
- [`docs/operations/portfolio-w07-staging-bindings.md`](operations/portfolio-w07-staging-bindings.md)
- [`docs/operations/portfolio05-staging-bindings.md`](operations/portfolio05-staging-bindings.md)
- [`docs/operations/portfolio18-staging-bindings.md`](operations/portfolio18-staging-bindings.md)
- [`docs/operations/portfolio26-staging-bindings.md`](operations/portfolio26-staging-bindings.md)
- [`docs/operations/portfolio34-staging-bindings.md`](operations/portfolio34-staging-bindings.md)
- [`docs/operations/portfolio37-staging-bindings.md`](operations/portfolio37-staging-bindings.md)
- [`docs/operations/portfolio50-staging-bindings.md`](operations/portfolio50-staging-bindings.md)
- [`docs/operations/portfolio52-staging-binding.md`](operations/portfolio52-staging-binding.md)
- [`docs/operations/portfolio59-staging-bindings.md`](operations/portfolio59-staging-bindings.md)
- [`docs/operations/worker06-staging-bindings.md`](operations/worker06-staging-bindings.md)
- [`docs/operations/worker09-staging-binding.md`](operations/worker09-staging-binding.md)
- [`docs/operations/worker12-staging-bindings.md`](operations/worker12-staging-bindings.md)
- [`docs/operations/worker29-staging-bindings.md`](operations/worker29-staging-bindings.md)
- [`docs/operations/worker33-staging-bindings.md`](operations/worker33-staging-bindings.md)
- [`docs/operations/worker38-staging-bindings.md`](operations/worker38-staging-bindings.md)
- [`docs/operations/worker45-staging-bindings.md`](operations/worker45-staging-bindings.md)
- [`docs/operations/worker46-source-bindings.md`](operations/worker46-source-bindings.md)
- [`docs/owner02-portfolio-staging-bindings.md`](owner02-portfolio-staging-bindings.md)
- [`docs/portfolio15-staging-binding.md`](portfolio15-staging-binding.md)
- [`docs/portfolio17/binding-contract.md`](portfolio17/binding-contract.md)
- [`docs/portfolio21-staging-bindings.md`](portfolio21-staging-bindings.md)
- [`docs/portfolio39-staging-bindings.md`](portfolio39-staging-bindings.md)
- [`docs/portfolio44-shared-interface-proposal.md`](portfolio44-shared-interface-proposal.md)
- [`docs/portfolio44-staging-bindings.md`](portfolio44-staging-bindings.md)
- [`docs/portfolio48-staging-bindings.md`](portfolio48-staging-bindings.md)
- [`docs/portfolio56/staging-bindings.md`](portfolio56/staging-bindings.md)
- [`docs/portfolio60-staging-bindings.md`](portfolio60-staging-bindings.md)
- [`docs/source-bindings/worker54.md`](source-bindings/worker54.md)
- [`docs/worker61-staging-bindings.md`](worker61-staging-bindings.md)
- [`docs/worker63-staging-bindings.md`](worker63-staging-bindings.md)
- [`docs/operations/bm-lc-sc-staging-binding.md`](operations/bm-lc-sc-staging-binding.md)
- [`docs/operations/bv-lu-sh-staging-bindings.md`](operations/bv-lu-sh-staging-bindings.md)
- [`docs/operations/worker24/README.md`](operations/worker24/README.md)
- [`research/portfolio40/README.md`](../research/portfolio40/README.md)

</details>

<details>
<summary>Additional named source declarations</summary>

- [`offmenu/refresh/adapter_mapping.py`](../offmenu/refresh/adapter_mapping.py)
- [`offmenu/refresh/capabilities.py`](../offmenu/refresh/capabilities.py)
- [`offmenu/refresh/et_table1_declaration.py`](../offmenu/refresh/et_table1_declaration.py)
- [`offmenu/refresh/nl_cp01_metadata.py`](../offmenu/refresh/nl_cp01_metadata.py)

</details>


### Coverage still to reconcile

The repository preserves the original discovery universe and later additions, but a single cross-inventory alias/release reconciliation is unfinished. Private retained holdings and live provider entitlements were not read or verified for this correction. Current all-corpus totals for collected, ingested, normalized, mapped and qualified records remain unknown from these metadata layers—not zero. Country links, source-native fields, licensing, parser support, qualification and actual feature use still require their own evidence. The [coverage assessment](global-coverage-assessment.md), [source execution plan](source-execution-plan.md) and [delivery programme](research-delivery-plan.md) retain the next work; no new acquisition or execution permission is granted here.

---

## Historical research and custody navigation

Historical research/custody navigation: worker paths, branch states and publication observations below belong to their dated evidence cuts. Use the [maintainer guide](maintainer.md) and [operations guide](operations.md) for current setup, canonical paths and tracking; do not use an old worker path as a current working directory.

Navigation and integrity references only; no complete-corpus or app-acceptance claim. **HISTORICAL published snapshot:** `abe0ddc9db357b1e8d0d61825392d6b9923352f0`, advertised as `origin/develop` at `2026-10-14T08:41:10.145121+00:00`; its reference hashes were checked at `2026-10-14T08:48:40.725173+00:00`. Observed remote `main` at that historical check: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.

**Current integration target at the last fresh fetch:** `908ca373dfc918f2e33fd5e44260879577bed5c5` (`2026-10-14T09:07:16.203531+00:00`, fetch exit 0), normally merged into this existing feature. The immutable links below intentionally remain at the historical `abe0` snapshot; they are not labels for the current branch tip. Changes brought in by develop belong to their original owner, not this documentation task. **GitHub availability observed at `2026-10-14T10:10:26.496332+00:00`:** the exact four-file candidate `b637424f53ceef2010b6d3465f9fb39e59a2878d` is published on the private review branch in [PR 4](https://github.com/maldous/offmenu/pull/4), which is open and unmerged. The earlier not-pushed state was observed at `2026-10-14T09:14:56.670512+00:00` and is historical. This later local correction awaits review and is not yet pushed; repository availability does not mean corpus admission or app deployment.

## Start here on Android

**Sign in to GitHub with access to the private `maldous/offmenu` repository.** The research links below remain pinned to the historical published snapshot. [Published review index](https://github.com/maldous/offmenu/blob/b637424f53ceef2010b6d3465f9fb39e59a2878d/docs/OFFMENU_CORPUS_INDEX.md) and the bounded CSV/receipt are available at the separately observed private PR publication; the local wording correction is still pending review. Paths/blob IDs were checked against that exact remotely advertised Git tree; research manifest, canonical register and source ledger were also fetched through the connected GitHub service. This is link/source verification, not a device trial.

All five authoritative source PDFs (PDF previews/downloads require repository access):

1. [Basket Normalization Addendum](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/reports/01-OffMenu_Basket_Normalization_Addendum.pdf)
2. [Product Review and Plan](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/reports/02-OffMenu_Product_Review_and_Plan-1-.pdf)
3. [Enrichment Discovery — 249 Countries](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/reports/03-OffMenu_Enrichment_Discovery_249_Countries.pdf)
4. [User-Driven Cache and Enrichment Design](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/reports/04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf)
5. [Global Shopping Baskets](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/reports/05-OffMenu_Global_Shopping_Baskets.pdf)

All four unchanged machine-readable research registers/specification:

- [OffMenu_Basket_Normalization_Spec.json](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/OffMenu_Basket_Normalization_Spec.json)
- [OffMenu_Country_Basket_Register.json](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/OffMenu_Country_Basket_Register.json)
- [OffMenu_Enrichment_Source_Register_249.json](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/OffMenu_Enrichment_Source_Register_249.json)
- [OffMenu_Global_Data_Source_Register.json](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/OffMenu_Global_Data_Source_Register.json)

The five PDF/four register SHA-256 values match [the preservation audit](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/research-audit.json). [Research metadata](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/research/manifest.json) records discovery scope and limits. The basket specification is one of the four register/specification inputs; it is not an ingested food database.

## Bounded dataset-discovery batch (review candidate)

[Open the 25-source CSV](dataset-discovery/offmenu-dataset-discovery-20261014.csv) · [Consolidation/provenance receipt](dataset-discovery/consolidation-receipt.json).

This **single bounded batch** has 31 columns and 48 rows: 25 metadata rows plus 23 existing samples. It is not all-corpus collection, ingestion, curation or admission. Original rights restrictions, attribution, units, uncertainty and no-admission statuses remain unchanged. CSV SHA-256: `bde659a82dc8014bf7a139b8ca53554e950293efaa42c544d4a78809860d1ead`.

The batch is normally merged from accepted consolidation `2f7cf2eb8546e2c86ba6cb8647717ed20ca67a27`; root/Worker 34 review covered 25 exact committed source-CSV/receipt provenance pairs. At the timestamped GitHub observation above, the b637424 index, CSV and receipt are published and available to authenticated Android readers in private GitHub, with PR 4 still open/unmerged. The machine index preserves the historical pre-push observations separately from this current observed availability. Source branch/commit references in the receipt may remain local-only and are not claimed as published URLs. Root owns the normal PR update/develop merge after Worker 34 re-review and mandatory platform gates; no raw source archives or private account/provider-response datasets are included.

## Requirements and discovery authority

- [Canonical 105-ID requirement register](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/recommendation-delivery-register.json): actual local path `/home/user/src/offmenu-workers/worker-07/docs/recommendation-delivery-register.json`; 105 unique IDs verified. [Delivery reconciliation](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/delivery-reconciliation.json) is historical status/evidence, explicitly `programmeComplete=false`.
- Externally reproducible ID check: compare the published canonical register above with the linked delivery reconciliation at the same `abe0` snapshot; each has 105 unique requirement IDs and the sets match. This is ID preservation, not completed delivery. Worker 14 mapping `cd27c470a3671261651c7a42e884d9dda4bdf341` is **operator-local retained evidence**, outside the approved four-file publication. External clones must not assume that object or its files exist; no `git show` command is offered as an external reproduction step. Its historical local comparison is retained only as custody metadata; no extra mapping is published.
- [Source delivery ledger](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/source-delivery-ledger.json): 1,303 entries verified; [country matrix](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/country-delivery-matrix.json): 249 unique ISO2 queues verified. Landing-page discovery, a download lead, or a country queue does not establish ingestion, matching, permission or operational coverage. The global register alone lists 365 sources; the combined ledger is the 1,303-entry reference.

## Capabilities: accepted scope versus pending work

- [Published provider code](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/cloud/provider-data.mjs) supports personal USDA/Edamam lookups and bounded public OFF/Open Prices/FSA/openFDA samples. [GLEIF/Wikidata enrichment](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/cloud/enrichment.mjs) produces candidates, not verified ownership or ingredient origin. [Catalogue labels](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/public/sources.js) are not proof of active connectors or grants. No provider requests, credentials or permissions were exercised here.
- Retained Worker 02 candidate `49c6ed037a0c506dc2e71a7c8ef40d423d6f46d0` has ledger-recorded acceptance of bounded source/synthetic compatibility only; it is not integrated in the indexed historical snapshot or published. See local candidate receipt in the JSON references.
- Pending catalogue capabilities include WhichGrocer/Spoonacular/Instacart adapters, Kroger OAuth/cart, Health Connect/HealthKit native bridges and Strava OAuth. Live grants, market/plan limits, clinical/culinary review, host wiring and release acceptance are separate gates.

## Local normalized, curated and common data

**Exact existing local paths, full manifest-byte SHA-256 values and per-reference scope are in [OFFMENU_CORPUS_REFS.json](OFFMENU_CORPUS_REFS.json).** Only manifests/metadata were read and hashed; no archives, record partitions or source corpora were copied or scanned. Source counts inside manifests remain producer declarations unless covered by the referenced historical evidence.

Let `D = /home/user/src/offmenu-data`. These are separate evidence tracks:

| Track | Actual manifest relative to D | Meaning |
| --- | --- | --- |
| Local normalized | `off-2026-10-12-lf/manifest.json`, `usda-2026-04/manifest.json`, `prices-2026-10-12/manifest.json`, `world-recipes-global-final-20261014/manifest.json` | Named normalized releases; not global or dietary acceptance |
| Curated delivery | `curated-expanded-country-search-20261013/blobs/manifest.json` | Declares 22,519,902 curated records / 18 sources; original source archives stay local |
| Curated recipes | `curated-world-recipes-global-20261014/blobs/manifest.json` | Declares 25,135 source recipes; unknown measures and incomplete OCR stay explicit |
| Historical producer proof | `common-ready-six-package-global-20261014.json` | Six-package global structural/provenance qualification; not caller authorization |

The six proof-listed common manifest byte hashes were independently matched to the existing local manifests (no packet replay):

- `/home/user/src/offmenu-data/common-data-reviewed-package-20261014/manifest.json` — proof marks this package grandfathered.
- `/home/user/src/offmenu-data/common-reference-delivery-final-20261014/manifest.json`.
- `/home/user/src/offmenu-data/common-national-semantic-final-20261014/manifest.json`.
- `/home/user/src/offmenu-data/measurement-terminology-final-qualified-20261014/manifest.json`.
- `/home/user/src/offmenu-data/recipe-expansion-final-qualified-20261014/common-graph/manifest.json`.
- `/home/user/src/offmenu-data/historical-recipe-quality-final-corrected-20261014/manifest.json`.

Each common directory uses `offmenu-common-package/1` packet delivery; public scope preserves citations, source text, Unicode IRIs, licence/attribution and unresolved joins. Different manifests can carry the same release ID: pin exact bytes, not the ID alone. No separately named CherryPick manifest was established by this check; use the exact retained curated paths above rather than assuming an additional package.

## Timestamped hosting check and rights boundary

At `2026-10-14T08:43:26.316324+00:00`, [hosted common manifest](https://offmenu-corpus.netlify.app/common-data/manifest.json) returned **HTTP 200**, 53,572 bytes, exact SHA-256 `a20aca224758eb6ac64ea89d0bb31d33280a2b0d2ec97e46ed6a2ddc71c92867`, matching [the historical byte receipt](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/common-data-manifest-checksum-verification-20261014.json). Root curation and recipe manifests exceeded the 1 MiB bounded read; their complete current hashes were not established. Three explicit manifest GETs only; no data partitions downloaded.

[The historical all-file publication receipt](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/common-data-publication-verification-20261014.json) is historical package/native-download evidence. That timestamped check proves one manifest is still available and byte-identical; it does not revalidate all files, whole data coverage, country completeness, app behavior or producer admission. Legacy embedded manifest payload digests are distinct from exact file-byte hashes.

Original archives, normalized inputs, common/public projections, personal provider responses and private accounts are distinct. Public accessibility is not redistribution permission. Per-citation licence/share-alike/attribution, owner scope, source plan, retention/revocation and independent admission still apply; private provider/account data must never be promoted to commons by this index. See [the common rights contract](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/corpus/common-data-contract.json) and [curation boundaries](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/curation-architecture.md).

Evidence/control receipt: `/home/user/Documents/Codex/2026-10-14/task-2/worker-07-corpus-index/`. Supplied controls: unrestricted filesystem (`danger-full-access`), network enabled, mandatory `auto_review`; separate approval-policy value unavailable. User configuration separately says profile `disabled`, filesystem `unrestricted`; it is not the basis for the active-control statement. No credential/security configuration changed.

Review gate: documentation only, pending independent review. No push, provider/source activation, production publication or programme acceptance.
