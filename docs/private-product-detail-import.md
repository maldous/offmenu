# Private product-detail import boundary

This is the selected import-only extraction of corrected source commit
`63dd92023c498b55a01711f0e1158c79fdd82a77`, based on accepted
`6431ddd417a746c9fe661230a9cb636b0375adce`. The eight writer definitions and
twelve reader definitions initially preserved their exact reviewed ASTs. The
production namespace binding imports `product_detail_import_readers` as `readers`.
The PR85 integrity correction added transaction/FK preflight. The continuation
change shares the asset writer between two explicit public APIs and preserves
the reviewed source-coordinate/row-writing rules. It also preserves callback
exceptions in the OFF/USDA reader boundaries. The source schema and
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


## Explicit closed-checkpoint continuation

`resume_existing_product_details(db, assets, *, checkpoint_receipt,
checkpoint_sha256, scan_asset_once, limits, generation_id,
input_manifest_sha256, operation_selection_sha256,
identifier_database_sha256, coverage_scope)` is separate from
`ingest_product_details`. The original API continues to require a new empty
store. Neither API provides a launcher, actual once admission or source factory.

The trusted reviewed caller supplies the **entire original ordered manifest**,
its original digest, generation and identifier database selection. It must
independently select the exact closed checkpoint and a genuinely new operation;
never derive authority from fields supplied by the checkpoint or an HTTP request.
`checkpoint_sha256` is SHA-256 of core `canonical(checkpoint_receipt)` (including
its final LF). The selected operation must bind that receipt and all limits.

For both initial ingestion and continuation, `coverage_scope` contains caller
metadata only. Its top-level keys must exclude `identifierDatabaseSha256`,
`assets`, `sourceFirst`, `identifierOccurrences` and `resumeAttempts`. A collision
raises `product-detail-coverage-reserved-key` before any SQL or scanner call,
even if the supplied value matches a writer default. The writer alone owns
these five fields. Continuation compares the remaining stored caller metadata
exactly with `coverage_scope`; it does not silently filter caller collisions.
Unknown caller fields and nested annotations are preserved. This validation
does not repair or relabel any previously created checkpoint.

The receipt has these fields:

| Field | Required value/evidence |
| --- | --- |
| `version` | `offmenu-product-detail-checkpoint/1` |
| `generationId`, `inputManifestSha256`, `identifierDatabaseSha256` | Original selections, exactly matching the API and SQL generation |
| `originalOperationSelectionSha256` | Original generation operation, retained unchanged |
| `resumeOperationSelectionSha256` | New independently selected operation passed to this call |
| `databasePath` | Exact absolute SQLite main path, without symlink ancestors |
| `databaseIdentity` | Closed file `[device, inode, size, mtime_ns, ctime_ns]` |
| `databaseSha256` | Independently selected closed database digest; not rehashed here |
| `coverageSha256` | SHA-256 of core canonical decoded `coverage_scope_json` |
| `state` | Exactly `incomplete` |
| `committedReceipts` | Complete original reader receipt objects in committed asset order, exactly matching SQL coverage receipt hashes |
| `producerTerminal`, `producerReaped`, `writableHandlesClosed` | All true, backed by actual postterminal caller evidence |
| `cleanJournalVerified`, `integrityAndForeignKeysVerified` | All true, backed by independent closed-checkpoint qualification |

These receipt facts are **trusted caller obligations**, not proof that this
library observed a producer exit, consumed an actual once, or hashed/qualified a
real store. In particular, inspect and preserve journal state **before opening**
the fresh RW connection: SQLite can recover a hot journal while opening or first
reading a database. This API cannot reverse an earlier caller recovery. It checks
the selected stable identity, rejects any journal/WAL/SHM sidecar (even cold or
stale), requires DELETE mode, and rejects `loading`, `completed`, `failed` and
unknown states. There is no loading/hot-journal repair mode. A failed prior
incomplete-state update therefore needs a separate reviewed recovery decision;
never change its state to make this API accept it.

Use a fresh idle connection with normal tuple rows and no attachments or caller
TEMP work. A caller transaction is rejected before **any SQL**, commit or rollback.
FK enablement must read back as one. Under its own `BEGIN IMMEDIATE` writer lock,
the API verifies the exact existing schema/index/view definitions, single
original generation, typed counts, coverage/identifier context, original manifest
order, contiguous committed assets, reader EOF/hash/count/source/qualification
receipts and per-asset SQL product/profile/identifier counts. It checks per-row
operation binding metadata, global row totals and foreign keys, then rechecks
file identity before mutation. These bounded SQL metadata checks do not select
old payload JSON, rehash full payloads/databases or open/stat/hash any completed
source body. Independent checkpoint qualification still owns full integrity and
provenance review. SQLite JSON functions are required for binding metadata checks.

Only after those checks does the writer append an attempt and enter `loading`.
It calls the existing scanner/callback only for the first uncommitted asset and
its successors. A reader-complete but rolled-back asset is uncommitted and must
be scanned again; a committed asset is never scanned again. Existing row IDs,
payload bytes, identifiers, coordinates and bindings are unchanged. Per-asset
receipt validation, atomic row+coverage commit, rollback and handler cleanup use
the shared writer engine. No DDL is executed against the existing database.

## Operation lineage and query selection

The generation's `operation_selection_sha256` remains the original operation
O0. Each old row retains its original `operationReceiptSha256`; each row written
by this call uses the new operation O1. Existing `coverage_scope_json.assets`
remains an ordered append-only committed prefix. The existing coverage JSON also
appends `resumeAttempts`, with one entry per admitted API attempt:

- `operationSelectionSha256`: O1, unique across O0 and all recorded attempts.
- `checkpointSha256` and `previousCoverageSha256`: immutable selected predecessor pins.
- `startedAfterAssetCount`: committed prefix length before this attempt.
- `startedAt`: UTC timestamp.
- `previousExceptions`: preserved previous generation diagnostics.

Prior attempt entries are retained exactly, including attempts that committed no
new asset. Their starts are nondecreasing and within the committed prefix; an
asset belongs to the last attempt whose start is no greater than its zero-based
manifest index, or O0 before any such attempt. SQL row operation bindings must
agree. The new attempt clears current exceptions only after copying them into
lineage; a new failure records current diagnostics normally. Reusing a recorded
operation, a stale checkpoint identity/coverage selection, or an unsupported
state fails closed without a source replay. An API receipt is not runtime once
proof; the supervisor still owns actual once consumption.

On full completion, the caller selects the held RO detail store with the original
`ProductDetailQuerySelection` generation/manifest/O0 and identifier digest, plus
the externally reviewed complete attempt chain and final publication evidence.
The unchanged query returns O0 at generation level and each row's actual O0/O1
binding in `sourceBinding`; coverage includes attempt lineage. Selecting O1 as
the generation operation is rejected. The complete query response remains capped
at 262144 canonical bytes, including lineage; excessive lineage fails the existing
typed bound, without truncation or a cap increase. An incomplete prefix cannot be
selected as a completed query generation.

## Bounds, failure and runtime follow-through

Asset/input-byte/record limits apply to the **full original target**, including
the retained prefix; database bytes cap the whole retained-plus-new main store.
Elapsed time starts anew for this invocation and includes SQL prefix validation;
per-record and reader limits still apply to newly scanned assets. A database
budget below its retained page footprint is refused before scanning. The page
cap is explicitly set from newly selected finite limits and read back, never
silently raised above that selection. OS limits, owned-envelope/journal/free-space
guards, custody and a new once are separate Worker57/Gateway responsibilities.
No source success implies adequate physical capacity, publication or acceptance.

Current-asset failures retain all prior commits. If recording `incomplete` itself
fails (for example a full store), the error escapes and the state may remain
`loading`: no complete receipt or automatic retry/repair is produced. A fully
committed but incomplete checkpoint (such as a late completion deadline) may be
finalized with zero scanner calls after the same validation. Partial target
success is never returned as full success. Publication still requires all original
assets/counts, close/fsync/selected hash/custody/review and caller publication.

The accepted source has no externally requested graceful asset-checkpoint API.
This change installs no signal handler or live-job control. A future continuation
requires observed producer terminal/reap and independently verified closed SQL
prefix; a latest reader receipt is insufficient.

OFF and USDA callbacks now propagate the **original callback exception object**,
including store bounds and SQLite failures, instead of relabeling it as invalid
source input. Input decoding/selection/hash/EOF errors retain their existing
reader error behavior. This fixes future diagnostics and does not establish the
cause of any previously masked producer error.
