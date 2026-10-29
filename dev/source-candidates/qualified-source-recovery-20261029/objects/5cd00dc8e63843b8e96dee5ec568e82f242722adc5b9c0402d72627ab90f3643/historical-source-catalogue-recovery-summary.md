# Historical source catalogue recovery

Recovered a 164 KB metadata-only JSON: `historical-source-catalogue-recovery.json`. No repository mutation, new dataset download, raw dataset inspection, or Foo access.

## What is established

- Exact repository-linked catalogue evidence: 365 global discovery citations across 249 countries; 938 enrichment canonical sources; their 1,303-row discovery ledger. Cloud-retained copies were verified against Git blob hashes.
- All 22 retained native-source mappings, including exact historical source IDs, releases, canonical types, attribution and licence statements, with separate current repository permission/download evidence where available.
- Ten focused global/shared source contracts and 17 exact country-level UN/FAO/WFP citations. IDs retain their originating register namespace.
- Overture `2026-09-23.1`: 16 exact Parquet keys and SHA-256s, 81,455,423 historical rows examined, 12,681,108 selected, explicit food/farm inclusion and tobacco exclusion. Its archiveSha256 hashes the acquisition manifest, not the concatenated source files.
- USDA April 2026: full ZIP candidate URL, declared archive SHA-256, 34 CSV table schemas, archive members and historical counts. The direct download and API are explicitly separate.

## Important limits

- Current 57 local assets remain unbound: the requested metadata export was not available to this review. Original requested/final URLs, current path/bytes and exact asset-to-release joins remain necessary.
- OSM has citation IDs S042/S043 and enrichment ID `src-dc7480cf5666`, but no validated historical dataset URL/release. Website manifest/XML links in its old ledger are not OSM data extracts.
- WFP S031 is the HDX API cookbook PDF, not a price dataset. Its per-country package/resource acquisition contract remains unresolved.
- No UN M49/UNSD source entry was recovered. FAOSTAT and UN Comtrade appear only as named follow-up context, with no bound asset.
- The OFF October 12 collection receipt is explicitly superseded by the Unicode line-separator defect. Do not promote its old counts to current acceptance.
- Discovery links, publisher rights evidence and historical receipts do not establish current runtime admission or current file custody.

## Repository references

- [Global source register](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/research/OffMenu_Global_Data_Source_Register.json)
- [Enrichment register](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/research/OffMenu_Enrichment_Source_Register_249.json)
- [Country basket register](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/research/OffMenu_Country_Basket_Register.json)
- [Native mappings](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/corpus/common-source-mappings.json)
- [Overture receipt](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/docs/collections/overture-food-places-2026-09-23.1.json)
- [USDA receipt](https://github.com/maldous/offmenu/blob/8652b312ce7989c5e4f2d49ae765d5d8daf5841d/docs/collections/usda-2026-04.json)
- [Release/permission metadata](https://github.com/maldous/offmenu/blob/60201e957fed59ce7e28f0528a78d4542ca20265/docs/source-release-permissions-evidence.json)

Validation: JSON parsed; Git-blob identities matched; all 16 Overture per-file row totals reconcile; USDA schema count is 34. No raw-body verification claimed.
