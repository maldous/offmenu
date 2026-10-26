// Synthetic DOM harness only: no browser, backend export, real identity or crypto qualification.
import test from 'node:test';
import assert from 'node:assert/strict';
import {setupOwnedBackupAccount} from '../public/owned-backup-account-ui.js';
const metadata=()=>({packageId:'synthetic-package',recoveryRef:'synthetic-recovery',keyReference:{keyRef:'synthetic-reference',keyVersion:1}});
const sealed=()=>({schemaVersion:'offmenu-private-portable-package/1',packageId:'synthetic-package',kind:'owned-backup',source:{namespace:'synthetic-instance',schemaVersion:'offmenu-household-domain/1'},identity:{ownerUserId:'synthetic-owner',issuer:'https://synthetic.invalid/issuer',subject:'synthetic-subject'},recipient:{ownerUserId:'synthetic-owner',issuer:'https://synthetic.invalid/issuer',subject:'synthetic-subject'},createdAt:'2026-10-26T00:00:00.000Z',scope:{fields:[],records:[]},consent:{id:'synthetic-consent',revision:1},protection:{recoveryRef:'synthetic-recovery'},manifestDigest:'a'.repeat(64),checksum:'b'.repeat(64),envelope:{version:1,algorithm:'AES-256-GCM',custody:'server-envelope',keyRef:'synthetic-reference',keyVersion:1,nonce:'AAAAAAAAAAAAAAAA',ciphertext:'AAAAAAAAAAAAAAAAAAAAAAAA'}});
const response=(value=sealed(),options={})=>Response.json(value,{status:200,headers:{'Content-Disposition':'attachment; filename="offmenu-owned-backup.json"',...options.headers},...options});
class Element{
 constructor(){this.attributes={};this.events=new Map();this.disabled=false;this.textContent='';}
 setAttribute(k,v){this.attributes[k]=v;}
 addEventListener(k,f){this.events.set(k,f);}
 removeEventListener(k){this.events.delete(k);}
 async click(){if(!this.disabled)return this.events.get('click')?.({preventDefault(){}});}
}
function harness({getMetadata=metadata,fetchImpl=async()=>response(),signedIn=true,open=true,anchorThrows=false}={}){
 const button=new Element(),status=new Element(),root=new Element(),dialog=new Element(),fetches=[],downloads=[],urls=[],revoked=[],timers=new Map();let nextTimer=0,user=signedIn?{id:'synthetic-owner'}:null;
 dialog.open=open;const document={defaultView:{URL:{createObjectURL(blob){const url='blob:synthetic-'+urls.length;urls.push({url,blob});return url;},revokeObjectURL(url){revoked.push(url);}},setTimeout(fn,ms){timers.set(++nextTimer,{fn,ms});return nextTimer;},clearTimeout(id){timers.delete(id);}},body:{append(a){a.attached=true;}},createElement(type){assert.equal(type,'a');const a={attached:false,remove(){a.attached=false;},click(){if(anchorThrows)throw Error('Synthetic download-adapter failure');assert.equal(a.attached,true);downloads.push({href:a.href,filename:a.download});}};return a;}};
 root.ownerDocument=document;root.querySelector=s=>s==='#owned-backup-download'?button:s==='#owned-backup-status'?status:null;
 const ui=setupOwnedBackupAccount({root,dialog,getUser:()=>user,getMetadata,fetchImpl:async(...args)=>{fetches.push(args);return fetchImpl(...args);}});
 return {ui,root,dialog,button,status,fetches,downloads,urls,revoked,timers,setUser:v=>{user=v;},close(){dialog.open=false;dialog.events.get('close')();},drainCleanup(){for(const [id,t]of timers)if(t.ms===1000){timers.delete(id);t.fn();}}};
}

test('DOM harness click sends exact nonsecret metadata and downloads only validated sealed bytes',async()=>{
 const h=harness();assert.equal(await h.ui.refresh(),true);await h.button.click();
 assert.equal(h.fetches.length,1);const [path,options]=h.fetches[0];assert.equal(path,'/api/private-portability/owned-backup/export');
 assert.deepEqual(JSON.parse(options.body),metadata());assert.equal(options.credentials,'same-origin');assert.equal(options.mode,'same-origin');assert.equal(options.redirect,'error');assert.equal(options.method,'POST');assert.equal(options.cache,'no-store');assert.deepEqual(options.headers,{'Content-Type':'application/json',Accept:'application/json'});
 assert.equal(h.downloads.length,1);assert.equal(h.downloads[0].filename,'offmenu-owned-backup.json');assert.deepEqual(JSON.parse(await h.urls[0].blob.text()),sealed());assert.equal(h.urls[0].blob.type,'application/json');
 assert.equal(h.root.attributes['aria-busy'],'false');assert.match(h.status.textContent,/download started/);assert.equal(h.button.disabled,false);assert.equal(h.revoked.length,0);h.drainCleanup();assert.deepEqual(h.revoked,[h.downloads[0].href]);assert.equal(h.timers.size,0);
});
test('signed out, closed dialog, absent metadata and caller authority fields stay unavailable with zero requests',async()=>{
 for(const options of [{signedIn:false},{open:false},{getMetadata:()=>null},{getMetadata:()=>({...metadata(),owner:'forbidden'})}]){
  const h=harness(options);assert.equal(await h.ui.refresh(),false);assert.equal(h.button.disabled,true);await h.button.click();assert.equal(h.fetches.length,0);assert.equal(h.downloads.length,0);
 }
});
test('default provider accurately disables the action without fabricating package metadata',async()=>{
 const h=harness({getMetadata:()=>undefined});await h.ui.refresh();assert.equal(h.button.disabled,true);assert.match(h.status.textContent,/unavailable/);assert.equal(h.urls.length,0);
});
test('HTTP refusal never downloads error JSON and permits an explicit retry',async()=>{
 let calls=0;const h=harness({fetchImpl:async()=>++calls===1?Response.json({error:'synthetic refusal'},{status:403}):response()});await h.ui.refresh();await h.button.click();
 assert.equal(h.downloads.length,0);assert.equal(h.urls.length,0);assert.match(h.status.textContent,/not authorized/);assert.equal(h.button.disabled,false);
 await h.button.click();assert.equal(h.downloads.length,1);h.drainCleanup();
});
test('200 error JSON, unsafe filename, missing attachment and oversized response are rejected',async()=>{
 const variants=[()=>response({error:'not a backup'}),()=>response(sealed(),{headers:{'Content-Disposition':'attachment; filename="../account.json"'}}),()=>Response.json(sealed()),()=>new Response(' '.repeat(2_000_001),{headers:{'Content-Type':'application/json','Content-Disposition':'attachment; filename="offmenu-owned-backup.json"'}})];
 for(const fetchImpl of variants){const h=harness({fetchImpl});await h.ui.refresh();await h.button.click();assert.equal(h.downloads.length,0);assert.equal(h.urls.length,0);assert.match(h.status.textContent,/could not be downloaded/);assert.equal(h.button.disabled,false);}
});
test('busy duplicate clicks do not repeat the request; closing aborts and discards a late response',async()=>{
 let resolve;const h=harness({fetchImpl:()=>new Promise(r=>{resolve=r;})});await h.ui.refresh();const pending=h.button.click();await Promise.resolve();assert.equal(h.fetches.length,1);assert.equal(h.root.attributes['aria-busy'],'true');await h.button.click();assert.equal(h.fetches.length,1);
 h.close();assert.equal(h.fetches[0][1].signal.aborted,true);resolve(response());await pending;assert.equal(h.downloads.length,0);assert.equal(h.urls.length,0);assert.equal(h.button.disabled,true);assert.equal(h.timers.size,0);
});
test('an account switch discards the previous account response',async()=>{
 let resolve;const h=harness({fetchImpl:()=>new Promise(r=>{resolve=r;})});await h.ui.refresh();const pending=h.button.click();await Promise.resolve();h.setUser({id:'other-synthetic-owner'});h.ui.reset();resolve(response());await pending;assert.equal(h.downloads.length,0);assert.equal(h.urls.length,0);assert.equal(h.button.disabled,true);
});
test('download-adapter failure revokes the object URL and reports an accessible retry error',async()=>{
 const h=harness({anchorThrows:true});await h.ui.refresh();await h.button.click();assert.equal(h.downloads.length,0);assert.equal(h.urls.length,1);assert.deepEqual(h.revoked,[h.urls[0].url]);assert.match(h.status.textContent,/could not be downloaded/);assert.equal(h.button.disabled,false);assert.equal(h.timers.size,0);
});
