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
