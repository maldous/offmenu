# Exact server preservation of source-referenced stock

The actual current13bd server `W` validator reconstructed lots without retaining
foundation or native source references. Browser-only Finish was not sufficient:
real `/api/state` persistence dropped those references in inventory and receipts.

## Minimal implementation

- Canonical source helper: `source/cloud/source-reference-stock.mjs`, importing the
  same `public/model.js` used by the integrated browser. It accepts only native or
  foundation referenced lots and uses the unchanged strict reference validators.
- `source-reference-stock-entry.mjs` is the local assembly entry for that source;
  only its import path points at the exact separately assembled browser source.
- `source-reference-stock.mjs` is the self-contained new Worker module. Its build
  manifest lists16 exact source input hashes and esbuild0.25.12. No external import,
  provider call, raw dataset, token or credential is included.
- `patch-server-reference.mjs` inserts only one import plus a219-byte total dispatch
  change into exact current server module13bd. It calls the helper only when the
  lot has a foundation/native reference. Every byte of the original legacy `W`
  body is retained. It does not rebuild/replace `CA`, authentication, user or shared
  storage handlers, source containment, origin checks, revision checks or routing.

The immutable original module is2,220,629bytes,
SHA256 `13bd5e94c11ded5756a09edafc414791164425f4aca0b12b947849e1af60157a`.
The original top-level `W` function is1,894bytes,
SHA256 `a14ce8fc820500a31f8a1faca1c97ff55a70818ec188d03a27bc35573a0da5fe`.
The generated server-only candidate is2,220,848bytes,
SHA256 `01ee8a6152de32e43cc0b2dac833815a7eac5e8bd26ae2b0a7e1404659beedde`.

Production composition owns the separately pinned browser/HTML/CSS literal
replacements. Apply the server function dispatch to that exact module hash while
requiring the `W` preimage hash above. The two changes do not overlap. Add the new
helper Worker module without changing other current183 modules/resources.

## Truthful source and amount boundary

Actual identity selection remains null. The delivered helper therefore rejects
native references with SOURCE_IDENTITY_NOT_CONFIGURED; this is not an admission.
The same exact recovered foundation binding is shared with the browser source.
It is a historical source preimage, not permission to replace a current selected
R8/R9/all15/alias binding. Rebuild both browser and server from the same actually
selected source binding if the production composition changes that binding.

Configured references retain original rights/provenance, lexical strings,
explicit unknown fields and false qualification/normalization flags. Private
stock requires a positive manually recorded amount. Staging data does not become
a normalized ingredient or a phase record. Existing unreferenced stock follows
the original server validator byte-for-byte. The localhost-only source-identity
HTTP adapter is not activated or widened by this stock persistence helper.

## Focused evidence

`server-reference-save.test.mjs`:5tests passed, recorded in
`server-reference-save-tests.log`.

The tests execute the actual original and patched Worker `fetch` entrypoint. An
isolated in-memory D1 mock and mocked Identity response are the only substitutes;
no provider/network/database operation occurs. Synthetic pins exist only in a
disposable source copy, never in delivered selection or admission files.

1. Original actual server demonstrably drops refs; configured patched PUT→GET→PUT
   preserves full native refs in inventory, lastReceipt and waste items.
2. Distinct phase references and exact native one-character/leading-zero identifiers
   survive actual save/reload without identifier coercion.
3. Actual null selection fails closed; unknown/package amounts, changed rights,
   invented English/type/normalization or mixed reference types do not write.
4. Legacy saved state is identical; authentication401, origin403, revision409 and
   OWN_DATA_REQUIRED503 containment remain effective.
5. Exact module/function preimages are enforced; duplicate patching is rejected;
   the outside-two-insertions invariant is checked.

These focused mocked save-path tests are not a live production acceptance or an
actual source admission. No Actions, deployment or production mutation occurred.

## Authored markup correspondence

The exact d626 `public/index.html` and `public/style.css` at sibling source assembly
`supplemental/foundation-*` are the intended paired authored replacement assets.
The HTML retains all408 current IDs and supplies all10 missing unconditional app
controls; the remaining5 missing static IDs are dynamically created. The exact
HTML/CSS pins and source provenance are in that assembly's
`foundation-supplemental-manifest.json`; no missing nodes were invented.

The same5 tests also passed against the fully composed app/browser/authored-markup
artifact d80ff41b23cada4c2686d0bc12a8aa69fd363ee0f898b452f5033029a8f86397
using `OFFMENU_TEST_APPLICATION`; both null/default and disposable configured test
loads used the combined module. See `composed-server-reference-save-tests.log`.
