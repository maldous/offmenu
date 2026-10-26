import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createOffPhotoRoutes} from '../cloud/off-photos.mjs';
import {createOffMenuHandler} from '../cloud/handler.mjs';
import {OFF_PHOTOS,selectedPublisherPhotos} from '../public/off-photo-catalogue.js';
import {selectProductVisual} from '../public/product-visual-selector.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';

const jpeg=new Uint8Array([255,216,255,224,0,0,255,217]);
const request=(path=OFF_PHOTOS[0].path,options={})=>new Request('https://app.invalid'+path,options);
const image=()=>new Response(jpeg,{headers:{'Content-Type':'image/jpeg','Content-Length':String(jpeg.length)}});

test('fixed publisher JPG route relays exact bytes without forwarding user cookies or credentials',async()=>{
  const calls=[];const route=createOffPhotoRoutes({fetchImpl:async(url,options)=>{calls.push({url,options});return image();}});
  for(const photo of OFF_PHOTOS){const response=await route(request(photo.path,{headers:{Cookie:'synthetic-private-cookie',Authorization:'Bearer synthetic-private'}}));
    assert.equal(response.status,200);assert.deepEqual(new Uint8Array(await response.arrayBuffer()),jpeg);
    assert.match(response.headers.get('Link'),/rel="license"/);assert.equal(response.headers.get('X-Content-Type-Options'),'nosniff');}
  assert.deepEqual(calls.map(call=>call.url),OFF_PHOTOS.map(photo=>photo.url));
  for(const {options} of calls){assert.equal(options.redirect,'error');assert.equal(options.credentials,'omit');assert.deepEqual(options.headers,{Accept:'image/jpeg'});}
});

test('arbitrary URL, unknown catalogue path, query and unsafe method never initiate an upstream fetch',async()=>{
  let calls=0;const route=createOffPhotoRoutes({fetchImpl:()=>{calls++;throw Error('Unexpected fetch');}});
  assert.equal((await route(request('/api/off-photos/unknown.jpg'))).status,404);
  assert.equal((await route(request(OFF_PHOTOS[0].path+'?url=https://other.invalid/private'))).status,404);
  assert.equal((await route(request(OFF_PHOTOS[0].path,{method:'POST'}))).status,405);
  assert.equal(await route(request('/api/state')),null);assert.equal(calls,0);
});

test('redirects, HTML, misleading JPEG types and declared or streamed overflow fail without image success',async()=>{
  const bad=[new Response(null,{status:302}),new Response('<html>',{headers:{'Content-Type':'text/html'}}),
    new Response('not a jpeg',{headers:{'Content-Type':'image/jpeg'}}),
    new Response(jpeg,{headers:{'Content-Type':'image/jpeg','Content-Length':'1000'}}),
    new Response(new Uint8Array(65),{headers:{'Content-Type':'image/jpeg'}})];
  for(const response of bad){const route=createOffPhotoRoutes({maxBytes:64,fetchImpl:async()=>response});
    const actual=await route(request());assert.equal(actual.status,502);assert.equal((await actual.json()).error,'PUBLISHER_PHOTO_UNAVAILABLE');}
});

test('aggregate deadline bounds a hung fetch and a stalled image body',async()=>{
  const hung=createOffPhotoRoutes({timeoutMs:15,fetchImpl:()=>new Promise(()=>{})});
  assert.equal((await hung(request())).status,502);
  let cancelled=false;const stalled=createOffPhotoRoutes({timeoutMs:15,fetchImpl:async()=>new Response(
    new ReadableStream({pull(){return new Promise(()=>{});},cancel(){cancelled=true;}}),{headers:{'Content-Type':'image/jpeg'}})});
  assert.equal((await stalled(request())).status,502);assert.equal(cancelled,true);
});

test('exact current source observation binds the separately observed photo, with unknown snapshot image membership',()=>{
  const {reference,detail}=photoFixture();const photos=selectedPublisherPhotos(reference,detail);assert.equal(photos.length,1);
  assert.equal(photos[0].provenance.releaseId,null);assert.match(photos[0].provenance.relationship,/unverified/);
  const visual=selectProductVisual({sourceObservationReference:reference,selectedProductRecordId:detail.referenceRecordId,
    photoCandidates:photos,permittedLocalAssets:OFF_PHOTOS.map(photo=>photo.path),canonicalConcepts:[],categoryMappings:[]});
  assert.equal(visual.tier,'product-photo');assert.equal(visual.src,OFF_PHOTOS[0].path);
  assert.equal(visual.caption,'Current publisher photo');assert.match(visual.rights.attribution,/foodless/);assert.match(visual.rights.license,/CC BY-SA/);
  for(const changed of [{...reference,sourceId:'usda-files'},{...reference,sourceLexicalValue:'different'},
    {...reference,observationKey:{...reference.observationKey,assertion_id:10}}, {...reference,releaseId:'different'}])
    assert.deepEqual(selectedPublisherPhotos(changed,detail),[]);
});

test('actual handler mounts the fixed image route and preserves exact existing CSP source bytes',async()=>{
  const handler=createOffMenuHandler({photoFetch:async()=>image()});
  assert.equal((await handler.fetch(request(),{},{})).status,200);
  const source=await readFile(new URL('../cloud/handler.mjs',import.meta.url),'utf8');
  assert.match(source,/img-src 'self' blob:; media-src 'self' blob:; connect-src 'self' https:\/\/offmenu-corpus.netlify.app;/);
  assert.equal(source.includes("img-src 'self' blob: https://images.openfoodfacts.org"),false);
});
