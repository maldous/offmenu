# Native Stokowski admission and runner boundary

UIF-124 uses the existing adapter and finite worker. It adds no queue, controller,
receipt migration or runtime activation. Source is based on the accepted PR194
merge `37f733cc29627c6f137eb7905221dfabe39a7ecb` plus the UIF-121 source contract
`57257b314a21aa4686dc8391c662e622dee7d85b`. Runtime adoption belongs to the
integration/activation owner after independent review and coherent qualification.

## Pinned native behavior

`stokowski-source.json` pins upstream revision
`339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16`. The inspected installed
`config.py`, `orchestrator.py` and `runner.py` match that manifest's byte hashes.
The native orchestrator retains priority ordering, stage runner selection,
dependency eligibility, global/per-state concurrency caps, slot accounting and
retry backoff. The adapter's current poll wrapper refreshes admission and finite
validation before delegating to the native tick; it does not implement a second
scheduler. Native retry timers confer no permission to replay retained work.

The admitted workflow requires exactly one selected project. Upstream
`ServiceConfig.agent_env()` and `resolved_api_key()` already delegate to that
project. Only the project's implementations require overrides: the child gets
the existing environment allowlist and the tracker client gets the owner-held
key. The duplicate service overrides are removed. The native no-project legacy
fallback is outside the adapter's admitted workflow.

Upstream's Codex command uses legacy `--quiet`, so its runner cannot replace the
finite worker. The observed Foo CLI is `codex-cli 0.162.1`; local `exec --help`
confirms `--json`, `--ignore-user-config`, sandbox, model, working-directory and
last-message flags. The worker keeps the approved command and confinement binder,
existing authentication reference, isolated state, finite timeout and owned
descendant cleanup. No model turn is needed to inspect CLI help.

## Admission and retained evidence

Fresh provider/resource admission, canonical source/issue/owner binding, logical
write scope and dependency checks remain required. The durable Pool and retained
dispatch intent, worker intent and receipt remain authoritative across restart.
Cleanup uncertainty retains the original lease. A stopped timeout or cancellation
retains its precise receipt status; failed qualification only downgrades a process
success, rather than overwriting an uncertain or stopped outcome. Cancellation
releases only after proven child termination, with a cancelled Pool outcome.

The adapter projects success only with explicit stopped-child evidence. Its native
attempt and ledger model field contain an observed model only when the worker
reports `resolution_status: observed` with a nonempty model. Missing, legacy or
unknown resolution projects `null`. The bounded report keeps requested model,
resolved model and resolution status separately; a request is not an observation.
The original receipt stays intact even when the native attempt projects failure.

No existing attempt, lease, operation or job ID is rewritten, including UIF-117.
ADR 0008's exact refusal/replacement witnesses remain in force. Historical
byte-digest evidence pins and typed readers retain their original meaning.
This component emits no new shared handoff; new handoffs belong to UIF-122's
validator, using `fingerprint(policy)` for the new policy identity only.

## Bounded local verification

From the component checkout, use the existing delivery Python with `PYTHONPATH=src`
and unittest discovery under `tests/delivery` for `test_stokowski_adapter.py`,
`test_stokowski_worker_regressions.py` and `test_stokowski_current_dispatch.py`.
These exercise real local Git/SQLite and finite synthetic processes with provider
and tracker boundaries replaced. They cover fresh/deferred admission, native
caps/backoff/dependencies, restart/no replay, immutable identities, refusal,
unknown cleanup, cancellation, model observation and source-bound reports.
They do not establish live provider readiness or installed-runtime acceptance.
Exact commands, results and hashes belong to the private source handoff packet.
