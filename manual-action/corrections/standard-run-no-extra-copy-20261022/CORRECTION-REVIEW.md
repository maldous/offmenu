# Standard run: no extra derived copy — 2026-10-22

## Result and owner direction
The owner accepts one physical cached source asset plus the actual database representation. The standard `./run` must not silently add another per-snapshot physical database/payload copy. The supplied correction disables that automatic phase and respects supplier aliases that the catalog already identifies as duplicates. It does not claim global deduplication or remove any existing data.

## Seven-file incremental scope
- `plan_runner.py` explicitly passes `materialize_relational_targets=False` for the normal plan, independent of receipt transport.
- `ingest_suppliers.py` skips catalog `disposition=duplicate` using the existing `catalog_skip` reason. This honors already-established same-inode or bounded-small-file byte equality; no new discovery/hash scan is added.
- Two generated test files verify normal-run ingestion, resume, receipts/evidence, absent new derived snapshots, historical derived-file preservation, known duplicate skipping, and historical row/checkpoint preservation.
- `FINAL-INGEST-RUN.md`, `README.md`, and `RELATIONAL-TARGETS.md` truthfully distinguish standard staging-only behavior from explicit optional derived materialization. They do not claim the optional phase ran.

## Preservation boundary
The explicit materializer implementation, mapping, schema and engine opt-in remain unchanged and tested. Existing staging/source state paths, adapter versions, source fingerprints, record keys and cursors remain unchanged. Existing derived databases/manifests are neither opened for cleanup nor deleted, moved, repaired or reported as newly produced by a normal run. Cross-domain staging representations are not merged. Previously ingested duplicate rows are not purged. Large uncatalogued byte-identical files remain unknown; there is no broad hash scan.

## Verification
Focused suites passed: 25 supplier tests (one optional-pyarrow skip), one actual generated `./run` integration test, and 34 standalone explicit-materializer tests. The complete generated-suite result is recorded in `generated-regression-results.json`; raw runner output stays in the local-only log and need not be published.

The integration fixture preserves completed/partial source state, ingests all six acquired families, emits bound readable receipt supplements without a `relational_targets` claim, and creates no derived target. A subsequent code-only run performs no repeated record writes and leaves deliberately seeded historical target/manifest sentinels byte- and mtime-identical. Known hardlink and byte-identical catalog aliases produce one supplier source checkpoint/record, two skips, and zero new writes on repeat. Existing rows/checkpoints remain byte-for-byte represented by the same queried values when their descriptor becomes duplicate.

## Provenance
This is a separate incremental correction after the frozen supplier-budget closure. Its supplier preimage is the budget-corrected source; other preimages match the frozen original published package. `CHANGED-FILES.json` binds each before/after SHA-256 and the preceding budget manifest. Neither prior manifest is rewritten. Independent review is recorded separately against these exact hashes.

No live Foo execution, retained-data cleanup/deletion, acquisition, project branch mutation, or network publication was performed while preparing this correction. Test Git operations use generated temporary repositories only.
