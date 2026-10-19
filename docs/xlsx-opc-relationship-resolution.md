# Contained OPC relationship resolution

## Confirmed code defect

The published `c74cfaee` composition contains media module SHA-256 `418b3bb5d006af25a072c5a91628c2ef080008d1ec4a6eea2c0008bf534c2dc5`. Its XLSX workbook-relationship loop concatenates `xl/` with each relative target and rejects every `..` segment. It therefore rejects legitimate internal references such as `../xl/worksheets/sheet1.xml`, even though resolution from the source part `/xl/workbook.xml` stays within the package.

The reviewed run metadata reported seven CoFID/AFCD workbooks with passed integrity/media stages, no unsafe ZIP entries or external relationships, and 30 parent-component targets/unresolved diagnostic lookups. Those aggregate facts are consistent with the code defect. They do not, by themselves, establish which relationship parts contain those targets or prove that this correction will resolve every actual workbook failure. No actual workbook was read in this task.

An authored synthetic workbook reproduces the published failure: integrity and media pass, extraction fails with `archive-unsafe`. The same bytes under the patched module complete all three stages and become structurally ready. Originals are unchanged and network requests remain zero.

## Resolution rule and scope

OPC resolves a part-level target against the owning source part, rather than the location of its `.rels` file. Microsoft's [TargetUri documentation](https://learn.microsoft.com/en-us/dotnet/api/system.io.packaging.packagerelationship.targeturi?view=netframework-4.8.1) describes that base. Its [ResolvePartUri examples](https://learn.microsoft.com/en-us/dotnet/api/system.io.packaging.packurihelper.resolveparturi?view=windowsdesktop-9.0) include both current-directory and parent-directory relative references. The path-merging and dot-segment rules are specified in [RFC 3986 sections 5.2.3–5.2.4](https://www.rfc-editor.org/rfc/rfc3986.html#section-5.2.3).

The small `_opc_target_member` helper applies those path rules to the workbook's existing internal relationships. An absolute package path begins at the archive root; a relative path begins at the source part's directory. Exact `.` segments are removed and `..` removes one parent. The bounded profile intentionally rejects climbing above the package root instead of clamping such attempts. Contained parts outside `xl/` are permitted only when the exact validated archive member exists. This is required for legitimate package-level folder layouts, including internal custom XML parts.

Only relationship references gain dot-segment resolution. ZIP member names still pass the unchanged traversal/symlink/duplicate/CRC/compression/code-member validation before any relationship lookup. No source-supplied path reaches the filesystem. Output paths remain content-addressed.

The resolver rejects external or unknown target modes, schemes, authorities, backslashes, queries/fragments, empty or directory targets, raw whitespace/control characters, malformed percent escapes, encoded path separators/control characters, encoded unreserved URI characters, missing exact members and root-escape attempts. Percent escapes are kept literal for exact ZIP-member lookup and never decoded or recursively reinterpreted. The target reference is bounded at 2,048 ASCII characters. Workbook relationship IDs must be present and distinct to prevent ambiguous lookup.

No external resource is followed, source script executed, parser installed, source body changed, or collection run. This patch does not make the handler a complete general OPC validator or change its existing hardcoded main-workbook/shared-string locations.

## Compatibility and limits

Handler/result/contract versions and emitted structural content stay unchanged. An ordinary previously successful workbook and its equivalent contained-parent-reference form produce identical derivatives, parameters and metrics. Existing valid ready receipts remain reusable; exact current source/module hashes bind the bug fix in publication provenance. This avoids invalidating successful unrelated-format receipts solely because a valid previously rejected path representation is now supported.

All resource, permissions, deadline, shared-storage-lock, original-integrity, archive and derivative limits remain unchanged. In particular: 32 MiB per archive member, 128 MiB total expanded bytes, 512 members and a 200:1 expansion ratio. The separately reported BLS member of 99,582,537 bytes and USDA archive expansion of approximately 3.26 GB still exceed this profile. They remain bounded-limit outcomes and are not repaired by this relationship fix.

## Verification

- All 69 existing media-preparation tests pass against the corrected module.
- 14 new synthetic OPC tests cover source-part-relative resolution, dot segments, package-root paths, contained non-`xl` parts, metadata relationships, root escapes, schemes/authorities, percent ambiguity, exact case-sensitive membership, external targets, duplicate IDs, unchanged archive traversal and unchanged caps.
- Old-form and new-form synthetic workbooks produce identical derivative hashes and structural metadata.
- The original source bytes and modification time are checked after each end-to-end fixture.
- Full collection/runtime behavior and the seven real workbook bodies were not tested; the owner controls manual execution.

The publication overlay contains only the media module, this documentation and the new focused test file. The existing 69-test file is unchanged. Shared collector, manifests, source contracts and launcher files are outside this patch.
