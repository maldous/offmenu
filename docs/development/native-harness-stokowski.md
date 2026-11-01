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

## Owner-sealed normal boundary wiring

The optional `current.json` field `native_harness_boundaries` maps an admitted
issue identifier to a private `{path, sha256}` selection reference. Its presence
requires actual protected owner custody; mutable legacy configuration cannot opt
into this route. The selection has exactly:

```json
{
  "binding": {
    "issue_id": "canonical issue UUID",
    "project_id": "canonical project UUID",
    "owner": "existing owner",
    "packet_sha256": "shared packet fingerprint",
    "operation_id": "original transaction ID",
    "phase": "linear",
    "unit_sha256": "shared original gate fingerprint"
  },
  "packet": {"path": "/private/pinned-packet.json", "sha256": "file-byte hash"},
  "context": {
    "engine_root": "/private/existing-engine-workspace",
    "engine_task": {"path": "/private/original-task.json", "sha256": "file-byte hash"},
    "unit_review": {"path": "/private/original-unit-review.json", "sha256": "file-byte hash"}
  }
}
```

This illustrates fields, not an admissible packet: hashes must be lowercase
SHA-256, identities must match the existing owner/project/unit, and all paths
must be canonical within the existing private runtime root. The phase is
`linear`, `integration` or `release`. Context references identify the existing
Engine task and independent review; they do not establish acceptance. Packet
file-byte pins remain distinct from `packet_sha256 = fingerprint(packet)`.
All runtime/contract/planner/release/Engine/status source and concrete factory
dependencies must be in the reviewed installed closure and its source pins.

A `linear` phase may use exactly `context: {}` because metadata planning does
not consume Engine or unit-review artifacts. It still requires the original
CurrentWork admission/native gate, owner/source/dependency checks, durable intent
and native effect readback. Existing nonempty contexts retain every prior
reference check. Integration and release require the genuine three references;
an empty context or a publisher-invocation-only context cannot bypass them.
This adds no Done, lease-release or refill authority.

The sealed selection's context may additionally contain `publisher_invocation`
with exactly `version: 1`, `closure_sha256` and `host_confirmation_sha256`.
Both hashes are lowercase SHA-256. Its bounded shared fingerprint remains part
of the complete pinned selection identity; no command, path, UID, environment
or callback selector is accepted. Ingress validates this metadata without
invoking a helper or reading publisher configuration. The separately reviewed
fixed client/helper must qualify the exact closure and actual host confirmation
under the existing publisher owner before use. A permission listing or a
successful read-only permission check cannot mint this authority. Absence adds
no capability and preserves the direct UID 1000 hold; no default is enabled.

The existing current-mode poll calls `continue_native_harness` after ordinary
validation/review continuation, under its existing coordinator lock. It consumes
one configured admitted unit per poll, rotating within that existing catalog.
It calls the fixed installed `native_harness_runtime.owner_adapters` function and
passes the coordinator's existing Linear client. No credential getter, callback,
module, command or principal is selected by issue/configuration JSON. A missing
concrete factory remains `native_harness_adapters_unavailable`; injected Python
factories are an explicit trusted installation/test seam, not a JSON API. The
consumer and its factory must be independently accepted before coherent adoption.

Source/config/selection/packet/native-unit checks repeat at the permission
boundary, and owner authorization must return exactly `True`. The original
transaction journal owns pending/unknown/denied effects; the adapter's saved
`native_harness` projection is diagnostic only. It neither grants replay nor
releases a lease. No new operation, queue, receipt migration or controller is
created. An interrupted boundary records a hold and reconciles that same
transaction through the existing adapters on the next poll.

Synchronous review/refresh callbacks cannot admit a successor for a bound trigger
merely from a saved verified projection. Only an immediate verified transaction
result with proven stopped children can lend the existing successor consumer an
in-memory permit, bound again to the exact selection, unit and operation. The
permit is cleared before returning, including errors/cancellation. Restart and
ordinary synchronous callbacks require another owner-bound readback. All prior
successor/scope/admission/independent-review gates still apply. Unbound legacy
units retain their original path without importing or executing the new consumer.
