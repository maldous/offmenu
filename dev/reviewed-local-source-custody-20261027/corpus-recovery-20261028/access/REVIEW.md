# Focused combined read-only ACL and mount review

Artifact: `offmenu_corpus_readonly_acl_mount.py`
SHA256: `bd8a61898801bbc578f5ab782a0965ea539d93f074c580529b51e51825b7d004`

No remaining blocking finding in this candidate under the inherited trusted-host-root/owner concurrency model. No actual Foo changes were performed by this review.

The exact eight approved package directories and two receipt files match the previously reviewed scope. The embedded read-only launcher template is byte-identical to the final reviewed non-ACL installer. It closes host source descriptors before running bubblewrap and retains fixed read-only bindings, namespace isolation, and runtime nested-mount rejection. Account, keys, SSH configuration and network access are unchanged.

The new ACL planner grants only UID985 read access to files and read/traverse to directories where needed. Existing effective grants to other principals are preserved by normalizing masked group-class entries before raising the mask. Owners, groups and default ACLs are not changed; default ACLs are compared but never written. Preexisting worker write permission or worker ownership causes a stop. No outside-scope ancestor ACL is changed.

Metadata-only complete scope census accounts for inode aliases. An external hardlink needing a grant is refused; already-readable external shared inodes remain untouched. Symlinks, special files, submounts, inode/owner/link-topology changes, or unexpected ACL changes stop the operation. Root-owned backups contain full preimages and a durable per-inode intent journal. Inodes are marked touched before the ACL syscall. Rollback restores only known before/after states on matching inodes and reports unresolved collisions rather than overwriting them.

Verification:
- Independently reran all 24 unit/fixture tests: passed.
- Independently exercised 4,096 pure ACL mask/default preservation cases: passed.
- Filesystem ACL apply/rollback, default preservation and post-ACL fsync failure paths were tested on disposable scratch fixtures. Because the cloud namespace maps only UID1000, syscall fixtures deliberately map the named test principal to UID1000; these are not proof of actual UID985 host access.
- The root-path handling bug and misleading inherited 'no ACL changed' error were corrected before this reviewed artifact.
- Actual Foo UID985 ACL behavior, whole-tree access and full namespace smoke remain mandatory installer verification. Windmill-worker verification follows successful installation.

Limitations: a process kill or power loss can interrupt a transaction; retained backup/journal supports recovery, but no automatic power-loss replay is claimed. Concurrent trusted-owner tree mutation may require a stop/reconciliation. No raw data contents were read or exported by review.
