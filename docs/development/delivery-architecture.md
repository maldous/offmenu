# Discovery, delivery and maintenance architecture

The [repository standard](../standards/repository.md) and retained ADRs define
source decisions; [task routing](task-routing.md) defines accountable owners.
[ADR 0005](../adr/0005-autonomous-integration.md) adopts Stokowski for admitted
coding and evidence-bound integration. Earlier Symphony records and the existing
`symphony_*` implementation filenames remain historical provenance and compatible
interfaces, not a second current orchestrator. Standard 2.3.0 adopts
[ADR 0006](../adr/0006-typed-extraction-validation-and-refill.md), including a
separate reviewed-extraction origin that never fabricates a coding attempt.

The [developer workflow](../../tools/delivery/README.md) contains execution and
recovery commands; [verification evidence](../../tools/delivery/validation.md)
separates exercised behavior from configuration. Linear owns the current phase
and evidence links. This guide owns maintained architecture, not a duplicate queue.

## State and evidence ownership

| Owner | Authoritative state and required identity | Source and boundary |
| --- | --- | --- |
| Linear outcome owner | Requirement, dependencies, decision and acceptance phase; link issue, source, run and evidence identities. | [Routing and tracking](task-routing.md). An assignment or Done state alone is not execution or product acceptance. |
| Stokowski coding owner | Admitted manifest/run, native session/attempt, lease, exact branch/base/workspace/path scope, resource declarations and model request. | [Worker](../../tools/delivery/stokowski_worker.py), [task contract](../../tools/delivery/symphony_tasks.py), [capacity admission](../../tools/delivery/symphony_capacity.py). Session completion produces a candidate, not independent acceptance. |
| LangGraph runner owner | Finite decision state and same-mount SQLite checkpoint; immutable task/schema version, source, branch, command and output witnesses. Retain exact runner/behavior and policy pins for the selected operation. | [Engine](../../src/offmenu/delivery/engine.py), [integration controller](../../src/offmenu/delivery/integration.py). A checkpoint is neither an external-effect receipt nor an off-host backup. |
| Immutable operation owner | Origin, accepted base/head, workspace, review/output/policy/runner/executor hashes; intent, exact logical operation/backend IDs and observed receipt. | [Operation journal](../../tools/delivery/stokowski_operations.py), [stage binding](../../tools/delivery/stokowski_stage.py). Reconcile the same immutable operation after uncertainty; never rename an unknown effect into a new attempt. |
| Windmill/backend execution owner | Exact server job and logical backend job, resource admission, execution status, receipt and verified stopped child tree. | [Typed dispatcher](../../tools/delivery/windmill_dispatcher.py), [native MCP adapter](../../tools/delivery/stokowski_mcp.py), [Foo runner](../../tools/delivery/windmill_runner.py). Wrapper success alone is not accepted output or external-effect reconciliation. |
| GitHub and sole integration owner | Exact candidate/base/tree, independent review, bound validation, normal merge and canonical parent/tree/ancestry readback. | [Integration policy](../../tools/delivery/integration-policy.json), [controller](../../src/offmenu/delivery/integration.py), [gateway](../../tools/delivery/integration-gateway.mjs). Only the authenticated integration owner consumes typed merge actions. |
| Sole publisher | Authorized deployment intent/result and canonical version/traffic readback; separate served hashes and functional acceptance evidence. | [Publication boundary](../../tools/delivery/README.md), [protocol handover](execution-protocols.md). Source integration, deployment, served content and functional acceptance are separate phases. |
| Evidence custodian | Private facts, checkpoint/log custody and restricted source/data/configuration holds; publish only permitted references and sanitized hashes/status. | [Repository standard](../standards/repository.md). No raw datasets, credentials, private profiles or runtime receipts enter Git. |

This retained integration gateway runs in the authenticated connector owner's durable
execution context. It is not an independently authenticated local publisher or
an installed continuous supervisor. Loss of that owner pauses publication while
retaining intent. LangChain Core supplies LangGraph integration dependencies;
this does not install another manager. LangSmith/private telemetry remains disabled.

The selected [UIF environment policy](../agents/uif-worker-policy.md) owns the
broader unattended lifecycle and off-Foo-authority contract. The limitations of
this retained adapter do not establish installed outage recovery or a new pause
for independent work or existing authorized capacity.

## Retained adapter recovery and execution limits

Checkpoint persistence is not exactly-once external execution. Reopen validates
source, schema/task identity, behavior/runner/policy bindings and output evidence;
completed effects must not be replayed merely because a caller lost its response.
A changed contract requires a new reviewed binding, while unresolved effects keep
their original operation identity until reconciled. SQLite and cooperative locks
are not distributed locks or independent backups.

Process cleanup and external effects require separate evidence. A stopped child
can leave an uncertain upload or merge; a recorded remote effect does not prove
the local child stopped. Environment disconnect, timeout, cancellation intent or
absence of chat updates never proves termination. Retain ownership until the
backend receipt, child cleanup and any external readback establish the outcome.
Retries remain bounded by the original safe-retry declaration and remaining
budget; command effects are not automatically rolled back.

[Ready-refill observations](../../tools/delivery/stokowski_refill.py) are currently
provisional and return `dispatch:false`. They neither reserve capacity nor admit
or dispatch the next task. Existing admission must recheck scope, source, provider
freshness and aggregate resources before work. There is no new polling manager,
schedule or permission to resume historical workers or the paused hourly automation.

This adapter's reviewed native coding configuration requests `gpt-6.1-sol` /
`medium` through `codex-chatgpt`.
Receipts distinguish that request from an observed resolution or explicit unknown.
Declared resources, affinity and sampled process/RSS observations are distinct;
they do not prove a kernel quota. Deterministic jobs have no model. The
[retained adapter's 8 coding / 16 service / 32 admitted jobs / 64 subprocesses ceilings](parallel-capacity.md)
are distinct from current UIF host capacity. The environment policy owns the
64-local-session target and quota handoff, subject to current runtime readback,
shared resource admission and qualified ownership controls. No ceiling is a
utilization target or guaranteed provider entitlement.

At the UIF-119 documentation checkpoint, compact observer correction
`0becb3a668d60910c9553118a2ff54bb0552c408` has independent candidate acceptance;
its source integration and runtime readback remain pending. This is separate from
PR152's adopted standard/extraction source. Finite restart/reopen evidence does
not establish continuous autonomous recovery or continuation after cloud-owner loss.
Current phase/readback belongs in [UIF-119](https://linear.app/maldous/issue/UIF-119),
not an assumption that this checkpoint remains current indefinitely.

One authorized native publisher route uses root systemd `LoadCredential` and
references `cloudflare-api-token` through `CREDENTIALS_DIRECTORY`; credential
values and private custody remain outside this guide. That route is distinct from
ChatGPT MCP product-scope OAuth. Native credential presence or expiry is not causal
proof of an MCP fault or repair, and this document establishes no new service,
credential transfer, access grant or failover route.

## Canonical end-state design and remaining proof

The [accepted editable graph, version 2.1](delivery-architecture/README.md)
is preserved here with its [layout JSON](delivery-architecture/layout.json),
[accepted SVG](delivery-architecture/accepted.svg) and exact Library
[source custody](delivery-architecture/source-custody.json). It contains the
24-node / 44-relation end-state design: a target model, not proof that every
path is live or enforced. The existing graph owner `/root/resume_hld_layout`
controls canonical revisions and renders. This repository copy preserves the
accepted design; it creates no competing graph or runtime acceptance claim.

Interpret its operation annotations with the corresponding state owners above:

- `022`, Windmill to integration: target handoff, not proof of an autonomous integration consumer.
- `035`, isolated coding to scoped tools: target capability, not proof that coding children hold those credentials.
- `040`, checkpoint and journal: complementary state, not exactly-once effects.
- `030`, owner-loss continuation: still requires actual supported recovery proof.

Graph labels ChatGPT/Claude and Codex/Claude describe targets. They do not establish
Claude installation, runtime entitlement or permission for paid inference. Broader
recovery and MCP consumer/task-binding acceptance remain explicit evidence gaps.
Preserve the existing no-Actions, no automatic deployment, no new spend/access or
credentials, no raw-data export, no OSM and no CIX-runtime boundaries. Historical
ADRs and accepted source evidence remain retained; new implementation increments
need their own bounded owner, source/review/output binding and normal admission.
