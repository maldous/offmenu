# Worker33 retained metadata binding package

Task: M-STAGING-BIND-20261018-W33. Portfolio: GH, GI, GM, GN. Baseline:
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. This package owns only
`worker33_bindings.py`, `worker33_portfolio.json`, its tests and this document.
No shared registry, adapter engine, admission table or caller/schema is changed.

## Interface and evidence

`assess(spec, supplied, now=UTC_ISO, previous_key=None)` consumes one configuration
entry and a dictionary of **retained metadata bytes**, keyed by binding ID.
`assess_portfolio` isolates malformed peer declarations. The code never opens a
path or acquires a source. Callers must use their existing controlled metadata
loader, never substitute raw source bytes. Input limit is 64 KiB per entry,
128 scalar field declarations, eight country selectors and 32 portfolio entries.

`worker33_portfolio.json` pins five exact retained metadata files, their parent
freeze manifest, known original-file hashes as opaque references, and acquisition
receipt hashes where retained. The input byte SHA is checked. Parent and original
pins are **declarations**; their bytes are not opened or verified by this module.
The configuration's `retained-metadata-sha256:` release IDs identify metadata
snapshots. `publisherRelease` preserves a retained publisher label or null; it
does not establish publisher release equivalence or complete source custody.

Every selected scalar has an exact JSON pointer and type. The shared
`field_origin_errors` validator checks the full scalar origin inventory. Origins
refer to the pinned **metadata projection**, not freshly verified original cells.
Semantic meanings preserve native lexical price units and transaction basis
unknowns, CPI index points with January 2020=100 and currency null, recipe
quantity witnesses with yield/nutrition unknown, and discovery-only reference
status. No conversion, mapping, recipe method inference or source-data copying
occurs. Unknown bounded fields do not prove absence from the original.

| Binding | Retained scope | Source-operation state |
| --- | --- | --- |
| GH price coverage | Two metadata samples; inherited 39,038-row coverage claim | WFP use/custody and canonical price context pending |
| GN price coverage | Two metadata samples; inherited 26,430-row coverage claim | WFP use/custody and canonical price context pending |
| GM CPI locator | Twelve lexical monthly index observations | Private inspection; redistribution unqualified |
| GH recipe locator | One locator, two quantity witnesses | Private inspection; republication, method/yield qualification pending |
| GI discovery | Three metadata leads | Original sources not acquired; source use unknown |

These counts are inherited evidence inventories, not newly fetched/parsed rows.
The separate prior 12-witness price packet and scoped Worker44 reviews retain
their existing bounds; this implementation does not enlarge or repeat them.
All six country requirement categories remain incomplete in the configuration.

## Replay, freshness and diagnostics

Build identity uses shared canonical JSON and SHA-256 over the entire binding,
including exact retained pins, semantics and holds. `validatedAt` and previous-key
observations do not change that key. A matching previous key reports a metadata
no-op **after** checking the input hash, selectors and types again; no files are
written. Callers should retain `buildKey` separately from validation timestamps.
Shared `StageResult` receipts contain only fixed codes and SHA-256 references.
Malformed diagnostics never include source text, paths, URLs or exception logs.

`originalAcquiredAt` stays separate from validation time; known original times
require an acquisition-evidence pin. Unknown times remain null. The shared
`acquisition.MIN_TTL` supplies the 30-day minimum. No shared pure cache planner is available at this baseline; the receipt types
that dependency explicitly. `cacheIntent` only reports
retain/refresh-review/age-unknown metadata: it has no refresh override, transport,
cache writer or permission-granting action. Revalidation does not reset original
age. Collection-date labels, metadata-modified times and filesystem mtime do not
replace acquisition time. A recent acquisition does not make old price dates
current. A stale **input pin** is quarantined independently of acquisition age.

The five required outcomes are: valid metadata (`succeeded`/`reused` only for
authored unheld metadata), missing (`unsupported`), held (`held`, even when
metadata is valid), malformed (`failed`), stale input (`quarantined`). Every
real retained entry remains source-held. Metadata success is not a generic-run
parse/normalize/accept success: no `Binding` handler is registered, no source
operations are authorized, and normalized/mapped/gold counts remain zero.

## Integration needs and remaining dependencies

Integrator00 owns shared-core integration and independent review intake. No
shared-interface modification is required to run this metadata package. A later
source-processing task would need reviewed generic WFP CSV, CPI and recipe
adapters, a reviewed loader/resource boundary and operation-specific source
contracts. Those are absent in the pinned shared registry; this module does not
replace them with country engines. Any later shared change must be proposed to00
with its exact interface and immutable independent review, not added here.

Morgan/Gateway owns scheduling/reconciliation. Existing WFP owners62 (GH) and12
(GN) retain original custody; owner43 retains the GM2011 rights binding. S027
regional table custody/dictionary/use, recipe method/yield/use and GI/GM/GN recipe
holder requests remain in B02-W33; do not duplicate them. Owner57's S284 source
identity correction remains separate. Missing custody is an input gap, not a
legal prohibition; explicit private-use and denied-action restrictions still
apply. The held FAO publication card's actual403 is not retried or replaced with
an alternate endpoint. Finland/Frida/nativeNO-FR restrictions remain intact.

Run `python3 -m unittest discover -s tests -p test_worker33_bindings.py` from an
integrated checkout. Seven authored tests cover all five outcomes, exact type/
country/selector rejection, duplicate-key/nonfinite JSON, bounded input,
deterministic no-op with stale recheck, unknown/future/old acquisition times,
no filesystem/network calls during assessment and independent peer diagnostics.
No original source bodies are used in these tests. Independent review and
integration are pending. Production, CIX and DEV7645 remain stopped/paused.
