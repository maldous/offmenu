import test from 'node:test';
import assert from 'node:assert/strict';
import {recipeIngredientCoverage} from '../../public/recipe-ingredient-coverage.js';
import {planSummary} from '../../public/menu-model.js';
import {allocateIngredients} from '../../public/cooking-model.js';

// Explicit generated recipe/lot/product associations, never source/name joins.
const date='2026-10-26';
const ingredient=(name='rice',quantity=100,unit='g')=>({ingredient:name,quantity,unit});
const recipe=(ingredients=[ingredient()])=>({id:'generated-recipe',servings:1,ingredients});
const lot=(id,quantity=100,extra={})=>({id,barcode:'generated-product-'+id,ingredient:'rice',quantity,unit:'g',...extra});
const run=options=>recipeIngredientCoverage({recipe:recipe(),inventory:[],date,servings:1,...options});
const freeze=value=>{if(value&&typeof value==='object'){Object.values(value).forEach(freeze);Object.freeze(value);}return value;};

test('duplicate source lines carry actual FEFO stock, with locations and one evidenced missing group',()=>{
 const inventory=[lot('later',50,{expires:'2026-10-29',location:{area:'Pantry',shelf:'B'}}),
  lot('first',50,{expires:'2026-10-27',location:{area:'Fridge',shelf:'A'}})];
 const out=run({recipe:recipe([ingredient('rice',60),ingredient('rice',60)]),inventory});
 assert.deepEqual(out.requirements.map(r=>[r.index,r.coveredQuantity,r.uncoveredQuantity,r.status]),[[0,60,0,'covered'],[1,40,20,'uncovered']]);
 assert.deepEqual(out.requirements[0].allocations.map(a=>[a.lotId,a.quantity,a.location]),[
  ['first',50,{area:'Fridge',shelf:'A'}],['later',10,{area:'Pantry',shelf:'B'}]]);
 assert.equal(out.requirements.flatMap(r=>r.allocations).reduce((n,a)=>n+a.quantity,0),100);
 assert.deepEqual(out.choices,{readyNow:false,oneExtraItem:true,unknown:false});
 assert.deepEqual(out.useFirstLots.map(l=>l.lotId),['first','later']);
});

test('readiness and exact inherited nutrient-basis eligibility remain separate per allocated lot',()=>{
 const inventory=[lot('rice'),lot('oil',10,{ingredient:'olive oil',unit:'ml'})];
 const products={
  'generated-product-rice':{nutrition_data_per:'100g',nutriments:{proteins_100g:8}},
  'generated-product-oil':{nutritionProvenance:{nutrientProfile:{basis:{amount:100,unit:'ml'}}}}
 };
 const input={recipe:recipe([ingredient(),ingredient('olive oil',10,'ml')]),inventory,products};
 assert.equal(run(input).nutritionBasisEligible,true);
 assert.equal(run(input).choices.readyNow,true);
 const wrong=structuredClone(input);wrong.products['generated-product-rice'].nutrition_data_per='100ml';
 const out=run(wrong);assert.equal(out.choices.readyNow,true);assert.equal(out.nutritionBasisEligible,false);
 assert.equal(out.requirements[0].allocations[0].nutritionBasisEligible,false);
 assert.equal(out.requirements[1].allocations[0].nutritionBasisEligible,true);
 assert.equal(out.requirements[0].allocations[0].location,null);
 const counted=run({recipe:recipe([ingredient('egg',1,'count')]),inventory:[lot('egg',1,{ingredient:'egg',unit:'count'})],
  products:{'generated-product-egg':{nutrition_data_per:'100g'}}});
 assert.equal(counted.choices.readyNow,true);assert.equal(counted.nutritionBasisEligible,false);
});

test('held recipes, missing quantities/yield, unsupported units and overflow stay unknown without allocation',()=>{
 for(const r of [
  {...recipe(),needsReview:true},{...recipe(),servingsUnknown:true},{...recipe(),servings:null},
  recipe([ingredient('rice',null)]),recipe([ingredient('rice',1,'cup')]),
  recipe([ingredient(),ingredient('rice',null)]),recipe([ingredient('rice',Number.MAX_VALUE)])
 ]){
  const out=run({recipe:r,inventory:[lot('rice')],servings:Number.MAX_VALUE});
  assert.equal(out.choices.unknown,true);assert.equal(out.choices.readyNow,false);assert.equal(out.choices.oneExtraItem,false);
  assert.ok(out.requirements.every(row=>row.status==='unknown'&&row.coveredQuantity===null&&row.allocations.length===0));
 }
 assert.throws(()=>run({servings:0}));
});

test('optional rows are excluded; missing optional quantities cannot supply or block required demand',()=>{
 const out=run({recipe:recipe([{...ingredient('salt',null),optional:true},ingredient()]),inventory:[lot('rice')]});
 assert.equal(out.requirements.length,1);assert.equal(out.requirements[0].index,1);assert.equal(out.choices.readyNow,true);
 const onlyOptional=run({recipe:recipe([{...ingredient(),optional:true}])});
 assert.equal(onlyOptional.choices.unknown,true);assert.equal(onlyOptional.choices.readyNow,false);
});

test('unknown same-ingredient stock does not become a known zero; sufficient known stock still proves coverage',()=>{
 const partial=run({inventory:[lot('known',20),lot('unknown',null)]});
 assert.equal(partial.matching.status,'missing');assert.equal(partial.requirements[0].coveredQuantity,20);
 assert.equal(partial.requirements[0].unallocatedKnownDemand,80);assert.equal(partial.requirements[0].uncoveredQuantity,null);
 assert.deepEqual(partial.choices,{readyNow:false,oneExtraItem:false,unknown:true});
 const ready=run({inventory:[lot('known'),lot('unknown',null)]});assert.equal(ready.choices.readyNow,true);
 const unbound=run({inventory:[lot('unknown',100,{ingredient:null})]});assert.equal(unbound.choices.unknown,true);
});

test('expired/review stock cannot allocate; units do not convert and product names cannot invent an ingredient join',()=>{
 const expired=run({inventory:[lot('expired',100,{expires:'2026-10-25'}),lot('review',100,{needsReview:true})]});
 assert.equal(expired.requirements[0].coveredQuantity,0);assert.equal(expired.requirements[0].uncoveredQuantity,100);
 const volume=run({inventory:[lot('ml',100,{unit:'ml'})]});assert.equal(volume.requirements[0].uncoveredQuantity,100);
 const named=run({inventory:[lot('unmapped',100,{ingredient:'unmapped'})],products:{'generated-product-unmapped':{name:'Rice',nutrition_data_per:'100g'}}});
 assert.equal(named.choices.readyNow,false);assert.equal(named.requirements[0].allocations.length,0);
 const alias=run({recipe:recipe([ingredient('eggs',2,'count')]),inventory:[lot('egg',2,{ingredient:'egg',unit:'count'})]});
 assert.equal(alias.choices.readyNow,true);assert.equal(alias.requirements[0].canonicalIngredient,'egg');
 const two=run({recipe:recipe([ingredient(),ingredient('carrot',1,'count')])});assert.equal(two.choices.oneExtraItem,false);
});

test('fractional servings preserve existing lot allocation and leave daily/weekly nutrition model unchanged',()=>{
 const inventory=[lot('rice',100)];const products={'generated-product-rice':{nutrition_data_per:'100g',nutriments:{proteins_100g:8}}};
 const r={...recipe(),servings:2};const input={recipe:r,inventory,products,servings:.5};
 const plan=[{recipeId:r.id,date,servings:.5},{recipeId:r.id,date:'2026-10-27',servings:.5}];
 const before=planSummary(plan,[r],inventory,products,[date,'2026-10-27']);
 const out=run(input);assert.equal(out.requirements[0].requiredQuantity,25);assert.equal(out.requirements[0].coveredQuantity,25);
 assert.equal(out.nutritionBasisEligible,true);
 assert.deepEqual(planSummary(plan,[r],inventory,products,[date,'2026-10-27']),before);
 assert.equal(before.totals.proteins_100g.value,4);assert.equal(before.totals.fat_100g.known,0);
});

test('bounded detached evidence preserves frozen inputs, refuses ambiguous lot IDs and invalid dates',()=>{
 const input=freeze({recipe:recipe(),inventory:[lot('rice',100,{location:{area:'Pantry',shelf:'A'}})],products:{},date,servings:1});
 const before=structuredClone(input),a=recipeIngredientCoverage(input),b=recipeIngredientCoverage(input);
 assert.deepEqual(a,b);assert.deepEqual(input,before);
 a.requirements[0].allocations[0].location.shelf='changed';assert.equal(b.requirements[0].allocations[0].location.shelf,'A');
 assert.equal(input.inventory[0].location.shelf,'A');
 assert.throws(()=>run({inventory:[lot('same'),lot('same')]}),TypeError);
 assert.throws(()=>run({date:'2026-02-30'}),TypeError);
 assert.throws(()=>run({inventory:[lot('bad',100,{expires:'unknown'})]}),TypeError);
});

test('later tiny lots and repeated ingredient remainders agree with the existing whole-recipe allocator',()=>{
 const r=recipe([ingredient('rice',1),ingredient('olive oil',1e-8,'ml'),ingredient('rice',1e-8)]);
 const inventory=[lot('rice',1.00000001),lot('oil',1e-8,{ingredient:'olive oil',unit:'ml'})];
 const expected=allocateIngredients(r,inventory,1,date);
 const out=run({recipe:r,inventory});
 const fields=d=>({lotId:d.lotId,quantity:d.quantity,ingredient:d.ingredient,unit:d.unit});
 const projected=out.requirements.flatMap(row=>row.allocations.map(a=>({...fields(a),ingredient:row.ingredient})));
 assert.deepEqual(projected,expected.deductions.map(fields));
 assert.equal(out.requirements[1].coveredQuantity,1e-8);
 assert.ok(out.requirements[2].coveredQuantity>0);
 assert.deepEqual(inventory.map(l=>l.quantity),[1.00000001,1e-8]);
});

test('matching/allocation cutoff disagreement is explicit and cannot present a zero-quantity extra item',()=>{
 const out=run({recipe:recipe([ingredient('rice',1)]),inventory:[lot('rice',.99999999)]});
 assert.equal(out.matching.status,'missing');assert.equal(out.matching.missing[0].quantity,0);
 assert.equal(out.requirements[0].status,'covered');
 assert.equal(out.classificationAgreement,false);
 assert.deepEqual(out.choices,{readyNow:false,oneExtraItem:false,unknown:true});
 assert.equal(out.nutritionBasisEligible,false);
});
