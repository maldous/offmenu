# Plain-text source context presentation

`gold_source_context_presentation.build_source_context_presentation` is a pure
adapter over the **unmodified result of the existing verified snapshot reader**.
It does not open a database, read a file, select a snapshot or run, authenticate
an admission, or qualify source facts. The verified menu reader also carries the
selected run's complete dependency/material/ingredient graph and supports, all
charged to its existing SQL row/source-byte/VM/time/output limits.

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
`textFormat: "plain"`. It preserves the complete original `admissionLimits`
object alongside `snapshot`, including unknown purpose, rights and restriction
fields, without interpreting them as new authority. The same fixed whole-output
limit applies to these fields; preserving them never permits truncation or a
larger cap. The returned object is detached from the input.

Each member preserves its run/entity/occurrence binding,
full source provenance and existing remaining holds, with ordered `events`:

- `source-context`: the complete original field, original Unicode span,
  citation/revision/rights, source-file pin metadata and source binding.
- `source-caution`: the complete original line (optionally excluding a leading
  `* `, `# ` or `- ` marker), with an exact `beforeActionId` and sequence.
- `instruction`: the existing qualified English text, action/sequence,
  evidence, full citations and unchanged unknown parameters. Both the action's
  `run_id` and its matching `actionRecord.run_id` must equal the selected native
  run; matching foreign rows or selected-run supports alone are insufficient.

Whole branch/note contexts appear before that member's instructions. A caution
appears exactly once, immediately before its bound instruction. The current
admitted20 example requires 39 instruction events, five whole branch/note events
and one caution event (45 total): the full Communion warning before flip
sequence9, three Flatbread branches and the complete 130/171-character Egg
notes. These facts are caller guards and retained input data, not hardcoded
recipe identities in the helper. Source-file pins are preserved as metadata and
are never dereferenced. Original source-record content digests are checked.

Two additional versioned context contracts are supported:

- `offmenu-source-local-lineage-qualified-companion/1`: three source-context
  events before instructions carry the full warning, full appliance variation
  (including source list marker), and the complete restricted lineage companion.
  Its complete original source must equal the selected occurrence. Every run,
  producer, consumer, material, source label, dependency ancestor, support and
  citation must bind to the menu's selected graph. All eight references, 48
  restriction entries and nine native unknown arrays must survive the explicit
  mandatory scope contract, including its companion hold ID and source-file pin.
  The full wrapper, original source/context, rights, unknown fields and selected
  graph remain in the DTO. This is source-local participation, with no physical
  material equivalence or quantity-allocation authority.
- `offmenu-private-historical-source-proof-context/1`: one inert source-context
  event per distinct claim retains the **entire** stored document, complete
  actual historical result, source/facts/provenance pointers, group/role closure,
  rights, restrictions and unknown fields. Its recipe/entity/occurrence/content
  and mention binding and canonical result digest must agree. `proofSnapshot`
  retains the original proof pins; `storageSnapshot` is the independently
  selected current storage pin. A proof made against21 is never rebound to23.
  Caller-review contexts, accepted-entry sets and referenced facts files are
  never loaded, reconstructed or evaluated. Actual selection/composition/fit,
  the seven physical gaps, servings and yield retain their unobserved/held/NULL
  states. Two claims attached to one recipe remain two distinct events.

These are private internal attributed presentation contracts. A stored
historical compatibility label does not qualify a current product, revoke a
hold, or confer source-use permission. Unsupported required context versions,
missing mandatory graph/support/rights/restriction fields and mismatched guards
fail the entire presentation. Full contexts appear before instructions and all
existing fixed input/output/node/depth/text/context limits remain unchanged.

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

## Shared sealed snapshot access

The barcode and generated-menu file wrappers use `gold_snapshot_access`.
Callers still supply the exact independently selected receipt digest; there is
no discovery, latest fallback, caller-authority reconstruction or source write.
The existing low-level connection APIs and relation reader keep their caller
custody requirements. This does not add a standalone unpinned relation route.

The boundary reads/hashes/parses one receipt buffer (at most1MiB), rejects
duplicate keys and nonfinite values, and holds its descriptor through the call.
Database identity is streamed before and after querying in chunks at most1MiB.
The explicit carrier ceiling is the barcode reader's existing1GiB policy;
the former menu-specific64MiB carrier rejection is removed. A75,481,088-byte
generated sparse fixture exercises the actual23 size boundary with a peak
Python allocation under5MiB. The database is never read into a single buffer,
deserialized, copied, written or cached by pathname/stat alone.

Verification has its own fixed10-second cumulative hashing limit and at most
two1GiB passes. This excludes SQL execution time and does not relax SQL VM,
time, row, source-byte, cell or final-output limits. `snapshotVerification`
reports actual carrier/hash bytes, passes, elapsed verification time, chunk
ceiling and the connection-identity method; it shares the original final output
cap. A larger complete barcode result can use its existing explicit output
option within the existing1MiB hard ceiling; it never receives an implicit cap
increase or truncation.

This file wrapper currently requires Linux `/proc/self/fd`, `O_NOFOLLOW` and
read-only descriptor inspection. SQLite opens the held descriptor through its
immutable/read-only URI. Because SQLite canonicalizes that path internally,
the helper separately verifies the **actual newly opened SQLite file
descriptor** against the hashed device/inode/size/mtime/ctime and read-only
flags. The descriptor scan stops at4096 entries. Unavailable, oversized or
ambiguous descriptor evidence fails closed. Do not run
unrelated concurrent SQLite/file-opening work in the same process during this
exclusive boundary; ambiguous opens are rejected rather than guessed.

The boundary rejects final-path symlinks, nonregular/oversized files and all
WAL/SHM/journal sidecars (including dangling symlinks). It enables query_only,
disables trusted_schema, uses memory temp storage, closes the connection and
rechecks held/SQLite/path identities, receipt bytes, database bytes and sidecar
absence before releasing a result. Replacement, mutation, receipt change,
resource exhaustion or consumer failure returns no successful partial result.
`mode=ro&immutable=1` requires an independently sealed snapshot; it is not a
locking protocol for a live writer. Private source/operation rights, immutable
independent code review, normal integration and mandatory auto_review remain
separate from carrier verification.
