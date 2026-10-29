# Scanner lookup availability

UIF-93 separates source knowledge from a failed lookup. When the selected lookup
is unavailable, Category and Ingredient match say **Lookup unavailable**. A
qualified field already loaded from a source remains visible during incomplete
coverage. A completed lookup without a qualified mapping retains its existing
unknown classification. Original barcode characters and qualification rules are
unchanged.

## Qualified source change

Base: `eca287b36b8b2027e9d32aa4899ffb204563236c` (`develop`).
Candidate branch: `bugfix/scanner-known-source-facts`.

The maintained changes are the fallback labels in both
`apps/web/src/shelf-scanner.js` and
`apps/web/src/production-scanner/shelf-scanner.js`, their regression test, and the
generated English message inventory/coverage report. No API, auth, source-data,
inventory, nutrition or planning admission changes are part of this fix.

The normal repository build currently uses `apps/web/src/shelf-scanner.js`.
Production209 is separately composed and has additional source consumers.
Publishing the normal build over that deployment is not justified by this fix.
`scripts/patch_scanner_lookup_state.py` prepares exactly two label edits in each
preserved209 scanner asset, refusing different baseline bytes or nonunique
preimages. It writes private candidates and hashes beneath `.delivery/`; it does
not deploy or change the rest of the application graph. Reconcile the currently
served asset hashes before applying those candidates through the existing owner.

## Verification and limits

The regression test failed on both original maintained render functions and
passes after the label correction. The four affected source-selection/queue
checks also pass. Run:

```sh
node --test --test-isolation=none tests/web/scanner-lookup-failure-state.test.mjs tests/web/production-scanner-queue-selection.test.mjs
npm run build
```

An offline Chromium replay executed the entire preserved production209 public
bundle, SHA-256
`a7391197f0e5330e69e6baf07cd6d426d9b8d81ee1303f014585ee0221c07e9f`.
The exact retained successful facts response already rendered Champ iced coffee,
Farmdale and its source citation. A structured index503 reproduced the blank
name and misleading classification labels. This establishes the UI-state defect;
it does not establish the cause of the historical API503.

Both complete patched public/private bundles were then replayed in Chromium with
all requests fulfilled from retained/synthetic inputs or blocked. They preserve
the successful name/brand display and show Lookup unavailable for index503,
without JavaScript page errors. This replay uses the current repository scanner
HTML with three added feedback controls required by the209 scripts; exact live
HTML/layout, authenticated routing and physical camera acceptance are unverified.
Raw receipts and screenshots remain private, outside Git.

Historical Cloudflare metadata confirms one503 and one200 corpus request during
the failed209 scan, but omits query strings and response bodies. A retained,
SHA-verified manifest and selected index shard return one candidate through the
generic handler locally. The10000ms index deadline remains a hypothesis for
intermittent unavailability, not a demonstrated historical root cause. UIF-94
owns that separate API investigation. No deadline change or new live food lookup
is included here.

Source integration, production publication and served acceptance remain separate
steps owned by the existing integration publisher. Do not mark the original
scanner issue resolved solely from these local checks.
