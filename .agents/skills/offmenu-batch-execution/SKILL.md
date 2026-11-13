---
name: offmenu-batch-execution
description: Execute and observe bounded OffMenu jobs through the existing Windmill SSH bridge and local job runner, preserving job identity, output limits and the no-network boundary.
---

# OffMenu bounded batch execution

Use `scripts/windmill/job_runner.py` in the actual `/offmenu` checkout. Verify the
installed reviewed helper's source/version and `--help`; source preparation alone
is not deployment evidence. No model, agent service or new plugin is involved.

## Select an explicit operation

Accept the approved local command, an explicit job ID, timeout and read/write
scheduling mode. Inputs/outputs stay within the existing mount. Do not infer that
historical `/home/user/...` data roots are available. Do not invoke the old root
`./run`, which performs Git network operations, through the no-network bridge.
Use the actual authorized local CLI/API; keep command arguments free of secrets.

The runner interface is:

```text
python3 scripts/windmill/job_runner.py --root /offmenu/data/.offmenu-platform run --job-id ID --mode read|write --timeout SECONDS
stdin: {"command":"the approved local command"}
python3 scripts/windmill/job_runner.py --root /offmenu/data/.offmenu-platform status --job-id ID
python3 scripts/windmill/job_runner.py --root /offmenu/data/.offmenu-platform cancel --job-id ID
```

IDs match `[A-Za-z0-9][A-Za-z0-9_.-]{0,79}`; timeouts are 1–1800 seconds. JSON on
stdin has exactly the `command` key. Quote/encode inputs rather than concatenate
untrusted text into shell syntax. Confirm the transport deadline permits the
selected timeout; do not detach an unsupervised process to evade that deadline.

## Run and establish the result

1. Reuse existing capacity observations only when they apply to this host and
   workload. Do not retry quota-blocked Foo/Codex environments until capacity is
   confirmed. Check the selected job ID first when recovering an uncertain call.
2. Submit one explicit operation through the existing bridge. The runner's two
   slots and shared-reader/exclusive-writer locks coordinate its own invocations.
   Admission is nonblocking, before ID reservation. A declared timeout over 30
   seconds also requires the single long-job lease, preserving control capacity.
   `busy` with `reserved: false` is not a started job; do not busy-loop retries.
   `read` is a trusted scheduling declaration, **not enforced filesystem
   read-only access**. Use `write` for mutations; unrelated processes are not
   protected by these cooperative locks.
3. Inspect the compact receipt. Match job ID, command hash and runner hash to
   this submission. A transport `ok` or exit code is not sufficient: establish
   the runner state and requested artifact/validation outcome. The jobs client
   separates `transport_ok`, `admitted` and `job_succeeded`; `ok` is true only for
   `succeeded`. `transport_ok` alone does not establish successful work.
4. If the caller disconnects, times out or returns truncated/uncertain output,
   read `status` for that same ID before further action. Duplicate IDs must not
   replay work; conflicting specifications must not be relabelled to force a
   retry. Reconcile unknown/stale state or `blocked_reconciliation` using the
   recovery skill; do not remove durable in-flight markers to force admission.
5. Report useful progress from compact status/counters. Observe until the
   requested terminal outcome or a real authorization/input blocker; an
   unchanged active state is not completion. Use Windmill background-job
   submission for long calls; the host supervisor itself remains synchronous,
   and session interruption does not guarantee that the process keeps running.

## Keep output and performance bounded

Raw stdout/stderr belong in the local job directory, each capped at 1 MiB by the
runner, not in tool/chat output or Git. The default receipt does not return them.
Inspect only a necessary safe diagnostic subset locally and return fixed status,
counts/hashes and error class. Never print environments or credential files.

For a batchable application, use its real cursor/transaction API and a bounded
batch; do not invent resume behavior for an arbitrary shell command. Reuse named
stdlib scripts, retained databases and source references instead of copying all
data or starting a process per row. Respect the application's resource limits.
Measure throughput and peak memory before raising parallelism; every job using
all visible cores can reduce total throughput. Third-party dependencies must be
already available and pinned per script; no online installation or workspace-wide
dependency-default changes. Do not claim a benchmark proves complete production
coverage.

## Inline failure evidence

Admitted failed/timed-out `run` operations raise safe business failures after an
inline owner-private incident write, so Windmill's run is red. Inspect the
matching job receipt and incident; never interpret transport completion as
business success. Unknown transport/cleanup outcomes remain reconciliation
cases, not retry permission. Busy and fresh active duplicate-ID observations
are normal data. Status and cancel actions do not manufacture new incidents;
a valid user cancellation stays quiet. Incident persistence failures do not
make failed work green. No nested long Windmill jobs are needed for capture.
