# OffMenu checkpoint and handoff receipts

Matt requires these receipts as routine delivery assurance. Root owns assignment reconciliation; each existing owner checkpoints only its own fixed worktree and task branch at a safe boundary. Worker64 inventories independently without modifying owner worktrees.

Every progress checkpoint and completion must record: owner and thread; fixed worktree; task branch; base and exact head; tracked authored changes and explicitly excluded untracked material; safe local checkpoint SHA; private-origin branch and independently read-back backup SHA containing the checkpoint; exact independent reviewer/verdict; verified develop merge SHA when authorized; retained recovery artifacts and outstanding exceptions.

Local commit, verified remote backup, independent qualification, and develop merge are separate states. A missing receipt remains unknown or blocked. Prose completion alone cannot close delivery. Before reusing a worker, preserve its old task branch, unfinished safe authored work and recovery artifacts, and reconcile the receipts.

Owners may commit explicit reviewed file lists on their own task branches and back up through the existing authorized Git workflow where eligible. Never blanket add, commit secrets/raw corpora/generated caches, switch or reset dirty checkouts, merge unreviewed work, force push, bypass review, or overwrite another owner. Remote backup is confirmed only by exact remote readback, not a successful local commit or an intended push.

Production STOP and separate security/trigger confirmation gates remain active. No new coordinator or broad test campaign is introduced.
