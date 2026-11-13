# Collaborative shopping: review-ready caller correction and exact contract proof

## Result first

A current production193 caller defect is reproduced and corrected locally: shared-kitchen viewers can toggle both custom and planned shopping checkboxes, mutating/persisting the local shared-list projection even though the server correctly refuses their writes. The app's existing capture listener filters buttons and submits, not checkbox changes. This is a local misleading-write defect, not demonstrated server authorization bypass.

The candidate passes all 53 available retained/new tests. The new focused suite is baseline 3 pass / 8 fail and candidate 11 pass / 0 fail. An additional six-test contract suite exercises the **exact retained production193 server module**, isolated with synthetic identities and in-memory SQLite: two-member revision conflicts/reconciliation, viewer/nonmember refusals, list-versus-stock separation, stock PUT replay, scanner replay, and private-field projection all pass.

## Minimal delivery artifact

- `shopping-write-scope.patch`: only `public/app.js`, `public/insights-ui.js`, and new `tests-web/shopping-write-scope.test.mjs`.
- `candidate/`: isolated retained app source plus those changes and tests. Do not copy the whole directory over newer parent source.
- `manifest.json`: exact preimages/postimages and validation scope.
- `build-receipt.json`, `build.log`: offline 69-input build with pinned esbuild 0.25.12 and exact retained auth dependency hashes; no external imports.
- Baseline app rebuild exactly equals production193 asset `9b0d51064d746887ee70dbb79baee98e32a4eb57caf8652a7111d3b9e383bf67`.
- Candidate browser app SHA256 `ebbd983538157b8ef9d717c5db5ce20f80ef624cb657904f67ee68c33b089015` (464,128 bytes).

The app change adds `canWriteShopping:()=>sharing.canWrite()` to the existing `setupInsights` call. Insights disables viewer checkbox/remove controls and rechecks that existing capability inside check/add/remove handlers, including changes between rendering and activation. No auth API, server, sharing lifecycle, manual save, history, expiry, or planner changes.

**Parent is the only integration/deployment writer.** This handoff is review-ready, not reviewed or deployed. Rebase the two narrow source hunks against the current parent source before integration. `public/app.js` baseline SHA256 is `55bc0086192208e7fe0892ef7fe8a0d34c67f293290c48f33b7597929f997ee2`; `public/insights-ui.js` baseline is `45937c6133b3f70af1c2a0cbc589c9d7d889d5fc190a2dd00afd24a1ec39e863`.

## Actual list/received-stock contract

1. `public/integrations.js:shoppingItems` derives planned/review rows and appends custom `profile.shopping` rows. Planned/review checks live in `profile.shoppingChecked`; custom checks are the row's boolean `checked`.
2. `public/insights-ui.js:renderShopping` changes only those fields. CSV labels this `Collected`. A check does **not** create a lot or establish a received quantity, location, source, or receipt.
3. `public/sync-model.js:kitchenProjection/applyKitchen` includes inventory plus plan/shopping/checks/batches. It excludes person history, goals, members and selection/private nutrition fields from shared projection; applying shared state preserves the current account's personal fields.
4. `public/sharing-ui.js` wraps the existing `setupSync` caller. `public/sync-ui.js` GETs current state, three-way merges using the known baseline, then PUTs the resulting state and revision. Exact server state writes require a current non-viewer member and atomically compare/increment the kitchen revision. A stale PUT returns 409; this is not an operation-ID receipt API.
5. `public/app.js:confirm-finish` validates the current checkout/scope, calls `finishInventory`, saves inventory and the local last receipt, then clears the checkout. `public/checkout-model.js:finishInventory` receives separately scanned/manually reviewed quantities into the selected location. A normal repeated checkout with existing lot IDs is rejected as duplicate; an exact scanner-completion replay is a no-op. Partial/conflicting scanner replay fails closed. Unknown source-stock quantity guards remain unchanged.
6. Concurrent independent list edits merge by stable item ID. Concurrent quantity edits to the same lot conflict rather than silently summing. Stale state PUT retry cannot double stock: the old revision is rejected and retry reconciliation still contains one lot.

**Remaining parent-obligation gap:** no current list-item -> confirmed receive operation -> inventory-lot/receipt binding exists. Neither a check nor matching food text is evidence that stock was received. The model cannot distinguish two independently created lot IDs representing the same physical purchase. A full linked lifecycle requires the authorized existing consumer/producer contract, stable item/operation/receipt provenance and ownership semantics; this lane neither invents them nor activates held receipt integration. The accepted boundary proof and local viewer correction do not close the full `COLLABORATIVE-SHOPPING-LIST` obligation.

## Evidence and rerun

`mcp-provenance.json` records this agent's successful own GitHub MCP read of `docs/operations/morgan-delivery-ledger.json` at exact commit `e2ec394485254ed2edc217078af67e72d8d608d7`. Historical ledger prose remains evidence, not new retry authority.

```sh
node --test candidate/tests-web/*.test.mjs
node build-app.mjs
```

Logs: `baseline-tests.log` (expected regression failures), `candidate-tests.log` (11/11), `contract-tests.log` (6/6), `all-tests.log` (53/53). Syntax checks passed for both changed source files. The contract test is a handoff-only harness requiring the retained `server/` artifact beside `candidate/`; only the focused shopping test is in the source patch. Actual server module SHA256 is `0e4420ef0152586a80cf982d7084582180b9e8798d9dd87cb6aae304da305a34`. Its unchanged source-reference module SHA256 is `c62237c29a2e32fd1c09653512903e0019af4c9c59cef1e510e2f129c5f32bb1`.

All server authentication fetches were local synthetic mocks, all DB calls used `:memory:` SQLite, and no external provider, user state, live database, receipt integration, Git write, production deploy, workflow, or quota executor was used. Synthetic DOM and SQLite tests are not authenticated real-browser/device or live D1 acceptance. No tool denial occurred.

## Parent review correction

Confirmed the reported captured-row display defect: after a planned checkbox is set while editable, its captured `item.checked` remains stale even though `profile.shoppingChecked` is current. Revoking write capability and attempting a toggle restored that stale value. `parent-review-repro.log` records 10/11 before correction with the new targeted tests. The denied onchange now resolves the current row from `items()` by ID, restoring canonical checked state without mutation or persistence. Corrected focused tests pass 11/11 and complete retained/new tests pass 53/53. The consumption lane's separate CSV section is untouched; root must merge disjoint hunks, not copy whole files.
