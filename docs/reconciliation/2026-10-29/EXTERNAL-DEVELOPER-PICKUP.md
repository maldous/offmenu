# External developer pickup

Canonical `develop` now includes reconciliation/onboarding documentation. Start with `docs/reconciliation/2026-10-29/ONBOARDING.md` and its commented nonsecret environment template. Main remains the verified-release policy branch; live209 UI failure is not a main release.

No application worker has been resumed. Select the exact owner branch below; do not wholesale merge custody snapshots.

| Branch | Head | Disposition |
|---|---|---|
| feature/source-facts-diagnostic-20261029 | 6c4ee1495a7daf3baa6b55a01e0e166b183118ea | reviewed inactive diagnostic candidate |
| bugfix/source-barcode-index-budget-20261029 | 5b3086ba67e88ae624846dfd119c769b06d5e0f0 | unreviewed inactive WIP |
| bugfix/scanner-ui-209-20261029 | fa1f04015b0fddd479bc76364f8198d5442fd4e0 | failing production209 source checkpoint |
| feature/windmill-platform-source-20261029 | 4632dd238e2bffefc60246bcb328264a6fb85f9e | operational source custody |
| feature/historical-tooling-source-20261029 | dceef4c5314e352633713b07979532d0869cc6a8 | historical custody only |
| feature/ai-tooling-source-20261029 | bbb2e489afdc30dab7d87a0f3653bbd2887cb54a | historical custody only |
| feature/reviewed-app-source-custody-20261029 | 6bfe2165c79e9152b4396d9c75b735665be47707 | historical reviewed deltas; custody only |
| feature/retained-worker-wip-20261029 | 63f3439a331bb5d19ef61d026f82f9c6ddb5b904 | mixed worker WIP custody |
| feature/repository-reconciliation-20261029 | 2c999c6d71058da9bec60da6771c65f453136e67 | integrated documentation/onboarding |
| feature/qualified-source-recovery-20261029 | 24c71f6c7fc518b61d7f71eadc5e8958512fb35a | deduplicated source custody only |

Exact bases, source paths, worktree locations and remaining issues: `EXTERNAL-DEVELOPER-BRANCH-QUEUE.json`. Private cleanup/restore journals are retained by the reconciliation custodian and are deliberately outside this source-only Git handoff.

The branch queue pins source heads before this handoff publication; the containing Git commit identifies this documentation successor.
