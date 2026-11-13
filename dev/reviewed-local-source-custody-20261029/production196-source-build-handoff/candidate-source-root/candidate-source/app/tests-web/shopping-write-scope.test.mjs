import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import path from 'node:path';
const root=process.env.SOURCE_ROOT||new URL('..',import.meta.url).pathname;
const {setupInsights}=await import(pathToFileURL(path.join(root,'public/insights-ui.js')));
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.checked=false;this.disabled=false;this.textContent='';this.style={};}
 replaceChildren(...nodes){this.children=[...nodes];}
 append(...nodes){this.children.push(...nodes);}
 setAttribute(){}
}
function harness({write=true,planned=false}={}){
 const old=Object.getOwnPropertyDescriptor(globalThis,'document'),elements=new Map();
 const el=id=>{if(!elements.has(id))elements.set(id,new Element('div'));return elements.get(id);};
 globalThis.document={getElementById:el,createElement:tag=>new Element(tag)};
 const profile={shopping:planned?[]:[{id:'synthetic-item',name:'Rice (synthetic)',amount:'100 g',checked:false}],shoppingChecked:[],plan:planned?[{id:'synthetic-plan',date:'2026-10-28',recipeId:'synthetic-recipe',servings:1}]:[]};
 const recipes=planned?[{id:'synthetic-recipe',title:'Synthetic rice',servings:1,ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]}]:[];
 const state={profile,inventory:[],products:{},recipes,date:'2026-10-28',usePantry:true};let saves=0;
 const insights=setupInsights({getData:()=>state,persist:()=>saves++,download(){},today:()=>state.date,canWriteShopping:()=>write});
 insights.renderShopping();
 return {profile,state,insights,el,get saves(){return saves;},checkbox:()=>el('shopping-checklist').children[0].children[0],remove:()=>el('shopping-checklist').children.find(e=>e.tag==='button'),setWrite:value=>{write=value;},cleanup(){if(old)Object.defineProperty(globalThis,'document',old);else delete globalThis.document;}};
}
for(const planned of [false,true]){
 test((planned?'planned':'custom')+' check changes list state only and replay does not duplicate a check',()=>{const h=harness({planned});try{const c=h.checkbox();c.checked=true;c.onchange();c.onchange();assert.equal(h.saves,2);assert.deepEqual(h.state.inventory,[]);if(planned)assert.deepEqual(h.profile.shoppingChecked,['planned:rice|g']);else assert.equal(h.profile.shopping[0].checked,true);}finally{h.cleanup();}});
 test((planned?'planned':'custom')+' viewer checkbox is disabled and cannot mutate local list state',()=>{const h=harness({write:false,planned});try{const before=structuredClone(h.profile),c=h.checkbox();assert.equal(c.disabled,true);c.checked=true;c.onchange();assert.deepEqual(h.profile,before);assert.equal(h.saves,0);assert.equal(c.checked,false);}finally{h.cleanup();}});
 test((planned?'planned':'custom')+' editable toggle then revocation restores the current canonical check without a write',()=>{const h=harness({planned});try{const c=h.checkbox();c.checked=true;c.onchange();const before=structuredClone(h.profile);assert.equal(h.saves,1);h.setWrite(false);c.checked=false;c.onchange();assert.deepEqual(h.profile,before);assert.equal(h.saves,1);assert.equal(c.checked,true);c.checked=false;c.onchange();assert.deepEqual(h.profile,before);assert.equal(h.saves,1);assert.equal(c.checked,true);}finally{h.cleanup();}});
 test((planned?'planned':'custom')+' click after write access changed is refused',()=>{const h=harness({planned});try{const before=structuredClone(h.profile),c=h.checkbox();h.setWrite(false);c.checked=true;c.onchange();assert.deepEqual(h.profile,before);assert.equal(h.saves,0);assert.equal(c.checked,false);}finally{h.cleanup();}});
}
test('read-only add and remove handlers preserve the list',()=>{const h=harness({write:false});try{const before=structuredClone(h.profile);h.remove().onclick();h.el('shopping-name').value='Forbidden synthetic addition';h.el('shopping-amount').value='1';h.el('shopping-add-form').onsubmit({preventDefault(){}});assert.deepEqual(h.profile,before);assert.equal(h.saves,0);}finally{h.cleanup();}});
test('editable add and remove still work',()=>{const h=harness();try{h.el('shopping-name').value='Peas (synthetic)';h.el('shopping-amount').value='200 g';h.el('shopping-add-form').onsubmit({preventDefault(){}});assert.equal(h.profile.shopping.length,2);h.remove().onclick();assert.equal(h.profile.shopping.length,1);assert.equal(h.profile.shopping[0].name,'Peas (synthetic)');assert.equal(h.saves,2);}finally{h.cleanup();}});
test('production caller uses existing sharing capability, without replacing authentication',async()=>{const source=await readFile(path.join(root,'public/app.js'),'utf8');assert.equal(/setupInsights\(\{[^\n]*canWriteShopping:\(\)=>sharing\.canWrite\(\)/.test(source),true,'production caller must pass current sharing capability');});
