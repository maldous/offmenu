# Worker 27 portfolio staging bindings

This proposal binds DK, DM, DO and DZ to the existing shared adapter descriptors
at develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. It is metadata/code only.
It does not execute a parser, download, inspect source bodies, qualify a dataset,
admit records or accept a country. Raw custody stays on Foo. Frida and all
existing source/privacy/denied-action/production/CIX holds remain in force.

Run from this checkout, using absolute paths for metadata and an output whose
parent already exists:

```sh
python3 -m offmenu.refresh.portfolio_worker27 \
  --request "$PWD/tests/fixtures/worker27-staging/retained-metadata.json" \
  --as-of 2026-10-18T05:00:00Z \
  --output /absolute/review-directory/worker27-bindings.json
python3 -m unittest discover -s tests -p test_worker27_staging_binding.py -v
```

The code catalog has 13 source/country bindings and all 24 country/type
requirements. It pins exact retained source/release/manifest/archive identities,
selected shared-code evidence, field selector declarations, native unit/basis
limitations and missing dependencies. It references existing owner27 category
reports without copying source payloads. The supplied observation file records
only previously verified manifest identities; it asserts no payload verification.
The installed default is an inert Python literal in `_worker27_catalog.py`,
returned by `load_catalog()` as a fresh deep copy. The original
`config/portfolios/worker27-staging.json` remains the exact review mirror; focused
transport tests verify its raw hash and canonical equivalence. This default
needs no checkout-relative JSON file in a wheel or sdist. All literal pins,
holds and unknowns are unchanged. Manifest paths are references and are never
followed by this CLI. There is no
dynamic module, expression, source URL, acquisition or adapter-execution option.

The current retained observation assessment yields 12 `missing` and one `held`
binding. All four countries remain incomplete. Dietary directory metadata has
no reviewed shared parser; DZ also lacks a retained dietary reference in the
selected snapshot. Recipes have no bound source in this portfolio package.
OFF candidate ingredients/nutrition are packaged-product assertions, not
national food-composition coverage. Open Prices observations and their locations
are candidates for prices/providers, not a retailer census or an accepted basket.

Each observation joins exactly by binding ID, country, source and release, plus
the catalog's manifest and archive hashes. Complete input-role pins, country
selector evidence and rights evidence are required metadata declarations. These
evidence references are not read or treated as grants. Prices requires all three
roles (prices, locations, proofs); OFF requires products. Field-origin templates
must cover the declared field inventory, including null and zero. The shared
`field_origin_errors` checks identity, exact input pins and scalar coverage.
Templates contain authored placeholders, not source values. Semantic correctness
of a selector, actual bytes, rights, country scope and native units remain for
independent source qualification. No reviewed constants/derived-origin policy is
supplied here, so those origin kinds do not qualify in this binding interface.

Statuses are scoped to each binding. `valid` means **metadata-ready-for-review
only**. `missing` reports absent required metadata/capability, `held` preserves a
catalog hold before observation inspection, `malformed` reports contract errors,
and `stale` requires review at 30 days or older. Structural request errors
(duplicate or unknown binding IDs, invalid JSON) fail the whole request before
output. Diagnostics contain fixed codes; no input body text is echoed. The CLI
returns 0 for a successfully written assessment, including held/missing results,
and 2 for an invalid request or output conflict.

Original acquisition time and later checked-at time are distinct. A manifest's
completion time, filesystem mtime, assessment time or recent check cannot fill in
missing acquisition time. Age is measured at the explicit UTC `--as-of`; a
complete fresh observation is reuse-only and a stale observation is review-only,
both with zero downloads. Shared `MIN_TTL` supplies the 30-day threshold. There
is no generic shared pure cache planner at this baseline: the portfolio reports
age classification only. It does not call the Wikibooks-specific `cache_policy`,
fixture-only registry planner or operational `CachedAcquirer`.

Identical canonical reports replay without rewriting. Different or corrupt
existing output fails; choose a new output path for a changed assessment. The
source identity excludes checking/acquisition/as-of times; the report itself
includes explicit as-of and catalog pins. No cursor, job, service or hidden state
is created. The tool reads only the explicitly supplied request metadata document
(bounded to 512 KiB), and reads an existing output only for exact replay
verification. Default catalog loading performs no filesystem or network I/O.

`observationEvidenceSha256` fingerprints every supplied non-clock observation
field, including exact input-role pins/mappings, country/rights evidence and
origin declarations. `replayIdentity` binds that fingerprint to the complete
catalog contract. Changed evidence therefore changes the persisted report and
cannot exact-replay as a no-op. These are declaration fingerprints, not evidence
file or payload verification. Original acquisition and checked-at values remain
separately visible in `cache`; assessment time remains at report level. Clock
changes do not change the evidence/replay identity but can change the assessment
bytes and freshness status. Held or absent observations are not assessed and
leave both fingerprint fields null; a hold never triggers observation inspection.

Before a future payload run, Morgan must route the exact missing metadata and
rights/selector/dictionary decisions to existing custodians. Owner27 retains
correction ownership; independent review and integrator00 develop integration
are pending. The integrator must verify the live provider/base at its delivery
gate. Product/reference source qualification, full record schemas, semantic
validation, source-specific rights and final admission remain in the shared
pipeline. No shared engine, registry, source permission or hold is changed here.

Official public documentation is retained as schema context:
[Open Prices data](https://openfoodfacts.github.io/open-prices/guides/data/),
[price creation fields](https://openfoodfacts.github.io/documentation/docs/Open-prices/prices/prices_create/),
and [OFF field reference](https://openfoodfacts.github.io/openfoodfacts-server/api/ref-cheatsheet/).
Current documentation does not establish compatibility or permission for the
historical retained releases. Selector declarations are grounded in the pinned
shared adapter code, with unresolved source semantics stated explicitly.
