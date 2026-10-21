# Retained product-detail federation v1

`offmenu.refresh.product_detail_federated_query` is a separate backend implementing
Worker13's selected consumer delta v1. The accepted native query (`c8600baf…`),
writers, schema and all retained store states are unchanged. This source creates
no database, view, observation reconstruction, import, source factory or runtime
activation. Tests use generated databases and qualification stand-ins only.

## Typed API and custody

Use the four names specified by13, all from this new namespace:

```python
FederatedIdentifierEvidence(db, run_id, database_sha256)
FederatedStoreEvidence(role, db, database_sha256,
                       load_receipt_sha256, qualification_sha256)
FederatedQuerySelection(generation_id, input_manifest_sha256,
                        operation_selection_sha256,
                        identifier_database_sha256)
read_federated_product_details(current_identifier_rows, *, selection,
    identifier_evidence, stores, selected_manifest,
    max_candidates=100, max_result_bytes=262144,
    max_steps=100000, max_seconds=5)
```

`stores` is a tuple of distinct exact-type evidence objects. Enabled roles are
`off-subset`, `usda-products`, `usda-profiles`; USDA roles enable together. Every
connection, including the identifier connection, must be distinct, idle,
query-only, and have only its main database (no attachments or TEMP namespace).
The function does not enable query-only, commit, roll back or open connections.

Caller05 independently selects and simultaneously holds all enabled files as RO,
with regular/no-follow custody and matching held/name fiveTuples at entry/exit
through final HTTP serialization. It verifies current load receipts, independent
qualification, external digests, immutable selection identity, rights and operation
scope. Evidence dataclasses and manifest flags do **not** perform that qualification.
The backend does not stat/hash/open any actual backing file, defend against
arbitrary same-UID external writers, or infer authority from a request. Native
configuration must never reuse a federation generation with changed backing pins;
there is no cross-request registry or controller in this library.

## Concrete selected-manifest encoding

The manifest is a native-selected dict. Its digest is SHA256(core.canonical(dict)):
sorted UTF8 JSON plus LF. The backend checks that digest and freezes nested values
by a canonical round trip. Its maximum encoded size is262144 bytes. Required keys:

- `version`: `retained-product-federation-manifest-v1`.
- `generationId`, `operationSelectionSha256`, `identifierDatabaseSha256` match
  selection; `identifierRunId` matches independent identifier evidence.
- `identifierFiveTuple`: five nonnegative integers, positive file size;
  `identifierLoadReceiptSha256`, `identifierQualificationSha256` are external pins.
- `roles`: exactly the three role names. Every role explicitly declares `enabled`.
- `usda`: required when the paired USDA roles enable, as described below.

Disabled roles declare `qualificationState` (`not-qualified` or `restricted`) and
safe lowercase `reasonCode`. They have no evidence object in `stores`. Missing
OFF qualification therefore disables OFF while permitting qualified USDA. Each
enabled role declares `qualificationState:qualified`, `databaseSha256`,
`loadReceiptSha256`, `qualificationSha256`, `fiveTuple`, `countsEvidenceSha256`,
`rightsReceiptSha256`, `operationEvidenceSha256`, and
`countBasis` (`independently-qualified` or `producer-reported`). The three context pins must match its evidence
object. The native caller must bind the declared fiveTuple and external receipt
meaning to that held context; the query cannot independently establish these facts.

USDA common selection contains `sourceId:usda-files`, `releaseId:2026-04-30`,
`assetId`, `candidateSha256` (the selected706c767d…candidate), `candidateBytes`,
positive equal `products`/`profiles`, `identifierInputId`, `projectionVersion`,
`representation:usda-native-jsonl`, `candidateFetchedAt`, `originalSha256`,
`qualificationSha256`, `sourceContractSha256` and `rightsReceiptSha256`.
The current backend explicitly supports that selected candidate/release, without
opening it. `candidateFetchedAt` is required explicitly: JSON null preserves a
known-null retained provenance clock; otherwise it must be a valid nonempty UTC
timestamp. Both raw records must contain `provenance.fetchedAt` and match the
selected value exactly, without normalization. Missing is distinct from null.
This is **not** an inferred original acquisition time: no mtime, completion,
qualification or query clock may replace an unknown value.

Both USDA role entries bind the same source/release/asset/candidate plus their
own `manifestSha256`, `sourceAssetCount:1`, and complementary retention counts:
products role `(retainedProducts:N, retainedProfiles:0)`, profiles role `(0,N)`.
Each backing `manifestSha256` is the producer's core-canonical UTF8+LF
`input_manifest_sha256`, not the hash of a pretty-printed metadata file.
The products role adds `assetSpecSha256` (core canonical asset descriptor). The profiles role adds `loadId`,
`provenanceManifestSha256`, `originalAcquiredAt` (nullable) and
`acquisitionClockState`. Its operation-evidence pin is checked against
`dietary_input`. The original clock facts are distinct from `candidateFetchedAt`;
null/unknown-retained remains null/unknown-retained in the response binding.

An enabled OFF role adds source/release, `generationId`, `sourceManifestSha256`,
`sourceOperationSha256`, `coverageSha256`, `subsetCertificateSha256`, exact `assets`
(committed asset coverage entries), `sourceAssetCount`, `retainedProducts` and
`retainedProfiles`. It requires an independently qualified immutable subset of
at most256 OFF assets from the original257-target incomplete generation. The
exact asset allowlist/counts/coverage digest and identifier context must match its
original SQL generation. Qualified operation lineage comes from that pinned
coverage. This does not mark the old generation completed or publish a snapshot.
An asset's expected operation is the original operation until the last resume
whose `startedAfterAssetCount` is no greater than its zero-based allowlist
position. This is the writer's attribution rule, not membership in all lineage
operations. Starts must be nondecreasing nonnegative integers within the prefix;
operation IDs are unique, and trailing empty attempts claim no earlier assets.
Actual256-subset qualification/publication remains64/57 work, not an author claim.

The artifact API and synthetic manifest example accompany each source freeze.
No field names in this concrete schema require a change to13's named API.

## Point evidence and output

Every observation first matches the persisted assertion PK in the independently
selected run, all12 accepted fields, source-asserted disposition and completed load.
Known identifiers stay known when detail availability is missing or restricted.

USDA uses Ingredient's indexed `(asset_id,asset_sha256,source_ordinal)` unique key
and audit PK; its deterministic reference must match core canonical asset/hash/P.
Only a selected odd native packet ordinal P permits the P+1 profile PK lookup.
Dietary audit/input/load and both raw packets must agree with the selected cohort.
The backend unwraps one-element packets, verifies source/native IDs, acquisition
stamp, private-candidate scope, schema, data/countries, nutrition link and complete
identifier lists. It never reconstructs profiles from nutrient observations.

The three digest encodings stay distinct: Ingredient's object hash uses core
canonical **with LF**; Dietary's packet hash uses exact original packet UTF8
**including LF**; derived pair/field evidence uses acceptance canonical([product,
profile]) **without LF**. Pair evidence is labelled `verified-retained-components`.
Raw extension/null/text/number values retain the accepted strict parser semantics.
OFF resolves every eligible indexed variant, verifies certified asset membership,
original coordinates, row/pair hashes and operation lineage. Virtual references
are deterministically namespaced with federation/backing identity and coordinates.
Each selected OFF projection's stored limitations are fetched by reference PK
after a byte-length check, charged to the aggregate byte budget before fetching,
and validated as a JSON string array. All entries, order and duplicates remain;
the subset-only caveat is appended. Malformed or oversized caveats fail typed;
they are never discarded or truncated. The complete response cap includes them.
Missing/mismatched pairs are unavailable; corrupt eligible digests and technical
failures are fixed typed `product-detail-federation-*` errors, never identifier misses.
For disabled USDA pairs, both required roles contribute disposition and reasons.
Any restriction takes precedence over not-qualified. The primary `reasonCode`
comes from the first restricted role (otherwise the first required role), while
`roleReasons` retains both roles' qualification states and reasons in product,
profile order. Availability and backend coverage use the same aggregation. All
added reason metadata is included in the unchanged complete response byte cap.

The result follows13's envelope, adds backend, selectionManifestSha256 and separate
backing store pins, and never supplies a synthetic single detail database digest.
Caller05 sets details.detailDatabaseSha256=null and validates generation, selection,
identifier digest and backing pins before composition. It preserves identifier
rows/cursor/generation on typed detail failure. Its complete final serialized HTTP
cap, including wrappers/errors/new metadata/LF, remains262144. SoleUI owns the
separate offlive rendering delta and later selected activation.

Coverage always has null expectedAssets/processedAssets/products/profiles,
coverageMode `federated-source-retention`, complete:false and accepted:false.
Per-backend qualified counts stay separate from target257/6908496/6908496. Their countBasis is
producer-reported if either backing count remains producer-attributed, even when
the store has a scoped independent point-access PASS; populationCountIndependentlyVerified
then remains false. Producer counts alone never enable a role: current independent
store qualification and custody are still required. This does not certify a whole
population from point evidence. Disabled
roles have no enabled counts. USDA pair validation is selected-pairs-on-query;
Dietary observation counts never become products. OFF is explicitly subset-only.
No aggregate materialized generation, country, canonical, English or gold
completion is implied.

## Shared budgets and acceptance boundary

At most25 observations and1000 aggregate enumerated candidates are allowed.
The result cap is262144 core canonical bytes including LF and **all** metadata,
including empty/missing results. Source payload bytes share that cap before fetch.
Each connection has the same aggregate VM/time guard; max_steps is at most1M,
max_seconds at most60. SQL length uses at most4MiB or the caller's stricter limit;
control JSON is independently bounded at2MiB. All installed progress handlers are
cleared and prior SQL limits restored on every exit. No wall-time/store-size/CPU
success is inferred from synthetic tests. Errors have safe fixed codes, not paths
or raw SQL messages;05 owns the separately bounded transport error envelope.

Source acceptance, Ingredient output acceptance, OFF certificate qualification,
current custody/rights,05 binding, soleUI rendering and actual activation remain
separate exact gates. Existing64 reviews the narrow new backend delta;00 owns
normal integration. Gateway owns scheduling and ledger reconciliation. No new
bulk USDA retry, body scan/copy, live reload or population job follows this source.
