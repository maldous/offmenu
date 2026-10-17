# OffMenu reproducible dataset refresh design

Recommend one Python CLI over a small package of reusable source adapters, an immutable artifact cache, and a local SQLite run ledger. Keep acquisition online and replay offline. Existing normalization, curation, graph alignment and validation should become explicit stages with pinned inputs. Ordinary refresh can run without AI or agent sessions. A giant script or a new management coordinator would make the existing fragility harder to remove.

This is a design for Morgan to review. Gateway routes decisions and retains evidence. Country workers, source custodians and their results retain their existing roles. No implementation, held-source processing, test execution, publication, commits or deployment is part of this task. Inspection used source code, JSON metadata/manifests, directory listings and retained receipts; source bodies were not parsed. Primary engineering documentation was consulted separately from source acquisition.

## Existing reusable code and evidence

Pointers below refer to `/home/user/src/offmenu`, observed at HEAD `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. The shared checkout has pre-existing tracked and untracked changes. `evidence.json` pins inspected code and key metadata; a pointer is evidence of inspected behavior, not an execution claim.

| Mechanism | Exact pointer | Reuse and limitation |
| --- | --- | --- |
| National normalization | [collect-national.py](/home/user/src/offmenu/scripts/collect-national.py:12), functions `ciqual`, `norway`, `frida`; `publish_local` at 60; `main` at 73 | Local XLSX/XML/JSON readers; food/component identities, native units and metadata; six fixed releases including imported AFCD, BLS and CoFID readers. No fetcher. Input-file SHA manifests and duplicate-ID checks; resume verifies retained raw hashes, not code/config/output hashes. |
| Numeric and identity helpers | [import-national-tables.py](/home/user/src/offmenu/scripts/import-national-tables.py:9), `numeric`, `wrap`, `bls`, `cofid` | Null, trace, not-detected, not-tested and limit qualifiers; namespaced native IDs. CoFID duplicate codes are disambiguated with a name hash at 70–73, so corrected names can change identity. `wrap` injects the current time. |
| Additional national formats | [collect-next-national.py](/home/user/src/offmenu/scripts/collect-next-national.py:14), `table`, `fineli`, `foodfiles`, `sweden`, `CONFIG`, `collect` | Strict delimited-row width, Fineli multilingual relational joins and bibliography continuation, source matrix distinctions in FOODfiles, Swedish edition/basis checks. Verifies selected archive hash but reads extracted files before that check; archive-to-extraction closure is not independently pinned. |
| Local table checkpoints | [collect-usda.py](/home/user/src/offmenu/scripts/collect-usda.py:27), `save` and `collect`; [normalize-usda.py](/home/user/src/offmenu/scripts/normalize-usda.py:35) | Archive hash, transaction per CSV table, row counts and atomic metadata replacement; changed archive refused. Normalizer verifies an existing output digest and uses streaming ordered joins and a partial output. Not a generic acquisition/retry system. |
| Bulk projection and quarantine | [collect-jsonl.mjs](/home/user/src/offmenu/scripts/collect-jsonl.mjs:15) | OFF/Open Prices normalizers and record validation from `public/unified-data.js`; complete price-related inputs, duplicate/exclusion/quarantine accounting; staging directory renamed after completion. Cache resume is not keyed by related-file hashes or normalizer version. Existing partial output is removed and restarted. |
| Large columnar sources | [collect-overture.py](/home/user/src/offmenu/scripts/collect-overture.py:36) | Pinned Parquet and licence digests, DuckDB/PyArrow selection, bounded memory, source identities, reconciliation and partial directory. Useful later for scale; not necessary for the first pilot. Partial staging reuse is not a generic safe-resume contract. |
| HTTP and cached pages | [collect-source-access.py](/home/user/src/offmenu/scripts/collect-source-access.py:6); [collect-world-recipe-wikis.py](/home/user/src/offmenu/scripts/collect-world-recipe-wikis.py:6) | Landing checks use eight threads and permanent per-source files, explicitly not ingestion. MediaWiki has four project workers, cached API pages, continuation/revision batches, timeout and selected HTTP retries. Filename cache has no general TTL/validator/force semantics; project concurrency is not a global host budget. |
| Curation and serving build | [build-curated-corpus.py](/home/user/src/offmenu/scripts/build-curated-corpus.py:74); [curation.py](/home/user/src/offmenu/corpus/curation.py:26); [policy.json](/home/user/src/offmenu/corpus/policy.json) | Local SQLite index; source whitelist, public/private checks, count reconciliation, checked notices, withheld reasons and explicit projections. Stable hashed record IDs; source-record references retained. Dense search posting IDs are build-local and depend on input order. Raw/curated/held counts already differ intentionally. |
| Common graph alignment | [align-national-common.py](/home/user/src/offmenu/scripts/align-national-common.py:177), `curated_records`, `graph`, `align` | Source-scoped URNs, typed values, original source paths, citations, locales, nulls, schema/identity/scope validation; deterministic gzip `mtime=0` at 317. Reads curated public shards, not full native archives. Fixed data roots and eleven source releases. |
| Validation and acceptance | [exercise-collection.mjs](/home/user/src/offmenu/scripts/exercise-collection.mjs:21); [exercise-curated-corpus.mjs](/home/user/src/offmenu/scripts/exercise-curated-corpus.mjs:11); [qualify-common-expansion.py](/home/user/src/offmenu/scripts/qualify-common-expansion.py:95) | All-record structural and synthetic consumer checks; checksums, joins, recipe gates; graph qualification uses disk-backed IDs and explicit admission/coverage requirements. Structural success is not semantic or rights acceptance. Curated exercise currently rewrites its input manifest at 30. |
| Registry and coverage | [country-delivery-matrix.json](/home/user/src/offmenu/docs/country-delivery-matrix.json); [source-delivery-ledger.json](/home/user/src/offmenu/docs/source-delivery-ledger.json); [report-country-execution.py](/home/user/src/offmenu/scripts/report-country-execution.py:7) | Verified 249 distinct country codes, thirteen domain defaults and 1,303 registered source entries. Existing reports distinguish source assertions from country completeness. Reporting script still embeds a release list and dated access-report path. |
| Contract and tests | [common-data-contract.json](/home/user/src/offmenu/corpus/common-data-contract.json:702), `common-data.schema.json`, `recipe.schema.json`; `tests/test_collection.py`, `test_next_national_collection.py`, `test_national_common.py`, `test_curation_projection.py`, `tests-web/curation.test.mjs` | Reuse typed source semantics, unknowns, separate rights and reviewed crosswalk rules. Existing fixtures cover CSV checkpoints, malformed rows, foreign matrices, language typing, projection and LF/gzip handling. Tests were inspected, not run. |

[pyproject.toml](/home/user/src/offmenu/pyproject.toml:5) already exposes `offmenu`, but its CLI is pantry/import oriented. Packaging includes `offmenu*`, not the `scripts` and `corpus` dependency tree. `collection` omits `openpyxl` and `jsonschema-rs` used by these scripts; these are in `test`. Python runtime is only `>=3.10`, setuptools is lower-bounded, and there is no inspected complete Python/transitive/runtime lock. Pin Python, SQLite, zlib and Node too where legacy JS stages are retained.

## Specific gaps to close

1. There is no single registry-driven refresh entry point connecting permitted discovery/acquisition, snapshots, normalization, projection, alignment, qualification and accepted output. Scripts already support much of the data work, but each assumes particular directories/releases.
2. `collect-national.py:75` expects a `matvaretabellen` input subdirectory. The retained bundle is `/home/user/src/offmenu-data/national-originals/norway`, with `en-foods.json` and its companion files. Its main also processes all six sources, so simply wrapping the existing invocation does not provide isolated country/source selection.
3. Hashes mean different things in current manifests: a single archive digest, an aggregate of directory-file metadata, or acquisition JSON. Name these distinctly. In particular, directory-wide hashing admits incidental files as dependencies, while archive-only hashing does not establish the integrity of already extracted files.
4. `import-national-tables.py:24`, `collect-national.py:67–70`, `collect-next-national.py:93–101`, `collect-jsonl.mjs:35,63`, `build-curated-corpus.py:57,200,232` introduce runtime timestamps or gzip metadata. `index-curated-countries.py:35,42` does too. Parallel completion order and positional workbook mappings also need explicit controls.
5. Current resume often proves only that a manifest exists or raw input matches. It does not prove output bytes, adapter/dictionary/schema versions, related inputs or stage completeness. Creating an output directory early can leave an unresumable failed target. Assertions used as gates must become explicit exceptions so optimized Python cannot disable them.
6. `align-national-common.py:325–357` compares counts to the curated source manifest, but several expected/observed coverage fields are assigned from the same observation. Shards are read without independently checking every input digest there. Require an independent input lock and expected asset set. Its `complete=true` concerns that selected package only.
7. Normalization and acquisition are not uniformly separated. For example `collect-business-references.py:14–40` may fetch country mappings and missing labels during normalization. All such lookup responses must become explicit pinned acquisition inputs for offline replay.
8. Publication projections intentionally suppress facts. Fineli's retained manifest has 4,238 native profiles; the retained curated release has 4,232 and six withheld profiles. Native preservation, curated projection, graph packaging and country completeness need separate accounting. No wrapper should route full raw records through the public aligner to evade projection.

## Danish candidate and worker evidence

Read [composition-receipt.json](/home/user/Documents/Codex/2026-10-17/offmenu-dk-m002-composition/composition-receipt.json), the exact local commit `dfc1777dcb61c2e550529a9394e3d31975c2732c` on base `922ab2d3f0cb56f0b034752f13b24c391b14744a`, and the two script files in `/tmp/offmenu-dk-m002-922-20261017`. Their hashes match the receipt: collector `378ba12f8fcc59a2f560b6516f142b59e1e0b5d317db414f72b662facd9a2ae0`; aligner `e8f543e8c241bd8edb01a099e63f89e88da91703298645cbed45c3f36110da3f`.

The patch preserves literal units/matrix codes for Frida definitions 363, 12, 135 and 203 and makes their common graph quantity unknown without an inherited profile basis. The unchanged curation whitelist suppresses these source-specific keys; affected-only profiles are withheld. The receipt reports 89 Python groups plus eight caller groups, 97 synthetic checks, and zero fetched/real-parsed/real-normalized/gold records. Composition/runtime results were not independently accepted in that receipt. Do not label it an adopted fix or infer that the live/public path exposes all four definitions. Preserve its exact bytes and tests as candidate regression evidence; adoption requires Morgan's selection and the existing review lane.

The [all64 export](/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/renewed-all64-followthrough/owner57/concise-all64.md:3) explicitly says evidence and worker proposals are not assignments or permissions. Its cut is 4684, so the later Danish composition receipt is a separate newer artifact. Worker49's FI entry reports 53,654 zero-value holds; Worker27 retains DK dictionary/basis gaps; Worker57 says HICP indices/rates are not retail prices or baskets. These are examples of enduring semantic boundaries, not reasons to repeat completed reviews. Worker IDs are evidence labels, not reusable runtime actors.

## Proposed package and stage contract

Add a reviewed `offmenu.dataset` package behind `offmenu dataset ...`; retain the existing CLI interface and scripts through compatibility wrappers. This is proposed functionality. Use small modules for registry, acquisition/cache, adapters, snapshots, stage execution, validation and manifests. Avoid a network service, AI coordinator or per-country script generator.

Use this dependency graph:

```text
online: policy and source plan -> acquire or import -> immutable raw bundle + receipts
offline: input lock -> verify -> parse -> normalize -> validate -> curate -> validate
                                                            -> public graph -> qualify
          -> deterministic content manifest -> separate acceptance -> local accepted pointer
```

Native normalized data stays in its permitted scope; public graph input comes from the permitted curated projection. Native-only companions keep a separate manifest and never enter the public branch implicitly. Existing source-specific semantics remain adapters, not a generic column-position inference engine.

Split transport from interpretation. HTTP files, publisher export operations, paginated APIs, and local/manual imports can share transport code. XLSX/XML/CSV/JSON readers can share syntax helpers. Matvaretabellen, CIQUAL, Fineli, Frida and each economic-statistic family still require versioned domain adapters and reviewed dictionaries. Country configurations select source/dataset/release, roles, explicit applicability/filter, language, rights profile, credential reference, TTL and adapter config. One global source acquisition can serve several country configurations; do not fetch it 249 times or infer country applicability from language, nearest neighbor, company registration or a global route.

The offline stage receives paths by immutable digest and has no HTTP client or credential capability. Reuse legacy Python/Node stages through explicit inputs first; remove hardcoded globals as a later reviewed refactor. Offline workers must fail on an undeclared dependency rather than resolve it online.

## Registry and honest completeness

Seed all 249 rows from the existing country matrix and attach existing source ledger IDs, retained result/rights references and exact applicability. Preserve historical worker evidence additively; do not make current ledger labels executable instructions.

Keep three distinct axes: adapter capability (`supported`, `manual-import`, `unsupported`, `unassessed`); source operation status (`fresh-cache`, `unchanged`, `acquired`, `failed`, `blocked-access`, `blocked-use`, `blocked-credentials`, `held-semantics`, `quarantined`); country/domain evidence (`unassessed`, `partial`, `accepted-scope`, `no-qualified-source`, `not-applicable` with evidence). Store operation-specific authorization for fetch, retain, parse, derive and export; permission for one does not imply another.

Every release completeness manifest lists all 249 countries, each domain and applicable sources, expected/observed input assets and counts, accepted/withheld/quarantined counts and reasons, missing releases, freshness, carried-forward snapshots and acceptance references. Separate `executionComplete`, `selectedScopeComplete`, `registryComplete` and `countryCoverageComplete`. Successful execution must never imply complete national coverage. Do not report 0 when a count is unknown; do not drop unsupported countries from the denominator. The CLI should return an incomplete/degraded exit status for unmet requested required sources while still producing a machine-readable report. An explicitly permitted-partial run can complete with enumerated limitations.

## Immutable snapshots and cache semantics

Store exact response/file bytes once by SHA-256 within the permitted rights/security scope. Restricted scopes must not share a public content-addressed store. Immutable bundle manifests bind source ID, publisher release, requested/final locator, request representation, raw body/member hashes, required dictionaries/notices, source coordinates, operation/use decision and acquisition receipt references. Store selected HTTP metadata and validators, capture method, continuation/revision list and any consistency limitation. An ETag is an opaque validator, not a content digest. A 304 can only revalidate the matching retained representation; a missing/corrupt body requires an allowed full retrieval or an explicit failure. [HTTP semantics](https://www.rfc-editor.org/rfc/rfc9110.html#section-8.8.3), [cache validation](https://www.rfc-editor.org/rfc/rfc9111.html#section-4.3.4).

A manifest alone cannot reproduce missing bytes. Keep a verified backup of permitted snapshots, code/runtime artifacts and dictionaries in an independently recoverable location under the existing custody rules; local storage is sufficient for the pilot and no cloud workflow is implied. Test recovery without `runs.sqlite`. Retention expiry or withdrawal can remove access or require deletion: retain an allowed tombstone/evidence reference and fail replay clearly, rather than treating immutability as perpetual permission.

Use separate modes:

| Proposed mode | Behavior |
| --- | --- |
| `--fetch-policy reuse` | Reuse a verified permitted fresh cache entry; never makes a network request. Report stale/missing rather than silently refreshing. |
| `--fetch-policy refresh` | Honor reviewed TTL and HTTP cache constraints; reuse while fresh, otherwise conditional request with retained ETag or Last-Modified. Without a validator, retrieve the permitted full representation. |
| `--fetch-policy revalidate` | Revalidate now even inside TTL. Conditional validators remain enabled; unchanged 304 or identical downloaded SHA reuses content. |
| `--fetch-policy force-download` | Bypass local freshness and omit conditional validators; request a full allowed response, then hash/deduplicate. It does not guarantee changed content or force an origin behind every intermediary. |
| `build --offline --rebuild` | Recompute from the exact input lock with networking denied. No source refresh; no credentials. A missing dependency fails. |

Default TTL is source-configured, bounded by applicable HTTP directives and reviewed use/retention policy. `no-store` or denied retention cannot feed a durable raw cache by default. A named immutable publisher release and a mutable “latest” locator need distinct records. Keep acquisition/revalidation times in an append-only evidence log; a 304 does not mutate old raw snapshots or their fetched time. A source publication/observation time that changes factual meaning is a pinned data input, not a build timestamp.

Request-cache key: source/dataset, adapter acquisition version, exact method/URL/query/body digest, representation headers including relevant Vary values, nonsecret authorization scope/market and policy fingerprint. Do not sort a query in a way that changes publisher semantics or key by the URL alone. Never store access tokens, cookies, signed secret URLs or secret header values in manifests; use redacted locators plus restricted references. Build key: canonical input content inventory + parser/normalizer/curator code digest + configuration/registry selection + schemas/contracts/dictionaries + pinned runtime + stage parameters. Changes invalidate only dependent stages. Acquisition receipt IDs and operational times remain sidecar evidence so no-change validation does not change semantic build keys.

`force-download` cannot retry recorded no-retry/challenge holds, bypass authentication or use restrictions, switch to another source, convert indices into prices, reinterpret zeros or fill missing bases. Fineli's retained [acquisition receipt](/home/user/src/offmenu-data/originals/next-national-20261013/acquisition.json) records “Official browser download; terminal request forbidden.” Keep its acquisition capability manual until a separately reviewed route changes that restriction. Record credentials by reference such as `credentialRef: provider-profile-name`, with operator-supplied secret resolution; no secret values in config, cache keys or logs.

## Reproducibility identity and safe writes

Lock complete code/dependency closure, Python/Node runtime, SQLite/zlib versions, dictionaries/ontologies, schemas, policy and configuration bytes. Keep artifacts available locally for network-disabled installation/replay or use a pinned pre-provisioned environment image. Set declared locale/timezone and encoding, reject NaN/infinity, fix numeric serialization, and sort sources, file inventories, unordered maps/sets, bundles and postings by documented keys. Preserve semantically ordered lists, source literals and original coordinates. Use deterministic gzip with fixed mtime, no path/filename leakage and pinned compressor. [Reproducible build definition](https://reproducible-builds.org/docs/definition/), [timestamp guidance](https://reproducible-builds.org/docs/timestamps/).

Preserve existing namespaced native IDs and curated hashes. Do not use run IDs or completion order for logical IDs. Dense search entry numbers are deterministic within a release, not stable identities across releases. Assert no hash collisions. Add reviewed migration/alias handling for corrected source IDs and CoFID name-based disambiguation; never silently merge equal names. Version observations/citations as necessary to distinguish revisions while retaining a stable source entity identity. Adoption of any changed ID scheme must preserve old accepted snapshots and reader compatibility.

Emit a canonical content manifest with relative paths, exact bytes/SHA-256, stage keys and count/coverage declarations. Exclude current wall-clock start/end times, logs and scratch DB files from the defined reproducible artifact set. Keep true source dates and pinned acquisition provenance. Write immutable qualification/acceptance sidecars referencing the exact content-manifest hash rather than rewriting it. Distinguish a content tree digest from a receipt digest and from optional decompressed-record semantic digests.

Build in a unique staging directory on the same filesystem. Verify all content, flush files and directories where supported, then finalize the immutable release and atomically replace a small local pointer. Repeating the same stage key verifies the prior accepted outputs and reuses them; a conflicting output digest is an error. Use a single local finalizer/lock so concurrent runs cannot overwrite each other's pointers. `os.replace` alone is not a transaction across all files and SQLite, nor a power-loss durability guarantee. Record intent, durable artifact completion and pointer transition separately; recovery verifies a finished manifest before repairing ledger/pointer divergence. Keep the old accepted pointer on validation or required-source failure.

## Parallel execution retries and resume

Use bounded I/O threads for acquisition and bounded processes/subprocesses for CPU-heavy parsing. An initial configurable limit of four requests total and one per host is adequate for the pilot; stricter source budgets win. Limit memory, open files, response bytes, decoded size, scratch space and queued work too. No task corresponds to a country worker/agent. Shared source jobs are deduplicated by acquisition key.

Keep mutable operational state in local SQLite on foo, with a unique job/stage key, attempt history, lease/owner token, input/output hashes, completed partitions and next eligible retry. Prefer one writer loop with short transactions and busy timeout; parallel workers return artifact receipts. SQLite WAL permits concurrent readers but only one writer and requires same-host storage, so do not put run state on a shared network filesystem. [SQLite WAL](https://www.sqlite.org/wal.html).

Use finite connect/read/overall deadlines, retry budgets and exponential backoff with jitter for explicitly retryable timeout/429/selected 5xx failures. Honor Retry-After, including its date form; a value beyond the run budget checkpoints a future eligible time rather than being shortened. Treat denied access, source-use holds, challenges and recorded no-retry states as terminal blocked outcomes. Publisher export POSTs require an adapter-specific retry safety decision. Handle redirects and credential scopes explicitly.

Checkpoint only complete, verified file/member/page partitions. On restart, validate stage version and input lock and rehash outputs before reuse; expire dead leases safely. Resume byte downloads only with publisher-supported Range plus a matching strong validator and checked Content-Range; otherwise restart the object. Paged acquisition must pin source snapshot/revision/cursors or disclose non-atomic source consistency. Never append a new live page sequence to an older mutable snapshot and call it complete.

Independent sources can finish when one fails. The candidate report exposes failure and freshness; an optional carried-forward source must cite its old accepted snapshot and stale status. Never mix failed/truncated new data into an accepted source, turn missing sources into zero rows, or advance a required complete-release pointer on partial failure. The database is recoverable operational state; immutable manifests and receipts remain sufficient to audit/replay without a running agent.

## Validation and semantic drift quarantine

Reuse existing structural/schema and all-record consumer checks, then add adapter contracts for file/sheet/table/header sets, key uniqueness, joins, source release, unit/matrix/denominator, language and expected finite scope. Compare with the last accepted source snapshot: row/key additions/removals, missingness, value/qualifier distributions, units, dictionary codes, release/rights text and withheld counts. Thresholds must be source-specific and versioned; new units, bases, definitions or rights always produce a held candidate rather than an automatic inferred mapping.

Schema drift and parse failure quarantine an entire incompatible source snapshot by default. Row-level quarantine is permitted only by the reviewed adapter contract, with complete raw/accepted/duplicate/excluded/quarantined reconciliation. A passing schema is not semantic equivalence. Preserve raw values/qualifiers; distinguish literal 0, missing, trace and less-than. New definitions remain source-scoped or withheld; crosswalks, densities, yields and basis conversions require reviewed evidence. Old accepted outputs remain readable and are never overwritten by a quarantined refresh.

## Proposed pilot and acceptance tests

Start with Norway JSON and CIQUAL XLSX/XML replay, plus Fineli CSV and access/semantic holds as a boundary case. Use the exact retained releases below; rights/operation/dictionary selection must be made through the existing lane before any future body processing. No new national acquisition campaign is needed.

| Source | Existing retained inputs and code | Pilot use |
| --- | --- | --- |
| Matvaretabellen 2026 | `/home/user/src/offmenu-data/national-originals/norway/`, `national-originals/acquisition.json`; `collect-national.py:norway`; normalized manifest reports 2,121 profiles | Multilingual JSON bundle, related dictionaries and sources, dependency closure and no-change refresh. Retained en-foods SHA is `89b8f5f494a79731bf7d8d98065ee66c55263ccdbb519e7c87941218be6c948d`; no claim that live ETag support was tested. |
| CIQUAL 2025 | `/home/user/src/offmenu-data/national-originals/ciqual/`; `collect-national.py:ciqual`; normalized manifest reports 3,484 profiles | XLSX plus XML identity reconciliation and positional-column drift detection. Workbook SHA `2c3495c8136d17356c50db410918da2102cb28096cb497c9cdf83c5f8ecb10ba`. Keep all supporting files and exact selected table contract. |
| Fineli 20.0 | `/home/user/src/offmenu-data/originals/next-national-20261013/fineli-basic2.zip`; `collect-next-national.py:fineli`; existing synthetic fixtures | ZIP/CSV parser structure, multilingual dictionaries and bibliography; archive SHA `e7e6bd8d4b9261d751229e763dad436b297d36d48fe853faf49e1fd2a116d262`. Actual zero interpretation remains held. Use metadata and existing synthetic fixtures until permitted replay is explicitly selected; force-download must remain blocked. |

Add the retained Danish synthetic composition fixtures as a regression boundary only. Do not rerun actual Frida bodies or expand four-definition schema/curation semantics as part of an infrastructure pilot.

Design these acceptance tests now; execution belongs to the later approved implementation/pilot:

| Test | Required observable result |
| --- | --- |
| Two offline builds | Fresh separate output roots and caches, identical locked permitted inputs/code/runtime, OS-enforced networking and DNS denial, no credentials, `--rebuild`. Equal path sets, bytes and SHA-256 for every declared normalized/curated/common content artifact and canonical manifest; consumer results equal. Compare decompressed semantic digests additionally. Logs/operational timestamps are explicitly outside content scope. Vary work directory and process scheduling to catch path/order leaks. |
| Cache hit and no change | Fresh permitted entry causes zero outbound requests. Expired/explicit revalidation sends matching validators to a controlled HTTP fixture; 304 and 200-with-identical-body both retain the same blob/build hashes, produce new evidence only, and make no pointer-content change. Reproduce key changes for language/Vary/auth scope so representations cannot cross-contaminate. |
| Forced behavior | `revalidate` ignores local TTL but sends validators; `force-download` omits them and performs a permitted full request even if fresh. Same body deduplicates; changed body creates a new candidate. A 304 with absent/corrupt/mismatched retained representation fails or performs an allowed full retry. Fineli/manual and no-retry holds produce no HTTP request in either forced mode. |
| Interrupted and retried run | Kill after one download, one parsed partition, after artifact finalization and during pointer/ledger transition. Resume under the same lock verifies completed artifacts and recomputes only incomplete/corrupt work. No duplicates, accepted truncation, concurrent pointer overwrite or loss of old accepted output. Inject 429/date Retry-After, timeout and retry exhaustion; assert global/host limits and eligible retry times. |
| Schema and semantic drift | Controlled copies/synthetic fixtures add a column, rename a sheet, duplicate a key, change a unit/basis/component code, change rights, and alter zero/null/trace proportions. Appropriate source is quarantined/held with exact coordinates; no invented conversion and no accepted-pointer movement. Danish four definitions keep unknown quantity/no inherited basis and whitelist suppression. |
| Partial source failure | One independent source fails while another finishes. Report all selected sources and all 249 country entries with explicit required/optional/fresh/stale/blocked states. Required complete candidate is rejected; permitted partial candidate never claims full country coverage. Any carry-forward cites the old exact snapshot. |
| Cache and acceptance integrity | Change adapter, dictionary, schema, policy or a required related file: dependent stage key changes. Corrupt a cached blob: reuse refused. Acceptance references exact content SHA, is separate from it, and never mutates a previously accepted manifest. Concurrent same-key jobs deduplicate or safely verify identical output. |

Use controlled local HTTP fixtures for protocol/error tests; live publisher validation is a separately permitted pilot step and cannot guarantee the publisher will return 304. Reuse the existing synthetic tests rather than processing held bodies to generate fixtures.

## Proposed CLI and artifact layout

These commands and paths describe interfaces to implement; they do not exist as refresh features today. Every command returns structured JSON plus human-readable progress, with precise scope and distinct failure/incomplete statuses.

```bash
offmenu dataset plan --countries all --registry registry.json --json
offmenu dataset refresh --countries NO,FR --fetch-policy refresh --jobs 4 --per-host 1 --root /data/offmenu-refresh
offmenu dataset acquire --source matvaretabellen --fetch-policy revalidate --root /data/offmenu-refresh
offmenu dataset acquire --source ciqual --fetch-policy force-download --root /data/offmenu-refresh
offmenu dataset import --source fineli --release 20.0 --bundle permitted-bundle.json --root /data/offmenu-refresh
offmenu dataset build --inputs inputs.lock.json --offline --rebuild --output /data/offmenu-refresh/staging/replay-A
offmenu dataset verify --release candidate-manifest.json --offline --json
offmenu dataset resume --run RUN_ID --root /data/offmenu-refresh
offmenu dataset status --countries all --json
```

`refresh` is the convenience entry point for acquisition plus locked offline stages. It produces a candidate and report. An import still checks retention/parse/use rights and does not clear Fineli's semantic holds. A later explicit local acceptance operation can be scoped separately from any public release or deployment.

```text
/data/offmenu-refresh/                     proposed new root outside existing data
  registry/ countries.json sources.json adapters.json
  policy/ rights.json dictionaries/ runtime.lock.json
  objects/<scope>/sha256/<prefix>/<hash>    immutable permitted bytes
  snapshots/<source>/<snapshot-id>/manifest.json
  locks/<content-input-id>.json             semantic content/dependency closure
  evidence/acquisitions/<receipt-id>.json   immutable acquisition evidence
  evidence/acceptance/<receipt-id>.json     exact candidate hash and reviewed scope
  state/runs.sqlite                        mutable local operational state
  runs/<run-id>/events.jsonl report.json     attempts, times, failures, lineage
  staging/<unique-run-and-stage>/           incomplete, never accepted
  builds/<build-key>/ native/ curated/ common/ content-manifest.json coverage.json
  accepted/<scope>.json                     small local pointer, separately updated
  quarantine/<source>/<snapshot-id>/        reason and restricted evidence references
```

## Staged implementation for review

1. **Freeze the design boundary.** Morgan selects exact sources/operations and designated review path. Inventory existing receipts/code/config/dictionary hashes in an isolated new development checkout and a new artifact root. Adopt existing accepted outputs by reference, not by renormalizing everything. Preserve source custody and all worker results, including holds and the exact Danish candidate. Do not operate in dirty shared main.
2. **Package and plan.** Add registry validation, the CLI plan/status interfaces and full249 manifest. Move or wrap selected functions behind explicit input paths and structured errors. Pin runtime/transitive dependencies and include required corpus resources in the package. Keep existing script invocations compatible. Deliver a dry plan with unsupported/blocked/manual states.
3. **Make offline replay deterministic.** Introduce input locks, separate evidence timestamps, canonical serialization/order/compression and stage keys. Split mixed network lookups into acquired inputs. Reuse current validators and consumer formats. Deliver two independent network-disabled builds with equal content hashes; retain old accepted outputs during any difference review.
4. **Add acquisition and safe resume.** Implement scoped immutable objects/bundles, the four fetch policies, host budgets/retry/checkpoint ledger and atomic finalization/recovery. Use controlled HTTP/failure fixtures first. Deliver no-change, force, interruption, drift and partial-failure evidence. Manual/denied sources remain blocked.
5. **Run the small selected pilot.** Only after exact source-use and dictionary prerequisites are satisfied, process the permitted NO/CIQUAL scope; keep FI/DK held work bounded as above. Review semantic diffs and any format/ID changes. Produce candidate snapshots, acceptance sidecars and a completeness manifest; no production or publication step is included.
6. **Expand adapters incrementally.** Add source families based on retained evidence and demonstrated requirements. Do not equate registering all249 with implementing all1303 leads. Existing publication pipeline remains a separate consumer with its own acceptance requirements.

Unattended work then includes permitted freshness checks, download/import verification, deduplication, parsing with reviewed adapters, deterministic projections, validation, retry/resume and candidate/completeness reports. An unchanged source or changes within an explicitly approved adapter contract can use standing local acceptance policy. New sources, changed access/use terms or credential scope, novel schemas/units/bases, dictionaries/crosswalks, zero interpretation, semantic drift thresholds, source withdrawal and public publication still need reviewed maintenance and Morgan's decisions. AI can help author proposals, but no AI inference or agent session is required for a refresh run.

A local process and SQLite are sufficient for the demonstrated single-machine requirements. Retain existing DuckDB/Node dependencies only for the stages that actually need them. DVC, Dagster or Prefect would add state and operations without a concrete unmet requirement here. Reconsider a workflow dependency only if demonstrated requirements include durable cross-host work queues, multiple operators with distributed leases, centralized secrets or scheduling/observability beyond local receipts. A future local scheduler can invoke the same CLI after an explicit scheduling decision; this task creates none.

## Scope of this outcome

The design and test specifications are complete; refresh functionality and pilot results remain unimplemented. Source rights and semantic holds remain exact source/operation constraints, not blockers to producing this design. Shared main status was unchanged during inspection. The isolated Danish candidate bytes were verified against its receipt, but its synthetic checks were not rerun. No worker instructions, source acquisitions, held processing, project-data writes, GitHub Actions, commits or production changes were made.
