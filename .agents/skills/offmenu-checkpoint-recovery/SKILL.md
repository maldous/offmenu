---
name: offmenu-checkpoint-recovery
description: Reconcile uncertain OffMenu job outcomes and verify or restore local checkpoint metadata using existing job/storage helpers without replaying work, deleting history or exposing data.
---

# OffMenu checkpoint recovery

Use the same job ID, storage root and source version as the interrupted operation.
These helpers store durable local evidence; they do not provide daemonized jobs,
a distributed lock, transactional rollback of arbitrary commands or a host backup.

## Reconcile a job before retrying

Read `scripts/windmill/job_runner.py status --job-id ID` through the established
bridge, with the same root `/offmenu/data/.offmenu-platform`.

- `queued`/`running`: inspect heartbeat and `reconcile_required`; do not start a
  duplicate. A stale heartbeat is uncertainty, not proof that effects did not
  happen. Check the corresponding Windmill run and known output/checkpoint.
- `succeeded`: verify the requested output/coverage; process exit alone does not
  establish completeness. `failed`, `timed_out` and `cancelled` can leave valid
  completed application batches that should be preserved.
- `busy` with `reserved: false`: no ID was reserved by that admission attempt.
  Wait for the reported capacity/conflict to resolve; do not use rapid retries.
- `unknown`, `id_conflict`, `blocked_reconciliation` or `supervisor_error`:
  reconcile the exact receipt,
  request binding and relevant local artifacts. Do not bypass the conflict by
  changing the ID, deleting its directory, resetting the checkout or clearing
  locks/in-flight markers. Those markers survive supervisor death and cannot be
  cleared merely because a PID or heartbeat disappeared. A fresh attempt needs
  an established safe application resume/retry point.
- `not_found`: the selected root has no record for that ID. After an uncertain
  submission, verify ID/root and Windmill run before concluding nothing ran.

For an authorized cancellation, use the runner's `cancel --job-id ID`. It writes
a job-ID marker read by the running supervisor. `cancellation_requested` is not
terminal evidence: observe the final status and `child_tree_gone`. Each SSH call
has a different PID namespace; never send a cross-session signal using a saved
PID. The runner limits declared timeouts above 30 seconds to one long job and
rejects busy admission immediately; two short jobs can still delay control until
their deadline. Do not claim a cancellation request acts immediately.

## Verify saved checkpoints/artifacts

The storage CLI is `python3 scripts/windmill/storage/offmenu_storage.py --root
/offmenu/data/.offmenu-platform OPERATION ...`. Match installed source/`--help`
before use. Supported operation arguments are:

```text
publish --source EXACT_LOCAL_FILE --name SAFE_LOGICAL_NAME --max-bytes BYTE_LIMIT
checkpoint --key KEY --json-file EXACT_METADATA_FILE [--artifact-receipt RECEIPT]
verify --key KEY [--version VERSION]
backup --key KEY
restore --key KEY --backup RETURNED_BACKUP_PATH
```

`publish` means **local** content-addressed storage, not Git/cloud publication.
Use it only for selected outputs needing durable copies; do not duplicate entire
retained databases just to report activity. Checkpoint metadata permits required
`run_id`, `partition`, `status` (`pending|running|completed|failed`) and optional
`cursor`, `counts`. Use opaque nonsecret identifiers and cursor values, never raw
records, paths, credentials or arbitrary exception text. Schema acceptance does
not prove a string contains no secret. Keep metadata within 8 KiB and reference
only the helper's verified artifact receipt paths (at most 64).

`verify` checks the snapshot identity/checksum and referenced artifact hashes and
sizes. Keep the returned version/hash/count and result status as evidence. A
missing/corrupt object is an integrity failure; do not mark it verified, replace
it silently or publish a new manifest pretending the old bytes are intact.

`backup` preserves the current checkpoint envelope locally. `restore` verifies
the selected backup and referenced artifacts, creates a **new checkpoint version**
and records its predecessor. Re-verify the new current checkpoint and preserve
the prior versions. Restore does not roll back application databases, recreate
missing artifact bytes or resume a process. Restart work only using the real
application's matching source/version and cursor semantics. Same-disk checkpoint
backups are not an independent backup of Foo or Windmill PostgreSQL.

## Return only evidence

Return the safe job/checkpoint identity, state, version/hash, checked artifact
count, and whether recovery/resume is established or still unknown. Keep logs,
checkpoint JSON, data artifacts and raw error text local and out of Git/chat.
No quota retries before capacity confirmation, Actions, network lookup, AI setup,
privilege expansion, deletion of unrelated files or new release gate is part of
this recovery procedure. Routine corrections remain within the existing approval.
