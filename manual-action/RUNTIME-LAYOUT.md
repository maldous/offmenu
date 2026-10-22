# Explicit local runner storage

The split runner requires `OFFMENU_RUN_LAYOUT` before reading or creating runner
state, locks or diagnostic output. It names a regular, nonsymlink, current-owner
0600 JSON file with exactly these fields:

```json
{
  "schema": "offmenu-runner-layout/1",
  "runtime": "/home/user/src/offmenu-data/runtime/manual-runner",
  "public_staging": "/home/user/src/offmenu-data/staging/public",
  "normalization": "/home/user/src/offmenu-data/normalized/manual-runner",
  "household": "/home/user/src/offmenu-data/private/household",
  "lock": "/home/user/src/offmenu-data/runtime/manual-runner.lock"
}
```

This example is documentation, not an installed configuration or migration.
All four directories must already exist, have private0700 permissions and belong
to the current user. They must be absolute, distinct, nonoverlapping and have no
symlink ancestors. The shared lock is outside those four roots; its parent must
exist, be owned by the user and not writable by group/others. An existing lock
must be a private0600 regular owner file. The resolver never creates directories,
copies databases or changes permissions to make an unknown layout acceptable.

Runtime contains `ingest` metadata, checkpoints, receipt caches and pending
spools. Public staging contains the six public domain DBs and their sidecars and
writer locks. Normalization contains compact caches/cursors and existing legacy
sidecars. Household contains its `staging` and `relational-targets/v1` children.
Ingest discovery excludes all four managed roots and refuses an older catalog
cursor lacking the matching physical exclusion binding. An owner must explicitly
reconcile such a cursor before resuming discovery; normalization never invokes
discovery. Acquisition cache locks and immutable original paths are unchanged.

The normal runner owns one nonblocking shared singleton regardless of checkout.
After acquiring it, it records `layout-admission.json` locally with the exact
config-byte SHA256/schema, resolved roots and their identities, and the singleton
device/inode. Process-local `OFFMENU_RUN_FD`, `OFFMENU_RUN_LAYOUT_SHA256` and
`OFFMENU_RUN_LAYOUT_BINDING_SHA256` carry that admission across re-exec. Lower-level
operational writers and diagnostics require the matching inherited lease; they
are not independent launchers that create their own per-checkout lock. Changed
selection/configuration/root/lock identity refuses admission. Re-exec must retain
all pins and the same FD. Physical admission is never added to logical source,
rule, cache or normalization snapshot identities, or retrofitted into old receipt
bytes. Executable source changes receive a new implementation/job identity.

Only synthetic fixtures may explicitly select `OFFMENU_RUN_LEGACY_FIXTURE=1` for
the previous nested layout. It is not an automatic fallback when an operational
selector disappears, and is not a post-cutover production launch mode. A present
split selector always takes precedence and invalid split configuration refuses.

Migration and rollback belong to the serialized owner, with actual process and
SQLite quiescence. Move three state children before residual runtime; separately
preserve the sibling `.git/offmenu-run.lock` inode at the common lock destination.
Keep WAL/SHM, private modes, source ownership, cache bytes and cursor state. Never
unlink/recreate a held singleton or launch an old binary on partially split state.
Rollback must exclude all consumers, keep one authoritative singleton and either
retain the selected external layout with compatible code or fully reverse the
physical groups before restoring old code. This source change performs no move,
rollback, restart, source acquisition or normalization admission.

Focused checks are `test_runner_paths.py` and `test_runner_layout_integration.py`.
They use generated state under the Worker26 artifact directory. They cover
missing selection without state creation, explicit fixture mode, private config,
shared lease contention, re-exec binding, consumer routing, and cache/cursor
continuity after directory rename with a new epoch for changed fixture WAL/data.
They do not establish retained-data acceptance, actual AI review or gold status.
