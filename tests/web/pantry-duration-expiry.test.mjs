import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
import {pantryDuration} from '../../apps/web/src/household-model.js';
import {matchMeals} from '../../apps/web/src/model.js';

const recipe={id:'synthetic-rice',title:'Synthetic rice',servings:1,needsReview:false,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const lot=(overrides={})=>({id:'synthetic-lot',ingredient:'rice',quantity:300,unit:'g',needsReview:false,...overrides});
const duration=(stock,start='2026-10-29',mealsPerDay=1)=>pantryDuration([recipe],stock,[],1,start,mealsPerDay);

test('duration stops using stock after the same expiry boundary enforced by meal matching',()=>{
  const stock=[lot({expires:'2026-10-29'})];
  assert.equal(matchMeals(stock,[recipe],1,'2026-10-30').filter(r=>r.status==='ready').length,0);
  const result=duration(stock);
  assert.equal(result.meals,1);
  assert.equal(result.days,1);
  assert.deepEqual(result.sequence,[recipe.title]);
});

test('multiple meals on the expiry day remain eligible before the next simulated day',()=>{
  const stock=[lot({quantity:500,expires:'2026-10-29'})];
  assert.equal(duration(stock,'2026-10-29',2).meals,2);
  assert.equal(duration(stock,'2026-10-29',2).days,1);
  assert.equal(duration(stock,'2026-10-29',3).meals,3);
});

test('later-expiring stock replaces the earlier lot for both readiness and deduction',()=>{
  const stock=[lot({expires:'2026-10-29'}),lot({id:'later-lot',quantity:200,expires:'2026-10-31'})];
  assert.equal(duration(stock).meals,3);
  assert.equal(duration(stock).days,3);
  assert.deepEqual(stock.map(l=>l.quantity),[300,200]);
});

test('already expired and review-held lots remain excluded',()=>{
  for(const held of [lot({expires:'2026-10-28'}),lot({needsReview:true}),lot({quantity:Infinity})]){
    assert.equal(duration([held]).meals,0);
  }
});

test('undated stock retains quantity-limited repeated-menu behavior without input mutation',()=>{
  const stock=Object.freeze([Object.freeze(lot())]);
  const before=structuredClone(stock);
  assert.equal(duration(stock).meals,3);
  assert.deepEqual(stock,before);
  assert.deepEqual(recipe.ingredients,[{ingredient:'rice',quantity:100,unit:'g'}]);
});

for(const [start,expiry,meals] of [
  ['2026-12-31','2027-01-01',2],
  ['2028-02-28','2028-03-01',3],
  ['2026-03-07','2026-03-08',2],
  ['2026-10-31','2026-11-01',2],
])test('UTC calendar advance across '+start+' through '+expiry,()=>{
  assert.equal(duration([lot({quantity:1000,expires:expiry})],start).meals,meals);
});

test('the existing 10000-batch cap remains finite for abundant undated stock',()=>{
  const result=duration([lot({quantity:1_000_000_000})]);
  assert.equal(result.meals,10000);
  assert.equal(result.limited,true);
});

test('the actual duration button reports the expiry-aware measured result',()=>{
  const {parse}=createRequire(import.meta.url)('acorn');
  const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
  const handler=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body.find(n=>
    n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&
    n.expression.left.object?.type==='CallExpression'&&n.expression.left.object.arguments[0]?.value==='duration-calculate');
  assert.ok(handler,'Current duration UI must still have its qualified caller');
  const fields=new Map([['duration-calculate',{}],['meals-per-day',{value:'1'}],['servings',{value:'1'}],['duration-result',{textContent:''}]]);
  const stock=[lot({expires:'2026-10-29'})];
  const context={$:id=>fields.get(id),pantryDuration,recipes:[recipe],profile:{members:[]},
    unexpiredInventory:()=>stock,today:()=> '2026-10-29',
    setLocalizedText:(node,template,values)=>{node.textContent=template.replace(/\{(\w+)\}/g,(_,key)=>values[key]);}};
  vm.createContext(context);
  vm.runInContext(source.slice(handler.start,handler.end),context);
  fields.get('duration-calculate').onclick();
  assert.match(fields.get('duration-result').textContent,/^1 measured household meals ≈ 1 complete days at 1 meals\/day\./);
  assert.match(fields.get('duration-result').textContent,/does not establish a nutritionally complete diet/);
  assert.equal(stock[0].quantity,300);
});
