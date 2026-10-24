# Plain-text source context presentation

`gold_source_context_presentation.build_source_context_presentation` is a pure
adapter over the **unmodified result of the existing verified snapshot reader**.
It does not open a database, read a file, select a snapshot or run, authenticate
an admission, or qualify source facts. `gold_generated_menu.py` is unchanged.

```python
from gold_source_context_presentation import build_source_context_presentation

presentation = build_source_context_presentation(
    menu_result,
    expected_snapshot={
        "databaseSha256": trusted_database_sha256,
        "admissionSha256": trusted_admission_sha256,
    },
    required_run_contexts={
        selected_run_id: {
            "recipeEntityId": selected_recipe_entity_id,
            "sourceOccurrenceId": selected_source_occurrence_id,
            "contextCount": required_whole_context_count,
            "cautionsBefore": [
                {"actionId": affected_action_id, "sequenceIndex": affected_sequence},
            ],
        },
    },
)
```

The snapshot pins and complete per-run guard are trusted caller inputs from the
accepted handover/source-context requirements. Do not derive them from an
incoming UI request or from the menu being checked. Every selected run must have
a guard, including runs requiring zero contexts/cautions. Hash agreement alone
does not authenticate arbitrary caller-provided dictionaries. This adapter is
not an acceptance API for untrusted records or a replacement for the verified
reader and independent source/written-data reviews.

The result has schema `offmenu.source-context-presentation/1` and
`textFormat: "plain"`. Each member preserves its run/entity/occurrence binding,
full source provenance and existing remaining holds, with ordered `events`:

- `source-context`: the complete original field, original Unicode span,
  citation/revision/rights, source-file pin metadata and source binding.
- `source-caution`: the complete original line (optionally excluding a leading
  `* `, `# ` or `- ` marker), with an exact `beforeActionId` and sequence.
- `instruction`: the existing qualified English text, action/sequence,
  evidence, full citations and unchanged unknown parameters.

Whole branch/note contexts appear before that member's instructions. A caution
appears exactly once, immediately before its bound instruction. The current
admitted20 example requires 39 instruction events, five whole branch/note events
and one caution event (45 total): the full Communion warning before flip
sequence9, three Flatbread branches and the complete 130/171-character Egg
notes. These facts are caller guards and retained input data, not hardcoded
recipe identities in the helper. Source-file pins are preserved as metadata and
are never dereferenced. Original source-record content digests are checked.

**Render text as text.** Use `textContent` or context-appropriate HTML escaping.
The adapter returns no HTML, template code, “safe HTML” marker or executable
link. Source markup remains literal data. Source/history/licence URL fields
must use HTTP(S), a host, no user information or control/whitespace characters,
and valid ports; this does not make strings safe to concatenate into markup.
Do not automatically render arbitrary fields from raw remaining-hold JSON.

Malformed JSON-looking holds, duplicate JSON keys, unknown companion-shaped
documents, missing/extra/foreign companions or cautions, clipped text, incorrect
Unicode spans, citation/rights/provenance mismatches, instruction/support/order
failures and scope uplift raise `SourceContextPresentationError`. Plain-text
holds and unrelated bounded JSON holds remain unchanged. No partial DTO is
returned and no input is mutated. A missing required caution cannot silently
become an instruction-only presentation.

Fixed limits have no caller override: input and output each1MiB, 100,000 JSON
nodes including keys, depth20, eight members, 128 instructions, sixteen combined
contexts/cautions, each hold JSON64KiB and each event text16KiB. Oversized
presentations fail whole; they are never truncated, split or silently relaxed.

Application-created/generated origin, absent source-menu evidence, false user
selection/planning/cooking flags and NULL recipe/combined nutrition are retained.
Full warning/note presentation does not grant product fit, serving/scaling,
quantity conversion, safety, cooking, user choice, current composition, runtime
or production authority. Source notes about people or eggs per person remain
source notes. Contextual product label nutrition and hypothetical label
scenarios remain separate and are not calculated by this adapter.

Tests use inline generated records only. Retained admitted20 acceptance is an
offline owner report against the frozen integrated menu output; it requires no
new barcode, database, native helper or source query. Independent exact-commit
review remains required before integration.
