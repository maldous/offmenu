# Assistant extraction and processing provenance handover — 2026-10-20

## Completed

- Added an offline assistant-intermediate cache/replay module. It performs no
  model/network calls and requires an affirmative source-specific processing
  flag plus evidence before accepting an externally supplied response.
- Cache inputs pin the original and extracted source-segment hashes, schema,
  prompt, parser/transform versions, model/settings identity. Invalid responses
  are quarantined; valid cache replay is deterministic and source-change aware.
- Added a private processing-provenance ledger builder. It records, per asset,
  separate `parse`, `normalize`, and `englishTranslation` stages, including
  method, engine, input/output checksums and locations, date evidence,
  validation status, and unresolved issues.
- Unknown engine/runtime/date facts remain `unknown`; normalization and English
  translation are recorded `not-run` where the source run says they did not
  occur. Agent-stage records must retain instruction version, model identity
  where known, response checksum, and supporting exact source spans/pages.
- No real source was sent to a model and no original was newly acquired.

## Current evidence and limits

The existing local source-faithful run contains 15 assets (13 recipes, two
menus), 83 accepted records, and zero reported failed assets. It identifies
parser `offmenu-source-faithful-recipe-parser/1.3.0`; normalization and
translation flags are false. The run log indicates the date, but per-asset
processing timestamps are absent and remain unknown. The inventory review found no row with both an explicit local original and a
source-specific assistant-extraction grant. Checksum joining the 15 local parse
inputs to the 6,068-row snapshot found no exact matches; those are distinct
evidence sets. No permission is inferred from custody, acquisition, or parsing.
Actual assistant extraction is blocked pending per-source authorization.

The processing ledger itself must remain local until absolute paths and
sensitive source references are sanitized. This handover contains no source
bodies, private absolute paths, or raw assistant responses. It describes
provenance mechanics and current stage status, not rights clearance,
completeness, normalization, translation, or publication approval.

## Verification

- `test_assistant_intermediate.py`: 4 synthetic-only tests passed.
- `test_processing_provenance.py`: 2 synthetic-manifest tests passed.
- `test_source_faithful_parse.py`: 4 tests passed.
- `test_recipe_format.py`: 6 tests passed after installing its declared pinned
  test extra in the ignored project virtualenv.
- Python compilation and recipe-schema JSON parsing passed.
- Actual-run ledger reconciliation passed for all 15 assets: parser artifact
  checksums validated; normalize and translation are `not-run`; per-asset dates
  remain `unknown`.

Fetch remains paused. No push or publication should include private originals,
cache bodies, or unsanitized ledger rows.
