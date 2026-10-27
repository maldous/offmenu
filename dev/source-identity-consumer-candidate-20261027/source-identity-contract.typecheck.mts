// Compile only. No admission fixtures, runtime requests or dataset access.
import {createSourceIdentityReader, composeWithQualifiedPhase} from './source-identity-reader.mjs';
import {createSourceIdentityHTTP} from './source-identity-http.mjs';
import type {
  SourceIdentityObservation, SourceIdentityQuery, SourceIdentityReaderInput,
  SourceIdentityHTTPBody, OptionalSourceIdentitySelection,
  QualifiedPhaseResultForComposition,
} from './source-identity-contract.js';
declare const input: SourceIdentityReaderInput;
declare const partial: SourceIdentityObservation;
declare const body: SourceIdentityHTTPBody;
declare const notSelected: OptionalSourceIdentitySelection;
declare const phase: QualifiedPhaseResultForComposition & {readonly unchangedExtension: 'preserved'};
const query = {sourceId:'usda-files', namespace:'barcode', lexicalValue:'0049022712744'} satisfies SourceIdentityQuery;
const reader = await createSourceIdentityReader(input);
const result = reader.lookup(query);
const combined = composeWithQualifiedPhase(phase, result);
const samePhase: 'preserved' = combined.phaseResult.unchangedExtension;
const claims: readonly SourceIdentityObservation[] = combined.sourceIdentityClaims;
const handler = await createSourceIdentityHTTP(input);
const response: Response | null = await handler.handle(new Request('http://localhost:7645/api/corpus/source-identity'));
if ('readerResult' in body) {
  const selectionPin: string = body.selectionSha256;
  const nextOffset: number | null = body.readerResult.nextOffset;
  void [selectionPin, nextOffset];
} else {
  const error: string = body.error;
  void error;
}
if (partial.matchedIdentifier.namespace === 'USDA-FDC') {
  const noBarcodeChecksum: null = partial.matchedIdentifier.sourceChecksumValid;
  void noBarcodeChecksum;
}
// @ts-expect-error Source lexical values must never become numbers.
reader.lookup({...query, lexicalValue:49022712744});
// @ts-expect-error A partial source claim cannot masquerade as a qualified phase row.
const phaseRecord: QualifiedPhaseResultForComposition['records'][number] = partial;
// @ts-expect-error Unknown English does not expose a canonical label value.
partial.englishName.value;
// @ts-expect-error Source metadata cannot assert normalization.
const normalized: true = partial.normalizationComplete;
// @ts-expect-error Partial identity never fabricates the existing foundation handoff reference.
partial.foundationSourceReference;
// @ts-expect-error No null selection reaches reader construction without narrowing.
createSourceIdentityReader({...input, selection:notSelected});
// @ts-expect-error Do not retag source metadata as an ingredient.
partial.foodType.state = 'ingredient';
// @ts-expect-error Native identity lookup is not a barcode phase lookup.
composeWithQualifiedPhase(phase, reader.lookup({...query, namespace:'USDA-FDC'}));
void [samePhase, claims, response, phaseRecord, normalized];
