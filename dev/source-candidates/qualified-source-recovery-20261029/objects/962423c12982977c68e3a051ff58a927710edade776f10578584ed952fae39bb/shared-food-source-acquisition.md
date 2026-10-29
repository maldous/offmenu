# OffMenu shared-source acquisition and coverage reference

Research checked: 18 October 2026 (UTC). Scope: official documentation and publisher-maintained technical references; no bulk data acquisition, country-coverage computation, repository changes, or acquisition jobs were performed.

## Decision boundary

The project-supplied historical rationale is retained as context: Open Food Facts (OFF) is the barcode baseline; USDA FoodData Central (FDC) is the US nutrition baseline; WFP supplies market/commodity/date-specific prices; FAO supplies distinct catalogue, guideline and vocabulary resources. This review validates acquisition guidance. It does not establish who originally chose these sources or invent historical decisions.

None of these sources establishes complete coverage of the project's 249 countries/territories. A shared source can be stored once, with country references into it. A country reference is not evidence of a complete national food database, local availability, representative nutrition measurements, or current prices.

## 1. Open Food Facts product database

**Exact content and attribution.** Community-contributed product/barcode records contain ingredients, nutrition and other product information. `countries` means countries where a product is sold; retain `countries_tags` and `countries_hierarchy` plus the country-taxonomy mapping. Keep ingredient origins and manufacturing locations separate. A product may legitimately belong to multiple sales countries. Missing/invalid country tags are unresolved attribution, not permission to infer a country from language or barcode prefix. The publisher disclaims completeness, reliability and accuracy. [Product schema](https://openfoodfacts.github.io/documentation/docs/Product-Opener/schemas/schemas/product_tags/) · [API overview](https://openfoodfacts.github.io/openfoodfacts-server/api/)

**Acquisition.** The official SDK identifies these global food exports:

- `https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz`: gzip-compressed JSON Lines, broad product representation.
- `https://static.openfoodfacts.org/data/en.openfoodfacts.org.products.csv.gz`: gzip-compressed tab-delimited file despite its `.csv` name, a reduced field selection.

The `en` filename is not evidence that the export covers only England or English-speaking countries. Preserve the downloaded original and derive country views separately. Check obsolete-product handling explicitly if historical completeness matters. OFF recommends bulk CSV/JSONL rather than API enumeration for more than a few hundred products, and describes daily exports. [SDK dataset implementation](https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-python/develop/src/openfoodfacts/dataset.py) · [SDK usage](https://openfoodfacts.github.io/openfoodfacts-python/usage/) · [API overview](https://openfoodfacts.github.io/openfoodfacts-server/api/)

**Freshness/integrity.** OFF's official SDK supports cache reuse and an optional ETag-based newer-file check. Its helper stores the URL, ETag and download timestamp; it performs a full streamed download to temporary storage, rather than demonstrating byte-range resume or a cryptographic checksum verification. These are moving export URLs, so preserve acquisition time, validators and a local SHA-256 under a versioned snapshot identity. No publisher checksum manifest or reliable delta-resume contract was verified in the reviewed references; do not assume one. [SDK download/cache helper](https://raw.githubusercontent.com/openfoodfacts/openfoodfacts-python/develop/src/openfoodfacts/utils/__init__.py)

**Access/reuse.** Reads require no account; use the publisher's identifying User-Agent and current limits if using the API. Database: ODbL; individual contents: Database Contents License; images: CC BY-SA with possible additional rights. OFF's caching guidance stresses share-back and warns against mixing incompatible external product data. Keep source custody and derived-database licensing explicit before consolidation or redistribution; an open download is not an unrestricted licence. [Licensing](https://openfoodfacts.github.io/openfoodfacts-server/api/tutorials/license-be-on-the-legal-side/) · [Caching guidance](https://openfoodfacts.github.io/openfoodfacts-server/api/tutorials/creating-a-local-cache-of-open-food-facts-data/)

## 2. USDA FoodData Central

**Exact datasets.** Preserve `data_type` and `fdc_id` rather than treating FDC as one homogeneous table:

- Foundation Foods: analytical commodity/minimally processed-food samples and variability metadata.
- Experimental Foods: research data associated with USDA-supported or collaborative publications.
- FNDDS: nutrient and portion values for foods reported in the US WWEIA/NHANES dietary survey.
- Branded Foods/GBFPD: voluntarily supplied product-label data, not uniformly laboratory measurements.
- SR Legacy: historical composition data, final release April 2018.

This supports a US-reference baseline, not 249 national baselines. [FDC data-type comparison](https://fdc.nal.usda.gov/data-documentation/)

**Country attribution.** Branded `market_country` identifies a product's availability market; retain it with `gtin_upc`, `fdc_id`, publication and modification dates. It is not manufacturing origin. Current HTML documentation lists United States and New Zealand; an older April 2024 PDF also listed Canada. Therefore measure the countries in the actual chosen release and retain its schema rather than hard-coding either list as timeless truth. Non-branded records must not be replicated as locally measured evidence for every country. [Current branded documentation](https://fdc.nal.usda.gov/GBFPD_Documentation/) · [Older April 2024 documentation](https://fdc.nal.usda.gov/docs/Branded_Foods_Documentation_Apr2024.pdf) · [Download field dictionary](https://fdc.nal.usda.gov/portal-data/external/dataDictionary)

**Acquisition/release metadata.** Use the official download catalogue's actual linked ZIPs, with CSV or JSON by data type, or the full CSV archive. The catalogue observed on the research date lists Foundation/Branded/full April 2026; FNDDS 2021–2023 released October 2024; SR Legacy April 2018. Save the displayed release, resolved download URL, archive size and bundled field dictionary. Supporting tables are included in archives from April 2023 onward. Historical archives may be corrected and reissued, so a date-labelled filename alone does not prove immutable bytes. [Download catalogue](https://fdc.nal.usda.gov/download-datasets/)

**Freshness/integrity.** Branded online/API data are updated monthly, while bulk files are generally twice yearly; these are different freshness promises. Foundation generally updates April/October, FNDDS with survey releases, and SR Legacy is frozen. Recheck the release catalogue rather than promising a new file every 30 days. No official checksum manifest or byte-range-resume guarantee was verified here; apply the conditional transport procedure below. [Branded documentation](https://fdc.nal.usda.gov/GBFPD_Documentation/) · [Data-type comparison](https://fdc.nal.usda.gov/data-documentation/)

**Access/reuse.** Public bulk links avoid API credentials. API access requires a data.gov key and currently documents a default 1,000 requests/hour/IP; protect keys. FDC data are public domain/CC0, with source acknowledgement requested. [FDC API and licensing guide](https://fdc.nal.usda.gov/api-guide/)

## 3. FAO dietary-guideline resources: keep three objects distinct

### A. Country catalogue and country profiles

FAO's public FBDG site is a curated HTML catalogue with country pages, not a single standardized downloadable national food-composition dataset. It describes more than 100 countries having developed guidelines, rather than all 249 project jurisdictions. Attribute a profile by its named country and canonical page URL; any ISO mapping is a separately recorded OffMenu mapping. A regional guide is not automatically a national guide for every member. Absence from the catalogue does not establish that a country has no guideline. [Catalogue](https://www.fao.org/nutrition/nutrition-education/food-dietary-guidelines/regions/en/) · [Background](https://www.fao.org/nutrition/education/food-dietary-guidelines/background/en/)

### B. Original guideline and educational documents

Country pages identify document names, publication/revision years, audiences and download links. These links can lead to national institutions, and materials vary by format, language, edition and age group. Preserve the profile separately from each original PDF/image/other file, including publisher, country, language, audience, edition/year, exact URL and licence evidence. A profile's retrieval date is not the guideline's publication date. The Brazil profile illustrates distinct 2014 general-population and 2019 young-child resources. [Example country profile](https://www.fao.org/nutrition/education/food-dietary-guidelines/regions/countries/brazil/en/)

**Freshness/access/reuse for A/B.** Public browsing requires no account. No uniform release cadence, bulk API, checksum manifest or resumable-download contract was established for the catalogue and linked documents. Revalidate each page/document and compare edition and content hash. Critically, FAO says national materials were republished with the owners' permission and further use requires permission from the copyright holder. Catalogue access does not supply a blanket redistribution licence for those originals. Check each document's actual terms before uses beyond permitted access/copying. [FAO country-material rights notice](https://www.fao.org/nutrition/nutrition-education/food-dietary-guidelines/regions/en/)

### C. AGROVOC vocabulary, if acquired as a separate shared asset

AGROVOC is a multilingual concept/term/relationship thesaurus. Concept URIs and language-tagged labels are semantic identifiers, not measured country food coverage. FAO documents RDF Core (RDF/XML, N-Triples) and LOD (N-Triples, N-Quads), with release timestamp on the concept scheme and VoID metadata. Save the chosen distribution and release metadata; do not label it a national guideline or nutrition dataset. [AGROVOC releases](https://www.fao.org/agrovoc/releases)

Updates are monthly. Current maintenance guidance assigns the six FAO-language content CC BY 4.0; rights in other languages rest with contributing institutions. An older AIMS FAQ still states CC BY-IGO 3.0, so retain release-specific rights evidence rather than applying one licence indiscriminately. Downloads/browsing are public; no registration or payment is required according to the FAQ. No checksum/resume guarantee was verified. [Current maintenance/rights](https://www.fao.org/agrovoc/maintenance) · [Older FAQ](https://aims.fao.org/standards/agrovoc/faq)

## 4. WFP Food Prices distributed through HDX

**Exact dataset and limits.** Use the HDX series `WFP - Food Prices` and its per-country price/market resources, or the separately identified global aggregate. Publisher-maintained OCHA pipeline metadata describes 98 countries and roughly 3,000 markets, weekly updating with mostly monthly observations, and uneven historical start dates. These are advertised scope figures, not a fresh count performed for OffMenu. Do not confuse the series with WFP Market Monitor or other derived indicators. Coverage is limited to observed market/commodity/date combinations, not every food, shop or territory. [Official pipeline metadata](https://raw.githubusercontent.com/OCHA-DAP/hdx-scraper-wfp-foodprices/main/src/hdx/scraper/wfp/foodprices/config/hdx_dataset_static.yaml)

**Attribution/schema.** The official pipeline's price CSV schema includes `date`, `admin1`, `admin2`, `market`, `market_id`, coordinates, `category`, `commodity`, `commodity_id`, `unit`, `priceflag`, `pricetype`, `currency`, `price`, `usdprice`. Its market CSV includes `countryiso3`. Country price files can rely on dataset-level country metadata rather than carrying a country column in every row; join markets via `market_id` and retain the verified dataset country. Never discard unit/currency, retail/wholesale type, observation flag or date. [Official schema configuration](https://github.com/OCHA-DAP/hdx-scraper-wfp-foodprices/blob/main/src/hdx/scraper/wfp/foodprices/config/project_configuration.yaml)

**Acquisition/provenance.** HDX's official cookbook documents `package_search`, `package_show`, country `groups`, series filtering and resource download URLs. Select resource by its identity/type, not blindly the first file. Retain package/resource IDs, original metadata JSON, country mapping, licence, reference period and exact resource URL. HDX country codes are usually lowercase ISO3 but include country-like entities. The OCHA pipeline publishes per-country prices and markets CSVs plus a global CSV; its processing includes USD conversion and duplicate consolidation. Thus an untouched local HDX CSV is an original copy of that published distribution, not necessarily raw WFP observations before processing. [HDX API cookbook](https://data.humdata.org/dataset/2048a947-5714-4220-905b-e662cbcd14c8/resource/3b675846-d01c-4fc9-b577-b7d426d2a598/download/hdx-ckan-api-cookbook.pdf) · [Official pipeline description](https://github.com/OCHA-DAP/hdx-scraper-wfp-foodprices)

**Freshness/access/reuse.** Public distribution is specified in pipeline metadata, with `cc-by-igo`; retain the resource's actual licence record and give attribution under the applicable licence. Preserve observation date separately from publication/retrieval timestamps. HDX metadata modification time alone can miss changes in an externally hosted resource. Public metadata and original resource retrieval are the recommended route; direct WFP API access requirements were not validated. No WFP/HDX resource checksum or byte-range-resume promise was established in this review. [Pipeline metadata](https://raw.githubusercontent.com/OCHA-DAP/hdx-scraper-wfp-foodprices/main/src/hdx/scraper/wfp/foodprices/config/hdx_dataset_static.yaml) · [HDX API cookbook](https://data.humdata.org/dataset/2048a947-5714-4220-905b-e662cbcd14c8/resource/3b675846-d01c-4fc9-b577-b7d426d2a598/download/hdx-ckan-api-cookbook.pdf) · [CC BY 3.0 IGO](https://creativecommons.org/licenses/by/3.0/igo/)

## Recommended custody and 30-day cache contract

The following are implementation recommendations, not claims of existing OffMenu behavior or provider guarantees:

1. Preserve exact original downloaded bytes separately from extracted/normalized data, with source ID, requested/final URL, acquisition timestamp, publisher release/reference period, response validators, byte count, local SHA-256, MIME/format, licence evidence and parser/schema version. Never place credentials in provenance.
2. Retain each successful original snapshot for at least 30 days. Retention and freshness are independent: checking for updates need not delete or mutate the previous original. If the intended policy instead means no network revalidation during 30 days, encode that explicitly and display the known source age.
3. Reuse verified local files. On revalidation use ETag/If-None-Match or Last-Modified/If-Modified-Since where actually supported. An ETag is a validator, not necessarily a content checksum. Resume a partial file only against the same representation with a suitable strong validator and validated `206`/`Content-Range`; on changed validators or a full `200`, restart safely rather than append. Range support is optional and was not probed for these assets. [HTTP conditional/range semantics](https://www.rfc-editor.org/rfc/rfc9110.html)
4. Treat absent publisher checksums as unverified provenance authenticity, not as a failed local checksum. Compute SHA-256 for local custody; compare any publisher checksum only when its algorithm and exact byte representation are documented. Validate archive integrity and parseability before atomically promoting a download. Local hashing does not prove that upstream data are accurate.
5. Maintain a 249-jurisdiction coverage matrix with separate dimensions for barcode, composition, guideline and price evidence. Record supported/partial/not-listed/unresolved/not-applicable, evidence and observation/release dates. `Downloaded`, `country-attributed`, `usable` and `complete` are separate states. Do not turn missing records into zeros or claim coverage through a fallback alone.

## Verification limits

The web research tool could not retrieve the OFF main data page (robots policy) or live WFP/HDX dataset/API pages (fetch errors). OFF's own documentation/SDK and OCHA's official distribution documentation/code were used instead. No restriction was bypassed. Download HTTP headers, current country counts, exact per-country licence payloads, provider-side checksum manifests, source bytes and local acquisition/resume behavior remain to be verified in an authorized acquisition run. This reference does not claim that any data have been downloaded or cached.
