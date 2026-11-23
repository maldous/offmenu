import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {getLanguage,hasTranslation,setLanguage,setLocalizedText,t} from '../../apps/web/src/i18n.js';

const app=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const start=app.indexOf('function renderRecipeAvailabilityNote(');
const end=app.indexOf("$('refresh').onclick=",start);
assert.ok(start>=0&&end>start,'bind the actual Meals notice and findMeals entry points');
const renderers=app.slice(start,end);
const states=[
 [
  "deferred",
  "Showing recipes saved on this device. The catalogue update was not applied.",
  "No matching menus in the recipes saved on this device. The catalogue update was not applied."
 ],
 [
  "partial",
  "Some recipes did not load. Showing the recipes that are available.",
  "Some recipes did not load. Try again later or browse the recipes already saved."
 ],
 [
  "unavailable",
  "The recipe catalogue did not load. Showing recipes already available to this kitchen.",
  "The recipe catalogue did not load. Try again later."
 ],
 [
  "loaded",
  "",
  "No matching menus in the recipes loaded. Try another ingredient or choose the whole kitchen."
 ],
 [
  "local-only",
  "",
  "No matching menus in the recipes saved on this device."
 ]
];

function mountMeals(recipeAvailability){
 class Node {
  constructor(tag){Object.assign(this,{tag,children:[],dataset:{},value:'',checked:false,textContent:'',hidden:false,classList:{toggle(){}}});}
  append(...children){this.children.push(...children);}
  replaceChildren(){this.children=[];}
  setAttribute(name,value){this[name]=value;}
  set innerHTML(_){assert.fail('The localized status must be text');}
 }
 const nodes=new Map();
 const $=id=>{if(!nodes.has(id))nodes.set(id,new Node(id));return nodes.get(id);};
 $('servings').value='2';
 const profile={members:[]};let plans=0;
 const context={recipeAvailability,document:{createElement:tag=>new Node(tag),createTextNode:textContent=>({textContent})},
  $,t,setLocalizedText,recipes:[],lots:[],products:{},profile,absentDiners:new Set(),
  menuInventory:()=>[],renderDinnerMembers(){},rankedMenus:()=>[],quantified:()=>true,
  today:()=>'2026-11-23',normalizeSearchText:value=>value,
  renderPlan(){plans++;},fetch(){assert.fail('Rendering an existing status must not start a lookup');},
  localStorage:{setItem(){assert.fail('Status display must not write to the kitchen');}},
  markDirty(){assert.fail('Status display must not dirty the kitchen');},
 };
 const run=code=>runInNewContext(renderers+'\n'+code,context);
 run('findMeals();');
 const empty=$('meals').children.find(child=>child.className==='empty-state');assert.ok(empty);
 assert.equal(plans,1);
 assert.deepEqual(profile,{members:[]});
 return {empty,note:$('recipe-availability-note'),run};
}

for(const locale of ['en','ar'])test('actual Meals notices keep availability states distinct in '+locale,()=>{
 const previous=getLanguage();setLanguage(locale);
 try{
  const seen=new Set();
  for(const [state,noticeKey,emptyKey] of states){
   const {empty,note,run}=mountMeals(state);
   assert.equal(empty.textContent,t(emptyKey),state);
   assert.equal(empty.lang,locale,state);
   assert.equal(empty.dir,'auto',state);
   assert.equal(note.hidden,true,'no second availability notice when the empty state is shown');
   if(locale==='ar'){assert.match(empty.textContent,/\p{Script=Arabic}/u,state);assert.notEqual(empty.textContent,emptyKey);}
   else assert.equal(empty.textContent,emptyKey,state);
   seen.add(empty.textContent);
   run('renderRecipeAvailabilityNote(true);');
   assert.equal(note.hidden,!noticeKey,state);
   if(noticeKey){
    assert.equal(note.textContent,t(noticeKey));assert.equal(note.lang,locale);
    if(locale==='ar'){assert.match(note.textContent,/\p{Script=Arabic}/u);assert.notEqual(note.textContent,noticeKey);}
    else assert.equal(note.textContent,noticeKey);
   }
  }
  assert.equal(seen.size,states.length);
  if(locale==='ar')assert.match(mountMeals('loaded').empty.textContent,new RegExp(t('Whole kitchen')));
 }finally{setLanguage(previous);}
});

test('unknown wording still falls back and a malformed language request uses the default',()=>{
 const previous=getLanguage();setLanguage('ar');
 try{
  const untouched='__offmenu_test_untranslated_fixture__';
  assert.equal(hasTranslation(untouched),false);
  assert.equal(t(untouched),untouched);
  assert.equal(setLanguage('not/a-locale'),'en');
 }finally{setLanguage(previous);}
});
