# Worker 21: whole-lot stock observations

Status: READY FOR MORGAN REVIEW after focused checks; not integrated, accepted or release certified.

## Dispatch and baseline

- Branch: `feature/stock-transitions-20261014`.
- Pinned base: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; HEAD and local `origin/develop` match.
- Dispatch supplied fresh fetch receipt: exit 0, `2026-10-14T06:40:46.646518+00:00`.
- Verdict: PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE; baseline qualification pending.
- No additional workers, worktrees, sessions, dependencies or corpora.

## Requirement and concrete gap

[Delivery plan](research-delivery-plan.md), Capture and reliable inventory row, requires
opened/frozen/thawed and partial/decanter lots. Dependencies in the
[requirement register](recommendation-delivery-register.json): P0-03 (ingredient identity
and dimensional units), P0-06 (cooking/serving/leftovers/waste reconciliation), TRUST-03
(use-by/best-before/review reminder distinctions). Their register status is unassessed;
this slice does not change those receipts or assert acceptance.

At the pinned base:

- `public/model.js:4–20`, `validateLot`, projects a fixed set of lot fields and drops
  `openedAt`, `frozenAt` and `containerId`. `cloud/state.mjs:7` uses that projection.
- `public/freshness-ui.js:6` edits entered expiry/reminder fields, with no stock transition operation.
- `public/checkout-model.js:3–10`, `finishInventory`, supports shelf/shopping/waste;
  partial waste subtracts quantity rather than preserving a lot through a transition.
- Existing `tests-web/insights.test.mjs:7–8` cover partial waste and reminder validation.
  Those behaviors already exist and are not reimplemented.

The new test's bounded negative example passes a synthetic 125.5 ml lot with observation
metadata through `validateLot`: all three transition fields disappear. Waste of 25.5 ml
leaves 100 ml, demonstrating why a waste operation cannot model a whole-lot observation.

## Independent contract

`transitionStock(state, command, {clock})` operates on a caller-owned envelope:
`{accountId, inventory, events}`. It appends an explicitly confirmed opened/frozen/thawed/
decanted event; every inventory field and quantity is deep-cloned unchanged. The
destination of whole-lot decanting is a container identifier, not a new lot identifier.
It does not convert units, split lots, move storage locations, calculate dates or infer
that food is safe. Label dates, uncertainty, nutrition/allergy unknowns, source rights
and consent metadata remain unchanged. A past date is preserved without a safety verdict.

The command must include the same account scope, the reviewed complete lot snapshot,
expected journal count, unique event ID, action and `confirmed:true`; decanting also
requires `containerId`. Stale snapshots/history, duplicate IDs, empty lots, unsupported
actions, missing confirmation and invalid clocks fail without mutating input. Unknown
thermal history cannot be thawed; a recorded freeze is required. The clock supplies a
canonical UTC observation instant and cannot precede that lot's last event. State is
bounded to 10,000 lots and 999 existing events; a full journal requires owner review,
not silent truncation. Replays fail explicitly, rather than implying retry-safe persistence.

Example for a future existing caller in `app.js`/`freshness-ui.js`:

```js
const next = transitionStock({accountId, inventory: lots, events: journal}, {
  accountId, lotId: selectedLot.id, expectedLot: reviewedLot,
  expectedEventCount: journal.length, eventId: userOperationId,
  action: 'decanted', containerId: reviewedContainerId, confirmed: true
}, {clock: () => observedAtUTC});
// Authorized owner must atomically persist next.inventory and next.events
// in the same account/kitchen, using a revision conflict check.
```

## Owner-controlled integration dependencies and limitations

App/freshness UI and cloud state owners must design journal validation/persistence,
authenticated account/kitchen scope, permission and consent checks, atomic revisions,
retry handling, display, backup and sync before adopting this reducer. String scope
equality and `confirmed:true` are consistency checks, not authentication or authorization.
The legacy state validator will not persist this envelope's events. Do not wire this
module into `save()` alone: the journal would be lost. No existing UI, schema, source
data, auth, sync or validator is modified here. Existing callers remain unchanged.

This slice covers whole-lot observations only. Partial decanting/splitting, inherited
thermal history, event retention policy, imported journal semantic qualification and
cooking allocation reconciliation remain integration work dependent on P0-03/P0-06.
Caller supplies a trusted, account-scoped journal and stable lot IDs. No real providers,
medical claims, expiry extensions, purchases, servers, jobs or deployment were used.

## Actual focused checks

`node --test tests-web/stock-transition-model.test.mjs`: 6 passed, 0 failed.
Coverage includes the existing-source negative example, all four transitions, deep input
immutability, provenance and unknown values, unchanged past label/reminder dates,
thermal preconditions, scope/confirmation, stale quantity/source/history, missing and
duplicate lots, event replay, clock validity/order and journal bounds.
Staged `git diff --check` and shared common-directory/main/index invariants are checked
before committing and read back afterward. No Git-writing test fixture is used.

Unit evidence qualifies only this independent model contract; it is not shipped behavior.
