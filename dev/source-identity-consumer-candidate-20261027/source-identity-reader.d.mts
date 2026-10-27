import type {
  SourceIdentityQuery, SourceIdentityNamespace, SourceIdentityReaderInput, SourceIdentityReaderResult,
  SourceIdentityBinding, SourceIdentityRights, SourceIdentifier, Sha256,
  QualifiedPhaseResultForComposition, OwnDataObservationComposition,
} from './source-identity-contract.js';
export const IDENTITY_INDEX: 'offmenu-source-identity-index/2';
export const IDENTITY_MANIFEST: 'offmenu-source-identity-manifest/2';
export const FIELD_SET: 'source-identifier-claims-with-provenance/2';
export interface IdentitySourceScope {
  readonly sourceId: 'usda-files';
  readonly releaseId: string;
  readonly sourceQualificationSha256: Sha256;
  readonly sourceRights: SourceIdentityRights;
  readonly selectedSourceIndexes: readonly Sha256[];
}
export interface IdentityIndexRecord {
  readonly stageId: string;
  readonly nativeId: string;
  readonly wireSha256: Sha256;
  readonly sourceInputIndexSha256: Sha256;
  readonly rightsVisibilityField: 'sourceVisibility' | 'visibility';
  readonly sourceBinding: SourceIdentityBinding;
  readonly identifiers: readonly SourceIdentifier[];
  readonly barcodePostings: readonly {readonly checksumValid: boolean; readonly lexicalCode: string}[];
  readonly sourceRights: SourceIdentityRights;
  readonly canonicalStatus: 'unresolved';
  readonly englishStatus: 'unresolved';
  readonly normalizationComplete: false;
  readonly goldAdmitted: false;
}
export function validateIdentityRecord(record: unknown, scope: IdentitySourceScope): IdentityIndexRecord;
export function sha256(bytes: Uint8Array): Promise<Sha256>;
export function createSourceIdentityReader(input: SourceIdentityReaderInput): Promise<Readonly<{
  lookup<TNamespace extends SourceIdentityNamespace>(
    query: SourceIdentityQuery & {readonly namespace: TNamespace},
  ): SourceIdentityReaderResult & {readonly namespace: TNamespace};
}>>;
/** Only already qualified reader results; never manufactures a phase record. */
export function composeWithQualifiedPhase<TPhase extends QualifiedPhaseResultForComposition>(
  phase: TPhase,
  identity: SourceIdentityReaderResult & {readonly namespace: 'barcode'},
): OwnDataObservationComposition<TPhase>;
