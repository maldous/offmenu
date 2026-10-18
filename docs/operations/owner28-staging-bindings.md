# EE/EG/EH/ER metadata and staging bindings

Selected request: `M-STAGING-BIND-20261018-W28`. Baseline:
`abecb99ee1125730ccbc2824b6ec49ffc5cc4302`. The pending handover/PR42 is
not used as accepted develop. This package owns four added files only; no shared
core, source admissions, Actions, runtime, UI or production settings are edited.

## Usable interface

`offmenu.refresh.portfolio28.assess_portfolio(metadata, now=UTC, validated_at=UTC)`
accepts a mapping of the configured logical keys to **explicitly supplied JSON
metadata bytes**. `config/portfolio28-staging.json` supplies exact retained
manifest/receipt/review SHA-256 pins, country/type applicability, source identities,
acquisition timestamps, selector expectations and preserved holds. All paths in
that configuration are evidence locators, never implicitly opened by the API.
No source body, model, clock, network, original filename inference or registry
activation is used. Per-binding maximum metadata input is 128 KiB per file.

The caller supplies only metadata already permitted for its actor and operation.
The API does not discover or load that metadata, and a matching hash is not a
permission grant. Missing data in one binding does not prevent other bindings'
diagnostics. Callers must inspect both report `errors` and each binding's `status`
and `errors`; a report is never a country or source-acceptance receipt.

`assess_binding(trusted_binding, metadata, now=..., previous=...)` exposes fixed
diagnostic codes and these outcomes:

| Outcome | Meaning |
| --- | --- |
| `bound-metadata-only` | Exact supplied metadata pins and selectors match; source actions still disabled. |
| `missing` | Required metadata, selector or original acquisition time absent. |
| `held` | Existing source/action/territory hold persists, even if metadata pins match. |
| `malformed` | Invalid JSON, duplicate keys, nonfinite number, shape, bounds or UTC clock. |
| `stale-input` | Input bytes differ from the exact retained manifest pin; no repinning. |
| `stale-review-required` | At least 30 days since original acquisition; no automatic download. |

Unknown values remain unknown. Boolean/integer selector coercion is rejected.
Diagnostics never echo supplied metadata values or exception text. An unchanged
successful metadata binding reports `no-op` against a matching previous binding
identity. Validation timestamps and the explicit evaluation clock do not change
that identity; release, pins, selectors, holds, acquisition time, policy version,
metadata bounds and the minimum reuse interval do. Semantic policy changes must
bump the owned policy version before integration.

## Acquisition, validation and cache boundary

The shared acquisition `MIN_TTL` defines the 30-day threshold. Original acquisition
age and latest validation age are separate. Revalidation cannot reset original
acquisition age, and future/non-UTC/inconsistent timestamps fail closed. Under
30 days a valid binding indicates retained **metadata** reuse with zero network;
at the boundary it requires review, also with zero network. No force or download
mode is exposed. This is a planning/binding interface, not a new cache engine,
proof of a physical cache hit or operational retention entitlement.

Actual cache objects, acquisition, isolation and publication remain with existing
shared owners. No production `SourceSpec`, source `SourceContract`, `Binding`,
acceptance registration or cache is installed. Source-specific local retention
rights, expired/retracted evidence policy and integration remain explicit inputs.
The shared planner `core.cache_policy` is historically hardcoded to Wikibooks;
`policy.plan_fixture` is fixture-registry specific. This package does not disguise
EG as either source. Integrator00 should select a reviewed generic identity-aware
planning entry point before wiring real portfolio refresh. No shared API change
is implemented here.

## Field origins and authored staging demonstration

The EG binding declares the already-reviewed candidate input, three stable IDs,
candidate JSON pointers, physical/printed/embedded page distinction and literal
text spans. Proposed per-field origins are **templates**, not newly transformed
records. The selected historical methodology statements are not composition,
retail prices, current dietary advice or clinical intake. Native narrative unit
and basis are null, never zero or invented denominators. The exact CC BY 3.0 IGO
attribution/adaptation and third-party exclusions remain in pinned metadata.

`render_authored_fixture` implements one tiny portfolio mapping demonstration with
two fixed `SYN:28:*` identities, explicit `fixtureOnly: true` and a fixed EG
fixture country. It accepts no real report/menu/CSV format. Every data scalar,
including nulls, gets a source coordinate. It uses shared singleton-packet
serialization and shared `field_origin_errors` coverage. A semantic callback also
compares the values and coordinates with the authored source, so coverage alone
cannot certify a wrong value.

`authored_fixture_contract` creates only a trusted `fixture=True` SourceContract;
its independent expected IDs/count and local schema are code, not source-manifest
flags. Shared `acceptance.qualify` checks exact bundle inventory, schema, semantics,
lineage, hashes, expected IDs/count and rights/holds. No `accept` call or pointer
promotion is made. Fixture qualification is not real source/dataset acceptance.

Run the isolated authored checks from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_portfolio28_bindings.py' -v
```

Tests create only temporary authored metadata/candidate/evidence files. They cover
valid, missing, held, malformed and stale inputs; exact 30-day boundary; validation
age separation; deterministic no-op and nonmutation; no file/network use in pure
preflight; source-origin/value corruption; and isolated missing evidence/schema
failures. They do not open or rehash original PDFs, archives or datasets.

## Typed remaining blockers and integration route

| Binding | Exact remaining source/integration input |
| --- | --- |
| EE TAI I/II/appendix | Exact bibliography, field semantics and action-specific derivative/retention decision; existing reading rights do not authorize processing. |
| EG methodology | Real staging representation/SourceContract and Morgan's review4267 effect-identity reconciliation. Existing three-record review is preserved; no duplicate review. |
| EH EC context | Derivative/attribution decision and exact record-to-territory/provider role; no silent EH-to-MA substitution. |
| ER WFP | Retained original/custodian/path/hash/extent/use not established; historical14 dispatch hold remains. Metadata24 scoped negative already answered; no routing it back. |

All four countries still need every required applicable data type. No canonical
identity, field equivalence, gold, translation, country completeness or raw-source
use is inferred. Finland/Frida and native NO/FR restrictions, explicit access and
credential denials, privacy, raw-on-Foo and production/CIX/DEV7645 holds persist.

The bounded proposed shared-interface request for existing integrator00 is:
review/select an identity-aware, offline metadata/cache planning hook accepting
explicit source/release/input digest/originalAcquiredAt/validatedAt/now and returning
reuse/review diagnostics without network or admission. Reuse shared CachedAcquirer
only after its exact source/rights/custody/resource contract is separately selected;
automatic under-30-day calls must never select force/revalidate downloads. Integrator
and independent review must approve integration before another substantive task.
