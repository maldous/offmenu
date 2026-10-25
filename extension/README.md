# offmenu retailer companion (preview)

Build from the repository root with `npm run build`. It regenerates the tracked `extension/popup.js` from `extension/popup-source.js` and writes `dist/retailer-extension.zip`. Review any generated diff. Install the repository's `extension/` directory as an unpacked extension in desktop Chrome / Chromium Developer mode; the archive contains the same extension files under `offmenu-retailer-extension/`. Store publication and end-to-end retailer testing are pending.

1. Sign in to your retailer directly in your own browser.
2. Open a product page and invoke the extension.
3. Read the page, review names / identifiers / prices / currencies and confirm the source terms.
4. Download the JSON. In offmenu, choose Shopping & apps → Bring your files → original source “Your retailer browser session”, import, review and save privately.
5. Use offmenu's shared shopping list. Perform cart and purchase confirmation directly at the retailer.

Only activeTab and scripting permissions are requested. No persistent retailer host permissions, password / cookie / payment access, retailer API emulation or automated purchasing are implemented. Structured JSON-LD can be absent, stale or different from the price visible to a signed-in user; review is mandatory. Imported amounts do not establish verified live stock. Retailer reuse terms still apply.
