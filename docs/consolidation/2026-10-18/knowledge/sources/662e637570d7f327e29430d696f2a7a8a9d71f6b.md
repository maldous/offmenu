# CACHE-08 aggregate privacy assessment — Owner 59

**Aggregate publication HELD. Production STOP.** This assessment neither certifies safe publication nor establishes anonymization. It identifies implemented boundaries, missing composition evidence and author-owned acceptance work. Independent review of the exact assessment commit remains required. No existing requirement status or publication setting is changed.

Actual pickup: thread `01a139ab-ddf3-7471-8e79-6c327d19c2d7`, `/home/user/src/offmenu-workers/worker-59`. Assessment date 15 October 2026 Melbourne; source inspection UTC `2026-10-14T13:22:31.882797+00:00`. Fresh locked `origin/develop` base `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; branch `feature/aggregate-privacy-owner59-20261014`. Earlier capacity commit `63fceac6563721c18f65a4790ff0a4df9a3a6148` and discovery-custody review are preserved.

## Original requirement and source

[Canonical CACHE-08](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/docs/recommendation-delivery-register.json#L1253) is “Separate aggregate privacy assessment and anti-reidentification rules”. The original design is `research/reports/04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf`, SHA-256 `2e049a433c329421249a27ccbf92f15c64b9da2cc3adb065d8c6ddb13dff2ccd`.

Printed page 1 separates aggregate observations from product facts and private responses. **Page 6, section 5**, specifies permitted measures, coarse time/location buckets, contribution limits, small-cell suppression and protection against repeated-query differencing. It explicitly rejects treating a fixed cohort size, removed names or hashed account IDs as proof of anonymity; retained internal linkage and external information matter. **Page 7** separates activity contribution from connection/product-fact choices and requires rechecks at job start, commit and serve after withdrawal. **Page 9**, stage 4, requires sparse-record/repeated-query acceptance, rights narrowing, revocation, derived-store deletion and restore-time replay. **Page 10** labels the architecture proposed design, not general legal/provider clearance.

The input `worker17-current-deliverable-coverage-update.json` at `/home/user/Documents/Codex/2026-10-14/task-2/worker17-current-deliverable-coverage-update.json` is an observed custody/coverage snapshot, not fresh implementation acceptance. Its exact SHA-256 and CACHE-08 row are retained in the JSON. CACHE-08 depends on TRUST-02 and CACHE-01. No research PDF, original canonical register or owner reservation is rewritten.

## Selected source flow and limits

| Boundary | Implemented in selected source | What remains unestablished |
| --- | --- | --- |
| Personal documents/health statistics | [Owner-filtered SQL, verified user and no-store replies](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/cloud/catalogue.mjs#L8); private exact statistics include series/latest/min/max. `aggregateActivity:false` is forced when saving settings. | Private descriptive statistics are personal output, not a public aggregate. A setting alone does not guard every future output path. |
| Generic records | [Sensitive-kind exclusions and private-use policies](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/public/record-policy.js#L5); [account-scoped provider record reads/storage/disconnect](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/cloud/provider-data.mjs#L16). | Neither open-source fallback nor private persistence permission grants aggregate reuse. Fine-grained behavior and sole-trader information may still be personal even under non-health kinds. |
| Household projection | [Projection](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/public/sync-model.js#L5) drops named member/health fields, selections, plan member IDs/adjustments and private product nutrient fields; [kitchen routes](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/cloud/kitchens.mjs#L6) require membership. | It retains inventory, recipes, dates, locations and shopping/plan data for the authorized household purpose. Household membership does not authorize public release or another member's health/account data. |
| Public catalogue/resolver | [Public enrichment](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/cloud/enrichment.mjs#L10) checks source policy, hashes query/policy/version keys, limits IP requests, leases refreshes, rechecks policy and applies retry backoff. [Coverage route](https://github.com/maldous/offmenu/blob/5f5bdb6ae716cbf80fab1e174d1af2e354468ead/cloud/catalogue.mjs#L8) counts public catalogue/source rows. | Public catalogue stock/coverage counts are not automatically behavioral statistics. IP/query hashing is not anonymity. Selected handler does not wire 29/30 candidate adapters. No selected aggregate publication gate or behavioral cohort mechanism is established. |
| Producer 07 | Coverage records observed pin `45080c376be9a91faf0d9846a82447931676a10f`; its commit adds recipe inventory. [Selected cloud/corpus.mjs](https://github.com/maldous/offmenu/blob/45080c376be9a91faf0d9846a82447931676a10f/cloud/corpus.mjs#L24) is a retained curated reader. | **Missing exact authoritative producer commit/path and output-to-assertion lineage contract.** Do not substitute this recipe inventory or source manifest for a producer graph. |
| Cache/dependencies 29 | [Adapter at 5a33fe8](https://github.com/maldous/offmenu/blob/5a33fe809c07ffd439378d24dc31c057da8d7e89/cloud/cache-invalidation-owner29.mjs#L7) checks scope, producer epoch, authoritative policy documents/revisions and assertions, then conditional SQL gates at read/write. It requires trusted permission/dependency/reserve callbacks. | [Owner contract](https://github.com/maldous/offmenu/blob/5a33fe809c07ffd439378d24dc31c057da8d7e89/docs/worker-29-cache-invalidation-consumer.md#L32) delegates complete payload binding to the producer/caller. It does not apply suppression, complementary cells, query history, privacy noise or aggregate purpose/consent lineage. No integrated acceptance is inferred. |
| Budget 30 | [Adapter at da6d481](https://github.com/maldous/offmenu/blob/da6d4817fef569bd7564f185702bb2d98f34754d/cloud/durable-budget-owner30.mjs#L10) offers provider-account CAS reservation, cost/request bounds, attempt receipts and backoff. | [Caller contract](https://github.com/maldous/offmenu/blob/da6d4817fef569bd7564f185702bb2d98f34754d/docs/durable-budget-owner30.md#L44) requires trusted account scope, price, clock and integration. Provider quota is not privacy/disclosure accounting; request windows/receipt expiry cannot reset privacy guarantees. |

Proposed composition is: trusted source/producer graph → current permission/dependency gates → cache/lease → provider-account reservation → fetch/produce → repeat commit/read gate → authorized response. It is **not** proof of the composition running in the selected application. A behavioral aggregate must pass a separate purpose/rights/privacy release gate before entering any shared cache, API, export, index or release.

## Threat assumptions and synthetic evidence

An attacker may know a household's approximate arrival/store/diet, compare permitted overlapping cohorts or release snapshots, correlate external public information, reuse cached results, and query through multiple authorized identities or export surfaces. Internal staff may retain contributor linkage. No actual private records, provider credentials or auxiliary datasets were inspected. The unit of protection (person, household or business contributor) must be defined by purpose before selecting mechanisms.

**17 deterministic synthetic assertions passed**, using exact pinned in-memory module imports and arithmetic fixtures. The full probe program, module hashes, expected/actual outputs and limitations are in the JSON. These are counterexamples to naive aggregation and limited existing-function checks; they are not a deployed leak demonstration or a passing anonymization mechanism.

| Synthetic case | Result and implication |
| --- | --- |
| Private owner mismatch, explicit personal public assertion, generic health kind and inactive policy | Existing functions deny these cases. Missing a personal marker still requires review. |
| Household synthetic sensitive fields | Selected projection removes the tested fields. Retained shared fields remain identifying in context. |
| A1 small cell | One contributor is directly exposed by an exact one-person cell; withhold. |
| A2 intersections | Two five-member marginals intersect in one person. Five is an illustrative attack value, **not a proposed safe threshold**. Review allowed dimensions/intersections. |
| A3 differencing | Totals 1,250 and 1,175 from overlapping 11/10-person groups expose excluded value 75, even if both cohorts exceed a simple cutoff. |
| A4 complementary suppression | Total 10 minus published complement 9 recovers suppressed cell 1. Suppression must account for all released totals. |
| A5 rare/sensitive homogeneity | A ten-member cohort with one sensitive category can reveal membership attributes despite no small count. Assess auxiliary information and rare combinations. |
| A6 temporal queries | Counts 20 then 21 plus known arrival time identify an event. Bound adjacent snapshots and temporal composition. |
| A7 stable hash | The same synthetic household hashes identically across releases; stable pseudonyms permit linkage. Hashing is not anonymization. |
| A8 revocation | Recomputed total 100 → 77 reveals removed contribution 23. Withdrawal cannot justify an unsafe before/after release; review derived lineage and recomposition. |
| A9 contributions | 100 events can belong to one contributor. Bound distinct contributors and per-unit influence, not raw event count alone. |
| A10 quota versus disclosure | Actual pinned quota permits two distinct attempts under its synthetic allowance. Those queries can be A3's difference; provider quota does not prevent inference. Memory-store injection does not qualify durable SQL/platform behavior. |

Generic `admission` can allow a verified non-marked public count of one when source policy permits `aggregate`. This is not evidence of an exposed endpoint; it demonstrates why that generic function must not stand in for the separate CACHE-08 release decision. All safeguards below are proposals/acceptance conditions unless the implemented-source table says otherwise.

## Author-owned correction and acceptance gates

The following touchpoints identify needed author work; they do not dispatch new workers, override reservations or authorize edits in this assessment.

### G1 — 07 producer with 02 integration owner

Supply exact immutable producer path and complete output-to-input assertion lineage. Classify behavioral observations separately from product facts; prohibit household IDs, raw timestamps, fine location, stable contributor keys in public payload.

Acceptance: Synthetic malicious payload containing a private trip field despite public assertion graph is withheld; changed producer epoch invalidates caches; no unknown/missing lineage promotes.

### G2 — 02 policy/caller owner plus source rights custodian

Separate aggregate action, purpose, audience, territory and source derivative permission from private/promotion rights; gate all HTTP/export/MCP/background/cache paths. Default disabled.

Acceptance: Setting true or permissive provider licence alone cannot publish; unknown rights, personal data marker omission and missing purpose/decision all deny. No credentials or actual private records in tests.

### G3 — 02 aggregate implementation owner; independent privacy reviewer accepts parameters

Define allowlisted measures, population/unit (distinct contributors or households), contribution clipping, approved bucket widths, risk-derived suppression plus complementary suppression, restricted dimension/intersection catalogue.

Acceptance: A1/A2/A4/A5/A9 fixtures withhold or coarsen; identical sensitive values and rare outside joins are assessed. Thresholds are unassigned; k alone never passes.

### G4 — 02 release caller with 30 accounting owner for separate privacy ledger

Bound query composition across accounts, windows, audiences and releases; prohibit arbitrary adaptive queries. If a DP mechanism is selected, independently specify adjacency, clipping, epsilon/delta, composition, correlated caching and fail-closed exhaustion.

Acceptance: A3/A6/A10 remain protected under distributed retries/cache hits/account rotation, window rollover and concurrent queries; provider budget does not reset disclosure cost; no invented DP guarantee.

### G5 — 29 dependency/invalidation owner plus 02 store/serving owner

Include contribution choice/purpose/entitlement epoch in authoritative graph; recheck at job start, commit and serve. Inventory derivative cache/search/export/embedding stores, pending jobs and backup restore replay; distinguish retention expiry from freshness.

Acceptance: Rights narrowing or withdrawal during fetch/reserve/write/serve returns no new output; revoked dependency cannot survive warm cache or restore; independent public evidence must have separate valid lineage. Recomputed release must pass A8 differencing review.

### G6 — 02 account/household boundary owner; 29 key/ledger owner

Keep contributor linkage in restricted purpose-bound ledger with specified retention; apply authorization and purpose limits to query logs, metrics, cache keys, fingerprints and quota readbacks. No public stable contributor identifier.

Acceptance: A7 demonstrates link risk; account B and household role never grant private health or provider account access. Query errors, timing/hit state and logs are checked for membership inference before widening.

### G7 — existing independent reviewer assigned by root; production decision remains root

Review exact assessment and subsequent implementation pins, independent synthetic attack replay, applicable provider decisions and intended information environment; time-bound review to intended recipients and outputs.

Acceptance: No safe-publication/anonymization/release certification from this assessment. Review broader auxiliary data, small producers/children/sensitive cohorts and later audiences; production STOP persists until separately authorized qualified acceptance.

## Release decision and retained evidence

Keep behavioral aggregate publication disabled. Independent review must select and justify the measure/dimension allowlist, contributor unit/caps, time/location granularity, suppression/complement mechanism, retained linkage lifetime, intended recipients and query/release composition limits. None is chosen here. If differential privacy is selected, its adjacency, clipping, epsilon/delta, accounting, correlated releases and exhaustion behavior need independent mechanism-specific verification; adding unspecified noise is not sufficient. A provider permission or opt-in cannot cure missing rights or reidentification risk.

Recheck permission, contribution purpose/choice and entitlement at job start, commit and serving; propagate rights narrowing through cached outputs, search/export/embeddings, pending work and restore-time deletion replay. An independently sourced public fact may have independent permitted lineage; it must not silently depend on revoked private evidence. Historical releases, derived recomputations and individual withdrawal have different constraints; do not promise universal retroactive deletion or claim retained linked records are anonymous.

No source/policy/settings/schema changes, private record access, source network acquisition, corpus mutation, provider calls, publication or production execution occurred. Only the required Git fetch/branch bookkeeping and these two assessment files were written. Prior source refs, capacity result and discovery review remain intact. Supplied filesystem access is unrestricted (`danger-full-access`), network enabled; mandatory `auto_review` is preserved. Separate approval-policy and persisted user configuration are unavailable; permission-profile environment is unset and no named profile is inferred.

[Machine-readable evidence, source pins and synthetic probe program](aggregate-privacy-owner59.json). This assessment needs independent review at its exact commit/base/tree; no safe-publication or release acceptance is claimed.
