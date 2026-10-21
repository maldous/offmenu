# Private lexical identifier database

`offmenu.refresh.identifier_database` implements one deterministic loader and
read-only query API. It has no network, AI, cloud writer, inventory or profile
population, ingredient resolver, source acquisition or automatic retry.

The schema embeds13's minimal-identifiers-v2 SQL (SHA256
`f3527cdd6cf03c9f6e9448b8dac19ff5e084867213b4699e2fae1e989678e3e4`)
and adds metadata columns plus a unique lexical identifier pool and asset-lineage
junction. The source assertions remain nonunique by identifier. Both
`barcode_identifier_inspection` and13's accepted14-column `v_barcode_inspection`
are actual views in the same database. Unproved product/symbology/context fields
remain NULL. Existing13 tables outside this slice are not prerequisites.

FETCH19 owns citation/asset identities. The caller passes its metadata rows;
the loader copies them with FKs and preserves fetch-bound versus local unresolved
states. Original `usda-archive:2026-04` is retained; release remains2026-04-30.
URLs, licence details and retrieval clocks may remain NULL with unknown reasons.
A PARSE-derived cached-input node is explicitly unresolved, not a fabricated
FETCH identity. Rich backfill, semantic mapping and English/gold are not gates.

## Inputs and actual load

`IdentifierInput`, `IdentifierLimits`, `prepare_identifier_manifest(...)` and
`build_identifier_database(...)` are the reusable typed API. Trusted application
code selects SourceContract/qualification, input manifest and operation receipt.
Constructing those objects or hashes does not authorize an actual body operation.

Full native singleton JSONL is streamed once: each line contributes to the same
held-FD hash and record count while parsing. EOF, exact bytes/hash/count and
pre/post FD/path identity must agree before publication. All source records have
crosswalks, including explicitly nonindexed nutrient-profile records; identifier
assertions come only from product fields. The initial known full USDA scope is
4,202,558 records/18,424,445,399 bytes, including2,101,279 product-kind records.
Those are source record counts, not physical product counts.

The fixed `selected22_input(operation)` adapter supports the already reviewed
34,844-byte cached envelope at `/lookup/matches[*]/record`. It uses the existing
full USDA contract/qualification unchanged, with a separately bound22-observation
input extent and lookup review. One bounded FD read/hash/EOF probe supplies the
JSON parser; it never opens the full candidate, source.sqlite or original ZIP.
Match ordinal, JSON pointer, original candidateLine and sourceRow stay separate.
The wrapper's original bytes have an input asset SHA; canonical record SHA uses
sorted UTF8 JSON plus LF. A wrapper occurrence has no fabricated raw line SHA.

## Exact command entry points

After64 source review and the existing execution selection,57 uses the SAME
module with its pinned control JSON (maximum1MiB):

```sh
python -B -m offmenu.refresh.identifier_database prepare-selected22 --operation /absolute/operation.json --operation-sha256 EXACT_CONTROL_SHA
python -B -m offmenu.refresh.identifier_database load-selected22 --operation /absolute/operation.json --operation-sha256 EXACT_CONTROL_SHA --manifest-sha256 EXACT_PREPARED_MANIFEST_SHA
python -B -m offmenu.refresh.identifier_database query --operation /absolute/completion-receipt.json --operation-sha256 EXACT_RECEIPT_SHA --namespace barcode --limit 25
```

`prepare-selected22` performs control/code reads only. The source packet includes
an actual prepared operation with19's selected rows.57 supplies the real once-run
selection receipt hash; none is invented by the author. Current input identity
can be supplied, or captured at the actual admitted open and retained in the
checkpoint. The parent output directory must already be private0700. Limits are
34,844 input bytes,22 observations,64KiB document cap,2 identifiers per record,
16MiB SQLite,64MiB owned storage and300 cooperative seconds.57 separately enforces
the selected OS RAM/CPU/walltime/FD/file/aggregate storage boundary. No resource
charge or body execution follows from this source preparation.

The selected22 command always marks full USDA and OFF scopes not loaded. It
cannot claim complete corpus,22 physical products or worldwide barcode coverage.
OFF full audit4,807,663 =4,807,278 valid-code occurrences +385 invalid rows is
separate, even after its small-receipt review. A later eligible representation
must retain all61 ambiguous groups/122 members and Q dispositions, never use a
singleton-only/old-clean oracle. No full OFF handler is selected in this slice.

## Lexical semantics and recovery

Namespace rules are explicit/versioned. TEXT/BINARY keys preserve leading zeros,
case, Unicode and whitespace. Numbers/booleans are not stringified; null/missing,
empty and unknown namespace outcomes are explicit. Raw identifier JSON/hash and
field locator retain invalid assertions. An oversized value retains its hash,
extent and original locator rather than a truncated string. NUL is explicit
policy-invalid; no replacement or normalization occurs. Syntax/check-digit
assessment never merges products or establishes GTIN assurance.

Every source occurrence survives, including identical repeats and conflicting
same-key content. Per-asset transactions/checkpoints carry expected/read/unread,
source partition, identifier partition, distinct/new/existing/repeated keys and
exceptions. Exact repeated references to an already completed asset reuse its
checkpoint without another input read or duplicate rows. Held assets refuse
automatic resume. Successful input completeness means accounted input bytes and
occurrences, not qualification of invalid source assertions.

SQLite opens an exclusively created0600 file beneath a private staged directory;
serialized Linux/default-VFS FD attribution binds the actual main handle.
After reconciliation, close/fsync and one bounded final DATABASE hash pass, the
existing no-replace rename helper publishes the file and verifies the moved
inode/signature. No source prehash or source replay occurs. Failures retain
stage/database/journal and explicit held evidence, without deletion or overwrite.
Late publication/sync failure is not success even if a file appears complete;
the external terminal receipt remains mandatory. These are point-in-time checks,
not hostile-process or indefinite custody guarantees.

Queries are parameterized read-only exact/prefix/keyset pages with VM/time/result
bounds. Cursors apply only to that exact immutable database receipt. Invalid and
unresolved assertions remain separately queryable. A result cap refuses rather
than returning a misleading complete answer. Names and identifiers are source
observations; no recipe, nutrition, supplier or user-state join is required.

## Full retained USDA and OFF source audit

`prepare-full` and `load-full` use the same control-file pin, manifest pin,
`build_identifier_database`, private output schema, finite limits and publication
guards. `full_retained_inputs(operation)` selects only `usda-files` and/or `off`;
the operation schema is `offmenu-full-retained-identifier-operation/1`. Each
source supplies its input path, optional identity, FETCH19 citation/asset metadata
and producer-job evidence. USDA also supplies its existing qualification. Limits
are all nine `IdentifierLimits` fields and must be finite positive integers.
Preparing does no input body open/stat/hash. An actual load still requires its
real once-operation receipt and external runtime/resource selection.

USDA uses its unchanged full SourceContract and one streaming hash/parse/EOF
pass over 18,424,445,399 bytes and 4,202,558 packets. The 2,101,279 product
records supply identifier assertions; the 2,101,279 nutrient profiles retain
source crosswalks and counts without hydrating profile contents into this DB.

OFF loads only the complete, independently verified `occurrences.jsonl` audit:
1,656,721,116 bytes, 4,807,663 rows. Its exact hash binds the earlier full
four-file membership verification; the loader does not reopen the original,
retained index, or redundant singleton/member/group sidecars. This metadata
binding has no product SourceContract. Source occurrence IDs use original
artifact SHA plus original ordinal. Original line/body digests, source row,
status and `/code` locator survive in the crosswalk and exception audit.

All 4,807,156 S rows and 122 C members retain their lexical code associations.
C assertions remain unresolved, with no selected primary or physical-product
merge. All 385 Q rows retain invalid-code audits with barcode NULL; the original
invalid value and its identifier hash/extent are unavailable, not invented.
The original line/body digests remain available. Per-asset reconciliation measures
4,807,278 valid-code associations, 4,807,217 distinct valid lexical keys and 61
ambiguous groups, rejects S/C overlap or wrong multiplicity, and keeps Q outside
valid keys. These are source identifier counts, never accepted product counts.

The combined input is 20,081,166,515 bytes and 9,010,221 source records. Exact
completed asset references reuse their checkpoint without rereading or adding
rows; held assets never auto-resume. Full loading uses a new destination and
preserves the earlier selected22 database. Shared exact lexical keys reuse the
identifier entity while every source assertion survives. No ingredient, exhaustive
citation enrichment, UI, English/gold or country-completion claim follows.
