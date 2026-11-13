# Retained common-corpus recovery assessment

Checked 2026-10-28 against cloud-recovered source only. No Foo commands, data processing, access expansion or mutation were performed by this assessment. Fresh parent inventory proves access/presence, not data integrity or qualification.

## Current evidence

The deployed Windmill metadata probe found six manifests, no final bulk or places manifest, 414 regular files in bulk and 2,407 regular files in places. The latter is not the old custody count of 2,393 packet assets; these are different observations/counting units, not evidence of verified new records. Current source custody and any old host process state remain unknown.

## Existing resume implementation

Bulk `scripts/repair-bulk-controls-20261014.py:278-372` refuses an existing output without `--resume`; resume requires `checkpoint.json` schema `offmenu-bulk-repair-checkpoint/1`, with exact input manifest/schema/contract/implementation/source-directory pins. It verifies all input assets before repair and compares every retained asset against the exact single permitted transform. Legacy partials lacking a pinned checkpoint are explicitly rejected. This is not a generic append/resume command.

`scripts/verify-bulk-repair-checkpoint.py` is the existing read-only recovery inspector. It compares 1..100 selected input/retained assets, records checksums and counts, and marks each usable or held. Its receipt is expressly NOT an admission manifest. It requires original input access and cannot run meaningfully with partial output alone.

Places `scripts/align-places-common.py:344-388` and `scripts/places_checkpoint.py:52-96` require an absent final output, existing `.partial` plus sibling `.checkpoint.sqlite` on resume. State version is 1. Pins include absolute input/output paths, every input byte hash, schema/contract, implementation/checkpoint implementation, and packet options. The checkpoint binds cursor, source-identity table, counts, closed packet receipts and any exact buffered orphan. It refuses arbitrary legacy packets. Merely copying a checkpoint to a new path invalidates its pins.

## Exact additional source/custody paths

All paths below are under `/home/user/src/offmenu-data`; none is in current approved mounts except the noted bulk checkpoint.

Required original inputs for completing existing algorithms:
- `common-bulk-food-20261014/`: immutable original common graph manifest and its listed assets. Required to verify authorized transform and missing assets.
- `curated-expanded-country-search-20261013/blobs/`: accepted curated input. The producer consumes manifest, records/overture-food-places, records/wikidata-food-businesses and applicable notices; however its CURRENT implementation hashes every file beneath blobs in its checkpoint input pins. Restricting that to fewer subtrees needs a reviewed implementation change and new pins, not silent omission.

Optional historical recovery/custody sidecars, if present (absence is evidence, not installer failure):
- `common-places-semantic-final-20261014.checkpoint.sqlite`
- Same path with `-journal`, `-wal`, `-shm` appended, only for a consistent read-only custody snapshot if present. Never open the retained source database in a mode that performs recovery/writes. A live DB needs quiescence/coherent snapshot before meaningful recovery.
- `common-places-semantic-final-20261014.alignment.lock`
- `common-bulk-food-semantic-final-20261014.repair.lock`

Already in current scope, but presence still needs a targeted check:
- `/offmenu-corpus/common-bulk-food-semantic-final-20261014/checkpoint.json`

These path derivations do not prove host existence. A legacy process predating checkpoint code may have none of these files. Do not grant the whole data root or host /proc just to inspect them.

## Safe path forward

1. With CURRENT mounts, run a metadata/checkpoint-presence check and bounded retained-output integrity inspection. Preserve original output bytes. Report whole-file SHA, gzip CRC/EOF, JSON validity and aggregate packet counts only. Never print records. Verify fstat identity/size/mtime before and after reading; a changed asset is unresolved, not reusable. Write separate diagnostic receipts only under approved `/offmenu/data/.offmenu-platform`, not retained packages.
2. Existing `packet_counts` and schema definitions can support an explicitly partial diagnostic wrapper (with installed jsonschema_rs if available); do not invoke the full qualifier on manifestless partials or fabricate a manifest to get around its admission check. Source equality, global identity/reference validity and full source coverage remain unresolved from this scan.
3. Obtain the specifically approved additional read-only input/custody scope in one bounded host change. Keep raw archives/credentials/other directories excluded. Confirm only metadata/current custody of documented legacy places PID209490 with birth/startTicks if needed using a host-admin helper; isolated runner PIDs cannot establish host process state. Never SIGCONT/kill an old PID based only on its number.
4. Use fresh output paths under current writable repo. Never resume or alter legacy mounted outputs. First pin original inputs and exact producer code. For bulk, source-compare all reusable retained assets with the existing inspector. A reviewed recovery importer may COPY verified complete assets into new output and write a new recovery record/checkpoint binding original receipts plus NEW paths; no blind checkpoint rewriting or invented historical admission. Missing/corrupt assets remain held and are recomputed from original input, without deleting originals.
5. For places, there is NO general legacy-output adoption implementation in inspected code. If a valid checkpoint exists, inspect its source/payload/identity/cursor consistency; relocation still requires explicit reviewed migration. If none exists, deterministic replay from verified curated inputs into a new run-owned output can compare completed retained packet boundaries and reuse only verified exact assets; this needs a reviewed recovery adapter. Otherwise a new production build would recompute the graph while preserving the retained output, but that is a recovery choice to resolve explicitly, not pretend resume.
6. Before new heavy processing, reconcile current owner/process custody and capacity. Existing custody requires final-output allowance plus >=60 GiB SQLite scratch and 10 GiB free reserve. Current reported free disk alone is not a post-output proof. Use existing agreed one-writer/resource controls, not blind six-worker defaults.
7. Existing release contract remains: complete final manifests, all-eight-package qualification with exact schema/contract/manifests/source counts, immutable assembly, then authorized static publication and served readback. Six-ready proof is historical and not an all-eight proof. Common-corpus expansion remains distinct from production foundation and identity-only candidate contracts.

## Essential blocker

Cannot complete/source-validate food or places from current mounts because the two immutable input roots are outside granted access. Cannot assert safe historical resume because checkpoints and host process custody are unverified. Useful retained integrity checks CAN proceed now without expanding access. No data or production publication should be represented as complete from current file inventory.

## Primary inspected sources

- `scripts/repair-bulk-controls-20261014.py`
- `scripts/verify-bulk-repair-checkpoint.py`
- `scripts/align-places-common.py`
- `scripts/places_checkpoint.py`
- `scripts/qualify-common-expansion.py`
- `scripts/assemble-common-corpus.py`
- `docs/OFFMENU_CUSTODY_HANDOVER_20261014.json`
- `../evidence/ACTUAL-INVENTORY-20261028.json`
