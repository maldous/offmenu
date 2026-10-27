# Partial owned-source identity: transport integration contract

This is a source-only delta for the existing reader and HTTP adapter. It adds
TypeScript declaration sidecars and a compile-only usage example, not a second
reader, a scanner client, an admission issuer or a runtime route.

## Exact boundary

`source-identity-http.d.mts` describes `createSourceIdentityHTTP` as implemented
in this directory. Successful `/api/corpus/source-identity` responses have a
`readerResult` containing `SourceIdentityObservation` values. They are not
foundation product rows. Errors have `error`, never a fabricated empty result.

`source-identity-contract.d.ts` is the shared DTO import for a consuming client.
The existing phase validator remains unchanged. A partial observation retains
the eight-field native source binding, source-input and wire pins, exact lexical
identifiers, original rights notices and the actual visibility-field provenance.
English name, food type, original name/language and nutrition remain explicitly
unknown. It cannot type-check as a qualified phase row or a foundation handoff
reference. All existing normalization, canonical/association, physical-product,
Gold and automatic planning/join assertions remain false.

Selection is operator-owned, with actual manifest/index/admission byte lengths
and SHA-256 pins plus the actual source qualification, source-rights field
contract and native-representation qualification. `OptionalSourceIdentitySelection`
is explicitly nullable. These types neither prove hashes nor create admission;
the existing reader still performs all runtime checks. No example supplies
invented pins or converts a prepared release into an accepted one.

The lookup namespace remains `barcode` or `USDA-FDC`. Both use exact strings;
there is no numeric conversion, zero stripping or lookup substitution. Source
claims stay `untyped`, separately from the existing typed-identifier contract's
GTIN-8/12/13/14, EAN-8/13, UPC-A/E, JAN/JAN-8/JAN-13 and ISBN-10/13 interpretations.
This delta neither narrows those supported representations nor infers food type,
manufacture country, physical carrier or packaging equivalence from them.

## Consumption boundary still awaiting exported source

The reported Worker13 package owns `source-identity-client.mjs`,
`composed-scanner-client.mjs` and `source-identity-selection.mjs`. None is copied,
reimplemented or edited here. Its reported result.json digest
`d608fe5f1a785df3dc7103e108aa9394ded7ea0b7685afd9df6df0baee06b7ac`
is a result-document identity, not an implementation hash or selection pin.
Actual client-source import edits require that exported implementation; actual
activation additionally requires the existing real selection/admission inputs.
Neither dependency is replaced by this declaration package.

Consumers should preserve the identity result's `totalSourceObservations` and
`nextOffset` independently from the phase reader's pagination. The existing
`composeWithQualifiedPhase` helper preserves the supplied phase result and
suppresses identical seven-field subjects only among the supplied phase rows;
it does not itself aggregate pages or carry identity pagination forward. The
new declarations describe this existing behavior rather than falsely implying
complete-query deduplication. Native USDA-FDC results cannot be passed to its
barcode-only composition signature.

## Provenance and focused checks

Observed foundation branch/base: `d6267b36bba7db669561293bd191980e1a6b567a`.
Observed develop: `dc39d0d7f29f0b0650be374f0e7e2111ec45c4b7`.
The implementation and existing test bytes used for the focused checks match:

| Existing file | Git blob |
| --- | --- |
| source-identity-reader.mjs | d7df4e418df1cb4778836bb779e3013f351f4abf |
| source-identity-http.mjs | d3691a66d83cfbc2dabb7878a5dcfc82a0bd0b97 |
| typed-identifier-contract.mjs | 84641cb514ec4f20adfa8abb260e95aa7f2be9dd |
| source-identity-reader.test.mjs | 45b645461793af839dee538b9e595334592ea8fb |
| source-identity-http.test.mjs | 5660937739ac7b6b70bdecd51639b191898b33de |

Focused results: strict TypeScript 7.0.2 compile passed, including expected
rejections for numeric lexical values, invented canonical English/normalization,
forged phase references, null selection and cross-namespace composition; the
unchanged reader/HTTP tests passed 20/20 on Node 24.19.0. Commands, from here:

```sh
tsc --noEmit --strict --target ES2022 --module NodeNext \
  --moduleResolution NodeNext --lib ES2022,DOM source-identity-contract.typecheck.mts
node --test source-identity-reader.test.mjs source-identity-http.test.mjs
```

These are focused contract checks, not an added release gate or full application
test claim. No package dependency, runtime/main/production source, raw dataset,
credential, selected-data artifact or actual admission changed.
