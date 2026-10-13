# Full collection execution checkpoint

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
