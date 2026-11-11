## Fixed operating role

This repository belongs to the OffMenu dedicated project role. Read the fixed project agents and general Cloud role
section in the local shared worker policy at startup and pass its version/hash to
children. Project cloud Git, CPU and storage are independent of Foo; optional MCP
execution must bind the correct host, project, worktree and branch. The general
Cloud role has no Git configuration or repository binding. Additional Foo Codex sessions require
restored allowance and current ownership checks. These are operating requirements,
not proof of provisioning, availability or universal adoption.

# Shared UIF worker directions

At every startup, including independent Foo work, read
[the shared worker policy](docs/agents/uif-worker-policy.md) and
[its local version manifest](docs/agents/uif-worker-policy.json).
Apply them with this repository's project-specific instructions, not instead of them.

Read the existing delivery contract below. ADR 0010 records this additive instruction-distribution change. Existing suspended workers, typed admission, resource controls and integration ownership remain unchanged.

# OffMenu developer and agent entrypoint

Read `docs/standards/repository.md`, `repository-standard.json` and the relevant
ADR before changing structure. Read `tools/delivery/README.md` for the repeatable
workflow. Discover the actual source/manifests before proposing new rules.

Use `develop` for integration, `main` for reviewed releases, and a reviewed
`feature/` or `bugfix/` branch for changes. The standardization workstream uses
`feature/langgraph-delivery-standardization`. New qualified product/backlog work
uses its own exact bound feature/bugfix branch. There is one Git integration writer.
Existing historical workers and the hourly automation remain suspended. Do not infer that
a Linear assignment or a prepared Symphony workflow permits their resumption.
Newly and specifically authorized, manifest-bound work may obtain fresh normal
provider, resource and ownership admission. This does not resume historical
workers, enable `automatic_start` or change `legacy_workers_resume`; all mandatory
platform confirmations and access/security limits still apply.

For releases, follow ADR 0009 and `config/delivery-release-policy.json`. Freeze
an exact candidate from accepted `develop`; exhaustive qualification stays bound
to its source, tree and artifacts while `develop` advances. Publish the frozen
candidate through `release/candidate-<candidate fingerprint>` into `main` only
after separate release review. Verify the resulting tree and immutable tag;
keep `main` static between approved releases. Source acceptance, installed
delivery BAU, application deployment and product acceptance are separate facts.

Select work using [task routing and tracking](docs/development/task-routing.md).
Keep immediate bounded answers and genuine decisions with the coordinating owner;
use available independent reasoning for separable analysis and the dedicated
project agent's isolated cloud Git checkout for independent repository work.
Owned Foo/Stokowski branches are the optional Foo execution lane when that task
requires it; resource-admitted Windmill jobs handle long-running deterministic
work. All lanes retain existing typed admission, bound review and sole integration
writer controls. Link runs and evidence to the existing Linear outcome rather
than creating issues for messages or subprocesses. Recover from durable receipts;
chat polling is not an execution or recovery mechanism. Capacity ceilings describe
available capabilities, not utilization targets or permission to resume workers.

For new origin-specific validation, retain exact source/review/workspace/output
bindings; source-only extraction is not a coding attempt. Record requested model,
effort and provider separately from observed or unknown resolution and resources.
Treat a ready-refill observation as provisional; use normal admission before work.
The proposed extension is scoped in ADR 0006 and does not relax existing gates.
For completed validation and standalone unit review, follow the [canonical runbook](tools/delivery/README.md#completed-validation-and-standalone-unit-review).

Classify source, generated files, historical evidence and private runtime data
before moving anything. Preserve data/configuration holds in the reconciliation
handoff. Keep checkpoints/logs private under ignored `.delivery/`; never add raw
datasets, credentials, screenshots or runtime receipts to Git.

Discover -> propose/record standards -> apply bounded changes -> check behavior
and accepted output hashes -> publish reviewed source -> verify remote content.
Record base/head, exact paths, checks, remaining failures and next step. A push
is not application acceptance. Changes to standards require version and ADR.

Bootstrap first; run `.venv-delivery/bin/python -m offmenu.delivery discover`,
`.venv-delivery/bin/python -m offmenu.delivery check` and
`.venv-delivery/bin/python scripts/check_final_layout.py`.
Use the pinned delivery environment for the graph and its tests. Runtime test
locations are `tests/web`, `tests/edge`, `tests/compat`; Python suites stay under
`tests/`. Historical pinned snapshot paths remain historical.

Linear records work/dependencies/acceptance; Stokowski provides admitted coding
sessions; Windmill executes bounded deterministic jobs; LangGraph tracks finite
workflow decisions/checkpoints. Review task command arrays as executable code.
Reconcile uncertain effects before retrying the same immutable task ID. No
recursive managers, automatic push/deploy, new schedules, new paid API charges or private telemetry are enabled by this workflow. Evidence-bound automatic integration into develop is enabled under ADR 0005 and tools/delivery/integration-policy.json; only the authenticated integration owner may consume its typed actions. Coding children cannot authorize their own merge.

No Actions execution/dispatch/retry, production deployment, live food/barcode
lookups, local model installation, force push/reset/clean or permanent data
removal is authorized. Inspect workflow triggers before publishing. Only push
this authorized feature branch; do not push the runner control branch.
