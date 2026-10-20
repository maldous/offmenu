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

Publication uses the existing Linux no-replace rename with the ORIGINAL parent
file descriptor retained from stage creation. A private random scratch directory
is pinned before invoking the iterator. SQLite stays in that directory; a separate
pinned `evidence` child contains only the output files. Files are exclusively
created relative to these descriptors, with no symlink following. Preflight
parent, stage, evidence and file checks refuse observed custody changes.

SQLite connection setup has a separate descriptor binding. The internal
`/proc/self/fd/<stage-fd>/index.sqlite` path pins the directory, not its mutable
leaf. Before any caller iterator or schema writes, the core requires serialized
setup in a process with one observed Python/OS thread. It snapshots process file
descriptors, opens SQLite and forces its main database open. Exactly one new
regular descriptor must be attributable to that open. The core duplicates this
OPEN descriptor and compares its device/inode against the separately held created
file. Substitution followed by restoration of the leaf cannot satisfy that inode
comparison. Mismatch raises `partition-sqlite-inode-mismatch`; an ambiguous
open-descriptor delta or observed concurrency also refuses success.

This is a Linux/default SQLite main-file setup contract, with no in-process
concurrent descriptor mutation during attribution. It does not claim arbitrary
VFS, threaded host or hostile in-process callback support. Observed unsupported
setup fails closed; a future executor must qualify this restriction. It changes
no platform security/runtime settings. Following successful binding, database
byte measurement and retained identity/location use the SAME duplicated SQLite
file descriptor, rather than another basename stat. Ordinary custody checks on
the created leaf remain additional refusal guards. On mismatch,
`partition_retained_state` reports the actual attributable database inode/path/
bytes plus the separately created database inode/path;
`databaseConnectionVerified:false` prevents acceptance. Ambiguous candidates are
listed explicitly without choosing one as a verified connection. Matching
created/connected identities describe one file and must be charged only once.
All observed/held mismatched entries remain preserved, with no deletion.

These checks cannot make a pathname rename conditional on a source inode. After
the actual rename, the core opens the destination relative to the original parent
and verifies its directory inode against the held evidence inode, followed by
parent/stage, inventory and file identity checks. A replacement substituted at the
rename boundary raises `partition-published-identity-mismatch`; it never returns
success. The syscall may already have moved the unrelated directory to the
requested destination. That entry is preserved and explicitly reported on the
error as `preserved_publication_location`/`preserved_publication_identity`.
There is no unsafe rollback. This is point-in-time attestation, not a guarantee
that another actor cannot replace a pathname after verification. A downstream
consumer must independently revalidate its selected evidence and custody.

There is NO automatic unlink, rmdir or recursive cleanup on either success or
failure. Available pathname APIs cannot atomically condition deletion on a
previously observed inode, and another stat does not close that race. The SQLite
database and scratch directory remain retained on success, outside the published
evidence directory. `retainedScratch` reports their held inode identities and
observed locations, `automaticDeletion:false` and
`resourceObligationActive:true`; `measurements.databaseBytes` remains charged
storage, not released storage. Failure preserves the original exception and
attaches `partition_retained_state` with stage/evidence/database identities and
best-effort descriptor-derived locations, including relocated owned entries.
No directory search or pathname-based ownership inference is performed.

Retained state is a concrete outstanding resource obligation. The caller must
record its disposition and account it once until a separately qualified owner
reconciles it under a safe custody/quiescence protocol. This core grants no
cleanup authority and claims no atomic inode-conditional unlink facility. On a
mismatch, a held owned `result.json` is not successful publication or acceptance.
The published evidence directory, when attested successfully, contains:

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
streamed with aggregate byte checks, including the result file. The DB is retained
outside the published evidence; its bytes remain an active storage commitment. Elapsed checks are cooperative; they do not interrupt a blocked
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
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests /home/user/src/offmenu-preservation-20261020/checkpoint-venv/bin/python -B -m unittest test_off_partition_witness -v
```

Generated tests cover full ordinal conservation, multiple/identical versions,
first/all member retention, EOF-late duplicate, order-independent class decisions
with original ordinals preserved, exact singleton/member/ID hashes, invalid typed
keys/leadingzeros, no payload copying, JSON/framing/truncation, declared caps,
deadline, immutable existing destination and publication race. No retained body,
cache, original, restricted sample or live database is accessed. Failed25 review
holds, incident10230, custody, runtime, production and CIX boundaries are unchanged.

PR73 regressions replace parent/stage names during iteration and at EOF, swap
the evidence entry at the actual rename call, and replace the database leaf.
They verify failure rather than successful publication of a wrong inode,
preserved replacement markers and owned resources, and explicit retained-state
reporting. Success and iterator failure tests prohibit core unlink/rmdir calls.
The exact Worker56 syscall schedules are replayed separately, with their original
observations retained even where their old hardcoded paths no longer locate the
new evidence-child layout. All S/C/Q/ordinal/digest and declared-cap tests remain.

The SQLite-open regression swaps the database leaf while connecting, forces the
alternate database open, then restores the original before subsequent checks.
The baseline succeeds with the empty original inode/zero bytes despite SQLite
using a different database. The successor refuses before schema writes and
reports both actual and created objects. Additional controls reject extra open
regular descriptors and observed concurrent setup, verify success byte accounting
against the bound descriptor, and check descriptor closure on failure. None of
these tests opens retained data or a live database.
