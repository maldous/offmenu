# Recipe component consumer v1 — finite source-review candidate

## Retained relationship and selected scope

The supported normalized relationship is exactly:
`RecipeVariant --urn:offmenu:relation:usesIngredient--> IngredientMention`,
with one `urn:offmenu:property:requiredQuantity` assertion of
`value.kind == "quantity"` on that exact mention. It is a source-normalized
declared relationship, with its original asserted/candidate status, not a newly
accepted ingredient identity, culinary formulation or inferred membership.

The retained core report SHA256 is
`9ab94d1566f9a3c784baea3621059a954736dd9b08899d718ebb6d7f5c38fbec`.
Its historical evidence records 198,791 typed quantity joins, 136,962
recipe-step joins, zero reviewed exact ingredient-identity links, zero
step-to-ingredient joins and zero recipe nutrient-observation edges. These
counts are not newly rerun or a claim that this reader covers every recipe.

The accepted entrypoint is `inspect_recipe_relations.inspect(...)`, retained at
`recipe-inspector-code-v6/inspect_recipe_relations.py`, SHA256
`55cc3e67bd01fd887b2d1375bb3ed4439c330e56686b3ed4e6be4ffde66b8d31`.
It is an aggregate, full-selected-input inspector, not a value-returning recipe
reader. Its index has resource/edge/assertion projections but no packet locator.
This implementation does not rerun it, open its index, add an index, or invent an
existing value-reader. The new bounded reader consumes a manifest-listed locator.

This version supports only the existing core
`/offmenu-corpus/common-data-reviewed-package-20261014`, manifest
`c15005b224ae18c1e660837c6ac9fab88beb0b4d53ce34db6a5a87f12f6d919d`.
Its recipe selection is the exact 51 manifest entries retained in the accepted
proof, each at most 5,235,571 compressed bytes and 500 packets. Selected packet
lines have a separate fail-closed 8 MiB read cap. No directory/whole-corpus
lookup, source acquisition, free-text search or external lookup is performed.

## API and consumed path

```python
consumer = RecipeComponentConsumer(existing_core_mount, existing_recovery_base)
result = consumer.lookup(
    manifest_asset_key, packet_ordinal, exact_recipe_resource_id,
    exact_source_id, exact_source_release,
    include_candidates=True,
)
```

The reader verifies exact manifest/proof/contract/schema bytes, reads only a
declared asset, verifies its full compressed byte count/SHA256, stream-selects
the requested bounded packet ordinal, validates that packet against the selected
schema and calls the pure `adapt_recipe`. There is no unused helper-only output:
the public lookup and optional one-recipe CLI invoke this exact path.

Literal True opt-in is required. Without it, no input packages/packets are read.
Missing resource or source/release keys return empty typed status; no labels,
names or candidate matches supply a substitute identity. Duplicate identities,
mixed scopes/citations and tampered byte bindings are rejected. Missing or
ambiguous explicit edge/endpoint/quantity evidence yields an empty unresolved
typed status; partial ingredient membership is not fabricated.

Every returned component record includes the original source relation,
IngredientMention endpoint and quantity assertion, their exact IDs and canonical
digests, original status/derivation/sourcePath and complete quantity object.
Recipe resource, original citation objects/licence/attribution and their digests,
exact manifest/asset/packet locator and packet canonical digest accompany records.
All joins use IDs and exact citation/source-release/scope evidence. The reader
does not cross packets or stitch sources. Public normalized evidence only.

Original source value/unit, unknown versus numeric zero, range, qualifiers,
source notation, preparation state identifiers and recipe-yield assertions are
preserved. Missing yield remains not supplied; multiple yields remain ambiguous.
No batch/per-serving default, magnitude conversion, portion scaling, density,
yield conversion, nutrient calculation or accepted canonical preparation occurs.
A state qualifier is retained as a source marker, not interpreted. An original
IngredientMention identityStatus is copied; canonical ingredient identity remains
not accepted by this consumer, not globally asserted absent.

Outputs keep zero accepted ingredient-identity joins, uncalibrated confidence,
and false publication, aggregation, planning, served-app activation and inferred
step-ingredient-membership flags. The interface consumes copied source-normalized
evidence; it does not grant source rights, replace human acceptance or qualify
a recipe for cooking/planning.

## Both contract bindings are preserved

Selected schema: `89ff701460e0c9c6e27c5d5ece7bd6868f26f55fc2aedd1d85c87b4408cf1f6c`.
Required selected contract:
`b4fa5afb2f8cc77326299b55ccd75b93f121e807317fdc1f9953709e98faa0aa`,
from the existing pinned `bulk-parallel` metadata manifest
`8cd8abbf28f8fac11ccb73f336a91c7a5d90fbaff6ec1c864ec7b492f13da58e`.
The core source's own manifest lists the earlier 45,531-byte contract
`c7d1ff1646848b8df2fda3672058c534da63ecae539df338b3f2e9aba01fb749`.
It is not silently substituted or relabelled as the selected contract.

The reader verifies both manifest-listed source and selected contract/schema
bytes and requires exact equality of the five used definitions: RecipeVariant,
IngredientMention, usesIngredient, requiredQuantity and yield. Their equality
was also checked during source-only recovery. A definition mismatch fails closed.
No newer Git schema/contract is used, no original is rewritten and no new
interpretation of unrelated source fields is claimed.

## Custody findings and limitations

`SOURCE_FINDINGS.json` records recovered proof/source/manifest pins and bounds.
The specifically named `ACTUAL-SIX-MANIFEST-BOUNDS.json` was not found in the
bounded retained local source/output searches. One exact reviewed-custody path
lookup returned 404; it was not retried under alternate paths. No replacement
artifact with that name was created. Relevant bounds were instead verified
directly from exact immutable manifests and accepted reports; this gap remains
explicit for the custodian.

Expansion manifest `6f035cbe1303554cb59e6d3ee82f0e49bfa577e8d3844c2266df3241a4e328d5`
and historical manifest `e4c06a1d4a2fcb492529c37c6245a595dd104061ef1a63427cbe9d65e7e2241f`
were metadata-verified during recovery. Neither package is read or supported by
this core-only reader. The separate repair manifest
`e10deb8b50cddce89b15a29f82aa664b71b87d1fdff56a901826aa793a9e53e5`
remains its finite 42-recipe/308-field repair; this implementation does not
relabel it as the 25,135-packet core proof.

## Pending independently reviewed one-recipe exercise

The optional CLI selects at most one RecipeVariant from packet ordinal 0 of the
first manifest-listed core recipe asset, obtains its exact source/citation
binding locally, then calls the public lookup and adapter. It does not enumerate
other recipes or search the index. No eligible unique locator/path produces a
closed failure, not an invented relationship. It caches that exact packet for
the lookup, so selection and consumption use the same verified input.

Only aggregate counts/flags, pins and a canonical output digest are exported.
Original resource/source/recipe identifiers and values remain on the confined
worker. A fresh `recipe-component-proof-v1-*` child under the existing derived
root receives only `integration-proof.json`; no existing output is replaced.

Run only after independent source review, through normal existing confined
Windmill admission, at 1 CPU, 2 GiB RAM, at most 8 MiB output and 660 seconds,
preserving the existing 70 GiB reserve. The supervisor bounds wall time and
resources; this module does not submit jobs, alter admission or bypass refusal.
Use the existing Python environment with its installed schema validator; no
dependency installation is authorized.

At this handoff only focused synthetic new tests have run, using the actual
selected schema source as metadata. No actual recipe packet/index was opened,
accepted proof/test/scan rerun, derivation, app/publisher edit, publication,
activation, external source lookup or new access occurred.
