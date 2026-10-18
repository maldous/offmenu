# BV/LU/SH retained metadata bindings

This package is portfolio configuration and a metadata diagnostic interface on
develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It does not collect, parse or
qualify source bodies, emit normalized country data, register an adapter, or
admit a country/source. Pending PR42 is not a dependency or accepted baseline.

Run from this checkout, with an explicit UTC diagnostic clock:

```sh
python3 -B -m offmenu.refresh.bv_lu_sh --evidence-root /home/user \
  --as-of 2026-10-18T05:00:00Z --output /tmp/bv-lu-sh-metadata-plan.json
python3 -B -m unittest discover -s tests -p test_bv_lu_sh_binding.py -v
```

The committed Python catalog is trusted configuration, installed with the
package without a new package-data rule. There is deliberately no CLI plugin,
manifest override, force-download option, downloader or body-processing hook.
Only the catalog's finite, size-bounded metadata JSON inputs are opened; each is
verified against the exact SHA/length, parsed with shared strict JSON handling,
then compared at the declared selector to its exact retained literal. Release
identity must match the source digest in the independently pinned acquisition
receipt. Shared `field_origin_errors` verifies every emitted literal's coverage
and source/release/input identity. It does not establish economic equivalence.
Shared path, timestamp, canonical serialization and atomic-output helpers
are reused. There is no copied national parser or country refresh engine.

`metadataBinding` is an evidence declaration, not an accepted common/native
candidate. Its input coordinates identify metadata selectors, not newly read
CSV/XLSX cells. `references` retain exact existing author/manifests/response pins
for review, and are never opened or represented as newly integrity-verified body
assets. Metadata is read through one nonblocking, no-follow regular-file descriptor,
with descriptor/path identity checks before/after, a pin-size-plus-one read bound,
and exact length/SHA verification of the bytes parsed. No second path open or
unbounded read occurs; no original/candidate dataset is read. Absolute recorded artifact paths
stay in private metadata output; no public projection is supplied.

| Country | Bound scope | Current disposition |
| --- | --- | --- |
| BV | Existing author receipt; all six categories explicitly missing | Missing exact source/release/custody/applicability; no fabricated asset |
| LU | E5407 receipt plus prior14 metadata: five unit/base/measure/frequency/role literals | Held: economic denominator/reference period and classification release unresolved; use/independent admission not supplied |
| SH | Existing workbook acquisition receipt timestamp and release digest only | Held: reuse, worksheet mapping and territorial coverage; units/base remain null |

All other required ingredient/recipe/nutrition/provider/dietary-reference types
are explicitly incomplete. LU is statistical weighting context, not retail
prices or food quantities. BV applicability is unknown; SH evidence does not
establish Ascension/Tristan coverage. Historical numeric holder labels remain
leads, not verified native source custody. Source/source-role labels and v2
publisher labels are not approved taxonomy targets. All4592 upstream target,
equivalence, use and admission nulls remain untouched. The C196 methods route's
explicit rights/admission hold is preserved; this task does not fetch linked
documentation to work around it.

The cache block separates original acquisition (pinned receipt `/utc`) from the
caller-supplied diagnostic/metadata validation clock. File mtime and subsequent
validation never reset acquisition age. The age is an observation only: this
portfolio does not decide freshness, eligibility, reuse or conditional-refresh
status. The shared source-neutral pure planner is absent, so every real-source
metadata report explicitly returns `planningCapability=unsupported-shared-planner-absent`,
`eligibility=null`, `action=unknown-no-download`, and zero automatic downloads.
Old timestamps alone do not hold otherwise-valid metadata or suppress a candidate.
This is not a raw cache or retention/refresh implementation. The controlling
minimum30day requirement remains an unimplemented shared capability, not a locally
copied threshold.
Same input/content/config has the same `bindingFingerprint` across clock changes.
`publish_report` returns `verified-no-op` and preserves inode/mtime for exactly
identical diagnostic bytes. Changed clock observations may write a new report;
the source-content fingerprint stays unchanged. No raw cache or source is mutated.

Diagnostics are per-country and fixed-code: missing source/metadata, source-held,
malformed/unsafe/pin/literal/clock contract, or metadata-ready with an unsupported
cache-planning capability. A bad
binding cannot stop peers. `metadata-ready` is possible for authored fixtures and
means only metadata binding validity, with acceptedRecords=0. The real catalog
does not release any current hold. Authored fixtures test valid/missing/held/
malformed and timestamp observations with absent planner, release-pin mismatch,
source pin/selector corruption,
duplicates/nonfinite JSON, symlinks/path bounds, isolated peers, no network/body
reads and actual output no-op. The focused correction additionally covers a
FIFO replacement at the open boundary with sibling progress and a growing regular
file whose read is limited to pin size plus one byte. They do not replay historical source suites or
native NO/FR handlers.

## Proposed shared interface for integrator00

No shared-core edit is included. The previous local threshold/eligibility logic
was removed in the correction for W12-W14-2192504-F2. `policy.plan_fixture` requires a registered
authored fixture and `core.cache_policy` hardcodes Wikibooks identity. To avoid
duplicating a future production policy, propose extracting an identity-neutral
`plan_acquisition_evidence(source_id, release_id, input_bundle_sha256, evidence,
*, now)` from the existing reviewed policy: preserve originalAcquiredAt, require
monotonic same-content revalidations, minimum30day automatic zero-download,
and return stale/revalidation-review diagnostics without a downloader/force
bypass. Existing fixture behavior/tests must remain unchanged. This proposal is
for00 review, not a prerequisite for using this metadata report or authorization
to modify the core. Wiring to execution/admission remains separately selected.

Independent approval and develop integration are required. The integrator must
reconcile the current target against this immutable base. Raw data stays Foo;
Finland/Frida/NO-FR/source/privacy/denial/production/CIX/DEV7645 holds remain.
