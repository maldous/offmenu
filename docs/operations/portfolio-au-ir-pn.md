# AU / IR / PN retained-input bindings

Selected request: M-STAGING-BIND-20261018-W03. Base develop snapshot
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`; pending PR42 code is not imported.
Owned paths are this document, `portfolio-au-ir-pn.json`,
`offmenu/refresh/portfolio_au_ir_pn.py`, and its dedicated test file.
There are no shared-core, source-reader, runner, production or admission edits.

The fixed runtime catalogue is now the inert literal Python module
`offmenu/refresh/portfolio_au_ir_pn_catalogue.py`, automatically included by the
existing `offmenu*` package discovery. The JSON remains a checkout evidence copy,
not a runtime resource dependency. Literal equivalence covers every source pin,
hold and unknown; `catalogue()` returns an independent copy. No shared packaging
configuration is changed. Wheel/sdist loading must work outside the checkout
without a `docs/` directory; this addresses live PR43 P1 comment4305926950.

The catalogue contains six trusted portfolio declarations: AFCD Release 3,
ABS 2025 statistical weights, three FSANZ notices, the IR PERSIAN supplement v1,
and two explicitly missing/held PN inputs. Paths and SHA256 references identify
retained metadata evidence on the selected local executor; the tool never follows those paths. It does
not copy raw bodies, third-party assets or credentials. Provenance and counts in
the referenced manifests retain their original scope. Historical manifest
`accepted` counts do not become STAGING acceptance.

## Repeatable metadata preflight

From the repository root, create a small metadata envelope from the declarations:

```sh
python3 - <<'PY'
import json
from offmenu.refresh.portfolio_au_ir_pn import catalogue
rows = {}
for spec in catalogue()['profiles']:
    row = {k: spec[k] for k in ('sourceId', 'releaseId', 'country', 'dataType',
                               'inputs', 'originalAcquiredAt')}
    row['evidenceSha256'] = spec['metadataEvidence']['sha256']
    row['validatedAt'] = '2026-10-18T00:00:00Z'
    rows[spec['bindingId']] = row
with open('/tmp/worker03-metadata.json', 'x') as stream:
    json.dump(rows, stream)
PY
python3 -m offmenu.refresh.portfolio_au_ir_pn --metadata /tmp/worker03-metadata.json --now 2026-10-18T00:00:00Z
```

Expected exit2: real declarations remain held or missing; no production readiness
is asserted. The explicit clock makes receipts repeatable. Input is limited to
256KiB; duplicate keys, nonfinite values, foreign source/release/country/type,
changed declared input pins and changed acquisition evidence fail closed. Sources
receive separate `StageResult` receipts, so one malformed source does not suppress
peer diagnostics. Unknown binding IDs fail the batch rather than being ignored.

`inspect_metadata(spec, envelope, now=..., previous_key=...)` is the caller-facing
pure interface. `spec` is reviewed application configuration, never a manifest
override. The CLI loads only this package's fixed catalogue. A ready **authored
test** declaration returns `succeeded`; the same binding key returns `reused`.
The caller owns retained receipts; no cache writes/pointer promotion happen here.
Validation timestamps are excluded from the key, original acquisition time is
bound to its evidence and included. Unknown AFCD original acquisition stays null:
its manifest `completedAt` is not substituted for a download time.
Unknown age emits `unknown-no-download`. Every result explicitly reports
`metadata-intent-only-generic-planner-unsupported`; this narrow portfolio intent
does not implement a shared pure cache planner or an operational source adapter.

The local executor metadata entrypoint rejects symlinks and nonregular files. It opens a
regular descriptor with nonblocking/no-follow flags, verifies descriptor identity
against the pre-open stat, bounds reads and rechecks identity/size/timestamps after
reading. FIFO/device/directory inputs and swaps fail with typed errors; a read
failure cannot modify metadata bytes or run a source operation. This is the
owned metadata-file boundary only, not a shared reader or cache engine.

Under30 days, metadata preflight requires zero downloads; at/after30 days it emits
review-required-no-download. A later validation never restarts that clock. Rights
and source holds apply even inside the cache window. This is a no-network
preflight contract, not an implementation of online refresh, byte verification,
conditional HTTP or shared cache storage. Revalidation/force-download library
options are deliberately not exposed. Cache reuse never means current recall
applicability. Changed content changes the key, but only independently qualified
source bytes can justify new pins or acquisition evidence.

## Shared validators, field origin and native semantics

This package calls shared `core.strict_json` / `timestamp`,
`acceptance.fingerprint`, `field_provenance.field_origin_errors` and
`global_run.StageResult`. The synthetic fixture exercises the actual shared
`SourceContract` / `qualify` path with `fixture=True`; it cannot supply production
acceptance. No shared engine is copied. The `origin_errors` hook checks structural
per-datum source/derived/constant coverage; it cannot prove a coordinate/value or
scientific equivalence. It must accompany the existing reviewed schema and
source-specific semantic callback before a real `CandidateArtifact` is selected.
No SourceContract is constructed from this catalogue.

Each selector declaration carries an evidence pin and explicitly unaccepted
locator status. ABS has sheet/cell/type/format coordinates, not prices; the IR
candidate has page/table/line/column and dimensionless correlations with one
quarantined point/CI anomaly. FSANZ uses label/descendant-field text only and keeps
GTIN/lot/applicability unknown. AFCD retains six workbook pins and two native
bases,100g/100mL; component unit/definition allowlists and per-datum serialized
origin mappings still need exact selection. Do not use generic site CC BY4 to
replace the AFCD Data User Licence Agreement, or copying rights as ingredient
equivalence evidence. Metadata inspections are not new legal grants.

All six country-required types remain required, with exact coverage evidence
pins in the catalogue. Research correlations, CPI weights, recall names and a
regional catalogue do not satisfy missing national recipes, ingredient identity,
retailer register, item prices/baskets or adopted dietary-reference requirements.
PN MPI original remains missing under a no-retry challenge hold. Regional PNDB
licence, actual body, units/bases and PN applicability remain unknown. No PN body
or policy is opened, and no category is declared not applicable.

## the product integrator interface request and next dependency

No shared-interface patch is included. Please review whether to extract an
existing source-neutral30-day planning helper from `core.cache_policy` /
`policy.plan_fixture`: their current identities are Wikibooks/fixture-specific.
Desired callable: trusted source/release/bundle identity + evidence-bound
original acquisition/validation timestamps + explicit UTC clock -> deterministic
reuse/review-required receipt, always no network and never resetting acquisition.
Retain existing callers and force-mode semantics; a future automatic adapter must
not bypass the under30-day zero-download rule. This is a proposed interface for
00, not worker03 permission to edit shared core.

For an actual portfolio staging run, the product maintainer must select exact reviewed source
schemas, per-datum selector/semantic contracts, source-use conditions, independent
scope/count/ID digests and the existing execution resource boundary. FSANZ
field-origin licence, PN finite parsed-body custody and AFCD original acquisition
remain typed input blockers. Only then bind generic factories to source stages;
qualification/curation/common graph/acceptance remain distinct. Independent
approval and develop integration of this code must precede another request.

Verification: `python3 -m unittest discover -s tests -p test_portfolio_au_ir_pn.py -v`.
Authored tests cover valid/missing/held/malformed/stale inputs, peer isolation,
identity and cache drift, null provenance, immutable input declarations and shared
fixture-only qualification. Source bodies and old country tests are not replayed.
Finland/Frida/nativeNO-FR/403/private/credential/denied-action restrictions,
production/CIX pauses and separate DEV7645 custody all remain unchanged.
