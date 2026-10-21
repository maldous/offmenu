# Private product-detail import boundary

This is the selected import-only extraction of corrected source commit
`63dd92023c498b55a01711f0e1158c79fdd82a77`, based on accepted
`6431ddd417a746c9fe661230a9cb636b0375adce`. The eight writer definitions and
twelve reader definitions initially preserved their exact reviewed ASTs. The
production namespace binding imports `product_detail_import_readers` as `readers`.
The PR85 integrity correction changes only the writer's transaction/FK preflight;
the other nineteen definitions retain their exact ASTs. The source schema and
version are unchanged:

- `VERSION`: `offmenu-retained-product-detail-store/1`.
- DDL SHA-256: `f85e1696fa46d3c1b268d4969fa0569534ccaa8ade209c1c523c09bbd0046632`.

The boundary exposes the manifest preparation, finite store writer, retained OFF
reader and qualified native USDA reader. It contains no label/component parser,
field wrapper, query/current-observation context, cache decoder, original barcode
display lookup, server, source factory or execution admission. The optional
decimal-comma finding remains visible on held PR84 outside this import boundary.
This extraction does not resolve that finding or merge PR84.

## Namespace and caller binding

Use normal package imports from the accepted checkout selected by the caller:

```python
from offmenu.refresh import product_detail_import as importer
from offmenu.refresh import product_detail_import_readers as readers
```

Construct `importer.ProductDetailStoreLimits`, `readers.RetainedProductShard`,
`readers.RetainedProductLimits` and `readers.NativeProductScanLimits` in these new
namespaces. Old-module dataclass objects do not satisfy the exact type checks.
The existing accepted `SourceContract`, independently selected qualification and
identifier metadata factory remain unchanged; this boundary does not rebuild or
requalify them.

Worker57 must update its actual driver module list, loader/return namespace,
`SOURCE`/`HERE` references and source/module hash pins. Remove eager loading of
the old mixed module and optional label/display modules from that driver path.
This is a real namespace/driver change, not merely replacing a digest. Preserve
the identifier factory and actual rights, held-file custody, resource limits,
once selection and output ownership. Source availability does not prove that the
driver has been updated, selected or run.

## Five-argument streaming callback

The writer still accepts `scan_asset_once(asset, consume)`. Its scanner calls:

```python
consume(packet, productOrdinal, profileOrdinalOrNone,
        identifierRecordOrdinal, sourcePointer)
```

For selected full-source assets, bridge the reader callbacks without collecting
the corpus in memory:

```python
# OFF on_packet(packet, N, code, originalSourceRow)
consume(packet, 2*N - 1, 2*N, originalSourceRow, f"jsonl:packet:{N}")

# USDA on_pair(packet, productLine, profileLine)
consume(packet, productLine, profileLine, productLine,
        f"jsonl:line:{productLine}")
```

The exact source coordinates are preserved per record:

| Representation | Product | Profile |
| --- | --- | --- |
| Full OFF paired packet N | `jsonl:packet:N/0` | `jsonl:packet:N/1` |
| Full USDA singleton lines P and Q=P+1 | `jsonl:line:P/0` | `jsonl:line:Q/0` |

The retained writer also preserves its existing metadata coordinate rules for
paired cache documents and product-only lookup objects. No cache decoder is
installed by this extraction. Each persisted row's `source_pointer` and binding
`recordPointer` identify that row; `recordPointers` lists product and optional
profile coordinates. There is no fabricated `/1` on a singleton USDA line or
appended `/0` on a cached record object. Coordinates/ordinals must agree with the
selected representation and streaming sequence. Record IDs, raw payloads,
canonical pair hashes, manifest meanings and source provenance are unchanged.

## Integrity, failure and publication

The caller must supply a connection with no active transaction. The writer rejects
`db.in_transaction` before issuing any SQL, changing connection setup or invoking
a reader. It does not commit or roll back caller work: pending writes and
savepoints remain caller-owned. Worker57 must pass the selected fresh idle
connection rather than silently committing existing work to satisfy this condition.

Before schema creation, the writer enables foreign keys and reads the effective
setting back. If enforcement is unavailable or a caller policy prevents enabling
it, the writer fails explicitly before creating tables or scanning an asset. A
successful import therefore starts with effective FK enforcement; orphan identifier
references, missing paired profiles and missing generations are rejected by SQLite.

Callbacks remain provisional until the selected reader returns its full receipt.
The writer verifies source/release, bytes/hash, EOF, one body pass, qualification,
source-only original hashes and actual counts before committing an asset. The
USDA receipt excludes rights/scope/clock evidence from original-source hashes.
The OFF reader checks gzip integrity, extent, shard/record linkage and held-file
identity. Both readers enforce finite byte/packet/time bounds.

On a source, receipt, coordinate, provenance or deadline failure, the current
asset rolls back, the completed prefix remains, and the generation is marked
incomplete with measured retained counts. There is no automatic retry, deletion,
repair or acceptance of an existing store. Progress handlers are removed on exit.
Worker57 owns exclusive output custody, OS/aggregate storage limits, final
close/fsync/hash and terminal receipts; independent output review and selected
publication remain separate steps.

The selected full scope remains 256 retained OFF shards plus one qualified USDA
native candidate: 257 assets, 19,991,040,655 declared input bytes, 6,908,496
declared source products and the same number of profiles. These are scope counts,
not loaded output, physical product identity, country completion, Gold admission
or an accepted release. Source-use restrictions and legacy duplicate/quarantine
gaps remain explicit. No actual corpus body, database, fetch or once operation is
performed by this source extraction.

## Focused validation

Run `python3 -m unittest tests.test_product_detail_import -v`. Tests use generated
packets and new temporary stores. They check clean imports without excluded
modules, new typed namespaces, full-source pointer resolution and payload hashes,
receipt/source binding, gzip/native EOF, late hash failure, coordinate/provenance
failure, completed-prefix retention, finite limits and deadline cleanup. Exact
definition/global AST qualification and prior corrected-source proof are retained
in the source handoff; unchanged behavior is reused rather than reassessed as a
new implementation.

Existing Worker64 independently qualifies the exact extracted source/import
binding. Worker00 then creates the honest import-only PR and applies normal
current provider/CI/security/expected-head/postmerge gates. This boundary grants
no approval bypass, runtime activation, production deployment or CIX execution.
