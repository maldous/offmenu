# Owner39 portable health persistence/withdrawal consumer

Actual pickup: fresh shared-lock fetch origin/develop at148fec8102ee64ec6801d4df96dfeb9a946ac619, exit0, completed before2026-10-14T16:26:15.174431Z. Branch feature/native-health-consumer-owner39-20261015. Prior be8d7040acc4789ae5e3a0dd227a206913cf2cce superseded draft/review checkpoint remains immutable on feature/native-health-import-owner39-20261015. Prior source and Bangladesh evidence/refs remain preserved. Owned paths only: cloud/native-health-import-owner39.mjs, tests-web/native-health-import-owner39.test.mjs and this note.

## Composition and exported operations

createNativeHealthConsumer exports import(request, command), withdraw(request, command) and publicProjection(). It composes EXACT Owner28 validateHealthImport, commit a108e1645ad5f19a5e0fe85e37e5c080f3582d8f, source SHA-25694b84d2420d8c900d61eab0dab458c05d3b16942f15d860369854743e6fcdc4b. Owner28 remains the portable envelope parser; this consumer does not normalize units/types or bypass its rejected rows. A trusted server loader supplies preview and sourceSha256, verifying bytes before evaluation. The digest field is a trusted binding assertion, not proof that an arbitrary injected function is genuine; the test loader actually verifies the Git source hash.

Host construction:

    const consumer = createNativeHealthConsumer({
      preview: exactReviewedOwner28.validateHealthImport,
      sourceSha256: verifiedOwner28SourceSHA256,
      authenticate: verifiedCurrentAccount,
      transaction: atomicAccountMemberHealthTransaction
    });

No central handler/schema/shared caller edits. No implicit storage, provider, SDK or network call. The module is a usable local boundary when its documented trusted bindings are supplied; it is held from application/D1 adoption until those bindings are independently qualified.

Import command fields: operationId, memberId, sourceId, expectedRevision, upload (the serialized28 envelope), selectedIds (unique preview record IDs), details (one for each selected ID). Each detail names recordId, sourceRecordId, sourceRevision, originDevice, vendor, startAt, endAt, timeZone, valueLexeme. Source IDs/revisions are explicit source assertions, not evidence that a real vendor issued them. The portable envelope stays manual-export/vendor-export; native modes remain rejected by28.

Owner28 checks source/member/account/consent/types/units/UTC timestamps. Consumer confirms that the selected subset belongs to this preview and that all details match its record/source ID and start timestamp. Decimal raw lexemes must numerically equal the validated preview value and are retained unchanged. Unknown numeric lexemes are NOT converted to zero: unsupported/missing quantities must remain in28 rejected-row review rather than enter storage. Only explicit nonfuture UTC intervals and an Intl-supported declared zone are admitted, without inventing offset/device clock fidelity. Source devices/vendors must be in the current authoritative policy lists.

## Authoritative transaction contract

transaction(owner, callback) MUST serialize all health writes for this account, including other callers. Callback is synchronous and gets state, authorize and commit. authorize receives action, owner/member/source and commandDigest; it MUST load current session, account membership (including child restrictions), source permission and consent in this same atomic boundary. It returns sessionCurrent/sourceActive, current28 context, device/vendor allowlists and confirmationDigest from an already-authorized exact-selection confirmation. Never copy these values from packet booleans or accept a client digest as server confirmation. A separate preflight check followed by a nonconditional write is insufficient.

Input is descriptor-checked and copied synchronously before any digest/authentication await. Accessors, non-JSON fields, sparse arrays and oversized/deep commands are refused. healthCommandDigest supplies the deterministic digest to the trusted confirmation service; upload, selection and metadata changes alter it. Consent/account/member/source state is rechecked after authentication inside the transaction. Confirmation is bound to the complete command, not merely the number of accepted rows.

State contract: {owner, revision, records, tombstones, operations}. Maximum1,000 retained records,1,000 withdrawal tombstones,1,000 replay entries; overflow refuses without truncating history. Existing records require qualified member/source/record/revision/interval metadata; old unqualified health-model rows cannot silently bypass overlap checks. Each operation key is memberId+operationId inside account partition, bound to the exact command digest. Same command replay returns the stored private receipt without new writes, after current policy checks. Conflicting operation reuse and stale account revisions refuse. Caller cannot use an old preview as current consent authority.

Committed record identity is member+source+sourceRecordId+type, preserving exportId, consentId, source mode and imported-unverified status from28. A lower sourceRevision refuses. Same revision with different content refuses; a higher revision can replace its same source record only after measured overlap checking. Source revision metadata does not establish vendor authenticity without the companion/provider qualification still missing.

Measured observations of the same member/type with intersecting half-open intervals (including point observations inside an interval or equal point instants) refuse across sources and within the batch. Adjacent intervals do not overlap. No steps/activity/sleep sums or schedule merging occur. Owner34 retains planned schedule and overlap model ownership; this conservative refusal is an ingestion gate, not a universal deduplication/clinical rule. More complex measured aggregation must be reviewed separately.

commit({state,revoke}) MUST atomically persist state and disable the source/member grant for withdrawal, or roll back all changes on any callback failure. Withdrawal removes private measurement values and stores minimal owner/member/source/record/type/sourceRevision tombstones. Later reactivation cannot reimport a tombstoned record through this boundary. It retains replay evidence without raw values. PublicProjection always omits measurements; private reads/exports require independently authorized account/member callers and are NOT provided by this module.

## Unknown outcomes and privacy

Known HealthImportRefusal means the callback refuses admission, assuming the host rollback contract. A backend exception returns status=unknown plus operationId only: it does not claim persistence failed or succeeded. The harness explicitly loses the response after commit and verifies this remains unknown. The host must reconcile its authoritative operation receipt before retry/adoption. A withdrawal retry after revoked permission cannot be used to regain access; a separately authorized operation-receipt query is a missing host dependency. No raw health values in logs/error receipts, no public projection, no credentials or session capabilities stored here.

## D1 / caller adoption hold and ownership reconciliation

Root clarified that04f889 was an owner-number shorthand. Exact selected commit f88902e87baa4e901006ec87083080c5188d06dd now resolves and was inspected, cloud/session-state-d1-owner04.mjs SHA-2561dc8633974f83f643d13b27cdeb44f3e4a4c3093c487583ff8719fefa574d12a. It implements generic /api/state session tables and validateState, not this health record/source/withdrawal envelope. Review11 checkpoint05debc7742b58d61f7a18b09e00a57610838edc3 was also inspected; it qualifies that protocol scope only. It must not be represented as a schema-compatible health store. A reviewed compatible account/member health transaction schema/binding is still required; resolving04 does not remove this hold. This task installs no D1 schema and supplies no actual D1 proof. The end-to-end harness is an in-memory synthetic atomic store.

Coordination is by exact owned paths/contracts read:28 portable validator remains unchanged;34 public/activity-schedule-model.js and docs/activity-schedule-owner34.md retain planned-health responsibilities;04 session-state-d1 contract retains identity/session/database ownership;03 public/integration-owner03.mjs and production-integration-owner03.json retain actual confirmation/UI caller integration. No cross-thread adoption approval is claimed. Different existing Owner34 review is required AFTER its activity review completes; root routes the immutable candidate. No request to bypass that review or current ownership.

## Tests, fixtures and qualification

Eight synthetic tests compose an explicitly included exact28 module snapshot (base64 in the owned test, decoded and source-hash-checked) with a meaningful local commit harness: exact preview→confirmed private commit; replay/conflicting command; cross-account/member/revoked session/consent/stale account; overlapping separate sources; source revision/content/origin/interval/lexeme mismatches; atomic delete+tombstone+grant withdrawal; mutation across auth await; lost response after persistence. These are fixture/model tests, not native/vendor records, actual D1, network access or clinical qualification.

Run: node --test tests-web/native-health-import-owner39.test.mjs. Production closure is the owned module plus explicitly injected server hooks, with no runtime Git or mutable owner import. Test closure is the owned module/test plus the embedded exact28 module snapshot and built-in Node. No historical Git/common-directory objects are needed at test execution; the module inclusion is executable code evidence, not an actual vendor fixture. Production integration must supply the same reviewed validator through a verified explicit server binding; an arbitrary function with a claimed digest is not proof. No installation or SDK acquisition.

OriginalPDF02 pp6/9 was read under prior review, fileSHA-2562d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c: preserve date/unit/source/consent and source permission lineage. Official Android/Apple permission distinctions remain recorded in immutablebe8d review. Browser login is not native health access; HealthKit read denial is hidden. No compatibility or permission/device/provider coverage is newly claimed. Permitted actual native/vendor fixtures remain unavailable; no new fixtures from vendors, device data, credentials, SDKs or corpus operations were acquired.

Missing native coverage: HealthKit/Health Connect companion permissions and revocation on physical device, source-issued revision/device/time metadata witness, vendor export terms/approved access, old-record interval adoption, independently qualified owner04 atomic store and owner03 confirmation caller. Numeric unknowns/native offsets unsupported by28 remain explicit review dependencies. No universal normalization, central writes, admission, unreviewed merge or production changes. Mandatory auto_review retained. Supplied filesystem unrestricted/network enabled; separate approval-policy/user configuration unavailable. Private backup and independent ls-remote SHA are reported at handoff.

Portable closure verification: copied only the three owned files into a disposable directory with no .git, historical objects, other-owner files or node_modules. All eight tests passed there. The disposable copy was removed. This verifies the declared local test closure, not native D1 or vendor access.
