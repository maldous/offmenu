# offmenu

Local barcode inventory → ingredient requirements → meal options → retailer price observations.
Python 3.10+ and SQLite; no runtime dependencies or network required. Run commands from this directory.

## Quick start

```bash
python3 -m offmenu init
python3 -m offmenu import-products examples/products.jsonl
python3 -m offmenu import-recipes examples/recipes.json
python3 -m offmenu map 0000000000001 'coconut milk'
python3 -m offmenu map 0000000000002 rice
python3 -m offmenu add 0000000000001 400 ml
python3 -m offmenu add 0000000000002 1000 g
python3 -m offmenu inventory
python3 -m offmenu meals --servings 2
```

The authored demo reports water as missing until tracked. No staples are silently assumed available. Example barcodes are fictional. Barcode scanners that type into a terminal can supply codes; the web interface also supports camera scanning where the browser provides BarcodeDetector.

Use `--db /path/to/database.sqlite` before a command to select another database.
`add` creates a lot; `remove INVENTORY_ID` removes one. Re-add remaining quantity after consumption. `--expires YYYY-MM-DD` excludes older lots from matching; this is inventory bookkeeping, not a food safety assessment.

## Data sources

- Products: https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz
  `python3 -m offmenu import-products /path/products.jsonl.gz --country en:australia`
  Streams JSONL/gzip; preserves string barcodes and existing ingredient mappings. Country filtering depends on supplied tags and is not exhaustive coverage of products sold in Australia. No photos downloaded. OFF database: ODbL; contents: DbCL.
- Recipes: `import-recipes` accepts the offmenu JSON array schema shown in examples/recipes.json, including source and licence provenance. Ingredients use explicit canonical names, quantity and unit (`g`, `ml`, `count`). Missing quantities remain unresolved. This is not yet a direct Wikibooks/RecipeNLG importer.
- Wikibooks candidate: https://huggingface.co/datasets/gossminn/wikibooks-cookbook (CC BY-SA 4.0). Adapter and ingredient parsing are next steps.
- RecipeNLG: https://recipenlg.cs.put.poznan.pl/ — non-commercial research/education terms; not bundled.
- Open Prices: https://github.com/openfoodfacts/open-prices/blob/main/docs/guides/data.md
  `python3 -m offmenu import-prices /path/prices.jsonl.gz`
  Requires product_code, price, currency, date; flattened retailer/location metadata is optional. Raw dumps without joined locations display Unknown retailer. Imports append observations, so repeated imports currently duplicate entries. `python3 -m offmenu shops BARCODE` returns dated observations, never current stock. Dataset ODbL. Australian coverage unmeasured.
- WhichGrocer: https://www.whichgrocer.com/developers — future optional backend connector. No credentials, calls or paid accounts configured. Cache/retention restrictions apply; no store-level stock guarantee.

## Matching contract

Map the culinary identity of a product, not the ingredients inside it. Chocolate containing milk does not satisfy milk. Exact normalized ingredient names only; no automatic substitutes or unit/density conversions. Quantities are pooled across unexpired lots. Repeated requirements are summed before matching. Servings scale requirements. Results are ready, missing, or needs_review. Separate meal options may use the same inventory; multi-meal allocation is not implemented. Unmapped lots appear in inventory and cannot satisfy recipes.

## Verification

```bash
python3 -m unittest discover -s tests -v
```

## Next implementation steps

1. Wikibooks adapter with preserved attribution and original ingredient text.
2. Ingredient aliases, product mapping suggestions and a review workflow.
3. Manual produce/staples entries, consumption updates and recipe detail display.
4. Idempotent Open Prices import and joined locations; measure Australian coverage.
5. Verify WhichGrocer GTIN support and terms before adding an optional connector.
6. Camera scanning and a local UI, then indexed/block-compressed deployment measurements.

A source archive can be compressed for distribution; the active SQLite database is not presented as a compressed random-access implementation. No full external dataset has been downloaded.

## Phone interface and camera scanning

```bash
python3 -m offmenu.server
```

Open http://localhost:8765 on the host computer. The mobile layout includes camera barcode detection, manual entry, product lookup, ingredient mapping, inventory quantities, meal suggestions and historical shop observations. Camera frames stay in the browser; only the decoded barcode is sent to this local backend. Browser-native BarcodeDetector support is checked at runtime. Unsupported browsers fall back to manual entry (bundled cross-browser decoder is a future step).

For a phone on the same Wi-Fi, serve HTTPS with a certificate trusted by the phone and valid for your host's LAN address/name:

```bash
python3 -m offmenu.server --host 0.0.0.0 --cert /path/certificate.pem --key /path/private-key.pem
```

Open https://YOUR-HOST-LAN-ADDRESS:8765. Configure your local development certificate authority on the phone or use a trusted HTTPS reverse proxy. Plain http://LAN-IP camera access will not work. HTTPS trust/proxy setup is not configured automatically. Do not expose this prototype to the public internet: there is no login yet. On an Android development device, USB ADB port reversal is another option:

```bash
adb reverse tcp:8765 tcp:8765
# Open http://localhost:8765 in the phone browser.
```

The phone UI requires connectivity to the host backend; it is not yet a standalone offline phone app/PWA. No browser or physical-camera verification has been performed in this environment.

## Public app (Cloudflare)

https://offmenu.aldous.info

The Cloudflare Worker serves the mobile app and uses the `offmenu-users` D1 database for:
- Private per-account pantry snapshots, product mappings/cache, profile, serving settings, imported recipes and selected meals.
- Shared product lookup records, dated price observations and recipe catalogue records.

Public product/price records retain source and licence. The catalogue is populated on barcode lookups; this is not a full downloaded OFF or Open Prices mirror. The starter catalogue contains an authored demonstration recipe. Bulk recipe adapters and retailer availability feeds remain future work.

Netlify Identity project: `offmenu-accounts`. Identity is enabled in https://app.netlify.com/projects/offmenu-accounts/identity with managed Google sign-in, open registration and required email confirmation. A fixed callback landing page in `netlify-return/` returns the Identity fragment to the public app for SDK handling. Live verification reached Google’s account chooser; first user sign-in and end-to-end cross-browser cloud restoration remain outstanding. The Worker proxies the documented Identity endpoints; it verifies tokens through the upstream `/user` endpoint before selecting private records. No user ID supplied by the browser selects another user's data.

Select a preferred country (global by default). Shop observations are filtered using the shop's reported country; unknown-country rows are excluded when a country is selected. Results cover only the latest 30 observations for the barcode. Recipe quantities currently remain metric even if imperial is selected. Country is never inferred from IP or identity.

Guest data and each account's browser copy use separate keys. Signing in restores the cloud copy unless that browser has unsaved account changes. **Save to cloud** is explicit; new edits are local until saved. Saving uses atomic revision checks. A conflict requires exporting local changes then loading the newer copy. This initial version does not auto-merge concurrent edits.

Build and verify:
```bash
npm ci
npm run build
npm test
python3 -m unittest discover -s tests -v
```

Deployment uses Cloudflare MCP with module upload, D1 binding `DB`, compatibility date `2026-10-12` and custom domain `offmenu.aldous.info`. Account `7edd51038e07b5b84a635b3ff7e11144`; database `006cbdd6-6be8-4181-9dd5-519de280b6ef`. No credentials belong in this repository. Schema is in `cloud/schema.sql`. Camera permission and physical scanning must still be tested on a phone.

Licensed catalogue imports can be prepared with `python3 scripts/catalogue-sql.py products products.jsonl.gz --country en:australia > products.sql`, or `python3 scripts/catalogue-sql.py recipes recipes.json > recipes.sql`. Apply SQL through Cloudflare MCP/D1. Bulk records must fit the chosen database capacity; no full dump has been imported.


## Home checkout layout (October 2026)

The public landing page introduces shelf-by-shelf inventory and includes a separate interactive demo. The app has Checkout, My shelves and Meal ideas tabs, with account/profile/backup controls in a dialog. Enabled identity providers appear as branded buttons (Google uses the multicolour G).

Checkout modes:
- **Rebuild a shelf:** choose Pantry, Fridge or Freezer and a shelf name. Empty that shelf onto the bench. Scan and confirm each product; the receipt stages items without modifying existing inventory. The finish dialog shows how many existing items will be replaced on this exact shelf.
- **Unpack shopping:** scan new groceries for one destination shelf, then add them while keeping its existing inventory.

Drafts remain in the current browser/account namespace and can resume after reopening checkout. Finishing retains area, shelf and check-in time on each lot, including in cloud snapshots and exported backups. Old inventory remains Unassigned until reshelved. Shelf drafts are local; finished inventory uses the existing explicit cloud save.

Register feedback uses Web Audio after the user enables sound; it can be muted and visual feedback remains. Nutrition widgets use available Open Food Facts per-100-g/ml values and show unknowns explicitly. Demo foods and nutritional figures are clearly illustrative and stored in a separate demo namespace. Emptying a recorded shelf without checking in any items is blocked.

Physical phone-camera operation and audible speaker output still require device testing. The layout includes narrow-screen CSS and reduced-motion support.

The checkout scanner prefers the front camera (`facingMode: user`) for screen-up bench scanning. Browsers may choose another camera if a front camera is unavailable. Physical focusing distance depends on the phone.


## Continuous register scanning

The front-camera decoder stays open between products. Each newly presented barcode is immediately accepted as a staged receipt line, with background product lookup and duplicate-frame suppression. Move a barcode out of view for about a second before presenting a second identical package. No per-product accept action is needed. Void last item or void a receipt line to undo. Finish shows a receipt with optional corrections and a single final confirmation. Labelled full-pack amounts are assumed; unknown amounts stay as one package. New unconfirmed ingredient suggestions are excluded from meal matching until corrected in the final receipt.

The final receipt is saved in the profile and can be reopened, printed or saved as a PDF using the browser's print dialog. It retains Unicode product names. Print CSS removes action controls and uses an A5 receipt layout. Receipt and feedback preferences are included in cloud backups.

Scan feedback settings offer sound, vibration, a gentle screen glow, camera light (only on a supported camera track), and spoken product names. Controls have large tap targets (56px minimum, primary mobile actions 64–76px), with labelled feedback toggles. All sensory feedback is optional. Vibration/light/speech depend on browser and device capability and must be verified physically.

## Menus and weekly planning

Menus lead the app navigation, alongside My week, Kitchen and Checkout. Browse the whole kitchen or one storage location; search dishes/ingredients and filter readiness. Cards show measured quantities scaled to the selected portions, original ingredient wording, directions, source/licence, matching shelves and estimated food data. The initial collection includes 39 Wikibooks recipes adapted from Gosse Minnema's July 2024 CC BY-SA 4.0 dataset, plus the authored demonstration. Source attribution and original text are retained; unspecified quantities remain unresolved.

Add menus to Breakfast, Lunch, Dinner or Snack on the selected date. My week groups them by date, with daily/weekly ingredient totals, shared-stock shopping gaps and nutrient estimates for all planned portions. Estimates use the first matching mapped product with a compatible g/ml basis. Missing values are excluded and partial coverage is reported; no density conversions are invented. Menu plans are saved in the profile and included in cloud snapshots. Meal matching excludes unconfirmed product-to-ingredient mappings. Statistics describe the plan, not confirmed consumption.


## Household and document workspace

Storage areas and containers are free-form (e.g. Bench / Bowl). Manage and rename locations from Kitchen; stock follows the renamed location. A checkout can also create a location by entering its area and container.

Household profiles store optional age/height/weight, explicit portion factors, avoided ingredients and dietary-advisor preferences. Rules screen known ingredient conflicts and suggest omitting optional ingredients. Shared-menu generation prefers one household dish; if none matches, it proposes member-specific dishes. Unknown recipe identification and package restrictions remain review items. Higher-protein/lower-carbohydrate/weight-management scoring uses complete available nutrient estimates, with adult weight-loss scoring disabled for under-18s. Body metrics do not currently prescribe calories or portion targets; users choose portions.

Meal planning can deduct existing pantry ingredients or produce a complete shopping list. Single-missing-ingredient suggestions identify measured recipes that additional purchases could unlock. Meal-duration coverage is a greedy lower-bound estimate over the quantified catalogue, allows repeats, consumes stock once, and is not a globally optimised maximum or proof of nutritional completeness.

Documents offers inventory, latest receipt, household preferences, shopping lists and a planned-menu/recipe booklet. Download responsive HTML or a reflowable EPUB for Send to Kindle; browser print gives PDF or paper. EPUB packaging uses an uncompressed mimetype first and validated CRC/XML.

Google health connection is pending: Google's October 2026 documentation says Google Health API is not onboarding new projects. Health Connect requires Android-side SDK integration. No health scopes are requested by ordinary Netlify/Google login. Manual profiles remain operational.

## Food observatory, after-meal records and cleanup

Statistics has 7/30/90/365-day views, per-member filtering, 12 nutrients, daily bars, user-entered daily targets or ceilings, meal detail snapshots and CSV history. Logging a recipe stores frozen nutrition estimates; missing fields remain unknown. Sodium is label sodium in grams ×1000 mg, otherwise salt in grams ×400 mg. OFF mineral values in grams are converted to mg. Optional eaten percentage scales recipe nutrition, including a valid 0% record. Custom label entries are already-consumed totals and are not scaled again. Saved / discarded / shared leftovers are contextual records. Logs do not automatically deduct inventory. Separate member/household logs of the same food would double count: the UI explains this.

Garbage checkout automatically stages matching stock IDs from the chosen source area/container. Its receipt supports partial removal quantities, retains other locations, and refuses changed source quantities. Confirmed cleanup receipts are retained in profile.waste. Voiding staged items changes no inventory. Label use-by dates and user-confirmed estimated check reminders are distinct; generic 7-day fruit / 14-day drink suggestions are examples, not shelf-life claims. Chosen intervals can be suggested again for the same barcode. No model infers safe consumption or automatically discards food.

Shopping & apps provides a shared-week checklist, manual extras, collected flags, Web Share / clipboard, CSV and Schema.org ItemList JSON-LD. Recipe exports use Recipe / HowToStep JSON-LD with source/licence. Reports include dietary history, completion, nutrient coverage, chosen goals, waste and freshness, in printable HTML / EPUB. Print uses the browser PDF destination. The trophy shelf recognises organisation, variety and participation, never calorie restriction or weight loss.

The provider directory distinguishes active OFF / Open Prices lookups, external ALDI catalogue and DoorDash delivery links, and access-required adapters. WhichGrocer requires an issued backend key and attribution; catalogue prices are retailer-wide, not local availability. DoorDash Marketplace retail APIs are approved merchant integrations. Instacart shoppable links require a Developer Platform API key. USDA FoodData Central needs a data.gov key. No keys or onboarding approvals exist for these providers here, so none is shown as connected. Google Health is not onboarding new projects as of 2026-10-12; Health Connect / HealthKit require native bridges. FHIR interoperability remains future work.

## Third-party REST API and remote MCP

Cloudflare hosts both interfaces, with D1-backed per-user delegated credentials. Netlify Identity authenticates the owner at token management and OAuth consent, not at third-party resource calls. Save local changes to cloud first; external callers read the saved snapshot.

- MCP endpoint: `https://offmenu.aldous.info/mcp` (stateless Streamable HTTP, POST JSON responses; no SSE session).
- REST base: `https://offmenu.aldous.info/api/v1` with GET `/inventory`, `/plans`, `/history`, `/directory`.
- OpenAPI 3.1: `/openapi.json`.
- Scopes: `inventory:read`, `plans:read`, `history:read`, `directory:read`. Dietary history includes consumed-food snapshots and completion; cleanup is separately named within the history response. Directory returns saved recipes / locations and excludes household body metrics.
- MCP tools: `get_inventory`, `get_meal_plan`, `get_food_history`, `get_directory`. Tool lists are filtered to granted scopes.
- Plans / history accept inclusive `from` / `to` YYYY-MM-DD filters. Responses contain version, saved revision and update timestamp.
- Personal bearer tokens: create in Shopping & apps, signed-in owner only; select REST or MCP audience, scopes and connection name. Raw secret shown once, SHA-256 hash stored in D1, 30-day expiry, owner-bound revocation. Never include a token in a URL.
- OAuth: protected-resource metadata at `/.well-known/oauth-protected-resource/mcp` and `/api/v1`; authorization-server metadata at `/.well-known/oauth-authorization-server`; dynamic public client registration `/oauth/register`; authorization `/oauth/authorize`; token `/oauth/token`; revocation `/oauth/revoke`. Registered exact redirect, S256 PKCE, resource-bound tokens, one-time five-minute code, explicit owner consent. Access tokens expire after 24 hours; refresh tokens and client metadata URL registration are not offered. Reauthorise when expired.
- Third-party REST requests have token-only CORS. MCP browser Origin checks accept this site's origin; server/desktop clients without Origin work. Cookies alone cannot read either resource interface.
- OAuth registration and token endpoints have per-IP hourly limits. Active personal connections are capped at 50 per user. Grant management and consent POSTs require same-origin plus a verified owner session.

Example REST request (secret supplied locally):

```sh
curl -H "Authorization: Bearer $OFFMENU_TOKEN" https://offmenu.aldous.info/api/v1/inventory
```

MCP client configuration for clients supporting bearer headers:

```json
{"mcpServers":{"offmenu":{"url":"https://offmenu.aldous.info/mcp","headers":{"Authorization":"Bearer YOUR_MCP_AUDIENCE_TOKEN"}}}}
```

OAuth-capable connectors can discover and register against the metadata endpoints. End-to-end third-party client certification / live Google consent were not performed; automated tests exercise issuance, user isolation, scopes, audience, expiry, revocation, PKCE and code replay. These interfaces currently offer read-only access; external writes and notifications are not exposed.

## Global data and bring-your-own credentials (2026-10-12)

The global source directory has 48 entries and defaults to every country. Public barcode/price feeds and open nutrition data do not require a user's provider credentials. The selected account's country is an optional filter; no IP-based or implicit regional restriction is applied in the new data browser. Major-country coverage is explicit for China, India, England/UK, France, Germany, Indonesia and Russia. Source presence is not a claim of complete national coverage or permission to redistribute.

Verified, normalized shared nutrition tables:

| Source | Profiles | Rights |
|---|---:|---|
| UK CoFID 2021 | 2,887 | OGL3; original definitions/notes preserved |
| ANSES CIQUAL 2025 | 3,484 | Etalab Licence Ouverte2.0; French/English names |
| Germany BLS4.0 | 7,140 | CC BY4.0; German/English names and nutrient origins/references |

All 13,511 source profiles were imported to source-partitioned public rows in D1. `scripts/import-national-tables.py` reproduces the ingestion from the official XLSX releases. It retains all provided nutrient columns, explicit units, source calculation methods and measurement qualifiers; `Tr`, not-detected, not-tested, `N`, censored `<…` and zero are distinct. CoFID alcoholic beverages retain per100ml basis, others per100g; fatty-acid bases are explicit. A duplicate CoFID food code is disambiguated with the food-name hash and joins use `(code,name)` to preserve both foods. Gzip record storage reduces repetitive source metadata; API consumers receive regular unified JSON. Source data is not relicensed as proprietary.

Official reproducible workbook URLs:

- CIQUAL FR: `https://entrepot.recherche.data.gouv.fr/api/access/datafile/666260`
- CIQUAL EN: `https://zenodo.org/api/records/17550133/files/Table%20Ciqual%202025_ENG_2025_11_03.xlsx/content`
- BLS full release: `https://blsdb.de/assets/uploads/BLS_4_0_2025_DE.zip`
- CoFID: `https://assets.publishing.service.gov.uk/media/60538b91e90e07527df82ae4/McCance_Widdowsons_Composition_of_Foods_Integrated_Dataset_2021..xlsx`

India IFCT electronic product reuse requires written NIN permission. Chinese CDC, Indonesian TKPI and Russian composition sources remain permission/access-review directory entries. GS1 DataKart / Russia API access requires the user's approved membership/account. Freely viewable documents are not assumed to permit commercial ingestion. The newer Quadram CoFID APIs have different, noncommercial terms and are not used instead of the GOV.UK workbook.

The versioned offmenu schema defines product, nutrientProfile, priceObservation, retailer, recipe, foodClassification, foodNotice, pantryLot, mealPlan, intakeRecord, shoppingList, healthObservation, activity and wasteRecord. Identifiers retain strings and namespaces; UTF-8 names and BCP47 languages are retained. Nutrition includes explicit amount/basis/state/unit/method/qualifier; prices retain currency/time/location/type/availability. Provenance carries source, original identity, licence, attribution, retrieval/source date, transformation and privacy. Schema ownership does not override source licensing or sharing obligations.

- Public source registry `/api/data/sources`, conventions `/api/data/schema`, actual shared counts `/api/data/coverage`.
- Public normalized lookup `/api/data/public?source=...&query=...` (OFF/Open Prices require barcode). National tables return a sample of up to20 profiles. All public data remains accessible without login. Legacy barcode responses now include `offmenu.records` without breaking old product consumers.
- Own connections `/api/data/connections`: verified account plus same-origin writes. Each credential is encrypted with AES-GCM, using a Cloudflare secret and user+provider-bound authenticated data. Lists return metadata, never keys. Owner can replace/remove their own configuration. Store secrets only in this vault, never profile backups or browser localStorage.
- Own API lookup `/api/data/lookup` currently supports USDA FoodData Central (own apiKey) and Edamam Food Database (own appId/appKey). Outputs are private and are not automatically cached. Plan rights govern storage/export. WhichGrocer, Spoonacular and Instacart keys can be configured with an explicit adapter-pending label. Other OAuth/partner/native services remain access workflows rather than fictitious live connections.
- User import `/api/data/records`: unified JSON, OFF or USDA JSON, CSV mapping to foods/nutrients/prices; authenticated records are private in D1. Guests/demos have bounded account-separated browser storage. The UI requires confirmation of storage/export rights and never turns private provider results into the public index.
- Personal normalized records can be read via REST `/api/v1/data` and MCP `get_unified_records` with `data:read`. These interfaces exclude provider credentials.
- Inventory enrichment is explicit: choose a matching item and verify identity/preparation/basis. The selected data replaces that barcode's current nutrient estimate; prior food-history snapshots stay unchanged.

The downloadable desktop Chromium extension preview uses only `activeTab` + `scripting`. It extracts allowlisted schema.org Product/Offer fields from the user-selected page, keeps retailer domains/SKUs distinct and strips page query/fragment. Passwords, cookies and payment details are not read or exported. Review is required before downloading a private import file. Retailer sign-in and checkout remain in the retailer's own interface. Store publication and live retailer validation are pending; not all pages publish structured data or personalized prices in JSON-LD.

Deployment **must preserve the vault secret**: use multipart metadata `keep_bindings:["secret_text"]` with the D1 binding. Do not regenerate `PROVIDER_VAULT_KEY` after user credentials exist; rotation needs decrypt/re-encrypt migration. Request query strings are redacted from observability; upstream key-bearing URLs are never returned in error responses.


## Product review checkpoint
See [implementation status and remaining validation gates](docs/product-review-status.md) for the dinner journey, cooking accounting, shared kitchen and request-reduction release.

## Worldwide recipes

The shared recipe library is acquired from licensed Wikibooks cookbook pages, pinned GitHub recipe collections, UniTools and documented historical/Smithsonian editions. The checked release has 23,661 source recipes plus 256 historical OCR candidates across 30 language editions/codes (including Simple English separately). Recipe wording, source quantities, unknown measurements, directions, revision, attribution and per-record rights are retained. It is not complete worldwide coverage or independently reviewed dietary advice.

In the kitchen, open **Today → Worldwide recipe library → Open worldwide recipes**. Search dishes or ingredients, choose a language, compare compatible source-batch quantities with usable pantry lots locally, and read source instructions. Explicitly review ingredients, measurements, servings and scaling before saving a personal kitchen recipe. Public recipes remain unreviewed; historical OCR and nonstandard measures require correction.

Public dataset: [manifest](https://offmenu-corpus.netlify.app/recipes/manifest.json), [JSONL gzip](https://offmenu-corpus.netlify.app/releases/world-recipes-20261014/recipes.jsonl.gz), [Schema.org JSON-LD gzip](https://offmenu-corpus.netlify.app/releases/world-recipes-20261014/recipes.schemaorg.jsonld.gz), [recipe schema](https://offmenu-corpus.netlify.app/recipes/schema.json). Per-record licences apply; preserve attribution and CC BY-SA share-alike. Ingredient-indexed REST example: `/api/data/public?source=world-recipes&query=rice`. Research and exclusions: `docs/world-recipe-research-20261014.json`. Full acquired originals and unresolved candidates stay in the local data directory.

Recipe extraction tests require the declared test extras: `uv pip install --python .venv/bin/python -e ".[test]"`, then `.venv/bin/python -m unittest discover -s tests`. Acquisition requires the collection extras.


### Common corpus acquisition contract (14 October 2026)

Current acquisition is aligned to [the common data contract](corpus/common-data-contract.json), [JSON Schema](corpus/common-data.schema.json) and [whole-corpus source mappings](corpus/common-source-mappings.json). Every new source must retain its citations, original measurement notation, language and cultural representation, map its fields and relations, and propose additional types when required. Stable shared identities are separate from localizable labels, source variants and reviewable candidate joins.

The data package contains 25,135 recipe records (24,879 source recipes and 256 partial historical OCR candidates), 29,255 FoodOn classes, shared ingredient terminology and source-published bilingual instructions. Thirty-two publisher language/edition codes include 31 languages plus Simple English. Mappings cover all 20 collected sources; fully aligned packets currently cover recipes, terminology and FoodOn. No worldwide completeness, reviewed recipe synthesis or completed universal translation is claimed.

The [data handoff](docs/I18N_DATA_HANDOFF.json) identifies immutable package files and the implementation owner. The other OffMenu i18n task owns application realization. Acquisition tools and declarative contracts in this checkpoint do not migrate the application. Published entry points: [common data](https://offmenu-corpus.netlify.app/common-data/manifest.json) and [recipe library](https://offmenu-corpus.netlify.app/recipes/manifest.json). Per-citation rights apply.
