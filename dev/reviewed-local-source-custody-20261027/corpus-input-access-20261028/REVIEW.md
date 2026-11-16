# Focused incremental input-access review

Artifact: `offmenu_input_readonly_acl_mount.py`
SHA256: `7a0754128163b1e560256d99b4fd01c90e7066f83290e600d73cfc7cf66c8e81`

Result: no remaining blocking finding in reviewed candidate under the existing trusted-host-root/owner model. No actual Foo modification was performed by this review.

Scope is exactly the two newly approved input directories and six explicitly listed optional existing sidecar files. ACL census and edits are restricted to this added scope; the previous eight package directory mounts, two receipt mounts and their pins are retained. Existing launcher must match SHA256 `93a8e8eeb65666d775caf45235d39d2d9695c33d25285948aeb4dff7be52b1c2`, then its mount list is parsed by AST literal evaluation, checked against exact prior paths/order/types, and reconstructed against the entire original reviewed template. No existing launcher code is executed during extraction.

ACL planner and ACL I/O are byte-identical to the preceding reviewed updater. Existing effective permissions/defaults/ownership are preserved; only UID985 read or read/traverse is added where needed. External shared inodes needing changes, unsafe symlinks/specials/submounts and changed metadata fail closed. Existing root-owned backup/journal and guarded rollback behavior remain intact.

Optional files absent at selection are not created or mounted. Only the exact six approved optional paths can be marked optional. Later missing files or identity/type replacements are omitted, never rebound to a new object; required roots and prior mounts remain strict. All source descriptors are closed before bubblewrap. A fixed isolated Python guard verifies mounted identity and read-only flags before executing any supplied command, preventing execution after a bind-time identity mismatch. Success output distinguishes selected/pinned files from those actually mounted at smoke time.

Verification:
- Independently reran all 42 tests, including prior ACL/rollback cases, exact scope, old-pin preservation/hash/template rejection, optional absence/permission distinctions, required strictness, replacement/symlink omission and descriptor cleanup: passed.
- Independent disposable bubblewrap test with user/PID isolation verified the in-jail guard permits exact read-only pins and rejects a mismatched inode before command execution.
- Confirmed prior template, ACL planner and ACL I/O are byte-identical to reviewed originals.
- Actual full namespace/UID985 verification on Foo is still required by the user-run installer; Windmill-worker verification follows installation. Cloud real-ACL fixture tests use mapped UID1000, not actual UID985.

Limitations: trusted-owner/root concurrent modifications remain outside the inherited threat model; a source disappearing between validation and bind can safely fail a single command rather than run against a replacement. No process restart/resume, database content read, source data modification, private-home exposure or network expansion is performed. Power-loss recovery is backed by the retained journal but no automatic replay is claimed.
