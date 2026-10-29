# Retained product-source candidate adapters

`offmenu.refresh.product_adapters` parses local immutable inputs only. It does not
fetch, register production admissions, execute runner jobs, accept a release,
change permissions, export public data, or claim country completion. Large/raw source custody remains exclusively in the authorized Foo workflow.
Synthetic/small metadata placement follows reviewed runner capacity, locality and
latency policy; tests generate small synthetic sources. Resource limits are explicit caller-owned configuration.

## Evidence and supported formats

Baseline: `d8e212fb7927e4dca0610e974be97076679c1e32`.
Historical handler evidence retained in `offmenu/refresh/capabilities.py`:

- OFF release `2026-10-12`: `scripts/collect-jsonl.mjs`, blob
  `3116933b6444871f2f437ccc1e9f48d414db9c51`: gzip JSONL product dump.
- Open Prices release `2026-10-12`: same handler, prices gzip JSONL plus required
  locations and proofs gzip JSONL. This adapter checks references against both
  related exports, avoiding in-memory location maps and global identity sets.
- USDA release `usda-2026-04`: `scripts/normalize-usda.py`, blob
  `950bb3d83fbb59149c073a3c7e9a9b672768f1d2`, and historical `collect-usda.py`:
  full ZIP containing relational CSV tables. Every CSV table is retained as original
  strings in private SQLite; supporting non-CSV assets stay in the pinned ZIP.
  Food, nutrient and food_nutrient tables are required; branded_food is optional.

These identify historical format evidence, not verification of current payloads,
rights, licenses or admissions. Source license/attribution and evidence hashes are
explicit configuration; the adapter never guesses or upgrades source rights.

## Contract and output

Call `normalize_products(context, inputs, destination, limits=...)` with
`ProductContext` and role/path mapping: OFF `products`; Prices `prices`, `locations`,
`proofs`; USDA `archive`. Destination must not exist, unless it is a completed
identical contract. `candidate.jsonl` uses one `[record]` packet per line.
`manifest.json` contains exact content pins, supplied acquisition timestamp,
source/release/rights provenance, counts, candidate hash, and `accepted: false`.
`source.sqlite` is private raw staging and MUST NOT be published: raw proof and
contributor metadata are deliberately retained there but excluded from candidates.
The immutable source files remain the authoritative complete originals.

Normalization is deterministic for a fixed contract. Per-source sharedSourceKey
includes inputs, source/release, policy metadata, bounds and adapter version; there
is no country-specific adapter/cache identity. Country consumers reuse one source
artifact. OFF country tags are preserved unmodified, with no guessed ISO mapping;
USDA records retain US source scope and original market_country separately.
Prices use supplied ISO-like location country codes without enlarging rights.
Cache TTL cannot be less than 30 days; the adapter never downloads or forces refresh.

Original nutrient numeric strings, units and duplicate observations survive.
No unit conversion is guessed. OFF raw nutriments survive in the product candidate,
with selected explicit `_100g` fields projected. USDA duplicate nutrient observations
have distinct observation-suffixed keys. Prices preserve `duplicateOf` rather than
silently discard rows; qualification/projection policy must explicitly decide their
use. Price amounts preserve original values alongside numeric projections.
Source assertions remain unverified; nutrition bases and regional joins require
source-specific qualification. OFF revision and modification values are retained
as source provenance, without claiming factual freshness.

## Failure, bounds and reuse

Global duplicate IDs, malformed JSON/CSV, unknown nutrient definitions, orphan food
or price references, nonfinite numeric values and unsafe archive paths fail closed.
No sample or quarantined subset is mislabeled complete. Limits cover compressed
input, expanded bytes, record bytes (including multiline CSV before accumulation),
rows, output, SQLite pages, archive metadata/member count and nutrients per food.
ZIP central-directory metadata is bounded before ZipFile loads it, including ZIP64.
SQLite indexes replace dataset-sized identity maps and joins; memory is bounded by
the configured record/nutrient ceilings rather than total rows.

Failure discards only the new staging tree. There is no automatic retry of corrupt
or rights-blocked sources. Retrying identical valid immutable inputs can succeed;
a complete output is reused only after its contract and both output hashes verify.
Changed inputs, evidence, bounds or corrupted outputs require a new destination or
explicit recovery outside this parser. Interrupted abandoned staging directories
are never promoted. No automatic network retry/download is performed.

## Remaining gates

Production operation still requires independently reviewed exact input pins,
rights and scope evidence, source-specific complete schemas and semantic policy,
expected full IDs/counts, Foo resource/custody authorization and distinct accepted
native/curated/common contracts. Native parser success is not graph readiness.
The default limits support fixture/review runs, not multi-gigabyte release jobs;
reviewed runner budgets must raise them explicitly without changing source identity.

## Evidence/qualification bridge

`product_qualification.qualify_product_candidate` accepts a trusted SourceContract,
exact bundle and parser-role map. Before parsing it checks retain/parse/transform
rights, holds, every file pin and exact nested inventory. Evidence files are never
confused with parser inputs. It retains the original normalization manifest and
writes a distinct `qualification-manifest.json` including the pinned rights and
scope files. Qualification rechecks custody after parsing. A two-record synthetic
end-to-end test shows independently declared IDs/counts pass; altered evidence,
missing rights, held sources, unexpected files and incorrect full scope do not.
This bridge is native-candidate-only and never calls acceptance or publication.
