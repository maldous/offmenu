# OffMenu consolidated delivery plan

Baseline: six specialist reviews dated 12–13 October 2026; current Cloudflare Worker/D1, Netlify Identity, PWA, private provider vault, personal REST/MCP and shared kitchens. Functionality and evidence take priority over presentation.

## Dependency order and acceptance

| Workstream | Depends on | Deliverable | Acceptance |
|---|---|---|---|
| Research preservation | supplied reviews | unchanged machine-readable registers, checksums and source IDs | 249 unique ISO entries in each country register; 2,523 demo + 707 published lines retained |
| Catalogue and coverage | research | indexed country, source, basket, food-concept and metric documents in D1 | original labels/status/URLs retained; unknown numeric data stays null; discovery and ingestion counts separate |
| Policy and evidence | catalogue | versioned permitted actions/audiences/territories; scoped assertions; retention and invalidation | unknown rights deny shared promotion; private identities excluded from public results; dependencies checked |
| Basket calculations | concepts + metrics + evidence | quantities/state conversion, 45 nutrient metrics, denominator and completeness gates | synthetic fixture reproduces expected totals; missing vitamin C withholds total/rank; no fabricated country quantities |
| Enrichment | evidence + providers | identity, dated company/origin/ownership/certification/recall assertions and preference outcomes | strict missing evidence produces unknown; scope and dates retained; no GTIN-prefix origin inference |
| Health and history | private permissions + metrics | manual/file measurement ingestion, provenance, deduplication, history/statistics and export | explicit measurement units/date/source; private account scope; no medical treatment or child deficit prescriptions |
| Product integration | all above | functional workspace, country starter shopping lists, permitted public lookups and reviewable private imports | end-to-end UI and API checks; no arbitrary URL fetch or credential pooling |
| Consumer interoperability | domain APIs | authenticated REST/MCP read scope, portable exports and import contracts | scopes enforced; no health fields leaked through household/catalogue reads |
| Operations and delivery | all above | idempotent import, cache backoff, coverage/status dashboard, tests, deployment/source checkpoint | source provenance and test evidence retained; gaps reported with concrete blockers |

## Design decisions

- Retain Cloudflare Worker/D1 and Netlify authentication; avoid an unrelated platform migration.
- Preserve all research registers in source. Store compressed versioned catalogue documents server-side and paginate; do not ship multi-megabyte registers to phones.
- Keep country editorial starter baskets separate from published examples and quantitative user baskets. Seven special provisioning entries do not receive invented household defaults.
- Use versioned, per-field evidence with identity, market, state, timestamps and rights. Proposed food concepts remain provisional until reviewed.
- Normalisation is an OffMenu schema, not relicensing of upstream content. Unknown provider rights remain transient/private as allowed, never publicly promoted.
- Complete country indexing is achievable now; complete worldwide barcodes, restaurant recipes, prices, ownership, legal rules and native health access are not established by these reports. Each source needs actual access, rights, schema and ingestion verification.
- Do not automate purchases, accept new paid contracts or claim clinical suitability. Native Health Connect/HealthKit bridges require separate mobile builds and user permissions; web imports remain usable.
- No behavioural aggregates are released until privacy assessment and source permission exist. Optional contribution defaults off; no pooling private subscriptions.

## Explicit external gates

Provider contracts/partner approval; user keys and granular health permissions; inaccessible or historical national tables; undocumented full country basket quantities; local-language food matching; native mobile bridges; clinical/local regulatory validation; independent recipe/device/household pilots. Track these as blocked or unverified, not implemented.

## Delivery evidence

Keep this plan with implementation status, source counts, API contracts, automated tests and actual deployment identifier. Store the source checkpoint after material changes. UI polish is deferred to the later feedback run.
