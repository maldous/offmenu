import test from 'node:test';
import assert from 'node:assert/strict';
import {makeAutoLot,finishInventory} from '../public/checkout-model.js';
import {validateLot} from '../public/model.js';
import {cookMeal,serveBatch,reconcileCookedStock,undoCook} from '../public/cooking-model.js';
// Every product, ingredient choice, recipe, household event and amount below is SYNTHETIC.
// This exercises accounting code only; it is not food, nutrient or user-data qualification.
const date='2026-10-26';
const product={name:'SYNTHETIC EXAMPLE · generated rice item',product_quantity:500,product_quantity_unit:'g',nutriments:{}};
const recipe={id:'synthetic-recipe',title:'SYNTHETIC accounting meal',servings:2,needsReview:false,
 ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
function received(area='Pantry'){
 const lot=validateLot({...makeAutoLot('0000000000111',product,'rice'),id:'synthetic-lot',quantity:300,amountBasis:'manual'});
 const session={mode:'shopping',area,shelf:'Synthetic shelf',startedAt:'2026-10-26T00:00:00+11:00',items:[lot]};
 return {session,inventory:finishInventory([],session)};
}
const cookedQuantity=inventory=>inventory.filter(l=>l.cookBatchId).reduce((n,l)=>n+l.quantity,0);
function cooked(){
 const {inventory}=received();
 return cookMeal({recipe,inventory,products:{},servings:2,date,mutationId:'synthetic-batch'});
}
test('synthetic scanned addition selects storage, edits quantity and supports existing void/remove actions',()=>{
 for(const area of ['Pantry','Fridge','Freezer']){
  const {session,inventory}=received(area);
  assert.equal(inventory.length,1);assert.equal(inventory[0].barcode,'0000000000111');
  assert.equal(inventory[0].quantity,300);assert.equal(inventory[0].location.area,area);
  const edited=validateLot({...inventory[0],quantity:250});assert.equal(edited.quantity,250);
  const undone=[edited].filter(l=>l.id!==session.items[0].id);
  assert.deepEqual(undone,[]); // Existing saved-item Remove action, not a new undo API.
  const draft={...session,items:session.items.filter(l=>l.id!==session.items[0].id)};
  assert.deepEqual(draft.items,[]);assert.throws(()=>finishInventory([],draft));
 }
});
test('a repeated shopping receipt cannot duplicate an inventory lot ID',()=>{
 const {session,inventory}=received();
 assert.throws(()=>finishInventory(inventory,session),/duplicate/i);
 assert.equal(inventory.length,1);assert.equal(inventory[0].quantity,300);
});
test('shelf replacement can retain the same ID after removing only the selected shelf',()=>{
 const {session,inventory}=received();
 const replacement={...session,mode:'shelf',items:[{...session.items[0],quantity:250}]};
 const next=finishInventory(inventory,replacement);
 assert.equal(next.length,1);assert.equal(next[0].quantity,250);
 assert.equal(inventory[0].quantity,300);
});
test('cooking and saved leftovers conserve synthetic portions without repeating raw deduction or serving',()=>{
 const c=cooked();assert.equal(c.inventory.find(l=>l.id==='synthetic-lot').quantity,200);
 const inventory=c.inventory.map(l=>l.cookBatchId?validateLot({...l,location:{area:'Freezer',shelf:'Synthetic cooked shelf'}}):l);
 assert.equal(reconcileCookedStock([c.batch],inventory,{date})[0].remaining,2);
 const args={portions:1,completion:50,remainder:'saved',memberId:'',date,slot:'Dinner',eventId:'synthetic-serve'};
 const first=serveBatch({...args,batch:c.batch,inventory});
 assert.equal(first.log.servings,.5);assert.equal(first.batch.events[0].saved,.5);
 assert.equal(first.batch.remaining,1.5);assert.equal(cookedQuantity(first.inventory),1.5);
 assert.equal(first.inventory.find(l=>l.cookBatchId).location.area,'Freezer');
 assert.equal(first.inventory.find(l=>l.id==='synthetic-lot').quantity,200);
 const retry=serveBatch({...args,batch:first.batch,inventory:first.inventory});
 assert.equal(retry.duplicate,true);assert.deepEqual(retry.inventory,first.inventory);
 assert.equal(retry.batch.events.length,1);assert.equal(retry.log,undefined);
 const last=serveBatch({batch:first.batch,inventory:first.inventory,portions:1.5,completion:100,remainder:'saved',date,eventId:'synthetic-last'});
 assert.equal(last.batch.remaining,0);assert.equal(cookedQuantity(last.inventory),0);
 assert.equal(first.log.servings+last.log.servings,2);
 assert.equal(last.inventory.find(l=>l.id==='synthetic-lot').quantity,200);
 assert.throws(()=>undoCook(last.batch,last.inventory));
 assert.ok(Object.values(last.log.totals).every(n=>n.known===0));
});
test('a changed serving replay must conflict rather than silently accept different consumption or leftovers',()=>{
 const c=cooked(),args={portions:1,completion:50,remainder:'saved',date,eventId:'synthetic-replay'};
 const first=serveBatch({...args,batch:c.batch,inventory:c.inventory});
 for(const change of [{completion:100},{remainder:'discarded'},{portions:.5},{memberId:'synthetic-other'},{date:'2026-10-27'},{slot:'Lunch'}]){
  assert.throws(()=>serveBatch({...args,...change,batch:first.batch,inventory:first.inventory}),/replay|changed|reconcile/i);
 }
 assert.equal(first.batch.remaining,1.5);assert.equal(first.batch.events.length,1);
});
test('cooked quantity edits reconcile once; unknown completion remains unknown and cannot be undone as raw stock',()=>{
 const c=cooked();
 assert.equal(undoCook(c.batch,c.inventory).find(l=>l.id==='synthetic-lot').quantity,300);
 const changed=c.inventory.map(l=>l.cookBatchId?{...l,quantity:1.5}:l);
 const [batch]=reconcileCookedStock([c.batch],changed,{date});
 assert.equal(batch.remaining,1.5);assert.equal(batch.events[0].quantity,.5);
 assert.equal(reconcileCookedStock([batch],changed,{date})[0].events.length,1);
 assert.throws(()=>undoCook(batch,changed));
 const unknown=serveBatch({batch,inventory:changed,portions:.5,completion:null,date,eventId:'synthetic-unknown'});
 assert.equal(unknown.log.intakeKnown,false);assert.equal(unknown.batch.events.at(-1).eaten,null);
 assert.equal(unknown.batch.events.at(-1).unknownRemainder,.5);
 assert.equal(unknown.batch.remaining,1);assert.equal(cookedQuantity(unknown.inventory),1);
});
