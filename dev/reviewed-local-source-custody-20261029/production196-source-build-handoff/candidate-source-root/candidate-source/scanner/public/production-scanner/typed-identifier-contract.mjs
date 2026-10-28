/**
 * Pure reference contract. No I/O, catalogue lookup, allocation inference or rewrite.
 * `checksum-valid` means only that the explicitly selected representation validates.
 * Keep the caller's complete source observation reference beside this interpretation.
 */
export const CONTRACT_VERSION = 'offmenu-typed-identifier/1';
export const CITATIONS = Object.freeze({
  upce: 'https://ref.gs1.org/guidelines/2d-in-retail/1.0.0/',
  jan: 'https://www.gs1jp.org/standard/barcode/jan_symbol.html',
  itf14: 'https://support.gs1.org/support/solutions/articles/43000734528-what-type-of-gtin-can-be-encoded-in-itf-14-',
  packaging: 'https://www.gs1uk.org/knowledge-hub/product-identification/how-do-i-identify-packaging-levels',
  isbnGS1: 'https://support.gs1.org/support/solutions/articles/43000734165-how-is-an-isbn-used-in-a-gs1-barcode-',
  isbnAgency: 'https://www.isbn-international.org/content/what-isbn/10',
});
export const REPRESENTATIONS = Object.freeze([
  'GTIN-8', 'GTIN-12', 'GTIN-13', 'GTIN-14', 'EAN-8', 'EAN-13',
  'UPC-A', 'UPC-E', 'JAN', 'JAN-8', 'JAN-13', 'ISBN-10', 'ISBN-13',
]);

const WIDTH = Object.freeze({'GTIN-8':8, 'EAN-8':8, 'GTIN-12':12,
  'UPC-A':12, 'GTIN-13':13, 'EAN-13':13, 'GTIN-14':14});
const CARRIER_HINT = Object.freeze({
  'EAN-8':'EAN-8', EAN8:'EAN-8', ean_8:'EAN-8',
  'EAN-13':'EAN-13', EAN13:'EAN-13', ean_13:'EAN-13',
  'UPC-A':'UPC-A', UPCA:'UPC-A', upc_a:'UPC-A',
  'UPC-E':'UPC-E', UPCE:'UPC-E', upc_e:'UPC-E',
  'ITF-14':'GTIN-14', ITF14:'GTIN-14',
});
const digits = value => typeof value === 'string' && /^[0-9]+$/.test(value);
function checkDigit(body) {
  let sum = 0;
  for (let i = body.length - 1, weight = 3; i >= 0; i--, weight = 4 - weight)
    sum += Number(body[i]) * weight;
  return String((10 - sum % 10) % 10);
}

/** Numeric syntax/checksum only; never evidence of a physical carrier or assignment. */
export function validateGTIN(value) {
  return digits(value) && [8,12,13,14].includes(value.length) &&
    checkDigit(value.slice(0,-1)) === value.at(-1);
}
export function validateISBN10(value) {
  if (typeof value !== 'string' || !/^[0-9]{9}[0-9X]$/.test(value)) return false;
  let sum = 0;
  for (let i = 0; i < 10; i++) sum += (value[i] === 'X' ? 10 : Number(value[i])) * (10-i);
  return sum % 11 === 0;
}
export function validateISBN13(value) {
  return typeof value === 'string' && /^(978|979)[0-9]{10}$/.test(value) && validateGTIN(value);
}

/** Explicit UPC-E interpretation only. An eight-digit value alone is not UPC-E. */
export function expandUPCE(value) {
  if (typeof value !== 'string' || !/^[01][0-9]{7}$/.test(value)) return null;
  const [n,a,b,c,d,e,f,k] = value;
  const expanded = f <= '2' ? n+a+b+f+'0000'+c+d+e+k :
    f === '3' ? n+a+b+c+'00000'+d+e+k :
    f === '4' ? n+a+b+c+d+'00000'+e+k : n+a+b+c+d+e+'0000'+f+k;
  return validateGTIN(expanded) ? expanded : null;
}

export function isbn10To13(value) {
  if (!validateISBN10(value)) return null;
  const body = '978'+value.slice(0,9);
  return body+checkDigit(body);
}
/** `no-equivalent` is distinct from invalid ISBN syntax/checksum. */
export function isbn13To10(value) {
  if (!validateISBN13(value)) return Object.freeze({status:'invalid', value:null, allocationStatus:'not-verified'});
  if (value.startsWith('979')) return Object.freeze({status:'no-equivalent', value:null, allocationStatus:'not-verified'});
  const body = value.slice(3,12);
  let sum = 0;
  for (let i = 0; i < 9; i++) sum += Number(body[i]) * (10-i);
  const k = (11 - sum % 11) % 11;
  return Object.freeze({status:'converted', value:body+(k === 10 ? 'X' : String(k)), allocationStatus:'not-verified'});
}

/** Naming, not manufacturing country or a new physical carrier. No length inference. */
export function janNaming(hint) {
  if (hint === 'JAN-8') return Object.freeze({naming:'JAN-8', representation:'EAN-8', countryOfManufacture:null});
  if (hint === 'JAN-13') return Object.freeze({naming:'JAN-13', representation:'EAN-13', countryOfManufacture:null});
  if (hint === 'JAN') return Object.freeze({naming:'JAN', representation:null, countryOfManufacture:null});
  return null;
}
/** A caller-supplied decoder label is not verified physical-camera evidence here. */
export function representationFromCarrier(carrier) {
  return typeof carrier === 'string' && Object.hasOwn(CARRIER_HINT, carrier) ? CARRIER_HINT[carrier] : null;
}
function family(hint) {
  return hint === 'UPC-E' ? 'UPC-E' : hint === 'ISBN-10' ? 'ISBN-10' :
    hint === 'ISBN-13' ? 13 : WIDTH[hint] ?? null;
}
function nullableString(value, name) {
  if (value == null) return null;
  if (typeof value !== 'string') throw new TypeError(name+' must be a string or null');
  return value;
}
function freezeResult(result) {
  result.labelledEquivalents = Object.freeze(result.labelledEquivalents.map(Object.freeze));
  result.possibleRepresentations = Object.freeze(result.possibleRepresentations.map(Object.freeze));
  return Object.freeze(result);
}

/**
 * @param {{original:string, namespace:string, sourceLexicalValue?:string|null,
 * sourceId?:string|null, representationHint?:string|null, observedCarrier?:string|null}} input
 * @returns {Readonly<object>} See the adjacent .d.ts for the precise result shape.
 * The namespace is caller-owned and is never inferred, trimmed, rewritten or merged.
 */
export function analyzeIdentifier(input) {
  if (!input || typeof input !== 'object' || Array.isArray(input)) throw new TypeError('input must be an object');
  if (typeof input.original !== 'string' || !input.original.length) throw new TypeError('original must be a nonempty string');
  if (typeof input.namespace !== 'string' || !input.namespace.length) throw new TypeError('namespace must be explicit and nonempty');
  const hint = nullableString(input.representationHint, 'representationHint');
  const carrier = nullableString(input.observedCarrier, 'observedCarrier');
  const naming = janNaming(hint);
  const carrierHint = representationFromCarrier(carrier);
  const effective = naming ? naming.representation : hint ?? carrierHint;
  const result = {
    contractVersion:CONTRACT_VERSION,
    original:input.original, namespace:input.namespace,
    sourceLexicalValue:nullableString(input.sourceLexicalValue, 'sourceLexicalValue'),
    sourceId:nullableString(input.sourceId, 'sourceId'),
    lookupOriginal:input.original, lookupContract:'caller-owned',
    requestedHint:hint, effectiveHint:effective, observedCarrier:carrier,
    hintOrigin:hint !== null ? 'explicit' : carrierHint ? 'decoder-label' : 'none',
    namingRelationship:naming, countryOfManufacture:null,
    status:'untyped', reason:'explicit-representation-required', syntaxValid:null,
    checksumValid:null, validatedRepresentation:null, comparisonGTIN14:null,
    gtin14LeadingDigit:null, packagingRelationship:'not-established',
    labelledEquivalents:[], possibleRepresentations:[],
    isbn10Equivalent:null, isbn10Availability:'not-applicable',
    allocationStatus:'not-verified', catalogueStatus:'not-queried',
    physicalCarrierStatus:carrier === null ? 'unobserved' : 'caller-label-only',
    productIdentityAsserted:false, ingredientClassification:'not-assessed',
  };
  const done = () => freezeResult(result);
  const add = (value, representation, rule) => {
    if (value !== input.original && !result.labelledEquivalents.some(x => x.value === value && x.representation === representation))
      result.labelledEquivalents.push({value, representation, rule});
  };
  if (hint !== null && !REPRESENTATIONS.includes(hint)) {
    result.status='invalid'; result.reason='unsupported-representation-hint'; return done();
  }
  if (hint === 'JAN') {
    result.status='hint-required'; result.reason='choose-JAN-8-or-JAN-13-explicitly'; return done();
  }
  if (effective === null) {
    if (carrier === 'ITF' || carrier === 'itf') result.reason='generic-ITF-does-not-declare-GTIN';
    else if (/^[0-9]{8}$/.test(input.original)) {
      result.status='ambiguous'; result.reason='eight-digits-do-not-select-EAN-8-or-UPC-E';
      result.possibleRepresentations=[
        {representation:'EAN-8', checksumCompatible:validateGTIN(input.original)},
        {representation:'UPC-E', checksumCompatible:expandUPCE(input.original) !== null},
      ];
    }
    return done();
  }
  if (hint !== null && carrierHint && family(effective) !== family(carrierHint)) {
    result.status='conflict'; result.reason='explicit-hint-conflicts-with-decoder-label'; return done();
  }
  let gtin = null;
  if (effective === 'ISBN-10') {
    result.syntaxValid=/^[0-9]{9}[0-9X]$/.test(input.original);
    result.checksumValid=result.syntaxValid ? validateISBN10(input.original) : null;
    if (result.checksumValid) {
      gtin=isbn10To13(input.original); result.validatedRepresentation='ISBN-10';
      result.isbn10Equivalent=input.original; result.isbn10Availability='original';
      add(gtin,'ISBN-13','validated-ISBN-10-to-978-ISBN-13');
    }
  } else if (effective === 'ISBN-13') {
    result.syntaxValid=/^(978|979)[0-9]{10}$/.test(input.original);
    result.checksumValid=result.syntaxValid ? validateISBN13(input.original) : null;
    if (result.checksumValid) {
      gtin=input.original; result.validatedRepresentation='ISBN-13';
      const converted=isbn13To10(input.original);
      result.isbn10Availability=converted.status; result.isbn10Equivalent=converted.value;
      if (converted.value) add(converted.value,'ISBN-10','validated-978-ISBN-13-to-ISBN-10');
    }
  } else if (effective === 'UPC-E') {
    result.syntaxValid=/^[01][0-9]{7}$/.test(input.original);
    gtin=result.syntaxValid ? expandUPCE(input.original) : null;
    result.checksumValid=result.syntaxValid ? gtin !== null : null;
    if (gtin) {
      result.validatedRepresentation='UPC-E';
      add(gtin,'GTIN-12','explicit-UPC-E-to-GTIN-12');
      add('0'+gtin,'EAN-13','GTIN-12-as-leading-zero-EAN-13');
    }
  } else {
    const width=WIDTH[effective];
    result.syntaxValid=!!width && digits(input.original) && input.original.length === width;
    result.checksumValid=result.syntaxValid ? validateGTIN(input.original) : null;
    if (result.checksumValid) {
      gtin=input.original; result.validatedRepresentation='GTIN-'+width;
      if (width === 12) add('0'+gtin,'EAN-13','GTIN-12-as-leading-zero-EAN-13');
      if (width === 13 && gtin.startsWith('0')) add(gtin.slice(1),'GTIN-12','leading-zero-EAN-13-as-GTIN-12');
      if (width === 14) result.gtin14LeadingDigit=gtin[0];
    }
  }
  if (!result.checksumValid) {
    result.status='invalid'; result.reason=result.syntaxValid ? 'checksum-invalid' : 'representation-syntax-invalid';
    return done();
  }
  result.status='checksum-valid'; result.reason='typed-syntax-and-checksum-only';
  result.comparisonGTIN14=gtin.padStart(14,'0');
  return done();
}
