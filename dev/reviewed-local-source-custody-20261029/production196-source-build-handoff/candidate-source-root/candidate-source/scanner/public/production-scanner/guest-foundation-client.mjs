import {createFoundationScannerLookup,FOUNDATION_CONTRACT,FOUNDATION_SELECTION,mergeIdentifierPages,foundationReadout} from './foundation-scanner-client.mjs';
export {mergeIdentifierPages,foundationReadout};
// Availability describes only the selected public representation, never whether
// a retained/held/private product exists. Keep every successful DTO unchanged.
export function createGuestFoundationLookup({fetchImpl=globalThis.fetch}={}){
 return async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode'){
  const availability=new Map();
  const qualified=createFoundationScannerLookup({fetchImpl:async(url,init)=>{
   const response=await fetchImpl(url,init),source=new URL(url,'http://local.invalid').searchParams.get('source');
   if(response.status===503){
    let kind='service-unavailable';
    try{
     const text=await response.clone().text();if(new TextEncoder().encode(text).byteLength>65536)throw Error();const d=JSON.parse(text);
     if(d.schemaVersion==='1.0'&&d.fieldContract===FOUNDATION_CONTRACT&&d.source===source&&d.barcode===raw&&d.releaseId===FOUNDATION_SELECTION.releaseId&&d.manifestSha256===FOUNDATION_SELECTION.manifestSha256&&d.httpStatus===503&&d.status==='own-data-unavailable'&&Array.isArray(d.records)&&d.records.length===0&&d.qualifiedSourceObservationCount===0&&d.externalFallback===false&&d.physicalProductEquivalenceAsserted===false&&d.goldAdmitted===false&&d.fullProductComplete===false)kind='no-usable-qualified-details';
    }catch{}
    availability.set(source,kind);
   }else if(response.status===400||response.status===409)availability.set(source,'query-unavailable');
   else if(response.status===401||response.status===403)availability.set(source,'access-unavailable');
   return response;
  }});
  const result=await qualified(raw,generation,cursor,symbology,namespace);
  return {...result,providerStates:result.providerStates.map(lane=>({...lane,...(lane.error?{availabilityKind:availability.get(lane.source)||'service-unavailable'}:{})}))};
 };
}
export const lookupIdentifiers=createGuestFoundationLookup();
