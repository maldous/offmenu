import {validateGTIN} from './typed-identifier-contract.mjs';
const SHA=/^[a-f0-9]{64}$/,object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const text=x=>typeof x==='string'&&x.length>0&&x.length<=512&&!/[\x00-\x1f\x7f]/.test(x);
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256','sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
const BINDING=[...SUBJECT,'nativeRecordId'];
const FLAGS=['canonicalIdentityAccepted','identityAssociationAccepted','physicalProductEquivalenceAsserted','normalizationComplete','goldAdmitted','automaticPlanningEligible','recipeNutritionJoinsAccepted'];
const UNKNOWN=['originalProductName','originalLanguage','englishName','foodType','nutrition'];
const FIELDS=['schema','stageId','nativeId','wireSha256','sourceBinding','sourceIdentifiers','sourceRights','matchedIdentifier','sourceInputIndexSha256','rightsVisibilityField','sourceURL',...UNKNOWN,...FLAGS];
const RESULT_FIELDS=['status','sourceId','namespace','lexicalValue','manifestSha256','totalSourceObservations','nextOffset','records','externalFallback','publicPublicationAccepted','normalizationComplete','goldAdmitted'];
function need(ok,message='SOURCE_IDENTITY_RESPONSE_MISMATCH'){if(!ok)throw Error(message);}
const exact=(x,fields)=>object(x)&&Object.keys(x).length===fields.length&&fields.every(k=>Object.hasOwn(x,k));
export function sourceSubject(binding){need(object(binding)&&SUBJECT.every(k=>text(binding[k]))&&SUBJECT.filter(k=>k.endsWith('Sha256')).every(k=>SHA.test(binding[k])));return JSON.stringify(SUBJECT.map(k=>binding[k]));}
export function validateIdentitySelection(selection){
 need(exact(selection,['selectionSha256','admissionSha256','manifestSha256','sourceId','releaseId','sourceQualificationSha256','sourceInputIndexSha256s']), 'SOURCE_IDENTITY_NOT_CONFIGURED');
 need(['selectionSha256','admissionSha256','manifestSha256','sourceQualificationSha256'].every(k=>SHA.test(selection[k]))&&selection.sourceId==='usda-files'&&selection.releaseId==='2026-04-30'&&Array.isArray(selection.sourceInputIndexSha256s)&&selection.sourceInputIndexSha256s.length>0&&selection.sourceInputIndexSha256s.length<=16&&selection.sourceInputIndexSha256s.every(x=>SHA.test(x))&&new Set(selection.sourceInputIndexSha256s).size===selection.sourceInputIndexSha256s.length,'SOURCE_IDENTITY_NOT_CONFIGURED');return structuredClone(selection);
}
export function validateSourceIdentityWire(wire,query,selection){
 const fixed=validateIdentitySelection(selection);
 need(object(query)&&['barcode','USDA-FDC'].includes(query.namespace)&&text(query.value)&&Number.isSafeInteger(query.offset)&&query.offset>=0&&query.offset<=10000&&Number.isSafeInteger(query.limit)&&query.limit>0&&query.limit<=20);
 need(exact(wire,['schema','kind','httpStatus','selectionSha256','admissionSha256','readerResult','status'])&&wire.schema==='offmenu-source-identity-http/1'&&wire.kind==='source-identifier-claims'&&wire.httpStatus===200&&wire.selectionSha256===fixed.selectionSha256&&wire.admissionSha256===fixed.admissionSha256);
 const d=wire.readerResult;need(exact(d,RESULT_FIELDS)&&d.sourceId===fixed.sourceId&&d.namespace===query.namespace&&d.lexicalValue===query.value&&d.manifestSha256===fixed.manifestSha256&&['externalFallback','publicPublicationAccepted','normalizationComplete','goldAdmitted'].every(k=>d[k]===false));
 need(Number.isSafeInteger(d.totalSourceObservations)&&d.totalSourceObservations>=0&&d.totalSourceObservations<=10000&&Array.isArray(d.records)&&d.records.length<=query.limit);
 const expectedCount=Math.min(query.limit,Math.max(0,d.totalSourceObservations-query.offset));
 need(d.records.length===expectedCount&&wire.status===d.status&&d.status===(d.totalSourceObservations>0?'source-identity-claims-found':'no-selected-source-identity'));
 need(d.nextOffset===(query.offset+d.records.length<d.totalSourceObservations?query.offset+d.records.length:null));
 const seen=new Set();for(const r of d.records){
  need(exact(r,FIELDS)&&r.schema==='offmenu-source-identity-observation/2'&&text(r.stageId)&&text(r.nativeId)&&SHA.test(r.wireSha256)&&SHA.test(r.sourceInputIndexSha256)&&fixed.sourceInputIndexSha256s.includes(r.sourceInputIndexSha256)&&['visibility','sourceVisibility'].includes(r.rightsVisibilityField));
  const b=r.sourceBinding;need(exact(b,BINDING)&&b.sourceId===fixed.sourceId&&b.releaseId===fixed.releaseId&&b.nativeRecordId===r.nativeId&&b.sourceQualificationSha256===fixed.sourceQualificationSha256);sourceSubject(b);
  need(exact(r.sourceRights,['license','attribution','sourceVisibility'])&&r.sourceRights.license==='USDA FoodData Central public domain / CC0 (retained declaration)'&&r.sourceRights.attribution==='USDA Agricultural Research Service FoodData Central'&&r.sourceRights.sourceVisibility==='source-staging'&&r.sourceURL==='https://fdc.nal.usda.gov/download-datasets/');
  need(Array.isArray(r.sourceIdentifiers)&&r.sourceIdentifiers.length>0&&r.sourceIdentifiers.length<=16&&r.sourceIdentifiers.every(i=>exact(i,['system','value'])&&['barcode','USDA-FDC'].includes(i.system)&&text(i.value))&&r.sourceIdentifiers.some(i=>i.system==='USDA-FDC'&&i.value===b.recordId));
  const m=r.matchedIdentifier;need(exact(m,['namespace','lexicalValue','relationship','representation','physicalCarrier','sourceChecksumValid'])&&m.namespace===query.namespace&&m.lexicalValue===query.value&&m.relationship==='exact-source-claim'&&m.representation==='untyped'&&m.physicalCarrier===(query.namespace==='barcode'?'unverified':'not-applicable')&&(query.namespace==='barcode'?typeof m.sourceChecksumValid==='boolean'&&m.sourceChecksumValid===validateGTIN(query.value):m.sourceChecksumValid===null)&&r.sourceIdentifiers.some(i=>i.system===query.namespace&&i.value===query.value));
  need(UNKNOWN.every(k=>exact(r[k],['state','reason'])&&r[k].state==='unknown'&&r[k].reason==='not-in-qualified-identity-metadata')&&FLAGS.every(k=>r[k]===false));
  const key=JSON.stringify([r.stageId,sourceSubject(b)]);need(!seen.has(key));seen.add(key);
 }
 return structuredClone(d);
}
export function createSourceIdentityLookup({selection,fetchImpl=globalThis.fetch}={}){
 let fixed;try{fixed=validateIdentitySelection(selection);}catch{}
 return async function lookup(raw,generation,namespace='barcode',offset=0,limit=20){
  const unavailable=error=>({identityLookup:true,sourceId:'usda-files',namespace,lexicalValue:raw,generation,requestOffset:offset,records:[],nextOffset:null,error});
  if(!fixed)return unavailable('SOURCE_IDENTITY_NOT_CONFIGURED');
  if(!text(raw)||!['barcode','USDA-FDC'].includes(namespace)||!Number.isSafeInteger(generation)||!Number.isSafeInteger(offset)||offset<0||offset>10000||!Number.isSafeInteger(limit)||limit<1||limit>20)return unavailable('SOURCE_IDENTITY_QUERY_UNAVAILABLE');
  const query={namespace,value:raw,offset,limit},url=new URL('/api/corpus/source-identity','http://local.invalid');for(const [k,v]of Object.entries({source:'usda-files',namespace,value:raw,offset,limit}))url.searchParams.set(k,String(v));
  try{
   const response=await fetchImpl(url.pathname+url.search,{method:'GET',credentials:'omit',cache:'no-store',redirect:'error',mode:'same-origin',headers:{Accept:'application/json'}});
   if(response.status!==200)return {...unavailable(response.status===403?'SOURCE_IDENTITY_ACCESS_UNAVAILABLE':response.status===400?'SOURCE_IDENTITY_QUERY_UNAVAILABLE':'SOURCE_IDENTITY_SERVICE_UNAVAILABLE'),httpStatus:response.status};
   const body=await response.text();need(new TextEncoder().encode(body).length<=2097152);const data=validateSourceIdentityWire(JSON.parse(body),query,fixed);
   return {...data,identityLookup:true,generation,requestOffset:offset,selectionSha256:fixed.selectionSha256,admissionSha256:fixed.admissionSha256,error:null};
  }catch{return unavailable('SOURCE_IDENTITY_RESPONSE_UNAVAILABLE');}
 };
}
export function identityMatch(record){return {kind:'source-identity',id:JSON.stringify(['source-identity',record.stageId,sourceSubject(record.sourceBinding)]),name:null,brand:null,sourceIdentityRecord:structuredClone(record),provenance:{...structuredClone(record.sourceBinding),license:record.sourceRights.license,attribution:record.sourceRights.attribution},sourceObservationReference:null};}
export function identityTitle(match){const r=match?.sourceIdentityRecord;return r?'USDA-FDC · '+r.sourceBinding.recordId:'Name not available';}
export function identityReadout(match,entry,view='overview'){
 const r=match.sourceIdentityRecord,rows=[{label:'Source record',text:'USDA-FDC · '+r.sourceBinding.recordId},{label:'Identifiers',text:r.sourceIdentifiers.map(i=>i.system+' · '+i.value).join(' / ')},{label:'Source',text:r.sourceBinding.sourceId+' · '+r.sourceBinding.releaseId}];
 for(const [key,label]of [['originalProductName','Product name'],['originalLanguage','Language'],['englishName','English name'],['foodType','Food type'],['nutrition','Nutrition']])rows.push({label,text:'Unknown · not supplied by this source identity view'});
 rows.push({label:'Licence and credits',text:r.sourceRights.attribution+' · '+r.sourceRights.license},{label:'Source URL',text:r.sourceURL},{label:'About this record',text:'Source identifier claims only. Product identity, food classification and inventory eligibility have not been established.'});
 if(r.matchedIdentifier.namespace==='barcode')rows.push({label:'Source barcode claim',text:r.matchedIdentifier.lexicalValue+' · '+(r.matchedIdentifier.sourceChecksumValid?'checksum valid; physical carrier unverified':'invalid checksum; source claim retained without correction')});
 if(entry.phaseTechnicalFailure)rows.push({label:'Lookup status',text:'Some product details could not be checked. This source record does not resolve that lookup failure.'});
 if(entry.identityState?.error)rows.push({label:'Source lookup',text:'Additional source records could not be checked right now.'});
 if(view==='source')rows.push({label:'Source record reference',text:JSON.stringify({stageId:r.stageId,nativeId:r.nativeId,wireSha256:r.wireSha256,sourceBinding:r.sourceBinding,sourceInputIndexSha256:r.sourceInputIndexSha256})});return rows;
}

export function identityStatusRows(entry){
 const s=entry?.identityState;if(!s)return[];
 if(s.error){const copy={SOURCE_IDENTITY_NOT_CONFIGURED:'Additional source records are not enabled in this view.',SOURCE_IDENTITY_ACCESS_UNAVAILABLE:'Source records could not be accessed.',SOURCE_IDENTITY_QUERY_UNAVAILABLE:'This source identifier could not be checked.',SOURCE_IDENTITY_SERVICE_UNAVAILABLE:'Source records are unavailable right now.',SOURCE_IDENTITY_RESPONSE_UNAVAILABLE:'Source records could not be verified right now.'};return[{label:'Source lookup',text:copy[s.error]||'Source records are unavailable right now.'}];}
 if(!s.records.length)return[{label:'Source lookup',text:'No exact source record was returned by this selected view. Other records may not be covered.'}];
 return[];
}
