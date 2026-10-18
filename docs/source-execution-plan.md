# Historical source execution plan

Baseline: develop `5cfb4f7d4346b06d58b82ec7d3e2c8dd5d5fedb3`.

Five offline adapters are implemented and tested with authored synthetic workbook
inputs: AFCD 3, MEXT corrected March 2026 main table, CoFID 2021, BLS 4.0 and
Sweden 2026-07-01. They call existing Git-blob-pinned source handlers, rather than
inventing new nutrient mappings. Parser implementation is not production admission.
There are currently zero production admissions and zero accepted datasets.

`execution.execution_plan(coverage)` consumes the existing exhaustive coverage
object and emits exactly one row per source, including all 1,303 discovery rows.
It preserves holds, distinguishes parser availability from admission, exposes
missing-input errors, budgets, family reuse and a minimum 30-day TTL. Generate the
full metadata plan on Foo alongside the coverage receipt; do not copy inventories
or payloads into Git. No source URL is synthesized from country or language codes.

## Execution boundary

`execution.execute` only accepts a source in the code-owned ADMISSIONS registry.
Each addition needs exact input filename/byte/SHA-256 tuples, verified custody,
release identity, timezone-aware acquisition time, reviewed rights and scope
references, and a positive expected normalized record count. Unknown acquisition
time must remain unknown; neither review date nor current time substitutes for it.
A caller-supplied lock or access grant cannot install a production admission.

The worker is offline, runs in a separate Python process, bounds address space to
1 GiB, CPU to 110 seconds, wall time to 120 seconds, input to 64 MiB and combined
output to 256 MiB, with a 64 MiB individual-file cap. It rejects symlinks, unexpected bundle members, altered pins,
duplicate IDs, wrong source identities, malformed packets and count mismatches.
Output is private staging only. Failed partial directories are not reusable and
must be retained as quarantined evidence or removed through an authorized cleanup.
The audit guard is for reviewed trusted code; it is not a hostile-code sandbox.
A production runner must independently enforce its Foo-only storage boundary.

`reviewed_bindings` supplies cache acquisition, verification, parsing, normalization
and structural validation stages to global_run. It deliberately has no curate,
graph, qualify or accept handlers until those contracts are reviewed. Default
256 MiB job reservations fail closed for these 1 GiB parser processes. A caller
must allocate an explicit 1 GiB job reservation within global memory limits.
Cache reuse checks the acquisition timestamp against the 30-day TTL, rejects future or stale evidence, and reports a bounded acquisition blocker. No refresh/force-download policy silently falls back to a network operation.

## Source-specific requirements

- AFCD: Food-Details.xlsx, Nutrient-profiles.xlsx, Nutrient-details.xlsx. Both
  mass and volume sheets are required; nutrient definition workbook stays in the
  bundle although the old records function only reads the first two. The adapter
  does not claim qualification of definitions. Keep the FSANZ licence, limitation
  statement, attribution and Australia-use notice with any future distribution.
  Custom share-alike applies to AFCD derivatives, not unrelated collection data.
- MEXT: exact corrected main workbook `20260327-mxt_kagsei-mext-000029402_02.xlsx`.
  Main-table projection is not the entire search API or all companion tables.
  Keep special-denominator companions outside the per-100g projection. Preserve
  unknown, trace and parenthesized qualifiers. Current rules allow application
  reuse with attribution/modification notice; paid book/ebook redistribution
  has a separate notification/fee exception and is not approved here.
- CoFID: exact cofid2021.xlsx; all three retained sheets; volume basis remains
  separate. Requires raw custody, release rights evidence and qualification.
- BLS: BLS_4_0_Daten_2025_DE.xlsx plus BLS_4_0_Components_DE_EN.xlsx. Keep source
  method/reference/formula fields and release-specific component definitions.
- Sweden: sweden-20260701.xlsx plus its pinned acquisition.json. The legacy
  collector independently checks the workbook against that receipt. Original
  values must remain unchanged; lossless representation needs exact review.

The version-labelled AFCD/MEXT publisher URLs in SOURCE_LOCATORS were inspected
on 2026-10-18 without downloading workbook bodies. They are not immutable hashes,
license acceptance, or enabled acquisition SourceSpec objects. Public file URLs
require no configured credential in this implementation. Other locators remain
unconfigured rather than guessed from landing pages.

## Remaining historical families

The capabilities registry remains authoritative for all 22 retained releases and
handler blob identities. Every family not listed above remains explicitly pending:

- OFF and Open Prices: streaming compressed JSONL and separately reviewed large
  source budgets; never pass multi-GB bodies through the 64 MiB workbook envelope.
- USDA: ordered SQLite join contract, multiple source CSV files and a larger
  bounded resource plan; presence of normalize-usda.py alone is insufficient.
- CIQUAL and Norway: retained source holds and unresolved native replay crashes;
  no native rerun or fixture-based promotion is enabled here.
- Frida: preserve the four-definition basis/curation restriction.
- Fineli: force-download and zero-interpretation holds remain mandatory.
- CNF: retained 2015 differs from discovery 2026. Do not claim a 2026 adapter.
- FOODfiles: extracted MSI member custody, original archive pin and matrix-specific
  denominators need a reviewed extracted-bundle contract; no installer execution.
- Wikidata businesses: separate network lookup from bounded offline transform.
- Wikibooks live, world recipes and recipe expansion: retain distinct discovery,
  recipe text, quantities and qualification scopes; discovery is not acceptance.
- Overture: bounded parquet/duckdb resources and food-place scope; not menu data.
- FoodOn and QUDT: ontology/unit scope, no inferred food identity or density/yield.
- Any release lacking a handler remains unsupported until implementation review.

AFCD/MEXT historical candidate metadata paths are known on Foo, but their present
size/hash/access and raw custody are not verified. Only the existing nine selected
Norway/France assets have current runner custody, and their acquisition timestamps
are still unknown. Receipt paths and historical counts do not establish raw access.
The D1 resolver invalidation helper is not a raw dataset cache. The 88 source lookup
proposals are not source admissions, translations or canonical equivalence.

## Tests and next review

`python -m unittest discover -s tests -p test_execution.py -v` exercises all five
static handlers with authored XLSX fixtures, plus closed admissions, exact bundle
pins, symlink rejection, bad acquisition times, exhaustive planning and the CNF
release mismatch. It runs no publisher download or production source body.

Before activating any production entry: verify exact Foo custody and timestamps;
review rights and transformation scope; pin complete definitions/companions;
measure the bounded parser on Foo; review semantic qualification and acceptance.
Keep all unknowns and held sources visible in the same exhaustive plan.

## Activation when evidence becomes available

There is no additional owner approval flag in the adapter API. Existing user
authorization covers the engineering and permitted same-scope follow-through.
Activation means adding an exact source/release Admission entry to code after
verifying the existing custody/rights/scope facts; it does not itself accept new
legal terms or grant missing filesystem access. If a publisher presents a new
explicit agreement, or the source path is outside granted access, follow those
platform requirements rather than manufacturing evidence hashes. Curate/qualify/
accept handlers remain actual unimplemented work, not an extra consent request.

The companion 22-release permissions evidence is frozen at SHA-256
ca2bac237e73124a1a60c02a6c53256351742fe99fd76c6a976139a9ce1c8ae7. It separates
discover/fetch/retain/parse/transform/serve/redistribute permissions and lists
conditions and publisher URLs. The custody plan separately identifies known
manifest locations and current selected-view evidence. Join these by source ID
and exact release, never by country or an unversioned publisher family alone.

Direct execute() is an explicit offline historical normalization operation, not
a fresh-cache claim: old acquiredAt is allowed, future acquiredAt is rejected.
The global-run factory implements fresh reuse and rejects timestamps beyond its
30-day TTL. Any future checkedAt/revalidation timestamp must be separately backed
by a verification receipt and must never overwrite original acquiredAt. Expired
cache is not an instruction or permission to download automatically. Exact-source
loading ignores legacy .pyc caches for both the handler and pinned dependencies.
