# Execution and protocol boundaries

Cloud durable task state and Foo-local execution state have separate interfaces
and credentials. A connected MCP tool does not transfer its authentication into
a local process. No webhook or cross-host checkpoint replication is implied.

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
