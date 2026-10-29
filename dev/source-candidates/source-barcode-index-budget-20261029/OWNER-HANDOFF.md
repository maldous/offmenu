# API deadline WIP owner handoff

Owner task:01a181e9. Scanner owner:01a182db. Both remain quiescent; this handoff does not resume either owner.

Branch:bugfix/source-barcode-index-budget-20261029. Worktree:/home/user/src/offmenu-worktrees/source-barcode-index-budget-20261029. Preserved source root:dev/source-candidates/source-barcode-index-budget-20261029. Agreed base:dc39d0d7f29f0b0650be374f0e7e2111ec45c4b7. Edit only this branch-owned source after coordinator resumption; original non-Git source remains byte-for-byte intact.

UNREVIEWED INACTIVE WIP. The10000ms server candidate deadline remains unchanged. A valid18-second synthetic input was rejected by the baseline. The reported40000ms client budget and approximately10.8-second503 are related observations, not a proven root cause. Four new test methods exist, but no correction, passing after-run or new build exists. The proposed30000ms value was not applied. No tests were run for this preservation commit.

Next owner action, only after coordinator resumption: inspect the preserved test and deadline contract, establish an appropriate bounded correction with evidence, obtain independent review, and integrate against the exact current209 source closure. Preservation does not authorize deployment or prove that deadline changes fix the scanner UI. Build imports remain the original recipe; inspect its dependencies before any execution.
