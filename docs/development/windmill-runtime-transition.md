# Windmill runtime transition candidate

This candidate separates version-controlled source from an explicitly installed,
content-pinned runtime. It does not activate services or make canonical cleanup
safe by itself. The current canonical checkout and its runtime paths remain intact.

## Source and private installation

`tools/operations/prepare_windmill_runtime.py stage` reads the reviewed candidate's
`repository-standard.json` hold inventory, the matching canonical operational files,
and the existing host capacity policy. It combines those with the candidate runner.
The installation preserves the `scripts/windmill/` and `tools/delivery/` layouts,
including sibling storage imports and the runner's relative policy lookup. Opaque
metadata remains private and is never added to Git. Datasets, logs, credentials,
job receipts, and checkpoint databases are not inputs to staging.

The tool stages under the destination's existing ignored `.delivery/windmill-runtime/`
namespace. This is private owner-only preparation, not a deployed path. A SHA256
fingerprint covers the exact file inventory, sizes, and hashes. Verification also
requires the selected hold inventory plus runner and policy; rejects special files,
symlinks, extra entries, altered content, wrong ownership, and non-private modes;
and requires the fixed no-cutover manifest contract. Files and nested directories
are synced before publication of the staged directory. A partial preexisting
installation fails closed and must be reconciled, not overwritten.

There must be one trusted staging writer. Hash naming and verification do not make
files immutable against the same owner, root, or existing writable container mounts.
Do not share the private installation, relax its permissions, or select it for an
executor until that executor's actual access and confinement have been qualified.

## Behavior preservation

The runner retains the installed `observed-host-v1` accounting option while leaving
`reserved-maxima-v1` as the default for existing repository policy. Observed mode
uses per-request limits for several resources, with sampled memory/disk guardrails.
It does not measure CPU load or I/O utilization, guarantee instantaneous headroom,
or enforce a kernel isolation boundary. Existing job/process counts and path-conflict
checks remain. Pooled jobs cannot declare write roots overlapping the installed
runtime namespace. Legacy jobs without explicit resources retain their existing
behavior; this check is not a security sandbox.

Runner and policy hashes participate in immutable job request identity. A changed
runner must not replay an old job under a new ID. Status/cancel and old receipts
must remain available, and uncertain outcomes must be reconciled before cutover.
The logical state root remains `/offmenu/data/.offmenu-platform`; staging never
moves its jobs, locks, checkpoints, artifacts, or database files.

## Cutover prerequisites still outstanding

- Approve the ADR 0010 production `.offmenu-runtime` access contract, then qualify it as readable by the actual UID985 SSH executor
  without exposing unrelated private `.delivery` material or relaxing confinement.
  The current owner-only staging directory is deliberately not readable there. Installation alone does not constitute consumer handoff or canonical cleanup.
- Verify actual visibility, policy/import resolution, and access through the
  existing `/offmenu` jail, not merely from the trusted host owner.
- Reconcile all deployed consumer paths, including bounded job and platform-check
  scripts, their legacy wrappers, and any active selected container/service bindings.
  Preserve credentials, transport, limits, state paths, and immutable receipts.
- Qualify old-ID status/cancel and changed-runner conflict, concurrent admission,
  mixed legacy/capacity jobs, timeout cleanup, and deployment rollback using the
  preserved old runtime. Do not resume suspended workers or schedules.
- Obtain review and established integration checks for the source candidate before
  publication/integration. After consumer migration, recheck all preserved dirty
  files, disposition non-runtime changes, then fast-forward canonical `develop`
  to the verified current remote. Verify exact commit and genuinely clean status.

Do not claim staging, focused tests, or a clean secondary worktree completes the
canonical checkout requirement. Do not clean files or change ignore rules to mask
unresolved operational dependencies.

Native Stokowski admission independently pins both runtime and canonical capacity policy. This four-file legacy Windmill installation does not authorize native resumption or satisfy those source-policy pins. Retain the old native records and requalify any newly selected native work through its existing admission procedure.
