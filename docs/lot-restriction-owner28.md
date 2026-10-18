# Lot restriction consumer — candidate for independent review

Pickup: feature/lot-restriction-consumer-28-20261014, fresh locked fetch exit 0
at 2026-10-14T10:16:52.343467+00:00. Base
908ca373dfc918f2e33fd5e44260879577bed5c5. Root handoff:
01a137cf-2242-761d-8fd7-6e6fc5658013.
Retained helper pin verified: e829f61c181a5965ffba70462433d4b446f226c7.
Dataset branch 606385a70f89d7f57309ab3e2964fb4633c87ed2 is preserved.

Gap: cloud/catalogue.mjs:19 accepts request-provided assertions for evaluation
without binding a selected inventory lot or saved preference provenance.
New cloud/lot-restriction-owner28.mjs accepts only lotId/preferenceId. It authenticates
the account, checks Origin, caps streamed JSON at 4096 bytes, loads account-owned
lots/products/preferences and binds product subject, actual lot code, source ID,
preference source, timestamp and revision. It delegates assertion qualification
to an injected evaluator. No raw request assertions or dataset metadata can be
promoted to admitted evidence. Returns no-store decisions without medical or
cross-contact guarantees, and never permits automatic selection.

## Exact owner integration delta (not applied)

Owner 03 production map must reserve the caller hook; owner 02 owns central
handler/schema changes. Owner 04 must supply a session-derived account loader.
No central path reservation or persistent mapping approval has been received.

After independent review of BOTH the retained helper and this new candidate,
owner 02/03 imports createLotRestrictionConsumer into the production handler and
constructs it with existing verifiedUser, a server clock, the reviewed evaluator,
and owner 04's loadAccount(owner) service. Before the existing catalogueRoutes
dispatch, insert:

```js
const restrictionResponse = await lotRestrictionRoute(request);
if (restrictionResponse) return restrictionResponse;
```

Loader contract: {owner, market, evidenceConsent, lots, products, preferences,
assertions, policies}. Lots require {id,owner,productId,lotCode}; products require
{id,owner,sourceId,assertionSubject,matchStatus:'verified'}. Preferences require
{id,owner,sourceId,revision,recordedAt,rule}. Assertion/policy DTOs match the retained
helper contract, including private display/derive permission and current scope.
The loader must recheck authorization/consent/source policy on every request;
use an account-consistent snapshot and propagate missing data as unknown.
Existing cloud/state.mjs:24 strips preference provenance beyond type/term, so
owner 04/02 must approve a persistent representation before storing these DTOs.
Nothing here changes that schema or writes account data.

Owner 03's UI may POST {lotId,preferenceId} to /api/catalogue/lot-restriction
and display the returned scoped decision and provenance. Existing household
checks remain required. The adapter has no storage or transport side effects.

## Evidence and limits

Focused HTTP Request/Response tests exercise this adapter entrypoint using the
EXACT retained helper loaded read-only from its Git pin, not a stub evaluator.
They cover positive scope, other lots, rights revocation, consent, provenance,
account isolation, origin, body injection and size cap. This is not evidence
that the existing production handler is wired or shipped. Independent review
is outstanding; the test-only helper loading is not production adoption.

Actual supplied controls: unrestricted filesystem, danger-full-access sandbox,
network enabled, mandatory reviewer auto_review. Separate approval policy is
unavailable. CODEX_PERMISSION_PROFILE is not used to infer controls.
Only the reserved module, unique focused tests and this note are changed.
No providers, bulk copies, installs, deployments, settings or extra workers.

Status: READY FOR INDEPENDENT REVIEW; owner 03/02 wiring and owner 04 session/
persistence contract remain outstanding. DATA-05/ENRICH-04 source qualification
and medical/allergy assurance are not established by this adapter.
