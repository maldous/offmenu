import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {pathToFileURL,fileURLToPath} from 'node:url';

const base=resolve(process.env.OFFMENU_SOURCE_APP||fileURLToPath(new URL('..',import.meta.url)));
const ui=resolve(process.env.OFFMENU_CANDIDATE_APP||base);
const sourceUrl=name=>pathToFileURL(resolve(base,name)).href;
const {cookMeal,serveBatch,reconcileCookedStock,undoCook}=await import(sourceUrl('public/cooking-model.js'));
const {intakeSummary}=await import(sourceUrl('public/insights-model.js'));
const {validateState}=await import(sourceUrl('cloud/state.mjs'));
const {NUTRIENTS}=await import(sourceUrl('public/menu-model.js'));
const {setupJourney}=await import(sourceUrl('public/journey-ui.js'));
let insightsSource=await readFile(resolve(ui,'public/insights-ui.js'),'utf8');
insightsSource=insightsSource.replace(/from '(\.\/[^']+)'/g,(_,name)=>'from '+JSON.stringify(sourceUrl('public/'+name.slice(2))));
const {setupInsights}=await import('data:text/javascript;base64,'+Buffer.from(insightsSource).toString('base64'));
const appSource=await readFile(resolve(base,'public/app.js'),'utf8');
const saveSource=appSource.match(/^function save\(next\)\{[^\n]+\}$/m)?.[0];
const persistSource=appSource.match(/^function persistProfile\(\)\{[^\n]+\}$/m)?.[0];
const commitSource=appSource.match(/^const journey=setupJourney\([^\n]+commit:(.+)\}\);$/m)?.[1];
assert.ok(saveSource&&persistSource&&commitSource,'exact current app save/persist/journey callback must be found');
const DATE='2026-10-28';
const recipe={id:'synthetic-rice',title:'Synthetic rice',servings:4,ingredients:[{ingredient:'rice',quantity:400,unit:'g'}],instructions:['Synthetic fixture only'],source:'synthetic-test',license:'test-fixture'};
const product={name:'Synthetic rice',nutrition_data_per:'100g',nutriments:{'energy-kcal_100g':100,proteins_100g:8}};
const lot={id:'synthetic-raw',barcode:'local:synthetic-rice',name:'Synthetic rice',ingredient:'rice',quantity:1000,unit:'g',location:{area:'Pantry',shelf:'Synthetic'},needsReview:false,amountBasis:'manual'};
const fixture=()=>({inventory:[structuredClone(lot)],products:{[lot.barcode]:structuredClone(product)},recipes:[structuredClone(recipe)],selections:[],profile:{servings:4,units:'metric',country:'',batches:[],history:[],plan:[],members:[]}});
const preventDefault=()=>{};
class Element{
 constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.dataset={};this.style={};this.textContent='';this.hidden=false;this.checked=false;this.open=false;this.classList={toggle(){}};}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.children=[...nodes];}
 get options(){return this.children;}
 setAttribute(){}
 addEventListener(){}
 showModal(){this.open=true;}
 close(){this.open=false;}
 reset(){}
}
function harness(state=fixture()){
 const original=Object.getOwnPropertyDescriptor(globalThis,'document'),elements=new Map(),stored=new Map();
 const $=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 globalThis.document={getElementById:$,createElement:tag=>new Element(tag),querySelectorAll:()=>[],documentElement:new Element('html')};
 const storage={setItem:(key,value)=>stored.set(key,value),getItem:key=>stored.get(key)??null};
 // Execute the existing app callback, save(), and persistProfile(), not a substitute commit.
 const bridge=new Function('state','localStorage','reconcileCookedStock','today',`
 let {profile,lots}= {profile:state.profile,lots:state.inventory};
 const PROFILE='synthetic-profile',KEY='synthetic-inventory';
 let feedback={},dirty=0;const markDirty=()=>{dirty++},applyFeedbackSettings=()=>{},pantry=()=>{},findMeals=()=>{};
 ${saveSource}\n${persistSource}
 const commit=${commitSource};
 return {commit,getData:()=>({...state,profile,inventory:lots}),getDirty:()=>dirty};
 `)(state,storage,reconcileCookedStock,()=>DATE);
 const journey=setupJourney({getData:bridge.getData,commit:bridge.commit,today:()=>DATE,view(){}});
 const downloads=[];
 const insights=setupInsights({getData:()=>({...bridge.getData(),date:DATE,usePantry:true}),persist(){},download:(...args)=>downloads.push(args),today:()=>DATE,request:()=>{throw Error('Network prohibited in synthetic test');}});
 $('history-range').value='7';
 const cook=()=>{journey.openCook(state.recipes[0]);$('cook-confirm').onclick();assert.equal(state.profile.batches.length,1,$('cook-notice').textContent);return state.profile.batches[0];};
 const serve=(batch,{portions=1,completion='',remainder='unspecified'}={})=>{journey.openServe(batch);$('serve-portions').value=String(portions);$('serve-completion').value=String(completion);$('serve-remainder').value=remainder;$('serve-form').onsubmit({preventDefault});assert.equal($('serve-dialog').open,false,$('serve-notice').textContent);return state.profile.history.at(-1);};
 return {$,journey,insights,state,stored,downloads,getData:bridge.getData,cook,serve,cleanup(){if(original)Object.defineProperty(globalThis,'document',original);else delete globalThis.document;}};
}
const rawQuantity=data=>data.inventory.filter(l=>!l.cookBatchId).reduce((sum,l)=>sum+l.quantity,0);
const cookedQuantity=data=>data.inventory.filter(l=>l.cookBatchId).reduce((sum,l)=>sum+l.quantity,0);

test('actual cook -> save/persist -> saved remainder -> unknown serving -> snapshot restore preserves conservation',()=>{
 const h=harness();try{
  const batch=h.cook();assert.equal(rawQuantity(h.getData()),600);assert.equal(cookedQuantity(h.getData()),4);
  const first=h.serve(batch,{portions:2,completion:50,remainder:'saved'});
  assert.equal(first.servings,1);assert.equal(first.totals['energy-kcal_100g'].value,100);
  assert.equal(cookedQuantity(h.getData()),3);assert.equal(rawQuantity(h.getData()),600);
  const unknown=h.serve(h.state.profile.batches[0]);assert.equal(unknown.intakeKnown,false);assert.equal(unknown.servings,0);
  assert.equal(unknown.totals['energy-kcal_100g'].known,0);assert.equal(unknown.totals['energy-kcal_100g'].total,1);
  assert.equal(cookedQuantity(h.getData()),2);assert.equal(rawQuantity(h.getData()),600);
  assert.equal(h.state.profile.batches[0].remaining,2);assert.equal(h.state.profile.batches[0].events.length,2);
  assert.deepEqual(JSON.parse(h.stored.get('synthetic-profile')),h.state.profile);
  assert.deepEqual(JSON.parse(h.stored.get('synthetic-inventory')),h.getData().inventory);
  const restored=validateState(JSON.parse(JSON.stringify(h.getData())));
  assert.equal(restored.profile.history[1].intakeKnown,false);assert.equal(restored.profile.history[1].totals['energy-kcal_100g'].known,0);
  assert.equal(restored.profile.batches[0].remaining,cookedQuantity(restored));
  const totals=intakeSummary(restored.profile.history,[DATE]).totals;
  assert.deepEqual(totals['energy-kcal_100g'],{value:100,known:1,total:2});
  assert.deepEqual(totals['calcium_100g'],{value:0,known:0,total:2});
  h.insights.render();assert.ok(h.$('food-history').children.some(card=>/intake amount unknown/.test(card.children[1].textContent)));
  const calcium=h.$('intake-nutrients').children[NUTRIENTS.findIndex(([key])=>key==='calcium_100g')];
  assert.equal(calcium.children[0].textContent,'—');
 }finally{h.cleanup();}
});

for(const remainder of ['saved','discarded','shared','unspecified'])test('actual serving caller conserves cooked stock for '+remainder,()=>{
 const h=harness();try{
  const batch=h.cook();h.serve(batch,{portions:2,completion:25,remainder});
  const next=h.state.profile.batches[0],event=next.events[0];
  assert.equal(event.eaten,0.5);assert.equal(event.saved+event.discarded+event.shared+event.unknownRemainder,1.5);
  assert.equal(next.remaining,remainder==='saved'?3.5:2);assert.equal(next.remaining,cookedQuantity(h.getData()));
  assert.equal(rawQuantity(h.getData()),600);assert.equal(h.state.profile.history.length,1);
 }finally{h.cleanup();}
});

test('model idempotence does not consume stock or record duplicate history and changed retry is rejected',()=>{
 const state=fixture(),cooked=cookMeal({...state,recipe,servings:4,date:DATE,mutationId:'synthetic-batch'});
 const input={batch:cooked.batch,inventory:cooked.inventory,portions:1,completion:50,remainder:'saved',date:DATE,eventId:'synthetic-event'};
 const first=serveBatch(input),duplicate=serveBatch({...input,batch:first.batch,inventory:first.inventory});
 assert.equal(duplicate.duplicate,true);assert.equal(duplicate.log,undefined);assert.deepEqual(duplicate.inventory,first.inventory);assert.equal(duplicate.batch.events.length,1);
 assert.throws(()=>serveBatch({...input,batch:first.batch,inventory:first.inventory,completion:100}),/Serving event changed/);
 const cookDuplicate=cookMeal({...state,recipe,inventory:cooked.inventory,servings:4,date:DATE,batches:[cooked.batch],mutationId:'synthetic-batch'});
 assert.equal(cookDuplicate.duplicate,true);assert.deepEqual(cookDuplicate.inventory,cooked.inventory);
});

test('stock removal reconciliation never restores raw ingredients or mutates consumed history',()=>{
 const h=harness();try{
  const batch=h.cook();h.serve(batch,{portions:1,completion:100});
  const data=h.getData(),history=structuredClone(data.profile.history);
  const inventory=data.inventory.filter(l=>!l.cookBatchId),batches=reconcileCookedStock(data.profile.batches,inventory,{date:DATE});
  assert.equal(batches[0].remaining,0);assert.equal(batches[0].events.at(-1).type,'inventory-removal');
  assert.equal(rawQuantity({inventory}),600);assert.deepEqual(data.profile.history,history);
  assert.throws(()=>undoCook(batches[0],inventory),/served batch cannot be undone/);
 }finally{h.cleanup();}
});

test('actual serving uses compatible nutrient evidence only, never fabricating unknown as known zero',()=>{
 const state=fixture();state.products[lot.barcode].nutrition_data_per='100ml';
 const h=harness(state);try{const batch=h.cook();const log=h.serve(batch,{completion:100});
  assert.equal(log.intakeKnown,true);assert.equal(log.servings,1);
  assert.deepEqual(log.totals['energy-kcal_100g'],{value:0,known:0,total:1});
  assert.deepEqual(log.totals['calcium_100g'],{value:0,known:0,total:1});
 }finally{h.cleanup();}
});

test('actual CSV caller leaves unknown intake blank but retains explicit zero and positive portions',()=>{
 const h=harness();try{
  const batch=h.cook();h.serve(batch);
  h.serve(h.state.profile.batches[0],{completion:0,remainder:'saved'});
  h.serve(h.state.profile.batches[0],{completion:50});
  h.$('history-csv').onclick();assert.equal(h.downloads.length,1);
  const [name,content,mime]=h.downloads[0];assert.equal(name,'offmenu-food-history.csv');assert.equal(mime,'text/csv;charset=utf-8');
  const rows=content.split('\r\n').map(row=>[...row.matchAll(/"((?:[^"]|"")*)"(?:,|$)/g)].map(match=>match[1].replaceAll('""','"')));
  assert.equal(rows[0][4],'Portions');assert.equal(rows[1][4],'','unknown completion must not export the storage placeholder as zero portions');
  assert.equal(rows[2][4],'0','explicit 0% completion remains a known zero');assert.equal(rows[3][4],'0.5');
  assert.equal(rows[1][6],'','unknown energy is blank');assert.equal(rows[1][7],'0/1');assert.equal(rows[2][6],'0');
  assert.ok(rows.every(row=>row.length===rows[0].length),'CSV column contract unchanged');
 }finally{h.cleanup();}
});
