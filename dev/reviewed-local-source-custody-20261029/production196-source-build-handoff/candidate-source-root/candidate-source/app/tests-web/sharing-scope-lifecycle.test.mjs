import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const deferred=()=>{let resolve;const promise=new Promise(r=>resolve=r);return {promise,resolve};};
const settle=()=>new Promise(resolve=>setImmediate(resolve));
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.textContent='';}
 replaceChildren(...nodes){this.children=[...nodes];}
 append(...nodes){this.children.push(...nodes);}
 setAttribute(){}
}
async function harness(){
 const original={};for(const key of ['document','localStorage','fetch','setInterval','__sharingTestSupport'])original[key]=Object.getOwnPropertyDescriptor(globalThis,key);
 const box=new Element('div'),stored=new Map(),applied=[],stateStarted=deferred(),body=deferred();let user={id:'account-a'};
 globalThis.document={getElementById:()=>box,createElement:tag=>new Element(tag),hidden:false};
 globalThis.localStorage={getItem:key=>stored.get(key)??null,setItem:(key,value)=>stored.set(key,value),removeItem:key=>stored.delete(key)};
 globalThis.setInterval=()=>0;
 globalThis.fetch=async path=>{
  if(path==='/api/kitchens')return Response.json({kitchens:[{id:'shared-a',name:'Kitchen A',role:'viewer'}]});
  if(path.endsWith('/members'))return Response.json({members:[]});
  if(path.endsWith('/state')){stateStarted.resolve();return {ok:true,json:()=>body.promise};}
  throw Error('Unexpected request '+path);
 };
 globalThis.__sharingTestSupport={t:x=>x,renderedLanguage:()=>null,apiError:v=>Error(v.error),kitchenProjection:x=>x,applyKitchen:(a,k)=>({...a,...k}),setupSync:()=>({pending:()=>false,reset(){},schedule(){},run:async()=>{}})};
 let source=await readFile(new URL('../public/sharing-ui.js',import.meta.url),'utf8');
 source=source.replace(/^import .* from '\.\/(?:i18n|sync-ui|sync-model)\.js';\n/gm,'');
 source=source.replace("'./scoped-kitchen-request.js'",JSON.stringify(new URL('../public/scoped-kitchen-request.js',import.meta.url).href));
 source='const {t,renderedLanguage,apiError,setupSync,kitchenProjection,applyKitchen}=globalThis.__sharingTestSupport;\n'+source;
 const {setupSharing}=await import('data:text/javascript;base64,'+Buffer.from(source+'\n// '+crypto.randomUUID()).toString('base64'));
 const sharing=setupSharing({getUser:()=>user,isDemo:()=>false,getKey:()=>`pantry-${user.id}`,snapshot:()=>({inventory:[],profile:{}}),apply:state=>applied.push(state),refreshSession:async()=>{},status(){},onScopeChange(){}});
 return {sharing,box,stored,applied,stateStarted,body,switchUser:()=>{user={id:'account-b'};sharing.reset();},cleanup(){for(const [key,descriptor] of Object.entries(original)){if(descriptor)Object.defineProperty(globalThis,key,descriptor);else delete globalThis[key];}}};
}
for(const reset of ['different account','same account reset'])test('late kitchen selection cannot apply after '+reset,async()=>{
 const h=await harness();try{
  await h.sharing.render();const open=h.box.children.find(e=>e.tag==='div').children[0];open.onclick();await h.stateStarted.promise;
  if(reset==='different account')h.switchUser();else h.sharing.reset();
  h.body.resolve({state:{inventory:[{id:'account-a-private-lot'}],profile:{}},revision:7});await settle();await settle();
  assert.deepEqual(h.applied,[]);assert.equal(h.stored.size,0);assert.equal(h.sharing.active(),false);
 }finally{h.cleanup();}
});
test('unchanged account still opens and remembers its selected kitchen',async()=>{
 const h=await harness();try{
  await h.sharing.render();h.box.children.find(e=>e.tag==='div').children[0].onclick();await h.stateStarted.promise;
  const state={inventory:[{id:'authorized-lot'}],profile:{}};h.body.resolve({state,revision:7});await settle();await settle();
  assert.deepEqual(h.applied,[state]);assert.equal(h.sharing.active(),true);assert.equal(h.stored.has('pantry-account-a-shared-session'),true);
 }finally{h.cleanup();}
});
