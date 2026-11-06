// Compatibility adapter for the existing audio-reviewed guest scanner, not a replacement UI.
// Only the already-qualified foundation DTO is displayed; no legacy product projection is fabricated.
import {createFoundationScannerLookup,foundationReadout as strictReadout,FOUNDATION_SELECTION} from './public/production-scanner/foundation-scanner-client.mjs';
const ORIGIN='https://offmenu.aldous.info',SCHEMA='offmenu-guest-foundation-pages/1';
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?'{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const failure=(raw,generation,symbology,requestCursor,error)=>({original:raw,namespace:'barcode',symbology,generation,requestCursor,foundationLookup:true,matches:[],status:'unavailable',hasMore:false,nextCursor:null,providerStates:[],externalFallback:false,error});
const state=(matches,lanes,more)=>lanes.some(l=>l.error)?(matches.length?'partial':'unavailable'):matches.length>1||matches.length&&more?'ambiguous':matches.length?'source-match':'unavailable';
export function createGuestFoundationLookup({origin,fetchImpl=globalThis.fetch,analyzeIdentifier}={}){
 if(origin!==ORIGIN||globalThis.location?.origin&&globalThis.location.origin!==origin||typeof fetchImpl!=='function'||typeof analyzeIdentifier!=='function')throw Error('EXACT_PUBLIC_FOUNDATION_ORIGIN_REQUIRED');
 let closed=false,epoch=0;const controllers=new Set();
 async function lookupIdentifiers(raw,generation,cursor=null,symbology=null,namespace='barcode'){
  const fail=reason=>failure(raw,generation,symbology,cursor,reason);
  if(closed)return fail('GUEST_FOUNDATION_CLOSED');
  if(namespace!=='barcode'||typeof raw!=='string'||!/^\d{4,32}$/.test(raw)||!Number.isSafeInteger(generation)||symbology!==null&&typeof symbology!=='string')return fail('UNSUPPORTED_EXACT_BARCODE');
  let forms;
  try{const typed=analyzeIdentifier({original:raw,namespace,representationHint:symbology});forms=[{value:raw,rule:null},...(typed.status==='checksum-valid'?typed.labelledEquivalents:[])].filter((f,i,a)=>/^\d{4,32}$/.test(f.value)&&a.findIndex(x=>x.value===f.value)===i);if(!forms.length||forms.length>8)throw Error();}catch{return fail('UNSUPPORTED_EXACT_BARCODE');}
  let index=0,sourceCursor=null;
  if(cursor!==null)try{if(typeof cursor!=='string'||cursor.length>10000)throw Error();const c=JSON.parse(cursor);if(c.schema!==SCHEMA||c.original!==raw||c.generation!==generation||c.symbology!==symbology||stable(c.selection)!==stable(FOUNDATION_SELECTION)||!Number.isSafeInteger(c.index)||c.index<0||c.index>=forms.length||c.sourceCursor!==null&&(typeof c.sourceCursor!=='string'||c.sourceCursor.length>6000))throw Error();index=c.index;sourceCursor=c.sourceCursor;}catch{return fail('FOUNDATION_GUEST_CURSOR_MISMATCH');}
  const turn=epoch,controller=new AbortController();controllers.add(controller);const timer=setTimeout(()=>controller.abort(),12000);
  const boundedFetch=(url,init={})=>{const target=new URL(url,origin);if(target.origin!==origin||target.pathname!=='/api/corpus/foundation'||(init.method&&init.method!=='GET'))throw Error('GUEST_FOUNDATION_ROUTE_CHANGED');return fetchImpl(target.href,{...init,method:'GET',credentials:'omit',cache:'no-store',redirect:'error',mode:'same-origin',signal:controller.signal});};
  try{
   const exact=createFoundationScannerLookup({fetchImpl:boundedFetch}),form=forms[index];
   const result=await exact(form.value,generation,sourceCursor,symbology,namespace);
   if(closed||turn!==epoch)return fail('GUEST_FOUNDATION_CLOSED');
   const matches=result.matches.map(value=>{const m=structuredClone(value);m.id=JSON.stringify([m.id,form.value]);m.matchContext={originalLexicalValue:raw,sourceLexicalValue:form.value,symbology,matchType:form.value===raw?'exact':'representation-alias',equivalence:form.rule??null,physicalProductEquivalenceAsserted:false};m.lookupOrigin={provider:'qualified-owned-foundation',selection:{...FOUNDATION_SELECTION}};m.detail={fields:{},sourceBinding:{sourceId:m.provenance.sourceId},assurance:'Qualified canonical base and type only; no full-product, normalization, nutrition or automatic inventory admission.'};return m;});
   const nextIndex=result.hasMore?index:index+1,hasMore=nextIndex<forms.length;
   return {...result,original:raw,requestCursor:cursor,matches,status:state(matches,result.providerStates,hasMore),hasMore,nextCursor:hasMore?JSON.stringify({schema:SCHEMA,original:raw,generation,symbology,selection:FOUNDATION_SELECTION,index:nextIndex,sourceCursor:result.hasMore?result.nextCursor:null}):null,selectedFoundation:{...FOUNDATION_SELECTION},coverage:{scope:'selected-qualified-owned-foundation-only',externalFallback:false,globalProductTotal:null,identityEquivalence:false},guestInventoryMutation:false};
  }catch{return fail('GUEST_FOUNDATION_UNAVAILABLE');}finally{clearTimeout(timer);controllers.delete(controller);}
 }
 function mergeIdentifierPages(previous,next){
  if(!previous.foundationLookup||!next.foundationLookup||previous.original!==next.original||previous.namespace!==next.namespace||previous.generation!==next.generation||previous.symbology!==next.symbology||previous.nextCursor!==next.requestCursor||stable(previous.selectedFoundation)!==stable(next.selectedFoundation))throw Error('GUEST_FOUNDATION_PAGE_CHANGED');
  const rows=new Map();for(const m of [...previous.matches,...next.matches]){if(rows.has(m.id)&&stable(rows.get(m.id))!==stable(m))throw Error('GUEST_FOUNDATION_OBSERVATION_CHANGED');rows.set(m.id,m);}
  const matches=[...rows.values()],providerStates=next.providerStates;return {...next,matches,status:state(matches,providerStates,next.hasMore)};
 }
 return Object.freeze({lookupIdentifiers,mergeIdentifierPages,destroy(){closed=true;epoch++;for(const c of controllers)c.abort();controllers.clear();}});
}
export function foundationReadout(selected,entry,tab){
 const rows=strictReadout(selected,entry,tab);
 if(selected?.matchContext?.matchType==='representation-alias')rows.splice(1,0,{label:'Barcode representation',text:'Original '+selected.matchContext.originalLexicalValue+'; selected source representation '+selected.matchContext.sourceLexicalValue+'. Representation relation only, not physical-product equivalence.'});
 rows.push({label:'Demo session',text:'Selected source observations remain in this tab. Finish does not add pantry stock, infer quantity, join nutrition, or change a private profile.'});
 return rows;
}
