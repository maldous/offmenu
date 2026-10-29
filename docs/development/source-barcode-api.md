# Source barcode API request budget

UIF-94 corrects a finite index deadline that could reject a valid pinned response
before the scanner's own 40-second request budget elapsed. The index now has one
absolute 30-second deadline across manifest, shard fetch, SHA verification,
stream parsing and response validation. Caller cancellation still aborts it
immediately. There is no retry, alternative source, cache, larger data limit,
identity promotion or change to the existing facts hydration budget.

## Source and deployment boundary

Base: `eca287b36b8b2027e9d32aa4899ffb204563236c` (`develop`).
Branch: `bugfix/source-index-deadline-budget`.

The eight source files under `apps/web/server/source-barcode-api/` recover the
qualified source closure of the separately composed production 207 endpoint.
Seven remain byte-exact. The only semantic change to recovered source is
`deadlineMs:10000` to `deadlineMs:30000` in `source-barcode-handler.mjs`.
The exact custody mapping and original/current hashes are recorded in
`source-barcode-api-provenance.json`. No private packets or populated datasets
are included.

The canonical application build and the deployed modular application currently
have different source closures. This component is not added to the canonical
dispatcher here. Build its replacement module with:

```sh
node scripts/build_source_barcode_api.mjs
```

It writes the standalone ESM endpoint bundle and build metadata under ignored
`.delivery/source-barcode-api/`. The public factory and nine named exports match
the accepted 207 module. Only the existing integration publisher may reconcile
the active module hash and replace `source-barcode-handler-205.mjs` while
preserving the fixed selection, dispatcher, bindings, auth, scanner and other
modules. A whole normal app build is not an appropriate production replacement.
No deployment occurs from this build command.

## Acceptance evidence

The valid 18-second pinned-input regression fails on original 207 source:
HTTP503, `index-unavailable`, `manifest-fetch`, `cancelled-or-deadline`.
With the correction, all 15 focused checks pass:

```sh
node --test --test-isolation=none tests/edge/source-barcode-index-budget.test.mjs tests/edge/source-barcode-facts-api.test.mjs
```

They preserve candidate-only response parity, exact source/citation/asset
verification, zero/unknown values, ambiguity, scoped misses, complete stream
boundaries, finite expiry and cancellation. A 33-second cumulative index delay
still fails without claiming absence. A noncooperative fetch expires without a
duplicate request. These tests use explicit synthetic fixtures and fake clocks.
The normal app build, repository check and final-layout check also pass.

A separate local workerd replay used the exact historical 207 compiled module
and the approved retained manifest plus one SHA-verified shard. Without induced
latency, it returned HTTP200 and one candidate. With a controlled 9.8-second local
manifest delay, the original module failed at shard-stream with deadline after
10.059 seconds. The corrected module returned HTTP200 and one candidate under
the identical delay in 11.042 seconds, using the same two local asset reads.
This isolates the deadline behavior in the Worker runtime; it is
not a reconstruction of the historical live failure or a throughput benchmark.
Runtime receipts and source data remain private under `.delivery/`.

The historical scanner failure logs contain one 503 and one 200 corpus request but
omit source queries and response bodies. Its exact cause remains unproven.
Independent source review, integration, production served-content reconciliation
and actual scanner acceptance are still required before declaring UIF-93 fixed.
