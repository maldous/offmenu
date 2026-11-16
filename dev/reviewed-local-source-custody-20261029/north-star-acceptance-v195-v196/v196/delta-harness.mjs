import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const source=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');
assert.equal(Buffer.byteLength(source),468574);
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),'e510c7a4cc6f418cbda6d984e0ff7de90f0d7b85d350640b9f624fd9b818c057');
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
const location=new URL('http://127.0.0.1:7645/kitchen.html?fixture=lifecycle31&run=independent-v196-nutrition-20261028');
location.assign=()=>{throw Error('Navigation is outside this isolated harness');};location.reload=()=>{};
const navigator={language:'en',languages:['en'],onLine:false,userAgent:'isolated synthetic v195 caller harness'};
class FixtureDate extends Date{constructor(...a){super(...(a.length?a:['2026-10-28T12:00:00Z']));}static now(){return Date.parse('2026-10-28T12:00:00Z');}}
const sandbox={document,localStorage:storage,sessionStorage:{...storage},location,navigator,console,Date:FixtureDate,URL,URLSearchParams,TextEncoder,TextDecoder,Uint8Array,Uint8ClampedArray,AbortController,AbortSignal,Blob,structuredClone,crypto:crypto.webcrypto,atob,btoa,performance,setTimeout:()=>0,clearTimeout(){},setInterval:()=>0,clearInterval(){},requestAnimationFrame:()=>0,cancelAnimationFrame(){},fetch:async(url)=>{blockedRequests.push(String(url));throw Error('NETWORK_BLOCKED_IN_ISOLATED_ACCEPTANCE');},confirm:()=>false,alert(){},history:{replaceState(){},pushState(){}},matchMedia:()=>({matches:false,addEventListener(){},removeEventListener(){}}),addEventListener(){},removeEventListener(){},innerWidth:1024,innerHeight:768,scrollTo(){}};
sandbox.window=sandbox;sandbox.self=sandbox;
const context=vm.createContext(sandbox);
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url),acorn=require('/home/user/src/offmenu/node_modules/acorn');
const ast=acorn.parse(source,{ecmaVersion:'latest',sourceType:'module'}),callbacks=[];
function walk(n){if(!n||typeof n!=='object')return;if(n.type==='Property'&&n.key?.name==='applyNutrition'&&n.value?.type==='ArrowFunctionExpression')callbacks.push(n.value);for(const [k,v]of Object.entries(n))if(k!=='parent'&&v&&typeof v==='object'){if(Array.isArray(v))v.forEach(walk);else walk(v);}}
walk(ast);assert.equal(callbacks.length,1);const cb=callbacks[0],callbackSource=source.slice(cb.start,cb.end);
const instrument='\nconst exactApply='+callbackSource+';globalThis.__delta={snapshot:()=>structuredClone({profile:W,inventory:Ee,products:De,recipes:Ce}),replace:s=>{W=s.profile;Ee=s.inventory;De=s.products;Ce=s.recipes;},render:()=>_e(),persist:()=>{ae.setItem(Yt,JSON.stringify(De));Nt();},reload:()=>uf(),apply:(id,p)=>{const lot=Ee.find(x=>x.id===id);return exactApply(lot,p,nr(p,lot.unit));}};';
try{
 await vm.runInContext('(async()=>{'+source+instrument+'})()',context,{timeout:20000});const app=context.__delta,checkpoints=[];
 const snap=label=>{const s=app.snapshot();checkpoints.push({label,state:s});return s;};
 const submit=id=>el(id).onsubmit({preventDefault(){}}),desc=e=>[e,...e.children.flatMap(x=>x instanceof Element?desc(x):[])];
 const button=(root,text)=>{let b=desc(el(root)).find(x=>x.tagName==='BUTTON'&&x.textContent===text);assert.ok(b,root+': '+text);return b;};
 let s=app.snapshot();s.profile={...s.profile,country:'AU',units:'metric',servings:2,members:[{id:'person-a',name:'Synthetic A',portion:1,advisors:['balanced'],avoid:[],restrictions:[]}],plan:[],batches:[],history:[]};app.replace(s);el('servings').value='2';el('plan-date').value='2026-10-28';el('plan-slot').value='Dinner';el('use-pantry').checked=true;
 for(const ingredient of ['rice','peas']){el('quick-add').click();for(const[k,v]of Object.entries({'food-name':'Synthetic '+ingredient,'food-ingredient':ingredient,'food-quantity':'500','food-unit':'g','food-date':'','food-date-type':'use-by','food-location':JSON.stringify({area:'Pantry',shelf:'Fixture shelf'})}))el(k).value=v;submit('food-form');}
 s=app.snapshot();assert.equal(s.inventory.length,2);for(const lot of s.inventory)s.products[lot.barcode]={name:lot.name,nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':lot.ingredient==='rice'?100:50,salt_100g:0}};app.replace(s);app.persist();
 const rice=s.inventory.find(x=>x.ingredient==='rice'),profile={kind:'nutrientProfile',id:'synthetic-private-profile-rice-v1',data:{basis:{amount:100,unit:'g',state:'raw'},nutrients:{energy:{value:200,unit:'kcal'},salt:{value:0,unit:'g'}}},provenance:{sourceId:'personal-import',recordId:'synthetic-rice-record',releaseId:'synthetic-release-v1',license:'Synthetic non-sensitive fixture only',attribution:'Independent acceptance fixture',sourceDate:'2026-10-28',visibility:'private'}};
 app.apply(rice.id,profile);let selected=snap('01-exact-served-applyNutrition-callback');const selectedRice=selected.inventory.find(x=>x.id===rice.id);assert.equal(selectedRice.nutritionSelection.sourceProfile.id,profile.id);assert.equal(selectedRice.nutritionSelection.canonicalIdentityAsserted,false);assert.equal(selected.products[rice.barcode].nutriments['energy-kcal_100g'],100);
 const card=el('meals').children.find(x=>x.textContent.includes('Rice and peas (synthetic)'));assert.ok(card);const nutrition=desc(card).find(x=>x.className==='recipe-food-data').textContent;assert.match(nutrition,/Energy: 250 kcal/);assert.match(nutrition,/Salt: 0 g/);assert.match(nutrition,/Vitamin C: not available/);
 desc(card).find(x=>x.tagName==='BUTTON'&&x.textContent.startsWith('Add to ')).click();button('week-menu','Cook this meal').click();el('cook-confirm').click();let cooked=snap('02-actual-menu-plan-cook-selected-source');const batch=cooked.profile.batches[0];assert.ok(batch,el('cook-notice').textContent);assert.equal(batch.totals['energy-kcal_100g'].value,250);const witness=batch.allocations.find(x=>x.lotId===rice.id).original.nutritionSelection;assert.equal(witness.sourceProfile.id,profile.id);assert.equal(witness.provenance.releaseId,'synthetic-release-v1');
 button('week-menu','Serve / after meal').click();for(const[k,v]of Object.entries({'serve-member':'person-a','serve-portions':'1','serve-completion':'100','serve-remainder':'unspecified','serve-date':'2026-10-28'}))el(k).value=v;submit('serve-form');let served=snap('03-actual-serving-history-batch-link');assert.equal(served.profile.history[0].totals['energy-kcal_100g'].value,125);assert.equal(served.profile.history[0].batchId,batch.id);
 const newProfile=structuredClone(profile);newProfile.id='synthetic-private-profile-rice-v2';newProfile.data.nutrients.energy.value=900;newProfile.provenance.releaseId='synthetic-release-v2';app.apply(rice.id,newProfile);await app.reload();let restored=snap('04-reselection-and-local-reload');const oldBatch=restored.profile.batches.find(x=>x.id===batch.id),oldWitness=oldBatch.allocations.find(x=>x.lotId===rice.id).original.nutritionSelection;assert.equal(restored.inventory.find(x=>x.id===rice.id).nutritionSelection.sourceProfile.id,newProfile.id);assert.equal(oldWitness.sourceProfile.id,profile.id);assert.equal(oldWitness.provenance.releaseId,'synthetic-release-v1');assert.equal(oldBatch.totals['energy-kcal_100g'].value,250);assert.equal(restored.profile.history[0].totals['energy-kcal_100g'].value,125);assert.equal(restored.profile.history[0].batchId,oldBatch.id);
 const result={status:'executed-changed-integration-only',release:{version:'abead872-5f5e-48f8-96f8-7cb96446fbbe',sha256:crypto.createHash('sha256').update(source).digest('hex'),bytes:Buffer.byteLength(source)},callback:{symbol:'applyNutrition production callback',startCharacter:cb.start,endCharacter:cb.end,sha256:crypto.createHash('sha256').update(callbackSource).digest('hex')},checkpoints,nutritionText:nutrition,blockedRequests,findingUpdate:{id:'NS195-G1',v196SelectedLotPath:'Original nutrient profile and source release are now retained indirectly: history.batchId -> profile.batches[id].allocations[].original.nutritionSelection. Re-selecting v2 on current lot leaves frozen v1 witness and totals intact after reload.',remaining:'Legacy product-cache-only path is not retroactively provided a source-profile witness. Recipe version/source snapshot is still not explicitly frozen in cooking batch. No complete real-source, device, account/privacy or full-loop acceptance inferred.'},limitations:['Minimal DOM/storage shim; actual picker UI is fixture-disabled, so exact extracted production applyNutrition callback receives explicitly confirmed non-sensitive normalized fixture, then real menu/cook/serve handlers execute.','No prior full journey or four isolated regressions rerun. One changed production callback-to-meal/history/local-reload integration case only.','No private data/session/device/provider or external food lookup accessed; all runtime fetches blocked.']};
 fs.writeFileSync(new URL('./EXECUTED-DELTA.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,release:result.release,checkpointCount:checkpoints.length,batchEnergy:250,servingEnergy:125,v1WitnessSurvivesV2Reselection:true,recipeVersionWitness:'not-explicitly-frozen',blockedRequests}));
}catch(e){console.error(e.stack);process.exitCode=1;}
