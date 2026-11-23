# Find and use recipes saved in your kitchen

This guide covers the local recipe journey in OffMenu source
`56026538d15d29f6f5afd427294a82be69557908`. It describes the source, not
a verified running installation or a particular browser or device.

## Find recipes

1. If you already have an OffMenu recipe JSON file, open **Profile & backup**,
   then **Backups & recipe imports → Import recipes (offmenu JSON)**. Choose a
   file no larger than 2,000,000 bytes. A kitchen backup, PDF or shopping CSV
   is not a recipe import. If an existing recipe has the same ID but different
   details, OffMenu stops the import and keeps the existing version.
2. Open **Today**. Expand **Adjust portions, diners & filters**, then use
   **Find a dish or ingredient** to look through recipes in this kitchen.
   Choose **Whole kitchen** in **Cook from** to include all your locations;
   check **Show** if the current availability filter is too narrow.
3. To see imported recipes that still need measurement review, select
   **Include imported recipes needing review**. **Household portions** changes
   the portions considered; it does not tell OffMenu how much anyone ate.

**Lookup unavailable** in the shared recipe area means the public catalogue
cannot be searched in this version. It does not mean a particular recipe is
missing. There is no automatic switch to an external recipe source. A recipe
you have already saved or imported is a separate path.

## Understand ingredient matches

On a recipe card, expand **Ingredients, quantities & directions**. Read the
quantities and steps, and check the recipe's source credit and licence shown
there. If **Original ingredient wording** appears, it preserves the supplied
wording; it is not a confirmation of a measured amount.

**Ready to cook** refers to the measured stock available within the selected
scope. **Ingredients to add** identifies shortages. **Review source quantities**
means information is still needed; do not treat an unknown amount as zero or
assume two names mean the same ingredient. A match is not an allergy, dietary
or food-safety assessment.

The **Food data & estimated nutrition** section describes estimates based on
matched ingredients and compatible amounts. Missing measurements or nutrition
values stay unknown. Source credit does not grant permission to publish or
reuse the recipe beyond its licence.

## Review a recipe for your kitchen

To plan a saved recipe, open **Plan** and choose **Day to plan** and **Meal**.
Return to **Today**, check **Household portions**, and choose the recipe's
**Add to [day] menu** button. Check the planned meal in **Plan**. Adding the
meal does not cook it, deduct ingredients or record anything eaten.

For a recipe with measured quantities, **More recipe options → Cook this
meal** may be offered. A disabled cooking action is not a prompt to guess a
quantity or override a check for selected diners. See
[record cooking and serving](kitchen-planning-guide.md#record-cooking-once) for
the separate steps.

## If you cannot continue

| What you see | What to do |
| --- | --- |
| No matching menus in the recipes saved on this device | Choose **Clear filters** if offered. If this kitchen has no recipes, import an OffMenu recipe JSON file you are permitted to use. |
| Lookup unavailable in the shared recipe area | Work with recipes already in this kitchen, or import your own eligible recipe file. Retrying the local recipe filter does not search the public catalogue. |
| No new recipes to import | If the file contains identical recipes that are already saved, no new copy is created. Check the current kitchen before trying again. |
| Invalid recipe file or matching ID with different details | Use a valid OffMenu recipe JSON file. Review differing versions before retrying; the import does not silently replace an existing recipe. |
| Quantity needs review | Read the original wording and verify the amount before relying on a match or recording cooking. |

Read the visible status as well as the cards. Where a result includes a
disclosure, its heading names the content to open. This guide does not verify
keyboard focus, screen-reader output, cloud sync or device behavior.

## Source and maintenance

OffMenu's documentation owner maintains this guide alongside the recipe
controls and source changes. Recheck the guide if discovery availability,
import requirements, or local recipe actions change. Existing search-index
and contextual in-app Help changes are separate work.

- [Recipe, import and plan controls](../apps/web/assets/index.html).
- [Local recipe discovery, import and plan binding](../apps/web/src/app.js).
- [Public catalogue availability boundary](../apps/web/src/public-catalogue-boundary.js).
