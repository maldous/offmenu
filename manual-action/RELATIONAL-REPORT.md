# Retained relational evidence reporter

`relational_readiness.py` implements the isolated, offline evidence step described
in `RELATIONAL-READINESS.md`. It is **not installed into the runner**, does not
provision application databases, and cannot enable FETCH. No actual retained or
household data was inspected to develop/test it: the fixture is synthetic.

**Authorization distinction (2026-10-22):** the later user instruction to add
additional sources and fetch them separately authorizes acquisition. This report
is not a veto or prerequisite for that separately authorized acquisition. Its
`fetch_status: disabled` means this reporter has no fetch capability and changes
no fetch settings; it does not describe or revoke another workflow’s authority.
Application/relational readiness remains unestablished until evidenced.

## One callable step, no new orchestration

A future existing-command integration can call:

```python
from relational_readiness import build_report, sanitized_summary, write_reports

private = build_report(existing_state_directory)
public_counts = sanitized_summary(private)
write_reports(new_private_report_directory, private)
```

The diagnostic CLI is available independently, but is **not a request to rerun
an ingest or to execute anything on Foo**:

```sh
python relational_readiness.py \
  --state-dir /explicit/existing/state \
  --output-dir /explicit/new/private/report-directory
```

The output directory must be private (0700). The two fixed report filenames are
created with 0600 and exclusive creation: existing evidence is not overwritten.
Only the CLI/report writer writes files; `build_report()` returns a local object.
The CLI prints only the sanitized summary. Exit 0 means the supported staging
inspection completed, **not relational/application readiness**; exit 2 means
incomplete/deferred/unavailable evidence. Both leave FETCH disabled.

### Live operation and immutable-read boundary

The reporter never acquires an ingestion writer lock, even momentarily. An
ordinary shared lock could reject `DomainStore`'s nonblocking exclusive writer.
It only observes existing lock metadata through Linux `/proc/locks`; missing or
unavailable lock observations are unknown, not proof that no writer exists.

A store is read only after all these conditions are established:

1. Existing `catalog.private.json`, `last-run.private.json`, and `last-report.json`
   bind the same terminal run and catalog-descriptor hash. A live/running or
   mismatched receipt prevents staging reads.
2. Its main/WAL metadata identity exactly matches the terminal output receipt.
3. An existing owned writer lock has no writer observed.
4. **No WAL file is present, including a zero-length WAL, and no rollback
   journal is present.** Live/WAL-backed
   stores are deferred; there is no automatic checkpoint, writer interruption,
   temporary full-database copy, or repeated inspection loop.

For this explicitly quiescent, no-WAL case, the connection uses
`mode=ro&immutable=1`, `query_only=ON`, and `trusted_schema=OFF`. This is a narrow
implementation refinement to the original proposed report boundary: plain
`mode=ro` can create `-wal`/`-shm` files on a WAL-format database even after its
writer closed, and ordinary rollback-mode readers can delay a writer's commit.
The immutable option is **never used to ignore an existing WAL**. A WAL-format
header with no WAL is accepted only with the terminal identity/no-writer checks;
a synthetic test proves it creates no source sidecars. Nothing changes a source
file, a source lock, a journal mode, or file permissions.

The reporter compares source main/WAL identities, terminal-metadata identities,
writer observations and implementation hashes before/after the bounded read.
`stable_terminal_observation` describes that observed evidence only:

- `atomic_cross_database_snapshot` is always `not_established`;
- uncooperative external-writer exclusion is `not_proven`;
- the eight independent transactions are **not** claimed to be one atomic
  snapshot; immutable `data_version` is explicitly not a live-writer detector;
- any changed/unknown identity, missing lock observation, active writer or WAL
  yields incomplete/deferred evidence, not a readiness claim.

This deliberately favors an honest unknown over side effects, expensive raw
copies, or slowing a live ingest. A future stronger coordinated snapshot adapter
would need its own reviewed contract; this reporter does not improvise one.

## Input and identity contract

Only the eight fixed staging paths are selected. Public domains are under
`<state>/staging/`; profiles/inventory are under
`<state>/private-household/staging/`. No filesystem-wide discovery or provider
network lookup occurs. Catalog native source paths are not opened. Native barcode
stores referenced by wrapper records remain uninspected adapter gaps.

Source versions come **only** from the terminal private receipt's explicit
`source_key`/`source_version` pairs. The reporter does not choose the largest
version, newest timestamp, most plausible name, or first provenance occurrence.
Catalog assignments must exactly reconcile with the selected receipt source keys.
Older versions and other source namespaces remain separate historical rows.
Missing version receipts, transformed adapter assignments that cannot reconcile,
partial/error sources, missing database IDs and stale counts remain unknown.

The snapshot ID binds the selected source/version counts, observed main/WAL
identities, terminal metadata byte hashes, implementation/rule hashes and rule
version. The complete observed record identity set receives its own digest.
Catalog/fingerprint hashes are **metadata identity**, not raw-source custody
checksums. Schema, indexes, declared FKs, full `integrity_check`, owning-record
`foreign_key_check`, table counts, cached count agreement and selected-record
canonical payload hashes are reported independently. Historical row counts do
not imply historical payload verification. Reference wrapper counts do not
become native product counts.

## Exact relation contracts

The detailed report holds separate resolution records, never changes
`relations.target_id`, and never asserts a canonical real-world entity.
Each record binds the full owning record identity and relation ordinal, selected
snapshot, rule version, contract ID, evidence JSON pointer, original identifier
value/type, full target record identities and a null `canonical_entity_id`.

Supported lookup keys retain **all** of:

```text
(target_domain, identifier_namespace, provider,
 source_key, source_version, source_native_id_lexical)
```

For adapter occurrence IDs, `identifier_role` explicitly says
`staging_occurrence_identifier`; the common lexical-key field does **not** claim
that the generated ID is native. Supplier lookups use native `entity_id` claims
and retain string versus integer type and leading zeros. Provider spelling aliases
are not collapsed. Null/unknown namespace/provider does not become a universal
lookup namespace.

| Contract | Exact condition |
|---|---|
| `recipe_mentions` | Recipe `has_ingredient_mention` to a same-source/version ingredient-mention occurrence; emitted `id`, shape and `recipe_id` must agree. |
| `mention_recipe` | Reverse same-source/version `ingredient_of` to an emitted recipe occurrence; owning `recipe_id` must agree. |
| `menu_entries` | `contains_menu_entry` to a same-source/version emitted menu/menu-item child. No menu-name→recipe/venue match. |
| `supplier_entities` | `owned_by`, `parent_organization`, or `subsidiary` with explicit subject claim, matching payload/source provider, same source/version, and exact native entity ID. Only organization/supplier-entity target records qualify. Ownership/price/place occurrences do not become organizations. |

Recipe reciprocals must themselves pass full relation/payload/hash/namespace
validation and uniquely resolve back to the owner. A raw reverse edge is not
sufficient. Menus have no invented reciprocal relation requirement.

Dispositions are explicit:

- **resolved:** exactly one compatible target in the selected observed snapshot;
- **missing:** zero compatible targets under a supported exact contract; source
  namespace/version mismatches have distinct reason codes;
- **ambiguous:** multiple compatible provenance records, with all targets retained;
- **unsupported:** unknown adapter/namespace, malformed or contradictory claim,
  incomplete target coverage, or an unavailable contract. This is **unknown**,
  not a zero-match result or successful join.

This implements `unsupported` separately rather than hiding unknown contracts
under `missing`. In particular, product-reference hashes are not barcode record
IDs; FDC/food IDs are not GTINs; equal source keys do not attach citations; names
and fuzzy matching are never used. Per-contract counts are reported separately.
All eight domains also carry a concrete unimplemented-adapter gap. Zero emitted
edges is not evidence that every required application join has been exercised.

## Private and normalized coverage

Private data is never invented. Empty private domains with matching terminal
receipts are `schema_only_awaiting_user_input`, and scope is
`not_exercised_no_input`. For present rows, explicit namespace/household/user
claims, conflicting/missing scope, duplicate scoped IDs and observed cross-scope
edge attempts are checked. No private edge is resolved by this version. This does
not claim access-isolation testing or stable identity for row-number fallbacks.

An existing local normalization sidecar is read only with no WAL and before/after
identity checks; its observations are independent, not an ingest-coordinated
snapshot. Matching requires the complete current source identity and payload hash,
not matching aggregate totals. Stale/orphan artifacts, rules-only, review pending,
rejected, validated interpreted, unresolved errors and ambiguous rule/version
sets are counted separately. Interpreted receipts are replayed through the
existing validators with caching disabled and a read-only store view. The reporter
never constructs a writable `NormalizationStore`, performs an actual review,
creates a receipt or requests a translation.

Without `--target-language`, translation/gold eligibility remains unknown. With
an explicit target language, existing conservative gold validators can report
blockers; this never replaces cross-domain/application readiness. Coverage flags
matter: counts from incomplete or capped scans are only observed lower bounds,
not invented totals. `null` counts mean unestablished totals.

## Local detail versus shareable summary

`retained-relational-readiness.private.json` contains source/record identifiers,
schema diagnostics, namespace claims and selected target identities. Keep it
local with the retained data. It must **not** enter a source-only consolidation
commit, public return or message.

`retained-relational-readiness.summary.json` is constructed with a positive
whitelist: fixed domain/contract/status labels and numeric counts only. It omits
paths, source IDs, record IDs, provider names, arbitrary relation labels, payloads,
snapshot hashes and exception messages. Source-supplied status strings are never
passed through. Summary statuses always include:

```text
status: blocked
binding_status: staging_not_application_bound
app_binding_status: app_binding_unknown
fetch_status: disabled
```

No application database identity/schema/query/cardinality evidence is currently
provided by this module. That, typed product/food/citation/private adapters,
review/translation/rights evidence, and stronger coordinated snapshot evidence
remain explicit prerequisites—not something a staging report certifies.

## Bounds and tests

Defaults: 120 seconds, 200,000 selected records, 1,000,000 relations, 8 MiB per JSON,
512 MiB parsed JSON total, 100 million SQLite VM steps, 100,000 metadata rows,
40 JSON nesting levels and 200,000 nodes per JSON. A cap leaves incomplete evidence
and no success claim. Database copy/repair/retry/network/subprocess/ingest code is
absent. Adjusting caps is a deliberate caller decision, not a background loop.

```sh
python -m unittest discover -s tests -p test_relational_readiness.py -v
```

The 33 synthetic tests cover source immutability, no network/process/write-store
creation, no lock acquisition, live-receipt refusal, WAL deferral and quiescent
no-sidecar reads, source/version/provider identity, leading zeros, occurrence
ambiguity, invalid/absent reciprocal edges, payload tampering, FK failures,
resource caps, private-scope attempts, summary injection resistance, exclusive
private report output, and normalized historical/rules-only coverage.
