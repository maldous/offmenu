// Unmounted internal adapter. Native providers own principal, privacy, rights and stores.
const ROUTE = 'https://offmenu-source-fields.invalid/__dev/source-field-slice';
const SCHEMA = 'offmenu-source-field-operation/1';
const REQUEST_BYTES = 8192, WIRE_BYTES = 262144, CHUNK_BYTES = 16384;
const SOURCE_BYTES = 16 * 1024 * 1024, TIME_MS = 5000;
const encoder = new TextEncoder();
const identityKeys = ['rowid','reference_record_id','source_id','release_id','asset_id',
  'asset_sha256','source_ordinal','native_record_id','source_pointer','original_language',
  'parsed_record_sha256','citation_id','citation_binding_status','parse_engine_id',
  'parse_engine_version','processing_status'];
const sliceKeys = ['schema','state','scope','selection','encoding','offsetUnit','offsetBytes',
  'endOffsetBytes','extentBytes','jsonText','hasMore','nextOffsetBytes','valueCompleteInThisSlice'];
const sliceCodes = ['selection','metadata-bound','qualification-required','qualification-unavailable',
  'qualification-mismatch','access-revoked','budget-required','budget-unavailable','budget-exhausted',
  'deadline','offset','chunk-bound','query-only-required','read-transaction-required','connection-mode',
  'encoding','row-missing','row-identity-mismatch','payload-type','extent-bound','extent-mismatch',
  'invalid-utf8','offset-not-utf8-boundary','chunk-too-small','blob-short-read','sqlite-failure',
  'blob-api-unavailable','wire-bound','internal'];
const nativeReasons = new Set([...sliceCodes.map(x=>'source-json-slice-'+x),
  ...['request','request-bound','record-mismatch','deadline-required','internal'].map(x=>'source-field-operation-'+x)]);
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const keys = (value, required, optional=[]) => object(value) &&
  required.every(key=>Object.hasOwn(value,key)) && Object.keys(value).every(key=>required.includes(key)||optional.includes(key));
const integer = (value, min, max) => Number.isSafeInteger(value) && value >= min && value <= max;
const sha = value => typeof value === 'string' && /^[0-9a-f]{64}$/.test(value);
const scalarString = value => typeof value === 'string' && value.length > 0 && value.isWellFormed();
class Failure extends Error { constructor(code,status){super(code);this.code=code;this.status=status;} }
const fail = (code,status) => {throw new Failure(code,status);};

// Reject duplicate keys and excessive nesting before JSON.parse. Record the actual
// selection byte span so its8192-byte bound never depends on reserialization.
function parseJSON(text, compact=false) {
  const stack=[];let selectionSpan=null;
  for(let i=0;i<text.length;i++) {
    const ch=text[i],top=stack.at(-1);
    if(/\s/.test(ch)){if(compact && !(ch==='\n'&&i===text.length-1))throw Error();continue;}
    if(ch==='"') {
      const start=i;
      for(i++;i<text.length;i++){if(text[i]==='\\'){i++;continue;}if(text[i]==='"')break;}
      if(i>=text.length)throw Error();
      if(top?.kind==='object'&&top.keyExpected) {
        const key=JSON.parse(text.slice(start,i+1));
        if(!key.isWellFormed()||top.seen.has(key))throw Error();
        top.seen.add(key);top.key=key;top.keyExpected=false;
      }
    } else if(ch==='{'||ch==='[') {
      const path=top?.kind==='object'&&top.path ? [...top.path,top.key] : stack.length ? null : [];
      stack.push({kind:ch==='{'?'object':'array',path,start:i,seen:new Set(),keyExpected:true});
      if(stack.length>16)throw Error();
    } else if(ch==='}'||ch===']') {
      const frame=stack.pop();if(!frame)throw Error();
      if(frame.path?.length===2&&frame.path[0]==='slice'&&frame.path[1]==='selection')selectionSpan=[frame.start,i+1];
    } else if(ch===',') {
      if(top?.kind==='object')top.keyExpected=true;
    }
  }
  if(stack.length)throw Error();
  return {value:JSON.parse(text),selectionSpan};
}

function validMetadata(value, depth=0, count={value:0}) {
  if(depth>8||++count.value>4096)return false;
  if(value===null||typeof value==='boolean')return true;
  // Unknown metadata numbers remain opaque wire lexemes (including large JSON
  // integers); every numeric control/extent/identity field is checked separately.
  if(typeof value==='number')return true;
  if(typeof value==='string')return value.isWellFormed();
  if(Array.isArray(value))return value.every(child=>validMetadata(child,depth+1,count));
  if(!object(value))return false;
  return Object.entries(value).every(([key,child])=>validMetadata(key,depth+1,count)&&validMetadata(child,depth+1,count));
}

function validateWire(wire, descriptor) {
  if(!(wire instanceof Uint8Array)||wire.byteLength<3||wire.byteLength>WIRE_BYTES)throw Error();
  // Own a stable byte copy before validation and before the policy release gate.
  const bytes=new Uint8Array(wire);
  if(bytes[0]!==123||bytes.at(-2)!==125||bytes.at(-1)!==10)throw Error();
  const text=new TextDecoder('utf-8',{fatal:true}).decode(bytes);
  const {value,selectionSpan}=parseJSON(text,true);
  if(value.schema!==SCHEMA)throw Error();
  if(value.state==='unavailable') {
    if(!keys(value,['schema','state','reasonCode','nextOffsetBytes','valueCompleteInThisSlice'],['sqlite'])||
       !nativeReasons.has(value.reasonCode)||value.nextOffsetBytes!==null||value.valueCompleteInThisSlice!==false)throw Error();
    if(Object.hasOwn(value,'sqlite')) {
      const d=value.sqlite;
      if(!keys(d,['stage','sqliteErrorCode','sqliteErrorName'])||
         !['metadata','query-only','encoding','blob-open','blob-read','blob-close'].includes(d.stage)||
         !(d.sqliteErrorCode===null||Number.isSafeInteger(d.sqliteErrorCode))||
         !(d.sqliteErrorName===null||typeof d.sqliteErrorName==='string'&&/^SQLITE_[A-Z0-9_]{1,64}$/.test(d.sqliteErrorName)))throw Error();
    }
    return {bytes,status:503};
  }
  if(value.state!=='slice-available'||!keys(value,['schema','state','slice']))throw Error();
  const p=value.slice,s=p?.selection;
  if(!keys(p,sliceKeys)||p.schema!=='offmenu-source-json-slice/1'||p.state!=='slice-available'||
     p.scope!=='selected-record-json-byte-slice'||p.encoding!=='utf-8'||p.offsetUnit!=='utf-8-bytes'||
     !keys(s,['recordId','rowIdentity','binding','sourceBytes','candidateSourceValueCapBytes'])||
     s.recordId!==descriptor.selectedRecordId||!selectionSpan||
     encoder.encode(text.slice(...selectionSpan)).byteLength+1>8192||!validMetadata(s)||
     !integer(s.candidateSourceValueCapBytes,1,SOURCE_BYTES)||!integer(s.sourceBytes,0,s.candidateSourceValueCapBytes)||
     !keys(s.rowIdentity,identityKeys)||s.rowIdentity.reference_record_id!==s.recordId)throw Error();
  for(const name of identityKeys) {
    const v=s.rowIdentity[name];
    if(name==='rowid'||name==='source_ordinal'){if(!integer(v,1,Number.MAX_SAFE_INTEGER))throw Error();}
    else if((name==='native_record_id'||name==='citation_id')&&v===null)continue;
    else if(!scalarString(v))throw Error();
  }
  const b=s.binding;
  if(!sha(s.rowIdentity.asset_sha256)||!sha(s.rowIdentity.parsed_record_sha256)||
     !object(b)||!object(b.store)||!object(b.operation)||!object(b.rights)||
     !sha(b.store.databaseSha256)||!sha(b.store.qualificationSha256)||!scalarString(b.store.generationId)||
     !sha(b.operation.receiptSha256)||!scalarString(b.operation.operationId)||
     !sha(b.rights.receiptSha256)||b.rights.state!=='permitted')throw Error();
  // Structural receipt fields are not the policy decision to disclose source bodies.
  if(!integer(p.extentBytes,0,SOURCE_BYTES)||p.extentBytes!==s.sourceBytes||
     p.offsetBytes!==descriptor.offsetBytes||!integer(p.endOffsetBytes,p.offsetBytes,p.extentBytes)||
     typeof p.jsonText!=='string'||!p.jsonText.isWellFormed()||
     encoder.encode(p.jsonText).byteLength!==p.endOffsetBytes-p.offsetBytes||
     p.endOffsetBytes-p.offsetBytes>descriptor.chunkBytes||p.hasMore!==(p.endOffsetBytes<p.extentBytes)||
     p.nextOffsetBytes!==(p.hasMore?p.endOffsetBytes:null)||p.hasMore&&p.endOffsetBytes<=p.offsetBytes||
     p.valueCompleteInThisSlice!==(p.offsetBytes===0&&p.endOffsetBytes===p.extentBytes))throw Error();
  return {bytes,status:200};
}

export function createSourceFieldAdapter({Response:ResponseClass,authorize,executeOperation}={}) {
  if(typeof ResponseClass!=='function')throw TypeError('SOURCE_FIELD_RESPONSE_REQUIRED');
  const headers={'Content-Type':'application/json; charset=utf-8','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
  const reply=(bytes,status)=>{try{return new ResponseClass(bytes,{status,headers});}catch{throw TypeError('SOURCE_FIELD_RESPONSE_UNAVAILABLE');}};
  const errorReply=(code,status)=>reply(encoder.encode(JSON.stringify({nextOffsetBytes:null,
    reasonCode:'source-field-host-'+code,schema:SCHEMA,state:'unavailable',valueCompleteInThisSlice:false})+'\n'),status);
  return async request=>{
    try{if(request?.url!==ROUTE)return null;}catch{return null;}
    const stop=performance.now()+TIME_MS,signal=request.signal;
    const current=()=>{
      if(signal?.aborted)fail('aborted',408);
      if(performance.now()>=stop)fail('timeout',408);
    };
    // Bound waiting, not the provider's execution. Late work may continue; it can
    // never cause this completed/aborted request to release source bytes.
    const wait=thunk=>new Promise((resolve,reject)=>{
      let settled=false,timer;
      const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);signal?.removeEventListener('abort',aborted);error?reject(error):resolve(value);};
      const aborted=()=>finish(new Failure('aborted',408));
      try{current();}catch(error){finish(error);return;}
      timer=setTimeout(()=>finish(new Failure('timeout',408)),Math.max(0,stop-performance.now()));
      signal?.addEventListener('abort',aborted,{once:true});
      if(signal?.aborted){aborted();return;}
      Promise.resolve().then(()=>{current();return thunk();}).then(value=>{
        try{current();finish(null,value);}catch(error){finish(error);}
      },error=>finish(error));
    });
    let reader;
    try {
      current();
      if(request.method!=='POST')fail('method',405);
      if(typeof authorize!=='function'||typeof executeOperation!=='function')fail('provider-unavailable',503);
      if(request.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase()!=='application/json')fail('json-required',415);
      const length=request.headers.get('Content-Length');
      if(length!==null){if(!/^(0|[1-9][0-9]*)$/.test(length))fail('request',400);if(Number(length)>REQUEST_BYTES)fail('request-bound',413);}
      if(!request.body||typeof request.body.getReader!=='function')fail('request',400);
      reader=request.body.getReader();let total=0;const chunks=[];
      for(;;) {
        const part=await wait(()=>reader.read());
        if(part.done)break;
        if(!(part.value instanceof Uint8Array))fail('request',400);
        total+=part.value.byteLength;if(total>REQUEST_BYTES)fail('request-bound',413);
        if(part.value.byteLength)chunks.push(new Uint8Array(part.value));
      }
      reader.releaseLock();reader=null;
      const raw=new Uint8Array(total);let cursor=0;for(const part of chunks){raw.set(part,cursor);cursor+=part.byteLength;}
      let query;
      try {
        if(raw[0]===239&&raw[1]===187&&raw[2]===191)throw Error();
        query=parseJSON(new TextDecoder('utf-8',{fatal:true}).decode(raw)).value;
      }catch{fail('request',400);}
      if(!keys(query,['selectedRecordId','offsetBytes'],['chunkBytes'])||!scalarString(query.selectedRecordId)||
         encoder.encode(query.selectedRecordId).byteLength>8192||!integer(query.offsetBytes,0,SOURCE_BYTES)||
         Object.hasOwn(query,'chunkBytes')&&!integer(query.chunkBytes,1,CHUNK_BYTES))fail('request',400);
      const descriptor=Object.freeze({selectedRecordId:query.selectedRecordId,offsetBytes:query.offsetBytes===0?0:query.offsetBytes,
        chunkBytes:query.chunkBytes??CHUNK_BYTES});
      const policy=async phase=>{
        let grant;
        try{grant=await wait(()=>authorize(descriptor,Object.freeze({phase,purpose:'source-json-slice',disclosure:'full-selected-source-body'})));}
        catch(error){if(error instanceof Failure)throw error;fail('authorization-denied',403);}
        if(grant!==undefined)fail('authorization-denied',403);
      };
      await policy('before-operation');
      let wire;
      try{wire=await wait(()=>executeOperation(descriptor));}
      catch(error){if(error instanceof Failure)throw error;fail('operation-unavailable',503);}
      let output;
      try{output=validateWire(wire,descriptor);}catch{fail('wire-invalid',502);}
      current();
      await policy('before-release');
      current();
      const response=reply(output.bytes,output.status);
      current();return response;
    } catch(error) {
      if(reader){try{Promise.resolve(reader.cancel()).catch(()=>{});}catch{}try{reader.releaseLock();}catch{}}
      else {try{if(request.body&&!request.body.locked)Promise.resolve(request.body.cancel()).catch(()=>{});}catch{}}
      return error instanceof Failure?errorReply(error.code,error.status):errorReply('unavailable',503);
    }
  };
}
