# Worker 45 source-input metadata bindings

Selected task: M-STAGING-BIND-20261018-W45. Base: accepted develop snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; pending PR42 is not this baseline.
Owned additions are the portfolio module/catalog, this document and authored
tests/fixture. Shared core and registry remain unchanged. No real body has been
opened, parsed, downloaded or accepted by this package.

## Repeatable metadata interface

```sh
python3 -B -m offmenu.refresh.portfolio45 --templates > /private/offmenu/metadata.json
python3 -B -m offmenu.refresh.portfolio45 --input /private/offmenu/metadata.json --as-of 2026-10-18T00:00:00Z
python3 -B -m unittest tests.test_portfolio45_bindings -v
```

The caller chooses an existing private local executor output directory. The CLI reads only
its small metadata envelope and the bundled trusted catalog; it never opens any
referenced source/evidence paths. stdout is deterministic canonical JSON with an
explicit clock. Unknown bindings, malformed descriptors and peers receive isolated
diagnostics; malformed JSON/duplicate keys or symlink inputs fail the whole CLI
before any descriptor inspection. Limits are 16 envelopes, 32KiB each, 512KiB file.

Each binding declares country/type, internal binding source/release identity,
exact retained qualification-metadata manifest path/SHA, known original-input SHA
or null, native units/bases, field selectors and unknowns. `releaseId` names the
binding's evidenced revision/scope, not an invented national release. Manifest
means the retained metadata evidence file here, not an accepted parser manifest.
`metadataValues` are small qualification facts/counts, never source observations.
Origins point into that exact retained metadata JSON; they do not claim direct
field coverage of raw nutrients/prices. Bodies stay exclusively on the selected local executor.

Shared `field_origin_errors` validates complete per-datum origin coverage, source
and input-pin identity. This binding additionally checks exact metadata values
and coordinates against trusted catalog declarations. Descriptor fields cannot
provide grants, remove holds or create shared `SourceContract`/admission objects.
Real catalog entries remain held, including the metadata-only execution boundary.
Missing inputs are reported alongside holds; no implied global source absence.

the product integrator baseline/interface result5798 confirms there is **no generic pure
cache planner** at this base. This package does not call Wikibooks-specific
`core.cache_policy`, registry-only `plan_fixture`, or operational `CachedAcquirer`.
It preserves originalAcquiredAt and validatedAt separately, reports informational
ages using shared timestamp validation, and declares the minimum30day requirement.
Cache intent is explicitly `unsupported-pure-cache-planner-no-download`, with
`cachePlannerSupported=false` and `stagingReady=false`. No force/revalidate/download
option exists and no TTL engine is copied here. Missing acquisition time stays
unknown; validation, publication or mtime cannot supply it. Stale manifest pins
are independently diagnosed even after recent validation. No real cache reuse,
refresh eligibility or staging write is claimed by metadata validity.

The replay key binds all trusted catalog details plus the metadata descriptor,
excluding only validation time and a caller-supplied previous key. Matching keys
produce `no-op` for the metadata plan. This is a pure comparison interface, not
proof of a prior staging write: the existing runner must verify its previous
receipt/artifacts before using it to skip work. `assetBytesVerified=false` and
`datasetAccepted=false` are unconditional. The package never publishes a pointer.

## Portfolio scope and remaining blockers

| Binding | Evidence and applicability | Typed remaining input / owner |
| --- | --- | --- |
| IT CREA | Original producer11 metadata receipt chain; one metadata row, zero food samples, 2019 label unverified | Custody: actual later release holder remains unknown; the product maintainer routes existing11 evidence. Rights: operation-specific grant/decision missing. No new acquisition. |
| IT facilities | Eight reviewed private Ministry facility/activity records, not recipes | Missing exact original manifest; private extent/operation acceptance retained with the source owner. No recipe/image/publication entitlement. |
| IS CPI | 12 bilingual legend categories,24labels; historical annual CPI changes context | No numeric bar/item-price extraction; semantic scope is taxonomy only. |
| IS ÍSGEM | Composition source metadata only | Authorization: existing agreement-authorized edition/dictionary required; the source owner. No agreement acceptance or body access. |
| JE RPI | 105 quarters/1680 lexemes; retained resource revision and original SHA | Semantics: historical labels/RPI(X) base binding; custody: original acquisition timing. Named OGL-J1.0 and retained isopen=false coexist, no new adjudication. |
| JE survey | Ten adult previous-day5+portion prevalence observations | Semantics: CSV fraction-versus-percent encoding unknown; no100 multiplication. Acquisition timing missing. |
| JM Table3 |14rows/182literalobservations; per100g edible portion, UK composites | Scientific: sugars/carbohydrate conflict, analyte legend, row primary-sample count; source authority required. No repair or national equivalence. |

All unlisted needed country/type requirements remain unfulfilled; this finite
metadata catalog is not portfolio completeness. No public documentation search
was needed for this successor: exact source-method findings were already retained
in B03-W45. Explicit denied routes, Finland/Frida and native NO/FR restrictions,
private-source holds, old uncertain sends, production/CIX and DEV7645 stay intact.

## Proposed shared interface for the product integrator

No shared change is required to run this standalone metadata package. For normal
runner wiring, propose an identity-neutral pure helper, selected and implemented
only by the existing shared owner:

```python
plan_retained_metadata(source_id, release_id, input_sha256,
                       original_acquired_at, *, as_of)
```

Return minimumReuseDays, acquisitionAgeDays, decision, assetBytesVerified=false
and networkRequests=0, with explicit unknown-time diagnostics and no force flag.
This aligns with result5798's central `plan_retained_input` proposal, which is not
implemented or called here. Current core v1 has hardcoded source labels. A later
reviewed metadata-only
SourceContract factory can wrap this portfolio callback after exact rights,
scope, inventory, record expectations and runner isolation are selected; no
factory/production admission is installed here. the product integrator owns that decision,
independent review and develop integration. Golden promotion remains later.

## Verification

### PR48 explicit JSON nesting correction

CLI serialized JSON now has an explicit maximum of48 nested array/object
containers. A bounded byte scan checks nesting **before** `strict_json`, ignoring
structural characters inside strings and handling escaped quotes/backslashes.
The shared decoder still owns full syntax, UTF-8 and duplicate-key validation.
Over-depth input consistently exits2 with the fixed diagnostic
`metadata-input-invalid: json-nesting-limit`, independent of whether a runtime's
JSON decoder raises `RecursionError`. Direct Python API per-peer containment is
unchanged; this new48-container contract applies to serialized CLI JSON ingress.

`python3 -B -m unittest tests.test_portfolio45_depth_delta -v` exercises boundary,
mixed-container, escaped-string, permissive-decoder, actual CLI and ordinary-held
controls using authored data. Seven tests passed on available Python3.12.3.
Python3.14 was unavailable locally and was **not run**. The permissive-decoder
probe establishes pre-decode rejection, not a claim of executing Python3.14.
Prior reader/isolation, selector/hold, cache-intent and replay scopes remain under
their existing evidence; SAME33 reviews this owned delta before00 integration.

### Reviewer33 correction (6428)

The local CLI now opens metadata once using no-follow directory descriptors and
a nonblocking final descriptor. Regular-file type, single-link identity, size and
pre/post inode metadata are checked on that descriptor; reads are bounded to the
512KiB limit plus one rejection byte. It does not check a path then reopen it.
Replacement, growth, FIFO and hardlink fixtures fail closed. Unsupported platforms
do not silently fall back to an unsafe reader; this selected implementation is
for the existing POSIX local executor runtime.

Recursive direct-API descriptors are contained as per-entry malformed diagnostics.
Nonstrings are not echoed as unknown binding identities, so cyclic inputs cannot
poison output serialization. CLI decoder/encoder recursion failures return a
fixed error without traceback. The focused correction suite is
`python3 -B -m unittest tests.test_portfolio45_review33_correction -v`.
Unchanged catalog/source/selector and narrow clock/replay positive coverage remains
under its existing receipts; the correction is pending SAME33 independent review.

Authored fixtures demonstrate valid, missing, held, malformed and stale metadata;
informational age across30days without planner success, validation-age independence, exact origin/pin/value checks,
deterministic replay/no-op, peer isolation and CLI rejection paths. A valid fixture
is never real-source staging acceptance. Existing shared field-origin tests are
run alongside these tests. OS resource isolation remains with the existing runner,
not this metadata diagnostic helper.
