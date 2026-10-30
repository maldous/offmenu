# UIF-109 canonical identity source disposition

2026-10-30 · finite documentation deliverable · independent review pending

Source base and unchanged Git HEAD: `075500f855c9b517fedd9a37d41b146f94c804ec`.
Isolated branch: `feature/uif109-canonical-identity-disposition`. This document
reconciles retained external design evidence with the completed 18-source
comparison; it neither adopts canonical identity nor declares umbrella UIF-109
Done. Only this exact user-specified path/case is authored. Repository standards,
ADRs, product code and private state remain unchanged.

## Evidence and review scope

The original v0.2 contract is external design evidence at historical source
revision `4693cbc3fe17cdde2e292e6eb00cd83769ee45ae`. Keep it unmerged in original
custody, together with its later supplement/addendum and scoped reviews. Extract
the endorsed boundaries and adapt historical consumer references to the current
paths below; do not cherry-pick a historical snapshot or copy private receipts.

The completed comparison (C01 below) was recorded at
`9e007c742dad43fa2c35caecf7e97c46ec4c30f4`. Its 18 source hashes still match the
current base exactly. This disposition consumes its conclusions rather than
repeating source/design comparison or historical tests. Full custody locators
remain in the supplied private input pins; the following are meaningful document
identities and SHA-256 references, not imported runtime logs.

| Ref | Original document | SHA-256 |
| --- | --- | --- |
| C01 | Completed contract/consumer comparison | `0f49e09444c4c8782cddd380813117c9671c548f9f907c9a8e1ca203fb053dbd` |
| E01 | Owner56 implementation contract, proposal v0.2 | `5a2a281abdd1777bbb5c5ce61f63a78aa532ecbf7a7b2318cc89b8e4a528bded` |
| E02 | SAME11 endorsement-delta review receipt | `ddfedab621552e2f2964951b3bfb87d7c5f7de4e1a80a26a51c41e00febc707f` |
| E03 | Owner56 endorsement-delta **freeze receipt** | `e52832b82f6175d389cae64ca3176e95375502b21bc1cebdc4a0d7db6d56bfff` |
| E04 | Owner56 contract endorsement supplement | `e0d49da714bd1cde14ef0aba5c9c108e7c09d9f6ff7d95b4b27b9e7705be13e3` |
| E05 | Owner56 structured contract addendum | `6f69f05404cdfaba83e63eaa5df1c49759747a037d6137afbcd6bee890c2d444` |

E02 records `PASS_SCOPED_ENDORSEMENT_DOCUMENTATION_DELTA`, with no findings.
Its `authorReceipt` is E03, the documentary freeze receipt, **not** the narrative
body. E02 and E03 bind E04/E05 by their exact hashes. The later-body locator
blocker in C01 is cleared: these exact bodies have now been read and verified.
E04/E05's freeze-time unreviewed-delta statements are historical, superseded only
by E02's scoped documentary review. No source semantic/runtime review was
repeated; E02 does not globally lift SAME11's hold or accept technical defaults,
types, namespace, mappings, implementation, migration or promotion.

The original v0.2 SAME11 review is retained by reported hash
`4b309f9e843bc4454f6ffaea935de9d79f75d9c9c01fc5b06741d7a1f4f9fecc`
and verdict `PASS_V02_EXTERNAL_DESIGN_WITH_UNACCEPTED_DECISION_GATES` in C01,
E02 and E05; that original review body was not reread here. The earlier proposal
0.1 PASS cited by E01 covers only proposal 0.1. Neither review accepts individual
identity mappings. No new human design choice is requested by the documentary
result.

## D01–D08 disposition against current requirements

Only D01/D04/D05/D07 have accepted **design endorsements**. Their detailed
implementation remains unaccepted. D02/D03/D06/D08 are delegated technical
proposals/defaults. Existing Worker56 document authorship and SAME11 review are
established; expanded Worker56 schema/registry/acceptance responsibilities,
Worker01 source coordination, Worker02 state, Worker04 storage, Gateway
custodian/allocation/release and sole integration-writer cutover labels are
design nominations, not current operational appointments or work dispatches.
The owner/input column identifies the existing coordination route and the
specific missing evidence; it appoints nobody.

| Decision / current functional requirement | Keep / extract / adapt / supersede disposition from C01 and E01–E05 | Existing owner route and concrete remaining input |
| --- | --- | --- |
| **D01 — entity granularity**; stable product, formulation, package, market, ingredient and lot must remain distinguishable | **Keep/extract endorsed separation. Adapt** to S01–S03: existing `FoodProduct`, `FoodIngredient`, `CrosswalkAssertion` and source-scoped nutrition/product records do not register `ProductFormulation`, `ProductPackageVariant` or `ProductMarketVariant`. Public source references establish no accepted canonical granularity. | Morgan Gateway must identify the current schema/architecture accepting authority and obtain its acknowledgment; Worker56's proposed schema role supplies exact definitions/type and projection registry diff, with independent SAME11 review scoped to that diff. Endorsement alone cannot register types/instances. |
| **D02 — typed relationships and uncertainty** | **Keep** existing `candidateMatch`, `broaderMatch`, `exactMatch`, `derivedFrom`, `hasQuantity`, `hasBasis`, `hasPreparationState` semantics. **Extract/adapt proposed** eight relations and nine evidence properties from E01; C01 finds them absent from inspected registered vocabulary (S01/S02). Null targets cannot become fake resources or positive relations; relation targets require IRIs and citations remain required. | Gateway must obtain a named current schema custodian and independent schema reviewer, using Worker56's vocabulary proposal and a predicate-by-predicate semantic-conflict disposition plus supported projection contract. Proposed names and bundle decision states are not registered graph vocabulary/enums. |
| **D03 — stable allocation without rekey** | **Keep** source/release/manifest IDs in S03/S07/S15. **Extract proposed** once-only opaque `urn:offmenu:resource:<uuid>` UUIDv4 allocation/reuse rules; source keys and identifier-assertion IDs remain source-scoped. Existing IRI syntax does not prove accepted allocation. | Gateway's allocation-accountability nomination must yield an acknowledged current registry writer/custodian, schema-authority namespace acceptance, exact durable allocation artifact and independently reviewed allocation-to-entity/reuse evidence. No writer is appointed and no IDs are minted here. |
| **D04 — positive identity acceptance** | **Keep/extract endorsed** independent evidence review followed by explicit custodian acceptance, separate from rights/admission, gold and nutrition/diet qualification. **Adapt** S05/S07/S09/S16: identity pages disclaim physical-product/ingredient qualification, public references validate selected source provenance, and display alias uniqueness does not check accepted positive crosswalks. No mapping bundle is accepted by these facts. | Gateway must identify an authorized accepting custodian and independent identity reviewer, with Worker56 mapping-author nomination kept distinct. Required record: exact mapping ID/revision, source dataset/release/record digest and citations, real target/type/granularity or explicit unresolved result, context/validity, relation, contradictions, adapter/method, review receipt, accepting custodian evidence and supersession. Source owner must separately supply rights/use admission; identity acceptance cannot substitute for it. |
| **D05 — lexical identifiers and context** | **Keep/extract endorsed** original barcode/namespace and unresolved context. **Keep** S04–S08 checksum, padding, typed/lexical binding and source observation handling. These prove representation/syntax and source binding, not canonical product/package/formulation/market equivalence. Identical codes, names, translations or display aliases cannot establish positive identity or move nutrition/price. S05 remains off-live/staged; legacy lookup is not strict canonical resolution. | Gateway must obtain current identity-custodian acceptance of exact context rules and supported source-specific adapters. Worker01's source-evidence coordination and Worker56's identity-contract labels remain nominations; the actual source owner must supply release/digest, market/time/formulation/package/unit evidence and accepted target mapping. Missing context stays unknown; UIF93/94-owned surfaces are not changed. |
| **D06 — versioned compatibility/storage** | **Keep** `offmenu-common/1`, unified `1.0`, existing account/corpus formats and barcode-keyed caches (S01–S03/S13–S15). **Extract/adapt proposed** separately versioned mapping bundle/sidecar; no accepted reader, projection or round-trip is established. No SQL/API/top-level-field/enum change or cache rekey follows. | Gateway must obtain acknowledged current schema/storage authorities; Worker56 schema lead and Worker04 storage lead remain nominations. They must provide an accepted bundle/adapter/reader-version matrix, exact supported projections, unknown/legacy-payload preservation, unsupported-version behavior and reader round-trip evidence before projection coding. |
| **D07 — owner-scoped lots and state** | **Keep/extract endorsed** separation of identity, lots, balances and owners; initial canonical links remain outside legacy lot payloads. **Supersede only** E01's broad historical claim that validators drop all identity references: C01 shows S07/S11/S13 preserve explicit `publicProductReference` and `sourceObservationReference` through lot validation, including receipt/waste paths. This does not prove canonical sidecar retention or round-trip. S12 batch/restore and actual inventory events remain distinct. | Gateway must obtain acknowledged current state/kitchen and identity custodians; Worker02 state/Worker04 storage roles remain nominations with no private-writer transfer. Any separately selected persistence scope needs owner/kitchen authorization, lot/source revision bindings, old-client/server/receipt/waste/batch round-trip and conflict evidence, plus rollback preserving intervening stock events. No private input is acquired by this deliverable. |
| **D08 — bounded compatibility then reversible adoption** | **Keep** offline-first, retained history and separate cutover/rollback proposal. **Extract/adapt**, without snapshot cherry-pick, only a future qualified mapping-bundle reader/conflict-report scope. C01 establishes no accepted identity reader; S16 retains `SOURCE_BARCODE_SELECTION=null`. PRODUCT56 (S17/S18) remains a separate source/code/language label lookup, not scanner or canonical identity. | Morgan Gateway must resolve D02/D03/D06 technical inputs and select an actual implementer, independent reviewer, fresh immutable base/candidate, permitted files, compatibility inputs, command/output contract and rollback boundary only when genuinely qualified. No implementation writer is selected now. The existing sole integrator's cutover role is a nomination without a named execution appointment; runtime/storage/consumer and release evidence remain phase-specific. |

D02's retained proposed names are `hasFormulation`, `packageOf`,
`marketVariantOf`, `identifiesPackage`, `describesFormulation`,
`hasComponentMention`, `componentOfMention`, `referencesItem`; evidence properties
are `mappingDecision`, `mappingRevision`, `adapterVersion`, `validFrom`,
`validUntil`, `marketContext`, `reviewReceipt`, `supersedesMapping`,
`identifierLexicalValue`. Preserve recipe `variantOf`. Unresolved decisions need
cited source-scoped assertions without positive target relations. Accepted,
fully bound records are a proposed prerequisite for positive resolution;
unsupported versions, missing digests or contradictory eligible targets yield
no selected target. Label ranking cannot override evidence acceptance.

The retained unresolved examples in E01/E04 still have null canonical targets:
Lindt's conflicting quantity notation/nested composition and Baby Dills'
pack/serving-versus-100g uncertainty remain unresolved. No second equivalent
barcode, ingredient percentages, translated identity or accepted nutrition/price
transfer is inferred. Only curated design conclusions are retained here; no
source rows, profiles or datasets are imported.

## Separate PRODUCT56 retained material

C01 establishes S17 is byte-identical to retained commit
`ac4fb2a47f0fa422e4054cc65b4b1460097a4c00`, SHA-256
`028c6b5cebb70e5639347ba78eb8cb831b88facd9d96443b8992bda55df6cf3d`.
Keep the [helper](../../../tools/data-processing/source_proposal_lookup_owner56.py)
and [maintained source-proposal guide](../../source-proposal-owner56-v2.md) as
separate source/code/language label lookup evidence. Module relocation does not
prove scanner integration, identity mapping or runtime adoption. C01 reports the
original helper test blob absent from the current tree; its historical five
checks/all-88-proposals evidence needs explicit external manifest/bundle inputs.
It was neither rerun nor independently reaccepted here.

## Phase-specific handoff and acceptance limits

The current barcode design is a framework with concrete missing inputs, not a
runnable implementation. E02 leaves M0–M5 holds intact:

| Phase | Concrete handoff that remains with existing coordination/owners |
| --- | --- |
| M0 — technical decisions | Morgan Gateway obtains acknowledged schema/namespace/registry authorities and the exact D01–D03/D06 decisions/diffs above; Worker56 authorship and SAME11 review do not supply execution appointments. |
| M1 — bounded offline implementation | Only after qualification, Gateway selects one fresh base/candidate/files/writer/input/output scope and independent exact-candidate review with relevant compatibility evidence. The historical source pin is not a fresh implementation selection. No parser/reader is authored here. |
| M2 — read-only resolution/serving | Gateway separately selects a serving writer/consumer scope; current identity custodian and independent reviewer bind the exact accepted mapping revision, source/target/context/contradictions, supported versions and separate source-owner rights/admission decision. No source/canonical/gold admission is implied. |
| M3 — private state | Acknowledged state/kitchen/storage and identity custodians supply the D07 authorization, revision-safe round-trip and rollback contract before any private-state scope. Nominated Worker02/04 roles transfer no writer authority. |
| M4 — consumer adoption | Gateway identifies the actual consumer owner and exact scoped ingredient/formulation/unit/market inputs; independent market/nutrition/composition/translation/privacy review belongs to that separately selected candidate. UI/prototype and runtime adoption remain held. |
| M5 — release/migration | Existing sole integrator and Gateway require a concrete separately authorized target/environment, reviewed immutable candidate/owner/source pair, applicable rights/security/custody acceptance and rollback evidence. No migration, production deployment or CIX restart is selected. |

This file is the reviewable finite source-reconciliation output for the existing
UIF-109 outcome. The same independent reviewer can assess the exact document
hash and evidence scope; the sole integrator retains integration authority. No
tracker update, appointment, new manager/worker, commit/ref/push/merge, runtime or
auth/provider activation is authorized or performed. Existing denied actions,
data/configuration holds, rights/privacy/custody/security boundaries, suspended
historical workers, production and UI holds remain. Nothing enables
`automatic_start` or changes `legacy_workers_resume`.

Requested model/effort/provider: per qualified native launcher; exact values not
observed in this documentary task. Resolved model/provider and sampled resources:
unknown; no resolver/session/configuration change is made to discover them.

## Offline verification

All six original document pins and all 18 current source pins were verified by
SHA-256. Relative repository link targets were checked offline. `git diff
--check` and an unstaged new-file whitespace check passed; final Git scope is
exactly this one document, with HEAD unchanged at the source base above. The
exact supplied path/case is retained under the repository standard's externally
specified-path rule; no naming exception, standard or ADR is added.

As explicitly scoped, bootstrap/discover/layout suites, tests, jobs, APIs,
browser/scanner/live lookups and historical review replay were not run. No raw
datasets, profiles, credentials, private state or unrelated/hidden sessions were
read. Remaining limitations are the specific technical/owner/input decisions
above and independent review/integration of this output, not missing later-body
locators or a new human design decision.

## Current source hash appendix

All relative paths below refer to immutable source base
`075500f855c9b517fedd9a37d41b146f94c804ec`; S01–S18 are C01's exact current-source
pins, verified unchanged here. Links locate source only and do not claim runtime
adoption or current operational appointments.

| Ref | Current source path | SHA-256 |
| --- | --- | --- |
| S01 | [contracts/corpus/common-data-contract.json](../../../contracts/corpus/common-data-contract.json) | `b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa` |
| S02 | [contracts/corpus/common-data.schema.json](../../../contracts/corpus/common-data.schema.json) | `f1968889c5e1500e841517bd7546af9c223bf97dce40bb68a3f584e93559298c` |
| S03 | [apps/web/src/unified-data.js](../../../apps/web/src/unified-data.js) | `82d027668d9f528dd83bce3cbb8c6f39b0bcdfbb88c62994456c433bc402b782` |
| S04 | [apps/web/src/evidence-model.js](../../../apps/web/src/evidence-model.js) | `b5f806696fb8296f5e3cb3d38ddbd458d86c3167aeeeab6094e78581b59dccd9` |
| S05 | [apps/web/src/scanner-identity-v2.js](../../../apps/web/src/scanner-identity-v2.js) | `ac3cad23512e09dc2aabac8e58d751db71b3d04c692e724a04fdd2a69b1c7d76` |
| S06 | [apps/web/src/typed-identifier-contract.mjs](../../../apps/web/src/typed-identifier-contract.mjs) | `5a3274d7272c5703c08ef8e6110078f4dd37d5edf4d3b9cc42c3c35d23586534` |
| S07 | [apps/web/src/scanner-kitchen-handoff.js](../../../apps/web/src/scanner-kitchen-handoff.js) | `e35169fee6a7391491c460ddb590f9e1d0b0e59a20a00dcbce557aee7faf1eb1` |
| S08 | [apps/web/src/production-scanner/scanner-model.js](../../../apps/web/src/production-scanner/scanner-model.js) | `38aa40fb6722f9bc392477d06f78a9921c414ab7a3b3ddb15b6df898f82ef228` |
| S09 | [apps/web/src/common-corpus-locale.js](../../../apps/web/src/common-corpus-locale.js) | `728a26ac7eae0a6e55fdf03df2d347ffb5fd7f7a8a44334b243cd6b7df2f14b7` |
| S10 | [apps/web/src/content-locale.js](../../../apps/web/src/content-locale.js) | `1431349bdf6fdec6a24dc24a6d4d54a7c1e2bbc50a4729419645fbdb2e29c27d` |
| S11 | [apps/web/src/model.js](../../../apps/web/src/model.js) | `4edfc0bc5fa54a0ca3152a3f0321c5c50aa9501b4d6229bd2ac3d8ff8b886fac` |
| S12 | [apps/web/src/cooking-model.js](../../../apps/web/src/cooking-model.js) | `f2cc79de2ce5f69028e920411120f668f48a9f6cc4cd79e502f1a35f727f33d4` |
| S13 | [apps/web/server/state.mjs](../../../apps/web/server/state.mjs) | `50023d296d373ab1fc39c6034c9ff5a331dc18fd9a5a965a31d6ae700a40c0ff` |
| S14 | [apps/web/server/schema.sql](../../../apps/web/server/schema.sql) | `48bad7a6e855478f3364f7e43292ccc34aa54802571c943ed9226a3a7270e380` |
| S15 | [apps/web/server/corpus-schema.sql](../../../apps/web/server/corpus-schema.sql) | `87fd745ba28de6db44e0c5e82bff4a9cd42435b0b6da4a60802b682d7743f254` |
| S16 | [apps/web/server/source-barcode-api/reviewed-hydration/source-barcode-selection.mjs](../../../apps/web/server/source-barcode-api/reviewed-hydration/source-barcode-selection.mjs) | `adaddd1ea29bc47860e4ed557b477240bab677b5eb431dc255a5c5887159f71e` |
| S17 | [tools/data-processing/source_proposal_lookup_owner56.py](../../../tools/data-processing/source_proposal_lookup_owner56.py) | `028c6b5cebb70e5639347ba78eb8cb831b88facd9d96443b8992bda55df6cf3d` |
| S18 | [docs/source-proposal-owner56-v2.md](../../../docs/source-proposal-owner56-v2.md) | `8a1bf1d4bbf8144136bd586f874388a011e8733b813bdf11525690d2cbf46bb3` |
