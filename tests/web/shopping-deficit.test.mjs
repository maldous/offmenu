import test from 'node:test';import assert from 'node:assert/strict';
import {calculateShoppingDeficit as calculate} from '../../integrations/candidates/shopping-deficit.mjs';
const row=(rowRef,quantity,extra={})=>({rowRef,ingredientId:'synthetic:rice',unit:'g',basis:'synthetic:dry-edible',quantity,...extra});
function frozen(x){if(x&&typeof x==='object'){Object.values(x).forEach(frozen);Object.freeze(x);}return x;}
test('exact coverage, partial stock, known zero, explicit empty stock and surplus',()=>{
 for(const [stock,expected]of [[10,0],[4,6],[0,10],[20,0]]){const result=calculate({requirements:[row('need',10)],available:[row('lot',stock)]});assert.equal(result.groups[0].deficit,expected);assert.equal(result.complete,true);}
 assert.equal(calculate({requirements:[row('need',10)],available:[]}).groups[0].deficit,10);
 assert.throws(()=>calculate({requirements:[row('need',10)]}),/Explicit bounded/);
});
test('duplicate demands/lots aggregate only exact keys and preserve every original citation/index',()=>{
 const input=frozen({requirements:[row('same-ref',2),row('same-ref',3)],available:[row('lot-1',1),row('lot-2',0.5)]});const before=structuredClone(input),result=calculate(input),g=result.groups[0];
 assert.equal(result.groups.length,1);assert.equal(g.requiredQuantity,5);assert.equal(g.availableQuantity,1.5);assert.equal(g.deficit,3.5);
 assert.deepEqual(g.requirementRefs,[{side:'requirements',index:0,rowRef:'same-ref'},{side:'requirements',index:1,rowRef:'same-ref'}]);assert.equal(g.availableRefs[1].rowRef,'lot-2');assert.deepEqual(input,before);
 g.requirementRefs[0].rowRef='changed';assert.equal(input.requirements[0].rowRef,'same-ref');
});
test('different preparation/basis stays separate and is explicitly incompatible, with no stock conversion',()=>{
 const result=calculate({requirements:[row('dry-demand',10)],available:[row('cooked-stock',100,{basis:'synthetic:cooked-edible'})]});
 assert.equal(result.groups.length,2);assert.equal(result.groups[0].deficit,10);assert.equal(result.groups[1].deficit,0);assert.equal(result.complete,false);
 assert.deepEqual(result.incompatibleGroups[0].groupIndexes,[0,1]);assert.match(result.incompatibleGroups[0].reason,/no conversion/);
});
test('units and IDs compare exactly; no mass conversion, normalization or identity inference',()=>{
 const units=calculate({requirements:[row('grams',100)],available:[row('kilograms',1,{unit:'kg'})]});assert.equal(units.groups[0].deficit,100);assert.equal(units.incompatibleGroups.length,1);
 const ids=calculate({requirements:[row('need',3)],available:[row('other',100,{ingredientId:'SYNTHETIC:RICE'})]});assert.equal(ids.groups.length,2);assert.equal(ids.groups[0].deficit,3);assert.equal(ids.incompatibleGroups.length,0);
 const exact=calculate({requirements:[row('one',1,{basis:'dry|g'})],available:[row('two',2,{basis:'dry|g',unit:'g|dry'})]});assert.equal(exact.groups.length,2);
});
test('missing requirement or available quantity is unknown, not a zero deficit or full shopping quantity',()=>{
 for(const input of [{requirements:[row('unknown',null),row('known',5)],available:[row('lot',2)]},{requirements:[row('need',5)],available:[row('unknown-lot',undefined)]}]){
  const result=calculate(input),g=result.groups[0];assert.equal(g.deficit,null);assert.equal(g.status,'unknown');assert.equal(result.complete,false);assert.equal(result.unknownGroups[0].groupIndex,0);
 }
 const g=calculate({requirements:[row('unknown',null),row('known',5)],available:[]}).groups[0];assert.equal(g.requiredQuantity,null);assert.equal(g.requiredKnownSubtotal,5);
});
test('missing basis/identity/unit cannot silently aggregate; ungroupable rows retain values and references',()=>{
 const result=calculate({requirements:[row('basis-1',2,{basis:null}),row('basis-2',3,{basis:null}),row('identity',null,{ingredientId:null})],available:[row('unit',0,{unit:undefined})]});
 assert.equal(result.groups.length,0);assert.equal(result.unknownGroups.length,4);assert.equal(result.unknownGroups[0].quantity,2);assert.equal(result.unknownGroups[1].rowReferences[0].index,1);assert.equal(result.unknownGroups[3].quantity,0);assert.equal(result.complete,false);
});
test('negative/nonfinite/coercible values, missing citations, accessors and unbounded arrays reject',()=>{
 for(const quantity of [-1,NaN,Infinity,-Infinity,'10',{},true])for(const side of ['requirements','available']){const input={requirements:[],available:[]};input[side]=[row('bad',quantity)];assert.throws(()=>calculate(input),/finite nonnegative/);}
 assert.throws(()=>calculate({requirements:[row('',1)],available:[]}),/rowRef/);
 assert.throws(()=>calculate({requirements:new Array(1),available:[]}),/Dense/);
 assert.throws(()=>calculate({requirements:Array.from({length:1001},(_,i)=>row(String(i),1)),available:[]}),/bounded/);
 const bad=row('getter',1);let calls=0;Object.defineProperty(bad,'quantity',{enumerable:true,get(){calls++;return 1;}});assert.throws(()=>calculate({requirements:[bad],available:[]}),/accessor/);assert.equal(calls,0);
 assert.throws(()=>calculate({requirements:[row('a',Number.MAX_VALUE),row('b',Number.MAX_VALUE)],available:[]}),/representable/);
});
test('stable first-seen order, stock-only groups and zero demand are explicit',()=>{
 const input={requirements:[row('b',1,{ingredientId:'b'}),row('a',2,{ingredientId:'a'}),row('b2',0,{ingredientId:'b'})],available:[row('c',5,{ingredientId:'c'})]};
 const result=calculate(input);assert.deepEqual(result.groups.map(g=>g.ingredientId),['b','a','c']);assert.deepEqual(calculate(input),result);assert.equal(result.groups[2].requiredQuantity,0);assert.equal(result.groups[2].deficit,0);
 assert.equal(calculate({requirements:[row('zero',0)],available:[]}).groups[0].deficit,0);
});
test('canonical decimal arithmetic avoids false deficits without epsilon-rounding genuine small needs',()=>{
 const r=calculate({requirements:[row('a',0.1),row('b',0.2)],available:[row('c',0.3)]});assert.equal(r.groups[0].requiredQuantity,0.3);assert.equal(r.groups[0].deficit,0);
 assert.equal(calculate({requirements:[row('small',1e-14)],available:[row('zero',0)]}).groups[0].deficit,1e-14);
});
