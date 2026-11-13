# Retained OpenPrices cache contract preparation

This source candidate covers the `prices`/`2026-10-12` retained
`offmenu-collection/1` projection. It prepares metadata and per-record validation
for separate independent review. It neither constructs a `SourceContract` from a
manifest nor admits a real body pass. The source family is **price observations**,
not products, GTIN identity, nutrition, ingredient edges or graph relationships.

## Exact retained selection

Worker57 owns selection10195, held operation/reservation10208 and the single
future body pass. Its existing1GiB reservation remains active and counted once;
this code does not allocate another job or budget. Current source metadata:

- the retained `prices-2026-10-12` manifest, SHA-256
  `a2b5502bcaad9489d9fef02c105f5656666d87f4765fc31c762c72a8028a48e5`.
- 317898 declared retained price observations,256 partitions,30400169 compressed
  bytes. These totals are metadata declarations, not a newly observed denominator.
- Declared original archive SHA-256
  `337f7bc662a8c8f880c457d966fffed7998722b25f2ed460b6194ba01f6653e0`.
  This code does not stat, hash, read or revalidate that original.
- The retained result packet pins the source handoff, operation evidence and all declared
  partition paths/counts/bytes/hashes. All256 current compressed hashes differ
  from historical committed collection metadata. Equal counts/archive assertions
  prove neither content equivalence nor freshness; old gzip pins are not adopted.

The accepted source baseline is `c670fb4aefa90c820bf902f311959871f19b5343`.
The projection is `scripts/collect-jsonl.mjs` with `normalizePrices` in
`apps/web/src/unified-data.js`. It differs from a fresh-source `product_adapters._price`
output; mixing their schemas would fabricate source fields or drop cache fields.

## Minimal API

`select_manifest(raw, expected_sha256)` accepts an already supplied UTF-8 metadata
buffer and an independently supplied expected pin. It checks exact metadata pin,
source/release/status/license/attribution, count reconciliation, price-only kind,
all256 unique canonical shard names and declared byte/count/hash bounds. It
returns an immutable `CacheSelection` with immutable `Partition` values and
`input_assets()` expectations. This does **not** verify the gzip bodies, make
counts independent, or turn a metadata license into permission.

`PriceValidator(selection)` compiles a closed Draft2020-12 schema once.
`validate_line(raw, partition=key, line=ordinal)` takes one bounded, already supplied
UTF-8 LF singleton packet and returns fixed diagnostic codes. It performs no
file/network IO, acquisition, decompression, mutation, output or acceptance.

The source-specific schema and checks bind:

- Exact `priceObservation`/`1.0`, source/release, declared archive hash,
  source record ID and `prices:priceObservation:<recordId>` ID, source logical
  row extent, `offmenu-bulk/1`, ODbL attribution and source rights notice.
- SHA-256 shard routing from the exact source record ID and declared partition
  line bounds. This is not a full-set uniqueness or custody check.
- The exact retained whitelist: amount, currency, date, retailer projection,
  unit price/unit, promotion/discount, regular amount, duplicate/proof identifiers,
  availability and price type. Unknown contributor/comment/image, graph IRI,
  ingredient and invented GTIN-verification fields fail closed.
- Null/zero/false, leading zeros and missing source identifiers remain distinct.
  Missing native amount/currency/date remain null and can pass this narrow native
  assertion check; the historical171 missing currencies and186 missing dates
  are not silently filled or promoted to usable offers. No unit/currency conversion
  or identity resolution occurs. Negative amount, nonfinite values, invalid
  dates, invalid cache clocks, source-date disagreement and nonsingleton packets fail.

The retained `provenance.visibility:'public'` is checked as original projection
metadata without rewriting it. It is **not** permission to publish. All intended
processing/output is private. The `fetchedAt` field is a cache-processing clock;
a valid timestamp does not establish original acquisition, present availability
or current price freshness. Proof/location identifiers remain source assertions;
their existence does not prove a reviewed relationship or authorize reading images.

Manifest bytes are capped at1MiB; compressed input declarations at512MiB total;
individual packets at2MiB. These checks do not replace Worker57's512MiB expanded
stream cap,512MiB heap,600-second deadline,1GiB total reservation, pre/post custody,
full-record count/uniqueness checks or OS resource boundary. The validator is
stateless across packets; repeated lines and aggregate expansion must be rejected
by that owner stream. No duplicate pass is implemented here.

## Accepted SourceContract fit and remaining evidence

The current metadata cannot honestly construct an accepted full SourceContract:

1. There is no current independent sorted unique-ID digest/all-record accounting
   witness.317898 and the partitions' row sums are declared counts. Worker57 owns
   the bounded witness once a reviewed operation is executable; this is not an
   invitation for another worker to read the bodies.
2. Original acquisition time is unknown. Accepted `product_clock.validate_clock`
   restricts `unknown-retained` to OFF/USDA. A cache `fetchedAt`/completion timestamp
   cannot be substituted for original acquisition. A synthetic test reproduces
   `retained-clock-contract-invalid` for prices. A reviewed cache-processing clock
   contract must preserve that distinction before selecting real qualification.
3. Generic `qualify` requires one uncompressed singleton JSONL candidate and its
   complete asset/rights/scope manifest. The existing gzip partitions are not that
   candidate. Separate `input_root` is restricted to private native OFF/USDA.
   No cache copy, new bundle or repackaging pass is smuggled into this source task.
   A minimal reviewed owner-stream/custody bridge remains to be selected.
4. Standing private use is already authorized:57operation evidence10208 and the
   current handoff bind ODbL/source attribution, private retained source assertions
   and exclusion of original/image/user/comment acquisition. Those exact use
   conditions still need binding in the reviewed executable contract; no blanket
   new publisher/human approval is requested, and a license hash grants nothing.

`qualification_gaps()` returns these explicit gaps and false values for
`sourceContractConstructed`, `familyQualified`, `relationshipInputReady` and
`executionAdmitted`. Per-row checks cannot change them. This is useful source
prequalification code, **not resolution of the full real-input dependency10212**.

Worker56 additionally needs a reviewed source-to-existing-IRI/role/context resolver
and actual source-supported relationship witnesses. Those are separate from
price-row schema qualification; no IRIs, relationships or reviewed assertions
are invented. Worker64 field mapping and Worker19 language-neutral mapping remain
their disjoint ownership. the product maintainer schedules the next exact contract/bridge work,
independent reviewer and the product integrator integration. Worker57 executes only after
review/integration and required operation/resource gates.

## Validation and retained boundaries

Run from the isolated checkout:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -B -m unittest test_openprices_cache_contract -v
```

Tests use synthetic256-partition manifests and authored price packets only. They
exercise current-vs-old pin differences despite equal counts, exact inventories,
rights/provenance/kind and source-ID/shard binding, null/zero/false, unknown/private
field refusal, malformed packets, line limits, nonfinite/overflow numbers, date
and clock guards. A pure accepted JavaScript normalizer comparison uses one
authored input; it does not run collection, acquisition or real normalization.

Only three new paths belong to this candidate. Frozen codec9d92b4bf, USDA producer,
runtime/security settings, existing source files and other workers' work stay
untouched. Source/privacy/no-read/custody/actual-denial holds, mandatory auto_review,
and production/CIX pauses remain. This is separate from the held25 review route.
