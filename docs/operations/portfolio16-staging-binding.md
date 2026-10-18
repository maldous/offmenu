# BN / BI / BJ / BL retained metadata binding

Base: accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
This is a portfolio configuration/adapter binding, not another country engine.
It emits **source-input metadata descriptors**, never food records, normalized
prices, recipes, nutrition targets, accepted STAGING data or gold.

## Run without original-source access

```sh
python3 -m offmenu.refresh.portfolio16_binding \
  --metadata-root /home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-16 \
  --output /private/foo/portfolio16-binding \
  --now 2026-10-18T00:00:00Z
python3 -m unittest tests.test_portfolio16_binding tests.test_refresh_field_provenance -v
```

The installed inert code catalogue `offmenu/refresh/portfolio16_catalogue.py`
fixes seven bindings to four exact `COUNTRY/deliverable-validation.json` metadata
files. `load_profile()` deepcopies it without opening any file. The original
`config/source-bindings/portfolio16.json` remains byte-identical as an audit
mirror; the installed loader does not require that repository-relative file.
An offline wheel/sdist transport proof covers default loading only, with source
metadata reads forbidden; it does not validate the actual retained metadata.
An alternative input root cannot alter the required bytes/SHA256. The adapter
opens only those relative metadata paths, rejects symlinks and traversal, caps
each file at 4 MiB, and checks before/read/after hashes. It never follows original
asset, acquisition receipt, rights, manifest, source URL or declared source-cell
pointers in the profile. Those are pinned declarations for later reviewed work.
No downloader, force option, importer, SourceContract factory or registry
admission is installed. Real files should remain on Foo; do not copy payloads
into a checkout to satisfy this adapter.

`metadata-candidate.jsonl` uses shared singleton-record JSONL serialization.
`binding-report.json` includes per-binding diagnostics, candidate digest/size,
original acquisition and validation ages, holds, and evidence declarations.
Both are private metadata artifacts, not acceptance receipts. Every descriptor
has `kind=source-input-metadata-binding`; `datasetAccepted` and source operations
remain false even when metadata is valid. Held/stale descriptors may still be
emitted as evidence, while missing/malformed metadata produces no descriptor.
Consumers must use the report's status/errors, not count descriptors as data.

Shared helpers are used directly: `core.strict_json/safe_path/digest/timestamp`,
`national_tabular.valid_input_name`, `field_provenance.field_origin_errors`,
`serialization.encode_records` and `acquisition.MIN_TTL`. The positive authored
fixture also passes the existing `acceptance.qualify` with a **fixture-only**
SourceContract supplied by test code, never constructed from a source manifest.
No shared core file is changed.

## Provenance and scope

Selectors follow RFC6901 string form (not URI fragments):
<https://www.rfc-editor.org/rfc/rfc6901>. Zero/null remain distinct from an absent
field. Invalid escapes, array leading-zero aliases and nonexistent array `-`
fail explicitly. No unit conversion, source equivalence or missing-value repair
occurs.

Every scalar in descriptor `data` has an origin checked by the shared validator.
Measured report fields point to the **validation metadata**, not the uninspected
food/source body. Portfolio annotations use tagged code constants pinned by the
reviewed profile fingerprint. BIF/EUR declarations are existing scoped currency
evidence; they are not new price observations. `nativeBasisDeclaration` and tax
stay explicit null. BI service stays unknown; BL's existing coverage statement
that service is included is retained as a pinned declaration, not newly verified
against the menu. Source-coordinate examples in the profile identify
existing first-record staged fields only; they are not an all-record origin map
or a certificate that an original cell was checked in this run.

| Country / retained input | Applicability and remaining limitation |
| --- | --- |
| BN MOH2020 reference | Bibliographic/dietary reference; commercial metadata applicability still unresolved; no clinical targets |
| BN download chain | Same-file acquisition control only; source date refers to original PDF acquisition, not derivation time of this sidecar |
| BI Best Outlook menu | Menu/price evidence, BIF; tax/service each unknown; reuse/currentness and quantities unresolved |
| BI FAOLEX policy | Policy reference, not analytical composition or adopted targets |
| BJ Fongbe |117 retained articles versus120 heading; no three missing records inferred; original expressions unnormalized; servings/basis/authenticity/reuse unresolved |
| BJ2015 guide | Reference; population/targets unqualified; separate2021 booklet's AGRIS licence assertion is not transferred |
| BL Pablo menu slice | Six retained EUR observations; service-included coverage declaration retained; acquisition time, tax, edition/currentness, quantities and derivative use unresolved |

The profile preserves the exact staged asset, original bundle manifest,3829
country batch and validation pins. Acquisition timestamps come from already
retained source receipt `/utc` fields where available; BL acquisition time is
unknown. A title/release label is reported as recorded, not requalified from a
body or promoted to current edition. All six required country/data types appear
in `countryTypeApplicability` with typed missing/held/not-suitable reasons and
`accepted=false`; reference metadata is never promoted to analytical nutrition.
Existing negative42/43 custody responses
remain in the external B01 restore checkpoint; no unchanged request is repeated.
An absent internal permission artifact is an unresolved input, not a new legal
prohibition. Public availability does not grant reuse. This task did not need a
new publisher format/licence ruling: its only input format is existing internal
JSON metadata, with the public selector format cited above.

## Cache, replay and diagnostics

The original acquisition timestamp drives the minimum30-day reuse window;
validation time is independently reported and cannot reset it. Under30 days the
interface says `reuse-retained-metadata-zero-download`. At/after30 days it says
`conditional-review-only-no-download` and emits `input-stale`. Unknown acquisition
time emits `original-acquisition-time-missing`. Neither aging nor a successful
metadata validation permits a download or removes a source hold. This is an
offline planning interface, **not implementation of conditional network refresh**
or proof of an existing original-body cache policy. `core.cache_policy` currently
names Wikibooks, and `policy.plan_fixture` is fixture-registry specific; neither
is falsely presented as a source-neutral production policy.
Every result explicitly reports `sharedPureCachePlanner=absent-at-abecb99`,
`realSourceRefreshCapability=unsupported-no-reviewed-source-binding`, and
`ageCalculationScope=metadata-age-diagnostic-and-intent-only`. This follows
integrator00 result5798 and its pinned late-dependency addendum; it does not
delay metadata binding on a speculative core implementation.

With an explicit UTC clock, unchanged inputs/profile produce identical bytes.
Publishing identical bytes is a no-op and preserves file mtimes. Changed files
are individually atomically replaced under the shared writer lock; multi-file
publication is not claimed transactional. Check the report's candidate digest.
Do not write outputs into the input bundle. No accepted pointer is moved.

Each binding returns one of `valid-metadata-only`, `missing`, `held`, `malformed`
or `stale`, plus sorted fixed diagnostic codes. Error accumulation preserves
coexisting holds/staleness/missing inputs. Primary precedence is malformed,
held, missing, stale, valid; inspect all codes. Failure of one source leaves
other results intact. Source payload values and exception paths are not echoed
in diagnostics. CLI exit0 means the report was produced; it does not mean all
sources are valid or accepted.

Authored fixtures/tests cover the five outcomes in one batch, source pins,
duplicate JSON keys, country/type-sensitive literals, unknown acquisition,
future clocks, null/zero, escaped selectors, symlinks,30-day boundary and no-op
mtime preservation. No actual source tests or original data processing occur.

## Exact proposed shared interface for integrator00

No core change is included. Proposed follow-up for the existing core owner:

```text
plan_retained_input(source_id, release_id, input_bundle_identity,
                    original_acquisition, revalidation_metadata, *, now,
                    retention_status, hold_status)
 -> {acquisitionAgeDays, validationAgeDays, minimumReuseDays,
     cacheDecision, errors, networkRequests:0}
```

This is the same proposal-only extension identified by00 result5798, not a
second competing helper. It should be source-neutral, pure, fixed-code
diagnostics, validate identity/hash/time/revalidation chains, preserve unknown
timestamps, reject future/reversed times, and provide no force/download bypass.
If adopted/reviewed, this binding can replace its small age calculation with
that helper. Actual source CachedAcquirer registration still requires separately
reviewed exact source/representation/rights/custody; do not enable one here.

Independent review and integrator00/develop integration are required. The
pending handover/PR42 is not this baseline. All source/Finland/Frida/NO-FR/403,
private/credential/denied-action, production/CIX and DEV7645 holds remain.
