# Symphony integration boundary

OffMenu's [Symphony workflow template](../../dev/delivery/symphony-workflow.md)
and [source binding](../../dev/delivery/symphony-linear-binding.json) are disabled
configuration artifacts. They do not start a service, poll Linear, resume a
worker or establish model eligibility.

## Local discovery

On 2026-10-29 this host had Symphony escript/OTP bundles under
`~/.local/share/cix/symphony/` and conventional `WORKFLOW.md` source examples under
CIX workspace snapshots. No `symphony` command was found on PATH. Inspection was
limited to non-secret workflow/schema source and an executable wrapper; initial discovery started no service or coding session. The isolated
native parser verification below subsequently loaded bundle modules without
starting the Symphony application. These are CIX-owned installations, not an
OffMenu installation acceptance receipt. Their project bindings, credentials,
operational paths and model command must not be copied or repurposed.

The inspected local implementation accepts YAML front matter and a templated
Markdown body. It uses `tracker.kind: linear`,
`tracker.provider.project_slug`, `tracker.required_labels`, named active/terminal
states, a workspace root, lifecycle hooks and Codex app-server configuration.
The OffMenu template follows that observed structure. Compatibility with a
future selected Symphony binary still requires a parse/configuration check;
this discovery does not assert any bundle is the current supported upstream build.

## Complementary responsibilities

| Component | Responsibility | Evidence that is insufficient for acceptance |
| --- | --- | --- |
| Linear | Selected work, owner, acceptance criteria and one current workpad; explicit state transitions. | Issue creation or a Done label by itself. |
| Symphony | One admitted coding session and its bounded repository workspace. | Session start, clean exit or proposed diff. |
| LangGraph | Finite discovery/delivery/verification progress and durable checkpoint/recovery identity. | A checkpoint for an intermediate node. |
| Windmill | Selected deterministic command execution, admission and actual job outcomes. | Submitted job or successful API response without result verification. |
| Repository review | Accepted changes against the versioned standard, affected checks and integration/release decisions. | Source preservation, push or directory count. |

Do not give each tool a second manager loop. A Symphony continuation reconciles
the existing LangGraph run and Windmill job identities, then proceeds from the
last verified outcome. Neither a timeout nor a lost session proves a mutation
failed. Inspect outcomes before retrying. Cancellation stops admission and records
remaining running jobs; it must not falsely report those jobs canceled.

## Binding contract and default-off behavior

The root integration writer resolves the real OffMenu Linear team ID, project
ID/slug, issue ID/identifier, admitted state IDs/names, required label IDs/names
and existing workpad comment ID. Names are displayed for humans; stable IDs bind
receipts. Record selected source head, allowed paths, owner, standard version,
checkpoint run ID, Windmill workspace and selected execution binary identity.
The team/project and four issue IDs are verified parent-supplied bindings. State IDs
are a catalog, not admission: admitted states remain empty while disabled. Missing
owner, workpad and label IDs remain unresolved requirements, not guessed values.
No token value belongs in a tracked binding; the template references a dedicated
`OFFMENU_LINEAR_API_KEY` setting whose existence or authorization is not assumed.

The template has three independent default-off barriers: no ordinary admitted
state, a workspace creation hook that exits 78 and `codex.command: false`.
`enabled: false` in the JSON is an OffMenu binding declaration, not a claim that
Symphony natively implements an enable flag. The Markdown filename deliberately
avoids a root `WORKFLOW.md` that a service might discover automatically.

Activation requires reviewing an OffMenu-specific deployment configuration,
verifying the selected binary schema and eligible model/provider, resolving the
contract, selecting a dedicated workspace and replacing the guards deliberately.
The tracked template itself remains disabled; a separately generated private runtime configuration can be launched explicitly. An eventual start should first prove
that unrelated projects and unlabeled issues are excluded and that only the
single admitted writer can change this branch. Do not attach OffMenu to CIX's
active service, reuse its runtime/workspaces or revive its workers.

Every session stays on `feature/langgraph-delivery-standardization`; it may not
create a new feature branch, automatically push, dispatch Actions, merge or deploy.
Parallel specialists remain read-only until the one integration writer applies
reviewed changes. Promotion to `develop` and release promotion to `main` are
separate review actions. Existing application-worker and automation holds remain
in force. LangSmith/private telemetry stays disabled.

## Completion evidence

The Linear workpad records exact branch/head, accepted standard version, changed
paths, actual selected checks and their exits, unrun checks, checkpoint/job IDs,
review disposition and blockers. The same identities must reconcile with the
local durable run. Do not publish private receipts merely to populate a workpad;
use sanitized summaries and restricted evidence references. Failure to update
Linear is a reported synchronization blocker, not permission to claim Done.

## Isolated native parser verification

The discovered executable wrapper is
`/home/user/.local/share/cix/symphony/0c01ff0975da80ded7044a5ad76a44ac87053670-d215a99ac5a44941/bin/symphony`.
Its archive SHA-256 is recorded in the source binding. The observed CLI has no
validation-only option; invoking it with its guardrail acknowledgement starts
the application. Do not use a normal CLI launch as a configuration check.

The isolated helper extracts only `.beam`/`.app` files into a temporary directory
and invokes the installed bundle's `Workflow.load/1` and `Config.Schema.parse/1`
in a temporary Erlang VM. It starts the Elixir runtime, not the Symphony
application/supervisor, tracker, lifecycle hooks or Codex sessions. This validates
compatibility with that exact local bundle without activating it:

```sh
python3 dev/delivery/symphony_validate.py --bundle /home/user/.local/share/cix/symphony/0c01ff0975da80ded7044a5ad76a44ac87053670-d215a99ac5a44941
```

Observed result: passed, exit 0. This is native workflow/config parsing, not a
Linear authentication check or a runnable coding-session receipt. Both
`OFFMENU_LINEAR_API_KEY` and fallback `LINEAR_API_KEY` were absent from this task's
process environment; only presence was checked, and no credential files or values
were read. Existing service credentials were not inspected or borrowed. Admission,
owned runtime credentials, owner/workpad identity and eligible model resolution
remain prerequisites for future separately reviewed activation.

## Existing launcher and authenticated executor discovery

A subsequent non-secret inspection found the installed system-unit declaration
`/etc/systemd/system/cix-symphony-primary.service` and its
`accepted-stable-paused.conf` drop-in. Their configured launcher is
`/home/user/.local/share/cix/service/primary/service-start.sh`. This is a
configuration observation, not a service-state check or authorization to start it.
The launcher selects the `native-completion-71b0aa5377fb96f2` Symphony escript with
the base bundle's OTP runtime, and a CIX-specific `WORKFLOW.native.md` path. The
base bundle used for OffMenu's isolated parser check is therefore not proof of
the exact CIX service implementation's schema or an accepted OffMenu runtime.

The service declares systemd credential name `linear-api-key`, sourced from
`/etc/cix-symphony-primary/linear-api-key`. Launcher source requires
`CREDENTIALS_DIRECTORY` and exports that credential as `LINEAR_API_KEY`. No
credential file was read and no launcher was executed. These are real local
credential conventions, rather than a guessed `CIX_LINEAR_API_KEY` variable.
This credential's OffMenu project/team scope is unestablished; its presence in a
CIX service must not be treated as authorization to copy or reuse it for OffMenu.

The retained `WORKFLOW.standard.md` selects:

```text
/usr/bin/python3 -I /home/user/.local/share/cix/service/primary/codex_compatible.py app-server
```

The retained paused workflow selects the vendor Codex executable directly. The
compatibility shim verifies installation and protocol, then inherits its process
environment and executes the accepted package generation's `app-server`. Its
`--check` can fetch npm artifacts, write cache/launch receipts and spawn protocol
probes; it is not a read-only status command and was not invoked.

The installed vendor executable exists at
`/usr/lib/node_modules/@openai/codex/node_modules/@openai/codex-linux-x64/vendor/x86_64-unknown-linux-musl/bin/codex`;
its package manifest reports version `0.162.1`. Calling only that executable's
`login status` returned exit 0 and reported a ChatGPT login, not API-key login.
Raw output was suppressed and no inference/session was started. This establishes
an existing authenticated local consumer Codex route. It does not establish API
credit, permission to reuse the CIX gate, eligible no-cost inference for OffMenu,
or a resolved model. A preferred model string is not a model-resolution receipt.

Presence-only checks in this task's process environment found
`CIX_LINEAR_API_KEY`, `LINEAR_API_KEY`, `OFFMENU_LINEAR_API_KEY`,
`CREDENTIALS_DIRECTORY`, `CODEX_HOME`, `OPENAI_API_KEY` and `OPENAI_BASE_URL` absent.
That does not contradict a system service's separately injected credentials or
the vendor's stored ChatGPT login. The remaining integration gap is an approved
OffMenu-scoped tracker credential delivery route and an accepted executor/model
eligibility decision. Existing installation and login discovery removes the
need to invent a new local AI installation, but does not close those gaps.
No CIX service configuration, credential, worker or session was changed.

## Own OffMenu native integration

The integration now has its own launcher and hooks:

- `dev/delivery/symphony_launch.py`: preflight, generate a private runtime workflow,
  verify native parsing, then optionally execute one finite selected run.
- `dev/delivery/symphony_workspace.py`: admit only `UIF-90`, clone the pinned local
  source branch without a second feature branch, verify its head and cap admissions
  at two attempts. The attempt marker sits outside the issue workspace so native
  terminal-workspace cleanup does not erase that budget.
- `dev/delivery/symphony_protocol.py`: initialize the vendor app-server, read account
  metadata without refreshing credentials, list models and read quota metadata.
  It never sends `thread/start` or `turn/start`; raw responses are not printed.
- `dev/delivery/symphony_test.py`: offline admission regression tests.

These files reuse the installed base native escript/OTP artifact and vendor Codex
executable, not the CIX custom launch gate, policy, service, hooks or workspaces.
A library installed below a CIX-named directory is reused as an immutable binary;
OffMenu owns its generated configuration, state and integration behavior.

Native Linear source filters `project.slugId`, which is `ccd080f4f6f0`; the human
browser slug is `offmenu-ccd080f4f6f0`. The project UUID remains
`ce60c1ab-a732-4a71-8471-14c9dc393886`. Before a run the launcher verifies tracker
access, project UUID/slugId/team, exact `UIF-90` identity and state, unique
`offmenu-uif-90` label, and that the candidate set contains only that issue. Hooks
reject all other workspace identifiers even if a later label changes. The native
schema supplies concurrency, turn and retry-backoff limits, but no maximum retry
count; the OffMenu hook supplies the finite attempt budget. The parent launcher
also imposes a 180-second default wall-time limit and terminates the owned process
group on timeout or after the first native after-run marker. That marker records
only that a coding attempt ended; it does not claim the tests passed.
A process exit is never reported as accepted delivery.

The run task is constrained to meaningful CLI integration tests at
`tests/delivery/test_cli.py` and an optional minimal, test-proven
`offmenu/delivery/__main__.py` correction. It uses the existing canonical
`.venv-delivery/bin/python` with the clone on `PYTHONPATH`. No auto commit, push,
merge, production deployment or Actions dispatch is enabled. The sole integration
writer reviews the resulting diff and tests before accepting it.

Native protocol preflight succeeded outside the restricted sandbox network:
account type `chatgpt`, plan `pro`, quota response present, and default model
`gpt-6.1-sol` supporting `medium` reasoning. The available model list also included
`gpt-6.1-terra`. No thread, turn or inference call was made. Earlier restricted
network account/quota requests returned internal protocol errors; they must not
be mistaken for unavailable credentials. The read-only preflight probe uses an ephemeral private
Codex home with a symlink to existing user authentication when file-backed, and
a writable temporary SQLite home. It copies no credential content, makes no new
key and removes its temporary home after process cleanup.

The root integration separately verified the existing systemd-delivered tracker
credential can access the OffMenu project, and assigned the dedicated label to
`UIF-90`. The launcher accepts either the selected runtime environment variable
or the service manager's injected `linear-api-key` credential; it never reads the
`/etc` credential source directly or stores a token in a workflow/receipt. Runtime
logs and checkpoints remain private outside the checkout. Do not print them
wholesale without sanitization.

Safe local commands before a coding run:

```sh
.venv-delivery/bin/python -m unittest discover -s tests/delivery -p test_symphony.py -v
python3 dev/delivery/symphony_launch.py preflight
python3 dev/delivery/symphony_launch.py preflight --probe
```

`prepare` and `run` require an explicit private runtime path and selected model.
They refuse tracked-dirty source, a wrong branch or an altered native escript.
A runtime configuration becomes executable only through an explicit `run` with
already established inference authority; no background service is registered.
A run must be followed by source/test evidence review and exact outcome
reconciliation, not a claim of completion based on the job starting.

The coding-run launcher uses an OffMenu-owned temporary `CODEX_HOME` (mode 0700),
references the existing user `auth.json` through a symlink, and selects owned
SQLite state. It reads or copies no authentication content and does not inherit
the workstation config, plugins or hooks. The home is removed only after the
owned process group has stopped. The root integration confirmed
the existing included ChatGPT Pro route for this explicitly authorized finite
coding task; no new paid API provider or key is required. Exact launch after a
clean source commit, from the already credential-injected process:

```sh
python3 dev/delivery/symphony_launch.py run --runtime /home/user/src/offmenu-data/runtime/symphony-uif90-20261029 --model gpt-6.1-sol --inference-authorized --duration-seconds 180
```

The launcher stops its owned process group when the first native after-run hook
produces a completion marker. Review the resulting clone diff and focused tests;
`accepted_delivery` remains false in the process receipt until that review.

## Initialize timeout diagnosis and bounded correction

The first real admitted run created its UIF-90 clone but timed out during native
`initialize`, before any thread, turn or code change. The after-run marker meant
only attempt ended. The launcher now records `coding_attempt_ended`, parses a
sanitized native outcome (`failed`, `normal_turn_completed` or `unknown`) and
returns a failure for failed/unknown outcomes. It never equates the marker with
successful delivery; `accepted_delivery` stays false pending review.

Following the systematic-debugging workflow, an initialize-only A/B comparison
held the native Bash login-shell command, model flags, clone cwd and
`symphony-orchestrator` client identity constant. Inherited default Codex home
reproduced the timeout. An isolated home referencing the same authentication
initialized successfully. No threads/turns or inference were started. The
workstation config contains multiple MCP/plugin and hook integrations; the
comparison identifies inherited home/config initialization collectively, not a
particular plugin. No companion FD requirement was found in launcher source.

`dev/delivery/symphony_codex.py` applies the proven isolation boundary to the
coding run. A regression test uses fake fixture files to verify private mode,
same-auth-path symlink, no config copying, cleanup and preservation of the source
files. A second regression test distinguishes a native failure from normal turn
completion. Eight focused tests pass. The native coding rerun remains a separate
execution receipt; these tests do not claim a coding session completed.

A live OffMenu-only session subsequently created11 meaningful CLI integration
tests. Its finite180-second supervisor deadline stopped it after a normal turn
while native continuation was still active; this was reported as unaccepted,
not green completion. The integration writer independently reviewed and ran
all11 tests successfully. The launcher now permits one coding turn so native
continuation does not duplicate a task after its candidate is produced.
