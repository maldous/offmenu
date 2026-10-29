# Source-only literal quantities and explicit alternatives

`build_source_recipe_literal_facts(record, *, qualified_context)` returns a pure
one-recipe companion. It preserves source amounts, units, qualifiers, ordinal uses,
unselected branches, actors and context independently of native/executable/nutrition
availability. It has no I/O, allocation, normalization, calculator or persistence
path. Existing native368ef, the egg/handful allocator, their schemas and the source
presentation helper are unchanged.

## Input and caller boundary

External JSON must first use the imported accepted `parse_json` boundary, rejecting
duplicate keys/nonfinite values. A dictionary cannot reveal keys already discarded
by another parser. The accepted pure finite-JSON, RFC6901 and R4 citation-visibility
guards are reused from `source_recipe_product_proofs`; no assessor function is used.
The fixed dependency is the accepted db470/R4 code family. Future changes to that
dependency require compatibility checks with this companion.

`QualifiedSourceFactContext(binding, review, custody, artifacts)` is constructed
only by the existing00/Gateway qualified caller route after genuine independent
source-fact/representation review and current owner custody. Source JSON, stored
approval flags and prose cannot instantiate authority. The helper cannot authenticate
an arbitrary Python caller, native identity, independent review quality or external
revocation; those remain the qualified caller's responsibility. It validates actual
resolved, hash-bound review/custody rows rather than a self-supplied hash alone.
Generated test `seal()` is never a real acceptance route.

The context's `binding` is the exact independent review row:

```text
purpose = PRIVATE_INTERNAL_ATTRIBUTED_SOURCE_FACTS_ONLY
sourceSHA256, sourceScope, recordSHA256,
coverage, citationRights, constraints, optional nativeAvailability,
authorThreadId, reviewerThreadId,
disposition = active, conflicts = [], revoked = false
```

`recordSHA256` is sorted compact finite UTF8 JSON, without Unicode normalization or
fileLF. Author/reviewer native IDs are distinct and nonempty. `review` and `custody`
each have exactly `artifactSHA256`, `pointer`, `rowSHA256`. `artifacts` maps raw UTF8
artifact SHA to already resolved original text, including its LF/whitespace. The
resolved review row must equal `binding` with strict JSON types. Custody must equal
`{review: review_reference, binding: binding, disposition: accepted}`. Unknown finite
binding fields are preserved, but never supply a higher-stage grant.

Existing accepted reviews are reused only for their qualified scope. A newly typed
amount/branch/actor delta needs review of the exact record and complete coverage;
retained author notes and old source availability alone do not qualify it. This
contract adds no registry, authority loader, Common/GOLD schema or SQL table.

The record has these fields:

* `purpose` and `sourceScope`, including `rawSHA256` and the qualified occurrence ID.
* `source`: exact `rawText`, its raw `rawSHA256`, an opaque stable
  `artifactReference`, and `scopePointers`. Those pointers bind every other scope
  identity field into the parsed original source. References are never opened.
* `citations`: ID-keyed verified rows with complete `payload` and canonical
  `payloadSHA256`. Context `citationRights` binds every ID to that hash, visibility
  and this purpose. Actual nested `scope.visibility` and supported flat visibility
  resolve without rewriting payloads; malformed/conflicting forms fail closed.
  License and attribution remain mandatory; visibility alone grants no operation.
* `literalFacts`, `relativeGroups`, `alternativeGroups`, `sourceEvents` and
  `mandatoryContexts`, described below.

The entire record/context is bounded and copied before comparisons. Caller input
is never mutated. Unknown record fields survive in `uninterpretedRecordFields`;
unknown fields inside facts/groups/events/context/citations survive in their original
objects. Source metadata survives in `sourceReference`; `rawText` is represented by
its exact hash/reference, preserving the original full source including unknown
fields by reference. The caller must retain that source artifact. Unknown fields
are opaque source data, never execution, fit, native or nutrition authority.

## Quantities and uses

Each literal fact has `id`, `binding` (`kind: ingredient-total|method-use`, `sourceId`),
whole `sourceSpans`, `citationIds`, `amount`, optional `unit`, `qualifiers`, optional
`useMentions` and optional `membership`.

Every span has `pointer`, `start`, `end`, exact `text` and
`offset_unit: unicode_codepoint`; quantities/units/qualifiers belong to their whole
source context. Known amounts use `state: stated`, an exact `lexeme`, `span`, and
`form: integer|relative-part|fraction|range|word-count`. Current lexical forms cover
up to9 ASCII integer digits, explicit ASCII/vulgar fractions, integer ranges and
source word `one`. The range dash/spacing and fraction glyph remain exact. A stated
amount requires its exact quoted unit. No min/max arithmetic or word-to-number,
fraction, cup, scoop, tin, density, mass or metric conversion occurs. Obvious partial
numeric signs/fractions/ranges/multiplication fail closed.
ASCII `x`/`X` multiplication and `e`/`E` exponent joins also reject partial operands,
including parenthesized operands and signed exponents. Caret expressions remain
unsupported. These guards never evaluate an expression or rewrite its source.
Right-operand lookahead consumes interleaved whitespace, signs and wrappers in one
finite walk for both product and exponent markers. It stops at128 prefix UTF8 bytes;
longer ambiguous prefixes reject atomically. A sign inside a wrapper or after x
cannot expose an incomplete leading quantity as a qualified fact.
Unrelated unit words beginning with x/e and compact numeric units remain supported.

Word-count `one` must be a whole source token. Adjacent Unicode letters, combining
marks, numbers, connector punctuation or word joiners cannot be part of that token;
apostrophes connecting another word also prevent qualification. Genuine standalone
quoted/parenthesized/case-preserved `one` remains literal. No Unicode normalization
or invented count is used to make a substring qualify.

Unstated amounts use `{state: not-stated}` without a hidden form/lexeme/span.
Qualitative source wording uses `state: qualitative`, exact lexeme/span and no
numeric form. These are never zero or a replacement for a known source amount.
Review-bound coverage includes every known-amount fact ID. Ordinal `useMentions`
retain exact source lexemes/spans without inventing allocation arithmetic.

Relative-volume groups contain ordered positive `volume`/`volumes` fact IDs, exact
source scope, source spans and citations. Every relative-part fact belongs to one
complete group. Date1:7 and Grenadine1:5 remain separate source-relative parts, with
no absolute size or serving multiplier. Jam2slices/first/second remain source uses;
Cocoyam½cup remains method water apart from unknown boiling water; Eba tins and the
garri/flour discrepancy, Hlib date qualifiers and unobserved preparation all remain.

## Choices, actors and source events

Alternative groups have a source scope, `sourceSpans`, citations, explicit
`selection: null`, kind and ID-keyed branches. Kinds are `quantity-choice`,
`ingredient-choice`, `method-choice`, `service-choice`, `optional-context`.
Ordinary choices have at least2 branches; an explicit optional context can have one
quoted positive branch without an invented negative branch. Each branch has source
spans, citations, `factIds` and ordered `eventIds`. Groups and branches remain
complete under the independently reviewed coverage manifest.

Source events have source spans/citations, an exact source verb lexeme/span, actor
and optional group/branch membership. Actors are explicit lexeme/span or
`kind: unspecified`. No default operator is inferred. Branch spans contain their
events and quantities; references are exact, exclusive and complete. Same-source
event order is preserved. These are source events, not normalized native instances
or executable action chains.

Affogato retains1scoop and1–2shots OR one long pull shot, independently of its
pour→serve OR side-by-side service/diner mixing routes. Hlib's primary method and
alternative simmer-in-milk route stay separate. No default choice, product filter,
branch flattening, Cartesian expansion or diner-to-operator substitution occurs.
The ingredient canonical-group validator has different semantics and is not reused
for service/actor groups.

`coverage` contains ordered `literalFactIds`, `knownAmountFactIds`, `eventIds`,
`contextIds`, `relativeGroupMembers`, `alternativeGroupBranches`, `explicitActors`.
Every item must match the actual supplied record. Establishing semantic completeness
requires the genuine review/caller route; the helper does not rediscover all source
numbers/verbs or repair omitted facts freshly certified by a malicious caller.

## Four independent output stages

Successful output has `outcome: source-facts-qualified` and all original typed facts,
branches, source events, contexts, citations and audit references/constraints.

1. `sourceFactQualification.status` is `qualified` after exact source/review/rights/
   coverage checks. Missing or invalid qualification produces an atomic rejection.
2. `normalizedInstructionAvailability` comes only from the trusted review binding's
   existing qualified native metadata. It is `available`, `held` or `not-supplied`,
   source-hash-bound with reasons/receipt. Absent native metadata defaults only to
   `not-supplied`, so it never blocks otherwise qualified source facts. Available requires a resolved receipt;
   its native semantics are qualified by the existing caller/review route, not
   reinterpreted here. Source facts never fabricate native availability or runs.
3. `executableSuitability.status` always remains `not-qualified`, actual selection
   `unobserved`, current fit null.
4. `nutritionCompleteness.status` always remains `not-qualified`, actual recipe
   composition null, global fit false, metric normalization null.

Thus native-held source facts remain useful without a fictitious `ready-for-review`
run or numeric allocation. Existing allocation/schema and presentation adapters
remain separate explicitly scoped work. Source-only facts do not resolve cooking,
safety, current products, physical preparation, servings, output yield or runtime.

Limits are fixed:1 recipe,128 facts,128 events,16 groups total,16 branches per group,
128 citations,128-byte amount lexemes,524288 input bytes,262144 output bytes,
depth32 and100000 nodes. Finite/type/count/byte checks have no caller override.
Malformed/budget failures return `outcome: rejected`, source qualification held and
no partial fact/group output. Original caller/source data remains retained. Output
never truncates constraints or contexts to fit.

Run generated-only regressions:

```sh
python3 -B -m unittest discover -s tools/source-processing/tests -p test_source_recipe_literal_facts.py -v
```

The original eighteen groups use seven retained source shapes with original artifact SHA anchors.
Focused regression groups cover multiplication/exponent fragments and Unicode
whole-word boundaries. All ASCII multiplication/exponent operators (`*`, `x`, `X`,
`e`, `E`) share the same bounded adjacent-operand check on both sides, including
interleaved signs, whitespace, wrappers and repeated or mixed operator runs.
Inspection continues across every existing operator glyph to the neighboring
operand; a second operator cannot disguise a numeric operand as a quantity
boundary. This is exclusion only and adds no supported expression grammar.
A leading `*` without a numeric left
operand remains a bullet. Clipped and full unsupported expressions reject without
arithmetic or rewriting source text; ordinary integer/fraction/range/word
positives remain supported. Operand-edge inspection is capped at128 UTF-8 bytes;
ambiguous over-budget prefixes reject atomically.
Generated wrappers/review contexts test fidelity and guards; they are not actual
corpus calls or historical approvals. Exact independent code/generated review and00
integration precede separately qualified real retained processing. The completed
five-claim historical assessment must never be replayed by this companion.
