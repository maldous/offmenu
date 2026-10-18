# One fixed Zenodo private original

## Exact selected operation

The next prepared profile is `zenodo-private-original`, source key `global.zenodo15169428.datasetcsv.v1`. It uses the unchanged reviewed `CachedAcquirer`, `ResourceBudget`, and `HTTPSFileTransport` from the existing acquisition core. There is no new collection or transport engine.

- Exact GET: `https://zenodo.org/api/records/15169428/files/dataset.csv/content`
- DOI: `10.5281/zenodo.15169428`, v1, published 2025-04-07; Pau Barba and Núria Canals, Zenodo deposit.
- Expected original: 110,013,794 bytes, publisher MD5 `986efafad65c7969fde13a46d2defba0`.
- Private source custody only. Publisher metadata declares ODbL 1.0. Upstream recipe-prose rights, commercial incorporation, redistribution, normalization, country/type mapping and gold acceptance remain held.
- One future GET, zero retries, HEADs, redirects, ranges, cookies or credentials. The earlier source-qualification probe was one disclosed 8,192-byte ranged GET and is separate from this future original request.
- Hard cumulative transfer bound: 128 MiB. Source body cap: the exact expected length. One shared 900-second deadline covers preparation, transfer, hashing and header verification; the existing dispatcher gives only this fixed step a 930-second outer kill bound. The workflow's existing 25-minute job bound is unchanged.

The request remains exactly `schemaVersion`, `jobId`, `profile`. No path, URL, command, selection or budget override is accepted. Source activation requires the later reviewed source/control composition and root-owned request.

## Evidence, claims and reuse

The immutable selection pins the source proposal, publisher metadata, header-only qualification and bounded lineage review. It also imports the already-pinned corrected owner snapshot and adopted r6 lookup through the approved preparation helper. Any exact source occurrence in those inputs blocks a new request, rather than treating it as an empty claim catalogue.

Before cache action, the adapter scans bounded runner metadata under `/srv/offmenu-refresh/cache` and `/srv/offmenu-refresh/outputs/collection`, without reading native user trees or raw bodies. Exact API/landing aliases, DOI/record ID, checksum and former draft key detect another cache identity or claim. Known alternate matches, source partials/recovery, uncertain claims or existing reservation files stop the operation. The scan is limited to 10,000 entries, depth six, 2 MiB per metadata file and 32 MiB total. An incomplete readable-runner scan stops; inaccessible native claims remain an explicit coverage limit, not a fabricated empty catalogue.

A single coordinator-owned repository selection and persistent runner intent precede reuse or acquisition. The existing dispatcher lock, the selected intent lock and the acquisition engine's shared-cache lock serialize the selected work. An interrupted or failed intent cannot silently retry. A verified matching cache is reused, retains its original acquisition timestamp and undergoes the same length, MD5, SHA-256 and header validation. A 29-day fixture proves zero-network reuse; a stale cache does not trigger another GET under this one-request intent.

The reviewed evidence found zero exact matches in the corrected snapshot and adopted index, and zero in 211 returned Gateway messages, 77 of which were truncated. Only 39 referenced native claim files were exported. Those limits remain disclosed. No universal current ownership clearance is asserted.

## Storage and capacity

Only the already-existing runner-owned outputs root is writable. The selected subdirectory is `/srv/offmenu-refresh/outputs/collection`; shared source objects remain inside its `source-cache`. All output directories must be owned by the runner, with symlink-safe paths and the same filesystem as the outputs root.

Before GET, fresh `statvfs` must cover the existing 88,418,025,472-byte planning guard, the 128 MiB transfer allowance, and a separate 110,013,794-byte physical reservation. That guard already includes the 20 GiB floor; it is not added twice. `posix_fallocate`, an allocated-block check and a second fresh free-space check verify the reservation. The existing collector preserves the guard during every write. Keeping the reservation while writing the original deliberately budgets both allocations conservatively. Unknown commitments are not reset or claimed reconciled.

Only the reservation file created by this invocation is released, after verifying its inode. Existing reservation files are never cleared. A killed process may leave an intent/reservation for later explicit reconciliation; the next run blocks. Allocation failure or insufficient capacity stops before network access.

## Results and verification

The raw original remains on Foo. The adapter checks only the first bounded header line and streams exact byte length, publisher MD5 and SHA-256; it does not parse recipe rows. A digest-named metadata receipt records all outcomes, including failed transfers. Request and byte counts survive claim-write, reservation-release and result-write failures. Stdout is a closed summary with integrity results, counts, receipt persistence and conservative safety flags; it contains no raw rows or arbitrary exception text.

The fixed steps are `readiness`, `zenodo-original-tests`, `zenodo-private-original`. Publisher changes are limited to the new profile and two step IDs plus their exact order. Both source pins are left unchanged in the preview for the later independently reviewed substitution. No permissions, credentials, runner identity, workflow trigger, publisher destination or native receipt path changes are included.

All source transfers in development tests are synthetic. This preparation does not itself download the original, publish control or dispatch a job.
