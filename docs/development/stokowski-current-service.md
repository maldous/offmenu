# Proposed current Stokowski service

Source-only proposal for [UIF-106](https://linear.app/maldous/issue/UIF-106), based
on `165523b64e7f3bf7a691edf858d5a5877820442a`. Only this guide and
[`offmenu-stokowski-current.service.in`](../../deploy/stokowski/offmenu-stokowski-current.service.in)
are proposed source. Nothing is installed, launched, committed or published.
The source owner will freeze the exact candidate head for independent review.
This does not change repository standards, policies or runtime qualification.

The proposed system-manager unit is `offmenu-stokowski-current.service`, manually
started as the existing `user` (verified UID 1000); Group is omitted to use its
primary group. No root coding, new account, boot enablement, timer, listener,
publisher or new manager is proposed. Leave `offmenu-runner.service` (the GitHub
Actions runner, account `offmenu-runner`, directory
`/srv/offmenu-runner/actions-runner`) alone. The frozen historical
`offmenu-symphony-layout-20261029.service` is neither a template nor a restart target.

## Required bindings

| Input | Exact value or required authority |
| --- | --- |
| Interpreter | `/home/user/src/offmenu/.delivery/stokowski/venv/bin/python` |
| `@REVIEWED_SOURCE_DIRECTORY@` | Canonical isolated, reviewed, clean exact checkout supplied by source owner `01a1866b`; exact head, branch and file hashes required |
| `@QUALIFIED_COORDINATOR_RUNTIME@` | Canonical existing qualified coordinator runtime from that owner's pending authoritative runtime/catalog packet |
| `REQUIRED_EXISTING_LINEAR_CREDENTIAL_REFERENCE` | Existing administrator-provided source reference for `LoadCredential=linear-api-key:<existingadministratorprovidedsource-reference>`; no secret value |
| Native authentication reference | `/home/user/.codex/auth.json`, through explicit `CODEX_HOME=/home/user/.codex`; existing ChatGPT authentication only |

The owner's corrected runtime/catalog packet and exact output are pending
separately. The credential reference is not the only missing input. Do not invent
a runtime, select the current canonical checkout/head as a substitute, modify the
owner's source, or run the preparer to manufacture qualification. This proposal
never creates, copies, rotates or grants a credential or reads the auth file.

Render by literal marker replacement in a data-processing tool, with no shell
interpolation, eval or command substitution of supplied values. Require absolute
canonical non-symlink paths from the owner/admin packet. For this unquoted unit
syntax, accept only path characters `[A-Za-z0-9_./-]`, reject `.`/`..` components,
newlines, whitespace, percent/dollar specifiers and other metacharacters. If an
existing credential reference cannot meet this narrow form, stop for a reviewed
rendering change; do not create a substitute credential source. Require exactly
three distinct input markers (the source marker occurs twice), replace every
occurrence, and reject any remaining marker before installation. Retain rendered
bytes/hash and exact input bindings privately; never install the literal template.

## Source contract and limits

[`stokowski_adapter.py`](../../tools/delivery/stokowski_adapter.py) derives
`SOURCE` from `__file__.resolve().parents[2]`. WorkingDirectory alone cannot bind
it: ExecStart must select the adapter in the reviewed checkout. Its argv is the
fixed interpreter, that adapter, `--current --runtime` and the qualified runtime.
Current mode ignores the finite duration deadline and polls until cancellation or
TERM/INT. Finite default mode, `--dry-run`, `--validation-stage`,
`--preview-dispatch` and `--reconcile-metadata` are separate modes, not service
readiness checks; even dry-run can contact Linear. Do not execute them here.

[`stokowski_prepare.py`](../../tools/delivery/stokowski_prepare.py) describes the
owner-prepared `current.json`: owner, runtime root, catalog, source head/file
hashes, workflow, policy and installation hashes. The adapter checks those pins,
qualified catalog admissions and per-task source/branch/request bindings; it
holds runtime and root-wide exclusive coordinator locks. Preserve immutable
intents, private owner journals and unknown leases. The worker's final
`Pool.admit`, scope and fresh provider checks remain authoritative. Eight coding
workers is a ceiling, not a load target. No `automatic_start` or
`legacy_workers_resume` change is authorized.

`HOME`, `USER`, `LOGNAME`, `LANG` and the minimal PATH are explicit non-secret
values. `UnsetEnvironment` removes both Linear key environment names, selecting
`credential()`'s `CREDENTIALS_DIRECTORY/linear-api-key` route. The coordinator
reads that existing credential into memory without exporting it. The worker's
`child_environment` SAFE_ENV excludes `CREDENTIALS_DIRECTORY`,
`OFFMENU_LINEAR_API_KEY` and `LINEAR_API_KEY`.
[`symphony_codex.py`](../../tools/delivery/symphony_codex.py) references the
existing native auth path from a private temporary Codex home without copying
credential contents. No auth inspection or provider/model invocation is part of
this proposal's checks.

Environment handoff isolation does **not** prove that same-UID coding children
cannot access credential mounts/files or parent memory. Existing trusted same-UID
execution remains the boundary; strict OS secret isolation is unproven. UMask
0077 supports private runtime files; it does not repair existing permissions or
set journal access policy. Normal journal output requires the existing private
journal access/retention contract; no key logging, exports or new telemetry.
No tested service-isolation claim is made. No unverified home/network/user,
privilege/syscall, read-only-path or task/memory sandbox knobs, bind mounts or
privileged cgroup operations are added; these could break native coding/auth.

SIGTERM reaches the coordinator first with `KillMode=mixed`; eventual timeout
kills the remaining service cgroup. The adapter stops dispatch, cancels workers,
waits up to 10 seconds for a worker process, then allows pending control and loop
settlement up to 30 seconds each. `safe_stop` also gathers cancelled tasks, so
these waits do not prove a total bound. Proposed `TimeoutStopSec=120s` leaves
margin over 10+30+30 seconds, but shutdown/descendant cleanup under this unit
still requires runtime qualification. A forced kill leaves effects uncertain.

`Restart=no` avoids automatic replay while owner-loss recovery is unproven.
Binding/admission failures normally exit 2; retained intents and leases must be
reconciled before any manual restart. Process restart capability is distinct
from end-to-end recovery. This source proposal proves neither continuous BAU nor
unattended publication. [ADR 0005](../adr/0005-autonomous-integration.md),
[ADR 0006](../adr/0006-typed-extraction-validation-and-refill.md) and the
[delivery workflow](../../tools/delivery/README.md) retain their authority.

## Future administrator adoption and reversal

These are future instructions, not commands executed by this source task.
Independent review/adoption, the exact owner source/runtime packet and the
existing credential reference must precede installation. Existing mandatory
action-time platform confirmation/access boundaries still apply; this adds no
routine human approval gate to admitted coding or integration.

1. At that boundary, verify UID 1000, exact clean source head/branch/file hashes,
   interpreter/installation and current.json/workflow/policy/catalog/admission
   hashes against the owner's packet. Check existing private runtime ownership
   and modes (directories 0700, private files 0600) without reading secrets;
   establish no competing current coordinator and reconcile unknown leases or
   uncertain effects through the existing owner flow. Do not clear locks/intents,
   bypass admission or audit unrelated services.
2. Render and independently review the exact unit bytes as above. The sole future
   target is `/etc/systemd/system/offmenu-stokowski-current.service`. Refuse an
   unexpected preexisting unit, drop-in or alias. If a prior version of this same
   target is known, capture its exact bytes, metadata and prior active state in a
   private reversible record before replacement. Preserve that backup. Stage the
   reviewed unit root-owned, mode 0640 or 0644, then install those exact bytes;
   no runtime or credential data is copied by this step.
3. Only under that installation authority, reload the system manager and start
   `offmenu-stokowski-current.service` once; do not enable it. Limit unit readback
   to `Id`, `FragmentPath`, `User`, `Group`, `MainPID`, `ActiveState`, `SubState`,
   `Result`, `ExecMainStatus`, `Restart`, `KillMode` and `TimeoutStopUSec` for this
   target. Do not dump Environment, ExecStart, full unit contents or credential
   values. Verify the non-root role and expected installed fragment.
4. Use the existing private owner journal and receipts to establish coordinator
   binding and coding admission. Record terminal unit review and served-refill
   proof separately; a running PID, provisional refill, successful coding exit or
   process restart does not establish parent acceptance or all BAU. No live
   Linear/Windmill job, deploy, Actions, CIX, Symphony or historical-worker resume
   is authorized by this source proposal.
5. To stop, act only on this new current target. Preserve journals, leases, intents,
   datasets and history; reconcile child cleanup/effects before restart or
   rollback. Do not stop/kill old workers or either named existing service.
6. For rollback after stop, cleanup and reconciliation, restore the captured prior
   same-target file/metadata if known. Otherwise remove only the new unit file
   proven created by this approved installation, then reload the manager. Do not
   delete runtime/credential data, enable/disable services or automatically start
   a restored unit. Any subsequent start follows the existing action-time boundary.

## Bounded source validation

Use a temporary Python ConfigParser/argv inspection to verify exact unit fields,
markers, credential ID/reference, no Install section or forbidden sandbox knobs,
and the worker SAFE_ENV exclusions without importing executable adapters. Run
`discover`, `check`, layout and whitespace checks with the existing pinned
`/home/user/src/offmenu/.venv-delivery/bin/python`, `PYTHONPATH=src`.
Do not bootstrap/install the absent workspace environment, run systemd programs
(even offline), launch a coordinator/provider/model, or run long suites for this
template/doc proposal. Static success proves source shape only; rendered-unit,
credential access, shutdown, recovery and actual coding/refill behavior remain
unvalidated until separately authorized qualification.
