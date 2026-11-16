import {createGuestFoundationLookup} from './guest-foundation-client.mjs';
import {mergeIdentifierPages as mergePhasePages,foundationReadout as phaseReadout} from './foundation-scanner-client.mjs';
import {createSourceIdentityLookup,sourceSubject,identityMatch,identityReadout,identityStatusRows} from './source-identity-client.mjs';
import {SOURCE_IDENTITY_SELECTION} from './source-identity-selection.mjs';
export {identityTitle,identityReadout,identityStatusRows} from './source-identity-client.mjs';
const same=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const technical=phase=>(phase?.providerStates??[]).some(l=>l.error&&l.availabilityKind!=='no-usable-qualified-details');
function compose(phase,identity,priorMatches=[]){
 const phaseMatches=phase?.matches??[],subjects=new Set(phaseMatches.map(m=>sourceSubject(m.foundationRecord.provenance))),old=new Map(priorMatches.map(m=>[m.id,m]));
 const claims=[];for(const r of identity.records??[]){if(subjects.has(sourceSubject(r.sourceBinding)))continue;const m=identityMatch(r),prior=old.get(m.id);claims.push(prior&&same(prior.sourceIdentityRecord,r)?prior:m);}
 const matches=[...phaseMatches,...claims],failed=(phase?.providerStates??[]).some(l=>l.error)||!!identity.error;
 const base=phase??{original:identity.lexicalValue,namespace:identity.namespace,symbology:null,generation:identity.generation,foundationLookup:true,providerStates:[],hasMore:false,nextCursor:null,requestCursor:null,externalFallback:false,fullProductComplete:false,goldAdmitted:false,automaticPlanningEligible:false,physicalProductEquivalenceAsserted:false};
 return {...base,phaseResult:phase,identityState:identity,matches,phaseTechnicalFailure:technical(phase),identityNextOffset:identity.nextOffset??null,status:identity.error==='SOURCE_IDENTITY_NOT_CONFIGURED'&&phase?phase.status:failed?(matches.length?'partial':'unavailable'):matches.length>1||matches.length&&base.hasMore?'ambiguous':matches.length?'source-match':'unavailable'};
}
export function createComposedScannerLookup({selection=SOURCE_IDENTITY_SELECTION,fetchImpl=globalThis.fetch}={}){
 const phaseLookup=createGuestFoundationLookup({fetchImpl}),identityLookup=createSourceIdentityLookup({selection,fetchImpl});
 async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode'){
  const phase=namespace==='barcode'?await phaseLookup(raw,generation,cursor,symbology,namespace):null;
  if(!['barcode','USDA-FDC'].includes(namespace))return phase??{foundationLookup:true,original:raw,namespace,generation,matches:[],providerStates:[],status:'unavailable',error:'UNSUPPORTED_EXACT_BARCODE',hasMore:false,nextCursor:null};
  const identity=await identityLookup(raw,generation,namespace,0,20);return compose(phase,identity);
 }
 async function moreIdentity(entry){
  const before=entry.identityState;if(!before||before.error||before.nextOffset===null||before.nextOffset===undefined)throw Error('SOURCE_IDENTITY_PAGE_UNAVAILABLE');
  const page=await identityLookup(entry.raw,entry.queryGeneration??entry.generation,entry.namespace,before.nextOffset,20);
  if(entry.identityState!==before)throw Error('SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED');
  if(page.error)return compose(entry.phaseResult,{...before,error:page.error},entry.matches);
  if(page.namespace!==before.namespace||page.lexicalValue!==before.lexicalValue||page.generation!==before.generation||page.manifestSha256!==before.manifestSha256||page.selectionSha256!==before.selectionSha256||page.admissionSha256!==before.admissionSha256||page.requestOffset!==before.nextOffset||page.totalSourceObservations!==before.totalSourceObservations)throw Error('SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED');
  const records=[...before.records],seen=new Map(records.map(r=>[identityMatch(r).id,r]));for(const r of page.records){const k=identityMatch(r).id;if(seen.has(k))throw Error('SOURCE_IDENTITY_DUPLICATE_PAGE_RECORD');seen.set(k,r);records.push(r);}
  return compose(entry.phaseResult,{...page,records,requestOffset:before.requestOffset},entry.matches);
 }
 return Object.assign(lookup,{moreIdentity});
}
export function mergeIdentifierPages(previous,next){
 const a=previous.phaseResult,b=next.phaseResult;if(!a||!b)throw Error('FOUNDATION_PAGE_CONTEXT_CHANGED');
 const phase=mergePhasePages(a,b),left=previous.identityState,right=next.identityState;
 if(!left||!right||left.namespace!==right.namespace||left.lexicalValue!==right.lexicalValue||left.generation!==right.generation||left.manifestSha256!==right.manifestSha256||left.selectionSha256!==right.selectionSha256||left.admissionSha256!==right.admissionSha256)throw Error('SOURCE_IDENTITY_PAGE_CONTEXT_CHANGED');
 // A phase-page request repeats the first identity page; preserve identity progress.
 if(!right.error&&right.records.some(r=>{const old=left.records.find(x=>identityMatch(x).id===identityMatch(r).id);return old&&!same(old,r);}))throw Error('SOURCE_IDENTITY_OBSERVATION_CHANGED');
 return compose(phase,right.error?{...left,error:right.error}:left,previous.matches);
}
export function foundationReadout(selected,entry,tab='overview'){return selected?.kind==='source-identity'?identityReadout(selected,entry,tab):[...phaseReadout(selected,entry,tab),...identityStatusRows(entry)];}
export const lookupIdentifiers=createComposedScannerLookup();
export const loadIdentityPage=entry=>lookupIdentifiers.moreIdentity(entry);
