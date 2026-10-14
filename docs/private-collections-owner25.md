# P2-03 private bookmarks and family collections

## Fresh standalone composition — 15 October 2026

Root read Worker20 scoped PASS at
docs/reviews/worker20-collections-c83fde9e in the reviewer checkout: original three
P2 findings closed,12 author checks and15 independent scenarios passed. This is
not full feature or source/rights acceptance.

Composition branch `feature/private-collections-composition-25-20261015` starts
from freshly locked fetched develop `4693cbc3fe17cdde2e292e6eb00cd83769ee45ae`,
fetch exit0 at2026-10-14T17:23:47.153058+00:00. Normal attributed cherry-picks of
bd51ca12 and c83fde9 applied without conflicts; prior source/review/PR7 refs remain
intact. Only the three reserved paths enter the composition. Historical source
sections below retain their original source base, not this fresh base.

Exact SHA256 closure comparison to reviewed c83:

- public/private-collections-owner25.mjs:
  e47105dafcf3b55f5079c0c973ae4e3c7ee7ee5c7b5750e9bbe05c145c3092db
- tests-web/private-collections-owner25.test.mjs:
  753d3bb9c77dca501d8871cbdcf6670feb7ad7907388621fa52463049a961f31
- public/sync-model.js:
  ba73ac030d9c773010dbf7bdb55c9c5e1b634353e4117f4152543221bb2863d3
- package.json:
  da7f853789e8e3a0c396319ef1448e6a6703ff97957a0371e44e20ec28a201c1

All four bytes identical; no runtime/test dependency delta. Consumer and sync-model
have no relative imports; focused test imports those two modules plus Node builtins.
The four declared files were exported from the actual composition Git tree into
an isolated temporary directory without .git, alternates, node_modules, inherited
GIT_* or dependency links. node --test tests-web/private-collections-owner25.test.mjs
passed12/12, no skips, exit0. Child test invoked no Git command or hidden object.
This is actual declared-tree portability evidence, not a hermetic Node install or
full npm suite. No broad campaign was run. Final doc-only receipt changes do not
change that tested closure. Exact final head/tree/base/patch and private backup
are reported separately to root to avoid self-referential commit metadata.

SAME independent20 fresh-composition review and root acceptance remain required
before normal PR. Actual schema/consent/source-policy atomic D1 composition,
central endpoint adoption and durable withdrawal/deletion remain pending owner02
human-answer prerequisites. No new producer/source/helper admission or full-feature
acceptance is implied. Production STOP remains.

READY FOR INDEPENDENT WORKER20 REVIEW. No PR or adoption before review/root gates.

## Source and custody

Original PDF02 actual pages5–6 were read. Page6 proposes private recipes, permitted
URL bookmarks/imports and family collections, and explicitly distinguishes private
import from permission for public redistribution. Page5 requires private household
ownership boundaries and source/change history. PDF SHA-256:
`2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c`.
Requirement P2-03 is in docs/recommendation-delivery-register.json.

Existing public/recipe-library-model.js personallyReviewedRecipe creates a private
copy through recipeForReview/recordPermission and records sourceRecipeId and the
limited personal-review scope. It has no bookmark/collection operations. Existing
public/sync-model.js kitchenProjection omits private profile fields, but directly
projects recipes. Therefore private collection copies remain inside the private
envelope, never inserted into the shared recipe list by this consumer. No creator
ownership, copyright transfer, medical or source-admission claim is inferred.

Fresh locked fetch exited0 at 2026-10-14T16:10:19.939653+00:00, base
`148fec8102ee64ec6801d4df96dfeb9a946ac619`.
Branch: `feature/private-collections-25-20261015`.
Root exclusively reserved this module/test/note. Reservation notice sent to
existing03 map owner before edits; no central entrypoint change requested or made.
Prior corrective branch1bd71a3, composition24d75fa, intake53853, helper59d8bca,
dataset4168ae2 and PR5/PR7 evidence remain retained.

## Exported consumer contract

createPrivateCollections receives authorize, load, resolveRecipe, commit and clock.
No storage, timers, network or credentials are owned by the module.

- authorize(session,{accountId,action}) resolves trusted current account, session,
  realm, epoch, resource and explicit private-recipe-collections consent ID/revision.
  Client flags are not authority. load(binding) returns the private envelope
  `{version:1,accountId,revision,collections}` under that exact authority.
- mutate captures plain JSON command/session before its first await without
  invoking accessors/toJSON; bounds depth/nodes/strings and rejects sparse arrays,
  symbols, custom prototypes/cycles. Commands carry stable operationId and
  expectedVersion, plus add/rename/remove collection, bookmark/unbookmark or reset.
  Account IDs, collection IDs and bookmark IDs are distinct. Duplicate IDs and
  duplicate recipe/source/version/rightsVersion tuples within a collection reject.
- Recipe references carry sourceId, recipeId, version, rightsVersion and HTTPS
  sourceUrl. resolveRecipe(reference,binding) must be authoritative, current and
  return the exact reference, explicit available/unavailable/withdrawn status and
  lineage. References must have exactly the five declared fields; extra fields
  reject on both commands and restored envelopes. Optional privateCopy is retained only for current available records,
  explicit privateCopyAllowed:true, matching account and personally-reviewed
  source namespace/recipe/version/rightsVersion review evidence. Explicit copy,
  review, copy-reference and recipe-provenance source/rights contradictions reject.
  These assertions are supplied by the
  owner-controlled resolver, never trusted from user command flags.
- read re-resolves status/visibility and withholds private copies when rights or
  availability are withdrawn. Stored original reference remains explicit, not a
  silently substituted recipe. Read and mutation rebuild each bookmark from the
  current resolver: absent private-copy permission, only bookmark ID, exact source
  reference and explicit status survive. Arbitrary old or returned provenance/body
  fields cannot bypass this boundary. Permitted copy review provenance remains
  a JSON snapshot; reference rightsVersion remains an assertion selector, not a grant.
  Retention expiry/deletion of persisted source bodies is resolver/store-owner work;
  read withholding alone does not claim durable deletion.
- commit({binding,operationId,expectedVersion,state}) is a primary atomic CAS+
  admission+operation-ledger adapter, not a client-side flag check. It must re-admit
  session/consent AND source-policy versions at the commit fence, capture the exact
  state/digest and deduplicate exact operation ID/content. Consent/source withdrawal
  cannot race through a stale client precheck. Updated envelope revision is
  expectedVersion+1 only after commit; returned binding, operation ID, committed
  status and revision are verified. Conflict never auto-rebases. Transport/malformed
  result or post-commit authority change gives unknown; authority is also rechecked
  after load before returning private conflict revision metadata. Status reconciliation under
  still-live authority is required before retry. No exactly-once claim by itself.

Bounds: 100 collections and 100 bookmarks per collection; global JSON capture
limit10000 nodes/depth12 also applies and may constrain smaller practical totals.
Name/ID limit200; private text fields bounded10000. Caller-stored state must satisfy
the full validated envelope; owner-approved migration/export/delete remains needed.

## Selected04 compatibility and remaining adoption

Read immutable native local D1 protocol `f88902e87baa4e901006ec87083080c5188d06dd`,
cloud/session-state-d1-owner04.mjs SHA256
`1dc8633974f83f643d13b27cdeb44f3e4a4c3093c487583ff8719fefa574d12a`,
and independent11 proof.json at
/home/user/Documents/Codex/2026-10-15/worker-11-review/native-d1-owner04.
It supplies operationId/expectedVersion/state mutation, primary revision CAS,
session/subject/realm/epoch/expected-version admission and outcome ledger in atomic
D1 batch. D1 is async; no JavaScript callback transaction or SQLite substitution
is assumed here. Its documented per-member consent/schema-extension/provider
revocation gaps remain real. This consumer's request version semantics align,
but it is NOT a drop-in passed D1 composition.

Owner02/04 must reserve and qualify private-envelope normalization, authoritative
accountId-to-subject binding, session capability transport (never persisted in
collections), consent/source-policy revision guards, exact digest/outcome mapping
and full-state preservation or dedicated private store. Today's central
validateState discards this profile extension; direct forwarding to selected04
would reject lossy normalization. No central handler/schema adoption until Matt
confirmation and reviewed owner composition. Existing03 can map UI entrypoints
only after these gates. Family collection names are organizational labels, not
household sharing grants. All shared projections must omit the private envelope;
future selective sharing requires separate source rights and scope qualification.

## Focused verification and limits

node --test tests-web/private-collections-owner25.test.mjs: eight tests pass.
Actual exported consumer add/bookmark/rename/unbookmark/remove/reset and revision
receipts; duplicate IDs/refs; unavailable/withdrawn/rights-denied copy omission;
cross-account/client-flags/revoked session; pre-await mutation capture/accessor
rejection; atomic adapter admission after a delayed revoke; stale revision and
lost applied ACK; actual kitchenProjection omission are exercised. Synthetic
authoritative resolver/commit fixtures are bounded, not actual D1/provider proof.
No broad suite/server/install/source call. Different existing20 reviews exact pin
before PR; independent source/helper/whole-feature acceptance remains withheld.

Only the reserved three authored paths committed. Primary main remains
8652b312ce7989c5e4f2d49ae765d5d8daf5841d and primary index SHA256
4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389.
Private-origin backup and independent remote readback accompany the handoff.
Production STOP; no endpoint, provider, credentials, public sharing, source writes
or new worker. Full implementation/provenance pin and patch hash reported to root.

## Worker20 findings correction

Original `bd51ca12d8b703ca77c7e5c3dc9e6d70d47210c7` remains the parent/recovery pin;
its review is not a PASS. Read exact worker20 review.md/independent-probes.mjs under
docs/reviews/worker20-collections-bd51ca12 in the reviewer checkout. Before edits,
ran the exact seven probe scenarios against the immutable original module loaded
from Git; removed only the review-output write so no reviewer artifacts changed.
All three observations reproduced: extra reference.privateCopy content survived
withdrawal; revoked load returned private conflict revision; explicitly conflicting
copy namespace/rights/provenance survived.

Successor changes only owned module/tests/note. Five-field reference rejection,
rebuilt identifier/status-only unauthorized projections (also before persistence),
post-load conflict authority recheck and exact review-source/rights guards address
W20-C1/C2/C3. Twelve focused cases pass (eight prior plus four regression groups),
including malicious command/restored references, restored/returned arbitrary body
fields, live-vs-revoked conflict, and review/provenance mismatch negatives. Existing
valid-copy author case exercises the strengthened exact namespace/rights binding.
No D1/central admission proof or self-acceptance is added. Same independent20
re-review is required before PR; successor pin and private backup/readback reported
to root separately. Fixture hooks remain synthetic and bounded.
