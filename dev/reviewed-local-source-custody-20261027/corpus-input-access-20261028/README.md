# Incremental OffMenu input access update

Approved 2026-10-28 01:11:11 UTC: add read-only input access, including named UID985 read/traverse ACLs where needed, to exactly two directories and six optional existing recovery files. No input writes, process restarts, credentials or network expansion.

Deliverable: `offmenu_input_readonly_acl_mount.py`
SHA256: `7a0754128163b1e560256d99b4fd01c90e7066f83290e600d73cfc7cf66c8e81`

The installed previous launcher must hash to `93a8e8eeb65666d775caf45235d39d2d9695c33d25285948aeb4dff7be52b1c2`. Its ten original mount pins are parsed with `ast.literal_eval`, checked against the exact original paths/kinds, and used to reconstruct the entire old reviewed template before any change. Those ten pins and their existing ACLs are preserved.

New required directories under `/home/user/src/offmenu-data/`:
- `common-bulk-food-20261014`
- `curated-expanded-country-search-20261013/blobs`

Optional existing files:
- `common-places-semantic-final-20261014.checkpoint.sqlite`
- `common-places-semantic-final-20261014.checkpoint.sqlite-journal`
- `common-places-semantic-final-20261014.checkpoint.sqlite-wal`
- `common-places-semantic-final-20261014.checkpoint.sqlite-shm`
- `common-places-semantic-final-20261014.alignment.lock`
- `common-bulk-food-semantic-final-20261014.repair.lock`

Absent optional files are recorded and skipped, never created. Present optional files are inode-pinned. Runtime disappearance or replacement omits that optional mount, never mounts a replacement, and does not disable required mounts. Only the six fixed approved file paths can have optional status. A fixed in-jail pre-execution guard rechecks mounted identity and read-only flags before any supplied shell command; a rename race refuses the command instead of exposing a replacement. No host source descriptors are inherited.

ACL changes are limited to newly approved trees and present optional files. Defaults, ownership and other principals' effective permissions are preserved. Existing safely readable externally hardlinked inodes remain untouched; unsafe external links stop the update. Required ancestor traversal must already exist; outside-scope ancestors are never changed.

Default execution is metadata-only preflight. `--apply` creates root-private backups and a durable intent journal, applies the checked access-only ACL plan, verifies UID985 access, installs the incremental launcher, and runs sandbox checks. Caught failures perform guarded rollback; forced termination/power loss requires reviewing retained journal/preimages rather than claiming automatic recovery.

Validation: 42 focused tests passed, including inherited ACL safeguards, exact prior mount preservation, optional omission/FD cleanup, malformed optional flags, strict required mounts and pre-execution guard. Actual synthetic bubblewrap guard test passed for matching pins; mismatching pins exited126 before executing the supplied command. Cloud user-namespace ACL syscall fixtures use mapped UID1000; actual Foo985 and full network-unshared sandbox verification remain in the user-run installer. No Foo execution occurred during preparation.
