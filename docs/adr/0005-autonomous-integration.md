# ADR 0005: Autonomous, evidence-bound integration

- Status: accepted direction; coding/validation adapters proven and typed dispatcher deployed; merge-controller implementation and activation pending
- Proposed standard: 2.2.0; current adopted standard remains 2.1.0
- Decision basis: the user explicitly requests autonomous, reliable integration
  without routine intervention, across the existing services, models and evidence
- Baseline: develop eca287b36b8b2027e9d32aa4899ffb204563236c

## Authority and responsibilities

Make autonomous integration into `develop` the normal successful outcome.
Do not require a human approval state for each ordinary implementation, review,
repair or merge. This decision supersedes the assumption that Stokowski's example
human gates are mandatory OffMenu workflow stages. It does not enable production
deployment or promotion to `main`, alter platform access controls or resume held
workers. The present policy still disables automatic merge until the following
integration is implemented and verified.

Use Stokowski as the sole OffMenu issue/coding orchestrator, replacing OffMenu
Symphony dispatch. Keep CIX unchanged. Stokowski owns stage transitions and
bounded rework, not the authority to certify its own source for merge. Retain
eight admitted coding agents and the existing aggregate resource reservations.

Place the merge decision in a small deterministic Windmill integration job,
using the existing Foo execution route. This is the single integration writer,
not another planning agent, scheduler or recursive manager. Serialize integrations
per repository/base branch with durable ownership. Windmill's job state is not
by itself that repository lock; use a persistent claim and reconcile any uncertain
previous operation before acquiring new ownership. A dedicated merge identity is
desirable, but existing access must be inspected first; no new grant is implied.

| Component | Authoritative responsibility |
| --- | --- |
| Repository | Versioned acceptance and integration policy, trusted validation commands, standards, ADRs and source |
| Linear | Requirements, dependencies, acceptance criteria, issue ownership, stage/outcome references |
| Stokowski | Dispatch, coding/review stages, repair routing, quota-aware task selection |
| Codex/other eligible models | Implementation and independent semantic review within the authorized provider routes |
| Windmill/Foo | Bounded execution, independent validation, serialized integration and operational receipts |
| LangGraph | Finite decision/checkpoint state, retry budget and recovery around each integration transaction |
| GitHub | Canonical refs, PR/review metadata, branch protection and final compare-and-merge outcome |

LangChain integrations may supply typed adapters where useful; they do not become
an extra manager. LangSmith remains optional and private telemetry stays disabled.
MCP access in a cloud task is not local credential availability. Local autonomous
operation needs an inspected, authorized API route independent of an interactive
chat; a temporary cloud connector response is not a production credential plan.

## Existing Codex integrations and utilization

GitHub's existing Codex review is the preferred independent PR review route,
rather than launching an additional equivalent review session by default.
The PR 144 receipt from `chatgpt-codex-connector` explicitly records reviewed
commit `fa8db46274`; the final PR head was `e96d8d055171c6f23ce5da3b1ae80c8f87e54df4`.
This demonstrates the integration exists, and also why resolving findings alone
cannot establish a fresh review of a repaired head. Request/reconcile review of
the exact current head, verify reviewer identity and completion, consume all
findings, and deduplicate requests by repository/PR/head/reviewer. A timeout or
absence of comments is not a clean review. Do not count the same review again
as a separate local independent review. Existing historical merges are not
retroactively certified under the proposed autonomous policy.

Linear project P-UIF-14 remains the OffMenu record authority. Readback confirms
access to project UUID ce60c1ab-a732-4a71-8471-14c9dc393886. Native Linear Codex
delegation is not yet verified: the advertised MCP `get_agent_context` operation
returned `Tool get_agent_context not found` during inspection. That does not prove
the Linear Codex application is absent; MCP connectivity, shared notes and native
agent delegation are distinct capabilities. Use the working Linear API path for
Stokowski and durable issue records. Do not make the unavailable notes operation
a dependency of delivery, or silently replace repository decisions with it.

If native Linear Codex delegation is available, admit it through the same ownership
and capacity policy as Stokowski sessions. Select exactly one execution owner per
issue/attempt. Prefer it for useful discovery or triage only when it can return
bound evidence and its quota/cost/credentials are understood; do not simultaneously
assign the same coding task through both services. GitHub Codex review, local
coding, cloud delegation and deterministic computation have distinct capacity
budgets. Record actual usage/latency and accepted outcomes, not utilization alone.
Use model selection and eligible fallback to improve completed work; never launch
duplicate work merely to keep subscriptions busy. Configuration authorization
does not imply unlimited provider capacity or permission to buy more.

## Evidence required for each candidate

Bind a candidate to repository, issue, requirement/acceptance revision, base SHA,
head SHA, source tree, exact changed paths, policy version/hash, environment and
dependency identity. Record deterministic check commands, actual exit/results,
accepted output hashes, provenance, known limitations and independent review
findings/disposition. An exit-zero job, model confidence, Linear Done state,
tracking comment or pushed branch alone cannot authorize a merge.

The implementing agent cannot edit its own trusted acceptance baseline, policy,
review outcome or integration credentials to manufacture eligibility. Treat
candidate code and generated reports as untrusted inputs. Run trusted validators
from the accepted base/control revision against the selected candidate; bind
results to both revisions. Changes to validators/policy require independent
review and verification under the previous policy before they take effect for
subsequent work. Never execute a candidate-provided merge command or deserialize
an unrestricted command from a report. Check altered Actions/deploy triggers
before publication; the existing no-Actions/no-production-deploy boundary remains.

Run a fresh review session separate from the implementation session, with a
recorded reviewer/provider/model identity and evidence references. Review the
actual immutable diff and acceptance results. A second model can be selected
when eligible and useful; model diversity alone is not independent evidence.
Use existing authorized Codex/Antigravity allowances or verified OpenRouter free
models only; do not assume a subscription grants paid API access. Capacity,
remaining quota and provider availability constrain admission. Do not install
Claude or silently buy capacity to avoid a blocked task.

## Finite integration transaction

1. Reconcile previous claims/effects. Admit the exact candidate with one writer.
2. Check project, dependencies, branch, scope, cancellation and immutable identity.
3. Execute affected behavior checks through the resource-declared Windmill route.
4. Independently review; route actionable findings automatically back to repair.
5. Refresh GitHub base/head, review/protection state and unresolved findings.
6. If the base changed, create a new candidate identity, integrate current base
   without force, and rerun affected checks/review. Never reuse old acceptance.
7. Persist merge intent, including exact expected head/base and policy/evidence
   references. Invoke GitHub's normal merge API with expected head. Recheck base
   as close as possible; where branch protection cannot enforce an up-to-date
   base, validate the resulting integration tree as well. Do not bypass protection.
8. Read back the PR, merge commit, parent relationships, remote `develop` and
   resulting tree. Observe deployment/Actions effects without triggering them.
9. Store accepted integration receipt, then update Linear with evidence. If that
   metadata write fails, retry/reconcile the metadata only; never re-merge.

On an API timeout, query the PR and exact commit/ref outcome before retrying.
Do not treat absence of a local receipt as proof that no merge occurred. If the
head moved, bind a fresh candidate. If another accepted PR advanced `develop`,
verify this merge is an ancestor rather than insisting the current tip equal it.
Post-merge regression creates a prioritized bounded repair/revert candidate;
do not rewrite history or claim acceptance while the resulting state is unknown.

## Recovery without routine user intervention

Bound retries and rework by explicit task budgets and meaningful new evidence.
Transient service failures use backoff and outcome reconciliation. Provider quota
shortage defers work or selects an already authorized compatible route. Semantic
failures return to implementation with the failed evidence and a fresh attempt
identity. Contradictory requirements trigger a discovery/review stage using the
repository decisions, source contracts and recorded user intent; record assumptions.
Preserve completed obligations rather than regenerating them after session loss.

When a task exhausts its budget, lacks authority, or has uncertain external effects,
quarantine that task with a durable reason and recovery action. Continue unrelated
admitted work. Do not repeatedly ask the user to arbitrate ordinary technical
choices. A genuine access/spending/product-policy decision outside existing
authority remains an exception; no reliable design can promise to bypass it.
Expose concise exception/progress reporting without turning every gate into a
human approval request. Neither the implementing agent nor a different model may
override a denied operation by switching tools or credentials.

## Required implementation proof before activation

The pinned Stokowski source at 339cbf4f3f6d9acdf808f9ba4c639d029cdd8e16
supports Linear polling, configurable stages/gates and tracking recovery, but its
Codex runner invokes `codex --quiet --prompt`. The installed CLI uses `codex exec`
and JSONL events. Adapt and test that route, guarantee descendant cleanup, filter
child environment credentials, preserve durable claims and replace example
main/rebase/human-gate hooks with the OffMenu policy. Do not run two orchestrators.

Before enabling autonomous merges, prove: successful useful work through actual
Codex and Windmill; automatic review/rework; stale base/head rejection; forged or
stale evidence rejection; duplicate/crashed ownership recovery; uncertain merge
reconciliation; cancellation; quota deferral; failed Linear update after successful
merge; and a normal GitHub merge/readback without human intervention. Use focused
fault injection rather than synthetic saturation or broad unrelated release gates.
Inspect actual GitHub protections and available authenticated local API routes;
neither is asserted to be configured by this ADR. Installation/execution of the
new third-party package and credential provisioning retain their required
action-time confirmation. Historical Symphony evidence remains historical.

Activation must update the adopted standard/version, operational configuration,
AGENTS.md and handover together. Until then, this ADR records the authorized
end state, not a claim that autonomous integration is running.
