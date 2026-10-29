# OffMenu Stokowski integration

Stokowski replaces OffMenu's native Symphony coding orchestration. CIX's Symphony
installation is unchanged. The approved upstream pin is version 1.1.0, commit
`339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16`, Apache-2.0. Its source file hashes
are retained in `tools/delivery/stokowski-source.json`. It is installed under
ignored `.delivery/stokowski/`; no third-party source or credentials are vendored.

## Bootstrap and boundaries

```sh
python3.12 scripts/bootstrap_stokowski.py
python3.12 scripts/bootstrap_stokowski.py --check
.delivery/stokowski/venv/bin/python -m pytest .delivery/stokowski/source/tests -q
.venv-delivery/bin/python -m unittest discover -s tests/delivery -q
```

The lock pins 31 installed packages including Stokowski. The bootstrap verifies
the exact upstream source before installation. It does not configure credentials,
start a dashboard, call models or install globally. Installation/build execution
requires the already-granted pinned-package authority; it is not permission for
future arbitrary upgrades. Do not invoke the unadapted upstream CLI for OffMenu.

`tools/delivery/stokowski_adapter.py` applies process-local adaptations to the
pinned package. `stokowski_worker.py` is a separate finite supervisor for each
coding attempt, so descendant cleanup cannot select sibling sessions. Existing
durable admission and exact runtime/manifest lease identities are reused from the
capacity modules; their compatibility names do not start a Symphony service.
The shared policy retains eight coding agents, sixteen Windmill service workers,
thirty-two declared jobs and sixty-four computation subprocesses per job.

The coordinator receives the existing approved Linear credential in memory using
the established transient service-manager injection route. Its local API client
polls Linear GraphQL for project `ccd080f4f6f0`, then intersects candidates with
the immutable admitted issue UUIDs. Candidate filtering does not narrow the key's
underlying privileges; no new key or grant is created. Codex and subprocess hooks
do not receive the key, its injected directory or unrelated provider/telemetry
variables. This is credential environment isolation, not a claim that coding
processes have a complete security sandbox or cannot read user-readable files.

Coding uses the existing ChatGPT login via an isolated temporary Codex home
referencing existing authentication, `codex exec --json`, `gpt-6.1-sol`, medium
reasoning and the workspace-write sandbox. No API key or paid API route is
selected. The exact native session ID and reported token usage are retained.
Upstream's legacy `codex --quiet --prompt` invocation is not used. Native Codex
session resumption is not implemented by this adapter; recovery uses immutable
source, receipts, leases and a newly admitted attempt after reconciliation.

## Actual interfaces and synchronization

| Edge | Interface and authority |
| --- | --- |
| Stokowski coordinator → Linear | Local Python/httpx HTTPS GraphQL; existing coordinator-only credential; exact project/issue selection |
| Stokowski → coding supervisor | Local Python subprocess and private request/receipt files; one supervisor per issue attempt |
| Supervisor → Codex | Native CLI exec; JSONL events, stdin prompt, bounded private files |
| Codex → model provider | Existing ChatGPT session; availability/quota remain provider-controlled |
| Windmill → Foo computation | Existing deployed API/SDK entrypoint and pinned SSH bridge; resource-declared deterministic jobs |
| Integration workflow → LangGraph | Existing Python SDK/SQLite checkpoint interface; immutable evidence and finite decisions |
| Integration writer → GitHub | Git source publication and separate PR/review/merge API operations |

Stokowski does not become an MCP server because workers can use MCP. The initial
isolated Codex configuration does not inherit workstation MCP servers or their
credentials. Configure selected worker tools explicitly only when useful and
authorized. Do not copy broad workstation configuration into every coding child.
The journal and validation continuation now submit Windmill jobs through native
MCP and a typed Windmill-side SDK dispatcher. This path is proven in explicit
draft-test mode, including terminal restart and backend cancellation, at source
`8815c61bca80cf6546919ac9394cfdf7b8e9d252`. Automatic approval review initially
rejected deployment of the new workspace item. After the user explicitly approved
the exact source, one normal retry deployed `u/admin/offmenu_delivery_dispatch`.
Deployed SHA-256 `4908969d73c2b2b0464771f543d35657da880c39c3b0162731d548aad2bb66b7`
matches reviewed source; extra permissions remain empty. Native MCP inspection of
the completed validation through the deployed route confirms success and cleanup.
No alternate deployment route was attempted. Full stage-to-job-to-merge
synchronization remains the pending ADR 0005 implementation.

The native MCP client reuses the existing configured Windmill OAuth session in
coordinator memory; no token/grant is created or copied into worker processes.
It calls only the typed dispatcher. That script uses Windmill's job-scoped SDK
authentication to address the fixed existing bridge and exact server job UUID.
The adapter reads the current Codex-owned OAuth cache and does not overwrite or
renew it. Refused/expired authentication defers work; unattended renewal still
belongs to the existing credential manager's lifecycle, not an invented grant.

Correlate issue UUID, immutable manifest, runtime path, source SHA, exact lease,
native session and Windmill job ID. One component owns each state transition.
Do not turn every service into a dispatcher or blindly retry ambiguous effects.
GitHub Codex review should replace equivalent duplicate review sessions when it
provides fresh evidence for the current head. Linear-native Codex delegation is
optional and unverified; ordinary Linear API access already works.

## Feature disposition

| Upstream feature | OffMenu disposition |
| --- | --- |
| Linear polling and workflow stages | Used with exact project/manifest filtering; preserve historical completed issues |
| Stage/gate tracking comments | Used for durable coordination; a coding-success comment is not acceptance |
| Native Codex execution | Adapted to installed CLI, explicit existing session route and recorded native session ID |
| Shared/per-state concurrency | Eight-agent ceiling plus persistent host/resource/ownership admission |
| Workspace creation and cleanup | Private clones on the selected branch/head; retain outputs and uncertain work instead of upstream deletion |
| Retry/backoff and restart recovery | Retain upstream coordination; immutable request/lease/receipt prevents blind coding replay; finite coordinator deadline |
| Stall/timeout/cancellation | Finite supervisor, resource sampling, TERM handling and unconditional owned-descendant cleanup |
| Shell hooks | Rejected in this adapter; upstream ignores some hook failures and does not reliably clean timed-out hook children |
| Reports, artifacts and run ledger | Safe structured attempt metadata and local ledger; raw worker reports/screenshots are not uploaded |
| Web dashboard/studio | Dependencies installed; no listener or public dashboard enabled; later local authenticated operation only if useful |
| Routing/multiple workflows | Upstream capability retained; first bounded execution selects one immutable task/pipeline |
| Multiple projects/Claude runners | Excluded from OffMenu/Codex scope; CIX is not enrolled |
| Human gates and merge stage | Example stages are not the end state; ADR 0005 specifies autonomous evidence-bound integration |
| MCP, Windmill, LangChain/LangGraph | Explicit adapters with separate credentials and state ownership; no automatic credential sharing or competing manager |

## First bounded task and remaining activation work

UIF-92 adds real restart/ownership regressions to the reviewed adapter. The initial
workflow ends at evidence-pending/In Review until independent checks and source
acceptance are recorded. This is a bounded installation/use demonstration, not
the final autonomous merge controller or a permanent requirement for human gates.
Do not mark the issue Done merely because a model exits successfully.

Runtime manifests, requests, provider readiness, intents, logs, leases and receipts
remain private. Existing intent, completed receipt, source drift or uncertain
process state blocks replay. A coordinator restart must reconcile those records;
it must not delete them or relabel a task to rerun it. Exhausted work is isolated
while unrelated work may proceed within admission. Observe child-tree termination
before releasing capacity. CPU affinity and sampled RAM/process limits are not
hard RAM/device-I/O cgroups.

The versioned integration policy now enables qualified develop integration through
`offmenu.delivery.integration` and `integration-gateway.mjs`, as specified in
[ADR 0005](../adr/0005-autonomous-integration.md). Trusted validators are loaded
from the accepted base before the candidate suite runs. Mutation state survives
stale/missing observations independently of display status, preventing retries
from erasing unknown effects or refused/exhausted metadata state. Cancellation
blocks new mutations while allowing read-only reconciliation of an issued merge.
Fresh independent review and canonical integration acceptance remain actual
runtime requirements, never inferred from the enabled policy. The current
publisher is the authenticated cloud connector owner; a permanent native GitHub
publisher grant/launcher has not been configured. Context loss therefore defers
publication with durable intent intact, rather than claiming uninterrupted
unattended operation. No credential is transferred to coding children.

## Verified validation continuation

`stokowski_stage.py bind` verifies the selected task, native output receipt,
unchanged native clone identity, candidate head, output hashes and the accepted
base's exact untracked holds. It preserves an explicit derivation record when
the integration writer adapts native output. It does not publish source or merge.
The Stokowski launcher can resume that bound stage with `--validation-stage`;
`--preview-dispatch` is an explicit test option, never an automatic fallback
after a deployment or permission refusal. Default mode selects the deployed item.

Each operation records issue/stage/base/head/acceptance/policy/executor identity,
one owner, deterministic Windmill UUID and Foo logical job ID. Requests are fsynced
to the journal before submission. A lost acknowledgement is inspected by the
same UUID; absence after an uncertain submission does not authorize blind replay.
Backend status observations use separate durable identities. An API wrapper's
failure or cancellation is not subprocess termination evidence. Cancellation
targets the Foo backend and waits for its reconciled receipt. Source/branch,
untracked maintained files and output hashes are checked before and after tests.

The real preview-mode validation passed 143 delivery tests (four optional native
checks skipped there; all 48 Stokowski tests pass in its environment). Seven output
hashes were verified. Reopening the completed stage produced no second submission.
A separate bounded validation operation reconciled to backend `cancelled` with
no remaining child tree. Neither result constitutes application or merge acceptance.
See [verification](stokowski-verification.json) for exact job IDs and hashes.
