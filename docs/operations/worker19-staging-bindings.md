# Worker19 retained metadata bindings

Request `M-STAGING-BIND-20261018-W19`, portfolio AF/AM/BT/CN. This proposal starts
from accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It adds an offline
metadata preflight and six explicit source branches. It installs no source-body
parser, acquisition route, source acceptance contract, GLOBAL handler or gold
promotion. Independent review and integration remain required.

## Use

From the checkout, provide an explicit UTC observation time:

```sh
python3 -m offmenu.refresh.owner19_bindings --now 2026-10-18T00:00:00Z
python3 -m offmenu.refresh.owner19_bindings --now 2026-10-18T00:00:00Z --retained-metadata
python3 -m unittest tests.test_owner19_bindings tests.test_refresh_field_provenance tests.test_reference_acceptance tests.test_reference_adapters
```

The first command reports missing metadata without opening retained files. The
second reads only the twelve pinned JSON metadata paths in the checked-in
catalogue. It does not follow paths inside those files. JSON response headers or
source values are never printed. Missing files, filesystem denial, rejected
paths, malformed JSON, changed pins and source holds have distinct diagnostics.
The Foo/POSIX reader pins parent directories, opens the leaf without following
links and with nonblocking mode, and checks the opened descriptor is regular
before reading. Reads are bounded; descriptor identity/size/times must stay stable,
and every descriptor is closed on success or failure.
The exit status describes request validity; inspect each result's status for
source readiness. A held/missing source does not suppress another result.

Library callers can pass bounded metadata buffers to `inspect_portfolio`, with
prior build keys keyed by binding ID. There is no arbitrary-config CLI, dynamic
plugin, force flag or route that enables a source. The catalogue is reviewed
application configuration, never a rights grant derived from a source manifest.
Non-Overture source IDs are local binding names, not new global registrations.

## Source branches and remaining requirements

| Branch | Retained evidence and source applicability | Remaining dependency / owner |
| --- | --- | --- |
| AF Overture | Release2026-09-23.1, pinned AF manifest, reviewer20 selection and reviewer46 semantic pair. Historical514 candidates,7 exclusions,14 source-local definitions/514 links. Food venues/retailers only. | Worker19/integrator00: reviewed legacy-native field-origin/format binding. Shared projection adapter expects a different format. Morgan must separately select actual record processing. |
| AF production | Source10 receipt and exact native-holder response; Ministry report1402 title,41 pages reported. Separate from Overture. | Holder has already attested no map/private-use/crosswalk in checked metadata. Worker19 needs selected table/row/crop/region/unit/statistic mapping; source-use reviewer resolves operation scope. No repeated same-question custody request. |
| AM annex | Two2025 government routes in source17 receipt; both originals arrays empty. Basket-reference intent only. | Source17/Morgan: complete permitted original and exact native custody. Worker19/source-use reviewer: table/population/currency/quantity/schema and action-specific scope. No duplicate acquisition selected. |
| BT prices | DAMC Apr–Sep2021 Thimphu title;2-page original reported. Exact B01-W19-51 response and claim bind native holder01a139a6-42f9-7de2-bb25-c1dcd7ed4b7a. | Checked metadata retains no table/header/row, currency, quantity/package, market or statistic map, and no private derive/retain-use decision. Worker19 and source-use reviewer resolve under separate processing scope. |
| BT assessment |2017 MoESD dietary assessment,33-page original reported. | Worker19/source-use reviewer: table/population/basis/schema and action-specific scope. Assessment does not establish national normative guidelines. |
| CN monthly | MOA issue145 October2025 commodity supply/demand publication; original pin reported. | Source17/Morgan: exact native custody; Worker19: metric/unit/quantity/statistic/observation-time map; source-use reviewer: operation scope. Not retail offers. Jiaozuo403 remains separate and no-retry. |

Exact artifact paths, SHA256 pins, selector assertions, scoped reviewer evidence,
native unknowns and typed blockers are in `offmenu/refresh/owner19_bindings.json`.
The four-country coverage receipt remains the source for uncovered ingredient,
recipe, composition, dietary, retailer and price/basket requirements. Six source
branches do not imply complete type coverage. Missing internal custody is an
evidence dependency, not itself a legal prohibition. No new legal prohibition or
permission is inferred here. Existing source restrictions retain their scope.

Field declarations distinguish metadata selectors from **unbound** original
datum coordinates. Null units/bases stay null. The old AF normalization omitted
geometry/contacts/street addresses; this package does not reconstruct them or
reinterpret semantic-link acceptance as full lineage acceptance. Metadata hashes
and historical review receipts do not revalidate the underlying data bytes.

## Clocks, replay and shared interfaces

Metadata inspection time is explicit and separate from original acquisition.
Every real binding currently reports its original acquisition clock as unknown:
release dates, report creation dates, source dates and file mtimes are not
substituted. Authored tests exercise known clocks at5 and30 days and prove that
later validation never rejuvenates the original age. The30-day comparison is an
age diagnostic only; it grants neither reuse nor refresh. All real operations
remain disabled.

The build key includes trusted configuration, metadata pins and hashes of this
module plus the two shared code modules it uses. Observation time and the prior
key do not enter identity. A same-key/current-pin result is
`no-op-unchanged-metadata`; an integrity failure never reports no-op. This is
diagnostic replay only: no materialized-record or persisted cache claim follows.

Integrator00 result5798 (`baseline-interface-receipt.json`, SHA256
`f94fbf0a42b5d7906e20ace0416295ae569ee400ddfd770f90a427f803d3b7cb`)
confirms that develop has no source-neutral pure cache planner. `core.cache_policy`
is Wikibooks-specific, `plan_fixture` is registry-only, and `CachedAcquirer` is
operational and may read bodies/fetch. None is invoked for these real bindings.
The output reports `shared-pure-planner-unavailable` and `unknown-no-download`.

The central proposal remains exactly a pure `plan_retained_input` interface:
reviewed source/release/bundle identity, original acquisition/revalidation chain,
UTC now and retention/hold status; zero I/O/network/rights acceptance. This package
requests no parallel implementation. For AF legacy normalized input, integrator00
must separately select a reviewed retained-native contract; do not feed old
singleton JSONL to the shared source-projection parser or reconstruct originals.

Tests compose shared `strict_json`, `canonical`, `timestamp`,
`reference_adapters`, `field_origin_errors` and `SourceContract/qualify` using
wholly authored fixtures. Qualification requires operation scope and every datum
origin, including null/zero, plus exact native selector/value checks. A fixture
pass is not real source admission, country completion or gold admission.

## Custody and review

Worker19 owns only this catalogue/module/document/tests and corrections after
review. Integrator00 owns shared interfaces and integration; Morgan owns scheduling
and ledger reconciliation. Keep the original Worker19 checkout/artifacts intact.
Use the human-authorized Gateway route for the integration packet when direct00
human messaging authority is absent. Transport receipt and reviewer acknowledgment
are separate evidence. Existing mandatory auto_review, denied actions, source-use,
Finland/Frida/native NO-FR, credentials and403 holds remain; production/CIX/DEV7645
remain paused/separately owned. No raw source body was used by this package's tests.
