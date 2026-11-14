# Parallel capacity and task admission

## Current operating-policy boundary

The [environment-owned UIF policy reference](../agents/uif-worker-policy.md)
describes the new 64 Foo-local-session ceiling, shared resource admission and
quota handoff to active Morgan. The installed native runtime and effective
capacity policy must be read back before using that ceiling. This document's
older OffMenu adapter configuration is not the current multi-project host
capacity declaration and does not qualify the new mode-transition controls.

## OffMenu adapter source configuration

The retained adapter's configured ceilings are **8 / 16 / 32 / 64**:

| Layer | Configured ceiling | Enforcement/evidence |
| --- | --- | --- |
| Native Symphony | 8 coding sessions | capacity-policy.json, generated native workflow, durable reservation pool and exact manifest admission. |
| Windmill service | 16 workers | Existing Compose override replicas plus running-container/heartbeat readback. |
| Resource-declared Foo jobs | 32 | Reviewed windmill_runner.py slots and aggregate reservations. |
| Computation/job | 64 subprocesses | Declared ceiling, plus at most eight overhead processes; sampled descendant/RSS guards. |

Native collaboration's root-plus-six pool is separate. The cloud durable-task
platform concurrency limit is not established by that number. Subscription usage
windows are also separate from session concurrency and from paid API entitlement.

`tools/delivery/capacity-policy.json` is the reviewed source of this adapter's settings.
[ADR 0004](../adr/0004-resource-aware-parallel-capacity.md) records budget partitions,
tradeoffs and limits. No automatic coding/merge/deploy, schedules or telemetry are
enabled by choosing capacity. Existing Codex/Antigravity allowances and OpenRouter
free models are authorized; this implementation selects the existing Codex
ChatGPT session route and configures no alternative paid API provider.

## Native tasks

Create a reviewed private JSON manifest, then prepare a new finite runtime:

```sh
.venv-delivery/bin/python tools/delivery/symphony_launch.py prepare --runtime /home/user/src/offmenu-data/runtime/SELECTED-RUN --model gpt-6.1-sol --manifest /private/reviewed-tasks.json
```

Manifest version 1 contains `branch`, `base_revision`, the exact OffMenu
`project_id`, a selected Linear `label`, and `tasks` keyed by exact issue
identifier. Each task declares `issue_id`, `owner`, `purpose`, `allowed_paths`,
`acceptance`, `attempt_limit`, and resources (`cpu_millis`, `memory_bytes`,
`io_slots`, `output_bytes`). Up to eight disjoint tasks can reserve execution
concurrently; longer reviewed queues may contain more tasks. The existing native
tracker uses Linear, while local LangGraph execution remains independent of it.

`run` additionally requires the existing credential-injected environment and
`--inference-authorized`. That flag records established authority; it cannot
bypass platform approval or create provider entitlement. Fresh session/model
metadata and a local provider-session budget govern admission. Account/quota
metadata may be unavailable; do not invent a balance or guarantee eight provider
turns. Provider errors, uncertain effects and exhausted attempts require explicit
outcome review rather than automatic task-ID replacement.

```sh
.venv-delivery/bin/python tools/delivery/symphony_launch.py cancel --runtime /home/user/src/offmenu-data/runtime/SELECTED-RUN
```

Cancellation records intent and closes admission. The owned process tree must be
observed stopped before reservations are released. Source output is checked
against the exact allowed paths and remains unaccepted until integration review.

## Windmill jobs

This historical adapter binds `u/admin/foo_jobs_20261027`. Current UIF execution
must discover its selected `foo` workspace route and deployed schema from the
environment profile; do not retarget or replay historical jobs by name alone.
For this adapter, supply explicit
`resources` for pool admission: `workers`, `overhead_processes`, `cpu_millis`,
`memory_bytes`, `output_bytes`, `read_roots`, `write_roots`, and optional
`io_slots` (defaults to one). Requests retain exact job/command/runner/policy hashes.
Read/write roots must be canonical within `/offmenu`; overlapping mutable scope
blocks concurrency. Quota, current RAM, reserved CPUs, disk and I/O declarations
can reduce actual admitted work below the configured ceiling.

Legacy calls without `resources` retain two-slot/one-long-job compatibility.
They do not exercise the new resource-declared pool. Do not represent that mode
as thirty-two-way execution. Memory/process observation is sampled, and declared
resources require trusted callers; this is not hard cgroup enforcement.

Run the meaningful offline admission/lifecycle suite:

```sh
.venv-delivery/bin/python -m unittest discover -s tests/delivery -v
```
