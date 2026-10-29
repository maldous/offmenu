# OffMenu: North Macedonia (MK) original-source acquisition package

Research checked: 2026-10-18 UTC. Scope: source discovery and acquisition preparation only. No Foo access, repository writes, large downloads, normalization, UI work, account creation, or provider outreach. Public pages, small metadata responses, HTTP headers, one CPI cell and one household-quantity cell were inspected. This file is a handoff manifest, not a claim that the source corpus has already been acquired.

## Result and immediate priorities

1. Acquire the Public Health Institute's 2014 national dietary-guidance PDF and 2019 adult guidance leaflet. Both exact files respond HTTP 200; the first is 1.56 MB and the second 1.87 MB.
2. Acquire original MAKSTAT metadata and bounded JSON-stat2 exports: household quantities and expenditures through 2025, plus monthly food CPI through September 2026. The public API and a one-cell JSON-stat2 export were verified.
3. Preserve the FVA public recall/news pages and original RSS XML, and obtain the publicly linked non-animal-food operator XLSX through its official Google Drive viewer. Do not substitute old static registries for current approval status.
4. Collect a small, provenance-complete manufacturer-label sample from Vitalia and retailer price-reference pages from Tinex/KAM. Their own pages are primary commercial evidence; open redistribution rights have not been established.
5. Acquire the SSM June 2026 original basket DOCX and September 2026 release HTML. SSM is the basket publisher, a trade union, not the national statistical office.
6. Retry official tourism recipe/cultural PDFs only after their current 502/redirect problems clear. Indexed records identify exact files, but successful current retrieval was not established.

Critical gap: no openly downloadable national MK food-composition database was verified. There is a 2025 university/Public Health Institute project lead, a regional Balkan FCDB candidate, and original Macedonian manufacturer labels. Keep those distinct. Do not fill MK coverage with Serbian or generic Balkan values and call it national source data.

## Existing OffMenu evidence reused

- Read-only repository source: https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/research/OffMenu_Global_Data_Source_Register.json
- Its MK entry has `composition: null`, `regional_candidate: null`, and a local Wolt North Macedonia lead, source ID S118. It explicitly leaves feed/API rights, market coverage, and menu nutrition/allergens unverified.
- This package extends that source discovery; it does not modify the register or duplicate country-worker coordination.

## A. Nutrition and food composition

### MK-01 — National dietary guidance, Ministry of Health / Institute of Public Health

- Original download: https://www.iph.mk/Upload/Documents/Nasoki_ishrana.pdf
- Ministry HTML edition: https://zdravstvo.gov.mk/vodich-za-ishrana/
- FAO corroborating national record: https://www.fao.org/nutrition/education/food-dietary-guidelines/regions/countries/the%20former%20yugoslav%20republic%20of%20macedonia/en/
- Format/release: Macedonian PDF, 32 pages; cover says Skopje 2014. FAO records the extended electronic draft in May 2014 and an earlier pamphlet in 2008. Preserve the original title and historical country name.
- Scope: national food-based dietary advice for healthy people over age 2; food groups, diet patterns and nutrient/energy recommendations. It is not a food-by-food nutrient database.
- Access: PDF parsed successfully in web retrieval. HEAD returned 200, application/pdf, 1,564,693 bytes. Last-Modified is 2023-09-01, a server file date, not the publication year.
- Rights: publicly downloadable; no explicit open-data/republication licence verified. Retain author/institution attribution and rights notice; do not infer that a government host means public domain.
- Priority: P1. Save original bytes and landing-page provenance.

### MK-02 — Healthy nutrition recommendations, 2019 adult leaflet

- Official landing: https://iph.mk/mk/home/infopublikacii/1113
- Exact original: https://www.iph.mk/Upload/Documents/Flaer-preporaki-za-zdrava-ishrana-na-vozrasno-naselenie-makedonski.pdf
- Format/release: Macedonian PDF; official landing labels the material 2019. Filename identifies the adult population.
- Scope: adult healthy-eating education. Do not replace MK-01's full guidance with the leaflet or silently apply adult recommendations to children.
- Access: direct link extracted from the official landing HTML. HEAD returned 200/application/pdf, 1,866,694 bytes; server Last-Modified 2023-06-08. Web PDF text rendering failed; full content/page count was not verified.
- Rights: no explicit reuse licence established. P1 original-file acquisition, followed by content verification.

### MK-03 — National traditional-food composition database project lead

- Primary academic programme: https://isaf2025.isaf.edu.mk/wp-content/uploads/2025/10/Programa-02.pdf
- Format/release: 72-page ISAF 2025 programme PDF, October 2025. Printed page 41 / PDF page index 40 names the project “Establishing a national food composition database for traditional foods in North Macedonia.”
- Institutions: Faculty of Agricultural Sciences and Food, Ss. Cyril and Methodius University, Institute of Public Health of North Macedonia, and Slovak National Agricultural and Food Centre.
- Scope: evidence of MK-specific database development, not evidence of an available table, nutrient coverage, number of foods, or licence.
- Access: programme readable. No dataset download/release was located. The programme lists Dushica Santa, dsanta@fznh.ukim.edu.mk, as the research contact; no contact was made.
- Priority: P2 evidence copy / future access lead. Do not assert that the database is absent today solely from an older paper; its public release remains unverified.

### MK-04 — CAPNUTRA Balkan composition and portion-size reference

- Publisher description: https://www.capnutra.org/food-and-nutritional-tools/
- Publisher-linked portion atlas: https://www.capnutra.org/wp-content/uploads/2026/01/Food_atlas_CAPNUTRA.pdf
- Format/release: atlas PDF, 82 pages, Serbian. URL upload folder is January 2026; edition date must be taken from the document, not inferred from that folder.
- Scope: regional Balkan foods/dishes and portion-size estimation; publisher describes 146 atlas foods/dishes/utensils, and a DAP-integrated regional FCDB exceeding 2,000 foods, recipes and supplements. North Macedonia is among survey applications and supported language contexts. This does not establish an MK-only national analytical table.
- Access/rights: publisher explicitly offers free access to the atlas, but the site says all rights reserved. Free download is not an open commercial-reuse grant. No original FCDB export URL or export licence was verified. Treat the atlas as optional reference, not a substitute for country composition data.
- Priority: P2; avoid large downloads until size checked.

### MK-05 — Manufacturer-declared branded nutrition, Vitalia

- Verified example: https://www.vitalia.com.mk/product/ovesni-krekeri-so-mesan-zelencuk/
- Price-list landing: https://www.vitalia.com.mk/cenovnici/
- Format/release: live Macedonian HTML product page, observed 2026-10-18, undated formulation. The example includes product identity, 90 g pack weight, local SKU 3887036, declared nutrient table per 100 g, and a denar price.
- Scope: that manufacturer's specific branded product, not national generic composition. The local SKU is not a verified GTIN. Formulation, market, pack size, and label image need matching.
- Data-quality caveat: the page has a clear per-100 g nutrient table and separate “per serving” promotional tiles repeating some values. Preserve both exactly in original capture; do not resolve the conflict during source collection.
- Rights/access: publicly readable; footer says all rights reserved. No bulk API/export grant verified. Price-list landing renders no usable table in text retrieval. P1 small original-page sample, P2 broader catalogue only after applicable reuse terms are established.

### MK-06 — National dietary survey of children, FVA / IPH

- Publisher record: https://efsa.onlinelibrary.wiley.com/doi/abs/10.2903/sp.efsa.2022.EN-7169
- DOI: https://doi.org/10.2903/sp.efsa.2022.EN-7169
- EFSA landing: https://www.efsa.europa.eu/en/supporting/pub/en-7169
- Format/release: external scientific report, first published 2022-02-11, EFSA Supporting Publications 19(2), 7169E.
- Scope: MK toddlers'/children's consumption survey methods and eating-pattern evidence, not a nutrient composition table and not public participant microdata. Authors are FVA and IPH personnel.
- Access/rights: publisher search record is open-access metadata; full report was not retrieved here. EFSA landing returned 429; do not repeatedly retry or bypass it. Verify article-specific licence before reuse. P2 source/methodology lead.

## B. Official household consumption and food prices

### MAKSTAT access contract

Publisher: State Statistical Office. Public API root verified with HTTP 200 JSON:
https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/

For the table endpoints below, GET retrieves original variable metadata. A POST to the same endpoint with a PxWeb query retrieves data. `json-stat2` was verified with a one-cell request for MK-09. Save both the exact request and original response bytes, including update metadata, without translating keys or altering missing-value conventions. English metadata still uses original Macedonian variable codes. CSV/Excel/PC-Axis exports may be available through PxWeb, but this worker did not verify each format.

SSO's 2017 publication landing explicitly says its data are free of charge with source citation. Current CPI UI says Copyright: Yes. No specific CC/ODC grant was verified. Preserve terms/attribution evidence with the originals rather than treating free access as unrestricted republication.

### MK-07 — Household quantities for personal consumption

- Metadata/data endpoint: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/ZivotenStandard/AnketaZaPotrosuvackaDomakinstva/225_ZivStand_mk_KOLICINI_ml.px
- Official catalogue: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/ZivotenStandard/AnketaZaPotrosuvackaDomakinstva/
- Format/release: PxWeb metadata JSON / original query export. Catalogue update 2026-05-28T12:00:00.
- Verified coverage: 2002–2025, 213 product categories, four household types, two measures (per household/per household member). Categories include foods and nonfoods; do not call all 213 foods.
- Scope: national household-budget survey aggregate quantities, including named local food categories, not individual intake, retail transactions, or nutrient composition. Original units and methodology must accompany data.
- Variable codes: `производи`, `година`, `тип на домаќинство`, `мерки`. P1 download metadata then bounded year slices, beginning 2025 and preserving all categories in originals.

Verified one-cell JSON-stat2 POST returned HTTP 200 / dataset dimensions [1,1,1,1]:

```json
{"query":[{"code":"производи","selection":{"filter":"item","values":["Ориз"]}},{"code":"година","selection":{"filter":"item","values":["2025"]}},{"code":"тип на домаќинство","selection":{"filter":"item","values":["вкупно"]}},{"code":"мерки","selection":{"filter":"item","values":["просек по член на домаќинство"]}}],"response":{"format":"json-stat2"}}
```

### MK-08 — Household expenditures by COICOP

- Metadata/data endpoint: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/ZivotenStandard/AnketaZaPotrosuvackaDomakinstva/150_ZivStand_mk_UPOTREBENI_ml.px
- Format/release: PxWeb; update 2026-05-28T12:00:00; verified years 2002–2025.
- Scope: 15 expenditure categories, four household types, and measures for household/person averages in denars and percentage shares. Food/non-alcoholic beverages and restaurants/hotels are separate categories. This is household expenditure, not a shopping-basket price quote.
- Variable codes: `употребени средства по COICOP класификација`, `година`, `тип на домаќинство`, `мерки`. P1 original metadata and bounded data export.

### MK-09 — Detailed monthly food CPI, ECOICOP v2

- Human-readable table: https://makstat.stat.gov.mk/PXWeb/pxweb/en/MakStat/MakStat__Ceni__IndeksTrosZivot__TrosociZivot/131_CeniTr_Mk_DetalnoTroZi_ecoicop_ml.px/
- Metadata/data endpoint: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/Ceni/IndeksTrosZivot/TrosociZivot/131_CeniTr_Mk_DetalnoTroZi_ecoicop_ml.px
- Format/release: PxWeb; update 2026-10-07T12:00:00. Verified coverage 2015M01–2026M09, 182 categories overall, seven index comparisons.
- Scope: national price indices, not absolute denar prices or merchant prices. `Продукти` values 0002–0020 cover food/non-alcoholic beverages and subgroups. The older COICOP archive is separate; preserve the classification break.
- Verified retrieval: a POST selecting September 2026, food/non-alcoholic beverages, year-on-year index returned HTTP 200, JSON-stat2 dataset, dimensions [1,1,1]. Full series not downloaded.
- P1. Re-read metadata before data requests; values and release can change.

Example exact bounded query, for method verification rather than a full acquisition:

```json
{"query":[{"code":"Година","selection":{"filter":"item","values":["2026M09"]}},{"code":"Продукти","selection":{"filter":"item","values":["0002"]}},{"code":"Индекс","selection":{"filter":"item","values":["03"]}}],"response":{"format":"json-stat2"}}
```

### MK-10 — CPI weights / historical archive

- Current weights metadata/data endpoint, table verified in official catalogue: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/Ceni/IndeksTrosZivot/TrosociZivot/132_CeniTr_Mk_Ponderi_ml.px
- Current catalogue: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/Ceni/IndeksTrosZivot/TrosociZivot/
- Historical classification catalogue: https://makstat.stat.gov.mk/PXWeb/api/v1/en/MakStat/Ceni/IndeksTrosZivot/DetPod/
- Format/release: weights table update 2026-03-13T12:00:00; older COICOP monthly tables in archive updated January 2026.
- Scope: index weighting/context; not a list of purchasable basket items with absolute prices. P2 original metadata and weight table. Table-level metadata for weights not independently fetched in this pass.

### MK-11 — Historical household consumption methods and tables, 2017

- Official landing: https://www.stat.gov.mk/PrikaziPublikacija_1_en.aspx?rbr=715
- PDF: https://www.stat.gov.mk/Publikacii/4.4.18.01.pdf
- Original Excel link: https://www.stat.gov.mk/xls_publikacii/2018/4.4.18.01.xls
- Format/release: publication 4.4.18.01, issued 2018-05-17, 116 pages, Macedonian/English; landing advertises 831 KB PDF and Excel tables.
- Scope: survey definitions, detailed 2017 quantities/expenditure. Landing explicitly identifies this as the last standalone edition and directs current users to MAKSTAT.
- Access: PDF indexed/readable; Excel exact URL obtained from official link, but web renderer could not handle the response. Actual Excel bytes/format remain to verify.
- Rights: free-of-charge data with source citation stated on landing. P2 historical/methodology acquisition, not a current release.

### MK-12 — SSM minimum basket, original monthly releases

- June landing: https://www.ssm.org.mk/mk/vrednosta-na-smk-za-mesec-juni-2026-godina
- Original June DOCX: https://www.ssm.org.mk/sites/default/files/files/dokumenti/2026/06/sindikalna_minimalna_koshnica_za_mesec_juni_2026_godina.docx
- September release: https://www.ssm.org.mk/mk/sindikalnata-minimalna-koshnica-zgolemena-za-757-denari-i-dostigna-69432-denari
- Format/release: June 2026 DOCX, 17,070 bytes, HEAD 200; server modified 2026-06-26. September 2026 HTML includes food/drink component and four-person household basis.
- Scope: publisher's model minimum household budget, not official CPI, poverty threshold or a personalized recommended diet. Separate baseline and rented-housing variant. Historical methodology should not be assumed unchanged.
- Rights: public original releases; reuse licence not verified. P1 small DOCX and HTML snapshots, with month and methodology source.

## C. Recipes and food practices

### MK-13 — Tourism agency Macedonian cuisine booklet / food-cultural map

- Official booklet landing: https://tourismmacedonia.gov.mk/makedonska-kujna/
- Exact indexed booklet PDF: https://tourismmacedonia.gov.mk/wp-content/uploads/2018/09/Taste.pdf
- Exact indexed 2023 map: https://tourismmacedonia.gov.mk/wp-content/uploads/2023/07/gastronomska-karta-2023.pdf
- Previously indexed alternate map URL: https://macedonia-timeless.com/img/gastronomska-karta-2023.pdf
- Publisher: Agency for Promotion and Support of Tourism. Landing describes recipes across all eight regions, ingredients/preparation and cultural background. The 2023 map describes regional dishes and food practices; it is not a quantitative nutrient dataset.
- Access status: official landing/PDF requests currently return 502. The alternate map URL now redirects to a short index HTML page rather than a PDF. Search-index text is evidence of the publication, not successful current acquisition. Do not save the HTML redirect body with a .pdf extension or mark the source acquired.
- Release: map title/filename identifies 2023. Taste.pdf upload path identifies September 2018, not a verified edition date.
- Rights: no reuse licence verified; recipes' explanatory prose, photographs and layout need separate rights consideration. P2 retry when available; no unofficial mirror substitution.

### MK-14 — University MKRecipes research, original research lead only

- Paper record: https://arxiv.org/abs/2510.14128
- Versioned HTML: https://arxiv.org/html/2510.14128v2
- Author repository: https://gitlab.finki.ukim.mk/ds4food/MKRecipes
- Licence record: https://gitlab.finki.ukim.mk/ds4food/MKRecipes/-/blob/main/LICENSE
- Format/release: paper v2, 2025-11-17; repository created 2025-08-26. Paper describes 36,237 recipes collected from Gotvi.mk, MoiRecepti.mk and Recepti.mk, stored as JSON Lines and subsequently parsed.
- Scope: Macedonian-language recipe research corpus; not a government recipe register, measured nutrient source, or proof of nationwide cultural completeness.
- Access/rights: paper and repo identify CC BY-NC-SA 4.0, which includes noncommercial and share-alike restrictions. Repository data files and exact downloadable dataset release were not verified. The licence does not independently establish rights over third-party recipe prose/images.
- Disposition: P2 provenance/access research only. Do not import this already-normalized corpus as original national source data or use it commercially without resolving restrictions. No code was run and no recipe corpus was downloaded.

## D. Recalls, food safety and provider reference data

### MK-15 — Food and Veterinary Agency current public notices / RSS

- Official news index: https://fva.gov.mk/mk/soopstenija-izjavi-vesti
- Original RSS: https://fva.gov.mk/mk/rss.xml
- Verified recall example: https://fva.gov.mk/mk/260210-preventivno-povlecheni-odredeni-serii-aptamil-formuli-doenchina
- Format/release: live HTML and RSS XML; example dated 2026-02-10, containing named product variants, lots, expiry dates, hazard/reason and consumer action.
- Access: HTML readable; RSS verified by direct GET 200 with application/rss+xml. Web text renderer rejects RSS content type; that is a renderer limitation, not source unavailability. The XML response begins with Drupal debug comments before the declaration; preserve raw bytes and handle parsing later, without changing source copies.
- Scope: national agency public communications, not a guaranteed complete structured recall database. RSS includes non-recall news, and European RASFF references do not prove every affected country/outlet. Preserve article title/date/URL and linked image/table assets.
- Rights: no open reuse licence verified. P1 original RSS and selected notice HTML. No monitoring/subscription was set up.

### MK-16 — FVA non-animal-food operator registry

- Official index: https://fva.gov.mk/index.php/mk/registri-hrana-nezivotinsko-poteklo
- Exact public file viewer: https://drive.google.com/file/d/1brInTyyFAyWxX8IgDaqUvD8ybQx1-4bx/view?usp=sharing
- Format/release: viewer title identifies `објекти и оператори со храна.xlsx`. Release date and actual workbook contents were not verified.
- Scope: registered facilities/operators dealing with food of non-animal origin. The index separately links supplements, special nutritional-use foods and fortified-food registers; do not conflate those products or registries.
- Access: official page explicitly describes downloading shared files. Use the viewer's supported Download action; no invented Google Drive export URL, no editing, no authentication bypass. The viewer landing was public, but workbook bytes not fetched.
- Rights: official public registry; no explicit redistribution licence verified. P1 acquisition and internal release-date/schema inspection. Any business/person contact details should be preserved only where relevant to provider identification.

### MK-17 — FVA animal-origin provider registers, historical snapshots

- Index: https://fva.gov.mk/mk/registar-odobreni-objekti-5
- Dairy original: https://www.fva.gov.mk/images/Sekcija_IX_Surovo_mleko_i_proizvodi_od_mleko_1812.17_09_17.12.2018.pdf
- Retail original: https://www.fva.gov.mk/images/1812.24_015_register_na_maloprodazni_objekti_od_zivotinsko_potekloza_objavuvane.pdf
- Format/release: dairy PDF 20 pages, dated 2018-12-17 in the document. Retail PDF 39 pages; filename suggests a historical snapshot, but its exact effective date was not established.
- Scope: establishment approval numbers, names, locations and product/activity classes. The index covers multiple animal-food sections and separately points to revoked decisions/importers/retailers.
- Access: both PDFs readable by web retrieval. Retail text extraction is badly incomplete (mostly row numbers), so visual/OCR verification is required after download; no usable table should be claimed yet.
- Rights: no explicit reuse licence verified. P2 historical reference only; never use these as evidence of current approval or current operation without a newer register/status check.

### MK-18 — FVA traceability/withdrawal guidance

- Original: https://fva.gov.mk/images/Vodic_Sledlivost_SPO_Hrana.pdf
- Format/release: official PDF, 64 pages indicated in indexed text. Exact publication date not independently verified; search-index age is not a release date.
- Scope: original guidance on food-business traceability, withdrawal and recall procedures. Not a recall event feed or current consolidated law.
- Access/rights: public indexed PDF, no open reuse licence established. P2 background documentation; preserve date/edition before any legal interpretation.

## E. Retailer and delivery-platform reference data

### MK-19 — Tinex public price disclosure

- Retailer provenance page: https://www.tinex.com.mk/%D1%82%D0%B8%D0%BD%D0%B5%D0%BA%D1%81-%D0%BB%D0%B8%D1%81%D1%82%D0%B0-%D0%BD%D0%B0-%D0%B0%D1%80%D1%82%D0%B8%D0%BA%D0%BB%D0%B8
- Official linked portal: https://ceni.tinex.mk/
- Indexed example branch/page: https://ceni.tinex.mk/?org=512&page=164&perPage=20&search=
- Format/release: branch-selectable live HTML price lists. Indexed sample has item name, selling/unit/regular/promotional price, availability, and a last-update timestamp.
- Scope: retailer/outlet-specific offers in denars, not official national average prices or nutrition. Capture branch identifier, date, unit, pack and offer conditions with each original snapshot.
- Access: retailer ownership/link verified. Portal root timed out in this pass; indexed example is not current price verification. No bulk API/export or reuse licence verified. P2 source capture when reachable; do not infer feed rights from mandatory/public price disclosure.

### MK-20 — KAM price disclosure and own recipe catalogue

- Price landing: https://www.kam.com.mk/ceni-vo-marketi.nspx
- Main site: https://www.kam.com.mk/
- Format/release: live retailer HTML. Price landing and navigation are reachable; rendered text shows no actual price rows. It also links an own-recipe catalogue and store directory.
- Scope: retailer's selected outlets/products and publisher-owned recipe pages, not nationwide composition or culturally representative recipes.
- Access/rights: actual prices/download endpoint not verified; likely needs the supported interactive page. Footer states all rights reserved. P2 targeted reference, not bulk ingestion-ready.

### MK-21 — Wolt North Macedonia, existing OffMenu lead

- Country page: https://wolt.com/en/mkd
- Country terms: https://explore.wolt.com/en/mkd/terms
- Format/release: live platform HTML, observed 2026-10-18; no fixed release.
- Scope: participating merchant/menu/store reference only. Country page lists Bitola, Ohrid, Skopje and Tetovo, while a separate courier FAQ still mentions Skopje only. Verify live city/outlet pages instead of treating either as a complete coverage statement.
- Access/rights: public page is readable; no licensed feed/API export or wholesale reuse right established. Prices/availability may depend on address and time. Do not infer ingredient, allergen or nutrient facts from dish names or photos.
- Priority: P2 provenance/coverage check, not original nutrition acquisition.

## Acquisition and custody checklist for the receiving worker

- Keep country scope MK / North Macedonia; preserve historical publisher names and original Macedonian titles. Do not accidentally collect Greek Macedonia sources as national MK data.
- Save original bytes unchanged, with source ID, exact requested URL, final response URL, retrieval UTC, HTTP status, MIME type, original filename, byte count and SHA-256. Retain relevant response headers and official landing page.
- Keep publication/reference date separate from upload path, server Last-Modified, search crawl date and retrieval date.
- For PxWeb save GET metadata, exact POST request, original response, table identifier, release/update time, classification and units. Make manageable source exports rather than a normalized table. Honour rate limits.
- Verify file signatures: PDF `%PDF`, XLSX/DOCX ZIP containers, actual spreadsheet rather than sign-in HTML. Never call a redirect/error page a successful PDF/workbook.
- Record licence evidence verbatim only as needed, and distinguish open licence, attribution-only notice, public-download/no licence, and access-blocked. Private repository status does not make copyright restrictions disappear.
- Source-copy approval is not permission to redistribute all publisher content publicly, buy licences, create accounts or contact institutions. No such actions were taken here.
- Known unresolved items: national composition release; tourism host availability; FVA workbook bytes/effective date; registry currency; retailer export rights; article-specific EFSA licence; MKRecipes third-party rights and noncommercial restriction.
- Stop after preserving and validating original sources and provenance. No normalization, recipe recalculation, nutrition estimation, UI work, bulk third-party scraping, repository push, or replacement-worker coordination is part of this package.
