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
