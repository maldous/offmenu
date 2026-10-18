# Bounded media preparation

`offmenu.refresh.media_preparation` prepares explicitly admitted, already received originals. The fixed global collection command owns the complete country/shared-source inventory, current custody checks, exact source selection and execution on Foo. This module has no acquisition, credential, scheduling, publishing, normalization, translation or gold-admission capability. Originals and derivatives remain on Foo. Only closed metadata receipts leave the runner.

## Contract and caller interface

The machine-readable contract is `schemas/media-preparation-contract.schema.json`. `validate_contract` is dependency-free runtime enforcement of the same closed fields, with additional cross-field/observed-format checks.

Call `prepare_asset(asset_contract, original_path, output_dir, absolute_deadline, maximum_output_bytes=remaining_global_output_budget, minimum_free_bytes=88418025472)` once for each admitted member of the one fixed global manifest. `absolute_deadline` uses `time.monotonic()`. It is clamped to 300 seconds per asset. The caller keeps a final-report margin outside that deadline. There is no per-country script and no manifest discovery from filenames.

Required fields:

- `schemaVersion`: `offmenu-media-preparation-contract/1`
- `assetId`: reviewed stable asset identity
- `expectedSHA256`, `expectedBytes`: exact verified received-original identity, filled from the successful immutable acquisition receipt for a new original; never guessed from a filename
- `expectedMediaTypes`: reviewed canonical MIME candidates; actual media is inspected separately
- `permissions`: independent exact booleans for `read`, `extract` and `copy`
- `holds`: preparation-stage codes `read`, `extract`, `copy`, `all`
- `parameters`: reviewed format parameters, or an empty object where bounded all-discovered defaults apply

Read/all holds or false read permission return before opening, statting or creating paths for the original. Extract/copy holds still allow an independently permitted whole-original integrity/media check; they do not allow unpacking or derivative output. These holds contain only restrictions applicable to preparation. The caller separately preserves every unrelated downstream normalization, translation, commercial-use, redistribution and gold-admission hold and its provenance. A download/private-custody approval alone does not establish read/extract/copy permission.

The production caller binds the original path beneath its already admitted Foo custody/cache tree and the output directory beneath its fixed Foo derivative tree. The module rejects symlink components and requires a private, owned output directory; it never uses source filenames as filesystem paths. Test fixtures use private temporary directories. Contract/file paths are not user-supplied runtime override channels.

## Storage and time budget

The fixed caller physically reserves the remaining global derivative budget before extraction and releases only its own reservation after completion/failure. It passes that same remainder as `maximum_output_bytes`, at most 256 MiB; this is a total across all derivative files for the asset, not a per-file allowance. The whole global command separately decrements that remainder for retained derivative receipts.

Every derivative block write checks available space against the live `minimum_free_bytes` floor plus the block size. The default is the existing 88,418,025,472-byte planning guard, which already includes the 20 GiB floor; do not add the floor twice or represent this historical guard as a measured universal reservation total. Synthetic tests explicitly replace the floor with zero or simulate insufficient capacity. No exception deletes or rewrites the original. Any parser/output failure remains non-ready.

Full-original hashing checks size, identity, SHA-256 and pre/post-read deadlines, including EOF. Original identity is rechecked after parsing and before final receipt. The parser subprocess has a hard deadline, CPU/memory/file-size limits and a process group so Poppler descendants can also be terminated. There is no shell invocation or source-script evaluation. Python parsers have network socket creation disabled; Poppler has fixed executable paths and fixed argument shapes. Its input is the already received PDF on stdin; it never fetches a URL. Nonblocking stdin/stdout multiplexing bounds captured output by the caller's remaining derivative budget without pipe deadlock. A confirmed session handshake permits cleanup of parser descendants even if the worker leader dies under a resource signal.

Hard caps:

- Original hashing: 1 GiB; parser input retained in memory: 128 MiB
- Derivative total: at most 256 MiB or caller's smaller remaining budget; at most 513 files (512 members plus private index)
- Archive members: 512; expanded total: 128 MiB; one member: 32 MiB; ratio: 200:1
- Archive central directory: 512 KiB before allocating ZIP member structures
- Pages: 2,000; sheets: 256; records: 1,000,000; cells: 5,000,000
- XML elements: 2,000,000; depth: 128; DTD/entities rejected before parsing
- One CSV field: 1 MiB; one JSONL output record: 4 MiB
- Parser address space: 768 MiB; runtime: at most 300 seconds and the shared global deadline

## Supported structural handlers

| Media | Preparation | Fixed/default parameters and limitations |
|---|---|---|
| PDF | Page-indexed text JSONL | All discovered pages by default; installed `pypdf`, otherwise already installed `/usr/bin/pdfinfo` + `/usr/bin/pdftotext`. Parser name/version, discovered/selected pages and possible OCR need are reported. No rendering, OCR, layout/table reconstruction or embedded-script execution. Encrypted PDFs remain unsupported. |
| CSV/TSV | Row-indexed arrays of source strings | Explicit `encoding`, `delimiter` and `hasHeader` required. Strict decoding/quoting and consistent row widths; no delimiter/encoding guessing. Blank rows omitted, strings and leading zeroes preserved. |
| JSON | Strict validation, record count, byte-preserved derivative | Explicit `jsonRecordPath` (empty list means root). Duplicate keys/nonfinite numbers rejected. Selected list length or one object counted; original JSON number representation is preserved byte-for-byte. |
| XML | Safe structural validation, record count, byte-preserved derivative | Explicit local `xmlRecordTag`; UTF-8 or BOM-marked UTF-16. DTD/entity declarations rejected. No XSLT, external-entity fetching or schema-network resolution. |
| HTML | Ordered text-node JSONL | Strict UTF-8/BOM UTF-16 unless an explicit supported encoding is given. Scripts/style/noscript/template text omitted; links/resources never followed. Recognizable HTML error pages are rejected even when HTTP claimed success. This is source text extraction, not recipe parsing. |
| XLSX | Ordered sheets/rows/cells JSONL | All discovered sheets by default. Bounded ZIP/CRC validation, safe XML, shared-string lookup; original scalar text, source types, coordinates and formulas retained. Formulas never evaluated; dates stay source serials; external workbook relationships rejected. |
| XLS | Ordered sheets/rows/cells JSONL | Already installed `xlrd` only. All discovered sheets by default; original cell types/scalars and cached formula results retained. No formula evaluation or date normalization. |
| DOCX | Ordered textual-part paragraphs JSONL | Main document plus headers, footers, footnotes, endnotes and comments. Safe bounded ZIP/XML; embedded objects never executed. Paragraph text is structural preparation, not document interpretation. |
| ZIP | CRC-verified unpacked members and private index | Member bytes use content-hash filenames; source member names exist only in the private index. Never recurse into nested archives. Members still need individual media/parameter contracts; the container is explicitly non-ready for source processing. |

Archive checks reject absolute/traversal/Windows paths, duplicate casefolded names, symlinks/special entries, encrypted members, unknown compression, macros/executable-script members, oversized metadata, excessive expansion, and CRC corruption. They never extract to a member-supplied path. OOXML inspection before extraction reads only bounded container-directory metadata.

Recognized GZIP/BZIP2/XZ/7z/RAR, legacy DOC, SQLite, Parquet, ambiguous OLE and unbound plain text are explicit unsupported outcomes. Recognition does not imply a handler. No parser is installed to hide a missing capability. `capabilities()` reports the actual runtime's installed `pypdf`/`xlrd` availability and probes the fixed installed Poppler binary's version without reading source bodies. A historical report that native jobs used Poppler does not prove the current runner has it.

`pageStart`/`pageEnd` and zero-based `sheetIndexes` can narrow extraction only in a reviewed contract. Any subset is explicitly non-ready with discovered/selected extent counts. All-discovered is the default and does not require a human to enumerate page/sheet counts beforehand. Cap failures remain non-ready, rather than pretending a truncated selection is complete.

## Sanitized stage receipts

The result schema is `offmenu-media-preparation-result/1`. It reports:

- Exact asset/contract identity, passed original hash/bytes and actual inspected media evidence
- Separate integrity/media/extraction states: passed, held, unsupported, failed, or not-run
- Closed error code, fixed handler/parser version, selected extraction parameters and finite bounds
- Numeric page/sheet/row/cell/member counts and possible OCR need, where established
- Content-addressed derivative IDs, SHA-256, bytes and closed format labels
- Next structural stage and `nextStageReady`, with explicit zero-network/no-normalization/no-translation/no-gold facts

It does not contain source text, header values, sheet names, archive member names, local paths, URLs, credentials, parser exception strings or extracted data. Parser stdout/stderr are suppressed. Poppler's raw metadata output is consumed only inside the private parser worker; only page/encryption facts are used.

`status=ready` means the admitted source has completed this structural stage and can proceed to source-specific processing under a separate applicable contract. It is not complete country coverage, accepted recipe/nutrient records, table semantics, normalization, translation, commercial reuse, redistribution, or gold readiness. PDF pages without text yield `pdf-ocr-required` with `ocrNeeded=possible`; OCR is not run. ZIP yields `member-contracts-required`. Both can retain checked private extraction outputs while remaining non-ready.

## Verification

The module reuses the existing `refresh.core` canonical JSON, strict JSON, SHA and safe-path primitives. Its archive safety derives from the reviewed `acquire-fixed-zenodo.py::validate_xlsx` limits and immutable validation pattern, extended with central-directory allocation bounds, member-type checks and no filename-based extraction.

Run `python -m unittest discover -s tests -p test_media_preparation.py -v` from the composed source tree. Tests use authored synthetic bytes only. They cover all text/OOXML/container paths, positive two-page PDFs, pypdf-absent Poppler fallback, genuinely unavailable parsers, exact hold behavior, content/receipt separation, traversal/symlink/ratio/member limits, unsafe XML, HTML error bodies, output identity/deduplication, live storage-floor failures, global output remainders, process deadline cleanup, and slow final-read deadlines. No production source bodies are needed or opened by the tests.
