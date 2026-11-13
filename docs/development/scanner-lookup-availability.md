# Scanner lookup availability

A failed lookup is different from a completed lookup without a qualified match.
When the selected lookup is unavailable, Category and Ingredient match say
**Lookup unavailable**. Qualified facts already loaded from a source remain
visible during incomplete coverage. A completed lookup without a qualified
mapping retains its unknown classification. Original barcode characters and
source qualification rules remain unchanged.

The maintained browser implementations are `apps/web/src/shelf-scanner.js` and
`apps/web/src/production-scanner/shelf-scanner.js`. The normal application build
uses the former; a separately composed deployment can have a different source
closure. Building the normal application is not permission to replace such a
deployment with an unrelated whole bundle.

The source regression uses authored/retained test inputs and distinguishes
lookup failure from absence. Focused checks are:

```sh
node --test --test-isolation=none tests/web/scanner-lookup-failure-state.test.mjs tests/web/production-scanner-queue-selection.test.mjs
```

Those checks establish the selected source behavior, not the cause of a past
live failure. Exact served assets, authenticated routing, browser layout,
physical camera and device behavior remain separate qualification. Do not use a
local pass to claim live source availability or complete product acceptance.

The [source barcode API](source-barcode-api.md) has its own request-budget and
cancellation behavior. Neither interface invents identity, nutrition, rights or
source facts when a lookup is incomplete.
