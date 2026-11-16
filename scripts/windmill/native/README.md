# OffMenu native operations (Community Edition)

These reviewed scripts use existing owner/job authentication and the existing
pinned confined SSH transport. No new credential, group, shared folder, workspace
setting, provider/model call, global handler, worker pool or data store is added.

## Owned entrypoints

- `u/admin/offmenu_platform_check`: `mode=health|verify`, `max_items=1..100`.
  Calls the fixed host `platform_check.py` directly, not a nested Windmill job.
  The host is limited to eight seconds, 64 MiB and bounded metadata selection.
  The native wrapper validates every returned field/code/hash and also verifies
  the baseline native config's owner, state type and private ACL.
- Health schedule `u/admin/offmenu_platform_health_15m`: `0 */15 * * * *`.
- Verify schedule `u/admin/offmenu_platform_verify_daily`: `0 17 3 * * *`.
  Both use `Australia/Melbourne`, args `{mode, max_items:100}`, no callback/retry
  or run-as override. The daily run follows Melbourne daylight-saving rules.
- The three `u/admin/offmenu_skill_*` resources are exact reviewed SKILL.md
  content in existing `ai_skill` resources. They are passive documentation;
  publishing them does not invoke any model or configure OpenRouter.

## Outcomes and coverage

A successful check reports only its selected bounded scope, not complete host or
corpus health. `full_coverage` remains false. `status=incomplete,ok=false` with
only budget/coverage warnings is returned as data, not mislabeled corruption or
healthy and not automatically retried. Actual error findings raise a safe fixed
exception after recording an incident; they remain failed Windmill runs. Known
old terminal failures are informational and do not create recurring alerts.

No check removes runtime files, rewrites checkpoints, clears locks, retries a
business operation, rotates a secret, verifies a provider key or sends messages.
Same-disk artifacts/checkpoint backups do not establish independent host or
Windmill PostgreSQL backup.

## Incident contract

`windmill_incidents.py` stores separate create-only native `state` resources at
`u/admin/offmenu_platform/incidents/<sha256>`. Identity is the opaque nonsecret
logical job ID, fixed phase/code, fixed source-path hash and test flag. The first
Windmill run ID/time wins; duplicate calls re-read and validate rather than
update. A create race is reconciled by readback. Existing resources must have
`created_by:admin`, `extra_perms:{}` and the exact expected schema. No shared
`u/admin/offmenu_platform` get-modify-set operation exists.

Only identifiers, fixed codes/severity, hashes, timestamps and booleans persist;
never log bodies, commands, raw errors, arbitrary paths, data or credentials.
SDK/transport/persistence exceptions are translated to fixed safe codes. Incident
persistence failure never turns a failed business/check operation green.

The existing hourly delivery process can list this prefix and deduplicate by
resource path. Ignore `test:true`. Incidents are immutable observations, not a
claim an issue remains active: reconcile the same job/status before reporting an
old unknown outcome. No new email/Slack destination or hourly sender was added.

## Build and evidence

`python build_native.py` bundles the reviewed incident source, the explicit
baseline SSH transport snapshot and the check entrypoint. The snapshot retains
host-key pinning and bounded fair stream drain; no secret value is source code.
Run `PYTHONPATH=. python -m unittest discover -p 'test_*.py' -v` here.
`DEPLOYMENT-RECEIPT.json` records actual verification, not planned outcomes.
The incident and schedule probes are private test drafts, not scheduled services.

## Read-only hourly delivery lookup

Use the existing hourly follow-through process; this is not real-time push.

1. List resources with exact prefix `u/admin/offmenu_platform/incidents/` in
   workspace `offmenu`. Read only returned incident paths. Validate owner
   `admin`, type `state`, `extra_perms:{}`, format `offmenu-incident-v1` and the
   exact allowlisted schema before using the value. Do not enumerate/read
   variables, provider resources or arbitrary neighboring resource values.
2. Ignore `test:true`, `SELFTEST_*`, routine cancellation and busy/nonadmission.
   Dedupe by the immutable resource path using the delivery process's existing
   ledger, not by modifying incident resources. Deliver only actionable NEW
   observations once. An old observation is not proof a condition persists.
3. For a run-phase incident with `needs_reconciliation:true`, inspect the same
   logical job using the production client's `action=status` with the exact
   recorded `logical_job_id`. For health/verify incidents, inspect the recorded
   `windmill_job_id` and latest check result instead; `check-<UUID>` is not a
   host business-job ID. Do not retry `run`, clear a lock, mutate a checkpoint,
   or infer success from `transport_ok`. If outcome remains unknown, report
   reconciliation needed.
4. Health/check state lives in the bounded **run result**, not a new mutable
   health aggregate: list runs for exact script path
   `u/admin/offmenu_platform_check`, then inspect the selected run's sanitized
   result fields `mode`, `checked_at`, `status`, `ok`, `coverage`, `counts` and
   `findings`. Run success alone is insufficient: `status:incomplete,ok:false`
   is explicitly incomplete selected coverage. Do not include raw logs in user
   delivery. The baseline `u/admin/offmenu_platform` config remains read-only.
5. Schedule definitions are the two exact paths above. The setup-only private
   `u/admin/offmenu_schedule_probe` defaults to `enable:false` and returns
   validated definitions plus next queued UUID/due time, no credentials.

No new delivery automation, subscriber, Slack/email integration, recipient or
credential is created. User-facing alerts should contain a fixed code, logical
job/run reference and the needed reconciliation/action, not raw command output.

## Schedule activation semantics

In Windmill v1.850.0 an existing schedule's edit schema has no `enabled` field;
writing a draft with `enabled:true` does not prove operational activation.
The reviewed setup probe validates both fixed definitions before calling the
normal owner API `POST /w/offmenu/schedules/setenabled/{path}` with
`{"enabled":true}` only for currently disabled schedules. It never supplies
`force`; permission or fork-conflict refusal stops. Readback and queued due times
are required evidence. Re-running the read-only probe does not reset the queue.

Official version-pinned implementation: [schedule edit and enable schema](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-api-schedule/src/lib.rs).
The check script uses no Enterprise schedule callbacks or workspace handlers.

## One-off controlled negative-test annotation

The intentional production-client exit-7 test is an expected synthetic failure:

- Logical job: `platform-phase2-failure-smoke-20261027`
- Windmill run: `01a17f9b-e218-8b96-c7c4-6669a2df1857`
- Code: `BUSINESS_FAILED`; child cleanup was verified.
- Exact incident: `u/admin/offmenu_platform/incidents/fcf46db77fb467b1c727834d61ba0ea72fd9eb9893f9e76ccabcda9ce7f9a97a`

This exercised the real production failure path, so its immutable `test:false`
is intentional and must not be rewritten. The existing delivery ledger should
acknowledge **only this exact known validation incident** rather than send a new
business-failure alert. This is not a prefix-based ignore rule: all genuine
future failures and unknown outcomes remain visible. Health correctly treats
this safely cleaned-up historical failed workload as informational, not platform
corruption or an unresolved active process. The separate incident helper probe
is explicitly `test:true` and remains excluded normally.

## Scheduled owner identity and adapter versions

Windmill scheduled creators use `WM_USERNAME=schedule-...`; authorization is
`WM_PERMISSIONED_AS=u/admin`. The native incident adapter requires the latter
owner identity and workspace `offmenu`, plus creator `admin` or one of the two
exact reviewed schedule creator/path combinations and the fixed checker job
path. It does not accept arbitrary scheduled creators or change grants.

The native bundled adapter therefore has the newer scheduled-context guard.
The existing production business client embeds its earlier reviewed manual-owner
adapter and is not scheduled; do not claim these embedded adapter versions are
byte-identical. No core client or baseline helper replacement was needed for
this native scheduled-context correction.

For delivery, immutable incident paths prevent duplicate delivery of the same
observation, but scheduled checks can produce new observations of the same
ongoing condition. Coalesce check-phase incidents by fixed check script/mode and
reason code into one ongoing condition in the **existing delivery ledger**;
record seen paths but notify only a new condition, material change, or recovery
requiring attention under existing quiet rules. Different run-phase logical
jobs remain separate failures. Unknown/blocked attempts may be grouped under
the actual underlying unsafe-job marker when known, never guessed. This changes
neither immutable runtime incidents nor introduces a new alert service.

Scheduled resource attribution was checked against the official v1.850.0
implementation: [queued-job owner/token handling](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-queue/src/jobs.rs),
[owner JWT identity](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-common/src/auth.rs),
[API JWT identity](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-api-auth/src/auth.rs)
and [resource create attribution](https://github.com/windmill-labs/windmill/blob/v1.850.0/backend/windmill-store/src/resources.rs).
The authorized principal supplies resource `created_by`; these owner schedules
remain `admin`. The strict resource-owner check is intentionally unchanged.
