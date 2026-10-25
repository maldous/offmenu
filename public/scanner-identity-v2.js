// Off-live UI adapter for the staged identity-search-plan-v2 contract.
// This file is not loaded by the 7645 scanner until source review and owner activation.
export const IDENTIFIER_DB = '97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0';
export const IDENTIFIER_RUN = 'worker57-full-retained-identifiers-v1';
export const DETAIL_SELECTION = 'd9a08c3b2b9eec880418b8108d60c177a253b53802e8ea0453eb8fd502498290';
const DISPOSITIONS = new Set(['source-asserted', 'unresolved', 'invalid']);
const SYMBOLOGIES = new Set(['EAN-13', 'EAN-8', 'UPC-A', 'UPC-E', 'GTIN-14']);
const KEY = ['run_id', 'input_id', 'record_ordinal', 'assertion_id'];
const bounded = (value, max) => typeof value === 'string' && value.length > 0 && value.length <= max;

export function validGTIN(value) {
  if (!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(value)) return false;
  let sum = 0;
  for (let i = value.length - 2, weight = 3; i >= 0; i--, weight = 4 - weight) sum += Number(value[i]) * weight;
  return (10 - sum % 10) % 10 === Number(value.at(-1));
}

export function expectedForms(original, symbology = null) {
  const forms = [{lexicalValue: original, matchType: 'exact', equivalence: null}];
  const add = (lexicalValue, equivalence) => {
    if (!forms.some(form => form.lexicalValue === lexicalValue)) forms.push({lexicalValue, matchType: 'representation-alias', equivalence});
  };
  let expanded = original;
  if (symbology === 'UPC-E') {
    if (!/^[01]\d{7}$/.test(original)) return forms;
    const [n, a, b, c, d, e, f, k] = original;
    expanded = f <= '2' ? n+a+b+f+'0000'+c+d+e+k : f === '3' ? n+a+b+c+'00000'+d+e+k : f === '4' ? n+a+b+c+d+'00000'+e+k : n+a+b+c+d+e+'0000'+f+k;
    if (!validGTIN(expanded)) return forms;
    add(expanded, 'explicit-upc-e-to-upc-a');
  }
  if (!validGTIN(expanded)) return forms;
  if (expanded.length === 12 && (!symbology || symbology === 'UPC-A' || symbology === 'UPC-E')) add('0'+expanded, 'upc-a-as-leading-zero-ean-13');
  else if (expanded.length === 13 && expanded[0] === '0' && (!symbology || symbology === 'EAN-13')) add(expanded.slice(1), 'leading-zero-ean-13-as-upc-a');
  return forms;
}

function status(matches, hasMore, partial) {
  if (partial) return 'partial';
  if (!matches.length) return hasMore ? 'searching' : 'scoped-miss';
  return matches.length > 1 || hasMore ? 'ambiguous' : 'source-match';
}

export function projectIdentityPage(data, original, generation, {symbology = null, requestCursor = null} = {}) {
  if (!bounded(original, 128) || /[\x00-\x1f\x7f]/.test(original) || symbology !== null && !SYMBOLOGIES.has(symbology)) throw Error('Invalid original capture');
  if (data?.databaseSha256 !== IDENTIFIER_DB || data.generation !== String(generation) || data.identitySearchPlanVersion !== 2 ||
      data.operation !== 'identifier-search' || !Array.isArray(data.rows) || data.rows.length > 25 ||
      !Array.isArray(data.identityMatches) || data.identityMatches.length !== data.rows.length ||
      data.identityQuery?.namespace !== 'barcode' || data.identityQuery.originalLexicalValue !== original ||
      (data.identityQuery.symbology ?? null) !== symbology || !['available', 'partial'].includes(data.identitySearchState) ||
      typeof data.hasMore !== 'boolean' || (data.hasMore && !bounded(data.nextCursor, 8192)) ||
      (!data.hasMore && data.nextCursor !== null)) throw Error('Selected identifier page binding mismatch');
  const forms = expectedForms(original, symbology);
  if (JSON.stringify(data.identityQuery.forms) !== JSON.stringify(forms)) throw Error('Representation plan mismatch');
  const coverage = data.identitySearchCoverage;
  if (!coverage || coverage.physicalProductIdentityAsserted !== false || coverage.ingredientQualificationAsserted !== false ||
      !Array.isArray(coverage.failures) || data.identitySearchState === 'partial' && !coverage.failures.length ||
      (!data.hasMore && coverage.state !== 'complete-for-selected-index-and-query-plan' && data.identitySearchState !== 'partial'))
    throw Error('Selected coverage binding mismatch');
  const matches = data.rows.map((row, index) => {
    const match = data.identityMatches[index];
    const form = forms.find(item => item.lexicalValue === row?.lexical_value);
    if (!row || row.namespace !== 'barcode' || !DISPOSITIONS.has(row.disposition) ||
        !Number.isSafeInteger(row.assertion_id) || row.assertion_id <= 0 ||
        !form || match?.assertionId !== row.assertion_id || match.sourceLexicalValue !== row.lexical_value ||
        match.matchType !== form.matchType || match.equivalence !== form.equivalence ||
        match.disposition !== row.disposition) throw Error('Source observation or alias binding mismatch');
    return {id:'identifier-assertion:'+row.assertion_id, identifier:row,
      sourceRecordId:row.source_record_id, nativeRecordId:row.native_record_id,
      provenance:{sourceId:row.source_id, releaseId:row.release_id},
      matchContext:{originalLexicalValue:original, sourceLexicalValue:row.lexical_value,
        symbology, matchType:form.matchType, equivalence:form.equivalence, disposition:row.disposition},
      availability:null, detail:null, variants:[], name:null, brand:null, ingredientsText:null};
  });
  return {generation, original, symbology, requestCursor, status:status(matches, data.hasMore, data.identitySearchState === 'partial'),
    searchState:data.identitySearchState, searchCoverage:coverage, hasMore:data.hasMore, nextCursor:data.nextCursor,
    databaseSha256:IDENTIFIER_DB, runId:IDENTIFIER_RUN, matches,
    detailsState:data.details?.state || 'not-requested', detailReasonCode:data.details?.error?.reasonCode || null};
}

export function mergeIdentityPages(previous, next) {
  if (!previous?.hasMore || previous.nextCursor !== next?.requestCursor ||
      previous.original !== next.original || previous.symbology !== next.symbology ||
      previous.databaseSha256 !== next.databaseSha256 || previous.runId !== next.runId) throw Error('Continuation binding mismatch');
  const seen = new Set(previous.matches.map(item => [item.identifier.assertion_id, item.identifier.lexical_value, item.identifier.disposition].join('|')));
  for (const match of next.matches) {
    const key = [match.identifier.assertion_id, match.identifier.lexical_value, match.identifier.disposition].join('|');
    if (seen.has(key)) throw Error('Repeated source observation across pages');
    seen.add(key);
  }
  // A later successful page can resume the previously failed lane.
  const matches = [...previous.matches, ...next.matches], partial = next.searchState === 'partial';
  return {...next, matches, searchState:partial ? 'partial' : next.searchState, status:status(matches, next.hasMore, partial)};
}

export function sourceObservationReference(match, page) {
  const row = match?.identifier, context = match?.matchContext;
  if (!row || !context || page?.databaseSha256 !== IDENTIFIER_DB || page.original !== context.originalLexicalValue)
    throw Error('Source observation not selected');
  const ref = {schema:'offmenu-identifier-observation/2', databaseSha256:page.databaseSha256, runId:page.runId,
    namespace:row.namespace, originalLexicalValue:context.originalLexicalValue,
    sourceLexicalValue:row.lexical_value, symbology:context.symbology,
    matchType:context.matchType, equivalence:context.equivalence, disposition:row.disposition,
    sourceId:row.source_id, releaseId:row.release_id ?? null, sourceRecordId:row.source_record_id ?? null,
    observationKey:Object.fromEntries(KEY.map(key => [key, row[key]])), detailSelectionSha256:DETAIL_SELECTION};
  if (!validSourceObservationReference(ref, page.original)) throw Error('Source observation reference incomplete');
  return ref;
}

export function validSourceObservationReference(ref, original) {
  const key = ref?.observationKey;
  const form = expectedForms(original, ref?.symbology).find(item => item.lexicalValue === ref?.sourceLexicalValue);
  return ref?.schema === 'offmenu-identifier-observation/2' && ref.databaseSha256 === IDENTIFIER_DB &&
    ref.runId === IDENTIFIER_RUN && ref.namespace === 'barcode' && ref.originalLexicalValue === original &&
    bounded(ref.sourceId, 40) && (ref.releaseId === null || bounded(ref.releaseId, 80)) &&
    (ref.sourceRecordId === null || bounded(ref.sourceRecordId, 200)) &&
    (ref.symbology === null || SYMBOLOGIES.has(ref.symbology)) && DISPOSITIONS.has(ref.disposition) &&
    form?.matchType === ref.matchType && form?.equivalence === ref.equivalence &&
    key?.run_id === ref.runId && bounded(key.input_id, 250) &&
    Number.isSafeInteger(key.record_ordinal) && key.record_ordinal >= 0 &&
    Number.isSafeInteger(key.assertion_id) && key.assertion_id > 0 &&
    ref.detailSelectionSha256 === DETAIL_SELECTION;
}

export function exactDetailRequest(ref, generation) {
  if (!validSourceObservationReference(ref, ref?.originalLexicalValue)) throw Error('Selected observation changed');
  return {namespace:'barcode', lexical_value:ref.originalLexicalValue, symbology:ref.symbology ?? undefined,
    generation:String(generation), databaseSha256:IDENTIFIER_DB, limit:1, cursor:null,
    include:['retained-product-federation-v1'], detailAssertionId:ref.observationKey.assertion_id,
    detailLexicalValue:ref.sourceLexicalValue, detailDisposition:ref.disposition};
}

export async function lookupIdentityPage(original, generation, {cursor = null, symbology = null, fetchImpl = fetch} = {}) {
  try {
    const statusResponse = await fetchImpl('/__dev/identifiers/status', {cache:'no-store'});
    const selected = await statusResponse.json();
    if (!statusResponse.ok || !selected.queryAvailable || selected.identitySearchPlanVersion !== 2 ||
        selected.databaseSha256 !== IDENTIFIER_DB || selected.runId !== IDENTIFIER_RUN ||
        selected.detailSelectionSha256 !== DETAIL_SELECTION) throw Error('Selected identity release unavailable');
    const request = {namespace:'barcode', lexical_value:original, limit:25, cursor,
      generation:String(generation), databaseSha256:IDENTIFIER_DB,
      ...(symbology ? {symbology} : {})};
    const response = await fetchImpl('/__dev/identifiers', {method:'POST', cache:'no-store',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify(request)});
    const data = await response.json();
    if (!response.ok || data.error) throw Error(data.error || 'Selected identifier page unavailable');
    return projectIdentityPage(data, original, generation, {symbology, requestCursor:cursor});
  } catch (error) {
    return {generation, original, symbology, requestCursor:cursor, status:'unavailable',
      matches:[], error:error.message, hasMore:false, nextCursor:null};
  }
}

export async function lookupExactObservationDetail(ref, generation, {fetchImpl = fetch} = {}) {
  if (!validSourceObservationReference(ref, ref?.originalLexicalValue))
    return {status:'detail-unavailable', sourceObservationReference:ref, error:'Selected source reference invalid'};
  try {
    const statusResponse = await fetchImpl('/__dev/identifiers/status', {cache:'no-store'});
    const selected = await statusResponse.json();
    if (!statusResponse.ok || !selected.queryAvailable || selected.identitySearchPlanVersion !== 2 ||
        selected.databaseSha256 !== IDENTIFIER_DB || selected.runId !== IDENTIFIER_RUN ||
        selected.detailSelectionSha256 !== DETAIL_SELECTION) throw Error('Selected detail release unavailable');
    const response = await fetchImpl('/__dev/identifiers', {method:'POST', cache:'no-store',
      headers:{'Content-Type':'application/json'}, body:JSON.stringify(exactDetailRequest(ref, generation))});
    const data = await response.json();
    if (!response.ok || data.error) throw Error(data.error || 'Exact source detail unavailable');
    if (data.databaseSha256 !== IDENTIFIER_DB || data.generation !== String(generation) ||
        data.operation !== 'observation-detail' || !Array.isArray(data.rows) || data.rows.length > 1 ||
        !Array.isArray(data.identityMatches) || data.identityMatches.length !== data.rows.length)
      throw Error('Exact source detail binding mismatch');
    const row = data.rows[0];
    if (!row) return {status:'source-stale', sourceObservationReference:ref,
      error:data.details?.error?.reasonCode || 'NO_CURRENT_SELECTED_OBSERVATION'};
    const key = ref.observationKey, match = data.identityMatches[0];
    if (row.namespace !== ref.namespace || row.lexical_value !== ref.sourceLexicalValue ||
        row.disposition !== ref.disposition || row.source_id !== ref.sourceId ||
        (row.release_id ?? null) !== ref.releaseId || KEY.some(field => row[field] !== key[field]) ||
        match.assertionId !== row.assertion_id || match.sourceLexicalValue !== row.lexical_value ||
        match.disposition !== ref.disposition || match.matchType !== ref.matchType ||
        match.equivalence !== ref.equivalence) throw Error('Exact source detail row mismatch');
    const details = data.details;
    if (!details || details.detailSelectionSha256 !== DETAIL_SELECTION ||
        details.detailBackend !== 'retained-product-federation-v1' ||
        !Array.isArray(details.sourceProducts) || details.sourceProducts.some(product =>
          product?.observationKey?.databaseSha256 !== IDENTIFIER_DB ||
          KEY.some(field => product.observationKey[field] !== key[field]) ||
          product.sourceObservation?.source_id !== ref.sourceId ||
          (product.sourceObservation?.release_id ?? null) !== ref.releaseId ||
          product.sourceObservation?.namespace !== ref.namespace ||
          product.sourceObservation?.lexical_value !== ref.sourceLexicalValue))
      throw Error('Selected detail envelope mismatch');
    return {status:details.state === 'unavailable' ? 'detail-unavailable' : 'detail-returned',
      sourceObservationReference:ref, row, details,
      error:details.error?.reasonCode || null};
  } catch (error) {
    return {status:'detail-unavailable', sourceObservationReference:ref, error:error.message};
  }
}
