import {createSourceBarcodeHydrator,hydratedSourceBarcodeReadout} from './source-barcode-hydrator.mjs';
import {createSourceBarcodeLookup,sourceBarcodeReadout} from './source-barcode-client.mjs';

const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
function combine(foundation,source,previousMatches=[]){
 if(!source?.enabled)return foundation;
 const prior=new Map(previousMatches.map(m=>[m.id,m]));
 const candidates=source.matches.map(m=>{const before=prior.get(m.id);return before&&same(before.sourceBarcodeCandidate?.reference,m.sourceBarcodeCandidate?.reference)&&same(before.sourceBarcodeCandidate?.query,m.sourceBarcodeCandidate?.query)&&before.sourceBarcodeCandidate?.manifestSha256===m.sourceBarcodeCandidate?.manifestSha256?before:m;});
 // Retain separate source observations; never merge a source candidate with a
 // canonical foundation record merely because they share a barcode or subject.
 const matches=[...foundation.matches,...candidates];
 const foundationFailure=(foundation.providerStates||[]).some(l=>l.error)||!!foundation.error&&!['UNSUPPORTED_EXACT_BARCODE'].includes(foundation.error);
 const indexFailure=source.configurationError||source.lanes.some(l=>l.status==='index-unavailable'||l.pageError);
 const failed=foundationFailure||indexFailure;
 const status=matches.length?(failed?'partial':matches.length>1||foundation.hasMore||source.ambiguous?'ambiguous':'source-match'):failed?'unavailable':foundation.hasMore?'searching':source.complete&&source.lanes.every(l=>l.status==='source-key-not-found')?'scoped-miss':'unavailable';
 return {...foundation,matches,status,foundationResult:foundation,sourceBarcodeResult:source,
  // Existing alias/exact paging continues through its original cursor only.
  hasMore:foundation.hasMore,nextCursor:foundation.nextCursor,
  canonicalIdentityAsserted:false,automaticPlanningEligible:false,nutritionAggregationEligible:false};
}
export function createSourceBarcodeInventory({foundationInventory,selection,fetchImpl=globalThis.fetch,limit=20}={}){
 if(!foundationInventory||typeof foundationInventory.lookupIdentifiers!=='function'||typeof foundationInventory.mergeIdentifierPages!=='function'||typeof foundationInventory.destroy!=='function')throw Error('EXISTING_FOUNDATION_INVENTORY_REQUIRED');
 const candidateLookup=createSourceBarcodeLookup({selection,fetchImpl,limit});let closed=false;
 const hydrator=createSourceBarcodeHydrator({selection,fetchImpl});
 async function lookupIdentifiers(raw,generation,cursor=null,symbology=null,namespace='barcode'){
  const foundation=await foundationInventory.lookupIdentifiers(raw,generation,cursor,symbology,namespace);
  if(closed||namespace!=='barcode'||cursor!==null)return {...foundation,foundationResult:foundation};
  const source=await candidateLookup(raw,generation,symbology,namespace);
  if(closed)return {...foundation,foundationResult:foundation};
  return combine(foundation,source);
 }
 function mergeIdentifierPages(previous,next){
  const foundation=foundationInventory.mergeIdentifierPages(previous.foundationResult||previous,next.foundationResult||next);
  return combine(foundation,previous.sourceBarcodeResult,previous.matches);
 }
 async function moreSourceBarcode(entry){
  if(closed||!entry?.sourceBarcodeResult?.enabled)throw Error('SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
  const before=entry.sourceBarcodeResult;
  if(before.original!==entry.raw&&before.original!==entry.original||before.generation!==(entry.queryGeneration??entry.generation))throw Error('SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
  const next=await candidateLookup.more(before);
  if(closed||entry.sourceBarcodeResult!==before)throw Error('SOURCE_BARCODE_PAGE_CONTEXT_CHANGED');
  return combine(entry.foundationResult||entry,next,entry.matches);
 }
 async function hydrateSourceBarcode(entry,match){
  if(closed||!entry?.matches?.includes(match)||match?.kind!=='source-barcode-candidate'||entry.sourceBarcodeResult?.generation!==(entry.queryGeneration??entry.generation))throw Error('SOURCE_DETAILS_CONTEXT_CHANGED');
  const state=entry.sourceBarcodeResult;
  const hydrated=await hydrator.hydrate(match);
  if(closed||entry.sourceBarcodeResult!==state||!entry.matches.includes(match))throw Error('SOURCE_DETAILS_CONTEXT_CHANGED');
  return {...entry,matches:entry.matches.map(m=>m===match?hydrated:m)};
 }
 return Object.freeze({lookupIdentifiers,mergeIdentifierPages,moreSourceBarcode,hydrateSourceBarcode,destroy(){if(closed)return;closed=true;candidateLookup.destroy();hydrator.destroy();foundationInventory.destroy();}});
}
export function inventoryReadout(foundationReadout,match,entry,tab='overview'){
 if(match?.kind==='source-barcode-candidate')return hydratedSourceBarcodeReadout(match)||[...sourceBarcodeReadout(match,entry,tab),...(match.sourceBarcodeCandidate.hydrationState==='unavailable'?[{label:'Source details unavailable',text:'Technical verification or loading failed. Identifier retained; no source absence is established.'}]:[])];
 const rows=foundationReadout(match,entry,tab);
 const source=entry?.sourceBarcodeResult;if(!source?.enabled)return rows;
 const count=source.matches.length,unknown=source.configurationError||!source.complete||source.lanes.some(l=>l.status==='index-unavailable'||l.pageError);
 return [...rows,{label:'Additional source identifier index',text:count?count+' source-scoped identifier reference(s) loaded. Choose a reference for its exact source binding; original facts remain pending verified hydration.':unknown?'The additional index could not be checked completely. The original identifier is retained; no source absence is established.':'No source key in the selected complete public index scopes. Other sources may differ; the original identifier is retained.'}];
}

// Additional coverage failure must not erase an existing unambiguous source
// observation. Overall status remains partial, with a visible coverage warning.
export function automaticSourceSelection(result){
 if(result?.status==='source-match'&&result.matches?.length===1)return result.matches[0];
 const foundation=result?.foundationResult,source=result?.sourceBarcodeResult;
 const additionalUnavailable=source?.enabled&&(source.configurationError||!source.complete||source.lanes?.some(l=>l.status==='index-unavailable'||l.pageError));
 if(additionalUnavailable&&source.matches?.length===0&&foundation?.status==='source-match'&&foundation.matches?.length===1&&!foundation.hasMore)return foundation.matches[0];
 return null;
}
