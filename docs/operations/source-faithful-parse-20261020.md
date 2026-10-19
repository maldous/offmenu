# Source-faithful parse handover — 2026-10-20

## Result

The prior structural-only result (`10d0f62e…`, `semanticParsingPerformed=false`) is not represented as semantic parsing. This local run used retained, receipt-backed originals and produced 83 usable records:

- **AU / English:** 13 retained Eat For Health recipe HTML originals → 13 recipe records, 84 ingredient lines, 16 ordered method blocks, and 208 raw nutrition table assertions (16 per recipe, when table rows were present).
- **MF / French:** Calmos Café 34 menu items and Ocean82 36 menu items → 70 menu records with source names, section/category when found, prices/currency lexemes, source card locations, and no recipe matches inferred.
- Total: 15 retained source assets, 83 accepted records, 0 rejected records in this selected HTML queue, 115 ingredient lines across the recipe set, 16 ordered steps, 208 nutrition assertions, 70 menu items.

These are evidenced local scopes, **not country/corpus coverage claims**. The run did no download, OCR, normalization, translation, canonical identity merge, or English gold admission. Missing source acquisitions remain a separate later concern.

## Private local outputs on Foo

- Run manifest and exact per-asset input hashes: `/home/user/src/offmenu-data/parsed-source-faithful-20261020/run-manifest.json`
- Aggregate summary: `/home/user/src/offmenu-data/parsed-source-faithful-20261020/summary.json`
- Actual source-linked sample: `/home/user/src/offmenu-data/parsed-source-faithful-20261020/DEMO.json`
- Recipe JSONL and per-source manifest: `recipes/AU-EATFORHEALTH/<run-key>/recipes.jsonl` and `manifest.json`
- Menu JSONL and per-source manifest: `menuItems/{MF-CALMOS,MF-OCEAN82}/<run-key>/menu-items.jsonl` and `manifest.json`
- Historical logs for initial run and immutable-output-conflict repair attempt remain on Foo under `logs/`; neither is published.

Records point to the field dictionary and source recipe/menu template by version. Every retained record includes original SHA-256, extracted-text SHA-256, release/citation, language/country evidence, parser version and source-span hash/UTF-8 locator. Recipe identities and menu-to-recipe candidates stay unresolved. Nutrient and ingredient amounts remain raw lexemes, with source units/bases kept separate from null interpreted values.

## Resume

The confirmed initial HTML run is complete. For a future parser version or a deliberately new isolated parse, use the receipt-pinned runner, which takes the existing writer lease non-blockingly, has no network code, checkpoints each asset, and rejects conflicting output instead of replacing it:

```bash
python3 /home/user/offmenu-global-collection/parse-worktree/scripts/run-source-faithful-parse.py \
  --output /home/user/src/offmenu-data/parsed-source-faithful-20261020-vNEXT \
  --lock /home/user/src/offmenu-data/owner-collection-runtime/collection/fixed-selection.lock
```

Use an unused versioned output directory for a new parser version; do not rerun into a previous immutable run-key path. The focused run processes one writer because these HTML pages are small; the user-specified Foo CPU/RAM capacity is not a reason to parallelize a single shared output. Inspect the emitted `latest-run.json`/versioned run manifest and output logs after launch.

## Rights and exact limits

Source receipts for the owner-03 recipe collections explicitly say unchanged private research only and do not grant commercial, derivative, normalization, translation, gold, or republication rights. The Calmos and Ocean82 receipts also say their reuse licence is unverified and local custody only. Accordingly, source-derived records and the full demonstration stay private on Foo. No English gold data was emitted or claimed. The precise external clearance required to admit those records as English gold is source-owner permission/licence covering the specific transformation and intended use, with attribution terms, for the recipe sources; menu records likewise require verified reuse rights before downstream publication/derivation. Parser completeness is not rights clearance.

The current semantic adapter is only for the three explicit receipt-backed HTML source groups above. Retained spreadsheets, CSV/JSON nutrition sources, ZIP members (including AUSNUT), PDFs/OCR, archives and wider existing parsed releases were **not** processed in this run. The retained corpus contains these types; each needs its existing source contract/mapping, permitted format adapter, and output/reuse verification. Encrypted or otherwise access-restricted content remains unopened. We did not restart the broader structural collection job or alter custody/overlap/rights holds.

The existing captured thread still shows `/home/user/offmenu-global-collection/source` detached with unrelated local handover/prompt edits, and `/home/user/offmenu-global-collection/parse-worktree` on the approved parse-records integration branch based on `97baf009`. The latter contains only relevant uncommitted parser assets. The first attempted repository push must remain a fast-forward-only operation from this base. No raw files, parsed corpus bodies, output paths containing content, credentials, or private execution logs belong in Git.
