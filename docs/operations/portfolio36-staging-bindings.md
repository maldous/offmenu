# Worker36 MU/SV/TN/VA source-input bindings

This metadata/code successor is based on accepted develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. Pending PR42 is not used.
It stages source-input **metadata evidence**, not normalized source records,
source-use permission, dataset acceptance or golden data. All 24 portfolio
country/domain cells remain unassessed by the shared `assess_cells` contract.

The five reviewed bindings in `config/source-bindings/owner36.json` are:

| Country/type | Retained scope | Still withheld |
|---|---|---|
| MU recipes | University Mauritius September2023 receipt and returned-use evidence | Adaptation entitlement, exact author credit, recipe quantity/yield selectors |
| SV prices/baskets | ONEC/BCR historical2001–2026 query receipt and source-methodology field bindings | Numeric month/cell validity, semantic source-scope acceptance |
| TN prices/baskets | INS2021 expenditure workbook receipt | Actual units/basis, release/use/attribution decision |
| TN dietary references | UNICEF infant/young-child toolkit receipt | Edition, permitted use and population/page acceptance |
| VA retailers/providers | Museums selfservice description receipt | Itemized release, serving/price units and derived-use evidence |

Every pin is a JSON **metadata** file. `evidenceReferences` preserve its original
Foo path and hash; `inputs` bind an exact portable filename, size and hash.
The source original paths appearing *inside* receipts are never followed.
No raw body is bundled in Git. The authored test fixture contains no source data.
No public documentation gap blocks this metadata-only implementation; publisher
use and payload-format questions remain typed blockers, not licence conclusions.

## Repeatable invocation

An integration/receipt owner places the exact seven permitted metadata snapshots
under the filenames in `inputs`, in a private Foo directory. No acquisition or
body extraction is involved. There is no CLI override for the reviewed binding
configuration, dynamic plugin, source URL, source parser or force-download mode.

```sh
python3 -m offmenu.refresh.portfolio36 \
  --metadata-root /absolute/private/metadata-snapshots \
  --workspace /absolute/private/binding-output \
  --now 2026-10-18T06:00:00Z
```

The clock is explicit UTC so a run can be reproduced. The generated
`binding-manifest.json` records metadata-only records, field origins and unknowns;
`diagnostics.json` records individual source outcomes. These are not the native
`candidate.jsonl`/SourceContract manifest shape. An old valid manifest is preserved
on a later input failure, but `manifestPublished=false` and current diagnostics
control the outcome. It must never be treated as a fresh dataset acceptance.

`offmenu.refresh.acceptance.fingerprint`, `assess_cells`, the shared
`field_origin_errors`, and core `strict_json`/`verify`/path/atomic helpers are
reused. All scalar fields, including explicit nulls, bind exact JSON pointers and
input digests. No absent unit, field or value is synthesized. Source-value shape
and literal expectations are checked; metadata provenance is not proof that
the underlying source-cell semantics have been independently accepted.

Accepted develop has **no source-neutral pure freshness planner**. This package
does not call Wikibooks `core.cache_policy`, fixture-registry `plan_fixture`, or
the operational/body-reading `CachedAcquirer`. It reports receipt age only,
`sharedPlannerCapability=unsupported-source-family` and
`cacheEligibility=not-evaluated-no-download`; no second planner is installed.
Original acquisition time comes from the reviewed receipt-bound configuration.
`validationAt` remains a separate assertion and never resets acquisition age.
The CLI has no download path at any age. At30days the source reports `stale-input`
with `conditional-revalidation-not-selected`, still zero network. No refresh or
revalidation function is invoked by this package. Retention/revocation/rights
restrictions take precedence over any later operational cache policy.

Unchanged metadata/policy yields byte-identical manifest content and
`verified-no-op`, including across a new validation time or stale boundary.
Diagnostics may change with the explicit evaluation clock. A changed policy or
metadata pin produces a different manifest. No accepted pointer is changed.

## Diagnostic and execution boundaries

The source outcomes are `metadata-ready`, `missing`, `held`, `malformed`, and
`stale-input`. Healthy peers retain their diagnostics/metadata records when
another source fails; complete manifest publication is withheld on missing,
held or malformed sources. The CLI exits2 for those isolated failures or an
invalid command/configuration, and0 for a written/no-op metadata manifest.
Stale metadata is preserved as evidence, not eligibility for payload execution.

The portfolio caller uses its own nonmutating `flock` boundary: an opened lock
descriptor must be regular, single-linked and still name the same inode. It
never truncates/writes lock contents. An existing replay manifest is opened
nonblocking/no-follow, checked as regular on that descriptor, read at most8MiB
plus one sentinel byte, checked for identity/size/time stability and validated
as the prior metadata-manifest JSON shape. Invalid/oversized/nonregular prior
artifacts are rejected without replacement. These caller guards correct
W19-W36-F1/F2; shared core and its other callers remain unchanged.

The fixed configuration permits at most32 sources,8JSON metadata inputs/source,
1MiB/input and64 scalar fields/source. Reads are bounded and checked against
the bytes actually parsed; symlink/traversal paths are rejected. Diagnostics
contain fixed codes rather than raw exception paths or source values. The runner
is offline, no-AI, synchronous and source-isolated at the diagnostic level;
it is **not** a new OS sandbox or production parser runtime. Any future source
operation must use the existing reviewed execution/resource boundary.

Tests exercise authored valid/missing/held/malformed/stale cases, exact/null
origins, literal drift, duplicate JSON keys, nonfinite numeric overflow, UTC/time
errors, corrupt pins, no read under holds, safe paths, no-op behavior and failure
isolation. A separate authored metadata candidate is checked by the shared
`SourceContract`/`qualify` path with `fixture=True`; no real SourceContract or
production admission is installed. Shared core files are unchanged.

## Integration request to00

No shared-interface change is required for this metadata evidence package.
Review/integrate the five owned paths and invoke the module explicitly; do not
auto-register it as a payload adapter or set any source admission. Proposal for00
only: a pure `policy.plan_retained_input` taking reviewed source/release/bundle
identity, original acquisition and revalidation metadata, UTC clock and
retention/hold status; it would return zero-network intent and explicit unknowns,
never execution/rights/admission. No such public API currently exists and none
is invoked here. See integrator result5798; Morgan selection and independent
review are required for any shared implementation.

Source processing, independent semantic approval, country acceptance and golden
promotion remain separate. Morgan selects the next request after independent
review and develop integration. Finland/Frida, NO/FR native-crash, actual-denial,
privacy, production/CIX and DEV7645 holds are unchanged.
