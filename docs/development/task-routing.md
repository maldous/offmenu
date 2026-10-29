# OffMenu task routing and tracking

This runbook applies the existing ADR 0004 resource policy and ADR 0005 integration
boundaries. It changes neither admission ceilings nor publication authority and
introduces no manager, scheduler, provider entitlement or service dependency.

## Reuse frameworks while preserving project semantics

The project owner's architectural history distinguishes USF, the Universal Service
Foundation, from UIF, the infrastructure beneath it for Cloudflare, Netlify and
external services. Its semantic graph service definitions addressed some concerns
that OffMenu now wants to serve with existing LangChain/LangGraph capabilities.
That overlap is motivation to evaluate reuse, not evidence of technical equivalence.

Prefer an appropriate existing framework capability for graph execution, typed
integration or checkpoint persistence when it satisfies the actual OffMenu contract.
Do not grow another custom universal framework merely to recreate those features.
Retain valuable domain definitions, provenance, source eligibility and acceptance
semantics. LangGraph checkpoints alone do not replace the operation journal's
external-effect reconciliation or the authenticated integration owner's authority.
Any replacement needs an explicit mapping of responsibilities and evidence that
the relevant behavior is preserved; framework availability alone is insufficient.

This guidance is scoped to OffMenu. It does not authorize rewriting USF, UIF or
CIX, importing their entire backlog, or migrating an active operation. OffMenu
remains within UIF; no team transfer is required. Resolve current tracker bindings
through the Linear owner rather than hardcoding a new team identity. Keep existing
issue/run/operation/job identifiers and running work stable.

## Documentation homes and update responsibility

| Subject | Canonical home | Who updates it and what other homes reference |
| --- | --- | --- |
| Active outcomes, bugs, owner, status, dependencies and acceptance | Existing [OffMenu Linear project](https://linear.app/maldous/project/offmenu-ccd080f4f6f0) and its issues, for example [UIF-106](https://linear.app/maldous/issue/UIF-106) | The issue owner records work/evidence; the Linear owner maintains project organization and reconciles duplicates. Repo handovers link the active issue and evidence, not a copied active queue. |
| Architecture, source/interface contracts, setup and runbooks | Versioned repository, indexed by [docs/README.md](../README.md); [maintainer setup](../maintainer.md), [layout](root-layout.md), [protocols](execution-protocols.md) and [delivery workflow](../../tools/delivery/README.md) | The source-change owner updates affected maintained guides/interfaces in the same reviewed candidate. Linear links the relevant path and source revision instead of copying the full document. |
| Decisions, rationale and supersession | [Repository ADRs](../adr/), including [ADR 0004](../adr/0004-resource-aware-parallel-capacity.md) and [ADR 0005](../adr/0005-autonomous-integration.md) | The decision owner proposes a new ADR when required; review records adoption/supersession. Preserve old rationale and mark superseded decisions with a successor reference rather than rewriting history. Standards changes still require the normal version/ADR process. |
| Actionable agent entry rules | [AGENTS.md](../../AGENTS.md) | The repo-doc/source owner maintains concise actions and links to canonical guides. AGENTS does not duplicate architecture prose, the Linear queue or private receipts; new instructions remain subject to the existing authority boundaries. |
| Product intent and longer-term direction | [Product README](../../README.md) and linked versioned plans | The product/source owner labels intended, implemented and verified behavior separately. Current acceptance comes from the issue and its evidence, not an aspirational feature list. |
| Execution details, checkpoint and effect evidence | Private `.delivery/` records and existing Windmill/GitHub readback | The operation/integration owner retains exact identifiers, hashes and receipts. Linear gets suitable references and the accepted source revision; no raw private runtime data is copied into Git or project documents. |

Use one subject home and short complementary summaries elsewhere. Stable links
should identify the issue/document or repo path; evidence about a particular source
state also names its immutable commit. Label summaries with an as-of revision/date
and whether they are current, historical, planned, proposed or accepted. A dated
report's old pending status does not override a newer verified issue/readback.
Mutable branch links are useful navigation, not immutable acceptance evidence.

The existing [UIF Home](https://linear.app/maldous/document/uif-home-build-first-delivery-model-96eeea3357ee)
provides umbrella context with OffMenu first; a future generic template is planned,
not delivered infrastructure. The [source-ID mapping](https://linear.app/maldous/document/offmenu-backlog-reconciliation-and-source-id-mapping-29-october-2026-371f5733c73e)
preserves reconciliation coverage and unresolved provenance. These complementary
documents link to repository rules rather than copying them. Organizational
placement does not change existing task filters, credentials or operation bindings.

At each handoff, the change owner checks affected references and reports any
unresolved mismatch. A source/interface change updates its canonical guide and the
entry/index links it invalidates. A status-only change belongs in Linear and need
not create a prose commit. The Linear owner owns changes to Linear's home/docs;
the repository writer owns repo docs and AGENTS. Cross-home changes coordinate
those owners rather than letting either silently overwrite the other's records.
If one side cannot be updated, record the exact pending reference correction on
the existing issue without blocking unrelated product publication.

Legacy ledgers and recoverably archived project records remain historical
provenance, not a parallel work queue. Archive links or an explicit historical
label should replace misleading current references. This map does not authorize
archival/deletion, alter USF/CIX ownership or import their obligations into OffMenu.

## Select the smallest useful execution lane

| Work | Execution owner and route | Completion evidence |
| --- | --- | --- |
| Immediate bounded answer, communication or genuine product/access decision | Coordinating owner; inspect the relevant source/receipt directly | Answer or explicit decision, linked to an existing issue when it changes durable work |
| Separable analysis or independent review | An available reasoning worker with a finite question, read scope and immutable candidate; use the existing qualified GitHub review route where appropriate | Findings against exact source/evidence; implementing workers cannot certify their own merge |
| Repository-heavy coding, builds or focused tests | An admitted Foo/Stokowski coding session, isolated exact feature/bugfix branch, allowed paths and accepted outputs | Native attempt receipt, stopped child tree, scope check, commit and affected behavior checks |
| Long-running deterministic validation or computation | Existing Windmill MCP/API route and Foo runner, explicit resource reservation and bounded command/profile | Operation key, exact job ID, terminal backend receipt, child-tree cleanup and accepted output hashes |
| Integration | Sole authenticated integration owner through existing controller/gateway | Exact-base/head independent review, persisted intent, GitHub merge/tree/ancestry readback |

Do not delegate a trivial answer merely to fill slots. Do not start a second owner
for an issue/attempt because one channel is slow. Check provider availability,
quota, dependencies and the existing ownership receipt first. A model selection
or configured slot does not establish a usable provider session. Existing paid
session allowances and verified free routes remain subject to their actual limits;
there are no new API charges or credentials authorized by this runbook.

## Durable work and the handoff chain

Linear owns product outcomes, reproducible bugs, dependencies, acceptance criteria
and evidence references. Reuse an existing matching issue before creating one.
Create a bounded issue only when there is a distinct outcome needing durable
ownership or acceptance. An utterance, tool call, check command, retry or subprocess
is not itself an issue. An issue can own several finite attempts.

Link the existing identifiers, rather than inventing another universal run ID:

`Linear issue → admitted coding run/attempt → operation key → Windmill job → candidate commit → validation/review → integration readback → acceptance evidence`

Record the owner, source base/head, exact branch, allowed paths, accepted output
hashes, acceptance revision and resource declaration at the relevant handoff.
The operation journal binds the issue, stage, source identities, profile, policy,
runner/executor hashes and outputs. It persists submit intent and deterministic
job identity before network submission. Changing the owner does not manufacture
a new operation key. A changed semantic candidate needs a new bound attempt after
the previous effect is reconciled; it is not a retry shortcut.

Project handovers and working context should link to the active Linear issue,
current owner and latest evidence/checkpoint. Historical ledgers provide provenance;
they are not a second active queue. Keep private receipts under ignored `.delivery/`
and publish only reviewed source and suitable provenance summaries.

## Recovery at phase boundaries

The executor persists terminal receipts whether or not the coordinating owner is
watching. The admitted stage/controller consumer reads those receipts at its next
finite phase boundary. A chat status request or repeated root polling does not
establish success, release a resource reservation or authorize a retry.

1. Read the original operation/job identity and last durable intent. Inspect the
   exact existing backend job before deciding whether submission occurred.
2. For running, uncertain, timed-out or cancelled commands, establish the actual
   effect and stopped child tree before reconciliation or reservation release.
   Keep unknown effects owned; do not create a replacement ID to bypass them.
3. Resume the same immutable LangGraph task from its private SQLite checkpoint.
   The runner revalidates source, command receipts and accepted output bytes;
   completed effects are not automatically replayed.
4. For integration, persist intent before an API mutation and require canonical
   readback afterwards. Retry metadata only after a verified merge; do not re-merge
   to repair a failed Linear update. Honor refusals and required platform approval.
5. If no admitted consumer is active, record the exact paused phase, evidence and
   next permitted operation in Linear/handoff. Do not claim unattended supervision.

`python -m offmenu.delivery inspect TASK` is an observation aid: it separates
recorded acceptance from current output hashes, identifies command reconciliation
holds and reports checkpoint availability without taking ownership or replaying
commands. It does not verify full source/check evidence, read checkpoint contents,
authorize recovery or substitute for the runner/controller's acceptance checks.

## Capacity is capability, not a target

| Resource | What is established | What it does not establish |
| --- | --- | --- |
| Native reasoning collaboration | The current tool session may expose a root plus six independent slots | Availability of cloud durable tasks, provider quota, or permission to duplicate work |
| Coding sessions | Eight configured admitted coding agents in capacity-policy.json; Stokowski is the selected orchestration route | Eight currently authenticated/available provider sessions or resumed legacy workers |
| Windmill service | Sixteen configured workers, supported by retained service readback | Sixteen simultaneously useful tasks |
| Foo deterministic jobs | Thirty-two resource-admitted job slots | Admission without aggregate CPU, memory, disk, I/O and scope checks |
| Computation in one job | Sixty-four declared subprocesses plus up to eight overhead processes | Hard cgroup enforcement or permission to generate load |

Use [capacity-policy.json](../../tools/delivery/capacity-policy.json) and
[admission details](parallel-capacity.md), not a copied numeric queue. Live resource
pressure, disjoint write scope and provider limits can reduce admission. Suspended
legacy workers and the hourly automation stay suspended.

## Examples and observed adoption

- A question about current LangGraph use is a bounded source/receipt answer. It
  does not require a new issue, inference job or installed service.
- A new reproducible shopping defect belongs to the existing shopping outcome or
  a distinct bounded bug when needed. Admit one coding owner and branch; link its
  tests and correction to the same issue rather than creating an issue per check.
- A delayed independent review can use an available qualified review worker on
  the exact candidate. Its result goes back to the existing owner; it does not
  create a competing integration writer.
- A validation job with an uncertain API response keeps its original operation
  key and job ID. Read backend state and cleanup evidence before retrying anything.

One real source-delivery route is [UIF-111](https://linear.app/maldous/issue/UIF-111):
the retained native Stokowski attempt completed with no scope violations and a
stopped child tree. Its two output hashes were retained in the combined PR149
validation set, independently reviewed and integrated by the sole owner in
[PR149](https://github.com/maldous/offmenu/pull/149), merge `24215eb278c6721b6d3cb5a9a54e0c649bdd5ff5`.
The combined Windmill job succeeded; the controller's retained observation binds
the issue outputs, exact head/base and canonical merge. See the curated
[product source summary](product-delivery-20261029.json). This demonstrates source
delivery, not production-served acceptance, and does not make the older summary's
historical pending status current.

Current adoption is partial: native coding, resource-declared Windmill jobs, local
checkpointed validation and authenticated integration have real retained receipts.
Finite stage tick/recovery interfaces exist. A continuously available supervisor
with independently demonstrated callback/restart delivery across owner loss is
not established by those receipts. There is no new schedule here. LangChain Core
is a dependency; LangSmith tracing is disabled; LangServe/hosted LangGraph Platform
are not required or asserted in this route.

The [illustrative validation handoff](../../examples/validation-handoff.json)
is checked against the existing operation validator and resource limits by
`tests/delivery/test_routing_examples.py`. Its synthetic identities/hashes must
never be submitted. Real operations use admitted source and evidence bindings.
