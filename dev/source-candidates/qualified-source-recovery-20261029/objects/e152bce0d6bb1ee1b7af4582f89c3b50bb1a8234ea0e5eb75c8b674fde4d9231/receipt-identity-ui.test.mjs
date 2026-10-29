import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const source=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
const start=source.split('\n').find(line=>line.startsWith('function startCheckout()'));
function harness(session=null,overrides={}){
 const fields={'storage-area':{value:'Kitchen',focus(){}},'shelf-name':{value:'Shelf',focus(){}}};
 let count=0;const ctx={session,selectedArea:'',selectedMode:'waste',feedback:{sound:false},profile:{locations:[{area:'Kitchen',shelf:'Shelf'}]},DEFAULT_LOCATIONS:[],crypto:{randomUUID:()=>`receipt-${++count}`},$:id=>fields[id],confirm:()=>true,t:s=>s,saveDraft(){ctx.saved=JSON.parse(JSON.stringify(ctx.session));},showRun(){},beep(){},persistProfile(){},canEditCheckout:()=>true,...overrides};vm.createContext(ctx);vm.runInContext(start,ctx);return ctx;
}
test('fresh checkout gets one identity and draft persists it',()=>{const h=harness();h.startCheckout();assert.equal(h.session.id,'receipt-1');assert.equal(h.saved.id,h.session.id);});
test('resuming same checkout preserves identity without generating replacement',()=>{const h=harness({id:'existing',mode:'waste',area:'Kitchen',shelf:'Shelf',items:[]});h.startCheckout();assert.equal(h.session.id,'existing');});
test('different checkout creates a distinct receipt identity',()=>{const h=harness();h.startCheckout();const old=h.session.id;h.selectedMode='shopping';h.startCheckout();assert.notEqual(h.session.id,old);});
test('cancelled replacement preserves original receipt',()=>{const h=harness({id:'original',mode:'shopping',area:'Kitchen',shelf:'Shelf',items:[{id:'lot'}]},{confirm:()=>false});h.startCheckout();assert.equal(h.session.id,'original');assert.equal(h.saved,undefined);});
test('current read-only sharing guard remains effective',()=>{const h=harness(null,{canEditCheckout:()=>false});h.startCheckout();assert.equal(h.session,null);});
test('finished receipt retains session identity through existing spread',()=>{assert.match(source,/const finished=\{\.\.\.session,items:session.items.map/);});
