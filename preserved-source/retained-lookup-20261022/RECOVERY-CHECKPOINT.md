# OffMenu source recovery checkpoint

Last observed: 2026-10-22T08:21:52.868650+11:00 (Australia/Melbourne).

This sanitized source-continuity note is not the project authority. Existing native owner contexts, the local operating entrypoint and the existing ledger/machine handover remain authoritative. Obtain private operational evidence locally through those owners; it is intentionally absent here.

## Accepted and preserved source

- Accepted `develop`: `d48d657b1c0d1816c143cc23c446a0b87be9085c` (PR #89, qualified retained OFF/USDA federation source).
- `main` last verified unchanged: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`.
- Exact delivery-source archive: `c78ee2568247d13ed2d1d88c99cd147d258f410d` on `preservation/retained-lookup-delivery-source-20261022`. It preserves 38 named source files under `preserved-source/retained-lookup-20261022`; nine identical dependencies are already present in the accepted base. It is source preservation, not a deployment or portable rebuild claim.

## Current recipe source lanes

| Lane | Source and PR | Last verified state | Next existing-owner action |
| --- | --- | --- | --- |
| HTML adapters | Author correction `c5aaf05e33fc26208fa5593dc62091bc30b3e9c7`; [PR #90](https://github.com/maldous/offmenu/pull/90) currently head `90b549b51c64914767948ea8b055ba4833d92c2c` | Exact independent source PASS now qualifies both whitespace/selector corrections. Source update is in progress; current PR head and unresolved old threads are not yet final acceptance. | Existing00 completes focused checks, updates the same PR, then ordinary current-head provider/body/inline, CI/security, expected-head merge and postmerge. Existing13 original qualification/load is separate. |
| Cache-only partial recipe loader | Author `37f27fc61c18a11cea1aed0c59c4229a6c5cc679`; [PR #91](https://github.com/maldous/offmenu/pull/91) head `5600e2e7d43e1ff7d200555406421457bf3ae16b` | Transaction correction and current matrix are qualified, but current provider found an allocated-page/effective SQLite size-limit issue. Application checks and GitGuardian passed; the PR remains held and unmerged. | Existing13 supplies the narrow size-bound correction and frozen successor; existing64 reviews it, then existing00 updates the same PR and normal gates. No actual database repair or cache/PDF replay. |
| UniTools | Latest reported frozen successor `7a7c69063e15f83067b1a13f23a4f352db996ee4` | Routed to the existing reviewer for native connection-mode review; not accepted or loaded. Older `dd7b43189f6818752b205c9d99da6422341f852a` remains held history. | Existing26/64/00 continue their exact author-review-integration sequence independently of the recipe lanes. |

The rejected cache predecessor `7050ef38f7196db47caf5561b05f00736febb37e` and its adverse atomicity evidence remain retained. The PASS applies to the corrected `37f` source only. Source acceptance is not a recipe database load, full-original qualification, canonical/gold mapping or country completion.

## Eight-domain product rationale and relationship contract
Human requirement recorded 21 October 2026 21:16 UTC. These are eight logical domains, each potentially using several relational tables and source-specific stores, not eight giant flat tables. This section records required behavior; it does not assert that every relationship, API or protection is implemented.

| Domain | Why it exists and required exposed behavior | Relationship and current implementation boundary |
| --- | --- | --- |
| Barcodes / products | Resolve lexical identifiers to product, package and market variants for scanner lookup; expose product and brand, source composition/nutrition/caveats and image/category fallback. | Identifier assertions point to source-native product variants. A product may fulfill an ingredient role through evidenced mapping; barcode is not ingredient identity. Retained OFF/USDA manual lookup is delivered. Image rights, fallback completeness and physical camera decoding are not established by that proof. |
| Ingredients | Provide stable ingredient concepts, aliases and hierarchy for later normalized matching. | Connect sourced product composition to recipe ingredient lines through explicit, versioned mappings. Current raw references/strings are retained; canonical mapping, translation and hierarchy coverage are not established. Preserve ambiguous or conflicting mappings. |
| Recipes / menus | Preserve quantities, units, preparation, regional variants and sharing IDs; later support pantry matching and substitutions. | Recipe lines refer to ingredient roles; explicit substitution and quantity rules may select compatible products and available lots. Do not infer substitution safety or unit conversion. Reported current database content is 13 recipe variants and **2 menus containing 70 items/entries**. The former 70-menu wording is superseded. PDF sections are cached, not yet database recipes. |
| Dietary / nutrition | Retain source nutrient observations, claims and measurement bases separately from derived calculations; support profile-aware evaluation. | Product/ingredient/recipe evidence plus a private profile can drive a qualified evaluation. Keep raw versus calculated values, units, basis, method/version and missing/conflicting evidence distinct. Unknown is never automatically safe, allergen-free or diet-compliant. Raw reference population does not establish this evaluator. |
| User Profiles | Hold private household membership, preferences, allergies, health/diet plans and sharing permissions. | User/household membership authorizes access to profiles, plans and inventory. Existing user_state/kitchens/kitchen_members schema is a foundation, not proof of complete health-plan or isolation behavior. No genuine retained user records are established for ingestion. |
| Inventory | Hold user-owned lots, quantities, locations, expiry and buy/stock/remove/void events. | Lots link to products and household ownership; recipe matching consumes availability, shopping proposes shortages. Void/removal must remain distinguishable from consumption and audit history. Existing development state is not genuine household stock; the full lot/event contract is required behavior, not claimed delivered. |
| Suppliers | Represent evidenced supplier relationships, offers, availability and prices. | Offers link suppliers to products and shopping needs with time/source/market scope. Arbitrary places/retailers are not verified suppliers or offers. Current supplier import remains held; place candidates do not populate supplier counts. |
| Citations | Link every source assertion to original asset URL, release, licence, hash and transformation lineage. | References accompany products, composition, recipe spans, dietary claims and supplier assertions. Preserve unavailable URLs/clocks/hashes as unknown; wrapper publication URL is not original acquisition proof. Existing indexed citations cover selected sources, not the complete retained inventory. |

Required user journey: scanner identifier → sourced product/package/market variants → evidenced ingredient roles → recipe lines and explicit substitution rules → household inventory availability → supplier shopping options. Dietary evaluation draws on source nutrients/claims and private profile constraints throughout. Citations and caveats remain visible along that chain; no matching or safety conclusion is inferred merely because records exist.

### Reference versus transactional behavior
Reference ingestion is source-faithful, versioned and generally read-only to consumers; retained federated stores may serve several domains without copying or counting shared records twice. Private mutable profile, household, stock and event records require authenticated owner/member-scoped operations, conflict/revision handling and explicit sharing. Public reference availability never authorizes exposing private state. Source-specific licences, attribution, acquisition/use restrictions and actual denials survive ingestion and derived views; images and public redistribution require their own applicable rights.

Preserve stable internal IDs alongside source-native identifiers and source ordinals; do not replace lexical barcodes or deduplicate conflicting assertions by guesswork. Keep source release/acquisition clocks, observed/checked times, created/updated times and event times semantically separate; unknown acquisition remains null. Required transactional designs should retain actor, operation/idempotency key, revision, audit provenance and soft-deletion/void/tombstone semantics where appropriate. These fields are not asserted universally present in existing tables.

Future database row-level security or equivalent enforced household isolation must cover every read/write/query, sharing route and background job; it is a requirement to implement and test, not a claim that SQLite/D1 currently provides a blanket RLS guarantee. Existing cloud/schema.sql contains user_state revisions/updated_at, kitchens/kitchen_members roles, source/licence/checked_at product and price records, and separate audit/tombstone structures for selected services. These do not by themselves prove full eight-domain isolation or universal deletion/audit behavior. Existing cloud/recipe-community-schema.sql and offmenu/refresh/{recipe_menu_store,ingredient_ingestion,dietary_native_store}.py remain source/schema references, not authorization for new operations.

Raw ingestion now must preserve original language, unknowns, null/empty distinctions, quantities, provenance and conflicting claims. Normalization, translation, canonical mapping, reviewed calculations and gold admission are later explicit stages; do not delay eligible raw retention for their global completion or label raw rows as gold.

The eight-domain contract below is the human-required product rationale recorded in the current local rolling handover. Statements about current content/schema are attributed status, not a fresh data, security or implementation audit by this documentation step. Requirements are not universal implemented guarantees.

Parent reports Page sequence 12 was updated and read back at 2026-10-22 08:10 AEDT (21 October 21:10 UTC), superseding the old 70-menu wording. This checkpoint attributes that Parent report; it makes no independent Page-read claim.

## Recovery directions

1. Resume through the existing manager/Gateway and exact existing owner; read the local operating entrypoint and current ledger/handover first. Do not create a replacement tracker, worker or coordinator.
2. Freshly reconcile accepted remote `develop`, the exact author/reviewer pair, current PR head and ordinary review/CI/security evidence. Do not assume a remembered or remote-tracking SHA is current acceptance.
3. Obtain the local owner recovery receipt and inspect the exact owner checkout/branch/uncommitted paths before editing. Preserve all WIP; do not reset, clean, stash or switch another owner's checkout.
4. Continue one existing selected action without duplicate jobs or review triggers. Provider request admission is not a verdict; read review bodies and inline threads independently. Normal source integration targets `develop`, with expected-head and exact postmerge evidence.
5. Keep the working scanner, data and healthy processes unchanged. Actual original/cache/PDF/store operations require their separately selected rights, custody, caller and load contract. Never infer that source presence or this note authorizes replay, restart or activation.
6. Refresh this same sanitized note after material source/PR acceptance changes. Refresh the existing local rolling note and derived machine handover through their current owners; do not copy their full histories into Git.

## Preserved boundaries

Existing source privacy, rights, provenance, custody, ownership, denied-action/seal and no-acquisition holds remain. Main, production and CIX remain paused. Physical camera decoding and broader platform/nightly assessment remain separately unresolved; no new test or runtime claim is made by this checkpoint.

No dataset rows, database locations, credentials, environment values, private operational receipts, process identifiers, active context/manifest contents, resource controls or full local handover note are included in this publication. Exact operational paths and owner WIP status remain in the local recovery receipt.
