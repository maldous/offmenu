# Worker56 retained metadata staging bindings

Base: verified develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
Only ES/NI/TK/WF configuration, an additive portfolio module and its authored
fixtures are owned here. No shared engine, source contract, registry or acceptance
policy is changed. Pending PR42 is not a dependency or accepted develop.

## Runnable interface

From this checkout, on the selected local executor:

```
python3 -m unittest tests.test_portfolio56 -v
python3 -m offmenu.refresh.portfolio56 \
  --config config/portfolio56/retained-metadata.json \
  --now 2026-10-18T08:00:00Z \
  --output /absolute/private/new-output-directory
```

The CLI reads **only the eight pinned JSON metadata files**, never a source body,
PDF, CSV, workbook, URL, historical collector or linked artifact. A source path
inside a receipt is not followed. No networking, AI or adapter execution exists.
Local absolute paths are intentional custody locators, not portable raw archives.
On another host these inputs are missing, not grounds for downloads.

Every input yields one isolated outcome: `ready-metadata-candidate`, `missing`,
`held`, `malformed` or `stale-input`. Missing files, bad JSON, changed digests,
unknown selectors, mismatched declared releases, exact holds and acquisition age are
reported without suppressing an independent source's result. Candidate packets
are *metadata* only, never dataset rows, canonical resources or admissions.
Absent real-source adapter capability is separately typed and does not block an
otherwise valid metadata-only candidate. No source/fixture identity is borrowed
to invoke a generic cache planner. The current real bindings all remain held and produce zero candidate rows.
A cleared configuration flag cannot create a trusted SourceContract or authorize
any stage. Actual staging needs code-owned, independently reviewed contracts and
source-specific operation rights through the shared acceptance interface.

The package reuses shared `strict_json`, UTC `timestamp`, canonical hashing,
`field_origin_errors`, retained adapter descriptors and singleton JSONL
serialization. Each emitted scalar, including zero/null, points to the precise
JSON selector in the pinned metadata. Dataset cell/page selectors are explicitly
unknown; receipt selectors cannot be substituted for them. Native units/bases
remain null; compound units, statistical weights, recipe yields and dietary roles
are never inferred. No English label or source owner number establishes identity.

## Actual retained applicability and remaining blockers

| Country/source | Proposed domain context only | Binding restriction |
|---|---|---|
| ES composition catalogue | ingredients/nutrition | Catalogue only; exact release/use absent; no403 retry |
| ES MAPA REGOE | providers | TLS failure; no retry/security bypass; no provider records |
| ES Cervantes | recipes | 403 challenge; complete recipe selector/use absent |
| NI BCN partial metadata | prices/baskets | Methodology prefix; actual release/custodian/use absent; no challenge retry |
| TK SPC regional publication | recipes | Printed edition, Tokelau association, complete recipe/notes selector and private derivative credits/use absent |
| TK fisheries report | providers | Report is not a producer registry; field scope/use absent |
| WF economic annual report | prices/baskets | Exact caption/pages/rows, period/index base/units/use absent; not BQP export |
| WF landing | prices/baskets | Landing metadata, not a dataset |

Configuration binds exact acquisition receipts/manifests and previously retained
validation/gap artifacts. The six required data types are listed for each country;
an absent type is a missing requirement, never not-applicable. This package neither
repeats the earlier body checks nor supplies missing dataset applicability or
independent acceptance. No source body acquisition is newly permitted. These
source facts already have exact retained evidence; no public research is needed
to reinterpret an explicit denial or evade a no-read restriction.

## Cache, replay and diagnostics

`--now` is explicit UTC. The selected acquisition timestamp belongs to the pinned
metadata/failed-response observation; it does not prove an underlying dataset was
acquired. Filesystem mtime and later verification timestamps are ignored for age.
Under30 days the policy returns `reuse-retained-no-download`; at or after30 days
it returns `conditional-review-required-no-download`. There is no force-download
flag. No decision ever performs a request or grants retention/reuse rights.

The build key includes metadata pins, portfolio field selectors and restrictions,
module contract version and implementation digest, output status/diagnostics and candidate content digest.
Changing only the policy clock within the same cache gate leaves candidate bytes
and identity unchanged; crossing30 days cannot reuse a previously ready artifact.
A repeated run verifies its cached candidate hash, build key and stable plan fields, returns a no-op
without modifying output bytes, and reports the current in-memory acquisition age.
The original `plan.json` timestamp/age remains a historical validation observation;
it is not rewritten to look newly acquired. Changed/tampered outputs require a new
isolated directory. Incomplete output directories fail rather than being deleted.

Fixtures are small authored metadata objects in `tests/test_portfolio56.py`.
They cover valid/missing/held/malformed/stale, null/zero/literal preservation,
source origins, duplicate identities/JSON keys, acquisition versus validation age,
30-day edge, no-op, tamper detection, symlinks and refusing body paths before IO.
A code-owned authored-fixture SourceContract also exercises shared qualify with
exact input/candidate pins, schema, field-origin callback, count/ID and held
controls. This qualification is fixture-only, not independent approval.
They do not import NO/FR/Finland/Frida engines, run old source tests, grant rights,
qualify a real parser or prove whole-country completion. Independent review and
normal develop integration are still required; golden promotion is later.

## Proposed shared-interface request to the product integrator (no core edit here)

The generic `core.cache_policy` is currently a specific Wikibooks pilot and
`policy.plan_fixture` requires a registered fixture. Neither is advertised as a
source-agnostic production gate here. Please review a future code-owned
source-neutral cache-decision interface with exact release/input identity,
original acquisition time, explicit UTC clock and operation rights, returning
under30-day no-download / conditional-review with no side effects. This package
has only a portfolio metadata policy; it does not install that shared interface.

Actual dataset integration must additionally supply an existing shared adapter
with a compatible retained release and a trusted SourceContract covering schema,
independent count/IDs, semantic unit/basis checks, input custody, rights, source
field origins and intended output scope. Do not construct one from this config.

## Current official documentation check

The [IEOM legal page](https://www.ieom.fr/Mentions-legales?lang=fr) describes
personal-use copying, short attributed citation and restrictions on other
electronic reproduction/archives. It does not establish the proposed WF data
transformation/cache entitlement. Source-specific holds remain. The attempted
SPC terminology disclaimer returned403; it was not retried and is not a cookbook
licence. `config/portfolio56/public-documentation.json` records this limited
research; no retained report/book body was opened or publisher contacted.

## SAME45 reader correction (review6504)

The original c49 candidate remains changes-required pending SAME45 delta review.
Local metadata/config reads (2 MiB maximum) and replay-plan/candidate reads
(256 MiB maximum per file) now use one bounded nonblocking/no-follow descriptor.
The opened regular inode must match the checked inode before any read; directory
components are anchored by descriptors and checked for identity/no-follow.
Single-link regular files only; FIFOs, devices, directories, symlinks, hardlinks,
oversized or changed objects reject. Post-read inode/size/time/link identity and
consumed size must remain consistent. Empty replay candidates remain valid for
held-only plans. Caller config is JSON-only and shares this ingress; it cannot
select a non-JSON body path. These checks do not claim an OS sandbox or grant use.

`python3 -m unittest tests.test_portfolio56_reader_delta -v` runs only the new
F1/F2 authored regressions and fresh positive controls. FIFO probes run in child
processes with a two-second kill/reap fallback. No real metadata/body source,
old author16 suite, shared batch or prior review suite is replayed. Original
configuration/evidence and acceptance boundaries remain unchanged.
