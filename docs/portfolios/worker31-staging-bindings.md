# Worker31 source-input bindings: CO, MP, ST, UZ

Selected request: `M-STAGING-BIND-20261018-W31`. Proposal base is the exact
Morgan-selected develop snapshot `abecb99ee1125730ccbc2824b6ec49ffc5cc4302`.
The existing Worker31 checkout and country results remain separate and unchanged.
Independent review and integrator00's fresh provider/base check remain required.

## Executable interface

From this source checkout, on Foo with the pinned retained metadata available:

```sh
python3 -m offmenu.refresh.portfolio31 --now 2026-10-18T12:00:00Z > /private/path/worker31-plan.json
python3 -m offmenu.refresh.portfolio31 --now 2026-10-18T12:00:00Z --previous /private/path/worker31-plan.json
python3 -m unittest discover -s tests -p test_portfolio31_bindings.py -v
```

The output is a deterministic private metadata declaration, with all 24 required
country/type cells represented. It is not source-record staging or a qualification
receipt. The CLI cannot select URLs, commands, dataset paths or a custom config.
It loads only `worker31-input-bindings.json`. That checked-in configuration contains
12 finite source bindings, receipt pins, metadata JSON pointers, declared original
asset pins, exact acquisition-time origins and explicit unknown units/bases.
Release IDs that are local labels are marked as unqualified declarations, rather
than represented as publisher-certified release contracts.

The metadata reader accepts bounded pinned JSON files only. Original asset paths
inside receipts are emitted as declarations and never followed. No PDF, workbook,
CSV body, publisher endpoint, source parser or operational cache is opened.
Records are not downloaded, normalized, mapped or admitted. Metadata outputs stay
private on Foo. These source-tree files do not add a wheel/package-data interface.

## Shared code reused, and absent capabilities

The adapter uses existing `strict_json`, `canonical`, `digest`, `timestamp`,
`field_origin_errors`, `fingerprint` and `StageResult`. The tests additionally use
the real `SourceContract`/`qualify` interface on an authored one-record metadata
fixture. Its qualified fixture cannot establish production or country acceptance.
No shared core file, registration, admission or generic country engine is copied
or changed.

At this base there is no generic pure retained-cache planner. The age check here
is a portfolio metadata diagnostic only, explicitly reporting that unsupported
shared capability. It does not invoke Wikibooks-specific `core.cache_policy`,
registry-only `plan_fixture`, or operational `CachedAcquirer`. A possible shared
`plan_retained_input` helper remains an integrator/Morgan proposal, not a dependency
that blocks these metadata bindings, and not a new public API implemented here.

`diagnose_binding(spec, now=..., previous=...)` returns fixed isolated diagnostics,
scalar metadata values and their exact receipt-field origins. Its `succeeded`
status means **metadata declaration ready for review** only. Every output retains
`stagingActivated=false`, zero normalized records and `datasetAccepted=false`.
`plan_portfolio` reports each source independently; missing/corrupt/held/stale
peers do not erase a healthy peer. Structural configuration failure is separate
from source-semantic unknowns. Requirement-evidence pin failures stay visible on
the affected country/type cell, which remains unaccepted.

## Acquisition age, replay and no-op

The original timestamp must match its exact pinned receipt selector. For example,
the CNMI PDF's actual GET time is used rather than the earlier top-level receipt
check time. Metadata `validatedAt` never resets acquisition age. Filesystem mtime
is not consulted for freshness. For an explicitly provided UTC time:

- under 30 days: metadata-only reuse intent, zero network;
- at or above 30 days: stale-input review diagnostic, zero network;
- unknown/future/inconsistent timestamp: typed diagnostic, no guessed age.

An unchanged valid declaration returns `unchanged-declaration-no-op` based on its
content/config identity, excluding only `validatedAt`. Every replay still checks
pins and selectors. A corruption, hold, semantic unknown or stale timestamp returns
`blocked-not-reusable`, never a no-op that skips diagnostics. A force-download flag
does not exist. Nothing here implements actual conditional refresh, retention,
acquisition-age renewal, source execution or a production cache policy.

## Portfolio evidence and typed blockers

- **CO:** SIPSA2025, TCAC2018 and BBCTC9/10/11 receipts are pinned. Source release
  metadata is usable; the existing ten-workbook/79-relationship manifest is retained
  as evidence, not reprocessed. TCAC copy/no-read restrictions and prior403 survive.
  Food/preparation and recipe method/yield dictionaries, intended operation scope,
  field origins, native units/basis and recognized custody remain unqualified.
- **MP:** CNMI October2026 menu and CHL/UOG link provenance are pinned. School-menu
  context is not a dietary guideline, supplier register or nutrient release.
  Recipe/card/collection custody and method/yield selectors remain unresolved.
  PNDB discovery remains metadata-only; no regional-to-national substitution.
- **ST:** the INE January2024 receipt provides release and original-asset metadata,
  not price/CPI unit/basis selectors. Omali description is not operational recipe
  data. EC trade metadata is explicitly not a producer register. Missing analytical,
  dietary, source-use and current-custody inputs remain typed requirements.
- **UZ:** SIAT1327 receipt and existing five source-header declarations are pinned,
  without reading the CSV. Classifier/unit/currency/territorial/market/missingness
  and source-datum selectors remain unknown. The distinct CPI lead's scoped
  NOT_HELD/CUSTODIAN_UNESTABLISHED response is retained without repeating that
  inquiry. Tourism cuisine metadata is not operational recipes or nutrition.

Missing public documentation is distinguished from actual denial. On 18 October
2026, the official Uzbekistan publisher's [dissemination policy](https://stat.uz/en/legal-acts/ensuring-the-quality-of-official-statistics)
was read as public method/licence metadata. Paragraphs21–24 permit use of published
official statistics with source attribution while retaining confidentiality/use
restrictions. This replaces a blanket claim that public-use terms are wholly
unknown. It does not identify SIAT1327's units, release-specific field semantics,
source-origin coverage or accepted staging scope. No held dataset body was read,
new data downloaded, denial retried, credential used or source hold lifted.

All source-specific rights, Finland/Frida, native NO/FR crash, privacy/custody,
publication, production, CIX and DEV7645 holds remain. No country/type cell,
golden data, parser execution or real refresh is accepted by this package.

## Integration handoff

Owned additions are this document, its adjacent JSON config,
`offmenu/refresh/portfolio31.py` and `tests/test_portfolio31_bindings.py` only.
No shared-interface change is necessary for this executable metadata proposal.
The exact proposal for a future central pure cache helper is the existing00
baseline/interface receipt5798; this package reports that capability as absent.
Integrator00 should not register these real sources or instantiate SourceContracts
from their receipts. A subsequent Morgan-selected source-specific task must bind
the remaining dictionaries/rights/applicability/field origins and reviewed generic
adapter capability. Reviewer acceptance and fresh expected-head integration are
separate from this authored-fixture implementation result.
