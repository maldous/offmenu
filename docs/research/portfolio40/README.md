# HT/HU/ID/IE source-input staging bindings

Metadata/code successor M-STAGING-BIND-20261018-W40, based on verified develop
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. The original worker40 checkout and
frozen external country artifacts are preserved. This package requires exact
independent review and integration; it installs no admission or production route.

Run from the repository root, without AI, network, original inputs or new packages:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m offmenu.portfolio40.binding \
  --bindings research/portfolio40/bindings.json \
  --snapshots research/portfolio40/snapshots.json --now 2026-10-18T00:00:00Z
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_portfolio40_binding -v
```

The CLI emits canonical JSON; exit 0 means all bindings are metadata-ready,
1 means typed unresolved/held/stale/malformed binding reports, and 2 means an
invalid CLI metadata envelope. The actual nine descriptors are held, so exit 1
is expected. `--previous` accepts an explicit small JSON map from sourceId to
the prior report's replayIdentity. Identical bindings return artifactAction=no-op;
the timestamp of a later validation does not change identity or acquisition age.
Errors are isolated per binding. Supplied metadata files are capped at 1 MiB and
parsed with the shared duplicate-key/nonfinite-rejecting JSON reader.

## Evidence and ownership

`bindings.json` contains nine metadata descriptors: HT methodology/menu;
HU GYERE, pocketbook and STADAT; ID consumption publication; IE AHM05, HSE and
the held FSAI access receipt. There are eight original references; FSAI has none.
Each descriptor pins the actual retained receipt and country validation manifest,
with a literal receipt-entry pointer. Original paths are evidence strings only,
never opened, followed, stat-ed or hashed by this package. No source records,
bulk files, credential contents or candidate values are included.

The local descriptor IDs are country plus receipt-directory names. They are NOT
new aliases in the shared source registry. Recorded release labels remain literal;
the explicit unresolved marker is not an authenticated edition. Country/type
associations are proposals, not accepted applicability. `nativeValue` is a proposed
output declaration with null origin/unit/basis, not a claimed source field. No
first-row coordinate, nutrient identity, currency or index/quantity equivalence
is invented. Scope, actual field selectors, primary source-specific decisions,
attribution, parser and staging acceptance remain typed missing inputs. Existing
public CSO/KSH policy evidence in the linked country receipts is not promoted
into a new reviewed transform decision.

`snapshots.json` represents only metadata equality checks. Original acquiredAt
comes from retained acquisition receipts. validatedAt stays null where the exact
validation clock is not bound. Cache decisions use acquiredAt exclusively: under
30 days proposes recorded-cache reuse with zero downloads; at/after 30 days
reports conditional revalidation required. Neither outcome performs revalidation,
downloads, verifies raw cache bytes or lifts a source hold. There is no force
override. Even metadata-ready fixtures always report bodyExecutionAllowed=false,
stagingAccepted=false, goldAdmitted=false and acceptedRecords=0.

## Shared interfaces used unchanged

- `refresh.core`: strict_json, canonical, sha, timestamp and RefreshError.
- `refresh.national_tabular.valid_input_name`: canonical relative bundle paths.
- `refresh.field_provenance.field_origin_errors`: source/release/input-pin and
  per-datum origin coverage on declaration placeholders, never real data rows.
- `refresh.adapter_mapping.retained_adapters`: exact supported source/release
  registry, never publisher/title/country inference.

The shared registry currently supplies no reviewed adapter for these exact local
source/release formats. This package reports shared-handler-unbound. It does not
copy or create country PDF, HTML, JSON-stat or nutrition engines. The authored
positive tests use one existing shared handler's exact synthetic identity and
an authored scope pin solely to validate the metadata interface.

## Proposed integrator00 interface work (not implemented)

1. Select an existing generic retained-format handler or independently review a
   generic JSON-stat/table metadata-input adapter and exact source/release schema
   when source-use and field/exception evidence permits it. No country-name route.
2. Supply a reviewed `SourceContract` and StageContext handler binding only after
   scope, operations retain/parse/transform, origin selectors, expected counts and
   real input qualification are established. This preflight never builds a
   SourceContract from its JSON config or calls qualify/accept/replay.
3. The pilot `core.cache_policy` labels source/release with Wikibooks constants.
   It is therefore deliberately not called for portfolio identities. If execution
   needs a reusable generic cache descriptor, integrator00 should select a shared
   source/release-parameterized interface, preserving under-30-day zero-download
   and unchanged-content no-op gates. This package only supplies metadata age and
   replay identity; it cannot certify a durable cache or change shared core.

All Finland/Frida, NO/FR crash, FSAI403, HSE derivative and other actual source
rights/privacy/custody restrictions survive. Raw stays Foo. No UI/DEV7645,
production/CIX, automation, worker dispatch, model or permission changes.
