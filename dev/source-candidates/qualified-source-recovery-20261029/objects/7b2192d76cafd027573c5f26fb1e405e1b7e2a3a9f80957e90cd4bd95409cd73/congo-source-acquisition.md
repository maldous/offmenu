# OffMenu source acquisition: Republic of the Congo (CG / COG)

Prepared 2026-10-18 UTC. Scope: original publisher files/pages and their provenance only. No bulk datasets were downloaded, no Foo access was used, and no normalization or UI work was performed.

## Recommended first batch

1. **Ministry of Health SMART final report**: save [gg.pdf](https://sante.gouv.cg/wp-content/uploads/2023/10/gg.pdf), retaining that original basename and a separate descriptive manifest title. It is a verified 210-page PDF, titled *Enquête nutritionnelle nationale utilisant la méthodologie SMART*, final report November 2022, posted 5 October 2023. [Publisher landing page](https://sante.gouv.cg/enquete-nutritionnelle-nationale-utilisant-la-methodologie-smart/).
2. **UNICEF country nutrition profile**: save [Nutrition_COG.pdf](https://data.unicef.org/wp-content/uploads/cp/nutrition/Nutrition_COG.pdf). Verified two-page PDF; [release landing page](https://data.unicef.org/resources/nutrition-country-profiles/) dated 18 March 2026 explicitly separates Congo from Democratic Republic of the Congo.
3. **UNICEF/INS MICS 2014–2015**: save [original French report PDF](https://www.unicef.org/congo/sites/unicef.org.congo/files/2019-06/Congo%202014-15%20MICS_French_0.pdf). This is the CG report, not the DRC DHS report. Preserve its actual survey period rather than treating the 2019 upload path as observation year.
4. **IRD/CIRAD food-practice study**: save [36928.pdf](https://horizon.documentation.ird.fr/exl-doc/pleins_textes/pleins_textes_6/b_fdi_33-34/36928.pdf), verified 22-page 1992 study of chikwangue production in Brazzaville. Save [catalogue metadata](https://www.documentation.ird.fr/hor/fdi:36928) alongside it.
5. **FAO CG food-practice chapter**: save the original [Republic of the Congo chapter HTML](https://www.fao.org/4/j3463f/j3463f07.htm) and [2004 publication contents](https://www.fao.org/4/j3463f/j3463f00.htm). The chapter is explicitly the Brazzaville/Congo case study; the neighbouring DRC chapter is separate.
6. **INS-Congo current price publication**: open [publications](https://ins-congo.cg/publications.html) or [economic statistics](https://ins-congo.cg/stat-eco.html), select *Bulletin INHPC de Août 2026*, and preserve the publisher's PDF and Excel if both resolve. The official indexed page advertises both; exact attachment URLs and successful file delivery still need verification in a normal browser. Do not substitute the test subdomain or fabricate a PDF URL.

Items 1–5 have exact primary document/page URLs. Item 6 is an actionable official-page acquisition, not a verified direct-file download. After these, resolve WFP observed-price export and the regional composition workbook below. Keep failure receipts if files cannot be retrieved.

## Source register and caveats

### A. Food composition and nutrition

**A1. CIFOR-ICRAF, 2023, Congo Basin food composition resource — regional candidate.**

- Official [project/download hub](https://www.cifor.org/gml/food-security-and-forests/); [French publication record](https://www.cifor-icraf.org/knowledge/publication/8936/); exact [English guide PDF](https://www.cifor-icraf.org/publications/pdf_files/Books/FCT-Guide-EN.pdf) and [French guide PDF](https://www.cifor-icraf.org/publications/pdf_files/Books/FCT-Guide-FR.pdf).
- [FAO directory](https://www.fao.org/food-composition/tables-and-databases/detail/table-de-composition-des-aliments-pour-les-pays-du-bassin-du-congo/en) confirms 2023, free access, PDF plus electronic file, English/French. Hub labels a database separately from guides. Exact electronic-file format and download URL were not resolved; do not label it XLSX yet.
- The guides describe a six-country basin that includes CG, but compilation was motivated by Cameroon/DRC dietary surveys in 2018–2019. FAO's directory country tags list Cameroon, CAR, DRC and Gabon, omitting CG. Preserve this discrepancy and treat as a regional reference; CG-specific ingredient/recipe coverage is **unverified**, not national coverage.
- Direct publisher fetches returned 403/timeouts in this research tool; indexed publisher text remains available. [Landscape Alliance's publisher-attributed record](https://www.landscapealliance.org/fr/ressources/publication/8936/) reports CC BY 4.0 for the publication. Preserve the guide/workbook's own licence when acquired; do not transfer the guide licence automatically to every workbook component.

**A2. Ministry of Health national SMART report — priority CG original.**

- URLs/release above. Country, national/departments, child and maternal nutrition, infant feeding, household dietary diversity, food-consumption scores, expenditure and food security. Report's internal tables refer to Congo 2021; inspect methodology and preserve observation dates separately from November 2022 report and October 2023 posting.
- Public PDF; no explicit open-reuse licence verified. A report is available; raw household microdata availability is unverified and is not needed for this acquisition batch.

**A3. UNICEF CG nutrition profile and MICS — priority originals.**

- URLs/releases above; [UNICEF Congo nutrition page](https://www.unicef.org/congo/survie-et-d%C3%A9veloppement-de-lenfant/nutrition) links MICS and provides the institutional context. Profiles are aggregate country indicators, not food nutrient records or meal plans.
- Profile landing page has differing notices: dataset download wording says CC BY 3.0 IGO, site default says CC BY-NC 3.0 IGO. Capture the artifact-specific rights statement; flag unresolved commercial reuse. Do not assume that profile terms grant rights to the older MICS report or photographs.

### B. Recipes and food practices

**B1. IRD/CIRAD, Trèche & Muchnik, 1992, chikwangue in Brazzaville — priority historical practice source.**

- Exact catalogue/PDF in first batch; document describes preparation variants, processing and production systems. Geographic catalogue tags explicitly say CONGO; BRAZZAVILLE.
- The direct PDF opened successfully. The catalogue also contains a generic restricted-access form; no sign-in or request was needed for this linked PDF. Open access is not proof of a permissive redistribution licence; licence unverified. Preserve as historical preparation evidence, not a validated modern cooking-safety instruction or current price series.

**B2. FAO, 2004, forest insects and food security — priority historical practice source.**

- Exact HTML URLs in first batch. CG-specific case study by Jean-Baptiste Moussa covers edible caterpillars, food use and commercial channels around Brazzaville. Whole volume also has other countries; retain original chapter boundaries. HTML is verified, a standalone PDF of this chapter was not verified. Explicit reuse licence unverified; retain publication/FAO rights notices.

**Recipe gap:** a modern, national, openly downloadable CG recipe corpus with quantities and yields was not verified. Do not import generic “Congolese” recipe collections that mix CG and DRC without source-level geography evidence.

### C. Dietary guidance

**C1. Country guidance availability — unresolved, not absent.**

- [FAO Africa dietary-guideline directory](https://www.fao.org/nutrition/education/dietary-guidelines/regions/africa/en/) does not list Congo in its displayed country filter. This is a directory finding, not proof the country has no guidance.
- UNICEF CG nutrition page and MICS/SMART contain nutrition/feeding recommendations and measured practices, but neither should be relabelled a national general-population food-based dietary guideline. Save their original titles/types.
- Next targeted discovery: Ministry of Health and INS publication catalogues for ANJE materials and national nutrition policy. A general-population guideline, publication date and reuse terms remain **unverified**.

### D. Prices and shopping baskets

**D1. INS-Congo INHPC — priority official national index/basket documentation.**

- [Price landing page](https://www.ins-congo.cg/stat-prix.html), [publications](https://ins-congo.cg/publications.html), [economic statistics](https://ins-congo.cg/stat-eco.html). Indexed official listings show monthly 2026 releases through August; catalogue advertises PDF/Excel. Page shell in this tool did not expose attachment links.
- [Historical official INS page](https://v2.ins-congo.cg/statistiques-des-prix/) describes a 635-variety basket and monthly collections in five sampled economic zones. That historical methodology must be dated; do not assume the current basket is unchanged. INHPC is an index and basket methodology, not automatically a complete current SKU-price feed. Site says all rights reserved; open-data licence not verified.

**D2. WFP observed market prices — priority country export to resolve.**

- Verified [WFP Congo price dashboard](https://dataviz.vam.wfp.org/southern-africa/congo/economic/prices) explicitly lists Brazzaville, Pointe-Noire, Nkayi, Owando, Sibiti, Likouala and Pool market locations, with retail commodity selection. CG coverage is therefore confirmed, but current row counts, date range and export schema are not.
- Candidate HDX landing: https://data.humdata.org/dataset/wfp-food-prices-for-congo . This slug has secondary corroboration but returned 403; CKAN metadata was inaccessible. Treat exact dataset metadata/resource URL/licence as **not yet verified**. Use WFP/HDX official navigation to resolve and save the original country CSV plus metadata/licence. Do not use a processed Hugging Face mirror as the original.
- Confirm ISO COG, currency and locations in actual file. Do not silently replace it with the much larger DRC series or assume a dashboard's latest period.

**D3. World Bank Real-Time Food Prices — optional, separately labelled estimates.**

- [CG catalogue](https://microdata.worldbank.org/catalog/4491/study-description), [download/terms page](https://microdata.worldbank.org/catalog/4491/get-microdata), [JSON metadata](https://microdata.worldbank.org/metadata/export/4491/json). Reference COG_2021_RTFP_v02_M; 13 markets. Catalogue says prices combine observed data and machine-learning imputation; this is not raw WFP observation data.
- Download page reports version **2026-10-05**, through **2026-10-01**, modified 8 October; study-description response still reported **2026-08-24**, through August. Preserve both responses and reconcile the actual acquired file's release rather than silently selecting one.
- Metadata JSON/PDF/DDI are offered; actual data-file URL/format not verified behind download controls. Terms allow reuse with attribution and caveats, including third-party ownership. Capture terms; do not accept a new explicit agreement automatically if a required confirmation applies. Optional after WFP originals, not a substitute.

**Basket gap:** no current CG minimum nutritious/food expenditure basket with verified quantities and direct download was confirmed. INS basket documentation and SMART expenditure tables are useful originals; DRC CDF-denominated minimum baskets are not CG evidence.

### E. Recalls and food safety

**E1. Ministry of Health safety-policy original.**

- [PNDS 2023–2026 official PDF](https://sante.gouv.cg/wp-content/uploads/2024/09/PLAN-NATIONAL-DE-DEVELOPPEMENT-SANITAIRE-DU-CONGO-2023-2026_VERSION-OFFICIELLE.pdf). Searchable official PDF describes food-contamination surveillance planning. It is policy context, not an incident/recall database. Explicit reuse licence unverified.
- [Ministry of Commerce official communications](https://www.commerce.gouv.cg/fr/communiques-officiels/) is a verified institutional discovery source. [Current FAO/WHO Codex CG contact record](https://www.fao.org/fao-who-codexalimentarius/about-codex/members/detail/en/c/15561/) verifies the national authority route. Save public pages only; do not send inquiries without authority.
- A public CG machine-readable recalls feed, historic recall list and completeness claim are **unverified**. No inference of “zero recalls.” RappelConso, EU alerts or other global/import-market sources must not be labelled CG coverage unless each notice establishes CG distribution. Old 2002/2005 statements about missing CG regulation must not be treated as current law.

### F. Retailers and providers

**F1. REGAL / Park N Shop — verified first-party retailer lead.**

- [Official retailer page](https://www.regal-congo.com/regal-parknshop.html) identifies local/imported food retail and CG locations. Download form: original HTML; no structured stock/price export or current catalogue verified. Site footer is ©2018 and advertised store counts must be treated as undated. Save corporate/location evidence; do not assume it is fresh inventory. Rights reserved.

**F2. Mercure International — verified operator lead.**

- [Official Congo food-business contact](https://www.mercureinternationalgroup.com/contact/) lists SCORE Pointe-Noire and CG address; [food activities](https://www.mercureinternationalgroup.com/en/activites/alimentaire) confirms Congo operations but contains visibly old brand/history text. HTML/provider evidence only. Current Casino/Super U branding and live prices need fresh verification. No open export/licence verified.

**F3. BRASCO — government-verified producer lead.**

- [Ministry of Industry BRASCO record](https://industrie.gouv.cg/industries/brasseries-du-congo-brasco) identifies a Brazzaville beverage producer; save original HTML. Do not confuse with **BRACONGO / bracongo.cd**, which is DRC. Product-label nutrient files and CG-specific catalogue availability remain unverified.

Retailer/producers' public pages do not authorize bulk crawling, image redistribution or customer-account access. No contacting, ordering, sign-in, age verification or app installation is necessary for this package.

## Acquisition controls for the replacement worker

- Route execution through the existing parent/Gateway arrangement. Do not reopen closed Worker30 or create a coordinator.
- Preserve publisher bytes unchanged, original filenames, final resolved URLs, UTC fetch timestamp, HTTP status/content type, byte size, SHA-256, source/release/observation dates, licence URL/text and geographic evidence in a sidecar manifest. A landing-page snapshot is not proof that the file was acquired.
- Separate acquisition states: acquired-and-hashed; verified-link-pending; access-blocked; licence-unresolved; coverage-unverified. Count CG-specific originals separately from regional references and modelled estimates.
- Stop at original-source custody. No extracted normalized tables, translation, inferred nutrient values, recipes, country reassignment, database loading or UI work. Do not overwrite prior originals; deduplicate by checksum after acquisition.
- Keep raw datasets outside GitHub. The approved repository-upload allowance excludes them; documentation can record paths and hashes without embedding raw rows. No credentials or personal household microdata in this handoff.

**Priority order:** direct CG report/practice originals → official INS current release → WFP observed CG prices → regional composition guides/workbook → safety/provider page snapshots. The unresolved recipe, national guideline, recall-feed and live retail export categories should remain explicitly open rather than filled with DRC or generic global data.
