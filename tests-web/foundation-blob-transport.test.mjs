import test from 'node:test';
import assert from 'node:assert/strict';
import {createFoundationBlobTransport} from '../corpus/foundation-blob-transport.mjs';
const d={key:'own-data/foundation/test/products/ab.json.gz',bytes:3,sha256:'a'.repeat(64),uncompressedBytes:10};
const make=fetchPublicFile=>createFoundationBlobTransport({fetchPublicFile,releaseId:'test',allowedFiles:[d]});
test('fixed own origin, omitted credentials, refused redirects and bounded streaming without arrayBuffer',async()=>{
  let seen;const read=make(async(url,options)=>{seen={url,options};return new Response(Uint8Array.of(1,2,3),{headers:{'content-length':'3'}})});
  assert.deepEqual(await read(d.key,d),Uint8Array.of(1,2,3));
  assert.equal(seen.url,'https://offmenu-corpus.netlify.app/'+d.key);
  assert.deepEqual(Object.keys(seen.options).sort(),['method','redirect','credentials','cache','signal'].sort());
  assert.equal(seen.options.redirect,'error');assert.equal(seen.options.credentials,'omit');assert.equal(seen.options.cache,'no-store');
});
test('request cannot substitute keys, sizes, source namespace or digests before fetch',async()=>{
  let calls=0;const read=make(()=>{calls++;throw Error('network')});
  for(const descriptor of [{...d,key:'other'},{...d,bytes:4},{...d,sha256:'b'.repeat(64)},{...d,uncompressedBytes:11}])await assert.rejects(read(d.key,descriptor));
  await assert.rejects(read('https://external.invalid',d));assert.equal(calls,0);
  for(const key of ['own-data/foundation/test/../x','own-data/foundation/other/x','own-data/foundation/test/a?token=x'])assert.throws(()=>createFoundationBlobTransport({fetchPublicFile:()=>{},releaseId:'test',allowedFiles:[{...d,key}]}));
});
test('redirected, changed URL, non-200 and dishonest content length reject',async()=>{
  for(const type of ['redirect','url','status','length']){
    const read=make(async()=>{const r=new Response(Uint8Array.of(1,2,3),{status:type==='status'?404:200,headers:type==='length'?{'content-length':'4'}:{}});if(type==='redirect')Object.defineProperty(r,'redirected',{value:true});if(type==='url')Object.defineProperty(r,'url',{value:'https://external.invalid'});return r});
    await assert.rejects(read(d.key,d));
  }
});
test('oversize chunk is rejected and stream cancelled before reading the remainder',async()=>{
  let cancelled=false,pulls=0;
  const read=make(async()=>new Response(new ReadableStream({pull(c){pulls++;c.enqueue(Uint8Array.of(1,2,3,4));},cancel(){cancelled=true}},{highWaterMark:0})));
  await assert.rejects(read(d.key,d));assert.equal(cancelled,true);assert.equal(pulls,1);
});
test('short response and stream failure reject',async()=>{
  await assert.rejects(make(async()=>new Response(Uint8Array.of(1,2)))(d.key,d));
  await assert.rejects(make(async()=>new Response(new ReadableStream({start(c){c.error(Error('fixture'))}})))(d.key,d));
});
test('configuration snapshot is fixed and invalid/duplicate bounds reject',async()=>{
  const original={...d};const read=createFoundationBlobTransport({fetchPublicFile:async()=>new Response(Uint8Array.of(1,2,3)),releaseId:'test',allowedFiles:[original]});original.bytes=4;
  assert.equal((await read(d.key,d)).length,3);
  for(const allowedFiles of [[d,d],[{...d,bytes:1048577}],[{...d,uncompressedBytes:2097153}]])assert.throws(()=>createFoundationBlobTransport({fetchPublicFile:()=>{},releaseId:'test',allowedFiles}));
});
