# Record food, plan meals and track cooked portions

This guide describes OffMenu source version
`284f2ce5b369c5b1a5bd57b9f79386e14993e3dc`. It is checked against the browser
source, not a live installation. It does not establish account persistence,
sync, device behavior, dietary suitability or food safety. Use the kitchen you
intend to change and check its permissions before recording changes.

## Add food to Kitchen

1. Open **Kitchen** and choose **+ Add food**.
2. Enter a **Name** you recognize and an **Ingredient identity** for recipe
   matching. These are separate fields: a product name is not a verified
   ingredient match.
3. Check **Amount** and **Unit**. Enter the amount actually available rather than
   accepting the initial value without checking it.
4. Choose **Put it in**, then enter a package date if you have one and select
   **Use-by** or **Best-before** as appropriate to the entered label.
5. Choose **Add to my kitchen**. If validation fails, read the message in the
   dialog and correct the fields before submitting again.

This creates a manually entered inventory item. An ingredient identity entered
here is your mapping decision; it does not independently verify the package.
An entered date is not a generated shelf-life recommendation.

Checkout modes have different effects. A finished shelf-reset checkout replaces
the recorded items in that exact area and shelf with its reviewed items. Grocery
unpacking adds items to existing inventory. Cleanup removes the reviewed amount
from existing items at the selected source location. A paused checkout is not a
completed inventory change; review the final receipt and location before
finishing. This guide does not qualify camera or barcode recognition.

## Find a meal and add it to Plan

**Today** shows recipe suggestions. Use **Household portions**, **Find a dish or
ingredient**, **Cook from** and **Show** to narrow the view. **Whole kitchen**
includes all locations in the suggestion scope; a selected location limits it.
Normal browsing shows up to 24 results. Search, a status filter or
**Explore all quantified recipes** expands the result list.

Read **Ingredients, quantities & directions** before planning. A **Ready to
cook** badge means the source's measured-ingredient check found sufficient
eligible stock in the selected scope. It does not certify package suitability,
allergen safety, freshness or the correctness of your inventory.
**Include imported recipes needing review** can show recipes whose original
quantities still need review. An unknown quantity is not a zero requirement.

1. In **Plan**, choose **Day to plan** and **Meal**.
2. Choose **Find a menu to add ✳** to return to the Today recipe view.
3. Review **Who is eating?**, portions and the recipe's quantity and household
   notices.
4. Choose the recipe's **Add to [day] menu +** button. Return to **Plan** to
   inspect the entry, date, meal slot and portions.

Adding a plan does not deduct ingredients or record consumption. **Remove** on
a plan entry removes that entry; it does not undo an already-recorded cooked
batch or delete a consumption record.

Use **Selected day** or **Whole week** for the plan totals. **Use existing
ingredients in shopping lists** controls whether recorded inventory is used to
calculate measured gaps. Missing or unmeasured ingredients and missing nutrient
data remain unknown; **No measured ingredient gaps** is not a claim that every
ingredient has been measured. Review any **Unmeasured ingredients to review**
and unresolved-reference notice. Planned nutrient totals are estimates for the
planned portions, separate from actual consumption.

## Record cooking once

Choose **Cook this meal** from a recipe or plan entry, then review **Cooked
portions**, **Cooking date**, ingredient amounts and directions. Optional
ingredients are omitted from stock allocation; edit the recipe beforehand if
you intend to include substitutions. Where the dialog requests it, review the
actual packages and preparation for the selected diners before checking the
confirmation. That is your decision, not OffMenu certification.

**Confirm cooked · deduct ingredients** deducts the measured raw ingredients
and creates a cooked batch. Cooking requires complete recipe quantities and
enough matching stock in compatible units. It excludes lots needing review,
nonpositive quantities and dates before the cooking date. Unlike the suggestion
filter, the cooking callback supplies the kitchen's full inventory to allocation;
do not assume **Cook from** limits the actual stock deduction. Review the
resulting inventory and batch.

The new cooked stock starts in **Fridge / Cooked meals**, with no entered expiry
date. This is a source default, not advice about suitable storage or shelf life.
Open **Kitchen** to review the batch and record its date.

If the source reports missing ingredients or incomplete quantities, correct the
inventory or recipe before confirming again. For a plan already linked to a
cooked batch, use that batch's serving action rather than cooking it again.
The source guards an existing active batch for the same plan entry, but that is
not a reason to repeat an uncertain action or assume a separate unplanned cook
is automatically the same operation.

The optional timer and keep-awake controls are conveniences. Keep-awake depends
on browser support and permission. The timer's completion message says to check
the food; neither control establishes that cooking is complete or safe.

## Serve from the cooked batch

In **Kitchen**, choose **Serve / after meal** for the batch.

1. Enter **Portions served now**, within the amount remaining.
2. Choose **Record owner** and **Date eaten**.
3. Optionally enter **Percentage eaten**. Blank means unknown intake, not zero
   food eaten.
4. Choose the **Uneaten part of this serving** action and select **Save serving**.

When a percentage is known and the remainder is **Saved as cooked stock**, the
uneaten part stays in the batch. **Discarded**, **Shared** and **Unknown / skip**
do not retain that part as saved cooked stock. If percentage eaten is blank, the
entire served amount is drawn from the batch even if **Saved as cooked stock**
is selected: the source cannot infer an uneaten quantity from unknown intake.
Unserved portions stay as cooked stock. Sharing a remainder does not infer what
the recipient ate.

Serving records stock movement and a meal-history snapshot. Nutrient amounts use
the allocated lots and a homogeneous-dish estimate; unknown completion leaves
intake unknown. If cooked stock has changed and no longer matches the batch,
the source asks you to reconcile it before serving.

**Undo cooking** is available only before any serving or inventory-removal event
has been recorded for the batch. It removes that cooked stock and restores the
original raw allocations when their identities still match. Changed raw-stock
identity can block undo. Deleting a meal log is a different action and does not
restore raw stock or undo serving.

The button **Edit cooked storage / date** currently opens a dialog that changes
the entered cooked date, labelled as a use-by date on save. It does not offer a
location editor in this source. Do not infer relocation from the button name.

## Set freshness reminders and review cleanup

In **Kitchen**, choose **Freshness reminders & cleanup**. Select an
**Inventory item**, review its **Label use-by date (optional)**, and optionally
enter **Estimated check reminder, days from today** and a **Reminder note**.
Choose **Save dates & reminder**.

**Use suggested check interval** copies a previous interval for that barcode or
an example based on the item name. It is not a shelf-life calculation. Choose
it only if it is suitable for the actual item and storage. Leaving the reminder
interval blank preserves an existing reminder; it does not clear it.

The due list includes entered dates and estimated reminders on or before today.
**Start cleanup for this location** opens a cleanup checkout for that item's
location; it does not immediately discard the item. Review what is being removed
and its amount before finishing. Reminders do not automatically delete food.
Removing cooked stock records an inventory-removal event and can make cooking
undo unavailable.

## Keep plans and consumption distinct

Food-history views show logged records, not evidence that every meal was logged.
Blank nutrient values mean unknown and partial estimates remain labelled.
Choosing **Delete log** removes a history entry, not its associated stock
movement. A recipe with an active cooked batch is directed to **Kitchen → Serve
/ after meal** so stock and intake stay linked. Manual consumed totals and
personal goals are user-entered information, not verified dietary advice.

## Source and maintenance

The OffMenu documentation owner maintains this guide when navigation, quantity
rules, plan actions, batch accounting or freshness messages change. In-app help,
search integration, screenshots and keyboard/screen-reader/device qualification
remain separate work.

- [Controls and labels](../apps/web/assets/index.html).
- [Application integration and plan actions](../apps/web/src/app.js).
- [Manual food, cooking and serving controls](../apps/web/src/journey-ui.js).
- [Cooking allocation, serving and undo rules](../apps/web/src/cooking-model.js).
- [Plan quantities and estimate coverage](../apps/web/src/menu-model.js).
- [Inventory checkout effects](../apps/web/src/checkout-model.js).
- [Freshness reminders](../apps/web/src/freshness-ui.js).
- [History, shopping and logging controls](../apps/web/src/insights-ui.js).
