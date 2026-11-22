import assert from 'node:assert/strict';
import test from 'node:test';
import {getLanguage,hasTranslation,setLanguage,setLocalizedText} from '../../apps/web/src/i18n.js';
import {setupCare} from '../../apps/web/src/care-ui.js';

function mount(){
 class Node{
  constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.ownerDocument=d;this.lang='';this.textWrites=0;}
  set textContent(value){this.value=value;this.textWrites++;}
  get textContent(){return this.value??'';}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  removeChild(child){this.children=this.children.filter(x=>x!==child);}
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
 function notice(){function find(n){return n.attrs.role==='status'?n:n.children.map(find).find(Boolean)}return find(root);}
 const status=()=>notice()?.textContent;
 return {care,status,notice,paths,setActor:a=>{actor=a;},setCases:b=>{cases=b;},hold:p=>{pending=p;}};
}
test('mounted Care distinguishes Guest, loading, unavailable, malformed and confirmed empty',async()=>{
 const m=mount();
 m.setActor(null);await m.care.refresh();
 assert.equal(m.status(),'Sign in to view your requests.');
 assert.ok(!m.paths.includes('/api/care/cases'));
 m.setActor({id:'synthetic-a'});
 const notice=m.notice();
 const first=m.care.refresh();assert.equal(m.notice(),notice);assert.equal(m.status(),'Loading your requests…');
 await first;assert.equal(m.notice(),notice);assert.equal(m.status(),'No requests yet.');
 m.setCases({});await m.care.refresh();assert.equal(m.notice(),notice);assert.equal(m.status(),'Could not load your requests.');
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

test('populated refresh clears and hides the same region; reset clears and detaches it',async()=>{
 const m=mount();await m.care.refresh();const node=m.notice();
 m.setCases({cases:[{id:'fixture',category:'support',title:'Test item',status:'open'}]});
 await m.care.refresh();assert.equal(m.notice(),node);assert.equal(node.textContent,'');assert.equal(node.hidden,true);
 m.setActor({id:'synthetic-b'});m.care.render();assert.equal(m.notice(),node);assert.equal(node.textContent,'Loading your requests…');
 m.setCases({cases:[]});await m.care.refresh();assert.equal(m.notice(),node);assert.equal(node.hidden,false);
 m.care.reset();assert.equal(node.textContent,'');assert.equal(m.notice(),undefined);
});

test('Arabic Care marks untranslated live status as English without replacing or rewriting it',async()=>{
 const previous=getLanguage();setLanguage('ar');
 try{
  const m=mount();m.setActor(null);await m.care.refresh();const node=m.notice();
  assert.equal(node.dir,'auto');
  assert.equal(node.lang,'en');assert.equal(node.textContent,'Sign in to view your requests.');
  const writes=node.textWrites;m.care.render();
  assert.equal(m.notice(),node);assert.equal(node.textWrites,writes);
  m.setActor({id:'synthetic-a'});await m.care.refresh();
  assert.equal(node.lang,'en');assert.equal(node.textContent,'No requests yet.');
  m.care.reset();assert.equal(node.lang,'');
  // The actual i18n helper reports an existing Arabic catalogue entry separately.
  // No Care status string currently has a reviewed Arabic catalogue entry.
  const translated={};assert.equal(hasTranslation('Interface language','ar'),true);
  setLocalizedText(translated,'Interface language');assert.equal(translated.lang,'ar');
 }finally{setLanguage(previous);}
});
