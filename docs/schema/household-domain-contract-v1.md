# Household and inventory application schema v1 — prepared, not activated

## Scope and evidence

Reviewed source baseline: `af99cdfb4bac3bce9f4badae34333921a0074a76` of `maldous/offmenu`. This is an additive application schema and encrypted-payload contract, **not an external-data ingestion stage**. Household profiles and stock are created by actual application use. There is no external profile/inventory source to fetch and no initial private data is seeded.

The source register is `docs/delivery-reconciliation.json` (105 requirements). Current `cloud/state.mjs`, `cloud/kitchens.mjs`, `public/model.js`, `public/sync-model.js`, `public/household-model.js`, `public/cooking-model.js`, `public/meal-context-model.js`, `public/meal-plan-owner19.mjs`, `public/meal-preference-model.js`, `public/health-model.js`, `public/receipt-review-model.js`, `cloud/intake-history-owner25.mjs`, `cloud/waste-observation-owner24.mjs` and `cloud/lot-restriction-owner28.mjs` were inspected at that exact baseline. The accompanying matrix maps every register ID, without upgrading historical implementation/acceptance statuses. Prior 20 October barcode-first design informed distinct lot/date/product-version handling; it was a proposal, not a deployed migration.

### Three existing stores are different

* `offmenu/core.py`: local CLI product/inventory tables contain barcode, quantity, g/ml/count and an undifferentiated expiry. They are **not** the shared application schema.
* `cloud/schema.sql`: production-source account/kitchen state is JSON, with independent `kitchens`, `kitchen_members` roles and hashed invitations; private profiles are removed by `kitchenProjection`. Existing provider credentials have their own `sealed` legacy field. This preparation does not reinterpret any of those values.
* `manual-action/relational-targets.schema.sql`: `household_profiles` and `inventory_lots` are ingest source-record projections. They are not the app schema. **Do not execute the new application migration against the manual-action target DB.** The same `household_profiles` name has a different contract in a different store.

## Practical next-run preparation

From a reviewed checkout containing the companion security overlay:

```sh
python3 -B scripts/prepare_household_schema.py
```

Default: validate the exact ordered SQL digests and compose an **empty in-memory** schema. No database file, private read, key lookup, fetch, deployment or duplicate template. Repeating this command is safe and writes no files. The integration-ready `./run` hook belongs **after the approved checkout refresh and before ingestion**; route only its sanitized JSON to the preparation receipt. This overlay does not silently alter the owned ingestion runner.

Optional explicit local artifact, under an existing parent:

```sh
python3 -B scripts/prepare_household_schema.py --output-dir /approved/local/new-schema-template
```

The directory must not exist. The command refuses existing directories and never opens an existing app database, overwrites a template or makes a timestamped per-run copy. It creates `household-empty-template.sqlite3` and a value-free `schema-readiness.json`. Do not upload the SQLite file or expand return allowlists to accept private databases. If a preparation fails, inspect/remove only the newly created failed artifact directory before retrying; no existing app data was touched.

Expected state: `schema_prepared_app_wiring_pending`, `private_rows: 0`, `external_sources_required: false`, `deployment_performed: false`, `application_wiring_verified: false`. Failure is explicit and sanitized; do not downgrade it to ready. A dependency SQL digest change requires reviewed regeneration of the preparation plan, not bypassing verification.

Order: unchanged `cloud/schema.sql`, then `20261022-byoc-security-v1.sql`, then `20261022-household-domain-v1.sql`. The latter is a once-only, fail-on-reapplication versioned migration; a future deployment runner must journal its hash, enable foreign keys and execute it transactionally. The preparation command already does this in a fresh empty database. No destructive down migration is supplied.

## Structural coverage

There are 31 domain tables, a schema-version table, and a derived stock balance view. Core keys and relationships are not replaced by a generic JSON staging record. `schemas/household-private-payloads-v1.schema.json` specifies 24 strict, versioned **decrypted** payload types; validate them before encrypting. These payloads are never written plaintext to the database. `docs/schema/household-envelope-bindings-v1.json` is the authoritative object/purpose/AAD mapping. Composite object IDs use compact JSON arrays (equivalent to SQLite `json_array` / JavaScript `JSON.stringify` on the component string array), never delimiter joining. Private attendance includes kitchen, meal and profile IDs even though its envelope remains account-private.

* Account-private profiles, preferences, dated observations, descriptive contexts and explicit exercise schedules, intake, private recipes and collections are owner-keyed. A profile need not have a login. All names, age/body metrics, allergy/religion/taste/culture/fasting details, nutrition goals and professional/guardian declarations are sealed. Unknown values remain explicit, not inferred identities or zero measurements.
* Existing `kitchens` and `kitchen_members` remain the tenant and owner/editor/viewer authority. Multiple homes are separate kitchen contexts; an explicit profile grant targets a current member and exact profile-sharing consent. A carer label never grants authority. No profile row is silently created or shared by accepting a kitchen invite.
* Locations, stock items and source-qualified mappings, lots, quantity conversions, ownership shares, events and checks retain identity uncertainty and physical state. Lot code, package/product version, market and package-date evidence are sealed. Use-by, best-before and review reminder are separate nullable fields. Open/freeze/thaw/decant and relocation events retain history.
* Receipts represent shelf, shopping, waste, receipt-OCR and label-OCR capture. Source digest is scoped by kitchen+owner+source; review is line-complete, correction-aware and immutable once finalized. Image retention is explicit and bounded by receipt retention. Scans preserve barcode string/scheme/namespace, including leading zeroes, and no-barcode/private items without invented GTINs.
* Plans/templates and meals, private attendance, reservations, cooking batches and the immutable movement ledger support measured deductions, leftovers, serving and undo. `stock_lot_balances` derives quantities from movements: there is no separate writable quantity balance to drift. Unknown actual intake is NULL rather than zero. Private recipient/health details never appear in the kitchen stock ledger.
* Shared shopping lists/lines retain claims, checked/purchased states, recipe needs, units, pack rounding, substitutions, price/currency/time/basis and budget preferences in typed encrypted payloads. Handoffs are reviewed exports; `purchase_authorized` is always false. No grocery order is placed by this schema.
* Private recipes, bookmarks, licensed packs and collections are distinct from public community publishing. Rights remain source-qualified; saving a private recipe never grants public contribution rights.

## Hard database guarantees versus application behavior

SQLite/D1 do not provide row-level read authorization here. Composite tenant/owner foreign keys prevent a row from pointing at another tenant's item, lot, location, plan, receipt, owner or envelope; they do **not** prevent an unscoped SELECT. Every read, export, search and decrypt must use a trusted authenticated owner or kitchen membership predicate.

Database checks cover unit identities, integer micro-quantities, dimensional separation, quantity bounds, exact compensating undo, one reversal, nonnegative balances, reservation oversubscription, ownership shares not exceeding one whole, line-review transitions, receipt duplicate keys, waste observations bounded by confirmed discard, source-event duplicate keys (health-observation HMAC includes source record, metric identity and profile; the native source_record_id is preserved), same-owner consent references, exact profile-grant consent scope, and immutable owner/object/purpose envelope binding. Envelope swaps across object, purpose, owner, kitchen or provider fail. Private profile envelopes must have a NULL kitchen scope.

Runtime adapter obligations, not established by the DDL alone:

1. Recheck authenticated session epoch, current kitchen role, object-specific grant, current consent choice/version/expiry, source rights, key status and retention in the **same transaction or equivalent atomic authorization boundary** as a write. Repeat before queued work, commit, serve and export. Viewer may read authorized kitchen data but may not mutate. Membership removal must revoke dependent grants before removing FK-linked ownership/assignment entries; it must not expose private profiles.
2. Enforce compare-and-swap revisions, idempotency request-HMAC equality, and replay the original result on an identical retry. A uniqueness error is not proof a changed retry request is equivalent. Actor IDs, current times and AAD are resolved by trusted code, not accepted as authority from JSON.
3. Strictly validate calendar dates, IANA time zones/offsets and timestamp units at ingress. SQL stores dates independently; it does not prove date validity or food safety. Plan consumption re-evaluates expiry/quarantine/review state at the actual date. Do not infer that a best-before date is a use-by cutoff or that a review reminder makes food safe.
4. Release/consume reservations before deductions in the same transaction. Multi-lot cooking, compensating undo and transfer in/out are one transaction; preserve attribution and original conversion evidence. Prevent served batches being undone. Reject cross-tenant transfer unless an explicit export/import sharing flow is authorized.
5. Only verified, source-scoped ingredient mappings and quantity conversions may drive automated matching. No universal ml↔g, count↔mass, pack↔edible or drained/yield conversion is invented. Fixed units store six fractional decimal places; finer precision is retained as original decimal text and requires an explicit rounding/review policy, never silent truncation.
6. Receipt review is separate from inventory commit; insertion of lots must bind included reviewed lines and add ledger entries atomically. A shelf scan is not a purchase. Source-byte duplicate detection and image privacy are bounded per explicit account/consent. Do not expose personal plaintext digests in public receipts or indexes.
7. Validate decrypted payloads with format checking and semantic cross-field constraints: age dating/adult-only scoring; nutrition `known <= total`; consistent portion remainder arithmetic; source release/version matching; conversion evidence applicability; consent/profile binding; no user-controlled provider URLs or purchase authorization. JSON Schema type validation alone cannot make those facts true.
8. SQL operational metadata (quantities, dates, IDs, roles, state and location linkage) is private and can reveal behavior. Exclude it from public corpus/cache/export/telemetry absent independent authorization. This is **not E2EE**. Server-envelope custody does not hide metadata from a DB operator. Client custody requires a separate non-server-decrypting path and must fail closed.

Health import adapters must derive `source_observation_hmac` from an injective tuple of source, native record ID, metric identity and profile using an account-scoped dedup key, not an unkeyed hash of low-entropy health values. SQL enforces the scoped digest uniqueness, not the correctness of that derivation; retain the native `source_record_id` unchanged. Distinct metrics/people in one vendor record are not collapsed. Exercise schedule payloads permit once/daily/weekly recurrence; calendar/time-zone expansion and semantic schedule validation remain trusted-adapter work.

## Existing-data preservation and adoption gates

**Priority 0 — before any runtime adoption:** implement the authenticated repository/transaction adapter, key resolution/KMS and rotation, profile/grant/consent checks, private payload validation, retention/deletion/restore replay and source entitlements; test viewer/revoked member/second-account races and actual D1 atomicity. No current handler, `validateState`, sync projection or CLI is switched by this batch. Existing state validators currently discard several additional lot fields; preserving them requires deliberate adapter changes.

**Priority 1 — controlled legacy migration:** inventory every stored account/kitchen version without exporting values; map legacy IDs explicitly; retain legacy `expires` as unclassified until its `dateType` or reviewed evidence resolves it; retain unknown receipts unlinked rather than inventing identity. Build an owner-only dry-run that reconciles source counts/quantities and digest-bound transformations. Seal private fields before writing new domain tables. Dual-write/backfill/read-switch must be transactional and reversible by feature flag; never run a generic destructive reset. Do not substitute this new empty template for a populated database.

**Priority 2 — behavior acceptance:** bind scan→receipt→lot, planner→reservation→cook→serve/leftover/waste, shopping handoff, offline/CAS conflict handling and private intake; preserve the current no-health-data kitchen projection. Add integration/device evidence only for changed paths. Physical camera performance, two-device sync, professional/child jurisdiction policies, clinical/IDDSI review, real providers and independent culinary/food-safety acceptance remain separate gates.

A tombstone is not erasure. Profile/receipt/intake rows with NOT NULL envelope FKs must be physically removed or explicitly migrated to a non-payload tombstone **before** the envelope can be deleted. Remove dependent observations, grants, attendance, collections and owner-specific links in safe FK order; remove receipt/image envelopes after permitted dependent provenance is detached or minimized. Keep only authorized value-free retention/deletion evidence. Invalidate queued work/search/derivatives/backups and replay deletion tombstones after restore. Never report completion merely because a row has `deleted_at`, `expired` or a revoked key.

## Genuine unknowns and exclusions

Clinical/IDDSI permissions, jurisdiction-specific child/guardian consent, provider-plan entitlements, exact account retention periods and organization membership policy need explicit decisions; this schema cannot decide them. Full organization hierarchy/clinical prescriptions are not inferred from kitchen roles. Date/quantity precision beyond the current declared contract requires a versioned extension. Commercial checkout orchestration, disease/medication dosing, smart-fridge dependency and a full social network remain excluded. Future unrecorded product ideas are not promised by an extensible schema.

## Focused evidence

`python -m unittest discover -s tests -p test_household_domain_schema_v1.py -v` uses synthetic fixtures only and composes the actual cloud base with both new migrations. The payload check needs the existing `jsonschema` test dependency. Tests prove the named SQL/type constraints, legacy-row preservation and offline-preparer behavior; they are not broad CI, production deployment, RLS, KMS, live OAuth, end-to-end sync or application acceptance.
