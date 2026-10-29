# Terminal filter R2 — TF-R1 correction, source review only

This isolated R2 fixes the one P2 defect in the independently reviewed frozen R1.
R1 and its original examples/artifacts are unchanged. The 23 source-custody files,
held publication and held live metrics adoption are untouched. No remote upload,
provider call, installation, product/dataset check or global activation occurred.

## Exact review basis

Baseline source SHA-256:
`f507ceb4d68c3c7232218f9b62e71d9a979a970bd6d72ecc9afddea34f0894e5`.
Baseline test SHA-256:
`952b4d39e251a8719cfec22210557f7327278bed5839c27ab1ab99a48e23b96c`.
`base/` preserves exact source/test snapshots and the actual independent review
receipt, SHA-256
`6bf605911dcd5acba322136665f49af8b5005484a6a13d8c3d62bae738a19211`.
The reviewer blocked R1 because a known child exit or cancellation was lost if
capture_command raised during persistence before returning its final metadata.
CLI then incorrectly returned 125 instead of 7 or 143.

## Minimal correction

capture_command now updates a caller-owned capture_state independently of receipt
finalization. Its finally block records the observed raw child return code,
cancellation flag/signal and existing private artifact pointer before restoration
of the scoped handler and before finalize. A failure during post-wait flush/fsync,
cleanup or finalization therefore cannot erase an already known outcome.

On exception, main uses actual returned finalized metadata when available, otherwise
that independent observed state. It reports tool_status=failed_closed plus the
error type, raw return code, cancellation state/signal and partial-original pointer.
finalized_receipt_returned=false and capture_receipt=null explicitly distinguish
unreturned/unfinalized persistence from a valid receipt. No length, SHA or receipt
is invented for a failed capture. Partial receipt files can exist when persistence
fails partway through; they are not returned as finalized evidence.

Known child failures retain their shell exit status. Cancellation retains 128+signal,
even when no child was launched and raw process_returncode is null. Successful or
unknown child status with tool failure still yields 125. Retained raw bytes remain
private; preservation failure is never converted into success or a shorter-output
claim. The existing profile allowlist, argv, no-shell policy, private modes,
classification, bounded summaries and process-group cleanup behavior are unchanged.

## Focused evidence

11 tests passed in focused-tests.log: the existing nine focused tests plus two
new regression methods, each testing forced finalize and fsync failure:

* Synthetic child writes ERROR retained failure and exits 7. CLI retains 7; the
  failure JSON reports process_returncode=7, failed_closed, original pointer,
  finalized_receipt_returned=false and no fabricated hash. Exact failure bytes
  remain private and no success summary is emitted.
* Synthetic pre-launch SIGTERM cancellation followed by forced persistence failure
  retains CLI 143, cancelled=true, cancellation_signal=15, process_returncode=null,
  original empty artifact pointer and no finalized receipt/hash or success summary.

No prior accepted product/dataset/provider checks were run. Only this local tool's
focused synthetic tests ran. No byte-reduction illustration was rerun. Existing R1
measurements remain illustrations of terminal bytes for two saved non-sensitive
logs, not tokens, production performance or R2 execution-time measurements.

## Review / invocation / rollback

`source.patch` is the narrow source-only correction; `review.patch` adds the two
test methods as well. Both apply cleanly to the exact base snapshots. Exact file
sizes/hashes are frozen in FILE-INVENTORY.json. Source/test/diff files are read-only
for accidental-edit protection; owner/root can still change permissions, so hashes
remain the custody check rather than a tamper-proof claim.

After independent review, explicit saved-log invocation remains:

```bash
python /home/user/src/offmenu-terminal-filter-candidate-20261028-r2/terminal_filter.py saved ai-reuse-r2 --max-bytes 1536
```

This is an invocation example, not activation performed by this handoff. Arbitrary
paths/commands remain rejected. The `run filter-tests` profile runs only this tool's
focused tests. Do not install a hook or wire this into the held live adapter path.
Rollback is to stop explicitly invoking the tool and retain raw artifacts/receipts.
R1 is preserved as historical source, not recommended as the corrected fallback.
