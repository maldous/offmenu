# Worker 43 retained-input metadata binding

Selected request: `M-STAGING-BIND-20261018-W43`. Baseline develop:
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This addition owns only
`offmenu/portfolio43.py`, `config/portfolio43.json`, its tests/fixture and this
document. No shared core or production admissions are changed.

## Runnable interface

```sh
python3 -B -m offmenu.portfolio43 --evidence-directory /private/foo/metadata --now 2026-10-18T00:00:00+00:00
python3 -B -m unittest discover -s tests -p test_portfolio43.py -v
```

The directory contains only small, explicitly selected metadata attestations
named `<binding-key>.json`. `tests/fixtures/portfolio43/authored.json` illustrates
the schema. The production CLI uses only the five reviewed portfolio descriptors,
not this fixture as a source registration. `--previous-keys` accepts a small map
of binding keys to previous `metadataKey` strings. Equal keys produce a metadata
no-op when the input remains eligible. Nothing is acquired, normalized, staged,
accepted or published by this command. Exit zero means a complete diagnostics
report was emitted; inspect every source status. A malformed request exits two.

The API `assess_portfolio` isolates malformed/missing peers and uses the shared
`StageResult` receipt shape. These receipts describe a **metadata check only**;
they must not be connected to GLOBAL acquire/normalize/accept stages as evidence
that those stages executed. All 24 country/type cells remain unaccepted,
including the 19 cells without a selected metadata binding.

The default code catalogue is shipped in `offmenu/portfolio43_catalogue.py` as
inert Python literals with a deepcopy-returning loader. Its values exactly match
the unchanged `config/portfolio43.json` mirror (SHA256
`840840b7189f2bdd47734d6de5095abf9b4769ad5bf6fc22f03bdc8541fd7699`).
Installed CLI loading no longer depends on a repository-relative JSON path.
The mirror remains code evidence, not source permission; evidence/replay ingress
still uses the previously reviewed descriptor-safe reader. No shared packaging
configuration is changed.

## Provenance and clocks

Each descriptor pins an exact retained metadata manifest and declares only
already-evidenced fields or explicit code-policy constants. Source fields retain
their manifest JSON pointer and record selector. Null native units/bases are not
converted into nutrient concentrations, prices, quantities or equivalences.
Shared `field_origin_errors` verifies per-scalar origin coverage; the binding
additionally requires exact equality with the configured field/value/selector
declaration. This checks declaration integrity, not the original payload bytes.
The CLI never follows paths inside provenance or reads the named originals.

`originalAcquiredAt` and `validatedAt` are separate UTC clocks. Validation cannot
reset source age. Missing original acquisition time stays unknown. The minimum
window uses shared `acquisition.MIN_TTL` (30 days). A stale input requires review,
without download. Source holds remain effective under every outcome. The content
key excludes current clock and validation age, includes source/release/manifest,
fields, acquisition time and holds, and therefore supports unchanged-content
metadata replay. It is not a raw asset-cache verification key.

A shared `SourceContract`/`qualify` test additionally checks a complete authored metadata packet, exact rights/scope assets, schema/field origins, and refusal of holds, missing operations and corrupt candidate bytes. It is fixture qualification only.

Shared cache tests use `CachedAcquirer` with a tiny authored response and injected
fake transport: no real source/network operation. They demonstrate under-30-day
reuse, stale refusal under reuse mode, and unchanged content after eligible fake
refresh. No private legacy source is inserted into the public acquisition cache.
`disabled_acquisition_spec` returns disabled/held descriptors for integration
inspection; validation refuses them even if the manifest claims a public licence.
The metadata API exposes no force/revalidate/download switch.

## Exact retained source boundaries

| Binding | Type and current evidence | Remaining blockers |
| --- | --- | --- |
| BZ school2019 | Institutional recipe source, exact 24-page original and pages14–18 selector pinned by earlier metadata | Recipe-text derivative use and field/yield/unit contract unaccepted; no recipe body read |
| FJ Gateway | Two-page undated merchant menu; effective date explicitly null | Private transcription/use, dated price evidence, literal field/portion semantics |
| RO HICP | Methodological metadata, no numeric observations | Named section mapping and document-specific exceptions; no item-price/basket release established |
| SR Overture | Existing1200 candidates, 13 farm exclusions, four legal holds, prior53 scoped PASS | Original acquisition time unknown in this chain; complete per-datum-origin and selected staging contract not accepted |
| SR EZOTI | Historical government fixed-price publication lead | Table/currency/package/date/use mapping unresolved; not observed merchant offers |

Every real descriptor retains `source-body-processing-not-selected`. The release
labels for undated/catalogue records are metadata identities, not newly accepted
publisher editions. Historical custodian numbers are not proof of current native
custody. Prior output hashes, reviews and original files remain unchanged.

The shared reference adapter supports the Overture **projection-array input**.
Worker43's retained `candidates.jsonl` contains already-normalized singleton
packets. Those are different representations; the binding does not feed the
candidate output back through the raw adapter or reconstruct missing fields.

## Public documentation evidence, 18 October 2026

Eurostat's official [copyright/re-use notice](https://ec.europa.eu/eurostat/help/copyright-notice)
authorizes reuse of its statistical data and metadata with attribution, subject
to individual notices, third-party material and listed exceptions. It does not
require a special written licence where the general permission applies. This
narrows the old generic “unverified licence” blocker: the remaining check is exact
document/field exception applicability and action-specific source binding, not
an assumed need to contact a publisher. No source-specific hold is lifted here.
Editorial EU-owned site content is separately identified as CC BY4.0; that label
must not be blindly assigned to third-party content or every source file.

The official [HICP methodology](https://ec.europa.eu/eurostat/web/hicp/methodology)
describes reference metadata as production/quality documentation and explains
weighted aggregation of indices. This supports keeping methodology, index
observations and actual retail prices/basket quantities distinct. No Romania
HTML body, statistical dataset or failed INS/legal route was fetched or processed.

## Exact shared-interface proposal to integrator00

Integrator00 baseline/interface result5798 and its late-dependency addendum were read with exact supplied hashes. They confirm the absence of a source-neutral pure planner at this baseline; private/held real inputs must not call the operational acquirer.

No shared edit is included. Before actual staging, integrate a reviewed
`SourceContract` supplied by code, with independent expected IDs/counts, complete
schemas/semantic callback, exact rights/scope evidence and all-field origins.
Do not construct it from this config, an evidence hash or CLI values.

`policy.plan_fixture` currently plans only the static registry fixture. A possible
shared addition is a pure retained-input metadata planner accepting a reviewed
source/release/bundle identity, original acquisition time, separate validation
events, explicit holds and clock, returning the existing typed reuse/stale/missing
diagnostics **without opening bodies or granting operations**. Automatic policy
must enforce zero downloads under30days regardless of caller force flags. This
package does not copy that engine, register a fixture as real, seed a cache,
or modify shared acquisition semantics. Integrator00 and independent review own
any shared change and subsequent develop integration.

All source/Finland/Frida/native NO-FR/403/private/credential/action-denial holds,
mandatory auto_review, raw-on-Foo custody, production/CIX and DEV7645 separation
remain. Tests establish only metadata/code behavior, not country acceptance.
