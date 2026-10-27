# Confined OffMenu job execution

This runner operates **inside** the existing `offmenu-wm` SSH/bubblewrap boundary.
It does not change host grants, SSH keys, network isolation, or mount exposure.
The checkout is `/offmenu` here, not its canonical host path. Do not create/prune
Git worktrees through this mapping without a separately reviewed path design.

## Interface

```text
python3 scripts/windmill/job_runner.py run --job-id ID --mode read|write --timeout SECONDS
# stdin: {"command":"approved command"}
python3 scripts/windmill/job_runner.py status --job-id ID
python3 scripts/windmill/job_runner.py cancel --job-id ID
```

IDs are 1–80 ASCII letters/digits/`_.-`, beginning with a letter/digit. Timeout is
1–1800 seconds after admission. Admission is nonblocking: busy does not reserve an ID. Each command is at most 32,000 UTF-8
bytes. Commands remain subject to the user's authorized scope; `read` is a trusted
scheduling declaration, **not a read-only filesystem security boundary**.

The default state root is ignored `data/.offmenu-platform/`, containing `jobs/`,
`artifacts/`, `locks/`, and `checkpoints/`. The source helper, tests and client are
tracked source, not stored only in ignored runtime state. A receipt includes the
command SHA-256, helper source SHA-256, job ID, state, timing and exit code. Actual
commands and credentials are not copied into receipts. Commands can themselves
write sensitive output: only run reviewed commands; do not export logs indiscriminately.

A job-ID directory is reserved atomically before execution. Identical retries return
its existing receipt; changed commands/limits/helper versions conflict. Missing or
stale receipts are **unknown**, never automatic permission to replay with this or
a fresh ID. Side effects and receipts are not a distributed transaction: process,
OS or disk failure can leave an uncertain result requiring reconciliation.

## Scheduling and supervision

Two execution-slot locks admit at most two cooperating jobs. Jobs with declared
timeouts above 30 seconds also require a single long-job lease, leaving Windmill
control capacity. Short calls may still delay control for up to their deadline.
Incompatible or full admission returns busy immediately; it does not wait on a worker. Writers hold an exclusive
access lock; readers share it. Start with one writer and independent parallel reads,
not parallel edits to the same checkout. External tools and other host users do not
participate in these advisory locks. Logs have independent 1-MiB storage limits;
excess output is drained and discarded to avoid deadlock. Receipts report truncation.

The supervisor uses a process group and Linux subreaper, hard kills descendants on
timeout/cancellation, reaps them, and reports `child_tree_gone`. Cancellation is a
shared job-ID marker, because each SSH call has its own PID namespace. A cancellation
request is **not** proof of termination: inspect the final receipt. SIGKILL/host crashes
cannot be handled by user-space code. Durable per-slot in-flight markers survive
supervisor death and block incompatible admission until explicit reconciliation.
Markers are removed and the parent directory fsynced only after verified cleanup
and a final receipt; never clear one merely because a PID or heartbeat disappeared.

## Windmill

The `windmill_foo_jobs.py` client accepts action, job_id, command, mode and timeout_seconds.
It pins the trusted SSH host key, retrieves the private key internally from the fixed
Windmill secret path, disables agent/key discovery, and uses only `offmenu-exec-v1`.
It returns compact receipts, not log bodies. Its `transport_ok` field describes receipt
transport/validation; `ok`/`job_succeeded` are true only for succeeded jobs. Inspect
`admitted`, `receipt.status`, `exit_code`, and `child_tree_gone`. For long calls use a Windmill background
run and track its job ID; do not detach a remote shell and assume it will survive.
The client drain budget is the requested job timeout plus 20 seconds. Windmill's own
workspace/job limits may terminate it sooner; verify those before very long batches.

Persistence here means survival of normal client/session disconnects for already
written receipts/logs, **not independent backup, disk-loss protection, or guaranteed
survival of an active command after SSH/Windmill termination**. Interrupted work is
reconciled by ID, not silently restarted.

## Validation

`python3 -m unittest discover -s scripts/windmill -p test_job_runner.py -v`
uses synthetic temporary artifacts only. It covers duplicate/unknown IDs, conflicts,
writer serialization, overlapping reads, capped dual-stream logs, cancellation, and
termination/reaping of a child that changes its session.
