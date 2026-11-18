# Using Global data in OffMenu

Choose **Global data** from the kitchen to open the **Global food and evidence workspace**. Use this page to inspect country and source evidence, compare measured baskets, and manage your own private measurement groups. It is **not** the kitchen’s Data tab: for CSV mapping, food-record import or connecting a provider, use the [food data import guide](data-import-guide.md).

**Find your task:** [country and public records](#find-and-check-a-public-record) · [basket arithmetic](#calculate-compare-or-download-a-basket) · [private measurement groups](#keep-private-measurements-separate) · [rules and contribution choices](#evaluate-a-rule-or-save-a-contribution-preference).

## Find and check a public record

1. Choose **Country**, then **Open country**. Read the evidence status and open **All source and mapping evidence** for the underlying record. Suggested foods are not a measured national basket. Changing the menu does not reload the open record: open the new country before downloading it or using its starter list.
2. To search individual records, choose a **Record family**, enter **Search** text, and press **Search**. The country filter applies to *Source directory* and *Basket lines*, not all families. **Next page** replaces the current results. If there is no next cursor, start a new search rather than assuming another page exists.
3. For a company candidate, choose **GLEIF** for a company name or **Wikidata** for an exact Q identifier. Check the returned evidence before using it. A matching name is not proof of identity; the company’s country is not the food’s origin.

**Use starter shopping list** takes the currently open country’s suggested foods to the kitchen, not measured quantities or purchased stock. If you see **Open a country first**, load its record. A special provisioning context with no ordinary starter cannot be imported with this button.

## Calculate, compare or download a basket

For a first look, choose **Load synthetic arithmetic example** and then **Calculate nutrients and coverage**. The example exercises the arithmetic; it is not dietary advice or evidence for a country. For your own measured basket, supply its quantities, preparation state, nutrient units/basis, source and definition. Volume needs a density and a count needs a unit mass. Treat unknown values as unknown, not zero. Compare the reported total with the known subtotal and coverage.

**Save privately** sends the *current basket JSON* for private account storage. **Download calculation** downloads the *most recent successful calculation*, not the editor contents. After editing the basket, calculate again before exporting: changing the text does not clear the previous result. Expand **Compare a second measured basket**, enter the second basket and metric, and choose **Compare compatible evidence**. Input errors appear in the page status; a failed comparison is not a finding that two baskets are equal.

## Keep private measurements separate

Use **My kitchen** to sign in for private storage. The public catalogue and private history serve different purposes. The app describes the history as account-specific, not a shared kitchen record or a native wearable connection.

- To add a measurement, pick the type and its displayed unit, enter the value, local date/time and source. Select the permission checkbox **only if you want to store these measurements in your account**, then choose **Save measurement privately**. The checkbox does not send a measurement by itself.
- **Import measurements JSON** is different: selecting a file starts the import immediately, not a preview. Select permission first if you intend to store the file. This handler accepts a JSON array or an object containing `records`; it rejects a missing file or one over 1,000,000 bytes. Use only information you are authorized to store.
- **Read history and statistics** displays a summary and adds one **Delete measurement group …** button for each returned group. The button acts on that *group*, not one individual value. This handler provides no second confirmation. After a successful deletion, read history again to refresh the totals. If statistics report partial coverage, do not treat the visible summary as complete.
- **Download private history** follows the history pages to export all returned private groups. Keep the downloaded JSON private. It is not a household backup. If an action fails, read the status before trying again; a failed request does not prove a previous save or deletion had no effect.

## Evaluate a rule or save a contribution preference

Enter the rule, market and evidence JSON, then choose **Evaluate evidence**. Unknown, conflicting, failing and passing evidence are distinct; this does not independently verify user-provided claims. For contribution, check or uncheck the preference and then choose **Save my preference**. The action stores that setting, not a grant to publish data. **Personal API specification** opens the interface description. It does not sign you in or grant API access.

## Control and evidence map

This is a source guide, not a live help index. The following lookup includes every button, field, link and disclosure present in this page's HTML and the additional interactive control types constructed by its script. The first column is a stable source locator (ID, href, disclosure label or dynamic selector); the last is the intended guide destination. Search words refer to this document, **not** to verified app search results. The kitchen Data tab, scanner, extension, administrator screens and translated/device behavior are outside this page’s inventory.

The line numbers below refer to [the page (H)](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/assets/data-workspace.html), [its module (J)](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/data-workspace.js) and [shared language setup (L)](https://github.com/maldous/offmenu/blob/51ad2b27a226f097dcaa9a27db5fade33d9ef4dd/apps/web/src/i18n.js#L120-L148). Controls labelled H are native HTML until an associated handler runs.

| Source locator | Source | Audience, task and guide lookup |
| --- | --- | --- |
| `workspace-language` | H1, J2, L120–148 | Any reader: change the interface language (English/Arabic). This is not a source-data translation. |
| `href:/` | H1 | Any reader: return to My kitchen, including for account sign-in. |
| `country` | H2, J10–14 | Public researcher: select the country for the next lookup; countries are populated at runtime. |
| `load-country` | H2, J11 | Public researcher: load the country summary and evidence. |
| `download-country` | H2, J12 | Public researcher: save the already-open country record. |
| `starter` | H2, J13 | Shopper: stage eligible starter foods and navigate to the kitchen. |
| `summary:All source and mapping evidence` | H2, J11 | Public researcher: expand/collapse the open country’s source record. |
| `kind` | H3, J14 | Public researcher: select a catalogue record family. |
| `query` | H3, J14 | Public researcher: enter catalogue search text. |
| `search` | H3, J14 | Public researcher: start the first page of a search. |
| `next` | H3, J14 | Public researcher: request the next page based on the preceding result. |
| `enrichment-source` | H4, J15 | Public researcher: select a company-evidence source. |
| `enrichment-query` | H4, J15 | Public researcher: enter a name or Q identifier for the selected source. |
| `enrich` | H4, J15 | Public researcher: request public evidence, not verified food origin. |
| `basket-example` | H5, J16 | Learner: fill the first editor with a synthetic example. |
| `basket-json` | H5, J16–18, J26 | Basket analyst: edit the first measured basket. |
| `calculate` | H5, J17 | Basket analyst: calculate metrics and inspect missing evidence. |
| `save-basket` | H5, J18 | Signed-in user: send the current basket for private storage. |
| `export-basket` | H5, J18 | Basket analyst: download the last calculated result. |
| `summary:Compare a second measured basket` | H5 | Basket analyst: reveal the second basket and comparison controls. |
| `basket-second` | H5, J26 | Basket analyst: enter the other basket. |
| `compare-metric` | H5, J26 | Basket analyst: select a metric by identifier. |
| `compare-baskets` | H5, J26 | Basket analyst: compare the supplied JSON for the selected metric. |
| `health-consent` | H6, J19 | Private account holder: authorize storage before a manual save or file selection. |
| `health-type` | H6, J20 | Private account holder: select the measurement and unit together. |
| `health-value` | H6, J20 | Private account holder: enter a value in the selected unit. |
| `health-date` | H6, J10, J20 | Private account holder: check local observation date/time before saving. |
| `health-source` | H6, J20 | Private account holder: identify the source of the observation. |
| `save-health` | H6, J19–20 | Private account holder: save the new measurement group. |
| `health-file` | H6, J19, J21 | Private account holder: selecting JSON starts the consent-gated import. |
| `health-history` | H6, J22 | Private account holder: load group deletion controls and descriptive statistics. |
| `dynamic:health-results/delete-group` | J22 | Private account holder: delete one returned group; reload to refresh totals. |
| `health-export` | H6, J7–8, J22 | Private account holder: export the paginated history, not just the displayed page. |
| `evidence-json` | H7, J23 | Evidence reviewer: supply rule, market and assertions. |
| `evaluate` | H7, J23 | Evidence reviewer: evaluate the supplied claims, not independent verification. |
| `contribute` | H8, J23 | Account holder: choose whether eligible facts may be considered. |
| `save-settings` | H8, J23 | Account holder: store the preference; this does not publish facts. |
| `href:/openapi.json` | H8 | Developer: open the personal API specification (not an authorization). |

The country options generated at J10 belong to the existing country selector, not another button. The J8 download anchor is created and clicked by the export handler, not added as a visible navigation control. A request button’s shared J6 handler disables it while awaiting the result, writes success or error text to the status region, and re-enables it. For catalogue pagination, the wrapper can re-enable **Next page** after the search function set it disabled; do not infer that a next page exists from its enabled appearance.

**Maintenance and remaining checks.** The owner changing this page, its script or language setup should update the affected row and guide text in the same reviewed change. The static coverage check catches unlisted controls; it does not prove that a backend is available, permissions are granted, wording is accessible on a device or help search routes here. The UI owner and independent reviewer still need to verify in-app discovery/ranking, no-result and stale/error states, keyboard/focus/assistive behavior and supported layouts on a qualified preview using synthetic data. Do not use real private records as test fixtures.
