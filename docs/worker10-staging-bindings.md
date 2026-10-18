# Worker10 retained-metadata staging bindings

This package binds KW/NO/SA/UA retained receipt metadata to deterministic staging
metadata. It opens five explicitly selected documents, capped at 1 MiB cumulative.
Metadata bytes use a single nonblocking, no-follow descriptor with regular-file
and before/after descriptor/path identity checks. A replacement is rejected for
that binding; verification and parsing use the same buffered bytes.
It does not run a country engine, open a referenced payload, fetch data, normalize
food/provider records, accept rights or admit data to gold. All 24 country/type
requirements remain unaccepted. Raw data remains on Foo.

Baseline: accepted develop `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`, confirmed
against remote develop on 2026-10-18. The pending handover/PR42 is separate.
The original Worker10 branch and untracked review directory were preserved.

Run from the isolated checkout with an explicit UTC observation time:

```sh
python3 -m offmenu.refresh.worker10_bindings --validated-at 2026-10-18T05:00:00+00:00 --retained-metadata
python3 -m unittest discover -s tests -p test_worker10_bindings.py -v
```

Omitting `--retained-metadata` produces an isolated missing-input diagnostic for
each binding without opening retained metadata. The CLI prints JSON and writes no
output files. The library `assess(config, metadata_paths, validated_at=...)` accepts
explicit metadata paths. The repository configuration is a reviewed trust input;
changing it requires review and is not a way to release a source-use hold.

The package reuses `core.strict_json`, `core.canonical`, `core.sha`,
`core.safe_path`, `core.timestamp` and `field_provenance.field_origin_errors`.
No shared-core files were changed. No generic payload adapter is enabled because
none of these exact source/release payloads has current processing admission in
this task. The usable route is pinned metadata projection with exact source
pointers, not a copied country parser or a claim that an unrelated adapter fits.

The default `load_config()` uses the owned inert Python catalogue in
`offmenu.refresh.worker10_catalogue`, returning a deep copy without opening a
file. It is included by the existing package discovery in both wheel and sdist.
The unchanged `config/worker10-staging-bindings.json` remains the exact checkout
mirror (SHA-256 `45509d70adc62fffa325b0ca5f6682d0c881c3e4acf625785f755637f670e0cc`).
An explicit `load_config(path)` still uses the existing JSON override reader.
Installed catalogue availability does not make the absolute retained metadata
paths available, authorize their reads or change source holds. Offline packaging
proofs call only the default catalogue loader and forbid actual source metadata
reads; the separate shared eight-sibling packaging correction belongs to 00/64.

Integrator00 baseline/interface receipt5798 confirms there is no generic pure
cache planner at this baseline. `core.cache_policy` is Wikibooks-specific and
`plan_fixture` is registry-only; neither is invoked or spoofed here.
`CachedAcquirer` is operational and may read bodies/fetch, so it is not invoked.
The `cache` object below is Worker10 metadata age/reuse intent only. A shared
source-neutral planner remains proposal-only under Morgan/integrator00; this
package does not add that API or block metadata bindings on its absence.

## Evidence scope

| Binding | Retained evidence | Data prerequisites |
| --- | --- | --- |
| KW Pista House | Receipt for complete 1,056,297-byte, one-page, single-venue menu | Source62 use/custody/attribution qualification and native currency/portion definitions. NOT_HELD is an unknown grant, not a legal prohibition. Separate MOH cookbook timed out at zero bytes; no retry. |
| NO Smilefjes | Receipt records 15,828,219-byte original; extent inspection pending | Exact version, use/privacy/attribution, extent and CSV dialect. Retain prior qualification1340; catalogue CC-BY wording alone does not grant the intended app operation. |
| NO composition | Reused metadata validation: 1 metadata row, 0 samples; exact manifest SHA and recorded 2,121 count | Later source-specific UNKNOWN/UNQUALIFIED derivative rights prevail. Original acquisition time and permitted native selectors unknown; native NO/FR execution hold stays. Per100g edible basis retained; nutrient-specific units/nulls require their own definitions. |
| SA CPI method | Source47 complete method and policy snapshots recorded by receipt | Policy1.2.2 supports the retained method/policy metadata with credit, marked changes and exclusions. No numeric monthly release, price units, index base, basket quantities or numeric custodian established. Method/version labels do not identify a data release. |
| UA eDozvil | Receipt records finite licence JSON, 13,207,431 bytes / 4,044 IDs | Restricted source inspection only. No derivative/app/privacy/provider admission. Prior4522 found economic-activity field null4,044/4,044, so no food subset can be inferred. Date/status meaning remains unknown. Separate Kharkiv CPI is regional index evidence, not item prices. |

All numbers above are recorded or previously validated evidence, not fresh body
measurements. Current execution verifies the selected **metadata** lengths/hashes
only. A source body hash projected from a receipt is a historical assertion.
`releaseId` identifies the exact retained metadata snapshot; publisher edition is
only the separately selected release statement, including its explicit unknowns.
Validation time does not become publication or acquisition time.

Exact source paths, byte lengths, SHA-256 pins, scalar JSON pointers, native
unit/basis declarations, typed prerequisites and dependency owners are in
`config/worker10-staging-bindings.json`. `reusedQualifications` points to prior
own exact qualifications; it neither reexecutes those inspections nor opens their
referenced bodies. Recorded nested manifest/policy hashes remain assertions until
separately authorized verification. No PII source values are projected.

## Result and continuation contract

`results` contains isolated `valid`, `held`, `missing`, `malformed` or
`stale-input` states, plus `skipped-budget` for unread peers. `valid` means only
valid metadata projection. Held sources
can produce traceable metadata about their holds; their `sourceStage` and typed
prerequisites persist. Staleness also preserves that independent source stage.
Missing/malformed metadata produces no row for that binding. A pin mismatch
produces no row for its binding and discards global staging, while safe peer
checks continue. Cumulative budget exhaustion stops further reads and discards
global staging; every remaining binding receives an explicit `skipped-budget`
result. All configured bindings remain represented in `results`, including
earlier diagnostics as observations rather than accepted data. Bytes read before
a failed identity check still count against the cumulative allowance.

Every staged scalar, including zero, null and false, has a source JSON pointer,
exact input hash and source/release identity checked by the shared validator.
Paths in documents are scalar evidence only and are never followed. The only
emitted kind is `source-input-metadata`; no food/provider IDs or values are read.

`cache.originalAcquiredAt` comes only from the configured source receipt selector.
`validatedAt` is an explicit UTC observation and `validationAgeSeconds` is zero at
that observation. Revalidation never resets original age; filesystem mtime is
unused. Unknown acquisition age stays unknown. Under30-day inputs use retained
metadata with zero downloads. At or above30 days the result requests review,
still with zero downloads. The `force` library argument is recorded but cannot
enable acquisition, change pins or bypass the reuse period.

Staging serialization and its SHA depend on pinned metadata/configuration, not
the observation clock. Supply prior **actual canonical staging bytes** as
`previous_staging` to obtain `verified-no-op` on exact equality; a claimed hash
alone is insufficient. This is a pure assessment interface, not a persisted job,
online cache service, OS network sandbox or scheduler.

Tests use small authored metadata documents only. They demonstrate all five
outcomes, isolated failure, hash/budget stop, strict JSON rejection, escaped
pointers, null/false/zero preservation, exact30-day boundary, unknown/future age,
force behavior, no network/reference-body opens and deterministic replay.
Focused correction regressions additionally cover FIFO/symlink/regular-file
replacement at open, descriptor/path replacement at read, bad-pin isolation in
first/middle/last source order, and explicit peers skipped after budget exhaustion.

Next: integration00 independently reviews this exact commit and decides develop
integration. Morgan owns source scheduling and ledger reconciliation. Existing
source/custody/privacy/denial, Finland/Frida/nativeNO-FR, mandatory auto_review,
PR42 P2, production/CIX and UI/runtime holds remain. The open correlated SA request
is not resent; no duplicate acquisition, new worker or shared-core edit occurred.
