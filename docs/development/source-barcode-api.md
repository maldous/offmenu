# Source barcode API request budget

The finite source-index request has one absolute 30-second deadline across
manifest/shard fetch, hash verification, stream parsing and response validation.
Caller cancellation aborts it immediately. This does not add an automatic retry,
alternative source, larger data limit, identity promotion or a different facts
hydration budget.

The component lives under `apps/web/server/source-barcode-api/`. Its source
provenance and file hashes are in [the product provenance record](source-barcode-api-provenance.json).
Historical identifiers in that record are provenance, not filesystem or service
requirements for a clean product checkout.

This standalone compatibility component is not automatically mounted in the
canonical application dispatcher. Build its ESM artifact with:

```sh
node scripts/build_source_barcode_api.mjs
```

The command prepares output and build metadata; it does not deploy. A selected
deployment must preserve its actual dispatcher, bindings, authentication, fixed
source selection and other modules. A whole application build is not a substitute
for qualification of a separately composed endpoint.

Focused source checks are:

```sh
node --test --test-isolation=none tests/edge/source-barcode-index-budget.test.mjs tests/edge/source-barcode-facts-api.test.mjs
```

The authored fixtures exercise finite expiry, cancellation, scoped misses,
ambiguity, zero/unknown values, exact selected assets/citations and complete
stream boundaries. They do not grant source-use rights, contact live data
providers or establish the cause of a historical production timeout. Preserve
those distinctions when interpreting a successful source build or test.
