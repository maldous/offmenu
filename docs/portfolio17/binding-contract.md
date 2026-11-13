# Worker17 NZ/SI/SY/UG metadata binding package

This package binds **permitted receipt JSON**, not publisher payloads, to the
shared develop contracts at `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
It does not register an acquisition, enable an adapter, read referenced bodies,
normalize source data, or grant rights/acceptance. PR42 is not a dependency.

## Repeatable interface

From this checkout, with an explicit validation clock and an output outside the
metadata root:

```sh
python3 -B -m offmenu.refresh.portfolio17 \
  --bindings docs/portfolio17/bindings.json \
  --metadata-root /absolute/private/metadata-root \
  --now 2026-10-18T00:00:00Z \
  --output /absolute/owned/output/portfolio17-diagnostics.json
python3 -B -m unittest discover -s tests -p test_portfolio17.py -v
```

The trusted portfolio configuration lists nine exact receipt pins and literal
RFC6901 selectors. Only explicitly declared relative `.json` metadata paths
marked `metadataOnly:true` can be opened. Paths must have no links or traversal.
The root and configuration are caller-selected trust boundaries; the flag or
filename alone cannot make an arbitrary JSON dataset permitted metadata. Review
any new config before use. Referenced PDF/CSV/HTML paths inside receipts remain
literal values. No network transport or historical collector is invoked.

The `--bindings` reader opens with nonblocking/no-follow flags and checks the
opened descriptor is a regular file before reading. Reads are capped at1MiB;
oversized, nonregular, failed and observably changing configuration reads fail
with typed `binding-config-*` errors before evaluation or output replacement.
Descriptor size, identity and modification/change times are checked across the
read. This is a stability check, not an immutable concurrent-write snapshot.
This correction qualifies the configuration-reader boundary only; the separate
metadata/output readers and remaining00batch invariants retain their own review.

The total evidence read budget is 1 MiB per evaluation (including repeated
references), at most 32 bindings/16 evidence files per binding. Outputs contain
metadata and manifest references, never copied payload bodies. They stay on the selected local executor.
Metadata values are limited to depth64 (root depth0), checked iteratively before
recursive provenance traversal. A deeper value or recursion failure returns
`metadata-depth-exceeded` for that binding and leaves later peers evaluable.

The output must have its own inode: an existing output with multiple hard links
is rejected before reading or writing it, including aliases of metadata or the
binding configuration. Changed output is written to a temporary sibling and
replaced as a directory entry, so writing never truncates the old output inode.
An identical ordinary output remains untouched.

## Shared contracts and origins

- `core.strict_json`, `canonical`, `timestamp`, `safe_path`, `sha` reject ambiguous
  JSON, provide deterministic bytes, validate UTC timestamps and scope paths.
- `field_provenance.datum_pointers/field_origin_errors` cover every scalar datum
  against exact metadata pins. These are **receipt-field origins**, not claims
  that publisher table cells have been compared or accepted.
- `adapter_mapping.retained_adapters()` resolves only exact shared source/release
  descriptors. No country-specific parsing engine is copied. The authored valid
  fixture resolves the existing FOODfiles2024-v01 descriptor; the selected nine
  real evidence bindings do not thereby become FOODfiles payloads or executable.
- `acquisition.MIN_TTL` supplies the shared minimum 30-day rule. No acquisition
  functions or mutable shared registries are called/edited.

Each entry returns a candidate metadata envelope, content hash, shared descriptor
when exactly applicable, typed diagnostics, existing holds and named missing
inputs. Null units/bases/record selectors are policy-origin explicit unknowns,
never guessed from a report name. Empty original lists remain empty.

`valid-metadata-binding` means this metadata interface and authored evidence
contract are complete; it never means source-stage eligibility. Every result
sets `sourceStageEligible:false`, `datasetAcceptance:false` and `goldAdmitted:false`.
`held`, `missing`, `malformed` and `stale` entries remain isolated from peers.
Malformed JSON, wrong pins, missing fields, future timestamps, unsafe paths and
budget errors are fixed diagnostic codes, without source content/exception paths.
Top-level malformed configuration fails without a new output. There is no repair,
skip-and-admit or publisher-format inference.

## Acquisition time, reuse and no-op

`originalAcquisition` is an exact metadata selector for the original retained
document's acquisition timestamp; validation time never replaces it. Missing
originals keep acquisition time unknown rather than using receipt-check time.
Each entry declares whether acquisition concerns a document, metadata or failure.
No filesystem mtime is used. Before30days the planning decision is cached reuse
with **zero downloads**; at/after30days it is stale-input review with **zero
downloads**, not a network instruction. There is no force-download option.

`retentionEvidence` is an evidence locator, not a parser-issued legal approval.
All production config entries leave it unknown and preserve their source holds.
A readable snapshot is not proof of permission for30day dataset reuse. The
authored fixture's retention string concerns fixture metadata only.

`candidateSha256` excludes validation age/time; revalidation cannot change the
source/release content identity. The diagnostics include the caller's clock.
Same inputs/config/clock produce byte-identical diagnostics; the CLI leaves an
identical output untouched. A changed clock can update diagnostics while keeping
the unchanged candidate hash. This is metadata replay, not payload refresh.

## Portfolio evidence and remaining inputs

| Binding | Actual selected evidence | Remaining processing boundary |
| --- | --- | --- |
| NZCheapEats | retainedMay2025 receipt/PDF-manifest references | Private extraction/use/retention/attribution and recipe selector held |
| SIrecipe | English02June2021 receipt-declared book | Actual source custodian, edition and use/selector grant unresolved |
| SIstatistics | DocSysFile14458, September2025 receipt | Issuer/edition/use/field/notes selector unresolved |
| SYWorldBank | catalogue4507 HTML metadata only | Exact retained CSV/field map/rights and retention binding absent |
| SYWFP | April2025 HTTP403, no original | No retry or alternative actor |
| UGHarvestPlus | 2012 composition rights/catalogue receipt |43attests metadata custody; no permission/original/table selector |
| UGUSAID | 2015-10 failure metadata |44attests no original/use/selector; DNS no-retry |
| UGUBOS | July2026 failure metadata |44attests no original/use/selector; TLS no-bypass |
| UGUNBS | cached certified-systems manifest,110declared rows | Primary licence review and company/scope field selector held |

All six country types stay open: ingredients, recipes, nutrition,
retailers/providers, prices/baskets and dietary references. Type routing identifies
the intended metadata role, not national coverage or semantic equivalence.

Prior official SY metadata evidence: catalogue
<https://microdata.worldbank.org/catalog/4507> and dictionary
<https://microdata.worldbank.org/metadata/export/4507/json>, file
`SYR_2021_RTFP_MKT`, edition2025-11-24. This describes market estimates and does
not supply local rows or an exact source-use licence in the retained receipts.
Missing unit/basis/rights evidence remains explicit rather than inferred from
general WorldBank terms. No missing public documentation is treated as an access
denial; no permission is asserted from public landing access.

## Integration boundary

Only `portfolio17.py`, its tests and this portfolio configuration/document are
owned here. Shared core, schemas, runtime, registries and acquisition controls are
unchanged. Integration00 should independently review these bytes on the pinned
develop baseline and reconcile the current develop head before integration.

Interface request for00: a future generic source-input metadata-contract facade
could expose the same pinned evidence/field-origin/clock diagnostics for source
families absent from `retained_adapters`. No shared change is required to run this
package, and no new payload family/admission is requested by this code. Actual
source work needs a separately selected input/use/field-origin contract and
independent acceptance. Finland/Frida, nativeNO/FR,403/private/custody holds,
production/CIX and the separate DEV7645 custodian remain unchanged.

### Consolidated interface receipt5798

The shared baseline has **no source-neutral pure cache planner**. This is an
`unsupported-shared-capability`, not a reason to block the metadata bindings.
The age arithmetic above is portfolio metadata diagnostic/reuse intent only.
It does not call the Wikibooks-specific `core.cache_policy`, registry-only
`policy.plan_fixture`, or operational `CachedAcquirer`. It does not spoof a
source/fixture identity to enter those paths. The FOODfiles authored test merely
checks an exact existing descriptor; no registry, acquisition or admission is
patched. `SourceContract/qualify` remains available for compatible authored
payload fixtures, but receipt metadata is not presented as such a payload.

The baseline/interface receipt5798 and its late-dependency addendum confirm
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302` as the selected proposal snapshot;
local4693cbc/5f5bdb6 refs are older ancestors. Integration00 must reverify live
provider/candidate/base at delivery gates. A later generic pure planner, if
the product maintainer selects it, belongs to00/shared-core ownership. This package neither
implements that shared extension nor makes held real inputs wait for it.
