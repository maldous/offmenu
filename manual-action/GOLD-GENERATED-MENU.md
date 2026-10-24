# Generated recipe groups over an admitted snapshot

This is a read-only application-created grouping, not source menu ingestion or
meal planning. `offmenu/refresh/recipe_menu_store.py` retains source menu listings;
`public/menu-model.js` summarizes selected meals; `prepared-menu-owner22.mjs`
projects an individual preparation. Those contracts do not resolve a generated
group's recipe references against the admitted Gold snapshot. No schema is added.

The sidecar has version `offmenu.application-created-recipe-group/1`:

```json
{
  "schemaVersion": "offmenu.application-created-recipe-group/1",
  "id": "application-menu:generated-example",
  "title": "Generated recipe grouping",
  "origin": "APPLICATION_CREATED",
  "selectionOrigin": "GENERATED",
  "snapshot": {"databaseSha256": "<owner-selected 64-hex hash>", "admissionSha256": "<owner-selected 64-hex hash>"},
  "members": [{"recipeEntityId": "<admitted recipe entity ID>", "nativeRunId": "recipe-actions:<exact 64-hex run hash>"}]
}
```

Recipe IDs must resolve to verified recipe entities in that exact snapshot.
Missing, duplicate, product/ingredient, foreign run and mismatched snapshot
references fail the whole request. Members retain order. `nativeRunId` is optional;
omitting it returns available run IDs and unknown instructions, never an implicit
latest run or a language guess. An explicit run preserves its exact English
instructions, native unknown parameters and scope holds. Source records and
individual recipe citations remain separate. There is no generated menu source
citation, user-choice assertion, meal-suitability judgment or combined nutrition.

Each `nameRecords[]` entry preserves the original `sourceName`, complete Gold
`textRecord` (including original text, language and raw evidence), parsed
`evidence`, the name's own citations/rights and field/translation support records.
A qualified name's citations also appear in the member citation collection, even
when different from the resource/occurrence citations. `englishNames` contains
only qualified display names. Missing/invalid name support or cited rights marks
that name `held` with explicit `holdReasons`; valid names and member siblings
remain available. No fallback citation or translation evidence is invented. This
projects the selected admitted records; it does not grant new source authority.

Each selected action has an `instructionRecords[]` entry with the complete
`actionRecord`, parsed action `evidence`, exact `supportRecords` and parsed
`supportEvidence`, and the support citations including license and attribution.
Qualified action citations join the member citation collection even when absent
from recipe, occurrence and name citations. Support must target the exact selected
run/action, contain valid Unicode source spans matching the action evidence, and
resolve its own citation and rights. Persisted native source/module and review
artifact pins must be present and correctly shaped; this is a projection check,
not a rerun of native review or proof of artifact contents. Raw admitted records
remain available for diagnosis. If any action is unqualified, `instructions` is
empty and `instructionState` is `held-action-provenance`, with per-action reasons;
a partial sequence is never displayed as a complete selected run. Healthy names
and other members remain available. No run selection still means unknown
instructions, with no implicit fallback.

The file wrapper explicitly recognizes receipt version
`offmenu.private-incremental-source-data-admission/1`. `admissionLimits` preserves
the receipt schema and the complete, separate `scopeLimits` and/or
`sourceAndConsumerLimits` blocks under `sourceFields`. Neither block overwrites
the other. The corresponding top-level compatibility fields contain qualified
blocks; unsupported schema, missing blocks or invalid blocks produce a `held`
metadata state, explicit reasons and null compatibility fields. Bounded raw blocks
remain visible in `sourceFields`. Limits are projected without interpreting false
restrictions as grants or following nested receipt paths. Prior rights/purpose
pins remain references. Receipt limits share the JSON structure/size and final
output bounds. Selecting a successor requires its explicitly supplied database
and receipt hashes in a separate sidecar; an older selection never upgrades itself.

For this recognized receipt version, each limits block may be a nonempty
dictionary. `scopeLimits` may also contain a nonblank documentary restriction
string, but only alongside a nonempty `sourceAndConsumerLimits` dictionary.
That string is preserved verbatim, including whitespace and Unicode; it is never
parsed into permissions. All dictionary values and unknown restriction fields
remain complete. A textual scope by itself, blank text, an invalid consumer
block or an unsupported receipt version stays held. The existing JSON and
output bounds apply equally to text and dictionaries; this shape support grants
no new source use or execution authority.

For the barcode consumer, pass each desired `paths[].recipeEntityId` as a member
reference after its admitted barcode traversal; select any native run explicitly.
This module resolves membership, not barcode eligibility or product selection.
Keep the upstream barcode/path evidence alongside the generated sidecar.

```python
from gold_generated_menu import read_generated_menu

# Caller has independently selected and byte-verified the admitted snapshot.
# db is its exclusively owned immutable/read-only connection, with query_only ON.
menu = read_generated_menu(
    db, sidecar, database_sha256=selection.database_sha256,
    admission_sha256=selection.admission_sha256,
)
```

File callers use `query_snapshot(admission_path, trusted_admission_sha256, sidecar)`
or the CLI below. The expected admission hash comes from the accepted owner
handoff, never the sidecar. The wrapper verifies receipt/database bytes, opens
SQLite `mode=ro&immutable=1`, rejects sidecars and checks hashes after closing.
An accepted-looking JSON document does not independently grant source authority.

```sh
python3 -B manual-action/gold_generated_menu.py --admission /absolute/admission.json --admission-sha256 OWNER_PIN --group /absolute/generated-group.json
```

Defaults cap eight members, 2,000 returned SQL rows, 1 MiB output, 8 MiB source
cell bytes, one million SQLite steps and three cooperative query seconds. Limits
may increase only to the documented fixed ceilings in the function. Snapshot
files are capped at 64 MiB; receipts at 256 KiB; sidecars at 64 KiB/depth12/4096
nodes. Errors never masquerade as empty or truncated success. The raw reader
temporarily owns the connection's progress handler and SQLite value-length limit,
clearing/restoring them before return. It runs SELECTs and read-only metadata only.

Tests use generated databases only. Actual admitted demonstrations remain private
local evidence. Recipe/source rights, recall unknowns, incomplete execution and
normalization/runtime/production holds survive grouping. Worker56 independently
reviews exact code and output; Worker00 alone integrates. No Gold/data write,
fetch, normalization, server, deployment or external service follows from a query.
