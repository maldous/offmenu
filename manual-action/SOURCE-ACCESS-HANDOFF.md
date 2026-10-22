# Approved, narrow source-read handoff

## Authorization and boundary

The user approved granting their existing Foo `user` account read-only access to
**exactly 50 newly acquired public-source artifacts and their 50 provenance
receipts**, with only the directory traversal required. No other data, write
access, mounts or service permissions change. The existing runner account owns
these private outputs. This package is an implementation and test artifact, not
an assertion that the grant has already been applied on Foo.

The only mutation entrypoint is:

```sh
python3 -I -B manual-action/grant_acquired_read_access.py --apply
```

Without `--apply`, the helper plans/verifies read-only and makes no filesystem
mutations. No arbitrary target user, cache root, manifest, file list, UID, or
permission parameter is exposed by the command. No sudo, setuid, source copying,
new package, service restart, mount, network request or dataset ingestion occurs.
The existing registered runner is the sole authorized writer, after independent
review; do not launch a competing local reasoning session or interrupt `./run`.

## Closed custody and path scope

`source-access-handoff-plan.json` binds each exact source ID/artifact filename to
its SHA-256 observed in successful acquisition run **39724029085, attempt 1**,
receipt commit **f9c75d1e38c4679ff660fa128bf1e52e0f3a81e3**, execution commit
**6740bcbfacfcc51e553128438f5153eca3a649a5**. The source fetcher preserves each
source's manifest artifact order; its sanitized summary emits the hashes in that
same order. That reconstruction is checked against all source counts and all 50
names. Observed hashes for non-publisher-pinned files are **not** relabeled as
publisher authentication. No source bytes or private ACL snapshots are in Git.

Pinned canonical JSON identities use `ensure_ascii=True`, sorted keys, compact
separators, and no NaN:

- Fetch manifest: `637bfeba82177e44a87080ca6be217c475cc02917848730762d9f1949e69ebec`
- Scope plan: `c9b2a39a54b5131b207c224fbfdea5803f6f08154688925f541ebc12947411e9`

The fixed cache prefix is:

`/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache`

Only `<prefix>/<source_id>/<artifact>` and its exact
`<artifact>.receipt.json` are file-grant targets. The 50 names are enumerated in
the plan. No status files, partial/checkpoint files, robots receipts, host-rate
metadata, fetch-summary, private ACL snapshot or other source is included.

The **nine** traversal-only grant targets are:

1. `/srv/offmenu-refresh/outputs`
2. `/srv/offmenu-refresh/outputs/additional-sources-20261022`
3. `/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache`
4. The cache child `foodista_common_pile`
5. The cache child `forkrecipe`
6. The cache child `medlineplus_healthy_recipes`
7. The cache child `fr_cnous_menus`
8. The cache child `fr_begles_menus`
9. The cache child `fr_toulouse_menus`

`/`, `/srv` and `/srv/offmenu-refresh` must already be traversable by the target;
otherwise the helper stops. It does not add permissions to those ancestors.

## Fail-closed preflight

- Resolve the existing accounts through the local account database. Require the
  current real/effective UID to equal non-root `offmenu-runner`; target existing
  `user` UID must be different and non-root. No account/group membership changes.
- Use existing system `libacl`; absence or unsupported filesystem ACLs blocks.
  There is no install or chmod fallback.
- Read paths through descriptor-anchored non-symlink parents and hold all 109
  selected nodes. Require actor ownership/group, regular nonexecutable files,
  single hard links, exact manifest/plan identity and the closed 50+50+9 scope.
- Read only reviewed schema keys in each source receipt. Verify exact source,
  revision, origin, license/attribution/scope, artifact key and completion flags;
  stream each artifact through SHA-256 against both its receipt and immutable
  observed acquisition hash. Require total **108,318,002 bytes**.
- For each newly traversable selected directory, inspect at most 4,096 immediate
  children using metadata/ACLs only, with no recursive crawl or sibling body read.
  Every unselected sibling must have zero effective target permissions. Refuse
  unlisted symlinks/special nodes, accessible siblings, unreadable metadata or a
  cap hit. Never revoke sibling rights or broaden the grant to solve a conflict.
  Repeat this boundary check before success; no unrelated sibling names appear
  in the sanitized report.

## Exact ACL semantics

Only named-user entries are added: target `r--` on files/receipts and `--x` on
private traversal directories. Reject preexisting target file execute/write or
private-directory read/write rights rather than silently retaining an excessive
handoff. No directory listing, default/inherited ACL, owner rights, world entry,
group entry, executable file bits, or write grant is introduced.

An ACL mask is required for named-user access. The helper explicitly calculates
it and compares every other principal's **effective** permissions before/after;
it stops if expanding the mask would expose masked permissions. It does not
blindly let `setfacl` recalculate the mask. Displayed group mode bits can reflect
the ACL mask even while the owning group's ACL entry remains `---`; those mode
bits alone do not mean the group received access. See the primary Linux ACL
[access-check and mask semantics](https://man7.org/linux/man-pages/man5/acl.5.html).

`acl_set_fd` changes only the held inode's access ACL, with actor ownership
checked; its permission model is documented in
[acl_set_fd(3)](https://man7.org/linux/man-pages/man3/acl_set_fd.3.html).
Directory default ACLs are observed and checked unchanged, never written.

## Snapshot, races, rollback and retry

A mode-0600 private original/planned ACL snapshot is fsynced before any grant,
under the runner-owned mode-0700 sibling `access-handoff` directory. It is not
part of the target's read scope. A private helper flock is held through summary
publication/stdout; the existing dispatcher's lock excludes other approved
runner jobs. Files/receipts are granted first; outer directory traversal is last.

Full inode/device/size/mtime/**ctime** signatures are retained before the first
write, checked after ACL reads and before changes, then refreshed only following
this helper's own successful ACL changes. Final verification rereads every
artifact/receipt against pinned custody and checks every resulting access ACL,
source identity and unchanged directory default ACL.

POSIX ACL updates are not atomic compare-and-swap against an uncooperative
same-owner/root writer. Preservation is established within the explicit
single-authorized-writer/dispatcher-lock boundary, with observable conflicts
failing closed—not by pretending to exclude an administrator ignoring locks.
No new host-wide locking daemon or service configuration is introduced.

On a caught failure, rollback restores only this invocation's changed ACLs on
still-matching identities and exact still-matching planned ACLs. It refuses to
overwrite an observed external change. `failed/rolled_back` means this helper's
changes were restored; it does **not** certify every unrelated principal's ACL
stayed unchanged. `partial/rollback_incomplete` is never success. Original ACLs
remain private for reviewed recovery; there is no broad `getfacl --restore` or
arbitrary rollback path command.

A process killed by an external timeout may leave a partial grant and durable
snapshot, not a completion proof. A later authorized same fixed `--apply` retry
revalidates the exact custody, permissions and boundary before completing the
remaining grant. It neither broadens scope nor treats an old summary as evidence.
The hash phases each have a 120-second budget; 109-node ACL work is finite. Any
outer timeout/cancel must remain non-success, even if a prior summary exists.

## Evidence and tests

The sanitized report has `schemaVersion=offmenu-source-access-handoff/1`,
`mode=apply|plan`, strict scope/plan/manifest identities, verified counts and fixed
outcomes. `complete` requires applied mode, exact 50 artifacts + 50 receipts + 9
directories, exact byte total, all preservation checks and explicit false
raw-upload/source-byte/default-ACL-mutation flags. It distinguishes `applied` and
`already_accessible`. Non-success exits are 2; complete/planned exit 0. Dispatcher
success is valid **only** for `mode=apply`, `complete`, exit 0 with fresh child
stdout; a dry plan or stale on-disk receipt is not success.

The fixed sanitized local summary is sibling
`receipts/access-handoff-summary.json`. Raw paths, numeric account IDs, ACL text,
private snapshot paths and unrelated sibling names are omitted. This establishes
POSIX ACL grant/readback, not a user-session open test, record acceptance or DB
write. The next ordinary-user access preflight still verifies actual readability.

Run synthetic tests only:

```sh
python3 -m unittest discover -s manual-action/tests -p test_grant_acquired_read_access.py -v
```

Coverage includes the full generated 50+50+9 plan; immutable custody/mutable
receipt mismatch; hardlinks/symlinks/executable data; exact traversal; ACL mask
safety; write-before-snapshot refusal; conflict-aware rollback; ctime tampering;
unlisted sibling exposure; strict report schemas; and in-memory real-libacl
numeric qualifier ABI round trips. The cloud fixture filesystem returns ENOTSUP
for actual POSIX ACL xattrs, so its filesystem-read test is explicitly skipped.
No live Foo ACL set/read or target-user accessibility is claimed by these tests.
