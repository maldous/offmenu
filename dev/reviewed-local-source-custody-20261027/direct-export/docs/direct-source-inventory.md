# Direct source-custody inventory; no GitHub Actions

The normal-user `inventory` command now covers complete **eligible** metadata and
is disk-backed. This is not an inventory of every checkout path. The former
50,000-candidate, 200,000-visit and depth-64 cutoffs are removed, not increased or
silently truncated. Fixed passive Git index output is spooled to a private file;
eligible path deduplication, sorting and the directory queue use private SQLite
scratch storage. Directory enumeration uses `scandir` and no-follow descriptors.
The production CLI never accumulates all index entries or inventory items in RAM.
No source file, checkout, Git index, service or host permissions are changed.

Each metadata batch targets 512 KiB of items plus a small packet envelope. Every
batch shares the complete canonical item-list SHA-256, total file/byte/part counts,
excluded-entry count and before/after-verified Git head/branch. `packet-set.json`
pins every packet's bytes and SHA-256 and is written only after successful full
enumeration and snapshot checks. The existing packet schema remains
`offmenu-local-source-packet/1`; metadata counts use signed-64-bit representable
integers rather than selected-content quotas. Disk exhaustion, unreadable
directories, malformed index data or a changed index/head fail explicitly: no
completion manifest represents a partial inventory.

The fixed passive index command has a 120-second execution timeout, not an output
size limit. Small Git head/branch probes keep their existing 30-second/32-MiB
guards. File checksum work still has the existing 64-MiB per-file and 512-MiB
overall budget; eligible files beyond it remain explicit `present-unhashed`
metadata with real size and null digest, not silently omitted or export-ready.
Secret/config/dataset/cache/log/dependency exclusions are preserved.
External runtime trees are never recursively searched.
Directories named `corpus` or `corpora` may contain application source: Python,
JavaScript and TypeScript module extensions there are included as metadata, also
when untracked. Dataset/text/JSON files there remain excluded, as do all other
denied subdirectories and secret paths. These module bytes are not published by
inventory; any later selected body export still needs explicit path/hash review.
Do not describe excluded schemas/documents or external uninspected paths as
recovered; those require a separately explicit reviewed selection.

`validate_packet_directory(directory)` checks the complete manifest and each
packet pin, then streams canonical inventory items in sorted order to verify
whole-inventory custody and duplicate absence. Its memory scales with one packet
and the small manifest receipt list, not the inventory item count. Selected source
groups retain the existing bounded full-content validation. The generator never
uploads by itself; the separately reviewed direct publisher uses existing `gh`
authentication and the workflow-trigger-safe custody branch only.

Run the immutable, hash-verified helper as the normal owner into a new private
temporary directory. The direct path uses **no `sudo`, `stage`, runner request,
GitHub Actions or local AI session worker**. The legacy stage/receive functions
remain inert for backwards compatibility and are not part of this procedure.
The direct publisher must verify pins again immediately before creating Git
objects, preserve the current branch by non-force update, and return the actual
immutable publication commit. No credentials are copied or created.

Optional `--include-pinned-anchor-docs` includes only the three existing exact
path/hash-pinned metadata documents; this is not recursive runtime access or
authorization to publish the application code they reference. Canonical-only
inventory must not be described as recovery of all external outstanding work.
