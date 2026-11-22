# Execution and protocol boundaries

Cloud durable task state and Foo-local execution state have separate interfaces
and credentials. A connected MCP tool does not transfer its authentication into
a local process. No webhook or cross-host checkpoint replication is implied.

## Connected Windmill workspace

The connected Foo Workspace account currently lists only workspace `foo`.
Use `workspace_id="foo"` for its supported connector calls. This observation
describes the connected account's scope, not the absence of every historical
workspace on the server. OffMenu is the project identity; script names,
`/offmenu` checkout paths and local workspaces are separate identifiers.

For example, inspect deployed dispatcher metadata through `read_workspace_item`
with the current binding before considering execution:

```json
{"workspace_id":"foo","type":"script","path":"u/admin/offmenu_delivery_dispatch","version":"deployed"}
```

The inspected dispatcher still requires `WM_WORKSPACE=offmenu` and the existing
admin owner, and targets `/w/offmenu/...`; the checkpoint adapter has the same
workspace mismatch. The maintained client `tools/delivery/stokowski_mcp.py`
also still sends `workspace_id="offmenu"`. These dependent routes are not
qualified for the current connector. Do not probe the old workspace, relabel
existing jobs or silently substitute a transport. UIF owns coordinated shared
client, dispatcher, receipt/observation and runtime alignment; this document
does not deploy that correction or establish publisher ownership.

The observations marked Used below and dated verification records retain their
original scope. Historical `?workspace=offmenu` URLs and the disabled
`tools/delivery/symphony-linear-binding.json` retain provenance, not current
actionable connector defaults. Independent project-cloud
work continues under its existing admission, review and integration controls.

## Retained protocol observations

| Source → destination | Direction and purpose | Actual interface | Status |
| --- | --- | --- | --- |
| Cloud task → connected Linear/GitHub/Windmill tools | Control: selected API operations and readback | MCP connector tools; platform connector transport details are not exposed here | Used |
| Cloud task → Foo executor | Control: bounded shell/file operations | Selected-environment executor tools; underlying platform transport unspecified | Used |
| Native Symphony → Linear | Pull: admitted issue/workpad selection | HTTPS GraphQL API, exact project/label/state filtering; configured 60-second polling | Used; no webhook |
| Native Symphony → Codex | Push: coding session/turn, receive events | Local Codex CLI `app-server`, JSON-RPC over stdin/stdout | Used |
| Codex → existing provider session | Model execution/authentication | Codex's existing ChatGPT session route; no MCP credential transfer | Demonstrated; quotas remain provider-controlled |
| Cloud Windmill connector → Windmill server | Control: submit/read jobs, deploy selected script | Windmill API through MCP; deployed Python uses the wmill SDK for existing state/resources | Used |
| Windmill Python worker → Foo | Control: bounded command; return receipt | Paramiko SSH with pinned host key, typed `offmenu-exec-v1` bridge and existing jailed identity | Used |
| Foo runner → computation | Execute and observe | Local subprocess/process groups, CPU affinity, private files and durable receipts | Used |
| Local CLI/Windmill adapter → LangGraph | Execution decisions and recovery | In-process Python SDK; LangChain core integration dependency | Used; no remote model manager |
| LangGraph → checkpoints | Durable local state | SQLite plus private accepted-output/event records under selected `.delivery/` | Used; same-host/mount |
| Foo Git → GitHub repository | Source fetch/push | Git over SSH | Used |
| Cloud GitHub connector → GitHub PRs/reviews | Control/metadata | GitHub HTTPS REST/GraphQL through MCP | Used; separate from Git transport |

Linear records requested work, dependencies and acceptance references. LangGraph
checkpoints restore execution decisions. Windmill receipts establish operational
outcomes. Git preserves reviewed source. These complement each other; none is a
replacement for all four. LangSmith remains an optional future observability
choice with private telemetry disabled.
