# Worker34 retained source-input declarations

Selected task: `M-STAGING-BIND-20261018-W34`. Base is accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`, independently verified with
`git ls-remote --heads origin develop` at pickup on 18 October 2026. The local
remote-tracking ref was stale and was neither used nor changed. The existing
Worker34 checkout and historical artifacts remain intact. Pending PR42 is not
this baseline.

## Runnable metadata interface

From the checked out source, run:

```sh
python3 -m offmenu.refresh.portfolio34 --now 2026-10-18T05:15:00Z
python3 -m unittest discover -s tests -p test_portfolio34.py -v
```

The command reads only the fixed JSON receipt/manifest paths in
`portfolio34_bindings.py`. It never follows any source body, parsed candidate,
URL, archive or publisher link declared inside those files. Each metadata input
is bounded to 512 KiB and must match its exact retained SHA256. A missing,
changed, unsafe, malformed or oversized metadata file produces fixed diagnostics
for its own source; peers continue. No source values or exception details appear
in errors. The full private report intentionally contains retained metadata
declarations and internal source paths; it is not a public projection.

Output is canonical JSON. `results[].rows` contains only
`sourceInputDeclaration` records. `sourceDataAccepted` and `countryComplete`
remain false. Exit 0 means every declaration is ready **as metadata only**;
exit 2 means at least one missing, held, malformed or stale input. Argparse uses
exit 2 for invalid CLI arguments as well; consumers must inspect the structured
per-source statuses. All four real bindings currently remain held.

Each declared scalar, including nulls and array elements, has an exact input
alias/SHA/JSON-pointer origin, checked with shared `field_origin_errors`.
`semantic_errors` additionally compares literal source-coordinate values: origin
coverage alone cannot validate a changed value. Source metadata roles are not
food/nutrition/price equivalence. Actual body identity pins are reported only as
retained receipt values; no fresh body checksum or physical custody is asserted.

The adapter uses shared strict JSON, timestamps, canonical serialization,
fingerprints, input-name validation and per-datum provenance. Authored tests
exercise the shared `SourceContract`/`qualify` interface on a temporary fixture
bundle with an independently authored rights/scope fixture. The fixture callback
is valid only for `sourceInputDeclaration`, never a nutrient/price/recipe record.
No real `SourceContract`, production admission or dynamic callback is installed.

## Portfolio and scope

| Country | Retained source/release | Applicability and remaining binding |
|---|---|---|
| GQ | BEAC BES N27, receipt `05d753ce…`, original reported `99d98756…`; custodian16 return consumed5229 | Regional statistical context. GQ table/page/row/column, index versus item price, period/base/geography and exact extraction-use decision remain scoped NOT_HELD. No denied INEGE/IMF/World Bank retry. |
| GS | BAS DOI `10.5285/93a1239d-e0b6-4ed4-889f-63126d0ffb80`, v1.0; source-context manifest `775a9b4e…` | Scientific survey evidence, not human-food composition. Manifest retains catch-mass definition in kg and source lineage, not canonical nutrition units/basis. 2,739 historical scientific rows and the separate 13-ID unmatched dossier remain unchanged. General cleaning language is not per-ID exclusion proof. |
| GT | INE urban/rural CBA2024–2026, update7Oct2026; receipt `250997e0…`, dictionary `234f2971…` | Expenditure basket. Dictionary distinguishes daily/monthly grams, kcal and costs, base quantities/units and base-unit price. Physical workbook coordinates, edible/purchased basis, field-level denominator, currency, missing rules and exact intended-use scope remain unresolved. No observation cells read. |
| GU | UOG CNEP retained88-original inventory `343e7456…` | Recipe-card acquisition inventory, not parsed recipe records. Derivative NOT_GRANTED/admission WITHHELD preserved. Exact per-card fields, yield/quantity and source-specific use/credit remain unresolved. |

The exact full pins, release labels, JSON pointers, source-use text and explicit
unknowns are in the fixed bindings and their pinned receipts. Historical source
producer labels do not appoint new custodians. Dataset completeness and required
country/type coverage still use the existing coverage-and-gaps manifests; none
is completed by this package.

## Cache, acquisition and replay

`inputKey` binds policy/configuration and exact metadata pins. Pass
`--previous-key SOURCE=SHA256` (repeatable) to declare a prior key. Identical input
reports `unchanged-no-op` with identical declaration bytes. There is no mutable
source cache, accepted pointer or output store in this command.

`--now` is a required explicit UTC validation clock. Original acquisition is an
independently declared receipt pointer, never file mtime, manifest creation,
HTTP Last-Modified or recent validation. GQ has an exact completed acquisition
response timestamp. GS lacks a bound original acquisition clock in its selected
manifest. GT/GU lack a reviewed multi-original cache binding; neither uses `checked_utc`
or inventory creation to manufacture freshness. GT's exact urban/rural response
timestamps and GU's first-original acquisition timestamp are retained as metadata
declarations; GU's full pinned manifest records each `/files/*/acquiredUTC`.
Those clocks are evidence, not an implemented reviewed multi-input cache policy.

Below30days, a verified acquisition clock permits metadata reuse only. At30days
the outcome requires conditional review, with zero downloads. Validation does
not reset acquisition age; missing or future acquisition evidence fails closed.
This code does not verify actual raw-cache retention. It cannot demonstrate
30days of real source retention or relax the shared acquisition policy. The
shared acquired-body cache/automatic refresh must be wired only after exact
source scope and independent review. No force-download option is exposed.

Integrator00 result5798 and its pinned late addendum confirm that no source-neutral
pure cache planner exists on this baseline. The report types that capability as
`unavailable-on-pinned-baseline` and real body adapters as `not-selected`.
The local `cache` field is metadata-age **intent only**, not a replacement shared
engine. Neither Wikibooks `core.cache_policy`, registry-only `plan_fixture`, nor
operational/body-reading `CachedAcquirer` is called or identity-spoofed. A future
central pure-planner API remains Integrator00/Morgan's separate proposal.

## Public documentation checked

Only official publisher documentation/metadata was researched, no new source
data downloads or held original reads. Search evidence is weaker than a retained
source-specific notice and does not change a recorded restriction.

- [BEAC bulletin catalogue](https://www.beac.int/publications/bulletin-economique-statistique/): official search result lists N27 under2025/CEMAC. This is catalogue context, not a table period, PDF edition proof or GQ applicability. The page open timed out.
- [BEAC legal notice](https://www.beac.int/mentions-legales/): official indexed text describes personal noncommercial copying subject to restrictions, without a resale/rediffusion grant. Direct page open timed out. No operation-specific interpretation or source-hold release is made here.
- [INE CBA dataset](https://datos.ine.gob.gt/dataset/costos-de-la-cba-urbana-y-rural): indexed metadata still states no licence provided; exact current page open timed out. An indexed older activity view is not treated as a current resource version. The already-pinned dictionaries remain the concrete field evidence.
- [UOG library policy](https://www.uog.edu/student-services/rfk-library/policies): page read successfully, including copyright information. Library collections policy does not establish applicability to CNEP cards. A CNEP landing path returned404 and was not retried. Unrelated UOG publications' notices are not imported as card permissions.

## Integration and typed remaining blockers

Owned additions are these two portfolio modules, tests and this document. Shared
core is unchanged. Integrator00 can review the exact commit and run the authored
tests plus shared provenance/qualification tests. No shared interface change is
required to consume the metadata report or the `semantic_errors` callback.

Future **source-data** staging needs separate reviewed source contracts:

1. `SOURCE_SCOPE_OR_SELECTOR_MISSING`: GQ table/period/unit and GS food-role,
   GT physical coordinates/basis/denominators, GU recipe quantity/yield selectors.
2. `SOURCE_USE_UNQUALIFIED_OR_HELD`: retain each exact existing restriction;
   general site access or a missing internal custodian does not decide legality.
   GS local scientific OGL scope is not an unrelated human-food grant.
3. `ACQUISITION_CACHE_EVIDENCE_MISSING`: GS original acquisition binding,
   GT/GU reviewed per-original clock-to-cache bindings and validator/retention
   evidence, plus demonstrated shared >=30day raw cache policy.
4. `REVIEW_AND_INTEGRATION_PENDING`: independent approval of this immutable
   commit, then Integrator00's normal develop integration. Golden promotion and
   fresh baseline qualification remain later gates.

All source/privacy/Finland/Frida/NO-FR/native crash/credential/denied-action holds,
old uncertain sends, raw-Foo locality, DEV7645 separation and production/CIX pause
remain. No refresh of raw sources, runtime installation, automation or shared
engine change is selected by this package.
