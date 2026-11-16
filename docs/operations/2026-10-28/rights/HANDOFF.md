# Current193 rights, representation-cache and retention propagation map

## Result

**The four ready read-only items now have one concrete 15-edge source/store/key map and exact next dependencies. None of their broader parent obligations is closed. No application patch, rights grant, data deletion or feed activation is proposed.**

Primary deliverable: `propagation-map.json`. It includes exact application function hashes/offsets, 12 source-to-app input pins, policy arguments, callers, stores, keys, clocks, missing receipts and four obligation dispositions. `validation.json` records 39 passing static source/hash/build-input checks, not another generic test suite or historical review.

Snapshot: production **193**, version `d572a1e0-f43d-432b-8033-fc78564ef7c9`; observed serving100% at **2026-10-28 06:04:43.258 UTC**. Application module SHA256 `0e4420ef0152586a80cf982d7084582180b9e8798d9dd87cb6aae304da305a34`. Browser app SHA256 `9b0d51064d746887ee70dbb79baee98e32a4eb57caf8652a7111d3b9e383bf67`. Parent may subsequently publish194+; this is an immutable193 map, not a claim193 remains latest.

## What the actual current routing changes

Do not substitute the retained unbundled `cloud/handler.mjs` from another candidate for current deployed code. The selected app source tree has only `cloud/state.mjs` and `meal-preference-owner20.mjs`; server mappings below come from the actual deployed module.

Current `landing-only.mjs` is hash-pinned `078b1c26b5b363427e6a42f550918935db80b923c0781d63686e7cc1bb11b4ca`, delegating to `worker.mjs` hash `7cef6c38c9a35e4b94d5e7d7d25702a04d64abf35a8497fbd6f91be848f0eabd`.

- The outer landing handler intercepts exact `source=off` / `releaseId=offmenu-off-selected-products-20261025-v1` public inventory requests before fallback. This is a qualified selected-inventory route, not permission to reopen arbitrary source lookups.
- The worker has an owned-foundation override, then authentication isolation, selected-release lookup, static assets and application fallback. Generic `/api/product`, `/api/prices` and `/api/data/public` **do not reach the older application source-fetch routes**. They are blocked unless selected routing already handled them.
- Protected API fallback responses receive `Cache-Control: no-store`, no ETag, and `Vary: Cookie, Authorization`. Main-module helper headers alone omit this outer behavior; do not report a newly invented Vary defect.
- `owned-foundation-response.mjs` is pinned `dcde08ee9d7299e1c406208210a2f07145742b5610a6209fc2718e5597af505b`; the bounded named-function selector did not locate its body. No complete review of that override or primary inventory provider is asserted.

## Concrete store/key propagation

| Path / current consumer | Store and exact identity | Enforcement / propagation boundary |
|---|---|---|
| `worker.$ -> _ -> mA` selected-release fallback | Manifest URL; query cache `__curation-cache/{manifest.manifestSha256}?filters={JSON filters}&manifestFile={selected file SHA}` | Explicit release/source/file hash; filters include source, barcode, query, kind, country, cursor, limit. Manifest60s, result300s. Partition cache is **null**, despite a dormant86400s header expression. This secondary branch is distinct from the outer primary inventory handler. |
| Main `wg`, `/api/catalogue/enrich` through protected fallback | D1 `resolver_cache`/`resolver_leases`: SHA256 JSON `{source, query:trimmed, policy:exact document, normalizer:version}` | `source_policies` display/public decision before cache hit; active/exact-document/persist decision after provider response. Fresh24h, lease30s, bounded backoff. Described only; no provider request made. |
| Main `sA/gI`, `/api/data/records` | D1 `unified_records(owner,id)`; policy by `sourceId` | Read rechecks policy, retention, status/dependencies; persist validates and stamps policy version before writes. MCP/REST data exports use `sA(action=export)`. No derived-store traversal here. |
| `data-ui -> app.applyNutrition` / `recipeForReview` | Local `products[barcode].nutritionProvenance`, `recipes[id].provenance`, `profile.dataRecords[id]` | Client action-time derive/persist/export admission. Product keeps input nutrient-profile ID/basis/status. Copied data is not automatically rechecked against later server policy edits. |
| `cookMeal/serveBatch`, `mealSnapshot/intakeSummary` | `profile.batches[id]`, `profile.history[id]` | Numeric snapshots flow from products; batch allocation retains lot/barcode/original. Totals do not store per-nutrient input record/policy IDs. Current source deletion alone cannot identify every historical derived total. |
| App snapshot + auto sync | D1 `user_state.user_id`; local five account namespaces; IndexedDB `offmenu-pending-v1/pending`, key `KEY` | Snapshots contain products/recipes/profile copies. Merge, baseline and queued state are additional retention/restore edges, not a cascading record delete. |
| Shared kitchen | `kitchens.id`, `kitchen_members(kitchen_id,user_id)`; local `KEY-shared-session`; pending key `KEY-kitchen-{id}` | Server and browser kitchen projections exclude private nutrition fields and private household/history fields. Membership removal ends future access; it does not remotely erase all previously copied/exported data. |
| Private health `rg -> BA/QI/tg` | `private_documents(owner,kind,id)`, revision | Explicit `offmenu-health/1` import consent; private descriptive statistics only. Settings force `aggregateActivity=false` and `backgroundRefresh=false`. No cross-account aggregate producer/publication demonstrated by this route. |
| Disconnect / explicit deletes | Provider connection(user,source); unified record(owner,id or source); personal document(owner,kind,id) | These operations remove their named direct rows only. No supplied receipt shows derived products/history/shared state/backups were erased. **No operation was executed.** |
| Token/member revocation | Token hash/id-user; membership kitchen-user | Access revocation and data erasure are separate. No auth migration or credential inspection. |
| Pantry export/restore | v1 JSON and five browser account state keys | Credential-key exclusion and structural/account guards exist, not source-policy/tombstone replay filtering. Restore copies retained provenance then marks dirty for sync. |
| Clear device account copy | Local account prefix/subkeys plus `clearPending(KEY)` | Pending deletion is prefix-based and includes matching shared-kitchen queues. Cloud and downloaded exports explicitly remain. Not a whole-device/cloud purge. |
| Scheduled retention | Cache/lease/direct record/evidence/limit tables | Direct private `retainUntil` cleanup only; no automatic dependency graph or backup restore suppression. Wired `scheduled()` is not a successful cron/deletion receipt. |

The embedded main `sw.js` excludes API/auth/protocol requests from shell caching. Its outer served-asset precedence was not qualified here, so the map does **not** call that embedded asset a verified active runtime cache.

## Exact disposition and next owner for all four items

Root remains **decision/dispatch accountable**, not the executor of a broad new search. Historical owner numbers below identify existing custody, not currently running agents. This packet is the new input for one narrowly selected custody-binding step.

1. **CACHE-REPRESENTATION-ISOLATION — current map delivered; policy/custody join still open.**
   - Root routes to the existing cache/source-policy custodian after confirming identity. Reuse author16 C1-RL receipt1735 `ca0dc517…a73b21`, reviewer14 receipt1779 `1998eee4…22f87a`, preparation2127 `b69fd9a8…04fbc6` and accepted audit52 temporal result `7c0280aa…42e5c`.
   - Missing: actual policy/grant/source-version and clock input for the selected R01/R03/R04 consumer; exact owner02/C035 envelope and disposition. No speculative cache patch or repeat CACHE52 review.

2. **DERIVED-RIGHTS-SAFETY-INVALIDATION — actual dependency edges delivered; authority/adoption open.**
   - Root routes the explicit R05→R06→R07→R08/R09/R13 edges to the existing derived-store/source-policy custodian. Preserve author52 result2035 `280344cd…3c3705`, reviewer44 result2237 `3198cdfb…3d0d43c`, bound return2242 and Gateway disposition2245 `299aa6b4…00fc18`.
   - Missing: permitted withdrawal/recall feed authority, source event/version identity, treatment of prior observations versus derived copies, actual operator/caller adoption receipt. No reimplementation of accepted portable invalidation work.

3. **AGGREGATE-HEALTH-PRIVACY — current private producer/store documented; aggregate scope not substituted.**
   - Root routes to existing aggregate/privacy-policy custody; historical author59/reviewer38 identity must be confirmed before any new execution.
   - Exact retained pointer `/pendingManagementActions/pending/310`: author2112 closure `34216e97…3a317e`; `/pendingManagementActions/pending/353`: review2194 `d8e534b4…80d7c5` names **H59-PREFLIGHT-R1** array-boundary correction. Missing exact corrected successor/current disposition and actual intended aggregate producer/store/policy authority. Do not infer privacy acceptance from validator work or treat private statistics as the requested aggregate deliverable.

4. **REVOCATION-DELETION-RESTORE — current action/restore boundary map delivered; operator receipt open.**
   - Root identifies/routes to the actual storage/backup operator. No named current operator is established by the inspected custody metadata.
   - Missing: scheduler/retention execution receipt; backup inventory, retention/restore replay and deletion verification; tombstone/version decisions covering local/cloud/shared/offline/export copies. Historical preparation `/pendingManagementActions/pending/185`, manifest `1fa8faa2…fccf273`, is not an operational deletion/restore receipt. Gateway messaging “restore-readiness” is not database backup evidence.

### Shared owner02/C035 prerequisite — exact existing pointers, not another broad search

Use retained `source-permission-evidence-join.md` (full source pin in map):

- Selected work item `/workQueue/items/38`, `owner02-local-source-permission-evaluator`; selection `99fedb83…81ce1`, delivery `85f04697…f1d93`, pickup `f20b698f…5899c3`.
- Required: selected evaluator result/attempt binding, exact implementation/reuse and synthetic artifact hashes, already completed matching review or explicit no-review/no-result disposition. Unrelated owner02 identity callback results must not substitute.
- C035 pointer `/pendingManagementActions/pending/297`, event `owner29-thirteen-resolution-source-field-permission-policy-20261016`, manifest `fc82634f…ad412`: exact synthetic policy/grant/source-version and full endpoint, field, action, purpose, audience, geography and time mapping.
- Existing current private-record helper does not take explicit endpoint/field/purpose arguments. That is an acceptance-evidence gap, not license to invent a replacement evaluator or actual rights grants.

## Preserved completed work and boundaries

192 malformed dependency-retention parity correction remains in193. The recorded48 helper checks and6 actual caller assertions were **not rerun**. This map distinguishes read-time denial from scheduled physical cleanup; it does not reopen that delivered fix.

Initial exact-source-slice retrieval was denied by auto-review for alleged unrelated/private-source scope. It was stopped. Parent then supplied additional verbatim continuing OffMenu production/MCP authority and the separate-research-session context, authorizing one known-unexecuted retry. The minimum worker prefix read was accepted at06:10:29Z and its exact SHA verified. No bypass or further retrieval after the bounded missing-function result. Initial whole-wrapper output was truncated, rejected as an exact local source and deleted; complete received excerpts and remote module hashes are retained instead.

No private userdata, credentials, source-policy database rows, raw datasets, external food lookups, paid/Actions/quotaCodex calls, auth changes, operational deletes, feed polling, source writes, Git writes or parent ledger edits. Parent alone integrates the additive dispositions.
