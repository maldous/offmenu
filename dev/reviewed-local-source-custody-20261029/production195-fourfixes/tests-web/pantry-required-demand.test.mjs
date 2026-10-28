import test from 'node:test';
import assert from 'node:assert/strict';
import {pantryDuration} from '../public/household-model.js';
const date='2026-10-29';
const rice={id:'rice',title:'Measured rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const optional={id:'optional',title:'Optional garnish',servings:1,ingredients:[{ingredient:'rice',quantity:5,unit:'g',optional:true}]};
const stock=[{id:'lot',barcode:'1111',name:'Rice',ingredient:'rice',quantity:200,unit:'g'}];
test('optional-only recipe cannot create pantry-funded meals from empty stock',()=>{
 const result=pantryDuration([optional],[],[],1,date,1);
 assert.equal(result.meals,0);assert.equal(result.days,0);assert.equal(result.limited,false);
});
test('unmeasured optional-only recipe does not imply measured pantry coverage',()=>{
 const result=pantryDuration([{...optional,ingredients:[{ingredient:'rice',optional:true}]}],stock,[],1,date,1);
 assert.equal(result.meals,0);assert.deepEqual(result.sequence,[]);
});
test('optional-only alternative does not mask the real finite measured estimate',()=>{
 const result=pantryDuration([optional,rice],stock,[],1,date,1);
 assert.equal(result.meals,2);assert.deepEqual(result.sequence,['Measured rice','Measured rice']);assert.equal(result.limited,false);
});
test('measured meals may retain optional ingredients without consuming them',()=>{
 const result=pantryDuration([{...rice,ingredients:[...rice.ingredients,{ingredient:'coriander',quantity:5,unit:'g',optional:true}]}],stock,[],1,date,1);
 assert.equal(result.meals,2);
});
test('unknown or held recipe yield remains excluded from the estimate',()=>{
 for(const recipe of [{...rice,needsReview:true},{...rice,servingsUnknown:true},{...rice,servings:0}]){
  assert.equal(pantryDuration([recipe],stock,[],1,date,1).meals,0);
 }
});
test('finite measured estimate preserves original stock and recipe inputs',()=>{
 const before=JSON.stringify({rice,stock});assert.equal(pantryDuration([rice],stock,[],1,date,1).meals,2);
 assert.equal(JSON.stringify({rice,stock}),before);
});
