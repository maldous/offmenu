# Local recipe/menu source importer

`prepare_recipe_menu(assets)` makes a code/control-only manifest.
`ingest_recipe_menu(connection, assets, *, parser_module, parse_asset_once,
limits, run_id, input_manifest_sha256, selection_receipt_sha256)` is the runnable
writer. It requires a NEW empty caller-owned private SQLite connection.57 owns
held-output custody, OS/aggregate-storage limits and final close/fsync/hash and
publication. This API refuses an existing schema and performs no fetching.

DDL is exactly13's asset-scoped13-table contract, SHA
`9a863b44edc8a829c988304c284fe017cb916513f20249f5c5b08423e738198c`.
The parser is unchanged accepted1.3.2, SHA
`5f4c8d9d1153f3e97b726bbaa5e9db39ea4385cc1d3045a2679b559f54089ac8`.
57's already prepared `parse_asset_once(asset,module)` supplies held-FD onepass
input bytes/hash/EOF/custody and returned records. The writer checks that receipt
and source/release/originalSHA/parser bindings before each asset transaction.
It also validates the selected recipe/menu template before inserting source rows.
Arbitrary JSON cannot create eligibility or runtime authority; the actual
caller/source/control/code/resource selection remains external and reviewed.

Every returned source record has full parsed JSON and a parsed-record hash.
Titles are not identity keys: IDs bind source/edition, original asset SHA,
record kind, native ID and occurrence ordinal. Repeated menu IDs/duplicate titles
remain separate occurrences. Recipe ingredient/step order is retained when
source ordinals are unique, including gaps. Component-local repeated ordinals
use stable array order in the flat SQL projection; original order/component and
native ingredientLineId remain in source-location JSON and the complete payload.
No source line/step is silently dropped.
Preparation rejects repeated source/release/blob selections, even under different
source record IDs or kinds, matching the persisted asset/ordinal uniqueness.

Original language, evidenced region, raw yield and quantity/unit lexemes,
preparations, alternatives, source notes, nutrition/time/equipment and locations
survive in the projections or full JSON. Unknown yield/directions/language remain
explicit; no zero-fill, inferred region, title-based dish merge or translation.
Menu items remain listings, never recipes or availability guarantees. All
canonical dish/ingredient links and matching decisions remain NULL/pending.
Source-faithful import does not wait for a canonical registry or complete citations.

19's existing citation/asset metadata is optional and retains unresolved-backfill
states and receipt pointers. The exact15 local-input preparation packet carries
those bindings. Earlier1.3.0 cached bodies are not relabelled or read.
Historical13 recipes/70 menu items are not new output oracles: observed parsed
records, lines, steps and exceptions are measured from the actual selected run.
The declared input extent is15 assets/1,030,719 bytes; neither corpus/country
completion nor English/gold follows from this source-store load.

Each successful asset commits independently. Parser/receipt/projection failure
rolls back that asset, preserves completed assets and a held exception, marks the
release incomplete and raises without a completion receipt. No automatic retry,
cleanup or overwrite occurs.57 must preserve failures and report actual custody.
Post-loop deadline/reconciliation failures also mark the release incomplete with
actual committed row/asset counts. Failure bookkeeping clears an expired handler;
the installed progress handler is always cleared before returning caller control.
`StoreLimits` bounds input extent, assets, records, parsed bytes, lines, steps,
DB pages and cooperative time; OS/FD/file/journal/aggregate limits are57's caller
responsibility. The API does not itself publish a database or grant source use.

The13 views and source tables are available to the selected private UI caller.
Use13's bounded keyset interface; no new browser/server/consumer writer is added.
Tests use the real accepted parser on generated HTML only, including multilingual
quantities, duplicate titles/native IDs, missing directions and invalid receipts.
No retained recipe/menu original, existing store,20GB DB, user profile or inventory
is opened by the source author. Dietary implementation belongs to56.
