# Normalization and diagnostic preparation — 2026-10-22

Source-only integration release. No retained datasets, private reports, source
payloads, review packets, caches, credentials or household records are included.

## Prepared capabilities

- Versioned, source-preserving normalization sidecars across eight domains;
  deterministic rules followed by an explicit actual-review receipt contract.
- Recipe/menu semantic templates, bounded review batches, reusable contextual
  translation units and conservative gold-candidate validation.
- Allowlisted ingestion error telemetry in existing checkpoint/receipt flows,
  with local private grouping and backward-compatible historical receipts.
- An isolated, bounded relational evidence reporter with exact source-scoped
  crosswalks and sanitized counts; it is not installed in the runner.

The common envelope schema is repository-root
`schemas/common-normalized-record.schema.json`; recipe/menu schemas are under
`manual-action/schemas/`. Detailed contracts and limits are documented in
`NORMALIZED-CORPUS.md`, `RECIPE-SEMANTIC-REVIEW.md`, `INGEST-ERROR-TELEMETRY.md`,
`RELATIONAL-READINESS.md` and `RELATIONAL-REPORT.md`.

## Evidence and limitations

The frozen source closure is validated with:

```sh
python3 -B -m unittest discover -s manual-action/tests -v
```

Result: 332 tests run, successful with one skipped optional dependency check.
All new data examples and review receipts are synthetic. The 33 relational tests
exercise terminal/no-WAL read boundaries, source immutability, exact namespaces,
ambiguity, reciprocal validation, private-scope checks and summary filtering.
Passing fixtures do not establish any retained corpus's acceptance or readiness.

No actual item review, translation, rights clearance, database provisioning,
application binding or live retained-data relational inspection was performed.
Private record export remains unapproved. Cross-database atomicity and
application readiness are not established by the report.

Error telemetry distinguishes retained all-version class/origin counts from
current-run callback reason counts; these populations must not be added together.
Historical reasons were not recorded. Synthetic findings do not diagnose the
live Foo error totals, and an already-running process is not hot-patched.

This commit does not alter `plan.json`, `run`, active ingestion settings or any
workflow. It neither auto-activates normalization/reporting nor dispatches an
Action, restarts ingestion or launches a fetch. The later user instruction to
add additional sources and fetch them separately authorizes acquisition; this
preparation does not revoke or gate that independently implemented workflow.
