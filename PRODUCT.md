# OffMenu

<!-- impeccable:product-schema 1 -->

## Platform

web

## Brand Commitments

Use a light green canvas (`#d9efda`) for the household app, shared light theme, retailer popup and local pantry demo. Open the landing page with the original blue-and-white OffMenu neon bowl on its dark signboard. Use the compact scanner-frame bowl wherever space calls for a small brand mark.

## Users

OffMenu is for the person standing in a household kitchen with one item in hand, asking “What can we make with this?” They may be cooking for themselves or for people who need different portions or ingredients. They should be able to make one meal decision before they have catalogued the kitchen.

## Product Purpose

Help a household decide what to cook from the food it has. A useful answer names a dish, shows which ingredients and quantities are accounted for, and makes the next decision clear. If a recipe needs more rice than is left in the pantry, show how much is missing. If the amount in the bag is unknown, give the cook a way to check it.

## Positioning

OffMenu connects a particular product on a particular shelf to an ingredient a recipe actually calls for. A carton of milk and a biscuit whose label lists milk can both turn up in a search for “milk”. Only one can supply the milk for a sauce. Keep that distinction visible when suggesting a meal, scaling portions or explaining a shopping gap.

## Operating Context

Scanning a barcode is one way to begin. Someone can also start with a loose ingredient or a dish they have in mind. At the shelf, a lookup answers “What is this?” Checking in a purchase is a separate decision. A household can review and correct several scanned items together before confirming what arrived and where it belongs.

The first delivery phase runs from product identification through a menu. The longer-term aim is to connect what was served, what each person ate and what was saved to the next plan and shopping trip. Parts of that journey exist in source. The README records the delivery status of each stage. [Household workflow and delivery status](README.md#the-complete-loop)

## Capabilities and Constraints

The browser app includes barcode lookup, kitchen stock, recipe planning and cooked-batch records. Product coverage varies by source and release. Ordinary barcode decoding processes the image on the device. Receipt-image review has a separate consent step.

Nutrition estimates depend on the ingredients used, their measured quantities and the serving size. Keep gaps visible. For future retailer orders, let the household review the order before submission and add goods to stock when someone confirms what arrived.

## Product Principles

- **Make one item useful.** Let the cook find a next step with a partially recorded pantry. Show what is on hand, what needs checking and what the recipe still needs.
- **Keep the reason for each answer visible.** Preserve original product labels, recipe variants and sources. Show the units and serving basis behind a quantity or nutrition estimate, and mark missing values as unknown.
- **Count food once.** Cooking draws from ingredient stock. Serving, eating and saving leftovers describe different events. Recording tomorrow’s lunch from a saved batch should draw on that batch once.
- **Let each person decide what to share.** Plan around individual portions, allergies and preferences. Shared pantry access and access to personal health or intake history require distinct permissions. Suggestions to change a preference need that person’s confirmation.

## Accessibility & Inclusion

A cook can have one hand occupied, be unable to aim a camera or need a quiet kitchen. Keep manual barcode entry, photo input and no-barcode food entry available as alternatives. Design for large targets and reduced motion. Let people choose sound, vibration and spoken feedback. Preserve original food names alongside localized interface text. [Scanner and kitchen requirements](README.md#scanner-and-kitchen-decisions-to-preserve)

## Evidence on Hand

- The recipe coverage tests use measured pantry lots to exercise a concrete question. When a recipe calls for rice twice, how much remains for the second step? They also distinguish an unknown amount from a measured shortfall. [Recipe coverage examples](tests/web/recipe-ingredient-coverage.test.mjs)
- The household design records the intended meaning of a serving, an intake entry and a saved portion. Use it when a screen asks someone to record what happened after cooking. [Consumption and inventory design](docs/consumption-inventory-integration-design.md#phase-two-household-loop)
