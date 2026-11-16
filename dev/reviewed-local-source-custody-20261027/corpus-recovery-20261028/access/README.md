# Approved OffMenu read-only corpus ACL and mount update

The user approved (2026-10-28 00:26:34 UTC) named UID985 read/traverse ACLs where needed within the original eight approved corpus directory trees plus read access to the two receipts. This standalone update replaces the earlier mount-only attempt, which stopped before changes because existing access was insufficient.

Deliverable: `offmenu_corpus_readonly_acl_mount.py`
SHA256: `bd8a61898801bbc578f5ab782a0965ea539d93f074c580529b51e51825b7d004`

Default invocation is a metadata-only preflight. `--apply` performs the complete checked change in one step.

- Checks exact original launcher hash, existing restricted account, launcher config and project identity.
- Inventories only approved trees/files, preserving credentials, SSH configuration, ownership and contents.
- Rejects symlinks, special files, host mounts, writable/worker-owned source inodes, unsafe ancestors and changed identities.
- Adds access ACLs only when needed. Directories receive read/traverse; files receive read. Existing other principals' effective rights are preserved even when the ACL mask must expand. Default ACLs are never written.
- Externally hardlinked files already safely readable remain untouched. Any externally linked inode needing an ACL change stops before modification.
- Saves root-private launcher/ACL preimages and plan, with an fsynced per-inode intent journal. Rechecks metadata/ACLs before mutation and verifies applied access while preserving defaults.
- Verifies the complete selected-tree traversal/read access as UID985, then installs the reviewed read-only mount launcher with automatic guarded rollback on caught failure.
- Sandbox destinations: `/offmenu-corpus/<approved relative path>`. No network expansion or host source descriptor inheritance.
- Real sandbox smoke checks read-only flags/identities, no leaked host corpus descriptors, private home/Docker absence, existing project write access and loopback-only interfaces.
- Forced termination or power loss cannot promise automatic rollback; retained preimages and journal support specific recovery. Concurrent administrative edits are never blindly overwritten.

Validation: 24 local tests and 4096 independently reviewed pure ACL cases passed. The cloud namespace cannot represent UID985, so real libacl syscall/rollback fixtures explicitly use mapped UID1000 while pure planner cases use985. Actual Foo985 access and full sandbox verification run in the installer and remain pending until user executes it. No Foo execution occurred during preparation.
