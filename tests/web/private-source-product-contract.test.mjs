import test from 'node:test';
import assert from 'node:assert/strict';
import {createPrivateSourceProductRoutes,SNAPSHOT,SOURCE_SCOPE} from '../../integrations/staged/private-product-lookup/private-source-product-route.mjs';
import {createPrivateSourceProductComposition} from '../../integrations/staged/private-product-lookup/current-entry-binding/private-source-product-composition.mjs';
import {createNativePrivateSourceLookup} from '../../integrations/staged/private-product-lookup/current-entry-binding/native-private-source-lookup.mjs';

// Generated in-process contracts only: no listener, real identity or source file.
const origin='http://127.0.0.1:7645';
const env={DEV_INTERACTIVE:true,DEV_IDENTITY_TRANSPORT:'real-existing-netlify'};
const selected={enabled:true,snapshotSha256:SNAPSHOT,sourceScopeSha256:SOURCE_SCOPE};
const request=(query='barcode=0000123456789')=>new Request(origin+'/api/private-source-products?'+query);
const verified={mode:'netlify',verifiedUser:async()=>({id:'generated-test-subject'})};
const dto=()=>({snapshotSha256:SNAPSHOT,barcode:'0000123456789',reviewStatus:'unreviewed',goldAdmitted:false,canonicalEquivalence:false,products:[]});

test('disabled and anonymous requests cannot reach source transport',async()=>{
  let calls=0;
  const fetchImpl=async()=>{calls++;throw Error('must not read a source');};
  assert.equal((await createPrivateSourceProductRoutes({fetchImpl})(request(),env,{runtime:verified})).status,404);
  const route=createPrivateSourceProductRoutes({...selected,fetchImpl});
  assert.equal((await route(request(),env,{runtime:{mode:'netlify',verifiedUser:async()=>null}})).status,401);
  assert.equal((await route(request(),env,{runtime:{mode:'netlify',verifiedUser:async()=>{throw Error('unavailable');}}})).status,503);
  assert.equal(calls,0);
});

test('unselected environments, origins and query shapes fail before source reads',async()=>{
  let calls=0;
  const route=createPrivateSourceProductRoutes({...selected,fetchImpl:async()=>{calls++;throw Error('not selected');}});
  for(const [req,bindings] of [
    [new Request('http://localhost:7645/api/private-source-products?barcode=1'),env],
    [new Request('http://127.0.0.1:17646/api/private-source-products?barcode=1'),env],
    [request(),{...env,DEV_INTERACTIVE:false}],
    [request(),{...env,DEV_IDENTITY_TRANSPORT:'fixture-only'}],
    [new Request(request(),{headers:{Origin:'https://example.invalid'}}),env],
  ])assert.equal((await route(req,bindings,{runtime:verified})).status,403);
  for(const query of ['barcode=1&barcode=2','barcode=1&raw=1','barcode=','barcode=123%27OR1%3D1','barcode='+('1'.repeat(65))])
    assert.equal((await route(request(query),env,{runtime:verified})).status,400);
  assert.equal(calls,0);
});

test('same-session composition keeps identity and credentials out of native request and response',async()=>{
  let authCalls=0,nativeCalls=0;
  const identityApp={async fetch(req){authCalls++;assert.equal(new URL(req.url).pathname,'/api/auth-page/session');assert.equal(req.headers.get('Cookie'),'generated-only');return Response.json({authenticated:true,userId:'generated-test-subject',mode:'netlify'});}};
  const composition=createPrivateSourceProductComposition({identityApp,options:{...selected,fetchImpl:async(url,init)=>{
    nativeCalls++;assert.equal(new URL(url).origin,'https://offmenu-private-product-source.invalid');
    assert.equal(new URL(url).searchParams.get('barcode'),'0000123456789');
    assert.deepEqual([...new Headers(init.headers).keys()],['x-offmenu-private-lookup']);
    assert.equal(init.redirect,'error');return Response.json(dto());
  }}});
  const response=await composition.handle(new Request(request(),{headers:{Cookie:'generated-only',Authorization:'generated-only'}}),env,{});
  assert.equal(response.status,200);assert.equal(response.headers.get('Cache-Control'),'no-store');
  const text=await response.text();assert.equal(text.includes('generated-test-subject'),false);assert.equal(text.includes('generated-only'),false);
  assert.equal(authCalls,1);assert.equal(nativeCalls,1);
});

test('oversized or promoted source DTOs fail closed',async()=>{
  for(const value of [{...dto(),goldAdmitted:true},{...dto(),canonicalEquivalence:true},{...dto(),products:Array(9).fill({})}]){
    const route=createPrivateSourceProductRoutes({...selected,fetchImpl:async()=>Response.json(value)});
    assert.equal((await route(request(),env,{runtime:verified})).status,503);
  }
  const route=createPrivateSourceProductRoutes({...selected,fetchImpl:async()=>new Response('x'.repeat(65537))});
  assert.equal((await route(request(),env,{runtime:verified})).status,503);
});

test('native service rejects credentials and missing actual owner authority without opening a snapshot',async()=>{
  const req=new Request('https://offmenu-private-product-source.invalid/lookup?barcode=0000123456789',{headers:{'X-OffMenu-Private-Lookup':'prior10300'}});
  assert.equal((await createNativePrivateSourceLookup()(req)).status,404);
  assert.equal((await createNativePrivateSourceLookup({enabled:true})(req)).status,503);
  const withCredentials=new Request(req,{headers:{'X-OffMenu-Private-Lookup':'prior10300',Cookie:'generated-only'}});
  assert.equal((await createNativePrivateSourceLookup({enabled:true})(withCredentials)).status,400);
});
