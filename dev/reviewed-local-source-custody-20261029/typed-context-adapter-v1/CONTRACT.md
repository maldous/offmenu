# Typed nutrient context adapter v1

This additive offline library consumes the already-returned value from retained
`SourceScopedConsumer.lookup(..., include_candidates=True)`. It closes the
consumer gap between source-scoped product/profile candidates and nested nutrient
quantity/metric metadata and same-source per-nutrient basis sidecars. It does not
select an actual lot's accepted nutrient profile, calculate nutrition, produce a
corpus, publish, or activate an application.

## API

```python
adapt(
    caller_result,
    include_candidates=True,
    expected_source_pins=reviewed_manifest_pins,
    upstream_code_pins=reviewed_code_pins,
    expected_contract_canonical_sha256=reviewed_contract_canonical_sha256,
)
```

Without literal `True` opt-in, return no records and
`candidate-opt-in-required`. On inconsistent, duplicate, ambiguous, malformed or
mismatched evidence, raise `EvidenceError` without returning partial records.
Input is finite JSON, at most 16 MiB, one product, 256 profiles and 16,384 context
assertions/profile. No inputs are mutated; all returned mutable evidence is copied.
Output records are sorted by content-derived IDs. There is no file/network/DB IO,
provider invocation, background work, settings change or runtime activation.

The integration owner must supply reviewed bindings separately from the result:
the exact three `sourcePins` returned by the caller, canonical digest of the
selected common contract, and the three retained code pins in `CODE_PINS`.
These are selection assertions supplied by the trusted consumer, not signatures.
The adapter cannot detect an adversary coherently rewriting both evidence and
its supposedly independent bindings.

## Trust boundary and prerequisites

**Verification is caller-bound, never fresh full-corpus byte verification.**
The retained upstream reader remains responsible for schema-validated authorized
immutable packages; source/derived manifest bytes and completion/candidate flags;
index byte pins; normalized and sidecar asset bytes; resource locators; packet
canonical digests; exact original identifier and product/profile edge assertions;
source release/citation/scope checks; and original/native basis restoration.
Per-source rights and derivative attribution remain an upstream authority check.

The caller result does not expose original nutrient assertion bodies, original
metadata assertion bodies, all source-assertion statuses, raw source records, or
code pins. A supplied input digest cannot authenticate absent bytes. The adapter
therefore preserves the returned candidate assertion and input-ID/digest inventory,
labels the quantity and metric metadata as copied source assertion values, and
does not claim to independently verify those originals or code execution.
A coherent change to copied metadata with recomputed unkeyed candidate IDs is
outside this adapter's detection boundary; a synthetic test makes this explicit.
This limitation must remain visible in consumers.

## Checked joins and typed output

- Check caller schema, status/cardinality, independent manifest selection and
  false planning/aggregation/application flags. Product and profile resource
  types, exact IDs, one original citation each, public scopes and source/release
  identities must agree. Preserve complete citation objects including licence,
  attribution and source text; never join on names, labels or nutrient labels.
- Validate normalized selection identity (manifest/relative asset path/digest/
  packet ordinal), matching context and basis packet digests, retained sidecar
  schemas/rulesets/methods, candidate IDs and unique input-ID/digest inventories.
- Join a basis target only by an exact input assertion ID present in the nutrient
  candidate, identical assertion digest, exact nutrient source path plus
  `.basis`, original quantity canonical digest, profile subject, citation
  identities, scope and normalized source selection. Check native selection
  structure and retained source-identity digest syntax. Raw native bytes and
  source identity fidelity still belong to the upstream reader.
- Preserve each original quantity object and source measurement, null versus
  numeric zero, original unit, qualifiers, range/trace/source values and
  denominator object without scaling. Preserve the exact structured metric
  definition/method metadata; do not reinterpret incompatible nutrient meanings.
- A supplied finite alias candidate is checked only against the retained
  four-entry symbol/dimension mapping (`kj/kJ`, `ug/mcg/µg`). Keep original
  unit and magnitude; no conversion, comparability or canonical acceptance.
- Copy own per-nutrient preparation literals separately from the original
  denominator. Null state is `unknown`; a non-null literal is
  `source-literal-not-canonicalized`; absent basis sidecars/targets are
  `not-supplied`. Accepted canonical preparation is always null. Any preparation
  fields already carried by the original quantity remain in that original
  object. Profile-reported basis is copied separately and never fills a missing
  nutrient preparation or qualifies its comparability.
- `productEvidence` preserves original product resource/citations/identifier
  evidence/selection. `profileEvidence` preserves resource/citations/selection,
  basis sidecar and upstream issues once per profile. Per-nutrient records retain
  the original context candidate plus the exact matching basis group/target,
  referencing profile evidence by exact ID. This avoids copying the complete
  basis sidecar for every metric.
- Missing context yields an explicit unresolved profile with available basis
  evidence. A basis target without its returned nutrient context is rejected.
  Original producer issues remain visible; output is not exhaustive original
  nutrient coverage. Missing metadata can prevent the producer from returning a
  context, and this adapter cannot recover it from absent originals.
- Ingredient and recipe identities are `not-supplied-by-this-caller` with null
  identities, not fabricated links and not assertions of global absence.
  Confidence remains `not-calibrated`/null; identity admission count is zero;
  publication, aggregation, planning and application activation remain false.

## Source custody and pins

Product North Star: private `maldous/offmenu` at
`04df9172621e858f21580ac330a4bab3ff606955`, `README.md` SHA256
`c6b3a4991f9cdbace5a5b4f60776167f27e4ad892f1e5c6894b370a9a4ee8e3b`;
read together with `docs/research-delivery-plan.md` at that same commit.
Those exact files were missing from this checkout's Git objects and were read
through the authorized GitHub file connector; the README digest was verified.
No raw data was fetched.

Retained reviewed source custody references supplied by the coordinator:
`a759cb1df44df4108dbd0cdc75f4221ecfd1d255` (V2) and
`b163301ccfc92863ca0ede1f43d6f7f74c2343d4` (V4), under
`dev/reviewed-local-source-custody-20261027/north-star-reviewed-source-v{2,4}-20261028`.
These commits were unavailable in this checkout. Implementation used the exact
staged source files below, independently checking each supplied SHA256 before
design. No claim is made to verify a Git ancestry unavailable locally.

Relative to the existing `north-star-derived-20261028` source root:

| File | Verified SHA256 |
| --- | --- |
| `caller-code-v2/source_scoped_north_star_consumer.py` | `75a43f30967c2ea38606e0a1468132629a51b9c79744eed71938a5e1d146b3bc` |
| `basis-code-v1/north_star_derivations.py` | `fee258de07319fd19c0032701ea2731afabc1f560eb69c80f111088c65cf0509` |
| `basis-code-v1/north_star_basis_restoration.py` | `cae8b86cbacdbf0d81b9a52bb508dadae56e29639cfd332f87fb2b71bd18566a` |

Tests build wholly synthetic native records, normalized packets and caller
results using the retained pinned `derive`, `native_projection`, `restore`,
`old_quantity` and `urn` functions. No populated indices, shards, manifests,
receipts or raw records are opened, and no accepted corpus proof is repeated.

Run with the three sibling staged source files available:

```sh
python3 -B -m unittest discover -s typed-context-adapter-v1 -p 'test_typed_nutrient_context.py' -v
```

This packet is source-only for independent review. Integration still requires
the sole integrator to obtain reviewed manifest/contract bindings through its
existing authorized reader and connect this pure adapter to its caller. No
source-rights grant, accepted culinary identity, actual-lot selection, recipe
nutrition, publication, deployed endpoint or application activation is supplied.
