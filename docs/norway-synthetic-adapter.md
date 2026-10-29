# Norway synthetic adapter

This is an isolated, synthetic-only repository integration of the independently
reviewed Norway adapter. It is not enabled in the shared refresh runner. There
is no source acquisition, historical replay, curation, public acceptance, or
production activation in this change.

## Run from a source checkout

From the repository root, with Python and no extra runtime dependencies:

```sh
python3 -B tools/data-processing/run_norway_synthetic.py --output /tmp/offmenu-norway-synthetic
python3 -B -m unittest discover -s tests -p 'test_norway*.py' -v
```

The script selects only the checked-in four-file synthetic fixture and frozen
lock. It has no input-directory, arbitrary-lock, or historical-scope option.
An existing output directory must match every rendered byte; retries verify it
rather than replacing it. Use a fresh output directory for a different build.

The review lock pins CPython 3.12.14 and zlib 1.3.2. A different runtime is
rejected by default. To explicitly test the same pinned synthetic data and
implementation on your current runtime:

```sh
python3 -B tools/data-processing/run_norway_synthetic.py \
  --repin-synthetic-runtime --output /tmp/offmenu-norway-synthetic-current
```

That option changes only runtime identity in the in-memory lock. It does not
rewrite the checked-in lock, renew acquisition age, alter any file hash, or
permit real inputs. A different runtime produces a different build key and is
not a claim of byte equality with the frozen review candidate. Unit tests make
their own synthetic locks for their runtime. The frozen-candidate comparison
test is skipped when the recorded runtime is unavailable.

The lower-level `python3 -m offmenu_norway.adapter` interface remains available
for explicit synthetic test authoring. Its synthetic label is a trusted-caller
declaration, not proof of data origin or permission. Never relabel real source
data as synthetic. Its `fixture_lock` helper cannot grant access or source-use
rights.

## Package boundary

The existing `offmenu*` package discovery includes the separate
`offmenu_norway` package. The additive `MANIFEST.in` includes its JSON contract
in source and wheel distributions. The fixture-only script, fixtures, and
review evidence are source-checkout assets; there is no new installed console
entry point. Existing `offmenu` and `offmenu.refresh` imports are unchanged.

## Preserved contract

- The input closure is exactly `en-foods.json`, `nb-foods.json`,
  `en-nutrients.json`, and `en-sources.json`. All sizes and hashes are verified
  before parsing the source bodies.
- The three adapter/contract files are byte-identical to independent review
  revision 2. Unknown, zero, trace, bounds, unresolved text and absent values
  remain distinct. Invalid units, contradictory explicit bases, invalid joins,
  and nonzero-to-zero underflow hold the candidate.
- Source metadata and deterministic candidate bytes remain separate from
  operational acquisition evidence. The original acquisition time controls
  the 30-day reuse window; retransform, 304, and identical-body 200 observations
  never reset it. The helper is a plan, not a download or rights authorization.
- Historical scope, public export, country completeness, and shared-consumer
  acceptance remain disabled or unassessed. CIQUAL is a separate pilot; Fineli
  access/zero semantics and Danish definition/basis/curation holds are unchanged.

## Review provenance

The original artifact manifest is
[`evidence/norway-synthetic/artifact-manifest.json`](evidence/norway-synthetic/artifact-manifest.json),
SHA-256 `f4d0e72048b3d4d5dee2a5258a7511cca8512060a73c95bf046cd4a31427c5ca`.
[`artifact-path-map.json`](evidence/norway-synthetic/artifact-path-map.json)
accounts for all 27 original entries. Eighteen are included here; seventeen
are unchanged, and the adapter test changes only its reference-fixture path.
Nine obsolete output or standalone-report entries are intentionally omitted.
The [verification summary](evidence/norway-synthetic/verification-summary.json)
records the checked pins, test counts, resolved defects, and limits. The full
default suite is not claimed to pass locally: two existing optional test
dependencies were unavailable, producing the same eight import errors before
and after this addition.

`candidate-v2-A` and `candidate-v2-B` are the final reference outputs.
Superseded `candidate-A` and `candidate-B` outputs are not included in the
repository or used by its entry point or tests. The two pinned legacy
scripts under `tests/fixtures/norway-reference/` are read as AST fixtures for
three reviewed functions; their full collectors are never imported or run.

## Stop before historical data

A real Norway run requires a separately authorized selected snapshot and
receipts, verified rights to retain/parse/derive, complete input hashes,
publisher release and provenance, dictionary/unit/basis checks, and a reviewed
historical-input/shared-runner interface under the approved offline boundary.
This integration does not provide those approvals or that interface. The
existing accepted pointer and grant controls remain unchanged.
