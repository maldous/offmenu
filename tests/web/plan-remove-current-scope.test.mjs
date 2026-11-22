import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const start=source.indexOf('const removeId=entry.id');
const end=source.indexOf('const log=',start);
const actual=source.slice(start,end);
assert.match(actual,/remove\.onclick/);
function snapshot(){
 const writes=[],dinner={id:'target',recipeId:'one',servings:2},a={id:'breakfast'},b={id:'next-day'};
 const owner={owner:'synthetic'};
 const context=vm.createContext({entry:dinner,plan:[a,dinner],profile:{plan:[a,dinner]},remove:{},sharing:{canWrite:()=>true},
  PROFILE:'private-key',planProfileKey:'private-key',requestIdentity:owner,planOwner:owner,planScopeEpoch:1,planEpoch:1,
  markDirty(){},renderPlan(){},localStorage:{setItem:(key,v)=>writes.push({key,value:JSON.parse(v)})}});
 vm.runInContext(actual,context);
 context.profile={plan:[a,{...dinner},b]}; // same-scope snapshot replaces profile without rerender
 return {context,writes,a,b,dinner};
}
test('existing rendered Remove reads the latest same-scope rows and keeps unrelated arrivals',()=>{
 const {context:c,writes,a,b}=snapshot();
 c.remove.onclick();
 assert.deepEqual(structuredClone(c.profile.plan),[a,b]);
 assert.deepEqual(writes,[{key:'private-key',value:{plan:[a,b]}}]);
});
test('stale account, scope epoch, write permission or selected row refuses changes',()=>{
 for(const alter of [
  c=>{c.requestIdentity={owner:'another'};},c=>{c.PROFILE='other-key';},c=>{c.planScopeEpoch++;},
  c=>{c.sharing.canWrite=()=>false;},c=>{c.profile.plan[1]={id:'target',recipeId:'changed'};},
  c=>{c.profile.plan.splice(1,1);}, c=>{c.profile.plan.push({...c.profile.plan[1]});}
 ]){
  const {context:c,writes}=snapshot();alter(c);const before=JSON.stringify(c.profile);
  c.remove.onclick();assert.deepEqual(writes,[]);assert.equal(JSON.stringify(c.profile),before);
 }
});
