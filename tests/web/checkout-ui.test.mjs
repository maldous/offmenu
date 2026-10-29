import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parse} from 'acorn';
import {finishInventory,locationKey,makeAutoLot} from '../../public/checkout-model.js';
import {validateLot,validSourceObservationReference} from '../../public/model.js';
import {IDENTIFIER_DB,IDENTIFIER_RUN,DETAIL_SELECTION} from '../../public/scanner-identity-v2.js';
import {reconcileCookedStock} from '../../public/cooking-model.js';
import {t,setLocalizedText,getLanguage} from '../../public/i18n.js';
import * as handoff from '../../public/scanner-kitchen-handoff.js';

// Execute the shipped callbacks, not copies of their logic. The small DOM/storage
// doubles intentionally make no browser, camera, network, or cloud-sync claim.
const source=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');
const nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
const names=['draftKey','saveDraft','readScannerImport','completeScannerHandoff','scannerScopeMatches','today','save','canEditCheckout','autoAccept','trustedIngredient','mappedIngredient','openWorkspace','startCheckout','renderBasket','saveReceipt','renderFinalReceipt','editReceiptItem'];
const functions=names.flatMap(name=>nodes.filter(n=>n.type==='FunctionDeclaration'&&n.id.name===name).map(n=>source.slice(n.start,n.end)));
for(const name of names)assert.equal(nodes.filter(n=>n.type==='FunctionDeclaration'&&n.id.name===name).length,1,name);
const handlers=['void-last','finish-checkout','confirm-finish','add'];
const assignments=handlers.map(id=>{
 const found=nodes.filter(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.property.name===(id==='add'?'onsubmit':'onclick')&&n.expression.left.object.type==='CallExpression'&&n.expression.left.object.callee.name==='$'&&n.expression.left.object.arguments[0]?.value===id);
 assert.equal(found.length,1,id);return source.slice(found[0].start,found[0].end);
});
const closes=nodes.find(n=>n.type==='ForOfStatement'&&source.slice(n.right.start,n.right.end)==="document.querySelectorAll('[data-close]')");
assert.ok(closes,'actual dialog close handlers');
const scanner=nodes.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='scanner'));
const canScan=scanner.declarations[0].init.arguments[0].properties.find(p=>p.key.name==='canScan').value;
class Element {
 constructor(){this.children=[];this.dataset={};this.attributes={};this.value='';this.textContent='';this.hidden=false;this.open=false;this.disabled=false;}
 append(...children){this.children.push(...children);} replaceChildren(...children){this.children=children;}
 setAttribute(key,value){this.attributes[key]=value;} showModal(){this.open=true;} close(){this.open=false;} focus(){}
}
const copy=value=>JSON.parse(JSON.stringify(value));
const inventoryLot=(id,shelf='Shelf 1')=>({id,barcode:'0000000000001',name:'Rice',ingredient:'rice',quantity:100,unit:'g',location:{area:'Pantry',shelf}});
const draft=(items=[],mode='shelf')=>({mode,area:'Pantry',shelf:'Shelf 1',items,startedAt:'2026-10-12T09:00:00Z'});
function harness({inventory=[inventoryLot('old'),inventoryLot('other','Shelf 2')],session=draft(),store=new Map(),lookup=()=>Promise.reject(Error('Unknown')),writable=true}={}){
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const cancel=new Element();cancel.dataset.close='finish-dialog';let dirty=0;
 const ctx={...handoff,$,KEY:'test-pantry',PROFILE:'test-profile',requestIdentity:{owner:null},session:copy(session),pendingScannerImport:null,scannerHandoffOperations:[],scannerHandoffReceipts:{},scannerHandoffStateValid:true,KITCHEN_HANDOFF:'offmenu-scanner-kitchen-pending-v1',validSourceObservationReference,lifecycleFixture:false,location:{search:'?scan=staged'},URLSearchParams,lots:copy(inventory),profile:{batches:[],locations:[]},products:{},feedback:{},latestAcceptedId:null,selectedMode:'shelf',selectedArea:'Pantry',demoMode:false,user:null,lastReceipt:null,editingId:null,crypto,Date,
  document:{createElement:()=>new Element(),querySelectorAll:selector=>selector==='[data-close]'?[cancel]:[]},window:{scrollTo(){}},
  localStorage:{getItem:key=>store.get(key)??null,setItem:(key,value)=>store.set(key,value),removeItem:key=>store.delete(key)},
  sharing:{canWrite:()=>writable},syncStatus:()=>{},finishInventory,locationKey,makeAutoLot,validateLot,reconcileCookedStock,t,setLocalizedText,getLanguage,
  localizedLotName:item=>({value:item.name}),localizedField:(item,key='name')=>({value:item[key]}),showLocalized:(el,text)=>{el.textContent=text.value;},suggest:()=>'',
  getProduct:lookup,markDirty:()=>dirty++,stop(){},setView(){},showRun(){},beep(){},pantry(){},findMeals(){},scanFeedback(){},displayAccepted(){},msg(){},persistProfile(){},DEFAULT_LOCATIONS:[],confirm:()=>false,
 };
 vm.createContext(ctx);vm.runInContext([...functions,...assignments,source.slice(closes.start,closes.end),`globalThis.scanAllowed=${source.slice(canScan.start,canScan.end)};`].join('\n'),ctx);
 return {ctx,$,cancel,store,setWritable:value=>{writable=value;},dirty:()=>dirty};
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
function scannerHandoffFixture(){
 const h=harness({session:{...draft(),id:'existing-receipt'}});
 const barcode='0000000000002',reference={schema:'offmenu-identifier-observation/2',databaseSha256:IDENTIFIER_DB,runId:IDENTIFIER_RUN,namespace:'barcode',originalLexicalValue:barcode,sourceLexicalValue:barcode,symbology:null,matchType:'exact',equivalence:null,disposition:'unresolved',sourceId:'fixture',releaseId:null,sourceRecordId:'fixture-1',observationKey:{run_id:IDENTIFIER_RUN,input_id:'generated-only',record_ordinal:0,assertion_id:1},detailSelectionSha256:DETAIL_SELECTION};
 assert.equal(validSourceObservationReference(reference,barcode),true);
 const handoff={schema:'offmenu-scanner-kitchen-handoff/1',operationId:'11111111-1111-4111-8111-111111111111',barcode,sourceId:'fixture',releaseId:null,name:'Beans',brand:null,assertionId:1,sourceObservationReference:reference};
 h.ctx.pendingScannerImport=handoff;h.$('storage-area').value='Pantry';h.$('shelf-name').value='Shelf 1';
 const removed=[];h.ctx.sessionStorage={removeItem:key=>removed.push(key)};return {...h,handoff,removed};
}
test('real scanner acceptance retains handoff and rolls back unsaved item after storage failure',()=>{
 const h=scannerHandoffFixture(),write=h.ctx.localStorage.setItem;
 h.ctx.localStorage.setItem=(key,value)=>{if(JSON.parse(value).items?.length)throw Error('storage full');write(key,value);};
 h.ctx.startCheckout();assert.equal(h.ctx.session.id,'existing-receipt');assert.equal(h.ctx.session.items.length,0);assert.equal(JSON.parse(h.store.get('test-pantry-checkout')).items.length,0);assert.equal(h.ctx.scannerHandoffOperations.length,0);assert.equal(h.ctx.pendingScannerImport,h.handoff);assert.deepEqual(h.removed,[]);
 h.ctx.localStorage.setItem=write;h.ctx.startCheckout();assert.equal(h.ctx.session.id,'existing-receipt');assert.equal(h.ctx.session.items.length,1);assert.deepEqual(JSON.parse(h.store.get('test-pantry-checkout')).items[0].sourceObservationReference,h.handoff.sourceObservationReference);assert.equal(h.ctx.pendingScannerImport,null);assert.deepEqual(h.removed,[h.ctx.KITCHEN_HANDOFF]);
});
test('saved handoff is consumed once even if rendering the persisted item fails',()=>{
 const h=scannerHandoffFixture();h.ctx.renderBasket=()=>{throw Error('fixture render failed');};
 h.ctx.startCheckout();assert.equal(h.ctx.session.id,'existing-receipt');assert.equal(JSON.parse(h.store.get('test-pantry-checkout')).items.length,1);assert.equal(h.ctx.pendingScannerImport,null);assert.deepEqual(h.removed,[h.ctx.KITCHEN_HANDOFF]);h.ctx.startCheckout();assert.equal(h.ctx.session.items.length,1);
});
test('a waste handoff with no matching stock remains pending and unconsumed',()=>{
 const h=scannerHandoffFixture();h.ctx.session.mode='waste';h.ctx.selectedMode='waste';h.ctx.startCheckout();assert.equal(h.ctx.session.items.length,0);assert.equal(h.ctx.pendingScannerImport,h.handoff);assert.deepEqual(h.removed,[]);
});
test('saved handoff cleanup failure cannot duplicate after real reload; fresh intentional scan remains possible',()=>{
 const first=scannerHandoffFixture(),tab=new Map([[first.ctx.KITCHEN_HANDOFF,JSON.stringify(first.handoff)]]);
 const storage={getItem:key=>tab.get(key)??null,setItem:(key,value)=>tab.set(key,value),removeItem(){throw Error('cleanup unavailable');}};let message='';first.ctx.msg=value=>{message=value;};first.ctx.sessionStorage=storage;first.ctx.startCheckout();
 assert.equal(JSON.parse(first.store.get('test-pantry-checkout')).items.length,1);assert.doesNotMatch(message,/was not saved/);assert.match(message,/saved|staged/);
 const next=harness({session:null,store:first.store});next.ctx.sessionStorage=storage;next.ctx.openWorkspace();next.$('storage-area').value='Pantry';next.$('shelf-name').value='Shelf 1';next.ctx.pendingScannerImport=next.ctx.readScannerImport();assert.ok(next.ctx.pendingScannerImport);next.ctx.startCheckout();
 let persisted=JSON.parse(next.store.get('test-pantry-checkout'));assert.equal(persisted.id,'existing-receipt');assert.equal(persisted.items.length,1);assert.deepEqual(persisted.items[0].sourceObservationReference,first.handoff.sourceObservationReference);
 const fresh={...first.handoff,operationId:'22222222-2222-4222-8222-222222222222'};tab.set(next.ctx.KITCHEN_HANDOFF,JSON.stringify(fresh));next.ctx.pendingScannerImport=next.ctx.readScannerImport();next.ctx.startCheckout();persisted=JSON.parse(next.store.get('test-pantry-checkout'));assert.equal(persisted.items.length,2);assert.notEqual(persisted.items[0].id,persisted.items[1].id);
});
test('legacy handoff receives a stable operation ID before adding inventory',()=>{
 const h=scannerHandoffFixture(),legacy={...h.handoff};delete legacy.operationId;const tab=new Map([[h.ctx.KITCHEN_HANDOFF,JSON.stringify(legacy)]]);h.ctx.sessionStorage={getItem:key=>tab.get(key)??null,setItem:(key,value)=>tab.set(key,value)};
 const first=h.ctx.readScannerImport(),second=h.ctx.readScannerImport();assert.match(first.operationId,/^[0-9a-f-]{36}$/);assert.equal(first.operationId,second.operationId);assert.equal(h.ctx.session.items.length,0);
 h.ctx.sessionStorage.setItem=()=>{throw Error('blocked');};tab.set(h.ctx.KITCHEN_HANDOFF,JSON.stringify(legacy));assert.equal(h.ctx.readScannerImport(),null);assert.equal(h.ctx.session.items.length,0);
});
test('consumed handoff identity survives draft completion and reload',()=>{
 const first=scannerHandoffFixture(),tab=new Map([[first.ctx.KITCHEN_HANDOFF,JSON.stringify(first.handoff)]]);const storage={getItem:key=>tab.get(key)??null,setItem:(key,value)=>tab.set(key,value),removeItem(){throw Error('cleanup unavailable');}};first.ctx.sessionStorage=storage;first.ctx.startCheckout();
 const saved=JSON.parse(first.store.get('test-pantry-checkout'));assert.equal(saved.items.length,1);assert.deepEqual(saved.scannerHandoffOperations,[first.handoff.operationId]);first.ctx.session=null;first.ctx.saveDraft();
 const next=harness({session:null,store:first.store});next.ctx.sessionStorage=storage;next.ctx.openWorkspace();assert.equal(next.ctx.session,null);next.ctx.pendingScannerImport=next.ctx.readScannerImport();next.ctx.startCheckout();assert.equal(next.ctx.session,null);assert.deepEqual(JSON.parse(next.store.get('test-pantry-checkout')).scannerHandoffOperations,[first.handoff.operationId]);
});
test('invalid saved handoff history fails closed without overwriting it',()=>{
 const h=scannerHandoffFixture(),raw=JSON.stringify({scannerHandoffOperations:['invalid']});h.store.set('test-pantry-checkout',raw);h.ctx.openWorkspace();h.ctx.pendingScannerImport=h.handoff;h.ctx.startCheckout();assert.equal(h.ctx.session,null);assert.equal(h.ctx.pendingScannerImport,h.handoff);assert.equal(h.store.get('test-pantry-checkout'),raw);
});
function receiptVoid(h){return h.$('finish-items').children[0].children.at(-1).children.at(-1);}

test('final receipt and cancel keep inventory intact; explicit confirmation replaces only the selected shelf',()=>{
 const h=harness({session:draft([inventoryLot('new')])});h.ctx.saveDraft();const before=copy(h.ctx.lots);
 h.$('finish-checkout').onclick();assert.equal(h.$('finish-dialog').open,true);assert.deepEqual(copy(h.ctx.lots),before);assert.equal(h.store.has('test-pantry'),false);
 h.cancel.onclick();assert.equal(h.$('finish-dialog').open,false);assert.equal(h.ctx.session.items.length,1);assert.equal(h.dirty(),0);
 h.$('finish-checkout').onclick();h.$('confirm-finish').onclick();
 assert.deepEqual(copy(h.ctx.lots).map(l=>l.id),['other','new']);assert.equal(h.ctx.session,null);assert.equal(h.store.has('test-pantry-checkout'),false);assert.equal(h.$('finish-dialog').open,false);
 assert.equal(JSON.parse(h.store.get('test-profile')).lastReceipt.items[0].id,'new');assert.equal(JSON.parse(h.store.get('test-pantry'))[1].id,'new');
});
test('Void from basket, final receipt, and last-item action removes only staged items, including a late lookup',async()=>{
 let resolve;const h=harness({lookup:()=>new Promise(r=>resolve=r)});h.ctx.autoAccept('0000000000001');assert.equal(h.ctx.session.items[0].pending,true);
 h.$('basket').children[0].children[1].onclick();resolve({name:'Rice',ingredient:'rice',quantity:'1 kg'});await tick();
 assert.equal(h.ctx.session.items.length,0);assert.equal(JSON.parse(h.store.get('test-pantry-checkout')).items.length,0);
 h.ctx.autoAccept('0000000000001',{name:'Rice',ingredient:'rice',quantity:'1 kg'});h.$('finish-checkout').onclick();receiptVoid(h).onclick();
 assert.equal(h.$('confirm-finish').disabled,true);assert.equal(h.ctx.session.items.length,0);
 h.ctx.autoAccept('0000000000001',{name:'Rice',ingredient:'rice',quantity:'1 kg'});h.$('void-last').onclick();assert.equal(h.ctx.session.items.length,0);
 assert.equal(h.ctx.lots.length,2);assert.equal(h.store.has('test-pantry'),false);
});
test('reload restores a staged unknown package without committing or inventing a measured quantity',()=>{
 const item={...makeAutoLot('0000000000001',null),pending:true};const store=new Map();const h=harness({session:draft([item]),store});h.ctx.saveDraft();
 const reloaded=harness({session:null,store});reloaded.ctx.openWorkspace();const restored=reloaded.ctx.session.items[0];
 assert.equal(restored.pending,false);assert.equal(restored.quantity,1);assert.equal(restored.unit,'count');assert.equal(restored.amountBasis,'package');assert.equal(restored.needsReview,true);
 assert.equal(reloaded.ctx.lots.length,2);assert.equal(store.has('test-pantry'),false);
 reloaded.$('finish-checkout').onclick();assert.match(reloaded.$('finish-items').children[0].children[1].textContent,/1 package/);
});
test('confirmation during a pending lookup retains the unknown package and ignores late hydration',async()=>{
 let resolve;const h=harness({lookup:()=>new Promise(r=>resolve=r)});h.ctx.autoAccept('0000000000001');h.$('finish-checkout').onclick();h.$('confirm-finish').onclick();
 const before=h.store.get('test-pantry');resolve({name:'Rice',ingredient:'rice',quantity:'1 kg'});await tick();
 assert.equal(h.store.get('test-pantry'),before);assert.equal(h.ctx.lots.at(-1).unit,'count');assert.equal(h.ctx.lots.at(-1).needsReview,true);assert.equal(h.ctx.lastReceipt.items[0].pending,false);assert.equal(h.store.has('test-pantry-checkout'),false);
});
test('read-only permission is enforced by checkout callbacks regardless of button text',()=>{
 const h=harness({session:draft([inventoryLot('new')])});h.ctx.saveDraft();h.$('finish-checkout').onclick();const rowVoid=receiptVoid(h);h.ctx.renderBasket();const basketVoid=h.$('basket').children[0].children[1];
 h.setWritable(false);const before=JSON.stringify({lots:h.ctx.lots,session:h.ctx.session,store:[...h.store]});
 assert.equal(h.ctx.scanAllowed(),false);h.ctx.autoAccept('0000000000002',{name:'Beans',ingredient:'beans',quantity:'1 kg'});
 for(const button of [basketVoid,rowVoid,h.$('void-last'),h.$('confirm-finish')]){button.textContent='✓ تأكيد';button.onclick();}
 h.ctx.editReceiptItem(h.ctx.session.items[0],h.ctx.session);h.ctx.editingId='new';h.$('add').onsubmit({preventDefault(){}});
 assert.equal(JSON.stringify({lots:h.ctx.lots,session:h.ctx.session,store:[...h.store]}),before);assert.equal(h.dirty(),0);
 const fresh=harness({session:null,writable:false});fresh.$('storage-area').value='Pantry';fresh.$('shelf-name').value='Shelf 1';fresh.ctx.startCheckout();assert.equal(fresh.ctx.session,null);assert.equal(fresh.store.size,0);
 const waste=harness({session:draft([inventoryLot('old')],'waste')});waste.ctx.saveDraft();waste.$('finish-checkout').onclick();const amount=waste.$('finish-items').children[0].children[2].children[0];waste.setWritable(false);const wasteBefore=waste.store.get('test-pantry-checkout');amount.value='25';amount.oninput();assert.equal(waste.ctx.session.items[0].discardQuantity,undefined);assert.equal(waste.store.get('test-pantry-checkout'),wasteBefore);
});
test('permission loss during a lookup prevents late draft mutation',async()=>{
 let resolve;const h=harness({lookup:()=>new Promise(r=>resolve=r)});h.ctx.autoAccept('0000000000001');const before=JSON.stringify(h.ctx.session),stored=h.store.get('test-pantry-checkout');
 h.setWritable(false);resolve({name:'Rice',ingredient:'rice',quantity:'1 kg'});await tick();assert.equal(JSON.stringify(h.ctx.session),before);assert.equal(h.store.get('test-pantry-checkout'),stored);
});

test('read-only final confirmation cannot write inventory or a receipt',()=>{
 const h=harness({session:draft([inventoryLot('new')])});h.ctx.saveDraft();h.$('finish-checkout').onclick();h.setWritable(false);
 h.$('confirm-finish').textContent='✓ Confirm shelf receipt';h.$('confirm-finish').onclick();
 assert.equal(h.store.has('test-pantry'),false);assert.equal(h.store.has('test-profile'),false);assert.equal(h.ctx.session.items.length,1);assert.equal(h.dirty(),0);
});
