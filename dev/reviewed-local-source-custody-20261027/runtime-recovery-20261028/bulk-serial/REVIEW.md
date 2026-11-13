# Focused bulk recovery batch review

Reviewed source: scripts/repair-bulk-controls-20261014.py
SHA256: cb7355ecc5d62e34fc68b6dcbb1ab6828ddc7c3b6dccb7f5fa4ee9c79deb41f6

Approved scope: first bounded batch into fresh /offmenu/data/.offmenu-platform/corpus-recovery-20261028-v1/bulk, with original input and retained legacy partial read-only. Stage and verify exact reviewed source/schema/contract before execution, require fresh output absence, then inspect actual paused checkpoint and output receipts before any continuation.

Proposed controls: one worker; maximum100 new assets;240-second cooperative budget;300-second runner hard cap;75,161,927,680-byte free-space reserve;20,000,000,000-byte output ceiling. Representative keys are accepted manifest entries packets/part-00000.jsonl.gz, packets/part-05452.jsonl.gz and packets/part-09478.jsonl.gz and must actually find all three required source/control examples. Actual prior whole-input verification plus these representatives reportedly completed in13.283seconds.

Review findings resolved:
- All accepted input bytes verified before output; consumed source checksums/stable metadata checked again for repair/adoption.
- Original repair_packet semantic transform unchanged; actual packet count must equal accepted entry count.
- Only fully source-compared retained assets are copied to exclusive new files, with copied SHA and retained stability checks. Truncated legacy output remains unchanged and is recomputed only in fresh output.
- Same-run committed receipts are exact-SHA checked; unjournaled outputs require full source comparison. Changed/corrupt/unexpected files stop rather than being silently overwritten.
- Atomic asset and checkpoint writes use exclusive unique temporaries and fsync file/directory. Interrupted leftovers remain for explicit reconciliation.
- Budget/capacity pauses do not emit a final manifest or mark completion. Existing lock ownership is respected; no fabricated legacy checkpoint or resume occurs.

Independently reran34 test executions successfully (includes inherited duplicate cases; not34 distinct behaviors). Deadlines are cooperative between files/assets, not a strict per-row wall-clock guarantee; the outer runner cap remains necessary. As prior-output verification grows, review actual batch timing before increasing work. Final full package qualification/publication is unchanged and not established by this batch.
