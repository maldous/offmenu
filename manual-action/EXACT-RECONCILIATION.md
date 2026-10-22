# Exact database reconciliation component — candidate boundary

**Prepared against the published normalization pass-1 source union `062dc707`.**
This module remains a standalone candidate component, not a deployment, corpus
run, AI review, or assertion that the 16.439m stored records are globally reconciled.
Its original three-file preparation is now composed with the bounded owner in
[DB-RECONCILIATION-RUN.md](DB-RECONCILIATION-RUN.md). That owner supplies capacity
admission, resume, quarantine and sanitized receipts; the module alone does not.
Preparation baseline dependencies were test support, not proposed changes.

## What it actually does

`normalization_reconciliation.py` produces a policy-pinned, private SQLite sidecar:

- Stable deterministic **identifier-key nodes**, source-occurrence identities,
  and exact source-version-bound relationships. These are candidate associations,
  **not verified real-world entities, transitive same-as closure, or merges**.
- Valid UPC/EAN/GTIN lexical aliases share the same GTIN-14 key, with an explicit
  `syntax_only_identifier_candidate` state. Allocation/ownership is not inferred.
- Registered exact namespaces can connect public domains; namespace record-type
  conflicts and per-record exclusive-identifier contradictions are held.
  Unregistered provider namespaces remain source/domain scoped, not global.
- An exact terminology/alias registry has explicit source scope, language, unit,
  role, immutable artifact provenance, and pointers into normalized projections.
  Source-declared aliases are candidates, not semantic equivalence. Lookup returns at most 32 candidate nodes by default (128 maximum), explicitly holds truncated sets, and checks source conflicts beyond the displayed prefix. No casefold,
  stemming, translation, name matching, fuzzy join, or language inference occurs.
- Nutrient identifier observations retain source namespace, canonical exact units,
  and distinct per-100g/per-100mL/per-serving bases. No salt/sodium conversion,
  serving inference, cross-dimension conversion, or dietary qualification occurs.
- Recipe ingredient mentions get stable occurrence-local identities and quantities,
  **not invented global ingredient IDs from names**. Menu/source relationships
  resolve only to an exact domain/source/version/record key. A missing target stays
  unresolved; a later target becomes a source-reference candidate automatically.
- Source records retain all versions. Same source/version/record with conflicting
  content holds both old and new memberships and aliases; no lexical latest winner.
- Count-only unresolved reports and separate effective relationship/membership
  views preserve conflicts. Provenance is the source key/version/record/content
  binding, artifact hash/cache key, versions hash, provenance hash, and normalized
  pointer. Complete field lineage remains in that exact immutable compact cache.

The default registry includes **only** `gs1:gtin14`. A production provider namespace
mapping needs an explicit reviewed contract and documentary provenance; a name
like `USDA` alone does not authorize remapping it to FDC identifiers. Tests use a
clearly synthetic `fixture:food` namespace for the cross-domain contract. A changed
registry hash requires a new sidecar; old interpretations are not silently reused.

## Integration API and bounded incremental operation

```python
from normalization_reconciliation import (
    ReconciliationStore, ingest_cache_keys, backfill_page,
)

# The existing owner's lease/cancel/time budget still governs orchestration.
# No existing source/cache/runner file is modified by this component.
with ReconciliationStore(private_output_path, registry=reviewed_registry) as graph:
    # Best boundary: exact keys from a completed normalization cache transaction.
    # Receipt lookup avoids source JSON/projection replay for unchanged artifacts.
    pending = graph.pending_keys(committed_cache_keys)  # at most 128 keys
    ingest_cache_keys(ingest_state_dir, public_domain, pending, graph)
```

- `ingest_cache_keys` opens only the fixed public-domain staging DB and compact
  normalization DB in `mode=ro`, `query_only`. It checks ownership bindings,
  bounded compressed/decoded cache integrity, exact source DB identity/provenance,
  full artifact hash, and deterministic rules projection before graph insertion.
  Custody admission matches the published engine’s 64-KiB cap, including its null provenance when over cap. Source metadata paths are never opened. `inventory` and `user_profiles` are
  rejected before DB access; there is no AI, remote service, or export route.
- Each transaction accepts at most 128 rows / 16 MiB of transient artifacts.
  Source read snapshots close before graph writes; no corpus-wide WAL read pin.
  Default free-space reserve is 2 GiB plus a conservative per-batch estimate.
  The graph stores relational facts/hashes only, never raw source payloads,
  compressed artifact copies, reviewer text, or custody documents.
- Exact cache receipts are committed with all facts. Retry of an identical key is
  idempotent. Changed source content/rules produce separate evidence; originals
  remain untouched. `pending_keys` is a historical receipt lookup, **not proof the
  underlying source still represents current truth**.
- Backfill: call `backfill_page(..., after=cursor, limit<=128)`, filter through
  `pending_keys`, ingest, and advance the caller's durable cursor **only after
  successful commit**. Retrying after a crash is safe. The existing runner must
  own the durable cursor/snapshot pin, cancellation, wall-time limit, and failed-key
  quarantine; they are intentionally not grafted into active runner files here.
- Discovery is indexed cache-key keyset paging, never rowid paging; `VACUUM` or
  physical rowid reuse does not lose keys. Restart discovery from `None` after a
  normalization snapshot changes (new hashes can sort before the old cursor).
  Receipt filtering means unchanged originals are not reprocessed. Exact newly
  committed-key delivery avoids that O(n) metadata discovery pass entirely.
- A malformed/stale batch rolls back without advancing a receipt. The owner may
  split it into bounded singleton retries to quarantine the precise failed key;
  never skip it while claiming complete coverage. Current rules must be able to
  verify a selected cache version. Historical incompatible rules stay unresolved,
  not silently reinterpreted.
- `report()` is an explicit aggregate diagnostic, not a per-record hot-path call.
  Point membership/term/relationship checks use the indexed source slot rather
  than materializing a whole-corpus conflict scan.

## Evidence and limits

Focused suite: **24 tests passed** (all six public domains, deterministic ordering,
GTIN aliases, cross-domain fixture namespace, conflicts, namespace collisions,
changed rules/content/versions, late relationship targets, scoped ambiguous aliases,
unit/basis separation, corrupt/stale caches, forbidden private domains, immutable
source bytes, no-network guard, no raw-copy sentinel, rollback/retry, keyset/VACUUM,
symlink refusal, byte/row/disk limits, and indexed point lookup).

A generated 3,000-row six-domain benchmark completed locally in 3.326 s and used
8,830,976 output bytes (2,943.66 bytes per fixture row). This is **not** an observed
production size/throughput forecast. The output is additive and capacity must be
admitted from actual bounded samples before a whole-corpus run; compact relation
storage is not zero storage. No production rows or private data were accessed.

This component closes a useful exact-identifier/terminology/relationship layer.
It does not claim a worldwide food ontology, authoritative allocation verification,
review acceptance, translation, gold readiness, a production incremental change
feed, or automatic current-version truth. Those boundaries remain explicit.
