# Owner 16 queue/state bridge candidate

Pickup: `feature/queue-state-bridge-owner16-20261015`, fresh locked origin/develop `5f5bdb6ae716cbf80fab1e174d1af2e354468ead`; fetch exit 0, started 2026-10-14T14:04:42Z (15 October Melbourne). Prior queue consumer branch stays at `61192ddba1c40747b974a45d5ed2fdad368d6c3d`; earlier source/dataset commits remain in their branches. No prior artifacts, dependencies or owner files changed.

## Requirement and demonstrated gap

Read original report 04 pages 1-10 and report 02 page 9 using Poppler extraction; actual file hashes match the original-readability receipt and abe0 originals:

- `04-OffMenu_User_Driven_Cache_and_Enrichment_Design-1-.pdf`: `2e049a433c329421249a27ccbf92f15c64b9da2cc3adb065d8c6ddb13dff2ccd`.
- `02-OffMenu_Product_Review_and_Plan-1-.pdf`: `2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c`.

Report 04 pp2-4 requires authorized reads and source/rights evidence without destructive identity merging; p5 stops queued work on grant cancellation; p7 rechecks access before commit; p8 requires idempotent version-aware insertion; p9 calls for account isolation, revoked queued jobs and in-flight acceptance cases. Report 02 p9 requires evidence-preserving staging and a versioned publication path, with private records kept out of public releases. This bridge addresses the private state-operation commit/confirmation boundary only. It does not implement source rights, promotion, consent, export, retention or whole-report acceptance.

New before/after probe executes immutable consumer `61192dd...` with queue `0e7279a...`: correct-looking binding/ID/revision but wrong digest is acknowledged by that predecessor. The new bridge rejects confirmation for the identical damaged result. Prior consumer source is not edited. Caller adoption must route confirmation through this bridge; existing app callers have not changed.

## Exact source and independent review

Protocol candidate: `25543bd75c3812a203e0d3b865d51302bfe1854d:cloud/session-state-owner04.mjs`, SHA-256 `4520436816c70f93028fbbef38fdec572018dd507a8489c9027bb528af6f0be5`. Tests read immutable Git bytes with inherited GIT variables removed. The imported validator at this base is SHA-256 `801c68accc3a21fa59756e8cc8029251319ff0266ad93152563ad499f666b88b`, asserted before execution. No mutable Owner04 checkout reads, source copies or source edits.

Read retained independent review `/home/user/Documents/Codex/2026-10-14/task-2/worker-11-review/session-state-owner04-independent-review/corrected-25543bd/review.txt`: F1 resolved for captured command/credential boundary; synchronous parser contract established. That verdict applies to Owner04, not this new bridge. This successor requires independent exact-pin review before adoption or normal publication.

## Bridge API and ordering

`createQueueStateBridge({protocol, trustedBinding})` supplies `submit(actualRequest,{operationId,expectedVersion,state})` and `recover(actualRequest,sameCommand)`.

`trustedBinding` synchronously returns a server-owned public selector `{subject,sessionId,realm,epoch,resource}` from reviewed explicit enrollment. It must not derive authority from queued/body fields. The binding is a comparison target only. Owner04 separately captures the protected session credentials synchronously, freshly authenticates the subject, checks request policy, and validates persisted session state inside its mutation transaction. The actual Request passes through unchanged. No bridge credential/body parser, issuer, fallback identity or automatic enrollment exists.

The bridge captures strict plain-data command and selector before awaiting anything, computes the canonical `{audience,method:'PUT',version,state}` digest, and invokes Owner04 before digest awaits so protected credentials are already captured. The protocol owns the single atomic admission/CAS/outcome transaction. Confirmation requires exact operation ID, digest, subject/session/realm/epoch/resource, committed status, explicit acknowledgement and expectedVersion+1. Reordered binding fields are equivalent. Terminal conflicts are confirmed conflicts with acknowledged=false; they never silently rebase or retire a queued mutation as successful. Invalid responses, storage failures, denied authority and lost responses remain unknown/unconfirmed. Status recovery also compares the original command digest; another payload cannot claim the old outcome. Revocation prevents replay/status under the old grant but cannot undo an earlier commit.

No separate transaction, queue row or detached admission decision is introduced. The bridge is a server-side composition seam; the existing browser consumer requires an Owner02-controlled transport that supplies the reviewed protocol and binding hook, forwards only the three command fields and distinguishes terminal conflict from successful queue ACK. Queue expiry remains local retry policy, never issuer TTL.

## New checks and custody

`node --test tests-web/queue-state-bridge-owner16.test.mjs`: eight focused tests. Real Node SQLite executes the exact protocol's store: replay once, stale conflict, lost response plus scoped recovery, trigger-induced ledger rollback with no state write, both commit/revoke orders, cross-account denial, fake digest/ID/revision, reordered binding and credential/command mutation while auth waits. Before/after digest probe is distinct from previously accepted unchanged helper tests. No Git-writing fixtures, providers, private user records, servers, real D1 or physical devices.

Owned delta only: `cloud/queue-state-bridge-owner16.mjs`, its focused test, this note. Primary `.git/HEAD` SHA-256 `28d25bf82af4c0e2b72f50959b2beb859e3e60b9630a5e8c603dad4ddb2b6e80`, index `4332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389`, main `8652b312ce7989c5e4f2d49ae765d5d8daf5841d` preserved. Command-scoped Worker16 commit identity; no persistent settings changes.

Actual supplied filesystem unrestricted/danger-full-access, network enabled, mandatory reviewer auto_review; separate approval policy unavailable. These are supplied controls, not named-profile inference.

## Owner02 and successor gates

Owner02 must qualify primary D1 atomicity/migrations, restore realm, reviewed protected transport, fixed Origin/CSRF/enrollment policies, fresh verifiedUser, budgets and ledger retention. State schema reconciliation and field-level consent/rights remain required; app-session scope alone is no permission to persist provider content. No central routes/schema/public app changes. No source admission, whole-105 acceptance, provider qualification or production release. Production STOP remains in force. Review-ready candidate, not adoption approval.
