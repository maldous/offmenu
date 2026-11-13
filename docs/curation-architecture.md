# OffMenu local curation and static delivery

<a id="current-product-design"></a>

## Product design and data boundaries

This document describes product contracts and intended delivery boundaries. Source
presence, a design decision or a successful parser is not proof of current
application availability, complete country coverage or qualified data. Source
rights, account consent and actual access restrictions apply independently to
each selected operation. Historical execution and custody receipts are preserved
outside the maintained product documentation.

<a id="north-star"></a>

### Established North Star and data semantics

The staged household daily loop and regional integrations are detailed in the
[consumption, inventory and integration design](consumption-inventory-integration-design.md).
They remain design requirements until their stated component acceptance is met.

**Barcode → Product → Ingredient → Recipe → Quantity → Nutrition → Menu → Serving → Consumption → Leftovers → History → Planning → Integration → Ordering → Receipt → Barcode** This is established
owner scope, not a new requirement discovered by this reconciliation. Matt's
reinforcement is `Sentinel_09fbc9f9e40881919333c5ce40dcd754` (25 October
2026, 06:31:47 UTC), followed by the explicit North Star/consumption clarification
and compact wording relayed through the product owner. Exact later native message
IDs are unavailable here and are not invented.

The exact extended loop supersedes the shorter wording above in earlier
preparation packets: Matt `Sentinel_dce80a65211481918f30f3e860727b03`,
25 October 2026 06:51:02 UTC. Integration, ordering and receipt are documented
requirements; working external integrations or ordering/receiving journeys are
not established by this wording. **Ordered is not received.** Confirmed received
goods reconcile through **Barcode scanning before entering stock**; the loop
returns to Barcode, not Product. Bind the existing
`COLLABORATIVE-SHOPPING-LIST`, `HOUSEHOLD-DURABLE-SYNC` and consumption/inventory
parents to actual current component owners and acceptance evidence; no new task
or permission to order, access an account or alter stock is created here.

Barcode recognition identifies source assertions; it does not establish a unique
canonical product or an ingredient. Product-to-canonical-ingredient links need
qualified identity, composition and provenance before recipe use. Recipe
quantities, units, preparation, yield and nutrient basis must support **both
whole-recipe and per-serving nutrition**. Preserve source version, evidence,
missing values, conflicts, uncertainty and correction lineage through every link.
Original-language/source-faithful import is distinct from parsing, normalization,
translation, canonical mapping, review and English Gold admission. A recipe title,
menu listing, barcode or unknown quantity cannot substitute for those stages.

Daily menus and household/individual profiles allocate person-specific servings.
Keep **planned, prepared, served, eaten, saved, discarded, transferred and
unknown/unlogged** distinct, including partially eaten meals and components.
**Serving never implies consumption; a missing log never means zero.** Reconcile
cooked batches, component leftovers, transfers and inventory effects without
counting them twice. Period-based actual-consumption estimates retain units,
yield, source versions, uncertainty, corrections, per-user allocation and
configured targets. History informs future planning; it does not erase earlier
source/disposition evidence. Intake estimates are not measured biometrics, and
being below a configured target is not a clinical deficiency diagnosis. Sensitive
profiles/history require consent, household permissions, audit and export
boundaries; kitchen membership does not grant access to private provider data.

Saved leftovers must be **added back as prepared-food inventory batches** in the
selected pantry, fridge, freezer or custom location. Preserve recipe/version and
original ingredient-source links; remaining quantity, units, servings and nutrient
allocation; preparation/storage dates and uncertainty. This is a **stock transfer**,
not a purchase or consumption. Later consumption, reheating, sharing or disposal
reconciles the remaining batch and person intake without double counting. Keep
saved, waste and unknown outcomes distinct; no automatic safe-storage or shelf-life
promise follows. This extends the existing consumption/inventory requirements,
not a new dashboard or separate task. Exact owner source:
`Sentinel_93926b4504dc819192befcf98888dfd8`, 25 October 2026 06:39:23 UTC,
relayed through the product owner.

<a id="normalised-vocabulary-and-nutrition-consistency"></a>

### Shared vocabulary and declared versus modeled nutrition

Use one inspectable, versioned persisted vocabulary projection over the existing common-resource and ingredient/GOLD contracts. Stable ingredient IDs are shared by product mappings and recipe mentions; compounds can contain several independently evidenced ingredients. Consistent English preferred labels retain original multilingual aliases, source versions and reviewed crosswalks. Categories, nutrients, units, preparation and quantity concepts retain their own types, definitions, evidence and unresolved states. Source-import tables and lexical alias lists are not evidence that this populated shared generation is qualified. Declared product nutrition remains a source fact separate from an ingredient-weighted modeled estimate. Consistency checks require compatible quantities or percentage ranges, nutrient definitions and units, product/serving basis, processing yield, uncertainty, rounding and any explicitly qualified applicable threshold evidence. A fat-containing ingredient alone does not refute a fat-free claim; unknown composition is insufficient evidence. Any supported possible discrepancy remains a review signal, not a diagnosis or regulatory conclusion.

Persisted schema/view foundations and import contracts do not establish a
qualified populated vocabulary generation. Canonical ingredient/dish links can
remain unresolved. Corpus counts do not establish current vocabulary coverage,
actual product fit or complete recipe nutrition. This design does not grant data
access or create a competing taxonomy or dataset.

### Component qualification

| Product area | Qualification boundary |
| --- | --- |
| Ingredient, recipe/menu and product stores | Preserve the [ingredient source contract](ingredient-ingestion.md), [recipe/menu source contract](recipe-menu-store.md) and [product federation](private-product-detail-federation.md). Unresolved canonical links remain explicit. |
| Identity and barcode interpretation | Identifier recognition and source-native dictionaries do not prove a product-to-ingredient mapping or an accepted default reader. |
| Household planning | Source-present plans and profiles do not prove diner adaptations, stock reservations, canonical quantities or whole/person nutrition. |
| Consumption, leftovers and history | Cooking, serving and waste events need their own source-bound reconciliation; interface presence is not complete longitudinal nutrition. |
| Shared kitchen and sync | Membership/roles and plan projection are distinct from actual two-device, offline, conflict and received-stock qualification. |
| Rights and account privacy | Check permitted operation/audience, consent, retention, withdrawal and restore/deletion behavior for each actual source and store. A checkbox or HTTP success is not a rights grant. |
| Authentication | The [foundation](better-auth-foundation.md) and [runtime seam](better-auth-runtime-seam.md) distinguish source integration from a configured, qualified account service. |

<a id="scanner-reconciliation"></a>

### Scanner and checkout boundaries

Preserve automatic acceptance, Void/Undo, final receipt review and checkout, and
the application/backend/account/inventory/source flows. A simulated interface is
not a substitute for those flows. A guide overlay does not prove that the actual
decoder crop or selected camera matches it. Camera switching, available-camera
fallback, sound, speech, vibration and light need real browser/device evidence.

Responsive layouts must respect available viewport area, hinge/safe areas,
readability and explicit user choice. Retain source/author/licence access with
product details. Interpreted ingredient/category/quantity values must not become
false identity or nutrition acceptance. Entered date labels and estimated review
reminders are separate and do not establish food safety.

<a id="feature-communication"></a>

### Product communication

Use the existing **From product to pantry to plate** headline and
[feature-copy asset](../apps/web/assets/feature-copy.v1.json). Preserve its keys,
values and mapping rather than inventing a competing copy store. Present values,
not internal feature keys. Planned features and foundation-unverified entries
must remain visibly distinguished from qualified available behavior. Approved
copy does not prove rendering, deployment or product functionality.

If feature rotation is implemented, preserve readable dwell time, stable layout,
a pause control, reduced-motion alternatives and a complete accessible list.
Repeated changes must not repeatedly announce through a screen reader. This
document does not qualify a rendering or activate a landing/authentication flow.

## Boundaries

| Location | Contents and role |
|---|---|
| Selected private local data root | Complete original releases, source SQLite tables, normalized source records, quarantine, reconciliation and build indexes |
| Netlify `offmenu-corpus` | Static OffMenu selected facts, own IDs, unresolved/review decisions, discovery references, provenance, compressed search indexes and manifests |
| Cloudflare Worker | Read-only queries against Netlify curation; manifest and completed-query cache; checksummed static-file reads; no public corpus database |
| Existing `offmenu-users` | Private account/shared-kitchen state, authentication support and encrypted BYOC connections; public source replicas retired |

Netlify Functions, Edge Functions, Database and Blobs are not required for this
path. Static delivery still uses Netlify bandwidth/web-request allowances.
Cloudflare query compute/cache limits still apply. No claim of unlimited hosting.

Selected facts are explicitly source reported, not independently reviewed or
verified diet qualifications. Renaming a source record is not sufficient curation:
the separate publication projection drops raw source fields, ingredient wording,
unmapped source tables, contributor/proof metadata and original recipe bodies.
Recipe discovery references cannot be automatically planned or cooked. Product
ingredient matches remain unresolved. Licences and attribution remain attached;
OffMenu's schema does not remove upstream rights obligations.

## Manual process

1. Collect the entire permitted named release locally. Reconcile all rows and
   required related tables; preserve original archives and hashes.
2. Run `scripts/exercise-collection.mjs` over every normalized record.
3. Run `tools/data-processing/build_curated_corpus.py` against admitted local releases, choosing
   a new immutable output/version. The publication projection is
   `tools/corpus/curation.py`, governed by `contracts/corpus/policy.json`.
4. Run `scripts/exercise-curated-corpus.mjs` over all curated output. This gate
   checks checksums, source/private payload exclusion, joins and consumer paths.
5. Set `OFFMENU_CURATED_RELEASE` locally to that accepted release directory.
   Run `node scripts/prepare-curated-publication.mjs`. Only accepted checksummed
   curation files enter `dist/curated-public`; local SQLite/originals never do.
6. When publication is separately authorized, deploy that static directory to
   the selected public-corpus site. Verify its identity first; do not relink or
   deploy to the account/authentication project.
7. Verify the live static manifest and indexed queries, then enable the Worker
   `CURATED_CORPUS_ORIGIN=https://offmenu-corpus.netlify.app` setting. Until that
   acceptance passes, the binding remains absent and corpus coverage empty.

Publishing requires the selected hosting account and normal authentication.
These processing steps do not provision hosting or establish that any live
release is active. Never extract connector or CLI tokens from configuration.
