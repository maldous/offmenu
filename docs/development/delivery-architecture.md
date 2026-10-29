# Discovery, delivery and maintenance architecture

Repository standardization is the first applied workstream. Source decisions,
accepted outputs and recovery evidence survive a model/session change through
versioned Git content and explicit runtime records. No model memory is the
source of truth. The [developer workflow](../../tools/delivery/README.md) contains
runnable commands; [verification evidence](../../tools/delivery/validation.md)
distinguishes actual execution from configuration.

| Component | Responsibility and implemented boundary |
| --- | --- |
| Git and versioned standards/ADRs | Durable reviewed source, architecture decisions, migration maps and exact base/head identities. One integration writer; reviewed integration into develop. |
| Linear | Existing OffMenu project records selected tasks, dependencies, decisions/workpads and acceptance links. It is optional for local execution. Historical operational obligations remain in their existing records; they were not imported wholesale. |
| Native Foo execution | Repository reads, builds, tests and coding commands run on Foo. Parallel agent owners are distinct from separate native Codex sessions; receipts state which actually ran. |
| Symphony | OffMenu-owned native launcher admits an exact project/issue/label, source head, bounded coding turn and isolated workspace using existing credentials. It produces candidate changes; it does not establish acceptance. |
| LangGraph | Finite discovery/standards/execute/verify graph with same-disk SQLite checkpoints. Bindings include immutable task, checkout, owner, exact branch and source/output witnesses. Recovered acceptance cannot reuse stale source or output checks. |
| LangChain | Core integration dependency of LangGraph; no additional agent manager, model router or autonomous orchestration loop is installed. |
| Windmill | Existing deployed Foo bridge executes bounded deterministic jobs with explicit job IDs, logs, stop/reconciliation state and runtime ownership. Worker mount paths are explicit. A successful wrapper is not accepted output. |
| LangSmith | Optional future observability. Private telemetry remains disabled; no credentials or paid tracing were configured. |

## Records and checkpoints complement each other

Linear records what was requested, why a decision was made, dependencies and
what evidence supports acceptance. A task record cannot restore an interrupted
subprocess. LangGraph checkpoints record execution decisions on one retained
mount; they cannot replace a durable human-readable decision/work record.
Windmill receipts establish the observed operational outcome. Git preserves the
source and approved standard. Handover connects these exact identities.

The normal flow is discovery of actual manifests/consumers, a versioned standard
and ADR, bounded edits, behavior checks plus output hashes, reviewed publication,
and verification of remote content. Maintenance repeats this flow with a new
immutable task ID and selected source revision. Do not replay old command IDs
after changing their task/source.

## Implemented recovery and limits

A crash/timeout/cancel leaves an explicit hold until the process tree and effects
are reconciled. Failed reconciliation can record a stopped failed operation even
when source was changed or removed; it cannot bless that drift as success.
Successful checks bind the bytes actually observed. Retry requires the original
safe-retry declaration and remaining finite budget. No transaction rolls back
arbitrary command effects.

SQLite checkpoints are local, not a distributed lock or off-host backup. The
checkout writer lock only coordinates cooperating callers. Native coding output
is reviewed separately from session completion; Windmill logs are checked
separately from its wrapper status. The selected branch and accepted hashes are
verified before publication. Existing source qualification and private-data
holds remain independent of layout acceptance.

## Proven versus future use

Implemented and exercised: native Symphony coding output reviewed into the CLI
and final-layout audit tests; LangGraph pause/resume, drift/collision/recovery
regressions and accepted-output checks; Windmill execution through the existing
Foo bridge; reproducible package/bootstrap and application build consumers.

Linear's selected project/issues and native admission are configured and used.
Broader task intake, historic-obligation migration, cross-host recovery, automated
release decisions and LangSmith expansion are future choices, not implied by the
pilot. No new scheduler, recursive manager, automatic merge/deploy or resumption
of frozen workers is introduced. Existing Codex/Antigravity allowances and
OpenRouter free models are authorized; new API charges and paid OpenRouter models
are outside the selected routes.
