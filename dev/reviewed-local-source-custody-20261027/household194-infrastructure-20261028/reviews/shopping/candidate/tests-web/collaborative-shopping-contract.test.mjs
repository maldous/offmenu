import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import worker from '../../server/deployed-application.mjs';
import {mergeStates,kitchenProjection,applyKitchen} from '../public/sync-model.js';
import {finishInventory} from '../public/checkout-model.js';
import {SCANNER_COMPLETION} from '../public/scanner-kitchen-handoff.js';
const state=()=>({inventory:[],products:{},recipes:[],selections:[],profile:{country:'AU',units:'metric',servings:2,shopping:[{id:'synthetic-item',name:'Rice (synthetic)',amount:'100 g',checked:false}],shoppingChecked:[],locations:[],plan:[],batches:[]}});
const session=()=>({mode:'shopping',area:'Pantry',shelf:'Synthetic shelf',startedAt:'2026-10-28T00:00:00.000Z',items:[{id:'synthetic-lot',barcode:'local:synthetic-lot',name:'Rice (synthetic)',ingredient:'rice',quantity:100,unit:'g',expires:null,amountBasis:'manual'}]});
function harness(){
 const db=new DatabaseSync(':memory:');db.exec('CREATE TABLE kitchens(id TEXT PRIMARY KEY,name TEXT,revision INTEGER,state_json TEXT,updated_at TEXT); CREATE TABLE kitchen_members(kitchen_id TEXT,user_id TEXT,role TEXT);');
 db.prepare('INSERT INTO kitchens VALUES(?,?,?,?,?)').run('synthetic-kitchen','Synthetic kitchen',1,JSON.stringify(state()),'2026-10-28T00:00:00.000Z');
 const membership=db.prepare('INSERT INTO kitchen_members VALUES(?,?,?)');for(const [id,role] of [['synthetic-a','owner'],['synthetic-b','editor'],['synthetic-viewer','viewer']])membership.run('synthetic-kitchen',id,role);
 const DB={prepare(sql){
  const statement=db.prepare(sql);
  return {bind(...params){return {
   async first(){return statement.get(...params)||null;},
   async all(){return {results:statement.all(...params)};},
   async run(){return {meta:{changes:statement.run(...params).changes}};}
  };}};
 }};
 const old=globalThis.fetch;globalThis.fetch=async(url,options)=>{assert.equal(url,'https://offmenu-accounts.netlify.app/.netlify/identity/user');const id=options.headers.Authorization.slice('Bearer '.length);assert.match(id,/^synthetic-/);return Response.json({id});};
 async function request(actor,method='GET',body){const response=await worker.fetch(new Request('https://synthetic.invalid/api/kitchens/synthetic-kitchen/state',{method,headers:{Origin:'https://synthetic.invalid',Authorization:'Bearer '+actor,'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined}),{DB});return {status:response.status,body:await response.json()};}
 return {request,cleanup(){globalThis.fetch=old;db.close();}};
}
test('server artifact is exactly retained production193, not a reconstructed route',async()=>{const bytes=await readFile(new URL('../../server/deployed-application.mjs',import.meta.url));assert.equal(createHash('sha256').update(bytes).digest('hex'),'0e4420ef0152586a80cf982d7084582180b9e8798d9dd87cb6aae304da305a34');});
test('two members merge independent list edits after exact server revision conflict',async()=>{const h=harness();try{
 const a=await h.request('synthetic-a'),b=await h.request('synthetic-b');assert.equal(a.status,200);assert.equal(b.body.revision,1);
 const localA=structuredClone(a.body.state),localB=structuredClone(b.body.state);localA.profile.shopping[0].checked=true;localB.profile.shopping.push({id:'synthetic-second',name:'Peas (synthetic)',amount:'200 g',checked:false});
 assert.equal((await h.request('synthetic-a','PUT',{revision:1,state:localA})).status,200);
 assert.equal((await h.request('synthetic-b','PUT',{revision:1,state:localB})).status,409);
 const newer=await h.request('synthetic-b'),merged=mergeStates(b.body.state,localB,newer.body.state);assert.deepEqual(merged.conflicts,[]);
 const saved=await h.request('synthetic-b','PUT',{revision:newer.body.revision,state:merged.state});assert.equal(saved.status,200);assert.equal(saved.body.revision,3);
 const final=await h.request('synthetic-a');assert.equal(final.body.state.profile.shopping[0].checked,true);assert.equal(final.body.state.profile.shopping.length,2);assert.deepEqual(final.body.state.inventory,[]);
}finally{h.cleanup();}});
test('server refuses viewer writes and nonmember access without mutating stock or revision',async()=>{const h=harness();try{const current=await h.request('synthetic-viewer');assert.equal(current.status,200);const candidate=structuredClone(current.body.state);candidate.inventory=finishInventory([],session());assert.equal((await h.request('synthetic-viewer','PUT',{revision:1,state:candidate})).status,403);assert.equal((await h.request('synthetic-outsider')).status,403);const latest=await h.request('synthetic-a');assert.equal(latest.body.revision,1);assert.deepEqual(latest.body.state.inventory,[]);}finally{h.cleanup();}});
test('separate receive-stock path is not triggered by list checking; stale PUT replay cannot duplicate stock',async()=>{const h=harness();try{
 const before=(await h.request('synthetic-a')).body;const received=structuredClone(before.state);received.inventory=finishInventory(received.inventory,session());assert.equal(received.inventory.length,1);assert.equal(received.profile.shopping[0].checked,false);
 const first=await h.request('synthetic-a','PUT',{revision:before.revision,state:received});assert.equal(first.status,200);
 assert.equal((await h.request('synthetic-a','PUT',{revision:before.revision,state:received})).status,409);
 const latest=(await h.request('synthetic-b')).body;assert.equal(latest.state.inventory.length,1);assert.equal(latest.state.inventory[0].quantity,100);
 const merge=mergeStates(before.state,received,latest.state);assert.deepEqual(merge.conflicts,[]);assert.equal(merge.state.inventory.length,1);assert.equal(merge.state.inventory[0].quantity,100);
 assert.throws(()=>finishInventory(latest.state.inventory,session()),/Duplicate checkout items/);
}finally{h.cleanup();}});
test('scanner-completion exact replay is a no-op while conflicting or partial replay fails closed',()=>{const checkout=session();checkout.scannerCompletion={schema:SCANNER_COMPLETION};const received=finishInventory([],checkout);assert.strictEqual(finishInventory(received,checkout),received);assert.equal(received[0].quantity,100);
 const changed=structuredClone(received);changed[0].quantity=50;assert.throws(()=>finishInventory(changed,checkout),/conflicts/);
 const partial=structuredClone(checkout);partial.items.push({...partial.items[0],id:'second-synthetic-lot'});assert.throws(()=>finishInventory(received,partial),/partially changed/);
});
test('conflicting quantity revisions are not silently combined; private fields stay outside shared projection',()=>{const base=state();base.inventory=finishInventory([],session());const a=structuredClone(base),b=structuredClone(base);a.inventory[0].quantity=60;b.inventory[0].quantity=40;assert.ok(mergeStates(base,a,b).conflicts.includes('/inventory/synthetic-lot/quantity'));
 const privateState=structuredClone(base);privateState.profile.history=[{id:'private-history'}];privateState.profile.members=[{id:'private-member'}];privateState.profile.goals=[{memberId:'private-member'}];const projected=kitchenProjection(privateState);for(const key of ['history','members','goals'])assert.equal(Object.hasOwn(projected.profile,key),false);const applied=applyKitchen(privateState,projected);assert.deepEqual(applied.profile.history,privateState.profile.history);
});
