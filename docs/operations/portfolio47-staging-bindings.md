# Portfolio 47 metadata and staging bindings

This package binds the retained LI/KY/LA/LB **metadata**, not their raw bodies,
to existing develop helpers. It does not create an execution admission or a
production `SourceContract`. Existing partial source scope and accepted LI
private-copy work remain unchanged. The base is
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; integrator00 owns delivery-time provider
verification, independent review and integration. No shared-core file is changed.

## Run the delivered interface

From the repository root, with Python and the existing project dependencies:

```sh
python3 -m offmenu.refresh.portfolio47_bindings --authored-fixture --now 2026-10-18T06:00:00Z
python3 -m offmenu.refresh.portfolio47_bindings --retained-metadata --now 2026-10-18T06:00:00Z
python3 -m unittest discover -s tests -p test_portfolio47_bindings.py -v
```

The first command uses small authored metadata. The second reads **only** the
exact JSON metadata files pinned in `portfolio47_sources.json`, in their existing
Foo locations, plus the committed public-method observation. It does not read,
stat, hash, copy or parse any original workbook, PDF, CSV or dataset. There is no
download, forced refresh, execution-handler registration, credential or AI path.
Output is stdout; callers retain their private evidence separately from source
inputs. Nothing writes an accepted pointer.

`plan(specs, metadata_root=..., now=..., previous_content_sha256=...)` is the
portfolio interface. `metadata_root` is intended for authored fixtures. The CLI
does not accept arbitrary source specs, a config path, URLs or shell commands.
The bundled catalog is source-controlled review input; editing it is a new code
delivery. Catalog changes never install real-source permission.

Each source result has `ready`, `missing`, `held`, `malformed` or `stale` metadata
state and sorted fixed diagnostic codes. Every source is inspected independently;
a held source does not prevent usable peer metadata. Multiple issues remain in
diagnostics even when one state has precedence. `readyFor` is only
`metadata-binding-review-only`: `dataProcessingAuthorized=false`, accepted records
zero, and country completion false in all outcomes.

## Exact source evidence and applicability

The catalog contains eight source declarations across the four countries, with
logical relative metadata filenames, exact SHA-256/length pins, actual retained
metadata locators, scalar JSON pointers and fixed source/release checks. Bodies
are referenced by existing receipt fields only; no new body inspection occurs.
Metadata pins refer to already-authored manifests and receipt evidence, not to a
claim that those metadata files were original datasets.

| Country/source | Source role and native semantics | Remaining typed limit |
| --- | --- | --- |
| LI agriculture361.2023.01.1 | Existing475aggregate crop-area observations; original `Aren` declaration, rounding and table-title evidence. Producer context only. | New staging-scope acceptance missing; no area equivalence, canonical food identity or new private-copy action. |
| LA ATNI2023 | Vientiane product-label benchmark; retained study/count metadata and112versus118conflict preserved. | Request-start time is not completed acquisition; adapted model/use/correction missing. No nutrient or recipe admission. |
| LB CAS August2026 | Statistical index with retained December2013=100 base and source percentage-format evidence. | Receipt-observation time is not completed acquisition; exact2026method applicability/classification and derivative-use unresolved. No item prices/currency inferred. |
| KY S243 | Let’s Eat access metadata | No finite export; actor/export gate remains. |
| KY S356 | Regional CFNI1995 catalog/access metadata | Print-only release not held; not national composition. |
| KY05ab | Registry online-tools access metadata | Paid/account route, no acquisition attempt. |
| KY331f | Registry root access metadata, distinct from online-tools | No finite permitted dataset established. |
| KY737d | Archived recall-programme access metadata | No current finite recall release/use evidence. |

Every country still requires ingredients, recipes, nutrition, retailers/providers,
prices/baskets and dietary references. The output enumerates all six; edges above
are contextual applicability, not trusted `CellRequirement` completeness evidence.
Uncovered categories are not made inapplicable. The new official CAS documentation
observation is in `portfolio47-publisher-docs.json`, with URL/page locators, unknown
edition/current-release applicability and the separate failed reader attempt.
Public documentation access creates no source-data reuse entitlement.

## Provenance and shared qualification

The module reuses `core.strict_json`, `canonical`, `timestamp`, shared singleton
JSONL serialization and `field_origin_errors`. Every scalar under record `data`,
including zero and null, has a pointer-bound source origin or an explicit reviewed
unknown constant. Origins bind the **metadata input** path/hash/selector, not an
unread raw cell. Existing metadata may itself point to raw coordinates; that chain
does not independently revalidate them or establish staging acceptance.

`nativeSemantics` is a catalog declaration with unknowns, not transformed food
data. Units/bases are kept as source context; there is no conversion or canonical
equivalence. The source-specific `SourceContract.semantic_validator`, actual row
schema, independent mandatory-source applicability and exact private staging scope
remain later reviewed inputs.

The tests construct one trusted **authored-fixture-only** `SourceContract` with
independent expected ID/count, input/rights/scope pins and full record schema.
Shared `qualify` validates that singleton output and rejects a unit mutation.
No real contract is generated from an input manifest or fixture registry alias.
No production, country or golden acceptance follows from this test.

## Cache, replay and isolated diagnostics interface

`cacheRequest` keeps original completed acquisition and last validation separate.
The report pins the supplied UTC clock as `evaluatedAt`; acquisition age is an
observation at that clock, not a claim of current publisher freshness.
Generic receipt time, request start and landing access remain unknown acquisition
times. Validation never resets age. The shared `MIN_TTL` is30days. Under30day
metadata eligibility does not prove payload cache bytes; stale inputs report a
review requirement without a download. No force-download interface is exposed.

At this baseline a source-neutral **pure metadata** cache planner is absent:
`core.cache_policy` is Wikibooks-specific, `policy.plan_fixture` requires a
registered fixture, and `CachedAcquirer` is operational and may read/fetch bodies.
This package calls none of those. It emits the explicit
`source-neutral-pure-cache-planner-required` interface dependency while still
delivering all independent metadata bindings. It does not implement a second
cache engine or impersonate another source/fixture.

For replay, pass the preceding `contentSha256`. Shared serialization makes the
same source-bound metadata content deterministic. `unchanged-metadata-no-op`
concerns output content only: pins, timestamps and holds are checked again. A
stale or newly-held input cannot become ready through an unchanged hash. This is
not an actual dataset cache hit, persisted acceptance or a30dayreuse guarantee.

Malformed/duplicate/nonfinite JSON, bad pins/identity/time/selectors, links,
missing inputs, stale acquisition and holds produce fixed isolated diagnostics.
There are at most16sources,8JSONfiles/source,32fields/source and256KiB/file.
Source values and exceptions are not echoed as diagnostics. Tests use only small
authored files and temporary private scratch, with no source-body/network calls.

## Precise shared-interface proposal to integrator00

Reuse the existing00 proposal, not a new implementation here: a pure
`plan_retained_input` interface should take reviewed source/release/content-bundle
identity, original acquisition/revalidation evidence, UTC clock, retention scope
and held/unknown status. It should return zero-network reuse/revalidation intent
and explicit unknowns, without I/O, registry aliases, rights activation or actual
cache-byte assertions. Portfolio `cacheRequest` supplies the evidence fields;
`inputPins` are metadata pins and must **not** be passed as payload cache pins.
An exact payload bundle/rights/custody contract remains required. This proposal
is routed to00 through Gateway; it edits no shared interface and selects no
central implementation. Unsupported real adapters stay unsupported.

Independent review, delivery-time base/provider verification, Morgan’s verdict
and integrator00’s develop integration remain required. Original checkout,
uncertain notifications, source/privacy/Finland/Frida/nativeNO-FR holds,
production/CIX and separate DEV7645 custody are unchanged.
