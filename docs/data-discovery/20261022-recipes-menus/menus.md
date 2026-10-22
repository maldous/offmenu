# Reusable menus and structured dish/menu-item data

**Review date: 2026-10-22. Preparation only; every acquisition entry remains disabled.**

## Decision and boundary

The strongest route is original school/institutional feeds plus carefully scoped historical collections, not indiscriminate restaurant scraping. This review records **31 source families: 14 explicit-license candidates (A), 13 conditional leads (B), and 4 restricted/non-equivalent leads (C)**. They are not additive unique corpora.

**Production fetch must occur on Foo only after all eight databases are provisioned and relationally fit for existing data.** The companion JSON is discovery metadata, not an active fetch configuration. No production fetch, bulk archive acquisition, source mirror, credential use, authentication bypass, database mutation or Git publication was performed by this workstream.

Tier A means explicit data/content permission for the stated scope—not that all schema, original-access, linked-resource and upstream-provenance gates are resolved. Tier B is not production-ready. Tier C includes noncommercial/commercial-contract or non-real-menu material.

## Highest-value findings

| Source | Scale semantics | Reuse and remaining gate |
|---|---|---|
| [Taiwan national lunches](https://data.gov.tw/dataset/98339) | Original study: 12,966,481 raw **dish records**, 12,688,008 after deduplication, 3,894 schools, May 2024–April 2026. Not millions of full menus. | Government Open Data License v1. National Traditional Chinese menus/ingredient relations; documentation returned 403. [Study](https://pmc.ncbi.nlm.nih.gov/articles/PMC13567730/) |
| [Korean NEIS](https://open.neis.go.kr/portal/data/service/selectServicePage.do?infId=OPEN17320190722180924242823&infSeq=1) | Nationwide service; five catalog rows are a **sample**, not corpus size. | Explicit unrestricted use; daily-load current-year menus/nutrition. Actual payload and key procedure pending. |
| [CNOUS](https://www.data.gouv.fr/datasets/menus-des-restaurants-brasseries-et-cafeterias) | **26 XML resources**, not 26 menus or restaurants. | Official Licence Ouverte. Course/daypart structure; actual XML and retention unverified. |
| [Konstanz archive](https://kondata.uni-konstanz.de/radar/de/dataset/ty235ftth5yvg7hd) | **3,753,180 final meal options**, 340 canteens, 2015–2024. | CC BY 4.0 data package. Upstream provenance and collection-date discrepancy require resolution; archive not downloaded. [Paper](https://www.nature.com/articles/s44458-026-00138-3) |
| [French SCDL](https://schema.data.gouv.fr/scdl/menus-collectifs/1.2.1/documentation.html) | One **dish per row**. | Common municipal parser family. `menuPlatPrix` is theoretical **production cost EUR**, not selling price. |
| [Japanese school menus](https://www.city.yamagata-yamagata.lg.jp/opendata/category/1007062/1012830.html) / [Shizuoka](https://shizuoka-kyushoku.com/lunchmenu/) | CSV schedules and monthly PDFs; no invented national count. | Explicit CC notices. Shizuoka content CC BY 4.0 excludes images; actual two-page text sampled. |
| [NYPL transcriptions](https://nypl.github.io/menus-api/) | Historical funder statement: >1.33m dish transcriptions / 17,500 menus; 45,000 is physical collection size. | Excellent relational format, but exact current original export and transcription license unresolved. [Funder](https://www.neh.gov/project/whats-menu) |
| [DoltHub 2021](https://www.dolthub.com/blog/2021-08-20-menus-bounty-retrospective/) | 6,479,347 menu-item rows / 44,720 restaurants. | Large historical price lead; content license and delivery-platform rights unresolved. Not live availability. |

## Normalization contract

Menu records retain venue/occasion, date/daypart, audience/variant, ordered sections and items. Venue directories are not menus, and dish names are not recipes. Preserve original Unicode/language, IDs, date/calendar, source snapshot/revision, currency and attribution. Translation and inferred classifications are separate derived data.

**Recipe reference stays null** unless an explicit source relationship is evidenced. Ingredients/nutrition without methods are not full recipes. Quantity stays null unless supplied. Price observations require kind, date, currency, audience and channel: retail, audience tariff, production cost and unknown are distinct.

Nutrition retains meal/item/serving/100 g basis; never attach whole-meal totals to every dish. Allergen/diet labels remain source assertions, not safety guarantees. Scheduled meals are not proven service. Historical prices and stock flags must not become live stock claims. Keep closure days separate; preserve repeated offers across dates, but deduplicate mirrors and shared school PDFs with explicit relationships.

Generic hospital/care-home meal plans are within scope; identifiable patient/resident medical records are excluded.

### Parser families

| Family | Mapping | Important qualification |
|---|---|---|
| SCDL collective CSV/JSON | restaurant ID + ID type → venue; date/daypart/audience → menu; dish type/name → course/item; dish code → composition join; publication/modification timestamps → provenance. | `menuPlatPrix` → production-cost EUR. Allergens combine ingredients/traces. Documentation URL 1.2.1 displays version 1.2.2: pin actual schema. |
| OpenMensa v2 | Route canteen/date → menu; category → section; id/name → item; notes → source assertions; prices → audience tariffs. | Validate currency, closure entries and operator-specific rights. |
| iCalendar | UID/date/location/description/revision → source meal event. | Unfold escaped lines; respect timezone/date-only dates. SUMMARY may omit courses included in DESCRIPTION. |
| Historical relational | Menu → MenuPage → MenuItem → Dish; preserve item price/page position. | Page layout does not establish course hierarchy; image and transcription rights differ. |
| School monthly CSV/PDF | Kitchen/school + cohort + date → menu; original dish labels + explicitly scoped nutrition/ingredients. | Shared kitchen PDFs do not represent independent content for every linked school. |

Actual observed/documented fields versus pending-schema mappings are labeled in each entry and JSON. All entries carry disabled production flags and activation gates.

## Source register

### Tier A — explicit scoped permission, still disabled

#### Taiwan national school lunch and ingredient registry 2.0 (`tw_school_lunch_v2`)

**Class:** dated school meal plan and related dishes. **Geography/language:** Taiwan; zh-Hant.

- **Rights:** Government Open Data License v1. Official catalog data; retain attribution, release and upstream source.
- **Access/update:** JSON documentation, regional/monthly CSV series. Monthly series; national catalog marks irregular update. Catalog metadata 2026-08-20. Unverified.
- **Count:** 12,966,481 raw dish records — Study extraction of 1,056 official files, May 2024–April 2026; not an independent fetch audit. 12,688,008 deduplicated dish records — Same study; school/date/dish deduplication. 3,894 schools — Same study; not menu count.
- **Inspection:** Catalog and original study inspected; no dish payload. JSON documentation returned HTTP 403. No retry, bypass, or archive fetch.
- **Parser:** `taiwan_school_monthly_csv_pending_schema`. Recipe reference unknown/null.
- **Cautions:** Separate dish, ingredient, seasoning and supplier tables; do not flatten suppliers into ingredients. Study records lack portion/serving weights: frequency is not consumption or nutrient intake. Taiwan year 107 means 2018. Preserve original ROC dates and calendar-conversion provenance. Older Taipei 2018 catalog is an archive expansion path, not additional current coverage.
- **Evidence:** [Primary source](https://data.gov.tw/dataset/98339); [Supporting source 1](https://data.gov.tw/en/datasets/78344); [Supporting source 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC13567730/).

#### Korea NEIS school meal service diet information (`kr_neis_meals`)

**Class:** dated school meal plan. **Geography/language:** South Korea; ko.

- **Rights:** Official catalog: unrestricted permitted use (이용허락범위 제한 없음). Dataset-specific public-data declaration; preserve provider attribution and API conditions.
- **Access/update:** JSON, XML, CSV, XLS, TXT. Daily loading; service documents current-year menus. Authentication-key application documented; do not bypass..
- **Count:** 5 CSV sample rows — Catalog sample only; not national corpus size.
- **Inspection:** Official service documentation and catalog inspected. One-row API request inaccessible to web tool; no live record verified.
- **Parser:** `neis_meal_service_pending_payload`. Recipe reference unknown/null.
- **Cautions:** Official pages differ: national catalog says 17 regions; service description says Ministry plus 16 education offices. Resolve before exact coverage claim. Allergen numbers 1–19 are source annotations, not independent safety certification. Portal modification/import timestamps are not necessarily menu modification dates. Current-year service is not proof of an indefinitely queryable historical archive.
- **Evidence:** [Primary source](https://open.neis.go.kr/portal/data/service/selectServicePage.do?infId=OPEN17320190722180924242823&infSeq=1); [Supporting source 1](https://www.data.go.kr/data/15002118/fileData.do).

#### CNOUS menus for restaurants, brasseries and cafeterias (`fr_cnous_menus`)

**Class:** dated institutional menu hierarchy. **Geography/language:** France and overseas CROUS regions; fr.

- **Rights:** Licence Ouverte / Open Licence. Official menu dataset; version not specified on inspected catalog.
- **Access/update:** XML. Catalog updated 2026-10-19; feeds intended for daily menus. Public resources advertised.
- **Count:** 26 main XML feed resources — Not 26 menus, restaurants, or universities.
- **Inspection:** Official metadata and described fields inspected. Attempt to open one 16.4 KB resource returned internal error; no XML payload inspected.
- **Parser:** `cnous_xml_pending_sample`. Recipe reference unknown/null.
- **Cautions:** 26 resources is a resource count; publisher describes 28 CROUS organizations separately. Join venues from companion restaurant dataset; venue records themselves are not menus. Rolling retention and future-date revisions require snapshot/date modeling. Prefer official origin; CROUStillant is an alternative derived source, not independent additive coverage.
- **Evidence:** [Primary source](https://www.data.gouv.fr/datasets/menus-des-restaurants-brasseries-et-cafeterias); [Supporting source 1](https://www.data.gouv.fr/organizations/centre-national-des-oeuvres-universitaires-et-scolaires/datasets).

#### CROUStillant cleaned CROUS menu CSV/API (`fr_croustillant`)

**Class:** derived institutional menu feed. **Geography/language:** France and overseas; fr.

- **Rights:** Licence Ouverte v2. Community-published cleaned menu dataset; preserve original CNOUS provenance.
- **Access/update:** CSV, API. Publisher says daily at 01:00; catalog checked 2026-10-21. API access conditions to verify.
- **Count:** No defensible menu/record count established.
- **Inspection:** Community dataset metadata inspected. No payload; reported resource byte size changes and is not row count.
- **Parser:** `croustillant_csv_pending_sample`. Recipe reference unknown/null.
- **Cautions:** Publisher is Paul Bayfield/community, not CNOUS. Deduplicate against official CNOUS by origin, venue, date, meal and item; preserve cleaning provenance. No count established; download count and megabytes are not record counts.
- **Evidence:** [Primary source](https://www.data.gouv.fr/datasets/menus-du-crous); [Supporting source 1](https://www.data.gouv.fr/fr/dataservices/api-croustillant/).

#### Bègles canteen menus via Bordeaux Métropole (`fr_begles_menus`)

**Class:** dated collective menu rows. **Geography/language:** Bègles, France; fr.

- **Rights:** Licence Ouverte. Dataset-specific official catalog declaration.
- **Access/update:** CSV, JSON, OpenDataSoft API. Daily; indexed modified 2026-10-15. Public catalog.
- **Count:** No defensible menu/record count established.
- **Inspection:** Indexed official description and initial schema field inspected. Single-record API request inaccessible; payload schema not verified.
- **Parser:** `scdl_collective_menu_pending_sample`. Observed/described fields: menucollnom. Recipe reference unknown/null.
- **Cautions:** Coverage currently Bègles only, not all Bordeaux Métropole. Related dish-composition dataset is an enrichment join, not a full cooking recipe. Validate actual column names against SCDL; do not infer complete schema from one observed field.
- **Evidence:** [Primary source](https://datahub.bordeaux-metropole.fr/explore/dataset/met_menu_cantine/).

#### Toulouse school menus and Datameal dish composition (`fr_toulouse_menus`)

**Class:** dated school menu rows and dish composition. **Geography/language:** Toulouse, France; fr.

- **Rights:** Licence Ouverte v2.0 / Etalab. Official linked dish-composition dataset explicitly licensed; confirm each menu/ingredient/technical-sheet resource declaration before activation.
- **Access/update:** CSV, JSON, XLSX, Parquet. Dish dataset modified 2026-10-15; menu rows indexed for 2026. Export interface has terms acknowledgment; no click-through performed..
- **Count:** 596 menu dataset rows — Indexed 2026 tenant export at review; date/course/population rows, not unique menus. 280 dish-composition dataset records — Indexed official Datameal dataset; not 280 complete recipes.
- **Inspection:** Indexed official export fields and linked dataset metadata. No downloaded payload
- **Parser:** `toulouse_datameal_pending_sample`. Observed/described fields: DateMenu, Libelle_Repas, Libelle_Ordre_Plat, Libelle_Population_Cible. Recipe reference unknown/null.
- **Cautions:** Rows repeat by cohort/course/date; group without collapsing distinct adult/primary/preschool audiences. Related technical sheets may support recipes only where actual quantities and method exist. Detect CSV delimiter/encoding; do not rely on contradictory export UI wording.
- **Evidence:** [Primary source](https://toulouse-metropole.opendatasoft.com/explore/dataset/menus/export/); [Supporting source 1](https://data.toulouse-metropole.fr/explore/dataset/plats-extrait-de-datameal/).

#### La Rochelle collective menu archives (`fr_larochelle_archive`)

**Class:** historical dated collective menu rows. **Geography/language:** La Rochelle, France; fr.

- **Rights:** Licence Ouverte / Open Licence. Current city archive dataset; exact version unspecified.
- **Access/update:** CSV. Current catalog updated 2026-10-10. Public catalog; some files flagged unavailable.
- **Count:** 17,016 legacy school-menu rows — Deprecated predecessor only; NOT current archive count, and must not be added twice.
- **Inspection:** Current archive metadata plus deprecated predecessor metadata. No CSV payload
- **Parser:** `scdl_collective_menu_pending_sample`. Recipe reference unknown/null.
- **Cautions:** Includes schools and municipal crèches. Legacy endpoint explicitly marked for decommissioning; use current archive as canonical. Separate current/future rolling menus from archive; related allergen tables require exact date/dish joins.
- **Evidence:** [Primary source](https://www.data.gouv.fr/datasets/restauration-archives-des-menus-collectifs); [Supporting source 1](https://d4c.agglo-larochelle.fr/lv/dataset/archives_des_menus_des_restaurants_scolaires).

#### Marseille school and crèche historical menus (`fr_marseille_archive`)

**Class:** historical dated school menu rows. **Geography/language:** Marseille, France; fr.

- **Rights:** Licence Ouverte v2. Identified 2020–2021 catalog snapshot, not all current Marseille web PDFs.
- **Access/update:** CSV. Historical 2020–2021 school year; 171 KB CSV dated 2021-07-05. Public catalog; canonical production catalog resolution required.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official catalog description and field semantics. No CSV payload
- **Parser:** `marseille_menu_variants_pending_sample`. Observed/described fields: restaurant type, service date, menu variant, course, dish. Recipe reference unknown/null.
- **Cautions:** Alternative variants contain only changed dishes: derive full alternatives by explicitly documented inheritance from main menu on same date. Local last-minute substitutions are not necessarily captured. Additional historical school/crèche years are discovery expansion, not counted here. Do not transfer this historical dataset license to current public PDFs without evidence.
- **Evidence:** [Primary source](https://dev.data.gouv.fr/datasets/marseille-menus-des-cantines-ecoles-2020-2021).

#### Dijon municipal school menus (`fr_dijon_school`)

**Class:** dated school menu rows. **Geography/language:** Dijon, France; fr.

- **Rights:** Licence Ouverte v2. School menu dataset, unrelated to Dijon library historic menu image collection.
- **Access/update:** CSV, JSON. Catalog last updated 2022-11-07; stale. Some resources reported unavailable.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official catalog metadata. No payload
- **Parser:** `municipal_school_menu_pending_schema`. Recipe reference unknown/null.
- **Cautions:** Small stale supplemental source, not a large national corpus. Advertised CSV 5.2 KB and JSON 24.6 KB are file sizes, not counts.
- **Evidence:** [Primary source](https://www.data.gouv.fr/datasets/menus-de-la-restauration-scolaire).

#### Yamagata school lunch open data (`jp_yamagata_school`)

**Class:** dated school meal plan. **Geography/language:** Yamagata, Japan; ja.

- **Rights:** CC BY 4.0. Official school-lunch open data.
- **Access/update:** CSV. Official page updated 2026-05-27 (Reiwa 8). Public download.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official dataset license and resources. CSV opened via web but tool cannot render text/csv; actual columns not inspected.
- **Parser:** `japanese_school_csv_pending_schema`. Recipe reference unknown/null.
- **Cautions:** Byte sizes are not record counts. Retain original era dates and validate encoding before conversion. Planned menus are not verified meals served.
- **Evidence:** [Primary source](https://www.city.yamagata-yamagata.lg.jp/opendata/category/1007062/1012830.html).

#### Noshiro southern community kitchen lunch menus (`jp_noshiro_school`)

**Class:** dated school meal plan. **Geography/language:** Noshiro, Japan; ja.

- **Rights:** CC BY; version not stated on inspected page. Official school lunch open data.
- **Access/update:** CSV, XLSX. Page updated 2025-03-28; January–March 2025 southern community kitchen. Public download.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official field list, license and resource metadata. CSV opened via web but unsupported text/csv; no row payload.
- **Parser:** `noshiro_school_csv_pending_sample`. Observed/described fields: municipality code, school code, location, name, grade, date, dish name. Recipe reference unknown/null.
- **Cautions:** Quarterly local archive, not all Japanese schools. Keep school/grade targeting; one common kitchen menu can apply to multiple schools without being independent menus. Record license version as unspecified, not CC BY 4.0 by assumption.
- **Evidence:** [Primary source](https://www.city.noshiro.lg.jp/city/opendata/oopun/25473).

#### Shizuoka school lunch menu PDFs (`jp_shizuoka_school`)

**Class:** dated school meal plan with ingredients and meal nutrition. **Geography/language:** Shizuoka, Japan; ja.

- **Rights:** CC BY 4.0. Menu content ONLY; images explicitly excluded.
- **Access/update:** PDF with extractable text. Monthly kitchen/block menus; current October 2026 sample. Public download.
- **Count:** 2 pages in inspected PDF — October 2026 elementary B-block Mariko kitchen sample; not corpus count.
- **Inspection:** Actual two-page PDF text inspected. Dated dishes, ingredient classes, seasoning and meal nutrition visible.
- **Parser:** `shizuoka_monthly_pdf_layout`. Observed/described fields: date, dish names, ingredients by nutrition class, seasonings, energy kcal, protein g, calcium mg, salt g. Recipe reference unknown/null.
- **Cautions:** Reuse text data, not excluded illustrations or page images as distributable assets. Deduplicate same PDF linked from many schools while retaining school-menu relationships. PDF cautions about ingredient omissions/cross-contact: extracted allergens are not an allergy-safety guarantee. Ingredients without method/quantities are composition, not full recipes.
- **Evidence:** [Primary source](https://shizuoka-kyushoku.com/lunchmenu/); [Supporting source 1](https://shizuoka-kyushoku.com/core/wp-content/uploads/2026/09/c67552f078d25792b04fd569e1c4b393.pdf).

#### Konstanz archive: German university canteen meal options 2015–2024 (`de_konstanz_canteens`)

**Class:** research archive of dated menu items. **Geography/language:** Germany; de, en metadata.

- **Rights:** CC BY 4.0. Archived data package license explicitly listed; retain OpenMensa upstream provenance and transformation history.
- **Access/update:** research archive; internal file/schema not yet inspected. Repository publication 2026-07-31; historical data 2015–2024. No embargo indicated.
- **Count:** 340 canteens — Research analysis, 2015–2024. 3,789,253 entries after excluding two company canteens — Original paper, not fetched audit. 3,753,180 final meal options — After removing 36,073 closure/nonmeal entries; not unique recipes or menus.
- **Inspection:** Indexed repository metadata and primary paper. No archive downloaded. DOI inaccessible; repository direct open timed out after indexed metadata.
- **Parser:** `konstanz_openmensa_archive_pending_schema`. Observed/described fields: textual description, date, diet labels where available, price, canteen/coordinates. Recipe reference unknown/null.
- **Cautions:** Repository says collection February 2024; paper says 2025-02-28. Resolve discrepancy before ingest. Paper preprocessing lowercases/removes punctuation, converts zero price to missing and corrects 20 high-price values; archive may not preserve raw source text. Inferred diet labels are analytical classifications, not operator safety statements. Do not assume CC BY repository label settles upstream rights without provenance review.
- **Evidence:** [Primary source](https://kondata.uni-konstanz.de/radar/de/dataset/ty235ftth5yvg7hd); [Supporting source 1](https://doi.org/10.48606/ty235ftth5yvg7hd); [Supporting source 2](https://www.nature.com/articles/s44458-026-00138-3).

#### Finna licensed historical menu image subsets (`fi_finna_licensed_menu_images`)

**Class:** historical menu images and CC0 catalog not transcribed dishes. **Geography/language:** Finland; hotel/airline historical collections; fi, sv, other original menu languages unverified.

- **Rights:** API metadata CC0 1.0; selected menu images explicitly CC BY 4.0. API metadata only gets CC0; linked images require individual imageRights/accessRestrictions, e.g. licensed Finnair and Helsinki Seurahuone menu objects.
- **Access/update:** JSON API metadata, licensed images, some IIIF manifests. Provider-dependent historical collections. No registration required under current terms; API expressly not designed for large result sets..
- **Count:** No defensible menu/record count established.
- **Inspection:** Primary API terms/docs and indexed actual menu-object metadata. No API query or images downloaded. Finnair item direct page returned HTTP 403; no retry.
- **Parser:** `finna_rights_filtered_catalog_then_ocr`. Observed/described fields: imageRights, accessRestrictions, images, recordPage, fullRecord. Recipe reference unknown/null.
- **Cautions:** Apply item-level rights allowlist before image acquisition; no terms means ask supplying organization. Licensed images can support new OCR work, but are not an existing structured menu-item corpus. Honor API large-result limitation; supported bulk arrangements would be a separate scoped step. Collection counts and content-language distribution not established.
- **Evidence:** [Primary source](https://www.kiwi.fi/spaces/Finna/pages/53839699/Finna%2BAPI%2BTerms%2Bof%2BUse); [Supporting source 1](https://www.kiwi.fi/spaces/Finna/pages/53839221/Finna%2BAPI%2Bin%2BEnglish); [Supporting source 2](https://www.finna.fi/Record/sim.M016-28254); [Supporting source 3](https://www.finna.fi/Record/hkm.HKMS000005%3Akm002234).

### Tier B — conditional, not production-ready

#### NYPL What’s on the Menu historical transcriptions (`us_nypl_menus`)

**Class:** historical menu page item hierarchy. **Geography/language:** United States collection; international historical menus; multilingual; per-menu language field.

- **Rights:** Export-wide transcription license not yet verified; capture-specific NYPL rights vary. Do not apply public-domain/CC0 status of selected images to all transcriptions or all menus.
- **Access/update:** legacy JSON/XML API, historical relational CSV export. Legacy API; current original distribution/retirement status not independently resolved. Legacy API requires token.
- **Count:** 17,500 transcribed menus — Historical NEH funder description, not current audit. 1,330,000 dish transcriptions (over) — Same historical description; not unique dish names. 45,000 physical menus in collection — Collection size, not digitized structured-menu count. 14,450 menus in old API example — Documentation sample only; not current count. 323,958 dishes in old API example — Documentation sample only; not current count.
- **Inspection:** Actual documented JSON examples and primary funder/rights documentation. Support page HTTP 403; legacy data page inaccessible; no bulk export downloaded.
- **Parser:** `nypl_relational_csv_pending_license`. Observed/described fields: menu id, sponsor/place/event/date/language/currency, page count, dish count, menu page id, dish name, price/high price, page positions, creation/update timestamps. Recipe reference unknown/null.
- **Cautions:** Prioritize licensed/public-domain subsets once exact export and image rights are resolved. Do not combine 45,000 physical menus with 17,500 transcribed menus as additive coverage. Historical price/currency must retain date, original currency and source context. Do not fetch a third-party mirror to work around unavailable official resources.
- **Evidence:** [Primary source](https://nypl.github.io/menus-api/); [Supporting source 1](https://www.neh.gov/project/whats-menu); [Supporting source 2](https://api.repo.nypl.org/); [Supporting source 3](https://www.nypl.org/research/support/whats-on-the-menu).

#### NYC MenuStat historical chain restaurant nutrition (`us_menustat`)

**Class:** chain dish nutrition observations not full menu hierarchy. **Geography/language:** United States chains; en.

- **Rights:** NYC public-use purpose documented; exact downloadable dataset license not verified. Do not rely on unverified third-party claim of CC0 Harvard deposit.
- **Access/update:** CSV, JSON, XML, Socrata. Catalog last updated 2022-05-10; annual source methodology. Latest coverage unverified. Public export advertised.
- **Count:** 35,000 items (over), historical claim — Older consortium description; not current national total. 75 chains in a 2013–2021 study — Study inclusion subset, not entire service coverage.
- **Inspection:** Official catalog/methods indexed; primary research inspected. One-record API and columns endpoint inaccessible. Menustat homepage/codebook/method PDF returned 403 on direct requests; no retry.
- **Parser:** `menustat_socrata_pending_schema_license`. Observed/described fields: longitudinal item identifier, restaurant, year, food group, nutrition, serving size, kids/LTO/regional/shareable/combo flags, customizable_build_id. Recipe reference unknown/null.
- **Cautions:** Not a price corpus: original study states pricing, promotions and purchasing data not collected. Twelve food groups are analytical categories, not necessarily original menu sections. Customizable components/combos must not be blindly summed; beverage-variation collection differs across years. Article access license does not license underlying menu observations.
- **Evidence:** [Primary source](https://catalog.data.gov/dataset/dohmh-menustat-historical); [Supporting source 1](https://www.menustat.org/uploads/1/4/1/6/141624194/menustat_data_completeness_documentation.pdf); [Supporting source 2](https://pmc.ncbi.nlm.nih.gov/articles/PMC11757062/); [Supporting source 3](https://portal.311.nyc.gov/article/?kanumber=KA-02893).

#### DoltHub menus bounty 2021 (`global_dolthub_menus`)

**Class:** restaurant menu item price observations. **Geography/language:** Primarily United States; en predominant; content languages unverified.

- **Rights:** Data content license unverified. Open-source Dolt software is not a license for third-party restaurant data.
- **Access/update:** Dolt/SQL tables. 2021 historical snapshot; subsequent maintenance unverified. Public repository metadata.
- **Count:** 44,720 restaurants — Publisher 2021 bounty retrospective. 6,479,347 menu item rows — Publisher 2021 snapshot, not current menus. 2,695,669 publisher-defined unique menu items — Deduplication semantics must be inspected. 6,312,564 rows with price — 97.4% of snapshot rows. 157,125 rows with nutrition — 2.42% of snapshot rows.
- **Inspection:** Primary publisher SQL examples and counts. Repository web view did not expose license/schema; no clone or export.
- **Parser:** `dolthub_menus_sql_pending_license`. Observed/described fields: name, restaurant_name, identifier, price_usd. Recipe reference unknown/null.
- **Cautions:** Many records originate from Uber Eats/Grubhub; source terms and chain of rights unresolved. Do not infer current outlet stock, live price, or full course hierarchy. Do not treat repository visibility as redistribution permission.
- **Evidence:** [Primary source](https://www.dolthub.com/blog/2021-08-20-menus-bounty-retrospective/); [Supporting source 1](https://www.dolthub.com/repositories/dolthub/menus); [Supporting source 2](https://www.dolthub.com/blog/2021-07-07-announcing-us-menus-data-bounty/).

#### OpenMensa live community menus (`de_openmensa_live`)

**Class:** dated canteen menu items. **Geography/language:** Germany and participating canteens; de; other provider languages.

- **Rights:** Content license not established from inspected docs. Open parser/client code licenses do not automatically license all operator menus.
- **Access/update:** JSON API. Provider-dependent live menus; retained history unverified. Public documentation.
- **Count:** No defensible menu/record count established.
- **Inspection:** Actual documented two-meal JSON example. No live provider payload fetched
- **Parser:** `openmensa_v2`. Observed/described fields: id, name, notes[], category, prices.students, prices.employees, prices.others/pupils. Recipe reference unknown/null.
- **Cautions:** Community scrapers aggregate different original operators; permissions vary. Konstanz archive is a separate explicitly licensed release, not evidence that the live API content has the same license. Closed/no-service entries must not become dishes.
- **Evidence:** [Primary source](https://openmensa.org/); [Supporting source 1](https://docs.openmensa.org/api/v2/meals/); [Supporting source 2](https://docs.openmensa.org/api/v2/overview/).

#### Studentenwerk Dresden original menu API (`de_dresden_original`)

**Class:** dated institutional menu api. **Geography/language:** Dresden, Tharandt, Zittau and Görlitz, Germany; de, en documentation.

- **Rights:** External application use invited; archival/redistribution/commercial license not explicit. Application access permission is narrower than an open corpus license.
- **Access/update:** JSON, mostly OpenMensa v2. Original operator menu publication; cadence not audited. Public documented endpoint.
- **Count:** No defensible menu/record count established.
- **Inspection:** Original operator API documentation. No live payload
- **Parser:** `openmensa_v2_pending_operator_differences`. Recipe reference unknown/null.
- **Cautions:** Four listed places are cities/locations, not a count of canteens. Prefer original source over community re-scrape once reuse scope is recorded.
- **Evidence:** [Primary source](https://www.studentenwerk-dresden.de/english/mensen/speiseplan-api.html).

#### Swedish Open Meal protocol and provider network (`se_open_meal`)

**Class:** provider discovery standard not single dataset. **Geography/language:** Sweden; sv.

- **Rights:** Protocol/client openness does not establish provider menu-data license. Resolve each municipality/provider independently.
- **Access/update:** JSON REST, optional iCalendar. Provider-dependent school/retirement-home meal plans. Some providers require headers/API keys.
- **Count:** No defensible menu/record count established.
- **Inspection:** Standard and documented ICS example. No provider data or discovery registry fetched
- **Parser:** `open_meal_provider_json_or_ics`. Observed/described fields: DTSTART, DTEND, DTSTAMP, UID, CREATED, SUMMARY, DESCRIPTION, LOCATION, LAST-MODIFIED, SEQUENCE. Recipe reference unknown/null.
- **Cautions:** This is an interoperability standard and directory, not a national menu corpus. ICS requires line unfolding, escapes, timezone and date-only event handling. Public care-home menus are generic institutional content; never ingest resident-level medical data.
- **Evidence:** [Primary source](https://sambruk.github.io/Open-Meal/docs/intro/); [Supporting source 1](https://sambruk.github.io/Open-Meal/docs/API/data_providers/); [Supporting source 2](https://sambruk.github.io/Open-Meal/docs/API/specification/); [Supporting source 3](https://sambruk.github.io/Open-Meal/docs/API/icalendar/).

#### São Paulo Prato Aberto municipal school menus (`br_prato_aberto`)

**Class:** school menu search and extraction service. **Geography/language:** São Paulo, Brazil; pt-BR.

- **Rights:** Menu-data license not established; open code is insufficient. Municipal transparency purpose does not alone grant bulk redistribution.
- **Access/update:** API v1, manager dataset extraction described. API store last updated 2021-06-01; current backend status untested. Store explicitly requires login, subscription and bearer access token.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official API-store page and municipal project descriptions. No API call; authentication boundary respected.
- **Parser:** `prato_aberto_pending_documentation`. Recipe reference unknown/null.
- **Cautions:** Large number of meals served by a city is not the number of records available. No API docs attached in inspected store page; field names not verified. Do not treat public source code as data content permission.
- **Evidence:** [Primary source](https://apilib.prefeitura.sp.gov.br/store/apis/info?name=PratoAberto&provider=admin&version=v1); [Supporting source 1](https://patiodigital.sme.prefeitura.sp.gov.br/codigosabertos/); [Supporting source 2](https://copicola.prefeitura.sp.gov.br/como-divulgar-cardapios-escolares-de-forma-colaborativa-e-transparente/).

#### MenuStatic community restaurant menu PDFs (`global_menustatic`)

**Class:** menu documents not structured item database. **Geography/language:** Global contributions; coverage unverified; mixed.

- **Rights:** Uploader grants platform hosting/display rights; downstream open reuse not established. Public access/download is not a transferable corpus license.
- **Access/update:** PDF/menu images. Community-dependent Public site access; scraping terms not fully established.
- **Count:** No defensible menu/record count established.
- **Inspection:** Terms reviewed. No menu documents fetched
- **Parser:** `document_layout_only_after_permission`. Recipe reference unknown/null.
- **Cautions:** Not a structured database of complete dishes merely because files can be viewed. Obtain menu-content rights rather than relying on platform’s uploader license.
- **Evidence:** [Primary source](https://menustatic.com/terms-of-use/).

#### UNLV historic menu collection (`us_unlv_menus`)

**Class:** historical menu images and metadata. **Geography/language:** United States / international hospitality history; mixed; mostly English catalog.

- **Rights:** Item-specific copyright; site cautions permission may be required. Library may not own copyright; scan accessibility is not universal reuse permission.
- **Access/update:** Dublin Core metadata, TIFF/menu images. Historical collection; digitization updates not audited. Public catalog.
- **Count:** No defensible menu/record count established.
- **Inspection:** Digitization process and one actual menu catalog item. One item advertises 80.6 MB TIFF; not downloaded.
- **Parser:** `catalog_metadata_then_licensed_ocr`. Recipe reference unknown/null.
- **Cautions:** The Library menu record is an image object, not a pre-existing transcribed dish list. Only licensed/public-domain item subset after item-level provenance review; do not bulk-fetch scans.
- **Evidence:** [Primary source](https://special.library.unlv.edu/collections/menus/digitizing-menus); [Supporting source 1](https://special.library.unlv.edu/node/316710).

#### Dijon municipal library historic menus (`fr_dijon_library`)

**Class:** historical menu images and catalog. **Geography/language:** France and historical international events; fr predominant.

- **Rights:** Digitized-menu content reuse license not verified. Municipal school-menu open license does not apply to library scans.
- **Access/update:** catalog, digitized images. Historical collection beginning in nineteenth century; current exact count unverified. Public catalog.
- **Count:** 13,000 digitized menus approximately — Library collection description; not transcribed dish rows.
- **Inspection:** Primary library/city and BnF collection descriptions. No scans or transcription payload
- **Parser:** `catalog_then_licensed_document_ocr`. Recipe reference unknown/null.
- **Cautions:** Physical collection counts and digitized counts differ; do not sum or equate. No complete structured-dish export demonstrated.
- **Evidence:** [Primary source](https://bm.dijon.fr/explorerlescollections.aspx?_lg=fr-FR); [Supporting source 1](https://www.dijon.fr/dijon-a-votre-service/culture/bibliotheque-municipale/); [Supporting source 2](https://ccfr.bnf.fr/portailccfr/ark%3A/16871/007Fonds_4231).

#### Los Angeles Public Library historic menus (`us_lapl_menus`)

**Class:** historical menu images and catalog. **Geography/language:** California and worldwide restaurant/travel menus; mixed.

- **Rights:** Collection-wide downstream content license not established. Inspect item-specific rights and public-domain status.
- **Access/update:** catalog, menu scans. Historical digitization; some rescans/legacy entries unavailable. Public catalog.
- **Count:** No defensible menu/record count established.
- **Inspection:** Official collection description. No scans downloaded
- **Parser:** `catalog_then_licensed_document_ocr`. Recipe reference unknown/null.
- **Cautions:** Includes hotels, restaurants, ships, airlines and clubs; not a current restaurant menu service. Count and machine-readable full transcription availability unverified.
- **Evidence:** [Primary source](https://tessa.lapl.org/c10).

#### Generic hospital/care-home published menus (`institutional_hospital_care`)

**Class:** generic institutional meal plans not patient records. **Geography/language:** United Kingdom and France; en, fr.

- **Rights:** Per-site menu-content license not established. Do not apply NHS.uk OGL automatically to separate hospital domains or private care homes.
- **Access/update:** HTML weekly menus, PDF. Care-home current weekly October 2026 pages; hospital current scope not verified. Public pages.
- **Count:** No defensible menu/record count established.
- **Inspection:** Indexed official generic menu listings; no personal medical data. Leicester direct page timed out; not retried. No patient records sought.
- **Parser:** `generic_weekly_html_or_pdf_after_license`. Recipe reference unknown/null.
- **Cautions:** Generic texture/diet labels are menu variants, not evidence about named residents or patients. Use no resident names, ward patient lists, individual prescriptions or clinical records. Public availability alone is not permission for corpus republication.
- **Evidence:** [Primary source](https://www.uhleicester.nhs.uk/patients-visitors/staying-hospital/after-treatment/patient-menus/); [Supporting source 1](https://jeanne-de-baroncelli.fr/menus-de-la-semaine/); [Supporting source 2](https://ehpadlavarenne.fr/menu-de-la-semaine/).

#### Fortaleza school meal menu CSV (`br_fortaleza_school_csv`)

**Class:** school menu CSV schema unverified. **Geography/language:** Fortaleza, Brazil; pt-BR.

- **Rights:** Catalog explicitly says no license provided. Open-data portal placement is not sufficient content permission.
- **Access/update:** CSV, CKAN catalog. Resource and metadata last updated 2024-01-30; 19.2 KiB advertised. Public resource metadata.
- **Count:** No defensible menu/record count established.
- **Inspection:** Indexed official resource metadata; page shell. No CSV fetched; columns not verified.
- **Parser:** `fortaleza_csv_pending_license_and_schema`. Recipe reference unknown/null.
- **Cautions:** File size is not row count. Confirm actual granularity; dataset title alone does not establish dated menus or full dish hierarchy.
- **Evidence:** [Primary source](https://dados.fortaleza.ce.gov.br/dataset/cardapio-alimentacao-escolar/resource/5fce42f1-6f31-4b8e-a1f4-dd70c4e93d94).

### Tier C — restricted or non-equivalent

#### IST Skolmaten commercial integration (`se_skolmaten_ist`)

**Class:** school menu service. **Geography/language:** Sweden; sv.

- **Rights:** Contractual service terms; not an open content license. Additional paid integration license and API key described.
- **Access/update:** API. Service-dependent API key; paid integration conditions.
- **Count:** No defensible menu/record count established.
- **Inspection:** Vendor terms inspected. No service request
- **Parser:** `not_authorized`. Recipe reference unknown/null.
- **Cautions:** Do not equate Open Meal support or an ISC client license with free reuse of Skolmaten data. Do not activate without separately approved appropriate agreement.
- **Evidence:** [Primary source](https://www.ist.com/hubfs/139630678/Sweden/Dokument/Allm%C3%A4nna%20Villkor%20IST%20Skolmaten.pdf?hsLang=sv).

#### Souslab US restaurant menu sample (`us_souslab_sample`)

**Class:** restaurant menu item observations. **Geography/language:** United States; en predominant.

- **Rights:** CC BY-NC 4.0 sample; commercial use requires separate contract. 10,000-row sample only; full commercial product not open.
- **Access/update:** CSV, dataset viewer, commercial API separate. Sample snapshot 2026-05-29. Public sample; full product contracted.
- **Count:** 10,000 sample menu item rows — Snapshot 2026-05-29. 4,600 restaurants approximately — Sample publisher claim. 44,300,000 full-product menu items, advertised — Commercial product claim, not available open sample. 449,000 full-product restaurants, advertised — Commercial product claim, not verified corpus.
- **Inspection:** Dataset card and schema viewer. No dataset downloaded
- **Parser:** `souslab_csv_only_if_approved_compatible_use`. Observed/described fields: item_uid, restaurant_id, menu_name, section_name, item_name, description, price, price_text, currency, out_of_stock, city, state, zip, geolocation, canonical_item_id. Recipe reference unknown/null.
- **Cautions:** Noncommercial sample is not ready for unspecified commercial OffMenu use. Source out_of_stock is not reliable current availability and must not feed stock claims. Full-product scale must not be reported as open reusable coverage.
- **Evidence:** [Primary source](https://huggingface.co/datasets/AnyStackLabsdev/souslab-us-restaurant-menus).

#### MIND Korean diet-planning benchmark (`kr_mind`)

**Class:** synthetic diets and dish ingredient nutrition. **Geography/language:** South Korea; ko, en metadata.

- **Rights:** Ingredient data: Korea Open Government License Type 1; menu/diet components: noncommercial-only attribution. Component-specific license; do not extend commercial permission of ingredients to diets/menus.
- **Access/update:** dietKit dataset components. 2021 research release Research release.
- **Count:** 1,500 synthetic daily diets — Expert/optimization/ML-generated, not observed restaurant menus. 3,238 cooked dishes called menus — Not 3,238 multi-item real menus. 3,036 ingredients — Separate component of benchmark.
- **Inspection:** Original paper and license supplement. No package downloaded
- **Parser:** `research_only_dish_component_mapping`. Recipe reference unknown/null.
- **Cautions:** Useful benchmark only if purpose is license-compatible; not the requested real-menu corpus. Fourteen nutrient dimensions do not make it a cooking-instruction recipe collection.
- **Evidence:** [Primary source](https://datasets-benchmarks-proceedings.neurips.cc/paper/2021/file/e3796ae838835da0b6f6ea37bcf8bcb7-Paper-round2.pdf); [Supporting source 1](https://openreview.net/attachment?id=woX9uagUQiE&name=supplementary_material).

#### Menu image/OCR benchmarks (MMConflict and Roboflow examples) (`global_menu_ocr_benchmarks`)

**Class:** image annotation benchmarks not full transcribed menus. **Geography/language:** Mixed/unknown; en annotations.

- **Rights:** CC0 / CC BY 4.0 claims respectively; underlying image provenance not established. Annotation license claims do not settle rights in all photographed menus.
- **Access/update:** images, bounding boxes, question annotations. Dataset-card release dependent. Public cards.
- **Count:** 500 images/questions in MMConflict — One candidate price/item bounding-box question per image; not 500 complete structured menus. 100 images in Roboflow example — Single menu object class; not dish transcription rows.
- **Inspection:** Dataset cards inspected. No images downloaded
- **Parser:** `evaluation_only_not_menu_import`. Recipe reference unknown/null.
- **Cautions:** MMConflict card indicates inherited Kaggle provenance and not human verified. Do not inflate structured-menu coverage with image count or selected question count.
- **Evidence:** [Primary source](https://huggingface.co/datasets/shivank21/mmconflict-restaurant-menus-500); [Supporting source 1](https://universe.roboflow.com/joel-kitching-4hi4b/restaurant-menus).

## Coverage and exclusions

- No claim of exhaustive all-language/global coverage. Highest-confidence large structured sources found are East Asian school meals, European institutional menus, and a German historical canteen archive.
- Arabic, Indic, African, mainland Chinese, Spanish-language and Southeast Asian nationwide reusable dated-menu coverage remains unestablished in this review; absence of a verified source is not evidence none exists.
- Historical-menu scans extend format/language breadth but need rights-filtered OCR and must not be counted as already structured transcriptions.

- **fr_national_canteen_register:** Venue/operator register, not dated dish menus; useful licensed venue enrichment only. [Source](https://www.data.gouv.fr/datasets/registre-national-des-cantines)
- **wfp_school_meals:** Program indicators, coverage and policy, not daily school menu records. [Source](https://www.schoolmealscoalitiondatabase.wfp.org/about)
- **openfoodfacts:** Primarily product database; restaurant nutrition imports are not faithful menu hierarchies. Reported undefined ingredient imports make inferred ingredients unsafe; coordinate separately with product/food-source stream. [Source](https://github.com/openfoodfacts/openfoodfacts-server/issues/14863)
- **shifttrained_aggregate:** Licensed aggregate statistics derived from 15,000 items do not establish a downloadable raw menu-item corpus. [Source](https://www.shifttrained.com/data)
- **places_and_taxonomies:** OSM/AllThePlaces venue records and Wikidata/Wikipedia dish taxonomies are optional enrichment, not menu corpora.
- **fi_lounasopas_aggregates:** Indexed publisher says CC BY 4.0 CSV/JSON analytics; menu-derived deduplicated dish statistics are not established as raw dated menu records. Direct page cache miss; no retry. Secondary upstream rights and exact export scope unresolved. [Source](https://lounasopas.com/lounashinnat/kunta/kirkkonummi)

### Bounded expansion paths

- **Japan:** Official additional municipal menu leads with indexed CC notices; verify exact dataset/image scope before separate registry entries. [Official lead 1](https://www.city.joetsu.niigata.jp/site/syoku-iku/kyusyoku-dayori.html); [Official lead 2](https://www.city.kanuma.tochigi.jp/0530/info-0000009896-0.html?idSubTop=0); [Official lead 3](https://opendata.city.chiba.jp/dataset/3180-3?activity_id=d87877d1-65e6-44aa-acf1-4c60107325b6)
- **Taiwan:** Regional academic-year CSV sibling menus and ingredients; avoid overlap with national 2.0 extraction. [Official lead 1](https://data.gov.tw/en/datasets/78344)
- **France:** Discover further compliant municipal datasets by schema, then verify each data license and resource availability. [Official lead 1](https://schema.data.gouv.fr/scdl/menus-collectifs/1.2.1/documentation.html)
- **India:** Official menu-policy/revision circulars found, but no verified licensed nationwide dated-menu dataset in this review. Do not equate program counts or policy templates with recorded daily menus. [Official lead 1](https://pmposhan.ap.gov.in/MDM/MDMCircularsDownload.aspx); [Official lead 2](https://pmposhan.education.gov.in/latest_update.html)

## Access outcomes and unresolved blockers

A denial, unsupported format, timeout and unknown API-key condition are distinct. None was used as justification for a bypass, source mirror or uncontrolled retry. Exact target URLs are in the JSON.

| Target/action | Observed result | Remaining action |
|---|---|---|
| Taiwan OpenAPI JSON documentation: Read documentation | HTTP 403 | No retry or bypass. Obtain supported official access/documentation after gates. |
| NEIS one-row API sample: Read one sample row | Web inaccessible | No retry; document auth/key procedure before activation. |
| Bordeaux one-row API sample: Read one sample row | Web inaccessible | No retry; schema remains unverified. |
| CNOUS one XML resource link: Read advertised 16.4 KB feed | Internal tool error; final resource URL not returned | No retry; catalog-only evidence. |
| Yamagata CSV: Inspect schema/sample | Web unsupported text/csv response | No download fallback performed; sample validation pending. |
| Noshiro CSV: Inspect schema/sample | Web unsupported text/csv response | No download fallback performed. |
| Konstanz repository/DOI: Read data-package metadata | Indexed metadata available; direct DOI inaccessible and repository page timed out | No archive requested or mirrored. |
| NYPL support/current distribution: Read current support/availability | HTTP 403; legacy data page inaccessible | No retries, third-party mirrors or bypass. |
| MenuStat documentation: Read homepage/codebook/method document | Direct HTTP 403 responses; indexed methods and official catalog available | No retries/bypass. Exact content license remains unresolved. |
| MenuStat NYC sample/schema: Read one row and schema metadata | Web inaccessible | No retry; no payload fields independently sampled. |
| MenuStat alleged Harvard deposit: Verify secondary CC0 claim against original deposit | Original deposit inaccessible; primary license not established | Do not use secondary CC0 claim. |
| Prato Aberto API: Read API-store documentation | Completed; bearer token/login/subscription requirement visible | No API request or authentication bypass. |
| Leicester generic patient menu page: Read generic institutional menu page | Timeout | Not retried; no private patient records requested. |
| Finnair menu object: Read licensed-item catalog page | Indexed metadata license visible; direct HTTP 403 | No retry or alternate acquisition; no images fetched. |
| LounasOpas aggregate page: Inspect claimed CSV/JSON analytic export scope | Indexed description available; direct cache miss | No retry; treat as aggregate-only lead, not raw menu corpus. |

## Activation sequence — not executed

1. Establish that **all eight databases are provisioned and relationally fit for existing data**. Until then no production acquisition on Foo.
2. Resolve each source’s data-content rights, attribution, provenance and original access. Code, article and selected-image licenses cannot substitute for dataset rights.
3. After applicable gates, obtain authorized small fixtures through supported original endpoints. Validate schema, language/encoding, date/currency meaning, row unit, revisions and recipe-link evidence. Do not bypass a 403.
4. Test price-kind distinctions, nutrition scope, allergen trace ambiguity, alternative-menu inheritance, closure filtering and mirror/shared-school deduplication.
5. Honor documented pagination/rate limits, retention and bulk-access restrictions; estimate volumes from verified metadata, not download counters or byte sizes.
6. Enable only separately cleared sources on Foo after the user gate. **This report enables none.**

## Deliverables

- `menus.md`: this evidence review.
- `menus.json`: 31 inactive source-family entries, field mappings, count semantics, license evidence, exclusions and access outcomes.
- No raw corpus, credentials, source archive, active production configuration or database data included.

