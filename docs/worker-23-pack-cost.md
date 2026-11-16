# Worker 23: selected-offer pack cost

Status: **READY FOR MORGAN REVIEW**. This is an independent calculation slice, not shipped UI, accepted integration, or release certification. Baseline verdict supplied by dispatch: `PROVISIONAL_UNQUALIFIED_INTEGRATION_BASELINE`; baseline qualification remains pending.

## Custody and requirements

- Branch: `feature/pack-cost-20261014` (already present on initial inspection).
- Exact base: `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`; local HEAD and origin/develop matched on inspection.
- Coordinator-supplied fresh origin/develop fetch receipt: exit 0, `2026-10-14T06:40:51.681366+00:00`. Worker 23 did not independently repeat that fetch or certify freshness.
- Requirements: [P2-04](recommendation-delivery-register.json#L217), [NORM-09](recommendation-delivery-register.json#L917), [BASKET-05](recommendation-delivery-register.json#L1365). Dependencies remain [DATA-06](recommendation-delivery-register.json#L413), [DATA-11](recommendation-delivery-register.json#L483), [NORM-05](recommendation-delivery-register.json#L861).
- [Research delivery plan](research-delivery-plan.md#L60) requires shopping gaps, pack rounding, unit price, budget comparison, dated conditions and separation of observation from current availability.

## Exact existing-source gap and bounded example

At the pinned base, `public/integrations.js:4` (`shoppingItems`) returns measured missing quantity/unit plus unmeasured review items and manual additions. `public/menu-model.js:6–8` (`planSummary`) allocates inventory and calculates remaining quantities, without offer selection, pack purchase cost or fees. `public/unified-data.js:13` (`normalizePrices`) retains amount, currency, observation date, retailer, unit price and unknown availability; it does not round purchases or compare budgets. `public/checkout-model.js:16–20` parses inventory package size, not price or shopping offers. `public/basket-model.js` calculates composition metrics, not pack purchase cost. Targeted searches in existing public JS and web tests found no offer-cost evaluator. No existing implementation was duplicated or changed.

Negative example: a 600 g shopping need, 500 g pack priced at 300 AUD minor units, and 50 minor units store fees. Existing shopping output retains a 600 g requirement; it has no fields representing two packs, 400 g leftovers, a 600 purchase subtotal, or a 650 total. Prorating the pack price would give 360, which is consumed-quantity cost rather than purchase cost. The focused fixture requires this distinction explicitly. The initial test invocation exited 1 because the new evaluator module did not exist; that import failure is existence evidence, not a behavioral failure in an existing helper.

## Contract and owner-controlled adoption

`evaluateOfferBasket` is a pure export from `public/offer-comparison-model.js`. It accepts 1–100 caller-selected `{need, offer}` lines and at most 100 per-store fee entries. It reads no clock, storage, transport or environment; the caller injects the calendar date and account id. No Git-writing fixtures or external calls are used.

An integration owner can call it after `shoppingItems` or `planSummary`, once an approved data adapter supplies explicit product identity joins and eligible offer facts:

```js
const quote = evaluateOfferBasket({
  accountId: verifiedAccountId,
  date: selectedShoppingDate,
  currency: 'AUD',
  lines: [{
    need: { id: 'planned:rice|g', productId: reviewedProductId, quantity: 600, unit: 'g' },
    offer: {
      id: reviewedOfferId, productId: reviewedProductId, storeId: reviewedStoreId,
      accountId: verifiedAccountId, currency: 'AUD', observedOn: selectedShoppingDate,
      pack: { quantity: 500, unit: 'g' }, priceMinor: 300,
      provenance: reviewedProvenance
    }
  }],
  fees: [{ storeId: reviewedStoreId, date: selectedShoppingDate, currency: 'AUD', amountMinor: 50 }],
  maxStoreStops: 1, budgetMinor: 650
});
```

The adapter must not equate ingredient names with product identities, or convert a generic `priceObservation` into a current offer automatically. It must establish price-per-pack, promotion/loyalty eligibility, tax inclusion, applicable complete fees, permission/consent and account access under the existing data owner's custody. Same-day observations still represent estimates, not availability. No authentication is performed by this pure helper. Fee inputs are caller-scoped complete store totals; a missing fee is unknown, never implicitly free.

Date compatibility requires a real observed calendar date at or before the requested date. Without an explicit complete validity window, observation date must equal requested date. With an explicit window, the requested date must lie inside it. No food expiry or safety is derived. Dates are explicit business dates, not inferred local clock values.

Only g/kg, ml/l and count conversions within the same dimension are supported. Missing quantity, incompatible identity, date, currency, account, provenance or unit, missing price/fee and unsafe arithmetic withhold complete totals. Prices, fees and budgets use nonnegative safe integer minor units; currency minor-unit conversion is the adapter owner's responsibility. `unitPriceMinor` is per one requested unit; `consumedCostMinor` is an unrounded proportional estimate. Pack purchase cost is rounded by pack count; fees are counted once per distinct store. Duplicate need ids and store fee entries are rejected. Multiple partial lines for the same need must be aggregated first.

`knownSubtotalMinor` is a partial subtotal, never a complete budget. `budgetStatus` and `storeStopStatus` are independently `within`, `exceeded` or `unknown`; `withinBounds` is false for a known violated bound, true only when both pass, otherwise null. The module evaluates a selected basket, not an optimizer. A caller can evaluate independently selected alternatives under the same date/account/currency and display uncertainty; this slice does not choose substitutes, rank health, authorize purchases or search offer combinations.

Outputs retain need/product/offer/store/account identities, provenance (including rights), dates, quantities and uncertainty. The integration owner must keep private results in the existing account-scoped channel. There are no changes to app/UI/auth/schema, source data, requirement records or other owners' files.

## Actual validation and limits

DATA-06/DATA-11 custody and qualification, NORM-05 conversion evidence beyond simple units, approved joins and conditions, UI adoption, accessibility and independent acceptance remain integration dependencies. No real provider coverage, release fitness, allergy/medical suitability, nutrition equivalence, food expiry, ownership or purchase authority is established by these unit tests. the product maintainer review is the next gate; Worker 23 returns to idle afterward.
