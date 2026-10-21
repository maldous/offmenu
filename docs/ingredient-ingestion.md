# Local ingredient source ingestion

`SourceAsset`, `ImportLimits`, `prepare_source_import(assets)` and
`ingest_source_assets(connection, assets, *, limits, input_manifest_sha256,
selection_receipt_sha256)` import existing locally selected native product
JSONL packets and source dictionary JSONL (plain or gzip). The caller owns a new
private SQLite connection, runtime/custody, aggregate storage limits and final
publication. Existing populated/schema-ready stores are refused. This source
core is not an execution grant or a complete standalone publisher.

The DDL is exactly13's six-table ingredient base, additive product audit, and
shared `retained_reference_record` definition, with exact source hashes in
`SCHEMA_PINS`. No independent schema or framework is introduced. Product raw
JSON lines preserve source text, language, numeric/unit lexemes, native IDs and
provenance. Every eligible source product has an audit row, including missing,
empty, null and invalid-type ingredient fields. Invalid types are quarantined
but retained. Nutrient-profile packets are counted separately and not copied.
Dictionary packets remain source-native cached records, not accepted concepts.

Stable internal IDs bind selected asset ID/hash and occurrence ordinal. Repeated
native keys never overwrite occurrences. Group counts explicitly mean exact
source/release/native record keys, not barcode groups or canonical products.
Per-asset count/hash/EOF and input FD/name checks precede completion. Exact
completed input references may reuse their checkpoint; held inputs refuse.
Failures preserve a held prefix for caller reconciliation, without auto-retry.

Raw import has no selector, registry, context witness, complete citation or
canonical mapping gate. Concept/declaration semantic FKs remain NULL, mapping
pending and composition unknown. Text is not split or mapped by similarity.
Frozen56 selector6b0906 remains unmodified and unadopted; later canonical
contains/is-ingredient/usable_as decisions require its independently accepted
source and actual qualified inventories. That deferred stage is not implemented
by this source-import core.

Actual local inputs, complete product/record denominators, original source/use
and cache lineage, citation pending states, and finite runtime limits must be
selected by the existing owners. No fetching, runtime AI, existing20GB database,
recipe body, user profile or inventory operation is performed by the author.
The two tests use generated local data only.57 must supply a reviewed held-output
caller and final resource/publication receipt before actual corpus execution.
