# Food places and additional national composition files

This checkpoint adds complete pinned Overture place acquisition and the complete
publisher downloads for Finland, New Zealand and Sweden. Serving acceptance and
live deployment evidence are recorded in `expanded-places-national-20261013.json`.

| Source | Complete local scope | Accepted curated records |
|---|---|---:|
| Overture 2026-09-23.1 | All 16 Parquet objects, 81,455,423 places examined; full food/drink, food-store, farmers-market and agricultural-site taxonomy selection | 12,681,108 |
| Fineli Release 20.0 | All 47 CSV tables in the 74-component archive; companion 55-component and raw-ingredient downloads retained | 4,238 |
| FOODfiles 2024 Version 01 | All 30 installer components retained; 2,857 foods and 571,495 unabridged nutrient observations parsed | 2,857 |
| Swedish database 2026-07-01 | Complete publisher workbook export; 2,606 foods and 151,148 nutrient cells, including missing cells | 2,606 |

Overture contains 1,794,885 retailer and 10,886,223 site references. Original
address-country tags include 251 values; 242 match the project's country registry.
UK maps to GB; unsupported tags stay in `sourceCountryTags` and are not allocated
by country filters. Category, country, confidence and operation remain source
assertions. Ownership, inventory and diet qualification remain unknown. Farm
classification alone does not establish food production. There is no confidence
threshold, first-N cap or name-only identity merge.

## Public API attribution and notices

`GET /api/data/public?source=overture-food-places&country=AU&kind=retailer`
returns selected place references. Every record carries original source licences,
attribution, provider names and links to notices. **Foursquare source data requires
the full [publisher NOTICE](https://offmenu-corpus.netlify.app/notices/overture-food-places/2026-09-23.1/FOURSQUARE-NOTICE.txt).**
The [Apache 2.0 licence](https://offmenu-corpus.netlify.app/notices/overture-food-places/2026-09-23.1/Apache-2.0.txt)
and [CDLA Permissive 2.0 licence](https://offmenu-corpus.netlify.app/notices/overture-food-places/2026-09-23.1/CDLA-Permissive-2.0.txt)
are also served with checksummed copies. OffMenu's field selection and omissions
are disclosed. Original Parquet files, contacts, street addresses and geometry
remain local. See the authoritative [Overture attribution rules](https://docs.overturemaps.org/attribution/#places)
and [Foursquare notice](https://opensource.foursquare.com/places-notice-txt/).

National lookup source IDs are `fineli`, `foodfiles` and `sweden-food`, with
country filters FI, NZ and SE. Source nutrient values are unchanged and definitions
stay namespaced. Missing and trace values remain distinct from zero. New Zealand
fatty-acid and nitrogen denominators are not treated as per-100g whole-food values.
Its multiple energy, carbohydrate and fibre definitions remain separate locally;
canonical energy uses the explicitly identified FSANZ available-carbohydrate
calculation. Original recipe bodies and dietary assertions do not become verified
meal plans or diet rules.

[Fineli's CC BY 4.0 notice](https://fineli.fi/fineli/fi/avoin-data) requires THL
attribution and no suggestion of endorsement. The actual archive has 4,238 foods;
the landing page still labels it 4,232. Release 20.0 is retained as the named
publisher download, not represented as current live API data. Four unquoted
bibliographic line breaks are rejoined without changing citation text.

[FOODfiles terms](https://foodcomposition.co.nz/terms/) require unchanged source
data, attribution and downstream access subject to those terms. These conditions
remain in every curated record's provenance. The supplied Excel names table
resolves one unescaped tilde in the text sampling-description field. The 2024
installer is the current complete download; the newer 2026 online search is a
separate source version, not included in this snapshot.

[Sweden's publisher terms](https://www.livsmedelsverket.se/livsmedel-och-innehall/naringsamne/livsmedelsdatabasen/sok-naringsinnehall/)
require source/version attribution and unchanged values. The export itself names
version 2026-07-01. Recipe-derived composition entries provide nutrient references,
not quantified cooking instructions.
