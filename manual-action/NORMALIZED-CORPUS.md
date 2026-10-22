# Two-pass normalized corpus and gold readiness (version 1)

This is a source-preserving normalization contract, not a completed corpus,
actual review, translation, production migration or FETCH authorization. The
current `./run` activates the bounded database-only rules orchestrator described
in [DB-NORMALIZATION-RUN.md](DB-NORMALIZATION-RUN.md), not the naïve API loop below.
The actual AI interpretation route remains unactivated. No real item has been
AI-reviewed by source publication or synthetic fixtures.

## Eight domains, one envelope

| Staging database/domain | Common record types |
|---|---|
| barcodes | barcode |
| ingredients | ingredient |
| recipes | recipe, menu |
| dietary | dietary_assertion |
| user_profiles | profile |
| inventory | inventory |
| suppliers | supplier |
| citations | citation |

Repository-root `schemas/common-normalized-record.schema.json` (that is,
`../schemas/common-normalized-record.schema.json` from this directory) specifies
the envelope and bounded review-output schema. The recipe/menu schemas are instead
under `manual-action/schemas/`. Common normalized fields are `title`, `language`, `fields`,
`relations`, and `field_lineage`; type-specific content is in `fields`.
`normalize_recipes.py` supplies the recipe/menu template and review coverage;
`normalization_domains.py` supplies other domain projections. Source relations
are retained, not silently resolved or merged. Shared unit conversion is only
exact where supported; uncertainties stay explicit, never converted to facts.

## Source custody and invalidation

`iter_staged_records(path, domain)` opens only a matching, owned staging database
in SQLite `mode=ro`. Input identities are the existing `ingest_store.py` composite
`(domain, source_key, source_version, record_id)` plus verified `content_sha256`.
The canonical JSON payload hash must match the staged value. `source_original`
is preserved unchanged by the low-volume legacy sidecar API. The production
DB-first compact runner instead retains a verified reference to that unchanged
payload in its existing staging DB, avoiding a full raw JSON duplicate. Exact
byte originals remain in retained
source custody, not recreated by JSON serialization. Read-only imported metadata
does **not** imply rights clearance, complete provenance, or language assessment.

`NormalizationStore(state_dir)` writes only
`state_dir/normalization-private/normalized-sidecars.sqlite3` (private permissions,
owned binding, no symlink targets). Household/profile/inventory sidecars stay
private in this common private store. Do not commit this directory or review
packets. No canonical/source store is writable through this API.

Both pass caches include full source identity/content, source provenance, rule,
domain-rule, template, model, prompt and schema versions. Interpreted artifacts
also bind the exact rules artifact digest. Changes create new immutable lineage;
old artifacts are historical and must not be treated as current. No destructive
cache deletion or silent receipt overwrite is performed. A corrected/retried
review with different content requires an intentional prompt/model/rules version
change and a fresh rules artifact; a cache conflict is not silently accepted.

## Low-volume local API (not the production runner loop)

```python
from normalization_api import Versions, run_rules, queue_review
from normalization_core import (NormalizationStore, iter_staged_records,
    validate_and_cache_actual_review, register_translation_units,
    validate_and_cache_translation, gold_readiness, build_gold_manifest)

# Select actual version identifiers before any real review; do not use this
# example to claim that a model, prompt, reviewer or source was actually used.
versions = Versions(model_version='selected-model-version',
                    prompt_version='approved-review-prompt/1')
with NormalizationStore('/private/local/state') as cache:
    for source in iter_staged_records('/private/staging/recipes.sqlite3', 'recipes'):
        artifact = run_rules(source, versions=versions, store=cache)
        packet = queue_review(artifact, store=cache)
        # STOP here until an actual reviewer inspects every required item.
        # reviewed = validate_and_cache_actual_review(artifact, actual_receipt, cache)
```

The example above commits full artifacts/packets and is not a scalable loop for
the retained corpus. Use the bounded compact orchestrator for the standard run.

Default model/prompt identifiers are `unconfigured` and cannot accept reviews.
The first pass always produces `rules_only`, `pendingreview`, `gold_status=blocked`.
Rules, confidence, successful extraction, parsed PDFs, or a batch-level success
cannot auto-mark a recipe/menu reviewed. Every artifact requires the interpreted
pass; recipe/menu templates additionally require the detailed item/source coverage
implemented by the recipe review hook. Batching is transport, not review waiver.

An actual review receipt must bind the exact artifact ID and SHA256; declare
reviewer identity/kind, model/prompt/schema/template versions, timestamp, evidence
reference and `direct_item_review`; contain the normalized result, explicit
per-item decisions, issues and uncertainty. Rejections/needs-changes remain
non-gold. The validator verifies structure, content binding and coverage. **It
cannot authenticate that a named reviewer really performed the work.** Only a
trusted actual review workflow may submit receipts, retaining the referenced
review transcript/evidence. Synthetic test receipts are test data, never review
evidence. Source text and outputs are bounded JSON data; nothing is evaluated,
executed, fetched, or obeyed as instructions. No API keys or external AI calls.

## Translation and gold gates

`register_translation_units` creates immutable source-text units bound to the
reviewed artifact, field JSON pointer, source/target language, text hash and all
versions. Versioned domain allowlists select natural-language title/name/alias/preparation/
prose/preference terms, not identifiers, status codes, dates, URLs or unit symbols.
Recipe/menu units use reviewed canonical grammar and contextual lexical units,
not original raw steps or whole-source text. Scope changes require a version bump. Actual translation
receipts use `direct_unit_review` and bind the exact unit digest. No machine
translation, guessed locale or review completion is manufactured. Matching
explicitly reviewed source/target languages need no translation; unknown source
language remains blocked. Source originals are never replaced by translations.

`gold_readiness` requires:

1. A cached validated interpreted artifact with immutable rules-parent lineage;
   its real-review receipt is replay-validated and exactly reproduces the result.
2. Every required item accepted, no validation errors or unresolved uncertainty.
3. Explicit rights clearance **and evidence**, custody, and citation IDs. A license
   string or copied/source-asserted suitability alone is insufficient.
4. Known reviewed source language; all required translation-unit receipts complete
   if target language differs.

`build_gold_manifest` checks duplicate source identities, exact authoritative
expected counts for all eight domains and each artifact's readiness. Missing
counts are unknown, not zero or complete. It only builds a candidate manifest;
counts must come from a reconciled complete staging snapshot, not a sample or an
estimate. Artifact schema validity or this manifest cannot prove the source DBs
are exhaustive. Production FETCH is **always false**, including in a fully ready
candidate; all-eight-database readiness/production authorization remains separate.

## Not authorized/executed by this foundation

- No source/recipe/menu payloads exported, uploaded or committed.
- No private review-batch branch created; separate review-data export approval is
  pending. Local packet preparation does not confer publication authority.
- No production FETCH, supplier crawling, Foo, ingestion rerun or plan revision.
- No actual review, translation, rights decision, gold promotion or app binding.

Source-only implementation/tests/docs publication is handled separately by the
parent's approved consolidation workflow, excluding credentials and raw data.

### Once-off interpretation reuse and per-source bindings

`interpretation_key(artifact)` is separate from the immutable source-artifact
cache key. It includes exact payload-content hash, domain/type, original
language/locale context, explicit `provenance.semantic_context`, required coverage
and all rule/template/schema/model/prompt versions. File modification/fetch time
and source-version metadata alone do not trigger re-interpretation. Exactness is
conservative: payload IDs/assertions remain content, so changed IDs, locale,
coverage or context can miss the cache rather than invent fuzzy equivalence.

`find_cached_interpretation` verifies the original accepted receipt and parent
lineage. `queue_review(..., store=cache)` may report that reusable evidence, but
leaves the new item `pendingreview`. A new item-binding receipt can set
`reuse_of_artifact_id`; it must independently bind this occurrence and all its
coverage, reference the verified existing interpretation, retain exactly its
semantic result, and have its own receipt ID. This is reuse attestation, **not a
required fresh model invocation** or a claim one occurred. `review_bindings`
stores the exact-equivalence proof and `reused_from_review_id` for every item.
A generic learned-template approval never accounts for uninspected source items.

Recipe/menu translation uses reviewed canonical templates and contextual lexical
units through `recipe_translation_units`, **not recursive translation of the raw
source corpus**. Stable unit content/context/version keys are reusable across
items; `translation_bindings` separately records each artifact's required units.
Source scaffolds, IDs, evidence text and step originals are not rewritten.

### Conservative nonrecipe interpreted overlay

The seven nonrecipe templates retain all source-backed fields, identities,
relations, title/language and lineage unchanged during review. The second pass
may add `fields.review_interpretation = {notes, resolutions}`; each resolution is
`{code, reason, evidence_ref}` and must name an existing issue/uncertainty.
Cleared uncertainty or removed issues require corresponding explicit review
resolution evidence. Arbitrary fields, silent scope changes, invented health
qualification and blanket deletion of warnings are rejected. Future semantic
entity-matching field families need a versioned typed validator. V1 does not
claim those production mappings already exist; unknown source language remains
held until there is an evidence-backed compatible source/template revision.

### Foo provisioning and relational readiness remain separate

The earlier fetching condition requested confidence that **all eight actual
databases on Foo have been provisioned and are relational for the retained data**.
The later instruction to add additional sources and fetch them separately
authorizes acquisition; this foundation does not veto that separate workflow.
Neither
these schemas, additive SQLite staging, source-normalization sidecars, a candidate
gold manifest nor passing synthetic tests establish that condition. This code
always reports `production_fetch_enabled: false`; it does not activate Foo.

Before that condition could be established, inspect a reconciled retained-data
snapshot and read-only evidence of the actual provisioned/app-bound stores:

- **Bindings and keys:** database location/owner/schema/migration version and app
  binding for each of the eight domains; canonical entity primary keys and
  namespace rules; source-to-canonical mappings retain
  `(domain, source_key, source_version, record_id, content_sha256)`.
- **Join/FK contracts:** barcode→product/ingredient identities (syntax validity
  is not product equivalence); recipe ingredient mentions→ingredient entities;
  menu items→recipes and documented course/meal-plan/venue relations; dietary
  observations→food/nutrient/unit/basis/reference entities; inventory→household
  and product/item identities; supplier/place/organization/ownership relations;
  citations→source/assertion/rights evidence. Cross-store relationships require
  explicit join contracts and validators, not a claim of SQLite cross-DB FKs.
- **Private scope:** profile/inventory keys, references and unique constraints
  include the authoritative household namespace/identity. Prove that joins cannot
  cross households; missing scope is not inferred from names.
- **Retained-data evidence:** exact current source-version selection and per-domain
  expected/actual record totals, adapter/mapping coverage and parse/review errors,
  actual review/translation/provenance/rights completion, duplicate-key and join
  cardinality distributions, unresolved mappings and orphan counts. Quantify
  relationship coverage against denominators, including unknown totals.
- **Relational verification:** schema/FK/index introspection where applicable,
  integrity checks, representative retained-data joins and reconciled orphan/
  mismatch reports; distinguish verified joins from source-asserted or unresolved
  relations. `ingest_store.relations.target_id` is an indexable source claim, not
  a proven cross-database foreign key or production relationship.

The candidate manifest rejects mixed historical versions of the same source and
missing/ambiguous referenced citation IDs. That is necessary sidecar consistency,
not proof of any of the above actual-store conditions. No live Foo inventory,
provisioning, binding, relation verification or production fetch was executed by
this implementation. This foundation has no fetch capability and does not launch
the separately authorized acquisition. Relational/application readiness remains
unestablished without real retained-data and provisioned-store evidence.

Canonical-template translation receipts additionally preserve the exact typed
placeholder names and occurrence counts; target-language word order may change.
Missing, added, renamed or malformed placeholders cannot become complete units.
Literal lexical-unit text is not interpreted as executable template syntax.

Rule-parent trust is established by deterministic recomputation from the preserved
source and versions before caching, queueing or accepting external review. A
caller cannot erase steps/coverage while retaining the source hash. Accepted
recipe templates also preserve detected action order and evidence-bound duration,
temperature, equipment and condition obligations; ingredient preparation/descriptive
residuals retain contextual lexical coverage. These checks are conservative
structural obligations, **not proof of semantic accuracy or actual human/AI work**.


An explicit recipe ingredient quantity with unresolved conversion/basis remains a
separate `recipe_ingredient_quantity_unresolved` gold blocker even if an honest
item review has completed. Review acceptance does not imply normalization of
ambiguous cups, densities or locale-dependent units. The recipe gold validator is
mandatory; its absence fails closed. No conversion is guessed by this gate.
