import test from 'node:test';import assert from 'node:assert/strict';
import {finishInventory,nutritionRows,packAmount,makeAutoLot,createScanGate} from '../public/checkout-model.js';
import {validateLot,matchMeals} from '../public/model.js';import {validateState} from '../cloud/state.mjs';
const lot=(id,area='Pantry',shelf='Shelf 1')=>({id,barcode:'0000000000001',name:'Rice',ingredient:'rice',quantity:100,unit:'g',location:{area,shelf}});
const session=(mode='shelf')=>({mode,area:'Pantry',shelf:'Shelf 1',items:[lot('new')],startedAt:'2026-10-12T09:00:00Z'});
test('shelf reset replaces only the selected shelf',()=>{const original=[lot('old'),lot('other-shelf','Pantry','Shelf 2'),lot('fridge','Fridge'),{...lot('legacy'),location:undefined}];const result=finishInventory(original,session());assert.deepEqual(result.map(x=>x.id),['other-shelf','fridge','legacy','new']);assert.equal(original.length,4);});
test('shopping additions retain existing stock',()=>assert.deepEqual(finishInventory([lot('old')],session('shopping')).map(x=>x.id),['old','new']));
test('empty resets cannot erase a shelf',()=>assert.throws(()=>finishInventory([lot('old')],{...session(),items:[]})));
test('shelf location survives cloud validation',()=>{const item=validateLot(lot('existing','Freezer','Top drawer'));const v=validateState({inventory:[item],profile:{country:'AU',units:'metric',servings:2},products:{},recipes:[],selections:[]});assert.equal(v.inventory[0].location.area,'Freezer');assert.equal(v.inventory[0].location.shelf,'Top drawer');});
test('missing nutrition is unknown, zero remains zero',()=>{const rows=nutritionRows({nutriments:{sugars_100g:0}});assert.equal(rows[0].value,null);assert.equal(rows[2].value,0);});

test('small salt values are not rounded to zero',()=>assert.equal(nutritionRows({nutriments:{salt_100g:.04}})[3].value,.04));

test('automatic checkout preserves labelled pack amounts',()=>{assert.deepEqual(packAmount({quantity:'1.5 kg'}),{quantity:1500,unit:'g',amountBasis:'full-pack'});assert.equal(packAmount({product_quantity:2,product_quantity_unit:'l'}).quantity,2000);});
test('unknown scan is accepted as one reviewable package',()=>{const lot=makeAutoLot('0000000000001',null);assert.equal(lot.quantity,1);assert.equal(lot.unit,'count');assert.equal(lot.needsReview,true);});
test('held barcode does not repeat; removal re-arms it',()=>{const gate=createScanGate();assert.equal(gate.read('1111',0),true);assert.equal(gate.read('1111',100),false);assert.equal(gate.read('1111',500),false);assert.equal(gate.read('2222',600),true);assert.equal(gate.read('2222',900),false);gate.miss(1800);assert.equal(gate.read('2222',1900),true);});
test('cloud profile preserves feedback and final receipt',()=>{const s={inventory:[],products:{},recipes:[],selections:[],profile:{country:'AU',units:'metric',servings:2,feedback:{sound:true,vibration:false,screen:true,light:false,speech:false},lastReceipt:{...session(),finishedAt:'2026-10-12T09:01:00Z'}}};assert.equal(validateState(s).profile.feedback.sound,true);assert.equal(validateState(s).profile.lastReceipt.items[0].name,'Rice');});
test('unreviewed ingredient suggestions do not satisfy recipes',()=>{const lot={ingredient:'rice',quantity:1000,unit:'g',needsReview:true};const r={servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};assert.equal(matchMeals([lot],[r],1,'2026-10-12')[0].status,'missing');});

test('ambiguous multipacks and unmeasured or zero pack amounts remain reviewable package counts',()=>{
 for(const product of [{quantity:'6 x 400 g'},{},{quantity:'0 g'},{product_quantity:0,product_quantity_unit:'g'}]){
  assert.deepEqual(packAmount(product),{quantity:1,unit:'count',amountBasis:'package'});
 }
});
