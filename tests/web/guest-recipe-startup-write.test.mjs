import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
import {validateRecipes} from '../../apps/web/src/model.js';

const source=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const initializer=source.match(/^async function init\(\).*$/m)?.[0];
assert.ok(initializer,'mounted startup initializer must still be bound');
const row=id=>({id,title:id,source:'Test fixture',license:'Test fixture',servings:1,ingredients:[{ingredient:'rice',quantity:1,unit:'g'}],instructions:[]});
const earlier=row('earlier'),later=row('later'),catalogue=row('catalogue');
async function startup({before=[earlier],after=before,remote=[],status='unavailable',current=true,user=null,demoMode=false}={}){
 let release,entered;
 const wait=new Promise(resolve=>{release=resolve}), ready=new Promise(resolve=>{entered=resolve});
 let stored=before===null?null:JSON.stringify(before);
 const writes=[],messages=[];
 const c=vm.createContext({user,demoMode,KEY:'test-pantry',PRODUCTS:'test-products',RECIPES:'test-recipes',
  recipes:[],lots:[],products:{},recipeAvailability:'local-only',
  jsonFetch:async()=>({}),initAuth:async()=>{},loadProfile(){},validateLot:x=>x,validateRecipes,
  localStorage:{getItem:key=>key==='test-recipes'?stored:null,setItem(key,value){assert.equal(key,'test-recipes');writes.push(JSON.parse(value));stored=value;}},
  async fetchRecipes(){entered();return wait;},isCurrentRecipeRead:()=>current,
  pantry(){},findMeals(){},connectivity(){},lifecycleFixture:true,navigator:{},msg:x=>messages.push(x),t:x=>x});
 vm.runInContext(initializer,c);
 const pending=c.init();await ready;stored=after===null?null:JSON.stringify(after);
 release({recipes:remote,status});await pending;assert.deepEqual(messages,[]);
 return {writes,stored:stored===null?null:JSON.parse(stored),recipes:JSON.parse(JSON.stringify(c.recipes)),availability:c.recipeAvailability};
}
test('Guest startup with unavailable or empty catalogue does not rewrite the offline cache',async()=>{
 for(const status of ['unavailable','loaded']){
  const result=await startup({status});
  assert.deepEqual(result,{writes:[],stored:[earlier],recipes:[earlier],availability:status});
 }
});
test('Guest startup does not overwrite a later append or resurrect a cleared value',async()=>{
 for(const after of [[earlier,later],null]){
  const result=await startup({after});
  assert.deepEqual(result,{writes:[],stored:after,recipes:after??[],availability:'unavailable'});
 }
});
test('a fetched catalogue discarded after an observed Guest change is not reported as loaded',async()=>{
 const result=await startup({after:[earlier,later],remote:[catalogue],status:'loaded'});
 assert.deepEqual(result,{writes:[],stored:[earlier,later],recipes:[earlier,later],availability:'deferred'});
});
test('positive unchanged Guest cache, signed-in and Demo flows, and stale-read fence retain their behavior',async()=>{
 const fetched=await startup({remote:[catalogue],status:'loaded'});
 assert.deepEqual(fetched,{writes:[[earlier,catalogue]],stored:[earlier,catalogue],recipes:[earlier,catalogue],availability:'loaded'});
 for(const actor of [{user:{id:'synthetic'}},{demoMode:true}]){
  const nonGuest=await startup(actor);
  assert.deepEqual(nonGuest,{writes:[[earlier]],stored:[earlier],recipes:[earlier],availability:'unavailable'});
 }
 const stale=await startup({after:[earlier,later],remote:[catalogue],status:'loaded',current:false});
 assert.deepEqual(stale,{writes:[],stored:[earlier,later],recipes:[],availability:'local-only'});
});

test('a deferred update explains that the catalogue update was not applied in both Meals states',async()=>{
 const {availability}=await startup({after:[earlier,later],remote:[catalogue],status:'loaded'});
 const note={dataset:{},textContent:''};
 const noteSource=source.slice(source.indexOf('function renderRecipeAvailabilityNote('),source.indexOf('function findMeals('));
 const emptySource=source.match(/setLocalizedText\(empty,(recipeAvailability===[\s\S]*?)\);setLocalizedText\(clear,'Clear filters'\)/)?.[1];
 assert.ok(noteSource&&emptySource);
 const c=vm.createContext({recipeAvailability:availability,$:()=>note,setLocalizedText(node,text){node.textContent=text;}});
 vm.runInContext(noteSource+'renderRecipeAvailabilityNote(true)',c);
 assert.equal(note.hidden,false);
 assert.equal(note.textContent,'Showing recipes saved on this device. The catalogue update was not applied.');
 assert.equal(vm.runInContext(emptySource,c),'No matching menus in the recipes saved on this device. The catalogue update was not applied.');
});
