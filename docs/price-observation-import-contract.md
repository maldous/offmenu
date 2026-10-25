# Existing price observation pipeline: bounded contract

This describes the existing global country/source registry and regional adapters,
plus a narrow identity fix. It is not a new price platform or acquisition grant.
Source code inspected: default `8266d8a1`, with the same seven price-related files
in the current PR137 source group. No runtime adoption is claimed.

## Actual import, save and lookup paths

`setupData` accepts unified JSON or mapped CSV, validates records, then saves only
after the source-use confirmation. Local save uses a Map keyed by unified record
ID. Signed save calls `/api/data/records`; `storePrivateRecords` applies record
policy and upserts on `(owner,id)`. Re-import of a stable observation ID therefore
updates that observation instead of duplicating it.

A product barcode is not an observation ID. Price CSV now requires a mapped,
nonblank source observation ID, unique within the batch. Different dates, stores,
channels, variants or conditions must have their own source observation identity;
the importer does not invent one from barcode or row number. A provider correction
to the same native observation may reuse its ID. Mapping a product/SKU column as
the observation ID is not justified merely because it is nonblank.

Open Prices JSON from the existing public adapter goes through `normalizePrices`.
Its native observation ID and location ID stay lexical, including zero. Product
barcode `00123` remains distinct from `123`; no GTIN verification, retailer-SKU
equivalence, variant/pack equivalence or canonical product join is inferred.
The imported data view displays amount, currency, observation date, store and the
provenance record. Its full record detail retains supplied data.

The separate Insights price button calls `/api/prices?barcode=…` and displays dated
API observations. It does not currently search saved/imported observations.
The existing public data lookup checks corpus lookup first, then its unchanged
Open Prices adapter when applicable. No API call or source acquisition was made
for this implementation or its tests.

## Shared global observation contract and present gaps

Preserve supplied source identity/provenance, GTIN/barcode, retailer SKU, variant,
pack size/unit, store/location/service area/channel, language, observation date,
time/offset/time zone and date precision, amount/currency/tax inclusion, unit
price and denominator, promotion/regular price/loyalty conditions, and fulfilment,
shipping and comparison conditions. Missing information is unknown, not zero,
false, tax-inclusive, universally available or a licence to infer a join.

The current CSV adapter maps observation ID, name, barcode, amount, currency,
date, retailer name and selected country. It does not yet map all of those richer
conditions. Its country selection is user-supplied, not independently verified.
The Open Prices adapter maps its existing supported amount/currency/date/location,
unit-price, discount/regular-price, duplicate/proof and provenance fields. A
date-only source value does not establish a time zone. The richer fields survive
existing unified-JSON validation/storage when explicitly supplied, but that is
not a source adapter, semantic validation or product/location identity proof.

Compare prices only when product/variant/pack, units, currencies, tax treatment,
market/store/service area, channel, date precision and applicable promotion,
loyalty and fulfilment conditions support the comparison. Do not silently convert
currencies, gross/net tax or shipping conditions. Historical prices are dated
observations; availability remains `unknown` and is not current stock or an offer.

## Existing connector and market coverage

Reuse `SOURCES` and the existing country/source registry. Listed countries describe
declared connector scope, not populated coverage, current observations or rights.

| Connector path | Declared registry scope | Current source-code state | Coverage/freshness/use in this task |
| --- | --- | --- | --- |
| Open Prices | Global/unspecified countries | Existing public lookup and native normalizer | Per-market coverage unknown; each observation date governs its limited time evidence; no live request or new body permission |
| WhichGrocer | AU | BYOC/API adapter pending | No credentials, plan, current permission, coverage or freshness verified |
| Instacart | US, CA | BYOC shopping-list adapter pending | Not an admitted global price or stock feed; permission/coverage unknown |
| Kroger | US | OAuth adapter pending | Requires its existing registered-app/user-consent workflow; none activated here |
| ALDI country portals | Existing listed regional countries | Browser workflow references | Per-site terms, selected market and lawful collection scope must be established; no global barcode-price API assumed |
| Retailer browser import | Selected user market/site | Existing extension preview/private import | User review and actual source permission are required; consent alone does not override retailer restrictions |

Permitted feeds/APIs require the existing provider-specific adapter, exact source
terms, operation/retention rights and provenance. Site collection requires an
explicitly allowed site/operation and reviewed private import; this task grants
no crawl or scrape. Consented BYOC requires the user's supported provider access
and the existing scoped credential/consent workflow; no signup, paid plan,
credentials or settings were changed. No Zyft content or credentials were used.

## Retained-data restriction and evidence

No eligible real retained price example was supplied. The historical Open Prices
10208 admission was superseded by the 10256 KEEP SEALED disposition; 10264 read
permission was false and 10360 source prequalification kept all readiness flags
false. These exact journal references were supplied by00; no held sample or cache
body was read. A current qualified SourceContract, clock/custody/use binding and
body admission, or a different eligible retained example selected by its actual
custodian, is required before a real-example proof. Generated work is independent
of that hold.

The focused proof uses authored JSON/CSV only: two observations share lexical
barcode `00123` but differ by source ID, date, store and amount. The old implicit
barcode fallback collapses them; the new guard rejects missing/duplicate IDs.
Explicit IDs retain both across repeated local saves and the existing owner/ID
upsert. Native zero/false/null and supplied unified-record conditions/provenance
remain distinct. Mock DB/DOM evidence is not a real account, database, current
market, price comparison or browser acceptance.
