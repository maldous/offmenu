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
No activation occurred in this workstream. An eventual start should first prove
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
