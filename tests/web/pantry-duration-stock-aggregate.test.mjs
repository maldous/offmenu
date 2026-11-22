import test from 'node:test';
import assert from 'node:assert/strict';
import {pantryDuration} from '../../apps/web/src/household-model.js';

const day='2026-11-18';
const recipe=(title,ingredient,unit='g',quantity=1)=>({title,servings:1,ingredients:[{ingredient,unit,quantity}]});
const lot=(ingredient,quantity,unit='g',expires=null)=>({ingredient,unit,quantity,expires});
const run=(recipes,stock)=>pantryDuration(recipes,stock,[],1,day,1);

// Unrepresentable rice mass is not a reason to suppress a separate measured unit.
test('the rational fallback excludes only the overflowing resource key',()=>{
 const stock=[lot('rice',1e308),lot('rice',1e308),lot('rice',2,'count')],before=structuredClone(stock);
 assert.deepEqual(run([recipe('mass','rice'),recipe('count','rice','count')],stock).sequence,['count','count']);
 assert.deepEqual(stock,before);
});

// The two huge lots cannot qualify on day one. After a safe alternative
// advances the simulated day, one has expired and the large meal is feasible.
test('expiry can restore a representable total on a later simulated day',()=>{
 const stock=[lot('rice',1e308,'g',day),lot('rice',1e308),lot('pea',1)];
 const r=run([recipe('rice','rice','g',1e308),recipe('pea','pea')],stock);
 assert.deepEqual(r.sequence,['pea','rice']); assert.equal(r.optimal,false);
});
