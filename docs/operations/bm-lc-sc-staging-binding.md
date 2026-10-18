# BM / LC / SC retained metadata binding

Selected request: `M-STAGING-BIND-20261018-W11`. Base is accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This package owns only
`offmenu/portfolio_bm_lc_sc.py`, `config/portfolios/bm-lc-sc.json`, its authored
fixture/tests and this document. No shared refresh implementation is changed.

Run from the repository on Foo, using an explicit UTC validation clock:

```sh
python3 -m offmenu.portfolio_bm_lc_sc --now 2026-10-18T06:00:00Z
python3 -m unittest discover -s tests -p test_portfolio_bm_lc_sc.py -v
```

The CLI reads only eight exact pinned JSON metadata receipts from the reviewed
configuration. It never follows receipt body paths, staged-projection paths,
publisher URLs or arbitrary user paths. It emits deterministic JSON to stdout;
exit 2 means at least one missing/held/malformed binding. Nothing is written
to a cache or staging directory. This is a proposed source-input metadata envelope,
not an adapter that extracts recipes or menu/price values. The existing generic
`field_origin_errors`, strict JSON, canonical serialization, timestamp/path guards
are reused. No country engine is copied. The metadata reader descends through no-follow directory descriptors, opens the final descriptor nonblocking, checks regular-file/type/size, and verifies stable descriptor identity/size around its bounded read. A FIFO or special file returns a fixed isolated error before the next peer. This guard is for local Foo files, not an OS sandbox or network-filesystem timeout promise.

`assess(binding, raw_metadata, now=..., previous_key=...)` is the pure interface
for reviewed callers and authored tests. `run` isolates failures by binding;
one malformed or inaccessible receipt cannot suppress other diagnoses. Supplying
custom bindings to that Python interface is a code-custody responsibility; the
CLI has no config/path/URL/rights/force override. It does not create a trusted
`SourceContract`, install a registry entry, produce accepted counts or enable any
source operation. No claim of an OS sandbox follows from these interfaces.

## Evidence and applicability

The config pins source receipts and previously frozen validation manifests.
`retainedBodyReferenceOnly` records historical custody, never a fresh body hash
verification. Source release IDs identify exact retained metadata snapshots;
publisher release labels remain distinct from independently qualified editions.
BM covers recipe/ingredient references, seven dated offer references, one dietary
poster and CPI metadata; LC covers the ministry collection-page record; SC covers
three venue/edition menu receipts. None proves national/category completeness.
The six required country types remain explicit; unrepresented types are missing,
not inapplicable or accepted. SC menus do not stand in for recipes or composition.

Every selected metadata scalar has an exact receipt JSON pointer, input digest,
source/release identity and origin declaration checked by the shared validator.
BM's existing staged projection pins additionally declare the future yield,
price/currency/package/basis/citation coordinates. They are held declarations,
not executed transforms. Yield items are separate from servings; unknown currency,
nutrients, conversions and units remain unknown. LC has no book field declarations;
SC has no parsed menu field declarations. No invented body locator or canonical
equivalence fills those gaps.

No publisher documentation lookup is needed to interpret these metadata fields.
Existing source-specific rights restrictions are the blockers, not lack of access
to an internal custodian. BM stays private inspection only, LC's edition-bound
grant was explicitly not held in the declared source-record scope, and SC lacks
an adaptation/redistribution grant. Public landing/download access and unrelated
CC0 directory metadata do not clear those operations. Rights-holder/source scope
acceptance remains a separate Morgan-selected step. No new legal determination
or universal prohibition on every possible use is asserted.

## Acquisition clock, replay and diagnostics

LC `/requests/0/finishedUTC` evidences the original HTML response completion.
Other recorded observation/finalization timestamps are declared separately; this
binding leaves original completion unknown until its exact meaning is qualified.
Validation time and filesystem mtime never fill that field or reset its age.

The controlling contract still requires minimum 30-day reuse, but accepted develop
has no generic pure cache planner. This binding therefore always reports
`plannerCapability=unsupported`, `decision=unknown-no-download` and
`downloadAllowed=false`, regardless of observed age. It does not classify input
as fresh/reusable/stale or choose revalidation eligibility. It retains the original
clock and observed acquisition age solely as evidence. Missing/held/malformed
inputs cannot produce a metadata envelope. Old authored metadata can produce a
metadata-only envelope or replay hint, never a cache-eligibility or source-use
verdict. The caller must retain the explicit unsupported cache capability.

The key pins the complete binding and metadata digest, but excludes the current
validation clock. Identical valid inputs return `unchanged-no-op` when the caller
supplies the prior key; no transform or publication occurs. This is a deterministic
preflight/no-op **interface**, not a new persistent cache engine. Existing shared
cache/execution adapters remain responsible for future reviewed staging. The
current generic `policy.plan_fixture` is fixture-registry bound and
`core.cache_policy` stamps Wikibooks identity; neither is misrepresented as a
production BM/LC/SC lifecycle. No refresh path is installed by this package.

Diagnostics are fixed codes, accumulated where independent and isolated by input.
They never echo exception details, paths or arbitrary source values. Authored
fixtures cover valid origins including explicit null, missing bytes/coordinates,
closed use, bad pins/JSON/selectors/clocks, unknown cache capability across age
boundaries, replay with changed holds, nonregular reader/peer progress, descriptor
cleanup, failure isolation, and absence of body/network I/O. Passing those fixtures
does not qualify any real source or country.

## Integrator00 interface proposal and remaining gates

No shared edit is necessary to review or run this metadata preflight. Proposed
future shared addition, for integrator00 only: extract a source-neutral, pure
cache-evidence planner accepting reviewed source/release/content identity,
original acquisition UTC and later validation UTC, with the existing minimum
30-day policy, zero-download return, no force bypass, and fixed diagnostics.
Keep source-specific bindings as callers. This package does not implement a
shared policy change or appoint its acceptance reviewer.

Before real staging: supply exact source-operation rights, qualified original
acquisition clocks where missing, complete retained input/scope manifests,
source field dictionaries/native units/bases and per-datum semantic acceptance,
then select a compatible shared parser/factory and independent review. Exact
source locks and all no-body/denial/Finland/Frida/NO-FR crash restrictions survive.
Golden promotion, country acceptance, production/CIX and DEV7645 are separate.
Independent approval and integrator00's normal expected-head develop integration
must complete before this worker's next request.

## Correction to reviewed predecessor 902d7310

W14-W11-P2-READER: reused the exact-applicable W06 qualified FIFO failure and
its reviewed nonblocking/no-follow/regular-fd boundary; no predecessor FIFO hang
was reexecuted. The owned successor adds authored FIFO/regular-peer and reader
cleanup regressions. W14-W11-P2-POLICY: the local MIN_TTL cache-decision branch is
removed. The policy fingerprint changes; original clocks/content replay remain,
while cache planning is explicitly unsupported at every age. Configuration and
fixture metadata stay byte-identical. Repository-only runtime scope remains:
installed-resource adoption would need a separately selected packaging correction.
Original reviewer14 must independently check this delta; no author closure claimed.
