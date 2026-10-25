// Public metadata pins only. No source records are embedded or fetched.
export const TRUSTED_PINS=Object.freeze({bytes:34844,sha256:'d69ea04ee0e973305be25ad560f2a1e89debadf18b9e0f373a3f788fd7ba91e8',sourceId:'usda-files',releaseId:'2026-04-30',count:22});
export async function importReviewedResult(file,pins=TRUSTED_PINS){
 if(!file||file.size!==pins.bytes)throw Error('Saved file size does not match the reviewed result.');
 const bytes=await file.arrayBuffer(),digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 if(digest!==pins.sha256)throw Error('Saved file does not match the reviewed SHA-256 pin.');
 const body=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)),q=body.lookup;
 if(body.status!=='PRIVATE_NATIVE_LOOKUP_VERIFIED'||q?.sourceId!==pins.sourceId||q.releaseId!==pins.releaseId||q.visibility!=='private'||q.fixture!==false||q.status!=='matched'||typeof q.barcode!=='string'||!Array.isArray(q.matches)||q.matches.length!==pins.count)throw Error('Saved result identity or release does not match.');
 const matches=q.matches.map(m=>{const r=m.record,d=r?.data,p=r?.provenance;
 if(r?.kind!=='product'||r.schemaVersion!=='1.0'||p?.sourceId!==pins.sourceId||p.releaseId!==pins.releaseId||p.visibility!=='private-candidate'||r.id!==m.nativeProductId||p.recordId!==m.sourceRecordId||!d?.identifiers?.some(x=>x.system==='barcode'&&x.value===q.barcode))throw Error('Source-record identity mismatch.');
 return Object.freeze({id:r.id,sourceRecordId:m.sourceRecordId,name:typeof d.name==='string'?d.name:null,brand:typeof d.brand==='string'?d.brand:null,ingredientsText:typeof d.ingredientsText==='string'?d.ingredientsText:null,market:typeof d.marketCountry==='string'?d.marketCountry:null,serving:d.serving?Object.freeze({...d.serving}):null,package:null,nutrition:null,concept:null,provenance:Object.freeze({...p}),candidateLine:m.candidateLine});});
 return Object.freeze({barcode:q.barcode,sourceId:q.sourceId,releaseId:q.releaseId,qualificationMeaning:q.qualificationMeaning,qualificationSha256:q.qualificationSha256,sha256:digest,matches:Object.freeze(matches)});
}
export function resolveSavedResult(rawLexical,generation,result){
 if(!result)return {generation,status:'unavailable',matches:[]};
 if(rawLexical!==result.barcode)return {generation,status:'saved-result-miss',matches:[],releaseId:result.releaseId,sourceId:result.sourceId};
 return {generation,status:result.matches.length>1?'ambiguous':'source-match',matches:result.matches,releaseId:result.releaseId,sourceId:result.sourceId};
}
