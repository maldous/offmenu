# Additional public-source acquisition — Foo only

## Authorization and boundary

The user's **22 October 2026 04:08:45 UTC** instruction, “Add the additional sources and fetch them”, supersedes the earlier **acquisition** hold. This finite operation downloads eligible public reusable source artifacts to a separate retained cache. It does **not** authorize ingestion, normalization, application/database mutation, new accounts/agreements, access-control bypass, or raw-data Git upload. The existing `run`, plan, ingestion and normalization modules are unchanged.

`fetch-sources.json` is the reviewed active acquisition manifest. It keeps all 80 discovery review rows visible, **6 enabled families / 50 exact artifacts** and 74 disabled dispositions. Those rows, files and language variants are **not counts of unique recipes or menus**.

| Enabled family | Exact initial batch | Important limitation |
|---|---:|---|
| Foodista / Common Pile | 5 immutable JSONL.gz shards; 36,802,922 compressed bytes | Mixed documents. Primary LFS SHA256/size pins verified; snapshot CC BY 3.0 policy retained. Recipe filtering, comments/third-party exclusion, author attribution and completeness remain downstream work. |
| ForkRecipe | 1 official archive pinned to `934319313379201f91ddccdd29abd054039a3ad6` | Explicit CC BY-SA 4.0 recipe/data grant. Archive is inert; no JavaScript execution/import or extraction. No invented publisher checksum. |
| CNOUS | 26 exact original XML feed endpoints | Official Licence Ouverte; rolling observations. Exact HTTP-only public-data exceptions are explicit, with **unverified HTTP transport**. No HTTPS downgrade or arbitrary HTTP URLs. Local checksum is not publisher authenticity. |
| Bordeaux / Bègles | 2 municipal JSON exports | Menus and dish composition are related datasets, not independent full recipes. Official Licence Ouverte. |
| Toulouse | 4 municipal JSON exports | Menus, dish composition, ingredient and technical-sheet registry rows; **no recursive supplier PDF fetch**. Official LO v2.0. |
| MedlinePlus | 12 exact EN/ES pages representing 6 explicitly linked works | NLM expressly identifies Healthy Recipes text as US public domain. No image/media downloads or broad crawler. Preserve source credits and translation discrepancies. Live robots preflight on Foo. |

The municipal export paths came from the official Export UI; the documented `timezone=UTC` parameter replaces the research browser's timezone. Small public API samples verified schemas/access, **not the full export bytes**. Foodista shard hashes are publisher LFS metadata, not Xet ETags. ForkRecipe and rolling feeds have no asserted publisher SHA256: receipts calculate the actual acquired bytes.

## Retained overlap and disabled sources

Do not refetch the pinned retained baseline: Wikibooks across 32 editions, UniTools 501, based.cooking-derived material, or the same AdamBouhmad historical archive revision. Demonstrated deltas and source/work/version deduplication are separate work.

Every other discovery row has a specific disabled reason. Notable holds: MFDS/NEIS approval or key gaps; Taiwan documentation HTTP403; Yamagata's additional deemed-acceptance/indemnification agreement; Koch-Wiki/Cuisine-libre bounded handler/export gaps; unresolved Konstanz original archive/provenance; commercial restrictions and uncertain upstream rights. The CROUStillant derivative is not added over original CNOUS and its deposited-data/direct-API terms distinction remains explicit. No new agreement is accepted and no denial is bypassed.

## Fixed execution contract

The existing reviewed Foo dispatcher profile invokes:

```sh
python3 -I -B manual-action/fetch_sources.py
```

The bundled manifest is the only input manifest; there is no arbitrary URL/command argument. Production refuses any hostname other than `foo` and any supplied Actions runner name other than `foo-offmenu`.

- Raw artifacts and private operational state: `/srv/offmenu-refresh/outputs/additional-sources-20261022/source-cache`
- Strict safe return: `/srv/offmenu-refresh/outputs/additional-sources-20261022/receipts/fetch-summary.json`
- Never use `/srv/offmenu-refresh/cache`: its runner mount is read-only. Never place this cache under the code checkout or existing ingestion staging.

Limits: **2 parallel source workers**, one sequential artifact at a time per source, approximately **2 MiB/s aggregate** transfer cap, **256 MiB transferred per invocation**, **1,200 seconds**, **10 GiB shared-filesystem free-space reserve**, 30-second socket operations, explicit artifact compressed/expanded caps and at most 3 transient/corruption attempts. Municipal sources wait 2 seconds/request, MedlinePlus 5 seconds, others 1 second. Server Retry-After takes precedence, including durable host-wide cooldowns across resumptions. A server delay beyond the available window is reported, never shortened to force another request.

The 256 MiB cap bounds actual transferred bytes including retries, not the sum of every artifact's defensive maximum. A capped invocation remains resumable; a cap is not evidence that all advertised data is unavailable. JSON municipal validation is capped at 64 MiB per file; no unbounded export or category traversal is performed.

## Integrity, recovery and status

An exclusive cache lock prevents simultaneous duplicate acquisition. Symlink components are refused. Streaming writes use private `.part` files, durable entity/byte checkpoints and atomic final rename. Resume requires a strong ETag/Last-Modified or pinned content hash; unchanged completed artifacts are rehashed and reused without a second payload GET. Orphan completion receipts recover the receipt/rename crash window locally. Changed or uncheckpointed prefixes are discarded safely before identity changes. At most one rejected temporary per artifact is retained; only owned partials can be replaced, never an existing accepted artifact.

401/403 and authentication/error HTML stop that artifact without credential use or alternate mirrors. Redirects are capped and restricted to reviewed HTTPS hosts; signed redirect query strings never enter receipts. Original HTTP exceptions cannot be reached by HTTPS downgrade. XML DTD/entity declarations are rejected by parser callbacks, including UTF-16; JSON/JSONL, gzip CRC and bounded archive-member/path checks run as data-only validation. Archives are not extracted and downloaded code is never executed.

Local per-artifact receipts retain source revision/origin, public license/attribution evidence, response metadata, redirect provenance without signed queries, byte length, actual SHA256, and whether that digest was publisher-pinned or locally observed. Private status and raw cache remain on Foo.

`sanitize_report` independently validates and projects the return JSON. It rejects contradictory safety flags or empty/blocked `complete` claims. Returned summaries contain only controlled source IDs/status/error enums, file/byte counts and SHA256s—not local paths, raw bodies, arbitrary errors, signed URLs or credentials. Disabled rows are a count in the public summary and retain their full dispositions in the source manifest.

- Exit **0 / complete**: every enabled artifact was acquired or verified reusable. This means acquisition completion, **not accepted recipe/menu records**.
- Exit **2 / partial**: an artifact/source failed, was rate-limited or hit a resource cap; other sources continue. Checkpoints preserve continuation.
- Exit **2 / blocked** failure schema: whole-run local preflight/lock/disk refusal. This is not permission to widen paths or bypass controls.

Summary schema/schemaVersion: `offmenu-source-fetch-summary/1`; fatal failure schema/schemaVersion: `offmenu-source-fetch-failure/1`. The reviewed dispatcher may return only the strict sanitizer projection. It must never collect the source-cache directory as an artifact or Git content.

## Offline verification

```sh
python3 -B manual-action/fetch_sources.py --validate-only
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s manual-action/tests -p test_fetch_sources.py -v
```

Tests use generated data and an in-memory HTTP transport only. They cover exact pins/retained-family refusal, atomic reuse/resume/crash recovery, ETag/range failures, rate limits, disk/byte/cancellation caps, UTF-16 XML entities, gzip CRC, inert JS archives, source isolation, host/path/redirect policy and strict sanitized returns. The preparation environment made **no production source downloads**.
