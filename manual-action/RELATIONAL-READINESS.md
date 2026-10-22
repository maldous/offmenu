# Retained-data relational readiness — evidence checklist

**2026-10-22 · source review, not a Foo observation or execution receipt.**

The earlier condition was to fetch on Foo only once the databases are provisioned
and relational **for the data already held**. The later instruction to add
additional sources and fetch them separately authorizes acquisition; this
checklist does not veto or gate that separate workflow. The present foundation
does not establish relational/application readiness. It supplies eight additive
staging databases and normalization sidecars; their declared binding is **not
application-bound**. This checklist itself does not launch a fetch, migration,
source rewrite, new household input, or an ingestion rerun.

## What exists in the reviewed source

`ingest_store.py:SCHEMA` gives each domain the same source-faithful tables:

- `sources` primary key: `(source_key, version)`.
- `records` primary key: `(source_key, source_version, record_id)`, with an
  in-database FK to `sources` and a canonical-JSON `content_sha256`.
- `record_fields` and `relations` reference their **owning source record** by
  that complete composite key. A relation additionally has an ordinal, kind,
  `target_domain`, `target_id`, and preserved `detail_json`.
- `relations_target(target_domain,target_id)` is an index, **not a target FK**.
  There is no target source namespace/version, cross-database FK, or reviewed
  canonical entity registry in this schema. `logical_records` groups plain
  `record_id`; its counts are not globally distinct entities.

`source_key` is a truncated hash of the catalog source ID/path (`ingest_api.py`).
`source_version` hashes filesystem metadata plus adapter selection, not the
entire source dataset. Metadata fingerprints must not be presented as verified
full-file custody checksums. The record payload hash is a separate identity.

The public domains live under `<state>/staging/<domain>.sqlite3`; profiles and
inventory live under `<state>/private-household/staging/`. `ingest_meta.binding`
is `additive_staging_not_app_bound`. `completed_outputs_available` checks owned
output identity/count markers and pending work; its own contract explicitly
does **not** perform a full integrity check or establish app binding.

## Eight-domain join inventory and exact gaps

| Domain | Present identity / useful relationship | Evidence still needed |
|---|---|---|
| Barcodes | Imported lexical code fields, or `readonly_source_reference` wrappers recording recognized original tables, code columns, PKs and indexes (`ingest_existing.py`). Normalization checks GTIN syntax/check digit and preserves source namespace/zeros. | Distinguish reference rows from product rows. Confirm each actual retained-store schema and lookup key. Check validated aliases for multiple source claims, conflicts and packaging distinctions; syntax validity is not issuer/product verification. A reference wrapper's row ID is not a product ID. |
| Ingredients | Recipe mentions use `<recipe_id>:ingredient:<ordinal>` and an `ingredient_of` edge. Native ingredient entities retain `source_native_id`; normalized ingredient IDs intentionally remain unresolved. Product mentions retain native product ID plus a `source-product:<hash>` target (`ingest_recipes.py`). | Verify reciprocal recipe/mention coverage. Supply reviewed source-ID→ingredient-entity mappings, including plant part/preparation. Product-target hashes are **not guaranteed to equal barcode `record_id`**; an explicit provider/native-product-ID→product-key bridge is required. Never join by a fuzzy name. |
| Recipes / menus | Recipe IDs are content-bound source identities. `has_ingredient_mention` points to ingredient mention IDs; menus have `contains_menu_entry` edges to recipe-domain child IDs. Recipe and ingredient adapters share source/version computation for the same ordinary recipe source. | Count zero/one/many target matches under the intended source/version first; do not silently select among provenance duplicates. Check both directions and menu parent/child closure. Menu→recipe/venue relationships and ingredient-entity links remain source claims or candidates, not accepted cross-domain joins. |
| Dietary | Content-bound retained assertion IDs, `source_record_id`, provider/source identity, original fields and precise numeric lexemes (`ingest_misc.py`). Nutrient bases remain distinct in normalization. | There is no emitted general dietary→ingredient/product edge table. Establish an explicit source/provider food ID namespace and reviewed mapping; distinguish per-100-g, per-100-mL and per-serving. Source diet/allergen assertions are not automatic suitability rules. |
| User profiles | App-runtime-managed, not an external-ingestion input requirement. Historical staging rows are preserved; DomainStore uses source record `id`/`source_id` or a source-row fallback; normalized scope requires namespace plus household ID and retains user ID. | No external/private-input request is required. Record `schema_only_app_managed` for empty staging, not fabricated rows or a claim that app migrations are deployed. Verify stable user/household keys, missing scopes, collisions and access isolation before linking. Source admission flags alone do not prove every row has a usable join key. |
| Inventory | App-runtime-managed, with no external fetch/import requirement. Existing historical staging identity, item/product references, quantity and location are retained. | Prove inventory→household/user and inventory→product/ingredient mappings with explicit scope and namespaces. A row-number fallback is an occurrence ID, not stable item identity. Confirm no cross-household/user joins. Empty private inventory is legitimate and must be reported as such. |
| Suppliers | Staging record IDs hash `(source_key, source_pointer)`; native `entity_id` is separate. Ownership edges target native entity IDs, with source property/subject claims (`ingest_suppliers.py`). | **Do not join ownership `target_id` directly to `records.record_id`.** Build/check the explicit provider/entity-ID lookup, reporting missing and multiple matches. Organization, place, supplier role, ownership and price observation remain distinct. No brand-prefix→supplier or venue-name→organization inference. |
| Citations | Content-bound citation IDs; `source_key`, `source_record_id`, reference and parent-reference metadata are kept distinct (`ingest_misc.py`). URLs retain meaningful fragments/query data. | No automatic domain-record→citation FK is emitted. Establish an evidence-link registry from the complete source-record key to citation IDs, evidence fragments and rights/custody claims. Do not inherit a parent digest as a child digest or treat matching URLs/license strings as rights clearance. |

`record_fields` is a bounded convenience index (depth limit, first 64 array
items, configured maximum indexed fields). A missing index entry does not prove
the full payload lacks a field or relation. Read `payload_json` under bounds for
completeness checks; do not use REAL numeric indexes as exact lexical values.

## Proposed exact crosswalk contract (not yet implemented)

Additive crosswalk storage must distinguish **identifier claims** from a
**selected, evidenced resolution**. It must not edit source rows or infer a
canonical entity from a name, equal hash, or unscoped numeric value.

The lookup key is the complete tuple:

```
(target_domain, identifier_namespace, provider,
 source_key, source_version, source_native_id_lexical)
```

`source_native_id_lexical` retains its original string/leading zeros; its source
value type and source JSON pointer are recorded separately. A generated
occurrence ID is not mislabeled as a native ID. Unknown provider/namespace is
an explicit unresolved prerequisite, not the universal namespace `unknown`.

Each resolution record contains:

```
lookup_key                         # tuple above, no fields omitted
selected_snapshot_id
join_contract_id / mapping_rule_version
disposition: resolved | missing | ambiguous
reason_code
targets: [{domain, source_key, source_version, record_id, content_sha256}]
evidence: [{source_record_identity, json_pointer, asserted_namespace,
            asserted_value, mapping_rule_id, review_evidence_ref_if_required}]
canonical_entity_id: null          # unless a separate reviewed registry exists
```

`resolved` requires exactly one compatible target in the selected snapshot;
`missing` means none; `ambiguous` means multiple compatible targets or
contradictory claims. Unsupported or unverified namespace/schema contracts use
`missing` with a precise reason, not a guessed target. Equal record IDs in two
source/version partitions are still different target identities. Multiple
provenance rows may be associated with a shared entity only through a separate
reviewed entity mapping; a crosswalk cannot manufacture that equivalence.

A separate relation-resolution record binds the **owning full record identity
plus relation ordinal**, the exact lookup key, contract/snapshot versions and
disposition. That makes every claimed join auditable without changing existing
`relations.target_id`. The term canonical record identity here means the full
chosen target-record tuple, not an assertion of worldwide entity identity.

### Exact mappings already recoverable versus adapter changes

| Gap | Exact evidence already in payloads | Required addition / limit |
|---|---|---|
| Recipe↔mention | Recipe `id`; mention `id`/`recipe_id`; reciprocal relation IDs; ordinary shared recipe sources have the same source key/version. | Read-only checker can test these now using source-scoped identity. Add explicit relation-resolution rows for durable proof; no ontology/name match needed. Do not assume independently transformed sources have matching versions. |
| Menu parent→child | Parent `contains_menu_entry.target_id` and emitted child `id` in the recipe domain. | Read-only scoped target check available now. Cross-source menu→recipe or menu→venue requires explicit native reference fields and a source-specific namespace contract; absent references remain absent. |
| Product ingredient→barcode | Ingredient relation `source_native_product_id`, `product_id`, provider/source provenance; native barcode sources may expose lexical code, FDC ID or a verified physical code column. | A provider-specific bridge must select the correct native product identifier and schema. Never compare the `source-product:` hash with a barcode row ID. Reused-store wrappers require a read-only lookup adapter to their **actual product tables**, not a join to the wrapper itself. FDC ID and GTIN are different namespaces. |
| Ingredient↔dietary food | Ingredient `source_native_id` plus source provenance; dietary `source_fields` retains explicit `foodId`/`food_id`/`FOODID`/`fdcId`/`fdc_id` where supplied. | Exact equality can be tested only inside a verified same-provider/same-ID-system contract. Extend adapters to emit typed identifier claims/edges with source pointers. Cross-provider food equivalence, plant part/preparation, missing IDs or a generic `code` field still need reviewed mapping; no text matching. |
| Supplier ownership | `entity_id`, `provider`; relation `subject_id`, `target_id`, source property and assertion. These are distinct from hashed staging record IDs. | Checker can build an exact provider/entity-ID lookup from payloads now. Durable adapter output must declare identifier namespace and target-source/version policy. Several retained occurrences of one entity produce ambiguity until a reviewed entity/provenance association is supplied; do not choose the first row. |
| Citation attachment | Citation `source_key`/`source_record_id` and reference fields; domain records retain source provenance. | Same source key alone is many-to-many and insufficient to attach one citation. Add explicit complete-record-key→citation-ID edges from a verified native citation/reference ID, evidence URL+fragment contract, or source-level coverage declaration. Without such evidence, record unresolved attachment. Rights clearance remains a separate evidenced decision. |
| Profile→inventory→product | Explicit household/user IDs and namespace if present, inventory item ID/product reference if supplied; private source admission flags. | A private adapter must emit stable scoped keys and typed product-ID namespace/edges. No rows or private identifiers are invented. Empty domains remain schema-only. Source-row fallback or unqualified product ID cannot establish the join. |

Provider spelling aliases are not silently equated. Any reviewed provider-alias
contract must be versioned and retain the original provider claim. Crosswalk
evidence stays local with the source data; only code/schema/tests/documentation
belong in the approved source-only publication.

## Normalization does not close these joins automatically

The common artifact binds `(domain, source_key, source_version, record_id,
content_sha256)` to immutable rule/interpreted versions, source originals,
field lineage, actual-review evidence and translation bindings. Its relations
remain source claims. `exact_identifier_links` produces candidates only, never
merges. Normalization storage is private sidecar storage, not a migration of
the eight app databases.

`gold_readiness` checks actual interpreted review, uncertainty, language,
translation, rights/custody and citations. `build_gold_manifest` also requires
authoritative expected counts for every domain. Neither checks every real
cross-domain target, provisions application schemas, verifies application
queries, or enables FETCH. A gold candidate and relational/app readiness are
separate decisions.

## One local, read-only evidence report — proposed contract

Prepare **one** private report, `retained-relational-readiness.private.json`,
against one declared terminal retained-ingest snapshot. The original specification
below is implemented conservatively by `relational_readiness.py`; see
`RELATIONAL-REPORT.md` for its narrower no-WAL immutable-read boundary, explicit
unsupported dispositions and remaining gaps. This is **not a completed check**.
Do not run `./run` merely to obtain it: that command performs ingestion.

### Inputs and read boundary

1. Use the exact existing state directory, current complete source catalog,
   latest terminal receipt and code/rule versions. Include only explicitly
   referenced retained barcode stores; no filesystem-wide discovery.
2. Record each file's main/WAL identity and owned database ID before and after
   the report. Open existing databases with URI `mode=ro`, `query_only=ON`,
   `trusted_schema=OFF` and bounded read transactions. Do not use `immutable=1`
   on a possibly WAL-backed store. Do not checkpoint, vacuum, migrate, create
   indexes, truncate WAL, stop writers, or repair anything.
3. If writers are still active or any source/output identity changes, label the
   cross-database snapshot **unstable/unknown**, not complete. Independently
   pinned transactions do not by themselves prove a coordinated snapshot.
4. Give the report a declared resource budget. A cap or unreadable/unrecognized
   table produces incomplete coverage, not a pass or an invented zero. No
   retries, repeated ingestion, or continuing background loop are implied.

### Contents from that single pass

- Per database: existence, binding/schema/database ID, schema/index/FK metadata,
  full integrity-check outcome, owning-record FK violations, actual table
  counts, source terminal/error states, selected source-version counts, and
  explicit zero-input private-domain dispositions. Integrity checks are exact
  only if their full scan completes; sampled checks cannot certify integrity.
- Full current-record count and payload-hash agreement, separately from
  historical versions, native external-store table rows, source references,
  changed-record writes and the cached `record_count` marker. Reconcile counts
  to the selected terminal catalog; metadata-based versioning alone cannot
  recover overwritten source occurrences or certify full raw-source custody.
- For each **declared relation kind and join contract**: edge count, null/
  unsupported targets, uniquely resolved targets, missing targets, ambiguous
  targets, source/version/namespace mismatches, and reciprocal mismatches where
  a reciprocal contract actually exists. Classify provider-native supplier
  entity joins and synthetic product-reference joins separately from recipe
  record-ID joins. Unresolved candidates are not successful joins.
- Per-domain normalized coverage: no artifact, rules-only, actual review
  pending/rejected, validated interpreted, unresolved/error, translation
  pending and gold-blocked. Reconcile artifact source/content/version identity
  against the same selected staging snapshot, not just matching total counts.
- Private-scope checks: missing namespace/household/user bindings, duplicate
  scoped keys and cross-scope edge attempts. Keep row values and diagnostics
  local; a shareable return contains only fixed status/count fields, never
  personal fields, identifiers, paths or source payloads.
- App-binding evidence: exact configured database identities/schema versions,
  explicit adapters/views for the declared joins, read-only representative
  application queries and their expected cardinality/results. If that app
  configuration or contract is unavailable, report `app_binding_unknown`.

Store the report privately and bind it to the complete observed snapshot/code
identity. Reuse it while that identity is unchanged; rerun only after a relevant
data/schema/mapping/app-binding correction, not as a ritual. Never publish the
private report or native rows in a source-only consolidation commit.

## Acceptance checklist / stopping condition

- [ ] All eight domains accounted for; absent private data explicitly accepted
  as schema-only, with no assertion that private joins were exercised.
- [ ] Current retained-source coverage and full integrity checks established;
  partial/failed/unknown sources are enumerated and dispositioned.
- [ ] Every required application join has a named key/namespace/version/scope
  contract and measured cardinality; no required missing/ambiguous edge is
  quietly counted as resolved. Optional unavailable relations are explicit.
- [ ] Source evidence/citations/custody and normalized/review/translation
  coverage match the same current snapshot; unknown totals remain unknown.
- [ ] Application bindings and read-only end-to-end queries are demonstrated
  against those exact stores, rather than inferred from staging receipts.
- [ ] No cross-household/user linkage; any real private inputs remain local.
- [ ] The user-facing decision records what is ready **for currently held
  data**, what is intentionally absent, and any remaining blockers.

**Current observation boundary:** this review read local source/schema/tests
only. Actual Foo databases, terminal run state, app configuration and retained
join counts have not been inspected here. Their readiness is **unestablished**,
not a claim that they are corrupt or missing. The report itself has no fetch
capability and changes no acquisition settings or authority.
