# OffMenu task skills

Repository source package for the approved Windmill baseline. These files install
no plugin, model, daemon or MCP permission. Skills live at
`.agents/skills/<skill-name>/SKILL.md`; this map and `reference-pins.json` live at
`scripts/windmill/skills/`. Paths below are relative to the repository root.
Source presence alone does not prove a skill was selected for a particular chat.

| Skill | Use | Required outcome |
| --- | --- | --- |
| `offmenu-batch-execution` | Start/observe bounded jobs using the installed helper | Correct job identity and terminal or explicitly active state |
| `offmenu-checkpoint-recovery` | Inspect/recover existing helper state and stored artifacts | Verified state/artifact integrity; history and unrelated work retained |
| `offmenu-provenance-validation` | Validate evidence and source-only provenance | Claims supported by measured counts, byte bindings and appropriate coverage |

## Implementation map

- Execution: `scripts/windmill/job_runner.py`,
  `scripts/windmill/windmill_foo_jobs.py`, `scripts/windmill/README.md`.
  The helper's `--help` and installed source define arguments/statuses. The jobs
  client separates `transport_ok`, `admitted` and `job_succeeded`; `ok` is true
  only for a `succeeded` receipt. Process success is not data completeness.
- Storage: `scripts/windmill/storage/offmenu_storage.py`,
  `scripts/windmill/storage/windmill_checkpoint.py`,
  `scripts/windmill/storage/README.md`. These define local artifact/checkpoint
  integrity, version-preserving restore and small Windmill-side state references.
  The reference adapter is for Windmill, not the no-network SSH jail.
- Offline analytics: `scripts/windmill/duckdb/runtime.py`,
  `scripts/windmill/duckdb/install_offline.py`,
  `scripts/windmill/duckdb/README.md`. Use the existing pinned runtime rather
  than fetching packages/extensions during a data job. Installation/verification
  commands and platform requirements are documented in that README.

`reference-pins.json` binds this map to the final source bytes. It contains only
repository paths, byte counts and SHA-256s, not private state, datasets, credentials
or authoring-workspace paths. Deployment receipts are separate evidence; hashes
alone do not prove execution, completeness or confidentiality review.

## Boundaries that affect execution

The installed SSH bridge confines execution to `/offmenu`, as a non-root account
without job networking, Docker or sudo. Host paths outside that mount are not
made accessible by these skills. Historical root `./run` fetches/pushes Git and
uses other data roots; do not invoke it as a substitute for the local helper.
Reuse current approvals for routine work in the same scope, including recovery;
ask only when an actual new permission/scope change is needed.

Do not retry quota-blocked Foo/Codex environments until capacity is confirmed.
Do not use GitHub Actions, introduce new external live food lookup, change
production bindings, or upload raw data/secrets while configuring this baseline.
Local AI remains deferred. No cloud model/provider is a free local substitute.

## Minimal dependencies, not a workspace-wide redeploy

Prefer stdlib Python and existing SQLite tooling. Use the pinned offline DuckDB
runtime when useful for a measured analytical workload. Record the actual
interpreter/package versions. For Windmill scripts use reviewed per-script
lockfiles or narrowly named dependency files; preserve exact pins. Nested imports
are not automatically inferred: retain the deployed explicit requirement
annotations for the SDK/SSH client. Do not run an online installer inside a job
or change workspace-wide defaults, which can redeploy unrelated scripts.
Enterprise-only S3 caching/dedicated workers are not assumed available.
