# PF / SL / TF / UY retained metadata bindings

M-STAGING-BIND-20261018-W24. Baseline: reviewed develop snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302` (PR41). Pending PR42 and its
reproduced P2 are outside this baseline. No shared core edits.

Run from the repository:

```sh
python3 -m offmenu.refresh.worker24_bindings --now 2026-10-18T00:00:00Z
python3 -m unittest discover -s tests -p test_worker24_bindings.py
```

The CLI loads the inert `worker24_catalogue.BINDINGS` module included in wheel
and sdist builds. Its literals exactly match the retained `bindings.json`
document; runtime loading does not depend on that repository document.
Embedded absolute evidence and
candidate paths are local executor custody pointers, never opened by the CLI. The report
does not certify current asset availability, bytes, rights or data acceptance.
The original immutable candidates/manifests remain unchanged. This metadata
package installs neither a production `SourceContract` nor GLOBAL handlers.

Default tests read only committed authored metadata fixtures. They resolve the
`tables` pointers, reject the old `members` pointer and reject declaration or
evidence-hash drift. Private local executor files are not required by test discovery.
For an explicit check of the actual eleven PF/UY metadata evidence pointers on
local executor, separately run:

```sh
python3 -m offmenu.refresh.worker24_metadata_diagnostic --foo-metadata
```

The `--foo-metadata` spelling is a retained compatibility flag for an explicit
local metadata diagnostic, not a dependency on a named host or external service.
This diagnostic follows only pinned metadata evidence paths. It checks their
hashes and the declared filename, digest, size, headers and release version;
it never opens the source/candidate body paths inside those documents. Missing
private metadata returns an unavailable diagnostic and exit2. This command is
an opt-in custody check, not a default test or payload validation.
Its metadata reads use nonblocking, no-follow, read-only descriptors, reject
nonregular or oversized files and verify descriptor/path identity, size and
timestamps across the read. An unavailable, replaced or changed file returns a
typed diagnostic. The reader never opens an output file or changes input bytes.

`bindings.json` pins existing metadata receipts, PF's ten individual member
versions/hashes/headers (556 prior lexical records), and UY's product resource
version/hash/headers (379 prior lexical records). It does not copy product rows,
establishment records or raw datasets. PF retains release identity separately
per member; its umbrella name is not a publisher release ID. UY's product
resource version does not establish applicability of price descriptors to2025.
Counts are historical receipt claims, not new validation results.

`origin_template` maps ordered lexical cells to exact retained header selectors,
input digest, member release and caller-supplied source record locator. The
caller must independently verify actual source coordinates and values before
staging execution. Authored fixture checks reuse shared
`field_provenance.field_origin_errors`; serialization, strict JSON and UTC time
validation reuse shared refresh core helpers. No parallel country parser exists.

All native unit/basis fields remain null where per-cell units are not reviewed.
Source titles and headers remain literal; tonnes, hectares or product labels
do not become nutrients, serving bases, canonical identities or market joins.
Empty lexical strings and zero strings remain distinct. Actual candidates are
not passed through these fixture helpers in this task.

The metadata planner separates original acquisition and later validation times.
Missing original acquisition evidence blocks freshness claims; file mtime,
release publication date and receipt-validation time cannot substitute for it.
Below30days it proposes retained metadata reuse. At30days it requires review
without download. There is no force option or network implementation. Content
identity excludes these observation clocks; unchanged metadata reports a no-op
while freshness is independently reevaluated. This is not a payload cache or a
claim that an operational30-day source-refresh lifecycle has been accepted.

Diagnostics are per-profile (`missing`, `held`, `malformed`,
`stale-review-required`, `reuse-metadata-only`). One profile's failure preserves
peer outcomes. `metadataNoOp` binds only configuration content. No report implies
qualification, reviewed records, gold admission or country completion.

## Remaining dependencies and integration request

| Dependency | Type / current owner | Next action |
| --- | --- | --- |
| PF/UY original acquisition timestamps and custody evidence | Missing input; original custodians24/47, selected through the product maintainer | Supply exact retained acquisition metadata, not a new download or guessed date |
| Actual cell-coordinate semantics and native staging schema | Review/contract; the product maintainer designated reviewer + integration00 | Review exact lexical-only scope and configure trusted `SourceContract` before any real row processing |
| Shared fixture-independent refresh planner hook | Shared interface; integration00 | Expose trusted source/release/input-key acquisition planning with explicit clock, no force bypass under30days, isolated diagnostics; existing `plan_fixture` is fixture-registry-specific |
| PF non-agricultural/IEOM and other country types | Source-use/applicability; the product maintainer + source owner | Supply operation-specific evidence; current metadata does not expand use |
| UY price body/allocation, date/schema join, composition release/rights | Missing input/authorization/source-use;47/45 via the product maintainer | Select exact metadata resolution; no2GB price acquisition or joins in this task |
| SL403 | Explicit denied route; the source owner | Preserve no retry; qualified evidence through existing owner only |
| TF report014873-01 exact section, max2pages, attribution and policy403 | Source-use + denied route; the source owner | Supply exact permitted section/use evidence; no report read or alternate route |

Proposed integrator interface is a successor request, not an installed core
change: `plan_retained(contract, acquisition_evidence, now, previous_content_key)`
should accept trusted reviewed bindings without admitting sources, retain input
hash/custody checks in the existing execution/acceptance boundary, and keep
original acquisition time independent of validation. This package deliberately
does not clone shared cache, parser or acceptance engines to fill that gap.

All six requested country types remain unaccepted in all four countries.
No new source downloads, raw-body reads, production/CIX/DEV7645 changes,
rights expansion, credential changes or held-route retry occurred. Independent
approval and develop integration are required before the next request.
