import {analyzeIdentifier, expandUPCE, validateGTIN} from './typed-identifier-contract.mjs';

export const CAPTURE_SCHEMA = 'offmenu-decoder-capture/1';
const EXTRA_LIMIT = 8192;
const CODE_LIMIT = 128;
const FORMAT = Object.freeze({
  ean_13:'EAN-13', EAN13:'EAN-13', 'EAN-13':'EAN-13',
  ean_8:'EAN-8', EAN8:'EAN-8', 'EAN-8':'EAN-8',
  upc_a:'UPC-A', UPCA:'UPC-A', 'UPC-A':'UPC-A',
  upc_e:'UPC-E', UPCE:'UPC-E', 'UPC-E':'UPC-E',
  ITF:'ITF', itf:'ITF', 'ITF-14':'ITF', ITF14:'ITF',
});

// Preserve the decoder's own strings. In particular, ZXing's `text` is not
// renamed as the compressed UPC-E printed value.
export function projectZXingResult(result) {
  return {text:result?.text, format:result?.format, error:result?.error ?? null,
    extra:result?.extra ?? null};
}

function extraUPCE(raw) {
  if (raw == null || raw === '') return {value:null,state:'absent'};
  if (typeof raw !== 'string' || raw.length > EXTRA_LIMIT) return {value:null,state:'unsupported-or-oversize'};
  try {
    const parsed=JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed) ||
        typeof parsed.UPCE !== 'string') return {value:null,state:'no-UPCE'};
    return {value:parsed.UPCE,state:'present'};
  } catch {return {value:null,state:'invalid-json'};}
}

export function captureFromDecoder(result, decoderPath) {
  const decoderText=result?.rawValue ?? result?.text;
  const returnedFormat=result?.format ?? null;
  const carrier=typeof returnedFormat === 'string' ? FORMAT[returnedFormat] ?? null : null;
  const rawExtra=result?.extra ?? null, upce=extraUPCE(rawExtra);
  const envelope={schema:CAPTURE_SCHEMA,namespace:'barcode',decoderPath,
    decoderText:typeof decoderText === 'string' ? decoderText : null,
    returnedFormat,rawExtra,extraState:upce.state,extraUPCE:upce.value,
    labelledDerived:null,
    lookupLexicalValue:null,lookupSymbology:null,lookupOrigin:null,
    typed:null,status:'manual-required',reason:'decoder-result-unavailable'};
  const finish=(status,reason,lexical=null,hint=null,origin=null)=>{
    envelope.status=status;envelope.reason=reason;
    envelope.lookupLexicalValue=lexical;envelope.lookupSymbology=hint;envelope.lookupOrigin=origin;
    if (lexical) envelope.typed=analyzeIdentifier({original:lexical,namespace:'barcode',
      representationHint:hint,observedCarrier:carrier === 'ITF' ? 'ITF' : returnedFormat});
    return envelope;
  };
  if (result?.error || typeof decoderText !== 'string' || !decoderText.length ||
      decoderText.length>CODE_LIMIT || /[\x00-\x1f\x7f]/.test(decoderText))
    return finish('manual-required','decoder-text-unavailable-or-out-of-bounds');
  if (rawExtra !== null && rawExtra !== undefined &&
      (typeof rawExtra !== 'string' || rawExtra.length > EXTRA_LIMIT))
    return finish('manual-required','decoder-extra-unavailable-or-out-of-bounds');
  if (!carrier) return finish('unsupported','decoder-format-not-enabled');
  if (carrier === 'ITF') return finish('literal-untyped','generic-ITF-does-not-declare-GTIN',
    decoderText,null,'decoder-text');
  if (carrier === 'UPC-E') {
    if (decoderText.length === 8) {
      const expanded=expandUPCE(decoderText);
      if (!expanded) return finish('manual-required','UPC-E-syntax-or-checksum-invalid');
      if (upce.value !== null && upce.value !== decoderText)
        return finish('manual-required','UPC-E-extra-conflicts-with-decoder-text');
      if (upce.state === 'unsupported-or-oversize' || upce.state === 'invalid-json')
        return finish('manual-required','UPC-E-extra-unreadable');
      return finish('ready','validated-compressed-UPC-E',decoderText,'UPC-E','decoder-text');
    }
    if (decoderText.length !== 12 && decoderText.length !== 13)
      return finish('manual-required','normalized-UPC-E-text-has-unsupported-width');
    if (upce.state !== 'present') return finish('manual-required','compressed-UPC-E-extra-missing');
    const expanded=expandUPCE(upce.value);
    if (!expanded || decoderText !== expanded && decoderText !== '0'+expanded)
      return finish('manual-required','UPC-E-extra-conflicts-with-normalized-text');
    return finish('ready','validated-UPC-E-extra-against-normalized-text',
      upce.value,'UPC-E','validated-decoder-extra.UPCE');
  }
  if (carrier === 'UPC-A' && decoderText.length === 13 && decoderText.startsWith('0') &&
      validateGTIN(decoderText)) {
    envelope.labelledDerived={value:decoderText.slice(1),representation:'UPC-A',
      rule:'leading-zero-EAN-13-to-UPC-A; printed original unverified'};
    return finish('ready','UPC-A-decoder-returned-leading-zero-EAN-13-text',
      decoderText,null,'decoder-returned-13-digit-form; printed-original-unverified');
  }
  const width=carrier === 'UPC-A' ? 12 : carrier === 'EAN-13' ? 13 : 8;
  if (decoderText.length !== width || !validateGTIN(decoderText))
    return finish('manual-required','decoder-representation-syntax-or-checksum-invalid');
  return finish('ready','validated-decoder-text',decoderText,carrier,'decoder-text');
}

// A candidate is identified by its exact lookup representation, not by a
// checksum-derived equivalent or by a decoder's possibly normalized text.
export function selectableCaptures(results,decoderPath) {
  return (results||[]).map(result=>captureFromDecoder(result,decoderPath))
    .filter(capture=>capture.status==='ready');
}

export function requiresUPCEConfirmation(results,decoderPath) {
  return (results||[]).some(result=>{
    const capture=captureFromDecoder(result,decoderPath);
    return capture.returnedFormat!==null && FORMAT[capture.returnedFormat]==='UPC-E' &&
      capture.status==='manual-required';
  });
}

export function captureEvidence(capture) {
  if (capture?.schema!==CAPTURE_SCHEMA || capture.status!=='ready') return null;
  return {schema:CAPTURE_SCHEMA,decoderPath:capture.decoderPath,
    decoderText:capture.decoderText,returnedFormat:capture.returnedFormat,
    rawExtra:capture.rawExtra,lookupLexicalValue:capture.lookupLexicalValue,
    lookupSymbology:capture.lookupSymbology,lookupOrigin:capture.lookupOrigin,
    labelledDerived:capture.labelledDerived};
}

export function verifyCaptureEvidence(evidence,raw,hint) {
  if (evidence==null) return true;
  if (evidence.schema!==CAPTURE_SCHEMA ||
      !['native','zxing-wasm','photo-zxing-wasm'].includes(evidence.decoderPath)) return false;
  const rederived=captureFromDecoder({text:evidence.decoderText,
    format:evidence.returnedFormat,extra:evidence.rawExtra},evidence.decoderPath);
  return rederived.status==='ready' && rederived.lookupLexicalValue===raw &&
    rederived.lookupSymbology===hint && rederived.lookupOrigin===evidence.lookupOrigin &&
    JSON.stringify(rederived.labelledDerived)===JSON.stringify(evidence.labelledDerived);
}
