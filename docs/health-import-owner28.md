# Worker 28 health-preview closure on f6

Task: OFFMENU-DELIVERY-20261015-C2, Worker28 existing health-preview closure.
Fixed checkout: /home/user/src/offmenu-workers/worker-28.
Branch: feature/health-preview-closure-owner28-f6cb92ae-20261015.
Exact composition base: f6cb92aef52a5cc8193717d7e794556bd84f8b3b.
The original checkout was already synchronized and clean on
sync/worker-28/f6cb92ae-20261015. No fetch, synchronization repair, merge or
central wiring was performed; Worker64 retains shared-fetch/sync ownership.

## Immutable reviewed source and fixture closure

This composition preserves the module and tests BYTE FOR BYTE from original
candidate a108e1645ad5f19a5e0fe85e37e5c080f3582d8f:

| Owned path | SHA-256 |
| --- | --- |
| cloud/health-import-owner28.mjs | 94b84d2420d8c900d61eab0dab458c05d3b16942f15d860369854743e6fcdc4b |
| tests-web/health-import-owner28.test.mjs | 9a2b294a800c80d138a04f0b42f968226d1f2644d517e25f3ef840b7e0b376f8 |

The third and only other owned path is this documentation file. No package,
dependency, schema, shared handler, UI, source fixture or other owner's file is
changed. The validator has no imports, network, storage, ambient clock, random ID
or write effects. Runtime dependencies are JSON, TextEncoder, Date and ordinary
JavaScript operations. The five retained tests use node:test/node:assert and the
module at the owned local path. Existing immutable synthetic fixtures only.

Different-author review: be8d7040acc4789ae5e3a0dd227a206913cf2cce,
docs/native-health-import-owner39.md, accepted the exact a108 preview for its
documented synchronous no-write boundary with trusted context production.
It did not accept native access, persistence, revocation or overlap enforcement.
The parser/test hashes above still match that review. The f6 composition/doc
delta remains independently reviewable; no historical caller approval transfers.

## Frozen source/envelope contract

validateHealthImport(serializedJSON, trustedContext) accepts schema version
offmenu-health-import/1 only. The UTF-8 envelope is at most 65,536 bytes and
contains at most 100 records. Top-level fields are schemaVersion, owner,
memberId, revision, source and records; unsupported fields are refused.
Source fields are kind, sourceId and exportId. Only manual-export/vendor-export
are portable modes. sourceId/exportId/sourceRecordId are separate identifiers;
none authenticates a real vendor or permits reuse of vendor content.

Records require id/sourceRecordId/type/unit/value/observedAt. Supported units:
weight kg, height cm, steps count, activityMinutes min, sleepMinutes min,
energyIntake kcal, proteinIntake g, sodiumIntake mg. No conversions are made.
Values must be finite and nonnegative; steps are safe integers. Existing plausibility
guards reject height above300 cm and weight above1000 kg. Canonical nonfuture
UTC timestamps are required, with either whole seconds or three-digit fractions.
These are format/measurement guards, not clinical validation.

Original IDs, observed value/unit/time, source, export, consent and person scope
remain attached to accepted records. Duplicate source-record/type identity or
record IDs inside one preview are withheld; cross-export replay and measured
overlap are not enforced here. Source-issued revisions, intervals, original time
zones, raw value lexemes, vendor/device identities and native export formats are
unsupported by this parser. They must not be fabricated from the single UTC
observation or silently added to the upload.

## Frozen consent and privacy contract

The trusted caller supplies owner, memberId, current account revision, now and
consent. Upload owner/member/revision must match exactly. Consent must have an
active status, valid id, matching owner/member, future canonical UTC expiry,
health-import purpose and explicit allowed source/type lists. The host must
derive these immutable facts from actual current authenticated membership and
person permission, including child-specific authority, never client booleans or
generic household access. Account import revision is not source record revision.

Output is a private no-write preview, with imported-unverified records, rejected
row indices/reasons and clinicalQualification:false. Unknown/null values do not
become zero. Rejected raw values do not appear in rejection summaries. A partial
needs-review preview does not authorize automatic import. The host must keep the
preview/upload account-private and apply explicit retention, deletion and
shared-device cleanup policy; no telemetry or public projections of health data.

Preview-time consent is not a permission lease. Any commit requires separate
exact-subset confirmation, then current account/member/session/source consent
and revision checks inside the actual authoritative write transaction. Source
withdrawal/cleanup requires its own continuing authority; no durable health
state or permission operation is implemented by this module.

## Existing consumer and adoption holds

Worker39's separate retained consumer composition is
7e6fa5972e108d884edce26fe4e81b842d862b38, three native-health-import-owner39 paths.
It declares the exact94b84 parser hash and composes import/withdrawal through
injected authentication/confirmation/transaction services. Those files remain
owned by39 and are not copied or altered here. Current contracts and review
limitations are read from that immutable pin; no closed review suite was rerun.

Owner04 supplies verified session/person policies and a compatible atomic health
store; generic /api/state D1 proof is not health-schema compatibility. Owner03
owns actual UI confirmation/availability; owner02's central wiring hold persists.
Owner34 retains planned/measured-overlap responsibilities and separate consumer
review. No central persistence, D1, caller, overlap, grant cleanup, provider or
device implementation is accepted by this preview closure.

## Evidence and checks

Original Product Review PDF02 printed p8 and pp10–12 distinguish optional native
companions from browser OAuth and require person-specific consent, privacy,
source/date/unit provenance and real device verification. Retained report:
research/reports/02-OffMenu_Product_Review_and_Plan-1-.pdf, SHA-256
2d1ec141bf3694f7dd1305b1dec9a78197bcf16ba156bfab7c4dfb2aebd44d9c.
P2-08/DATA-14 remain broader requirements, not completion claimed by this slice.
Earlier official Health Connect/HealthKit documentation evidence remains in the
exact39 review; no fresh SDK/version compatibility or native permission claim.

Current-base command: node --test tests-web/health-import-owner28.test.mjs.
Result: five passed, zero failed. These are synthetic checks, not actual vendor
export fixtures, device permissions, clinical assurance or end-to-end app proof.
Source/test SHA-256 comparisons passed before writing; staged bytes are checked
again before checkpoint. Main HEAD/ref/index and retained task refs are checked
before/after. Initial main HEAD8652b312ce7989c5e4f2d49ae765d5d8daf5841d;
index SHA-2564332ef16a3df2cd9032b4f099a74425a111bd2e5448e0f5066c5f3f3cb54f389.
Prior preview a108, review f235054c307497a195b23d77f3895c1135b57b0f and
source-collection receipts remain preserved. Raw sources remain outside Git.

No new private-health import, source acquisition, credentials, SDK, server,
deployment, source admission or new worker. Production STOP and all ownership,
rights and exact denial holds persist. Supplied filesystem unrestricted/network
enabled; mandatory reviewer auto_review unchanged; separate approval policy
unavailable. Completion is a frozen f6 PREVIEW CANDIDATE FOR REVIEW, not accepted
central persistence or a native integration. Full candidate/private-backup pins
are reported in the handoff; no self-referential commit field is invented here.
