# Worker 18 stock receipt integration

Pickup custody:

```json
{
  "branch": "feature/dataset-uk-cofid-20261014",
  "head": "74d95fc4a0e23ffa28ce7288515935b1eade1d0d",
  "status": "",
  "main": "8652b312ce7989c5e4f2d49ae765d5d8daf5841d",
  "index_sha256": "4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389",
  "primary_status": "",
  "helper": "e3149b555789231b525b732e5b127fb7ba8d578d",
  "dataset_artifacts": {
    "docs/dataset-discovery/worker-18/note.md": "007e0354368408550b343e044a2a3aeff9b9f44ee51596f7fab66a731a6b97a5",
    "docs/dataset-discovery/worker-18/receipt.json": "7fde08b1aea5834688b57b6b602f35cd6de1f9360546918ee4df446e16aa57d7",
    "docs/dataset-discovery/worker-18/source.csv": "0049575634ed04d830b570affb2881061938a59e345f34a83e3abfb73dfdb9b4"
  },
  "fetch_utc": "2026-10-14T10:16:03.708264+00:00",
  "fetch_exit": 0,
  "base": "908ca373dfc918f2e33fd5e44260879577bed5c5"
}
```

## Candidate and production boundary

READY FOR INDEPENDENT REVIEW / MORGAN REVIEW, not integrated or shipped.
Own files: `cloud/stock-receipt-owner18.mjs`,
`tests-web/stock-receipt-owner18.test.mjs`, this note only.

The dispatch helper pin had an extra trailing `8`. Verified retained commit is
`e3149b555789231b525b732e5b127fb7ba8d578d`; source and branch remain intact.
That helper reviews OCR extraction, not received stock, persists nothing, and
requires trusted prepared drafts and an authoritative atomic ledger. It handles
exact-byte duplicate identity rather than cross-upload purchase identity. This
candidate does not import or adopt it. Independent review of both retained helper
and this candidate remains required before any adoption.

Existing boundary evidence: `cloud/schema.sql` defines account `user_state`;
`cloud/handler.mjs` persists whole state with revision compare-and-swap.
`cloud/state.mjs:validateState` strips stock receipt history and lot provenance.
`public/checkout-model.js:finishInventory` shopping replay duplicates stock.
These are concrete integration gaps; synthetic dataset samples are unrelated and
never supply automatic stock admission.

`stockReceiptRoutes` is a real HTTP-to-D1 account persistence adapter for POST
`/api/stock-receipts`, using the existing `user_state` table and parameterized SQL.
It writes the stock lots, immutable receipt snapshots and replay history together
in one revision-checked update. No additional table, migration, provider or UI is
required by the adapter itself. Account state must already exist. Explicit reviewed
receipt and actual-received confirmation, exact supplied quantities/units, stable
source-line and lot IDs, purchase issuer/ID, source record ID, source-byte digest,
received date and an authenticated account are required. Unknown ingredient identity
stays unmapped/reviewable. No source, nutrition or medical equivalence is inferred.

The private account plus purchase issuer/ID defines replay identity. Identical
canonical payload replay returns the existing lot IDs without changing stock or
revision; changed quantity/provenance under the same purchase identity conflicts.
A stale concurrent write conflicts and the same-purchase retry converges. Purchase
identity is explicitly supplied/reviewed, not guessed from merchant/name/amount.
A new purchase with an old lot ID is rejected even after the original lot is consumed.
Receipt provenance stores original received quantity/unit separately from remaining
lot quantities. This is explicit provenance, not proof of purchase or food safety.

## Exact owner-controlled integration delta

No central path reservation was supplied or found. These are required owner03/02
changes, not edits made by Worker18. The adapter must remain disabled until all
hooks and independent reviews are complete.

1. Owner03/02 central `cloud/handler.mjs`: import
   `{stockReceiptRoutes, preserveStockReceipts}` from
   `./stock-receipt-owner18.mjs`; before the generic method fallback dispatch:

   ```js
   const receipt = await stockReceiptRoutes(request, env, {
     verifiedUser, boundedJSON, authorizeReceipt
   });
   if (receipt) return receipt;
   ```

   `authorizeReceipt` must be a trusted current server policy/consent/source-digest
   admission callback. It receives `{user, receipt, now}` and returns
   `{allowed:true, accountId:user.id, sourceId:receipt.sourceId,
   privateStorageConsent:true, expiresAt:<integer UTC milliseconds>}` only after
   actual admission. A callback trusting client `reviewed`, CSV licence metadata,
   contentDigest or a saved allowed flag is insufficient. No callback is provided
   here; the route fails closed with 503 if absent and 403 if mismatched/expired.

2. Owner02 account `/api/state` PUT: before its existing CAS write load the current
   stored account state using the verified account ID. Set
   `state = preserveStockReceipts(storedState, body.state, user.id)` instead of
   accepting client history or relying on `validateState` alone. Keep the existing
   revision CAS, origin/auth checks and first-save behavior. Server history must be
   retained even when a consumed lot disappears. The helper overwrites untrusted
   incoming provenance from server history and rejects receipt-bound unit changes
   or quantity increases (a separate correction receipt is needed). First saves
   must ignore/reject client receipt history; they cannot mint this ledger.
   Any additional account write route must apply the same preservation rule.

3. Owner03 `public/app.js` consumer: stage reviewed receipt lines, request actual
   received-stock confirmation, and POST using the active account revision. On 201
   or duplicate 200 reload `/api/state` and reapply the returned state; on 409 retain
   the draft, reload and ask for reconfirmation if stock changed. Use a stable
   purchase identity and lot IDs across retries. Never call `finishInventory` to
   append those lines again. Cloud GET already returns full stored JSON, but local
   `validateState`, export/restore and sync serialization must preserve/display the
   receipt snapshot and provenance through owner-controlled validation.

4. Owner04 session/state: bind request and returned state to the same active account
   generation; discard a response after logout/account switch. Do not post an
   account receipt while a shared kitchen is active. This adapter rejects explicit
   kitchen scope; shared-kitchen roles/projection/privacy require a separate owned
   design. Do not leak account/source provenance through kitchen projection.

5. Owner02/04 lifecycle: define account deletion/export, private receipt retention
   and consent withdrawal against retained stock provenance and the replay ledger.
   This slice deliberately does not prune replay history or retain OCR/images;
   it caps history at 1,000 receipts and returns conflict when full. No independent
   retention compliance claim. A reviewed deletion policy must specify whether
   replay memory is lost after deletion; do not silently drop history on sync.

There is no schema migration in this candidate. Existing schema supports the JSON
extension, but current validators, state PUT, client lifecycle and routing must
adopt it together. Those central reservations and owner coordination are pending;
no worker03/04 changes or review outcomes are claimed.

## Validation and limits

`node tests-web/stock-receipt-owner18.test.mjs`: initial 5 passed/1 failed; malformed
lot errors were corrected from 503 to 400; final 6 passed/0 failed. Two focused Node
processes total; no Git-writing fixture or broad suite. Real SQLite in memory
executes the unchanged production schema and adapter SQL. Checks exercise atomic
receipt/stock writes and readback, account separation, replay with fresh callback
instances, altered payload rejection, concurrent CAS and retry, origin/auth/policy
checks, bounded body, receipt preservation after consumption, and source provenance.
SQLite is not a deployed D1 runtime qualification; no real account/provider accessed.

Actual `cloud/handler.mjs.fetch` at the pickup pin returns 405 for the new POST;
this proves the central route is still absent. Tests exercise the adapter's HTTP
entrypoint against actual schema but do not claim integrated handler success.
Current `validateState` demonstrably removes both receipt history and lot provenance;
`preserveStockReceipts` is tested as the required server hook.

Actual supplied controls: filesystem danger-full-access/unrestricted, network
enabled, mandatory reviewer auto_review. Separate approval policy unavailable.
CODEX_PERMISSION_PROFILE environment was previously observed unset, and no profile
is inferred from it. No settings changed. Current controls are preserved.

Current Cloudflare references read before writing:
[Workers best practices](https://developers.cloudflare.com/workers/best-practices/workers-best-practices/)
and [D1 prepared statements](https://developers.cloudflare.com/d1/worker-api/prepared-statements/).
No type dependency was downloaded/installed; this JS slice uses the existing binding
shape. All critical writes are awaited; no background work or global request state.

Only the owned module/test/note are committed. Dataset artifacts stay at immutable
commit `74d95fc4a0e23ffa28ce7288515935b1eade1d0d` on their original branch; no copies
were added to this branch. Their stored hashes are verified by Git-object readback.
Primary main ref/index/status and prior branch pins are asserted after the commit.

Requirement trace: [P1-01, DATA-10 and TRUST-02](delivery-reconciliation.json). This candidate implements received-stock persistence/replay/provenance; receipt OCR/provider rights and privacy lifecycle remain separate gates.

## W23-RECEIPT-F1 correction — 15 October 2026

Worker23 independently reviewed actual stock receipt source 7b971f17f4a98325b074502a3a89dff74355d82a; forecast naming mismatch history is retained in their review directory. Reproduced blocking partial-consumption increase: received 500g, stored remaining 100g, incoming 400g was accepted by the old hook. New regression failed before correction (6 pass/1 fail) and passes after (7 pass/0 fail).

preserveStockReceipts now validates current server stock and compares incoming bound quantity to both remaining stock and original received quantity, with the same unit. Receipt-bound IDs absent from current stock cannot resurrect. Equal/decreasing quantities remain allowed. The hook cannot authorize an increase, correction or cook undo; those require an independently reviewed correction-event workflow, not a client whole-state replacement. No such workflow or central adoption added here.

Only existing owned module/test/note changed. Same branch, original commit retained as parent; prior private backup retained. Exact successor requires Worker23 rereview. Production STOP, source admission/whole105 withholding, consent/session/state integration and actual runtime qualification gates remain. Before/after primary main/index/status and prior dataset/helper pins are asserted. This correction does not accept metadata or authorize purchases.
