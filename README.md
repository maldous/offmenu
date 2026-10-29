# OffMenu

## From product to pantry to plate

OffMenu is being built around an everyday household routine: understand an item, know what is in the kitchen, decide what to cook, record what people actually eat, and use that knowledge when planning and shopping again. It should help with one ingredient or one meal without requiring the whole kitchen to be catalogued first.

This README is the human-readable product North Star and delivery guide. It describes the intended connected experience, the foundations already in the repository, and what still needs to work together. **It is not a claim that the whole experience is available in the current app.**

[App](https://offmenu.aldous.info) · [Documentation](docs/README.md) · [Developer setup](docs/maintainer.md) · [Detailed delivery programme](docs/research-delivery-plan.md)

## The complete loop

**Barcode → Product → Ingredient → Recipe → Quantity → Nutrition → Menu → Serving → Consumption → Leftovers → History → Planning → Integration → Ordering → Receipt → Barcode**

There are fifteen distinct stages in three connected phases. The return to Barcode closes the loop when goods actually arrive; a shopping intention or draft order is not stock.

### Phase 1 — Barcode to Menu

Understand what an item is, connect it to useful food knowledge, and turn available ingredients into a practical meal.

| Stage | Household outcome | Where delivery stands |
| --- | --- | --- |
| **Barcode** | Scan an item to find out what it is. | Camera, barcode-photo, manual and compatible hardware-scanner foundations exist. The latest scanner decisions and real-device behaviour still need reconciliation and verification. Broader identifiers and non-food coverage remain part of the intended scope, not a universal lookup promise. |
| **Product** | See the information available about each product. | Source lookup and detail foundations preserve identity, variants and unknowns. Shared product pictures, classification and access to all available source fields need consistent treatment across screens; a summary must not replace the underlying evidence. |
| **Ingredient** | See how products connect to the ingredients you cook with. | Culinary mappings and source-preserving ingredient ingestion exist. A label mentioning milk does not make that product usable as milk. Canonical identities, relationships and uncertain matches still need qualified data and connected consumers. |
| **Recipe** | Find recipes by dish, ingredient or source. | Recipe discovery, private review and source attribution have foundations. Linking ingredients to each cooking step, preserving variants and admitting recipes for practical use are not completed by importing a recipe file. |
| **Quantity** | Adjust quantities for the portions you want to make. | Measured quantities and portion scaling have foundations. Ranges, preparation, yield, pack amounts and substitutions must remain traceable; missing measurements and unsupported conversions must not be guessed. |
| **Nutrition** | See nutrition for the whole recipe and each serving. | Product estimates, nutrient sources and coverage reporting exist. Reliable recipe and serving totals still depend on the actual ingredients, quantities, preparation and compatible nutrient definitions. Unknown is not zero. |
| **Menu** | Make one meal work for different people and portions. | Meal ideas, weekly plans and household preferences have foundations. The full menu experience must combine individual restrictions, meal variants, portions, available stock and remaining shopping needs. |

Product knowledge is broader than food: the intended lookup experience includes everyday non-food items, while food-specific ingredient, recipe and nutrition relationships apply only where appropriate. International sources should retain their original names and wording alongside shared terminology and citations. Coverage must be stated for the sources and releases actually available, never as “every product” or “every barcode”.

### Phase 2 — Serving to Planning

Make the kitchen record reflect real meals, not just a plan or a plate that was served.

| Stage | Household outcome | Where delivery stands |
| --- | --- | --- |
| **Serving** | Record what each person was actually served. | Cooking-batch and serving foundations exist. Complete person-specific servings and meal variants still need connected screens, permissions and durable records. |
| **Consumption** | Record what was eaten, not just what was put on the plate. | Food-history and completion records exist. Recording eaten and uneaten components separately from served amounts remains part of the fuller experience. Skipping a log must not imply that nothing was eaten. |
| **Leftovers** | Put prepared food back into storage with its remaining quantity and nutrition. | Saved cooked-stock foundations exist. The complete flow must return a prepared batch to the chosen pantry, fridge, freezer or other space, retaining its quantity, nutrition estimate and ingredient/source history. |
| **History** | Follow each person’s recorded intake over time. | Frozen food-history estimates and trend views have foundations. Complete individual history must connect actual consumption, substitutions and later use or disposal of leftovers without counting the same food twice. |
| **Planning** | Use food history, preferences and leftovers to shape the next menu. | Meal planning and shopping gaps exist; reusable plans, richer preferences and history-informed suggestions are partial or planned. Suggestions should ask for confirmation rather than silently changing a person's preferences. |

These stages share a few essential rules:

- **People are not interchangeable.** Individual and family restrictions, allergies, dislikes and preferences need clear distinctions, person-specific portions and the right authority to view or change them. Household membership alone must not expose another person's private health information.
- **Count food once.** Cooking consumes ingredient lots once. Serving, eating, saving, sharing and discarding partition what remains. A later meal can use saved food without repeating the original ingredient deduction or intake record.
- **Keep the evidence with the food.** A prepared batch retains its recipe/version, actual ingredient changes, quantity basis and nutrition provenance. Unknown quantities or nutritional values remain visible when it is stored, served again or discarded.
- **Learn with permission, not diagnosis.** Repeated avoidance can prompt a preference review. Recorded intake below a chosen target can be flagged, but missing logs are not zero intake, and these observations are not diagnoses or medical prescriptions.

### Phase 3 — Integration to Receipt, then back to Barcode

Let a household use its preferred services while keeping the decision to buy, and the record of what arrived, explicit.

| Stage | Household outcome | Where delivery stands |
| --- | --- | --- |
| **Integration** | Let authorised apps help with the information you choose to share. | Scoped REST/MCP interfaces, portable documents, private imports and supported personal-connection foundations exist. Regional retailer interfaces, broader open-format exchange and household/profile permissions still need individual integration and acceptance. |
| **Ordering** | Prepare a shopping list or draft order for a supported service, then review it before anything is submitted. | Shopping gaps, selected-offer calculations and handoff proposals are foundations, not a completed ordering service. Provider access, destination checks, current price/availability and explicit confirmation remain required. |
| **Receipt** | Check what was received, review the receipt and bring those goods into the kitchen. | Home-checkout receipts exist; receipt-image review and duplicate-handling helpers are partial foundations. Only confirmed received goods return to stock through the Barcode/check-in step. An order, payment or receipt image must not automatically create inventory. |

Bring-your-own connections use the person's own supported account and permissions. Credentials must stay protected, separate from profile backups and public data. Open formats, import/export and MCP should provide useful alternatives where a direct regional connector is unavailable. A provider directory entry, outbound link or source adapter is not a working vendor integration. No automatic purchase or active retailer API is promised by this plan.

## Scanner and kitchen decisions to preserve

The scanner is one entry point into the loop, not the whole product. Its current design requirements include:

- **Look up or check in deliberately.** Exploring an item must not change inventory. In a checkout context, continuous scanning automatically stages new items into a draft receipt; it does not require a confirmation for every product. Keep Void, line corrections and one final receipt confirmation, with duplicate-scan protection.
- **Keep the operation clear.** Unpacking adds received goods to a selected location. Rebuilding a shelf replaces only that shelf after review. Garbage/cleanup records confirmed removals, including partial quantities, without changing other locations. Preserve resumable drafts and show what Finish will do in the current context.
- **Keep receipts useful.** A finished receipt can be reopened and printed or saved as PDF through the browser's print dialog. Unknown amounts and unconfirmed ingredient mappings remain explicit.
- **Prefer the rear camera on phones.** This is the latest phone default, superseding the older front-camera bench default. Keep a visible camera switch, capability-aware fallback and alternative input methods; do not infer new defaults for other devices.
- **Let the camera remain usable.** The selected design keeps the camera visible behind a movable, collapsible information panel. Maximise the barcode aiming guide within the available camera view and align it with the actual decoder region and crop, rather than drawing a decorative frame alone. Preserve access to complete source details as well as a readable summary. Product identity, source claims and interpreted ingredient information must not be confused.
- **Offer accessible alternatives.** Manual entry, barcode photos, no-barcode food entry and compatible scanner input complement the camera. Sound, vibration, glow, light and spoken feedback are optional and capability-dependent; quiet, large-target and reduced-motion use must remain practical.
- **Protect the capture.** Camera frames and barcode photos are processed locally in the scanner; they are not uploaded or retained as part of ordinary barcode decoding. Receipt-image capture is a separate, consented review workflow, not permission to retain every camera image.

These decisions are the reconciliation target. Selected wording and visual designs do not by themselves establish implementation, production approval or reliable physical-device operation. The [scanner engineering record](docs/scanner-engineering.md) contains earlier implementation evidence; its older phone-default wording is superseded by the requirement above.

## Capabilities that support the loop

- **A household kitchen:** pantry, fridge, freezer and custom spaces; loose food and partial packs; label dates separated from check reminders; waste records; private recipes and collections; shared kitchens with appropriate roles.
- **Useful food knowledge:** recipes and cultural variants, source-labelled nutrition, product categories and pictures, brands/suppliers and origins, dietary/certification evidence, possible recall matches, restaurant menus and country food baskets. These areas have different levels of data and feature readiness; none implies universal coverage or clinical safety.
- **Practical planning:** preferences, attendance, portions, use-first ideas, leftovers, reusable weeks, lunchboxes, equipment, pack sizes and budgets. Historical prices remain observations, not current offers or guaranteed savings.
- **Control and portability:** backups, printable recipes/receipts/menus/lists, HTML/EPUB and structured exports, scoped apps and assistants, secure personal connections, profile privacy and consent. Expanded protected portability and professional/care sharing still require their own adoption and verification.
- **An inclusive product:** accessible controls, multilingual source text, interface localization, help and correction reports, moderated recipe sharing and positive achievements for variety, organisation and participation—not calorie restriction or weight loss.

## What remains before the loop is complete

“Present in source”, “connected to a working screen”, and “verified in the released app” are different milestones. Historical acceptance records describe their own releases; they do not certify a newer build, a different data release or the full loop above. This README update does not claim a new live release or a passed full test baseline.

| Delivery area | What completion needs to establish |
| --- | --- |
| **Experience and frontend** | A coherent journey across scanning, menus, people, serving, leftovers and shopping; the scanner decisions above; clear corrections, uncertainty, recovery and accessible alternatives on real devices. |
| **Data and backend relationships** | Qualified product → ingredient → recipe → quantity → nutrition relationships; actual lots/batches/servings/events; source versions and citations; complete source-field preservation without turning uncertain matches into facts. |
| **Connections and ordering** | A real supported regional/provider workflow, its permissions and limits, reviewed handoff/ordering, and received-goods reconciliation. Existing app infrastructure is not proof of a Phase 3 connector. |
| **Identity, consent and privacy** | Account continuity; household roles separate from personal/profile/health authority; current, limited-purpose connection and sharing consent; revocation and deletion across derived records. |
| **Persistence and recovery** | Durable edits, retry-safe stock/intake operations, explicit conflicts, interruption recovery, backup/restore and multi-device/offline evidence without duplicate consumption or stock. |
| **Release evidence** | The exact source and data release exercised through the intended workflow, with live/device acceptance where applicable and unresolved limitations stated plainly. |

Keep the existing requirement identities in the [detailed delivery programme](docs/research-delivery-plan.md), [recommendation register](docs/recommendation-delivery-register.json) and [delivery reconciliation](docs/delivery-reconciliation.json). This README is their readable product guide, not a second task tracker. Current actions and release decisions remain in the established delivery record; dated checkpoints remain evidence, not automatic current status.

## Architecture and development

OffMenu keeps its existing stack: a JavaScript browser/PWA application under `public/`, a Cloudflare Worker/D1 application backend under `cloud/`, and a separate Python/SQLite CLI and small local interface. The [local curation/static delivery architecture](docs/curation-architecture.md) keeps original source releases local and separates qualified publication projections from private account state. Do not recreate a hosted raw-source corpus simply to build a feature.

The existing interface contracts include REST `/api/v1`, MCP `/mcp` and OpenAPI `/openapi.json`; access is scoped and may read the saved account snapshot rather than unsaved browser edits. [Personal AI](docs/personal-ai.md) has its own capability and reviewed-action boundaries. The app's [optional operational services](docs/third-party-services.md), such as diagnostics, consent and support, are separate from Phase 3 household/retailer integrations; configuration is not activation.

The current authentication default remains the established Netlify path. The alternative authentication seam is integrated in source, but a live change still requires explicit configuration, staging, account-continuity and release work; it is not a completed sign-in migration. See the [current configuration guide](docs/maintainer.md#configuration-and-authentication-state).

### Source catalogue and coverage

OffMenu's source programme is much broader than the small CLI examples below. It spans product labels, national food composition, recipes, prices, companies, safety notices, places and optional personal connections. The [source catalogue](docs/OFFMENU_CORPUS_INDEX.md#source-catalogue) points to the existing registers, release mappings and later country/recipe catalogues, rather than treating six import examples as the whole corpus.

The repository records **1,303 discovery entries**, **22 historical retained-release mappings** and **54 app-directory entries**, with additional country and recipe evidence. These inventories overlap and have different purposes; they are **not an additive total of collected or live sources**. Discovery, collection, parsing, qualification and live use are separate milestones. Historical counts and directory labels are not a current coverage guarantee.

| Source group | Named sources and what they contribute | Delivery boundary |
| --- | --- | --- |
| Products and barcodes | Open Food Facts; GS1 GDSN and certified pools such as 1WorldSync and Syndigo; GS1 India DataKart and Australia Trusted Content/National Product Catalogue; NIQ Label Insight/Brandbank. | OFF has retained-release and implementation evidence. The other product-content routes are documented candidates or agreement-dependent services, not automatically available datasets. |
| National and regional nutrition | USDA FoodData Central; Australia AFCD and AUSNUT; UK CoFID; Canada CNF; France CIQUAL; Germany BLS; Norway Matvaretabellen; Denmark Frida; Finland Fineli; New Zealand FOODfiles; Sweden's food composition database; Japan MEXT. The wider catalogues also name NEVO, TBCA, TACO, PortFIR, Czech NutriDatabaze, Cyprus composition tables, IFCT, TKPI, China CDC, Russian composition references and the Pacific Nutrient Database. | Named releases for a subset are mapped and have historical parser evidence. Other entries remain discovery, retained-reference or permission-review work. FAO/INFOODS, EFSA, EuroFIR and regional tables are additional routes, not proof of complete country coverage. |
| Recipes and cookbooks | Wikibooks language editions; HowToCook; based.cooking; TacoFancy; OpenRecipe; UniTools; Open Recipe Archive; Smithsonian book texts; recetasdemami, Indisch-eten, libre_cuisine and Ricette. Later research also records Wellcome works, Library of Congress leads and country-specific cookbooks. | The dated recipe reports distinguish collected/parsed material, qualified local candidates and excluded records. Metadata for a book is not a parsed recipe. RecipeNLG and other restricted or uncleared corpora are not general-purpose bundled content. |
| Prices and household baskets | Open Prices; FAO FPMA; WFP food prices via HDX; OpenDOSM PriceCatcher; national statistics, household-budget and CPI sources, including Statistics Canada, STATEC and country-portfolio records. | Dated observations, commodity series, household baskets and price indices remain different types. None alone establishes a current offer, local stock or a complete shopping basket. |
| Producers, ownership and certification | Wikidata; GLEIF; OpenCorporates; Companies House; Open Ownership; USDA Organic INTEGRITY, EU TRACES, national organic registers, Fairtrade/FLOCERT, Rainforest Alliance, RSPO, ASC, halal, kosher and vegan certification directories. | Discovery/reference evidence must retain its issuer, date and scope. A company link or certification-directory entry is not a verified ownership chain, product claim or automatic boycott decision. |
| Safety and food guidance | UK FSA alerts and hygiene ratings; France RappelConso; openFDA enforcement; FSANZ and Canadian recalls; EU RASFF; China SAMR; Indonesia BPOM; USDA FoodKeeper; national dietary-guideline references. | Country, affected product and batch must match. Inspections are not necessarily recalls; registration identifiers are not barcodes. Historical openFDA enforcement research is not a public-alert or recall-lifecycle feed. |
| Places, menus and shopping connections | OpenStreetMap, Overture Places and Google Places; country retailer and restaurant catalogues; ALDI country portals; WhichGrocer, Instacart, Kroger, Square, Toast, Deliverect, Uber Eats, DoorDash and Wolt. | Place references and retained menus do not establish live menus, nutrition or inventory. Commercial and merchant routes need their own access, scope and terms; future ordering still requires explicit confirmation. |
| Meaning, units and enrichment | FoodOn, FAO AGROVOC, QUDT, ChEBI and Codex references, alongside source-native classifications and nutrient definitions. | Some named releases have reference adapters; others are research candidates. A vocabulary or parser does not itself prove ingredient equivalence, a unit conversion or a dietary conclusion. |
| Optional personal services and imports | USDA's personal API, Edamam, Spoonacular, fatsecret and Nutritics; Apple HealthKit, Android Health Connect, Google Health, Withings, Garmin and Strava; user-provided files, receipts and open document formats. | Provider approval, plan-specific rights and per-person consent remain separate from source registration. Private account data is not the shared food corpus. Native OffMenu JSON and Schema.org Recipe are formats, not external datasets. |

For exact source IDs, releases, historical evidence and outstanding restrictions, use the [catalogue and status guide](docs/OFFMENU_CORPUS_INDEX.md#source-catalogue), [source acceptance contract](docs/source-acceptance-contract.md) and [delivery programme](docs/research-delivery-plan.md). This summary is not fresh licence clearance, download permission, provider entitlement or proof that a connector is live.

<details>
<summary>Historical small-CLI import notes — a limited subset, not the source catalogue</summary>

The following notes preserve the earlier README's small-CLI scope and historical licence observations; they are not fresh permission or present coverage claims.

| Source | Preserved scope and limitations |
| --- | --- |
| [Open Food Facts products](https://static.openfoodfacts.org/data/openfoodfacts-products.jsonl.gz) | The small CLI's `import-products` accepts JSONL/gzip, preserves barcode strings and existing ingredient mappings, and can filter supplied country tags; that filter is not exhaustive national coverage. The importer does not download photos. Historical licence notes distinguish the ODbL database from DbCL contents; image rights are separate. |
| [Native OffMenu recipe JSON](examples/recipes.json) | `import-recipes` accepts the example array format with source/licence provenance, explicit culinary ingredient names and quantities in `g`, `ml` or `count`. Missing amounts remain unresolved. This command is not a direct Wikibooks or RecipeNLG importer. |
| [Wikibooks Cookbook candidate](https://huggingface.co/datasets/gossminn/wikibooks-cookbook) | The historical candidate declared CC BY-SA 4.0. Collection/extraction tools are retained in [`collect-wikibooks.py`](scripts/collect-wikibooks.py) and [`collect-wikibooks-live.py`](scripts/collect-wikibooks-live.py); the small CLI still requires its own interchange format. Earlier adapter/parsing roadmap items and later recipe-library work are distinct scopes, not evidence that every recipe is reviewed or usable. |
| [RecipeNLG](https://recipenlg.cs.put.poznan.pl/) | Recorded as restricted to non-commercial research/education and not bundled. Its appearance in the source inventory is not approval for commercial ingestion or redistribution. |
| [Open Prices](https://github.com/openfoodfacts/open-prices/blob/main/docs/guides/data.md) | The small CLI's `import-prices` expects product code, price, currency and date; retailer/location metadata is optional. Unjoined locations show an unknown retailer. Repeated imports historically append duplicate observations. `shops` returns dated observations, not current stock; Australian coverage was unmeasured. Historical licence note: ODbL. |
| [WhichGrocer](https://www.whichgrocer.com/developers) | A future optional backend connector in the earlier README, with no account, calls or paid service configured at that checkpoint. Issued access, attribution and cache/retention terms need review; catalogue prices do not establish store-level stock. |

</details>

### Setup, build and checks

Start with the [maintainer guide](docs/maintainer.md) for the supported Node/Python environment, declared dependencies, configuration and precise commands. There is no `npm run dev` or `npm start` script. The small Python server is not a substitute for the full browser/Worker app.

For an already prepared development checkout, check tracked generated-file drift before building:

```sh
npm run check:generated
npm run build
```

Use the [validation workflow](docs/development/validation-workflow.md) to select checks appropriate to a change and the [maintainer check sequence](docs/maintainer.md#checks-and-generated-files) for explicit full validation. The retained full baseline workflow is manual, not an automatic push/PR guarantee. A build does not deploy the app or publish data, and checks not run must remain reported as unrun.

### Small local demo

After installing the declared Python dependencies, use a separate temporary demo database and the authored examples:

```sh
OFFMENU_DEMO_DIR="$(mktemp -d)"
OFFMENU_DEMO_DB="$OFFMENU_DEMO_DIR/offmenu.sqlite"
python3 -m offmenu --db "$OFFMENU_DEMO_DB" init
python3 -m offmenu --db "$OFFMENU_DEMO_DB" import-products examples/products.jsonl
python3 -m offmenu --db "$OFFMENU_DEMO_DB" import-recipes examples/recipes.json
python3 -m offmenu --db "$OFFMENU_DEMO_DB" map 0000000000001 'coconut milk'
python3 -m offmenu --db "$OFFMENU_DEMO_DB" map 0000000000002 rice
python3 -m offmenu --db "$OFFMENU_DEMO_DB" add 0000000000001 400 ml
python3 -m offmenu --db "$OFFMENU_DEMO_DB" add 0000000000002 1000 g
python3 -m offmenu --db "$OFFMENU_DEMO_DB" meals --servings 2
python3 -m offmenu.server --db "$OFFMENU_DEMO_DB" --host 127.0.0.1 --port 8765
```

Open `http://127.0.0.1:8765`; stop your own server with Ctrl-C. Example barcodes are fictional. The small demo uses explicit ingredient mappings and measured quantities; it does not silently assume staples, substitute ingredients or invent density conversions. Its expiry bookkeeping is not a food-safety assessment. The CLI is not a read-only inspector for retained source databases.

For a phone on the same network, camera access needs HTTPS with a certificate trusted by that phone and valid for the server's address. The local server accepts `--cert certificate.pem --key private-key.pem`; configure trust or a suitable HTTPS reverse proxy deliberately. Plain HTTP to a LAN address is insufficient. Do not expose the unauthenticated Python prototype to the public internet. Local-server connectivity, browser/PWA offline behaviour and real camera acceptance are separate concerns.

### Source, release and further reading

- [Documentation index](docs/README.md): current guides and specialist evidence.
- [Maintainer guide](docs/maintainer.md) and [operations](docs/operations.md): setup, source/configuration boundaries and release procedure.
- [Source acceptance contract](docs/source-acceptance-contract.md) and [curation architecture](docs/curation-architecture.md): source rights, original data, qualified projections and publication boundaries.
- [Common data contract](corpus/common-data-contract.json): shared identities, source assertions, quantities, citations and private/public distinctions.
- [Internationalization](docs/i18n.md): interface and source languages, original text and explicit fallback. Arabic remains a preview, not a fully translated release.
- [Private portability contract](docs/schema/private-portability-v1.md): the bounded source implementation and remaining identity, consent, custody and restore dependencies.
- [Historical product review](docs/product-review-status.md) and [acceptance register](docs/acceptance-register.md): dated evidence and limitations, not certification of the current runtime.

Source licences and per-record attribution remain attached to the data; normalization does not relicense it. Credentials, private customer records and raw datasets do not belong in this repository. Health interpretation, high-risk dietary claims and physical-device reliability require evidence beyond source code and automated fixtures.

## Developer delivery

Start with [the repository standard](docs/standards/repository.md),
[the repeatable developer workflow](dev/delivery/README.md) and
[agent instructions](AGENTS.md). Run `npm run check:repository` to check the
versioned layout and naming contract. Browser, edge and compatibility tests now
live under `tests/web`, `tests/edge` and `tests/compat`.
