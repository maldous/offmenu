# Find and review a shared recipe

This guide describes the recipe-library interface in OffMenu source version
`284f2ce5b369c5b1a5bd57b9f79386e14993e3dc`. It has been checked against that
source, not a live deployment. Available recipes depend on the collection served
by your installation. No screenshots or device behavior have been verified for
this guide.

## Find recipes

1. In Today, find **Explore the shared recipe library.** Choose
   **Open worldwide recipes**. From Plan, **Find a menu to add ✳** also opens
   the Today recipe view.
2. Enter a dish or ingredients in **Dish or ingredients**. Changing the search
   starts a new result list. Keep searches to 100 characters or fewer.
3. Use **Recipe language** to filter the results already loaded. This selects
   recipe content language; it does not translate the source recipe or change
   the application language.
4. Select **Prioritise recipes using my available ingredients** to restrict the
   loaded results to recipes with at least one required ingredient matched in
   your kitchen. A match is a hint to review, not confirmation that you have
   everything needed.
5. When **Show next recipes** appears, use it to request the next page. The list
   keeps the latest 200 results. Language and kitchen filters apply to those
   loaded results, so a filtered empty list does not prove there are no matching
   recipes in the whole collection.

The status message distinguishes results shown, results loaded and the published
collection total. Searches may take a moment; the interface shows
**Searching shared recipes…** while requesting results.

## Understand ingredient matches

Matching uses inventory on the device within the selected **Cook from** location.
Choose **Whole kitchen** when you want to include all kitchen locations. Recheck
the match after changing that scope. Items marked for review,
items with an expiry date before today, and items without a positive finite
quantity are excluded from the match calculation. Optional recipe ingredients
are excluded from required-ingredient totals.

A matching ingredient name does not establish a measured quantity. The source
compares quantities in `g`, `ml` or `count`, using the source recipe batch. It
does not convert cups or spoonfuls by assuming density. Check both the
ingredient identity and the quantity before relying on a match. No dietary,
allergen or food-safety certification follows from a match.

## Review a recipe for your kitchen

You need an editable kitchen to save a personal recipe. Viewing shared recipes
does not itself give you permission to edit a kitchen.

1. Choose **Read recipe & review quantities**. Read **Source instructions** and
   follow **Original source** to inspect the attributed source and licence.
2. Under **Review for my kitchen**, check each ingredient against the source.
   Edit its kitchen ingredient name, measured quantity, unit and optional status.
3. Enter a positive **Reviewed serving yield**. Every required ingredient needs
   a positive measured quantity and a unit of `g`, `ml` or `count`. Keep at least
   one required ingredient.
4. Read the source scaling notice. The personal recipe uses linear quantities;
   source recipes may describe another scaling rule.
5. Select the confirmation stating that you have reviewed ingredient identities,
   measurements, yield and instructions and choose linearly scalable quantities.
6. Choose **Save my reviewed recipe**. A successful callback displays
   **Your reviewed recipe is saved in this kitchen.** This guide does not verify
   hosted persistence, account synchronization or another device's copy.

Your review creates a personal recipe and retains source provenance; it does not
edit the original source. Personal review is not independent dietary
certification.

Historical OCR candidates can have incomplete ingredient extraction. For those
candidates, kitchen matching and saving a personal recipe are blocked until
complete transcription. Reading or downloading an OCR candidate does not make
its ingredient list complete.

Choose **Download source recipe as JSON-LD** to download the selected source
recipe representation. This downloads the source recipe, not your edited
personal copy. Attribution, licence and source links are retained. Check the
source licence before reuse; a download does not grant additional rights.

## If you cannot continue

| What you see | What to do |
| --- | --- |
| A search failure or collection-validation message | Check the connection and try **Open worldwide recipes** again. An installation must serve a compatible accepted collection; there is no automatic upstream collection fallback. |
| No visible recipes | Check the search and the language/kitchen filters. Filters cover loaded results only. |
| Recipe no longer in this search | Search again and reopen it. Older results may have left the latest-200 list. |
| Open an editable kitchen before saving a recipe | Open a kitchen you are permitted to edit before saving; viewing shared recipes does not grant write access. |
| Confirmation or quantity validation message | Review the yield, required ingredient names, positive quantities, units and confirmation before saving again. |
| Historical OCR transcription message | Do not treat the partial extraction as a ready kitchen recipe. Complete transcription is required; this interface does not provide that workflow. |

Search progress and review messages use status text, and generated ingredient
fields have names for ingredient, quantity and unit. Keyboard, screen-reader,
mobile, tablet and foldable behavior still need qualification on the selected
installation; this source review does not establish those results.

## Source and maintenance

OffMenu's project documentation owner maintains this guide. Review it whenever
recipe discovery, matching, personal review or the corresponding labels change.
Contextual in-app help and search-index integration remain separate work.

Source references for this revision:

- [Recipe controls and dialog](../apps/web/assets/index.html).
- [Recipe-library interaction and messages](../apps/web/src/recipe-library-ui.js).
- [Matching, personal review and export](../apps/web/src/recipe-library-model.js).
- [Discovery requests and collection checks](../apps/web/src/recipe-discovery-client.js).
- [Application integration](../apps/web/src/app.js).
