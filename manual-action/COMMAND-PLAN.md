> **Historical planning record, superseded for routine operation:** root `./run` now executes the reviewed finite `retained_ingest_all` plan (schema 2, job version 1), with actual parallel adapters for all eight domains, local resumable staging, and automatic strict sanitized checkpoint/final receipt commits and pushes. The supplier-only plan and future-tense statements below describe the earlier package, not the current implementation. See `README.md`, `plan.json`, and the `ingest_*.py` adapter closure. One-time bootstrap: `git pull --ff-only && ./run`. No source archive or raw/private data is uploaded.


# Manual command plan: order and feedback

Planning only — 22 October 2026. Foo is currently unavailable; this document starts no jobs. It does not implement or qualify a retained-data importer. The small supplier-filename correction is separate and does not wait on this plan.

## What the current package actually does

| Command | Work and ordering | Feedback available now |
| --- | --- | --- |
| `preflight` | Read-only known-path/disk/process metadata, sequential | Final private JSON and optional sanitized summary |
| `inventory` | Bounded metadata-only directory discovery, sequential | Final private JSON and optional sanitized summary; incomplete scans explicitly truncated |
| `supplier` | Fixed archive identity, safety and source-member inspection, sequential | Final private manifest/checksums and optional sanitized summary; human source review still required |
| `collect` | `preflight` → `inventory` → `supplier`, in that order | End-of-run results, not streaming progress/checkpoints |

These are short checks, not background import jobs. The observation phase has a 30-second alarm; final exclusive JSON writes/fsync occur afterward. Nothing is uploaded automatically. After the filename correction, only the blocked **supplier** step needs rerunning with fresh output names; the successful preflight/inventory need not be repeated merely to validate that fix.

## Planned order for a future qualified long run

1. **Reconcile existing work first.** Read the current run/checkpoint/lease state without changing healthy jobs. Unknown or apparently running attempts must be reconciled before any retry; missing feedback is not proof that a process stopped.
2. **Qualify each selected operation.** Bind its exact accepted source and caller revisions, rights, input/custody identity, allowed transformation, output destination, finite resource limits and terminal-receipt requirements. Source presence or a successful diagnostic is not import authorization/readiness.
3. **Respect dependencies.** Required source/caller review, input verification and output preparation precede the dependent operation. A later stage consumes only an accepted predecessor result, never a guessed or half-written output.
4. **Parallelize only independent qualified work.** Independent checks or operations with separate safe outputs may overlap when their combined CPU, memory, disk/I/O and free-space budgets permit it. Set concurrency from the actual resources and operation contracts; no fixed worker count is assumed here.
5. **Serialize shared writes.** Use one writer per target database, with explicit ownership/exclusion. Do not run competing loads, migrations or repairs against the same store. Existing jobs and the working scanner retain their resources and ownership.
6. **Finish with a terminal result.** Record completed, failed or blocked status and the exact remaining action. A checkpoint or process start is not completion. No destructive cleanup, automatic replay or uncontrolled retries.

There are currently **no runnable HTML, PDF/cache, UniTools or supplier import commands** supplied by this package. The above is the contract for building and reviewing them, not instructions to launch hypothetical loaders.

## Planned live feedback and result-return contract

For a future long-running implementation:

- **Live local feedback:** readable phase/progress output and a bounded private local log, with explicit log-size limits. Record source/caller pins, selected operation, input identity and detailed errors privately. Never display credentials or raw dataset bodies merely to report progress.
- **Periodic sanitized checkpoints:** small versioned records at meaningful phase boundaries and an agreed bounded interval. Include generated run/attempt ID, sequence, observation time, phase, status, safe aggregate progress, source/caller hashes and fixed error codes. Omit host paths, PIDs, command lines, environment, private control values, raw rows and source bodies. Publish each checkpoint atomically; identify the terminal record distinctly.
- **User-controlled return:** the user may paste/attach checkpoints, or explicitly commit/push only the selected sanitized checkpoint file(s) to the private action branch while work continues. Never auto-push, bulk-stage the checkout or upload private logs. A sanitized final summary remains required.
- **Honest remote status:** cloud progress is only as fresh as the latest returned checkpoint. Silence means unobserved progress, not success or failure. A read-only status reconciliation must precede a restart if the previous attempt might still be running.

The current CLI has only final JSON output: live logs, periodic checkpoints, status/resume reconciliation and long-run orchestration described above are **planned, not implemented**.

## Execution route

Manual checkout/run/return remains the fast primary route. Use the existing reviewed GitHub Actions route only as an optional fallback when appropriate; it must not introduce arbitrary commands, broaden access or dispatch a duplicate of an uncertain/manual attempt. One-time source/fixture validation is not a per-run Actions rehearsal gate. Any fallback must report its actual executor and access limits rather than implying hosted Actions can see Foo's retained data.
