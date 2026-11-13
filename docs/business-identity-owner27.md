# Worker 27 business identity consumer handoff

Pickup for coordinating root `01a137cf-2242-761d-8fd7-6e6fc5658013`.
Branch `feature/business-identity-consumer-27-20261014`, fresh locked fetch exit 0
started `2026-10-14T10:16:58.512059+00:00`; resolved origin/develop base
`908ca373dfc918f2e33fd5e44260879577bed5c5`.
Prior clean dataset branch and commit `38ff7e45179e4eefae4af0f637c5262869db4968`
are preserved. Retained helper full pin `7965b02a3d48b62e881e26d8c11d6f34fc823df7`
verified as a commit; not cherry-picked or adopted without independent review.
No prior artifacts/untracked files were overwritten; prior status was empty.

## Boundary and use

`cloud/business-identity-owner27.mjs` exports pure `evaluateBusinessIdentity`.
It projects owner-reviewed source relationship identities rather than matching
names. Input identities carry sourceId/recordId (strings retaining leading zeros),
canonicalId and explicit company/brand/site/product role. Relationships carry
exact source-qualified subject/object references, ID and predicate. Both carry
sourceRecordId, rightsRevision, jurisdiction, market, validFrom/freshUntil,
optional validUntil, matchStatus, reviewStatus and status. Dates are real ISO
calendar dates, inclusive start and exclusive end. Evaluation requires explicit
finite now, market and jurisdiction; arrays are bounded to 1,000 rows each.

Only explicit status active, reviewStatus admitted, matchStatus verified rows
are eligible. These fields are trusted source-owner decisions, never permission
obtained merely by accepting a browser payload. Missing/unsupported states yield
unknown. No raw status normalization or upgrade is performed. Ambiguous active
aliases and conflicting canonical roles withhold identity resolution. Names are
unused. Control/accounting-parent/minority are separate from operation, franchise
and licensing; minority traversal is opt-in. Invalid competing parents are
excluded before control conflicts. Cycles terminate; missing parents are unknown,
not independent or ultimate owners. Matching a requested target does not establish
ultimate/beneficial ownership. Original relationship and mapping objects accompany
evidence for source/date/rights review without changes to input. Errors refer to
unusable rows; caller retains the original projection, including rejected rows.

## Exact remaining production delta: owners 03/02/04

Actual inspected entry point: `cloud/catalogue.mjs::catalogueRoutes`,
POST `/api/catalogue/evaluate`. It currently calls generic ownershipPath on
`b.evidence` directly. `public/data-workspace.js` posts the evidence form there.
No production caller imports this new module. No reservation/integration map was
found in this checkout or the task artifact filenames searched. No reservation
or coordination acknowledgment has been obtained; this document is the proposed
integration handoff, not a claim of completed coordination or shipped behavior.

Owner 03 must reserve the catalogue route before modifying it. Minimal delta:

1. Import evaluateBusinessIdentity from `./business-identity-owner27.mjs`.
2. For an ownership query, obtain an owner-reviewed, rights-admitted projection
   through an owner-controlled server loader using a stable projection ID. Resolve
   subject/target as sourceId+recordId tuples; do not reinterpret display names or
   bare canonical IDs as source matches. Existing generic b.evidence must not be
   upgraded into this input. Missing loader/projection returns ownership unknown.
3. Evaluate with server time and explicitly selected market/jurisdiction:

```js
const evaluated = evaluateBusinessIdentity(admittedProjection, {
  subject: sourceSubject, target: sourceTarget, now: Date.now(),
  jurisdiction: selectedJurisdiction, market: selectedMarket,
  includeMinority: explicitlySelectedMinority
});
// Route ownership = evaluated.ownership; retain evaluated.evidence/errors internally.
```

4. Preserve existing origin/body bounds and other qualification output. Return
   only rights-permitted evidence details, relationship type, effective interval
   and unknown reason to the UI. A private projection must never enter public cache.

Owner 02 owns the loader/schema decision: no business identity catalogue kind or
server loader exists at this pin, and this increment adds neither schema nor
storage. The loader must preserve source/release provenance, licence entitlement
and invalidation; metadata discovery CSV is not an admitted projection. Owner 04
must scope the loader to a verified account/session if private evidence is used.
Existing personal evidence writes force candidate status and cannot be promoted
by the client. This adapter performs no persistence or session processing.

Required owner entrypoint checks after reservation: route with admitted projection
returns evidenced path; no projection/client-forged admission returns unknown;
wrong account cannot read private projection; missing/invalid/expired identity
returns unknown; invalid competitor does not suppress active parent. These HTTP
checks have NOT run because no loader or hook is adopted. Independent review of
both retained helper and this immutable candidate is required before adoption.

## Checks and custody

Actually run with inherited GIT_* stripped:
`node --test --test-isolation=none tests-web/business-identity-owner27.test.mjs`:
6 passed, 0 failed. In-memory synthetic fixtures only; zero child test processes,
no source acquisition, provider data, account storage or corpus copies. Tests cover
source namespace/leading-zero identity, state/admission, temporal crosswalk,
role/alias conflict, relationship scope/duplicates, active conflicts/cycles,
minority boundaries and discovery metadata refusal. No live-provider or production
entrypoint acceptance is claimed. Diff checks run before the attributed scoped
commit. No central file or schema changed.

Primary checkout before: HEAD and main ref
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; index SHA-256
`4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`.
Final readback must match. Filesystem controls actually supplied: unrestricted
danger-full-access; network enabled; mandatory reviewer auto_review. Separate
approval policy unavailable; no named profile inferred. Controls unchanged.

## Worker 09 correction follow-through — 15 October 2026

Prior immutable candidate c9277fd8e06c1d16fcd98e04736d47dfd1f58d2c remains the
parent on the same branch. The retained independent review identified the following contract corrections.
W09-BI-F1 arose from the generic company/brand child fallback being applied to
accounting-parent; this predicate now requires company -> company explicitly.
An evidenced brand-control -> company -> accounting-parent chain remains usable;
brand accounting consolidation alone is unknown with a role mismatch diagnostic.
W09-BI-F2 arose from JavaScript truthiness in the minority filter and generic-helper
option. Both now use one normalized literal-true Boolean. Unsupported strings,
numbers, null, arrays and objects withhold minority traversal; they do not coerce
into opt-in. The caller must still construct an explicit Boolean from a genuine
user selection, never a truthiness conversion of untrusted text.

Before editing the module, two new W09 regression groups failed (exit 1, 0/2
passed). After the narrow correction, the full focused file passed 8/8, exit 0:
node --test --test-isolation=none tests-web/business-identity-owner27.test.mjs.
Both commands stripped inherited GIT_*; tests used only in-memory synthetic data.
No generic catalogue, loader, source admission or central consumer was adopted.
Same Worker09 independent bounded delta review is required at the new full pin;
prior review is not silently promoted to approval. Owner02/03/04 HTTP integration
and production/whole105 gates remain pending/STOP as previously documented.

Worker24 review and its explicit-file checkpoint outside this checkout remain
intact. Source c927 and prior dataset/helper history remain reachable. Backup
eligibility uses the existing Worker09 private-origin metadata/preservation receipt
for maldous/offmenu (visibility private) and an exact matching local origin URL;
CLI API auth was unavailable. Only this branch's explicit three owned code/test/doc
files are checkpointed. No secrets, corpus or generated caches are added. Final
handoff records push result and independent remote SHA, not an inferred backup.
