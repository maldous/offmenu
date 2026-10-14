# OffMenu corpus and research index

Checked 14 October 2026 (Melbourne). Navigation and integrity references only; no complete-corpus or app-acceptance claim. Exact base: `abe0ddc9db357b1e8d0d61825392d6b9923352f0` (published `origin/develop`); observed remote `main`: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. This new index is local and **not pushed**.

## Start here on Android

**Sign in to GitHub with access to the private `maldous/offmenu` repository.** These links point to existing blobs at the published base, not this unpublished index. Paths/blob IDs were checked against that exact remotely advertised Git tree; research manifest, canonical register and source ledger were also fetched through the connected GitHub service. This is link/source verification, not a device trial.

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

## Requirements and discovery authority

- [Canonical 105-ID requirement register](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/recommendation-delivery-register.json): actual local path `/home/user/src/offmenu-workers/worker-07/docs/recommendation-delivery-register.json`; 105 unique IDs verified. [Delivery reconciliation](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/delivery-reconciliation.json) is historical status/evidence, explicitly `programmeComplete=false`.
- Worker 14 secondary mapping: immutable `cd27c470a3671261651c7a42e884d9dda4bdf341`. Read `git show cd27c470a3671261651c7a42e884d9dda4bdf341:docs/worker-14-backlog.json` (and `.md`). Its 105 IDs match the canonical set. Those files are absent at the published base; no published URL is claimed. This index does not replace or modify Worker 14 consolidation.
- [Source delivery ledger](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/source-delivery-ledger.json): 1,303 entries verified; [country matrix](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/country-delivery-matrix.json): 249 unique ISO2 queues verified. Landing-page discovery, a download lead, or a country queue does not establish ingestion, matching, permission or operational coverage. The global register alone lists 365 sources; the combined ledger is the 1,303-entry reference.

## Capabilities: accepted scope versus pending work

- [Published provider code](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/cloud/provider-data.mjs) supports personal USDA/Edamam lookups and bounded public OFF/Open Prices/FSA/openFDA samples. [GLEIF/Wikidata enrichment](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/cloud/enrichment.mjs) produces candidates, not verified ownership or ingredient origin. [Catalogue labels](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/public/sources.js) are not proof of active connectors or grants. No provider requests, credentials or permissions were exercised here.
- Retained Worker 02 candidate `49c6ed037a0c506dc2e71a7c8ef40d423d6f46d0` has ledger-recorded acceptance of bounded source/synthetic compatibility only; it is not integrated at this base or published. See local candidate receipt in the JSON references.
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

## Fresh hosting check and rights boundary

At `2026-10-14T08:43:26.316324+00:00`, [hosted common manifest](https://offmenu-corpus.netlify.app/common-data/manifest.json) returned **HTTP 200**, 53,572 bytes, exact SHA-256 `a20aca224758eb6ac64ea89d0bb31d33280a2b0d2ec97e46ed6a2ddc71c92867`, matching [the historical byte receipt](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/common-data-manifest-checksum-verification-20261014.json). Root curation and recipe manifests exceeded the 1 MiB bounded read; their complete current hashes were not established. Three explicit manifest GETs only; no data partitions downloaded.

[The historical all-file publication receipt](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/common-data-publication-verification-20261014.json) is historical package/native-download evidence. This fresh check proves one manifest is still available and byte-identical; it does not revalidate all files, whole data coverage, country completeness, app behavior or producer admission. Legacy embedded manifest payload digests are distinct from exact file-byte hashes.

Original archives, normalized inputs, common/public projections, personal provider responses and private accounts are distinct. Public accessibility is not redistribution permission. Per-citation licence/share-alike/attribution, owner scope, source plan, retention/revocation and independent admission still apply; private provider/account data must never be promoted to commons by this index. See [the common rights contract](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/corpus/common-data-contract.json) and [curation boundaries](https://github.com/maldous/offmenu/blob/abe0ddc9db357b1e8d0d61825392d6b9923352f0/docs/curation-architecture.md).

Evidence/control receipt: `/home/user/Documents/Codex/2026-10-14/task-2/worker-07-corpus-index/`. Supplied controls: unrestricted filesystem (`danger-full-access`), network enabled, mandatory `auto_review`; separate approval-policy value unavailable. User configuration separately says profile `disabled`, filesystem `unrestricted`; it is not the basis for the active-control statement. No credential/security configuration changed.

Review gate: documentation only, pending independent review. No push, provider/source activation, production publication or programme acceptance.
