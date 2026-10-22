# Historical diagnostic-package provenance

> Historical record: the original text and hashes below describe the earlier diagnostic/source-capsule package, not the current parallel retained-ingest plan. Current implementation provenance and validation are appended at the end. Earlier statements about no imports or no automatic returns must not be read as the current `./run` behavior.

# Provenance and boundaries — 22 October 2026

New stdlib diagnostic/capsule-inspection code, no retained data/runtime caller copied. Cloud filesystem work only; no Foo session, job, scanner, load, download or external AI request. This does not transfer authority to integrate other source or run loads.

Directly inspected connected GitHub sources:

- `integration/offfoo-synthetic-handoff-20261022`, head `b639857d84097c4a1424a1b1f9437de28f23d52e`: `portable-synthetic/README.md` and commit contents for `continuation/cloud-continuation-delta.md`.
- Frozen handoff `24f5d62a3b0fba9f2375496d9dfe40a6767f3061`: `continuation/README.md`, `continuation/source-state.json`. These are on the separate continuation commit, not present at those paths under `b639857d`. Explicit executable-load continuation incomplete.
- Recovery `52b6a50a59b458bdb49fe7ea090b72c63a4b1a30`: `preserved-source/retained-lookup-20261022/RECOVERY-CHECKPOINT.md`. Operational data/caller details intentionally absent.
- Parent's existing final-handoff evidence gives the exact supplier archive path and SHA-256 prefix `e2508555` (archive digest, not commit). Full digest unknown in cloud. Parent confirms retained root `/home/user/src/offmenu-data`. Current exact OSM custody path unknown; no further path invented.

Root AGENTS.md request at handoff returned 404; publisher independently found none in develop's recursive tree. Current user AGENTS rules apply: approved source/tests/docs publication excludes raw datasets/credentials.

Historical documentary refs, not load-qualified here: HTML `c5aaf05e33fc26208fa5593dc62091bc30b3e9c7`; PDF successor `ff423621445eb6bf97d48765a89ef4c805237eeb`, PR91 source head `570707e3763c54b4c63cf07d08c1bf8abf85e453`; UniTools `7a7c69063e15f83067b1a13f23a4f352db996ee4`. Parent subsequently reports PR91 merged to develop `e18ff620e434cb0489c87a2d85069e621fefc4b8`; publisher verifies latest base. Source acceptance does not qualify a retained-data load.

## Custody and validation

Private output retains host paths/PIDs/names and source member manifest locally. Sanitized return is fixed count/status/checksum schema. Explicit source upload requires successful full capsule inspection and human review; original archive remains unmodified. Automated heuristics cannot prove all secrets/disguised raw data absent. No output is auto-uploaded.

`python3 -B -m unittest discover -s manual-action/tests -v`: 20 generated-fixture tests passed in cloud at 01:06 UTC. No actual capsule/retained inventory available. Review receipt records final file hashes and validation. No live command or Actions rehearsal claimed.


# Current retained-ingest implementation provenance — 22 October 2026

The current `./run` contract is the schema-2 `retained_ingest_all` plan in `plan.json`. It self-pulls the existing private integration branch once, then uses the frozen local code for the run. The accepted user scope is broad retained-data ingestion across all eight domains, with independent source failures recorded while other sources continue. This publication supplies executable source, tests and documentation only; it does not launch Foo or establish a successful live ingestion.

## Complete source closure

- Coordinator and receipt delivery: `plan_runner.py`, `plan.json`, existing executable root `run`.
- Shared ingestion contracts and private transactional staging: `ingest_api.py`, `ingest_store.py`, `ingest_engine.py`, `ingest_all.py`.
- Bounded retained source catalog and read-only existing-store reuse: `ingest_catalog.py`, `ingest_existing.py`.
- Fixed domain adapters: `ingest_recipes.py`, `ingest_suppliers.py`, `ingest_misc.py`.
- Exact recipe parser/schema vendor closure: `reviewed_recipe_sources/manifest.json`, its parser/schema/package files and boundary README. The parser is SHA-256 `843d7808881d39cfb65ad8db1bbc4604ea9706d54bc504854b88664e0c9887f2`; the schema is `6c450429cea05a719bd367116cda978b465c44ab5f0e65c6fa0dc7a80ef57814`, copied unmodified from PR90 source commit `f1faa0d63b6fd46e145122b1843ad3bb9fa60c0f`. No stale native recipe writer replaces accepted application code.
- Generated fixture suites for core, catalog, existing-store, recipe/ingredient, supplier/place, dietary/citation/private domains and the complete root-run protocol.

New databases are additive private local staging with the explicit disposition `additive_staging_not_app_bound`; they do not claim the existing UI is populated. Rich retained product/identifier stores are reused read-only through local references, not rewritten or bulk-copied to inflate imported counts. Public counters describe source-provenance rows rather than unique canonical products/recipes. Household inputs require explicit user-supplied and household-scoped metadata; empty private domains are legitimate.

No original dataset, populated database, credentials, internal review notes, real catalog or private runtime checkpoint is included in this source publication. Runtime catalogs, source paths, raw records, individual errors, staging databases and private household data remain local. Only strict sanitized periodic/final summaries can be committed automatically. There is no new download, archived-source execution, external AI call or live Foo launch in this publication. Optional dependencies are used only if already installed; missing optional adapters remain isolated, not silently claimed successful.

The initial independent diagnostic review and hashes above remain historical. Current implementation test evidence is recorded in `REVIEW.md`; it is not a fabricated current provider approval or a claim of live data acceptance.
