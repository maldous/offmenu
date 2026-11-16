# Worker54 source-input bindings

This package binds **retained metadata declarations**, not raw country records,
to the accepted `abecb99ee1125730ccbc2824b6ec49ffc5cc4302` contract snapshot.
It owns only `portfolio54_config.py`, `portfolio54_binding.py`, this document and
the focused test. No shared core, source registry, production admission or country
coverage requirement is changed. the product integrator's result5798 confirms this proposal
baseline; live provider/candidate/base checks remain delivery gates.

The code reuses `strict_json`, `timestamp`, canonical serialization/fingerprinting,
`field_origin_errors`, and the shared minimum reuse constant. Authored fixtures
exercise the existing `SourceContract`/qualification/acceptance interface. There
is no KM XLSX, KN HTML, KP PDF or KR guideline parser here. The retained KM parser
remains a separate asset with unresolved scientific/source scope; it is not run
or dynamically imported. All raw and staged source bodies remain on the selected local executor.

## Country/type declarations

| Country | Retained input and exact declaration | Applicability and remaining input |
| --- | --- | --- |
| KM | Corrected PLOS `.0323506.s002`, v1/file54151418; metadata `KM-mapping-proposals.json`, SHA256 `4022dc85b6c9b6df5ff02684a9153e148c0b49996eb1d093c33d7cad38128732` | Research nutrient table, not an approved national composition release. Header/unit declarations point to exact `/columnProposals/N/...` fields in that metadata. Stored reference mass, row preparation, FCT entry and unit applicability remain unknown. README `.s001`403 STOP persists. |
| KN | `KN-input-resolution-proposal.json`, SHA256 `43d23798897fa08a7f829447c7a655481f633eff735791df5c37d612e2709892` | Statistical CPI reference; not merchant prices or a physical basket. Edition label versus extent, literal row selectors and DOS ownership/licence applicability remain unresolved. Acquisition time is bound separately to the historical receipt `/finishedUTC`. |
| KP | `KP-input-resolution-proposal.json`, SHA256 `382b8b9074b9f74e83f4e5452b82ab0b9d403a27add96192740bb3179213aabc` | GIEWS crop/weather reference (04 September2026) and distinct population-survey lead; neither supplies the requested price/recipe/provider/guideline observations. Matching source manifest and native fields are absent in the scoped evidence. |
| KR | `KR-input-resolution-proposal.json`, SHA256 `28cbb9aec8ab5089acd77156eb9f92730e423e4dcd429aae262413ab89475b95` | FAO profile metadata for a2016 guideline claim; not the original Korean guideline or current numeric advice. Original edition/body/page/use evidence remains unresolved. |

Configuration includes exact retained local executor metadata paths and digests, separately
labelled original-body digest claims where supplied. Importing or calling this
module never opens those paths, verifies original bytes or grants custody. The
KM acquisition time comes from the historical acquisition receipt `/utc`, not
from a new hash check. No signed locator or credential is included. KP
missing acquisition time stays `null`; a recent validation cannot fill it. KN uses
its exact receipt `/finishedUTC`; KR uses `/completed_utc` for the FAO profile HTML
only, not the original Korean guideline. These are historical receipt assertions,
not new source-body checks.

All six portfolio data requirements remain explicit: ingredients, recipes,
nutrition, retailers/providers, prices/baskets and dietary references. None is
accepted by this package. A source reference, metadata candidate or passing test
does not establish an entire country/type cell. KP's wrong-source-type finding
is retained rather than converting a survey or brief into another data type.

## Metadata-only interfaces

From the repository (Python plus the existing optional `jsonschema` dependency):

```sh
python3 -m offmenu.refresh.portfolio54_binding --country KM \
  --now 2026-10-18T12:00:00Z --declaration
python3 -m offmenu.refresh.portfolio54_binding --country KN \
  --now 2026-10-18T12:00:00Z
```

`--declaration` emits one code-authored `source-input-binding` metadata record.
Its source identity is the retained metadata declaration, **not** the original
workbook/report. Every scalar in `data` has a shared-validator-compatible origin:
an exact metadata JSON pointer, or a policy-pinned explicit unknown constant.
`metadata_semantic_errors(country, row)` verifies coverage and exact declared
values/selectors. This is a hook for a future independently reviewed metadata
`SourceContract`; it does not construct one from untrusted source metadata.

The default command emits diagnostics for missing observation metadata. An
optional `--observation -` accepts at most64KiB of strict JSON on stdin, with only:

```json
{
  "sourceId": "reviewed target identity from code configuration",
  "releaseId": "exact target release from code configuration",
  "manifestSha256": "64 lowercase hex characters",
  "originalSha256": null,
  "acquiredAt": null,
  "validatedAt": null
}
```

These are assertions for comparison, not verified acquisition/cache records.
Unknown values cannot be replaced with guessed timestamps or source digests.
The CLI never dereferences input paths or URLs. Duplicate keys, extra grant/hold
fields, nonfinite JSON, malformed identity/pins/times and oversized requests fail
closed with fixed diagnostic codes. Source exceptions or raw input are not logged.
Each invocation is independent: one failed input cannot corrupt another source's
report. Exit0 means declaration emission or metadata readiness only; exit2 means
the diagnostic report is held/blocked/malformed/missing/stale. Neither is source
qualification, acceptance, a GLOBAL Binding or an OS isolation guarantee.

## Acquisition, validation, replay and diagnostics

`plan(country, observation, now=..., previous_key=...)` returns separate
`inputStatus`, `disposition`, sticky holds and sorted diagnostic codes. A valid
metadata assertion may still have `disposition=held`. Real portfolio bindings
all retain source-processing holds. An observation cannot clear them or install
an operation grant. Missing internal custodian recognition is recorded evidence
uncertainty, not a claim that public documentation is legally prohibited.

The original-acquisition and metadata-validation ages are computed independently
from an explicit UTC clock. Replacing a known acquisition time is rejected; an
unknown one remains unknown. Under30days the report identifies the minimum reuse
window. At/after30days it reports review-required/stale input; it neither declares
cached bytes unusable nor permits fetching them again. Later metadata validation
does not renew original acquisition age. `fetchAllowed`, `sourceBodyAccessAllowed`,
`qualified` and `accepted` always remain false. No force/revalidate/download switch
exists. Actual cache bodies and retention entitlements are not inspected.

The replay key binds identity, input digest, original acquisition assertion and
the whole reviewed declaration policy. Identical assertions under the same policy
produce the same key; validation time alone does not change it. Unknown required
metadata prevents readiness. A policy change changes the key. Held sources never
receive a replay instruction. A separate authored fixture demonstrates `noop`;
no real-country hold is removed for a positive test.

There is **no generic pure planner** in this baseline. This is a portfolio
metadata intent/validation interface, not a copy of a shared cache engine.
`CachedAcquirer` is operational and can read/fetch bodies; it is never invoked.
`core.cache_policy` and `plan_fixture` are not reused by impersonating their source
or registering a real source as a fixture.

## Integration proposal and remaining blockers

No shared API change is required to run this diagnostic/declaration CLI. For
source execution, the product maintainer must select and independently review the
exact adapter, source/release/input manifest, actual field origins, native units,
bases, scope, operation-specific rights and acceptance contract. Retained licence
metadata or public landing access alone is not such a contract. The existing
README403/native-crash/Finland/Frida/private/credential/denial holds are unchanged.
No new documentation fetch is needed for this implementation: the selected
official metadata/method/licence evidence is already pinned in the retained B03
package; the remaining KM document is explicitly denied, while KN/KP/KR need exact
source applicability/original inputs, not a generic landing-page permission.

If the product maintainer selects a shared pure-planner extension, reuse the product integrator's result5798
proposal for one source-neutral, I/O-free helper; do not promote this private
portfolio helper into shared execution. It must retain identity/pin/time chains,
unknown/held outcomes, the minimum30day no-download automatic window and explicit
metadata-only semantics. This package does not install or assume that extension.

Focused tests use small authored metadata and temporary fixture bundles, never
the retained originals or stages. They demonstrate valid, missing, held,
malformed, stale, no-op/policy-change and missing-runtime-dependency outcomes;
literal unit/unknown retention; exact per-datum origins; deterministic bounded
CLI output; and shared qualification with `accepted-fixture-scope` only. No test
claims real-source freshness, source acceptance, country completion or golden
promotion. Independent review, the product maintainer verdict and develop integration remain
required. Production/CIX and the separate DEV7645 custodian are unchanged.
