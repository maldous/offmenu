# Historical recipe/product proof comparison

`source_recipe_product_proofs.assess(request, trusted_context=context)` is a pure,
bounded comparison helper for `HISTORICAL_SOURCE_DECLARATION_COMPATIBILITY_ONLY`.
There is no consumer integration or authority-loading adapter in this increment.
It does not open files, databases, services, calculators, native sessions or models.
It performs no writes. No real proof has been approved by adding this code.

## Boundary and API

External JSON must enter through `parse_json(text)`, which rejects duplicate keys,
nonfinite numbers and excessive inputs. A Python dictionary cannot retain evidence
of duplicate keys that its creator already discarded. Callers supplying dictionaries
are responsible for using that boundary first.

The request is `{"claims": [{"id": "caller-local-id", "claim": exact_claim}, ...]}`.
The envelope ID is outside the hashed claim. The five retained proposal claim hashes
therefore remain unchanged. The helper neither imports nor executes those actual
five claims. Additional request fields, including events, selections, prose reviews,
owner receipts and `compositionEvidence`, confer no authority.

`CallerReviewContext(snapshot, accepted, artifacts, facts, rules)` must be constructed
by an already authorized caller through the existing00/Gateway accepted independent
review and same-ledger custody route. Never deserialize this class from source JSON.
This helper cannot authenticate a native identity, discover revocation or establish
that a caller really is authorized. The caller must resolve current accepted custody,
independence and supersession before constructing context. No such loader, registry
or new controller is introduced here. Mutable context data is bounded and copied at
entry; callers must not mutate it concurrently during that copy.

`snapshot` has exactly `admissionSHA256` and `databaseSHA256`, lowercase64hex pins.
These are explicit immutable evidence pins, not an assertion of latest admission.
The current proposal is snapshot20; retained generated label arithmetic stays17.
A later snapshot requires independently accepted exact rebind. This helper cannot
read those snapshots or infer that a hash names their current contents.

`accepted` contains at most100 distinct-ID proof entries. Each entry contains
`id`, `claimSHA256`, `authorThreadId`, `reviewerThreadId`, `review`, `custody`.
Exactly one accepted entry may match a claim. Conflicting entries hold that claim.
Both references have exactly `artifactSHA256`, `pointer`, `rowSHA256`.
`artifacts` maps the raw UTF8 artifact SHA to its already-resolved JSON text.
Raw bytes including whitespace are hashed first; the JSON pointer is resolved;
the actual row is canonically hashed and compared, including strict JSON types.

The review row must equal this structured binding:

```text
claimSHA256, purpose, snapshot, constraints, factsSHA256,
authorThreadId, reviewerThreadId,
disposition="active", conflicts=[], revoked=false
```

The two native IDs must be nonempty and distinct. The custody row must equal
`{"review": review_reference, "binding": review_row, "disposition": "accepted"}`.
An arbitrary copied receipt in the request cannot enter the caller's accepted set.
Self-supplied hashes or an `accepted:true` field are insufficient. A forged owner
receipt inside a caller-created but unqualified context violates the caller boundary;
the pure function cannot turn attacker-controlled Python code into authority.
Old03 `/semanticAssessment` text and `/verdict`, or old12 `/decision`, are historical
evidence only; they do not have this new typed receipt shape.

## Caller-qualified fact projection

`facts` maps unchanged canonical claim SHA to a bounded, snapshot-qualified bundle:

* `claim`: the complete exact claim, compared with strict JSON types.
* `constraints`: nonempty structured, independently reviewed restrictions.
* `endpoints`: four ID-keyed rows (`source`, `mention`, `class`, `product`). Each
  carries the exact claim subobject in `binding`, actual source-bound `entityId`,
  `payload`, `payloadSHA256`, `state`, `resourceState`, `occurrenceState`,
  `supports`, `requiredSupportIds`, `bindingPointers`. The last map has one exact
  JSON pointer per binding field into the resolved payload; the helper compares
  every actual pointed value with strict JSON types. All endpoint/resource/occurrence states must be
  verified. Resource and occurrence qualification is supplied by the trusted caller;
  this is not a raw database adapter. Its payloads must be the actual qualified
  resource evidence, never manufactured mirrors of a claim.
* `relations`: actual ID-keyed edge rows with payload/state/support closure. Exactly
  the claim's mentions, canonical_ingredient and represents path is compared by
  payload SHA, predicate and source/mention/class/product endpoints. Relation IDs
  and citation IDs must agree with the exact claim.
* `citations`: ID-keyed rows with actual `payload`, `state`, `allowedPurpose`.
  Exact claim citation SHA/visibility/license/attribution are compared. All used
  citations must be verified, licensed, attributed, and authorized for this purpose,
  including private material. Visibility alone is never processing permission.
* Each endpoint/relationship/declaration row has all required record-or-field or
  relationship supports. Support rows contain distinct `id`, exact `targetId`,
  `kind` (`record`, `field`, `relationship`), verified `state`, `citationId`, and
  `valueSHA256`. Field supports also have a JSON `pointer` into that row's payload;
  other supports hash the full payload. `requiredSupportIds` equals the full set.
* `canonicalGroup`: the complete set of declarations for this mention, including
  held/conditional siblings, with actual payload/state/support rows. The trusted
  caller must obtain that complete closure from existing qualified facts. A
  selected-path query cannot establish completeness.
* `groupQualification`: `complete:true`, sorted exact `memberIds`, canonical
  `groupSHA256`, and exact six-field `sourceScope` (recipeId, mentionId, sourceKey,
  sourceVersion, recordId, contentSha256). The owner receipt binds the entire facts
  digest, including this qualification and all declarations. Removing a sibling,
  even while keeping the chosen triple, invalidates that custody binding.
* `selection`: null for the single unconditional mapping. Conditional selection
  must equal the selected declaration's complete typed condition.

The caller's accepted review is responsible for qualifying that this full projection
contains every required resource/occurrence field and relationship support. The
helper cannot detect a deliberately incomplete projection freshly certified by a
malicious caller. It rejects missing/mismatched closure in supplied qualified facts;
it does not implement another graph discovery engine.

`AlternativeRules(relation_condition, alternative_group_valid)` receives the existing
accepted typed-group functions from the trusted caller. The helper imports no builder
or SQL code. Tests pass those exact functions from `gold_builder`. They are trusted
code, never callbacks from request JSON. Mixed unconditional/conditional declarations,
duplicate branches, conflicting scopes/objects and unknown choices remain held.
Held sibling declarations stay visible but cannot be selected as verified paths.
The five actual proposal paths are unconditional; no product filter chooses a branch.

## Outputs and limits

`outcome="assessed"` includes one result per envelope, narrowly `qualified` or `held`
for historical compatibility. A bad tuple does not invalidate independent healthy
tuples. Malformed batch types, duplicate IDs or exceeded bounds return
`outcome="rejected", results=[]`, with no positive partial batch output.

Every v1 result always has `actualSelection="unobserved"`, `currentStateFit=null`,
`actualRecipeComposition=null`, `productFitAcceptance=false`,
`existingProductFitAcceptance=false`. Composition readiness remains held and its
seven structured gaps stay unobserved even when the request carries event-shaped
approvals. Preparation includes softened butter. Quantities, volume, counts and
missing ingredients cannot grant actual use or mass. Input sums and printed yield
or servings cannot establish measured output. This helper neither calculates nor
replays the existing Beurre8complete/8partial scenario; it never executes the Egg400g
partial proposal or trims required ingredients. Valid history survives such gaps.

Limits:5 claims,100 accepted proof rows,524288 total input bytes across request and
context including resolved artifact text, depth32,100000 JSON nodes,262144 output
bytes. Bounds and finite/type checks run before canonicalization. Canonical digest
uses sorted compact UTF8, `ensure_ascii=False`, finite numbers, no Unicode
normalization, no fileLF. Raw artifact SHA deliberately includes its original LF.

Run the generated-only tests from the assigned worktree:

```sh
python3 -B -m unittest discover -s manual-action/tests -p test_source_recipe_product_proofs.py -v
```

The27 reviewed vectors are exercised as5 positive,13 historical-negative,
8 composition-only and1 budget case, plus forgery/closure/purity/type controls.
Synthetic `sign()` exists only in tests and is not a real acceptance route.
Exact code review by56 and00 custody/publication are required after this freeze;
neither passing these controls nor design approval activates any real proof.
