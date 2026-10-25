import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {validateLot,validSourceObservationReference} from '../public/model.js';
import {finishInventory,makeAutoLot,locationKey} from '../public/checkout-model.js';
import {reconcileCookedStock} from '../public/cooking-model.js';
import {t,setLocalizedText,getLanguage} from '../public/i18n.js';
import * as handoff from '../public/scanner-kitchen-handoff.js';
import {createPublicLookup} from '../public/production-scanner/scanner-production-lookup.js';
const {parse}=createRequire(import.meta.url)('acorn');
const root=new URL('..',import.meta.url),app=fs.readFileSync(new URL('public/app.js',root),'utf8'),nodes=parse(app,{ecmaVersion:'latest',sourceType:'module'}).body;
const uuid=n=>String(n).padStart(8,'0')+'-1111-4111-8111-111111111111';
const inputs=[1,2].map(n=>({operationId:uuid(n),barcode:'000000001313'+n,name:'Generated product '+n,brand:null,publicProductReference:{schema:handoff.PUBLIC_PRODUCT_REFERENCE,...handoff.PUBLIC_PRODUCT_SELECTION,recordId:'offmenu:generated:'+n,namespace:'barcode',lexicalValue:'000000001313'+n,provenance:{sourceId:'off',visibility:'public',license:'Generated source declaration',attribution:'Generated fixture',url:null,sourceDate:null}}}));
class Element{constructor(){this.children=[];this.dataset={};this.value='';this.textContent='';this.hidden=false;this.open=false;this.classList={toggle(){}};}append(...v){this.children.push(...v);}replaceChildren(...v){this.children=[...v];}setAttribute(k,v){this[k]=v;}showModal(){this.open=true;}close(){this.open=false;}focus(){}}
class DiskStorage{
 constructor(file){this.file=file;this.fail=null;this.writes=[];if(!fs.existsSync(file))fs.writeFileSync(file,'{}');}
 values(){return JSON.parse(fs.readFileSync(this.file,'utf8'));}getItem(k){return this.values()[k]??null;}
 setItem(k,v){if(this.fail?.(k,v))throw Error('Generated storage failure');const all=this.values();all[k]=String(v);fs.writeFileSync(this.file,JSON.stringify(all));this.writes.push(k);}
 removeItem(k){const all=this.values();delete all[k];fs.writeFileSync(this.file,JSON.stringify(all));this.writes.push(k);}
}
function fixture(t){const dir=fs.mkdtempSync(path.join(os.tmpdir(),'offmenu-scanner-finish-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));return {store:new DiskStorage(path.join(dir,'inventory.json')),tab:new DiskStorage(path.join(dir,'tab.json'))};}
function harness(store,tab,{writable=true,key='generated-pantry-A',owner=null,restore=false}={}){
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const ctx={...handoff,$,crypto,Date,URLSearchParams,TextEncoder,KEY:key,PROFILE:'generated-profile-A',PRODUCTS:'generated-products-A',SELECTIONS:'generated-selections-A',requestIdentity:{owner},applicationDefaults:{batches:[],locations:[]},authResolved:false,syncReady:false,applyFeedbackSettings(){},
 session:null,pendingScannerImport:null,scannerHandoffOperations:[],scannerHandoffReceipts:{},scannerHandoffStateValid:true,KITCHEN_HANDOFF:handoff.SCANNER_HANDOFF_KEY,lifecycleFixture:false,location:{search:'?scan=staged'},
 lots:JSON.parse(store.getItem(key)||'[]').map(validateLot),profile:JSON.parse(store.getItem('generated-profile-A')||'{"batches":[],"locations":[]}'),products:{},feedback:{},latestAcceptedId:null,selectedMode:'shopping',selectedArea:'Pantry',demoMode:false,user:null,lastReceipt:null,editingId:null,
 document:{createElement:()=>new Element(),querySelectorAll:()=>[]},window:{scrollTo(){}},localStorage:store,sessionStorage:tab,sharing:{canWrite:()=>writable},syncStatus(){},
 finishInventory,makeAutoLot,locationKey,validateLot,validSourceObservationReference,reconcileCookedStock,t,setLocalizedText,getLanguage,
 localizedLotName:item=>({value:item.name}),localizedField:(item,key='name')=>({value:item[key]}),showLocalized:(el,value)=>{el.textContent=value.value;},suggest:()=>'',
 markDirty(){},stop(){},setView(){},showRun(){},beep(){},pantry(){},findMeals(){},scanFeedback(){},displayAccepted(){},msg(value){ctx.message=value;},persistProfile(){},DEFAULT_LOCATIONS:[],confirm:()=>false,getProduct(){throw Error('No provider calls in generated persistence checks');}};
 const names=['draftKey','saveDraft','readScannerImport','completeScannerHandoff','scannerScopeMatches','today','save','canEditCheckout','autoAccept','trustedIngredient','mappedIngredient','openWorkspace','startCheckout','renderBasket','saveReceipt','renderFinalReceipt','editReceiptItem','loadProfile'];
 const functions=nodes.filter(n=>n.type==='FunctionDeclaration'&&names.includes(n.id.name));
 const handlers=nodes.filter(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.object.type==='CallExpression'&&['confirm-finish','finish-checkout','add'].includes(n.expression.left.object.arguments[0]?.value));
 vm.createContext(ctx);vm.runInContext([...functions,...handlers].map(n=>app.slice(n.start,n.end)).join('\n'),ctx);
 // Execute the exact existing reload expressions without calling auth, network,
 // service-worker, or recipe startup. This is not authentication acceptance.
 ctx.loadProfile();const init=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='init');
 const initTry=init.body.body.find(n=>n.type==='TryStatement');const stockReads=initTry.block.body.filter(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&['lots','products'].includes(n.expression.left.name));assert.equal(stockReads.length,2);vm.runInContext(stockReads.map(n=>app.slice(n.start,n.end)).join('\n'),ctx);
 if(restore)ctx.openWorkspace();$('storage-area').value='Pantry';$('shelf-name').value='Generated shelf';
 return {ctx,$,setWritable(v){writable=v;}};
}
function stage(h,tab){tab.setItem(handoff.SCANNER_HANDOFF_KEY,JSON.stringify({schema:handoff.PUBLIC_SCANNER_HANDOFF,items:inputs,KEY:'foreign-space',owner:'not-authority'}));h.ctx.pendingScannerImport=h.ctx.readScannerImport();assert.ok(h.ctx.pendingScannerImport,'actual receiver accepts the typed public handoff');h.ctx.startCheckout();}
function review(h){for(const item of h.ctx.session.items){h.ctx.editingId=item.id;h.$('name').value=item.name;h.$('ingredient').value='unmapped';h.$('quantity').value='25';h.$('unit').value='g';h.$('expires').value='';h.$('add').onsubmit({preventDefault(){}});}}
function scannerHarness(tab){
 const source=fs.readFileSync(new URL('public/production-scanner/shelf-scanner.js',root),'utf8'),ast=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body,elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};let requests=0;
 const query=createPublicLookup({selection:handoff.PUBLIC_PRODUCT_SELECTION,fetchImpl:async url=>{requests++;const q=new URL(url,'https://generated.invalid').searchParams;assert.equal(q.get('manifestSha256'),handoff.PUBLIC_PRODUCT_SELECTION.manifestSha256);const raw=q.get('barcode');return Response.json({releaseId:handoff.PUBLIC_PRODUCT_SELECTION.releaseId,manifestSha256:handoff.PUBLIC_PRODUCT_SELECTION.manifestSha256,records:[{id:'offmenu:generated:'+raw,kind:'product',provenance:{sourceId:'off',visibility:'public',license:'Generated declaration',attribution:'Generated source',url:null,sourceDate:null},data:{name:'Generated '+raw,pack:'500 g source package is not stock',identifiers:[{system:'barcode',value:raw}]}}],nextCursor:null});}});
 const ctx={...handoff,$,crypto,document:{createElement:()=>new Element(),documentElement:{dataset:{theme:'light'}}},window:{},navigator:{onLine:true},innerWidth:900,performance,
  active:true,paused:false,finished:false,processed:new Set(),generation:0,queue:[],current:null,selected:null,mode:'Explore',sheetTouched:false,streaming:false,sound:false,audio:null,
  productVisual:{show(){}},projectedField:()=>null,projectedValue:()=>null,humanValue:String,renderConsumerSummary(){},renderData(){},setSheetSnap(){},cancelPendingSpeech(){},readTone:()=>false,showReadCue(){},scanner:{start(){},stop(){},noteAccepted(){}},sessionStorage:tab,location:{assign(value){ctx.destination=value;}},lookupIdentifiers:query};
 const names=['el','btn','message','open','close','displayValue','selectedQueueRecord','render','capture','showMatches','renderQueue'];const ids=['manual-namespace','manual','manual-open','pause','undo','finish'];
 const selected=ast.filter(n=>n.type==='FunctionDeclaration'&&names.includes(n.id.name)||n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='CAPTURE_FORMATS')||n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.object.type==='CallExpression'&&ids.includes(n.expression.left.object.arguments[0]?.value));
 vm.createContext(ctx);vm.runInContext(selected.map(n=>source.slice(n.start,n.end)).join('\n'),ctx);
 return {ctx,$,requests:()=>requests,async manual(raw){$('manual-open').onclick();$('barcode').value=raw;$('manual-namespace').value='barcode';$('manual-representation').value='';$('manual').onsubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));}};
}
test('actual manual, bounded lookup, List, Undo and scanner Finish bridge to reviewed persisted inventory and cold reload',async t=>{
 const {store,tab}=fixture(t),s=scannerHarness(tab);await s.manual('0000000013131');const first=s.ctx.selected;await s.manual('0000000013132');s.$('pause').onclick();s.$('queue-list').children[0].children[2].onclick();assert.equal(s.ctx.selected,first);s.$('undo').onclick();assert.equal(s.ctx.selected,first);await s.manual('0000000013133');s.$('finish').onclick();assert.equal(s.ctx.destination,'/kitchen.html?scan=staged');assert.equal(s.requests(),3);
 const pending=tab.getItem(handoff.SCANNER_HANDOFF_KEY),batch=JSON.parse(pending);assert.deepEqual(batch.items.map(i=>i.barcode),['0000000013131','0000000013133']);
 const h=harness(store,tab);h.ctx.pendingScannerImport=h.ctx.readScannerImport();h.ctx.startCheckout();assert.equal(store.getItem(h.ctx.KEY),null);assert.ok(h.ctx.session.items.every(i=>i.amountBasis==='package'));h.$('confirm-finish').onclick();assert.equal(store.getItem(h.ctx.KEY),null);review(h);h.$('confirm-finish').onclick();
 const cold=harness(new DiskStorage(store.file),new DiskStorage(tab.file),{restore:true});assert.equal(cold.ctx.lots.length,2);assert.ok(cold.ctx.lots.every(i=>i.quantity===25&&i.unit==='g'&&i.needsReview));assert.deepEqual(Array.from(cold.ctx.lots,i=>i.id),batch.items.map(i=>i.operationId));
 tab.setItem(handoff.SCANNER_HANDOFF_KEY,pending);cold.ctx.pendingScannerImport=cold.ctx.readScannerImport();cold.ctx.startCheckout();assert.equal(cold.ctx.session,null);assert.equal(JSON.parse(store.getItem(cold.ctx.KEY)).length,2);
});
test('actual receiver, Correct and finish callbacks persist only after review, reload durably and deduplicate handoff retry',t=>{
 const {store,tab}=fixture(t),h=harness(store,tab);stage(h,tab);assert.equal(h.ctx.session.items.length,2);assert.equal(store.getItem(h.ctx.KEY),null);
 h.$('confirm-finish').onclick();assert.equal(store.getItem(h.ctx.KEY),null);assert.match(h.$('finish-explanation').textContent,/quantity|review/i);
 review(h);h.$('confirm-finish').onclick();assert.equal(h.ctx.session,null);const persisted=JSON.parse(store.getItem(h.ctx.KEY));assert.equal(persisted.length,2);assert.ok(persisted.every(i=>i.quantity===25&&i.unit==='g'&&i.needsReview));assert.equal(store.getItem('foreign-space'),null);
 const next=harness(new DiskStorage(store.file),new DiskStorage(tab.file),{restore:true});assert.equal(next.ctx.lots.length,2);assert.equal(next.ctx.lots[0].publicProductReference.schema,handoff.PUBLIC_PRODUCT_REFERENCE);stage(next,tab);assert.equal(next.ctx.session,null);assert.equal(JSON.parse(store.getItem(next.ctx.KEY)).length,2);
 const conflict={schema:handoff.PUBLIC_SCANNER_HANDOFF,items:[{...inputs[0],name:'Conflicting replay'}]};tab.setItem(handoff.SCANNER_HANDOFF_KEY,JSON.stringify(conflict));next.ctx.pendingScannerImport=next.ctx.readScannerImport();next.ctx.startCheckout();assert.match(next.ctx.message,/conflict/i);assert.equal(JSON.parse(store.getItem(next.ctx.KEY)).length,2);
});
test('inventory write followed by receipt failure can reload and retry exactly once; conflicting stock retry is rejected',t=>{
 const {store,tab}=fixture(t),h=harness(store,tab);stage(h,tab);review(h);let fail=true;store.fail=(k,v)=>k==='generated-profile-A'&&JSON.parse(v).lastReceipt&&fail;
 h.$('confirm-finish').onclick();assert.equal(JSON.parse(store.getItem(h.ctx.KEY)).length,2);assert.ok(h.ctx.session);fail=false;
 const next=harness(new DiskStorage(store.file),new DiskStorage(tab.file),{restore:true});next.$('confirm-finish').onclick();assert.equal(next.ctx.session,null);assert.equal(JSON.parse(store.getItem(next.ctx.KEY)).length,2);
 const receipt=next.ctx.profile.lastReceipt,existing=next.ctx.lots;assert.deepEqual(finishInventory(existing,receipt),existing);
 assert.throws(()=>finishInventory(existing,{...receipt,items:receipt.items.map((i,n)=>n?i:{...i,quantity:26})}),/conflict/i);
 assert.throws(()=>finishInventory(existing.slice(1),receipt),/conflict/i);
});
test('current receiver namespace and write guard dominate payload; account or scope change blocks inventory commit',t=>{
 const {store,tab}=fixture(t),h=harness(store,tab,{writable:false});stage(h,tab);assert.equal(h.ctx.session,null);assert.equal(store.getItem(h.ctx.KEY),null);h.setWritable(true);h.ctx.startCheckout();review(h);
 const before=fs.readFileSync(store.file,'utf8');h.ctx.KEY='generated-other-space';h.$('confirm-finish').onclick();assert.equal(fs.readFileSync(store.file,'utf8'),before);h.ctx.KEY='generated-pantry-A';h.ctx.requestIdentity={owner:'generated-changed-owner'};h.$('confirm-finish').onclick();assert.equal(fs.readFileSync(store.file,'utf8'),before);
 h.ctx.editingId=h.ctx.session.items[0].id;h.$('add').onsubmit({preventDefault(){}});assert.equal(fs.readFileSync(store.file,'utf8'),before);assert.match(h.ctx.message,/space/i);
});
test('distinct published reference does not masquerade as private observation and wrong release is rejected',()=>{
 assert.equal(validSourceObservationReference(inputs[0].publicProductReference,inputs[0].barcode),false);
 assert.throws(()=>handoff.parsePublicScannerHandoff({schema:handoff.PUBLIC_SCANNER_HANDOFF,items:[{...inputs[0],publicProductReference:{...inputs[0].publicProductReference,manifestSha256:'0'.repeat(64)}}]}));
});
test('partial draft storage failure rolls back only the unsaved operation and a retry stages exactly two items',t=>{
 const {store,tab}=fixture(t),h=harness(store,tab);let fail=true;store.fail=(key,value)=>key.endsWith('-checkout')&&JSON.parse(value).items?.length===2&&fail;stage(h,tab);assert.equal(h.ctx.session.items.length,1);assert.equal(JSON.parse(store.getItem(h.ctx.KEY+'-checkout')).items.length,1);assert.ok(h.ctx.pendingScannerImport);
 fail=false;h.ctx.startCheckout();assert.equal(h.ctx.session.items.length,2);assert.equal(new Set(h.ctx.session.items.map(i=>i.id)).size,2);assert.equal(h.ctx.pendingScannerImport,null);review(h);h.$('confirm-finish').onclick();assert.equal(JSON.parse(store.getItem(h.ctx.KEY)).length,2);
});
