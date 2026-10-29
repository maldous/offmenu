import test from 'node:test';
import assert from 'node:assert/strict';
import {cookMeal,serveBatch,undoCook} from '../../apps/web/src/cooking-model.js';
import {IDENTIFIER_DB,IDENTIFIER_RUN,DETAIL_SELECTION} from '../../apps/web/src/scanner-identity-v2.js';
import {validateLot} from '../../apps/web/src/model.js';
import {PUBLIC_PRODUCT_REFERENCE,PUBLIC_PRODUCT_SELECTION} from '../../apps/web/src/scanner-kitchen-handoff.js';

// Synthetic accounting fixtures only; no food, account or source lookup.
const date='2026-10-29';
const recipe={id:'synthetic-rice-meal',title:'Synthetic rice meal',servings:2,needsReview:false,
  ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const original={id:'synthetic-rice-lot',barcode:'0000000000111',name:'Synthetic rice',
  ingredient:'rice',quantity:300,unit:'g',amountBasis:'manual',needsReview:false};
function cook(lots=[original]){
  return cookMeal({recipe,inventory:structuredClone(lots),products:{},servings:2,date,mutationId:'synthetic-batch'});
}
function editRaw(inventory,change,id=original.id){
  return inventory.map(l=>l.id===id?validateLot({...l,...change}):l);
}
function rejectsUnchanged(batch,inventory){
  const before=structuredClone({batch,inventory});
  assert.throws(()=>undoCook(batch,inventory),/reconcile/i);
  assert.deepEqual({batch,inventory},before);
}

for(const [label,change] of [
  ['unit',{quantity:2,unit:'count'}],
  ['ingredient',{ingredient:'lentils'}],
  ['barcode',{barcode:'0000000000222'}],
  ['raw/cooked identity',{cookBatchId:'synthetic-other-batch'}],
  ['own cooked identity',{cookBatchId:'synthetic-batch'}],
]) test(`undo rejects a same-ID ${label} collision without changing inputs`,()=>{
  const c=cook();rejectsUnchanged(c.batch,editRaw(c.inventory,change));
});

const source={schema:'offmenu-identifier-observation/1',databaseSha256:'a'.repeat(64),
  runId:'synthetic-run',namespace:'barcode',lexicalValue:original.barcode,sourceId:'synthetic-source',
  releaseId:'synthetic-release',sourceRecordId:'synthetic-record',
  observationKey:{run_id:'synthetic-run',input_id:'synthetic-input',record_ordinal:0,assertion_id:1},
  detailSelectionSha256:null};
const sourceV2={...source,schema:'offmenu-identifier-observation/2',databaseSha256:IDENTIFIER_DB,
  runId:IDENTIFIER_RUN,originalLexicalValue:original.barcode,sourceLexicalValue:original.barcode,
  symbology:null,matchType:'exact',equivalence:null,disposition:'source-asserted',
  observationKey:{...source.observationKey,run_id:IDENTIFIER_RUN},detailSelectionSha256:DETAIL_SELECTION};
const published={schema:PUBLIC_PRODUCT_REFERENCE,...PUBLIC_PRODUCT_SELECTION,recordId:'offmenu:synthetic-record',
  namespace:'barcode',lexicalValue:original.barcode,provenance:{sourceId:'off',visibility:'public',
    license:'Synthetic declaration',attribution:'Synthetic fixture',url:null,sourceDate:null}};
for(const [field,reference,changed] of [
  ['sourceObservationReference',source,{...source,sourceRecordId:'synthetic-other-record'}],
  ['sourceObservationReference',sourceV2,{...sourceV2,sourceId:'synthetic-other-source'}],
  ['sourceObservationReference',source,{...source,observationKey:{...source.observationKey,assertion_id:2}}],
  ['publicProductReference',published,{...published,recordId:'offmenu:synthetic-other-record'}],
]) test(`undo rejects changed retained ${field} identity`,()=>{
  const c=cook([validateLot({...original,[field]:reference})]);
  rejectsUnchanged(c.batch,editRaw(c.inventory,{[field]:changed}));
});
for(const [field,reference] of [['sourceObservationReference',source],['sourceObservationReference',sourceV2],['publicProductReference',published]]){
  test(`undo rejects removed or newly attached ${field}`,()=>{
    const retained=cook([validateLot({...original,[field]:reference})]);
    rejectsUnchanged(retained.batch,editRaw(retained.inventory,{[field]:undefined}));
    const plain=cook();rejectsUnchanged(plain.batch,editRaw(plain.inventory,{[field]:reference}));
  });
  test(`undo accepts separately copied ${field} with reordered keys`,()=>{
    const c=cook([validateLot({...original,[field]:reference})]);
    const reordered=Object.fromEntries(Object.entries(structuredClone(reference)).reverse());
    if(reordered.observationKey)reordered.observationKey=Object.fromEntries(Object.entries(reordered.observationKey).reverse());
    const inventory=editRaw(c.inventory,{[field]:reordered});
    assert.equal(undoCook(c.batch,inventory).find(l=>l.id===original.id).quantity,300);
  });
}

test('undo validates every allocation before restoring an earlier compatible or missing lot',()=>{
  const c=cook([{...original,quantity:40},{...original,id:'synthetic-second-lot',quantity:300}]);
  assert.equal(c.batch.allocations.length,2);
  const conflicting=editRaw(c.inventory,{ingredient:'lentils'},'synthetic-second-lot');
  rejectsUnchanged(c.batch,conflicting); // First lot is absent and would otherwise be recreated.
  rejectsUnchanged(c.batch,[{...original,quantity:10},...conflicting]);
});

test('same-unit undo restores stock, preserves mutable edits and does not mutate inputs',()=>{
  const c=cook(),before=structuredClone(c);
  assert.equal(undoCook(c.batch,c.inventory).find(l=>l.id===original.id).quantity,300);
  assert.deepEqual(c,before);
  const inventory=editRaw(c.inventory,{quantity:125,name:'Corrected display',
    location:{area:'Freezer',shelf:'Changed shelf'},expires:'2027-01-01',amountBasis:'package'});
  const snapshot=structuredClone(inventory),restored=undoCook(c.batch,inventory);
  assert.deepEqual(restored,[{...inventory.find(l=>l.id===original.id),quantity:225}]);
  assert.deepEqual(inventory,snapshot);assert.deepEqual(c.batch,before.batch);
});

test('absent lot restores only the allocated quantity with original snapshot fields',()=>{
  const lot=validateLot({...original,quantity:100,sourceObservationReference:source,
    location:{area:'Pantry',shelf:'Original shelf'}}),c=cook([lot]),before=structuredClone(c);
  assert.equal(c.inventory.some(l=>l.id===lot.id),false);
  assert.deepEqual(undoCook(c.batch,c.inventory),[lot]);
  assert.deepEqual(c,before);
});

test('already-undone batch remains an identical-reference no-op even with conflicting stock',()=>{
  const c=cook(),batch={...c.batch,undone:true},inventory=editRaw(c.inventory,{quantity:2,unit:'count'});
  assert.strictEqual(undoCook(batch,inventory),inventory);
});

test('existing served-event refusal is preserved without changing inputs',()=>{
  const c=cook(),served=serveBatch({...c,portions:1,completion:100,date,eventId:'synthetic-serving'});
  const before=structuredClone(served);
  assert.throws(()=>undoCook(served.batch,served.inventory),/served batch cannot be undone/i);
  assert.deepEqual(served,before);
});

test('removing a partially consumed original lot restores the allocation, not its original total',()=>{
  const c=cook(),inventory=c.inventory.filter(l=>l.id!==original.id);
  assert.deepEqual(undoCook(c.batch,inventory),[{...original,quantity:100}]);
});

test('public source attribution edits preserve the retained product identity',()=>{
  const c=cook([validateLot({...original,publicProductReference:published})]);
  const inventory=editRaw(c.inventory,{publicProductReference:{...published,
    provenance:{...published.provenance,attribution:'Updated synthetic attribution'}}});
  assert.equal(undoCook(c.batch,inventory)[0].quantity,300);
});
