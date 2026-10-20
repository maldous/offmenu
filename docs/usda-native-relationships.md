# USDA native relationship validation preparation

This source-only adapter implements Task B without changing the recipe/menu
validator, field-origin emitter, normalizer, source contract factory, consumer or
runtime. It performs no file, database, network or model IO and emits no graph
edges. All real endpoint/context/ingredient/subfield/witness evidence is still
absent. No real policy or authority factory is installed.

`native_product_relationship_errors(record, assertion, policy=None,
resolver=None)` returns fixed diagnostic tuples. Its default is
`usda-relationship-unbound`. Missing review authorities or origin policy pins
also refuse before any resolver use. A successful empty tuple means the selected
metadata checks agreed; it is not execution, rights, mapping or gold admission.

## Existing interfaces reused

`NativeProductPolicy` binds an already selected native/private USDA
`SourceContract`, its independently selected qualification digest, exact product
snapshot digest, candidate line, original asset, origin policy pins and a typed
native-input review witness. It is an application object, not a JSON-loaded
source registration. Existing private lookup `_binding` checks the native
qualification/contract/fixture scope; the local selected product schema and
provenance must match. Unknown-retained acquisition stays unknown.

`ResolverInventory` snapshots already selected bytes, `ResolvedClaim` objects,
role mappings and `ReviewedWitness` objects. It implements the needed subset of
the existing English `Resolver` surface. It does not parse a sidecar into review
authority or invent a second protocol. Caller mutations cannot change the
stored inventory; returned claim/witness objects are copies. Existing English
`_Check.claim_context` and `_Check.relationship` enforce qualified endpoint
versions, role/IRI resolution, source-product assignment context, food form and
affirmative exact relationship witnesses. No existing English source file is
edited; these private helper dependencies must be pinned/reviewed with this
adapter by any later application factory.

The native input is `product.data`/`product.provenance`. It is never rewritten
into a `recipeTemplate`, `menuTemplate` or invented `record.source` wrapper. The
native-input witness uses the same typed `ReviewedWitness` mechanism with a
source-specific selection scope: exact source/release/record/original,
candidate/line/pointer, snapshot digest, qualification/contract, provenance,
origin inventory digest and private validation purpose. This selection scope is
review metadata, not a graph class or public relationship protocol.

## Origin and relation boundary

The selected product must have complete existing `fieldOrigins` coverage under
selected origin policy pins. `field_origin_errors` is reused unchanged. The
ingredient field must trace to the existing branded-food CSV ingredient
coordinate convention; a constant or primary food description cannot substitute.
These are structural and selected-evidence checks, not a database read or
reconstruction. A separately qualified Task A packet/input-selection review must
establish the actual coordinate, value, join, member and transform fidelity.
This module cannot make fabricated coordinates trustworthy by checking their
hashes or syntax.

The assertion uses the existing `productIngredientLinks` fields and relations.
Only reviewed `declares-ingredient`/`refers-to-ingredient` assertions with selected
evidence are eligible for success. Proposed/unresolved/rejected assertions stay
held; no state is rewritten. The final affirmative witness additionally binds
the native input, exact product and ingredient claim versions, product
formulation/package/market/effective period, food form, and ingredient field
origin/text digests. Qualified endpoints alone do not qualify the relationship.
Opaque IDs are never cast to graph IRIs. Text alone is never parsed into concept
IDs or quantities. A serving amount is not an ingredient amount.

The source-field binding covers the exact whole ingredient field. It does not
provide individual word/token offsets, ingredient quantities or a qualified
subfield interface. Narrower claims need actual independently qualified
subfield evidence and a separately reviewed binding; recipe page coordinates
must not be fabricated for CSV data.

## Deliberately missing real bindings

The existing selected private lookup does not contain full field origins,
qualified canonical product/ingredient roles or affirmative relationship
witnesses. It cannot satisfy this API by itself. Task A remains source-owner
work: selected-record origin caller plus actual qualified database/member and
derivation context. A later factory must select a qualification valid for the
exact origin-enriched/selected output; the input-selection witness must establish
that exact snapshot's membership and provenance, not bless a rehashed cache or
substitute an old whole-source receipt for a changed output.

Real qualified source-product assignment and formulation snapshot, package,
market/effective period, ingredient identity/food form, source field/subfield
evidence and exact affirmative endpoint/version witnesses remain required.
Review authorities are empty by default. Constructing dataclasses, fingerprints,
qualification-shaped JSON or a resolver inventory establishes none of that
authority. The caller must select the objects independently in reviewed code;
this module supplies no real-source grant, constructor, registry, schema
publisher or admission callback wiring.

The API checks one already bounded snapshot/assertion using explicit evidence
read/byte bounds inherited by the shared checker. It does not scan a full
candidate or qualify runtime capacity. Private evidence stays private. All
SAME11, source/privacy/custody/ownership/denial/mandatory auto_review and
execution/promotion/production/CIX holds remain unchanged.

PR76 assertion correction: before copying the record/assertion/policy or using
the resolver, the caller assertion must have the existing flat closed shape.
Its evidence-list item count is additionally capped by `max_evidence_reads`,
including repeated pins even when evidence-byte caching would avoid another
resolver dispatch. Aggregate built-in string lengths are capped before JSON
serialization, and the exact serialized assertion must fit
`max_evidence_bytes`. This bounds temporary escaping/UTF8 expansion as well as
subsequent copy, evidence traversal and assertion fingerprint work. Oversize
returns `usda-relationship-assertion-bound`; malformed nested shapes refuse.
Small repeated pins remain supported with their exact matching review.
This correction does not change upstream native-record qualification or claim
that arbitrary trusted resolver/policy code has an OS CPU/memory boundary.

## Synthetic verification and review

Tests use invented in-memory product/origin records, qualification snapshots,
claims, role contexts and witnesses. The fixture qualification snapshots model
already qualified synthetic inputs; this suite does not perform source
qualification or confer authority through self-fingerprints. No real lookup,
original, candidate, database, profile or restricted sample is read.

Tests demonstrate a supported native case, default/empty/missing authority
refusal, stale input/qualification/origins, primary-row/constant substitutions,
missing endpoints, wrong role/context/form, non-affirmative/stale/wrong-input
witnesses, fixture mismatch, inventory isolation, evidence bounds and no IO.
Existing recipe/menu semantic suites verify unchanged behavior separately.

This is author evidence only. Fresh independent review of the exact source pair
and Worker00 integration/current gates remain required before acceptance.
