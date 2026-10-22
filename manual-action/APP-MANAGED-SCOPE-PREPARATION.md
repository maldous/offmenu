# App-managed profiles and inventory: external-ingestion scope correction

**Preparation only.** This patch is based on the exact reviewed 12-path
`offmenu-next-batch-20261022` source export (stored totals plus classified record
isolation), itself based on `af99cdfb4bac3bce9f4badae34333921a0074a76`.
The active run is not changed, stopped, inspected, or restarted. Promotion remains
held until the owning workflow establishes a safe exit boundary.

## Owner policy

`user_profiles` and `inventory` belong to application runtime. There is no
external/private dataset to fetch, solicit, or import for these domains. Existing
household admission flags do not opt them back into external ingestion.

This change is reporting/ingestion scope only. It does **not** implement, deploy,
or attest readiness of typed application schemas, encryption, migrations, or
application bindings. Those are separate deliverables. Existing schemas and data
are retained; no catalog assignment, stored record, source version, or cursor is
deleted or rewritten to make pending counts disappear.

## Behavior

- All eight domains remain in reports. The engine still opens each owned staging
  store under the existing ownership/single-writer rules, creates the existing
  schema if absent, and reports actual committed stored totals. Observed private
  zero is zero; a populated historical private store retains its nonzero total.
- Private-domain external adapters are bypassed before dispatch, including custom
  handlers and legacy explicitly scoped descriptors. The direct existing-source
  adapter also refuses to import private-domain sources. `schema_only` describes
  this ingestion path, **not** an assertion that a private store is empty or an
  actual app schema is deployed. `scope: app_managed` makes the distinction clear.
- Every historical private catalog assignment stays in the private queue detail,
  with its source identity/path/provider/disposition, `scope: app_managed`,
  `status: schema_only`, and `excluded_from_pending: true`. Its source is not
  opened, statted, or fingerprinted by pending-work collection. Mixed-domain
  descriptors retain their independent external-domain assignments.
- External pending totals exclude these assignments. The optional pending-work/1
  `scope` object has fixed policy `external_ingest_only` and exact
  `app_managed_assignments` counts for profiles and inventory. Current snapshots
  have no private awaiting-input domains or synthetic private-input requirement.
- Evidence retains catalog totals and domain mappings. Private assignments use
  the existing `unqualified` eligibility vector column plus explicit optional
  `domain_scope`; no vector length or existing enum is changed. Missing private
  source paths do not generate source-access or private-input requests. Cached
  evidence from the old policy is recounted from descriptors, not source data.
- Readiness diagnostics label empty private staging `schema_only_app_managed`;
  the prior label remains accepted for historical summaries. Console output does
  not solicit household data, including when handed a historical pending report.

## Protocol and custody

New scope extensions are optional and strictly validated. Historical pending-work,
evidence, and receipt canonical bytes are accepted unchanged; old status/action
enums remain for recovery, but current collectors no longer emit private-input
requests. No adapter-version bump, source-key change, cursor reset, download,
fetch activation, process-parser change, schema migration, database copy, source
upload, or deletion is introduced. Catalog discovery/assignment ownership remains
unchanged; only external-ingestion eligibility and reporting are corrected.

## Focused verification

Nine new generated-fixture tests cover 91 retained assignments, mixed mappings,
legacy scoped descriptors, private adapter/source access prohibition, actual
stored totals (two historical profile rows and zero inventory rows), unchanged
private records/source checkpoint rows, old canonical bytes, malformed extension
rejection, evidence-policy recapture, and non-soliciting console behavior.
Seven selected existing regressions cover private adapter behavior, pending
counters, eight-domain engine recovery, and worst finite supplement/receipt bounds.
Two additional generated-fixture checks exercise the root-run flow against local
bare Git and the staging-readiness label/legacy acceptance. No broad suite or
live-host diagnostic was run. Test results and exact source hashes are recorded
in `APP-MANAGED-SCOPE-SOURCE-MANIFEST.json`.
