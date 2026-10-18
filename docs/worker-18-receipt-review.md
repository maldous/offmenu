# Worker 18 receipt review slice

Disposition: READY FOR MORGAN REVIEW. No integration or release acceptance claimed.

Custody: branch `feature/receipt-review-20261014`, base
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`. Dispatch supplied an
`origin/develop` fetch exit 0 at `2026-10-14T06:40:39.040408+00:00`;
inspection confirmed local HEAD and `origin/develop` at that exact SHA.
Verdict remains `PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE`.
Only the two reserved new module/test files and this document were changed.

## Requirement and existing gap

[P1-01](delivery-reconciliation.json) (entry at line 179) explicitly requires
reviewed receipt/label OCR, duplicate detection, corrections and minimal image
retention. Dependencies are DATA-10 (line 492, separate private/contribution
rights) and TRUST-02 (line 596, narrow consent/deletion). The register expressly
distinguishes historical recipe OCR from this feature.

`public/checkout-model.js:finishInventory` guards duplicate IDs only within the
incoming batch, then appends shopping items to existing inventory. A bounded
negative example applied the same one-line shopping receipt twice: two entries
with identical ID and quantity 2 resulted. `createScanGate` only debounces a
barcode held in view; it does not track imported receipt identity.
`public/app.js` final checkout/review and `public/documents.js:buildDocument`
operate on scanner checkout receipts, not injected OCR extraction or its image
lifecycle. `public/recipe-library-model.js` handles historical recipe OCR;
`public/record-policy.js` provides general source admission rather than receipt
review/replay. No existing owners' implementation was modified.

## Pure contract and owner-controlled adoption

`prepareReceipt(input, context)` accepts at most 200 injected OCR lines with
stable source line IDs, exact original text, explicit parsed fields and nullable
confidence. `context.now` is an injected integer clock. Authenticated account,
current narrow review consent and current private source-use rights are required.
Unknown quantities/units remain null. No image is retained by default; an opaque
image ID requires separate image consent and a deadline no later than the receipt.
No pixels or arbitrary provider fields enter the model.

`reviewReceipt(draft, review, ledger, context)` requires explicit confirmation
and include/exclude decisions for every source line. Corrections remain separate
from immutable source extraction. Exact source-byte digest, source identity and
account identity form the duplicate key. Return `duplicate` means no receipt or
ledger write. The digest must be computed by the adapter from actual source bytes,
not trusted from an OCR provider. Exact-byte duplicates only: rescans, altered
images, OCR-equivalent documents and merchant transaction identity require a
separate reviewed strategy. Retention expiry/deletion of the ledger also ends
duplicate memory; this is deliberate minimal retention, not forever deduplication.

An existing caller such as `public/app.js` could later adopt this sequence through
its owner, after Morgan review and explicit integration dispatch:

1. Resolve active authenticated account and write permissions; acquire OCR through
   an authorized provider adapter; calculate source digest; pass admitted rights,
   narrow consent, bounded deadlines and injected clock to `prepareReceipt`.
2. Display original fields and uncertainty, collect corrections and line decisions,
   then call `reviewReceipt` using the account's authoritative ledger. The adapter
   must make the ledger check and receipt/ledger write atomic, including offline
   retries/concurrent devices. This pure function does not provide transactions.
3. Handle returned deletion instructions, discard transient duplicate-upload images,
   and persist only permitted private records. Recheck current rights/consent on
   every read/use; persisted expiry stamps do not grant perpetual permission.
4. Separately request confirmation of actual received stock and map reviewed lines
   through existing lot validation, source identity and inventory ownership checks.
   A reviewed receipt alone grants no ownership or purchase authority. Missing
   units/quantities require further review; do not turn null into one package.
5. Apply `receiptRetentionPlan` at access/deadline, consent withdrawal and account
   deletion. Delete the receipt, image and ledger as instructed across browser,
   server, exports, caches and backups under their owning policies. `retainImage`
   must come from current consent. The function only produces a plan; it neither
   schedules nor proves deletion. Unpersisted drafts are trusted in-memory outputs
   of `prepareReceipt`; external stored drafts require owner schema validation.

Provider/UI wiring, auth, schema, image storage, rights admission, atomic ledger,
offline custody and lifecycle enforcement are explicit integration dependencies.
No safety/allergen/nutrition/expiry inference is present. User review does not
establish medical safety, shared publication rights or nutrition equivalence.

## Focused verification

Two Node processes total: the bounded baseline negative example and
`node tests-web/receipt-review-model.test.mjs` (exit 0, 8/8 tests).
Tests cover replay, scope separation, corrections/source preservation, missing
fields, explicit decisions, consent/rights expiry, image deadlines/withdrawal and
bounded malformed extraction. No provider calls, Git-writing fixtures, servers,
installs or broad suites. No additional agents, sessions or worktrees.

Shared custody baseline: common directory `/home/user/src/offmenu/.git`, main SHA
`8652b312ce7989c5e4f2d49ae765d5d8daf5841d`, main checkout clean, main index SHA-256
`4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`.
These invariants are asserted again after the worker commit. Shared Git object
storage necessarily receives the new result commit; main and its index stay intact.
Synthetic unit checks establish this module's bounded behavior only; the feature
is not shipped, independently accepted, integrated or release-certified.
