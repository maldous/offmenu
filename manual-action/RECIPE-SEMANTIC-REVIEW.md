# Recipe/menu semantics — local two-pass contract

**Actual AI review is implemented but not activated. No retained recipe/menu has been AI-reviewed by this
change.** The tests use generated recipes and explicitly synthetic receipts.
The current `plan.json`/`./run` activates DB-only cached rules and compact pending
review references, not an actual AI invocation. Ingestion adapters and raw
records are unchanged; see [DB-NORMALIZATION-RUN.md](DB-NORMALIZATION-RUN.md). No AI API,
API credential, export destination, network lookup or data upload is needed by
these modules. Actual review/export remains separate: until the approved review
destination/workflow is established, keep all packets and results local, private
and out of Git. This document and generated test source contain no retained data.

## Pass 1: deterministic, source-preserving, cached

`normalize_recipes.normalize_record(record, source_context=None)` consumes the
**current `ingest_recipes.py` projections**, not an invented replacement format:

- Recipes: `id/kind/title/language/yield`, `ingredients` with raw expressions,
  source names, quantity/unit and original objects, and `steps` with raw text,
  source ordinal, section and original object.
- Menus/menu items: `id/kind/title/description/price/currency/language`, explicit
  projected relations and source-native assertions in `raw_source`.
- Raw `raw_source`/`raw_source_json` originals remain unchanged in the core
  artifact; sidecar status is distinct from source status. Exact number lexemes,
  source assertions and provenance stay with their original records.

The result fits the common normalized-record contract and adds
`normalized.fields.recipe_menu_template` and `translation_plan`.
`normalization_core.run_rules` owns the immutable first-pass cache. Identity
includes source/content/version and normalization/schema/template/prompt/model
versions. Changing content or a relevant version does not reuse an old result.

Source array order is preserved even if upstream ordinals are irregular. Each
contiguous source section stays distinct (including repeated headings). A grouped
source step is **not** silently split or reordered by punctuation or verb matches.
The small English action vocabulary proposes preparation/cooking/presentation
candidates only; unknown/non-English language remains opaque. Candidate duration,
temperature, equipment, condition and exact-name ingredient mentions carry Unicode
code-point offsets and exact source text. Numeric conversion delegates to the
shared deterministic unit normalizer; ambiguous cups and missing units remain
unresolved. Dependencies are not guessed from source order. Missing temperatures,
quantities, materials or conditions are never filled with plausible defaults.

Menus retain item/section relationships and explicit course, meal-plan, venue or
recipe assertions. A source assertion is **not** a resolved cross-source entity
match. Names are never matched to recipes or venues by the rule pass. Flattened
menu parents, sections and items each require their own artifact review.

## Pass 2: actual native-assistant review, in bounded batches

`build_review_batches(artifacts, max_items=20, max_bytes=1048576)` is a streaming
iterator: each yielded packet is bounded by occurrence count **and UTF-8 bytes**.
No packet file is written automatically. A single oversized item fails closed;
it must receive an explicitly designed segmented review with reconciled coverage,
not be truncated or skipped. Rule artifacts with unconfigured model/prompt
versions can be queued but cannot produce an accepted interpretation receipt.

Each packet contains:

1. A manifest entry for **every input occurrence**: item ID, input hash, artifact
   ID/hash, versions and all required coverage IDs.
2. Source originals plus rule proposals, explicitly delimited as untrusted data.
   Instructions embedded in a recipe/menu are never assistant instructions.
3. The actual review requirements. Read every item's title, ingredients, ordered
   source steps/sections, yield, menu description/price and relationships as
   applicable. Review preparation, cooking, presentation and measuring/equipment
   semantics; do not merely check that a generic template exists.

Coverage includes the record itself and each title, ingredient, step, yield,
menu field/link and unsegmented cached raw section. Exact repeated artifact
occurrences can share one packet payload, but each occurrence stays in the
manifest and reconciliation ledger. Different content/source versions or IDs are
not silently approved through similarity. Core explicit cache-reuse receipts,
when supported, still require a new bound receipt and all per-item decisions.

A native assistant must genuinely read the packet and emit the core
`direct_item_review` envelope (`recipe-review-result.schema.json`). It includes
artifact digest, receipt/reviewer/model/prompt/schema/template versions, timestamp,
evidence reference, explicit per-coverage decisions **and meaningful notes**,
issues/uncertainty and the reviewed normalized sidecar. Runtime credentials are
not a prerequisite. The implementation never generates production verdicts.

`validate_reviewed_template` and core validation require:

- Actual `assistant` review method, matching digest/versions and exactly complete
  coverage: missing, duplicate and extra coverage/results fail.
- Immutable source scaffold, sections, source spans, source quantities, source
  relationships and lexical source units. Corrections are additive semantic
  template definitions/instances, not edits to original records.
- A content-addressed reusable grammar definition with action, phase, pattern,
  typed slot schema, source locale and grammar context. Per-record values and
  evidence are **not** part of the reusable template identity.
- An instance for every source action/step, full non-whitespace source instruction
  coverage, valid exact character-span evidence, preserved source order, and no
  unknown/forward/cyclic dependencies or invented ingredient IDs.
- Evidence-bearing typed slots: ingredient/material references, quantity/unit,
  equipment, temperature, duration, condition and lexical text. Source omissions
  stay explicit `unknown_parameters`; an ambiguous meaning stays unresolved.
- A pending result for unresolved semantic ambiguity or incomplete extraction.
  Raw PDF sections do not become invented steps. Source recipes with no methods
  remain pending. `needs_changes`/`rejected` receipts are cached as such, without
  claiming accepted learned templates.

`reconcile_review_results` checks every receipt before caching batch results and
returns a per-occurrence ledger, including exact reuse. Cache commits are local
and immutable, not a single cross-record transaction; rerunning identical valid
receipts is safe. Review receipts remain separate from source records.

**Trust limit:** structural/evidence validation does not cryptographically prove
who reviewed a packet or prove semantic correctness. The actual native-assistant
review must happen; neither a well-shaped fabricated receipt nor these tests is
proof that any retained corpus item was reviewed. Accepted semantic review alone
also does not mean gold/application acceptance, translation completion or rights
clearance.

## Translation: reusable grammar and typed arguments, not raw-step volume

`recipe_translation_units(artifact, target_language)` emits nothing eligible
until the artifact's actual review is accepted. Then it registers only:

- Canonical template patterns with typed-slot schema and grammatical context.
- Contextual lexical units such as recipe/menu titles, descriptions and ingredient
  names. Ingredient names are translatable variables, never opaque ID literals.
- Material/equipment/condition/text slot expressions and ingredient-name variants
  in each template's slot/grammar context, allowing case, number, agreement and
  target-language word-order differences to be reviewed.

It does **not** recursively send raw source steps, candidate spans, IDs, provenance
or every field string for translation. Unit IDs are stable across records when
text/template, slot grammar, locales and relevant versions agree. The core keeps
separate artifact-to-unit bindings and translation receipts. Changing context,
locale, definition or translator version invalidates reuse. Numbers and units
remain typed values for target-locale rendering, not guessed ingredient strings.
The review pass does not translate; every target-locale translation still needs
its own actual reviewed result. There is no assumption that word-for-word slot
concatenation is grammatical.

## Files and validation

- `normalize_recipes.py`: adapter, semantic validator, streaming batch contract,
  reconciliation ledger and reusable translation-unit registry.
- `schemas/recipe-menu-template.schema.json`: source scaffold and reviewed
  additions. JSON Schema alone is insufficient; runtime evidence checks apply.
- `schemas/recipe-review-packet.schema.json`: local bounded packet manifest.
- `schemas/recipe-review-result.schema.json`: one actual assistant result.
- `tests/test_normalize_recipes.py`: complete generated ingest projections,
  synthetic receipt validation and failure cases; no corpus-acceptance claims.

Run the existing standard-library suite with:
`python3 -B -m unittest discover -s manual-action/tests -v`.
Schema checks use `jsonschema` only when already installed; no installation or
network access is required. Runtime validators remain standard-library code.

### Fail-closed detail accounting and material-reference limit

Accepted templates must account for each detected action in source order and each
detected duration, temperature, equipment and condition in evidence-bound typed
slots. Numeric duration/temperature slots retain the exact supported normalized
source quantity. A full-step evidence span alone cannot discharge those separate
obligations. Unsupported/disputable candidates remain `needs_changes`; v1 has no
silent candidate-dismissal mechanism. This is a conservative check for detected
mentions, **not** proof that all semantics, negations or non-English details were
recognized. Actual item-level AI review is still mandatory.

Ingredient lexical scope retains source preparation/detail fragments beyond an
exact unique name and exact leading quantity/unit. Ambiguity retains extra source
text rather than guessing meaning. Structured native ingredient JSON is never
translated as prose; supported explicit preparation/notes/description fields are
separate contextual lexical units. Original text and Unicode evidence offsets
remain unchanged. This does not translate raw recipe steps or whole corpora.

`material_reference` is reserved but cannot occur in an accepted v1 instance:
there is not yet a typed, source-grounded material/output registry against which
to validate its ID. Existing ingredient IDs use `ingredient_reference`; a source
material description may use evidence-bound `lexical_text` without asserting an
entity identity. A future registry requires a versioned contract, not fabricated
IDs. Optional lexical overrides are validated for source text and locale too.

An explicit ingredient quantity that cannot be normalized (for example a cup
without the source context needed to interpret it) produces rule uncertainty and
`recipe_ingredient_quantity_unresolved` in gold readiness. A genuine review may
still be recorded as reviewed; it does not erase that nested unresolved state.
V1 has no evidence-backed quantity-resolution overlay, so it remains blocked
rather than guessing conversion, density or locale. A source omission is not an
invented quantity and is distinct from an explicit unresolved quantity.
