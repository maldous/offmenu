import test from 'node:test';
import assert from 'node:assert/strict';
import {planSummary} from '../../apps/web/src/menu-model.js';
import {shoppingItems} from '../../apps/web/src/integrations.js';
import {buildDocument} from '../../apps/web/src/documents.js';

const date='2026-10-29';
const recipe={id:'synthetic-rice',title:'Synthetic rice',servings:1,needsReview:false,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const meal={recipeId:recipe.id,date,servings:1};
const lot=(overrides={})=>({id:'synthetic-stock',barcode:'0000000000111',ingredient:'rice',quantity:99.9996,unit:'g',needsReview:false,...overrides});
const summary=(stock,selected=recipe,plan=[meal])=>planSummary(plan,[selected],stock,{},[date]);
const shopping=(stock,selected=recipe,plan=[meal])=>shoppingItems({plan},[selected],stock,{},date);

test('actual planSummary to shoppingItems keeps a known positive shortfall instead of a zero shopping line',()=>{
  const stock=[lot()],gap=100-stock[0].quantity;
  const missing=summary(stock).missing[0],item=shopping(stock)[0];
  assert.equal(missing.quantity,gap);
  assert.equal(item.quantity,gap);
  assert.equal(item.amount,'0.0004 g');
  assert.ok(Number.isFinite(item.quantity)&&item.quantity>0);
});

for(const deficit of [0.0002,0.000002,0.0000002])test('known deficit '+deficit+' stays positive above the existing allocation tolerance',()=>{
  const item=shopping([lot({quantity:100-deficit})])[0];
  assert.ok(Number.isFinite(item.quantity)&&item.quantity>0);
  assert.ok(Number(item.amount.split(' ')[0])>0);
});

test('ordinary positive deficits retain the current three-decimal result',()=>{
  assert.equal(summary([lot({quantity:75.5})]).missing[0].quantity,24.5);
  assert.equal(shopping([lot({quantity:75.5})])[0].amount,'24.5 g');
  assert.equal(summary([lot({quantity:99.1234})]).missing[0].quantity,0.877);
});

test('exactly covered demand produces no missing shopping line',()=>{
  assert.deepEqual(summary([lot({quantity:100})]).missing,[]);
  assert.deepEqual(shopping([lot({quantity:100})]),[]);
});

test('multiple demand entries and lots aggregate without changing the original inputs',()=>{
  const selected={...recipe,ingredients:[{ingredient:'rice',quantity:60,unit:'g'},{ingredient:'rice',quantity:40,unit:'g'},{ingredient:'milk',quantity:100,unit:'ml'}]};
  const stock=[lot({id:'first',quantity:30}),lot({id:'second',quantity:20}),lot({id:'milk',ingredient:'milk',quantity:75,unit:'ml'})];
  const before=structuredClone({selected,stock});
  assert.deepEqual(summary(stock,selected).missing.map(x=>[x.ingredient,x.quantity,x.unit]),[['rice',50,'g'],['milk',25,'ml']]);
  assert.deepEqual({selected,stock},before);
});

test('expired and review-held stock cannot erase the shopping requirement',()=>{
  for(const stock of [[lot({expires:'2026-10-28'})],[lot({needsReview:true})]]){
    assert.equal(shopping(stock)[0].quantity,100);
  }
});

test('incompatible units do not offset a known measured requirement',()=>{
  const item=shopping([lot({quantity:100,unit:'ml'})])[0];
  assert.equal(item.quantity,100);
  assert.equal(item.unit,'g');
});

test('unknown quantities and cooked-plan nutrient coverage remain explicit',()=>{
  const unknown={...recipe,ingredients:[{ingredient:'rice',quantity:null,unit:'g'}]};
  const result=summary([],unknown),item=shopping([],unknown)[0];
  assert.equal(result.unresolved,1);
  assert.deepEqual(result.missing,[]);
  assert.equal(item.quantity,undefined);
  assert.equal(item.amount,'Review source quantity');
  const cooked=summary([],recipe,[{...meal,cookBatchId:'synthetic-cooked'}]);
  assert.deepEqual(cooked.missing,[]);
  assert.deepEqual(cooked.totals.proteins_100g,{value:0,known:0,total:1});
});

test('rounding cannot turn a finite positive deficit into Infinity',()=>{
  const selected={...recipe,ingredients:[{ingredient:'rice',quantity:1e308,unit:'g'}]};
  const item=shopping([],selected)[0];
  assert.equal(item.quantity,1e308);
  assert.ok(Number.isFinite(Number(item.amount.split(' ')[0])));
});

for(const usePantry of [true,false])test('largest finite measured requirement stays finite in shopping and its document, pantry deduction '+usePantry,()=>{
  const selected={...recipe,ingredients:[{ingredient:'rice',quantity:Number.MAX_VALUE,unit:'g'}]};
  const profile={plan:[meal]},items=shoppingItems(profile,[selected],[],{},date,usePantry);
  assert.equal(items[0].quantity,Number.MAX_VALUE);
  assert.equal(items[0].amount,Number.MAX_VALUE+' g');
  assert.ok(Number.isFinite(Number(items[0].amount.split(' ')[0])));
  const doc=buildDocument('shopping',{profile,recipes:[selected],inventory:[],products:{},date,usePantry});
  assert.ok(doc.body.includes(Number.MAX_VALUE+' g'));
  assert.doesNotMatch(doc.body,/Infinity|NaN/);
});
