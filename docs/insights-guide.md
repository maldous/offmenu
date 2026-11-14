# Review your food history and recorded estimates

This guide follows OffMenu source
`59496c6cf006c16b6ac4859580d0e91374682756`, checked by reading source rather than
using a running account. Live persistence, sync, provider access, downloads and
device/accessibility behavior remain unverified. Labels below are English labels.

## Choose whose records and which dates to inspect

Open **Me → Statistics & history** to reach **Your food observatory.**

1. Choose **Whose records?**: a named person, **Unassigned household**, or
   **All recorded meals**. **Archived member** retains records for someone no
   longer in the current member list.
2. Choose **Period**: 7 days, 30 days, 90 days or 1 year.
3. Set **Through date**, the last day included in that period.

**Logged meals**, **Days with records** and **Different dishes** describe matching
consumption records. They do not establish a complete food diary. **Planned
meals** counts plans in the period separately; that count is not filtered to the
person chosen for consumption. Avoid recording the same meal once for a person
and again for the unassigned household: the all-records view counts both entries.

If the journal is empty, check the dates and record owner first. The message
**Your food journal starts with the next meal.** means there are no matching
loaded entries, not proof that nothing was eaten or that another account has none.

## Read nutrient totals and daily bars

Choose **Explore a nutrient** to change the daily bars. The displayed units belong
to the recorded consumed total, not a per-100-g target. **Recorded totals for
this period** sums the loaded snapshots for the selected dates and owner.

**—** or a blank bar means unknown. **\*** marks a partial estimate; the coverage
text counts known versus total ingredient entries, not the percentage of your
diet recorded. Some bars can be incomplete even when a number is shown. Values
are rounded for display; extra decimal places would not add source accuracy.
Sodium uses supplied sodium where available, otherwise the source's salt-to-sodium
calculation. It remains an estimate from the food data recorded at logging time.

Expand **Meal nutrients & notes** under a journal entry to inspect its individual
totals, source and notes. Snapshots stay as recorded; changing a recipe or product
later does not recalculate old meal entries. Planned portions, consumed portions
and measured nutrient evidence are separate inputs.

## Add a history entry with the right intake meaning

Choose **Log a meal +**, then choose a saved recipe or **Custom meal / food label**.
Set **Date eaten**, **Meal**, **Who ate this?** and **Portions served**. Use the
record owner you intend, rather than leaving it unassigned accidentally.

For a recipe, **Eaten (%) · optional** scales the estimate by the recorded
percentage. Leaving it blank records the serving with unknown intake, even though
the field's placeholder mentions 100. Enter 100 only when that is the completion
you mean to record. A recipe with an active cooked batch asks you to use
**Kitchen → Serve / after meal**, keeping its stock and intake linked.

For a custom meal, enter **Meal name** and nutrient totals actually consumed in
the units shown. Leave unknown values blank; enter zero only for a known zero.
The completion percentage is context here: it does not rescale entered totals.
**What happened to the rest?** and **Meal notes** retain your description; this
history form does not move stock or save a cooked remainder.

Choose **Save after-meal record ✓** and inspect the resulting entry. Read any message
inside the dialog, such as an invalid percentage, missing date/positive portions
or the active-batch notice, before correcting the input. There is no history-entry
editor here. **Delete log** immediately removes that record; it does not undo
cooking, serving or inventory movement. Keep a copy before deleting needed detail.

## Record your own daily comparison value

Under **Daily targets & ceilings.**, select **Record owner**, **Nutrient** and
**Goal type** (**Target** or **Ceiling**), then enter a positive **Daily amount**
in the displayed unit and choose **Save my goal**. This stores your chosen value;
the app does not prescribe an amount or verify that it is appropriate.

Saving switches the history owner and explored nutrient to that goal. One value
is kept per owner and nutrient; saving another replaces it. **Remove goal** removes
that saved comparison. Energy ceilings are refused for named members whose age
is missing or below 18. That input rule is not clinical approval of other entries.

Choose the same owner and nutrient to see its line on the daily bars. **All
recorded meals** does not combine personal goals. The progress cards compare only
the **Through date** day's recorded intake with the saved amount, not the whole
period. **No nutrient data for selected day** and incomplete coverage cannot
establish that a target or ceiling was met.

## Inspect completion, cleanup evidence and milestones

**Completion & leftovers.** uses meals with an explicitly recorded completion
percentage. Its average concerns those entries only. Blank completion is omitted;
it does not count as zero. **Remainder saved** counts marked meals, not a measured
weight of saved food. The chart displays at most the last 30 matching completed
entries. With none, it asks you to enter optional completion after a meal.

**Household cleanup receipts** and **Recorded cleanup evidence** concern the
selected dates for the household, not just the chosen person's meals. Read the
unknown-value and unusable-coverage counts. **Partial measured observations** do
not turn every removed stock item into a measured waste amount or monetary loss.

**Your trophy shelf.** reflects recorded organisation and participation, such as
logging different dishes or dates. It uses the overall loaded profile rather
than the current date/person filter; it is not a nutrition or health assessment.

## Keep measurements and exports in their actual scope

For a member's entered measurements, open **Me → Dietary profiles**, then
**Edit preferences** for that person (or **Add household member +** for a new one).
The form has optional **Height, cm** and **Weight, kg** fields. Choose
**Save member profile** to store the values; blank fields remain unknown. These
are current profile fields, not a dated measurement log or a weight-trend chart.
The Insights route does not offer a health-device import or clinical interpretation.

**Export history CSV ↓** downloads every entry in the currently loaded profile's
food history. **It does not apply the visible person or date filters.** Review
the whole file before sharing it: it includes dates, meal/person labels, dishes,
portions, source and nutrient values with coverage. Blank exported nutrients stay
unknown. A CSV download is separate from an account backup or verified cloud save.

## Look up dated price observations in Shop

Open **Shop**, find **What has this barcode cost?**, enter a numeric **Product
barcode** (4–32 digits, preserving leading zeros), and choose **Find dated price
observations**. This displays observation cards, not a price-history chart.

Saved permitted observations can appear alongside the latest Open Prices sample.
Read each amount, currency, date, location and provenance. Expand **Unified record,
provenance & licence** on a saved card for its retained context. The directory's
country selection filters the observations when set. A matching barcode does not
establish equal pack size, promotion, tax or delivery cost, current stock or a
complete market comparison.

An empty latest sample is not global absence. Messages distinguish unavailable
saved observations from an unavailable latest lookup; retained dated observations
remain historical. For **Account changed. Retry from your current account.**,
check the account before trying again. No result is a guaranteed current offer.

Choose the intended account and private kitchen before editing personal records.
If a member form says the account, kitchen or member changed, reopen it before
saving. Browser-local saving is separate from successful cloud sync. For support
and reporting, see [support and preferences](support-preferences-guide.md).
