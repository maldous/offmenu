# Worker12 portfolio source-input binding

Selected task: `M-STAGING-BIND-20261018-W12`, ML/MM/MN/MO only. Base is the
verified develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Pending
PR42 is not this baseline. This package changes only portfolio bindings, their
metadata diagnostic interface and authored tests. It installs no source admission,
rights decision, downloader, country engine or shared-core change.

## Run the metadata interface

```sh
python3 -m offmenu.refresh.portfolio12 --now 2026-10-18T00:00:00Z
python3 -m unittest discover -s tests -p test_portfolio12.py -v
```

The CLI reads code-owned declarations only. Missing evidence is reported rather
than silently opened. `portfolio_report(now=..., observed={path: metadata_bytes},
previous={binding_key: prior_binding_digest})` additionally checks the declared
metadata hashes and JSON pointers. Callers supply only the exact receipt/validation
metadata listed in `portfolio12_bindings.BINDINGS`. The function opens no path.
Original paths and digests in `assetClaims` are historical manifest claims;
neither existence, size nor current source bytes are verified by this plan.
Do not populate `observed` with original bodies or bulk candidate JSONL.

Each source returns isolated fixed diagnostics: missing metadata, malformed
contract/time/JSON, pin or selector mismatch, held scope, or stale input. No source
exception text or source value is printed. All 24 country/type cells remain
explicitly unaccepted, including types without any input. Output is deterministic
for the same declarations, evidence and explicit UTC clock. A prior matching
binding digest yields a metadata-plan no-op only for an unheld authored fixture.
It is a replay hint, not an asset or acceptance receipt. Later validation time is
excluded from content identity; it never resets original acquisition age.

The 30-day threshold imports shared `acquisition.MIN_TTL`. Under30-day recorded
input age is distinct from verified usable cache. At exactly30 days the interface
reports `stale-input-review-required`; it never downloads, including for missing
cache or stale metadata. Unknown acquisition time stays unknown, even with a new
validation receipt. No force/revalidate option or retention entitlement exists
here. A real refresh will need a separately reviewed `SourceSpec` and the shared
`CachedAcquirer` boundary; this package neither constructs nor invokes it.

## Existing evidence and applicability

The Python declarations pin exact external receipt/validation manifests and their
selectors. Source snapshots remain on Foo; nothing is copied into this commit.

| Country | Retained source scope | Binding and origin declaration | Remaining limits |
| --- | --- | --- | --- |
| MM | World Bank RTFP market release2026-10-05, recorded archive/member hashes;71638 literal rows x60 columns | CSV row/column/header, complete header inventory, acquisition timestamp from retained capture; private literal review4278/Gateway4303 | Model estimates, not observed merchant offers. Non-oil detail, coverage/confidence operational meanings, cache/action-use and real source correspondence remain unqualified. |
| MO | DSEC Jan2025 bulletin table3.7, pp25/26;352 historical price strings | Existing bbox/row/block/column artifacts,22 item columns,66 annual+286 monthly values; MOP/kg with egg/orange/apple each exceptions |2022-24 observations, not current offers. Original acquisition timestamp not supplied in this binding; cache/action-use and future native schema still require scope acceptance. |
| ML | Two source-evaluation PDF integrity receipts,22+81 pages; exact Mali2004 print-only negative reply | Original manifest claims only; structured selectors absent | No structured recipe/nutrient records. Print-only/no digital exception, source-use and explicit denial/no-retry holds remain. |
| MN |2016 NSO historical receipt claims and retained rights/access metadata | No verified finite source input or record selector | Edition/language/manifest/action-use/custody unresolved; no body access or denied-route retry. |

Missing original-custodian identity is a provenance dependency, not a legal
prohibition by itself. Existing actual use restrictions and denials remain separate.
Public documentation may clarify semantics; a landing page or hash does not
create a use grant. The code deliberately prevents all real-source processing
even if a caller clears a copied list of holds.

### Official metadata read for this binding

On18 October2026, the [World Bank exact-release catalogue](https://microdata.worldbank.org/catalog/4501)
identified version2026-10-05 and described a mixture of measured and estimated
prices. Its ticker metadata supplies oil denominator L, other listed food
denominators KG, and the food index base January2018=1. This resolves the prior
index-base unknown for this edition; currency strings remain source literals.
The access section labels the estimates open data and requires a dataset citation;
the page refers further usage conditions to licence details. No new retention or
processing decision is inferred.

The [exact dictionary](https://microdata.worldbank.org/catalog/4501/data-dictionary/MMR_2021_RTFP_MKT?file_name=MMR_RTFP_mkt_2007_2026-10-05.csv)
lists71638 cases and60 variables. The individual
[coverage](https://microdata.worldbank.org/catalog/4501/variable/MMR_2021_RTFP_MKT/V016?name=data_coverage)
and [confidence](https://microdata.worldbank.org/catalog/4501/variable/MMR_2021_RTFP_MKT/V018?name=index_confidence_score)
pages provide labels and counts but no operational definitions in their displayed
notes. Those semantics remain explicit unknowns. Only public HTML documentation
was opened; no dataset, report, archive or held original was fetched.

## Shared qualification interface and authored verification

`literal_errors(binding, row, input_pins)` composes shared
`field_provenance.field_origin_errors` with source/release, literal shape, native
unit/basis allowlists and a declared coordinate grammar. It verifies declarations,
not source-cell equality or completeness. It does not manufacture origins or
map units. Real contracts need an additional reviewed source correspondence
validator, exact schema, independent expected IDs/counts and scope evidence.

The tests construct one tiny CSV with authored zero-text/unit/basis fields, two
authored rights/scope fixtures and exact origin pointers. They run the existing
`SourceContract`/`qualify` path with `fixture=True`; no acceptance function is
called. They cover deterministic success, origin inventory/pin/selector failure,
unknown units, held rights, absent metadata, malformed metadata, acquisition versus
validation age, the exact30-day boundary and a malformed sibling next to a valid
fixture. No record is dropped to make diagnostics pass.

## Proposed shared integration boundary, for existing integrator00

No shared-interface patch is proposed or required for this metadata package.
Integrator00 can review/cherry-pick the four owned files and run the bounded tests
without changing registry/admission tables. The observed MM/MO literals are not
the shared `[record]` candidate envelope; no wrapper or raw-data replay was done.

Before any separately selected real source task, the existing owner/integrator
must bind reviewed `SourceContract` factories to those exact native projections,
including source correspondence, expected IDs, actual acquisition evidence,
operation-specific retention/cache rights and a reviewed execution budget. MM's
recorded92,992,320-byte JSONL exceeds the historical64MiB eager parser input cap;
do not bypass that cap or copy a smaller unpinned derivative. Shared qualification
has its own bounded streaming interface, but using it on real bytes requires
explicit selected scope and resource admission. Do not independently modify the
shared execution core to accommodate this portfolio.

Independent review and develop integration remain required. Morgan owns scheduling;
existing00 owns integration. Preserve all source/privacy/Finland/Frida/nativeNO-FR
denial restrictions, old uncertain sends, rawFoo custody and separate DEV7645 lane.
Golden promotion, production and CIX remain held.
