// Explicit foundation publication namespace. No legacy curated-ready admission
// is changed, and internal producer projections are never served directly.
import {assessFoundation,FOUNDATION_CONTRACT} from './foundation-phase-contract-v2.mjs';
const SHA=/^[a-f0-9]{64}$/,encoder=new TextEncoder(),decoder=new TextDecoder('utf-8',{fatal:true});
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(v,k)=>Object.hasOwn(v,k);
const text=v=>typeof v==='string'&&v.length>0&&v.length<=512&&!/[\x00-\x1f\x7f]/.test(v);
const safeKey=k=>typeof k==='string'&&k.startsWith('own-data/foundation/')&&
  k.split('/').every(p=>/^[-A-Za-z0-9._]+$/.test(p)&&p!=='.'&&p!=='..');
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256',
  'sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
export class FoundationOriginError extends Error{constructor(message,status=503){super(message);this.status=status;}}
const need=(ok,message,status)=>{if(!ok)throw new FoundationOriginError(message,status);};
export async function foundationDigest(bytes){return Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');}
function descriptor(d,max=1024*1024){
  need(object(d)&&safeKey(d.key)&&SHA.test(d.sha256)&&Number.isSafeInteger(d.bytes)&&d.bytes>0&&d.bytes<=max,'Invalid foundation file descriptor');
  if(d.uncompressedBytes!==undefined)need(Number.isSafeInteger(d.uncompressedBytes)&&d.uncompressedBytes>0&&d.uncompressedBytes<=2*1024*1024,'Invalid foundation expanded bound');
}
async function decode(bytes,d){
  if(!d.key.endsWith('.gz'))return decoder.decode(bytes);
  need(Number.isSafeInteger(d.uncompressedBytes),'Missing foundation expanded bound');
  const reader=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('gzip')).getReader(),chunks=[];let total=0;
  try{while(true){const r=await reader.read();if(r.done)break;total+=r.value.length;need(total<=d.uncompressedBytes&&total<=2*1024*1024,'Foundation file exceeds expanded bound');chunks.push(r.value);}}
  finally{await reader.cancel();}
  need(total===d.uncompressedBytes,'Foundation expanded length mismatch');const out=new Uint8Array(total);let at=0;
  for(const chunk of chunks){out.set(chunk,at);at+=chunk.length;}return decoder.decode(out);
}
function cursorDecode(value){need(typeof value==='string'&&value.length<=700,'Invalid foundation cursor',400);try{return JSON.parse(atob(value.replaceAll('-','+').replaceAll('_','/')));}catch{throw new FoundationOriginError('Invalid foundation cursor',400);}}
const cursorEncode=v=>btoa(JSON.stringify(v)).replaceAll('+','-').replaceAll('/','_').replace(/=+$/,'');

export async function createAcceptedFoundationReader(readBlob,selection){
  need(typeof readBlob==='function'&&object(selection)&&text(selection.sourceId)&&text(selection.releaseId)&&
    SHA.test(selection.consumerCodeSha256)&&SHA.test(selection.admissionReceiptSha256),'Fixed foundation selection required');
  descriptor(selection.manifest,128*1024);descriptor(selection.policy,128*1024);
  const namespace='own-data/foundation/'+selection.releaseId+'/';
  need(selection.manifest.key.startsWith(namespace)&&selection.policy.key.startsWith(namespace),'Foundation selection namespace mismatch');
  const cache=new Map();let reads=0;
  async function load(d,max=1024*1024){
    descriptor(d,max);need(d.key.startsWith(namespace),'Foundation file is outside selected namespace');
    const id=d.key+'#'+d.sha256;if(cache.has(id))return cache.get(id);need(++reads<=8,'Foundation read budget exceeded');
    const result=await readBlob(d.key,{...d,cachePolicy:'no-store'});need(result!==null&&result!==undefined,'Foundation file unavailable');
    const bytes=result instanceof Uint8Array?result:new Uint8Array(result);
    need(bytes.byteLength===d.bytes&&await foundationDigest(bytes)===d.sha256,'Foundation file checksum mismatch');
    let value;try{value=JSON.parse(await decode(bytes,d));}catch(e){if(e instanceof FoundationOriginError)throw e;throw new FoundationOriginError('Invalid foundation JSON');}
    cache.set(id,value);return value;
  }
  const manifest=await load(selection.manifest,128*1024);
  need(manifest?.schema==='offmenu-foundation-publication/2'&&manifest.releaseId===selection.releaseId&&
    manifest.status==='phase-qualified-release-ready'&&manifest.fieldContract===FOUNDATION_CONTRACT&&
    manifest.policySha256===selection.policy.sha256&&manifest.consumerCodeSha256===selection.consumerCodeSha256&&
    manifest.acceptance?.status==='selected-phase-records-exercised'&&
    manifest.acceptance.receiptSha256===selection.admissionReceiptSha256&&
    manifest.privateProviderData===false&&manifest.rawSourcePayloadPublished===false&&
    manifest.acquisitionAtRuntime===false&&manifest.goldAdmitted===false&&manifest.fullProductComplete===false&&
    manifest.legacyCuratedAdmission===false&&object(manifest.sources)&&own(manifest.sources,selection.sourceId),
  'Foundation publication is not admitted');
  const source=manifest.sources[selection.sourceId];
  need(source?.sourceId===selection.sourceId&&text(source.releaseId)&&text(source.license)&&text(source.attribution)&&object(source.partitions),'Foundation source notices or partitions are missing');
  const policy=await load(selection.policy,128*1024),qualified=policy.sourceQualifications?.[selection.sourceId];
  need(policy.schema===FOUNDATION_CONTRACT&&qualified?.releaseId===source.releaseId&&
    qualified.qualificationSha256===source.qualificationSha256,'Foundation policy/source mismatch');
  const version=[selection.manifest.sha256,selection.policy.sha256,selection.sourceId].join(':');
  return {lookup:async({source:requested,barcode,cursor='',limit=20}={})=>{
    need(requested===selection.sourceId,'Lookup source does not match selected foundation release',409);
    need(typeof barcode==='string'&&/^[0-9]{4,32}$/.test(barcode),'Invalid exact lexical barcode',400);
    need(Number.isSafeInteger(limit)&&limit>=1&&limit<=20,'Invalid foundation page size',400);
    let offset=0;
    if(cursor){const c=cursorDecode(cursor);need(c.version===version&&c.source===requested&&c.barcode===barcode&&c.limit===limit&&Number.isSafeInteger(c.offset)&&c.offset>=0,'Foundation cursor belongs to another lookup',409);offset=c.offset;}
    const digest=await foundationDigest(encoder.encode(barcode));
    const prefixes=Object.keys(source.partitions).filter(p=>/^[a-f0-9]{2,8}$/.test(p)&&digest.startsWith(p)).sort((a,b)=>b.length-a.length);
    let rows=[];
    if(prefixes.length){
      const partition=await load(source.partitions[prefixes[0]]);
      need(partition?.schema==='offmenu-foundation-products/2'&&partition.sourceId===requested&&
        partition.policySha256===selection.policy.sha256&&object(partition.entries),'Invalid foundation product partition');
      if(own(partition.entries,barcode))rows=partition.entries[barcode];
    }
    need(Array.isArray(rows)&&rows.length<=10000&&offset<=rows.length&&
      new Set(rows.map(r=>r?.id)).size===rows.length,'Invalid foundation product list or offset');
    const records=[];
    for(const row of rows.slice(offset,offset+limit)){
      const c=row?.candidate,b=c?.identity?.sourceBinding;
      need(row?.schema==='offmenu-foundation-product/2'&&row.id===c?.identity?.stageRecordId&&
        c.barcode===barcode&&b?.sourceId===requested&&b.releaseId===source.releaseId&&
        b.sourceQualificationSha256===source.qualificationSha256,'Foundation record source/identity mismatch');
      const assessment=assessFoundation(c,policy);need(assessment.foundationComplete&&assessment.goldAdmitted===false&&assessment.publicationAccepted===false,'Unqualified foundation record');
      records.push({schemaVersion:'1.0',id:row.id,kind:'product',
        provenance:{...Object.fromEntries(SUBJECT.map(k=>[k,b[k]])),visibility:'public',license:source.license,attribution:source.attribution},
        curation:{schema:'offmenu-foundation-curation/2',phaseContract:FOUNDATION_CONTRACT,rawSourcePayloadPublished:false,legacyCuratedAdmission:false},
        data:{name:c.base.canonicalEnglishLabel,identifiers:[{system:'barcode',value:barcode}],
          classification:assessment.classification,canonicalEnglishKey:c.base.canonicalEnglishKey,
          canonicalConceptId:c.base.conceptId,meaningfulType:c.type,variantParameters:c.parameters,
          foundationComplete:true,fullProductComplete:false,normalizationComplete:false,goldAdmitted:false,
          automaticPlanningEligible:false,recipeNutritionJoinsAccepted:false}});
    }
    const next=offset+records.length;
    return {schemaVersion:'1.0',fieldContract:FOUNDATION_CONTRACT,source:requested,barcode,
      releaseId:manifest.releaseId,manifestSha256:selection.manifest.sha256,records,
      status:records.length?'phase-qualified-own-data':'own-data-unavailable',httpStatus:records.length?200:503,
      qualifiedSourceObservationCount:rows.length,physicalProductEquivalenceAsserted:false,externalFallback:false,
      nextCursor:next<rows.length?cursorEncode({version,source:requested,barcode,limit,offset:next}):null,
      metrics:{blobReads:reads},goldAdmitted:false,fullProductComplete:false};
  }};
}
