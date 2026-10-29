# OffMenu Symphony integration

The supported capability is eight concurrent admitted coding sessions, selected
by [capacity-policy.json](../../tools/delivery/capacity-policy.json). Native
Symphony, workspace hooks and Codex state are OffMenu-owned. CIX services and
credentials are not reconfigured. Capacity does not automatically start sessions
or resume paused application workers.

Use the [parallel-capacity guide](../development/parallel-capacity.md) and
[ADR 0004](../adr/0004-resource-aware-parallel-capacity.md). Exact-source reviewed
manifests select the OffMenu project, issue IDs, tracker label, owners, write
scopes, resources and acceptance criteria. The tracker preflight rejects missing
or extra candidates. The legacy convenience default selects UIF-90; it does not
restrict manifests or the eight-session reservation pool to one issue.

Native hooks create private same-branch source clones, reserve resources before
coding, enforce disjoint logical write ownership, retain immutable task/source
bindings and record completion separately from acceptance. After-run scope
checks preserve violations as failed evidence. Cancellation retains resource
holds until the owned process tree is observed stopped. Unknown state does not
release a lease through time expiry or permit silent replay.

Codex app-server uses the existing ChatGPT login with no new API purchase.
Each workspace has separate Codex SQLite state. OffMenu's temporary auth reference
uses a private symlink to the existing auth file, without copying credentials or
inheriting workstation plugins. The native supervisor reaps its owned child tree
and retains unresolved outcomes. Provider-session readiness is refreshed without
starting a coding turn; a locally selected eight-session ceiling is not a vendor
quota guarantee. New paid API use and paid OpenRouter models remain outside scope.

The selected tracker key is delivered by the existing credential-injected
OffMenu environment. MCP credentials are not transferred. Native tracker polling
uses HTTPS GraphQL and a configured 60-second interval; it is not a webhook.
Linear records selected work; local LangGraph tasks remain independent of it.

```sh
.venv-delivery/bin/python -m unittest discover -s tests/delivery -v
```

```sh
.venv-delivery/bin/python tools/delivery/symphony_launch.py prepare --runtime /home/user/src/offmenu-data/runtime/SELECTED-RUN --model gpt-6.1-sol --manifest /private/reviewed-tasks.json
```

Preparation validates source/branch/native bundle, immutable inputs and native
configuration without starting tracker/model execution. `run` requires the same
explicit manifest, a new finite runtime, existing credential route and
`--inference-authorized`. Inspect the exact admitted commands and acceptance
before invoking it. `cancel --runtime ...` records intent; observation of stopped
processes establishes cleanup. No push, merge, deployment or issue assignment is
performed automatically.

Historical one-turn native sessions produced reviewed CLI tests and the
final-layout audit. Their recorded outcomes and limitations remain in
[validation.md](../../tools/delivery/validation.md). Those pilot receipts do not
set current operating capacity. The eight-session capability is verified through
real concurrent reservation tests, multi-task native configuration and failure/
cancellation/ownership cases, without an eight-model filler workload.
