# Native finite graph and recovery

UIF-125 extends the existing `offmenu.delivery.engine.Engine`, `StateGraph` and
local `SqliteSaver`. It keeps the original task ID as LangGraph's thread ID,
`.delivery/<task-id>/graph.sqlite`, writer lock, command/acceptance receipts and
legacy digest algorithm. It adds no storage driver, checkpoint migration,
LangChain manager or telemetry. Installed source and installed runtime adoption
remain separate.

## Run an immutable task

The existing CLI remains the operational entry point:

```sh
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  -m offmenu.delivery --root /absolute/isolated/worktree run /private/task.json
```

`--pause-after discovery|standards|execute|verify` stops at a native checkpoint.
Reopen with the same task file, root and task ID. LangGraph resumes with `None`
instead of resubmitting initial state, using synchronous superstep durability
supported by pinned LangGraph 1.2.18 and checkpoint-sqlite 3.1.2. No framework
retry policy wraps effectful nodes. If a command completed before the graph
checkpoint was saved, its existing successful command receipt suppresses replay.

The immutable task includes every command, timeout, original attempt budget,
retry-safe declaration, expected output and optional shared-contract value.
Changing it requires a separately reviewed identity; changing the owner or
branch cannot relabel a retry. The engine detaches the caller's input and checks
its task fingerprint at every source gate. Source, HEAD, branch and recorded
output drift block cached evidence reuse. Existing explicitly safe output
rechecks can spend only the remaining original attempt budget.

## Shared handoff and release facts

A task may additionally embed `handoff` (delivery-handoff-v1),
`release_candidate` (release-candidate-v1), or both. The engine imports the
UIF-122 `native_harness_contract` module from the reviewed tools path and loads
`config/delivery-release-policy.json` from the selected checkout. Missing shared
code or invalid policy/contracts fail before command execution. The engine does
not copy a validator or read referenced evidence files.

The validated source head must equal task `base_revision`, its branch and tree
must match the selected checkout, and its base must be an ancestor of its head.
Uncommitted input files cannot claim the committed source tree. Declared output
files may be produced by commands and remain covered by existing output evidence.
Handoff owner and exact output map must match the task. If both shared values
are supplied, their source values must agree. Candidate artifacts must equal the
exact expected output map. New policy identity uses UIF-122's canonical JSON
fingerprint; historical byte digests retain their original meaning.

Ordinary runs still require feature/bugfix branches. A validated release
candidate additionally permits a frozen `develop` checkout targeting `main`;
`main` itself is never an execution branch. This graph validates the frozen
source and artifacts. It does not aggregate required release profiles, promote
source, verify a tag or assert release acceptance. The candidate's profile list
is part of its immutable fingerprint. Advancing the checkout's HEAD blocks
reentry even if the new commit has an identical tree.

Run results and new acceptance receipts include `native_harness` with the exact
validated source, target, handoff/candidate fingerprints and accepted output map.
Before status `accepted`, that map describes required outputs, not a claim of
completed validation. After acceptance it matches freshly checked output bytes
and command evidence. Existing legacy receipts retain their fields and readers.
A graph acceptance is local command/output validation, not independent source
review or runtime acceptance. Read-only/reviewed source origins never fabricate
coding attempt, lease, operation or job IDs.

## Effect recovery ownership

The graph never submits or reconciles a referenced external operation. A handoff
with a non-succeeded operation or a non-verified effect blocks execution and
acceptance. Its original operation/job/evidence identity remains unchanged;
return it to its existing Windmill/GitHub/Stokowski owner. Updating an old task's
handoff to upgrade an uncertain effect also changes its immutable task binding,
so it cannot silently authorize replay.

Local `running`, `uncertain`, `timed_out` and `cancelled` command receipts retain
the existing checkout-wide reconciliation hold. Use the existing CLI
`reconcile` with stopped-process evidence, preserving the original attempt
number. Failed reconciliation does not need surviving source and cannot accept
outputs. Successful reconciliation still requires source/output proof. Neither
outcome replenishes attempts or grants permission to repeat an uncertain effect.

## Bounded verification

Use the pinned delivery interpreter and the reviewed shared module, with no
installation or live backend:

```sh
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  -m unittest discover -s tests/delivery -p test_engine.py -q
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  -m unittest discover -s tests/delivery -p test_native_graph_harness.py -q
PYTHONPATH=src:tools/delivery /home/user/src/offmenu/.venv-delivery/bin/python \
  -m unittest discover -s tests/delivery -p test_cli.py -q
```

These exercise real native SQLite checkpoints and subprocess CLI reopening,
command-receipt recovery after graph interruption, immutable retry budgets,
source/output rejection, fixed release identity and unknown-effect holds. They
do not qualify installed service adoption or external effect reconciliation.
