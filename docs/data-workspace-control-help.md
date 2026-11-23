# Using Global data in OffMenu

The public catalogue is unavailable. This does not mean a product, recipe or
country is missing. The workspace does not look for a replacement provider.

- [Check availability](#check-availability)
- [Save a measured basket](#save-a-measured-basket)
- [Keep private measurements separate](#keep-private-measurements-separate)
- [Evaluate a rule or save a contribution preference](#evaluate-a-rule-or-save-a-contribution-preference)

See the [data import guide](data-import-guide.md) for keeping private or
user-provided records separate from the public catalogue.

## Check availability

The workspace shows availability without making a public lookup. Use **My kitchen**
to go back to the app. System appearance and interface language remain independent
of food data.

## Save a measured basket

In **Advanced private and technical tools**, enter the basket in the measured
basket editor. Sign in through **My kitchen** before saving it privately. The
workspace does not calculate or compare a basket against public nutrient data.

## Keep private measurements separate

Sign in and review the consent field before saving a measurement or importing a
measurement file. Use history to review those records, export the complete
paginated history, or delete one returned group; reload the history after
deletion to refresh the totals.

## Evaluate a rule or save a contribution preference

Rules evaluate the evidence you supply. They do not fetch public evidence or
certify a claim. A signed-in contribution preference is not publication. The
browser uses a local download anchor for export; it does not transfer the file.

## Control and evidence map

H refers to the current workspace markup; J refers to its JavaScript.

| Source locator | Source | Audience, task and guide lookup |
| --- | --- | --- |
| `a.workspace-brand[href="/"]` | H1 | Any reader: select the OffMenu brand to return to the app home. |
| `workspace-language` | H1 | Any reader: change the interface language (English/Arabic). This is not a source-data translation. |
| `href:/` | H1 | Any reader: return to My kitchen, including for account sign-in. |
| `button[data-theme-toggle]` | H1 | Any reader: switch the interface between light and dark appearance. This does not change data or language. |
| `summary:Advanced private and technical tools` | H3 | Any reader: expand/collapse advanced measured, private and technical inputs. Opening it does not sign in or send data. |
| `basket-json` | H3 | Basket analyst: enter measurements as JSON. This action does not look up or calculate public nutrients. |
| `save-basket` | H3, J10 | Signed-in user: send the current basket for private storage. |
| `health-consent` | H4 | Private account holder: authorize storage before a manual save or file selection. |
| `health-type` | H4 | Private account holder: select the measurement and unit together. |
| `health-value` | H4 | Private account holder: enter a value in the selected unit. |
| `health-date` | H4 | Private account holder: check local observation date/time before saving. |
| `health-source` | H4 | Private account holder: identify the source of the observation. |
| `save-health` | H4, J12 | Private account holder: save the new measurement group. |
| `health-file` | H4, J13 | Private account holder: selecting JSON starts the consent-gated import. |
| `health-history` | H4, J14 | Private account holder: load group deletion controls and descriptive statistics. |
| `health-export` | H4, J14 | Private account holder: export the paginated history, not just the displayed page. |
| `evidence-json` | H5 | Evidence reviewer: supply rule, market and assertions. |
| `evaluate` | H5, J15 | Evidence reviewer: evaluate the supplied claims, not independent verification. |
| `contribute` | H6 | Account holder: choose whether eligible facts may be considered. |
| `save-settings` | H6, J15 | Account holder: store the preference; this does not publish facts. |
| `href:/openapi.json` | H6 | Developer: open the personal API specification (not an authorization). |
| `dynamic:health-results/delete-group` | J14 | Private account holder: delete one returned group; reload to refresh totals. |
