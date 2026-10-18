# Worker29 retained metadata bindings

Assignment `M-STAGING-BIND-20261018-W29`; baseline develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Owner29 retains FO/ET/FK/FM.

`offmenu.refresh.portfolios.worker29.stage_metadata` consumes explicitly supplied
bytes of one exact retained **metadata receipt/manifest**. It never opens the
recorded paths, source bodies, network or a cache, and never registers a source
or constructs a `SourceContract`. Input pins are trusted code configuration;
release IDs explicitly identify local retained snapshots, not publisher editions.
Source-body hashes are declarations inherited from receipts, not revalidated here.

The four bindings project metadata only:

| Binding | Exact extent | Selectors / provenance | Unknowns and holds |
|---|---|---|---|
| FO IP02006 | Author receipt for 36,153 literal slots | `/counts/observationSlots`, INDEX explicit unit/base | Unit and index base remain null; Q code/M label frequency conflict remains; 4,326 food slots overlap the whole table. No retailer price semantics. |
| ET Table1 | Manifest for 32 label profiles, 160 data cells | `/actualMeasuredCounts` row/dash/blank counts | Label profiles are not nutrient measurements; no quantity units/basis asserted. Sample date unknown; HTML/rights date conflict retained. |
| FK menu | Exact returned currency metadata binding | `/fieldDispositions/*/value` | Currency, fees and effective date stay null. Unknown fees are not zero. Derivative use and current offers unqualified. |
| FM menu | One institutional weekly-menu locator receipt | `/dateHeading/selector`, `/menuTableCount` | Locator only; quantity unit/basis inapplicable. Custodian50 ownership and menu-text use holds retained; heading is not service verification. |

Every emitted scalar has an origin pointing into the exact pinned metadata
receipt, checked by shared `field_origin_errors`. This proves metadata-selector
identity only. It does not claim a new source-cell validation or independent
review. Native unit/base output is explicitly null; the FO projection separately
preserves the receipt's explicit null fields. No conversion or basis inference.
The `UNBOUND` inventory names remaining FO recipes, ET2025 composition, FK
recipes, FM composition and FM recipes. No country or corpus is complete.

The caller supplies UTC `now`, optional validation timestamp and additional
holds. FO's original acquisition time is pinned from retained metadata; other
original times are explicitly unknown, never substituted with manifest generation
or validation time. Both ages remain separate. Ages are diagnostic observations,
not cache eligibility. `cacheDecision=shared-pure-planner-required` exposes the
existing integrator00 dependency: shared `core.cache_policy` is source-specific,
`policy.plan_fixture` requires a registered fixture, and `CachedAcquirer` performs
filesystem/body operations. No country cache engine is copied or patched here.

Outcomes are `ready-metadata`, `no-op`, `held`, or `invalid`, with sorted isolated
diagnostics (including missing, malformed and stale-input pin mismatch). Errors
and stage holds discard the entire projection. Downstream holds always remain.
A prior successful `receiptSha256` yields no-op for an unchanged contract and
projection; validation timestamps and observation time do not change that key.
That key is not an acceptance receipt. Caller owns retention of prior successful
receipts. Outputs always state zero body operations, network and admitted records.

Example (caller already possesses authorized metadata bytes):

```python
from offmenu.refresh.portfolios.worker29 import BINDINGS, stage_metadata
result = stage_metadata(BINDINGS['fo-ip02006'], supplied_metadata_bytes,
                        now='2026-10-18T00:00:00Z')
```

Run `python3 -m unittest tests.test_worker29_staging tests.test_refresh_field_provenance -v`.
The tiny fixture is authored synthetic metadata, not copied country data. Tests
cover zero/null distinction, shared provenance failure, exact pin and selector
rejection, malformed/duplicate/nonfinite JSON, bounds, holds, original/validation
ages, deterministic replay and absence of implicit filesystem access. Independent
review and develop integration remain required; no gold admission, public-use
permission or production/CIX/DEV7645 change follows from passing these tests.
