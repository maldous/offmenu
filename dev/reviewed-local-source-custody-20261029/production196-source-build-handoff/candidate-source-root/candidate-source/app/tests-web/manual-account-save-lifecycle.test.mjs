import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const path=process.env.OFFMENU_APP_SOURCE||new URL('../public/app.js',import.meta.url);
const source=fs.readFileSync(path,'utf8');
const start=source.indexOf("$('cloud-save').onclick=async()=>");
const end=source.indexOf('\nasync function signedIn',start);
assert.ok(start>=0&&end>start,'actual app cloud-save caller found');
const handler=source.slice(start,end);
function fixture(){
 let resolve,reject;const pending=new Promise((a,b)=>{resolve=a;reject=b;});
 const storage=new Map([['pantry-a-revision','3'],['pantry-a-dirty','1']]);
 const nodes={'cloud-save':{},'sync-status':{textContent:'A pending'}};
 const sent=[];let active=false,scheduled=0;
 const ctx={requestIdentity:{owner:'a'},KEY:'pantry-a',revision:3,dirty:true,
  lots:[{id:'lot-a',ingredient:'rice',quantity:100,unit:'g'}],products:{},recipes:[],selections:[],
  profile:{country:'AU',units:'metric',servings:2,members:[{id:'member-a',mealPreferences:{version:1,scope:{accountId:'a',memberId:'member-a'},likes:['rice'],textures:[],spice:'mild'}}]},
  $:id=>nodes[id],sharing:{active:()=>active,schedule:()=>scheduled++},
  localStorage:{getItem:key=>storage.get(key)??null,setItem:(key,value)=>storage.set(key,String(value)),removeItem:key=>storage.delete(key)},
  setLocalizedText:(node,text)=>{node.textContent=text;},
  saveProfile:()=>{ctx.dirty=true;storage.set(ctx.KEY+'-dirty','1');},
  currentState:()=>({inventory:ctx.lots,products:ctx.products,recipes:ctx.recipes,profile:ctx.profile,selections:ctx.selections}),
  cloudRequest:async(method,body)=>{sent.push({method,body:structuredClone(body)});return pending;}
 };
 vm.runInNewContext(handler,ctx,{filename:String(path)});
 return {ctx,storage,nodes,sent,resolve,reject,run:()=>nodes['cloud-save'].onclick(),share:value=>{active=value;},scheduled:()=>scheduled};
}

test('actual manual caller preserves private member preferences through serialized PUT',async()=>{
 const f=fixture(),before=structuredClone(f.ctx.profile.members[0].mealPreferences),done=f.run();
 assert.equal(f.sent.length,1);assert.equal(f.sent[0].method,'PUT');assert.equal(f.sent[0].body.revision,3);
 assert.deepEqual(f.sent[0].body.state.profile.members[0].mealPreferences,before);
 f.resolve({revision:4});await done;
 assert.equal(f.ctx.revision,4);assert.equal(f.storage.get('pantry-a-revision'),'4');assert.equal(f.storage.has('pantry-a-dirty'),false);assert.equal(f.ctx.dirty,false);
 assert.deepEqual(f.ctx.profile.members[0].mealPreferences,before);
});
test('late successful old-account save does not write current account revision or clear its dirty state',async()=>{
 const f=fixture(),done=f.run();
 f.ctx.requestIdentity={owner:'b'};f.ctx.KEY='pantry-b';f.ctx.revision=9;f.ctx.dirty=true;
 f.storage.set('pantry-b-revision','9');f.storage.set('pantry-b-dirty','1');f.nodes['sync-status'].textContent='B pending';
 f.resolve({revision:4});await done;
 assert.equal(f.ctx.revision,9);assert.equal(f.ctx.dirty,true);assert.equal(f.storage.get('pantry-b-revision'),'9');assert.equal(f.storage.get('pantry-b-dirty'),'1');assert.equal(f.nodes['sync-status'].textContent,'B pending');
});
test('late old-account error cannot overwrite current account status',async()=>{
 const f=fixture(),done=f.run();f.ctx.requestIdentity={owner:'b'};f.ctx.KEY='pantry-b';f.nodes['sync-status'].textContent='B status';
 f.reject(new Error('Private A failure'));await done;assert.equal(f.nodes['sync-status'].textContent,'B status');
});
test('same-account meal preference edits made during save remain dirty and are not mutated',async()=>{
 const f=fixture(),done=f.run();f.ctx.profile.members[0].mealPreferences.likes.push('beans');
 f.resolve({revision:4});await done;
 assert.deepEqual(f.sent[0].body.state.profile.members[0].mealPreferences.likes,['rice']);
 assert.deepEqual(f.ctx.profile.members[0].mealPreferences.likes,['rice','beans']);
 assert.equal(f.ctx.revision,4);assert.equal(f.ctx.dirty,true);assert.equal(f.storage.get('pantry-a-dirty'),'1');assert.equal(f.nodes['sync-status'].textContent,'New changes pending');
});
test('transition to shared kitchen suppresses private save completion effects',async()=>{
 const f=fixture(),done=f.run();f.share(true);f.nodes['sync-status'].textContent='Shared kitchen';
 f.resolve({revision:4});await done;assert.equal(f.ctx.revision,3);assert.equal(f.storage.get('pantry-a-dirty'),'1');assert.equal(f.nodes['sync-status'].textContent,'Shared kitchen');
});
test('newer loaded account revision is not overwritten by an earlier response',async()=>{
 const f=fixture(),done=f.run();f.ctx.revision=5;f.storage.set('pantry-a-revision','5');f.nodes['sync-status'].textContent='Newer cloud state';
 f.resolve({revision:4});await done;assert.equal(f.ctx.revision,5);assert.equal(f.storage.get('pantry-a-revision'),'5');assert.equal(f.nodes['sync-status'].textContent,'Newer cloud state');
});
test('autosync storage revision change is not overwritten when app revision is stale',async()=>{
 const f=fixture(),done=f.run();f.storage.set('pantry-a-revision','5');f.nodes['sync-status'].textContent='Autosync newer';
 f.resolve({revision:4});await done;assert.equal(f.storage.get('pantry-a-revision'),'5');assert.equal(f.nodes['sync-status'].textContent,'Autosync newer');
});
test('reset of same identity invalidates in-flight save through identity generation',async()=>{
 const f=fixture(),done=f.run();f.ctx.requestIdentity={owner:'a'};f.nodes['sync-status'].textContent='Account reset';
 f.resolve({revision:4});await done;assert.equal(f.ctx.revision,3);assert.equal(f.nodes['sync-status'].textContent,'Account reset');
});
test('ordinary current-account error remains visible and local changes remain dirty',async()=>{
 const f=fixture(),done=f.run();f.reject(new Error('Save failed'));await done;
 assert.equal(f.nodes['sync-status'].textContent,'Save failed');assert.equal(f.ctx.dirty,true);assert.equal(f.storage.get('pantry-a-dirty'),'1');
});
test('shared kitchen save delegates to existing sharing caller without private request',async()=>{
 const f=fixture();f.share(true);await f.run();assert.equal(f.scheduled(),1);assert.equal(f.sent.length,0);
});
