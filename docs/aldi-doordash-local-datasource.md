# ALDI via DoorDash local datasource

Source ID: `aldi-doordash-au`. This is a local, authenticated-browser catalogue
snapshot, separate from DoorDash's partner API and ALDI's country portals.

Import the retained capture and register it in the local datasource directory:

```sh
python3 -m offmenu import-aldi-doordash CAPTURE_DIRECTORY NEW_OUTPUT_DIRECTORY --register
python3 -m offmenu datasource aldi-doordash-au --food-only --query tomatoes --limit 25
python3 -m offmenu datasource aldi-doordash-au --kind priceObservation --query tomatoes
python3 -m offmenu datasource aldi-doordash-au --kind retailer
```

`OFFMENU_DATA_ROOT` selects the existing local data directory; the default is
`offmenu-data` beside the repository. The per-source `current.json` references
one checksum-bound normalized snapshot. Imports require a new output directory;
registration replaces only that source's current pointer. A directory can also
be passed directly instead of the source ID. Pages contain at most 25 records.

Outputs use the existing unified `1.0` record shape and `offmenu-common/1` graph
schema. `normalized.jsonl.gz` contains products, dated prices and one retailer.
`common.jsonl.gz` preserves recursively typed, citation-bearing source facts.
`records.sqlite` supports bounded local lookup; `manifest.json` records counts,
original snapshot hashes, visibility, and generated file hashes.

Product identity is `(DoorDash store ID, source item ID)`, never a fabricated
barcode. Price IDs include the snapshot release. Prices reference their products
and retailer through source-scoped IDs. Estimated each prices
remain each prices; original pack text is retained without guessed conversion.
Unknown composition, allergens, brand, nutrition and ingredient matches remain
unknown. Food-only filtering uses the captured department classification; it
does not establish that a composite product is one cooking ingredient.

The 16 October 2026 capture covers ALDI at 313 Victoria Street: 2,722 listings
across 23 departments, including 2,150 food/beverage listings. Displayed stock
wording and prices are dated observations, not guaranteed current availability.

All records and graph facts carry `local-restricted` scope. The source is absent
from the public publication policy, and the normalized status is deliberately
ineligible for the public corpus compiler. Registration enables the local CLI;
it does not activate the independently owned DEV7645 browser adapter or deploy
to production. The UI owner can consume the existing page envelope through a
separate controlled integration. Source terms and publication rights still
require review before any public release.
