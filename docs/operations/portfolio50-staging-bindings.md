# MV / PR / SD / SM receipt-to-staging bindings

Request `M-STAGING-BIND-20261018-W50`. Base: sole-integrator-confirmed develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. The previous Worker50 branch and
external evidence remain intact. These additions own only `offmenu/portfolio50`,
this document and `tests/test_portfolio50_bindings.py`; shared refresh code is
unchanged. Pending PR42/handover is not the accepted baseline.

## Usable interface and boundary

```sh
python3 -B -m offmenu.portfolio50.bindings --now 2026-10-18T12:00:00Z
python3 -B -m unittest discover -s tests -p test_portfolio50_bindings.py -v
```

The CLI accepts only an explicit UTC clock. It reads the four exact, code-pinned
`receipt.json` files in `profiles.py`, bounded to 1 MiB each. It never follows an
original path, opens a workbook/PDF/CSV/ZIP/HTML body, creates a cache, fetches,
imports historical collectors, registers an adapter or constructs a production
`SourceContract`. Exit 2 means at least one binding is not metadata-ready; this
is the expected real-portfolio result, not a crashed parser. Stdout is the report.

`inspect(binding, raw, now=..., validated_at=..., previous_key=...)` returns typed
`metadata-ready`, `missing-input`, `held`, `malformed` or `stale-input` outcomes.
The `Binding` is trusted application code, never built from CLI/source fields.
`assess_many` isolates missing/malformed peers. `stage_interface` returns the
existing `StageResult` envelope with `unsupported/portfolio-metadata-only`, not a
successful acquire/normalize/accept stage. Production dispatch is not installed.

Source release, original size/hash and acquisition time come from literal receipt
pointers. Local binding IDs are receipt identities, not canonical source mappings.
Every projected scalar, including explicit nulls, is checked by the existing
`field_origin_errors`; nulls with no known source coordinate cite the reviewed
unknown-marker policy, never an invented source cell. Native units, bases and
selectors stay unknown where exact evidence is absent. There is no unit conversion,
translation, default 100g basis or canonical nutrient mapping.

Replay identity includes the receipt content pin, source/release, field map, holds,
dependencies and policy. Observation clocks do not change it. Repeating an eligible
metadata projection with the same key produces `unchanged-no-op`. Fresh validation
never resets original acquisition age. At the shared `MIN_TTL` boundary (30 days)
the metadata interface requests review and performs zero downloads. Under 30 days
it also performs zero downloads. It does **not** certify source cache integrity,
freshness/HTTP retention, or implement another cache engine.

Shared reuse: core strict JSON/canonicalization/hash/UTC clock and safe paths,
`acquisition.MIN_TTL`, `field_provenance`, `global_run.StageResult`, and the generic
`acceptance.qualify` in an authored-fixture integration test. Only authored test
metadata, rights and scope files are qualified there; no production source contract
or country acceptance is generated. Shared `CachedAcquirer` owns any future lawful
cache execution. No network callback is exposed here.

## Exact retained input and remaining scope

Full immutable receipt pins and selectors are in `profiles.py`; all four real
profiles have non-overridable code holds for body-operation selection and source-use
qualification. Source metadata can describe a condition or grant but cannot clear
those reviewed configuration holds itself.

| Country | Selected receipt / release | Native facts and typed remaining blockers |
| --- | --- | --- |
| MV | `3da11b31095dd318ce8f`; MBS August 2026 CPI XLSX | 323221 bytes and nine sheet names declared. Exact food sheet/range, index base/unit/period and private structured-use/credit scope unresolved. CPI is not an item offer or physical basket. |
| PR | `0095e92f71b581e8ef27`; UPRM bitstream `20378e59-fd11-4593-8f2e-a774fa1c9905`, 2018 | 994839-byte thesis; native36 metadata producer now bound. Exact nutrition table/treatment/unit/basis and structured-use/citation scope not held. No culinary raw/cooked equivalence. |
| SD | `d0a270bf30f14afcad10`; World Bank 2026-10-05 modeled market prices | ZIP 793811 bytes; exact CSV member retained. Headers/missing codes/item units/bases need version-bound evidence. SDG is a currency declaration, not a quantity basis. Publisher metadata versus retained market-count scope differs. |
| SM | `2531d123cb8b64a637b6`; December 2025 CPI PDF | 230793 bytes declared. Native61 historical producer bound; current body-operation custody/transfer unresolved. Exact table/base/unit/period and derivative-use/credit manifest not held. |

Existing PR36 and SM61 responses explicitly report the missing selectors/candidates
as NOT_HELD and use scope as UNKNOWN. Do not route the identical unanswered request
back to them. Morgan decides a new exact evidence/operation scope. Source holds,
Finland/Frida and NO/FR restrictions, production/CIX and DEV7645 custody remain.

## Current official documentation, 18 October 2026

Only public publisher documentation was researched; no data downloads, original
body reads, forms/terms acceptance or publisher contact occurred. These are bounded
paraphrased observations and URLs, not offline snapshots or new permission decisions.
Mutable documentation must be version-bound before processing.

* [MBS CPI publication/guide index](https://statisticsmaldives.gov.mv/cpi/): exposes
  methodological guides; it does not establish the retained August workbook's
  literal food range or an applicable reuse grant. Guide PDFs were not opened.
* [UPRM thesis copyright guidance](https://libguides.uprm.edu/licensing-your-thesis/thesis-copyright):
  states student thesis copyright normally belongs to its author. The exact thesis's
  license/derivative conditions remain unverified; repository access is not a grant.
* [World Bank exact October-version access terms](https://microdata.worldbank.org/index.php/catalog/4506/get-microdata):
  describes commercial/noncommercial adaptation subject to metadata attribution,
  nonendorsement and third-party restrictions. This improves terms evidence but does
  not resolve release-specific exclusions or authorize this held processing lane.
* [World Bank study description](https://microdata.worldbank.org/catalog/4506/study-description):
  describes modeled estimates and ticker-specific units. Its displayed September
  version cannot automatically qualify October's item units. Different official
  pages expose different versions. The October access page says 19 markets; the
  retained receipt declares 20. Preserve the discrepancy for scope review.
* [World Bank variable metadata](https://microdata.worldbank.org/index.php/catalog/4506/variable/SDN_2021_RTFP_MKT/V002?name=country)
  identifies `country` for the October member and reports 4760 valid values. Other
  searched dictionary metadata exposes ISO3/area/market/location fields; it is an
  incomplete header view. A direct October dictionary open returned a tool
  accessibility error, not a publisher access denial; no alternate data fetch followed.
* [San Marino price documentation index](https://statistica.sm/pub1/StatisticaSM/Dati-statistici/Prezzi-e-retribuzioni/Prezzi.html):
  distinguishes 2016–2025 from 2026 ECOICOP2 series. Do not transfer a 2026 method or
  classification into the retained December 2025 PDF without exact evidence. Linked
  original reports/method PDFs were not opened; reuse terms remain unresolved.

## Proposed shared interface, integrator00 ownership

No shared change is included. The current `core.cache_policy` is Wikibooks-specific,
`policy.plan_fixture` requires a registry fixture and `CachedAcquirer` accesses the
filesystem/body and can fetch. An optional future pure shared planner would take
trusted source/release/body pin, original acquisition and separate validation evidence,
clock and reviewed holds/retention scope; return original-age and zero-download
reuse/revalidation-review diagnostics without stat/read/network/registry mutation.
It should reject forced under-window automatic downloads and never turn metadata
into permission or body verification. This is a proposal to integration00; this
portfolio module implements only metadata binding and a diagnostic interface,
not that shared planner or a refresh engine.

Review/integration prerequisites: exact source commit, independent review, Morgan
verdict and normal develop integration. Passing authored tests establishes code
behavior only. All six country categories remain incomplete; golden promotion later.
