# Local OffMenu handoff — original artifacts and review evidence

This evidence-only addition preserves every source/runtime byte from handoff commit `7807b9488ec509747d8ec9b732aed66c1d761f5e`. It does not activate the follow-on or update `integration/manual-actions-20261022` or the receipt branch. Existing local coordinator Worker00 has accepted the source handoff (parent-reported ledger13654); runtime reconciliation and any future activation are now local responsibilities.

## Exact original bytes

- `combined/`: original 22-path patch, current source manifest, and 23-path freeze.
- `reconciliation/`: earlier reviewed executable reconciliation patch, manifest, and freeze.
- `receipt-retry/`: exact incremental recovery patch and manifest over that reconciliation closure.
- `ARTIFACTS.json`: remote paths, original source-artifact locations, byte counts, SHA-256 and Git blob identities.

These are the original files, not patches reconstructed from Git. Apply neither patch to the active Foo checkout merely to inspect this handoff. The current composed runtime is already readable at the source handoff commit; the patches are provenance/transfer evidence. Historical publication gates/targets in original manifests are intentionally unchanged.

## Review provenance

`reviews/` contains the independent reviewer's retrospective records, issued 2026-10-22 20:35:28 UTC. The original PASS records were agent messages/tool results; no contemporaneous standalone signed receipts existed. The reviewer created these records solely for transfer, without new reviews/tests or source edits. They bind exact original artifacts and distinguish eight personally executed R3 hook tests from builder/parent test evidence inspected; composition review was metadata-only. Original review dates and limitations are explicit. This is not a new review, signature, or production acceptance.

No raw datasets, databases/caches, credentials, private runtime output, or raw generated test logs are included. Runtime source remains unchanged; no Foo execution or new test cycle was performed for this transfer. Source handoff commit7807's automatic CI passed run39848950707; any CI triggered by this evidence addition is separate and must not be conflated.
