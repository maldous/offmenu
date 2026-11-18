# Bring food data into OffMenu

Use the kitchen’s **Data** tab to explore source records, review a file, and
choose what to retain privately. Start with a small batch whose food identities,
units and source terms you can check.

For the separate **Global data** page, see [country records, basket comparisons and private measurement history](data-workspace-control-help.md).

This guide describes source revision
`1ea77f7bf9eda6f3487a4954bd4dbab72305c15f`. It is source-backed guidance;
screens, device layouts and the deployed service have not been verified for
this guide. Labels below use the English interface wording.

## Choose where to start

| I want to… | Start here |
| --- | --- |
| Find records already offered by a public source | **Explore & enrich your food data** |
| Bring a JSON or CSV file I am allowed to use | **Bring your files, too** |
| Review records I previously saved | **Load my private records** |
| Use my own provider API plan | **Add my credentials** on that source’s card, while signed in |

Loading or normalizing a batch gives you a preview. It does not itself save the
batch to your profile. **Save batch to my profile** and **Export unified JSON ↓**
are separate actions with separate permission checks.

## Explore a source

1. In **A world of food data**, use **Country filter**, data-type, access or text
   filters to narrow the catalogue. Country filtering is optional; a global
   source can still appear for a selected country. Choosing a country does not
   prove every food from that country is available.
2. Read the source card’s access details, rights, notes and status. A catalogue
   entry, a configured credential or an **adapter pending** label is not a
   guarantee that a lookup is available. The country coverage table distinguishes
   named national sources from records actually integrated into OffMenu.
3. Choose **Explore normalized data** where offered, or select a **Source** in
   **Explore & enrich your food data**. Enter a **Food / business search** or a
   **Barcode (OFF / Open Prices)** as appropriate. Keep barcode leading zeroes.
4. Choose **Explore normalized records** and wait for the status message. Read
   any coverage or source limitation shown with the result count.
5. Review each result’s identity, country, attribution and values. Expand
   **Unified record, provenance & licence** for the complete record.

**Next collection page** replaces the current public result page; it does not
accumulate every earlier page into one batch. Save or export a permitted page
before moving on if you need to retain it. The screen renders at most 100
records from a loaded batch. When the batch contains more, its export includes
that whole loaded batch, subject to the permission checks below.

Public feeds can return samples. A result from a notice or enforcement source
does not establish that your own food or batch is affected. Follow the original
official notice; do not treat a search result as a food-safety determination.

## Import a JSON file

1. In **Bring your files, too**, choose the truthful **Original source**.
   **Personal import** is for material you are entitled to use privately; do not
   relabel a restricted provider response to evade its terms.
2. Select a `.json` file using **Data file (under 2 MB per batch)**. Split larger
   files into smaller batches first. Do not put passwords or provider API keys
   in a food-data file.
3. The ordinary importer accepts unified OffMenu JSON (a record array or an
   object with `records`), USDA food JSON with `foods` or `fdcId`, and Open Food
   Facts product JSON with `product`.
4. Read the normalization status, then review the displayed batch before using
   **Save batch to my profile** or **Export unified JSON ↓**.

Unified records need supported schema and record types, identifiers, country
codes, and source/licence/attribution metadata. The ordinary validator allows
up to 2,000 records per batch; a source row can generate both a product and a
nutrient profile, so row count and record count can differ. Imported ordinary
records are marked private. That label does not grant upstream reuse rights.

### Common-corpus JSON is a different preview

A JSON file with schema `offmenu-common/1` opens a local common-corpus graph
preview. It preserves source identities, citations and quantities and can show
explicit translation fallbacks. Nothing is saved by loading it; the ordinary
**Save batch to my profile** and **Export unified JSON ↓** buttons are disabled.
This preview shows at most 100 resources and 50 assertions per resource.

To return to ordinary records before importing a CSV, run an ordinary source
search or choose **Load my private records**. These actions leave graph-preview
mode. Do not expect common-corpus JSON to become an ordinary saved record batch.

## Map a CSV carefully

Use a comma-separated `.csv` file with column headings. Quoted fields can
contain commas; an unmatched quote produces **Unclosed CSV quote.** Keep
barcodes as text in your spreadsheet so leading zeroes survive the export.

1. Set **Country filter** if the imported records have a known country, then
   choose their **Original source** and the CSV file.
2. Choose **CSV record type**: **Foods + nutrient profiles** or **Dated prices**.
3. Map **Food / product name**. Leave genuinely absent fields as **Not supplied**.
   Rows without a food/product name are omitted during normalization.
4. Map **Source record ID** where available and **Barcode (keep as text)** only
   to a barcode column. For dated prices, every row needs a distinct source
   observation ID: a product barcode cannot identify a dated price observation.
5. For foods, select **Nutrient basis** (**Per 100 g** or **Per 100 ml**),
   **Energy column unit**, **Sodium column unit** and **Food state**. These must
   describe the source values, not your preferred display units. The energy
   selector converts kJ to kcal; the sodium selector converts g to mg. Other
   mapped nutrient columns have the units named in their labels.
6. Supply **Name language (BCP 47)** when known. This records the language of
   the source name; it does not translate that name. For prices, map currency,
   observation date and retailer where supplied, or set **Default currency for
   prices** when the source has one known currency.
7. Choose **Normalize mapped CSV**, then check names, IDs, quantities, country,
   preparation state, price context and provenance in the preview.

Selecting a CSV opens its mapping controls before normalization. Any earlier
ordinary result batch can still be on screen at that point. Wait for the new
CSV normalization message and review its records before saving or exporting;
selecting the file alone does not replace that earlier batch.

Blank, unknown, trace, not-tested, not-detected and less-than nutrient values
retain their meaning; they do not become measured zeroes. For example, a
less-than value retains a limit rather than becoming an exact amount. Do not
replace missing measurements with invented numbers merely to complete a row.

## Review, save or export

Check **My source licence or personal provider plan permits this storage /
export.** only when it is true for the intended action. A checkbox cannot grant
commercial rights. Source policy can still refuse storage, export or derived
reuse; expired access, withdrawn/quarantined records or disallowed input
dependencies can also block an action. Sensitive health/history records belong
to their separately consented workflow.

| Action | What happens in this source version |
| --- | --- |
| **Save batch to my profile**, signed in outside demo | Sends the current permitted batch for private storage in that signed-in profile; read the returned saved count. |
| **Save batch to my profile**, guest or demo | Saves permitted private records in that browser profile, subject to a combined 500-record / 1,000,000-character limit. This is not a cloud save. |
| **Load my private records** | Loads the current profile’s saved records. Signed-in loading follows the private-record pages; guest/demo loading uses that browser profile. |
| **Export unified JSON ↓** | Downloads `offmenu-unified-data.json` for the current permitted ordinary batch. It is a data-record export, not a complete kitchen/account backup. |

For a nutrient profile, **Use this food data for that item** requires a matching
inventory item and permission for derived reuse. The item’s unit must match the
profile’s per-100 basis. Verify food identity and preparation before applying;
prior consumption snapshots remain unchanged. **Add recipe for review** saves a
recipe for your review; check ingredient matches, quantities and yield before
planning or cooking.

**Food-name display language** changes which supplied name is displayed. It does
not manufacture translations or change the source identifiers or quantities.

## Personal provider connections

Sign in to your own profile before selecting **Add my credentials** or **Manage
my connection**. Supply the provider-issued API key, or the application ID and
application key when that provider’s form requests them. Retailer account
passwords belong on the retailer’s own login page.

Saved credentials belong to the signed-in profile. The interface describes them
as encrypted on the server and excluded from backups and MCP/REST records.
Saving configures the connection; an actual search validates provider access.
If **Credential vault setup is pending** appears, the deployment’s vault is not
ready. A saved connection does not create an adapter or a provider entitlement.

**Remove my connection** removes OffMenu’s stored connection and its saved
unified records for that provider in your signed-in profile. Keep a permitted
export first if you need those records. Revoke the key at the provider as well
if you want the external credential invalidated.

## If something goes wrong

| Message or symptom | Next step |
| --- | --- |
| **Load or import records first.** | Run a source search or select a supported file, then review its normalization result before saving. |
| **Import a file under 2 MB; split larger files into batches.** | Split the original into complete, valid files with the necessary headings or record metadata in each batch. |
| **Import up to 2,000 records at a time.** | Reduce the normalized batch, allowing for product/profile pairs from a single food row. |
| **Map the food / product name column.** | Choose the actual name heading, rather than leaving that mapping blank. |
| Price observation IDs missing or repeated | Map a unique source observation ID for every dated-price row. Keep the product barcode in its separate field. |
| **Source and licence metadata are required.** or **Invalid unified record.** | Check the file’s supported format and required provenance fields. Keep the original file; do not remove provenance to force acceptance. |
| Storage/export/reuse is refused | Read the stated source-policy, retention or dependency reason. Check your entitlement; changing visibility to private does not remove restrictions. |
| **Sign in for cloud record storage, or export this batch.** | The browser-profile storage limit was reached. Use a permitted export or sign in, then load/import and review the batch in the intended profile. |
| **Profile changed. Retry in your current profile.** | Confirm the intended profile and start that load/search again. Switching profile or demo clears the current preview and credential form; do not assume the previous preview was saved. |
| A search fails or returns no useful records | Read the status message, source coverage and access notes; check the query, barcode, country and connection. Catalogue presence does not promise complete coverage. |
| Save/export remain disabled after a graph preview | Choose **Load my private records** or perform an ordinary source search to leave common-corpus preview mode. |

Use the labelled form controls in order, and read the status message after each
load, normalization or save. Nutrient results include an accessible selector
named for the food profile. This guide supplies no claim of completed keyboard,
screen-reader, RTL or device-layout qualification.

## Source and update ownership

The OffMenu documentation owner maintains this journey under UIF-183. Recheck it
when the [Data controls](../apps/web/assets/index.html),
[Data UI](../apps/web/src/data-ui.js),
[normalizers and limits](../apps/web/src/unified-data.js),
[record-use policy](../apps/web/src/record-policy.js) or
[source catalogue](../apps/web/src/sources.js) changes. Existing
[data tests](../tests/web/data.test.mjs),
[dependency/retention policy tests](../tests/web/record-policy-dependency-retention.test.mjs)
and [common-corpus tests](../tests/web/common-corpus-i18n.test.mjs) describe
supporting behavior; they were read, not rerun, for this documentation change.
This guide does not establish live provider access, deployment currency or
complete help/search acceptance.
