import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {finishInventory} from '../../apps/web/src/checkout-model.js';
import {milestones} from '../../apps/web/src/insights-model.js';

const {parse}=createRequire(import.meta.url)('acorn');
const src=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const nodes=parse(src,{ecmaVersion:'latest',sourceType:'module'}).body;
const declarations=new Set(['GUEST_SHELF_STARTER','isLocalGuest','readGuestShelfStarter','recordGuestShelfStarter']);
const exposed=new Set(['confirm-finish','clear-local']);
const source=nodes.filter(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>declarations.has(d.id.name))||n.type==='FunctionDeclaration'&&declarations.has(n.id.name)||n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&exposed.has(n.expression.left.object?.arguments?.[0]?.value)).map(n=>src.slice(n.start,n.end)).join('\n');
const KEY='offmenu-profile-v1-shelf-starter';
const item={id:'synthetic-lot',quantity:2,unit:'count',location:{area:'Pantry',shelf:'One'}};
const shopping={mode:'shopping',area:'Pantry',shelf:'One',startedAt:'2026-01-01T00:00:00Z',items:[item]};
const waste={...shopping,mode:'waste',items:[{...item,discardQuantity:1}]};
function run({storage={}, session=shopping, lots=[], authResolved=true, user=null,demoMode=false,shared=false,lifecycleFixture=false,fail='',writable=true}={}){
 const elements=new Map(),events=[],access=[];
 const $=id=>{if(!elements.has(id))elements.set(id,{hidden:true,close(){}});return elements.get(id);};
 const localStorage=new Proxy(storage,{get(obj,key){
  if(key==='getItem')return k=>{access.push(['get',k]);if(fail==='marker-read')throw Error('storage denied');return obj[k]??null;};
  if(key==='setItem')return (k,v)=>{access.push(['set',k]);if(fail==='marker')throw Error('storage denied');obj[k]=v;};
  if(key==='removeItem')return k=>{access.push(['remove',k]);if(fail==='reset'&&k===KEY)throw Error('storage denied');delete obj[k];};
  return obj[key];
 }});
 const record=(kind,fn=()=>{})=>value=>{if(fail===kind)throw Error('storage denied: '+kind);events.push(kind);fn(value);};
 const context={$,session,lots,authResolved,user,demoMode,lifecycleFixture,sharing:{active:()=>shared},requestIdentity:{owner:user?.id??null},KEY:'offmenu-pantry-v1',PROFILE:'offmenu-profile-v1',PRODUCTS:'offmenu-products-v1',RECIPES:'offmenu-recipes-v1',SELECTIONS:'offmenu-selections-v1',localStorage,
  canEditCheckout:()=>writable,scannerScopeMatches:()=>true,document:{querySelectorAll:()=>[]},finishInventory,profile:{},
  persistProfile:record('waste'),save:record('stock',value=>{context.lots=value;}),saveReceipt:record('receipt'),saveDraft:record('draft'),
  setLocalizedText:(el,value)=>{el.textContent=value;},t:v=>v,beep(){},pantry(){},findMeals(){},msg(){},
  confirm:()=>true,clearPending:async()=>{if(fail==='pending')throw Error('storage denied');events.push('clear');},location:{reload:()=>events.push('reload')}};
 vm.createContext(context);vm.runInContext(source,context);
 return {finish:()=>$('confirm-finish').onclick(),clear:()=>$('clear-local').onclick(),read:()=>vm.runInContext('typeof readGuestShelfStarter === "function" && readGuestShelfStarter()',context),events,access,$};
}
test('legacy receipt is not an earned award; first newly added stock earns it, later waste and reload preserve it',()=>{
 assert.equal(milestones({lastReceipt:waste},[])[0].earned,false);
 const storage={},first=run({storage});
 first.finish();assert.deepEqual(first.events,['stock','receipt','draft']);
 assert.equal(storage[KEY],'1');
 const reloaded=run({storage,session:waste,lots:[item]});reloaded.finish();
 assert.deepEqual(reloaded.access,[]);
 const earned=reloaded.read();assert.equal(earned,true);
 assert.equal(milestones({lastReceipt:waste},[],earned)[0].earned,true);
 assert.deepEqual(reloaded.access,[['get',KEY]]);
});
test('waste, same-ID shelf recount, permission refusal and every failed required write never award',()=>{
 for(const input of [{session:waste,lots:[item]},{session:{...shopping,mode:'shelf'},lots:[item]},{writable:false},...['stock','receipt','draft'].map(fail=>({fail}))]){
  const storage={},h=run({...input,storage});h.finish();assert.equal(storage[KEY],undefined);assert.deepEqual(h.access,[]);
 }
});
test('denied milestone storage neither fails completed checkout nor invents achievement',()=>{
 const storage={},h=run({storage,fail:'marker'});h.finish();
 assert.equal(h.$('checkout-complete').hidden,false);
 assert.equal(storage[KEY],undefined);assert.deepEqual(h.access,[['get',KEY],['set',KEY]]);
 assert.equal(run({storage:{[KEY]:'1'},fail:'marker-read'}).read(),false);
});
test('non-Guest cannot read, write, or clear the Guest award; confirmed Guest reset removes it',async()=>{
 for(const scope of [{authResolved:false},{user:{id:'synthetic-owner'}},{demoMode:true},{shared:true},{lifecycleFixture:true}]){
  const storage={[KEY]:'1'},h=run({...scope,storage});h.finish();
  assert.equal(h.read(),false);await h.clear();assert.equal(storage[KEY],'1');assert.deepEqual(h.access,[]);
 }
 const storage={[KEY]:'1'},guest=run({storage});await guest.clear();assert.equal(storage[KEY],undefined);
 assert.deepEqual(guest.events,['clear','reload']);assert.deepEqual(guest.access,[['remove',KEY]]);
 const held={[KEY]:'1','offmenu-pantry-v1':'[]'},denied=run({storage:held,fail:'reset'});
 await assert.rejects(denied.clear(),/storage denied/);
 assert.equal(held['offmenu-pantry-v1'],undefined);assert.equal(held[KEY],'1');assert.deepEqual(denied.events,['clear']);
});
test('other milestones are unaffected by the new award option',()=>{
 const profile={history:[],plan:[]};assert.deepEqual(milestones(profile,[],true).slice(1),milestones(profile,[],false).slice(1));
});
test('late pending-clear refusal preserves the Guest award and never reloads',async()=>{
 const storage={[KEY]:'1','offmenu-pantry-v1':'[]'},guest=run({storage,fail:'pending'});
 await assert.rejects(guest.clear(),/storage denied/);
 assert.equal(storage['offmenu-pantry-v1'],undefined);
 assert.equal(storage[KEY],'1');
 assert.deepEqual(guest.events,[]);
 assert.deepEqual(guest.access,[['remove','offmenu-pantry-v1']]);
});
