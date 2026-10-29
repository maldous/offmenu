# OffMenu Symphony integration

OffMenu has its own on-demand Symphony launcher, workspace hooks, Linear binding
and Codex configuration. It uses the existing installed native engine and Codex
executable; it does not start, reconfigure or inherit CIX services, policies or
workflow hooks. The static template remains default-off. The launcher creates
a separately admitted finite runtime for the selected issue.

## Responsibilities and admission

Linear records work, dependencies, acceptance and the current workpad. Symphony
runs a coding session in an isolated source clone. LangGraph owns finite
workflow state/checkpoints. Windmill executes deterministic bounded commands
through the existing SSH jail. The integration writer reviews candidate changes
and verifies output/test evidence before publication. No component infers
acceptance from another component's successful API response.

Current binding: project UUID ce60c1ab-a732-4a71-8471-14c9dc393886, team UIF,
issue UIF-90. Native Symphony requires project slugId `ccd080f4f6f0`; the browser
URL uses `offmenu-ccd080f4f6f0`. The tracker preflight verifies the exact project,
team, issue, In Progress state and unique `offmenu-uif-90` label, and checks that
exactly one candidate is admitted. Source branch/head and installed engine hash
are pinned. All sessions use the same authorized feature branch name.

The launcher permits one agent and one coding turn, at most two hook admissions,
and a selected finite deadline. No permanent service/schedule is registered.
Workspace creation refuses existing content; retries preserve attempt records.
A completion marker means an attempt ended, not that its code is accepted.
Failed, unknown and deadline outcomes remain explicit. The integration writer
checks the diff and relevant tests before accepting source output.

## Existing authentication and isolated state

The existing tracker key is delivered in memory through an explicitly selected
environment or systemd LoadCredential `linear-api-key`. Its OffMenu project
access was verified by an isolated transient user process. No key is printed,
copied into source/configuration, replaced, or granted broader access. MCP
credentials are not exported. CIX's service remains unchanged.

A native no-turn preflight verified the existing ChatGPT Pro Codex route, quota
availability and available default `gpt-6.1-sol` with medium reasoning. This
selects the existing included subscription route; no API key/provider purchase
is configured. Record the actually selected/requested model and any resolution
limits rather than claiming an unset resolver model.

An exact-command A/B test reproduced initialize timeout with inherited Codex
home/configuration and initialized successfully with an isolated home. The
inherited home includes workstation MCP/plugin/hook configuration; no individual
plugin was singled out without evidence. OffMenu now creates a private temporary
Codex home referencing the existing auth path through a symlink. It never reads
or copies auth content and cleans that reference after the owned process ends.
Only OffMenu SQLite state and private runtime logs/checkpoints are retained.
This excludes unrelated workstation configuration without changing it.

## Commands

Bootstrap the project environment first, then run offline admission checks:

```sh
.venv-delivery/bin/python -m unittest discover -s tests/delivery -p test_symphony.py -v
```

```sh
python3 dev/delivery/symphony_launch.py preflight
```

```sh
python3 dev/delivery/symphony_launch.py preflight --probe
```

The last command queries initialization/account/model/quota only: no thread or
turn starts. Network access must be available for the existing account endpoints.
`prepare`/`run` refuse tracked-dirty source, wrong branch or altered engine hash.
Run only from the existing credential-injected user process, selecting a new
private runtime and reviewed task admission:

```sh
python3 dev/delivery/symphony_launch.py run --runtime /home/user/src/offmenu-data/runtime/SELECTED-OFFMENU-RUN --model gpt-6.1-sol --inference-authorized --duration-seconds 180
```

The authority flag records already established authorization; it does not grant
access. The configured task is deliberately limited to the selected OffMenu
work item and allowed paths. Extend that contract explicitly for future tasks.
No automatic push, merge, deployment, Actions, old-worker activation or external
product lookup occurs. Runtime state/receipts are private and excluded from Git.

## Verified useful work and recovery

The live coding session created eleven CLI integration tests. Independent review
and rerun passed all eleven, after which the integration writer committed them.
That session's supervisor hit its finite deadline during continuation; its
receipt correctly remained unaccepted. A subsequent one-turn session completed normally before its deadline and added five reviewed CLI regressions. Its after-run marker ended the owned polling process cleanly. One-turn configuration avoids
continuing the same coding task after its candidate is produced. Source-output
acceptance remains separate from process/session completion.

See [validation evidence](../../dev/delivery/validation.md) for exact source,
Windmill graph acceptance, checks and remaining limitations. The local engine's
`.beam` workflow/config parsers can also be invoked without starting Symphony
using `dev/delivery/symphony_validate.py` and the installed bundle selected in
the source binding. No CIX launcher or compatibility shim is called.
