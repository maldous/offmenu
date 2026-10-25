// Generated Requests, wire and fake callbacks only; no network/store/mount/keys.
import test from 'node:test';
import assert from 'node:assert/strict';
import {createSourceFieldAdapter} from '../cloud/source-field-host.mjs';

const URL='https://offmenu-source-fields.invalid/__dev/source-field-slice';
const encoder=new TextEncoder();
const canonical=value=>typeof value==='bigint'?String(value):Array.isArray(value)?'['+value.map(canonical).join(',')+']':
  value!==null&&typeof value==='object'?'{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+canonical(value[k])).join(',')+'}':JSON.stringify(value);
const encode=value=>encoder.encode(canonical(value)+'\n');
const request=(query={selectedRecordId:'generated-record',offsetBytes:0},options={})=>new Request(URL,
  {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(query),...options});
function success(descriptor,text='{"generated":true}') {
  if(descriptor.offsetBytes===16777216)text='';
  else if(encoder.encode(text).length>descriptor.chunkBytes)text='0'.repeat(descriptor.chunkBytes);
  const end=descriptor.offsetBytes+encoder.encode(text).length;
  return {schema:'offmenu-source-field-operation/1',state:'slice-available',slice:{
    schema:'offmenu-source-json-slice/1',state:'slice-available',scope:'selected-record-json-byte-slice',
    selection:{recordId:descriptor.selectedRecordId,rowIdentity:{
      rowid:1,reference_record_id:descriptor.selectedRecordId,source_id:'generated-source',release_id:'generated-release',
      asset_id:'generated-asset',asset_sha256:'a'.repeat(64),source_ordinal:1,native_record_id:null,
      source_pointer:'/generated/1',original_language:'und',parsed_record_sha256:'b'.repeat(64),citation_id:null,
      citation_binding_status:'fixture-only',parse_engine_id:'generated-parser',parse_engine_version:'1',processing_status:'fixture-only'},
      binding:{store:{databaseSha256:'c'.repeat(64),qualificationSha256:'d'.repeat(64),generationId:'generated-generation'},
        operation:{receiptSha256:'e'.repeat(64),operationId:'generated-native-slice'},
        rights:{receiptSha256:'f'.repeat(64),state:'permitted'}},sourceBytes:end,candidateSourceValueCapBytes:16777216},
    encoding:'utf-8',offsetUnit:'utf-8-bytes',offsetBytes:descriptor.offsetBytes,endOffsetBytes:end,extentBytes:end,
    jsonText:text,hasMore:false,nextOffsetBytes:null,valueCompleteInThisSlice:descriptor.offsetBytes===0}};
}
const unavailable=(reason='source-json-slice-access-revoked')=>({schema:'offmenu-source-field-operation/1',
  state:'unavailable',reasonCode:reason,nextOffsetBytes:null,valueCompleteInThisSlice:false});
function fixture({authorize,executeOperation,ResponseClass=Response}={}) {
  const phases=[],operations=[];
  const adapter=createSourceFieldAdapter({Response:ResponseClass,
    authorize:authorize??((descriptor,context)=>{
      phases.push(context.phase);assert.equal(context.purpose,'source-json-slice');
      assert.equal(context.disclosure,'full-selected-source-body');assert.ok(Object.isFrozen(context));assert.ok(Object.isFrozen(descriptor));
    }),executeOperation:executeOperation??(descriptor=>{operations.push(descriptor);return encode(success(descriptor));})});
  return {adapter,phases,operations};
}
async function error(response,status,code) {
  assert.equal(response.status,status);const text=await response.text(),value=JSON.parse(text);
  assert.equal(value.state,'unavailable');assert.equal(value.reasonCode,'source-field-host-'+code);
  assert.equal(value.nextOffsetBytes,null);assert.equal(value.valueCompleteInThisSlice,false);
  for(const privateValue of ['PRIVATE_PATH','PRIVATE_BODY','PRIVATE_TOKEN'])assert.ok(!text.includes(privateValue));
  return value;
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));

test('exact internal route only; all other URLs return null without providers/body consumption',async()=>{
  const f=fixture();
  for(const url of ['http://offmenu-source-fields.invalid/__dev/source-field-slice',URL+'?',URL+'?x=1',URL+'#',URL+'#x',
    'https://user:PRIVATE_TOKEN@offmenu-source-fields.invalid/__dev/source-field-slice',
    'https://offmenu-source-fields.invalid:444/__dev/source-field-slice',
    'https://other.invalid/__dev/source-field-slice',URL+'/',URL.replace('__dev','__dev/..')]) {
    let consumed=false;
    assert.equal(await f.adapter({url,body:{getReader(){consumed=true;throw Error();}}}),null);assert.equal(consumed,false);
  }
  assert.deepEqual(f.phases,[]);assert.deepEqual(f.operations,[]);
  await error(await f.adapter(new Request(URL,{method:'GET'})),405,'method');
});

test('missing/noncallable providers fail closed; no Response fallback or native authority is invented',async()=>{
  assert.throws(()=>createSourceFieldAdapter({authorize(){},executeOperation(){}}),/SOURCE_FIELD_RESPONSE_REQUIRED/);
  for(const providers of [{},{authorize:true,executeOperation(){}},{authorize(){},executeOperation:{}}]) {
    const adapter=createSourceFieldAdapter({Response,...providers});await error(await adapter(request()),503,'provider-unavailable');
  }
});

test('wire bytes are forwarded exactly with LF/Unicode/huge number lexemes and copied before release',async()=>{
  let original,expected;
  const text='{"huge":'+'9'.repeat(6000)+',"lexical":1.2300e+004,"unicode":"café😀"}\r\n';
  const f=fixture({executeOperation(descriptor){const value=success(descriptor,text);value.slice.selection.binding.opaqueNumber=BigInt('9'.repeat(400));
      original=encode(value);expected=original.slice();return original;},
    authorize(descriptor,{phase,purpose,disclosure}){assert.equal(purpose,'source-json-slice');assert.equal(disclosure,'full-selected-source-body');
      if(phase==='before-release')original.fill(32);}});
  const response=await f.adapter(request());assert.equal(response.status,200);
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),expected);
  assert.match(response.headers.get('Cache-Control'),/private.*no-store/);assert.equal(response.headers.get('X-Content-Type-Options'),'nosniff');
});

test('policy runs before operation and release with source-body purpose; metadata-only permission is insufficient',async()=>{
  const f=fixture();const response=await f.adapter(request());assert.equal(response.status,200);
  assert.deepEqual(f.phases,['before-operation','before-release']);assert.equal(f.operations.length,1);
  assert.deepEqual(f.operations[0],{selectedRecordId:'generated-record',offsetBytes:0,chunkBytes:16384});
  let executions=0;
  const denied=fixture({authorize(_,{purpose}){const metadataOnly=true;if(metadataOnly&&purpose==='source-json-slice')throw Error('PRIVATE_BODY');},
    executeOperation(){executions++;}});
  await error(await denied.adapter(request()),403,'authorization-denied');assert.equal(executions,0);
});

test('only undefined policy success is accepted; boolean/admin objects are denied without native execution',async()=>{
  for(const grant of [true,false,null,0,'permitted',{administrator:true}]) {
    let executed=false;const f=fixture({authorize:async()=>grant,executeOperation(){executed=true;}});
    await error(await f.adapter(request()),403,'authorization-denied');assert.equal(executed,false);
  }
});

test('release-time revocation discards valid source wire; callback exceptions never echo private data',async()=>{
  const f=fixture({authorize(_,{phase}){if(phase==='before-release')throw Error('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN');}});
  await error(await f.adapter(request()),403,'authorization-denied');assert.equal(f.operations.length,1);
  const broken=fixture({executeOperation(){throw Error('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN');}});
  await error(await broken.adapter(request()),503,'operation-unavailable');
});

test('closed request rejects paths/SQL/authority/context/cursors and malformed scalar boundaries',async()=>{
  const f=fixture(),base={selectedRecordId:'generated-record',offsetBytes:0};
  for(const key of ['databasePath','sql','table','rights','admin','actor','principal','context','account','generation','connection','selection','cursor','deadline'])
    await error(await f.adapter(request({...base,[key]:'PRIVATE_BODY'})),400,'request');
  for(const query of [[],null,{}, {...base,selectedRecordId:''},{...base,selectedRecordId:7},{...base,selectedRecordId:'\ud800'},
    ...[-1,true,0.1,16777217,9007199254740992,'0'].map(offsetBytes=>({...base,offsetBytes})),
    ...[0,true,16385,'16384'].map(chunkBytes=>({...base,chunkBytes}))])await error(await f.adapter(request(query)),400,'request');
  assert.deepEqual(f.operations,[]);assert.deepEqual(f.phases,[]);
  const valid=await f.adapter(request({...base,offsetBytes:16777216,chunkBytes:1}));assert.equal(valid.status,200);
});

test('request byte cap8192 includes UTF8, accepts split Unicode and rejects duplicate escaped keys',async()=>{
  const f=fixture(),small=JSON.stringify({selectedRecordId:'generated-record',offsetBytes:0});
  const exact=' '.repeat(8192-encoder.encode(small).length)+small;
  assert.equal((await f.adapter(request(undefined,{body:exact}))).status,200);
  await error(await f.adapter(request({selectedRecordId:'é'.repeat(4096),offsetBytes:0})),413,'request-bound');
  for(const body of ['{"selectedRecordId":"x","selectedRecordId":"generated-record","offsetBytes":0}',
    '{"selectedRecordId":"x","selected\\u0052ecordId":"generated-record","offsetBytes":0}'])
    await error(await f.adapter(request(undefined,{body})),400,'request');
  const bytes=encoder.encode(JSON.stringify({selectedRecordId:'Café咖😀',offsetBytes:0}));let offset=0;
  const body=new ReadableStream({pull(controller){if(offset===bytes.length)controller.close();else controller.enqueue(bytes.slice(offset,++offset));}});
  assert.equal((await f.adapter(request(undefined,{body,duplex:'half'}))).status,200);
  await error(await f.adapter(request(undefined,{body:new Uint8Array([255])})),400,'request');
});

test('oversized stream cancels without awaiting a stalled cancel hook and never runs policy/operation',async()=>{
  const f=fixture();let cancelled=false;
  const body=new ReadableStream({start(c){c.enqueue(new Uint8Array(8193));},cancel(){cancelled=true;return new Promise(()=>{});}});
  await error(await f.adapter(request(undefined,{body,duplex:'half'})),413,'request-bound');
  assert.equal(cancelled,true);assert.deepEqual(f.phases,[]);assert.deepEqual(f.operations,[]);
});

test('abort interrupts body waiting without claiming to preempt underlying work',async()=>{
  const f=fixture(),controller=new AbortController();let cancelled=false;
  const body=new ReadableStream({start(c){c.enqueue(encoder.encode('{'));},pull(){return new Promise(()=>{});},
    cancel(){cancelled=true;return new Promise(()=>{});}});
  const req=request(undefined,{body,duplex:'half',signal:controller.signal}),pending=f.adapter(req);
  controller.abort();await error(await pending,408,'aborted');assert.equal(cancelled,true);assert.deepEqual(f.operations,[]);
});

test('timeout bounds callback waiting, handles late rejection and never authorizes late source release',async t=>{
  t.mock.timers.enable({apis:['setTimeout']});
  let began,lateReject;const started=new Promise(resolve=>{began=resolve;}),late=new Promise((_,reject)=>{lateReject=reject;});
  const f=fixture({executeOperation(){began();return late;}}),pending=f.adapter(request());
  await started;t.mock.timers.tick(5001);await error(await pending,408,'timeout');
  lateReject(Error('PRIVATE_PATH PRIVATE_BODY PRIVATE_TOKEN'));await flush();assert.deepEqual(f.phases,['before-operation']);
});

test('abort during provider wait drops late wire and does not call release authorization',async()=>{
  const controller=new AbortController();let began,finish;
  const started=new Promise(resolve=>{began=resolve;}),late=new Promise(resolve=>{finish=resolve;});
  let descriptor;const f=fixture({executeOperation(d){descriptor=d;began();return late;}});
  const pending=f.adapter(request(undefined,{signal:controller.signal}));await started;controller.abort();
  await error(await pending,408,'aborted');finish(encode(success(descriptor)));await flush();assert.deepEqual(f.phases,['before-operation']);
});

test('valid native unavailable wire is preserved verbatim with safe SQLite detail and fresh release check',async()=>{
  const value=unavailable('source-json-slice-sqlite-failure');value.sqlite={stage:'metadata',sqliteErrorCode:9,sqliteErrorName:'SQLITE_INTERRUPT'};
  const bytes=encode(value),f=fixture({executeOperation:()=>bytes});const response=await f.adapter(request());assert.equal(response.status,503);
  assert.deepEqual(new Uint8Array(await response.arrayBuffer()),bytes);assert.deepEqual(f.phases,['before-operation','before-release']);
});

test('malformed native wire/state/identity/dimensions and unsafe errors fail closed without echo',async()=>{
  const d={selectedRecordId:'generated-record',offsetBytes:0,chunkBytes:16384};
  const mutations=[v=>{v.extra='PRIVATE_BODY';},v=>{v.schema='wrong';},v=>{v.state='complete';},
    v=>{delete v.slice.selection.rowIdentity.source_id;},v=>{v.slice.selection.recordId='wrong';},
    v=>{v.slice.offsetBytes=1;},v=>{v.slice.endOffsetBytes++;},v=>{v.slice.nextOffsetBytes=1;},
    v=>{v.slice.valueCompleteInThisSlice=false;},v=>{v.slice.selection.candidateSourceValueCapBytes=16777217;},
    v=>{v.slice.selection.rowIdentity.rowid=9007199254740992;},v=>{v.slice.jsonText='\ud800';}];
  for(const mutate of mutations){const value=success(d);mutate(value);await error(await fixture({executeOperation:()=>encode(value)}).adapter(request()),502,'wire-invalid');}
  for(const wire of [null,'PRIVATE_BODY',new Uint8Array(262145),encode(success(d)).slice(0,-1),encoder.encode(canonical(success(d))+'\n\n'),
    encoder.encode(canonical(success(d)).replace('"state":"slice-available"','"state":"bad","state":"slice-available"')+'\n'),
    encode(unavailable('PRIVATE_PATH_PRIVATE_TOKEN')),encode({...unavailable(),jsonText:'PRIVATE_BODY'})])
    await error(await fixture({executeOperation:()=>wire}).adapter(request()),502,'wire-invalid');
});

test('metadata8192 and chunk16384 boundaries are checked on raw wire without reserializing source',async()=>{
  const d={selectedRecordId:'generated-record',offsetBytes:0,chunkBytes:16384};
  const value=success(d,'\x00'.repeat(16384));value.slice.selection.binding.padding='';
  const padding=8192-(encoder.encode(canonical(value.slice.selection)).length+1);assert.ok(padding>0);
  value.slice.selection.binding.padding='x'.repeat(padding);const wire=encode(value);assert.ok(wire.length<=262144);
  assert.equal((await fixture({executeOperation:()=>wire}).adapter(request())).status,200);
  value.slice.selection.binding.padding+='x';await error(await fixture({executeOperation:()=>encode(value)}).adapter(request()),502,'wire-invalid');
  const tooBig=success(d,'x'.repeat(16384));tooBig.slice.jsonText+='x';tooBig.slice.endOffsetBytes++;
  tooBig.slice.extentBytes++;tooBig.slice.selection.sourceBytes++;
  await error(await fixture({executeOperation:()=>encode(tooBig)}).adapter(request()),502,'wire-invalid');
});

test('content type/declared request overflow and broken Response are stable failures without provider effects',async()=>{
  const f=fixture();await error(await f.adapter(request(undefined,{headers:{'Content-Type':'text/plain'}})),415,'json-required');
  await error(await f.adapter(request(undefined,{headers:{'Content-Type':'application/json','Content-Length':'8193'}})),413,'request-bound');
  assert.deepEqual(f.operations,[]);
  class BadResponse{constructor(){throw Error('PRIVATE_PATH PRIVATE_TOKEN');}}
  await assert.rejects(createSourceFieldAdapter({Response:BadResponse})(request()),/SOURCE_FIELD_RESPONSE_UNAVAILABLE/);
});
