# Worker 31 shopping consumer — candidate for independent review

Root: 01a137cf-2242-761d-8fd7-6e6fc5658013. Branch:
feature/shopping-handoff-consumer-31-20261014. Locked fresh origin/develop fetch
exit 0 completed 2026-10-14T10:17:08.765252+00:00, base
908ca373dfc918f2e33fd5e44260879577bed5c5.

Preserved pins: dataset branch feature/dataset-uk-fsa-alerts-20261014 at
20863845eb5f3affcdc2133a59c0a5a3408cbed1; retained helper
ac19b0c863ca486b9e6139cd2cad8497694fa368. Neither was merged or modified.
Pickup tracked/staged/untracked state was clean. No symlinks/dependency copies
were created. Primary main HEAD/index/main-ref hashes and common-dir identity
remain fixed. Git calls strip inherited GIT_*; command-scoped Worker31 identity.

## Real entrypoint evidence and selected boundary

At this exact base, public/insights-ui.js:28 calls shoppingItems. Line 33 shares
only names and amount text through Web Share or clipboard. It supplies no
quantity/source/confirmation readback. This candidate imports the same production
shoppingItems directly from integrations.js and exercises it with both measured
and unmeasured inputs. It builds source-bearing proposals from those actual
shopping lines, then rebuilds from CURRENT data for explicit confirmation.

Browser boundary: public/shopping-handoff-owner31.mjs. Only a retailer proposal
is supported by this consumer; retained calendar/substitution functionality is
not exposed here. No purchase, external transport, clipboard call, navigation,
storage write or provider call exists in this module. Confirmation returns a
confirmed proposal for user readback, never an executed handoff or order.

## Exact owner-controlled integration delta (not applied)

Worker03's current thread was read on this turn: it has reserved the narrow
insights-ui hook plus its production map/module/test and is considering a waste
consumer. Worker04's current thread was read: its isolated server protocol needs
real authenticate/readSession/request policy and does not supply an installed
D1/session route. These reads confer neither reservations nor review approval.
No cross-owner file was changed. Hook reservation for this shopping flow remains
pending 03/root; app.js/cloud handlers/schema remain 02 only.

After independent review of BOTH retained pin and this immutable candidate:

1. Owner03 imports createShoppingHandoff into insights-ui.js, accepts a new
   getShoppingReadback and reviewedShoppingHelper injection in setupInsights,
   and creates ONE controller with read:getShoppingReadback, now:Date.now,
   helper:reviewedShoppingHelper. The reviewed helper object has pin equal to the
   exact retained SHA, reviewRef to actual independent evidence, and propose /
   confirm functions from the independently approved helper. The module checks
   presence/pin, not authenticity of reviewRef: owner/root enforces that gate.
2. Replace ONLY share-shopping onclick at line 33: call controller.preview with
   a new id, kind:'retailer', destinationId from a reviewed owner destination
   selection. Render draft.detail.lines AND draft.records, destination, scope,
   limitations and all unknowns in a review dialog via textContent/localization.
   A separate explicit confirm action invokes controller.confirm(the SAME view,
   {confirmed:true}), displays the returned confirmed proposal, and clears the
   dialog. Cancellation has no effects. Do not call navigator.share/clipboard or
   provider/cart APIs from this flow; external export would need its own reviewed
   destination/rights and user-action policy. Do not label this as purchasing.
3. Owner02 passes getShoppingReadback from its setupInsights bootstrap. Return
   accountId, kitchenId, revision, sessionEpoch, canExport, demo, policies, data,
   bindings. data is the existing {profile,recipes,inventory,products,date,
   usePantry}. Authenticated account/kitchen, export permission, current revision
   and nonsecret session epoch come from the reviewed active owner04/02 session
   boundary; no hardcoded guest or local-storage authority. Changed account,
   kitchen, login epoch, revision or shopping data invalidates the preview.
4. Every uncollected shopping line needs one or more explicit bindings:
   {lineId,accountId,kitchenId,revision,admitted:true,record}. The record is the
   actual rights-bearing source record with stable id/provenance, not a CSV row.
   The binding producer must establish joins/admission independently; this module
   cannot prove those owner declarations. Missing bindings reject, including
   custom/unmeasured lines. Unknown values remain null and visible, never zero.
   Source record reuse is rechecked by the retained helper at confirmation.

No persistent fields or server request were added: therefore this slice does not
adopt Worker04's in-progress SQLite protocol, create a D1 migration, or invent a
persisted app-session epoch. Owner02/04 must expose an accepted session readback
before real UI activation. The existing shoppingItems rounds amount text while
preserving original measured quantity; both survive independently here.

## Checks and review limits

node --test tests-web/shopping-handoff-owner31.test.mjs: 5 tests passed. Tests
load retained helper via git show at the full pin with GIT_* stripped and resolve
its existing record-policy dependency from this base; no copied corpus/dependency
or helper checkout. Actual shoppingItems feeds unknown and measured lines.
Coverage: input immutability; source IDs and quantities; confirmation must use the
same controller-issued preview object; one successful confirmation consumes it;
account/kitchen/revision/epoch/data/collected-state change; unavailable export,
demo, missing/unadmitted/expired/unknown-provider sources; malicious accessors
(no getter execution), sparse arrays and purchase requests reject.

Tests use a synthetic reviewRef explicitly labelled NOT independent review.
Independent reviews of helper and candidate remain outstanding. Author inspection
identified the retained helper's permissive source-policy dependency behavior
(e.g. inherited recordPermission handles dependency dates) as upstream review
scope; this candidate does not assert that policy provenance/admission is trusted
merely because a string/sourceId exists. No helper adoption occurred in production.

The actual UI callback/browser flow is not exercised or installed. Evidence is
production shoppingItems -> adapter -> exact retained helper under bounded
synthetic inputs, not a shipped browser feature. Owner03/02 integration delta,
source-binding producer, accepted session boundary, independent review and UI
acceptance remain explicit gates. P0-05/P2-04/DATA-11 dependencies and dataset
admission remain separate; previous source CSV metadata is never auto-admitted.

Actual supplied controls: danger-full-access filesystem sandbox, unrestricted
filesystem access, network enabled; mandatory reviewer auto_review. Separate
approval policy unavailable. CODEX_PERMISSION_PROFILE unset; no named-profile
inference. Controls unchanged. No provider payments, bulk, deploy, Actions,
security/settings changes, force, extra workers/agents/worktrees/sessions.

## DELIVERY-CONTINUE-OWNER31-20261015 local composition

Manager-selected source f0072452731b87411d90a83a7f8937a594475e53 is now composed
in the same isolated permanent Worker31 checkout on its own task branch,
feature/shopping-composition-owner31-20261015, preserving the calendar branch at
3beb2668f5c43feb7c0e492bd0db88c4f0ef7c69. Base:
f6cb92aef52a5cc8193717d7e794556bd84f8b3b. The local cached origin/develop remained
4693cbc3fe17cdde2e292e6eb00cd83769ee45ae; it was not repaired or fetched. Before
composition, the supplied base existed locally and an independent read-only
ls-remote of origin refs/heads/develop returned exactly f6cb92a. No fresh-base
claim is derived from the stale tracking ref.

The retained independent shopping review remains historical evidence, not a current checkout dependency.
Its probe-results, review runner and check-output hashes were verified. Verdict:
PASS bounded in-memory list proposal/confirmation only; URL transport, source
admission, session binding and production consumer installation unqualified.
That source verdict does NOT accept this new composition. Independent candidate
review/root acceptance are pending. Publication hold and exact prior PR action
rejection remain binding. No PR retry, alternate actor, push or external write.

Exact source delta: adapter module is byte-identical to reviewed f007245
(SHA256 603aa5115fa15de9e6d6324b9c6c782553326094f03a01b35601f3d5b2f5e2ac).
Test delta adds two assertions/probes within the owned test file: actual
shoppingItems 75 g x4 servings x2 meals minus 200 g inventory =400 g, with no
packCount inference; current configured Arabic default fallback preserves Arabic
shopping labels, unknown/null quantity and exact source identity through fresh
confirmation. Documentation delta is this composition receipt section only.

Eight existing reviewed dependency files are unchanged. public/i18n.js and
public/locale-negotiation.js changed only to pass/use the configured defaultLocale
and honor exclusions when choosing fallback. They are used from this exact base,
not copied from a former branch. The new locale probe exercises that actual
changed interface. public/record-policy.js matches the retained ac19 helper's
reviewed dependency bytes. The helper remains pinned/injected, never automatically
installed as a provider authority or source admission mechanism.

Focused check: node --test tests-web/shopping-handoff-owner31.test.mjs,
7 passed, 0 failed. No broad suite or production browser/transport was exercised.
The actual shoppingItems->adapter->exact helper chain is checked against the new
base. A synthetic reviewRef in fixtures does not impersonate independent review.

Confirmation interface remains: read() must supply current trusted accountId,
kitchenId, revision, sessionEpoch, canExport:true, demo:false, data and admitted
rights-bearing per-line bindings plus source policies. preview(request) binds a
new id, kind:'retailer' and opaque destinationId to all current lines/records.
The caller must render that entire preview, then explicitly confirm the SAME
controller-issued view with {confirmed:true}; changed list/scope/session/source
provenance requires a new preview, and success consumes the view. Confirm only
returns a confirmed proposal. Neither copied metadata nor reviewRef/admitted
booleans prove user/account/source authority. No purchasing, navigation or sharing
executes. Owner03/02/04 hook, bindings and accepted session producers remain the
same separate requirements; no central file or other owner's code changed.

This local checkpoint is intentionally NOT privately backed up under the current
no-publication instruction. Prior refs/private backups/reviews remain preserved.
Shared main/index, cached refs and existing untracked custody were not changed;
only the three authored owned paths were committed. Production STOP remains.
