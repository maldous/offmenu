import test from 'node:test';
import assert from 'node:assert/strict';
import {diagnosticPublicResponse,DIAGNOSTIC_MEDIA} from '../../dev/public-field-capture/diagnostic-response.mjs';
const key={databaseSha256:'a'.repeat(64),run_id:'generated',input_id:'generated-input',record_ordinal:1,assertion_id:2};
const product=()=>({observationKey:{...key},sourceObservation:{source_id:'generated'},
  sourceBinding:{sourceId:'generated'},fields:{names:{state:'present',value:{en:'Generated'}},
    ingredientDeclaration:{state:'null',value:null,sourceFieldState:'unknown'},
    rawNutriments:{state:'present',value:{'source-key_100g':0}},
    nutritionSourceBasis:{state:'present',value:'serving'},
    nutrientProfile:{state:'present',value:{basis:{amount:100,unit:'g'},nutrients:{unknown:null}}}}});
const reply=()=>({operation:'observation-detail',databaseSha256:key.databaseSha256,generation:0,
  rows:[{...key}],identityMatches:[{...key}],details:{state:'loaded',detailBackend:'retained-product-federation-v1',
    detailSelectionSha256:'b'.repeat(64),sourceProducts:[product()]}});
const request=(path='/__dev/identifiers',accept=DIAGNOSTIC_MEDIA)=>new Request('http://127.0.0.1:7645'+path,{headers:{Accept:accept}});
test('ordinary, status and denied native replies pass through without a new operation',async()=>{
  for(const [req,response] of [[request(undefined,'application/json'),Response.json(reply())],
    [request('/__dev/identifiers/status'),Response.json({state:'ready'})],
    [request(),Response.json({error:'denied'},{status:403})]])assert.equal(await diagnosticPublicResponse(req,response),response);
});
test('selected diagnostic representation preserves bindings and nested values without raw-data double wrapping',async()=>{
  const native=reply(),response=await diagnosticPublicResponse(request(),Response.json(native));
  assert.equal(response.status,200);assert.equal(response.headers.get('Content-Type'),DIAGNOSTIC_MEDIA);
  assert.match(response.headers.get('Vary'),/Accept/);const data=await response.json(),out=data.sourceProducts[0];
  assert.deepEqual(out.fields,native.details.sourceProducts[0].fields);assert.deepEqual(out.binding.observationKey,key);
  assert.equal(out.fields.rawNutriments.value['source-key_100g'],0);assert.equal(out.fields.ingredientDeclaration.value,null);
  assert.equal(out.fields.ingredientDeclaration.sourceFieldState,'unknown');assert.equal(data.generation,0);
  assert.equal(out.fields.nutritionSourceBasis.value,'serving');assert.equal(out.fields.nutrientProfile.value.basis.amount,100);
});
test('unavailable native details retain their original state and do not become empty success',async()=>{
  const native=reply();native.details={state:'unavailable',detailBackend:'retained-product-federation-v1',reasonCode:'generated-missing'};
  const response=Response.json(native);assert.equal(await diagnosticPublicResponse(request(),response),response);
});
test('binding mismatch, already captured products and oversized input fail closed without partial output',async()=>{
  const bad=reply();bad.details.sourceProducts[0].observationKey.assertion_id=9;
  const wrapped=reply();wrapped.details.sourceProducts[0]={schema:'offmenu-public-field-capture/1',binding:{},fields:{}};
  for(const native of [bad,wrapped,{...reply(),padding:'x'.repeat(262145)}]){
    const response=await diagnosticPublicResponse(request(),Response.json(native));assert.equal(response.status,503);
    assert.deepEqual(await response.json(),{error:'PUBLIC_DIAGNOSTIC_CAPTURE_UNAVAILABLE'});
  }
});
