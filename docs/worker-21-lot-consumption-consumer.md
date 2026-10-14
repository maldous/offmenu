# Worker 21: transactional partial lot consumption and decanting

READY FOR INDEPENDENT REVIEW. No adoption, integration or release acceptance implied.

## Pickup and custody

Same permanent local worker: thread `01a138f9-d5c4-75c0-9ccb-91dac497b5a9`,
checkout `/home/user/src/offmenu-workers/worker-21`, host `foo` (prior verified readback).
Dispatch source/root: `01a137cf-2242-761d-8fd7-6e6fc5658013`.
New branch: `feature/lot-consumption-consumer-21-20261014`.
Locked origin/develop fetch exited 0 at `2026-10-14T10:16:13.456810+00:00`;
exact base `908ca373dfc918f2e33fd5e44260879577bed5c5`.

Preserved previous clean branch `feature/dataset-india-ifct-20261014` and full pin
`3fb6ee105d8d9c7bd09e50587b0ccf7716ad9e0b`. Prior staged/tracked/untracked changes:
none; no untracked dependency links were present. Prior branch/artifacts remain reachable
through Git; no reset, clean, forced update, deletion or copied corpus.

Dataset blob hashes:

- source.csv: `376c2647f73359175cd247e54af58ce79412f30023169a678261694c2fbfcc59`
- receipt.json: `a5189c2e0cb20100678180cf00230a3b00850d10a40c6eedff5a2a89c5d974d9`
- note.md: `53ed04c257883cd80677fd54eaefa763f597fe24596f8e6f948319353bf2dab1`

Retained transition helper verified at full pin
`c051de0f7895cabc490466693f3cde993bd4d48e` on its unchanged branch.
It preserves whole-lot observations, explicitly defers partial decanting, and does not
provide atomic persistence. Its independent review remains required. This adapter
does not import/copy/adopt that helper; no independent approval has been invented.

Actual supplied filesystem control is unrestricted `danger-full-access`; network enabled;
mandatory reviewer `auto_review`. Separate approval policy unavailable.
Environment permission profile `disabled`; CODEX_PERMISSION_PROFILE unset in prior readback,
not a named full-access profile inference. No settings changes.

## Existing behavior and requirement links

[P0-03/P0-06/TRUST-03](recommendation-delivery-register.json) and
[capture/consumption requirements](research-delivery-plan.md) remain the links.
Existing `checkout-model.js:finishInventory` already supports partial waste; it does
not represent consumption versus waste or decanted destination lineage.
`model.js:validateLot` and `cloud/state.mjs:validateState` drop unrecognized lot metadata.
`cloud/handler.mjs` atomically versions entire `/api/state` saves, but does not have a
lot operation endpoint or persisted operation acknowledgement there.

## Usable server consumer

`cloud/lot-consumption-owner21.mjs` is transport-neutral; no Worker/D1 API, route,
production schema migration, authentication issuer or deployment is added.
`createLotConsumptionConsumer` authenticates the request using a trusted injected
hook and enforces an injected request policy. Body account authority is rejected.
The account is captured before asynchronous policy work. Inputs are captured as bounded
plain JSON without invoking coercion/accessor hooks.

Inside one caller-owned admitted transaction it checks session admission, immutable
operation replay, exact expected revision, complete reviewed source snapshot, measured
amount/unit/provenance, then writes updated state and immutable acknowledgement together.
The transaction implementation must roll back both writes on failure. Matching replay
returns the original receipt; changed command using the same ID conflicts. Admission
occurs before replay, so a revoked session cannot read a receipt through this consumer.

Quantity arithmetic uses exact scaled integers with at most nine decimal places and
maximum magnitude 1e9. Unsupported precision, nonrepresentable results, unit mismatch,
underflow and implicit conversions reject. Zero remainder removes the source entry;
  the immutable receipt retains its complete source snapshot, identity and quantity. Consumption describes physical
stock removal; nutritional intake and medical safety are not inferred.

Partial decant keeps the source lot ID, creates an explicit distinct destination sublot,
records root/source lineage and container, copies source evidence and entered dates,
and uses the user's explicit destination location. Quantities retain the observed unit.
No density, recipe yield, expiry extension or allergen/nutritional equivalence is inferred.
`quantityObservation21` stores the changed quantity observation; original `amountBasis`
and unit evidence remain historical source evidence, not a new full-pack assertion.
Cooked lots reject: owner 19 must reconcile batch/serving quantities instead.

## Coordination evidence and exact remaining adoption delta

Read-only inspection of current owner threads showed Worker 03's integration map and
narrow insights UI reservation; Worker 04's isolated session-state protocol is being
implemented with owner 02/16 coordination. This worker did not edit their checkouts
or send coordination messages. The following contract is proposed for their review;
no path release or independent acceptance is assumed. Reserved writers remain 02 for
app/state/handler/schema and 03 for its selected consumer hook.

Owner 04's observed `cloud/session-state-owner04.mjs` exposes a synchronous SQLite
transaction store with session admission, subject-scoped state CAS, and operation ledger.
Its current `write` validates/projections full states before committing, so it cannot
silently substitute for this metadata-preserving transformation. Its exact candidate
pin must be selected and independently reviewed before using the proposal below.

Minimal proposed method **inside** owner 04's protocol factory (using its existing
private context/binding/admission/transaction helpers):

```js
async lotTransaction({request, accountId}, work) {
  const ctx = await context(request, 'lot-consumption');
  if (ctx.subject !== accountId) deny('SUBJECT_MISMATCH');
  const b = await binding(request);
  return transaction(tx => {
    const row = admission(tx, ctx, b);
    return work({
      admit: () => true, // persisted grant was checked in this same transaction
      state: () => tx.state(ctx.subject),
      operation: id => tx.operation(row, id),
      write: (version, json, at) => tx.write(ctx.subject, version, json, at),
      record: (id, digest, result) => tx.record(row, id, digest, result)
    });
  });
}
```

This is a trusted internal callback, never client-supplied executable code.
Owner 04 request policy must explicitly admit the new resource/method; its current
fixed `/api/state` audience is not a grant to a new endpoint. Owner 04's session and
operation identifiers have stricter length/syntax than this generic consumer; enforce
those at that boundary. Persisted grant/epoch/audience must remain in the same transaction.
No legacy bearer-only fallback is allowed when the session transaction hook is missing.

Owner 02 minimal handler delta, after approved dependency inclusion:

1. Import `createLotConsumptionConsumer` from the unique server module.
2. Construct it with real `verifiedUser`, explicit POST/exact-Origin/resource policy,
   reviewed owner 04 `lotTransaction`, and injected server UTC clock.
3. For exactly `/api/lot-consumption`, reject unsupported methods, parse command with
   existing `boundedJSON(request,65536)`, invoke consumer, and return no-store JSON.
   Map known LotOperationError status; ambiguous storage/transport failures require
   retry with the same operation ID or authoritative status read, not a new deduction.
4. Preserve and validate `quantityObservation21`, `lotLineage21`, and approved existing
   source metadata in lot backup/PUT/sync projections, or reject lossy saves explicitly.
   This requires owner-reviewed typed validation; arbitrary unknown fields must not
   become admitted nutrition/rights assertions. Tests below demonstrate current loss.

Owner 03/02 UI adoption must collect measured quantity/unit/source evidence, destination
identity/container/location for decant, capture full reviewed lot and revision, retain
one operation ID through acknowledgement loss, and refresh authoritative state only
after receipt. No hook in existing app/UI was reserved for this worker, so none changed.
Shared kitchens, private-field projections, backup restore and cooked-batch linkage
remain separate owner contracts. The current adapter handles private account stock only.

## Actual bounded evidence

`node --test tests-web/lot-consumption-owner21.test.mjs`: final **8 passed, 0 failed**.
Initial run found a test fixture syntax error; fixed before any checks could execute.

Tests use actual disposable SQLite files, two independent connections, existing raw
`cloud/schema.sql`, and clearly test-only grant/ledger tables. They exercise:

- Partial/full consumption/decanting, exact decimal quantities and source metadata.
- Atomic version/CAS conflicts, injected ledger failure with whole-transaction rollback.
- Lost acknowledgement replay and changed-ID-content conflict.
- Revocation after async policy but before transaction; account/Origin denial.
- Unit/provenance/snapshot/cooked-batch/precision guards, input capture and hostile JSON.
- Actual existing `handler.fetch(GET /api/state)` reading committed revision and lineage,
  then actual `validateState` proving the metadata loss in the current PUT projection.

This proves the adapter and a real existing read entrypoint, not an installed write route,
production session issuer, D1 replication/transaction parity or full app acceptance.
The test grant policy is synthetic; it does not qualify owner 04's production session protocol.
Independent exact-pin review of retained helper and new candidate remains pending.
No providers, payment, bulk acquisition, browser/server, Actions, deploy or settings changes.

Before/after commit assertions retain common-directory identity, primary HEAD/main/index,
the prior dataset branch/blob hashes and helper branch pin. Only this doc, the unique
server module and its focused unique tests are committed.
