# CIQUAL synthetic adapter

Status: independently reviewed, authored synthetic-only candidate. This repository slice remains separate from the shared refresh runner. The package implements
the second national pilot in the recovered design. It does not enable historical
source inputs, acquisition, acceptance, public export or production changes.

## Verified source contract

The private repository's `scripts/collect-national.py:ciqual` was read at
commit `208d7b2dff1a844925996ebbf60278dd627b0bf2`. Its bytes match the recovered
design's pinned collector. The two unchanged files in `tests/fixtures/ciqual-reference/` are regression
evidence, not scripts to run as a batch:

- `collect-national.py`: 9,061 bytes, SHA-256
  `3f1140b6809d4909a8be415ad51a67ee6677ad57c17d580ec5fbda57edc196e5`
- `import-national-tables.py`: 8,953 bytes, SHA-256
  `99216f9ed0aa279b0e15b194c2782dcd8548b86362ea9c55038ad287162cf6c8`

The collector's actual CIQUAL inputs are
`Table Ciqual 2025_ENG_2025_11_03.xlsx` and `alim_2025_11_03.xml`.
It reads the English workbook's first worksheet, uses column 7 as the food
code and column 8 as the English name, and joins XML `alim_code` to obtain
`alim_nom_fr`. Nutrients begin at column 10. Canonical metric positions are
retained, including separate `protein` and `proteinNx625`; unknown components
remain `ciqual:column:N`. The existing basis is 100 g, as-described, source edible
portion. There is no nutrient conversion. CIQUAL country applicability is FR;
that does not establish complete French coverage or dietary suitability.

The observed source notice is `Etalab Licence Ouverte 2.0`, attribution is
`Anses. 2025. Ciqual French food composition table.`, and the collector's source
URL is https://zenodo.org/records/17550133. These are retained source metadata,
not a fresh legal/source-use review.

`docs/evidence/ciqual-synthetic/source-evidence.json` records links and historical comparison pins. The recovered
design explicitly did not parse or independently hash raw national bodies. The
historical workbook digest is receipt-reported; its size and the XML size/digest
remain unestablished here. The prior manifest is 1,930 bytes with SHA-256
`df4df008991e573c1a0f23111611b5fff2f68b62640546d9bb0360fe760cf9ab`.
Its reported 3,484 profiles are not this candidate's measured count.

## What this package does

The implementation is isolated under `offmenu_ciqual/`; it does not import or
modify the shared refresh core, runner, Norway adapter, common-data graph,
accepted pointers or consumer integrations. It uses only the Python standard
library at runtime. The legacy parity test uses the repository's already-pinned
`openpyxl==3.1.5`, which was present; no package was installed.

The XLSX reader is a deliberately narrow OOXML value reader, not a general Excel
engine. It supports the fixture's single worksheet, inline/shared text, and
numeric cells. It rejects formulas, external relationships, unreviewed number
styles, extra worksheets, unsupported cell types and extensions. General/default
styles are the only permitted format, avoiding silent date/percentage conversion.
Root package/workbook relationships, content types and required string/style
dictionaries must agree. Duplicate semantic containers and nested/ambiguous scalar
text or numeric content fail closed. All ZIP members are inspected in memory, with no extraction. Duplicate/unsafe
member names, links, binary/macro parts, encryption and unsupported compression
are rejected. Bounds are 64 MiB compressed archive, 128 members, 32 MiB per XML
member, 96 MiB expanded total, 1000:1 compression ratio, XML depth 40, one million
XML elements across the archive, 10,000 worksheet rows, 128 columns and 4,096-character
text values. Every XML parser rejects DTDs and processing instructions, including
UTF-16 DTDs; external entity resolution and network fetching are not implemented.

Before interpretation, the adapter verifies exact SHA-256, nonzero size, role and
release `2025` for both source files and a third required `ciqual-columns.json`
dependency. It verifies all four implementation/contract files and the pinned
Python/Expat/zlib runtime. Reads use anchored directory descriptors and reject
symlinks and non-regular files; the verified bytes are the bytes parsed. Extra
input-directory files are not discovered or hashed.

The additional column dictionary is authored synthetic test data. It explicitly
pins the entire 73-column header sequence, 64 nutrient names/positions, units,
native-to-canonical mapping and basis. Its complete content must also match the
versioned fixture contract. Reordering a header or changing its definition,
denominator or unit fails even when the input files are rehashed. No real CIQUAL
header dictionary or XML envelope has been observed in this task. The fixture's
`ALIMENTS/ALIMENT` envelope is a test choice, not a claim about the actual XML.

Workbook and XML identities must each be unique and have exactly equal sets.
Equal counts alone do not pass. Text identity leading zeros survive. Numeric
identity floats and ambiguous identities fail instead of being coerced. Missing
names, orphan rows, duplicate XML fields and unreviewed XML fields are held.
All identity/column metadata is retained in `source-metadata.json`.

Missing/blank/dash, trace, ND, NT, present-without-amount, less-than bounds,
unresolved text and literal zero remain distinct. Non-finite values and nonzero
decimals that would underflow to binary zero fail, including raw numeric XLSX
cells before conversion. Malformed or unsupported qualifier syntax remains
explicit unresolved source text, never a manufactured amount. No unknown is
replaced with zero.

Output is deterministic `normalized.jsonl.gz` with one-element arrays per line,
native source metadata and a content manifest. Candidate identity/data and
static source provenance are compared against actual AST-extracted legacy
functions on the authored workbook/XML fixture. Legacy live timestamps, public
visibility and broad complete-release claims are intentionally not reused.
The source inventory digest is named `inputBundleSha256`, not a single archive
hash. Input declaration order, local path and filesystem mtime do not affect
content. Cooperative writers use a lock and atomic staging rename; retry verifies
every existing byte. No failed parse creates a candidate.

The three synthetic profiles are normalized candidates. Accepted count is null,
acceptance is not performed, public export is disabled, and selected-scope,
country and registry completeness remain false. Only execution and the selected
locked input set can be complete.

## Reproduce from a source checkout

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p 'test_ciqual*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest discover -s tests -p 'test_ciqual*.py' -v
PYTHONDONTWRITEBYTECODE=1 python3 scripts/run-ciqual-synthetic.py --output /tmp/offmenu-ciqual-candidate
```

The output parent must already exist. The repository CLI accepts only the checked-in
synthetic inputs and frozen lock. It exposes no arbitrary input, historical,
acquisition, acceptance or shared-runner option. An identical retry verifies
every existing candidate byte. The default rejects a different runtime. To test
these same pinned synthetic fixture and implementation bytes on another runtime,
explicitly add `--repin-synthetic-runtime`. Only the in-memory runtime pin changes;
the frozen lock stays untouched and the build key may differ. The scope label and
runtime option are trusted-caller test declarations, never a source-access grant.

There are 61 adapter tests plus repository integration tests. They cover legacy
parity using the existing `openpyxl==3.1.5` test extra, qualifier distinctions,
underflow, dependency closure, identity/header/unit/basis drift, unsafe XML/ZIP/
OOXML, duplicate or ambiguous containers/scalars, discarded mixed text, deterministic
locations, immutable retries/corruption, simulated pre-rename interruption,
historical rejection before reads, reuse boundaries, and audit-hook-denied
network/process/native-library operations. Independent malformed-input probes
also fail closed. Only approved `candidate-v3-A` and `candidate-v3-B` goldens are
retained under `docs/evidence/ciqual-synthetic/approved-artifact/`.

The four approved implementation files are byte-identical to the reviewed
artifact. The test fixture helper and legacy reference files are relocated to
CIQUAL-specific paths; the test logic is unchanged. The root README, dependencies,
existing core/runner/ledger/grant/Norway files are unchanged. `MANIFEST.in` retains
the Norway contract inclusion and appends the CIQUAL contract. Existing `offmenu*`
package discovery includes the library; no installed console command is added.
See `docs/evidence/ciqual-synthetic/verification-summary.json` for measured checks
and the partial-checkout baseline limitations. The original source manifest is
immutable provenance; its pre-review status is superseded by that summary.

These tests are not a real-source run, an OS network/DNS sandbox proof, a complete
Excel implementation, a full interpreter/distribution provenance lock, full
hostile-output-filesystem confinement, crash/power-loss durability proof, or
shared-consumer/schema qualification. Runtime versions and local code pins close
this reviewed package, not every standard-library binary or OS component.

## Acquisition evidence and the historical gate

Acquisition/revalidation evidence is separate from semantic content. The pure
`plan_reuse` helper recommends verified retained input for less than 30 days from
the original acquisition and reports revalidation review needed at 30 days. A
304 or identical-body 200 never resets that acquisition age. This helper neither
fetches data nor verifies retained bytes, rights, HTTP caching directives,
withdrawals or retention expiry. The included acquisition evidence is synthetic.

Only the exact `synthetic-fixture` scope is enabled. That scope label and the
fixture-lock authoring helper are trusted-caller test declarations, not proof of
origin or an access grant. Relabeling historical bytes as synthetic to bypass
authorization is forbidden. A matching hash or acquisition receipt does not
authorize parsing or reuse.

Before historical enablement, the separate approved read-only snapshot must
provide both real files and bounded receipts. Verify actual hash/size/release,
the selected operations' source-use rights and exact notices, true header/unit
definitions, XML schema and all needed mappings/dictionaries. Reconcile the
historical pins and prior manifest without assuming equality. Change the
contract only through explicit source review; never weaken a test to admit
unreviewed bytes. Then add a separately reviewed historical-input scope and
runner integration, execute two offline candidates under its OS network
boundary, and qualify semantic drift and common-data consumers. Acceptance is a
separate decision and the prior accepted pointer must remain intact.

This slice stops at independent synthetic review. Fineli access/zero-semantics,
Danish definition/basis boundaries, production holds and CIX are unchanged.
