# One-shot selected source custody through the existing Foo runner

This is an explicitly approved, fixed export—not a shell gateway. No source file
is executed, changed, committed or pushed. The runner keeps `contents: read`.
The service, its account, home protection, bind mounts, groups and ACLs stay
unchanged. Production, main, normalization and source/privacy holds remain.

## First step: canonical metadata only

Run the reviewed, immutable helper as the normal owner, outside the checkout:

```sh
python3 -I -B /PRIVATE/TEMP/export-local-source.py inventory \
  --job-prefix foo-source-inventory-20261027 \
  --output-directory /PRIVATE/TEMP/packets
```

The output directory must not exist. It is created private (0700), with private
JSON packets and `packet-set.json` (0600). The checkout is fixed at
`/home/user/src/offmenu`; there is no arbitrary root or command option.
Inventory exports only eligible path/kind, index object/mode, size, SHA-256 and
explicit availability state. It reads candidate bytes for hashes, not for body
publication. It does **not** run `git status` or diffs, which can invoke configured
clean filters/fsmonitor. Fixed passive ref/index commands have a scrubbed
environment, optional locks and fsmonitor disabled, a 30-second timeout and a
32-MiB output-file ceiling. No remote URLs, Git configuration, credentials or
environment values are emitted; `.git` is never exported.

Traversal uses no-follow descriptors. Source symlinks, hardlinks, nonregular files,
secret/config paths, datasets, caches, logs and dependency directories are
excluded. Eligible untracked `.github` and `.agents` source is included. External
runtime/data trees are **never** traversed. Missing/nonregular/unreadable files
remain explicit. Inventory is not a claim that every outstanding external source
has been discovered, reviewed or recovered, nor a transactionally frozen checkout.

Inventory has a 50,000-candidate count, 200,000 visited-entry count and depth 64
limit: exceeding these fails explicitly, never truncates. Its SHA-256-reading
budget is 512 MiB and 64 MiB per file. Candidates beyond those checksum limits
remain in metadata as `present-unhashed`, with real size and null SHA-256; they
are not silently dropped or export-ready. Metadata size totals allow signed
64-bit positive integers independently of selected-content limits.

## One owner-executed deposit, with no persistent access expansion

After reviewing the packet manifest, run the **same hash-verified helper** once:

```sh
sudo python3 -I -B /PRIVATE/TEMP/export-local-source.py stage \
  --packet-directory /PRIVATE/TEMP/packets
```

This does not inspect the checkout as root. It reads only the explicit packet
set, validates every packet, complete batch membership and full-file content
pins, then copies only those validated JSON packets into
`/srv/offmenu-refresh/outputs/source-export/<jobId>.json`. It first verifies the
existing outputs directory is owned by `offmenu-runner` and is 0700. It creates
only `source-export` as root:offmenu-runner 0750 and each selected packet as
root:offmenu-runner 0440. Symlink destinations and existing job files are refused;
no overwrite, removal, chmod of existing outputs, service action, home read
permission, credential creation or runner repository-write token is involved.
Partial filesystem failures are reported; inspect the exact deposit before
retrying rather than deleting or overwriting unrelated files.

The normal owner cannot normally write the runner's existing 0700 outputs parent,
so this one explicit privileged copy is necessary. The Actions job cannot apply
its own host access configuration and does not attempt to do so.

## Exact externally known metadata anchors (optional, separate)

`inventory --include-pinned-anchor-docs` additionally emits **selected** packets
for exactly the three fixed, hash-pinned JSON documents declared in `ANCHORS`:
client13 result, its source-and-import closure, and All15 accepted-delivery
metadata. Their source hashes come from the parent handoff. These are metadata
inspection documents, not evidence that the referenced client/application source
has already been exported. Missing or mismatched anchors fail that optional
combined preparation; omit the flag to keep canonical inventory independent.
There is no recursive `offmenu-data` or runtime search.

## Explicit reviewed source selection

After inventory/anchor inspection, create a selection JSON with exactly
`repository` (the inventory's head/branch) and `selection` (explicit entries):

```json
{"repository":{"head":"FULL_OBSERVED_HEAD","branch":"OBSERVED_BRANCH"},"selection":[{"sourcePath":"/home/user/src/offmenu/scripts/example.py","repositoryPath":"dev/reviewed-local-source-custody-20261027/example/scripts/example.py","bytes":123,"sha256":"EXACT_64_HEX_DIGEST","kind":"source","reviewRef":"exact-review-reference"}]}
```

Each selected path is absolute under canonical checkout or the explicitly known
`/home/user/src/offmenu-data/runtime/layout-migration` source-artifact location.
Only the exact listed regular files are opened; no external directories are
listed. Kinds are `source`, `test`, `documentation`, or individually approved
`artwork`. The latter is distinct from raw product datasets and is never a
blanket binary-tree selection. JSON DTOs, data indexes, grant files, raw datasets,
caches and runtime outputs are not source-selection authority merely because a
path is reachable; review exact purpose and pins before listing a file.

```sh
python3 -I -B /PRIVATE/TEMP/export-local-source.py select \
  --job-prefix foo-selected-source-20261027 \
  --selection /PRIVATE/TEMP/reviewed-selection.json \
  --output-directory /PRIVATE/TEMP/selected-packets
sudo python3 -I -B /PRIVATE/TEMP/export-local-source.py stage \
  --packet-directory /PRIVATE/TEMP/selected-packets
```

Head/branch are checked before and after selection; every selected source must
match its full expected bytes and SHA-256. Raw bytes are preserved, not Git's
filtered/normalized representation. Text must be valid UTF-8 without NULs.
Known credential signatures and credential-bearing URLs fail closed; this is a
supplemental check, **not a guarantee that arbitrary source contains no secrets**.
Exact source selection and subsequent byte review remain required before origin
publication. No whole `.git`, configuration, source environment, raw datasets,
DTO/index/grant payload or raw runtime tree is ever an authorized selection.

Selected-content limits are 64 MiB/file, 512 MiB/selection and 50,000 files. Those
limits fail explicitly rather than silently dropping any selected path. Content
is split into 512-KiB parts and packets below 8 MiB. The full selection manifest,
batch index/count, file/byte/part totals and selection digest travel with every
packet. If an explicit selection exceeds the total, split it into documented
selection manifests; preserve the overall custody list. Oversized single files
remain blocked, not purportedly recovered.

## Existing Actions profile extension

Only after the exact source commit and workflow delta are reviewed, publish its
immutable SHA, then set **both** trusted-code pins in the existing control-branch
workflow. The source template deliberately contains placeholders and cannot run.
The live control branch is not changed by this preparation. Preserve request
schema, actor/repository predicates, action pins and read-only Foo permissions.

For each staged packet, submit one existing three-field request with that exact
packet `jobId` and profile `local-source-export`. Await completion before the next.
The dispatcher runs runtime readiness, focused helper tests, then only the fixed
`receive` command. That command reads one staged root-owned 0440 packet, checks
its identity/schema/pins, and writes a canonical copy into the current run/attempt
runner temporary directory. The dispatcher rechecks its SHA-256 before setting a
boolean artifact-ready output. The existing pinned upload-artifact action uploads
that exact `source-export.json`, never a glob or source directory.

Artifact name: `offmenu-source-export-RUN_ID-ATTEMPT`; retention: 14 days. Logs and
completion receipts contain only sanitized summary/digest/count evidence. The
report describes **pre-upload** preparation (`sourceCodeArtifactPrepared`); it
cannot prove artifact delivery. Check the actual upload step, artifact identity,
run/head binding and downloaded packet hash separately. Existing dataset disclosure
flags remain false; selected-code artifact inclusion is separately explicit in
`localSourceExport.sourceContentsIncluded`.

The hosted completion publisher keeps its existing PR31 identity, closed-unmerged
acceptance, SHA-CAS and idempotency contract. PR31's historical closed-head SHA
is not the current results branch SHA. Verify the immutable receipt commit, actual
terminal run and actual source artifact, not merely an old PR snapshot.

A retry of this new read-only profile revalidates the same staged packet in the
new run/attempt, rejects any changed packet digest, and regenerates the temporary
artifact. Other profiles retain existing durable-receipt behavior. Do not create
a second request while an existing run is pending.

## Consumer custody contract

Schema `offmenu-local-source-packet/1` has exactly `schemaVersion`, `jobId`,
`phase`, `batch`, `custody`, `repository`, `selection`, `items`. Selected items are
`fileIndex`, `offset`, `bytes`, `sha256`, `contentBase64`. Consumers must require
all batch indexes, equal custody/selection/repository metadata, exact contiguous
chunk coverage with no duplicates/extra trailing empty part, full reconstructed
file bytes/SHA-256 and content review. The helper's `validate_packet_set` performs
these checks before deposit. Canonical JSON uses sorted keys, ASCII escapes,
compact separators and one trailing newline. No uploaded content is executable.

Import reviewed files through the existing GitHub connection to an isolated
custody integration branch only; preserve duplicate/unknown/missing dispositions.
Do not claim application activation, production readiness or complete recovery.
