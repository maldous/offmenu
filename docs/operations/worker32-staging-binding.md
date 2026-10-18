# GB/GD/GE/GF retained source-input bindings

This package is the metadata/code successor selected as
`M-STAGING-BIND-20261018-W32`, based on develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It changes only
`offmenu/portfolio32`, its authored tests and this document. It installs no
source acquisition, source-body parser, shared registry entry, SourceContract,
acceptance receipt, country completeness decision or golden promotion.

## Executable interface

Run from the reviewed source checkout, supplying the observation clock explicitly:

```sh
python3 -m offmenu.portfolio32.binding --observed-at 2026-10-18T00:00:00Z
python3 -m offmenu.portfolio32.binding --key gb-phe-2016 \
  --observed-at 2026-10-18T00:00:00Z --emit-candidate
python3 -m unittest tests.test_worker32_staging_binding -v
```

The default command emits one compact diagnostic per installed binding. Exit 0
means every selected **metadata** input is ready; exit 2 retains each missing,
held, malformed or stale diagnostic, including healthy siblings. Candidate mode
requires exactly one key and emits deterministic singleton JSONL packets only
when that input is ready. Held/error candidate requests return a diagnostic and
exit 2. Neither mode writes files or performs network operations. There is no
force-download option. A caller can capture stdout in its own selected staging
location; this CLI never changes an accepted pointer.

`inspect(spec, raw, observed_at=..., validated_at=..., previous_candidate=...)`
is the pure bytes interface. Its `Inspection` contains a diagnostic and optional
candidate bytes. `inspect_many` isolates the outcomes of a batch. Runtime file
access is limited to the installed catalog's metadata path, with symlink-component
rejection and a 16 MiB read bound. A hold is checked before reading or parsing.
Nested source, cohort, note, original-body and rights pointers remain opaque;
the command never follows them. A stale input requires review and emits no new
candidate, without fetching or repairing anything.

The caller retains responsibility for OS resource/network isolation. The tests
use bounded authored data and a network-denying socket mock; that is not proof of
OS confinement. The shared qualifier's SQLite scratch/resource limits and full
reviewed execution boundary remain applicable to later selected execution.

## Portfolio evidence and scope

`catalog.json` pins each source/release, exact retained manifest/evidence and
country/type applicability. It lists all six required portfolio data types, but
declares no complete country/type cell. Absolute metadata pointers refer to
retained local Foo artifacts; missing files remain typed missing inputs on another
host. No raw dataset, image, PDF, workbook, credential or generated corpus is
included in this source package.

The installed declarations are concrete even for inputs without a selected data
parser: one GB context collection, 13 GD receipt rows, nine GE receipt rows and
one GF partial-extent annotation. They name exact metadata pins and JSON selectors
for release, rights, source identity, custody uncertainty and extent. GD/GE unit,
basis and original acquisition remain explicit unknowns. These declarations are
available for downstream manifest binding even while body processing is held;
the CLI exposes them without reopening the receipt targets or copying source data.

GB uses the existing immutable PHE August 2016 **field-evidence metadata** file,
62 contexts referencing 558 prior literal records. The source acquisition clock
comes from the pinned original acquisition receipt `/utc`, not its publication
date, the binding's creation time, a validation timestamp or filesystem mtime.
The existing source/review and rights evidence is unchanged. The binding has
specific applicability only to historical GB dietary-reference source metadata;
it does not establish current clinical guidance or Guernsey applicability.

GD exposes a held receipt-metadata binding: eight GFNC images remain images,
and historical CPI/menu acquisition does not grant recipe derivation or current
national price coverage. GE's historical order, CPI, menu and report evidence
does not establish the missing national 2009 food-composition table, current
policy, item prices, a producer roster or a reviewed derivative-use scope.
GF's 16,777,216/33,138,801-byte partial source remains held with no retry, cap
increase or concatenation. For these three bindings the acquisition clock and
field-level candidate are unknown, never synthesized. The installed hold reasons
are returned with diagnostics; source selection gaps are not represented as a
new publisher denial or a general legal prohibition.

Missing internal custody alone is not treated as a rights prohibition. Existing
source-use evidence supports the recorded historical retention scope; this
selection covers binding retained metadata only. It does not select new body
operations. No missing public format/licence/method documentation is needed to
interpret these already-bound metadata fields; public landing visibility and
licence labels are not substituted for an operation-specific use decision.

## Origins, unknowns and shared qualification

Every emitted scalar under `/data` has a `source` origin whose `inputPath` is
`retained-contexts.json`, `inputSha256` is the installed metadata pin and
`sourceField` is the exact JSON pointer into `/bindings/{index}`. The source
context and record IDs, literal label/unit/denominator, source publication claim,
comparison, subnote and ten unresolved decision slots survive without conversion.
The `mg/d` denominator remains `d`; absent comparison remains null. The Table 4
vitamin D context39 requires its STOP flag and null subnote binding. All ten
target/use/admission slots remain null. The cohort and parsed-artifact selectors
are declared in provenance without loading their target bodies or making a new
semantic/applicability decision.

Shared interfaces are imported, not copied:

- `core.strict_json` rejects duplicate keys; shared canonical serialization also
  rejects nonfinite/overflow values.
- `serialization.encode_records` supplies deterministic singleton JSONL bytes.
- `field_provenance.field_origin_errors` checks complete scalar origin coverage.
- `acceptance.qualify` verifies authored fixture candidates against explicit
  `SourceContract`, schema, exact asset/ID/count/rights/scope pins and the
  portfolio callback in the tests.

`semantic_validator(spec, raw)` binds exact source coordinates, values and origin
objects to the pinned metadata. It is a callback for a separately reviewed shared
SourceContract, never a constructor of rights or acceptance authority. The tests
construct only `fixture=True` contracts with authored rights/scope assets and
independently listed fixture IDs. No production contract is installed. Source
metadata schemas and the semantic policy fingerprint travel separately; the
reviewed commit/file pins must accompany any future execution configuration.

## Cache and replay

The 30-day minimum uses the shared acquisition `MIN_TTL` and explicit original
acquisition timestamp. `validatedAt` is a separate observation and cannot reset
acquisition age. Future, naive and inconsistent clocks fail closed. Under 30
days the interface reuses the retained metadata with zero downloads. At or after
30 days it returns `stale-input` and `revalidation-review-required-no-download`.
No stale outcome activates a conditional request, publisher access or bypass.

Candidate identity depends on exact input bytes, original acquisition provenance,
literal fields and binding policy, not the validation clock. Repeating the same
content yields identical candidate bytes; a supplied identical previous candidate
returns `verified-no-op`. This is deterministic metadata reuse, not an installed
30-day acquisition cache or proof of source-wide refresh acceptance.

Integration00 baseline/interface result5798 confirms that no generic pure cache
planner exists at this base. The Wikibooks-specific `core.cache_policy` and
registry-only `plan_fixture` are not called or spoofed. Operational
`CachedAcquirer` is not invoked. The small portfolio observation above is labelled
cache/replay **intent**, with the absent shared planner reported as a typed
dependency. A central planner extension remains Morgan/00 proposal-only and does
not prevent these retained metadata declarations from being delivered.

## Integration and remaining typed inputs

The shared accepted develop contracts currently have no reviewed PHE dietary
recommendation body adapter. This package does not create or register one. No
shared-core change is requested for the metadata candidate: the existing scalar
origin checker, serializer and qualifier suffice. Any future body adapter,
registry route, real qualification contract, refresh or acceptance must be a
separate exact integration00/Morgan selection with actual source-use, runtime,
independent review and field semantics. Current dictionary/equivalence/use and
admission gaps remain explicit; metadata readiness grants none of them.

The old worker checkout/dirty artifacts remain preserved. The clean managed
worktree holds only this branch for review. Independent approval and expected-head
develop integration by existing integration00 remain required before another
request. Pending handover/PR42 is not substituted for develop. Finland/Frida,
native NO/FR crash, privacy/denial/source holds and raw-on-Foo custody remain;
production/CIX and separate DEV7645 are untouched.
