# Worker 63 source-input bindings: GW, PE, TV, ZM

Portfolio-specific metadata/code proposal on develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This installs no source admission,
country acceptance, gold record, source-body parser, acquisition or shared-core
change. Raw assets stay on Foo. The configuration is reviewed code/configuration,
not a manifest that can grant `SourceContract`/`Admission` privileges.

## Run

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p 'test_worker63_staging_bindings.py' -v
python -B scripts/worker63_staging_bindings.py --now 2026-10-18T00:00:00Z --output /OWNED_NEW_GENERATION/report.json --metadata-output-root /OWNED_NEW_GENERATION/metadata
python -B scripts/worker63_staging_bindings.py --now 2026-10-18T00:00:00Z --previous /OWNED_NEW_GENERATION/report.json --output /OWNED_NEW_GENERATION/replay.json --metadata-output-root /OWNED_NEW_GENERATION/metadata
```

Use actual caller-owned new generation paths. Expected CLI exit **2** means a
metadata result exists with real data stages held; exit **3** is an invalid request.
No CLI flag enables processing, rights, network, force refresh or acceptance.
Every country has independent typed diagnostics: `valid`, `missing-input`,
`malformed-input`, `stale-input`, plus separate data-stage `held`. A missing or
bad country's metadata does not suppress other countries. Fixed diagnostic codes
never echo parser exceptions or arbitrary source values.

The only readable inputs are the configuration's pinned JSON metadata assets,
bounded to 1 MiB each. Original asset paths/hashes are **references only**, never
opened, statted or rehashed. `safe_path`, `strict_json`, `digest`, `canonical`,
`timestamp`, `bundle_files`, `datum_pointers` and `field_origin_errors` reuse
existing generic contracts. No country engine or shared adapter registry is copied.

`referenceMetadata` packets preserve selected JSON values including zero/null,
with one field origin per scalar tied to the exact metadata digest/JSON pointer.
Their identity/release explicitly describe metadata snapshots, not publisher
food releases. Their `fetchedAt` stays null. This is not a qualifying source
candidate; no rights/expected production counts/schema are invented. The optional
writer stages these metadata inputs plus candidate packets and a separate
metadata manifest. Unexpected/different output bytes are a generation conflict;
identical snapshots are a write no-op. Failed stages remain explicit failures.
The authored synthetic tests alone use a fixed `fixture=True` SourceContract and
shared `qualify`; no `accept`, real admissions or source factories are installed.

## Scope bindings and remaining prerequisites

| Country | Existing input/origin declaration | Retained boundary |
| --- | --- | --- |
| GW | Regional WAFCT2019 manifest, use notice Introduction B26 and citation B25; sheet `03 NV_sum_39 (per 100g EP)` | 1,028 existing regional rows are not GW membership. Nine multi-country fortified-oil labels do not prove GW samples or markets. Private literal-research use does not supply canonical adaptation/commercial clearance. |
| PE | INS acquisition/release/rights metadata; repository2023 and PDF March2025 remain separate | No edition unification, numerical extraction or inferred nutrient units/basis. NC-ND metadata versus broader reproduction notice remains unresolved; original native custody unestablished; MINSA403 no-retry. |
| TV | Exact CPI2026-Q2 report/table metadata | Index base, weights, population, table/header/row selectors and work-specific use remain unknown. No price/currency/basket substitution. |
| ZM | Leeds DOI10.5518/1111 mapping; Dataset A/B/C/D and E:BE; basis Meta information A4:A6 | Historical waste-adjusted daily supply,1961–2013, not composition/intake. g/mg/µg/kcal per capita/day stay whole literal units; canonical targets, preparation, detailed waste method and original acquisition timestamp remain unknown. |

All six country/data-type applicability declarations are unreviewed. Metadata
validity, snapshot replay and prior scoped review do not establish data completion.
Rights/custody and Finland/Frida/nativeNO-FR/private/403/production/CIX/DEV7645 holds
remain unchanged; existing25/57/64 work remains separately owned.

## Acquisition age, cache and replay

Original acquisition timestamps retain their exact metadata locators; validation
age is independent and never replaces source acquisition time. Unknown ZM
acquisition stays unknown, not epoch, file mtime or this validation's clock.
Under30day intent is zero download; at30days the result is only conditional-refresh
eligibility. No actual cached body has been verified by this binding. Content
hash replay is separate from cache freshness, processing rights and diagnostic
clock. No-op output equality does not clear a hold.

At this baseline there is **no generic pure cache planner**. This portfolio's
small cache declaration emits intent only using shared MIN_TTL. `core.cache_policy`
is Wikibooks-specific and is not used; `plan_fixture` is registry-bound;
`CachedAcquirer` is operational/body-reading and is not invoked. The optional
shared proposal below is not needed to run the present metadata package.

Suggested integrator00-only future interface, **proposal, not implemented**:
`plan_retained_input(source_id, release_id, bundle_identity, original_acquired_at,
validated_at, now, retention_seconds, holds)` in shared policy code. It should be
pure/no-I/O, preserve unknowns and original age, require explicit trusted identity,
return typed missing/malformed/stale/held/reuse-intent/conditional-intent, and never
turn force/revalidation flags into network or rights/asset-verification claims.
Independent central selection/review must cover30day boundaries, changed binding
identity, future clocks, unknown originals, policy holds and zero network. No
shared-core changes are proposed as part of this portfolio commit.

## Evidence and delivery

24 focused authored-fixture tests pass. They exercise actual shared qualification
and per-datum-origin validators, not real food payloads. Actual metadata execution
emits29 reference packets (GW8,PE4,TV8,ZM9); all four data stages remain held.
Replay preserves14 snapshot files including mtimes. No source records normalized.

Private local evidence, command logs, parser/import failure and correction,
per-country cache/source blockers and snapshot hashes are retained under:
`/home/user/Documents/Codex/2026-10-13/task-3/reports/country249-fixed64-priority/deliverables/owner-63/M-STAGING-BIND-20261018-W63/validation-v2/`.
The first pre-preparation import attempt failed because old checkout shadowed the
shared export; no test ran then. The corrected prepared checkout runs passed.
No reported code pass substitutes for independent exact review/Morgan verdict or
fresh-develop integration. Integrator00 receives the exact commit/patch/checks
through Gateway; no remote push, merge or shared source mutation is performed.
