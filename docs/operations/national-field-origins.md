# National workbook datum origins

This opt-in emitter covers the exact AFCD Release 3 and MEXT corrected 2023-main historical projections. It neither grants admission nor lifts source holds. It does not cover CNF, FOODfiles, CoFID, BLS, Sweden, held Frida/Fineli, companions, or other downstream projections. This separately versioned successor includes an actual execution-worker hook; no production admission is added. The prior frozen integration batch is unchanged.

## Fields covered

Every scalar under `data`, including nulls, identifier items and all emitted nutrient metadata, is reconstructed and compared with the historical adapter's actual output before origins are attached. Extra/unmapped leaves, changed values, duplicate mapped nutrient keys, duplicate food identities, unresolved source headers, formulas and changed asset pins fail closed.

- AFCD: food identity/name/classification/derivation and nutrient values use physical cells in `Nutrient-profiles.xlsx`; nutrient labels/units/definitions use the actual located header row, not a presumed row number. Description, sampling, specific gravity and portions use the matching physical `Food-Details.xlsx` row. Blank source cells retain exact iterated positions. Both mass and volume sheets remain distinct. Numeric interpretations retain raw originals and tagged code markers. Energy uses the parsed source-kJ origin plus the pinned 4.184 divisor. Copied energy metadata reuses the respective source field's actual origin; conversion strings are code constants.
- MEXT: food fields and all components use the main workbook's physical row/column. Component codes use row 12; labels include all contributing populated cells from rows 3–5 before distinct text joining. Units are explicitly code constants from the historical column mapping, never represented as source labels. Source-derived sodium chloride is source reported here, not falsely represented as a new sodium calculation. Unknown/trace/parenthesized/text markers are explicit code constants within source-dependent interpretations.
- Adapter-generated identifier systems, basis declarations, reference URLs, empty labels and method strings carry policy-pinned code constants.

Each source origin records input path, SHA-256, sheet, row, column, A1 cell, source field, source food/header identity, original value and original workbook type. The source coordinate is from actual workbook iteration, including blank cells; positions are never guessed from output ordinal. Formula cells used by the mapping are rejected because the historical `data_only=True` cache is insufficient to establish their input lineage.

## Implemented worker hook in this successor

`execution_worker.py` constructs exactly one `NationalWorkbookOrigins` mapper for AFCD/MEXT inside an `ExitStack`, after executing the already-pinned historical collector. It stamps acquisition/release identity, calls `annotate`, replaces the packet with the returned copy, then serializes that annotated packet into `candidate.jsonl`. The regenerated gzip payload is byte-identical to the candidate, and both candidate receipt and manifest hashes are computed after annotation.

The worker stores the reviewed literal `NATIONAL_ORIGIN_POLICY_SHA256` (35141a082fe2048a432ecac9c9672d8224eaaffdc58a6e60e5189fa6dee67838), which the mapper checks against its actual implementation bytes. The digest is included in the generated receipt and manifest as `fieldOriginPolicySha256`. Input hashes come from the verified admission contract, never from workbook assertions. The hook does not modify historical handlers or their pinned hashes.

Before each write, it checks the origin-enriched serialized record against the existing 8 MiB record bound and total candidate bytes against the existing aggregate output bound. Existing 64 MiB per-file, 1 GiB memory, CPU, wall-time and combined-output checks remain unchanged. No production fit is claimed.

Keep output-byte, count, identity and hash checks in place. The origin data increases serialized candidate size materially; existing limits may reject full production candidates. Do not raise limits or claim production fit without a separately reviewed bounded-execution plan. Qualification calls must pass this literal policy digest as a trusted policy pin alongside the exact acquisition input pins, then retain full-schema and source-semantic checks. The integration tests invoke the worker only on authored small fixtures with temporary in-memory admissions; no production data, downloads or Foo jobs are involved.

## Tests and evidence

Run `python -m unittest discover -s tests -p test_national_field_origins.py -v` in the composed tree. Tests create only small authored workbooks and run the unchanged actual historical `records`/`collect` functions. The emitted records are then annotated. Assertions cover coordinates (including a skipped MEXT row), raw text/zero/null, joins, formulas, pin failures, output drift and source/constant/derived separation. Complete coverage on those candidates is not coverage of every national source or production qualification.


`python -m unittest discover -s tests -p test_national_origin_worker.py -v` runs the actual offline subprocess for each source, checks exact serialized source/derived/constant origins, gzip/candidate equality, updated receipt/manifest custody and fixture-only qualification through the shared validator. Removing an origin and refreshing the candidate digest still fails semantic qualification. An isolated worker with a deliberately smaller test-only output limit proves provenance expansion fails specifically at `origin-expanded-output-bound-exceeded` before writing a success receipt. The original limit is asserted unchanged.

The older synthetic AFCD execution fixture now supplies its five named metadata columns instead of relying on missing-header defaults. Test helpers close workbook handles opened by the historical scripts; the pinned parser scripts remain untouched. Full successor composition on the accepted PR41 baseline: 239 tests pass, with no resource warnings in the captured run.
