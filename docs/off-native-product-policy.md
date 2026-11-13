# OFF native product/profile policy

This three-new-path source candidate fills the schema/pure-semantic gap identified
by Worker26 readiness10296. It reuses accepted `product_adapters._off` and the
existing ProductContext, clock, generic qualification and acceptance contracts.
It changes no producer, runner, USDA policy, price module or codec. All evidence
is synthetic; it does not qualify or deliver any retained data.

## Scope and exact representation

The retained input is metadata-declared
`off-2026-10-12.jsonl.gz`,13132516914 bytes, SHA-256
`11f50515dc79181f385df8e59d37ae5ddb85b9b932f84b6411055e026d84680e`.
The module does not read, stat or hash that file or any cache body. The fixed
source asset is an expected pin for later verified application binding, not an
observation of its current bytes. No additional source permission follows.

`off_native_policy.native_schemas()` supplies complete closed schemas for the
actual native Python product and nutrientProfile records. This is not the richer
public JavaScript OFF projection. The product has only name, identifiers, brand,
ingredientsText, sourceCountryTags, rawNutriments, nutritionSourceBasis,
qualificationStatus and nutritionId. The profile has foodName, identifiers,
basis and the accepted projector's recognized nutrient map. Nested projected
objects and nutrient names/units/source fields are closed. Unknown source
nutriment keys and JSON values remain unchanged inside rawNutriments; they are
not silently promoted into recognized nutrients or canonical facts.

Native code is an exact4–32 ASCII digit string, preserving leading zeros. A code
that passes this lexical rule is not necessarily a valid GTIN; a valid GTIN
checksum is not proof of product/formulation/market identity. This policy never
verifies those identities. It keeps `qualificationStatus:unverified-source-assertions`,
`countries:[]`, raw country tags and the original nullable ingredient wording.
It does not infer English, allergens/traces/labels, structured ingredient edges,
ingredient quantities, normalized country membership or absence claims.

The accepted projector owns fallback names, numeric parsing, basis and selected
nutrient rules. Sodium remains the existing source-g convention; there is no salt
conversion. Negative finite values remain native source assertions, not canonical
nutrition qualification. Null, zero, false, numeric/string lexical differences
and unknown raw values remain distinct. Missing names fall back exactly as the
existing producer does; optional ingredient text stays null/empty as supplied.

## Pure source-bound check

```python
native_semantic_errors(record, context,
    source_record=verified_raw_row, source_ordinal=verified_logical_row)
```

The caller supplies a trusted ProductContext for OFF2026-10-12 with the policy's
data-only ODbL/DbCL attribution label and exact rights/scope/unknown-clock pins.
The label is a record convention, not a permission grant or a relicense. Original
acquisition remains unknown: fetchedAt/sourceDate are null, with the existing
unknown-retained marker. Source revision/last-modified/last-updated scalar claims
are preserved from that same row; they do not become acquisition or freshness.

The checker requires both the raw row and its logical ordinal. It checks schema,
exact lexical code/record identity, source context/pins, source-row provenance,
revision fields and every projected value. It reuses the accepted pure `_off`
projection, adds the exact producer provenance additions and compares canonical
JSON to preserve scalar types as well as values. It neither opens source.sqlite
nor builds another parser. Nonfinite or unrepresentable JSON fails closed.
Diagnostics are fixed codes without source values.

Passing arbitrary caller-supplied rows establishes only that comparison. It does
**not** establish source custody. The later reviewed application binding must
obtain each row and its ordinal from the SAME independently verified normalization
source.sqlite/input/manifest context. It must check that original identity equals
the selected code, verify the DB/manifest/input pins and immutability before and
after use, apply the actual witness row bound, and preserve current source holds.
No such real IO or bridge is installed by this candidate.

`UnboundOffSemantics(context)` is the explicit default callback: both product and
profile records fail with `off-native-source-authority-required` until that binding
exists. A plausible self-consistent profile or product cannot pass merely through
shape validation. Calling generic qualify with this unbound policy cannot qualify
the source. All-record count/ID uniqueness, counterpart inventory, exact custody,
operations and resource checks remain with the existing generic contracts and
the eventual reviewed source binding.

The native schema does not admit fieldOrigins enrichment. Existing origin code
is reusable, but any enriched representation needs its own reviewed coverage and
source-coordinate/transform qualification. No common/English/gold or public
record is emitted by this policy.

## Concrete pending finalization fields

`policy_descriptor()` exposes review identity and the pending fields; it constructs
no SourceContract and installs no default real ProductLimits. The accompanying
result packet pins this exact module, tests, documentation and accepted adapter.

After the actual complete eligible OFF terminal witness, finalization requires:

1. Exact terminal witness and independent review paths/hashes, full source input
   bytes/hash and complete/eligible/anomaly status. No historical accepted subset.
2. Expected native product+profile count and sorted unique-ID digest from that
   witness, actual raw-row extent, and explicit reviewed duplicate/invalid/quarantine
   disposition if the original is ineligible. Never manufacture counts/IDs.
3. Product-specific reviewed rights, scope and unknown-clock evidence assets,
   purpose and source conditions. Existing private witness authority is not a
   blanket grant for public/composite/image operations; no new blanket approval
   is imposed on already covered private preparation.
4. The verified SAME-source normalization DB/row/ordinal binding described above,
   complete schema/policy/code pins and actual all-record semantic callback wiring.
5. Explicit real ProductLimits and SourceContract byte/record/scratch/work limits,
   exact runtime/destination, current capacity/commitments and once-only operation
   selection. The schema sourceRow maximum remains unresolved until the witness;
   minimum1 is a coordinate rule, not an invented full-input row/resource envelope.

Do not require a future product output to run the separately scoped full-input
witness. That witness is already implemented; Worker57 owns its execution packet,
Worker64 its independent review and the product maintainer its current admission/scheduling.
the product integrator alone integrates reviewed source changes. This candidate does not retry
a denied review, consume the restricted OpenPrices sample or alter its holds.

## Verification

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tests python -B -m unittest test_off_native_policy -v
```

Authored rows exercise the accepted pure Python projector only. Tests cover full
schema shapes and source comparisons for both kinds, missing authority, altered
source/provenance/ordinals, lexical codes versus identity, fallback names, nullable
tags/ingredient text, unknown raw nutriments, source field/number/unit/basis and
inventory tampering, scalar type differences, nonfinite values, forbidden richer
JS/graph/origin fields and absence of witness/resource defaults. A guard test
rejects any call to normalization, gzip opening or SQLite connection during the
semantic check. No real original/cache/sample stat, hash, read, acquisition or
normalization is performed. Passing these tests is source-code evidence only.
