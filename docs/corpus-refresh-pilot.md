# Local corpus refresh pilot

This is a small, transport-neutral vertical slice based on `develop`
`922ab2d3f0cb56f0b034752f13b24c391b14744a`. It reuses the historical
`scripts/collect-wikibooks.py` adapter and its existing `offmenu-collection/1`
manifest and normalized recipe records. It does not migrate the entire corpus
or claim current source or country completion.

## Scope and safety boundary

Implemented:

- Bounded, read-only asset metadata inventory, with no source-content reads,
  recursive hashing, symlink traversal, absolute paths or arbitrary filenames
  in the resulting JSON.
- Strict pinned-input manifest validation and local checksum verification.
- Source-wide immutable SHA-256 cache, shared across country requests.
- SQLite stage checkpoints, kernel-owned workspace/source locks, explicit
  resume, no-op verification, and explicit local rebuild.
- Deterministic offline replay of the historical July 2024 Wikibooks JSON
  format, with preserved attribution, source quantities and review gates.
- Atomic rename of a verified immutable output generation into a local release
  directory. There is **no active-corpus pointer or deployment**.
- Small allowlisted success/failure receipts suitable for manual review and
  GitHub reporting. Source content, raw datasets, private paths and secrets are
  excluded.

Not implemented: online acquisition, HTTP conditional revalidation, live
Wikibooks crawling, other source adapters, arbitrary archive extraction,
large streaming datasets, source-rights discovery, cloud publication,
249-country completion, scheduler/runner installation or persistent access.
The adapter's recipe rows have no country assignment. A global source lead is
not an implemented adapter or evidence of complete coverage.

Linux, CPython 3.10+, SQLite (Python stdlib), and Git are required. No pip/npm
installation or credentials are required for this slice. Run from a repository
checkout; Git HEAD is read locally. All paths below are host-local. These
commands do not access another computer.

## Start with read-only inventory

On the machine holding the existing datasets:

```sh
python3 -B -m offmenu.refresh inventory \
  --root /home/user/src/offmenu-data --max-entries 10000 --max-depth 4
```

The root shown is the documented historical location, **not verified current
host state**. Select the actual root if it has moved. Inventory does not create
a workspace, read asset contents, inspect credentials or hash the 171 GB tree.
Use `-B` to prevent Python bytecode writes. A snapshot is not an atomic
filesystem inventory; concurrent source changes can affect metadata.

The report includes aggregate file counts/bytes, common file types, bounded
known-filename candidate signatures, and explicit exclusions/limits. Candidate
IDs hash the relative path; paths and source bytes are absent. File names are
only candidate signatures, not verification, provenance or freshness. Hidden,
credential, dependency and known dev-preview directories are skipped. A capped
scan, skipped directory or symlink makes `scopeComplete` false. It is normal for
this first check to be incomplete. Candidate details are limited to 100; the
report does not imply every source was discovered.

Do not commit the host filesystem, input manifests containing private paths,
raw assets, cache, checkpoints or output generations. Only review and commit
the emitted sanitized report if requested. The CLI has no Git push behavior.

## Run the synthetic fixture pilot

The checked-in fixture is authored test data, not a download from Wikibooks.
Its fake Cookbook URLs exercise the existing identity format and should not
be treated as real source pages. All output remains unreviewed and unsuitable
for automatic planning. The fixture is released under CC BY-SA 4.0; the adapter
retains the upstream attribution format as a contract test, not evidence that
Wikibooks authored the fixture.

Use an output directory outside the input directory and its ancestors:

```sh
python3 -B -m unittest discover -s tests -p 'test_corpus_refresh.py' -v
python3 -B -m offmenu.refresh replay \
  --manifest tests/fixtures/corpus-refresh/input-manifest.json \
  --input-root tests/fixtures/corpus-refresh \
  --workspace /tmp/offmenu-refresh-pilot
```

Repeat the exact replay command. It verifies the input, cache and published
output hashes and reports `verified-no-op`; artifact modification times are
unchanged. It creates a new small invocation receipt, not duplicate records.

`--force-rebuild` explicitly repeats the local transform and temporary cache
copy with the same input pins. It never bypasses input/hash/rights checks,
overwrites immutable cache bytes or downloads. The new output must be
byte-identical to the existing generation. `--force-refresh` is reserved for
future acquisition behavior and currently fails with
`online-acquisition-not-implemented`.

## Download-cache policy: minimum 30 days

```sh
python3 -B -m offmenu.refresh plan \
  --manifest tests/fixtures/corpus-refresh/input-manifest.json
```

This pure planner reads the small manifest, not asset bytes. It explicitly says
whether it verified bytes (it has not). For a checksum-verified cache with a
reviewed acquisition timestamp, the policy is:

1. Less than 30 days old: reuse the downloaded bytes; do not refresh.
2. At least 30 days old: consider **conditional revalidation first**, using
   ETag/Last-Modified or publisher release metadata when acquisition adapters
   are added. Elapsed time does not authorize a blind large download.
3. An explicit refresh request is a separate acquisition decision. No online
   step is implemented by this pilot, even with a force flag.

The policy never infers freshness from filesystem mtime. Existing files with
unknown acquisition provenance remain unknown until their small manifest and
source evidence are reconciled. Do not hash every existing asset merely to
inventory it. Validate only a selected input when it is actually replayed.

The cache identity is source/release/content, not country. One global source
must not be downloaded independently for each of the 249 country queues. New
adapter code can rebuild a derived generation from the same immutable bytes
without re-downloading or extending the acquisition timestamp. Offline replay
is allowed for old, exactly pinned snapshots and does not claim they are
current. A 304 response must eventually update a separate validation receipt,
not the immutable original acquisition record; that online mechanism is not
implemented here.

## Pinned input contract

`tests/fixtures/corpus-refresh/input-manifest.json` is the complete example.
Unknown fields and versions fail closed. Supported fields are:

- `schemaVersion`: `offmenu-refresh-input/1`
- `sourceId`: `wikibooks`; `releaseId`: `2024-07-31`
- `scope`: `synthetic-fixture` or `historical-source-snapshot`
- `input`: relative safe `path`, positive `bytes`, lowercase SHA-256 `sha256`
- `acquiredAt`: an explicit UTC acquisition timestamp
- `rights`: `status=reviewed-local-use`, `license=CC BY-SA 4.0`, and the exact
  preserved adapter attribution string

A manifest records the operator's evidence and review; it does not independently
prove that a website licensed those bytes. Do not relabel a new or unknown
release as July 2024. Later releases need a reviewed adapter/config change.
No manifest strings become executable commands. No environment credentials
are passed to the adapter child. Source/input paths must be regular,
non-symlink files, and source and workspace roots must be disjoint.

Source JSON rejects duplicate keys, NaN/Infinity and malformed shapes before
calling the legacy parser. Order is semantic: repeated identical input bytes
produce the same output, and the existing first-duplicate-wins behavior is
preserved. This is not shuffled-input equivalence. Missing identities remain
quarantined; accepted + duplicates + quarantined + excluded must reconcile to
raw input rows. Unknown recipe quantities remain unknown.

## Checkpoints, locks and recovery

Workspace structure:

```text
cache/sha256/<input-sha256>     immutable source bytes
checkpoint.sqlite             local run ID/pins/stage/artifact checkpoints
locks/wikibooks.lock           stable source flock inode, PID diagnostic only
workspace.lock                stable workspace flock inode
staging/<run-id>/              incomplete transform, never an active corpus
releases/<identity>/           verified immutable output generation
receipts/<run-id>.json         sanitized completed invocation receipt
```

The workspace-wide lock covers all shared SQLite/cache/publication mutation;
the source lock also makes source ownership explicit. Kernel `flock` ownership
releases on exit/SIGKILL, not based on PID age. Lock files intentionally remain;
**do not unlink them**. The adapter child inherits the lock descriptors, so a
killed parent cannot allow another writer to race a still-running child.

On `unfinished-run-requires-resume`, repeat the identical pinned replay command
with `--resume`. Matching pins and actual code/runtime fingerprint are required.
Interrupted cache copies use the persisted run ID and only that run's exact
owned partial is reclaimed on resume; unrelated files are never glob-deleted.
Interrupted transforms are discarded and rerun from verified immutable bytes;
this pilot checkpoints stages, not individual records. If a crash occurred
after rename but before its checkpoint, resume validates the complete
published generation against the previously saved artifact hashes.

`--resume` without a matching unfinished run fails explicitly. A normal rerun
after completion produces a verified no-op. `writer-lock-held` means another
process still owns it; wait and retry rather than delete the file. Corrupt
cache, changed inputs or modified published outputs fail closed and are not
repaired by force. Preserve and investigate corrupted artifacts before a
separate recovery decision; do not edit SQLite checkpoints to force success.

The sanitized CLI error includes `operationId`; once a run is initialized it
also includes its `runId`, actual Git HEAD, dirty-source indicator, runtime,
code/config fingerprints and pinned input size/hash. It excludes traceback,
source text and paths. Completion receipts are persisted locally. An error
before a run exists has no invented run ID. GitHub/manual transport can retain
stdout independently; the CLI never sends it anywhere.

## Reproducibility and resource limits

- Input cap: 64 MiB, because the reused historical adapter reads its JSON into
  memory. This slice is not a 171 GB streaming pipeline.
- Accepted output: at most 256 MiB aggregate across three expected artifacts.
- Worker per-file limit: 256 MiB; transient maximum is three times that, before
  aggregate validation. Disk preflight reserves that 768 MiB bound, twice the
  input size, plus 16 MiB for local control files. Available space can still
  change concurrently; disk errors do not publish an unverified generation.
- Worker address-space cap: 1 GiB, CPU cap: 110 seconds, parent timeout: 120
  seconds. POSIX `resource` and Linux file locking are required.
- Input size is checked before any payload read, then hash checked on every
  invocation, with bounded reads/copies and stat-before/after mutation
  detection. Copies and existing CAS blobs are verified; corrupted bytes are
  never adopted. Publication only follows output validation and fsync/rename.
- Gzip uses fixed mtime and no embedded filename. Record `fetchedAt` is pinned
  to acquisition, not invocation time. Source/adapter/package bytes plus Python,
  SQLite and zlib versions form the code/runtime fingerprint; different runtimes
  produce different generation identities. Actual Git HEAD and dirty status are
  separately reported, never accepted from a caller-supplied SHA.
- The child uses Python isolated mode, a minimal environment, and an audit guard
  denying socket/DNS, subprocess/exec and ctypes operations. This is a trusted
  adapter's application-level offline guard, **not a hostile-code sandbox or
  OS network namespace**. For stronger production isolation run within a
  separately configured network-disabled container. This pilot never creates
  a container, installs a service or changes host security settings.

## Verification and next slice

Run the focused suite above. It covers repeat/force determinism, count/provenance
invariants, corrupt cache/output/input, strict schemas, network guard tripwires,
path overlap/symlinks, shared lock contention, disk preflight, minimum-30-day
policy, sanitized errors and interruption/resume around publication boundaries.
Independent acceptance should additionally kill real processes during locking
and rename recovery, then rerun against the frozen code fingerprint.

The next source adapter must reuse the repository's existing parser/cache/schema
where available and supply fixtures, rights evidence, version pins, resource
limits and recovery tests. Prefer bounded local cache reconciliation before
adding online acquisition. Full-country source discovery, source leads and
running pipeline adapters must remain separate states.
