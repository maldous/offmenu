# Native source outcomes

This opt-in tail runs under the existing CurrentWork owner lock after a verified
normal integration effect. It does not dispatch, compute, merge, or replace the
original native receipt, validation Journal, independent review or protected
publisher. Missing owner policy leaves the legacy route unchanged.

`native_harness_linear.finalize_source_outcome` consumes the sealed policy, exact
selected owner binding, original native unit and request, successful Journal,
independent exact-source review, and correlated canonical publisher facts. It
requires fresh issue/project/team/assignee/delegate, unchanged description,
completed dependencies and an uncancelled workflow state. An explicitly issued
full source-only contract must equal the original manifest's acceptance clauses
and allowed paths. Only that bounded class can select the granted completed
state. Broad parent outcomes remain open; source acceptance does not assert
product, runtime, deployment, release or global delivery acceptance.

Each outcome has deterministic evidence content and separate durable intents for
its evidence comment and optional bounded-source completion. Existing metadata
intent means readback only. A lost reply can be reconciled from exact native
content; absence after an uncertain write never authorizes another mutation.
The tail has no computation or merge callable, and uncertain metadata withholds
refill. No raw logs, secrets or private corpus bodies enter its evidence comment.

`accepted_project_source(current, project_id)` returns exactly
`{repository, branch, head, tree, evidence:{path,sha256}}`. The source is application
`develop`, independent of the installed control revision. A sealed policy seed
is used only before the first authenticated canonical merge. The existing
publisher writes immutable `by-commit/<head>.json` or `by-operation/<operation_id>.json` facts and the exact `{schema:'offmenu-accepted-project-source-pointer/1',latest:{path,sha256}}`
`latest.json` pointer under `/var/lib/offmenu-publisher/accepted-sources`.
The reader requires the fixed directory's UID 984/mode 0755 and no-follow,
single-link regular UID 984/mode 0444 files. Neither worker-authored Boolean
receipts nor CurrentWork state can certify accepted source.

The immutable fact schema is `{schema:'offmenu-accepted-project-source/1',
repository,branch,head,tree,parents,base,candidate_head,operation_id,unit_sha256,
packet_sha256,policy_sha256,pr_url,helper_receipt:{path,sha256},previous,observed_at}`.
The first `previous` is exactly `{schema:'offmenu-accepted-project-source-seed/1',
head,tree,policy_sha256:fingerprint(project_source)}` matching the sealed seed;
later facts pin the previous immutable `{path,sha256}`, whose head must equal the
actual pre-merge base. `observed_at` is an integer UTC epoch timestamp. The base
is the actual canonical pre-merge base, not a relabelling of original execution.
The exact candidate, operation, unit and packet bind the original proof.

The publisher alone emits facts after its real normal Controller merge/readback.
The reader follows immutable references to the sealed seed (or corroborating
local Git ancestry), verifying local tree/parents when the object is present.
If absent, acquisition may fetch only that authenticated SHA; remote-tip movement
is never acceptance. Each task retains an immutable fact reference. Missing,
changed or untrusted facts hold instead of falling back to a seed. CurrentWork
stores a projection only and cannot roll accepted source backwards.

The callback input `outcome` contains `effect`, `handoff`, an original `review`
reference, and `canonical` as the protected immutable fact reference. It invokes
the fixed installed `native_harness_runtime.verified_canonical_source(current,
issue,binding)`, whose result is exactly `{fact,evidence:{path,sha256}}`. This
publisher-owned reader re-correlates authenticated canonical facts; a cached JSON
body or a worker-written verified flag never substitutes for it. The callback
independently reads the referenced UID 984 fact and requires exact equality.

The existing `stokowski_prepare.owner_intake_policy` and `owner_policy_contract`
readers own sealed policy/qualification. A contract may carry
`source_outcome:{full_issue_contract,team_id,description_sha256,done_state_id}`;
acceptance, scope, assignee and dependencies come from that same issued contract.
Without explicit authority the tail holds. The compiler/qualifier must not set
`full_issue_contract` merely because a coding task finished. The project source
descriptor uses `source_repository` and `accepted_facts_path` for its fixed local
Git repository and protected latest-pointer path.

The coding compiler and source acquisition use the accessor before preparing
each new task. Installing a new control package per application task is not
required. Root owns the sealed policy and final callback installation. The
publisher owns protected facts; this module never writes its store. Preparation
or a passing fixture is not proof of live adoption.
