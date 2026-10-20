# Pure deterministic association selection

Source/synthetic candidate only. This module selects already reviewed
`productIngredientLinks` assertions under one exact selected input. It does not
parse ingredient text, mint concept/assertion IDs, infer product identity, emit
graph edges, grant source access, install a registry or change a consumer.
Frozen native candidate9ee7 remains separate; this change does not import or
edit it. Existing recipe/menu, origin emitter and UI code are unchanged.

## Selection and authority

`select_association(input_binding, policy=None, resolver=None)` returns a
deterministic decision/evidence projection. The default is unresolved with
`selection-unbound` and no selected assertions. `SelectionPolicy` and the
resolver are trusted application objects, never constructed by source JSON.
No real application factory is supplied. Review authorities are empty by
default. Inventing these objects or qualification-shaped JSON does not confer
authority.

The caller must independently qualify the exact native input and complete
source-field/origin/subfield evidence, operation rights and source context.
The selected `input_binding` must retain all those actual hashes/locators and
versions. The module requires source/release/record/original/qualification and
field-origin keys, exact equality with independently selected `expected_input`,
and an affirmed `ReviewedWitness` binding the entire input and private purpose.
It does not reconstruct origins, inspect source bodies, validate native
membership or prove fidelity from hash syntax. A malformed or fabricated
input must never receive that independent selection witness.

The resolver uses the existing evidence/claim/graph_role/relationship surface.
Existing `_Check` verifies evidence pins/work bounds, SourceContract operations,
qualified product/ingredient claims, exact versions, roles, formulation,
package/market, bounded effective period and ingredient food form. Every
eligible assertion also needs the existing exact affirmative
product-ingredient-relationship witness; endpoints alone are insufficient.
Private helper dependencies and the eventual actual factory need independent
review. Trusted resolver implementations must honor their own selected-byte
and no-IO contract; this module is not an OS boundary around arbitrary code.

Three explicit selected metadata inventories are pinned by path/SHA and version:

- Dictionary: `version`, `entries` of entryId, ingredientIdentityClaimId,
  exact existing ingredientVersion and independently reviewed specificity
  (`specific` or `broader`). Concept IDs are existing qualified graph bindings
  returned by claims. Shared entries/claims can serve several products.
- Rules: `version`, `entries` of ruleId, exact inputBinding fingerprint
  (`inputSha256`), entryId and an unchanged existing productIngredientLinks
  assertion. This first slice is finite exact-scope selection, not a general
  lexical matcher or rule interpreter. Additional qualified inputs need their
  own explicit applicable rules and witnesses; text similarity cannot supply
  them.
- Adjudications: `version`, `entries` of adjudicationId, exact inputSha256,
  complete applicable candidateRuleIds, selectedRuleId, affirmed/unresolved
  state and evidence. An empty set must be an explicitly selected pinned
  inventory. Missing is not implicitly empty. A stale candidate set, unknown
  selection or missing evidence refuses. Multiple matching adjudications remain
  ambiguous rather than last-writer-wins.

An independently selected affirmed inventory `ReviewedWitness` binds all three
pins/versions, full input, product claim and method version. It affirms the
entire selected dictionary/rule/adjudication set at that scope, including the
specificity labels and accepted adjudications. Generic policy approval is not
that witness. Source-side pins or a JSON `state` cannot select the authority.
Final relationship witnesses separately bind actual assertion and endpoint
versions. These are private decision-evidence details, not a graph protocol or
new fields on closed common records.

When all applicable candidates qualify, one canonical graph concept/form/
specificity/relation outcome selects all its existing source assertions. Rule
multiplicity gives no confidence or priority. Different eligible outcomes
remain ambiguous unless an exact accepted adjudication selects one outcome;
alternatives and reasons stay in the result. Any applicable candidate with
missing evidence prevents the remaining one from silently winning. Broader
stays broader; there is no automatic narrowing, majority vote, global barcode
merge, purity/allergen inference or usable_as inference. Assertions are never
rewritten from proposed to reviewed.

The decision retains full input, inventory hashes/versions, selected assertions,
ordered alternatives with eligibility/reasons and adjudication IDs. Cite this
payload through existing citation/derivation evidence in any later application.
All assertion evidence and endpoint/input/review pins remain necessary. The
same bytes and selected objects produce the same canonical result; no clock,
locale, random value, AI, network or database participates. Reordering inventory
bytes changes their hash and review, but semantic alternatives/assertions remain
stably ordered. No timestamp is inserted into the semantic result.

## Explicit uncertainty arithmetic

`uncertainty_metrics` accepts the four category counts plus an explicit assessed
denominator. It reports confirmed-specific, broader-only, ambiguous/conflicting
and unmapped/missing-evidence separately. Unclear is the latter three. A known
denominator must equal the category sum. Unknown denominator keeps observed
counts but returns null for total unclear numerator and percentage. A known
empty set has numerator0 and percentage null. Unassessed/excluded remain
separate explicit values or null; neither becomes a clear case.

The caller still owns the cohort/source/group/link inventory, definition and
axis, deduplication and complete accounting. This helper does not invent that
inventory or classify unassessed evidence. Report product identity separately
from ingredient associations, provisional source/barcode groups separately
from canonical products and required links. Never turn22 selected source rows
into22 products or apply selected-sample percentages to a corpus. No inclusion
threshold, deletion, source drop or acceptance policy is installed.

## Verification and remaining actual dependencies

Tests use invented input-selection/review inventories and existing synthetic
endpoint qualification fixtures, not real origin/input qualification. They
exercise replay, stable ordering/new pins, shared outcomes, broader retention,
competing outcomes/adjudications, stale input/inventory/endpoint/authority,
missing/nonaffirmative witnesses, explicit empty inventory, unknown candidates,
work bounds, fixed diagnostics, no direct IO and null/zero metric denominators.
This is author evidence; fresh independent review is required.

No actual dictionary/context/origins/ingredient witness set is selected here;
actual eligible mappings and emitted edges remain0. No private Wesson text or
original/candidate/DB/profile/recipe/pantry body is read. Actual linked examples
remain dependent on those qualified inputs and later consumer vocabulary/use
bindings. Recipe/pantry allocation and recursive composition/nutrition remain
dependent requirements in the existing design, outside this small source slice.
SAME11, source/ownership/privacy/custody/denial/auto_review and all schema/gold/
ingestion/UI/execution/promotion/production/CIX holds remain intact. Existing00
alone integrates a fresh independently accepted immutable candidate.
