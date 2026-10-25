// Production scanner boundary. No private retained index, fixture session, or live provider fallback.
// A release may be selected only after its exact published manifest bytes and rights are qualified.
const SELECTED_PUBLIC_RELEASE = null;
const HEX = /^[a-f0-9]{64}$/;
const RELEASE = /^[-A-Za-z0-9.]{1,128}$/;
const PUBLIC_SOURCE = 'off';
const unavailable = (generation, reasonCode) => ({generation,status:'unavailable',matches:[],hasMore:false,nextCursor:null,error:reasonCode});
function selected(selection) {return selection && RELEASE.test(selection.releaseId||'') && HEX.test(selection.manifestSha256||'') && selection.sourceId===PUBLIC_SOURCE;}
function projected(record) {
  const d=record.data, value=(v)=>({state:v===null?'null':v===undefined?'missing':'present',value:v??null});
  const fields={name:value(d.name===d.identifiers?.[0]?.value?null:d.name),brand:value(d.brand),markets:value(record.countries),packageQuantity:value(d.pack),ingredientDeclaration:value(d.ingredientsText),sourceAllergenClaims:value(d.allergens),sourceTraceClaims:value(d.traces),sourceDietaryLabelClaims:value(d.labels),categories:value(d.categories),origins:value(d.origins),manufacturingPlaces:value(d.manufacturingPlaces),names:value(d.names),nutritionSourceBasis:value(d.nutritionSourceBasis),rawNutriments:value(d.rawNutriments),nutrientProfile:{state:'not-loaded',value:null}};
  for(const [key,raw] of Object.entries(d))if(!Object.hasOwn(fields,key))fields[key]=value(raw);
  return {id:record.id,name:fields.name.value,brand:fields.brand.value,ingredientsText:d.ingredientsText??null,provenance:{...record.provenance,releaseId:record.releaseId??null},detail:{fields,sourceBinding:{sourceId:record.provenance.sourceId},assurance:'Published source record; claims are attributed, not independently certified.'},publicRecord:record};
}
export function createPublicLookup({selection,fetchImpl=fetch}={}) {
  return async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode') {
    if(!selected(selection))return unavailable(generation,'PUBLIC_RELEASE_NOT_SELECTED');
    if(namespace!=='barcode'||typeof raw!=='string'||!/^\d{4,32}$/.test(raw))return unavailable(generation,'UNSUPPORTED_PUBLIC_IDENTIFIER');
    const url=new URL('/api/data/public',globalThis.location?.origin||'https://offmenu.invalid');
    for(const [k,v] of Object.entries({source:PUBLIC_SOURCE,barcode:raw,releaseId:selection.releaseId,manifestSha256:selection.manifestSha256,kind:'product',limit:'25'}))url.searchParams.set(k,v);
    if(cursor)url.searchParams.set('cursor',cursor);
    try {
      const response=await fetchImpl(url.pathname+url.search,{method:'GET',cache:'no-store',headers:{Accept:'application/json'}});
      if(!response.ok)return unavailable(generation,response.status===409?'PUBLIC_RELEASE_MISMATCH':response.status===400?'PUBLIC_QUERY_INVALID':'PUBLIC_LOOKUP_UNAVAILABLE');
      const body=await response.text();if(new TextEncoder().encode(body).byteLength>262144)return unavailable(generation,'PUBLIC_RESPONSE_BOUND');
      const data=JSON.parse(body);
      if(data.releaseId!==selection.releaseId||data.manifestSha256!==selection.manifestSha256||!Array.isArray(data.records))return unavailable(generation,'PUBLIC_RESPONSE_MISMATCH');
      const matches=[];
      for(const record of data.records){
        if(record?.kind!=='product'||record.provenance?.sourceId!==PUBLIC_SOURCE||record.provenance?.visibility!=='public'||record.data?.identifiers?.some(id=>id.system==='barcode'&&id.value===raw)!==true)return unavailable(generation,'PUBLIC_RECORD_BINDING');
        matches.push(projected({...record,releaseId:selection.releaseId}));
      }
      if(data.nextCursor!==null&&data.nextCursor!==undefined&&typeof data.nextCursor!=='string')return unavailable(generation,'PUBLIC_CURSOR_INVALID');
      const hasMore=!!data.nextCursor;
      return {generation,status:matches.length>1?'ambiguous':matches.length===1?'source-match':hasMore?'searching':'scoped-miss',matches,hasMore,nextCursor:data.nextCursor||null,original:raw,namespace,symbology,releaseId:selection.releaseId,manifestSha256:selection.manifestSha256};
    }catch{return unavailable(generation,'PUBLIC_LOOKUP_UNAVAILABLE');}
  };
}
export const lookupIdentifiers=createPublicLookup({selection:SELECTED_PUBLIC_RELEASE});
export function mergeIdentifierPages(previous,next){
  if(previous.original!==next.original||previous.namespace!==next.namespace||previous.releaseId!==next.releaseId||previous.manifestSha256!==next.manifestSha256)throw Error('Selected public release changed');
  const matches=[...previous.matches,...next.matches];return {...next,matches,status:matches.length>1?'ambiguous':matches.length===1?'source-match':next.hasMore?'searching':'scoped-miss'};
}
