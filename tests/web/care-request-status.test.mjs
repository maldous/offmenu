import assert from 'node:assert/strict';
import test from 'node:test';
import {setupCare} from '../../apps/web/src/care-ui.js';

function mount(){
 class Node{
  constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.ownerDocument=d;}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  setAttribute(k,v){this.attrs[k]=v;}
 }
 const d={createElement:t=>new Node(t)},root=d.createElement('main');
 let actor={id:'synthetic-a'},cases={cases:[]},pending;
 const paths=[];
 const ok=b=>({ok:true,json:async()=>b});
 const care=setupCare({root,getUser:()=>actor,authFetch:async path=>{
   paths.push(path);
   if(path==='/api/care/cases')return pending??ok(cases);
   return ok({});
 }});
 function status(){function find(n){return n.attrs.role==='status'?n:n.children.map(find).find(Boolean)}return find(root)?.textContent;}
 return {care,status,paths,setActor:a=>{actor=a;},setCases:b=>{cases=b;},hold:p=>{pending=p;}};
}
test('mounted Care distinguishes Guest, loading, unavailable, malformed and confirmed empty',async()=>{
 const m=mount();
 m.setActor(null);await m.care.refresh();
 assert.equal(m.status(),'Sign in to view your requests.');
 assert.ok(!m.paths.includes('/api/care/cases'));
 m.setActor({id:'synthetic-a'});
 const first=m.care.refresh();assert.equal(m.status(),'Loading your requests…');
 await first;assert.equal(m.status(),'No requests yet.');
 m.setCases({});await m.care.refresh();assert.equal(m.status(),'Could not load your requests.');
 m.hold(Promise.resolve({ok:false,json:async()=>({})}));await m.care.refresh();
 assert.equal(m.status(),'Could not load your requests.');
});
test('a late result cannot overwrite the latest owner and request state',async()=>{
 const m=mount();
 let release,started;const entered=new Promise(r=>{started=r});
 const oldResponse=new Promise(r=>{release=r});
 m.hold({then: (resolve,reject)=>{started();oldResponse.then(resolve,reject);}});
 const old=m.care.refresh();await entered;
 m.setActor(null);await m.care.refresh();
 release({ok:true,json:async()=>({cases:[]})});await old;
 assert.equal(m.status(),'Sign in to view your requests.');
});
