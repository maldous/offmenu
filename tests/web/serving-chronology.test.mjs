import assert from 'node:assert/strict';
import test from 'node:test';
import {cookMeal,serveBatch} from '../../apps/web/src/cooking-model.js';
const date='2026-11-23';
function cooked(){
 const recipe={id:'synthetic',title:'Synthetic fixture',servings:2,ingredients:[{ingredient:'synthetic base',quantity:200,unit:'g'}]};
 const inventory=[{id:'test-stock',barcode:'local:test',name:'Synthetic stock',ingredient:'synthetic base',quantity:200,unit:'g',location:{area:'Pantry',shelf:'Test'}}];
 return cookMeal({recipe,inventory,products:{},servings:2,date,planId:'first-test-meal',mutationId:'batch-test'});
}
test('a later leftover batch cannot create a past serving for an earlier planned meal',()=>{
 const {batch,inventory}=cooked(),before=structuredClone({batch,inventory});
 assert.throws(()=>serveBatch({batch,inventory,date:'2026-11-22',portions:1,completion:100,eventId:'incorrect'}),/cannot be before the cooking date/i);
 assert.deepEqual({batch,inventory},before);
 const first=serveBatch({batch,inventory,date,portions:1,completion:100,eventId:'same-day'});
 const later=serveBatch({batch:first.batch,inventory:first.inventory,date:'2026-11-24',portions:1,completion:null,eventId:'later'});
 assert.deepEqual(later.batch.events.map(e=>e.date),[date,'2026-11-24']);
 assert.equal(later.log.date,'2026-11-24');
 assert.equal(later.log.batchId,batch.id);
 assert.equal(later.batch.remaining,0);
});
