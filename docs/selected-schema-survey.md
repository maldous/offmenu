# One bounded NO/FR schema survey

The `national-schema-survey` Foo profile reads the six exact selected Norway and
CIQUAL bodies on the existing read-only cache mount and three corroborating
receipts. It produces schema evidence only. The source snapshot stays on Foo.
No adapter is activated, no normalization is called, no candidates or accepted
pointers change, and nothing is downloaded. Fineli and all other sources remain
outside the selection.

## Invocation and fixed batch

```sh
python3 -B -m offmenu.refresh survey-selected \
  --workspace /srv/offmenu-refresh/outputs/schema-surveys
```

The existing shared CLI is extended; there is no parallel refresh pipeline.
There is no caller input root, manifest, lock, module, source selection, download,
force, or historical-admission flag. The workspace must be beneath the fixed Foo
outputs root. Run as the ordinary runner service user.

Fixed profile graph: `readiness` → `schema-survey-tests` → `schema-survey`.
The survey independently checks each country and runs the two source workers
serially. A missing/mismatched/unsupported Norway input does not suppress the
CIQUAL survey, and vice versa. It does not depend on a global all-sources-ready
result. A process/resource/input failure is a held country result. Other
countries still run.

The nine input sizes and SHA-256 pins are frozen in `survey.py` from diagnostics
run [39077114923](https://github.com/maldous/offmenu/actions/runs/39077114923),
executing source `bd2e8b0730a74f224d333d2cdc1cc7aa0f0b84e3`. The six bodies total
30,610,009 bytes; all nine selected files total 30,623,126 bytes. This binds the
retained snapshot, not present-day upstream freshness or a new source-use review.
Each worker rechecks its acquisition/prior receipts and all source files before
parsing. A hash match never enables the synthetic adapters for real data.

## Evidence collected

Norway:

- Root and row field presence/type histograms for all four JSON documents.
- English/Norwegian native identity types, validity, uniqueness, set digests and
  cross-locale reconciliation; no food identity strings or names are exported.
- Full bounded native nutrient dictionary labels, nutrient/euroFIR identifiers,
  units, definition uniqueness and legacy canonical-mapping compatibility.
- Nutrient and source-reference joins, duplicate observations, unresolved counts,
  unit consistency, food/energy/portion/LanguaL structures, and explicit-basis
  shapes. Absence of a basis does not invent a denominator.
- Distinct absent/null/blank/dash/literal-zero/numeric/trace/ND/NT/N/less-than/
  unresolved/invalid counts and lexical shape counts. No quantity is converted,
  imputed or replaced with zero.

CIQUAL:

- Bounded ZIP/package/relationship inventory and workbook feature counts, all
  sheet labels/dimensions, shared-string/styles/number-format evidence, formulas,
  merged/hidden structures and unsupported-feature holds. Formulas are never
  evaluated and external relationships are never followed.
- First-sheet ordered header labels, exact decoded-header hashes and ordered
  header-sequence hash, literal unit suffixes with unverified semantics, per-column
  cell-type and qualifier counts. No canonical metric mapping is inferred.
- Column-7 identity type, leading-zero/float/missing/duplicate diagnostics,
  column-8 name presence, and identity-set reconciliation with XML.
- Observed XML envelope/namespace/entry/field schema and duplicate/missing/type
  diagnostics. The synthetic ALIMENTS/ALIMENT envelope is not imposed on the real
  file. Food rows, names, codes and XML text values are not exported.

Structural labels are retained when safe; they are the evidence needed to review
real dictionaries. Arbitrary source prose, URLs, food values and exception text
are excluded. `sanitize_report` and source-specific closed-schema validators
check evidence again before persistence and transport. Unknown or over-budget
shapes are held explicitly, with incomplete evidence never promoted to success.

## Bounds and delivery

Each isolated `-I -B` worker has 1 GiB address space, 90 CPU seconds and 100 wall
seconds. There is only one active source worker at a time. It inherits the survey
lock and remains in the dispatcher's process group for cancellation. A worker
alarm also bounds an orphan. The fixed Python audit guard denies network,
subprocess/native-library operations and filesystem writes; this is not an
OS-enforced network proof. The receipt says so.

Input reads are anchored directory-descriptor reads with no symlink traversal,
regular-file/single-link/size checks, read-only mount verification, stable inode
and ancestry checks, and exact SHA-256 checks. Verified in-memory bytes are the
bytes supplied to the parser. No temporary raw bundle or cloud raw copy exists.

Limits include 32 MiB per selected asset, 64 MiB per source bundle, 10,000 food or
worksheet rows, 128 workbook columns/members, 96 MiB expanded ZIP bytes, 32 MiB
per XML member, XML depth 40 and one million XML elements. Source result caps are
32 KiB each, combined survey evidence 96 KiB and the fixed profile's outer receipt
128 KiB. Existing Foo profiles retain their 32 KiB receipt limit.

An invocation writes immutable `started.json`, `NO.json`, `FR.json`, then
`report.json` beneath its new operation directory, with file fsync and atomic
linking. Country results are durable before the next worker begins. Existing
reports are never overwritten. There is no accepted-pointer rollback to perform:
no candidate or accepted state was touched. A retry is a new read-only invocation.

`surveyComplete` means the selected structural evidence was fully inspected.
`status: held` may coexist with complete evidence when a compatibility issue was
observed. The CLI exits 0 for complete survey evidence, even with explicit
compatibility holds; it exits 2 for incomplete evidence. The dispatcher requires
validated evidence to establish success; an incomplete survey is `blocked` and
the batch is `incomplete`. Neither state means a source/country is complete,
accepted, public, or safe for all downstream uses.

Original acquisition time is unknown in the pinned historical acquisition
schema. It remains null. The minimum reuse preference is 30 days, but no age or
freshness is invented from mtime, hash verification, rebuild time, or a 304/200
observation. No online request or revalidation is implemented here.

## After the survey

Current Norway and CIQUAL adapters still reject historical scope. Shared registry
admission is still Norway authored fixtures only. The CIQUAL fixture's 73-column
map and XML envelope are authored examples, not independently verified publisher
schema. Existing legacy collector code establishes historical field assumptions,
not their compatibility with these actual bytes.

A later candidate slice needs independently reviewed real source contracts,
complete dictionary/unit/basis/qualifier and identity checks, source-operation
rights and provenance, separate exact input/dependency/runtime pins, and an
appropriate offline boundary. It should extend the existing registry and shared
cache/checkpoint/atomic candidate lifecycle rather than invoke legacy collectors
or add a new pipeline. Original acquisition observations stay outside semantic
content/build identity. Acceptance, public export and country/registry completeness
remain separate decisions.

## Focused verification

```sh
python3 -B -m unittest discover -s tests -p 'test_refresh_survey*.py' -v
python3 -B -m unittest discover -s tests -p 'test_foo_schema_survey.py' -v
python3 -B -m unittest discover -s tests -p 'test_foo_delivery_diagnostics.py' -v
```

Fixtures cover actual synthetic schemas, useful dictionary export, qualifier and
identity distinctions, real-shape survey compatibility, input pin/read-only
failures, independent country continuation, CLI/profile routing, bounded closed
report export and immutable output. Real source bodies have not been copied into
this checkout or surveyed here. The real schema result will come from one Foo run.
