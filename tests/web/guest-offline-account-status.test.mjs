import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
const app=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const start=app.indexOf('async function initAuth(){'),end=app.indexOf('async function cloudRequest(',start);
assert.ok(start>=0&&end>start);
for(const [name,rows] of [['warm',[{id:'fixture'}]],['cold',[]]])test('sign-in failure does not promise catalogue for '+name+' Guest state',async()=>{
 const nodes={'auth-controls':{},'account-status':{}};
 const harness={recipes:rows,$:id=>{assert.ok(Object.hasOwn(nodes,id));return nodes[id];},
  handleAuthCallback:async()=>null,getSettings:async()=>{throw Error('synthetic offline');},
  setLocalizedText:(node,text)=>{node.textContent=text;}};
 const initAuth=runInNewContext(app.slice(start,end)+'\ninitAuth',harness);
 await initAuth();
 assert.equal(nodes['auth-controls'].hidden,true);
 assert.equal(nodes['account-status'].textContent,'Sign-in is unavailable. You can still use your Guest pantry.');
 assert.deepEqual(harness.recipes,rows);
});
