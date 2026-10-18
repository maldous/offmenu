# Worker61 GP / NU / TO / YT metadata bindings

Base: accepted develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
The pending handover and PR42 are separate and remain unmerged. This package owns
only its portfolio configuration, binding module, authored fixtures and tests.
No shared engine, registry admission, source policy or core validator is changed.

## Run on Foo

Requires the existing Python test extra (`jsonschema`); nothing is installed by
the command. Use this worktree's Python module, never dynamically import an old
producer script.

```sh
python3 -B -m offmenu.portfolios.worker61 \
  --config bindings/worker61-gp-nu-to-yt.json \
  --metadata-root /home/user \
  --now 2026-10-18T00:00:00Z \
  --output /absolute/new/private/metadata-report.json
python3 -B -m unittest discover -s tests -p test_worker61_bindings.py -v
```

The output parent must already exist. No network, source-body read/stat/hash,
download, copying, parser execution or country acceptance is performed. Every
manifest points to a bounded, hash/size-pinned JSON receipt only. Original paths
and checksums are returned as **historical receipt values**, never followed.
Names, URLs and general licence assertions remain source-scoped evidence.
Do not point the tool at a source body disguised as receipt metadata; only the
reviewed configuration is an execution input. Raw assets stay outside Git on Foo.

## Source and type boundaries

Seven declarations cover six retained metadata receipts and one explicitly
missing workbook. `domains` lists the type being investigated, not coverage or
accepted applicability. The report retains all six required types for all four
countries as not accepted. No not-applicable category is inferred.

| Binding | Recorded source role | Outstanding binding |
| --- | --- | --- |
| GP release | Insee HTML release page | workbook, sheet/cells, native unit/period/base and exact-file use applicability |
| GP workbook | advertised XLSX, not held | retained manifest and field/method evidence |
| NU census | agriculture aggregates, not producer identities | table/cell/unit/year, edition, aggregate privacy/use |
| NU CPI | separate owner53 aggregate index | current custodian, dictionary/base/time/use; not item prices |
| TO | historical nutrition policy reference | edition/component page/use; not current numeric guidance |
| YT menu | dated education-venue menu, not recipes | permitted actor/page/date/course/transcription credit |
| YT memento | failed transport metadata | original absent; no retry permitted |

Each field carries the exact receipt SHA, JSON pointer, native value, and explicit
unit/basis declarations. Null means unknown, never converted or defaulted. No PDF
coordinate or food observation is synthesized. `stagingReference` covers each
resolved scalar datum through shared `field_origin_errors`: receipt values have
exact source origins; unit/basis unknowns or authored declarations are distinct
configuration constants bound to `bindingKey`. This is structural origin coverage,
not independent validation of source semantics or applicability. The selected existing generic
adapter list is read through `adapter_mapping.retained_adapters`; no reviewed
PDF/HTML payload route matches these source/release pairs. That absence is an
integration dependency, not permission to borrow a national or recipe engine.

## Shared interfaces and diagnostics

The module reuses `core.strict_json`, `timestamp`, `safe_path`,
canonical JSON, `acceptance.fingerprint`, `acquisition.MIN_TTL`, and the shared
adapter descriptors and `field_origin_errors`. JSON Schema validates authored configuration; no copied
country parsing or qualification engine is introduced. The fixture bridge uses
the existing `acceptance.SourceContract` / `qualify` path for one authored metadata
reference. Its rights, count and schemas apply only to that synthetic fixture.
No real source processing rights or country completeness follow from that pass.

`assess(config, metadata_root, now=UTC_STRING)` returns isolated per-source
outcomes: `metadata-bound`, `missing`, `held`, `malformed`, `stale-input`,
`invalid`, or `needs-input`. A stale input means exact metadata-pin mismatch;
cache age is reported separately. A held source can still have verified receipt
metadata, but `sourceProcessingAuthorized` always remains false. Diagnostics are
fixed codes; they do not echo raw receipt bodies or exception details. Malformed
complex/oversized selector values are cleared rather than echoed. Metadata is
bounded to 256 KiB per pinned receipt, 32 scalar selectors per source, 8,192
characters per selected string, and 32 source declarations.
Malformed
identities, paths, missing selectors, duplicate bindings and failed pins do not
prevent valid peers from reporting. No failed subset becomes complete output.

`metadataSourceKey` depends on source/release/receipt pin, independent of country
consumers and observation/validation age. `bindingKey` separately identifies the
portfolio configuration, including declarations/holds. Original acquisition time
is taken from an explicit receipt pointer. Validation time is separately supplied
and never renews original acquisition age; unknown validation time stays null.
Under 30 days the metadata plan says reuse without download; at the boundary it
says review revalidation without download. Neither state activates acquisition or
asserts cached source bytes were verified. No force-download option exists here.

An identical config/pinned input/explicit-clock run produces identical bytes.
`write_report` returns `no-op` without touching an identical output; changed
evidence or clock requires a new path. Tests exercise changed inputs, 30-day age,
recent validation, unknown units, symlinks/traversal, duplicate JSON keys,
nonfinite values, peer isolation, and shared fixture qualification.

## Publisher documentation

[Insee's current legal notice](https://www.insee.fr/fr/information/2008466),
observed 18 October 2026, provides a default Open Licence 2.0 rule for public
information, with attribution/date/integrity and service-use conditions and
exceptions. The small authored evidence summary is
`bindings/worker61-public-documentation.json`. It improves the general-use
documentation gap; exact file applicability and existing action holds remain.
An absent internal custodian is not itself a legal prohibition. No extra grant is
presumed necessary when applicable published terms suffice. Landing access alone
is not treated as permission. No held original or denied endpoint was read.

## Exact proposed interface for integrator00 (not implemented in shared core)

Provide a pure, source-neutral policy entry point, for example
`plan_retained_metadata(source_id, release_id, input_pins, original_acquired_at,
validated_at, now, holds=()) -> dict`, in the existing refresh policy module.
It must retain the original timestamp, report validation age separately, reject
future/naive times, use source/release/content identity independent of countries,
return zero network activity, and never turn hold clearance or stale metadata
into permission to fetch. Existing `core.cache_policy` hardcodes the Wikibooks
pilot identity; `policy.plan_fixture` is fixture-only. This package therefore
exposes a small metadata-only decision while awaiting a reviewed shared entry
point; it does not edit either implementation or the existing acquisition P2.

Later payload execution additionally needs reviewed rights/scope assets, exact
field-origin selectors and full counts/IDs for `acceptance.SourceContract`,
source-specific semantic validation, and a matching supported adapter. Current
PDF/HTML format support remains absent. Integrator00/Morgan own any shared-core
change, independent review, corrections and develop integration. Golden
promotion, production, CIX, DEV7645, Finland/Frida and native NO/FR restrictions
remain unchanged.

## Reviewer49 runtime-boundary correction

The correction to exact candidate `2325c2ef09788adbe8c5f4efb6b0ef8496c3b99a`
addresses only F1/F2/F3 in reviewer49's changes-requested receipt. Shared core
and real source assets remain unchanged.

- Config, metadata and existing replay-report reads use the author-owned
  `read_regular` helper: nonblocking/no-follow opens, verified regular-file
  descriptors, bounded reads and before/after descriptor identity checks. Parent
  traversal also uses directory descriptors with no-follow. Metadata hash checks
  and JSON parsing consume the same returned bytes; there is no digest/reopen
  boundary. An existing FIFO is rejected before reading, and new output still
  uses exclusive creation.
- Selected nonfinite floating values, including finite-looking exponent
  overflow, are rejected and cleared before field origins or serialization.
- Acquisition and validation clocks are bounded UTC strings validated before
  attachment. Rejected values leave only null/unknown and fixed diagnostics.

Focused authored regressions (no source-body or full-suite replay):

```sh
python3 -B -m unittest discover -s tests -p test_worker61_corrections.py -v
```

The nine tests cover config/report FIFOs, metadata replacement before open and
after descriptor acquisition, regular-file bounds/symlinks, positive/negative
numeric overflow, rejected acquisition/validation values, and valid-peer
serialization/clocks/origins/no-op preservation. Subprocess timeout guards kill
and reap a hung regression child; passing runs terminate normally. Prior14-test
and independent positive evidence is retained, not claimed as a newly rerun
suite. SAME reviewer49 must assess the changed immutable delta before acceptance;
integrator00 retains develop and live-provider gates.
