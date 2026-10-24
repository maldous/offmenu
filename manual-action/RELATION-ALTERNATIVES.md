# Source-scoped exclusive alternatives

An ingredient mention such as “white OR turbinado” is one source mention with
two conditional `canonical_ingredient` relations. Keep the original expression,
source path and citations; do not manufacture two unconditional ingredient
requirements, select a default, or evaluate source prose as executable code.

Each relation carries the following typed condition:

```json
{
  "kind": "selected-alternative",
  "groupId": "sugar-choice",
  "branchId": "white",
  "sourceScope": {
    "recipeId": "source:recipe",
    "mentionId": "source:sugar-mention",
    "sourceKey": "publisher",
    "sourceVersion": "revision-1",
    "recordId": "record-1",
    "contentSha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  }
}
```

The other relation has the same group and exact source scope, its own branch ID,
and the source-supported turbinado class as its object. At least two distinct
branches and objects are required. One exclusive group is supported per mention;
duplicate branches, mixed conditional/unconditional mappings and conflicting
scopes fail closed. This bounded contract intentionally supports canonical
ingredient alternatives only. Other predicate conditions require a separately
reviewed extension. Untyped `alternativeGroupId`, `groupId` or `branchId` fields
on a relation are rejected by the builder/lookup, not treated as unconditional.
Multiple distinct canonical targets with no conditions also fail closed: a
legacy packet missing both conditions cannot silently restore the original leak.

`gold_builder.py` requires the usual public source, English, occurrence rights,
relationship support and endpoint qualification. It also binds the condition to
the exact qualified recipe occurrence and its supported `mentions` relation.
The mention must have the same source key/version. A valid qualified alternative
is proposed as an edge in state `conditional`; a bad or unsupported branch is
held. All declared branches participate in structural validation, including held
ones, so removing qualification cannot silently change the declared choice.
For every required resource citation, the builder and lookup accept qualified
`record` **or** `field` support. The scopes may differ between citations; one
supported citation never covers another missing, wrongly scoped or invalid-pin
citation. Relationship citations still require `relationship` support.

The builder's potential graph retains source-qualified alternative endpoints so
a later explicit selection can use them. That graph is **not a selected recipe
or recommendation**. For conditional packets the connectivity report separates
unconditional core seeds from source-qualified potential seeds and reports
`selection_required`. Existing unconditional packets retain their behavior.
Missing own product/nutrition associations and other existing holds still apply.
No proposal is automatically admitted to GOLD.

`gold_relation_lookup.lookup_recipe_products` is the actual SQL lookup. Supply
the exact source scope and zero or more selections shaped as
`{"groupId":"sugar-choice","branchId":"white","sourceScope":{...}}`.
An absent selection returns `unknown` and no conditional paths. One exact,
qualified selection returns paths for that branch only. Unsupported branches,
duplicate/conflicting selections, malformed conditions, stale source scopes,
missing support or held endpoints never fall back to a sibling. Independent
unconditional paths remain available. Results include the original relation
payloads with their source paths, citations and scope/reuse restrictions; this
lookup neither interprets free-text reuse restrictions nor grants a new use.
It does not qualify cooking execution, nutrition, interchangeability or safety.
Each result explicitly reports `productFitAcceptance: false`. Every returned
path carries `sourceScope` for its exact recipe occurrence and mention, plus
`productFitQualification: {"state":"held","reason":"selected-tuple-fit-contract-not-evaluated"}`.
Together with the path's `canonicalId` and `productId`, this identifies the exact
source/mention/class/product tuple whose fit remains held. Supported source
identity relations remain available as structural evidence. A selected canonical
alternative does not qualify the fit of every product in that class. Neither
free-text `reuseScope` nor documentary claims in relation metadata grant fit
acceptance, even when they name an exact product or resemble a review receipt.
Original relation payloads, citations and reuse restrictions remain unchanged.

This is an explicit documentary/held boundary, not a positive selected-tuple
proof evaluator. All fits remain held, including tuples reviewed outside this
consumer. Missing, stale or conflicting documentary proofs cannot lift that
hold. A positive fit consumer requires a separately reviewed enforceable contract
bound to exact source occurrence, mention, class, product and supporting review
evidence. This change introduces no proof input, allowlist, predicate or schema
extension and grants no new source use. Callers must not consume structural
paths as accepted product fits.

An attributable requested mention whose application mapping is held supplies
source context only. It is reported as held while independent qualified siblings
remain eligible; it cannot supply a sugar path. Unknown recipe occurrences,
source mismatches and undeclared mention contexts still fail closed globally.

The command-line route accepts JSON arguments without writing the database:

```sh
python3 -B manual-action/gold_relation_lookup.py \
  --database /absolute/path/to/reviewed-snapshot.sqlite \
  --source-json '<exact source scope JSON>' \
  --selections-json '<selection list JSON>'
```

It opens an existing SQLite snapshot with `mode=ro&immutable=1` and
`query_only=ON`. Use only a frozen snapshot, not an active WAL database whose
uncheckpointed contents an immutable connection would miss. Source/operation
authority to read any real snapshot is separate from this code. Tests use only
generated data and disposable fixtures.

The SQL proposal schema adds `conditional` to **edge states only**, qualifies
its endpoints on insert/update, and prevents a conditional payload from being
silently promoted to `verified` (including after an intermediate hold). Full
condition and group validation lives in the builder and is repeated in the
lookup. Existing consumers filtering `state='verified'` exclude these branches;
they do not gain explicit-choice support automatically. Integrators must route
choice-aware callers through this lookup rather than unioning both states.
Insert guards also check existing physical edge and logical relation identities
before replacement/conflicting inserts, including held condition-bearing rows.
Those identities cannot be relabelled in place to evade the insert guard.
An identity collision is rejected without discarding the prior source payload.

This implementation is qualified only by bounded generated fixtures and frozen
snapshot use. It uses `fetchall`; live or unbounded consumer qualification is
excluded and requires separate review rather than an assumed capacity guarantee.

This is proposed source DDL, not a migration of any existing database. Worker00
owns review, integration and any separately authorized snapshot rebuild/schema
transition. Prior snapshots, source artifacts and review receipts remain
immutable. Existing databases with the old CHECK constraint cannot store
conditional edges and must never have them flattened to verified to bypass it.

Focused generated checks cover the source expression, unknown/selected choices,
an independent unconditional sibling, source mismatches, malformed or missing
conditions, conflicting groups/selections, held support/endpoints, SQL update
guards, common schema validation and the real read-only CLI. Run:

```sh
python3 -B -m unittest discover -s manual-action/tests
```
