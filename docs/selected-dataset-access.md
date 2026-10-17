# Bounded selected-data grant and diagnostic

The existing dedicated runner stays in place. The owner operates one pinned local
administrative batch, then returns one sanitized receipt. Keep the job queue quiet
while the grant runs. No cloud test has executed the grant on foo.

## Exact selected files

All source names below are relative to `/home/user/src/offmenu-data/`:

| Asset ID | Exact source file |
| --- | --- |
| NO_EN_FOODS | national-originals/norway/en-foods.json |
| NO_NB_FOODS | national-originals/norway/nb-foods.json |
| NO_EN_NUTRIENTS | national-originals/norway/en-nutrients.json |
| NO_EN_SOURCES | national-originals/norway/en-sources.json |
| FR_WORKBOOK | national-originals/ciqual/Table Ciqual 2025_ENG_2025_11_03.xlsx |
| FR_IDENTITIES | national-originals/ciqual/alim_2025_11_03.xml |
| NATIONAL_ACQUISITION | national-originals/acquisition.json |
| NO_PRIOR_MANIFEST | matvaretabellen-2026/manifest.json |
| FR_PRIOR_MANIFEST | ciqual-2025/manifest.json |
| FI_ACQUISITION | originals/next-national-20261013/acquisition.json |
| FI_PRIOR_MANIFEST | fineli-20.0/manifest.json |

The first six are raw data; each is capped at 64 MiB and their total at 256 MiB.
The five metadata files are capped at 64 KiB each. The two Finland metadata files
are optional and never enable raw Finland or Danish processing. A complete Norway
set may be selected independently when France files are missing or inaccessible.
The acquisition receipt is shared; each country's prior manifest is required for
its raw bundle. Copied evidence is gated by source group. A provenance-blocked France or optional
Finland group is explicitly reported and its just-created private copies are
removed before publication; a verified Norway group can still proceed. A bad
shared acquisition receipt blocks both Norway and France. The accepted subset is
pinned in a private selection receipt and never expanded implicitly on retry.

This grant uses a new bounded root-private snapshot. It never copies or mounts the
mixed 171 GB tree. Maximum copied payload is 256 MiB + 320 KiB, plus a small pinned
inspector copy and administrative receipts. It checks free space with a further
16 MiB reserve. Original bytes, ownership, modes and ACLs remain unchanged.

## One local batch

Use a checkout pinned to the reviewed commit. The owner-facing wrapper verifies
this helper's digest, invokes it once, saves stdout as private JSON, and posts that
one sanitized receipt to the verified GitHub destination even on exit 2. The
wrapper must preserve the helper's actual exit code. Do not use a moving branch or
put any token in the helper. The complete wrapper is supplied separately after
review and after the queue is confirmed idle.

Its privileged invocation is:

```sh
sudo /usr/bin/python3 -I -B scripts/grant-selected-dataset-view-v1.py --apply
```

`-I` is mandatory: user-controlled import paths must not affect root execution.
Omit `--apply` for root-local validation only. The helper itself never calls sudo,
uses the network, reads credentials or gives the runner privileged capabilities.
It requires the original completed-bootstrap unit and installed helper pins, the
exact dedicated account/group and no unrecognized systemd drop-ins.

Exit 0 means validated, applied or already-applied. Exit 2 means blocked. Controlled
outcomes emit one JSON document, at most 16 KiB, with schema
`offmenu-selected-data-grant/1`, `reportKind=dataset-view-grant`, `grantVersion=1`,
fixed asset/source statuses, source-read and snapshot-write counters, verified
mount IDs, service restart/readiness and rollback outcome. Snapshot verification
adds only the inspector's strict allowlisted evidence, never payloads, private
paths, arbitrary errors or subprocess logs. No rights or corpus acceptance decision
is made. Missing/invalid output after a terminal kill or power loss is failure.

## Filesystem boundary

The grant opens every original ancestor with anchored directory descriptors and
`O_NOFOLLOW`; it opens each regular leaf without following links and holds those
file descriptors through copying. It checks owner, type, single link, bounded size,
non-executable/non-group-or-world-writable mode, stable stat identity, and existing
read permission for the dedicated account. ACLs or ambiguous access are blockers,
not permission to chmod, chown or copy otherwise inaccessible data as root.

Only approved file descriptors supply copied bytes. Parent/leaf substitutions
cannot redirect those reads. The complete copied content must match the pinned
historical metadata and matching acquisition/prior-manifest declarations before it
is exposed. This hash check also prevents trusting coarse filesystem timestamps.
The already-reviewed inspector is loaded only from bounded bytes matching its exact
SHA-256; those verified bytes are copied privately before execution so its own
fingerprint never rereads a user-writable pathname. No source format is parsed.

Local paths added by this version:

- `/var/lib/offmenu-selected-datasets-v1`, root-only mode 0700, holds the backup,
  exact inspector copy and snapshot. Its private parent keeps these copies
  inaccessible to the runner account outside the service namespace.
- `snapshot/` beneath that store contains only selected fixed filenames. It and
  its directories are root:offmenu-runner mode 0750; files are mode 0440.
- `.snapshot.staging/` is root-only 0700 while content is copied and verified.
  Atomic no-clobber rename publishes the complete snapshot. An unknown or
  interrupted pre-existing staging directory is blocked for review, not erased.
- `/etc/systemd/system/offmenu-runner.service.d/40-selected-datasets-v1.conf`
  resets only BindReadOnlyPaths and binds the verified snapshot child to
  `/srv/offmenu-refresh/cache`. No original source pathname is bound.
- `/run/offmenu-selected-datasets-v1.lock` is a separate root-only batch lock.

No original unit or installed helper is overwritten. The empty bootstrap directory
is preserved. Source copying is at most one bounded pass per selected file on the
initial grant; retries reuse only the exact existing private snapshot and rehash
that bounded snapshot rather than rereading original bodies. Unrecognized files,
changed stored selection, wrong modes/owners, symlinks or hardlinks fail closed.
The stored subset must still satisfy the original source-readability preflight;
newly available extra source files are not added by rerunning this version.

The dispatcher kernel lock is held throughout. The helper verifies the exact
service cgroup has no active Runner.Worker or unrecognized process before stopping
only offmenu-runner.service. The operator keeps the queue quiet to prevent a new
assignment between local checks and shutdown. If idleness cannot be established,
no service stop occurs. After systemd-analyze verification, it reloads/starts the
same service and verifies its unchanged sandbox, read-only cache mount and mounted
snapshot file identities. ProtectHome, capabilities and writable output boundaries
are retained. No corpus outputs are activated.

Failure after adding this invocation's drop-in attempts to remove only those exact
bytes and restore the original service. A pre-existing empty drop-in directory is
preserved. Backups and verified private snapshots remain. A later rerun accepts only
identical versioned content. Changes need a reviewed version rather than overwriting
an unknown file. Cleanup of partial files is restricted to paths created by the
current invocation; a crash cannot authorize deletion of pre-existing files.

## Runner inspection and readiness

After the grant receipt is checked, the fixed reviewed runner profile invokes:

```sh
python3 -B scripts/inspect-selected-datasets.py --cache-root /srv/offmenu-refresh/cache
```

The inspector emits at most 12 KiB using schema
`offmenu-selected-data-inventory/1`. It hashes each selected raw file once and parses
only bounded receipt JSON. Strict JSON rejects duplicates and nonfinite numbers.
It never parses raw source JSON, XLSX, ZIP or XML. The deadline is 210 seconds inside
the dispatcher's 240-second child limit. The transport adds job/run/code identity;
the inspector fingerprints its actual bytes and fixed selection.

Status `ready-for-adapter-design`, `completeReady=true`, exit 0 requires both NO/FR
sets to match their pinned historical metadata and acquisition/prior declarations,
be stable/readable/read-only, and retain recognized historical rights profiles.
This is input-design readiness only: rightsDecision and acceptance are
`not-performed`. Empty, missing or partial views emit `incomplete`, exit 2. The
independent ledger audit still runs.

Finland always remains `metadata-only-held` and `manual-only-held`. Unknown
acquisition times stay unknown; filesystem mtime and normalization completedAt are
never freshness. Minimum reuse is 30 days. No diagnostic downloads or revalidates
anything, regardless of elapsed time.

## Tests

```sh
python3 -B -m unittest discover -s tests -p 'test_selected_dataset_metadata.py'
python3 -B -m unittest discover -s tests -p 'test_selected_dataset_grant.py'
```

Inspector tests use synthetic bodies/receipts, including a deterministic growth
fixture that does not assume fine-grained filesystem timestamps. Grant tests mock
all privileged/systemd boundaries; they exercise bounded copying, parent replacement,
private staging, exact selection, permission refusal, subprocess/read bounds,
no-clobber publication, lock exclusion and scoped rollback. They do not establish
that foo's actual paths or mounts are ready; that evidence comes from the local
receipt and runner inspection.
