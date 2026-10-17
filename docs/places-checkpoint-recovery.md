# Places checkpoint and recovery review

Worker 01 implementation, 14 October 2026. Status: READY FOR MORGAN REVIEW.
No retained dataset writer, qualification job or publication was started.

## Checkpoint contract

`align-places-common.py --resume` only continues its own pinned state. A sibling
`OUTPUT.checkpoint.sqlite` holds the source/file/line cursor, a disk-backed unique
(source ID, record ID) index, counters and compressed packet buffer. Input paths,
all input-file hashes, output path, schema, contract, implementations and packet
options are pinned. SQLite commits identities and cursor together at packet
boundaries; uncommitted records are replayed. Resume skips prior input files and
reads the cursor file to the saved line boundary.

Compressed assets retain the existing deterministic packet encoding and grouping.
They are fsynced and renamed atomically. A closed file left between rename and
checkpoint commit is reusable only if it equals the exact saved buffer. Other
extra/missing/corrupt files fail closed. An interrupted `.pending` write or stale
writer lock requires explicit custody reconciliation; neither is deleted or
reclaimed by resume. Final package bytes/schema are not altered by checkpoint
sidecars; the creation timestamp is retained across resume. Previously accepted
packages remain immutable and cannot be resumed.

The writer lock guards one output destination, not all possible destinations.
Morgan must maintain one-writer allocation across paths. An abrupt process death
leaves this lock intentionally held. Full-run throughput, filesystem power-loss
behavior and production-scale SQLite usage have not been qualified. Pins require
rehashing inputs on resume. Concurrent mutation of admitted inputs is prohibited.

## Legacy inventory

`places-recovery-preflight-20261014.json` records 2,407 packet assets against the
historical count of 2,393 (+14), total 2,441,520,421 bytes, with a canonical
key/size inventory digest and fourteen bounded tail hash receipts. The historical
receipt contained only a count, so it cannot prove exactly which files arrived
later. No manifest/checkpoint exists and no source comparison or adoption was
performed. Original places partial, food partial and truncated food asset stay
unchanged. A separately reviewed recovery plan must establish source equivalence,
identity state and fresh output/checkpoint custody before any reuse.

## Storage preflight

The preceding measurement was 207.078 GiB available; the saved dry-run measures
222,259,838,976 bytes (about 207 GiB). The illustrative incremental budget is
50 GiB new outputs (food plus places), 8 GiB checkpoint/state including journal
peak, 60 GiB qualification scratch and 10 GiB reserve: 128 GiB total, leaving
84,820,885,504 bytes of headroom. These are proposed bounds, not measured full-run
requirements or approved allocations. Retained originals already consume space;
there is no reclaim/hardlink discount. Additional assembly/publication copies
must be included in an approved budget. Passing this arithmetic does not authorize
execution or replace the all-eight-package acceptance gate. The old 35 GiB
launcher remains held.

Read-only invocation (prints JSON; no allocation or alignment):

```sh
/home/user/src/offmenu/.venv/bin/python scripts/places-recovery-preflight.py \
  --data-root /home/user/src/offmenu-data \
  --legacy-partial /home/user/src/offmenu-data/common-places-semantic-final-20261014.partial \
  --historical-count 2393 --output-gib 50 --checkpoint-gib 8 \
  --scratch-gib 60 --reserve-gib 10
```

Missing/nonpositive/nonfinite budgets are rejected. Insufficient free bytes print
`capacityPass: false` and exit 2. Allocation approval remains Morgan-owned, and
this dry-run is not an enforced writer disk quota.

## Validation and next gate

`/home/user/src/offmenu/.venv/bin/python -m unittest discover -s tests -p 'test_places*.py' -v`
passes ten tests: exact synthetic interrupted/resumed manifest and gzip equality
with one- and three-packet file grouping; mid-packet rollback; atomic-close crash
recovery; persisted duplicate rejection; changed pins/options, corruption,
truncation, extra assets, immutable output, stale locks and legacy refusal; storage
boundary checks and read-only inventory; existing places semantic/schema checks.

Morgan review/integration, approved peak-storage allocation, bounded legacy source
comparison and explicit new-run custody precede any production data execution.
No broad collection, scratch allocation or publication is authorized by this change.
