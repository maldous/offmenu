# Help search: four source-bound verification fixtures

This is verification preparation for UIF-186, not an executed search test or
help-completeness verdict. It selects four existing controls and specifies the
evidence to collect when qualified content and contextual search are available.
It adds no search interface, index, deep link or browser implementation.

## Bound source and inventory

Source revision: `1ea77f7bf9eda6f3487a4954bd4dbab72305c15f`.
The existing static-control inventory file
`main-app/static-controls.json` has SHA-256
`4dd45aea9b1d17efc599e04aad396c1986fc7bdf05e994f1e17069d78f121aab`.
Reuse its 289 source nodes; they are not 289 verified visible controls, unique
features or accessible interactions. Row pointers below are zero-based JSON
pointers into `/nodes`. No inventory was regenerated for this plan.

The inventory's HTML hash matches this revision. The source relationships below
were inspected, without running tests, opening a browser or exercising accounts.
The older seven staff/Insights preparation cases cover authority, settings,
source-policy conflict, insight scope, goals, history export and dated prices.
They explicitly do not establish contextual-index membership or ranking. These
four fixtures address that separate search-verification gap; they do not repeat
those cases or the mixed-direction cooking/serving preparation under UIF-190.

## Query fixtures and relevance expectations

Expected topics describe acceptance requirements, not existing article titles
or indexed documents. Before execution, bind each topic to actual content IDs,
versions and destinations selected by the help implementation owner. If none
exists, record a missing-content/index binding rather than inventing a result.

| Fixture / source control | Queries to retain verbatim | Expected relevant topic and source fact | Misleading relevance to reject |
| --- | --- | --- | --- |
| H1 · `/nodes/13`, `workspace-account`, **Profile & backup** · HTML line 12; `app.js` line 210 | `profile backup`; `where is my account` | Account/profile entry and the actual backup choices supported by that content version. The control calls `openAccount`; it is not a verified help-search entry. | A claim that opening the account panel automatically backs up or restores data; retailer or shopping-list export offered as account recovery. |
| H2 · `/nodes/116`, `share-shopping`, **Share / copy list ↗** · HTML line 53; `insights-ui.js` line 35 | `share shopping list`; `copy uncollected items` | Browser share/copy of uncollected shopping names and amount text, cancellation and download fallback. | A purchase/cart submission, retailer-proposal confirmation, received-stock addition or an assertion that checked lines are included in this text share. |
| H3 · `/nodes/117`, `shopping-csv`, **Download CSV ↓** · HTML line 53; `insights-ui.js` line 33 | `download shopping csv`; `collected column` | Shopping CSV includes Ingredient, Amount and Collected for all current list items, including checked lines. Distinguish it from food-history export and JSON-LD. | Search/snippet guidance claiming this CSV exports only unchecked items, filters food-history dates, records payment or imports stock. |
| H4 · `/nodes/211`, `confirm-finish`, **Confirm & finish** in static markup · HTML line 70; `app.js` lines 224, 226; `checkout-model.js` `finishInventory` | `confirm grocery receipt`; `shelf reset versus grocery unpacking` | Explain the current mode-specific confirmation: grocery adds staged items; shelf mode replaces that location; waste removes selected stock. Opening final review is distinct from confirmation. | Treating checklist collection or a shopping proposal as received stock; presenting shelf replacement as an append; treating a completed receipt as another active confirmation. |

For each query, save the ordered first five results (or all if fewer), exact
title/snippet, content ID/version, index revision and destination. The expected
topic should be the first directly actionable result, with its critical
distinction visible in the result or immediately on opening it. Record competing
results and explain any justified alternative ordering. A keyword match alone
does not pass relevance; a top result that contradicts the source fact fails.
Use these fixtures as a bounded sample, not proof of corpus-wide ranking quality.

## Contextual entry, destinations and failure states

For H1–H4, record separately whether the implementation exposes a help entry
from the source control, from the containing panel, or only from general search.
Do not count a product-action handler as a contextual-help handler. Record its
accessible name, invocation method and the content version it opens. Missing
contextual entry is an explicit coverage gap, not an assumed deep link.

Where a qualified article destination exists, verify opening it from the result,
direct navigation and reload; retain selected topic/section and a usable return
path. Test invalid, removed and unavailable destinations with safe synthetic
content. They must explain the unavailable topic and offer a route back without
performing the product action. These are requirements; no route format is
specified or claimed here.

Use the following additional inputs against the actual search interface:

- Empty and whitespace-only query: record the agreed empty state; do not silently
  label suggested content as matching search results.
- A synthetic nonsense query such as `zz-help-no-match-186`: distinguish a genuine
  no-result response from a network/index failure; preserve a way to edit or clear
  the query and reach general help.
- An isolated unavailable-index/failed-request fixture: show an understandable
  error and supported retry/back route. Do not report “no results” for failure or
  leave old results appearing to answer a newly failed query.

Never trigger purchases, checkout confirmation, account changes or exports while
testing help navigation. Use synthetic user/list/receipt examples only where a
qualified fixture is required; do not collect private household data.

## Accessibility and device evidence still required

For each fixture, record browser/version, viewport, input method, locale and the
actual content/index/source revisions. Exercise keyboard entry, search submission,
clear, result traversal, opening and returning; verify logical focus order,
visible focus and no keyboard trap. Confirm that search/clear/result controls
have meaningful accessible names, and that result counts, loading, no-result and
error changes are available to assistive technology without unexpectedly moving
focus. Retain the actual screen reader/version and observed announcement, rather
than inferring it from an ARIA attribute.

Check WEB, TABLET, FOLDABLE and MOBILE layouts using recorded viewport sizes;
separate physical-device observations from emulation. Verify zoom/reflow, long
result titles, touch targets, scrolling, focus visibility and return navigation.
Record failures, unavailable equipment and untested layouts. Link existing
locale/RTL verification where applicable; this plan neither repeats UIF-190 nor
certifies WCAG compliance. Browser, device and assistive-technology results are
currently **unexecuted and unqualified**.

## Ownership, staleness and result recording

These are responsibility requirements, not appointments of named operational
owners or new permissions:

| Role | Required responsibility |
| --- | --- |
| Product source owner | Identify changes to these control IDs, labels, handlers, modes or export semantics and provide the changed revision/path to the documentation owner. |
| Content maintainer | Bind each fixture to actual source-versioned content; review affected instructions/snippets when source changes, keeping unsupported features and draft-only content explicit. |
| Contextual-help/index owner | Record content/index revision and actual contextual-entry/destination mapping; refresh affected entries and verify that removed or stale destinations fail intelligibly. |
| Independent verifier | Record observed order, navigation, failures and accessibility/device evidence at exact revisions; retain untested or failed cases without calling preparation acceptance. |

A changed source hash, content version, destination or ranking/index revision
requires rechecking the affected fixture before reusing its result. Reuse
unaffected evidence with its original pins; do not rerun the entire inventory
or impose a new universal release gate. If an owner or artifact is unavailable,
record that precise responsibility/input gap in UIF-186 and the relevant existing
content/index issue. Source-copy publication does not establish runtime currency.

Keep one result row per fixture/query with: source/control pointer, content ID
and hash, index revision, contextual-entry mapping, ranked results, relevant and
misleading matches, destination/return observations, failure-state observations,
browser/device/assistive evidence, verdict, unresolved gap and responsible role.
All rows start **planned**, with no measured result. Final UIF-186 acceptance
requires qualified actual content and contextual search plus independent evidence;
this four-control sample cannot close the parent help-completeness outcome.

## Source SHA-256 pins

| Path | SHA-256 |
| --- | --- |
| `apps/web/assets/index.html` | `00cf4b964b4c686920171da7c1780d80d3043cad3b15c4cdd1f0666725e7a720` |
| `apps/web/src/app.js` | `ee6543a3c1e0472237dadff1ae4e5590bfd8e0d173f8a1e782adfcba71a1d237` |
| `apps/web/src/insights-ui.js` | `45937c6133b3f70af1c2a0cbc589c9d7d889d5fc190a2dd00afd24a1ec39e863` |
| `apps/web/src/integrations.js` | `675fe4dd36e09fa8afeebd8a5380bd42d86154efee61074da2bd579b384f1543` |
| `apps/web/src/checkout-model.js` | `46c35698eef7389c7627ea87a21edf9f8e402daf2ad0be04172023b1e5bb29ad` |
