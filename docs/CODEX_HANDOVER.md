# OffMenu Codex handover

Latest expansion, 13 October 2026: **`expanded-country-search-20261013` is live**
with **22,519,902 curated records from 18 sources**. Added the complete Overture
food-place selection (12,681,108 references), Finland (4,238 composition foods),
New Zealand (2,857) and Sweden (2,606). Country/type indexes cover every search
entry; all 18 source examples and large/default/text-filtered country pagination
passed through the live Worker. Full licence notices and the prior accepted
static release are retained. 115 JavaScript tests, 26 Python tests and build pass.
Runtime matches tested source `f3f42f6403762193ec451d5312b3044d943c8d9b`;
private state and vault binding remain unchanged, public D1 replicas remain zero.
Finland's additional 2,032 recipe formulae and 27,536 diet assertions are normalized
and exercised locally; cooking/serving and qualification review is still required.
The 249-country report records accepted tagged facts in 243 queues, with six
explicit gaps. Source assertions do not establish complete country coverage,
ownership, inventory or verified diet qualification. See
[18-source execution evidence](expanded-places-national-20261013.json) and
[collection scope and notices](places-national-expansion.md). This supersedes the
older delivery checkpoints below.


Latest expanded execution, 13 October 2026: `expanded-world-20261013` is live
with 9,829,099 curated records from 14 sources. Complete local collections now
include eight added national composition tables (AU, FR, GB, DE, NO, DK, CA, JP),
the current 3,796-page Wikibooks recipe category, 1,505 Wikidata business
references and 100 country guideline references. The original source archives
remain local. Every curated record passed structural and consumer checks;
country-matched examples and pagination passed through the live Worker.
115 JavaScript tests, 17 Python tests and the build pass. Private state and
the vault are preserved. The prior accepted static release is retained so
cached manifests can finish requests across publication switches.

All 1,303 registered source landing pages have been checked; 182 have download
leads. The 249-country execution report distinguishes observed records from
remaining source, access, rights and field gaps. These checks do not establish
complete country coverage, verified ownership or diet qualification. See
[expanded execution](expanded-execution-20261013.json) and
[country execution](country-execution-20261013.json). Older checkpoints below
retain investigation history and are superseded by this evidence.

Latest recovery outcome: Workers Paid was activated with the user's explicit
approval ($5/month plus usage). OffMenu now has a 10,000 ms CPU ceiling.
Default and oversized live queries passed pagination checks across the published
three-source curation after activation. The prior CPU/plan blocker is resolved.
OFF recovery also completed: 4,807,663 raw rows reconcile to 4,807,217 accepted,
61 duplicates and 385 quarantined; all 9,614,434 normalized records passed the
consumer exercise. OFF remains local, outside the currently published release.
See `recovery-2026-10-13.json` for current evidence; earlier notes below retain
the investigation history.

## Local recovery, 13 October 2026 — read first

The historical migration checkpoint below is superseded by `curation-architecture.md`
and `recovery-2026-10-13.json`. Source datasets belong only in local
`/home/user/src/offmenu-data`; publish only accepted OffMenu curation as static
Netlify files. Do not restart public D1 imports or use Netlify Functions for this path.
The repository has been restored locally from `8fcf67d`. Reacquisition is authorized.
The remaining 15,312 public source records, 14 product caches and one price cache
were deleted successfully; read-back is zero, with the account aggregate unchanged
(one account, revision sum 2, 821 bytes). The vault binding is preserved.

Install Python test dependencies with `uv venv .venv` and
`uv pip install --python .venv/bin/python -e '.[test]'`, then use
`.venv/bin/python -m unittest discover -s tests`. The fresh checkout initially lacked
openpyxl. Recovery verification passes 115 JavaScript tests, nine Python tests and
the Worker build. Local raw archives, collection outputs and per-stage logs are
outside Git under `offmenu-data`; inspect these before restarting long operations.
The static three-source curation is live. Worker CPU exhaustion remains intermittent;
see the recovery JSON for the confirmed account-plan API discrepancy and current deployment.

Checkpoint: 13 October 2026, Australia/Melbourne. Owner: Matt Aldous, GitHub account `maldous`. Migration destination: **private** repository `https://github.com/maldous/offmenu`, branch `main`. This handover imports the saved source checkpoint, all five reports and four research registers. Historical Git history is preserved in `migration/offmenu-checkpoint.bundle`; the remote migration commit is based on the existing bootstrap commit. Read `docs/MIGRATION.md` for provenance and verification.

## Mission and authorization

Continue the existing OffMenu product, assimilating the specialist research and delivering functionality in sustained work. Matt has authorized implementation, hosting and MCP use. Provide regular, short progress updates. Prioritize working data, recipes, household planning, inventory accounting, statistics, dietary qualification, health import and interoperability. Extensive UI/UX feedback will follow later; do not spend this run primarily on presentation. Do not replace the established product or invent complete worldwide coverage.

## Start here

1. Read this file, `docs/delivery-plan.md`, `docs/product-review-status.md`, `README.md`, every report in `research/reports/`, and the four `research/OffMenu*.json` registers. The README contains historical sections; reconcile them against code and this checkpoint.
2. Establish the current source commit and actual production deployment before changing anything. Other project sessions have worked on this same product; reconcile current state and avoid overwriting newer changes.
3. Install with `npm ci`; run `npm test`, `python3 -m unittest discover -s tests`, and `npm run build`.
4. Verify D1 counts and schema before replaying imports. Writes are idempotent, but needless replay increases requests. Tool responses for large result lists can truncate: use bounded pagination or small aggregate queries, never assume a truncated list is complete.
5. Continue the dependency order in `docs/delivery-plan.md`, maintain a concrete acceptance matrix, then deploy and verify live workflows. Save checkpoints after material changes.

## Existing architecture

- Source originally at `/home/user/src/offmenu`. Python/SQLite CLI and local server coexist with a JavaScript PWA and Cloudflare Worker/D1 backend.
- Public product: https://offmenu.aldous.info/ . Worker name: `offmenu`.
- Cloudflare account: `7edd51038e07b5b84a635b3ff7e11144`.
- D1 database: `offmenu-users`, ID `006cbdd6-6be8-4181-9dd5-519de280b6ef`, binding `DB`.
- Netlify Identity project: `offmenu-accounts`, Google provider and return-page integration already implemented. Inspect current settings rather than recreate accounts or authentication.
- Credential vault: Cloudflare secret `PROVIDER_VAULT_KEY`. It is NOT in source. Preserve it with Worker metadata `keep_bindings:["secret_text"]`; do not regenerate it. Existing encrypted user credentials would become unreadable.
- Worker currently uses compatibility date `2026-10-12`, flag `nodejs_compat`. Preserve query-string redaction and current bindings/settings. Build output is `dist/worker.mjs`; module upload is multipart with `main_module` and module content. Retrieve current Cloudflare API documentation before deploying.
- No credentials, private user snapshots or production DB exports belong in git. The research reports/registers and public feature code belong in the private repository.

## Verified checkpoint

Migration verification: **92 JavaScript tests pass**, **7 Python tests pass**, production build succeeds. No new deployment was performed by this continuation before the user requested the move to Codex. Cloudflare deployment metadata confirms version `e968ff23-2040-4cd2-af3e-ad7af89be93a` at 100%, deployment `4fc7e209-1bbf-4939-98e0-338f53898a82`, created `2026-10-12T20:49:36.041213Z`. Thus the new research-workspace code is saved locally, but is not established as deployed. Recheck this metadata when resuming.

Latest production D1 aggregate query:

| Record kind | Count |
|---|---:|
| country | 249 |
| basketLine | 3,230 |
| foodConcept | 337 |
| metric | 45 |
| source | 1,303 |
| specification | 3 |
| total catalogue | 5,167 |
| source-country applicability links | 1,400 |

Public `unified_records`: AFCD 1,801; CIQUAL 3,484; CoFID 2,887; Germany BLS 7,140; total **15,312**. These are composition records, not complete barcode or retailer catalogues.

Earlier in this continuation, production had 249 countries, 3,230 basket lines and 1,056 source records, and the source-country table was absent. The schema was applied and four import batches were sent successfully. A subsequent aggregate query shows the complete counts above, including all links. Therefore **do not blindly resume batches 4–8**: recheck database first. This discrepancy may reflect work in another project session. Preserve current results and reconcile provenance.

Research regeneration:

```bash
python3 scripts/consolidate-research.py
python3 scripts/source-territories.py
```

These create `dist/catalogue.sql`, `dist/source-territories.sql` and research checksums. `cloud/catalogue-schema.sql` is additive and idempotent. Generated artifacts are excluded from git and can be recreated.

## Functionality present; acceptance still needed

The saved code includes dinner-first navigation; front-camera continuous checkout, void and receipts; custom locations; household diet/preferences; 30 new quantified recipes plus prior sample; cook/serve ingredient deductions and usable leftovers; meal completion; shopping gaps; nutrition history, goals and organisational rewards; private snapshots and shared-kitchen roles; provider vault and unified imports; scoped REST/MCP with OAuth/PKCE; global data browser and research workspace.

The new catalogue layer adds country/source/basket/concept/metric pagination, country starter lists, evidence-aware calculation and qualification, GLEIF/Wikidata candidate enrichment with caching/backoff, private health measurements/statistics, private evidence and basket documents, and contribution preferences with publication disabled pending rights/review. Key files: `cloud/catalogue.mjs`, `cloud/enrichment.mjs`, `public/data-workspace.js`, `public/basket-model.js`, `public/evidence-model.js`, `public/health-model.js`, `tests-web/delivery.test.mjs`.

Audit these against the reports rather than equating code presence or passing model tests with complete live acceptance. Validate production routes, country filtering, source applicability, calculations and privacy. Real-device camera/audio/accessibility testing, external MCP-client testing, multi-device/offline kitchen testing and independent recipe/nutrition review remain gates.

## Required data/evidence constraints

- All 249 ISO entries remain indexed. Seven special provisioning entries (AQ, BV, GS, HM, IO, TF, UM) have no invented ordinary household default.
- 2,523 editorial starter lines and 707 published examples remain separate. Neither constitutes 249 complete official quantitative baskets. Missing quantities/state/composition prevent country ranking.
- Unknown nutrients stay unknown, not zero. Preserve source units, definitions, prepared state, edible fractions, method, coverage and lineage; compare only compatible cohorts and definitions.
- A GTIN prefix does not prove manufacturing/ingredient origin. Company and ownership links need identity, dates, market, scope and evidence; name matches stay candidates. Dietary qualification must distinguish verified, conflict and unknown.
- Public access does not establish ingestion/redistribution rights. The schema does not relicense upstream data. Provider-key results stay private unless field-level source rights, entitlement, market, purpose and consent permit promotion.
- Shared cache promotion and behavioural aggregates are disabled until the applicable rights and privacy requirements pass. Terms disclosure or anonymisation alone is insufficient.
- Health measurements, personal dietary history and provider credentials remain account-private, including household and REST/MCP projections. Health imports require explicit consent; native Health Connect/HealthKit and provider access remain external development/access gates.
- Food stock, served food, eaten food, leftovers and waste are distinct. Do not reward children for finishing food or prescribe child calorie deficits.
- Freely usable public sources should be available globally, with optional country filters. Credential-requiring services use user-owned connections. Do not pool subscriptions or silently use OffMenu keys in place of BYOC.
- A source directory entry is not an active connector. Track documented lead, verified access, permitted ingestion, actual ingested records, freshness and blocked dependencies separately.

## Delivery priorities

Finish a requirements-to-implementation acceptance register, verify live research/data workflows and deploy the current code if needed. Then close functional gaps in rights/invalidation, feature-ready recipe and regional data ingestion, coherent food-to-meal-to-consumption accounting, statistics and exports, BYOC integrations, and API/MCP scopes. Keep external contractual, native-app and clinical gates explicit. Report exactly what is delivered, what is verified, and what needs access or device testing. Do not claim 'full global food data' from country-index completeness.

## Handover prompt

Continue OffMenu from this repository. Read `docs/CODEX_HANDOVER.md`, the delivery plan and all specialist reports/registers before implementation. Reconcile current Cloudflare deployment and D1 state; preserve user data, household state and the provider-vault secret. Deliver the dependency-ordered functionality and permitted normalized datasets in sustained work, keeping discovery separate from verified ingestion and unknown evidence explicit. Prioritize functionality over presentation. Use available MCP connections, batch requests, run meaningful checks, and provide brief progress updates at least every minute while working. Maintain an acceptance register, deploy verified changes, save checkpoints, and report concrete external blockers without pretending coverage is complete.
