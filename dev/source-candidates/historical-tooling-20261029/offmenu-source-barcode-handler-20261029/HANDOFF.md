# Additive source-barcode Worker adapter — review candidate

Implemented only the assigned endpoint adapter. No production mutation, index fetch/build/proof, raw graph/database read, auth/provider change, cache change, identity activation or source promotion occurred. The inaccessible producer data directory was not read again or permission-modified. Both supplied source inputs match their authoritative exact byte lengths and SHA256s; source consumption began only after those checks.

## Existing seam and exact pickup

input/endpoint-seam201.json is the supplied 5,210-byte immutable current-v201 landing-only.mjs seam, SHA25645bc8b9a7eb6dbd609cb2683aede1490028d6ca6a4c7bf583cc1ae5a8ea66fbc. Its module pin is cceef18a1e65cc9e12d99d52e531b84aec0fdd9227edee275805bc7107065d29. Full Worker source is deliberately not reconstructed here. Reconcile newer dispatcher drift at the actual integration point.

Import createSourceBarcodeHandler (and SOURCE_PINS/PUBLIC_BASE as applicable) from the source modules; alternatively import createSourceBarcodeHandler and PUBLIC_BASE from build/source-barcode-handler.bundle.mjs and SOURCE_PINS from source/protocol-pins.mjs. Initialize a single closure:

    const sourceBarcode = createSourceBarcodeHandler({selection: ACTUAL_REVIEWED_PUBLISHED_SELECTION});

The selection must contain manifestUrl exactly https://offmenu-corpus.netlify.app/common-data/derived-releases/source-barcode-index-v1-20261029/manifest.json, manifestSha256 (actual published bytes; never a synthetic pin), indexReleaseId source-barcode-index-v1-20261029, exact SOURCE_PINS and exact PUBLIC_BASE. Missing or mismatching selection produces index-unavailable without fetching. SELECTION-TEMPLATE-NOT-ACTIVE.json has null pin by design; it is documentation and must not be deployed as an active selection.

Insert ONLY this branch immediately AFTER the existing environment fallback return and BEFORE the /api/data/public branch:

    if(new URL(request.url).pathname==='/api/corpus/source-barcode')return sourceBarcode(request);

Preserve the existing fallback guard, all routes/assets, previous.fetch, scheduled forwarding and headers. dispatcher-before/after.txt and dispatcher-only.patch are exact excerpt-level artifacts, not a full landing-only replacement. The focused test executes the actual supplied dispatcher with only this insertion and verifies environment fallback precedence and byte-identical removal of the added branch. The integrator remains sole live writer. Roll back by removing only this branch/import/closure/new module, preserving newer unrelated changes.

## HTTP contract

GET /api/corpus/source-barcode?source=...&release=...&namespace=barcode&value=... accepts only those four required fields and optional limit1..20/cursor. Duplicate or unknown params are 400; wrong methods are 405 Allow:GET; other routes return null. The dedicated candidate-reference route with explicit full source tuple is the HTTP opt-in to candidate references (the Python local reader's allow_candidates=True); no phase/2 or normalized food lookup is fabricated. Original lexical characters/leading zeros/whitespace/Unicode are retained exactly. There is no digit/checksum repair, trim, GTIN conversion, food gate, source stitching or arbitrary URL parameter.

Response envelope is offmenu-source-barcode-candidates/1 with the frozen four statuses. Validated matches/absence return200. Technical/integrity/resource/cursor errors return503 index-unavailable, countKnown:false, complete:false, candidateTotal:null, no refs. Invalid request fields return400 with the same unavailable envelope and null query. A missing publication pin can never become not-found.

Candidates are references only. citationRefs/ingredientRefs/nutrientRefs and sourceAssertionStatus remain null; their meaning remains unresolved, not absent/zero. False canonical-identity/planning/aggregation flags stay false. Exact manifest/base/source pins accompany successful responses. Ambiguous keys preserve total count and the stored20-ref cap. Pagination binds manifest, exact query, limit and offset in canonical URL-safe base64; capped terminal pages can remain truncated:true with nextCursor:null. complete:true denotes exact-index lookup completion, not nutrition/hydration completeness.

The adapter pins manifest bytes, validates its complete 256-shard inventory and every descriptor's path/hash/count types/producer bounds, then pins the consumed compressed shard before gzip decoding. It validates full shard entry count, strict hash ordering, each exact tuple/hash/prefix, candidate totals/returned count/truncation, resource uniqueness and all exact reference fields. Unrelated malformed entries invalidate the entire shard before any not-found response. It does not rerun global producer census/proof or fetch all shards to requalify publication: immutable reviewed manifest selection remains the authority for those producer-wide counts.

## Worker feasibility — remaining activation prerequisites

No real completed manifest pin or measured shard sizes were supplied. No full-coverage or live runtime-performance claim is made. Producer64MiB compressed/256MiB decoded ceilings are not Worker memory allocations. This consumer enforces4MiB compressed and8MiB decoded per requested shard,16384 entries,200000 JSON nodes,32 nested JSON levels,256KiB response,32768-byte cursor and one10-second request budget. All over-limit cases return unavailable rather than partial absence or a smaller source subset. Reference string bounds are4KiB IDs/2KiB safe original asset paths. Path references containing URL escapes/control/query/fragment characters are refused rather than normalized. Confirm actual producer output fits these bounds before enabling; do not silently relax them or claim complete availability merely from mock tests. Source inventory remains whole; oversized requested prefixes are explicitly unavailable.

Reads are streaming/bounded; exact compressed hash verification precedes bounded gzip decompression. Native Web Crypto needs a bounded complete compressed buffer; bounded decoded JSON text/object allocation is still necessary and is NOT a constant-memory streaming index parser. No disk/service/framework/global state/cache was added. The strict parser rejects duplicate decoded keys, nonfinite/unsafe numbers and malformed UTF-8/Unicode before acceptance. Total request deadline/caller cancellation aborts fetch/read and prevents a duplicate fallback call. Workers clock precision/CPU limits mean synchronous parsing is bounded structurally, not preempted by a JavaScript timer; actual CPU/memory/concurrency feasibility remains an integrator check using measured index sizes and the existing Worker settings, without raising limits by assumption.

The fixed .gz URL must expose the raw pinned gzip file bytes with absent/identity Content-Encoding. The adapter requests Accept-Encoding:identity and refuses other Content-Encoding, redirects, changed response URL, HTTP/length mismatch, oversized chunks and decompression/hash failure. Confirm published response headers and exact source SHA in the actual Worker before activation. If hosting automatically decodes/transforms the .gz body, this adapter honestly returns unavailable; publication transport must be reconciled by existing owners, never bypass SHA checks.

## Evidence and reproduction

15 focused deterministic mocked Node tests passed, including exact supplied dispatcher, four statuses, immutable selection, SHA/gzip/count/reference integrity, pagination/ambiguity, duplicate JSON keys, no arbitrary outbound path, stream cancellation and a fake-clock absolute deadline. No real index/source/provider calls occurred. A separate bundled ESM smoke verified exact tuple digest, unrelated-route null and missing-selection503 without a fetch. source/ contains standard Web APIs only, no Node dependency. Tests use Node standard library gzip/crypto only. build-handler.mjs uses already-installed pinned esbuild0.25.12 to bundle this three-file component with zero external imports; no app build, install or deployment.

    node --test tests/source-barcode-handler.test.mjs
    node build-handler.mjs

The build recipe's module path points at Foo's existing esbuild installation; another authorized executor must select its already-pinned0.25.12 module path. Do not install as an integration side effect. CANDIDATE-RECEIPT.json/MANIFEST.json carry exact hashes and input authority.

Primary current runtime references consulted (no configuration changed):
https://developers.cloudflare.com/workers/runtime-apis/web-standards/ (gzip DecompressionStream and clock behavior)
https://developers.cloudflare.com/workers/runtime-apis/fetch/ (Accept-Encoding/automatic compression)
https://developers.cloudflare.com/workers/best-practices/workers-best-practices/ (bounded streaming/request state)
