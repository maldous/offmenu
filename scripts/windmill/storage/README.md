# OffMenu local artifacts and small Windmill checkpoints

## What is configured, and what is not

- Native Windmill `state` resource `u/admin/offmenu_platform` was deployed in
  workspace `offmenu` on 2026-10-27 and read back: `created_by=admin`,
  `extra_perms={}`. It contains nonsecret configuration and an empty checkpoint
  collection. It is owner-private apart from existing workspace administrators.
- Windmill script `u/admin/offmenu_platform_checkpoint` is deployed with private
  `extraPerms={}` and exact source read-back verification. Its read-only inspect
  preview succeeded with explicitly pinned `wmill==1.850.0`, resolved from the
  existing worker dependency cache. The sole host writer subsequently passed all
  26 tests in the actual jail and verified publication, checkpoint backup and
  restore using a 28-byte synthetic artifact. Its real receipts were committed
  to Windmill, then inspected successfully in a separate job on the other worker.
  Job IDs and hashes are recorded in `deployment-receipt.json`.
- No new PostgreSQL credential, database, resource type, Hub sync, authentication
  grant, worker network route, host mount, object store, AI runtime or account was
  created by this storage component.
- Python files are installed under `scripts/windmill/storage/` by the sole host
  writer; actual jail tests and receipts are recorded separately from local tests.
- **Windmill's PostgreSQL Docker volume persistence and independent backups remain
  unverified.** This helper neither inspects nor backs up that database.

## Layout and contracts

The intended owner-controlled, ignored runtime root is
`/offmenu/data/.offmenu-platform` inside the existing jail. It must be owned by the
executing user with mode `0700`. Newly created directories are `0700`; files are
`0600`. Never place this runtime root, source datasets, credentials or arbitrary
job results in Git or a chat attachment.

```
artifacts/objects/sha256/<prefix>/<sha256>       content-addressed artifact bytes
artifacts/manifests/<manifest-sha256>.json     small immutable receipts
artifacts/staging/                           temporary publication files
checkpoints/<key-sha256>/versions/<version>.json
checkpoints/<key-sha256>/current.json         atomic latest-version pointer
backups/checkpoints/<key-sha256>/<version>.json
locks/storage-<key-sha256>.lock              advisory local lock inode
```

`offmenu_storage.py` uses only Python's standard library on Linux. It does not
execute commands, open a network connection, inspect environment credentials or
automatically discover/copy data. `publish` streams only its explicitly selected
source, checks that it did not change during the copy, and publishes by an atomic
same-filesystem link. Existing content is verified, never overwritten. Manifest
and checkpoint files are fsynced before publication, then their containing
directories are fsynced. A checkpoint version is written before an atomic current
pointer replacement; an interrupted publication can leave an unreferenced version
or artifact, but must not advance the current pointer to incomplete output.

This is integrity checking against accidental damage, **not a cryptographic
signature or WORM store**: an authorized writer can modify files and recompute
hashes. Root-directory permissions and the existing jail are the security
boundary. Do not use network filesystems, share the directory with untrusted
writers, or remove lock files while jobs are active.

The allowlisted checkpoint record is small, nonsecret operational metadata:

```json
{"run_id":"example-run","partition":"part-01","status":"completed","cursor":1,"counts":{"processed":1}}
```

Supported statuses are `pending`, `running`, `completed`, `failed`. The cursor
is a bounded nonsecret string or nonnegative integer; counts are bounded integer
counters. Arbitrary rows, exception dumps, credentials and unknown fields are
rejected. **A schema cannot prove a string contains no secret:** callers must
never put one in an identifier or cursor. Records are limited to 8 KiB, checkpoint
envelopes to 64 KiB, and each checkpoint to 64 artifact receipts. Artifact copies
default to a configurable 1 GiB maximum per invocation. This is not a corpus
ingestion or bulk backup command. Budget storage before selecting larger files.

## CLI

Use the existing no-network execution bridge; do not open a second host shell,
install dependencies, or add networking for this helper.

```sh
python3 scripts/windmill/storage/offmenu_storage.py \
  --root /offmenu/data/.offmenu-platform \
  publish --source APPROVED_DERIVED_ARTIFACT --name run-id/partition/output.parquet

python3 scripts/windmill/storage/offmenu_storage.py \
  --root /offmenu/data/.offmenu-platform \
  checkpoint --key run-id/partition \
  --json-file APPROVED_SMALL_METADATA_JSON \
  --artifact-receipt artifacts/manifests/RECEIPT_SHA256.json

python3 scripts/windmill/storage/offmenu_storage.py \
  --root /offmenu/data/.offmenu-platform verify --key run-id/partition

python3 scripts/windmill/storage/offmenu_storage.py \
  --root /offmenu/data/.offmenu-platform backup --key run-id/partition

python3 scripts/windmill/storage/offmenu_storage.py \
  --root /offmenu/data/.offmenu-platform restore --key run-id/partition \
  --backup backups/checkpoints/KEY_SHA256/VERSION.json
```

Use actual returned relative receipt paths, never the placeholders above. Success
prints one JSON receipt, not artifact or checkpoint payload contents. Failure
exits `2` with a sanitized exception class; do not respond by logging arbitrary
exception bodies or dumping environment variables.

## Recovery and backup meaning

`backup` verifies the current checkpoint and all referenced artifacts before
writing an immutable copy of the small checkpoint envelope. `restore` validates
the backup checksum, key, version and every referenced artifact before creating
a **new** checkpoint version and moving the pointer. Existing history is retained.
Missing or corrupted artifacts prevent restore. A bad/current missing pointer
does not prevent recovery from a good backup. This restores metadata, not a
running process, source corpus or PostgreSQL database.

Same-disk checkpoint copies protect against accidental pointer loss/overwrite;
they do **not** protect against loss of Foo or its disk. A complete independently
recoverable store needs both checkpoint backups and referenced manifests/object
files copied to an authorized independent destination, followed by a restore
test. No such off-host copy, destination or credential is configured here. There
is no automatic retention deletion: size/retention policy should be based on the
actual workload, preserving referenced artifacts and accepted provenance.

## Windmill-side integration

The default, already deployed resource is a baseline configuration, not a growing
global mutable map. `windmill_checkpoint.py` stores each run/partition reference
under `u/admin/offmenu_platform/checkpoints/<key-sha256>` as native `state`.
Its `main` defaults to `operation="inspect"`; `operation="commit"` requires the
matching `checkpoint_receipt` **and** `backup_receipt` returned by the CLI.

Keep this adapter on the **Windmill worker side**, where the existing job-scoped
SDK is available. Do not copy its authentication into Foo's SSH jail. If installed
as a Windmill script, its source uses the SDK's own authenticated `get`/`post`
methods, without constructing URLs or reading a token. It uses exact HTTP 404 for
absence; 401/403/server failures fail closed rather than masquerading as missing
state. First creation is create-only, existing values must have the expected
native type and private owner, and writes are read back to verify the receipt.

Caller order:

1. Execute one bounded partition using the existing job runner.
2. Atomically publish derived output; verify receipt.
3. Write the local checkpoint and its versioned checkpoint backup.
4. Send only those small receipts back to the Windmill wrapper.
5. Commit the corresponding Windmill state reference, then verify it.

If step 5 fails, the completed artifact and local backup remain available for
idempotent retry. A Windmill reference cannot itself prove the host file exists;
the actual host `verify` result supplies that evidence.

**Serialize each key across the whole job.** The local advisory file lock only
covers an individual helper call; it does not coordinate all Windmill workers.
Windmill's whole-value set is not CAS, a transactional lease or a distributed
lock. The adapter's read-back detects some conflicting writes but does not make
the preceding read/update atomic. Prefer distinct per-run/per-partition keys;
only introduce application PostgreSQL transactions when that requirement exists.

## State is not job history

Native `state` resources persist across jobs, unlike a flow's temporary shared
directory and custom flow state. Community job details are retention-limited;
do not use job history as the durable provenance archive. In Windmill v1.850.0,
`state` and `cache` are expressly excluded from normal resource version history
and workspace exports. Therefore explicit versioned checkpoint copies are
necessary; a workspace export is not evidence these checkpoints were backed up.

Sources (inspected 2026-10-27):

- [Windmill persistence semantics](https://www.windmill.dev/docs/core_concepts/persistent_storage/states_resources_shared_directory)
- [Job retention](https://www.windmill.dev/docs/core_concepts/jobs)
- [v1.850.0 Python SDK](https://github.com/windmill-labs/windmill/blob/v1.850.0/python-client/wmill/wmill/client.py)
- [v1.850.0 resource store implementation](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-store/src/resources.rs)

## Tests

```sh
python3 -m unittest discover -s scripts/windmill/storage -v
```

All tests use tiny synthetic data in private temporary directories, and the
Windmill adapter tests use a fake SDK. They exercise interruption, corruption,
metadata-only restore, history preservation, idempotence, local writer exclusion,
path traversal/symlink rejection, permission and size bounds, exact-404 handling,
private owner/type checks and sanitized receipts. They do not test PostgreSQL
backup, host reboot survival, or a real cross-host recovery.
