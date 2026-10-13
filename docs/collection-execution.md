# Full collection execution checkpoint

13 October 2026, Australia/Melbourne. Programme execution is in progress, not complete.

**Later decision/checkpoint:** User requires source data only locally and static
OffMenu curation on Netlify with Cloudflare queries/caching. Separate public D1
is now deleted; residual public records in the shared account DB are quota-blocked
for deletion. Initial OFF normalization acceptance is superseded by a Unicode
JSONL reader defect; complete recollection is running. Historical D1 publication
statements below describe the superseded approach, not current availability.
Current architecture and truthful status: `curation-architecture.md`.

The complete USDA April 2026 CSV archive downloaded, checksummed and reconciled: all 34 CSV tables, 36,049,091 raw rows and the supporting workbook retained in the original archive. All 2,101,279 food rows and 27,195,013 nutrient observations normalized into 4,202,558 unified records; all original relational columns remain in the release database. Multiple nutrient observations are retained instead of overwriting. Sample/acquisition records remain research records, not household food identity approvals.

Open Prices daily 12 October 2026 export: 326,767 raw price rows = 317,898 accepted + 8,869 source-marked duplicate exclusions; zero unexplained losses or quarantines. All 7,550 location rows and 127,894 proof metadata rows parsed and checksummed. Contributor identities, consumption fields, comments and image paths stay out of public projections. Proof images are not acquired. Prices are dated observations, not offers or inventory guarantees.

The Wikibooks 31 July 2024 named snapshot contains 3,895 recipe rows; every row normalized, zero exclusions/duplicates/quarantines. All records imported to the dedicated public corpus D1 and activated after the row count gate. Complete ingestion does not establish reviewed ingredient identities, diet suitability or yield: all imported recipes require review and are excluded from automatic cooking/planning until reviewed. Original text, licence, attribution and unresolved quantities remain attached.

OFF's full 12 October 2026 JSONL release downloaded (13,132,516,914 bytes). Full normalization is running; no final count, full reconciliation or publication claim is made at this checkpoint. No arbitrary first-N collection limit is used. The existing lookup service remains available during ingestion.

## Storage and operations

Account database, authentication and provider vault preserved. Read-only aggregate baseline remains one account, summed revisions 2, 821 state bytes. Production source e57db23 and deployment 495d5259-cea5-42f0-90d8-c04c718c2a34 remained current at initial reconciliation.

Created a separate public-only D1 database, offmenu-open-corpus, a3c9b1fc-bc8d-4c3e-afdf-de78caeeba49, in OC. Importing public data here does not block the account database. Partial releases remain inactive. Every publication requires reconciliation and a count-gated activation; immutable source/release IDs isolate previous snapshots. Large source payloads are outside Git at /home/user/src/offmenu-data; collection scripts and checksums make them reproducible. They have not yet been archived to durable object storage.

Cloudflare R2 API explicitly returned error 10042: “Please enable R2 through the Cloudflare Dashboard.” Durable raw-release storage remains externally blocked on account activation. Subscription inspection returned API authentication error 10000; do not assume a paid tier or silently upgrade. Measure D1 sizes and obey actual platform limits before committing further capacity. Public corpus serving uses separate bindings; no account/vault migration is needed.

## Verification at this checkpoint

111 JavaScript tests and nine Python tests pass; build succeeds. New tests cover complete table imports/resume, changed-release refusal, malformed-row rejection, price export fields, unknown nutrient retention, no silent 1,000-row CSV truncation, public-only corpus queries/pagination, and review gates for source recipes. Deployment and live corpus acceptance are still pending.

## Hacker News discovery extension

Matt additionally requested HN announcements and novel curated datasets. Maintain a supplemental register with announcement and primary-source links, exact releases, novelty against the original register, licence text and quality disposition. HN itself is a discovery signal, not source rights or validation. OpenNutrition 2025.1 downloaded and SHA-256 matches the publisher; its primary methodology explicitly includes model estimates and unresolved citations, and modified contents attribution obligations need enforcement. It is not admitted as measured composition or verified allergy/diet evidence. RecipeNLG, Swiss openfood and SNAPMe are additional leads under primary-source review. Original research registers are not rewritten.

## Confirmed quota stop

Cloudflare API error 7500 now rejects D1 writes: account free-tier daily row write allowance exhausted. This affects account saves until reset at midnight UTC (14 October 2026 at 11:00 Australia/Melbourne) or an authorized plan change. Bulk imports have stopped. All 317,898 accepted prices are staged and count-verified in the public D1; price activation failed, so that release is correctly not advertised as available. Wikibooks had already been activated. Public D1 size is 472,342,528 bytes. No quota bypass or silent plan upgrade will be attempted. Future bulk publication requires verified capacity plus a protected account-write reserve; import parts must be checked against total rows including index writes before uploading. This run underestimated account-wide quota impact; the production account records remain unchanged.

Product/price upstream lookup now treats optional cache-write failure as a transient storage issue: valid upstream data is returned even while cache storage is unavailable. Private saves still fail explicitly and retain the local copy; no success is fabricated.

Matt confirms paid Cloudflare and Netlify subscriptions. The connected Cloudflare account list exposes only 7edd51038e07b5b84a635b3ff7e11144, matching production; Workers settings report default_usage_model=standard. Billing subscription reads are denied with error 10000. Therefore the observed D1 free-tier error is a billing/entitlement discrepancy to reconcile, not proof Matt lacks a paid Cloudflare subscription. Cloudflare documentation distinguishes Workers Paid from website plans; confirm the existing Workers entitlement before recommending or attempting any new subscription. Netlify billing does not determine D1 limits.

Cache-write resilience verification now passes: 112 JavaScript tests, nine Python tests, successful production build.
