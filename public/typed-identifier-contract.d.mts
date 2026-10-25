export type RepresentationHint = 'GTIN-8'|'GTIN-12'|'GTIN-13'|'GTIN-14'|
  'EAN-8'|'EAN-13'|'UPC-A'|'UPC-E'|'JAN'|'JAN-8'|'JAN-13'|'ISBN-10'|'ISBN-13';
export interface IdentifierInput {
  original: string;
  namespace: string;
  sourceLexicalValue?: string|null;
  sourceId?: string|null;
  representationHint?: RepresentationHint|null;
  observedCarrier?: string|null;
}
export interface NamingRelationship {
  readonly naming: 'JAN'|'JAN-8'|'JAN-13';
  readonly representation: 'EAN-8'|'EAN-13'|null;
  readonly countryOfManufacture: null;
}
export interface IdentifierAnalysis {
  readonly contractVersion: 'offmenu-typed-identifier/1';
  readonly original: string;
  readonly namespace: string;
  readonly sourceLexicalValue: string|null;
  readonly sourceId: string|null;
  readonly lookupOriginal: string;
  readonly lookupContract: 'caller-owned';
  readonly requestedHint: RepresentationHint|null;
  readonly effectiveHint: RepresentationHint|null;
  readonly observedCarrier: string|null;
  readonly hintOrigin: 'explicit'|'decoder-label'|'none';
  readonly namingRelationship: NamingRelationship|null;
  readonly countryOfManufacture: null;
  readonly status: 'untyped'|'invalid'|'hint-required'|'ambiguous'|'conflict'|'checksum-valid';
  readonly reason: string;
  readonly syntaxValid: boolean|null;
  readonly checksumValid: boolean|null;
  readonly validatedRepresentation: string|null;
  readonly comparisonGTIN14: string|null;
  readonly gtin14LeadingDigit: string|null;
  readonly packagingRelationship: 'not-established';
  readonly labelledEquivalents: readonly Readonly<{value:string;representation:string;rule:string}>[];
  readonly possibleRepresentations: readonly Readonly<{representation:'EAN-8'|'UPC-E';checksumCompatible:boolean}>[];
  readonly isbn10Equivalent: string|null;
  readonly isbn10Availability: 'not-applicable'|'original'|'converted'|'no-equivalent';
  readonly allocationStatus: 'not-verified';
  readonly catalogueStatus: 'not-queried';
  readonly physicalCarrierStatus: 'unobserved'|'caller-label-only';
  readonly productIdentityAsserted: false;
  readonly ingredientClassification: 'not-assessed';
}
export const CONTRACT_VERSION: 'offmenu-typed-identifier/1';
export const CITATIONS: Readonly<Record<'upce'|'jan'|'itf14'|'packaging'|'isbnGS1'|'isbnAgency',string>>;
export const REPRESENTATIONS: readonly RepresentationHint[];
export function validateGTIN(value: unknown): boolean;
export function validateISBN10(value: unknown): boolean;
export function validateISBN13(value: unknown): boolean;
export function expandUPCE(value: unknown): string|null;
export function isbn10To13(value: unknown): string|null;
export function isbn13To10(value: unknown): Readonly<
  {status:'converted';value:string;allocationStatus:'not-verified'} |
  {status:'invalid'|'no-equivalent';value:null;allocationStatus:'not-verified'}>;
export function janNaming(hint: unknown): NamingRelationship|null;
export function representationFromCarrier(carrier: unknown): RepresentationHint|null;
export function analyzeIdentifier(input: IdentifierInput): Readonly<IdentifierAnalysis>;
