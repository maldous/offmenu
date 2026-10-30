import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLot,matchMeals} from '../../apps/web/src/model.js';
import {rankedMenus,pantryDuration} from '../../apps/web/src/household-model.js';

const date='2026-10-30';
const ingredient=(quantity,overrides={})=>({ingredient:'rice',quantity,unit:'g',...overrides});
const recipe=(ingredients,overrides={})=>({id:'synthetic-rice',title:'Synthetic rice',servings:1,ingredients,...overrides});
const lot=(quantity,overrides={})=>validateLot({id:'synthetic-lot',barcode:'1111',name:'Synthetic rice',...ingredient(quantity),...overrides});
const consumed=(r,stock,servings=1)=>[
  matchMeals(stock,[r],servings,date)[0],
  rankedMenus([r],stock,{},[],servings,date)[0],
];
function assertArithmeticReview(r,stock,servings=1){
  const before=structuredClone({r,stock});
  for(const row of consumed(r,stock,servings)){
    assert.equal(row.status,'needs_review');
    assert.equal(row.coverage,null);
    assert.equal(row.demandKnown,false);
    assert.ok(row.reviewReasons.includes('arithmetic_unrepresentable'));
    assert.ok(row.unknown.includes('rice'));
    assert.ok(row.missing.every(i=>Number.isFinite(i.quantity)));
  }
  assert.equal(pantryDuration([r],stock,[],servings,date,1).meals,0);
  assert.deepEqual({r,stock},before);
}

test('aggregate demand and stock overflow cannot satisfy each other through validated lots and ranking',()=>{
  assertArithmeticReview(recipe(Array.from({length:3},()=>ingredient(1e308))),[
    lot(1e308),lot(1e308,{id:'second-lot'}),
  ]);
});

test('aggregate need overflow stays unknown with absent or finite stock',()=>{
  for(const stock of [[],[lot(100)]]){
    assertArithmeticReview(recipe([ingredient(1e308),ingredient(1e308),ingredient(1)]),stock);
  }
});

test('aggregate stock overflow cannot establish coverage of finite demand',()=>{
  assertArithmeticReview(recipe([ingredient(100)]),[lot(1e308),lot(1e308,{id:'second-lot'})]);
});

for(const [name,quantity,servings,yieldCount] of [
  ['scaled overflow',1e308,2,1],
  ['intermediate multiplication overflow',1e308,2,2],
  ['division overflow',1,1,Number.MIN_VALUE],
  ['scaled underflow',Number.MIN_VALUE,1,2],
  ['intermediate multiplication underflow',Number.MIN_VALUE,.5,.5],
])test(name+' stays unresolved through matching, ranking and duration',()=>{
  assertArithmeticReview(recipe([ingredient(quantity)],{servings:yieldCount}),[lot(100)],servings);
});

test('a later finite duplicate cannot erase a scaling failure',()=>{
  assertArithmeticReview(recipe([ingredient(Number.MIN_VALUE),ingredient(100)],{servings:2}),[lot(100)]);
});

test('overflow is confined to referenced ingredient and unit keys',()=>{
  const stock=[lot(1e308),lot(1e308,{id:'second-lot'}),lot(3,{id:'count-lot',unit:'count'})];
  const safe=recipe([ingredient(1,{unit:'count'})]);
  for(const row of consumed(safe,stock)){
    assert.equal(row.status,'ready');assert.equal(row.coverage,1);assert.equal(row.demandKnown,true);
  }
  assert.equal(pantryDuration([safe],stock,[],1,date,1).meals,3);
  const mixed=recipe([ingredient(1),ingredient(20,{ingredient:'milk',unit:'ml'})]);
  for(const row of consumed(mixed,stock)){
    assert.equal(row.status,'needs_review');assert.equal(row.coverage,null);
    assert.deepEqual(row.unknown,['rice']);
    assert.deepEqual(row.missing,[{ingredient:'milk',unit:'ml',quantity:20}]);
  }
});

test('finite duplicate needs and stock retain scaling, ranking and quantity-limited duration',()=>{
  const r=recipe([ingredient(40),ingredient(60)],{servings:2});
  const stock=[lot(150),lot(150,{id:'second-lot'})];
  const before=structuredClone({r,stock});
  for(const row of consumed(r,stock,2)){
    assert.equal(row.status,'ready');assert.equal(row.coverage,1);assert.equal(row.demandKnown,true);
    assert.deepEqual(row.missing,[]);assert.deepEqual(row.reviewReasons,[]);
  }
  assert.equal(pantryDuration([r],stock,[],2,date,1).meals,3);
  for(const row of consumed(r,stock,.5)){
    assert.equal(row.status,'ready');assert.equal(row.coverage,1);
  }
  assert.equal(pantryDuration([r],stock,[],.5,date,1).meals,12);
  for(const row of consumed(r,[lot(75)],2)){
    assert.equal(row.status,'missing');assert.equal(row.coverage,0);
    assert.deepEqual(row.missing,[ingredient(25)]);
  }
  const missing=recipe([ingredient(1,{ingredient:'milk',unit:'ml'})],{id:'missing'});
  assert.deepEqual(rankedMenus([missing,r],stock,{},[],2,date).map(row=>row.id),[r.id,missing.id]);
  assert.deepEqual({r,stock},before);
});

test('large finite deficits remain finite when decimal rounding would overflow',()=>{
  for(const row of consumed(recipe([ingredient(1e308)]),[])){
    assert.equal(row.status,'missing');assert.equal(row.coverage,0);
    assert.equal(row.missing[0].quantity,1e308);
  }
  for(const row of consumed(recipe([ingredient(1e308)]),[lot(1e308)])){
    assert.equal(row.status,'ready');assert.equal(row.coverage,1);
    assert.equal(row.demandKnown,true);assert.deepEqual(row.reviewReasons,[]);
  }
});

test('unknown, zero, optional and review-held inputs preserve existing matching behavior',()=>{
  const stock=[lot(100)];
  for(const amount of [null,undefined,0]){
    for(const row of consumed(recipe([ingredient(amount)]),stock)){
      assert.equal(row.status,'needs_review');assert.equal(row.coverage,0);
      assert.equal(row.demandKnown,false);assert.deepEqual(row.unknown,['rice']);
      assert.deepEqual(row.reviewReasons,[]);
    }
  }
  for(const held of [{servingsUnknown:true},{servings:0},{needsReview:true}]){
    for(const row of consumed(recipe([ingredient(100)],held),stock)){
      assert.equal(row.status,'needs_review');assert.equal(row.coverage,null);assert.equal(row.demandKnown,false);
    }
  }
  for(const row of consumed(recipe([ingredient(100),ingredient(1e308,{optional:true})]),stock)){
    assert.equal(row.status,'ready');assert.equal(row.coverage,1);
  }
  for(const held of [lot(0),lot(100,{needsReview:true}),lot(100,{expires:'2026-10-29'})]){
    assert.equal(consumed(recipe([ingredient(100)]),[held])[0].status,'missing');
  }
});

test('frozen inputs are not mutated along matching, ranking or duration paths',()=>{
  for(const quantity of [100,1e308]){
    const r=Object.freeze(recipe(Object.freeze([Object.freeze(ingredient(quantity)),Object.freeze(ingredient(quantity))])));
    const stock=Object.freeze([Object.freeze(lot(300))]);
    const before=structuredClone({r,stock});
    consumed(r,stock);pantryDuration([r],stock,[],1,date,1);
    assert.deepEqual({r,stock},before);
  }
});
