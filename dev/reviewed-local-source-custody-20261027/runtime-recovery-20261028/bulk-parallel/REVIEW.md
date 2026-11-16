# Bounded bulk asset pool candidate

Not deployed. Source SHA256: 2fde257a76102f192972cefe19d6fc908649be766fbf27c338d3c0fe8986d544.

## Transition
Freeze current verified 513-asset output as provenance. Create a separate run-owned `bulk-parallel` output with this new implementation and recover-from pointing at the current 513-asset output, not the historic corrupt partial. Adopt retained candidates with workers=1 in bounded batches. Once all 513 have been source-compared, copied and checkpointed, resume the SAME frozen implementation with workers=2 initially or 4 after review. Existing implementation pins and original output are never rewritten.

## Parallel behavior
- At most N submitted/in-flight futures for N workers (1..16); no unbounded task queue.
- Each worker owns a distinct manifest key and atomic temporary/rename.
- Only parent records results and writes the checkpoint.
- Worker deadlines checked before work, per JSONL line, before rename. In-progress temporary is removed on cooperative pause. Outer supervisor remains hard deadline/cancellation owner.
- Completed but unjournaled atomic assets are independently source-compared on resume; no final manifest until every input entry is represented.
- All source bytes verified before work. Legacy candidates cannot be dispatched to pool until serial reconciliation.
- Aggregate pending asset allowances counted against free space and output budget before dispatch.

## Bounds / limitations
Disk allowance is admission plus cooperative monitoring, not a filesystem quota; unusually expanded assets can exceed estimate before post-result pause. Per-process address-space limits are not an aggregate cgroup. Reviewed driver v2 must account parent plus workers explicitly. Driver cancellation and outer supervisor provide process cleanup; this producer alone does not independently contain descendants. Existing serial adoption behavior retained. Do not advertise measured speedup before a real pool batch is verified.

## Tests
`python3 -m unittest discover -s tests -p 'test_*.py' -q`
60 test executions pass, including inherited repeated fixture cases. New checks cover real two-process output equality with serial compressed assets, bounded resume, capacity admission, legacy refusal, per-line deadline cleanup, orphan recovery, and aggregate in-flight reservations.
