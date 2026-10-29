import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const source=fs.readFileSync(new URL('./app.js',import.meta.url),'utf8');
assert.equal(Buffer.byteLength(source),476307);
assert.equal(crypto.createHash('sha256').update(source).digest('hex'),'19c11668db13b88a4c77ddd565dbf7853928b9c0c22cebe1da87fa3742cdb7a5');
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
const location=new URL('http://127.0.0.1:7645/kitchen.html?fixture=lifecycle31&run=independent-v198-witness-20261028');
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
const instrument='\nconst exactApply='+callbackSource+';globalThis.__delta={snapshot:()=>structuredClone({profile:Y,inventory:Ee,products:De,recipes:Ce}),replace:s=>{Y=s.profile;Ee=s.inventory;De=s.products;Ce=s.recipes;},render:()=>_e(),persist:()=>{ae.setItem(Zt,JSON.stringify(De));ae.setItem(kt,JSON.stringify(Ce));Ot();},reload:()=>_f(),apply:(id,p)=>{const lot=Ee.find(x=>x.id===id);return exactApply(lot,p,ur(p,lot.unit));},shared:_i,copy:rn};';

try{
 await vm.runInContext('(async()=>{'+source+instrument+'})()',context,{timeout:20000});const app=context.__delta,checkpoints=[];
 const snap=label=>{const s=app.snapshot();checkpoints.push({label,state:s});return s;};
 const submit=id=>el(id).onsubmit({preventDefault(){}}),desc=e=>[e,...e.children.flatMap(x=>x instanceof Element?desc(x):[])];
 const button=(root,text)=>{let b=desc(el(root)).find(x=>x.tagName==='BUTTON'&&x.textContent===text);assert.ok(b,root+': '+text);return b;};
 let s=app.snapshot();s.profile={...s.profile,country:'AU',units:'metric',servings:2,members:[{id:'person-a',name:'Synthetic A',portion:1,advisors:['balanced'],avoid:[],restrictions:[]}],plan:[],batches:[],history:[]};app.replace(s);el('servings').value='2';el('plan-date').value='2026-10-28';el('plan-slot').value='Dinner';el('use-pantry').checked=true;
 for(const ingredient of ['rice','peas']){el('quick-add').click();for(const[k,v]of Object.entries({'food-name':'Synthetic '+ingredient,'food-ingredient':ingredient,'food-quantity':'500','food-unit':'g','food-date':'','food-date-type':'use-by','food-location':JSON.stringify({area:'Pantry',shelf:'Fixture shelf'})}))el(k).value=v;submit('food-form');}
 s=app.snapshot();assert.equal(s.inventory.length,2);for(const lot of s.inventory)s.products[lot.barcode]={name:lot.name,nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':lot.ingredient==='rice'?100:50,salt_100g:0}};app.replace(s);app.persist();
 const rice=s.inventory.find(x=>x.ingredient==='rice'),profile={kind:'nutrientProfile',id:'synthetic-private-profile-rice-v1',data:{basis:{amount:100,unit:'g',state:'raw'},nutrients:{energy:{value:200,unit:'kcal'},salt:{value:0,unit:'g'}}},provenance:{sourceId:'personal-import',recordId:'synthetic-rice-record',releaseId:'synthetic-release-v1',license:'Synthetic non-sensitive fixture only',attribution:'Independent acceptance fixture',sourceDate:'2026-10-28',visibility:'private'}};
 const seeded=app.snapshot(), recipe=seeded.recipes.find(x=>x.title.includes('Rice and peas (synthetic)'));assert.ok(recipe);recipe.id='independent-versioned-rice-peas';recipe.version='fixture-recipe-v1';recipe.source='Synthetic recipe source v1';recipe.license='Synthetic fixture license v1';recipe.attribution='Independent acceptance';recipe.instructions=['Measure 100 g rice and 100 g peas.','Cook synthetic recipe v1.'];recipe.provenance={sourceId:'synthetic-recipe-source',recordId:'rice-peas',releaseId:'recipe-release-v1',version:'fixture-recipe-v1',license:recipe.license,attribution:recipe.attribution,visibility:'public',citations:[{id:'public-root',visibility:'public',citations:[{id:'private-nested-evidence',visibility:'private',recordId:'synthetic-private-evidence'}]}]};app.replace(seeded);
 app.apply(rice.id,profile);let selected=snap('01-exact-served-applyNutrition-callback');const selectedRice=selected.inventory.find(x=>x.id===rice.id);assert.equal(selectedRice.nutritionSelection.sourceProfile.id,profile.id);assert.equal(selectedRice.nutritionSelection.canonicalIdentityAsserted,false);assert.equal(selected.products[rice.barcode].nutriments['energy-kcal_100g'],100);
 const card=el('meals').children.find(x=>x.textContent.includes('Rice and peas (synthetic)'));assert.ok(card);const nutrition=desc(card).find(x=>x.className==='recipe-food-data').textContent;assert.match(nutrition,/Energy: 250 kcal/);assert.match(nutrition,/Salt: 0 g/);assert.match(nutrition,/Vitamin C: not available/);
 desc(card).find(x=>x.tagName==='BUTTON'&&x.textContent.startsWith('Add to ')).click();button('week-menu','Cook this meal').click();el('cook-confirm').click();let cooked=snap('02-actual-menu-plan-cook-selected-source');const batch=cooked.profile.batches[0];assert.ok(batch,el('cook-notice').textContent);assert.equal(batch.totals['energy-kcal_100g'].value,250);const witness=batch.allocations.find(x=>x.lotId===rice.id).original.nutritionSelection;assert.equal(witness.sourceProfile.id,profile.id);assert.equal(witness.provenance.releaseId,'synthetic-release-v1');
 button('week-menu','Serve / after meal').click();for(const[k,v]of Object.entries({'serve-member':'person-a','serve-portions':'1','serve-completion':'100','serve-remainder':'unspecified','serve-date':'2026-10-28'}))el(k).value=v;submit('serve-form');let served=snap('03-actual-serving-history-batch-link');assert.equal(served.profile.history[0].totals['energy-kcal_100g'].value,125);assert.equal(served.profile.history[0].batchId,batch.id);
 const frozenWitness=JSON.stringify(served.profile.batches[0].cookingWitness), frozenHistoryWitness=JSON.stringify(served.profile.history[0].cookingWitness);assert.equal(JSON.stringify(batch.cookingWitness),frozenWitness);assert.equal(frozenHistoryWitness,frozenWitness);assert.equal(batch.cookingWitness.recipe.version,'fixture-recipe-v1');assert.equal(batch.cookingWitness.visibility,'private');assert.equal(batch.cookingWitness.recipe.instructions[1],'Cook synthetic recipe v1.');assert.equal(batch.cookingWitness.allocations.find(x=>x.lotId===rice.id).quantity,100);assert.equal(batch.cookingWitness.nutrientInputs.find(x=>x.lotId===rice.id).nutriments.salt_100g,0);assert.equal(Object.hasOwn(batch.cookingWitness.nutrientInputs.find(x=>x.lotId===rice.id).nutriments,'vitamin-c_100g'),false);
 const edited=app.snapshot(),editedRecipe=edited.recipes.find(x=>x.id===batch.recipeId);editedRecipe.version='fixture-recipe-v2';editedRecipe.source='Synthetic recipe source v2';editedRecipe.license='Synthetic fixture license v2';editedRecipe.provenance.releaseId='recipe-release-v2';editedRecipe.provenance.citations=[];editedRecipe.instructions=['Changed instructions v2.'];editedRecipe.ingredients[0].quantity=900;edited.products[rice.barcode].nutriments['energy-kcal_100g']=777;app.replace(edited);app.persist();
 const newProfile=structuredClone(profile);newProfile.id='synthetic-private-profile-rice-v2';newProfile.data.nutrients.energy.value=900;newProfile.provenance.releaseId='synthetic-release-v2';app.apply(rice.id,newProfile);await app.reload();let restored=snap('04-reselection-and-local-reload');const oldBatch=restored.profile.batches.find(x=>x.id===batch.id),oldWitness=oldBatch.allocations.find(x=>x.lotId===rice.id).original.nutritionSelection;assert.equal(restored.inventory.find(x=>x.id===rice.id).nutritionSelection.sourceProfile.id,newProfile.id);assert.equal(oldWitness.sourceProfile.id,profile.id);assert.equal(oldWitness.provenance.releaseId,'synthetic-release-v1');assert.equal(oldBatch.totals['energy-kcal_100g'].value,250);assert.equal(restored.profile.history[0].totals['energy-kcal_100g'].value,125);assert.equal(restored.profile.history[0].batchId,oldBatch.id);

 assert.equal(JSON.stringify(oldBatch.cookingWitness),frozenWitness);assert.equal(JSON.stringify(restored.profile.history[0].cookingWitness),frozenHistoryWitness);assert.equal(oldBatch.allocations.find(x=>x.lotId===rice.id).quantity,100);assert.equal(restored.inventory.find(x=>x.id===rice.id).quantity,400);assert.equal(restored.recipes.find(x=>x.id===batch.recipeId).version,'fixture-recipe-v2');assert.equal(oldBatch.cookingWitness.recipe.provenance.releaseId,'recipe-release-v1');assert.equal(oldBatch.cookingWitness.recipe.license,'Synthetic fixture license v1');assert.equal(oldBatch.cookingWitness.recipe.ingredients[0].quantity,100);
 const codec=await import('./cooking-witness.mjs'),privacyCases=[];
 const publicBatch=structuredClone(oldBatch);function makePublic(v){if(!v||typeof v!=='object')return;for(const[k,x]of Object.entries(v)){if(k==='visibility')v[k]='public';else makePublic(x);}}makePublic(publicBatch.cookingWitness);for(const n of publicBatch.cookingWitness.nutrientInputs)n.provenance.visibility='public';publicBatch.cookingWitness.visibility='public';
 const clean=x=>JSON.parse(JSON.stringify(x));
 for(const mode of ['private','unknown','public']){const b=structuredClone(publicBatch);const child=b.cookingWitness.recipe.provenance.citations[0].citations[0];if(mode==='unknown')delete child.visibility;else child.visibility=mode;
 const servedProjection=app.shared(b),exactHelperProjection=codec.sharedCookingBatch(b);assert.deepEqual(clean(servedProjection),clean(exactHelperProjection));assert.equal(Object.hasOwn(servedProjection,'cookingWitness'),mode==='public');assert.deepEqual(clean(servedProjection.allocations),clean(b.allocations));if(mode!=='public')assert.equal(JSON.stringify(servedProjection).includes('synthetic-private-evidence'),false);privacyCases.push({nestedVisibility:mode,outerVisibility:b.cookingWitness.visibility,witnessIncluded:Object.hasOwn(servedProjection,'cookingWitness'),servedAndExactSourceHelperEqual:true,unrelatedAllocationsRetained:true});}
 const result={status:'passed-focused-v198-changed-path',release:{version:'188dac2d-ac29-4354-a757-e112a9a84258',deployment:'786625f4-e35e-4aa8-a112-359979d467fc',sha256:crypto.createHash('sha256').update(source).digest('hex'),bytes:Buffer.byteLength(source)},callback:{symbol:'applyNutrition production callback',startCharacter:cb.start,endCharacter:cb.end,sha256:crypto.createHash('sha256').update(callbackSource).digest('hex')},checkpoints,privacyCases,blockedRequests,assertions:{actualCallerMenuCookServeReload:true,recipeVersionSourceLicenseInstructionsAndIngredientsFrozen:true,oldBatchAndHistoryWitnessByteIdenticalAfterEdits:true,originalLotProfileAndSourceReleaseFrozen:true,oldQuantitiesAndNutrientTotalsPreserved:true,knownZeroSaltAndAbsentVitaminCPreserved:true,currentRecipeAndLotProfileUpdated:true},finding:{id:'NS196-G2',disposition:'Resolved for independently executed synthetic served-client recipe/version/source/profile cooking-witness path and corrected helper shared projection; authenticated Worker roundtrip and real-source semantics remain outside this evidence.'},limitations:['Actual hash-pinned served client evaluated in isolated VM with retained minimal DOM/storage shims. Exact production applyNutrition callback receives an explicitly confirmed synthetic profile because picker UI is fixture-disabled. Real caller menu/cook/serve handlers and local reload executed.','Shared projection exercised both served bundled helper and exact hash-bound corrected source helper; no authenticated shared workspace or real-account persistence exercised. Existing independent Worker review is separate evidence, not rerun.','No full v195/v196 journey, product/corpus tests or provider/device/browser-session access; runtime fetches blocked. Synthetic data only.']};fs.writeFileSync(new URL('./EXECUTED-DELTA.json',import.meta.url),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify({status:result.status,release:result.release,checkpointCount:checkpoints.length,assertions:result.assertions,privacyCases,blockedRequests}));
}catch(e){console.error(e.stack);process.exitCode=1;}
