# Global coverage assessment

## Scope and evidence

The metadata-only `offmenu.refresh.coverage.assess(matrix_path, ledger_path)` is deterministic and has no HTTP client, adapter execution, scheduling, acceptance or publication operation. The large inventories stay on the selected local executor. Only compact code, pins and historical handler descriptors are checked in.

Exact inspected baseline: `2266e85046eb22d5baccba09149c0f3b70dadd25`. The frozen country matrix is 133,210 bytes, SHA-256 `894e05f09744c76b790f8e5f159141bed6c308a9af3d90c3c82aa79105cf5ea8`; the source ledger is 1,701,843 bytes, SHA-256 `2f3c917a6463153824b8c807b41707870e7f763c65b5ff7957ec4988cd96bfcf`. Missing or different inventory bytes fail closed. No fallback source URL generation is supported. Supply the exact matrix and source-inventory paths on the selected executor. Historical directory names do not establish that those files are available.

The 249 ISO entries and 13 required domain names yield 3,237 country/domain cells. All 1,303 discovery records originally represent landing-page access checks. Historical counts remain 1,040 HTTP 200s, 182 sources with download candidates and 456 sources with rights links. These never establish payload availability, current rights or completeness.

The compact `capabilities.py` reconciles all 22 retained releases from `corpus/common-source-mappings.json` (Git blob `858c4de5f6e27deb049ee8bc27567a40461bad49`). It records 21 historical collector/normalizer implementations, 23 discovery-to-source-family/domain mappings and 22 discovery entries with historical handler evidence. The remaining 1,281 discovery entries have no handler evidence in this compact registry. This does not claim no other code exists; it states the evidenced mapping coverage. Source-family matching is not proof that a discovery API and retained release share format or scope. In particular the Canadian discovery entry describes 2026, while the retained CNF parser handles 2015.

The current physical location of that mapping is
`contracts/corpus/common-source-mappings.json`; the cited blob above retains its
historical source identity.

Every retained release includes its source ID, release, historical count, canonical types, scope, parser path and inspected Git blob when available. None is an executable binding. National domain links are only attached where both country linkage and handler country scope agree. Global routes are kept separate and never multiplied into all countries. No country acceptance or fresh payload verification was performed.

## Historical capability priorities

1. Recover exact existing cache manifests, acquisition receipts, dependency locks and output hashes for the retained releases. AFCD and Japan have both the original collectors and preserved qualification sidecar implementations; these are preferred evidence to inspect before designing replacement parsers.
2. Preserve NO/FR native crash restrictions and Fineli force-download/zero-interpretation holds. The Danish four-definition basis/curation boundary remains. Production and CIX stay paused.
3. Reuse the eight-source private v2 observation normalizer only within its exact adapter pin contracts. Its existence does not grant acquisition, source acceptance or cross-source semantic equivalence.
4. SourceProposalLookup is an exact pinned lookup over 88 external proposals: 14 DOSM CPI division labels and 74 Fineli component terminology proposals. No canonical, translation or semantic equivalence acceptance follows. CPI is not a retail price/basket dataset.
5. `apps/web/server/cache-invalidation-owner29.mjs` handles bounded D1 resolver envelopes and policy/dependency epochs. It is not an immutable raw-dataset cache or a national-source acquisition handler. Its adoption boundary remains explicit.
6. Complete exact source/release/endpoint binding, original asset set, rights-by-operation and pinned normalization contract for the eligible sources. Registration of remaining discoveries can remain explicit unsupported records while independent permitted sources progress.

## Required next bounded local executor assessment contract

The assessment must report the full registered source universe, not only the first cache hits. It may inspect only currently approved accessible roots. Report a missing/inaccessible root as such; do not expand mounts or follow symlinks. No source-body download, held parsing, native NO/FR replay, production activity or scheduler changes are implied.

Use one explicit UTC `observedAt` for the report, supplied by the caller. For every source, emit independently:

- Source ID, country links, domain links, source family/release, handler code pin and scope, plus whether the binding is historical evidence or executable admission.
- Every available cache asset metadata reference and original receipt pin, expected versus observed asset-set reconciliation, digest-verification state and incomplete/depth/entry-limit reasons. Filename recognition and file size alone are candidates, never verified cache hits.
- Original `acquiredAt`, `validatedAt`, expiry/TTL and validator provenance when present. Compute age against `observedAt`; missing/future/invalid receipt times remain unknown. File mtime is not acquisition time or freshness.
- Acquisition status: not requested, blocked, missing, retained candidate, verified reuse, stale, or failed. Reuse and avoided downloads need observed exact hashes, representation identity, permissions and receipt evidence. This read-only batch reports `downloadReused: null` when no actual reuse operation occurred.
- Rights for discover, fetch, retain, parse, transform, serve and redistribute separately; unresolved terms remain blocked for the affected operation.
- Normalization status, existing output digest, source/dependency/adapter/dictionary/schema/runtime pins, retained row-count claims, observed validation and quarantine/hold reasons. Existing output or historical counts do not mean normalization ran in this assessment.
- Structured errors with stage, source, retryability and concrete missing input. One source failure must not suppress later independent sources or the final 249-country report.

Include aggregate counts that reconcile to all 1,303 registered discoveries plus a separate retained-release view. Every one of the 3,237 required country/domain cells remains explicitly unassessed, partial, held or qualified from independent acceptance evidence; discovery counts cannot advance it. Per-source family mappings and historical outputs remain visible even where current accepted scope is unestablished.

## Current blockers and stopping boundary

Current approved runner-accessible matrix/ledger paths, cache-acquisition manifest paths, full cache metadata and retained acceptance sidecars have not been established by this code inspection. The inventory loader is ready; it is not evidence that a running local executor container has those paths. The next read-only job should expose these precise missing inputs and runtime limits while preserving all independent observations. Broad source refresh requires reviewed endpoint bindings and retention/normalization rights; the generic acquisition transport currently admits zero production endpoints by default.

This deliverable has seven synthetic tests plus successful metadata-only reconciliation against the exact baseline files. It performs zero publisher requests and reads zero raw dataset bodies. Bulk runtime reports and inventories are not included in the repository artifact set.
