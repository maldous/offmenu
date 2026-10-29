# Developer delivery workflow

This is an on-demand local workflow, with an optional Windmill entrypoint. It
never schedules work, creates branches, merges, pushes or deploys. Task JSON is
reviewed executable configuration: commands run with your account's privileges.
Keep credentials out of arguments, task files and outputs. This is not a sandbox.

## Bootstrap

Use Python 3.12 for the delivery environment (the application retains its declared
Python support). From the repository root:

```sh
python3.12 scripts/bootstrap_delivery.py
python3.12 scripts/bootstrap_delivery.py --check
.venv-delivery/bin/python -m offmenu.delivery discover
.venv-delivery/bin/python -m offmenu.delivery check
.venv-delivery/bin/python -m unittest discover -s tests/delivery -v
```

Bootstrap creates only the ignored project-local `.venv-delivery/`. `--check` checks all 41 locked versions without network; installation is repeatable from a clean checkout and never mutates system Python.

The optional `.[delivery]` extra pins the two direct dependencies; the lock pins
this verified Python 3.12 environment transitively. No provider, model or paid
inference is configured. LangGraph owns the finite graph and SQLite checkpoints;
LangChain core is its integration dependency, not a second autonomous manager.
LangSmith is installed transitively but tracing is disabled in graph execution
and child commands, even if a developer's shell enables it.

## Reviewed task contract

Create a task JSON under `dev/delivery/` with `version:1`, a lowercase hyphenated
`id`, `owner`, `purpose`, immutable `base_revision` (40-character HEAD SHA),
`checks:[{id,argv,timeout,attempts,retry_safe}]` and
`accepted_outputs:{"relative/path":"sha256"}`. Use the actual desired file bytes'
hashes, not hashes invented by the runner. Checks are explicit argument arrays;
there is no implicit shell. A shell explicitly named in argv remains executable
code requiring review. Require meaningful behavior checks, not just file existence.
The standards document and ADR describe how to discover and evolve standards.

```sh
.venv-delivery/bin/python -m offmenu.delivery run .delivery/accepted-layout.json --pause-after standards
.venv-delivery/bin/python -m offmenu.delivery status .delivery/accepted-layout.json
.venv-delivery/bin/python -m offmenu.delivery run .delivery/accepted-layout.json
```

Create the local validation task with `python -m offmenu.delivery prepare --task-id accepted-layout --owner YOUR-NAME`, then inspect its JSON before running it. The generated task verifies the delivered standard and tests; it does not generate arbitrary application changes.

The first invocation deliberately checkpoints after discovery and standards.
The next `run` uses the same ID/input and persisted graph state. Completed checks
have durable receipts and are not rerun. Before reporting acceptance, the graph
verifies every declared output hash. `status` reports recorded acceptance only;
it does not revalidate current files. `run` revalidates accepted output bytes.
A changed task with an old ID fails closed. A changed HEAD requires a newly
reviewed task. Tasks are bound to the checkout's absolute path, owner, and tracked/new source hashes (excluding declared outputs and the exact held paths listed in the standard). Source drift blocks cached check reuse.

Each check has a 1–600 second deadline, at most three explicitly safe attempts,
and a 1 MiB local log cap. One cooperative writer per checkout is admitted with a
nonblocking OS lock; unrelated developers and legacy runners do not honor that
lock. Do not run this against a checkout another tool is changing. The workflow
is finite (maximum 32 checks) and does not use Windmill's capability ceilings as
load targets. Returned JSON status `blocked` or `failed` is not accepted delivery.

## Recovery and cancellation

`.delivery/<task-id>/` contains the input binding, SQLite graph checkpoints,
immutable event files, bounded private logs and acceptance receipt. It is ignored
by Git. Retain it across developer/worker restarts on the same mount. These are
same-disk receipts, not off-host backups or distributed locks. Do not share the
SQLite file between hosts. Restrict runtime access to trusted developers.

```sh
.venv-delivery/bin/python -m offmenu.delivery cancel .delivery/accepted-layout.json
```

Cancellation records intent without waiting for the writer lock. The active
command is killed as a process group when observed; its final receipt establishes
whether it stopped. A crashed supervisor may leave children/effects uncertain. Unresolved command receipts block admission of every task in the checkout, even after its writer lock is released; explicit reconciliation is the only writer operation allowed through that hold.
Do not clear a lock marker, change IDs or rerun an uncertain step. Inspect the
exact local command, process tree and output artifacts first. A `running`,
`timed_out` or `cancelled` receipt requires explicit reconciliation. Provide a
private evidence JSON containing `observer`, `reason`, and
`process_tree_gone:true`, then:

```sh
.venv-delivery/bin/python -m offmenu.delivery reconcile .delivery/accepted-layout.json --check-id CHECK --outcome failed --evidence /private/reconciliation.json
```

A succeeded reconciliation additionally verifies all declared output hashes.
A failed reconciliation does not grant extra attempts; only remaining attempts
explicitly declared safe in the original task can run. Cancellation remains
terminal for that task and is not silently cleared. Arbitrary command effects
are not transactional or rolled back by LangGraph.

## Windmill boundary

`windmill_entrypoint.py` provides `main(task_path, action='status')` for review and
on-demand deployment to the existing worker. It requires the reviewed OffMenu
package and pinned dependencies preinstalled on a worker with `/offmenu` and its
private `.delivery` mount. It never forwards MCP credentials, installs packages,
creates resources, schedules work, or resumes prior workers. Use the existing
approved bridge to the checkout when Windmill cannot access that mount directly;
do not infer a shared filesystem from matching path names. This change validates
the adapter locally; live installation is a separate verified deployment step.

Use the same immutable task ID for retries. A remote timeout is uncertainty:
inspect the same local receipt and Windmill job before retrying. The adapter
raises failed/blocked outcomes so Windmill cannot interpret transport success as
accepted delivery. The local writer lock supplies admission without depending on
Windmill enterprise concurrency features. Existing platform job supervision and
storage remain separate; this runner does not replace their capacity/backup claims.
