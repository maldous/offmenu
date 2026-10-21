# Private partial recipe section cache

`offmenu.refresh.recipe_section_cache.load_cached_recipe_sections` is a separate
cache-only entry point. It reuses `recipe_menu_store.DDL`, `_put`, `_id`, `_hash`
and the existing SQL columns. The full-template/HTML parser and writer are
unchanged. It opens no file, parses no PDF, calls no model and starts no process.

The caller supplies immutable bytes of the reviewed JSONL cache, its contract and
selected page text caches. It independently qualifies current cache custody,
rights, review/operation evidence and accepted adapter/dependency code pins.
Hashes and dataclass instances bind that selection; they do not grant permission
or independently establish the truth of a review/rights document.

## API

All types come from this exact accepted module namespace:

```python
CacheSelection(run_id, records_path, records_sha256, contract_sha256,
               review_sha256, operation_sha256, adapter_sha256,
               expected_records, expected_sections)
SourcePin(source_id, release, pdf_sha256, receipt_sha256, expected_records)
PageCache(source_id, pdf_page, path, sha256, raw)
CacheLimits(max_records_bytes=8388608, max_page_bytes=16777216,
            max_records=256, max_sections=4096,
            max_database_bytes=33554432, max_seconds=30,
            max_steps=1000000)
load_cached_recipe_sections(db, raw_records, contract_raw, *, selection,
                           sources, pages, limits=CacheLimits())
```

`sources` and `pages` are immutable tuples. `PageCache.raw`, `raw_records` and
`contract_raw` are bytes. Paths are locator labels only; the module never opens
them. The native caller reads selected caches through current held RO custody
and checks named/held identities before and after reading. It never reopens a
PDF or invokes the old HTML parser to reconstruct these inputs.

`db` must be an idle caller-owned NEW empty SQLite connection with no attached or
TEMP databases. The caller owns private/exclusive output creation, process and
storage limits, final close/fsync/output digest/custody/publication, terminal
receipt and any later adoption. Never pass the existing83-record database or a
live selected scanner store. The function validates every supplied cache record
and anchor before creating DDL, then explicitly owns a native SQL
`BEGIN IMMEDIATE`/`COMMIT`/`ROLLBACK` row transaction. This covers accepted idle
legacy connections including `isolation_level=None` and Python
`autocommit=True`; it does not rely on Python commit/rollback methods, which can
be no-ops. Python `autocommit=False` normally starts a caller-owned transaction
and is rejected before DDL; an explicitly native-idle connection still uses the
same owned SQL transaction. A
write failure rolls back that row transaction; already-created empty DDL may
remain in the caller's new staged database. Retain the failed stage and report
the exact error; do not silently retry/delete or infer publication.

Before DDL or any write/configuration that can alter database contents, the
loader checks allocated `page_count * page_size` against the byte budget. An
empty schema left after dropped tables can still exceed the budget and is
rejected without repair, shrinking or VACUUM. The requested page cap is the
floor of bytes/page_size (never rounded up); a sub-page budget is rejected.
The requested limit also preserves a stricter existing page cap. The returned
effective `max_page_count` must fit that limit and cover existing allocated
pages before the database is admitted. No cap increase is authorized.

Hard maximums match the default byte/record/section/database/VM ceilings;
`max_seconds` may be selected up to900. Smaller limits are accepted. A shared
wall-time guard covers cache validation and SQL; SQL progress is bounded, handlers
cleared and the caller's SQL length limit restored after the write phase.

## Mapping and grain

The source cache version is
`offmenu-source-faithful-pdf-recipe-section-cache/1`. Its pinned contract must
name that version, JSONL digest and exact record count. Every record must retain
`importReady:false`, `ingredientLines:null`, `orderedSteps:null` and
`quantityInterpretations:null`. Empty lists are rejected, not translated into
unknowns. Source/release/original PDF metadata digest and receipt digest match
independent `SourcePin` evidence. No PDF hash is calculated by this module.

The reviewed two-book candidate has24 records (12 per source),94 sections and48
referenced recipe pages within51 page text caches. Those numbers are selected
expectations, not hardcoded success. Validation checks page pins, source/page
membership, line bounds, Unicode character offsets and section text/digests;
it derives UTF8 byte offsets from the decoded page. Sixteen reviewed anchors have
different character/byte offsets. Both coordinate spaces refer to cached text,
never original PDF byte positions. No layout repair or visual/extraction accuracy
claim follows from cache replay.

The exact reviewed preview mapping is retained:

- One `recipe_source_record` and one `source_recipe_variant` per cache record.
  Source ordinals restart independently per source. Stable internal keys bind
  source/release/PDF digest/cache record ID/ordinal; native_record_id stays NULL.
- `source_payload_json` is the exact JSONL input line, including its newline.
  `parsed_record_sha256` is core-canonical JSON+LF, distinct from raw-line SHA.
  `record_pointer` records the JSONL path/digest/line/UTF8 range/raw-line digest.
  `source_asset_sha256` remains the original PDF metadata digest, not cache SHA.
- `original_title` is exact raw title-section text, not `titleDisplay`. Language
  preserves the original source-document declaration, content-unverified.
  Yield section text is raw; absent yield remains NULL. Quantity lexemes,
  interpretations, native IDs, citations, canonical concepts and region stay
  NULL unless separately qualified by a future explicit contract.
- All94 anchors and derived cached UTF8 offsets remain in variant locations.
  Ingredient/step states are
  `partial-raw-section-retained; granularity-unknown`; zero child rows does not
  assert missing source ingredients or zero logical counts. No granular child,
  menu, concept, citation or region rows are invented.

A release can be `completed` **at raw-section cache grain**. The returned summary
therefore has `cacheGrainComplete:true`, `fullTemplateComplete:false`,
`importReady:false`, `accepted:false`, and null logical ingredient/step counts.
It is not a full-template acceptance, population/release/gold/country completion
or new source-use grant. Attribution, original values/unknowns, licence caveats
and source provenance remain in the exact payload.

## Acceptance boundary

Source selection13402 reviewed the cache contract/locators/preview, not this new
entry point or a database load. Existing64 reviews this exact source delta and
focused generated tests; existing00 owns normal integration. Only a distinct
selected bounded cache-only load may use the reviewed real cache afterward.
The24 cached records, existing83 rows and failed HTML stages are preserved.
Existing26 owns HTML corrections and the separate UniTools adapter. No source
schema migration, parser/version spoof, normalization gate or new framework is
introduced here.
