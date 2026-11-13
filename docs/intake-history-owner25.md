# Worker 25 intake persistence candidate

## Fresh composition — 15 October 2026 Melbourne

Root confirmed Worker21 scoped PASS for original `53853acd35226ca7af591b978b72a92473c0b075`
(six author checks and four SQLite review checks). Standalone adapter scope only
is selected for progression; metadata-preserving session/consent/caller adoption
remains held. No central handler/schema edit is included.

Composition branch: `feature/intake-history-composition-25-20261015`.
Fresh locked origin/develop fetch exited 0 at 2026-10-14T14:30:22.861032+00:00,
base `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`. Original commit was cherry-picked
with source attribution (`-x`), without conflicts. The six focused author checks
pass against this fresh base; no broad campaign was run. Adapter/test content is
unchanged from the scoped PASS pin. Historical sections below describe the
original candidate; their old base is not this composition base.

Original branch, helper and dataset remain retained. A different existing reviewer
must review this exact fresh composition before any PR/develop merge. The final
composition pin, patch hash and independent remote backup readback are reported
to root separately to avoid a self-referential commit receipt.

READY FOR MORGAN REVIEW; not adopted or shipped.

Branch `feature/intake-history-consumer-25-20261014` starts at freshly fetched
`908ca373dfc918f2e33fd5e44260879577bed5c5`. Locked fetch exited 0 at
2026-10-14T10:16:38.282343+00:00. Root pickup sent to
`01a137cf-2242-761d-8fd7-6e6fc5658013`. Prior dataset branch remains at
`4168ae2c8be6f535193df92d595b4e944748720e`; its CSV/receipt/note remain in that
immutable branch. Prior checkout was clean, with no untracked files. Full retained
helper pin verified: `59d8bca52cc3281741862d17f2579668d6e6140d`.

Actual source path: public/app.js sets up insights; public/insights-ui.js log-form
mutates profile.history; public/insights-model.js validates legacy logs;
cloud/state.mjs projects profile; cloud/handler.mjs /api/state validates and saves
user_state using verifiedUser and revision CAS. A focused test calls the actual
validateState entrypoint and proves it drops profile.intakeHistory. This candidate
does not claim that an in-memory store is deployed persistence.

## Usable adapter and exact remaining integration contract

cloud/intake-history-owner25.mjs exports createIntakeHistory with injected:

- entryModel: independently reviewed createIntakeEntry/partitionIntakeEntries
  exports from retained helper pin. This branch deliberately does not copy or
  adopt the unreviewed helper. Tests load its exact Git blob by full pin; read-only
  Git subprocess strips inherited GIT_*.
- store.transaction(accountId, callback): exclusively reads the account-private
  envelope, invokes async callback, atomically commits returned state, and returns
  detached result. Exceptions roll back; callbacks serialize or retry against
  current revisions. No stale check followed by non-atomic write is acceptable.
- authorize({session, accountId, action, consentId, memberId}): trusted session
  owner resolves authenticated account and member authority, returns exact
  accountId/allowed:true and current persisted recording consent for append/read.
  Request assertions are not authorization. Revoke requires authority even if
  consent is already withdrawn. Consent withdrawal must share the same
  serialization/revision fence as intake writes and reads; the adapter alone
  cannot prevent a cross-store consent race.
- sourceAllowed(foodRef, auth): current explicit source/version/account reuse
  permission, checked on append and read for actual and planned substitution
  identities. CSV metadata is never permission or automatic admission.
- clock: injected ISO timestamp provider. No ambient storage, network or clock.

Methods append/read/revoke use an account-private version-1 envelope with entries
and revokedConsentIds. Writes use trusted consent, reject mismatched account input
and duplicate events, and retain source lineage/physical quantities. Reads return
separate planned/consumed/unknownConsumed buckets; denied consent fails closed and
denied source permission withholds entries. Revoke deletes matching history and
retains a bounded consent-ID tombstone, preventing reintroduction with that ID.
Capacity failures are explicit. Regrant requires a new verified consent ID. Source
withdrawal withholds reads but does not purge storage; retention/deletion policy
must be wired by owner02. No nutrient/safety/equivalence/ownership inference.

**Owner02 minimal production delta:** reserve cloud/handler.mjs and schema; add
authenticated /api/intake-history GET/POST and consent-ID DELETE route after
verifiedUser, with existing body bounds/origin/method restrictions. Derive account
from verified user, invoke this adapter, map denied access/validation/conflict to
appropriate HTTP errors. Provide a separate private intake envelope store and
atomic CAS/transaction fence with consent; keep it out of user_state until state
validation and sync owners explicitly support it. Do not publish a partially
wired endpoint. Database migration/CAS implementation is owner02 work, not this
candidate. Version and retry behavior must be qualified against actual DB.

**Owner04 minimal session/state delta:** expose verified intake consent and member
authority; serialize revoke with intake transaction; fence read/write after
logout/account switch; qualify private deletion/export/recovery and sync. Do not
send these records through today's validateInsights projection.

**Owner03 mapping:** confirmed insights-ui mutation path and that its current
reservation is read-only insight, not intake mutation/state routing. Its message
places central app/handler/state with02/04. Their reservation is required before
the UI owner imports/uses reviewed adapter results or app data hooks. Integration
requests were sent to03/04/02; no central file was edited. Separate review of both
retained helper and candidate is required before adoption; root must assign the
existing pool reviewer. No review verdict is claimed here.

## Checks, custody, controls

`node tests-web/intake-history-owner25.test.mjs`: six checks pass. Actual
validateState metadata loss, injected atomic-store persistence/reload, source
lineage/unknown separation, forged scope/session/current consent denial,
revocation deletion/tombstone, source permission on writes/reads and concurrent
duplicate rejection are exercised. Store and auth are bounded synthetic adapters;
real handler/D1/browser/identity integration is unexercised. No broad suite or
Git-writing fixture. Staged diff whitespace check and three-file scope verified.
