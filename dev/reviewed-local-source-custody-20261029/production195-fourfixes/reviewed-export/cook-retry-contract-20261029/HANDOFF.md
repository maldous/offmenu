# Cooking retry conflict check

Row CONSUMPTION-LEFTOVERS-RECONCILIATION. Source pinned72d146c. Three regressions demonstrate cookMeal silently returns duplicate success for changed recipe ID, serving count or date when matching a live mutation or plan batch. Unlike serveBatch its duplicate branch never reconciled the stored request dimensions.

The correction rejects differing stored recipeId/servings/date before returning the existing batch. Valid same-request retries, retry without optional plan binding, new mutation ID for the same plan and cooking after undo remain supported. Three regression failures on baseline; all seven focused checks pass candidate, without stock mutation on rejection. No ingredient/content identity, receipt producer, auth, upstream proof or historical source-use policy is inferred.

Existing sole integration writer reviews this two-file delta against the latest actual app source, preserving any newer cooking changes; replacement.json supplies the exact function-local edit. Use current normal localization extraction for the new error string if required. Rerun these focused checks with integrated cooking checks. No production or authenticated acceptance claimed. Parent producer/confirmed-receipt join remains open. No scanner/pantry/corpus/shared-checkout/provider/GitHub Actions/deploy mutation.
