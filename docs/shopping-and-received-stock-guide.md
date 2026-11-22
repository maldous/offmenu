# From a shopping list to food in your kitchen

Use your shopping list to plan what to get, then record what actually arrived
through grocery unpacking. Checking an item as collected, sharing a list and
confirming a retailer proposal do not add food to your kitchen stock.

This guide describes accepted source at
`1ea77f7bf9eda6f3487a4954bd4dbab72305c15f`. Your deployed version may differ.
It distinguishes the available list and grocery-receipt controls from a separate
retailer-proposal helper that is not connected to those controls at this revision.

## Build and check your list

1. Plan meals for the selected week in **My week**. Check the
   **Use existing ingredients** setting: it determines whether the shopping
   list shows measured gaps after available kitchen ingredients or the full
   measured requirements.
2. Open **Your week’s shopping** in the integrations view. Review both the
   ingredient names and amounts. An ingredient marked **Review source quantity**
   needs your attention; the label is not a quantity of zero.
3. Use **Add anything else** for an extra item and **Amount or note** for your
   own quantity or reminder. This free-text note does not create a measured
   stock quantity or choose a retailer product.
4. Tick a line when collected. This saves a checklist choice. It does not record
   payment, delivery, a substitute, or food received into stock. You can untick
   the line if you still need it. The remove control is available for manually
   added shopping items; planned lines derive from the meal plan.

For example, a planned line showing `400 g` is an ingredient requirement, not a
pack count or a request for a particular retailer’s 400 g product. Check the
package and the actual amount you receive before recording it in your kitchen.
Changes to the plan, week, or kitchen ingredients can change the calculated list.

An empty list says **Plan a meal in My week, or add a shopping item below.**
This does not prove that you have enough of every ingredient: check the selected
week, the pantry setting and any unmeasured recipe ingredients.

## Take the list with you

**Share shopping list** opens the browser’s sharing facility for the names and
amounts of uncollected lines. **Copy shopping list** writes that text to the
clipboard only when you choose it. Check the recipient before sending household
information. If either control is unavailable, use a download.

**Download CSV** includes the list’s ingredient, amount and collected status.
**Download JSON-LD** exports an item list with names and amount descriptions.
These files do not reserve products, check retailer stock, charge an account,
submit an order or import received stock. If sharing fails, use a download;
the app may show **Sharing unavailable. Download the list instead.**

Keep retailer selection, availability, substitutions, payment and delivery
confirmation in the retailer’s own process. A dated price observation is not
proof of current price or stock.

## Retailer proposals: a separate capability

At this source revision, the shopping screen’s share button uses the ordinary
share/copy flow above. It does not invoke the separate proposal/confirmation
helper. There is no retailer-proposal button to find in this screen, and this
guide does not imply that a live retailer connection is enabled.

The separate helper supports an in-memory retailer proposal for a properly
integrated caller. Its intended review sequence is:

1. Preview the current uncollected shopping lines, destination, account/kitchen
   scope, quantities, uncertainties and source records.
2. Review the entire preview. Unknown quantities and units remain unknown;
   a product name or copied source identifier does not establish a usable amount.
3. Explicitly confirm that same preview. A changed list, account, kitchen,
   revision, session or source readback requires a fresh preview. A successful
   confirmation consumes the preview rather than making it reusable.

Even successful helper confirmation returns only a confirmed proposal. It does
not purchase, navigate to a retailer, send a cart, copy the list or save stock.
The helper requires trusted current session/export permission and admitted
source bindings; a destination label alone does not establish these. If an
integration reports an unavailable export scope, missing provenance, an empty
list or a changed readback, return to the current list and review the problem.
Do not treat that refusal as a completed handoff or try to bypass it with an old
preview. Live transport and a user-facing integration need their own supported
implementation.

## Record the groceries you actually received

Once you have the food, use the checkout workflow’s grocery-unpacking mode.
The running checkout identifies this as **GROCERY UNPACKING**. Choose it when
adding newly received food to existing stock. **SHELF RESET** instead replaces
the recorded contents of the selected shelf with the scanned contents; it is
not the same operation.

1. Choose the destination storage area and shelf/container, then open your
   checkout. Scan the items you are putting away. Keep separate locations in
   separate checkouts.
2. Review the staged items and choose **Final receipt →**. This opens a review;
   it has not yet saved those items into stock.
3. Use **Correct** to check each name, ingredient, amount, unit and entered
   expiry. A full-pack amount can be assumed from product data; correct it if
   the pack is partly used. An unknown package amount needs a known quantity
   before it can reliably match measured recipe requirements. A barcode does
   not state how much food you own.
4. Use **Void** to remove an item from the staged receipt, or **Keep scanning**
   to return to checkout. If a product lookup is still pending, the receipt can
   retain an unknown package; read its review note and correct it rather than
   assuming nutrition or ingredient matching is complete. Retained/published
   scanner source items have additional quantity-review requirements before
   saving.
5. Check the receipt’s location and the explanation asking whether to add the
   scanned items to that shelf’s existing stock. Choose
   **✓ Confirm grocery receipt** only when it describes what you received.
6. After **Shopping, settled.**, inspect your kitchen stock and the saved
   receipt. The confirmation describes local/browser saving; follow the app’s
   separate backup or sync status for cloud persistence.

Receipt confirmation adds the staged grocery items to the existing inventory.
It does not automatically clear or reconcile the shopping checklist, record a
retailer payment, or prove every planned ingredient arrived. Record the actual
delivered product and amount, including a substitute, rather than treating a
checked shopping line as receipt evidence. Review ingredient suitability yourself.

## If something does not look right

| What you see | What to do |
| --- | --- |
| A collected item still appears on the list | A tick changes collected status; the list still renders it. Sharing omits checked lines, while CSV retains their status. |
| The amount says **Review source quantity** | Review the original recipe or your own shopping note. Do not invent a weight or pack count. |
| No retailer-proposal control | Use the current share/download options. The separate helper is not wired into this screen at the documented revision. |
| No staged items or a disabled final-receipt action | Choose a location and scan at least one item before trying to finish. |
| An unmapped or unknown product | Correct its details on the receipt. Unmapped ingredients are excluded from meal matching. |
| A request to set a known quantity for a scanner item | Review the item and enter the actual amount/unit; source identity is separate from your stock amount. |
| An account/inventory-space change or a view-only kitchen | Return to the intended editable kitchen and review its saved checkout. Do not continue using a receipt from another scope. |
| A duplicate-item or conflicting scanner-completion error | Inspect the saved receipt and existing stock before trying again; do not rescan everything into another checkout to force it through. |
| Stock remains unchanged after opening the final receipt | Review alone does not save stock. Check whether you confirmed, cancelled, or received a save/permission error. |
| Shopping gaps change after receiving groceries | The pantry setting and current ingredient quantities affect calculated gaps. Recheck unmeasured ingredients separately. |

For a support report, include the app version if available, the control used,
the message shown and whether you were reviewing a list, proposal or grocery
receipt. Omit credentials and private household details that are unnecessary
to explain the problem.

## Source and update ownership

The OffMenu product documentation owner maintains this guide alongside changes
to these callers. Recheck the screen wiring before documenting a retailer
integration as available, and recheck receipt semantics before changing the
stock-saving instructions. Source inspection supports this guide; it does not
establish a live retailer, browser/device acceptance or deployed-version parity.

| Source at the revision above | Behavior documented |
| --- | --- |
| [integrations.js](../apps/web/src/integrations.js) | Weekly measured/unmeasured/custom list construction and export formats. |
| [insights-ui.js](../apps/web/src/insights-ui.js) | Collected checkboxes, manual additions/removal, downloads and actual share/copy caller. |
| [shopping-handoff-owner31.mjs](../apps/web/src/shopping-handoff-owner31.mjs) | Separate source-bound preview and fresh explicit confirmation. |
| [shopping-handoff-model.js](../apps/web/src/shopping-handoff-model.js) | Proposal/confirmation validation; no executed purchase. |
| [checkout-model.js](../apps/web/src/checkout-model.js) | Grocery addition versus shelf replacement and duplicate/conflict checks. |
| [app.js](../apps/web/src/app.js) | Checkout setup, final review/correction, explicit grocery confirmation and local saving. |

The existing [shopping consumer note](shopping-handoff-consumer-owner31.md) and
[destination boundary note](shopping-destination-owner31.md) retain their dated
integration and review limits. Their proposed wiring is not evidence that the
current shopping screen uses it.
