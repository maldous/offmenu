# Shared refresh registry: bounded synthetic bundle integration

This slice adds a trusted Norway fixture entry to `python3 -m offmenu.refresh`.
It reuses the existing cache, SQLite checkpoint ledger, locks, isolated worker,
and immutable local candidate lifecycle. It does not admit historical Norway
or CIQUAL inputs, acquire data, change grants, schedule jobs, accept a corpus,
move accepted pointers, or publish/deploy data.

The reviewed Norway library remains byte-identical. CIQUAL remains a separate,
reviewed library until an additional fixed registry entry is reviewed. The old
`scripts/run-norway-synthetic.py` helper is unchanged for compatibility and is
legacy-only: use the shared CLI for lifecycle work. Converting that helper to a
forwarding shim is a separate interface migration, not part of this slice.

## Commands

From a source checkout, or an installed wheel containing `offmenu`:

```sh
python3 -B -m offmenu.refresh plan-fixture --fixture norway
python3 -B -m offmenu.refresh replay-fixture --fixture norway --workspace /tmp/offmenu-refresh-A
python3 -B -m offmenu.refresh replay-fixture --fixture norway --workspace /tmp/offmenu-refresh-A
python3 -B -m offmenu.refresh replay-fixture --fixture norway --workspace /tmp/offmenu-refresh-A --force-rebuild
```

The second replay verifies the complete retained bundle and all existing
candidate bytes. `--force-rebuild` repeats the local transform and requires the
same bytes for an existing qualified build. Use `--resume` for a matching
interrupted run. `--resume` and `--force-rebuild` are mutually exclusive.
`--force-refresh` fails explicitly and never downloads or bypasses admission.

The frozen fixture lock records CPython 3.12.14 and zlib 1.3.2. A different
runtime fails closed unless `--repin-synthetic-runtime` explicitly binds the
same fixture and implementation pins to the current runtime. This changes the
qualified build key. Canonical content is checked independently; exact gzip
reproducibility across zlib versions is not claimed.

Wikibooks `inventory`, `plan`, and `replay --manifest ... --input-root ...`
remain the v1 interface, including historical-snapshot semantics, the legacy
artifact layout, acquisition timestamp behavior, and receipt schema. No v1
manifest or checkpoint is reinterpreted as v2. As before, changed implementation
bytes/runtime invalidate the build key and cannot adopt old partial work.
Existing immutable candidates remain untouched.

## Trusted admission and complete bundle contract

`registry.fixture('norway')` selects an in-code entry, never a caller module,
path, command, arbitrary lock, or synthetic label. The entry verifies the exact
reviewed lock bytes (`1066` bytes, SHA-256
`0e39e65eb38e0353abbf54514c8e163a347f5945f2357420f13a233ddf1e3d28`).
That lock binds source `matvaretabellen`, release `2026`, synthetic scope, the
four inputs, and the reviewed implementation/interpretation contract.

The four logical inputs are `en-foods.json`, `nb-foods.json`,
`en-nutrients.json`, and `en-sources.json`. Their original bytes are packaged
verbatim as base64 Python resources and checked against their original sizes
and SHA-256 hashes. This deliberately avoids requiring a source checkout's
`tests/` directory, an unreviewed fixture generator, or shared packaging changes.
The resource regression test checks every packaged byte against the separately
retained fixture files and lock. Implementation and contract files are verified
before importing the source adapter or decoding fixture bodies.

Historical source admission is absent. A caller label, matching source name,
access grant, a freshly invented hash, or replacement body does not confer
admission. Future historical support needs an independently reviewed exact
input/dependency lock, current operation/retention rights and provenance,
release/dictionary/unit/basis checks, and explicit rejection of expired,
withdrawn or mismatched scope before source/cache reads. This release cannot
consume such inputs even if the host grant is later supplied.

The internal adapter contract exposes source/release/scope, exact named input
and output sets, dependency pins, resource caps, a pure normalization step, and
candidate validation. Norway's `verify_bundle` and `normalize` are reused;
its standalone `build`, writer lock, cache, and publisher are never invoked.
The source adapter receives only the selected, complete cached bundle.
Subsequent entries must be hardcoded reviewed adapters, not dynamically loaded
configuration plugins.

## One lifecycle and resource boundary

The shared core owns:

- `cache/sha256/<digest>` immutable verified blobs
- `workspace.lock`, `locks/<source>.lock`, and `checkpoint.sqlite`
- run-owned staging and temporary bundle views
- `releases/<qualified-build-key>` immutable local candidates
- sanitized run receipts

The state sequence remains `started → cached → transformed → published →
complete`. Here, `published` means the existing local atomic-rename checkpoint,
not public publication or acceptance. `cached` is reached only after all four
assets are verified. Cache copy interruptions restart only that run's temporary;
interrupted transforms restart only that run's staging. Existing candidates are
reverified and never overwritten. Shared locks and checkpoints isolate source
runs while allowing content-addressed deduplication. Parent-held lock file
descriptors remain inherited by the worker until it exits.

Resources are fixed in the trusted descriptor and match the shared worker:
64 MiB total selected inputs, 256 MiB total output, 1 GiB address-space limit,
110 seconds CPU, and 120 seconds wall time. Canonical gzip decoding is bounded.
The worker uses `-I -B`, a minimal fixed environment, and a Python network/
subprocess audit-deny guard. This is not OS-enforced network/DNS confinement;
the v2 receipt says `osNetworkConfinementVerified: false`. Historical execution
still requires the separately approved offline boundary. No network, system,
or runner-isolation configuration is changed by this slice.

## Content, build, transport, and acquisition are distinct

The versioned common policy (`offmenu-serialization-policy/1`) specifies UTF-8,
sorted JSON keys, compact separators, finite numbers, explicit nulls, preserved
Unicode and meaningful array order, one singleton record array per LF-delimited
line, and no inference/imputation. Numeric spelling uses the pinned Python JSON
implementation. Gzip uses empty filename, mtime zero, and compression level one.
Its header has no source path or timestamp. DEFLATE bytes are runtime-qualified.

Four candidate outputs are declared:

1. `normalized.jsonl.gz`: normalized records, retaining Norway's unknown/zero/
   trace/bound and unit/100 g edible-basis behavior.
2. `source-metadata.json`: canonical native dictionaries/reference metadata.
3. `content-manifest.json`: source/release/scope, input bundle identity, canonical
   JSON/LF policy, uncompressed record and metadata hashes, counts and
   explicit acceptance/completeness holds. Its SHA-256 is the canonical content
   identity. Transport settings belong only to the build policy. It contains no runtime label, gzip hash, run ID or completion time.
4. `build-manifest.json`: runtime-qualified build key, exact build pins and
   actual transport hashes for the three files above. The shared receipt also
   hashes this build manifest and all other output bytes.

The qualified build key binds the source/release/scope, fixed fixture lock,
implementation and interpretation/attribution contract, resources, common
serialization policy, complete installed refresh/source code bytes, and
Python/zlib/SQLite runtime. A Git commit is diagnostic metadata, not identity
or a substitute for byte hashes. Installed fixture replay works without Git or
legacy scripts; v1 keeps its original Git availability requirement.

Canonical-content validation and exact transport validation are both performed
before final rename and on reuse. `accepted` remains null, `acceptance` is
`not-performed`, public export is disabled, and country/registry completeness
remain unassessed. Normalized row counts are never used as accepted row counts.

## Minimum 30-day reuse and evidence-only observations

Optional planning evidence is a separate JSON file:

```json
{
  "schemaVersion": "offmenu-refresh-acquisition-evidence/2",
  "inputBundleSha256": "75adc03ef4ce4fea22dce0756124e1f9c140e3d80274d08f7a70451f3040968e",
  "originalAcquiredAt": "2026-09-01T00:00:00Z",
  "revalidations": [
    {
      "observedAt": "2026-10-01T00:00:00Z",
      "result": "not-modified-304",
      "inputBundleSha256": "75adc03ef4ce4fea22dce0756124e1f9c140e3d80274d08f7a70451f3040968e"
    }
  ]
}
```

```sh
python3 -B -m offmenu.refresh plan-fixture --fixture norway --evidence observations.json
```

This example is fabricated fixture evidence, not an acquisition claim. The
planner checks UTC timestamps, chronological observations and the exact bundle.
Both `not-modified-304` and `identical-body-200` observations leave the original
acquisition age unchanged. Under 30 days it reports reuse; at 30 days it reports
revalidation review required with no download and `nextOnlineStep: none`.
Without evidence, age is unknown. Filesystem mtimes and rebuilds never supply
or reset acquisition age. Evidence and receipt timestamps are never passed to
the normalizer or included in content/build keys. Planning neither reads cache
bodies nor claims retained-asset verification. No evidence writer or online
revalidation implementation is introduced.

## Verification and remaining scope

Focused command:

```sh
python3 -B -m unittest discover -s tests -p 'test_refresh_registry.py' -v
python3 -B -O -m unittest discover -s tests -p 'test_refresh_registry.py' -v
python3 -B -m unittest discover -s tests -p 'test_corpus_refresh.py' -v
python3 -B -m unittest discover -s tests -p 'test_norway*.py' -v
```

The new suite covers immutable resource pins, pre-body admission failure,
forbidden configuration/input paths, complete-bundle cache checkpoints,
interrupted copy/transform and publication recovery, corrupt-cache/transport
refusal, cross-source isolation including unchanged v1 historical behavior,
code/policy resume mismatch, minimum 30-day observation handling, independent
canonical goldens, fixed gzip headers and runtime-label/content separation.
The existing independent Wikibooks acceptance suite additionally exercises
actual process kills, post-rename recovery and parent/child lock custody.

Frozen-runtime canonical content SHA-256:
`09d8c24fff64d0a26b567dbc831632b102789843a8d52bed791faf2bf82e1153`.
The canonical golden is always checked; the fixed gzip golden is checked only
on its recorded runtime. Same-runtime normalized/source-metadata bytes match
the unchanged reviewed Norway library exactly. An isolated extracted-wheel
replay/no-op also checks this canonical golden without Git, tests, or scripts.

This is a bounded Norway lifecycle integration. CIQUAL registry admission,
legacy-helper retirement, historical grants/input locks/rights review, OS-level
offline qualification, acquisition, all-country registry coverage, curation,
common-consumer acceptance and public publication remain separate work.
