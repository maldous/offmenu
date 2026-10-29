# Somalia (SO/SOM): original-source acquisition plan

Verified 18 October 2026. Research handoff for Morgan Gateway; former Worker30 is closed. This is an acquisition manifest, not a completed dataset or a licence opinion. No Foo access, bulk collection, repository writes, new coordinator, account creation or provider contact occurred. Only public pages/metadata, PDF-reader inspection, a 6,975-byte market-reference CSV and a 1,400-byte prices header/sample were read. Keep all current downstream holds intact.

## Findings and order of work

1. **P0: WFP prices and market reference; FSNAU basket workbooks; SNBS CPI.** Strong official acquisition targets, with distinct prices, market locations, humanitarian baskets and inflation-index roles.
2. **P1: Somali food practices and population nutrition.** Original FAO-FSNAU field studies provide local food names and preparation descriptions. New CFSVA 2026 is based on 2025 fieldwork; it is not a food-composition database.
3. **P1: SoBS provider/product certification metadata and regulatory notices.** Small live public registers exist, but do not constitute all Somali food businesses or a comprehensive recall feed.
4. **Gap: national analytical food composition.** No current Somalia-specific national table verified. A historical shared FAO/USDA Near East table explicitly includes Somalia in its source-search scope; each food's provenance must be checked. Do not call Kenya, Tanzania, West Africa or generic global nutrient values Somali analytical data.
5. **Gap: full current dietary-guidance package.** Somalia's 2026 MIYCAN launch is verified; the complete downloadable package was not found. Older guidance remains an archival source, not silently current. No general-population national food-based dietary guideline was verified.

## P0 acquisition targets

### SO-WFP-PRICE: World Food Programme original price database via HDX

- Landing: https://data.humdata.org/dataset/wfp-food-prices-for-somalia
- Public metadata: https://data.humdata.org/api/3/action/package_show?id=wfp-food-prices-for-somalia
- Prices: https://data.humdata.org/dataset/26727d1b-af49-4323-9215-c2ac479abb87/resource/39614bfb-0f9c-4800-8997-e68e41a38ced/download/wfp_food_prices_som.csv
- Market reference: https://data.humdata.org/dataset/26727d1b-af49-4323-9215-c2ac479abb87/resource/bf3725e2-cbb5-4dc2-8d6a-2f2f1c6ef855/download/wfp_markets_som.csv
- Release/format: prices CSV metadata modified 2026-10-11, advertised 5,314,485 bytes; declared observation range 1995-01-15–2026-08-15. Markets CSV modified 2026-09-27, 6,975 bytes. Metadata JSON.
- Coverage: observed market-reference file has 145 distinct market IDs, 18 nonempty admin1 labels and 74 nonempty admin2 labels; one record lacks admin1. These are reference locations, **not 145 verified price-series markets**. Actual commodity/market/time coverage must be computed from acquired price rows. The 98-country/3,000-market statement in metadata describes the global database and must not be copied as Somalia coverage.
- Schema verified: date, admin1, admin2, market, market_id, latitude, longitude, category, commodity, commodity_id, unit, priceflag, pricetype, currency, price, usdprice. Preserve price flags, currency and unit; do not merge Somali and Somaliland currency values without explicit conversion provenance.
- Licence: publisher metadata says CC BY-IGO, linked to http://creativecommons.org/licenses/by/3.0/igo/legalcode . Capture the licence with the acquired revision.
- Access: landing returned HTTP403 to the web reader. The official public metadata endpoint and small CSV/header reads independently succeeded. Preserve both facts; this is not authority to circumvent provider restrictions or Foo holds. Full prices CSV was not downloaded.

### SO-FSNAU-MEB: FAO-FSNAU minimum expenditure baskets

- Landing/method: https://fsnau.org/sectors/markets
- General basket, May 2026: https://fsnau.org/downloads/CMB%20for%20Somalia%2C%20Main%20Cereal%20is%20Red%20Sorghum_May%202026.xlsx
- Cash-intervention urban/main markets, May 2026: https://fsnau.org/downloads/CMB%20Cash%20Based%20Intervention%20Urban%20Main%20Markets_May%202026.xlsx
- Format: XLSX, landing sizes 614 KB and 579 KB respectively. These are separate products, not duplicates. Reader reached XLSX content but cannot parse that MIME; no download denial established.
- Coverage: method describes 71 monitored markets, 46 urban/25 rural. Four minimum baskets separate rural/urban and northwest Somaliland-shilling areas/rest-of-country Somali-shilling areas. Basic food and nonfood requirements; food energy basis 2,100 kcal/person/day, household 6–7. The cash-intervention workbook is restricted to urban/main markets. Exact current sheets, rows, periods and town completeness still require file inspection.
- Important: these are minimum humanitarian expenditure baskets, not nutritionally optimal menu recommendations. FSNAU basket-based CPI uses March 2007; do not combine it directly with SNBS CPI.
- Access: https://fsnau.org/ids/index.php offers Excel exports behind registered login; https://api.fsnau.org/ requires an API key and email. Stop before credential/access provisioning. Use public publications first.
- Rights: no file-specific open licence verified. Apply FAO/FSNAU rights review before commercial redistribution or database incorporation; see rights section.

### SO-SNBS-CPI: Somali National Bureau of Statistics

- Index: https://nbs.gov.so/category/consumer-price-index/
- Current verified landing: https://nbs.gov.so/consumer-price-index-cpi-aug-2026/
- PDF: https://nbs.gov.so/wp-content/uploads/2026/10/CPI-Report_2026_August.pdf
- Release: August 2026 observations, eight-page PDF, hosted under October 2026. Do not confuse publication month with price month.
- Coverage/type: report says Mogadishu plus all Federal Member States; 537 basket items, COICOP2018, 13 divisions. Output is aggregate inflation and component indices, not a unit-price catalogue. Historic October 2024 report covers four Mogadishu collection zones only. A methodological page mentions Somaliland, but the inspected August 2026 report does not; verify actual published state rows before asserting Somaliland coverage.
- Licence: SNBS portal data terms https://nbs.gov.so/terms-of-use-for-open-data-portals-and-datasets/ specify CC BY4.0, attribution/source link, retained notices, changes and no endorsement, with additional/general terms. Confirm this file is within that grant rather than treating every site publication as automatically open-licensed.

## P1 food practices, nutrition and guidance

### SO-CFSVA-2026: SNBS/WFP/FAO-FSNAU joint assessment

- Landing: https://nbs.gov.so/cfsva2026report/
- Working official file target: https://fsnau.org/downloads/CFSVA-2026-SNBS-FAO-FSNAU-WFP.pdf
- FSNAU publication index: https://fsnau.org/products/research-studies (posted 15 June 2026).
- PDF advertised 12,403,265 bytes; web reader rejected size, not provider access. Old indexed SNBS https://nbs.gov.so/wp-content/uploads/2026/05/CFSVA_Report2026.pdf returned404; preserve it as a failed alias, not the acquisition target.
- Coverage: official indexed executive summary says 8,816 households, 34 districts, 17/18 pre-war regions, **Middle Juba excluded**, urban/rural/IDP populations; fieldwork February–May2025. Includes consumption, food spending, food access and vulnerability. Do not infer nomadic coverage or individual nutrient intake from household measures. Confirm survey exclusions in the full methodology on acquisition.
- Rights: joint publication; inspect its copyright page. Deduplicate any identical WFP/SNBS/FAO copies by hash while retaining all publisher URLs.

### SO-FSAU-FOODUSE-2002: original food-use case studies

- PDF: https://fsnau.org/downloads/Food-Utilization-in-Somalia-September-2002.pdf
- September 2002, 54 pages; index https://fsnau.org/products/research-studies .
- Scope: four livelihood case studies in two areas: Hiran riverine and southern agropastoral in Belet-Weyne; Hawd pastoral within 60 km of Hargeysa and Hargeysa urban. Historic local preparation, meal composition, seasonality, storage and food names, including canjeero, soor, cambulo and iskukaris. Not representative of all present-day Somalia or diaspora cuisine.
- Use preparation descriptions as attributed observations, not measured standardized recipes. Annex 3 explicitly says nutrient values were borrowed from composition tables, not directly analyzed for this study. Do not label them Somali laboratory measurements.
- Rights: FAO publication, no file-level permissive licence verified.

### SO-FSNAU-FISH-2011 and SO-FSNAU-OFFAL-2010

- Fish PDF: https://fsnau.org/downloads/KAP-Study-Fish-Consumption-in-Somalia.pdf (November 2011; 26 pages).
- Fish scope: primary qualitative work in 25 locations, May 18–June 25 2011; coastal/inland/riverine and urban/rural sites across South Central, Puntland and Somaliland.60 focus groups and 75 key-informant interviews. Useful local fish names, consumption barriers, preferred species, preparation and preservation. Purposive fieldwork, not current national consumption prevalence.
- Offal PDF: https://fsnau.org/downloads/KAP-Study-Offal-Consumption-July-2010.pdf (July 2010; 28 pages).
- Offal scope: Boroma, Burao and Bossaso; local offal names, food practices and cooking descriptions. Narrative beliefs are not established medical benefits; some reported practices are unsafe. Keep them descriptive and out of recommendation-generation. Table 3 nutrient values need source tracing and unit/outlier review before use; do not treat the table as a national composition source.
- Both appear in https://fsnau.org/products/research-studies . Rights require FAO/file-specific review.

### SO-MOH-MICRO-2019: national micronutrient survey

- Landing: https://www.unicef.org/somalia/reports/somalia-micronutrient-survey-2019
- PDF: https://www.unicef.org/somalia/media/1681/file/Somalia-Micronutient-Survey-2019.pdf
- Release: August 2020 report, English PDF about 3 MB; collection December 2018–July 2019. Five geographic strata plus an IDP stratum. Women of reproductive age and children under 5; biomarkers, anthropometry and salt/water iodine. This is population nutrition evidence, not food nutrient composition. Preserve exact sampled strata/exclusions during extraction.
- MoH/FMS/Somaliland/UNICEF and implementing partners credited. UNICEF general terms reserve rights; no commercial-reuse licence verified in file.

### SO-MOH-GUIDANCE: guidance hierarchy and unresolved current release

- Current launch evidence: https://www.unicef.org/somalia/press-releases/somalia-redefines-child-survival-launch-2026-maternal-infant-young-child-and
- Release 28 January 2026: Ministry of Health 2026 Maternal, Infant, Young Child and Adolescent Nutrition Guidelines and Counselling Package (MIYCAN), supported by UNICEF. Full package/download unverified. Acquisition priority: locate the actual approved Somalia package and language/version inventory; do not substitute similarly titled Uganda guidance or the global package.
- Archival training PDF: https://www.unicef.org/somalia/media/1971/file/Somalia-harmonised-community-health-workers-training-manual-Oct-2020-ENG_1.pdf (October 2020; 224 pages; infant feeding, food groups, food hygiene and cooking-demonstration guidance). It is a training manual, not a general recipe dataset or general-population dietary guideline.
- Archival strategy landing: https://www.unicef.org/somalia/reports/somalia-nutrition-strategy
- Strategy PDF: https://www.unicef.org/somalia/media/1756/file/Somalia-nutrition-strategy-2020-2025.pdf (October 2020; policy period 2020–2025, expired period). Do not mark current merely because downloadable.
- Rights: UNICEF/file-specific permission review before republication; clinical guidance should retain intended population and edition.

## P1 safety and provider-reference metadata

### SO-SOBS: official standards authority and public registers

- Official authority: https://www.sobs.gov.so/ ; independently corroborated by https://www.iso.org/member/8867946.html and https://www.fao.org/gm-platform/browse-information/country-details/somalia/en .
- Product register: https://imis.sobs.gov.so/public-directory/products . Observed 23 products; fields include product/brand/company/origin/certificate/mark, issue/expiry dates and status. Types QM, ISM, HM, PM and export CoC. Scope is certified records, not all packaged foods, restaurants or all imports; neither nutrients nor product availability is established.
- Provider register: https://imis.sobs.gov.so/public-directory/service-providers . Observed 42 certificate holders across multiple sectors. Capture approved scope and status; retain food-relevant suppliers only when the actual scope supports it. An SCC/Tier1 record is certification, not blanket accreditation or endorsement.
- Master register: https://imis.sobs.gov.so/public-directory . Includes expired/revoked status search. No machine-readable export API verified; use bounded public metadata only after applicable permissions/terms review.
- Standards: https://imis.sobs.gov.so/standards . Observed 2,033 standards and 250 Food Technology entries; all-sector count must not become food count. Catalogue is metadata only; full text obtained from SoBS. Preserve Somali SOS designation and original adopted standard number/year. Purchase flow says coming soon; do not scrape/pay for unavailable full text or assume third-party ISO/AOAC/EAS rights transfer.
- Notices: https://www.sobs.gov.so/gazette and https://www.sobs.gov.so/news . Gazette showed 4 notices and 0 publications at inspection. No verified dedicated public food-recall CSV/API/feed found. Do not claim no recalls exist or infer market-wide safety from certificate status. No general open-data licence verified.

### SO-MOLFR-SAFETY-2024: policy background, explicitly draft

- https://molfr.gov.so/wp-content/uploads/2024/07/FINAL-DRAFT-NATIONAL-FOOD-SAFETY-POLICY-Federal-Republic-of-Somalia-22-July-2024.pdf
- 37-page PDF; cover says June 2024 and **FINAL DRAFT**. National food-safety institutional roles and proposed framework, not evidence of enacted binding rules or current recalls. Obtain adoption/gazette evidence before presenting any proposal as in force. No open licence verified.

## P2 structured survey and composition backfill

### SO-SNBS-SIHBS2022

- Original catalogue: https://microdata.nbs.gov.so/index.php/catalog/59
- Related materials: https://microdata.nbs.gov.so/index.php/catalog/59/related-materials
- English report: https://microdata.nbs.gov.so/index.php/catalog/59/download/125
- English questionnaire: https://microdata.nbs.gov.so/index.php/catalog/59/download/122
- Somali report: https://microdata.nbs.gov.so/index.php/catalog/59/download/164
- DDI-SOM-SNBS-SIHBS-2022-v02, catalogue modified 23 September 2024; PDFs and metadata. Household consumption/expenditure and food-item questionnaire, urban/rural/nomadic, 17 regions. Middle Juba is absent from the coverage list. Catalogue lists 2023 collection dates despite 2022 title and February 2023 main report: record and resolve this metadata inconsistency rather than silently rewriting dates. Microdata access request/terms not exercised; reports/questionnaire first. No raw household data acquisition or upload authorized by this handoff.

### SHARED-FAO-NE1982: historical regional composition fallback

- Original HTML publication/TOC: https://www.fao.org/4/X6879E/X6879E00.htm
- Method/coverage: https://www.fao.org/4/X6879E/X6879E01.htm
- Data-source bibliography: https://www.fao.org/4/X6879E/X6879E26.htm
- FAO/USDA Food and Nutrition Paper 26, 1982, ISBN 92-5-101277-6. Table I 848 foods, proximate/mineral/vitamin values; amino acids 128 foods; fatty acids 106. Somalia is explicitly in the geographic literature-search scope, with historic Somali references, but rows combine many Near East sources. Do not infer every row was sampled in Somalia. Check each food's source, state, edible/as-purchased basis, units and analytical evidence.
- Format HTML tables; legacy text offers machine-readable tables on request, but no current public file URL verified. Cover explicitly all rights reserved; permission review needed, especially commercial use. Metadata/reference priority only until cleared. Download once in the shared layer if approved, then country pointers for verified applicable records.

## Rights, deduplication and evidence requirements

- FAO general rights: https://www.fao.org/publications/about-fao-publishing/permissions/ . Research access does not establish commercial redistribution rights; follow each asset's actual licence. Publication rules and statistical-database licences may differ.
- UNICEF: https://www.unicef.org/legal . General terms reserve copyrights and require written permission for reproduction/republication/translation; check asset-specific exceptions. Do not automatically treat UN material as public domain.
- SNBS portal terms and WFP dataset licences above are more specific; preserve the exact licence revision and applicability. Do not upload originals/raw datasets to GitHub under the source-code/documentation approval.
- Acquire a single immutable original per release/content hash, with publisher, exact URL, retrieval time, release/data period, HTTP outcome, MIME/bytes/hash, licence evidence, geography, type and extraction status. Shared FAO/WFP material is acquired once; maintain explicit Somalia relevance links, not blanket country claims.
- Separate original/derived/provider-supplied/modelled/reference-only rows. Keep household surveys, measured nutrient composition, food-practice observations, humanitarian baskets, retail prices, inflation indices, certificates and recall events in their proper data classes.
- Before promotion, validate units/currencies, local names/transliterations, geographic codes, release cutoffs, formula/cache values in XLSX, OCR/table alignment in PDFs and document duplicates. Preserve missing/unknown values; do not convert them to zero.
- Open gaps to return through Gateway: current national composition table; full 2026 MIYCAN approved files; general-population dietary guideline; definitive public recall source; per-asset commercial rights; any secured FSNAU exports/API access. Do not create credentials or contact providers without the relevant authorization.
