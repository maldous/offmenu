# Portfolio 15 source-input metadata bindings

Selected task: `M-STAGING-BIND-20261018-W15`. Baseline:
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302` (accepted develop snapshot).
Pending handover/PR42 is not the implementation baseline. No shared core is
changed, no source body is read, and no acquisition or admission is enabled.

## Use

```sh
python3 -B -m offmenu.refresh.portfolio15 --now 2026-10-18T08:00:00Z
python3 -B -m offmenu.refresh.portfolio15 --now 2026-10-18T08:00:00Z --coverage
python3 -B -m offmenu.refresh.portfolio15 --binding owner15-bg-menu \
  --now 2026-10-18T08:00:00Z --previous-build PREVIOUS_BUILD_KEY
python3 -B -m unittest tests.test_portfolio15_binding tests.test_refresh_field_provenance
```

The default command emits one deterministic JSON report per reviewed binding.
`load_catalog()` returns a deep copy of inert packaged declarations in
`offmenu.refresh.portfolio15_catalogue`; it opens no repository resource or
metadata file. The unchanged `docs/source-bindings/owner15.json` is the review
mirror. Both contain identical values; each load returns independent nested
containers. This follows the reviewed PR43 catalogue transport convention and
requires no shared packaging changes.

The catalog contains exact **metadata** paths, SHA256, sizes and JSON pointers;
it is reviewed application configuration, not a discovery/URL input interface.
These Foo-local paths deliberately return `MISSING` elsewhere rather than
downloading, searching for replacement files or following a corpus path.
An unavailable or altered metadata file never silently substitutes a new pin.

`read_metadata(binding, operation='metadata-bind')` opens each fixed JSON metadata
input once through nofollow directory descriptors and a nonblocking nofollow file
descriptor. It refuses nonregular files before reading, caps the returned buffer
at 1 MiB, compares descriptor identity/size/timestamps before and after reading,
and authenticates the actual returned buffer against the declared length/SHA256.
Missing inputs remain missing; other read/custody failures use fixed diagnostic
codes and close owned descriptors. It never verifies one path read and returns
another. The pure
`plan(binding, inputs, now=..., operation='metadata-bind', previous_build=None)`
accepts a map of metadata bytes. Holds and every non-metadata operation are
checked before filesystem or JSON interpretation. It does not write staging,
open a PDF/workbook, run a collector, publish or install a source contract.

## Shared interfaces, not copied country parsers

- `core.strict_json/canonical/digest/safe_path/timestamp`: duplicate-key,
  nonfinite-value, custody, path and timestamp checks.
- `field_provenance.field_origin_errors`: exact per-scalar source/constant
  origin coverage against reviewed input and policy pins. Additional local
  checks compare selected metadata values, country and types; a structural
  provenance pass alone is not a source-content semantic decision.
- `acquisition.MIN_TTL`: the common minimum 30-day interval. This binding never
  constructs or invokes `CachedAcquirer`; its body and rights gates remain
  separate. Metadata age is not proof of cached corpus bytes or HTTP freshness.
- `adapter_mapping.retained_adapters`: report a shared source-family descriptor
  only on an exact source-ID match. None of these PDF/receipt-only source IDs
  is represented as a supported national/product/reference body adapter.

No new shared interface is necessary for the selected metadata-only operation.
Integrator00 may register this portfolio command as a metadata-only caller.
It must not install it as a GLOBAL parse/transform/accept factory. Any future
source-family adapter or `SourceContract` needs a separately reviewed exact
release/format, source semantics, rights, scope and independently expected
record identity/count. Such a change belongs to the existing shared-core owner.
`portfolio_requirements()` reuses shared `assess_cells` for all 24 country/type
cells. With no reviewed actual-source `CellRequirement` and acceptance installed,
all remain explicitly unassessed, including ingredients and other absent types.
Metadata-ready reports cannot fill these cells.

Integrator00 interface result5798 confirms that **no source-neutral pure cache
planner exists at this baseline**. Reports type that capability as
`UNAVAILABLE_AT_ABEC`, and real body-adapter capability as unsupported for this
scope. The age observation below is local metadata diagnostic intent, not a new
shared freshness engine or `core.cache_policy` replacement. A future shared
`plan_retained_input` extension remains proposal-only for Morgan/00.

## Six bindings and their exact scope

| Binding | Country/type applicability | Retained input and unresolved scope |
| --- | --- | --- |
| `owner15-bd-worldbank-78559` | BD, prices/baskets **historical report lead only** | World Bank 2013 receipt; chapter/table, units, basis and private projection grant remain unheld. Not current merchant prices. |
| `owner15-be-europe-bia-paper` | BE, dietary references **research context only** | 2022 European BIA paper receipt; existing method metadata, not Belgian national nutrition or guidance. No score/third-party data rights inferred. |
| `owner15-be-reference47` | BE, dietary references **bibliography only** | Citation of Sciensano2021 `D/2021/14.440/52`; exact citation authors/title/depot/attribution preserved. Cited-report body, acquisition time, custody and use evidence missing. |
| `owner15-bf-insects-denied` | BF, nutrition **denied-response metadata only** | 403 robots receipt, no article original. The timestamp belongs to the retained error response, not an acquired article. Regional workbook/rights remain missing. |
| `owner15-bg-menu` | BG, recipes **document identity only** | National-menu receipt; URL release hint is preserved separately from unknown authoritative edition. No methods/yield/derivative grant. |
| `owner15-bg-agricultural-report` | BG, retailers/providers **report reference only** | 2025 report receipt; no provider-register or composition equivalence. Exact table/use scope remains pending. |

Every source/release name above is a local metadata-binding identity, not a
canonical source admission or publisher identifier. `sourceRecordId=json-root:/`
identifies the pinned metadata envelope; it does not invent a publisher record
key. Corpus-file pins in `sourceAssetClaim` are opaque retained assertions;
`sourceAssetVerifiedByThisPlan` is always false. Existing manifest/receipt pins
are never represented as newly hashed corpus bytes.

Native unit and quantity basis remain explicit `null` unknowns, with policy
origins, for these non-measurement metadata records. Literal IDs/values are not
coerced. Source assertions such as `sourceCompleteClaim` remain assertions, not
country completeness. Country/type applicability is deliberately narrow and
does not fill any whole-country/domain acceptance cell.

## Outcomes and diagnostics

| Outcome | Meaning |
| --- | --- |
| `READY_METADATA_ONLY` | Selected metadata has matching pins, selectors, types, origins and a capture event inside the minimum window. Not body-processing or dataset acceptance. |
| `MISSING` | A selected metadata file/field or original acquisition event is unavailable. Unknown units/bases remain null; they are not invented to pass. |
| `HELD` | An explicit metadata hold or any requested body operation. No filesystem read is attempted for a held operation. |
| `MALFORMED` | Contract, metadata custody, JSON, scalar type, country or clock is invalid. Diagnostics are fixed codes, never source text or credential/header contents. |
| `STALE` | Metadata capture age reaches 30 days. Review is required; the module cannot download or revalidate a source. |

These diagnostics are isolated per binding: one failure cannot suppress the
other reports. The API retains sorted diagnostic codes and stage flags;
source acceptance, golden admission, country completion and network/body-read
counts remain false/zero. Body holds are task/source-operation boundaries,
not a claim that an unknown legal grant can never exist.
Metadata containers are bounded at 64 levels before shared JSON decoding.
Depth overflow returns the fixed `metadata-depth-limit-exceeded` diagnostic;
the per-binding CLI boundary also contains recursion/serialization errors, so
a malformed first input does not prevent a valid second binding's report.

## Cache and replay

Original capture/retrieval time comes from an exact retained receipt selector.
Local validation time is reported independently when evidenced; neither mtime
nor a new hash-validation clock resets original acquisition age. In particular,
BF's response timestamp cannot become an article-acquisition timestamp, and
BEreference47 has no cited-report acquisition event. Metadata freshness cannot
be used to schedule HTTP validation or body reuse.

Reports always prohibit automatic downloading, including under 30 days. They
retain separate acquisition/validation ages and the common minimum interval.
This module does not certify an actual corpus cache, retention permission or
the shared acquirer's HTTP retention logic. Those remain separately contracted.

The build key binds exact metadata values/origins, metadata-manifest pins,
reviewed applicability including its explanatory scope, the complete opaque
source-asset claim, source holds, shared capability/adapter descriptors and the
reviewed cache evidence selectors/meaning. An unchanged binding is `NO_OP` under a later planning clock;
the clock/age observation alone does not change content identity. Changed source
metadata bytes produce a new origin pin/build, even if they describe an unchanged
body. This preserves evidence history rather than silently rewriting provenance.
In particular, a changed source-asset digest or applicability note is
`NEW_BINDING` even when the selected candidate record is otherwise identical.

## Verification and remaining blockers

Small authored fixtures cover valid, missing, held, malformed and stale outcomes;
additional tests cover duplicate keys, overflow, leading-zero IDs, source-country
mismatch, exact field origins, unknowns, future clocks, no-op replay, symlinks and
holds before IO. Shared provenance tests are run unchanged. No legacy source test,
source acquisition, corpus-body processing or production admission is exercised.
One additional authored-fixture test feeds the actual metadata-binding record
through shared `SourceContract/qualify`, including full record schema, independent
ID/count, exact three-file synthetic bundle and shared field-origin callback.
It qualifies fixture scope only and also demonstrates a held contract; no
production contract, `accept` call or accepted pointer is installed.

Actual pinned metadata planning yields five `READY_METADATA_ONLY` reports and
one `MISSING` report (BEreference47 acquisition evidence). All six requested
body operations remain `HELD` before IO. These are binding/diagnostic outputs,
not six processed data releases. Source-specific manifests, rights, actual body
custody, selectors, field semantics and independent acceptance remain typed
dependencies. Raw data stays Foo; Finland/Frida, native NO/FR, 403, privacy,
production/CIX and DEV7645 restrictions are unchanged.
