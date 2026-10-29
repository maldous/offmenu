# OffMenu developer and agent entrypoint

Read `docs/standards/repository.md`, `repository-standard.json` and the relevant
ADR before changing structure. Read `tools/delivery/README.md` for the repeatable
workflow. Discover the actual source/manifests before proposing new rules.

Use `develop` for integration, `main` for reviewed releases, and a reviewed
`feature/` or `bugfix/` branch for changes. The standardization workstream uses
`feature/langgraph-delivery-standardization`. New qualified product/backlog work
uses its own exact bound feature/bugfix branch. There is one Git integration writer.
Existing workers and the hourly automation remain suspended. Do not infer that
a Linear assignment or a prepared Symphony workflow permits their resumption.

Select work using [task routing and tracking](docs/development/task-routing.md).
Keep immediate bounded answers and genuine decisions with the coordinating owner;
use available independent reasoning for separable analysis, owned Foo/Stokowski
branches for repository work, and resource-admitted Windmill jobs for long-running
deterministic work. Link runs and evidence to the existing Linear outcome rather
than creating issues for messages or subprocesses. Recover from durable receipts;
chat polling is not an execution or recovery mechanism. Capacity ceilings describe
available capabilities, not utilization targets or permission to resume workers.

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
