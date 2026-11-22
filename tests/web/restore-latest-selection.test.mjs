import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync as read} from 'node:fs';
const app=read(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const source=app.slice(app.indexOf('async function readJSON'),app.indexOf("let recipeImportGeneration=0;"));
function fixture(){
 let requestIdentity={},lots=[{id:'initial'}],profile={},products={},recipes=[],selections=[];
 const user=null,demoMode=false,field={value:'',files:[]},$=()=>field;
 const KEY='inv',PROFILE='profile',PRODUCTS='product',RECIPES='recipe',SELECTIONS='selection', PANTRY_BACKUP_MAX_BYTES=20_000_000;
 const prompts=[],writes=[],statuses=[],choice={accept:true};
 const localStorage={getItem:()=>null,setItem:(k,v)=>{if(k===KEY)writes.push(JSON.parse(v)[0].id);},removeItem(){}};
 const restorePantryBackup=v=>({inventory:v.inventory,state:null});
 const t=s=>s,confirm=s=>(prompts.push(s),choice.accept),today=()=>'',reconcileCookedStock=()=>[];
 const markDirty=()=>{},loadProfile=()=>{},pantry=()=>{},findMeals=()=>{},msg=s=>statuses.push(s);
 eval(source);
 function select(id){let end;const promise=new Promise(resolve=>end=resolve);field.files=[{size:40,text:()=>promise}];field.value=id;return {end:(raw=JSON.stringify({version:1,inventory:[{id}]}))=>end(raw),done:field.onchange()};}
 return {select,field,prompts,writes,statuses,choice,switchActor(){requestIdentity={};}};
}
for(const olderFirst of [true,false])test('only latest selection prompts/writes, olderFirst='+olderFirst,async()=>{
 const f=fixture(),a=f.select('old'),b=f.select('latest');
 if(olderFirst){a.end();await a.done;assert.equal(f.field.value,'latest');assert.deepEqual(f.prompts,[]);b.end();await b.done;}
 else {b.end();await b.done;a.end();await a.done;}
 assert.deepEqual(f.writes,['latest']);assert.deepEqual(f.prompts,['Replace your pantry with this backup?']);assert.equal(f.field.value,'');
});
test('stale parse error does not report, prompt or clear newer choice; current parse error still reports',async()=>{
 const f=fixture(),a=f.select('old'),b=f.select('latest');a.end('{');await a.done;
 assert.deepEqual(f.statuses,[]);assert.equal(f.field.value,'latest');
 b.end('{');await b.done;assert.equal(f.statuses.length,1);assert.deepEqual(f.prompts,[]);assert.deepEqual(f.writes,[]);assert.equal(f.field.value,'');
});
test('actor change prevents prior confirmation/write and cancelled current prompt makes no write',async()=>{
 const f=fixture(),a=f.select('old');f.switchActor();a.end();await a.done;
 assert.deepEqual(f.prompts,[]);assert.deepEqual(f.writes,[]);assert.match(f.statuses[0],/Account changed/);
 f.choice.accept=false;
 const b=f.select('latest');b.end();await b.done;
 assert.deepEqual(f.prompts,['Replace your pantry with this backup?']);assert.deepEqual(f.writes,[]);assert.equal(f.field.value,'');
});
