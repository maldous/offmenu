import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {validateLot,validSourceObservationReference} from '../../apps/web/src/model.js';
import {finishInventory,makeAutoLot,locationKey} from '../../apps/web/src/checkout-model.js';
import {reconcileCookedStock} from '../../apps/web/src/cooking-model.js';
import {t,setLocalizedText,getLanguage} from '../../apps/web/src/i18n.js';
import * as handoff from '../../apps/web/src/scanner-kitchen-handoff.js';
import {createPublicLookup,mergeIdentifierPages} from '../../apps/web/src/production-scanner/scanner-production-lookup.js';
const {parse}=createRequire(import.meta.url)('acorn');
const root=new URL('../..',import.meta.url),app=fs.readFileSync(new URL('apps/web/src/app.js',root),'utf8'),nodes=parse(app,{ecmaVersion:'latest',sourceType:'module'}).body;
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
 const source=fs.readFileSync(new URL('apps/web/src/production-scanner/shelf-scanner.js',root),'utf8'),ast=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body,elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};let requests=0;
 const query=createPublicLookup({selection:handoff.PUBLIC_PRODUCT_SELECTION,fetchImpl:async url=>{requests++;const q=new URL(url,'https://generated.invalid').searchParams;assert.equal(q.get('manifestSha256'),handoff.PUBLIC_PRODUCT_SELECTION.manifestSha256);const raw=q.get('barcode');return Response.json({releaseId:handoff.PUBLIC_PRODUCT_SELECTION.releaseId,manifestSha256:handoff.PUBLIC_PRODUCT_SELECTION.manifestSha256,records:[{id:'offmenu:generated:'+raw,kind:'product',provenance:{sourceId:'off',visibility:'public',license:'Generated declaration',attribution:'Generated source',url:null,sourceDate:null},data:{name:'Generated '+raw,pack:'500 g source package is not stock',identifiers:[{system:'barcode',value:raw}]}}],nextCursor:null});}});
 const ctx={...handoff,$,crypto,document:{createElement:()=>new Element(),documentElement:{dataset:{theme:'light'}}},window:{},navigator:{onLine:true},innerWidth:900,performance,
  active:true,paused:false,finished:false,processed:new Set(),generation:0,queue:[],current:null,selected:null,mode:'Explore',sheetTouched:false,streaming:false,sound:false,audio:null,
  productVisual:{show(){}},projectedField:()=>null,projectedValue:()=>null,humanValue:String,renderConsumerSummary(){},renderData(){},setSheetSnap(){},cancelPendingSpeech(){},readTone:()=>false,showReadCue(){},scanner:{start(){},stop(){},noteAccepted(){}},sessionStorage:tab,location:{assign(value){ctx.destination=value;}},lookupIdentifiers:query};
 const names=['el','btn','message','open','close','displayValue','selectedQueueRecord','render','capture','showMatches','renderQueue'];const ids=['manual-namespace','manual','manual-open','pause','undo','finish'];
 const selected=ast.filter(n=>n.type==='FunctionDeclaration'&&names.includes(n.id.name)||n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='CAPTURE_FORMATS')||n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.object.type==='CallExpression'&&ids.includes(n.expression.left.object.arguments[0]?.value));
 vm.createContext(ctx);vm.runInContext(selected.map(n=>source.slice(n.start,n.end)).join('\n'),ctx);
 return {ctx,$,requests:()=>requests,async manual(raw){$('manual-open').onclick();$('barcode').value=raw;$('manual-namespace').value='barcode';$('manual-representation').value='';$('manual').onsubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));}};
}

for(const [raw,hint,matched] of [['080442957X','ISBN-10','9780804429573'],['01234558','UPC-E','012345000058'],['12345678',null,'12345678']]){
 test('actual receiver/makeAutoLot/review/persist/reload/retry '+raw,async t=>{
  const {store,tab}=fixture(t);const query=createPublicLookup({selection:handoff.PUBLIC_PRODUCT_SELECTION,fetchImpl:async url=>{
   const q=new URL(url,'https://generated.invalid').searchParams;assert.match(q.get('barcode'),/^\d{4,32}$/);
   return Response.json({...handoff.PUBLIC_PRODUCT_SELECTION,records:q.get('barcode')===matched?[{id:'offmenu:generated:'+matched,kind:'product',countries:['AU'],provenance:{sourceId:'off',visibility:'public',license:'Generated declaration',attribution:'Generated source',sourceDate:null},data:{name:'Generated product',pack:'500 g is not stock',identifiers:[{system:'barcode',value:matched}]}}]:[],nextCursor:null});
  }});
  let page=await query(raw,1,null,hint);while(page.hasMore)page=mergeIdentifierPages(page,await query(raw,1,page.nextCursor,hint));assert.equal(page.status,'source-match');
  const batch=handoff.createPublicScannerHandoff([{...page,id:uuid(9),raw,selectedRecord:page.matches[0]}]);const pending=JSON.stringify(batch);tab.setItem(handoff.SCANNER_HANDOFF_KEY,pending);
  const h=harness(store,tab);h.ctx.pendingScannerImport=h.ctx.readScannerImport();assert.ok(h.ctx.pendingScannerImport);h.ctx.startCheckout();assert.equal(h.ctx.session.items.length,1);
  assert.equal(h.ctx.session.items[0].barcode,raw);assert.equal(h.ctx.session.items[0].publicProductReference.lexicalValue,matched);assert.equal(h.ctx.session.items[0].id,uuid(9));
  assert.equal(h.ctx.session.items[0].needsReview,true);assert.equal(h.ctx.session.items[0].amountBasis,'package');assert.equal(store.getItem(h.ctx.KEY),null);
  h.$('confirm-finish').onclick();assert.equal(store.getItem(h.ctx.KEY),null);review(h);
  let fail=true;store.fail=(key,value)=>key==='generated-profile-A'&&JSON.parse(value).lastReceipt&&fail;
  h.$('confirm-finish').onclick();assert.ok(h.ctx.session);assert.equal(JSON.parse(store.getItem(h.ctx.KEY)).length,1);fail=false;
  const cold=harness(new DiskStorage(store.file),new DiskStorage(tab.file),{restore:true});cold.$('confirm-finish').onclick();assert.equal(cold.ctx.session,null);
  const persisted=JSON.parse(store.getItem(cold.ctx.KEY));assert.equal(persisted.length,1);assert.equal(persisted[0].barcode,raw);assert.equal(persisted[0].quantity,25);assert.equal(persisted[0].unit,'g');assert.equal(persisted[0].publicProductReference.lexicalValue,matched);
  if(raw!==matched){assert.equal(persisted[0].publicProductReference.capturedLexicalValue,raw);assert.equal(persisted[0].publicProductReference.representationHint,hint);}
  const history=JSON.parse(store.getItem(cold.ctx.draftKey()));assert.ok(history.scannerHandoffOperations.includes(uuid(9)));assert.equal(history.scannerHandoffReceipts[uuid(9)],handoff.publicHandoffFingerprint(batch.items[0]));
  tab.setItem(handoff.SCANNER_HANDOFF_KEY,pending);cold.ctx.pendingScannerImport=cold.ctx.readScannerImport();cold.ctx.startCheckout();assert.equal(cold.ctx.session,null);assert.equal(JSON.parse(store.getItem(cold.ctx.KEY)).length,1);
  tab.setItem(handoff.SCANNER_HANDOFF_KEY,JSON.stringify({...batch,items:[{...batch.items[0],name:'Conflicting retry'}]}));cold.ctx.pendingScannerImport=cold.ctx.readScannerImport();cold.ctx.startCheckout();assert.match(cold.ctx.message,/conflict/i);assert.equal(JSON.parse(store.getItem(cold.ctx.KEY)).length,1);
 });
}
test('constructor never grants standalone X or an unqualified alias reference',()=>{
 assert.throws(()=>makeAutoLot('080442957X',{name:'Generated'}));
 assert.throws(()=>makeAutoLot('080442957X',{name:'Generated',publicProductReference:{lexicalValue:'9780804429573',capturedLexicalValue:'080442957X',representationHint:'ISBN-10'}}));
});
