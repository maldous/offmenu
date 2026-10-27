/**
 * Source-only transport boundary for the existing reader and local HTTP adapter.
 * These declarations grant no admission, validate no digest, and activate no route.
 * A lexical identifier is always a string; leading zeroes and invalid claims survive.
 */
export type SourceIdentityNamespace = 'barcode' | 'USDA-FDC';
export type SourceIdentityFieldSet = 'source-identifier-claims-with-provenance/2';
/** Runtime validation still requires a lowercase 64-character hexadecimal digest. */
export type Sha256 = string;
export interface SourceSubject {
  readonly sourceId: 'usda-files';
  readonly releaseId: string;
  readonly recordId: string;
  readonly sourceObservationSha256: Sha256;
  readonly sourceDocumentSha256: Sha256;
  readonly inputDatabaseSha256: Sha256;
  readonly sourceQualificationSha256: Sha256;
}
export interface SourceIdentityBinding extends SourceSubject {
  readonly nativeRecordId: string;
}
export interface SourceIdentityRights {
  readonly attribution: string;
  readonly license: string;
  readonly sourceVisibility: 'source-staging';
}
export interface SourceIdentityDescriptor {
  readonly sha256: Sha256;
  readonly bytes: number;
}
/** Operator-owned exact selection. A digest-looking value is not an admission. */
export interface SourceIdentitySelection {
  readonly sourceId: 'usda-files';
  readonly releaseId: string;
  readonly sourceQualificationSha256: Sha256;
  readonly sourceRightsFieldContractSha256: Sha256;
  readonly nativeRepresentationQualificationSha256: Sha256;
  readonly manifest: SourceIdentityDescriptor;
  readonly index: SourceIdentityDescriptor;
  readonly admission: SourceIdentityDescriptor;
}
/** No default pins: the client stays unselected until actual admission is available. */
export type OptionalSourceIdentitySelection = SourceIdentitySelection | null;
export interface SourceIdentityReaderInput {
  readonly selection: SourceIdentitySelection;
  readonly manifestBytes: Uint8Array;
  readonly indexBytes: Uint8Array;
  readonly admissionBytes: Uint8Array;
}
export interface SourceIdentityQuery {
  readonly sourceId: 'usda-files';
  readonly namespace: SourceIdentityNamespace;
  readonly lexicalValue: string;
  readonly offset?: number;
  readonly limit?: number;
}
export interface UnknownIdentityField {
  readonly state: 'unknown';
  readonly reason: 'not-in-qualified-identity-metadata';
}
export interface SourceIdentifier {
  readonly system: SourceIdentityNamespace;
  readonly value: string;
}
export type MatchedSourceIdentifier = {
  readonly namespace: 'barcode';
  readonly lexicalValue: string;
  readonly relationship: 'exact-source-claim';
  readonly representation: 'untyped';
  readonly physicalCarrier: 'unverified';
  readonly sourceChecksumValid: boolean;
} | {
  readonly namespace: 'USDA-FDC';
  readonly lexicalValue: string;
  readonly relationship: 'exact-source-claim';
  readonly representation: 'untyped';
  readonly physicalCarrier: 'not-applicable';
  readonly sourceChecksumValid: null;
};
/** Not a foundation product, ingredient, normalized-English record or stock reference. */
export interface SourceIdentityObservation {
  readonly schema: 'offmenu-source-identity-observation/2';
  readonly stageId: string;
  readonly nativeId: string;
  readonly wireSha256: Sha256;
  readonly sourceBinding: SourceIdentityBinding;
  readonly sourceIdentifiers: readonly SourceIdentifier[];
  readonly sourceRights: SourceIdentityRights;
  readonly matchedIdentifier: MatchedSourceIdentifier;
  readonly sourceInputIndexSha256: Sha256;
  readonly rightsVisibilityField: 'sourceVisibility' | 'visibility';
  readonly sourceURL: 'https://fdc.nal.usda.gov/download-datasets/';
  readonly originalProductName: UnknownIdentityField;
  readonly originalLanguage: UnknownIdentityField;
  readonly englishName: UnknownIdentityField;
  readonly foodType: UnknownIdentityField;
  readonly nutrition: UnknownIdentityField;
  readonly canonicalIdentityAccepted: false;
  readonly identityAssociationAccepted: false;
  readonly physicalProductEquivalenceAsserted: false;
  readonly normalizationComplete: false;
  readonly goldAdmitted: false;
  readonly automaticPlanningEligible: false;
  readonly recipeNutritionJoinsAccepted: false;
}
export interface SourceIdentityReaderResult {
  readonly status: 'source-identity-claims-found' | 'no-selected-source-identity';
  readonly sourceId: 'usda-files';
  readonly namespace: SourceIdentityNamespace;
  readonly lexicalValue: string;
  readonly manifestSha256: Sha256;
  readonly totalSourceObservations: number;
  readonly nextOffset: number | null;
  readonly records: readonly SourceIdentityObservation[];
  readonly externalFallback: false;
  readonly publicPublicationAccepted: false;
  readonly normalizationComplete: false;
  readonly goldAdmitted: false;
}
export interface SourceIdentityHTTPSuccess {
  readonly schema: 'offmenu-source-identity-http/1';
  readonly kind: 'source-identifier-claims';
  readonly httpStatus: 200;
  readonly selectionSha256: Sha256;
  readonly admissionSha256: Sha256;
  readonly readerResult: SourceIdentityReaderResult;
}
export interface SourceIdentityHTTPError {
  readonly schema: 'offmenu-source-identity-http/1';
  readonly error: 'source-identity-origin-not-allowed' | 'source-identity-method-not-allowed' |
    'invalid-source-identity-request' | 'source-identity-service-unavailable';
}
export type SourceIdentityHTTPBody = SourceIdentityHTTPSuccess | SourceIdentityHTTPError;

/** Minimum existing phase-reader boundary, not a replacement phase validator. */
export interface QualifiedPhaseRecordForComposition {
  readonly provenance: Omit<SourceSubject, 'sourceId'> & {readonly sourceId: string};
  readonly data: {readonly foundationComplete: true};
}
export type QualifiedPhaseResultForComposition = {
  readonly fieldContract: 'offmenu-barcode-foundation-phase/2';
  readonly manifestSha256: Sha256;
  readonly source: string;
  readonly barcode: string;
  readonly externalFallback: false;
} & ({
  readonly status: 'phase-qualified-own-data';
  readonly httpStatus: 200;
  readonly records: readonly QualifiedPhaseRecordForComposition[];
} | {
  readonly status: 'own-data-unavailable';
  readonly httpStatus: 503;
  readonly records: readonly [];
});
export interface OwnDataObservationComposition<TPhase extends QualifiedPhaseResultForComposition> {
  readonly schema: 'offmenu-own-data-observation-composition/1';
  readonly sourceId: 'usda-files';
  readonly namespace: 'barcode';
  readonly lexicalValue: string;
  readonly phaseResult: TPhase;
  readonly sourceIdentityClaims: readonly SourceIdentityObservation[];
  readonly sourceIdentityManifestSha256: Sha256;
  readonly sourceClaimsSuppressedForQualifiedSubject: number;
  readonly sourceIdentityClaimsCanonical: false;
  readonly externalFallback: false;
}
