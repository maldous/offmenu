import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {cookMeal,serveBatch,validateBatches} from '../public/cooking-model.js';
import {createCookingWitness,captureNutrientInput,copyCookingWitness,preserveCookingWitnesses} from '../public/cooking-witness.js';
import {createLotNutritionSelection} from '../public/lot-nutrition.js';
import {asOffNutriments} from '../public/unified-data.js';
import {nutritionForLot} from '../public/lot-nutrition.js';
import {validateInsights} from '../public/insights-model.js';
import {NUTRIENTS} from '../public/menu-model.js';
import {validateState} from '../cloud/state.mjs';
import {createPantryBackup,restorePantryBackup} from '../public/pantry-backup.js';
import {kitchenProjection} from '../public/sync-model.js';
import {finishCookingWitnessState} from '../cloud/cooking-witness-parity.mjs';

const date='2026-10-29';
function fixture({visibility='public',version=true}={}){
 const recipe={id:'rice',title:'Rice v1',servings:2,source:'https://example.invalid/recipe/v1',license:'CC0',attribution:'Synthetic source',...(version?{version:'v1'}:{}),provenance:{sourceId:'synthetic',recordId:'rice-variant',releaseId:'edition-v1',manifestSha256:'a'.repeat(64),visibility,privateNote:'UNRELATED_PRIVATE_NOTE'},ingredients:[{ingredient:'rice',quantity:100,unit:'g',raw:'100 g rice'}],instructions:['Cook v1.'],privateNotes:'UNRELATED_PRIVATE_NOTE'};
 const profile={schemaVersion:'1.0',kind:'nutrientProfile',id:'usda-files:nutrientProfile:fixture-v1',countries:[],provenance:{sourceId:'usda-files',recordId:'fixture-v1',releaseId:'source-v1',license:'CC0',attribution:'Synthetic source',visibility},data:{status:'candidate',basis:{amount:100,unit:'g',state:'as-described'},nutrients:{fat:{value:7,unit:'g'},protein:{value:0,unit:'g'},sugars:{value:null,unit:'g',qualifier:'unknown'}}}};
 const lot={id:'raw',barcode:'1111',name:'Rice',ingredient:'rice',quantity:200,unit:'g'};lot.nutritionSelection=createLotNutritionSelection(lot,profile,asOffNutriments(profile,'g'),{confirmed:true});
 return {recipe,profile,lot,products:{},inventory:[lot]};
}
function cooked(f=fixture()){return {f,...cookMeal({recipe:f.recipe,inventory:f.inventory,products:f.products,servings:2,date,mutationId:'batch-a',planId:'plan-a'})};}
function seedWitness(c){if(!c.batch.cookingWitness)c.batch.cookingWitness=createCookingWitness(c.f.recipe,c.batch.id,c.batch.allocations,c.batch.allocations.map(a=>captureNutrientInput(a,nutritionForLot(a.original,c.f.products))));return c;}
function served(c){return serveBatch({batch:c.batch,inventory:c.inventory,portions:1,completion:100,date,eventId:'event-a'});}
function state(c,s){return {inventory:s.inventory,products:c.f.products,recipes:[c.f.recipe],selections:[],profile:{country:'AU',units:'metric',servings:2,batches:[s.batch],history:[s.log]}};}

test('new cook captures exact recipe version/source and actual ingredient inputs',()=>{
 const c=cooked(),w=c.batch.cookingWitness;assert.ok(w,'cooking-time witness required');
 assert.equal(w.recipe.version,'v1');assert.equal(w.recipe.provenance.releaseId,'edition-v1');assert.equal(w.recipe.provenance.manifestSha256,'a'.repeat(64));assert.equal(w.recipe.ingredients[0].quantity,100);assert.equal(w.allocations[0].quantity,100);
});
test('recipe v2 and changed current profile cannot mutate old cooking inputs',()=>{
 const c=seedWitness(cooked());c.f.recipe.version='v2';c.f.recipe.ingredients[0].quantity=900;c.f.recipe.instructions[0]='Cook v2.';c.f.lot.nutritionSelection.sourceProfile.nutrients.protein.value=11;
 assert.equal(c.batch.cookingWitness.recipe.version,'v1');assert.equal(c.batch.cookingWitness.recipe.ingredients[0].quantity,100);assert.equal(c.batch.cookingWitness.recipe.instructions[0],'Cook v1.');assert.equal(c.batch.allocations[0].original.nutritionSelection.sourceProfile.nutrients.protein.value,0);
 assert.equal(c.batch.cookingWitness.nutrientInputs[0].sourceNutrientContext.protein.value,0);assert.equal(c.batch.cookingWitness.nutrientInputs[0].sourceNutrientContext.sugars.value,null);
});
test('serving retains the cooking witness without consulting current recipe',()=>{
 const c=seedWitness(cooked());c.f.recipe.version='v2';const s=served(c);assert.deepEqual(s.log.cookingWitness,c.batch.cookingWitness);assert.equal(s.log.totals.fat_100g.value,3.5);
});
test('history normalization preserves the batch-bound witness',()=>{
 const c=seedWitness(cooked()),s=served(c);s.log.cookingWitness=c.batch.cookingWitness;assert.deepEqual(validateInsights({history:[s.log]}).history[0].cookingWitness,c.batch.cookingWitness);
});
test('local JSON and current cloud validator retain v1 while recipe is now v2',()=>{
 const c=seedWitness(cooked()),s=served(c);s.log.cookingWitness=c.batch.cookingWitness;c.f.recipe.version='v2';const input=JSON.parse(JSON.stringify(state(c,s))),out=validateState(input);
 assert.equal(out.recipes[0].version,'v2');assert.equal(out.profile.batches[0].cookingWitness.recipe.version,'v1');assert.equal(out.profile.history[0].cookingWitness.recipe.version,'v1');assert.equal(out.profile.history[0].totals.fat_100g.value,3.5);
});
test('ordinary pantry backup/restore retains captured provenance and totals',()=>{
 const c=seedWitness(cooked()),s=served(c);s.log.cookingWitness=c.batch.cookingWitness;c.f.recipe.version='v2';const out=restorePantryBackup(JSON.parse(JSON.stringify(createPantryBackup(state(c,s))))).state;
 assert.equal(out.profile.history[0].cookingWitness.recipe.version,'v1');assert.equal(out.profile.history[0].totals.fat_100g.value,3.5);
});
test('absent upstream version stays unknown and legacy meals are never backfilled',()=>{
 const c=cooked(fixture({version:false}));assert.equal(c.batch.cookingWitness?.sourceVersionState,'unknown');assert.equal(c.batch.cookingWitness.recipe.version,undefined);
 const legacy=structuredClone(c.batch);delete legacy.cookingWitness;assert.equal(validateBatches([legacy])[0].cookingWitness,undefined);
});
test('retry after recipe edit returns the original batch without recomputation',()=>{
 const c=seedWitness(cooked());c.f.recipe.version='v2';const retry=cookMeal({recipe:c.f.recipe,inventory:c.inventory,products:c.f.products,servings:2,date,mutationId:'batch-a',batches:[c.batch]});assert.equal(retry.duplicate,true);assert.equal(retry.batch,c.batch);assert.equal(retry.batch.cookingWitness.recipe.version,'v1');
});
test('private or unknown-public witness content is not added to shared projections',()=>{
 for(const visibility of ['private','unknown']){const c=seedWitness(cooked(fixture({visibility}))),s=served(c);const shared=kitchenProjection(state(c,s));assert.equal(shared.profile.batches[0].cookingWitness,undefined);}
 const c=seedWitness(cooked()),s=served(c),shared=kitchenProjection(state(c,s));assert.equal(shared.profile.batches[0].cookingWitness.recipe.version,'v1');assert.ok(!JSON.stringify(c.batch.cookingWitness).includes('UNRELATED_PRIVATE_NOTE'));
});
test('batch and history validators reject a witness rebound to a different meal',()=>{
 const c=seedWitness(cooked()),s=served(c),bad=structuredClone(c.batch.cookingWitness);bad.batchId='other-batch';
 assert.throws(()=>validateBatches([{...c.batch,cookingWitness:bad}]),/witness/i);assert.throws(()=>validateInsights({history:[{...s.log,cookingWitness:bad}]}),/witness/i);
});
test('exact retained server-history helper preserves the same witness and zero/unknown behavior',()=>{
 const c=seedWitness(cooked()),s=served(c);s.log.cookingWitness=c.batch.cookingWitness;s.log.servings=0;s.log.completion=null;s.log.intakeKnown=false;delete s.log.servedPortions;
 const helper=readFileSync(new URL('../evidence/server-history-helper.js',import.meta.url),'utf8');
 const result=vm.runInNewContext(helper+';lg(profile)',{profile:{history:[s.log]},T:NUTRIENTS,__offmenuCookingWitness198:{preserveCookingWitnesses}});
 const out=JSON.parse(JSON.stringify(result));assert.deepEqual(out.history[0].cookingWitness,c.batch.cookingWitness);assert.equal(out.history[0].servedPortions,undefined);assert.equal(out.history[0].intakeKnown,false);
});
test('final server-state seam copies only validated witness fields without recomputing values',()=>{
 const c=seedWitness(cooked()),s=served(c);s.log.cookingWitness=c.batch.cookingWitness;const input=state(c,s),normalized=validateState(input);delete normalized.profile.history[0].cookingWitness;
 const out=finishCookingWitnessState(input,normalized);assert.deepEqual(out.profile.history[0].cookingWitness,c.batch.cookingWitness);assert.deepEqual(out.profile.history[0].totals,normalized.profile.history[0].totals);assert.equal(out.inventory,normalized.inventory);
 const bad=structuredClone(input);bad.profile.history[0].cookingWitness.batchId='other';assert.throws(()=>finishCookingWitnessState(bad,normalized),/witness/i);
});

test('retained source references do not acquire a public visibility grant',()=>{
 const f=fixture(),c=seedWitness(cooked(f));const a=structuredClone(c.batch.allocations[0]);
 a.barcode='x'.repeat(512);a.original.sourceObservationReference={schema:'offmenu-identifier-observation/1',sourceRecordId:'retained-source',privateNote:'SOURCE_REFERENCE_PRIVATE_NOTE'};
 const w=createCookingWitness(f.recipe,c.batch.id,[a],[captureNutrientInput(a,nutritionForLot(a.original,f.products))]);
 assert.equal(w.allocations[0].barcode.length,512);assert.equal(w.allocations[0].sourceReferences.sourceObservationReference.sourceRecordId,'retained-source');assert.equal(w.visibility,'unknown');
 const shared=kitchenProjection({...state(c,served(c)),profile:{batches:[{...c.batch,cookingWitness:w}]}});assert.equal(shared.profile.batches[0].cookingWitness,undefined);assert.ok(!JSON.stringify(shared.profile.batches).includes('SOURCE_REFERENCE_PRIVATE_NOTE'));
});

import * as serverWitness from '../cloud/cooking-witness-parity.mjs';
function citationFixture(visibility){return {id:'source-citation',sourceId:'synthetic',recordId:'citation-v1',...(visibility===undefined?{}:{visibility}),citations:[{id:'nested-citation',sourceId:'synthetic',visibility:'public'}]};}
test('public recipe cannot publish private or unqualified retained citations',()=>{
 for(const visibility of ['private','unknown',undefined,'public']){
  const f=fixture();f.recipe.provenance.citations=[citationFixture(visibility)];const c=cooked(f),w=c.batch.cookingWitness;
  assert.equal(w.visibility,visibility==='public'?'public':visibility==='private'?'private':'unknown');assert.equal(w.recipe.provenance.citations[0].recordId,'citation-v1');assert.equal(w.recipe.provenance.citations[0].citations[0].id,'nested-citation');
  const shared=kitchenProjection(state(c,served(c)));assert.equal(!!shared.profile.batches[0].cookingWitness,visibility==='public');
 }
});
test('selected nutrient provenance retains citations and uses all child visibility',()=>{
 for(const visibility of ['private','unknown',undefined,'public']){
  const f=fixture();f.lot.nutritionSelection.provenance.citations=[citationFixture(visibility)];const c=cooked(f),w=c.batch.cookingWitness;
  assert.equal(w.visibility,visibility==='public'?'public':visibility==='private'?'private':'unknown');assert.equal(w.nutrientInputs[0].provenance.citations[0].recordId,'citation-v1');
  assert.equal(!!kitchenProjection(state(c,served(c))).profile.batches[0].cookingWitness,visibility==='public');
 }
});
test('nested source-reference evidence cannot inherit a public grant from its parent',()=>{
 for(const visibility of ['private','unknown',undefined,'public']){
  const c=cooked(),a=structuredClone(c.batch.allocations[0]);a.original.sourceObservationReference={visibility:'public',observation:{provenance:{visibility:'public',citations:[citationFixture(visibility)]}}};
  const w=createCookingWitness(c.f.recipe,c.batch.id,[a],[captureNutrientInput(a,nutritionForLot(a.original,c.f.products))]);
  assert.equal(w.visibility,visibility==='public'?'public':visibility==='private'?'private':'unknown');assert.equal(w.allocations[0].sourceReferences.sourceObservationReference.observation.provenance.citations[0].recordId,'citation-v1');
  const shared=kitchenProjection({...state(c,served(c)),profile:{batches:[{...c.batch,cookingWitness:w}]}});assert.equal(!!shared.profile.batches[0].cookingWitness,visibility==='public');
 }
});
test('server parity shared-batch contract rechecks misleading public flags and preserves batch fields',()=>{
 assert.equal(typeof serverWitness.sharedCookingBatch,'function');
 const c=cooked(),w=structuredClone(c.batch.cookingWitness);w.recipe.provenance.citations=[citationFixture('private')];w.visibility='public';
 const filtered=serverWitness.sharedCookingBatch({...c.batch,cookingWitness:w});assert.equal(filtered.cookingWitness,undefined);assert.equal(filtered.id,c.batch.id);assert.equal(filtered.totals,c.batch.totals);assert.equal(filtered.events,c.batch.events);
 assert.equal(copyCookingWitness(w).visibility,'private');
 w.recipe.provenance.citations[0].visibility='public';assert.equal(serverWitness.sharedCookingBatch({...c.batch,cookingWitness:w}).cookingWitness.visibility,'public');
 delete w.recipe.provenance.citations[0].visibility;assert.equal(serverWitness.sharedCookingBatch({...c.batch,cookingWitness:w}).cookingWitness,undefined);
});
test('retained per-nutrient evidence context also gates shared visibility',()=>{
 for(const visibility of ['private','unknown',undefined,'public']){
  const f=fixture();f.lot.nutritionSelection.sourceProfile.nutrients.protein.provenance={visibility:'public',citations:[citationFixture(visibility)]};const c=cooked(f),w=c.batch.cookingWitness;
  assert.equal(w.visibility,visibility==='public'?'public':visibility==='private'?'private':'unknown');assert.equal(w.nutrientInputs[0].sourceNutrientContext.protein.provenance.citations[0].recordId,'citation-v1');
  assert.equal(!!serverWitness.sharedCookingBatch(c.batch).cookingWitness,visibility==='public');
 }
});
