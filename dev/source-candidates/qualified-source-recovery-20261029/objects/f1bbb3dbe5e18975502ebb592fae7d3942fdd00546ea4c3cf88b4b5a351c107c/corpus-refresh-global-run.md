# Global refresh assessment contract

Baseline: `2266e85046eb22d5baccba09149c0f3b70dadd25`.

## Read-only CLI

`python3 -B -m offmenu.refresh.global_run --matrix /approved/matrix.json --ledger /approved/ledger.json --compact`

The coverage loader verifies the exact retained inventory pins. This command
reads metadata only. It does not read source bodies, fetch landing pages, start
Foo work, change accepted pointers, or run national adapters. Source paths must
be registered separately before adding this operation to a runner profile.
No caller-provided URL or dynamically imported plugin is supported.

Default stdout is the comprehensive JSON assessment. `--compact` emits a closed
summary under 2 KiB suitable for bounded control logs. Its `reportSha256` and
`reportBytes` describe the comprehensive report encoded as UTF-8 JSON with sorted
keys, comma/colon separators, and no trailing newline. Full reports belong on
Foo, not GitHub or shared control logs. `--output /approved/foo/report.json`
streams canonical JSON to an exclusive output file and emits only compact stdout.
Existing files and symlink paths are rejected. Serialization and digesting are
incremental, avoiding a second giant JSON string; the bounded report object remains
in memory (maximum 4,096 source jobs). No full global report was written in cloud
tests, only tiny synthetic writer fixtures. The CLI returns 2 for incomplete coverage
or invalid metadata. Assessment completion and dataset completion are separate.

## Exhaustive reporting

Every assessment includes all 249 ISO countries, all 13 required domains
(3,237 cells), every registered discovery source and all nine execution stages:
acquire, verify, parse, normalize, validate, curate, graph, qualify and accept.
Unbound sources are explicitly unsupported. Holds stay held even when a caller
requests force-download or local rebuilding. A failed stage blocks its dependents
while independent sources continue. Exception details are excluded from receipts;
fixed diagnostic codes remain available. Unknown counts stay null.

Recovered metadata includes 22 retained release descriptors, 23 discovery-to-family/domain
mappings and historical handler evidence for 22 discovery entries. This evidence is
retained separately, including historical counts and the CNF 2026/2015 release mismatch.
There are still no admitted executable bindings or current acceptance receipts. Therefore
all country/domain cells remain unassessed, and no global dataset completion is
claimed. Landing-page HTTP 200, a download candidate, native extraction, synthetic
fixtures and a successful source pipeline do not establish country acceptance.
Fineli access/zero semantics, the unresolved historical Norway/France replay
restrictions, and Danish semantic/curation boundaries are preserved. Production
and CIX remain paused.

## Trusted stage integration

`run(coverage.assess(matrix, ledger), bindings=...)` accepts reviewed code-supplied
`Binding` objects. No production bindings ship in this patch. Each binding needs
reviewed admission and an explicitly verified resource/isolation boundary. Stage
callbacks receive a frozen `StageContext` and return `StageResult` containing
fixed status/code, content-addressed evidence references, and an optional count.
Success without evidence is rejected. Binding admission is an internal contract,
not a replacement for operation-specific source rights or permissions.

Each source is scheduled once regardless of how many countries reference it.
Output order is independent of completion order. At most four source jobs are
submitted concurrently; memory reservation may lower that cap. Input/output/time
limits are supplied to adapters. The coordinator is deliberately not an OS
sandbox: adapters must enforce these limits in subprocesses and enforce offline
network denial for interpretation. No unverified boundary is dispatched. A stuck
callback cannot be safely killed by Python threads; such callbacks must never be
bound directly. The existing replay engine owns its immutable cache, locks,
checkpoint/resume and publication recovery; the harness does not replace it.

Acquisition policy is passed only to the acquisition stage. Local force-rebuild
is passed only to subsequent stages. The acquisition adapter implements reuse,
refresh, revalidate and force-download, including the minimum 30-day default
reuse policy. Force rebuilding never forces network refresh. Explicit revalidate
or force-download still cannot override holds or retention/use restrictions.
Acquisition defaults to 64 MiB/180 seconds. A separately reviewed streaming
acquisition binding may reserve up to 1 TiB/600 seconds via `acquire_bytes` and
`acquire_wall_seconds`, using the acquisition module’s explicit `ResourceBudget`
and verified Foo storage policy. A configured path is not proof of the host.
This does not raise the separate parser input cap (64 MiB), admit an endpoint,
expand archive processing, or create a production binding.
Network counts remain unknown for bound adapters until measured receipts are
wired in; no zero-request claim is inferred from a requested policy.

## Verification and remaining work

Focused synthetic tests cover exhaustive cells, deterministic ordering,
independent failure continuation, holds, missing handlers, evidence requirements,
bounded concurrency/memory reservations, invalid registries, immutable stage
context and local rebuild/network separation. They do not validate any live
national data, network acquisition campaign, OS isolation boundary, production
binding, or full corpus completion.

End-to-end execution still requires reviewed release/domain/applicability
bindings, source-specific acquisition/interpretation rights, verified retained
assets and dictionaries, bounded isolated adapters, actual qualification evidence
and separate acceptance. No number of discovery rows can substitute for these.
