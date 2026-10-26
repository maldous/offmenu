# Typed barcode foundation phase candidate

`offmenu-barcode-foundation-phase/2` is a pure, unadopted successor. It delegates
the original identity, subject, eligibility, parameter-state and later-phase
boundaries to the unchanged v1 assessor.

Entity kind and food-use eligibility remain separate from canonical base and a
meaningful English ontology type/category. A candidate requires a separately
reviewed `type` relation matching the selected base's `typeRelation`: exact key,
label, target concept, relationship ID/kind, subject concept, registry and review
pins, with source-subject-bound derived-type evidence. Generic `ingredient` or
`noningredient` entity labels cannot satisfy this requirement. Missing or
unqualified relations remain unresolved; the adapter never invents them.

Two additional parameter shapes preserve the actual reviewed R2 representation:

- `concept-reference`: an exact `{conceptId}` object selected by the policy.
- `assertion-list`: an ordered list of exact assertion/value/evidence entries.
  Every ID/value must be selected, IDs must be distinct, and all IDs must fit an
  explicitly reviewed nonexclusive group. Every nested evidence item passes the
  original source-subject and field-provenance checks. Conflicting alternatives
  cannot be silently flattened into a winner.

Unknown parameters retain the original qualified-representation meaning. No N/A
policy, source absence, numeric fat requirement, nutrition/recipe join, Gold,
full-product completion or publication acceptance is introduced. Source
attributes remain separate. Counts are selected-assessment counts only.

The caller must pin and independently review the actual semantic policy,
ontology relations, source/record/wire reader and publication operation. The
superseded policy with entity kind used as type is not admitted. Synthetic tests
demonstrate code behavior; they do not qualify source records or publish data.
