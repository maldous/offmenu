# Acquired-source catalog bridge (2026-10-22)

## What is and is not established

`ingest_acquired_catalog.py` converts exactly named artifacts from the reviewed
`fetch-sources.json` into private retained-loader descriptors. Generated fixtures
verify the contract; the cloud workspace has **not** opened Foo's real source
files, parsed them, or verified database writes. Acquisition's 50 files and
108,318,002 bytes are not counts of accepted recipe/menu records. The current
user-operated run is not interrupted or changed by this work.

No fetching, cache mutation, archive extraction, JavaScript execution, linked
media/PDF retrieval, directory crawl, database write, permission repair, or raw
Git upload occurs in this module.

## Exact routing

| Family / artifact role | Files | Adapter | Domains |
|---|---:|---|---|
| Foodista JSONL gzip documents | 5 | `foodista_common_pile` | recipes, ingredients, citations |
| ForkRecipe inert tar gzip | 1 | `forkrecipe` | recipes, ingredients, citations |
| MedlinePlus EN/ES HTML variants | 12 | `medlineplus_healthy_recipes` | recipes, ingredients, citations |
| CNOUS XML menus; optional explicit ingredient labels | 26 | `fr_cnous_menus` | recipes, ingredients, citations |
| Bègles `met_menu_cantine.json` | 1 | `fr_begles_menus`, menu | recipes, citations |
| Bègles `met_plat_cantine.json` | 1 | `fr_begles_menus`, dish | recipes, ingredients, citations |
| Toulouse `menus.json` | 1 | `fr_toulouse_menus`, menu | recipes, citations |
| Toulouse `plats-extrait-de-datameal.json` | 1 | `fr_toulouse_menus`, dish | recipes, citations |
| Toulouse `denrees-extrait-de-datameal.json` | 1 | `fr_toulouse_menus`, ingredient | ingredients, citations |
| Toulouse `liste-des-ft-des-denrees-de-la-cc-tls.json` | 1 | `fr_toulouse_menus`, technical_sheet_reference | citations |

These are explicit dispatch bindings, not a claim that menus are full recipes,
that all Foodista documents are recipes, or that ingredient labels are normalized
foods. Medline's 12 variants retain six work IDs and independent language/URL
provenance; counterparts are not automatically equivalent. Unknown artifacts
receive `adapter-required`, never extension-based generic ingestion.

## Python integration

- `discover_acquired_sources(options=None, existing_sources=())` returns new page
  `sources`, `errors`, `counts`, `source_dispositions`, `restriction_updates`,
  `complete`, `truncated`, `resume_cursor`, and `manifest_sha256`.
- `merge_acquired_sources(existing_sources, acquired_result)` merges exact paths;
  unrelated source IDs, fingerprints and checkpoint metadata are unchanged.
- `preflight_acquired_access(options=None)` opens only named data/receipt pairs
  read-only, reads no payload, and reports access separately from integrity.
- Options: `acquired_cache_root`, `acquired_manifest`,
  `acquired_resume_cursor`, `acquired_max_files` (100),
  `acquired_max_hash_bytes` (512 MiB), `acquired_max_scan_seconds` (120).
- Default cache is
  `/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache`.
- The acquired cursor is separate from the retained discovery cursor. Merge prior
  acquired pages before resuming. A changed manifest/root invalidates that cursor;
  do not reset or overwrite retained DB cursors.

Every bridge descriptor has `acquired_source: true`, exact `acquired_adapter`
when mapped, `acquired_role`, and `metadata.acquisition`. Dispatch must reject
unverified/held/unreadable/duplicate entries independently; it must not fall back
to a generic adapter for an acquired descriptor lacking a reviewed mapping.

## Verification and resume

Each `<artifact>.receipt.json` must match the fetcher's canonical `artifact_key`,
source ID/revision/origin, license/evidence/attribution/scope, optional catalog
resource identity, acquisition-only/no-upload flags, complete status, expected
length/hash, and declared checksum basis. Original bytes are then streamed through
SHA-256; inode/device/size/mtime/ctime and receipt replacement races are checked.
Local digest matching is never promoted to publisher authentication, especially
for CNOUS's explicitly unauthenticated HTTP transport.

An unchanged input can reuse the **previous byte-hash observation** only when
manifest digest, receipt digest, artifact key, SHA, bytes and full stat signature
match; a read-only open rechecks current access. `verification_basis` distinguishes
`cached_byte_hash_and_current_metadata` from `current_full_byte_hash`. Changed
identity is rehashed. No complete-file hash is repeated merely to rediscover an
unchanged verified input.

Path-derived IDs match retained catalog conventions. Unchanged acquired bindings
preserve existing fingerprint keys; specialized adapters own explicit parser
versions. A byte alias only suppresses reprocessing when its existing source has
a compatible acquired adapter/role/domain/language/work binding and its recorded
identity still matches. Incompatible-parser aliases remain candidates with alias
provenance rather than borrowing unrelated cursors. Rights holds remain holds;
unknown record-level rights are still checked by the content adapter. Disabled
manifest rows are individual source dispositions, not invented files or a global
job gate. `complete` means catalog evaluation complete, not ingest completion.

## Read access: static finding, not a live-host assertion

The primary service source at immutable fetch execution
[`6740bcbf`](https://github.com/maldous/offmenu/blob/6740bcbfacfcc51e553128438f5153eca3a649a5/scripts/runner_host_setup.py)
sets `User=offmenu-runner`, `Group=offmenu-runner`, `UMask=0077`; its host setup
requires the output root owned by that account with mode `0700`. The fetcher
inherits that identity, creates source directories `0700`, and receipts `0600`.
Thus a normal distinct `user` account would ordinarily lack access. Actual Foo
UIDs, ACLs and live readability remain unobserved here.

The user has approved a narrow named-user read-only handoff of these exact 50
public-source artifacts plus their provenance receipts and necessary traverse-only
ancestors. Implementation/review is separate; approval is not evidence it has
already been applied. Do not silently `chmod`, broaden groups/world access, copy
raw data elsewhere, change services/mounts, or acquire wider permissions. Before
that handoff is verified, new-cache ingestion is access-pending, not fully ready.

Linux parent descriptors use `O_PATH|O_DIRECTORY|O_NOFOLLOW`, permitting an exact
file open with directory traversal only; no directory-listing right is needed.
Missing/unreadable files remain isolated structured errors, with no raw exception
text and no permission repair.

## Tests

`python3 -m unittest discover -s manual-action/tests -p test_ingest_acquired_catalog.py -v`

Synthetic fixtures cover all 50 exact bindings, receipt identity/rights/hash/size
mismatches, unchanged metadata-only reuse and source/version identity stability,
modified-cache rehash, symlink parents/leaves, denied reads, access-only preflight,
O_PATH traversal, independent rights holds, incompatible aliases, paired language
provenance, finite page/byte budgets, cursor identity, receipt races and no cache
mutation/directory crawl. They do not establish real Foo data or app readiness.
