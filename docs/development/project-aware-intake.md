# Project-aware current intake

The existing protected owner can admit the two already supported exact project
pairs in one current coordinator. Stokowski 1.1.0 supplies native
`ServiceConfig.projects`, per-project polling and one shared concurrency pool.
`CurrentWork`, its owner, catalog history, coordinator root lock, resource pool
and global eight-agent ceiling remain shared. This is source capability; only
the integration owner may seal configuration and activate it.

The optional root-sealed `current.json.project_routes` is a list of one or two
objects with exactly these fields:

```json
[
  {
    "project_id": "ce60c1ab-a732-4a71-8471-14c9dc393886",
    "project_slug": "ccd080f4f6f0",
    "normal_intake": {"path": "/absolute/private/stokowski/offmenu-intake.json", "sha256": "<exact file digest>"}
  },
  {
    "project_id": "ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0",
    "project_slug": "21558318e036",
    "normal_intake": null
  }
]
```

These are OffMenu and UIF respectively. No other pair, duplicate route or extra
field is admitted. The existing `project_route` (default OffMenu) remains the
primary route and must be present. With `project_routes`, a top-level
`normal_intake` is refused to avoid ambiguous authority. Each route has its own
private byte-pinned intake policy, or `null` to disable uncatalogued intake for
that project. The policy must bind the same owner, current source head and exact
route. Its authority references retain exact issue UUID, project, accepted
scope, acceptance and completed dependencies. An issue body can reference an
owner-approved authority; it cannot add routes or supply authority itself.
Without `project_routes`, the existing single-route configuration is unchanged.

The sealed workflow uses the native `projects` list with exactly one uniquely
named block per admitted slug. Move each project's `tracker`, `workspace`,
`hooks`, `prompts` and `states` into that block as required by Stokowski. Keep the
existing coordinator workspace root, Codex agent state, evidence gate and disabled
hooks. The adapter checks every project's runner and hooks, and the single global
agent ceiling and disabled server. It passes each native fetch's route explicitly
through candidate and intake checks; no mutable ambient polling project exists.
Admission ticks serialize within this coordinator so shared validation and native
continuation permits cannot overlap between project loops. Native coding children
still share the existing concurrency pool.

Catalog and replacement history stays append-only under existing exact snapshot
grants. A replacement must retain its refusal witness's original project, issue,
owner and prior receipt; route admission never relabels old entries. Native
harness selections must name an admitted project, and consumption checks that
project against the original pinned manifest and native unit binding. A successor
may target either explicitly admitted route while preserving the original
trigger's operation, review, custody and immediate continuation gates. Existing
per-unit native review policy selection remains available; a project-specific
static review template does not authorize another project's review.

For local verification, use the pinned delivery interpreter with
`PYTHONPATH=src:tools/delivery:tests/delivery` and run
`python -m unittest test_stokowski_project_routing`. The tests use real native
fetch/parsing and pool construction with synthetic API and OS-custody boundaries.
No live tracker writes, service changes or publication are performed. Root sealing,
new catalog versions, Linear admission and activation remain distinct owner actions.

## Bounded owner-policy compilation

The optional root-sealed `current.json.owner_intake_policy` is an exact
`{path,sha256}` reference. The referenced file and every ancestor must pass the
existing root-owned, non-writable protected-input reader. It can contain explicit
approved contracts and the bounded delegated source-only code-fix `workclass`.
Root seals this policy once. The existing native poll and native completion
boundary then qualify and compile eligible instances without new per-item Root
files or configuration. Issue prose and a bare proposal never extend authority.

Policy `schema` is `offmenu-owner-policy-intake/1`. Its exact fields are:

- `owner`, `source_head`, `source_branch`, `coordinator_runtime`: the existing
  guarded coordinator identity and accepted source, not a future candidate.
- `expires_at`: a finite epoch deadline for new preparation/publication.
  Expiry does not remove previously admitted catalog history.
- `resource_ceiling`: the four existing integer resource fields. Normal Pool
  admission and native concurrency limits still apply.
- `provider_requirements`: the existing publication requirement shape
  (`requested_model`, `requested_effort`, `route`, `session_ceiling`,
  `max_age_seconds`, `checked_at_max_future_skew_seconds`). This grants no probe,
  spend, credential or new model route. Publication calls the existing
  source-pinned `symphony_launch.provider_proof` through the producer's trusted
  callback. No manually refreshed proof file or per-item Root stamp is needed.
- `installation`: the exact original `{path,sha256}` installation reference.
- `contracts`: at most 32 records keyed by exact issue identifier. Each has
  `issue_id`, `project_id`, `assignee_id` (UUID or explicit null), `purpose`,
  `scope`, `input_paths`, `acceptance`, `prompt`, `timeout_seconds`, `resources`
  and `dependencies` (exact UUID list). Paths, immutable accepted text, resources
  and dependency identities are owner-approved typed data, never issue prose.
- Optional `workclass`: `assignee_id` (Matthew's exact UUID), `project_ids`
  (subsets of the two existing routes), `allowed_files`, `max_files:4`, the four
  resource fields in `resources`, `timeout_seconds` (at most 600), fixed
  `acceptance` and `selection_label` (the exact sealed `offmenu-source-bau` label).
  Allowed files are exactly `OWNER_CODE_FILES` in `stokowski_prepare.py`: its own
  source, the adapter, the current-dispatch/first-dispatch/owner-policy test files,
  and this guide. Acceptance must equal `OWNER_CODE_ACCEPTANCE`, not an agent's
  replacement conditions. CPU/memory/IO/output ceilings are 1000 millicores,
  1.5 GiB, one slot and 512 MiB. Requested model/effort are fixed to the existing
  `gpt-6.1-sol`/`medium` route. No other workclass is introduced.

`CurrentWork.candidates` calls `stokowski_prepare.owner_policy_candidate` only
for an uncatalogued issue. It checks the guarded source and fresh native Linear
identity, admitted project, assignee, Todo/In Progress state and exact completed
dependency set. A known native dependency additionally needs the original
`_reconciled_unit` boundary. It derives manifest/request/claim/config/handoff
bytes under deterministic private paths and invokes the existing
`prepare_publication` producer through an internal current-owner capability.
The local owner observation represents that guarded protected coordinator; it
does not claim a fresh GitHub login or authentication by a JSON boolean.

Without an explicit contract, the workclass requires the exact Matthew assignee,
no delegate, selected label, admitted project and completed dependencies. The
existing read-only `_qualification_boundary`/`qualification_child` creates one
source-pinned request through the same provider/Pool path. It uses 129's shared
`clone_current_workspace(source,path,head,branch)` helper, never a second clone
implementation. The proposal string encodes a strict typed plan: matching issue
UUID/head, `rights:source-only-synthetic`, at most four allowed files, only allowed
source inputs, bounded requested behavior and one affected unittest method.
Missing inputs or nonconforming plans stay held.

Promotion independently rechecks the original request/spec, output digest,
stopped successful result and exact Pool lease binding with finished/succeeded
status. Only then may the trusted owner compile it under the sealed delegation.
A bare output, label, issue body, saved diagnostic or agent-declared right cannot
replace those checks. Original intent, lease, result and input history remain;
no retained qualification is launched again.

When native harness boundaries exist, compilation requires their actual fresh
verified permit. The latest native candidate observation is consumed by one
callback inside `continue_native_harness`, before `_successor_boundary` and
before its `finally` clears the permit. Every candidate is freshly rechecked
against the tracker. Ordinary polling outside that window holds preparation;
no permit is persisted, copied, synthesized or weakened. Stokowski still owns
polling, ordering and final coding admission; this is no new queue or controller.

Existing files are immutable: conflicting or partial preparation is held for
reconciliation, never replaced with a new attempt identity. The existing producer
owns publication locking, journal, fsync, runtime materialization and catalog
write. No coding child, lease, service, external job or merge is started by this
compiler. The next native candidate pass adopts the entry and all existing
workspace/provider/resource/ownership gates remain in force.

After the existing root seed/static catalog grants, a dynamic append is accepted
only if the same sealed contract and actual immutable inputs derive its exact
manifest/request/admission entry. Prefix bytes/entries remain append-only;
repeated identities, arbitrary appends and altered admission pins refuse. This
does not grant replacements: use the existing explicit replacement protocol.
Source adoption needs a newly qualified policy at the new accepted source and
preservation of existing seed/history, never relabeling old execution receipts.

The focused fixture is
`python -m unittest test_stokowski_owner_policy_intake.OwnerPolicyIntakeTests.test_two_contracts_native_boundary_and_refusals`
with the existing pinned interpreter and `PYTHONPATH=src:tools/delivery:tests/delivery`.
It runs the real producer, catalog/admission and native candidate paths for two
synthetic units, including a delegated future UUID without a sealed per-item
contract. It exercises the actual verified native consumer/callback and checks
the permit disappears outside it. Root filesystem custody, provider metadata and
model completion are explicit fixture boundaries; original Pool request/result
verification, producer and catalog operations remain real. It performs no actual provider,
coding, service, tracker or production operation.
