# Owned foundation production integration

## Delivered

A new, separately qualified production-target release, an owned-data API, matching protected browser/server stock bindings, and a narrow adapter in the **existing** reviewed-audio Demo scanner. Target: `https://offmenu.aldous.info`. This lane has not deployed anything.

The original R8 local manifest `f9338984…`, declared admission `d02e9df2…`, and `localhost-only` / `publicPublicationAccepted:false` remain unchanged. The original admission body was unavailable: it is not claimed verified, recreated, or reused as public admission. The new technical receipt records the checks actually performed under the user's production-delivery direction, not an independent semantic review.

## Actual scope

- 11,527 qualified source observations: OFF 2,871; USDA 8,656.
- 4,908 source-specific queries: OFF 2,871; USDA 2,037. These are not a global unique barcode count or normalized-ingredient total.
- 2,037 known and 274,611 explicitly unknown parameter states.
- No full-product, normalization, Gold, automatic planning, recipe/nutrition join or physical-product equivalence admission.
- The separate 2,574 partial identity claims are excluded. Actual identity selection remains null; no English/type/admission was invented.

The recovered 26ef bundle was passively parsed, never executed. All 515 blob hashes/bounds and all 512 product partitions were checked. All 4,908 source-specific queries were exercised with exact existing reader `0b098783…` and unchanged policy/phase assessor. Public DTOs passed raw/private-field and filesystem-locator exclusions.

The new payload removes only 651 unused internal `sourceProjection` envelope members. All candidates/observations are unchanged. After 240 partitions were recompressed, a second complete traversal produced the identical source-record DTO digest:
`a7fe5c4b4f497374e23b8bcf6a60fed0bc21041d5bb4fe4980b238aa6d41143a`.

OFF ODbL/DbCL attribution and image-rights caveat, USDA retained public-domain/CC0 declaration, source qualification and unknown/false flags are retained. Historical notices remain with a new-target addendum. No images, trademarks, new acquisition or external provider lookup are introduced.

## New release pins

- Release: `offmenu-foundation-production-20261027-v1`.
- Manifest: `10f4f5acb9dbab8e5411dc7c7aa9136d6bb6317cd5eb11d9ec6c9ccdd4a1a0db`.
- Technical receipt: `fedce50756a6598ee3fc53d6e0507a4d21103711dcaee6911c61679b70cb2cdb`.
- Unchanged policy: `ad8f03427a4a59f7570c0eb3a12c4e311fb46998d9ee0dbc56058ef360b5d25e`.
- Notices: `9b34b1c2642129e4a8b4f5872dd4e519d72c1bb78911424fb93082bb8649e79b`.
- Handoff binding: `5cf149699ea8ac2894a9b53b720dc9f919764160bdce68480dae85aa7f87f584`; the three historical bindings are retained.

## API, source and data boundary

Runtime files under `private-release-build/production/`:

| Module | Bytes | SHA-256 |
|---|---:|---|
| owned-foundation-response.mjs | 31,274 | dcde08ee9d7299e1c406208210a2f07145742b5610a6209fc2718e5597af505b |
| foundation-production-release.mjs | 9,285,993 | e2ff55d2c5081010656fc13e41a7ef13a377a3add8780c6894c51aac8bd6011a |
| source-reference-stock.mjs | 91,327 | c62237c29a2e32fd1c09653512903e0019af4c9c59cef1e510e2f129c5f32bb1 |

**The release module is curated data, not source-only custody.** Do not upload it, original blobs, query indexes, or blanket build directories to the source-only GitHub branch. `source-artifact-manifest.json` is the explicit source/test/safe-metadata selection.

The API separately verifies the new production manifest, receipt and notices. Old local-only metadata fails closed. Only exact owned origin, matching optional Origin header, GET/HEAD and strict queries are accepted. There is no wildcard CORS, request/header rewriting, arbitrary-blob endpoint, private-profile route or provider fallback.

The three public paths are `/api/corpus/foundation`, `/api/corpus/foundation/notices`, and `/api/corpus/foundation/release`.

**Mount the API on outer `worker.mjs`, not only the contained app:** the existing outer guard otherwise authenticates `/api/*` before delegation. `patch-owned-foundation-route.mjs` adds only an import/default wrapper; these three exact paths dispatch first, and every other path retains the old guards/handlers. Verified synchronized outer output: 4,604,740 bytes, `7cef6c38c9a35e4b94d5e7d7d25702a04d64abf35a8497fbd6f91be848f0eabd`, from exact `40dad9d5…` preimage. Inner synchronized app remains unchanged.

`browser-source/` is the separately pinned complete source tree for the existing builder. Logical two-file selection/binding delta: `production-foundation-selection.patch`; five build-copy locations: `production-browser-source-delta.json`. Strict validators are unchanged.

## Existing Demo scanner — not a replacement

`patch-existing-guest.mjs` operates only on exact current guest `bab01e0e…`:
1. Prepend the source-only foundation adapter.
2. Replace its one inventory provider factory.
3. Add a foundation-specific readout hook with existing source-choice controls.

All other bytes, including original camera/decoder, audio/voice timeout, capture, queue and Finish functions, are retained. The adapter reuses the strict foundation client and the existing typed-identifier analyzer. Original lexical values and explicitly qualified representation aliases stay separate; no product equivalence is inferred.

Output `private-release-build/guest/full-scanner.js`: 907,183 bytes, SHA-256 `484e302e75e11521ebeb98299f7138883eea046357f42f6927f82f82d26c7e67`. The coordinator must replace only the existing `/demo/full-scanner.js` payload/descriptor; do not mount the older recovered guest bundle wholesale.

The existing guest Finish retains its in-tab list and does not persist pantry stock, infer package amounts or access private profiles. This existing behavior is preserved, not misrepresented as authenticated inventory mutation.

## Focused evidence

- 6 actual release/API/scanner/reference tests pass: OFF/USDA paging, source notices, strict selection, manual/unknown quantity, old-local-scope rejection, and private stock PUT→GET with auth/D1 mocks.
- 5 original server tests pass with the production binding, preserving legacy stock, auth, origin/revision checks and `OWN_DATA_REQUIRED`.
- 3 outer-worker tests pass: anonymous exact public routes work; all tested private/unknown/suffix routes retain original responses; no external calls.
- 5 existing-guest tests pass: exact manual-submit→capture handler reaches the anonymous outer API as primary provider; explicit source choice and truthful readout work; leading-zero aliases survive; Finish stays local; original audio/camera/Finish bytes remain exact.

The guest test runs exact UI handler source in a bounded DOM-stub harness, not a live camera/audio device or visual browser session. Final current-module composition, deployment/read-back and production review remain coordinator-owned. Tests accept `OFFMENU_TEST_WORKER` or `OFFMENU_TEST_APPLICATION` to exercise the final composed modules without changing their code.
