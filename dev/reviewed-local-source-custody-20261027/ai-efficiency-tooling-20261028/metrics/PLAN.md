# Existing Windmill integration: source review only

The Foo task exposes the existing `Windmill OffMenu Chat` connector and successful
read-only calls were made using workspace `offmenu`: `read_workspace_item` with
`version=deployed`, `list_workers`, and filtered script metadata listings. No MCP
configuration, credentials, resource values, host Docker access, job execution,
provider inference, draft writes or deployment were involved. No worker directory,
mount, service, script or lock test was created.

## Live evidence obtained

* Adapter `u/admin/offmenu_groq_public_development_20261028` is deployed Python3,
  empty extraPerms, exact source SHA
  `3760b83e2678f89e2330a62f2ccdf0a8e935461f5cbc2168a3f57d0e725e9f38`.
  It still matches the independently approved R2 baseline, including all five tasks.
* Deployed caller `u/admin/offmenu_provider_orchestrator_20261028` has empty
  extraPerms and source SHA
  `cef944eedb0a6990cd6500b49abac023103d289551506c741b7162bdb6f829dd`.
  Its actual ROUTES map names the adapter and all five tasks. Its RESOURCES map
  names `u/admin/offmenu_provider_groq_20261028`. launch() passes
  `connection='$res:'+RESOURCES[p]` and Groq `task` to `wmill.run_script_async`.
  No credential is synthesized or exposed. Registry lookup is by
  `u/admin/offmenu_free_provider_registry_20261028`; its contents were not read.
* list_workers returned 64 recent workers, all in group `default`, each advertising
  `python3`. Returned fields are only worker identifier, group, custom_tags,
  last_ping and jobs_executed. These establish available Python routing, not the
  specific adapter job's worker, mount topology, permissions or fork/signal support.
* The exposed supported connector has no mount/permission/fork/signal metadata
  method. A filtered script metadata query for `mount` returned no items; the
  runtime query found only an unrelated publisher draft, which was not read/run.
  No existing runtime evidence proving the needed cache prerequisites was obtained.

## Ready for source review: metrics/validation independently of cache

`offmenu-ai-integration-20261028-metrics-only.patch` changes the exact live adapter
and only the caller's results projection. It is a new proposed integration hunk,
not covered by R2 approval and not activated.

The adapter contains only the existing fixed task catalog, transport and approved
R2 deterministic validator/token parsing logic. It adds prompt/completion tokens,
reported provider cached tokens (null if absent), local elapsed seconds, response
IDs, validation errors and the bounded full response bytes. It does not pad or
change prompts or settings, retry, call a second provider, or use filesystem state.
No fork/signal/cache imports, storage paths or account namespace are required.

Structural validity is exposed as `schema_accepted`, with an explicit validator
version; it is never semantic acceptance or delivery. The uncached stage omits
`new_accepted_outputs` and accepted artifact IDs: without persistent provenance
and deduplication, it cannot truthfully claim unique accepted-artifact accounting.
`cache_hit` remains false. Missing usage remains unknown.

`main(connection, task)` retains the exact typed live signature and calls named
`uncached_main(connection, task)`. That function performs the single transport
call and never calls main or run_cached. No R2 cache wrapper is imported or aliased.
The caller ROUTES, RESOURCES, admission/quota logic, dispatch arguments, job
launch, cancellation handling and schedules are untouched.

The caller's `results` projection currently drops all new metrics/errors/response
IDs. Its proposed small hunk includes those scalar fields, reports schema rejection
as `failed_structured_validation_not_delivery`, marks summary-only output clipping,
and retains the full adapter-result job ID. The full bounded adapter result stays
in the existing Windmill job result; the summary does not pretend to contain it.
The existing run URL and job ID remain present. Even a schema-valid output remains
`candidate_requires_review`.

Validation here was source-only: both proposed Python sources parse; all five
prompts/settings and validator/token helper functions match the approved source;
the patch applies cleanly to exact deployed snapshots; main's forwarding target
is uncached_main and the proposal contains no run_cached call. No prior tests were
repeated and no runtime/inference claim is made. Independent review of this new
hunk and any requested focused mocks must precede activation.

## Cache activation remains blocked, with exact next steps

Before a cache integration diff, the existing owner must supply read-only verified
runtime evidence for a persistent trusted POSIX store shared by the actual
participating containers, private ownership/permissions, functioning atomic
replace/flock semantics, and actual Python fork/SIGALRM/SIGKILL support. The current
connector's worker list cannot furnish those facts. Do not infer sharing from the
configured `windmill_worker_cache` name or `/tmp/windmill/cache`; do not adopt
world-writable `/srv/windmill/runtime`; do not use ordinary platform resource
state as a distributed lock. No alternative host/Docker route was attempted.

The owner must also identify a non-secret account namespace tied to the existing
resource identity and a verified model revision/epoch, without reading/exporting
credential values. None was chosen here. If prerequisites are unavailable, the
metrics-only stage can still be reviewed/adopted; no storage project is required.

After prerequisites are evidenced, the cache integration must bind
`_provider_child` directly to named `uncached_main`, then separately wrap the public
main or dispatch to run_cached using owner-reviewed non-secret configuration.
R2's current child calls main; simply wrapping main would recurse and is forbidden.
That future binding/configuration hunk needs independent review and focused mocks
before activation. R2 deadlines, exact provenance, receipts, unique artifact IDs,
and no-fallback behavior remain required. No cache diff or activation is proposed
before the missing evidence arrives.

## Adoption / rollback handoff

1. Independent reviewer evaluates the metrics-only patch against the two exact
   live source snapshots and hashes. R2 remains frozen unchanged separately.
2. Authorized existing connector owner rechecks both deployed hashes immediately
   before applying any approved source hunk; preserve typed input schema, resource
   reference and empty extraPerms. No inference is necessary to publish source.
   Do not activate from this investigation alone.
3. Roll back the metrics stage by restoring the two exact saved live source
   snapshots through that existing connector, retaining prior job results. No
   provider credentials, data, storage or admission controls need rollback.

Supporting files share this prefix in `/home/user/src`:
`offmenu-ai-integration-20261028-`. The inventory records exact hashes. The approved
R2 directory and original Windmill files were verified unchanged.
