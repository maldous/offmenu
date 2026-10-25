# Consumption, inventory and external integration design

This is the bounded phase-two design and phase-three roadmap reference under the
existing OffMenu requirements. **No domain implementation, migration, renderer,
source/store operation, vendor connection or purchasing is authorized here.**
Worker00 alone integrates the document; phase one remains the priority.

Established North Star (owner scope, preserved exactly):

**Barcode → Product → Ingredient → Recipe → Quantity → Nutrition → Menu → Serving → Consumption → Leftovers → History → Planning → Integration → Ordering → Receipt → Barcode**

Phase one runs through Menu. Phase two designs the subsequent daily household
loop; phase three prepares interfaces to others. The companion
[curation architecture](curation-architecture.md) is integrated in this source
change from Worker19's proposed reference SHA256
`2e6a953c2167d3126b89886a572cb6ecc72d01d2089ca0d5ef7ca383b22ea910`,
with Worker00's repository-copy link and later owner UI-approval refinements.
That source presence is requirement context, not runtime or end-to-end feature
acceptance. This document preserves its scanner decisions and historical evidence.
The latest owner loop `Sentinel_dce80a65211481918f30f3e860727b03`,
25 October 2026 06:51:02 UTC, supersedes the earlier shorter wording and is
preserved exactly above. No separate tracker or source-use grant follows.

Accepted ordinary code considered here is
`9b641c5b6048a8c61a2f6eb70eb9d01a2633da14`. Existing
[ingredient ingestion](ingredient-ingestion.md), [recipe/menu source store](recipe-menu-store.md),
[meal-plan adapter](meal-plan-owner19.md) and [intake history](intake-history-owner25.md)
are contracts/source and scoped historical receipts, not newly qualified personal
data, runtime or end-to-end nutrition. Worker56's phase-one assessment supplies
scoped metadata/evidence; no repeated corpus inspection or duplicate schema follows.

<a id="phase-two-household-loop"></a>

### Phase two design: serving, consumption, leftovers, history and planning

**Design/preparation only.** Phase one through Menu remains the delivery priority.
This extends the existing North Star above; it is not a second schema, tracker,
clinical model, implementation, migration or UI approval. The existing canonical
parent IDs below and their prior requirement references remain the authority.
Gateway selects actual component owners; Worker00 alone integrates this reference.

#### Phase-one interface and present evidence boundary

Reuse the selected source/Gold resource IDs, source versions, mentions and typed
relations. The existing path is product entity/resource/source occurrence →
`represents`/`contains` → canonical class ← `canonical_ingredient` ← source mention
← `mentions` ← recipe occurrence, retaining branch choices and supporting evidence.
It is not name equality, browser aliases, culinary suitability or complete
ingredient composition. Phase two consumes a qualified selection, not another
ingredient resolver.

The phase-one producer must supply exact recipe/source/version/occurrence and
chosen variant/branch references; selected product/ingredient observations and
actual-fit evidence; ordered preparation/component references; raw and normalized
quantities with dimensional units, preparation state and uncertainty; yield and
serving basis; nutrient-definition/source/basis/version and coverage; and the
applicable rights, qualification and correction receipts. These are conceptual
consumer requirements on existing contracts, not a new JSON/SQL schema or a
caller-provided `qualified:true` permission grant. Missing authority means an
explicit unavailable/unknown result, while useful source-faithful preparation
continues independently.

Worker56's frozen phase-one handoff is metadata-only. Its recorded Gold26 cut
(receipt SHA256 `fee48b49301c164ae5a6932403df35617dc015e6845a90dd3f17eef77b0ed5ae`,
journal16295, 25Oct12:06:13+11:00) contains376 documentary recipes,
1,665 mentions and13 canonical classes, but zero admitted positive actual product
fits/complete executable recipes. It is not a fresh global census or current
alias-store generation. Actual recipe/per-serving nutrient allocation remains
unqualified. Hypothetical ingredient-input sums are not meal, cooked-yield,
portion or actual-intake totals. No source/store access follows from these counts.

#### Reused domain roles and interfaces

| Existing role/contract | Required phase-two distinction and evidence |
| --- | --- |
| `MealPlan` and household/person profile | Intent, attendance, selected recipe/variant, person portion proposal, date/timezone, cost/access/equipment constraints and review status. A plan reserves nothing or records no intake unless its existing separate operation does so. |
| `Batch` and prepared-stock allocation | One versioned preparation outcome, component allocations, original recipe/product/source links, measured/reported yield and units, preparation time/state, stock location and uncertainty. Raw-to-prepared transformation is distinct from stock transfer. |
| `Portion` / `ServedFoodEvent` | A person/component amount allocated and served from a batch. Serving is not eating. Keep plate allocation and unserved stock separate. |
| `IntakeEvent` and component outcome | Actual reported eaten quantity, component uneaten quantity and its separately selected outcome; or explicit unknown. Record reporter/subject authority, source/batch/portion/event references and measurement method. A whole-meal completion percentage cannot silently scale every component. |
| `WasteEvent` / saved or transferred stock | Distinguish discarded, saved, transferred and unresolved remainder. Saved food returns to selected storage as a prepared-food batch linked to its parent; a transfer is neither purchase nor intake. |
| Existing private history/goal interface | Period/person projections of corrected events with coverage, source/quantity/nutrient uncertainty and configured target version. History informs proposals; it cannot create a restriction, diagnosis or actual purchase. |

Keep user-declared allergies, intolerances and other safety constraints separate
from preferences/dislikes and chosen goals. Each assertion has its type, scope,
source, validity/version, consent and uncertainty. Do not promote a dislike, text
alias or repeatedly avoided component into an allergy. A person may request a
strict preference, but it remains a chosen constraint rather than clinical fact.
Safety evidence, ingredient completeness and package/cross-contact limits are
explicit; absence of a known conflict is not a safety guarantee. Unknown evidence
cannot be cleared by omitting an optional ingredient or sharing a family dish.

Family planning may propose a common base plus distinct person variants and
portions. Bind each variant's changed components and quantities to its own
recipe/version and evidence. Check the actual selected ingredients/preparation
and cross-contact context for each person; don't inherit the base dish's apparent
suitability. Preserve cost, access, portion size, alternatives and incomplete
records as possible explanations, not inferred health conditions.

#### Event and stock reconciliation contract

The proposed event roles are **planned, prepared, served, eaten, component
uneaten, saved, discarded, transferred and unknown/unlogged**. They refine existing
operations; they are not new canonical task IDs or a new event service. Every
operation binds an immutable event/operation identity, household and authorized
subject, recipe/batch/component/portion versions, occurrence time and timezone,
recording time, quantity/unit/basis, source/measurement evidence, revision and
correction/supersession links. Preserve source-event time separately from ledger
write time. Apply the existing account/consent/revision protocol at the actual
durable write, not an unverified client account string.

Within one comparable prepared component/basis, account for unserved storage,
on-plate remainder, eaten, discarded and outward transfers; incoming transfers
retain their own linked origin. Unknown amounts are explicit unresolved balances,
not zeros. Do not compare raw ingredient weight with cooked yield or add unlike
units. Nutrient allocation needs the chosen product, food state, component amount,
basis, definition and yield evidence; a heterogeneous plate's leftovers cannot
be treated as a uniform fraction without support. Unknown allocation remains
unknown even when the stock count is known.

Saving plate leftovers transfers a known remaining amount back to the selected
pantry/fridge/freezer/custom location. Preserve parent batch, recipe/version,
original ingredient/product observations, quantity/unit/servings and nutrient
coverage, preparation/storage timestamps and conditions, corrections and
uncertainty. Never default to a location or promise safe storage/shelf life.
Unserved stock already remaining in inventory is relocated/split, not added again.
Current `serveBatch` retains its saved remainder in batch stock through
`draw=portions-saved`; an adopter must reconcile that existing representation
before a saved-back event, rather than duplicate it. Reheat, split, share, consume
and discard each reference the remaining batch/version and do not count the
same amount twice. Reheat metadata is not a new purchase, intake or automatic
nutrition/safety transformation.

Use a stable operation identity on replay. The same action/digest adds nothing
twice; a changed replay rejects/conflicts, and an uncertain acknowledgment is
reconciled rather than retried under a new ID. Corrections preserve prior evidence
and update affected stock/person/period projections together under their existing
revision boundary. Undo after serving/consumption or a descendant transfer needs
explicit reconciliation/compensating lineage; it must not resurrect consumed
stock or silently erase history. This specifies acceptance, not an implemented
transaction or a new atomicity framework.

#### Logical interfaces for later implementation

These are versioned design roles, not exported methods, a replacement schema or
an additional event service. Bind their exact eventual shapes to the existing
owner's contract and authorization before implementation. Each mutating role
uses the stable operation identity, expected revision and verified purpose/consent
boundary above; a descriptor never creates that authority.

| Logical interface | Required input / explicit result |
| --- | --- |
| Receive phase-one meal selection | Exact qualified recipe/version/branch/product/quantity/yield/nutrient receipts, or typed unknowns. Result identifies which components, quantities and nutrient allocations are actually eligible; structural links are insufficient. |
| Propose family/person plan | Existing household participation and scoped constraint/goal versions, source selection, portions, cost/access and uncertainty. Result is a reviewable intent/variant set, not stock, consumption or safety clearance. |
| Commit preparation / allocate serving | Accepted selection and actual preparation/batch evidence, then person/component quantity. Result separates prepared inventory, on-plate allocation and unknown outcomes; serving creates no intake. |
| Reconcile component outcome | Portion/event reference plus reported eaten, uneaten and saved/discarded/transferred/unknown amounts and selected storage destination. Result is a consistent stock/intake/waste projection or explicit unresolved balance/conflict; no uniform-meal scaling assumption. |
| Correct, undo or replay | Prior immutable event, expected revision, correction reason and affected descendants. Result is the same acknowledged replay, a compensating projection or a conflict needing reconciliation; never a second stock/intake effect. |
| Read history / propose next plan | Authorized person/period, source/target versions and coverage. Result separates known contribution, unlogged/unknown data and proposed changes with provenance. No diagnosis, automatic restriction, purchase or target mutation. |
| Export / revoke / restore | Current purpose/consent/source-rights selection and scope. Result is the minimum permitted projection or denial, with existing deletion/revocation/restore semantics; no blanket household or AI export. |

#### History, privacy and planning

A missing log is not zero intake; served is not eaten. The current manual recipe
history path's `completion ?? 100` default conflicts with explicit unknown
consumption and is a concrete later correction, not behavior accepted by this
design. Keep planned, recorded consumed and unknown-consumed buckets separate.
Compare only qualified, coverage-described recorded contributions with the
person's selected configured target/version. Below-target recorded contribution
with incomplete logs is a recorded-intake gap with unknown actual intake, never
a deficiency diagnosis. Keep missing nutrients/amounts and uneven logging visible.

Repeated recorded avoidance may suggest **user review** with its supporting
events and logging/cost/access/portion context. It never changes a restriction or
target automatically. History can propose family/person plans, reviewed
substitutions and leftover reuse; preserve intent versus accepted action and
uncertainty. No medical, safety, affordability or dietary-completeness claim is
inferred from ranking or history.

Consent and authorization apply to the actual person, household, purpose and
operation at read/write/export time. Reuse existing membership/roles and intake
consent interfaces; kitchen membership alone does not reveal private profiles,
provider data or individual health reasons. Use minimum shared compatibility
information, scoped authorized delegation and separate private person history.
Fence account switch/revocation with writes and cached reads. Correction, audit,
export, deletion/revocation and restore replay follow the existing policy, with
source rights and derivative/cached-export effects retained. Audit retention is
not permission to keep withdrawn private content indefinitely.

#### Acceptance scenarios and staged existing backlog

These are proposed acceptance criteria using authored design fixtures, not test
execution or current domain acceptance. No real person, source body or store was
read. Component roles and quantities are fictional; no recipe nutrition was
calculated.

| Existing requirement references | Scenario / next bounded output and dependency |
| --- | --- |
| `MEAL-DISCOVERY-DELIVERY`, `HOUSEHOLD-MEAL-PLANNING`, `HOUSEHOLD-DIET-PROFILES`, `P1-02`, `P0-04` | Propose a shared base and person variants. Missing actual ingredient/package/cross-contact evidence leaves safety unresolved; preference changes remain user choices. Existing household/recipe custodians supply qualified selection and current consent before implementation. |
| `CONSUMPTION-LEFTOVERS-RECONCILIATION`, `P0-06`, `P2-05` | Fictional prepared component8 units: serve3, eat2, save0.5, discard0.5; unserved5 stays stock and saved0.5 moves to selected storage. Later eat0.25 and discard0.25 from the saved batch: stock5 + eaten2.25 + discarded0.75 =8. Saving adds zero purchase/intake; duplicate save/receipt adds zero. Reconcile legacy already-retained saved stock first. |
| `CONSUMPTION-LEFTOVERS-RECONCILIATION`, `NUTRITION-HISTORY-GOALS`, `P0-06`, `P2-06` | Blank completion/component outcome stays unknown, including the manual history route. Separately account for eaten components and uneaten outcomes; a later correction reprojects the affected person/period without duplicating intake. Existing history/consumption owner addresses the named default and durable integration; no implementation is selected here. |
| `NUTRITION-HISTORY-GOALS`, `P2-06`, `P1-02` | Incomplete logs/unknown nutrient allocation prevent complete daily claims. Repeated avoidance produces an opt-in review proposal only. Planning shows source, coverage, portion/cost/access uncertainty and never creates a diagnosis or restriction. Requires56's actual qualified phase-one calculation/fit interfaces, not a generated label example. |
| `HOUSEHOLD-DURABLE-SYNC`, `P0-05`, `P0-04`, `TRUST-04` | Duplicate/lost acknowledgment, conflicting correction, cross-account switch and descendant-batch undo preserve exact identities, fail closed and reconcile without stock/intake duplication. Reuse current durable-state/consent caller contracts; synthetic adapter success is not a live two-device proof. |
| `SOURCE-FIELD-PERMISSION-POLICY`, `AGGREGATE-HEALTH-PRIVACY`, `REVOCATION-DELETION-RESTORE`, `TRUST-04` | Unauthorized member/AI export receives no private person profile; consent/source withdrawal prevents reappearance through caches/restore. Actual privacy/store owner supplies scoped read/write/export/recovery evidence. Existing receipt-integration denials are not retried through another sender/path. |

Gateway binds existing component owners and records dispositions in the same
ledger. This staged design backlog creates no new dispatcher, owner, canonical
task or automatic job. Phase-one source ingestion/qualification and unrelated
engineering continue under their existing independent authorizations.

<a id="phase-three-integration-roadmap"></a>

### Phase three annex: integration with others

This is a staged roadmap/interface annex to the same design task, not permission
to connect accounts, sign up, provision credentials, purchase, submit an order,
run MCP services or mutate stock. DoorDash and Amazon are examples supplied by
the owner, **not verified support**. Current third-party application/auth/runtime
components are distinct from future customer business integrations.

The phase-three loop segment is **Planning → Integration → Ordering → Receipt → Barcode**.
Its operation stages remain draft list/cart/order, explicitly approved/submitted,
fulfilled, physically confirmed receipt, then Barcode scan/reconciliation.
Retail catalogue, quoted availability, ordered items, seller acceptance and a
fulfilment notice never establish household stock. Only actually received goods
reconciled by **Barcode scan before stock** can
enter inventory through the selected qualified identity/receipt contract. A
receipt or arrival awaiting scan/identity/quantity reconciliation remains pending,
not stock. A scanned unexpected/unknown product may remain source-bound stock
requiring review only where that existing contract permits it; it is never an
inferred ingredient, safe substitution or invented barcode.

Under `ARCH-CURATED-CORPUS-DELIVERY`, `COLLABORATIVE-SHOPPING-LIST`,
`HOUSEHOLD-DURABLE-SYNC` and `SOURCE-FIELD-PERMISSION-POLICY`, prepare a versioned
capability descriptor per country/region, marketplace, service area, currency,
tax/fees, units, pack basis, language, fulfilment, terms/source-use and account
consent. Unknown/unsupported/not-configured is explicit. A global brand does not
imply a global catalogue or API. Select lawful permitted public/open standards
and import/export formats with exact versions, canonical/source identifiers,
units, provenance and conformance evidence; reuse accepted project contracts,
and do not describe an unqualified vendor adapter as standards compliant.

Customer-owned connections/BYOC use scoped revocable secret **references** through
the existing secure owner boundary, never shared plaintext credentials in
schemas, logs, prompts or exports. Capability/connection selection must bind the
actual customer, country/account, purpose and current authorization. An import
retains source identifiers, version, units, unknowns and rights rather than
silently merging by name or barcode. No actual adapter/account has been selected
or verified by this design.

Versioned interfaces should separate capability discovery, permitted catalogue
read, list/cart draft, quote, explicit approval, submission/status reconciliation,
receipt reconciliation and export/revocation. Each has an existing-policy-bound
read/write purpose and minimal DTO, not blanket AI access. MCP preparation for
authorized AI uses separate read, draft and consequential-write capabilities;
planning assistance or an export grant is not purchasing or private-profile
permission. No protocol server/tool implementation or credential access follows.

Before a consequential order, obtain the applicable explicit confirmation of
seller/account, exact items/pack quantities, substitution policy, total currency,
tax/fees and shipping/address reference, bound to the current quote/version.
Changed price/items/seller/substitution/address requires fresh applicable
confirmation; an unknown submit outcome requires reconciliation with the same
operation identity, not a new order. Retain allergy/safety constraints separately
from preferences; never substitute automatically based on a name, category,
price or supposed equivalence. An unavailable safe/qualified alternative remains
unresolved.

Receipt reconciliation binds the actual order/fulfilment/receipt-line occurrence,
observed barcode/product/source reference, actual quantity/unit/pack and
substitution outcome to the plan. Confirm actual arrival, Barcode scan,
identity/quantity reconciliation and selected
destination before a retry-safe stock operation. Do not bypass Barcode by copying
a retailer catalogue product or guessed name directly into stock. Duplicate
receipt replay adds zero; partial
arrival, returns, missing items, changed packs and later corrections retain their
lineage and unresolved identity/fit. Receipt confirmation is neither eating nor
nutrition acceptance. Existing receipt-route denials and household/source rights
remain binding; design is not an alternative execution route.

Staging under those existing IDs: first define a permitted country/service-area
capability and standards/terms cut; then isolated authorized read/import/export
contract preparation; then customer-scoped draft/quote and approval semantics;
finally independently qualified order/status/confirmed-receipt integration when
explicitly selected. Security/privacy/correction/export criteria also bind
`AGGREGATE-HEALTH-PRIVACY` and `REVOCATION-DELETION-RESTORE`.00/Gateway retain
current owner selection and reconciliation; no new integration owner or work item
is created here. These dependencies do not interrupt phase one or authorize
phase-three implementation, spending, live tests or vendor-support promises.


Feature-copy boundary: the single approved75 asset is
`/home/user/src/offmenu-data/runtime/layout-migration/gateway/approved-feature-copy-20261025/approved-feature-copy.v1.json`,
SHA256 `2445a3b24770472a288f1d7c2ec866da93f07bcb938fa39bbdcca4d6e217b4a5`.
Preserve its exact key/value mapping; Worker00 owns versioned
`public/feature-copy.v1.json` placement, crosslink and ledger at its writer boundary.
That selected future repository location is not a placement claim by this design.
This design neither copies it into another asset nor rewrites slogans. Future
values-only rotation marks planned capabilities with `* Planned`; actual
availability must be reconciled before unmarked claims. Copy approval grants no
rendering, implementation, account connection or purchase approval.
