import test from 'node:test';
import assert from 'node:assert/strict';
const deferred=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
function environment(t){
 const names=['window','navigator','document','localStorage','indexedDB','setInterval','setTimeout','clearTimeout'];
 const originals=new Map(names.map(k=>[k,Object.getOwnPropertyDescriptor(globalThis,k)]));
 t.after(()=>{for(const [k,v]of originals)if(v)Object.defineProperty(globalThis,k,v);else delete globalThis[k];});
 const set=(key,value)=>Object.defineProperty(globalThis,key,{configurable:true,writable:true,value});
 const storage=new Map(),writes=[],statuses=[],applies=[];
 set('window',{addEventListener(){}});set('navigator',{onLine:true});set('document',{hidden:false});
 set('setInterval',()=>1);set('setTimeout',()=>1);set('clearTimeout',()=>{});
 set('localStorage',{getItem:k=>storage.get(k)??null,setItem:(k,v)=>{writes.push(k);storage.set(k,v);},removeItem:k=>{writes.push(k);storage.delete(k);}});
 const db={transaction(){const tx={objectStore:()=>({put(){queueMicrotask(()=>tx.oncomplete?.());},get(){const r={result:undefined};queueMicrotask(()=>r.onsuccess?.());return r;}})};return tx;}};
 set('indexedDB',{open(){const r={result:db};queueMicrotask(()=>r.onsuccess?.());return r;}});
 return {writes,statuses,applies};
}
for(const kind of ['changed-account','same-account-stale-generation','ordinary-failure'])test('sync safely handles '+kind,async t=>{
 const f=environment(t),started=deferred(),response=deferred();let account='synthetic-alice';
 // Fresh real module state isolates its private IndexedDB promise per fixture.
 const {setupSync}=await import('../../apps/web/src/sync-ui.js?scope-cancellation='+kind);
 const sync=setupSync({getUser:()=>account?{id:account}:null,isDemo:()=>false,getKey:()=>account+'-kitchen',snapshot:()=>({inventory:[],products:{},recipes:[],profile:{}}),apply:s=>f.applies.push(s),request:async()=>{started.resolve();return response.promise;},onStatus:(...args)=>f.statuses.push(args)});
 const running=sync.run();await started.promise;
 if(kind==='changed-account')account='synthetic-bob';
 response.reject(kind==='changed-account'?Symbol('old-sharing-cancellation'):kind==='same-account-stale-generation'?new DOMException('Stale sharing scope','AbortError'):new Error('Synthetic transport failure'));
 await assert.doesNotReject(running);
 assert.deepEqual(f.applies,[]);assert.deepEqual(f.writes,[]);
 if(kind==='ordinary-failure')assert.match(f.statuses[0][0],/Synthetic transport failure/);else assert.deepEqual(f.statuses,[]);
});
