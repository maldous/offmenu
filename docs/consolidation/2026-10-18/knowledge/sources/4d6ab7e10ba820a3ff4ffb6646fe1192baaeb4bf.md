# Worker 24 waste analysis — ready for Morgan review

Requirement: [P2-05](recommendation-delivery-register.json), “Measured waste reasons/quantity/value and seasonal smaller-pack suggestions”; dependent on P2-02 stock custody and P2-04 pack/cost snapshots. Register status remains unassessed; this does not update acceptance.

Dispatch base: 8652b312ce7989c5e4f2d49ae765d5d8daf5841d on feature/waste-analysis-20261014. Dispatch supplied fresh origin/develop fetch exit 0 at 2026-10-14T06:40:54.126855+00:00. PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE; baseline/release qualification remains pending.

## Existing-source gap and bounded negative example

public/checkout-model.js:5 deducts partial amounts after checking source identity, location and stock. tests-web/insights.test.mjs:7 already covers this; no duplicate deduction helper was added. public/insights-ui.js:19 reports cleanup receipt count. public/documents.js:19 lists discarded dates, source, name and quantities, with no value, reason/season analysis or unknown cost coverage. The app's receipt flow (public/app.js:136) only exposes discard amount. These are retained unchanged.

For two measured waste rows (125 g from source lot-1 with a captured 500 g/AUD 4 cost, and 50 g from lot-2 with no cost), the current report can list quantities but provides no AUD 1 known subtotal or one-record unknown-value coverage. The added test encodes those expectations. Before implementation the focused test failed with ERR_MODULE_NOT_FOUND; after implementation it passes. The missing behavior is evidenced by the existing renderers above, not merely by that missing import.

## Integration contract

The new pure analyzeWaste(rows, {accountId}) consumes up to 1000 owner-adapted rows with explicit accountId, receiptId, sourceId, measured flag, positive quantity and unit. Optional reason and season remain unknown if absent. costSnapshot is an immutable purchase/stock-cost observation with matching sourceId, quantity, unit, amount and currency. Cost is proportional only when the discard fits that snapshot; no unit conversion or current price lookup. Totals remain separate by exact unit/currency. A real zero cost is known; missing/invalid cost is null. The caller retains original snapshots and their provenance/uncertainty. An assumed full-pack quantity must never be marked measured.

An owner-controlled future caller in insights-ui.js or documents.js can import analyzeWaste, adapt consented profile.waste receipts and join P2-02/P2-04 source snapshots by immutable identity, then render result.values and result.coverage together. Account mismatch rejects the entire request. Existing receipt data lacks this complete contract: do not invent account IDs, measurement provenance, reason, season, cost, or permissions. Schema/capture changes and rendering require their owners' review before adoption. No app integration is included.

Suggestions are optional planning prompts only: recorded oversized-pack reason, explicit observed season, measured discard, and smaller same-unit pack options with the same explicit season. Options retain source IDs (maximum 100 per eligible row). No nutrition/allergy/safety/expiry/equivalence, availability, savings, ownership or purchase authority is inferred. Offers and source rights/consent must be validated by the adapting owner; this module performs no access grant or external action. Duplicate input rows are caller responsibility; bounded pages are not all-time totals. Monetary outputs are unrounded proportional values; currency display/rounding is caller-owned.

## Actual checks and custody

1. node --test tests-web/waste-analysis-model.test.mjs — expected pre-implementation failure (missing module).
2. node --test tests-web/waste-analysis-model.test.mjs tests-web/insights.test.mjs — 11 passed, 0 failed. Synthetic fixtures only; no Git-writing fixtures, provider calls, installs, servers or broad suites.

Only the three reserved new files changed. Shared common-dir is /home/user/src/offmenu/.git. Shared main was 8652b312ce7989c5e4f2d49ae765d5d8daf5841d and shared index hash was 278bf843ee0776af9cbb80ad26ae938583396c3b before work; commit preparation checks both unchanged. No other workers or sessions created.

Status: READY FOR MORGAN REVIEW. Not shipped, integrated, accepted or release-certified. Future integration requires Morgan custody/review gates and separate baseline qualification.
