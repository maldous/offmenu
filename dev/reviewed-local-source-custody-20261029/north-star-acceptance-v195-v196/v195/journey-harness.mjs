import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const source=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');
assert.equal(Buffer.byteLength(source),464652);
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),'fce748582a1e4aa940022b00ccaab7ac00ec5d1ca5d357d5f45f4ff0756e1fdf');
const elements=new Map(),events=[],blockedRequests=[],memory=new Map();
class Element {
 constructor(tag='div',id=''){this.tagName=tag.toUpperCase();this.id=id;this.children=[];this.dataset={};this.style={};this.attributes={};this.value='';this.checked=false;this.hidden=false;this.disabled=false;this.open=false;this._text='';this.listeners={};this.classList={add(){},remove(){},toggle(){},contains(){return false;}};}
 set textContent(x){this._text=String(x??'');this.children=[];}
 get textContent(){return this._text+this.children.map(x=>x.textContent??String(x)).join('');}
 set innerHTML(x){this._text=String(x);this.children=[];}
 get innerHTML(){return this._text;}
 get options(){return this.children.filter(x=>x.tagName==='OPTION');}
 append(...x){for(const n of x){if(n&&typeof n==='object')n.parentElement=this;this.children.push(n);}}
 appendChild(x){this.append(x);return x;}
 replaceChildren(...x){this._text='';this.children=[];this.append(...x);}
 addEventListener(type,fn){(this.listeners[type]??=[]).push(fn);}
 removeEventListener(){}
 setAttribute(k,v){this.attributes[k]=String(v);}
 getAttribute(k){return this.attributes[k]??null;}
 hasAttribute(k){return Object.hasOwn(this.attributes,k);}
 removeAttribute(k){delete this.attributes[k];}
 closest(s){return s==='button'&&this.tagName==='BUTTON'?this:this.parentElement??this;}
 querySelector(){return new Element();}
 querySelectorAll(){return [];}
 showModal(){this.open=true;}
 close(){this.open=false;for(const fn of this.listeners.close??[])fn({target:this});}
 reset(){}
 focus(){}
 remove(){}
 before(){}
 after(){}
 insertBefore(n){this.append(n);return n;}
 insertAdjacentElement(_where,n){this.append(n);return n;}
 scrollIntoView(){}
 getBoundingClientRect(){return {width:800,height:600,left:0,top:0,right:800,bottom:600};}
 getContext(){return {drawImage(){},getImageData(){return {data:new Uint8ClampedArray(4),width:1,height:1};}};}
 cloneNode(){return new Element(this.tagName);}
 click(){if(this.disabled)return;const e={target:this,preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}};this.onclick?.(e);}
}
const el=id=>{if(!elements.has(id))elements.set(id,new Element('div',id));return elements.get(id);};
const document={getElementById:el,createElement:t=>new Element(t),createTextNode:t=>({textContent:String(t)}),querySelector:s=>s.startsWith('#')?el(s.slice(1)):new Element(),querySelectorAll:()=>[],addEventListener:(t,fn)=>events.push({t,fn}),documentElement:new Element('html'),body:new Element('body'),head:new Element('head'),cookie:'',visibilityState:'visible'};
const storage={getItem:k=>memory.get(k)??null,setItem:(k,v)=>memory.set(k,String(v)),removeItem:k=>memory.delete(k),key:i=>[...memory.keys()][i]??null,get length(){return memory.size;}};
const location=new URL('http://127.0.0.1:7645/kitchen.html?fixture=lifecycle31&run=independent-v195-journey-20261028');
location.assign=()=>{throw Error('Navigation is outside this isolated harness');};location.reload=()=>{};
const navigator={language:'en',languages:['en'],onLine:false,userAgent:'isolated synthetic v195 caller harness'};
class FixtureDate extends Date{constructor(...a){super(...(a.length?a:['2026-10-28T12:00:00Z']));}static now(){return Date.parse('2026-10-28T12:00:00Z');}}
const sandbox={document,localStorage:storage,sessionStorage:{...storage},location,navigator,console,Date:FixtureDate,URL,URLSearchParams,TextEncoder,TextDecoder,Uint8Array,Uint8ClampedArray,AbortController,AbortSignal,Blob,structuredClone,crypto:crypto.webcrypto,atob,btoa,performance,setTimeout:()=>0,clearTimeout(){},setInterval:()=>0,clearInterval(){},requestAnimationFrame:()=>0,cancelAnimationFrame(){},fetch:async(url)=>{blockedRequests.push(String(url));throw Error('NETWORK_BLOCKED_IN_ISOLATED_ACCEPTANCE');},confirm:()=>false,alert(){},history:{replaceState(){},pushState(){}},matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}}),addEventListener(){},removeEventListener(){},innerWidth:1024,innerHeight:768,scrollTo(){}};
sandbox.window=sandbox;sandbox.self=sandbox;
const context=vm.createContext(sandbox);
const instrument='\nglobalThis.__journey={snapshot:()=>structuredClone({profile:W,inventory:Ae,products:Re,recipes:Ie,draft:Z}),replace:(s)=>{W=s.profile;Ae=s.inventory;Re=s.products;Ie=s.recipes;},persistInputs:()=>{ae.setItem(Mt,JSON.stringify(Re));xt();},cook:cn,insights:au,canWrite:()=>Ye.canWrite(),render:()=>{Le();cn.renderBatches();},manualScan:()=>Dl(),reload:()=>Zp(),historySummary:(dates,member)=>Fn(W.history||[],dates,member)};';
try{
 await vm.runInContext('(async()=>{'+source+instrument+'})()',context,{timeout:20000});
 const app=context.__journey,records=[];
 const snapshot=label=>{const s=app.snapshot();records.push({label,state:s});return s;};
 const submit=id=>{assert.equal(typeof el(id).onsubmit,'function',id);el(id).onsubmit({preventDefault(){}});};
 const descendants=e=>[e,...e.children.flatMap(x=>x instanceof Element?descendants(x):[])];
 const button=(root,text)=>{const b=descendants(el(root)).find(x=>x.tagName==='BUTTON'&&x.textContent===text);assert.ok(b,`${root}: ${text}`);return b;};
 assert.equal(app.canWrite(),true);
 let initial=app.snapshot();initial.profile={...initial.profile,country:'AU',units:'metric',servings:2,members:[{id:'person-a',name:'Synthetic A',portion:1,advisors:['balanced'],avoid:[],restrictions:[]},{id:'person-b',name:'Synthetic B',portion:1,advisors:['balanced'],avoid:[],restrictions:[]}],plan:[],history:[],batches:[],shopping:[]};app.replace(initial);
 el('servings').value='2';el('plan-date').value='2026-10-28';el('plan-slot').value='Dinner';el('use-pantry').checked=true;el('history-range').value='7';
 for(const ingredient of ['rice','peas']){
  el('quick-add').click();for(const [k,v]of Object.entries({'food-name':`Synthetic ${ingredient}`,'food-ingredient':ingredient,'food-quantity':'500','food-unit':'g','food-date':'','food-date-type':'use-by','food-location':JSON.stringify({area:'Pantry',shelf:'Fixture shelf'})}))el(k).value=v;
  submit('food-form');assert.equal(el('food-dialog').open,false,el('food-notice').textContent);
 }
 let seeded=app.snapshot();assert.equal(seeded.inventory.length,2);
 for(const lot of seeded.inventory)seeded.products[lot.barcode]={name:lot.name,nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':lot.ingredient==='rice'?100:50,salt_100g:0},nutritionProvenance:{sourceId:`synthetic-${lot.ingredient}`,sourceDate:'2026-fixture',attribution:'Non-sensitive synthetic acceptance values, not real food nutrition',nutrientProfile:{id:`synthetic-profile-${lot.ingredient}-v1`,basis:{amount:100,unit:'g'},status:'synthetic'}}};
 app.replace(seeded);app.persistInputs();app.render();snapshot('01-pantry-manual-entry');
 const card=el('meals').children.find(x=>x.textContent.includes('Rice and peas (synthetic)'));assert.ok(card);
 const nutrientText=descendants(card).find(x=>x.className==='recipe-food-data')?.textContent;assert.match(nutrientText,/Energy: 150 kcal/);assert.match(nutrientText,/Salt: 0 g/);assert.match(nutrientText,/Vitamin C: not available/);
 descendants(card).find(x=>x.tagName==='BUTTON'&&x.textContent.startsWith('Add to ')).click();assert.equal(app.snapshot().profile.plan.length,1);snapshot('02-quantified-menu-planned');
 button('week-menu','Cook this meal').click();el('cook-confirm').click();let cooked=snapshot('03-plan-cooked');assert.equal(cooked.profile.batches.length,1,el('cook-notice').textContent);assert.equal(cooked.profile.batches[0].remaining,2);assert.equal(cooked.profile.batches[0].totals['energy-kcal_100g'].value,150);assert.equal(cooked.profile.batches[0].totals.salt_100g.known,2);assert.equal(cooked.profile.batches[0].totals['vitamin-c_100g'].known,0);
 const rawAmounts=s=>s.inventory.filter(x=>!x.cookBatchId).map(x=>[x.id,x.quantity]);const deducted=rawAmounts(cooked);assert.deepEqual(deducted.map(x=>x[1]),[400,400]);
 for(const [label,member,portions,completion,remainder,date,remaining]of [['04-A-half-eaten-saved','person-a','1','50','saved','2026-10-28',1.5],['05-B-fully-eaten','person-b','1','100','unspecified','2026-10-28',.5],['06-next-day-leftover-eaten','person-a','.5','100','unspecified','2026-10-29',0]]){
  button('week-menu','Serve / after meal').click();for(const [k,v]of Object.entries({'serve-member':member,'serve-portions':portions,'serve-completion':completion,'serve-remainder':remainder,'serve-date':date}))el(k).value=v;
  submit('serve-form');const s=snapshot(label);assert.equal(s.profile.batches[0].remaining,remaining,el('serve-notice').textContent);assert.deepEqual(rawAmounts(s),deducted);assert.equal(s.profile.history.at(-1).memberId,member);
 }
 let consumed=app.snapshot();assert.equal(consumed.profile.history.length,3);assert.equal(consumed.inventory.some(x=>x.cookBatchId),false);assert.equal(consumed.profile.history.reduce((n,x)=>n+x.totals['energy-kcal_100g'].value,0),150);
 assert.equal(app.historySummary(['2026-10-28','2026-10-29'],'person-a').totals['energy-kcal_100g'].value,75);assert.equal(app.historySummary(['2026-10-28','2026-10-29'],'person-b').totals['energy-kcal_100g'].value,75);
 el('history-end').value='2026-10-29';el('history-member').value='all';app.insights.render();assert.match(el('food-history').textContent,/Synthetic A/);assert.match(el('food-history').textContent,/Synthetic B/);snapshot('07-person-specific-history-rendered');
 const beforeCorrection=JSON.stringify(consumed.profile.history);for(const product of Object.values(consumed.products))product.nutriments['energy-kcal_100g']=9999;app.replace(consumed);app.persistInputs();assert.equal(JSON.stringify(app.snapshot().profile.history),beforeCorrection);
 el('servings').value='12';el('plan-date').value='2026-10-29';app.render();const secondCard=el('meals').children.find(x=>x.textContent.includes('Rice and peas (synthetic)'));descendants(secondCard).find(x=>x.tagName==='BUTTON'&&x.textContent.startsWith('Add to ')).click();app.insights.renderShopping();assert.match(el('shopping-checklist').textContent,/200 g/);
 const beforeShopping=app.snapshot();for(const x of descendants(el('shopping-checklist')).filter(x=>x.tagName==='INPUT')){x.checked=true;x.onchange?.();}
 let checked=snapshot('08-future-plan-shopping-checked-not-stock');assert.deepEqual(checked.inventory,beforeShopping.inventory);assert.deepEqual(checked.profile.history,beforeShopping.profile.history);
 checked.products['9900000000001']={name:'Synthetic received rice',ingredient:'rice',product_quantity:200,product_quantity_unit:'g',quantity:'200 g',nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':100,salt_100g:0}};app.replace(checked);app.persistInputs();
 el('mode-shopping').click();el('storage-area').value='Pantry';el('shelf-name').value='Fixture shelf';el('start-checkout').click();el('barcode').value='9900000000001';await app.manualScan();const drafted=snapshot('09-cached-synthetic-barcode-receipt-draft');assert.equal(drafted.draft.items.length,1);assert.deepEqual(drafted.inventory,checked.inventory);
 el('finish-checkout').click();const preview=snapshot('10-receipt-preview-not-stock');assert.deepEqual(preview.inventory,checked.inventory);assert.equal(el('finish-dialog').open,true);
 el('confirm-finish').click();const confirmed=snapshot('11-explicit-receipt-confirmed-stock');assert.equal(confirmed.inventory.length,checked.inventory.length+1,el('finish-explanation').textContent);assert.equal(confirmed.inventory.filter(x=>x.ingredient==='rice').reduce((n,x)=>n+x.quantity,0),600);assert.deepEqual(confirmed.profile.history,checked.profile.history);assert.ok(confirmed.profile.lastReceipt);
 await app.reload();const restored=snapshot('12-local-reload');
 // pending is a transient checkout marker intentionally removed by inventory normalization.
 const durableLots=s=>s.inventory.map(({pending,...lot})=>lot);
 assert.deepEqual(durableLots(restored),durableLots(confirmed));assert.deepEqual(restored.profile.history,confirmed.profile.history);
 const result={status:'executed',release:{version:'8db6b5c4-2e5f-483f-90ea-de0260733526',bytes:Buffer.byteLength(source),sha256:crypto.createHash('sha256').update(source).digest('hex')},journey:'Actual served bundled app boot plus real manual-food/menu/plan/cook/serve/history/shopping/checkout handlers in isolated synthetic fixture mode',nutrientText,records,blockedRequests,storageKeys:[...memory.keys()],limitations:['DOM is a minimal in-memory event/element shim, not browser layout/device or authenticated acceptance.','No account, browser session store, external provider or dataset inspected. Fetch stub denies every runtime request; /api/services attempts are recorded.','Synthetic source-labelled nutrition is not real source qualification or clinical validity.','Receipt item supplied by cached synthetic barcode through actual manual-scan controller; no physical scan or retailer order executed.']};
 fs.writeFileSync(new URL('./EXECUTED-JOURNEY.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify({status:result.status,checkpointCount:records.length,servedHash:result.release.sha256,historyRecords:restored.profile.history.length,totalConsumedKcal:150,finalRawRiceGrams:600,blockedRequests,receiptConfirmed:true,localReload:true}));
}catch(error){console.error(error.stack);process.exitCode=1;}
