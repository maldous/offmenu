# OffMenu confined execution baseline — 2026-10-27

## Installed and verified

- Private deployed Windmill job client: `u/admin/foo_jobs_20261027`.
  Source: `scripts/windmill/windmill_foo_jobs.py`; pinned cached dependencies
  `paramiko==5.1.0`, `wmill==1.850.0`; no workspace-wide dependency change.
- Confined host supervisor: `scripts/windmill/job_runner.py`. Durable job IDs,
  command/source hashes, compact receipts, 1-MiB-per-stream host logs, hard
  process-tree deadlines/cancellation, and crash markers that fail closed.
- Nonblocking admission: one writer or two independent short readers; one job
  with a declared timeout over 30 seconds, leaving a worker for control calls.
  These are cooperative scheduling locks, not protection against unrelated
  processes. Read mode does not make the filesystem read-only.
- Private native Windmill state: `u/admin/offmenu_platform`; deployed checkpoint
  adapter: `u/admin/offmenu_platform_checkpoint`. Only bounded metadata/hash
  references go into control state. Large artifacts remain on Foo.
- Host artifact/checkpoint helper: `scripts/windmill/storage/offmenu_storage.py`.
  Atomic content-addressed publication, verified versioned checkpoints and
  same-disk backup/restore; source/docs/receipts in `storage/`.
- Offline DuckDB 1.5.6 runtime:
  `/offmenu/data/.offmenu-platform/duckdb/1.5.6-bc9619ed7d4f/runtime.py`.
  Use `python3 -I -S`; explicit authorized local paths only, four query threads,
  8-GiB buffer and 20-GiB spill ceilings, extension loading disabled, external
  access disabled outside the allowlist, configuration locked. See `duckdb/`.
- Repository skills: `.agents/skills/offmenu-batch-execution/`,
  `offmenu-checkpoint-recovery/`, and `offmenu-provenance-validation/`.
  Source references and pins live under `scripts/windmill/skills/`.

## Actual evidence

All **66 synthetic tests** passed inside the real jail (13 execution/client,
26 storage/state, 27 DuckDB validator/runtime tests):
`01a17f87-c0a9-2f78-5cb7-7abf64fbc6af`; detailed summaries:
`01a17f87-ee7c-b7bd-36e1-f47efdf1a59a`.

The deployed long-job test completed in 62.569 seconds, beyond the former
60-second transport cap: `01a17f79-9493-18e9-88f0-582b58e44d0f`.
A second long submission returned busy without reserving its ID, and live status
remained responsive. Actual child termination, duplicate-ID no-replay and bounded
logs are covered by the jail tests.

Synthetic artifact/checkpoint backup and restore succeeded on Foo; the restored
reference was committed and independently read on the other Windmill worker.
See `storage/deployment-receipt.json`. This is **not an independent backup**.

DuckDB's pinned wheel and 53 installed files were verified. Two actual 10,000-row
Parquet write/read/group-by checks passed. Outside-allowlist reads and post-lock
setting changes were actually denied. See `duckdb/DEPLOYMENT-RECEIPT.json` and
`duckdb/INDEPENDENT-VERIFICATION.json`. Tiny synthetic timings are not a throughput,
speedup or measured-optimum claim.

## Boundaries retained

No root/Docker access, host-network access for jobs, raw-data export, new database
service, local AI, model endpoint, GitHub Actions or quota-blocked Foo/Codex
executor was introduced. Host canonical worktree paths remain outside the jail;
never prune worktrees because their paths look absent through this mount.

Receipts survive normal sessions once written, but active jobs are not guaranteed
to survive SSH/Windmill termination. Unknown outcomes need explicit reconciliation,
not automatic replay or deleting in-flight markers. The 1,800-second configurable
helper maximum is not a measured Windmill server timeout guarantee. PostgreSQL
persistence/independent backups remain unverified.

The runtime wheel, venv, logs, state and artifacts live in ignored
`data/.offmenu-platform/`; they are excluded from source custody. Reviewed code,
tests, dependency locks, public provenance and synthetic verification receipts are
kept in this source tree. The setup-only installer draft is retained for provenance,
not deployed as an unnecessary reinstall endpoint.
