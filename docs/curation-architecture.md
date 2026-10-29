# OffMenu local curation and static delivery

<a id="current-product-design"></a>

## Current product design reference — 25 October 2026

This section is the current requirements/status navigation reference, not a new
tracker, release acceptance or execution grant. The dated 13 October evidence
below is historical. Its original bytes, counts, test claims and deployment
instructions are retained for provenance; they do not establish today's live
availability, English Gold admission, complete countries or current permissions.
Current production/CIX execution remains paused, Normalizer STOP and Sonar
DEFERRED; source rights, ownership and actual platform denials remain binding.

<a id="north-star"></a>

### Established North Star and data semantics

The staged household daily loop and regional integrations are detailed in the
[consumption, inventory and integration design](consumption-inventory-integration-design.md).
They remain design requirements until their stated component acceptance is met.

**Barcode → Product → Ingredient → Recipe → Quantity → Nutrition → Menu → Serving → Consumption → Leftovers → History → Planning → Integration → Ordering → Receipt → Barcode** This is established
owner scope, not a new requirement discovered by this reconciliation. Matt's
reinforcement is `Sentinel_09fbc9f9e40881919333c5ce40dcd754` (25 October
2026, 06:31:47 UTC), followed by the explicit North Star/consumption clarification
and compact wording relayed through Parent/Gateway. Exact later native message
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
relayed through Parent/Gateway.

<a id="normalised-vocabulary-and-nutrition-consistency"></a>

### Shared vocabulary and declared versus modeled nutrition

Use one inspectable, versioned persisted vocabulary projection over the existing common-resource and ingredient/GOLD contracts. Stable ingredient IDs are shared by product mappings and recipe mentions; compounds can contain several independently evidenced ingredients. Consistent English preferred labels retain original multilingual aliases, source versions and reviewed crosswalks. Categories, nutrients, units, preparation and quantity concepts retain their own types, definitions, evidence and unresolved states. Source-import tables and lexical alias lists are not evidence that this populated shared generation is qualified. Declared product nutrition remains a source fact separate from an ingredient-weighted modeled estimate. Consistency checks require compatible quantities or percentage ranges, nutrient definitions and units, product/serving basis, processing yield, uncertainty, rounding and any explicitly qualified applicable threshold evidence. A fat-containing ingredient alone does not refute a fat-free claim; unknown composition is insufficient evidence. Any supported possible discrepancy remains a review signal, not a diagnosis or regulatory conclusion.

This is the existing owner requirement under
`ARCH-CURATED-CORPUS-DELIVERY`, `CORE-BARCODE-CANONICAL-IDENTITY`,
`MEAL-DISCOVERY-DELIVERY`, `NUTRITION-HISTORY-GOALS` and
`SOURCE-FIELD-PERMISSION-POLICY`. Worker56's bounded source assessment identifies
persisted schema/view foundations, but no current qualified populated generation
or new permitted inspection operation was selected. Its prepared queries were
not executed. Existing Gold26 counts describe their dated source-purpose cut;
they do not establish current vocabulary coverage, actual product fit or complete
recipe nutrition. This requirement creates no competing taxonomy, dataset,
implementation, release gate or source-access grant. Source and scanner delivery
continue independently under their existing permissions.

### Existing requirements, owners and current status

Canonical authority remains the existing
[requirement index](/home/user/src/offmenu-data/runtime/control/interim-obligation-index.json)
plus [permanent journal](/home/user/src/offmenu-data/runtime/control/permanent-ledger/events.jsonl),
read via its existing adapter. The bounded status cut used here is sequence
16613, 25 October 2026 06:35:24.619280 UTC. Broad parent states are not component
acceptance or fresh runtime evidence. Worker00 alone integrates this document
patch and records its disposition. Unmapped historical subrequirements use the
existing parent plus this document's anchors, never invented canonical tasks.

| Existing requirement ID(s) / reference | Owner and evidence | Implementation, integration and acceptance boundary |
|---|---|---|
| `ARCH-CURATED-CORPUS-DELIVERY`; this section | Worker13; [ingredient source contract](ingredient-ingestion.md), [recipe/menu source contract](recipe-menu-store.md), [product federation](private-product-detail-federation.md) | Parent state: initial architecture synthesized/bounded measurement active. Source contracts exist at accepted `9b641c5b6048a8c61a2f6eb70eb9d01a2633da14`; canonical ingredient/dish links remain NULL/pending in import contracts. End-to-end North Star qualification/live delivery is not established. |
| `CORE-BARCODE-CANONICAL-IDENTITY` | Worker56, existing independent review/custodian boundaries | Parent retains design endorsements with execution/promotion holds. Identifier recognition or source-native dictionary retention does not prove ingredient mapping. Later scoped code authorizations/receipts remain separate; do not interrupt56's assessment or reinterpret this parent as a global engineering pause. |
| `MEAL-DISCOVERY-DELIVERY`, `HOUSEHOLD-MEAL-PLANNING`, `HOUSEHOLD-DIET-PROFILES` | Gateway binds existing component custodians; Worker56 owns dietary implementation per recipe source contract | Parent rows open/tracking-gap-reconciled. Recipe/menu/profile UI and plan model are source-present at `9b641c5`; diner adaptations, canonical quantities, stock reservations and whole/person nutrition need exact current acceptance evidence. |
| `CONSUMPTION-LEFTOVERS-RECONCILIATION`, `NUTRITION-HISTORY-GOALS` | Gateway binds existing03 producer/confirmed-receipt and history custodians | Existing after-meal/waste scope is extended/reconciled by the North Star, not duplicated. Meal/history/waste UI subsets exist; full component disposition, corrections, period reconciliation and per-person longitudinal nutrition are not established by source presence. Receipt-integration denial remains held. |
| `HOUSEHOLD-DURABLE-SYNC`, `COLLABORATIVE-SHOPPING-LIST` | Gateway binds current caller/transport and shared-kitchen owners | Authenticated membership/roles and kitchen plan projection are source-present; real two-device/offline/conflict and received-stock journeys remain separate acceptance requirements. |
| `SOURCE-FIELD-PERMISSION-POLICY`, `AGGREGATE-HEALTH-PRIVACY`, `REVOCATION-DELETION-RESTORE` | Gateway binds actual source-policy, store/privacy and backup custodians | Existing parents open. BYOC rights, consent, allowed audience, revocation/derivative propagation, retention and restore deletion replay require actual qualified caller/store evidence. API success or a user checkbox is not source-use or publication authority. |
| `UI-ROUTE`, `CORE-APP-SCANNER-DELIVERY`; scanner reconciliation below | Separate direct UI owner for UI-ROUTE; Root/UI owns four current scanner sheets/HTML; Parent owns historical review; Gateway binds device acceptance | Matt has explicitly accepted the latest scanner interface and authorized implementation on localhost7645 for real browser integration review. The earlier final-scanner-approval hold is superseded. Four-device concepts and actual implementation remain distinct; actual serving, backend flows and physical-camera qualification still require their own evidence. Landing/auth remains preparation until scanner local review completes. |
| `IDENTITY-DEV`; existing work item `BETTER-AUTH-REQUIRED-MIGRATION` | Existing identity owner/Worker05 runtime; Worker00 integration | IDENTITY-DEV remains configuration-blocked. Work-item reference is verified in journal events16420/16421 under IDENTITY-DEV, not a separately invented parent. Auth dispatcher/browser seam is source-integrated at `9b641c5`; actual provider configuration, DEV/full-account journeys and live migration are unverified. See [foundation](better-auth-foundation.md) and [runtime seam](better-auth-runtime-seam.md). |

Source-present means only the named subset is implemented in the accepted source
snapshot. Integration is not deployment. Qualification requires its exact current
independent receipt; live availability was not checked in this reconciliation.
Historical recipe consumer publication evidence explicitly excludes independent
culinary/dietary acceptance; source counts are not Gold-admitted counts.

<a id="scanner-reconciliation"></a>

### Scanner source-to-design reconciliation and supersession

Historical sources below are direct Matt messages in
[the 12 October conversation](https://chatgpt.com/c/6acc7fdf-a7bc-83ec-98f0-54206442ff39),
with exact identifiers supplied by Parent/Gateway. History coverage is bounded
and no exhaustive-history claim is made. All rows bind existing
`CORE-APP-SCANNER-DELIVERY`; household/menu/waste rows also bind the parent IDs
above. Latest four-sheet/HTML paths and hashes must be bound by Parent/Root before
claiming visual coverage; Worker19 has not duplicated that visual review.

| Original source / requirement | Actual source versus reported concept | Current disposition / owner |
|---|---|---|
| 12Oct08:58:56UTC `bbb21ffe-00d7-4c8c-a3ed-b3e2b8c341b6`: automatic acceptance, Void/Undo, final receipt check/confirm and PDF export | `public/app.js` autoAccept/displayAccepted hides per-item Add, has Void and separate final receipt/confirm; browser `window.print()` exists, dedicated PDF exporter not proven. Separate shelf-scanner session close is not that confirmation. Parent reports immediate Add/Finish-closes concept conflicts. | Unresolved route/concept semantics. Parent resolves Explore/Checkout/Quick-add before final approval; do not silently choose semantics or label reported design coverage independently verified. |
| 12Oct08:57:04UTC `bbb210ad-da18-4b36-9c2d-bb80472215db`: phone front-lens default on flat bench | Shelf scanner offers handheld rear/bench front/stand rear; source initializes handheld. A screen overlay does not prove physical lens selection. | **SUPERSEDED:** Matt 25Oct06:36UTC (17:36AEDT) explicitly selects **phone rear/environment preference by default**, retaining camera switch and available-camera fallback. No re-ask; do not extrapolate tablet/PC defaults. Exact later message ID unavailable. |
| 12Oct09:00:05UTC `bbb218ce-af67-4d38-b80e-b4c3f6abe644`: configurable vibration/torch/screen/sound/speech | `public/app.js` feedback toggles and capability-bound brief torch pulse exist; source presence does not qualify devices. | Retain optional controls; later owner direction calls for separate steady torch and restrained visual feedback. Parent reconciles historical flash request/current source to latest requirements. No automatic pulse acceptance inferred. |
| 12Oct09:23:45UTC `bbb213f4-c870-40ac-af34-b3ac98a259b8`: custom bench/bowl/storage/household menu preferences | Location/household/menu bindings exist; full custom bench/bowl fields and latest design coverage are unverified here. | Parent binds exact coverage; Gateway binds existing household/menu custodians. New Settings/Profile pages remain deferred. |
| 12Oct10:11:04UTC `bbb21ca6-6ea2-459e-8ea9-6181c644b7c5`: garbage scan/use-by freshness prompts | Existing waste scan requires a matching source-location lot; entered-date/estimated-reminder UI exists. | Full consumption reconciliation remains separate. Entered dates/reminders are not a food-safety guarantee. Parent checks design coverage; existing waste owner retains implementation scope. |

All current scanner corrections apply to **mobile, tablet, desktop and foldable**
artifacts, including the latest overlay/options/chrome, removal of developer hints,
values-only Category/Ingredient-match/pack-size presentation, identity divider,
qualified photo and plain-copy corrections. Earlier mobile-only artifact scope
is superseded. Matt subsequently accepted the latest interface and requested its
realization on localhost7645. Maximize the camera aiming frame within the available
camera viewport and align the actual decoder crop/ROI; a decorative guide alone
is insufficient. Preserve automatic acceptance, Void/Undo, final receipt checkout
and existing application/backend/auth/inventory/source flows; do not substitute
the simulated prototype. This supersedes the earlier pending scanner-approval
gate, but grants no production/main/credential or network-permission change.
Responsive defaults use the available area: mobile remains camera-first with a
collapsible sheet; an open-book foldable, tablet, desktop or wide view presents
useful expanded details without requiring a drag merely to fill blank space.
Preserve explicit user choice, hinge/safe areas and readability, with no fabricated
data or padding. Remove the extra compact “Photo from Open Food Facts” row;
retain required author/source/license access under Source/details. Interpreted
values use the secondary brand/barcode typography and consistent spacing. These
are refinements of the accepted implementation, not new rendered assets.

The exact latest owner message ID is unavailable here; the explicit quotation
was relayed by Parent through the existing Gateway. Root/UI retains artifact
ownership. No duplicate
visual research, rendering, test fleet, source acquisition or engineering pause
follows from this prerequisite.

<a id="feature-communication"></a>

### Feature communication and background-only landing/auth preparation

Owner-selected headline: **From product to pantry to plate**. The former
“From bag to dinner” ad copy is superseded; no ad regeneration or new tagline
selection follows. Exact owner-approved feature copy is the existing
[75-entry key/value asset](../apps/web/assets/feature-copy.v1.json),
SHA-256 `2445a3b24770472a288f1d7c2ec866da93f07bcb938fa39bbdcca4d6e217b4a5`
(13,258 bytes), approval source `Sentinel_01846dd6563081919eaf261c16669512`,
25 October 2026 06:45:23.250881 UTC. Preserve exact keys, values and mapping;
this supersedes earlier draft supporting phrases. Reuse the asset, with no
competing copy store, ad-hoc slogans or wording changes. Display **values only**,
never feature keys. Its proposed rotation is a shuffled cycle without immediate
repeats; future entries carry `*` with the legend **`* Planned`**. Current entries
remain foundation-unverified until availability is reconciled to canonical
delivery evidence before unmarked claims. **Copy approval is not rendering or
implementation approval**, nor proof of operational availability.

Barcode/recipe/nutrition/pantry/planning/sharing source subsets exist at `9b641c5`;
coverage, account membership and source rights limit them. Recall source/import
references exist, but product-matched live alerts remain unverified/planned.
International/nonfood records do not imply complete countries/products or food
ingredient links. English Gold is an admission policy, not a proven consumer
feature; public availability/open licensing never means blanket public domain.

If later authorized, supporting sentences use gentle fade, readable dwell, stable
reserved height, pause control, reduced-motion static alternative and a full
accessible feature list; automatic changes must not repeatedly announce through
a screen reader. Current work is metadata preparation only, with no landing/auth
render or implementation. The completed admin-proof **interface** artifact is
separate and does not establish live delegation.

Detailed, finite preparation evidence (not a replacement requirements store):
[feature/status inventory](/home/user/src/offmenu-data/runtime/layout-migration/worker19/landing-auth-preparation-20261025/feature-status-inventory-20261025.json),
[consumption refinement](/home/user/src/offmenu-data/runtime/layout-migration/worker19/landing-auth-preparation-20261025/north-star-consumption-addendum-20261025.json),
[historical scanner crosswalk](/home/user/src/offmenu-data/runtime/layout-migration/worker19/landing-auth-preparation-20261025/historical-scanner-conflicts-addendum-20261025.json).
The historical crosswalk's unresolved phone-front-default entry is superseded by
the 25Oct06:36UTC owner decision above. Current canonical integration/acceptance
must use Worker00's exact new document/result ledger receipt, not infer admission
from these staged preparation packets.

## Historical execution and architecture evidence — 13 October 2026

The following material is retained unchanged from the accepted preimage. Its
“latest”, “live”, “current”, deployment and cleanup wording refers to its dated
historical checkpoint, not present qualification or authorization.

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

Recovery update, 13 October 2026: the repository and authenticated deployment
are restored. The three-source static curation is live on Netlify and enabled in
the Worker. Residual public D1 rows and raw caches are zero; the private account
aggregate and vault binding are unchanged. Live queries still intermittently hit
Cloudflare CPU exhaustion. The API currently rejects CPU settings as Free-plan
unsupported despite the user's paid-plan context. This remains unresolved;
see `recovery-2026-10-13.json`. The complete OFF archive is verified locally,
with normalization and full-record exercise continuing under a user service.

13 October 2026. This decision supersedes bulk D1 corpus replication and the
prototype Netlify query function. User instructions: manually trigger local
collection and normalization; host only OffMenu curation; use Cloudflare for
request caching. No source datasets in Cloudflare or Netlify.

## Boundaries

| Location | Contents and role |
|---|---|
| Local `/home/user/src/offmenu-data` | Complete original releases, source SQLite tables, normalized source records, quarantine, reconciliation and build indexes |
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
6. Deploy that static directory with the Netlify CLI to site
   `a1df1508-4bb9-4b55-ab1f-88611e456e61`. This is a separate project from
   `offmenu-accounts`; do not relink or deploy to the authentication project.
7. Verify the live static manifest and indexed queries, then enable the Worker
   `CURATED_CORPUS_ORIGIN=https://offmenu-corpus.netlify.app` setting. Until that
   acceptance passes, the binding remains absent and corpus coverage empty.

Netlify CLI authentication is currently unavailable in this execution environment.
The empty target project exists; no curation deploy has been claimed. The CLI's
normal login flow is required; never extract connector or CLI tokens from configs.

## Cleanup checkpoint

Cloudflare `offmenu-open-corpus` database
`a3c9b1fc-bc8d-4c3e-afdf-de78caeeba49` deleted successfully. `CORPUS` detached
from the Worker; settings deployment `82549a5b-a0b0-494b-a540-43bac7c0c878`,
version `268d0f10-00ff-4254-ab58-35d7333bdfdf`. Read-back verifies only private
DB and the unchanged `PROVIDER_VAULT_KEY` secret bindings. Account aggregate
remains one row, summed revision 2, 821 bytes. Authentication endpoint unchanged.

Deleting the remaining 15,312 `public:*` unified records returned Cloudflare
7500 (D1 free-tier daily write quota). Remaining old source caches: products 14,
price observations 1; `public_products` 0. These are pending deletion, not removed.
Never drop the shared account DB or mixed `unified_records` table. Keep the
40 existing curated application recipes and private/application tables.

`apps/web/server/provider-data.mjs` retires national source replica serving and excludes
replica counts from current operational coverage. `apps/web/server/handler.mjs` stops raw
product/price response cache reads and writes. Deploy and verify that code before
claiming those retirement changes are live.

## Collection correctness checkpoint

The initial OFF normalization used Node readline, which splits valid JSON
strings at Unicode U+2028/U+2029. Its reconciliation and all-record exercise are
superseded. The original complete archive remains intact. `scripts/gzip-jsonl.mjs`
uses literal LF and propagates gzip corruption errors. Tests verify Unicode
separators, multibyte text and truncated gzip. The full OFF release is being
recollected into `off-2026-10-12-lf`; no accepted final counts yet.

The unfinished curation version 2 was stopped and its reproducible output removed
before upload. It must not be accepted or published. Full curation rebuild follows
the corrected OFF reconciliation and all-record consumer exercise.
