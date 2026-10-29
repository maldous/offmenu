# Worker 39 — retained UK CoFID validation

Validated 1,000 actual retained CoFID 2021 records against the workbook and existing normalized rows, with 1,000 code+name identity matches. Selected the first 1,000 food rows per composition sheet, joined by exact code and name; this is a bounded window, not a statistically representative sample or release admission. No duplicate source code appears in this window. The existing code+name hash preserves disambiguation; the focused test checks same-code/different-name separation without claiming a fabricated source duplicate.

The read-only adapter is scripts/local-data-validation/worker-39.py. Default output is a validation report on stdout. Use --format records for source-scoped JSONL records from the same verified read. --limit accepts 1–1000. --data selects an already-held data root and missing input stops with an exact held path. Use the bundled Python runtime with existing openpyxl; no installation is needed. There is no write, ingestion, publication or network code.

Example invocation:

    /home/user/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/local-data-validation/worker-39.py --limit 1000

The report pins the retained manifest, compressed normalized file, XLSX workbook, official retained page, revision 2021 and selected adapted record content. The manifest archive digest is a digest of its sourceFiles JSON array, not a binary archive or record digest. Manifest/file hashes and before/after custody match. The page links OGL 3.0 and the manifest attributes Public Health England; this is retained rights evidence, not a fresh independent licence clearance.

Concrete findings:

- scripts/import-national-tables.py:cofid reads only Proximates, Inorganics and Vitamins. The workbook has Vitamin Fractions, detailed SFA/MUFA/PUFA tables, Phytosterols and Organic Acids. In this window, 206,000 missing component cells include 19,296 numeric observations (including real zeros). The adapter retains all composition table metrics as separate sheet/component/column observations instead of overwriting source definitions.
- scripts/align-national-common.py:graph passes the food-level basis to quantity for every nutrient. originalMetricFields retains native metadata, but the typed metricValue uses the wrong denominator for 10,070 cells, including 2,192 numeric observations. Ackee record 13-145:0d9ae4876b has TOTn6PFAC = 4.30 g per 100 g fatty acids at Proximates row 4, column 29; existing canonical quantity labels it per 100 g food. The adapter retains the fatty-acid mass basis. Explicit /100g Food headers retain food mass; they do not inherit beverage volume.
- Seven alcoholic beverage records retain the workbook's default 100 ml basis; 993 other food records use 100 g. No density or mass/volume conversion is inferred. The focused test checks real drinks and food records.
- Tr and N remain null with trace and present-no-reliable-amount qualifiers. Existing normalization preserves those meanings but drops the original lexical tokens in 6,720 imported cells. The adapter retains raw original cells as well as parsed values. Across all adapted worksheets the window contains 9,868 Tr and 3,579 N cells; ND was not observed. ND handling is tested as parser boundary behavior, never reported as a source occurrence.
- Previous source-code metadata is missing from 628 imported records in this window. The adapter retains the original seven metadata cells per worksheet, including previous code, references, description and footnote. Missing values remain null.

The adapter reads composition worksheets only. Notes and 1.2 Factors are not adapted food composition records. Actual header/description, code, row, column, source file and revision remain attached, and record digests describe the adapted evidence, not original XLSX row byte ranges. No shared schema, owner01 importer, handler or corpus file was modified.

Six focused tests pass, including a reproduction of the existing aligner denominator behavior on the actual retained Ackee metric. That reproduction extracts only the actual pure dimension/quantity functions from source, without running acquisition entrypoints or substituting a validator. No complete canonical graph/schema validation is claimed.

Pickup: fresh locked develop fetch completed 2026-10-14T11:37:26.581484Z, base 5f5bdb6ae716cbf80fab1e174d1af2e354468ead, branch feature/local-data-validation-39-20261014. Prior USDA discovery and qualification commits remain on their original branches. Only the owned adapter, focused test, report and note are changed. Independent review and qualification by owner01/63, then local consumption by owner02/05, remain outstanding. No full dataset admission follows from this bounded validation.
