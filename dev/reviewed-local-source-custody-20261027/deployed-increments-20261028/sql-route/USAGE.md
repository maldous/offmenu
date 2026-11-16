# Local SQL queries through Windmill

Deployed owner-private entrypoint: `u/admin/offmenu_sql_query_20261028` in workspace `offmenu`.
Open https://windmill.aldous.info/scripts/get/u/admin/offmenu_sql_query_20261028?workspace=offmenu
or use the connected MCP script-run tool. Exact deployed source and `extra_perms={}`
were verified after the user's specific deployment approval. No credentials are arguments.

## Real query

1. Select a **finalized derived Parquet file** already inside `/offmenu` and a
   reviewed UTF-8 SQL file inside `/offmenu`. The SQL must be one SELECT and
   refers to the selected Parquet as `input_data`. Do not point this route at
   the active SQLite proof DB or an original corpus mount.
2. Call `plan` to inspect the shared resource reservation without executing.
   Replace the example paths with real authorized paths:

```json
{
  "action": "plan",
  "job_id": "report-20261028-01",
  "input_path": "/offmenu/data/reports/finalized.parquet",
  "sql_path": "/offmenu/queries/report.sql",
  "threads": 8,
  "memory_gib": 8,
  "spill_gib": 4,
  "result_gib": 1,
  "timeout_seconds": 300
}
```

3. Use the same arguments with `action: "submit"`. This starts a real native
   Windmill child using the existing capacity-admitted Foo runner. The result
   returns the child ID/link and logical ID. `submitted:true` is not admission
   or completion; always inspect the returned child.
4. Call `status` or `results` with the returned identifiers:

```json
{
  "action": "results",
  "job_id": "report-20261028-01",
  "windmill_job_id": "REPLACE_WITH_RETURNED_UUID"
}
```

This returns bounded metadata only: admitted/busy reason, actual terminal state,
engine settings, row counts, input row groups, wall/CPU metrics, output/profile
hashes and local result/profile paths. The actual table rows and query plan text
remain on Foo. The query receipt is not a second authoritative database.

For an explicitly requested cancellation use `action:"cancel", job_id:"..."`.
Cancellation returns a separate request ID; it is not proof the job is terminal.
Read the original status until the supervisor confirms child cleanup.

## Existing verified result, without new work

This reads the tiny functional test's completed receipt; it does not rerun it:

```json
{
  "action": "results",
  "job_id": "sql-wrapper-20261028-0541",
  "windmill_job_id": "01a18107-7236-114c-89c7-9373ab8e3c59"
}
```

## Operating rules

- Default 4 query threads is not a permanent optimum. Request 1–27 threads under
  current shared CPU admission; 8 threads reserves 8,000 millicores but still one
  process. Simultaneous queries and qualification share the same reservation pool.
- Buffer RAM, process headroom, spill and output are budgeted together. Runtime
  query settings are locked after configuration. No external access or extension
  autoload/autoinstall is enabled. Only the exact selected input and private
  output directory are accessible to the engine.
- SELECT may use predicates, projection, grouping and joins/subqueries on its
  selected input. Optimize the real plan first. More threads do not make a single
  tiny Parquet row group parallel or make SQLite support parallel writers.
- A busy response with `reserved:false` did not run. Reconcile and wait for the
  stated conflict/capacity to clear before retrying the same logical ID. Never
  change IDs to bypass a reservation or replay an uncertain query.
- Completed and incomplete output IDs are exclusive. They are not overwritten
  or automatically resumed. Missing receipt does not prove no side effects.
- Result growth has a sampled interruption guard; this is not a filesystem quota.
  DuckDB buffer limits do not bound all process memory; supervisor RAM guards
  and declared headroom still matter.
- Result digest is recorded after the write. Routine status checks validate
  identity and size, not a new full content hash. Input stat stability is checked,
  but a source content hash is not asserted. Same-disk files are not independent
  disaster recovery or a backup of Windmill PostgreSQL.
