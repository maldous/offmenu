# Windmill storage and SQL: actual findings, 2026-10-28

## Live observations

Supported MCP reads independently returned no configured Data Tables and no
DuckLake catalogs. These are separate features. Workspace-settings read was
explicitly denied (`Require Admin privileges for admin`); no alternative route
was used to obtain those settings. Native `u/admin/offmenu_platform` exists as
owner-private `state`, `extra_perms={}`, with the documented local artifact root.
The checkpoint and health scripts exist. Raw API resource reads and Foo-mounted
local files are not automatically equivalent to Windmill Asset references.

The existing offline DuckDB package on Foo is 1.5.6. Direct bounded no-file
SELECT/parser check succeeded in Windmill run
`01a180f8-74d3-db06-7a6f-2ec9abb97ec9`. There is no deployed dedicated SQL-query
entrypoint; only the setup installer draft. The old connection factory caps each
connection at four threads, 8 GiB buffer and 20 GiB spill. Its tiny 10,000-row
smoke is correctness evidence, not proof that four threads is optimal.

## Native feature trade-offs, not dashboard filling

- **Data Tables:** useful for genuinely shared transactional metadata/querying,
  but current docs say workspace members have CRUD access. An instance-backed
  table provisions a separate database on existing PostgreSQL and a generated
  service role, rather than requiring another PostgreSQL service. This is not
  equivalent to private state. Do not provision it without specific approval
  for the database/role and wider workspace access. It does not accelerate the
  active SQLite coordinator merely by existing.
- **DuckLake:** an object-storage-backed catalog, not a switch that makes local
  DuckDB faster. Managed maintenance is Enterprise-only. No live catalog exists;
  do not migrate the active proof DB or create a second authoritative corpus.
- **Workspace object storage:** current CE docs describe 10 GiB total storage,
  a browser limit above 20 objects and broad workspace access without advanced
  permissions. The current 15+ GB proof DB is not an appropriate wholesale
  import. A new same-Foo object service would add machinery and credentials,
  but would not be an independent backup. No such change was made.
- **Assets:** tracks supported resource/object/table references in scripts,
  not every file on a mounted host. Empty Assets does not mean there is no data
  or durable execution. Real lineage should identify the actual query, inputs,
  output digest and producing run rather than inventing S3 references.

Official current documentation (reviewed live):
- https://www.windmill.dev/docs/core_concepts/persistent_storage/data_tables
- https://www.windmill.dev/docs/core_concepts/custom_instance_database
- https://www.windmill.dev/docs/core_concepts/persistent_storage/ducklake
- https://www.windmill.dev/docs/core_concepts/object_storage_in_windmill
- https://www.windmill.dev/docs/core_concepts/assets

Pinned v1.850.0 public source fetch was unavailable (GitHub/raw fetch failures),
so these are current documented constraints, not a claim to have independently
verified all compiled CE enforcement branches in the running binary.

## Useful no-new-service change

`duckdb_query.py` supplies the missing actual query route: a trusted reviewed
SELECT over one finalized local Parquet input named `input_data`; it writes the
result and plan/profile/receipt locally, never the source. It uses the existing
pinned native package in a new in-memory connection, without changing the old
locked runtime or the active proof DB. Extension/network restrictions remain,
with exact allowed input paths and a private output directory.

Engine threads are separate from worker processes. The operating default is
four, but the supported requested range is 1–27 under the current supervisor's
27,000 millicore limit. CPU reservation equals threads × 1,000, once per query;
RAM reservation includes buffer headroom, and spill/result bytes share the same
aggregate admission budget. A connection must fit the assigned CPU affinity.
No factor of 64 jobs or 256 subprocesses is multiplied into these reservations.

`EXPLAIN ANALYZE COPY` executes and profiles the actual query once while writing
Parquet. Source row groups and wall/CPU time are recorded. More threads are only
a capability: useful parallel scans need multiple row groups; the right number
must be measured on the user's real immutable workload. No synthetic stress or
throughput benchmark is requested. Prefer projection/filter pushdown and set
queries over Python row loops. PostgreSQL planning would need real EXPLAIN
plans and query/session budgets; no Postgres admin setting was changed. SQLite
still has one writer; this route makes no parallel-write claim.

DuckDB references:
- https://duckdb.org/docs/1.5/guides/performance/how_to_tune_workloads
- https://duckdb.org/docs/1.5/guides/meta/explain_analyze

## Verification and boundaries

Twenty local contract and wrapper tests pass, including declared-resource tampering,
thread/process separation, unsafe paths, parent-directory fsync, exclusive
output IDs and sampled result-growth interruption. Sampled interruption is not
an OS disk quota. Input stat stability is not a content hash or independent
backup; receipts state that explicitly. Existing finalized Parquet inputs are
required. Failed output directories are retained, not replayed or overwritten.

The first tiny three-row/eight-configured-thread end-to-end functional test was
not admitted: `busy/incompatible_job_active`, `reserved:false`, Windmill run
`01a180fa-64f1-a47e-41f5-d98dcee18b0a`. No host workload ran. The same ID is held
for the owner's confirmed clean boundary; no exclusion bypass occurred.

Also found a live health-check mismatch: `markers_checked <= 2`, while capacity
now supports 64 slots. Capacity owner was notified to reconcile the actual
checker scan and validator; this task does not edit that owner's files.

## Actual end-to-end result at confirmed clean boundary

Same previously nonadmitted logical ID ran at the qualifier owner's confirmed
clean boundary. Windmill run `01a180ff-9b94-264a-079f-d8c9bbab8220` succeeded,
`child_tree_gone:true`, `reconcile_required:false`, approximately 0.120 seconds
for the enclosing helper. It read three synthetic rows and wrote one row in a
227-byte Parquet file, with eight configured engine threads. This verifies
capability/functional wiring, not throughput improvement (one input row group).
Metadata receipt readback, output digest, local profile and duplicate-ID refusal
passed. Full sanitized evidence is `ACTUAL-FUNCTIONAL-RESULT.json`; readback
Windmill run `01a18100-3d2b-093a-8012-b5a76f089373`. Qualifier owner was promptly
released to resume its real workload; no proofDB/data source was opened.

## Deployment boundary

Independent final review passed, all20tests passed and actual draft plan/results
paths succeeded. Attempt to deploy `u/admin/offmenu_sql_query_20261028` was
rejected by platform auto-review: it requires specific authorization for this
exact persistent workspace change. No deployment or workaround occurred.
The reviewed per-user draft remains usable through editor preview/MCP test run;
normal deployed-path invocation remains blocked pending that authorization.

## Deployment resolved with specific authorization

After the user explicitly approved the exact private SQL entrypoint, the
unchanged candidate was reconciled and the known-nonexecuted deployment retried
once. It succeeded. Readback confirms deployed source byte-for-byte unchanged
and `extraPerms={}`. Live deployed status succeeded in
`01a18106-e370-7bfa-870f-ed85861cae58`.

The complete deployed submit → shared admission → native child → query → results
path was then verified using the existing three-row functional fixture, not a
stress workload. Submit run `01a18107-7186-b0a3-e746-9369fa3bd95b` returned child
`01a18107-7236-114c-89c7-9373ab8e3c59`; results run
`01a18107-a165-c31d-319c-500d54f14969` confirmed admitted, succeeded, child tree
gone, one227-byteParquet output and matching expected output digest. No active
qualification pause, corpus reads, proof DB access or credentials change occurred.
