# Native harness Windmill execution

UIF-126 retains the existing CE job backend and Foo supervisor. This source
component does not deploy a worker, change SSH/data permissions, install a
package, create credentials or add schedules. Source acceptance, installed
runtime adoption and delivery acceptance remain separate.

The dispatcher uses the existing `u/admin/foo_jobs_20261027` bridge in workspace
`offmenu`. A caller retains its reserved Windmill UUID and logical Foo job ID;
job history is read through `jobs_u/get`. A duplicate UUID, lost response or
transport timeout requires inspection of that same operation. A new wrapper
status job must reference the original logical computation ID, never resubmit
the computation. The maintained completed-job reader covers the retained
Windmill 1.850.0 response shape without a `running` field. This is source
compatibility evidence, not a fresh installed-version observation.

The runner persists command, runner and capacity-policy byte hashes, request
identity, bounded logs and terminal receipt under the existing private job root.
Reopening an identical job returns its receipt. Changed execution identity
returns `id_conflict`; source drift never silently migrates an old operation.
The Engine's existing exact source/output bindings and typed historical receipt
readers continue to govern validation acceptance. The native handoff contract's
canonical policy fingerprint is a separate new field; it must not replace these
historical file-byte hashes. No alternate handoff validator is implemented here.

A completed API wrapper is not proof of stopped computation. Status-only
inspection preserves the original backend status, reconciliation hold and
`child_tree_gone` fact. Stale heartbeats and orphan reservations never authorize
replay or capacity release. The existing subreaper kills and reaps actual owned
descendants, including children that detach with `setsid`, before removing a
reservation. It does not kill unrelated jobs or infer cleanup from wrapper exit.

CE execution retains the local aggregate admission lock, persistent slot
reservations, resource declarations and sampled descendant/RSS guards from
ADR 0004. No Enterprise concurrency feature is required. These cooperative
budgets are not hard cgroup limits or security boundaries. Existing legacy
requests retain their compatibility exclusion and original identities.

The maintained sampling seam tolerates only procfs `ENOENT` and `ESRCH` when a
child disappears between enumeration and reading its stat. Other I/O and
permission errors still fail supervision closed. Surviving descendants continue
to contribute RSS; the enumerated process count remains conservative until the
next sample. This change does not suppress malformed stat data or change cleanup.

Bounded offline verification from the selected worktree, using the existing
pinned interpreter:

```sh
PYTHONPATH=src:tests/delivery /home/user/src/offmenu/.venv-delivery/bin/python -m unittest test_windmill test_stokowski_dispatcher test_capacity_policy test_capacity_review_regressions -v
```

The focused regression fails on the original unhandled `ESRCH` and passes after
the fix; permission and I/O errors remain failures. Real local CLI checks cover
timeout, detached-child cleanup, same-ID reopen without duplicate computation,
command/runner/policy drift rejection and retained unresolved reservations.
Dispatcher tests preserve status-only observations separately from wrapper
completion. These synthetic local checks do not establish live Windmill access,
installed source equivalence, release qualification or parent outcome completion.

## Explicit resource receipt projection

The native direct bridge API accepts optional
`receipt_projection='legacy'|'resources-v1'`. The default is `legacy`: resource
fields are stripped exactly as before, so the existing strict typed dispatcher
continues to consume its original response shape. That dispatcher and its
read/180-second request profiles are unchanged. Unknown projection values are
rejected before SSH transport or credential access.

New `release_qualification.bridge_request` requests explicitly select
`resources-v1`. The projection copies only `receipt.resources` received from the
runner over the existing confined service transport. It never fills missing
resource facts from the bridge's requested arguments. Missing facts remain
missing, and release aggregation holds them. This is the runner's recorded
resource declaration, not sampled CPU/RAM use or an assertion of hard limits.

`resources-v1` allows exactly workers, overhead processes, CPU millicores,
memory/output bytes, I/O slots and read/write roots, with the maintained runner
ranges. Integers exclude Booleans/nonfinite values. Remote roots must be unique,
canonical POSIX paths within `/offmenu`, with bounded counts and lengths; mutable
roots cannot overlap delivery/platform control paths or their ancestors.
Read mode cannot declare writes; write mode must declare them. The detached
resource JSON is capped at 16 KiB within the existing bounded receipt channel.
Larger otherwise admissible declarations require a separately qualified receipt
route; the bridge does not silently truncate them. Filesystem/symlink admission
remains the remote runner's responsibility: matching path names on the Windmill
worker do not establish access to the SSH jail.

The added argument controls receipt projection only. It is not forwarded into
the runner execution specification and does not change its historical
`request_sha256` recipe, logical job identity, command, timeout or resource
request. Original request/runner/policy and output checks in release aggregation
remain mandatory. A changed or forged declaration is not repaired to match the
plan; its exact raw request hash and resource values must qualify.

For custody, select the nested receipt JSON returned by the native bridge,
persist its exact selected serialization and pin those bytes in the existing
handoff receipt reference. Pin the outer native Windmill job UUID, workspace,
script/source and full request including the projection opt-in through the
existing evidence references. Preserve the logical computation ID separately.
This is a service-origin allowlisted projection, not a byte-identical copy or
file-byte hash claim for the full private Foo `receipt.json`. Source-controlled
code, outer job provenance and native readback must qualify before the projected
receipt is accepted; local synthetic tests alone do not establish that trust.
No privileged raw-file collector, permission change or argument-based resource
reconstruction is introduced. Logs, unknown errors and other private fields
remain stripped. Receipts without resource fields retain valid legacy handling.

Focused tests exercise actual bridge receipt projection into the real release
aggregator, resource/request-hash equality, malformed/control-path rejection,
missing-resource requests, legacy dispatcher compatibility and early invalid
projection rejection. They use inert external SDK/transport doubles: no live
Windmill writes, jobs, deployment, credential reads or SSH effects occur.
