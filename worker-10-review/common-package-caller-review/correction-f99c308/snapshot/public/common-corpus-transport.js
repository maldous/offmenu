import {createCommonCorpus} from './common-corpus-locale.js';

const GROUPS=['resources','assertions','relations','citations','translations'];
const STATUS='all-packets-schema-identity-citation-and-scope-checked';
const HASH=/^[a-f0-9]{64}$/;
const GRAPH_KEY=/^(concepts|recipes|terminology|ontology)\/part-[0-9]+\.jsonl\.gz$/;
// Hard ceilings; callers may only lower these. All counters span the entire call.
export const COMMON_TRANSPORT_LIMITS=Object.freeze({
  manifestBytes:1024*1024, manifestFiles:4096, files:2,
  compressedFileBytes:8*1024*1024, compressedBytes:8*1024*1024,
  decompressedFileBytes:32*1024*1024, decompressedBytes:32*1024*1024,
  packetBytes:2*1024*1024, packets:1000, rows:50000, nodes:500000,
  depth:64, reads:16384, timeoutMs:30000,
});
const fail=message=>{throw Error('Common transport: '+message);};
const object=value=>value!==null&&typeof value==='object'&&!Array.isArray(value);
const integer=value=>Number.isSafeInteger(value)&&value>0;
const iri=value=>typeof value==='string'&&/^[a-z][a-z0-9+.-]*:.+$/i.test(value)&&!/[\u0000-\u0020\u007f]/.test(value);
const strings=value=>Array.isArray(value)&&value.every(item=>typeof item==='string');
const sha256=async bytes=>Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
const canonical=value=>JSON.stringify(value,(_,item)=>object(item)?Object.fromEntries(Object.keys(item).sort().map(key=>[key,item[key]])):item);
function safeKey(key){
  if(typeof key!=='string'||!key.split('/').every(part=>/^[a-z0-9]/i.test(part)&&!(/[^a-z0-9._-]/i.test(part))&&part!=='.'&&part!=='..'))fail('unsafe package path');
  return key;
}
function limitsFor(overrides){
  if(!object(overrides))fail('invalid limits');
  const limits={...COMMON_TRANSPORT_LIMITS};
  for(const [key,value] of Object.entries(overrides)){
    if(!(key in COMMON_TRANSPORT_LIMITS)||!integer(value)||value>COMMON_TRANSPORT_LIMITS[key])fail('invalid limit '+key);
    limits[key]=value;
  }
  return limits;
}
const statuses=['source-asserted','candidate','editor-authored','reviewed','verified','unknown','conflicting','superseded','needs-transcription'];
function fields(value,names){
  if(!object(value)||Object.keys(value).some(key=>!names.split(' ').includes(key)))fail('unknown/malformed object field');
}
function optional(value,key,valid){if(Object.hasOwn(value,key)&&!valid(value[key]))fail('malformed optional '+key);}
const string=value=>typeof value==='string';
const iris=value=>strings(value)&&value.every(iri);
function scope(value){
  fields(value,'visibility ownerId reuseScope');
  if(!object(value)||!['public','private','local-restricted'].includes(value.visibility)||value.visibility==='private'&&!(typeof value.ownerId==='string'&&value.ownerId.length))fail('malformed scope');
  optional(value,'ownerId',v=>string(v)&&v.length>0);optional(value,'reuseScope',string);
}
function cited(value){if(!strings(value)||!value.every(iri))fail('malformed citation references');}
function text(value){
  fields(value,'kind id language value sourceTextSha256 status citationIds');
  if(!object(value)||Object.hasOwn(value,'scope')||value.kind!=='text'||!iri(value.id)||typeof value.value!=='string'||!HASH.test(value.sourceTextSha256)||!statuses.includes(value.status)||typeof value.language!=='string'||!/^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/.test(value.language))fail('malformed source text');
  cited(value.citationIds);
}
function typed(value){
  if(!object(value))fail('malformed typed value');
  const names={text:'kind id language value sourceTextSha256 status citationIds',quantity:'kind value unitId dimension sourceValue sourceUnit sourceNotation range qualifiers countedEntityId basis preparationStateId methodId currencyCode definitionId',reference:'kind id',list:'kind items',structure:'kind fields',expression:'kind syntax value'};
  fields(value,names[value.kind]||'kind value');
  switch(value.kind){
    case 'text':text(value);break;
    case 'number':if(typeof value.value!=='number'||!Number.isFinite(value.value))fail('malformed number');break;
    case 'boolean':if(typeof value.value!=='boolean')fail('malformed boolean');break;
    case 'null':if(value.value!==null)fail('malformed null');break;
    case 'uri':if(!iri(value.value))fail('malformed IRI');break;
    case 'reference':if(!iri(value.id))fail('malformed reference');break;
    case 'identifier':case 'date':case 'datetime':case 'expression':
      if(typeof value.value!=='string'||value.kind==='expression'&&typeof value.syntax!=='string')fail('malformed fixed value');break;
    case 'list':if(!Array.isArray(value.items))fail('malformed list');value.items.forEach(typed);break;
    case 'structure':if(!object(value.fields))fail('malformed structure');Object.values(value.fields).forEach(typed);break;
    case 'quantity':
      if(!(value.value===null||typeof value.value==='number'&&Number.isFinite(value.value))||!(value.unitId===null||iri(value.unitId))||!['mass','volume','count','energy','time','length','temperature','currency','ratio','concentration','unknown'].includes(value.dimension)||!(value.sourceValue===null||['number','string'].includes(typeof value.sourceValue))||!(value.sourceUnit===null||typeof value.sourceUnit==='string')||!strings(value.qualifiers))fail('malformed quantity');
      if(value.sourceNotation!==undefined)text(value.sourceNotation);
      if(value.range!==undefined){fields(value.range,'min max');if(!['min','max'].every(key=>value.range[key]===null||typeof value.range[key]==='number'&&Number.isFinite(value.range[key])))fail('malformed quantity range');}
      for(const key of ['countedEntityId','preparationStateId','methodId','definitionId'])optional(value,key,iri);
      optional(value,'currencyCode',string);
      if(value.basis!==undefined){if(value.basis?.kind!=='quantity')fail('malformed quantity basis');typed(value.basis);}break;
    default:fail('unknown typed value');
  }
}
// Consumer safety validation, not a replacement for producer schema/semantic qualification.
function validatePacket(packet,limits,usage){
  const walk=(value,depth=0)=>{
    if(++usage.nodes>limits.nodes||depth>limits.depth)fail('node/depth budget exceeded');
    if(typeof value==='number'&&!Number.isFinite(value))fail('non-finite JSON number');
    if(value&&typeof value==='object'){
      for(const child of Object.values(value))walk(child,depth+1);
    }
  };
  walk(packet);
  if(!object(packet)||packet.schemaVersion!=='offmenu-common/1'||!GROUPS.every(key=>Array.isArray(packet[key])))fail('malformed packet graph');
  if(Object.keys(packet).some(key=>key!=='schemaVersion'&&!GROUPS.includes(key)))fail('unknown packet field');
  const ids=new Map(GROUPS.map(key=>[key,new Set()]));
  for(const key of GROUPS)for(const row of packet[key]){
    if(++usage.rows>limits.rows)fail('row budget exceeded');
    if(!object(row)||!iri(row.id)||ids.get(key).has(row.id))fail('duplicate/malformed packet identity');
    ids.get(key).add(row.id);
    if(key==='citations'){
      fields(row,'id sourceId originalRecordId originalUrl revisionId sourceDate contentSha256 license attribution rightsEvidenceUrl sourcePath scope historyUrl');
      if(typeof row.sourceId!=='string'||!row.sourceId||typeof row.originalRecordId!=='string'||!iri(row.originalUrl)||typeof row.license!=='string'||!row.license||typeof row.attribution!=='string')fail('malformed citation');
      optional(row,'revisionId',v=>v===null||string(v)||Number.isSafeInteger(v));
      optional(row,'sourceDate',v=>v===null||string(v));optional(row,'contentSha256',v=>v===null||string(v)&&HASH.test(v));
      for(const key of ['rightsEvidenceUrl','historyUrl'])optional(row,key,iri);
      optional(row,'sourcePath',string);
      scope(row.scope);
    }else{
      cited(row.citationIds);
      if(key==='translations'){
        fields(row,'id textId language value sourceTextSha256 translator method status citationIds terminologyResourceIds');
        if(Object.hasOwn(row,'scope')||!iri(row.textId)||typeof row.language!=='string'||!/^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$/.test(row.language)||typeof row.value!=='string'||!HASH.test(row.sourceTextSha256)||typeof row.translator!=='string'||!['source-published','human','machine','human-reviewed-machine'].includes(row.method)||!['published-source','draft','reviewed','stale'].includes(row.status)||!strings(row.terminologyResourceIds)||!row.terminologyResourceIds.every(iri))fail('malformed translation');
      }else{
        scope(row.scope);
        if(key==='resources'){
          fields(row,'id type identityStatus names citationIds scope additionalTypes');optional(row,'additionalTypes',iris);
          if(!iri(row.type)||!['source-scoped','candidate-join','curated-concept','identified'].includes(row.identityStatus)||!Array.isArray(row.names))fail('malformed resource');
          row.names.forEach(text);
        }else{
          fields(row,key==='assertions'?'id subjectId propertyId value status citationIds sourcePath culturalRepresentationIds scope derivation':'id subjectId predicateId objectId status citationIds scope sourcePath');
          if(!iri(row.subjectId)||!statuses.includes(row.status)||typeof row.sourcePath!=='string')fail('malformed statement');
          if(key==='assertions'){
            if(!iri(row.propertyId))fail('malformed property');typed(row.value);optional(row,'culturalRepresentationIds',iris);
            if(row.derivation!==undefined){fields(row.derivation,'methodId inputAssertionIds reviewStatus');if(!iri(row.derivation.methodId)||!iris(row.derivation.inputAssertionIds)||!statuses.includes(row.derivation.reviewStatus))fail('malformed derivation');}
          }
          else if(!iri(row.predicateId)||!iri(row.objectId))fail('malformed relation');
        }
      }
    }
  }
  // Packager guarantees packet-local citation closure; resource joins may be external.
  const checkRefs=references=>{
    if(references.some(id=>!ids.get('citations').has(id)))fail('unresolved packet citation');
  };
  const valueRefs=value=>{
    if(value.kind==='text')checkRefs(value.citationIds);
    if(value.kind==='list')value.items.forEach(valueRefs);
    if(value.kind==='structure')Object.values(value.fields).forEach(valueRefs);
    if(value.kind==='quantity'){
      if(value.sourceNotation)valueRefs(value.sourceNotation);
      if(value.basis)valueRefs(value.basis);
    }
  };
  for(const key of GROUPS)if(key!=='citations')for(const row of packet[key]){
    checkRefs(row.citationIds);
    if(key==='resources')row.names.forEach(valueRefs);
    if(key==='assertions')valueRefs(row.value);
  }
}

/** Explicit bounded slice. No discovery, implicit release acceptance, cache or pagination. */
export async function loadCommonCorpusPackage({manifestUrl,manifestSha256,acceptedReleases,files,
  allowedOrigins,fetchImpl,limits:overrides={},readerOptions={},signal}={}){
  const limits=limitsFor(overrides);
  if(typeof fetchImpl!=='function'||!HASH.test(manifestSha256))fail('injected fetch and exact manifest byte SHA-256 required');
  if(!Array.isArray(acceptedReleases)||!acceptedReleases.length||acceptedReleases.some(row=>!object(row)||typeof row.releaseId!=='string'||!row.releaseId||!HASH.test(row.manifestSha256)))fail('accepted release pins required');
  if(!acceptedReleases.some(row=>row.manifestSha256===manifestSha256))fail('unaccepted manifest pin');
  acceptedReleases=structuredClone(acceptedReleases);readerOptions=structuredClone(readerOptions);
  if(!Array.isArray(allowedOrigins)||!allowedOrigins.length)fail('origin allowlist required');
  for(const origin of allowedOrigins){const url=new URL(origin);if(url.protocol!=='https:'||url.origin!==origin)fail('unsafe allowed origin');}
  allowedOrigins=[...allowedOrigins];
  const url=new URL(manifestUrl);
  if(url.protocol!=='https:'||!allowedOrigins.includes(url.origin)||url.username||url.password||url.search||url.hash||url.href!==manifestUrl||!url.pathname.endsWith('/manifest.json'))fail('unsafe manifest URL');
  url.pathname.slice(1).split('/').forEach(safeKey);
  if(!Array.isArray(files)||!files.length||files.length>limits.files)fail('file count budget exceeded');
  const selected=structuredClone(files),keys=new Set();
  for(const file of selected){
    if(!object(file)||!GRAPH_KEY.test(safeKey(file.key))||!HASH.test(file.sha256)||keys.has(file.key))fail('invalid/duplicate selected file pin');
    keys.add(file.key);
    if(file.packetIndexes!==undefined&&(!Array.isArray(file.packetIndexes)||!file.packetIndexes.length||file.packetIndexes.length>limits.packets||!file.packetIndexes.every(n=>Number.isSafeInteger(n)&&n>=0)||new Set(file.packetIndexes).size!==file.packetIndexes.length))fail('invalid packet selection');
  }
  const usage={requests:0,reads:0,compressedBytes:0,decompressedBytes:0,packets:0,selectedPackets:0,rows:0,nodes:0};
  const deadline=performance.now()+limits.timeoutMs;
  const abort=new AbortController(),onAbort=()=>abort.abort(signal.reason);
  if(signal?.aborted)onAbort();else signal?.addEventListener('abort',onAbort,{once:true});
  const timer=setTimeout(()=>abort.abort(Error('Common transport: timeout budget exceeded')),limits.timeoutMs);
  const check=()=>{
    if(performance.now()>=deadline&&!abort.signal.aborted)abort.abort(Error('Common transport: timeout budget exceeded'));
    abort.signal.throwIfAborted();
  };
  // Also interrupts injected readers/fetches that stall; the injector remains a trusted capability.
  async function guarded(promise){
    check();let listener;
    try{return await Promise.race([promise,new Promise((_,reject)=>{listener=()=>reject(abort.signal.reason);abort.signal.addEventListener('abort',listener,{once:true});})]);}
    finally{if(listener)abort.signal.removeEventListener('abort',listener);}
  }
  async function collect(stream,max,onChunk){
    if(!stream||typeof stream.getReader!=='function')fail('streaming response body required');
    const reader=stream.getReader(),chunks=[];let size=0,complete=false;
    try{
      for(;;){
        check();if(++usage.reads>limits.reads)fail('read count budget exceeded');
        const {done,value}=await guarded(reader.read());if(done){complete=true;break;}
        if(!(value instanceof Uint8Array))fail('non-byte stream');
        size+=value.byteLength;if(size>max)fail('byte budget exceeded');onChunk?.(value.byteLength);
        chunks.push(value);
      }
    }finally{if(!complete)void reader.cancel().catch(()=>{});reader.releaseLock();}
    const bytes=new Uint8Array(size);let offset=0;for(const chunk of chunks){bytes.set(chunk,offset);offset+=chunk.length;}return bytes;
  }
  async function fetchBytes(href,max){
    check();usage.requests++;
    const response=await guarded(Promise.resolve().then(()=>fetchImpl(href,{method:'GET',redirect:'error',credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store',signal:abort.signal})));
    if(response?.status!==200||response.redirected||response.url&&response.url!==href){void response?.body?.cancel().catch(()=>{});fail('unexpected status or redirect');}
    const encoding=response.headers?.get('content-encoding');
    if(encoding&&encoding!=='identity'){void response.body?.cancel().catch(()=>{});fail('HTTP content encoding obscures package bytes');}
    const length=response.headers?.get('content-length');
    if(length!==null&&length!==undefined&&(!/^\d+$/.test(length)||Number(length)>max)){void response.body?.cancel().catch(()=>{});fail('declared byte budget exceeded');}
    return collect(response.body,max);
  }
  try{
    const manifestBytes=await fetchBytes(url.href,limits.manifestBytes);
    if(await guarded(sha256(manifestBytes))!==manifestSha256)fail('manifest byte hash mismatch');
    const decode=bytes=>new TextDecoder('utf-8',{fatal:true}).decode(bytes);
    const manifest=JSON.parse(decode(manifestBytes));
    if(manifest?.schemaVersion!=='offmenu-common-package/1'||manifest.contractVersion!=='offmenu-common-contract/1'||manifest.status!==STATUS||!acceptedReleases.some(row=>row.releaseId===manifest.releaseId&&row.manifestSha256===manifestSha256))fail('unknown/unaccepted release or package contract');
    if(!Array.isArray(manifest.files)||manifest.files.length>limits.manifestFiles)fail('manifest file budget exceeded');
    const entries=new Map();
    for(const file of manifest.files){
      if(!object(file)||!integer(file.bytes)||!HASH.test(file.sha256)||entries.has(safeKey(file.key)))fail('malformed/duplicate manifest file');
      entries.set(file.key,file);
    }
    // Preflight the complete explicit selection before any gzip request.
    let plannedBytes=0,plannedPackets=0;
    for(const file of selected){
      const entry=entries.get(file.key);
      if(!entry||entry.sha256!==file.sha256)fail('selected file pin mismatch');
      if(!integer(entry.packets)||entry.bytes>limits.compressedFileBytes||entry.packets>limits.packets)fail('file byte/packet budget exceeded');
      if(file.packetIndexes?.some(n=>n>=entry.packets))fail('packet index outside selected file');
      plannedBytes+=entry.bytes;plannedPackets+=entry.packets;
    }
    if(plannedBytes>limits.compressedBytes||plannedPackets>limits.packets)fail('aggregate compressed/packet budget exceeded');
    const graph={schemaVersion:'offmenu-common/1',...Object.fromEntries(GROUPS.map(key=>[key,[]]))};
    const merged=new Map(GROUPS.map(key=>[key,new Map()])),receipts=[];
    for(const selection of selected){
      const file=entries.get(selection.key),href=new URL(file.key,url).href;
      const compressed=await fetchBytes(href,file.bytes);
      usage.compressedBytes+=compressed.length;
      if(compressed.length!==file.bytes||await guarded(sha256(compressed))!==file.sha256)fail('file byte hash/size mismatch');
      const stream=new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'));
      const plain=await collect(stream,limits.decompressedFileBytes,size=>{
        usage.decompressedBytes+=size;if(usage.decompressedBytes>limits.decompressedBytes)fail('aggregate decompressed byte budget exceeded');
      });
      // Check raw line byte lengths before decoding or parsing JSON.
      const wanted=selection.packetIndexes===undefined?null:new Set(selection.packetIndexes);
      let start=0,count=0,selectedCount=0;
      const packetAt=end=>{
        check();
        if(end===start||end-start>limits.packetBytes)fail('empty JSONL packet or packet byte budget exceeded');
        if(++usage.packets>limits.packets)fail('packet count budget exceeded');
        const packet=JSON.parse(decode(plain.subarray(start,end)));
        validatePacket(packet,limits,usage);
        if(wanted===null||wanted.has(count)){
          usage.selectedPackets++;selectedCount++;
          for(const key of GROUPS)for(const row of packet[key]){
            const old=merged.get(key).get(row.id),serialized=canonical(row);
            if(old!==undefined&&old!==serialized)fail('conflicting graph identity '+row.id);
            if(old===undefined){merged.get(key).set(row.id,serialized);graph[key].push(row);}
          }
        }
        count++;
        check();
      };
      for(let i=0;i<plain.length;i++)if(plain[i]===10){packetAt(i);start=i+1;}
      if(start<plain.length)packetAt(plain.length);
      if(count!==file.packets)fail('manifest packet count mismatch');
      receipts.push({key:file.key,sha256:file.sha256,compressedBytes:compressed.length,decompressedBytes:plain.length,packets:count,selectedPackets:selectedCount,packetIndexes:selection.packetIndexes??null});
      check();
    }
    // The existing adapter owns scope and translation projection. No source rewrite or inferred joins.
    const corpus=await guarded(createCommonCorpus(graph,readerOptions));
    return {corpus,receipt:{schemaVersion:'offmenu-common-transport-receipt/1',releaseId:manifest.releaseId,manifestUrl:url.href,manifestSha256,manifestBytes:manifestBytes.length,files:receipts,usage:{...usage},limits,
      coverage:'explicit bounded slice; unresolved resource joins retained; no whole-corpus lookup'}};
  }finally{clearTimeout(timer);signal?.removeEventListener('abort',onAbort);abort.abort();}
}
