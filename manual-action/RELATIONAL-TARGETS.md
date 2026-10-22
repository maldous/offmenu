# Optional additive relational targets — explicit invocation only

`ingest_relational_targets.py` now **materializes useful typed tables and exact
joins**, rather than only reporting generic staging rows. It is **not enabled by
the standard `./run`**, including isolated receipt transport: that run uses the
existing staging databases without an additional derived snapshot/payload copy.
The implementation remains available for a separate explicit invocation, offline
after all domain workers close. Existing outputs are preserved, never cleaned up
or represented as newly materialized by a standard run.
This package was developed against synthetic fixtures;
no actual Foo databases or current `./run` were opened or changed here.

## Output and binding

When explicitly invoked, all eight domains are represented in a single versioned join database:

```
<state>/private-household/relational-targets/v1/<snapshot>.sqlite3
<state>/private-household/relational-targets/v1/<snapshot>.manifest.json
```

Everything is private (files `0600`, new directories `0700`), including public
source projections, so joins cannot accidentally publish household records. The
original eight staging stores and retained native files are never migrated,
rewritten, checkpointed, repaired, or replaced. Native product-store reference
wrappers remain references, not millions of invented product rows.

The exact source-to-adapter-to-staging-to-derived contract is in
`relational-target-mapping.json`; SQL is `relational-targets.schema.sql`.
`source_records` retains the complete domain/source/version/record/content identity.
Typed target tables cover recipe headers, ingredient mentions/entities, menu
entries, product IDs, dietary assertions, suppliers, citations, household profiles
and inventory lots. `identifier_claims`, `relation_claims`,
`relation_resolutions`, and `relation_candidates` preserve every declared edge,
its mapping contract, lookup scope, zero/one/many cardinality and provenance.
`resolved_links`, `recipe_ingredient_links`, `menu_member_links`,
`supplier_ownership_links` and `citation_links` are actual queryable joins.
`unresolved_links` is queryable too; missing/ambiguous links never disappear.

### Actual application schema inspection

At repository commit `8652b312ce7989c5e4f2d49ae765d5d8daf5841d`:

- `cloud/schema.sql` defines D1 `products(barcode,data,...)`,
  `recipes(id,title,doc)`, `unified_records(owner,id,...)`, `user_state` and
  `kitchens`, among other tables.
- `offmenu/core.py` defines a different local `products`, `mappings`, `recipes`,
  `requirements` and `inventory` schema; recipe requirements use explicit
  quantities/units and ingredient names.

Neither is the eight generic staging databases. A reviewed source schema is not
evidence of the runtime application's DB identity or an accepted migration.
Therefore this target is explicitly **`versioned_derived_not_app_bound`**,
`app_binding=deferred`; no app tables are silently populated and no app readiness,
semantic review, translation, suitability, rights clearance or gold status is
claimed. A future app adapter must select the real intended contract and pass
representative scoped queries against the actual bound stores.

## Implemented join contracts

1. **Recipe/mention:** same source key/version, exact recipe and mention IDs;
   reciprocal checks apply to actual `recipe` rows, not to menu compositions
   masquerading as cooking recipes.
2. **Menu:** exact parent/child, observation/anchor, source-composition and
   source-ingredient edges. Cross-file Bègles/Toulouse links use the explicit
   selected source family, publisher-local sub-scope where required, typed native
   ID and emitted scoped target ID. Bègles needs both SIRETs. Toulouse's family
   itself is the namespace, so its explicit null sub-scope is valid. No names,
   suffix stripping, numeric/string coercion or venue guessing.
3. **Products:** materialized OFF records' lexical `code` is bridged to product
   ingredient references, only with identical provider and physical source
   fingerprint (adapter version may differ). The `source-product:` hash is never
   treated as a barcode ID. Original leading zeros and identifier types survive.
4. **Dietary:** explicit FDC fields can link to ingredient entities under the
   same provider/source-asset contract. Raw nutrient basis, units and numeric
   lexemes are retained; other food namespaces require reviewed contracts.
5. **Supplier:** source-scoped `(provider, native entity_id)` crosswalks link
   ownership claims to stored record identities. Multiple occurrences remain
   ambiguous; no first-row selection or canonical entity manufacture. Ownership
   and price observations are separate `supplier_assertions`, not entity targets.
   A relationship assertion's subject and object must both resolve before it is
   presented as a fully linked ownership tuple.
6. **Citation:** acquired adapters emit exact `cites` / `cites_record` edges.
   Legacy citations without an explicit record reference retain a countable
   unresolved attachment; matching URLs/source keys do not imply attachments.
7. **Private:** inventory/profile joins require the same explicit namespace,
   household and user. Missing scopes and product mappings remain deferred.
   Empty private domains get real schemas and `schema_only`, not fabricated data.

The selected local snapshot is **not an atomic publisher export**. Acquisition
batch agreement alone cannot prove common release dates or that all cross-file
references were published together. Source versions and duplicate targets remain
separate; absent links remain measurable.

## Execution, bounds and reuse

Only a separately explicit caller (or an explicitly configured engine API call
with `materialize_relational_targets=True`) runs this phase. The standard runner
sets that option to `False`. An example explicit API invocation is:

```python
result = materialize_relational_targets(
    state_dir, selections, catalog_complete=True,
    max_records=100_000_000, max_seconds=3600,
    reserve_bytes=2 * 1024**3)
public_counts = sanitize_relational_summary(result['summary'])
private_manifest = result['manifest']
```

Selections must contain actual `domain`, `source_key`, `source_version`; private
pending details may use `stored_source_key` / `stored_source_version` when a
reference/ingredient-derivation key differs from its catalog key. Never infer the
latest source version or include a not-yet-read version as if it were present.
API defaults are deliberately smaller (2 million records / 120 seconds); the
explicit caller may supply the generous finite bounds above. Caps produce
`partial` plus `resource_budget`, not a success or a reason to fetch more.
The shared filesystem's free bytes are checked before creating a target and
throughout copying/resolution, preserving the configured disk reserve plus
headroom for the next projected record. A low-space stop adds `disk_reserve`,
commits its safe cursor prefix and resumes later; it never deletes older data.
This guard cannot exclude unrelated concurrent disk consumption, but an actual
SQLite I/O failure rolls back the current transaction, not the staging stores.
An optional `progress_callback(summary)` publishes sanitized partial counts at
most once per 60 seconds after committed batches. Delivery failure is isolated
from loading; the final summary is the completion evidence, not a progress tick.

All existing staging writer locks are held shared. Any active writer, missing
lock, nonempty WAL or rollback journal causes explicit deferral, never
checkpoint/repair. A regular zero-byte WAL contains no header, frames or committed
data: it may be ignored only under these locks with its exact file identity bound
into that run's observation manifest and checked before/after. Empty-WAL inode
churn is not a logical content change and does not invalidate target reuse.
It is never deleted or truncated.
Read connections are immutable only inside this guarded no-WAL-data boundary.
Main/WAL identities and journal absence are checked before/after. Every copied payload's stored SHA-256 is
verified; all derived FK constraints are checked. This does **not** claim a full
raw-file custody checksum or complete staging integrity scan.

Copying is cursor-checkpointed by exact selected source primary key, and partial
targets resume without rereading already materialized records. Resolution starts
only after the selected available records have all been copied; an incomplete
candidate population cannot yield a uniquely resolved edge. Resolution itself
also resumes. Identical input/code snapshots reuse completed outputs only when
their private manifest and actual output file identity agree. Completed source
reopens do not invalidate identity (covered by a synthetic test). Changed inputs
create a new immutable snapshot namespace; old records are never destroyed.
An interrupted derived write has an explicit private `write_in_progress` marker.
Only that owned derived database may recover its own SQLite journal and resume
after SQLite quick/FK checks; input databases are never recovered or repaired.
`relational_outputs_available(state_dir)` is the coordinator's metadata-only
completion-cache guard. It checks the private receipt, exact owned snapshot path,
persisted manifest, code/mapping and output/source identities under shared source
writer locks. A deleted/replaced target or missing manifest cannot skip needed
work; no source-record reread is required to verify this cache boundary.

`complete` means the selected available rows were materialized and resolution was
attempted, **not that every relation resolved or the entire ingest completed**.
`source_partial`, `catalog_incomplete`, `untyped_records`, unresolved counts and
`app_binding_deferred` remain visible even when that bounded phase completes.
The outer ingest/evidence report is still authoritative for unread/failed sources.

## Remaining blockers: action / target / reason / status

| Action | Target | Reason | Status |
|---|---|---|---|
| Confirm runtime DB contract and implement reviewed app projection | Cloud D1 or local app DB | Verified schemas differ; runtime target/migration unproved | Deferred; no app write |
| Inspect and implement sealed read-only native product lookup | Retained barcode-store product tables | A reference wrapper is not a product, and external writers/WAL may exist | Deferred; references retained |
| Add reviewed provider ID contracts | Other dietary/product namespaces | Generic `code` or equal numeric IDs do not prove shared identity | Deferred, countable |
| Supply explicit record attachments | Legacy citation metadata | Source key/URL equality is insufficient | Deferred, countable |
| Supply explicit private input and scopes if desired | Profiles/inventory | Private data may legitimately be absent | Schema-only accepted; missing scopes deferred |
| Inspect an explicitly requested derived run's exact missing/ambiguous links | Selected retained snapshot | No live Foo counts were measured during development; standard run creates no derived snapshot | Deferred until explicitly invoked |

Synthetic tests cover exact joins, ambiguous suppliers, same-ID different source,
lexical zero/type preservation, no native-wrapper conflation, menu family scopes,
private isolation, empty schemas, bounded resume, no source mutation, active
writer/nonempty-WAL refusal, unchanged empty-WAL handling, payload mismatch,
output tampering and unchanged-source reuse. Explicit source-metadata wrappers
remain untyped rather than inflating product/dietary counts.
