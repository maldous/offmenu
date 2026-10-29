# Source-literal recipe quantity successor

This current connector extension preserves source amounts that immutable native
`368ef2ce0e42bba3497c5e548f47422a989ea10a` cannot normalize. The native helper,
fixtures, source scaffold and genuine semantic review remain unchanged. An
unresolved native ingredient quantity stays unresolved. The connector may render
reviewed source instructions using a separately typed, evidence-bound literal
allocation. It never calls a household measure a metric normalization.

Opt in with `source_literal_quantities` in the qualified connection body, before
calculating its qualification digest. Each row has exactly these fields:

```json
{
  "source_ingredient_line_id": "source:ingredient-line",
  "kind": "item-count",
  "value": "4",
  "unit": "eggs",
  "descriptor": "large",
  "evidence": [{"pointer":"/ingredients/0/raw_text","start":0,"end":12,
                "text":"4 large eggs","offset_unit":"unicode_codepoint"}],
  "citation_ids": ["source:citation"]
}
```

`household-measure` supports literal `handful`/`handfuls` with no descriptor.
`item-count` supports `egg`/`eggs`, with a literal `large` descriptor when supplied
by the source. Positive ASCII integer tokens are supported; other units, kinds,
descriptors, fractions and ranges remain held. This is a small source-literal
capability, not an arbitrary unit registry or recipe-ID allowlist. Existing
metric/time/temperature range normalization is unchanged.

The source quantity, unit and native original must match exactly. Only native
`quantity_unit_unsupported` quantities are eligible. Evidence must contain the
full contiguous literal phrase, so `4 eggs` cannot stand in for `4 large eggs`.
Spans must resolve in the exact rule source and belong to that ingredient's own
row or a source step whose native ingredient reference binds that line. Required
citations must be qualified in the connection. Duplicate, unknown or unrelated
line bindings, bad spans and missing citations fail closed. This validates
bindings, not the truth of a human/assistant review; genuine source-purpose,
semantic and independent acceptance still govern use.

The existing ingredient link must bind a quantity slot with the same value,
unit and descriptor. A household measure may use an explicit unit slot or include
the unit in the quantity display. An egg count uses its ingredient noun as the
unit: a quantity display `4 large` plus noun `eggs`, without duplicated units.
The descriptor must be present in the typed quantity value, not silently dropped.

In this opt-in profile **every known source ingredient quantity** must allocate
its whole amount once, at its first native ingredient-reference use. This keeps
a supported `400 g` base-flour row separate from an unresolved extra-flour row,
and prevents the known amount from disappearing behind qualitative NULL links
after an egg-count fix. Wrong rows, slots, later-use bindings, partial amounts,
duplicate allocations and over-allocation remain held. This conservative
transcription profile does not support split amounts. A source that requires
splits needs a separately reviewed extension.

Missing water/oil/extra-flour quantities remain NULL and explicit source/action
unknowns. NULL is not zero. Method-only salt/water identities, tool alternatives,
shape, thickness, temperature conflicts and other source unknowns are not
resolved by this contract. Source authors must retain them in the genuine
reviewed instances and their presentation; the extension does not invent them.

The output allocation union adds a `source-literal` object containing the exact
row claim and evidence, `metric_normalization: null` and
`scaling: "not-qualified"`. It has no fictitious native `normalized`,
`normalized_unit` or `scaled_min/max` values. Metric allocation objects remain
unchanged. Requested-serving/scaling input is refused for this profile, including
an apparently unchanged serving request. No g/mL conversion, density, calibration,
food mass, yield, recipe nutrition, cooking, safety or planning grant follows.

The additive JSON output allocation union is necessary to represent that
honestly. The existing SQL `allocation_json` already accepts JSON objects; no SQL
schema/native pin/table change is made. Legacy calls without this opt-in retain
their existing validation, unsupported-unit holds and output. Neither JSON Schema
nor a `ready-for-review` result grants GOLD admission.

Implement and independently accept/integrate code using generated controls
first. Execute qualified retained source packets only after that gate with pure
`store=None/cache_result=False` helpers and new genuine source-bound reviews.
Worker00 alone owns shared candidate writes and admission after independent
review of the exact actual output. Existing variants and all source-use,
provenance and denied-action holds remain active.
