# Review a retailer product page in OffMenu

The **retailer companion** is a desktop Chromium extension preview. Use it to review structured product or price observations from a product page you choose and, when permitted, download a file for private import. It does not add to a cart, place an order or mark shopping as received. It is not a live stock or price guarantee.

## From product page to private import

1. Open an HTTPS product page in **your own** retailer browser session. Sign in directly with the retailer if needed; do not enter retailer passwords into OffMenu. Open the companion on that tab.
2. Choose **Read selected product page**. Check the status and every displayed product name, barcode or retailer SKU, price, currency and availability against the page you intended to read. The preview reads structured product metadata, not the visible shelf or checkout price. A product can have identifiers but no priced offer; missing currency is not a known currency.
3. Check **I reviewed the product, price, currency and source terms.** only if those observations match and you are permitted to retain them. **Download private import JSON** saves `offmenu-retailer-import.json` to your device. Checking the box alone does not download, import or publish anything.
4. Choose **Open offmenu to import / plan shopping**, or return to your own OffMenu kitchen. This opens OffMenu; it does **not** transfer or save the downloaded file. In the kitchen’s **Data** tab, find **Bring your files, too**. Select the correct original source (**Your retailer browser session**) and choose the JSON file. Read the normalization status and review the records before deciding whether to save them. See the [data import guide](https://github.com/maldous/offmenu/blob/de5fdc7d1ab65d061cfacb3065913c840c191b2c/docs/data-import-guide.md); that guide also distinguishes guest/browser storage from signed-in profile storage.

### If the result is empty, stale or unexpected

- **No supported structured product data found:** there were no supported records to offer in this read. That does not mean the retailer has no products. If you have an authorized receipt or export, use the appropriate import route, or enter the information manually.
- **Unable to read this page:** check that the active tab is the intended HTTPS product page. Do not confirm or download cards left visible from a previous read; close and reopen the popup and obtain a new successful result. That failure status does not describe any records left on screen.
- **Download unavailable:** complete a successful read with at least one record, verify it, then confirm. If a retailer shows a different price, quantity or currency, do not treat the extraction as authoritative. Keep leading zeroes in barcodes. No action here records payment, updates stock or grants redistribution rights.

## What the preview reads

The published source declaration requests `activeTab` and `scripting`; it declares no persistent retailer host permissions. The action inspects structured JSON-LD product data on the selected tab. The source URL retained for provenance excludes the query and fragment, but the host, path, product and price observations can still be private. Keep the download private and honor the original source terms. The companion does not request retailer passwords, cookie access or payment details. Complete orders directly with the retailer.

## Repository and packaged versions

From the repository root, the declared `npm run build` entry point regenerates **`apps/retailer-extension/popup.js`** from **`apps/retailer-extension/popup-source.js`** and writes **`dist/retailer-extension.zip`**. Do not hand-edit the generated bundle. `npm run check:generated` compares its bytes with the configured esbuild output. This guide does not assert either command was run on this revision.

For an authorized development installation, the unpacked directory in a checkout is **`apps/retailer-extension/`**. In the built ZIP it is **`offmenu-retailer-extension/`**. Select the directory **containing `manifest.json`**, not its parent or a nonexistent root-level `extension/`. Installing an extension/using Developer mode needs the browser owner's permission. No installation or store release is implied.

**Scope and upkeep.** This guide is bound to [`de5fdc7d`](https://github.com/maldous/offmenu/tree/de5fdc7d1ab65d061cfacb3065913c840c191b2c/apps/retailer-extension). The four visible controls are the read button, review checkbox, download button and OffMenu link; generated review cards are informational. The source owner should recheck these instructions when popup controls, extraction, build paths or the kitchen import flow change. Browser installation, actual retailer behavior, keyboard/assistive use, rendering and store publication require their own evidence; no such acceptance is claimed here.
