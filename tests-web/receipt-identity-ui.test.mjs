import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {parse} from 'acorn';
import {PUBLIC_SCANNER_HANDOFF} from '../public/scanner-kitchen-handoff.js';
const source=fs.readFileSync(new URL('../public/app.js',import.meta.url),'utf8');
const nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
const declaration=name=>{const n=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);assert.ok(n,name);return source.slice(n.start,n.end);};
const cleanup=declaration('completeScannerHandoff'),start=declaration('startCheckout'),scope=declaration('scannerScopeMatches');
function harness(session=null,overrides={}){
 const fields={'storage-area':{value:'Kitchen',focus(){}},'shelf-name':{value:'Shelf',focus(){}}};
 let count=0;const ctx={PUBLIC_SCANNER_HANDOFF,session,pendingScannerImport:null,scannerHandoffOperations:[],scannerHandoffStateValid:true,KITCHEN_HANDOFF:'offmenu-scanner-kitchen-pending-v1',selectedArea:'',selectedMode:'waste',feedback:{sound:false},profile:{locations:[{area:'Kitchen',shelf:'Shelf'}]},DEFAULT_LOCATIONS:[],crypto:{randomUUID:()=>`receipt-${++count}`},$:id=>fields[id],confirm:()=>true,t:s=>s,saveDraft(){ctx.saved=JSON.parse(JSON.stringify(ctx.session));},showRun(){},beep(){},persistProfile(){},canEditCheckout:()=>true,...overrides};vm.createContext(ctx);vm.runInContext(scope+'\n'+cleanup+'\n'+start,ctx);return ctx;
}
test('fresh checkout gets one identity and draft persists it',()=>{const h=harness();h.startCheckout();assert.equal(h.session.id,'receipt-1');assert.equal(h.saved.id,h.session.id);});
test('resuming same checkout preserves identity without generating replacement',()=>{const h=harness({id:'existing',mode:'waste',area:'Kitchen',shelf:'Shelf',items:[]});h.startCheckout();assert.equal(h.session.id,'existing');});
test('different checkout creates a distinct receipt identity',()=>{const h=harness();h.startCheckout();const old=h.session.id;h.selectedMode='shopping';h.startCheckout();assert.notEqual(h.session.id,old);});
test('cancelled replacement preserves original receipt',()=>{const h=harness({id:'original',mode:'shopping',area:'Kitchen',shelf:'Shelf',items:[{id:'lot'}]},{confirm:()=>false});h.startCheckout();assert.equal(h.session.id,'original');assert.equal(h.saved,undefined);});
test('current read-only sharing guard remains effective',()=>{const h=harness(null,{canEditCheckout:()=>false});h.startCheckout();assert.equal(h.session,null);});
test('finished receipt retains session identity through existing spread',()=>{assert.match(source,/const finished=\{\.\.\.session,items:session.items.map/);});
test('scanner handoff uses the resumed receipt and preserves the exact source observation',()=>{
 const reference={matchType:'representation-alias',equivalence:'UPC-A to EAN-13',disposition:'unresolved'};
 const handoff={operationId:'11111111-1111-4111-8111-111111111111',barcode:'012345678905',sourceId:'retained-fixture',releaseId:'fixture-release',name:null,brand:'Fixture',sourceObservationReference:reference};
 const removed=[];let accepted;
 const h=harness({id:'existing',mode:'shopping',area:'Kitchen',shelf:'Shelf',items:[]},{selectedMode:'shopping',pendingScannerImport:handoff,sessionStorage:{removeItem:key=>removed.push(key)},autoAccept(code,product){accepted={code,product,receipt:h.session.id};h.session.items.push({barcode:code,sourceObservationReference:product.sourceObservationReference});h.saveDraft();return true;},msg(value){h.message=value;}});
 h.startCheckout();assert.equal(accepted.receipt,'existing');assert.equal(h.saved.id,'existing');assert.equal(accepted.code,handoff.barcode);assert.equal(accepted.product.sourceObservationReference,reference);assert.equal(h.saved.items[0].sourceObservationReference.disposition,'unresolved');assert.equal(accepted.product.retainedSource,true);assert.deepEqual(Object.keys(accepted.product.nutriments),[]);assert.equal(accepted.product.quantity,'');assert.equal(h.pendingScannerImport,null);assert.deepEqual(removed,[h.KITCHEN_HANDOFF]);assert.match(h.message,/labelled UPC-A to EAN-13/);
});
test('a throwing scanner handoff retains its pending source and storage entry',()=>{
 const handoff={operationId:'11111111-1111-4111-8111-111111111111',barcode:'012345678905',sourceId:'retained-fixture',releaseId:null,name:null,brand:null,sourceObservationReference:{disposition:'unresolved',matchType:'exact'}};
 const removed=[];const h=harness(null,{selectedMode:'shopping',pendingScannerImport:handoff,sessionStorage:{removeItem:key=>removed.push(key)},autoAccept(){throw Error('fixture save failed');},msg(value){h.message=value;}});
 h.startCheckout();assert.equal(h.session.id,'receipt-1');assert.equal(h.pendingScannerImport,handoff);assert.deepEqual(removed,[]);assert.match(h.message,/handoff was not saved: fixture save failed/);
});
