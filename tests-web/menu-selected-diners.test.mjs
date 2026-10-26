import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {webcrypto} from 'node:crypto';
import {appendRecipeIngredientCoverage} from '../public/recipe-ingredient-coverage-ui.js';
import {pathToFileURL} from 'node:url';

// Execute the real rendered-menu and diner-checkbox handlers with synthetic
// state. This is source/handler evidence, not a browser or real-user test.
const source=readFileSync(process.env.OFFMENU_APP_SOURCE||new URL('../public/app.js',import.meta.url),'utf8');
const moduleURL=(variable,name)=>process.env[variable]?pathToFileURL(process.env[variable]).href:new URL('../public/'+name,import.meta.url).href;
const {planSummary,NUTRIENTS}=await import(moduleURL('OFFMENU_MENU_MODULE','menu-model.js'));
const {rankedMenus,householdPortions}=await import(moduleURL('OFFMENU_HOUSEHOLD_MODULE','household-model.js'));
const {quantified}=await import(moduleURL('OFFMENU_INGREDIENT_MODULE','ingredients.js'));
function declaration(name,end){
 const marker='function '+name+'(';
 assert.equal(source.split(marker).length,2,'one real '+name+' declaration');
 const start=source.indexOf(marker),finish=source.indexOf(end,start);
 assert.ok(finish>start,'bounded real '+name+' source');
 return source.slice(start,finish);
}
const handlers=declaration('findMeals',"\n$('refresh').onclick")+'\n'+declaration('renderDinnerMembers','\nlet syncReady=');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.value='';this.checked=false;this.style={};this.dataset={};this.attributes={};this.textContent='';this.ownerDocument=document;this.classList={toggle:(name,on)=>{this.classes??=new Set();on?this.classes.add(name):this.classes.delete(name);}};}
 setAttribute(name,value){this.attributes[name]=value;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=[...children];}
}
const document={createElement:tag=>new Element(tag),createTextNode:text=>String(text),activeElement:null};
const plain=x=>JSON.parse(JSON.stringify(x));
const date='2026-10-26';
const recipe={id:'synthetic:rice',title:'Synthetic rice meal',servings:2,source:'synthetic-fixture',license:'fixture-only',instructions:['Synthetic step'],ingredients:[{ingredient:'rice',quantity:100,unit:'g'}]};
const members=[{id:'small',name:'Same name',portion:.5,advisors:[],avoid:[],restrictions:[]},{id:'large',name:'Same name',portion:1.5,advisors:[],avoid:[],restrictions:[]}];
function harness({people=members,mapped=true,recipeCount=1}={}){
 const elements=new Map(),$=id=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
 const inventory=[{id:'synthetic-lot',barcode:'synthetic-product',ingredient:mapped?'rice':'unmapped',quantity:500,unit:'g'}];
 // Explicit synthetic product/ingredient association and illustrative per100g
 // values. No source-local DTO identity or product name establishes this join.
 const products={'synthetic-product':{name:'Rice',product_quantity:500,product_quantity_unit:'g',nutrition_data_per:'100g',nutriments:{proteins_100g:7}}};
 const store=new Map();let dirty=0;
 const ctx={$,recipeLibrary:null,profile:{members:plain(people),units:'metric',plan:[]},recipes:Array.from({length:recipeCount},(_,i)=>({...plain(recipe),id:recipeCount===1?recipe.id:recipe.id+':'+i})),products,absentDiners:new Set(),selections:[],PROFILE:'synthetic-profile',crypto:webcrypto,NUTRIENTS,planSummary,rankedMenus,householdPortions,quantified,
  document,appendRecipeIngredientCoverage,
  today:()=>date,menuInventory:()=>inventory,normalizeSearchText:s=>String(s).toLowerCase(),multilingualSearchText:r=>r.title.toLowerCase(),normalize:s=>String(s).toLowerCase(),locationKey:()=>'',
  setLocalizedText:(el,text,values={})=>{el.textContent=String(text).replace(/\{(v\d+)\}/g,(_,k)=>String(values[k]));},t:(s,values={})=>String(s).replace(/\{(v\d+)\}/g,(_,k)=>String(values[k])),getLanguage:()=> 'en',
  localizedField:(r,k)=>({value:r[k]}),showLocalized:(el,v)=>{el.textContent=v.value;},displayAmount:(n,u)=>n+' '+u,displayName:s=>s,
  renderPlan(){},markDirty(){dirty++;},localStorage:{setItem:(key,value)=>store.set(key,value)},journey:{openCook(){}}
 };
 $('servings').value=String(householdPortions(people));$('plan-date').value=date;$('plan-slot').value='Dinner';
 vm.createContext(ctx);vm.runInContext(handlers,ctx);ctx.findMeals();
 const checkbox=index=>$('dinner-members').children[index+1].children[0];
 const add=()=>{const article=$('meals').children.find(x=>x.tag==='article');const button=article.children.find(x=>x.tag==='button'&&x.className==='coral');assert.ok(button);button.onclick();return plain(ctx.profile.plan.at(-1));};
 const summary=()=>planSummary(plain(ctx.profile.plan),[recipe],inventory,products,[date]);
 return {ctx,$,store,checkbox,add,summary,dirty:()=>dirty};
}
test('excluded diner is absent from persisted menu; half portion demands25g and keeps missing nutrition unknown',()=>{
 const h=harness();const box=h.checkbox(1);box.checked=false;box.onchange();
 assert.equal(Number(h.$('servings').value),.5);
 const meal=h.add();assert.deepEqual(meal.memberIds,['small']);assert.equal(meal.servings,.5);
 assert.deepEqual(JSON.parse(h.store.get('synthetic-profile')).plan[0].memberIds,['small']);
 const s=h.summary();assert.equal(s.requirements[0].quantity,25);assert.equal(s.totals.proteins_100g.value,1.75);assert.equal(s.totals.proteins_100g.known,1);
 assert.equal(s.totals.fat_100g.known,0);assert.equal(s.totals.fat_100g.total,1);
 assert.ok(h.$('meals').children[0].children.some(x=>x.tag==='details'&&x.children.some(y=>y.className==='recipe-food-data'&&y.textContent.includes('Fat: not available'))));
 assert.equal(h.dirty(),1);
});
test('both present retain separate IDs despite identical names and demand100g',()=>{
 const h=harness();const meal=h.add();assert.deepEqual(meal.memberIds,['small','large']);assert.equal(meal.servings,2);assert.equal(h.summary().requirements[0].quantity,100);
});
test('restoring a diner uses the new rendered selection and quantity',()=>{
 const h=harness();let box=h.checkbox(1);box.checked=false;box.onchange();h.add();box=h.checkbox(1);box.checked=true;box.onchange();
 const meal=h.add();assert.deepEqual(meal.memberIds,['small','large']);assert.equal(meal.servings,2);assert.equal(h.ctx.profile.plan[0].servings,.5);
 assert.deepEqual(plain(h.ctx.profile.plan[0].memberIds),['small']);
});
test('product name cannot create a missing ingredient join or turn absent nutrient evidence into known zero',()=>{
 const h=harness({mapped:false});h.add();const s=h.summary();assert.equal(s.missing[0].quantity,100);assert.equal(s.totals.proteins_100g.known,0);assert.equal(s.totals.proteins_100g.total,1);
});
test('anonymous measured menu keeps no invented household identity',()=>{
 const h=harness({people:[]});const meal=h.add();assert.deepEqual(meal.memberIds,[]);assert.equal(meal.servings,2);assert.equal(h.summary().requirements[0].quantity,100);
});

 test('filtered results expose the entire loaded collection and last result saves only selected diners',()=>{
 const h=harness({recipeCount:130});
 assert.equal(h.$('meals').children.length,24);
 assert.equal(h.$('meals').tabIndex,-1);
 const box=h.checkbox(1);box.checked=false;box.onchange();
 h.$('menu-search').value='synthetic';h.ctx.findMeals();
 assert.equal(h.$('meals').children.length,130);
 assert.equal(h.$('meals').tabIndex,0);
 assert.equal(h.$('meals').classes.has('meal-results-scroll'),true);
 const last=h.$('meals').children.at(-1);
 last.children.find(x=>x.tag==='button'&&x.className==='coral').onclick();
 assert.equal(h.ctx.profile.plan.at(-1).recipeId,recipe.id+':129');
 assert.deepEqual(plain(h.ctx.profile.plan.at(-1).memberIds),['small']);
 h.$('menu-search').value='';h.ctx.findMeals();
 assert.equal(h.$('meals').children.length,24);
 assert.equal(h.$('meals').classes.has('meal-results-scroll'),false);
 h.$('show-all-meals').checked=true;h.ctx.findMeals();
 assert.equal(h.$('meals').children.length,130);
 });
