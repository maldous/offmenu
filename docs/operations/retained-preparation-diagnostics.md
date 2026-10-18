# Retained preparation diagnostics

This optional owner-mode observation covers the exact 22 nonready preparation outcomes in manual result `7e844aae16ed22b088c2643fec3f9722110cdad30b9f0fcc264c2db57eba4795` at commit `3bbb6835568dcc58ff147f8b1c459c5e37dfc3e0`. It does not execute or authorize another acquisition, promote originals, repair documents, change claims, or relax preparation guards.

## Integration

Load `scripts/diagnose-retained-preparation.py` from the verified source. While holding the existing exclusive `collection/fixed-selection.lock`, before acquisition/preparation workers start, invoke:

`run_diagnostics(output_root, min(global_deadline, time.monotonic() + 60), assets=manifest['assets'])`

Only owner mode should invoke it. Add its return as optional `retainedPreparationDiagnostics` in the complete global report before immutable hashing. The pure `sanitize_diagnostics(report)` must validate that field during publication. No new request fields or output paths are needed. The module never writes; the existing global checkpoint/report publisher provides durability. All 22 rows remain in the report if one is inaccessible, held, changed or over deadline. The row indices refer to the pinned prior manifest; asset IDs are the join key if a future manifest reorders rows.

Current manifest read/extraction permission and source-stage holds are checked before opening originals. Missing or duplicate current asset bindings fail closed. Source-specific downstream restrictions remain in the manifest and are not reinterpreted as source-read permission. Original identities, paths and prior detail hashes are fixed in code. Output root is the established owner runtime and UID1000; this is not a generic arbitrary-path diagnostic.

## Bounds and evidence

- At most 60 seconds within the caller's remaining global deadline; sequential metadata operations, no parser processes, threads or network.
- At most 1GiB aggregate original hashing; the exact 22 extents total 692,908,020 bytes. Each read is at most64KiB. Files are no-follow regular-file descriptors with before/after inode/size/time/mode checks, complete fixed-path no-follow re-opening, and exact SHA256 verification. Parent renames and symlink substitutions are reported as changed identity.
- Prior complete result and each full preparation checkpoint are read only by exact content hash, at most8MiB each. No directory scan or newest-file guess.
- ZIP central directory is bounded before construction:512 entries,512KiB directory, no ZIP64/multidisk. Existing member32MiB, expanded128MiB and ratio200 limits are reported as separate closed reasons. Unsafe names, symlinks, special files, encryption, executable suffixes and unsupported compression remain rejection reasons. No archive member is copied or executed.
- Only `xl/_rels/workbook.xml.rels` may be decompressed, capped4MiB,128 XML depth and10,000 elements; DTD/entity declarations are rejected. Counts distinguish external relationships, parent components, backslashes, absolute paths outside `/xl`, unresolved targets and duplicate/missing IDs. No target, URL, member name, XML value or text is emitted. These observations do not establish that a currently rejected relationship is safe.
- PDF facts are recovered from the exact prior full parser detail after re-verifying the current original. This avoids another costly parse and exposes the previously omitted `pagesWithoutText` count. An encrypted flag does not establish that a password is required; `passwordRequired` remains unknown. Blank text does not prove an image-only page, and OCR is never run. Prior parser name is explicitly historical, not a current capability probe.
- BLS ZIP deeper member contracts and USDA streaming preparation remain explicit capability gaps. Metadata may establish which current archive limit applies; it never increases a bound. Inaccessible Swiss/SB/BA paths remain source-specific access outcomes, with no new download or permission change.
- The closed result is at most16KiB. It contains fixed asset IDs, counters, reason enums and verification booleans only. Full source text, URLs, paths, parser stderr and credentials are excluded.

## Limits

A file read on an unresponsive filesystem can block in the operating system despite between-read monotonic deadline checks, as with the existing original verifier. The function must run within the existing global process deadline; it does not expand that deadline. Missing prior private checkpoints result in an explicit unavailable diagnostic rather than an inferred PDF state. No outcomes are marked prepared or ready by this diagnostic.
