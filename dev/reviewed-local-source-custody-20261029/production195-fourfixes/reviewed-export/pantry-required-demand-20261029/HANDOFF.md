# Pantry duration: require actual measured demand

Row SHOPPING-PLAN-DURATION. Branch source pinned72d146c. With no stock, an optional-only recipe was selected10000times; when mixed with a real measured recipe it masked the finite estimate. Root cause: the required-ingredient .every predicate accepts an empty array and the simulation skips every optional ingredient, so no stock is consumed.

Fix: require at least one nonoptional ingredient in the existing usable-recipe filter. No new meal/reservation semantics, source data or ingredient mapping. Three regressions fail baseline; all six focused checks pass candidate, including ordinary finite consumption, optional garnishes, unknown yields, and input preservation.

Deliverables: two-file patch, exact predicate-replacement JSON, baseline/candidate logs and manifest. Existing sole integration writer reviews/applies only the predicate correction and adds the test file. IMPORTANT: public/household-model.js on this branch does not itself contain the193 expiry correction recorded in deployment receipts. Preserve the actual latest deployed simulated-day and expiry-aware deduction code; never overwrite it from this snapshot. If applying the full line-based patch conflicts, use the exact predicate replacement in the current actual source and run these tests there alongside existing duration regression checks. No production regression or full duration acceptance claimed from this source-only candidate.

No scanner, corpus, shared checkout, user data, GitHub Actions, external data, or production mutation occurred. Rights/receipt/qualified-source prerequisites remain open. Integration is pending normal existing single-writer follow-through, no user decision requested.
