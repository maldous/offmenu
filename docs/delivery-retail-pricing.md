# Worldwide delivery retail pricing

`delivery-retail-global` is a local partner-neutral import and lookup datasource, open to any partner and market. It is not a live worldwide feed. `corpus/delivery-partners.json` is discovery metadata, not another work tracker: 34 partners, with evidence and unresolved coverage. Directory countries do not imply grocery service or captured inventory. Seventeen entries remain unverified candidates.

The initial registered snapshot re-expresses the existing 2,722 ALDI/DoorDash AU observations. It does not add 2,722 independent observations. `upstreamEvidence` links each row to the original capture/hash/line and explicitly marks the duplication. Use one representation when aggregating. No non-Australian prices have been captured in this dataset yet.

## Local use

```
python3 -m offmenu delivery-partners
python3 -m offmenu import-delivery-prices observations.jsonl /absolute/new-snapshot --register
python3 -m offmenu datasource delivery-retail-global --kind priceObservation --query tomato --limit 25
```

Output directories must be new; a successful registration changes only the local current pointer. Older snapshots remain available by path. The existing ALDI datasource continues to work. No public runtime adapter or production change is included.

## Input contract

UTF-8 JSON Lines, one captured observation per line. Required fields:

- `partnerId`: lowercase slug; partner need not already be in the discovery registry.
- `storeId`, `itemId`, `observationId`: nonempty original identifiers. Keep observationId stable on reimport, change it for a new observation. They never become barcodes.
- `name`, `retailerName`: source names, any language.
- `country`, `currency`: uppercase two/three-letter codes. The importer checks format; the source collector must verify actual ISO assignments and currency applicability.
- `amount`: finite nonnegative number, `observedAt`: ISO timestamp with timezone.
- `sourceUrl`: public HTTPS evidence URL without account credentials or personal address.
- `priceDisplay`: literal displayed price, `priceBasis`: per-pack, per-unit, per-weight, estimated-weight, or unknown.

Optional: `language` (BCP 47; defaults und), `packLabel`, `brand`, `categoryScope`, `availability`, `availabilityText`, and source-evidence objects `unitPrice`, `promotion`, `membership`, `tax`, `fees`, `upstreamEvidence`. Missing conditions remain null. These objects preserve evidence; no automatic discount, tax, unit-price or checkout calculation is performed. Collectors must exclude account, delivery-address, payment and session data.

Identity includes partner, country, store and item. Prices additionally include observation identity. Multiple dates can coexist. Conflicting product metadata within one snapshot fails validation: separate product-version captures instead of silently replacing facts. Source-scoped identities do not infer product or ingredient equivalence between partners. Original currencies are never converted; delivery prices are not asserted to equal shelf prices.

Normalized records, common-graph records and readonly paginated SQLite follow the existing OffMenu formats. Raw input is preserved and checksummed. Snapshot status remains `normalized-local-restricted`, publicationEligible false. Source terms and republication remain separate from permission to view a catalogue.

## Remaining coverage

Capture actual retailer listings store by store using publicly accessible catalogues or authorized account/export access; retain market, date and price conditions. Directory presence alone never completes coverage. Store-specific login, geography and rights requirements remain unresolved until inspected. The existing data/UI owner retains browser runtime integration and independent acceptance. Production and CIX remain paused.
