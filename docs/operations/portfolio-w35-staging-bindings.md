# Worker35 retained source-input bindings

This package binds seven retained metadata scopes for GY/HK/HM/HN to the shared
develop contracts at `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It does not parse
source payloads, create production SourceContracts, accept datasets or implement
another country engine. The prior branch and external source artifacts remain
retained. The pending `28a5ba73` handover/PR42 is not the accepted develop baseline.
Local moving develop refs differed at pickup; integration00 must verify freshness
and reconcile this exact commit before integration, with independent review.

## Usable offline interface

`offmenu.refresh.portfolio_w35.bindings()` returns the fixed portfolio table,
including exact source/release, country/type, retained manifest pins, field
declarations, native units/bases, scoped source holds and explicit unknowns.
The JSON file beside the module is trusted checked-in configuration. A source
manifest or CLI input cannot supply an executable handler or grant rights.

`assess(packet, now=UTC, previous_key=None)` checks one metadata packet;
`diagnose(raw_bytes, now=UTC)` checks up to32 packets/64KiB with independent
diagnostics. The CLI performs the same operation:

```sh
python3 -B -m offmenu.refresh.portfolio_w35 \
  --metadata tests/fixtures/portfolio-w35/valid-metadata.json \
  --now 2026-10-18T00:00:00Z
python3 -B -m unittest tests.test_portfolio_w35 -v
```

The example fixture's acquisition/validation dates are **authored test inputs**,
not the real HN acquisition times. Real original acquisition timestamps remain
unresolved: receipt completion, HTTP Date, filesystem mtime and a fresh metadata
check are not substituted for original acquisition evidence. `observationTimesVerified`
and `assetBytesVerified` remain false. This interface checks declarations; it does
not verify a payload or publisher cache. A caller must not wire metadata-ready into
GLOBAL acquire/parse/normalize/qualify/accept stages.

The statuses are metadata-ready, no-op, missing-input, held, malformed-input and
stale-input. Each result always reports zero network/source processing/admission.
The key binds source/release/input path/hash, manifest pins, native field policy,
basis and holds. Rechecking at a later time does not alter this key. Equal key
means metadata replay/no-op, not that an output file was published. Original
acquisition age and metadata-validation age are reported separately; at30days
the result requires reviewed conditional validation, even if validation is recent
or the previous key matches. Under30days this planner cannot download. It imports
the shared acquisition minimum TTL and does not implement an HTTP/cache engine.
No real cache is created, renewed or proven rights-qualified by this package.

The shared `field_provenance.field_origin_errors` validates coverage/identity of
native **declarations**, and `global_run.StageResult` serializes the metadata check
receipt. Declaration nulls are placeholders, not observed source null values.
HN's source-record patterns and candidate-JSON pointers are templates tied to the
existing Table5/6 metadata; actual per-datum coordinate/value verification remains
an independent payload qualification step. Retained original PDF pages17/18 and
review receipts remain in the provenance chain. Native index points, percent and
percentage points remain distinct; December2025=100 is not currency/item pricing.

## Scoped bindings and typed dependencies

| Binding | Actual retained scope | Remaining prerequisite / owner |
| --- | --- | --- |
| GY reference | Five references and429HTML failure, no food rows | Existing complete release, source-use/schema/field origin; Morgan/source custodians. No retry of the failed endpoint. |
| HK restaurant licences | Publisher/terms references, no XML snapshot | Exact permitted operation/authorized principal terms decision, XML snapshot pin and dictionary contents; Morgan/principal/custodian27. Dictionary availability failure is technical, not itself a legal prohibition. |
| HK CFS | Index/rights metadata only | Exact work-specific written authorization and source selectors; Morgan/principal/custodian45. |
| HK cookbook | Publisher reference only | Edition, work-specific use and finite recipe scope; Morgan/principal/custodian27. |
| HM AFMA2024–25 | Original report pin, HM fishery reference subset | Report-specific derivative permission and territorial/semantic dictionary/selectors; Morgan/custodian28. General site terms do not establish these. |
| HN IPC July2026 Table5 | Reviewed literal candidate:48period slots,43observed,129numeric,15blank cells | Original acquisition timestamp and reviewed staging SourceContract/actual source-to-field semantics; Morgan/owner32/35. |
| HN IPC July2026 Table6 | Reviewed literal candidate:14rows,98cells,95numeric,3ellipsis-null | Same; no food-ontology, item-price or gold mapping implied. |

The six required country/data types are retained explicitly in configuration.
These seven partial source scopes do not satisfy full country/type applicability
or completeness. Neither an internal custodian's missing artifact nor a public
landing page establishes a legal prohibition or an operation grant. Existing
scoped holds stay until their actual decision owner qualifies the operation.
No old custody question is rerouted by this package.

## Current official documentation inspected18October2026

- [DATA.GOV.HK restaurant-licence catalog](https://data.gov.hk/en-data/dataset/hk-fehd-fehdlmis-restaurant-licences)
  identifies XML resources and a linked dictionary. No XML/resource body was read.
- [FEHD dictionary](https://www.fehd.gov.hk/datagovhk/data_dictionary/english/restaurant_licences.pdf)
  returned a web fetch timeout. Its field definitions were not invented; no retry.
- [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions), v1.2 dated26May2025,
  describe conditional use with attribution/compliance/indemnity. This documentation
  check does not establish the actual authorized principal's resource-specific
  operation decision or accept an agreement on OffMenu's behalf. Existing hold retained.
- [BCH monthly IPC series](https://www.bch.hn/estadisticas-y-publicaciones-economicas/publicaciones-de-precios/series-ipc)
  lists separate December2025=100 and December1999=100 series. It corroborates a
  distinction already in retained evidence; no linked data/PDF was downloaded.

## Integration boundary

Only this portfolio module/configuration, this document and its authored fixture/
tests are owned by35. No shared core files are changed. There are no proposed
shared-interface edits required for this metadata package. A future payload lane
needs a separately reviewed trusted `acceptance.SourceContract`, full native
schema/semantic callback, independent count/IDs, exact source custody/rights/scope,
and verified OS resource boundary before shared `qualify()`/`accept()` dispatch.
Adding GLOBAL production handlers or acquisition SourceSpecs remains a separately
selected integrator change; do not treat a metadata StageResult as that admission.

Independent review and verified develop integration remain pending. Source-use,
Finland/Frida/NO-FR native-crash,403/private/credential/denied-action, mandatory
auto_review, production/CIX and DEV7645 holds remain. Raw data stays on Foo.
