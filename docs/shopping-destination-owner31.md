# Worker31 shopping destination boundary — independent review candidate

Selected task: OFFMENU-DELIVERY-20261015-C2, Worker31 destination boundary.
Parent/base bce4c336f2a10ab78aaf78e1a4db3763a0a896bf includes manager-selected
f6cb92aef52a5cc8193717d7e794556bd84f8b3b. Branch:
feature/shopping-destination-owner31-20261015. Only new module, test and this
note are owned; no edits to the parent adapter/helper or central app/schema.

Worker64 discharged the original no-write hold via exact descendant/custody
record in the retained develop-inclusion evidence,
observed 2026-10-15T11:22:52.666402+00:00. Worker31 row is registered, ownership
validated, clean, developIncluded true, unchanged bce4 head. No sync/fetch/ref
repair or new checkout was performed. The bce4 task ref and Worker24 verdict
remain retained; a new local task branch protects that exact reviewed candidate.

## Contract and deliberately blocked default

createShoppingDestinationBoundary injects:
- handoff: the existing qualified shopping controller from the parent adapter;
- readPolicy(): {version,destinations:[{id,url,markets,enabled,expiresAt}]};
- readContext(): {accountId,kitchenId,revision,sessionEpoch,market,canExport,demo};
- now(): finite epoch milliseconds.

No defaults grant a destination. A missing producer, empty allowlist, disabled
entry, unsupported market, expired entry, unavailable export permission or demo
scope blocks. Registry producers are owner-controlled trusted code, not a
user-supplied payload. Presence/version/boolean/expiry checks cannot prove policy
approval or source entitlement. No built-in retailer entry is shipped. Synthetic
shop.example URLs and synthetic reviewRef values in tests are not approvals.

Requests contain exactly {id,kind:'retailer',destinationId}. Credential, URL,
header and other unknown fields reject. Destination IDs are bounded lower-case
ASCII identifiers, so URL-like strings accepted opaquely by the old adapter no
longer qualify here. Policy entries have exact known fields and unique IDs,
strict boolean enabled, nonempty ISO-code market lists and finite explicit
expiry. URLs must be literal canonical HTTPS with no userinfo, whitespace,
backslashes, query/fragment markers (including empty ones), or custom port.
No URL is built from the request, shopping data or user credentials. Policy
URLs must still undergo owner review for correct public endpoint/region/terms:
canonical syntax does not prove a host, path, rights or retailer is trustworthy.
No DNS/network request, URL navigation, provider/cart/purchase, clipboard, share,
calendar action, account storage or central wiring exists in this module.

preview(request) reads a detached plain policy/context snapshot, resolves the
allowlisted destination, invokes the existing handoff.preview and checks its
retailer kind, account+kitchen scope, revision, epoch and exact destination ID.
It returns {status:'destination-preview',destination,handoff}. Owner UI must
render BOTH the destination and the full handoff/quantity/source/uncertainty
preview, with safe text rendering and appropriate private-data confirmation.

confirm(the SAME preview,{confirmed:true}) rejects mutation/forged views, rereads
policy/context and expiry, then invokes the existing handoff.confirm. That
controller rechecks current list, quantities, provenance and source rights; this
wrapper does not duplicate or override its source policy. A successful result
consumes the preview. It returns {status:'destination-approved-proposal',
destination,handoff}, as detached plain JSON. This status denotes only a local
allowlisted proposal; it is not provider authorization, authenticated consent,
a navigation permission or an executed purchase/handoff. No transport follows.

Original and returned objects share no quantity/provenance references. Unknown
quantity/unit remain null, uncertainty and sourceRecordIds remain as emitted by
the existing controller, source records are retained in full, and no pack, price,
GTIN, nutrition/allergen equivalence or availability is invented. A later UI,
transport or persistence integration still requires its own owner reservation,
authenticated producer, source rights, privacy/consent and independent review.
Policy reads are synchronous injected snapshots; this is not an atomic remote
revocation/authorization protocol or a claim that client declarations establish
server trust. A qualified producer must establish that trust separately.

## Exact checks and review disposition

node --test tests-web/shopping-destination-owner31.test.mjs: 7 test groups passed,
0 failed. Actual current parent shoppingItems -> adapter -> immutable ac19 helper
chain is exercised by injection; inherited GIT_* are stripped for helper reads.
No source/helper copy or extra worker was created.

Coverage: blocked default; unapproved/URL-like IDs; request credential/URL fields;
userinfo and unsafe/relative/noncanonical/query/fragment/custom-port URLs; unknown
registry fields; real detached 400g and null/unknown line/provenance; explicit
confirmation and single use; policy revocation/version/URL/market changes; expiry;
account/kitchen/revision/epoch/export/demo changes; changed quantity, checked
state, provenance and source withdrawal; forged/mutated previews; duplicate IDs;
non-boolean enabled; accessor rejection without getter execution; detached
original-request mutation cannot redirect a preview.

Initial run: 6 passed, 1 failed, exposing empty '?' URL marker acceptance; the
URL test now rejects both literal '?' and '#' markers even when WHATWG URL
search/hash are empty. Final run: 7 passed. No broad suite was run.

Retained Worker24 review for parent bce4:
the retained independent shopping-composition review receipt
SHA256 06a58bd47f58d2d408c07858f083a2eda7fe5eb0863b6a52a5f4376204cd64a1.
Its bounded PASS is not acceptance of this new boundary. SAME existing Worker24
is the selected distinct reviewer; new immutable candidate verdict pending.
No repeated shopping source review or borrowed UI/provider acceptance.

Original branch/source/dataset/calendar pins and untracked custody are preserved.
Only the three new owned files are committed. No external publication or backup
attempt is made under the standing hold; checkpoint is local-only. Prior calendar
PR action-specific rejection remains STOP; no alternate route or retry. No
canonical merge/main change, production deployment or new feature wave.
Production and source-admission/household-adoption holds remain. Supplied controls
are unchanged; filesystem unrestricted, network enabled, mandatory auto_review
preserved, current approval policy never (no escalation requested).
