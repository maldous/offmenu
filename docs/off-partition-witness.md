# Opt-in OFF occurrence partition core

This isolated implementation follows proposal10481 and independent policy
PASS10498. It changes no existing witness, normalizer, binder, consumer or runner.
The old clean witness remains dirty/held. No real source read, reconstruction,
execution, new resource charge or data admission is selected by this source scope.

`partition_stream(lines, destination, original_sha256=..., expected_rows=...,
limits=PartitionLimits(...))` consumes explicitly supplied UTF-8 LF byte lines.
Every limit is required; there is no real default envelope or installed CLI.
It implements classification and evidence emission, not the original-file custody
wrapper. A declared original hash and matching expected row count do NOT prove
stream derivation. Returned `sourceCustodyVerified`, `accepted`, clean-scope,
product-semantic and real-operation/resource flags are always false.

## Classification and evidence

The core checks bounded framing, strict JSON objects/finite values and exact
ASCII4–32-digit string keys. No numeric/Unicode/whitespace/GTIN coercion occurs.
Invalid native code becomes Q; malformed JSON/framing, count mismatch, incomplete
stream, or resource failure aborts without publishing a successful result.

Private temporary SQLite stores original ordinal, nullable lexical key, exact
raw-line SHA and canonical-body SHA only. It stores no source payload. Key counts
are indexed. Only after EOF is S/C/Q assigned: multiplicity1 is singleton S;
every occurrence of multiplicity>1 is held C, including first and identical repeats;
invalid-code rows are Q. No winner, merge, revision or majority rule exists.

Output uses the existing Linux no-replace primitive with the ORIGINAL parent
descriptor retained from stage creation. A private random stage is opened and
its inode pinned before invoking the input iterator. SQLite uses the internal
`/proc/self/fd/<stage-fd>/index.sqlite` path; evidence files are created exclusively
relative to the pinned stage descriptor with no symlink following. Parent-path,
stage-entry and owned-file inode checks precede publication. The parent is never
reopened after iteration. Path replacement refuses publication.

Failure cleanup is nonrecursive and descriptor-relative: only known file entries
still matching their created inode are removed, then the stage name is removed
only if it still names the original empty stage. Unrelated replacement entries
are preserved. If an owned stage was relocated and its original name no longer
identifies it, its known files are cleaned through the retained descriptor and
`partition-owned-stage-cleanup-incomplete` reports `retained_stage_identity` and
`retained_stage_location`; an empty relocated directory can remain for explicit
owner reconciliation. This is an error/hold, never claimed successful cleanup or
publication. No recursive search/deletion or ownership inference from a reused
pathname is performed. The final directory contains:

- `occurrences.jsonl`: every original ordinal exactly once, original-hash/table
  locator, class/reason, nullable code and raw/canonical hashes.
- `singletons.jsonl`: exact source key, original ordinal and hashes, in BINARY
  key order. These are candidates for later native qualification, not accepted
  products or verified identities.
- `groups.jsonl`: every repeated key, multiplicity, `selectedPrimary:null`,
  unresolved status and ordered complete-member digest.
- `members.jsonl`: all repeated-key members, key then original ordinal order.
  A huge group is streamed, never expanded into one in-memory list.
- `result.json`: exact counts, expanded-stream hash, evidence file pins,
  candidate singleton product/profile ID digest/count, limits and measurements.

Raw-line hash includes the exact supplied LF-delimited bytes. Canonical-body and
member/ID hashes use existing core canonical UTF-8 sorted compact JSON plus LF.
IDs use all `off:nutrientProfile:<key>` then `off:product:<key>` in BINARY key order.
This digest is explicitly a candidate membership result, not the old dirty-key
digest or an automatically accepted SourceContract binding. Product semantics,
schema failures, code-to-product identity and quarantine alias uncertainty remain
unresolved; a later normalizer must not silently drop S failures.

## Bounds and measured evidence

The caller supplies maximum rows, line bytes, expanded bytes, DB bytes, aggregate
output bytes and elapsed seconds. Integer representations are bounded to signed
SQLite-compatible63-bit positive values. SQLite page count bounds main DB size;
journaling is off in disposable staging, cache is2MiB, and no raw bodies are stored.
Ordered reads use indexes; query-plan checks refuse temporary B-tree sorts rather
than leaving external sort scratch unaccounted. Outputs and all group members are
streamed with aggregate byte checks, including the result file. The DB is removed
before publication. Elapsed checks are cooperative; they do not interrupt a blocked
input iterator or an SQLite operation. An eventual executor still needs its OS
wall-clock/memory/file boundary and fresh free-space/commitment guard.

The author result's `generated-resource-proof.json` records measured database,
output, elapsed and Python-traced peak values for an authored10,000-row stream.
Python tracemalloc is not total RSS or SQLite native allocation. The file also
computes a conditional metadata-wire bound from maximum serialized evidence rows,
not sample extrapolation. It assumes this exact schema/canonicalization and does
not establish real SQLite size, total memory, CPU, input expansion or available
capacity. No old10GiB witness budget is adopted for a future operation.

## Required actual evidence/resource plan

Before any real operation, existing owners must separately select a minimal
original-custody adapter around this core. Reuse the reviewed verified-file and
gzip protocols under a new exact opt-in scope, with exact original13,132,516,914B
SHA`11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e`,
source-use/unknown-clock evidence, selected code/runtime/destination and initial/
final file identity/size/hash plus complete gzip CRC/EOF. Never treat this stream
API as that proof or build authority from its own output hashes.

The operation must preserve original denominator4,807,663 and reconcile previous
witness valid-first-keys4,807,217, laterduplicates61 and Q385 against the new group
inventory: S+G=4,807,217; C-G=61; Q=385; S+C+Q=N. All original ordinals must appear
once; all group members and first occurrences must be present; sidecar/member and
ID digests must be independently recomputed. Any disagreement holds the result.
Actual G/S/group memberships remain unknown here. The measured83,278,049,962
expanded bytes from the previous full witness are planning evidence, not proof
that a new configuration fits. Current real resources/limits are unset.

Worker57 owns any selected adapter/execution/custody/resource packet, Worker64
independent output review, Gateway admission/scheduling and Worker00 integration.
Fresh independent source review precedes actual operation selection. Preserve
source rights/private artifacts and account concurrent commitments exactly once.
The downstream partition-aware normalization/contract and PR72 independent
derivation pins are separate future bindings, unactivated. Do not change frozen
clean/default producer behavior or make candidate-output-before-witness gates.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests /home/user/src/offmenu-preservation-20261020/checkpoint-venv/bin/python -B -m unittest test_off_partition_witness -v
```

Generated tests cover full ordinal conservation, multiple/identical versions,
first/all member retention, EOF-late duplicate, order-independent class decisions
with original ordinals preserved, exact singleton/member/ID hashes, invalid typed
keys/leadingzeros, no payload copying, JSON/framing/truncation, declared caps,
deadline, immutable existing destination and publication race. No retained body,
cache, original, restricted sample or live database is accessed. Failed25 review
holds, incident10230, custody, runtime, production and CIX boundaries are unchanged.

PR73 regressions replace parent/stage names during iteration and at EOF. They
prove no unrelated publication/deletion, descriptor-anchored parent-failure
cleanup, preserved replacement marker files and explicit owned-relocation
reporting. The original ee53 source fails both provider reproductions; the
corrected source retains all S/C/Q/ordinal/digest and resource-control tests.
