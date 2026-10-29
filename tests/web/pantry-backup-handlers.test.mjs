import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import {parse} from 'acorn';
import {createPantryBackup,restorePantryBackup} from '../../public/pantry-backup.js';
import {reconcileCookedStock} from '../../public/cooking-model.js';

// Execute the actual browser handlers without starting the app or touching real storage.
const source=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');
const ast=parse(source,{ecmaVersion:'latest',sourceType:'module'});
function fixture({failKey,absent=false}={}){
 const nodes=new Map(),messages=[],downloads=[],sync=[];
 const old={inventory:[],profile:{country:'AU',units:'metric',servings:2},products:{},recipes:[],selections:[]};
 const raw=new Map([['pantry','[] '],['profile',JSON.stringify(old.profile)+' '],['products','{} '],['recipes','[] '],['selections','[] ']]);
 if(absent)raw.delete('products');
 const before=new Map(raw);let failed=false;
 const $=id=>{if(!nodes.has(id))nodes.set(id,{files:[],value:''});return nodes.get(id);};
 const context={$,Blob,JSON,Object,Error,createPantryBackup,restorePantryBackup,reconcileCookedStock,
  KEY:'pantry',PROFILE:'profile',PRODUCTS:'products',RECIPES:'recipes',SELECTIONS:'selections',
  lots:old.inventory,profile:old.profile,products:old.products,recipes:old.recipes,selections:old.selections,
  user:null,requestIdentity:{owner:null},today:()=> '2026-10-26',confirm:()=>true,t:x=>x,
  localStorage:{getItem:k=>raw.get(k)??null,setItem(k,v){if(k===failKey&&!failed){failed=true;throw Error('Synthetic quota failure');}raw.set(k,v);},removeItem:k=>raw.delete(k)},
  msg:x=>messages.push(x),download:(name,data)=>downloads.push({name,data}),loadProfile(){},pantry(){},findMeals(){},
  markDirty(){sync.push(JSON.stringify({inventory:context.lots,profile:context.profile,products:context.products,recipes:context.recipes,selections:context.selections}));}};
 vm.createContext(context);
 // save() is included solely to reproduce the old partial-commit behavior.
 vm.runInContext(source.slice(ast.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='save').start,ast.body.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='save').end),context);
 const start=source.indexOf("$('export').onclick");
 const constStart=source.lastIndexOf('const PANTRY_BACKUP_MAX_BYTES=',start);
 vm.runInContext(source.slice(constStart>=0?constStart:start,source.indexOf("$('recipe-import').onchange",start)),context);
 const input=(value)=>{const text=JSON.stringify(value,null,2);$('restore').files=[{size:new Blob([text]).size,text:async()=>text}];};
 return {context,$,raw,before,messages,downloads,sync,input};
}
const value=()=>({inventory:[{id:'synthetic-lot',barcode:'1111',name:'Rice',ingredient:'rice',quantity:2,unit:'g'}],profile:{country:'AU',units:'metric',servings:3},products:{'1111':{name:'Rice'}},recipes:[],selections:['synthetic-favourite']});

test('a legitimate exported pantry above 2MB restores with the same byte contract',async()=>{
 const f=fixture(),v=value();v.products['1111'].ingredients='rice '.repeat(420000);
 const backup=createPantryBackup(v);assert.ok(new Blob([JSON.stringify(backup,null,2)]).size>2_000_000);
 Object.assign(f.context,{lots:v.inventory,profile:v.profile,products:v.products,recipes:v.recipes,selections:v.selections});
 f.$('export').onclick();assert.equal(f.downloads.length,1);
 f.input(f.downloads[0].data);await f.$('restore').onchange();
 assert.match(f.messages.at(-1),/Backup restored/);assert.equal(f.sync.length,1);
 assert.equal(JSON.parse(f.raw.get('products'))['1111'].ingredients,v.products['1111'].ingredients);
});
test('a late storage failure rolls back exact raw values and leaves memory and sync unchanged',async()=>{
 const f=fixture({failKey:'selections',absent:true}),memory=JSON.stringify({lots:f.context.lots,profile:f.context.profile,products:f.context.products,recipes:f.context.recipes,selections:f.context.selections});
 f.input(createPantryBackup(value()));await f.$('restore').onchange();
 assert.match(f.messages.at(-1),/quota/);assert.deepEqual(f.raw,f.before);assert.equal(f.sync.length,0);
 assert.equal(JSON.stringify({lots:f.context.lots,profile:f.context.profile,products:f.context.products,recipes:f.context.recipes,selections:f.context.selections}),memory);
 assert.equal(f.$('restore').value,'');
});
test('successful restore schedules one coherent complete state',async()=>{
 const f=fixture(),backup=createPantryBackup(value());f.input(backup);await f.$('restore').onchange();
 assert.equal(f.sync.length,1);assert.deepEqual(JSON.parse(f.sync[0]),restorePantryBackup(backup).state);
 for(const [key,field]of [['pantry','inventory'],['profile','profile'],['products','products'],['recipes','recipes'],['selections','selections']])assert.deepEqual(JSON.parse(f.raw.get(key)),JSON.parse(f.sync[0])[field]);
});
test('inventory-only backup retains the current profile and other stores',async()=>{
 const f=fixture(),oldProfile=f.context.profile,oldProducts=f.context.products;
 f.input({version:1,inventory:value().inventory});await f.$('restore').onchange();
 assert.match(f.messages.at(-1),/Backup restored/);assert.equal(f.context.profile.servings,oldProfile.servings);
 assert.equal(f.context.products,oldProducts);assert.equal(f.sync.length,1);
});
test('account change while reading refuses the restore without writes or sync',async()=>{
 const f=fixture(),backup=createPantryBackup(value());f.input(backup);
 const read=f.$('restore').files[0].text;f.$('restore').files[0].text=async()=>{f.context.requestIdentity={owner:'other'};return read();};
 await f.$('restore').onchange();assert.match(f.messages.at(-1),/Account changed/);assert.deepEqual(f.raw,f.before);assert.equal(f.sync.length,0);
});
test('scoped member preferences keep the existing account guard',async()=>{
 const f=fixture(),v=value();v.profile.members=[{id:'member',name:'Synthetic',portion:1,avoid:[],advisors:[],mealPreferences:{version:1,scope:{accountId:'owner',memberId:'member'},likes:['rice'],textures:['soft'],spice:'mild'}}];
 const backup=createPantryBackup(v,{accountId:'owner'});f.context.user={id:'other'};f.input(backup);
 await f.$('restore').onchange();assert.ok(!f.messages.at(-1).includes('Backup restored'));assert.deepEqual(f.raw,f.before);assert.equal(f.sync.length,0);
});

test('the pantry byte ceiling is shared and recipe import keeps its 2MB ceiling',async()=>{
 const f=fixture();f.$('restore').files=[{size:20_000_001,text:async()=>{throw Error('Must not read oversized input');}}];
 await f.$('restore').onchange();assert.match(f.messages.at(-1),/exceeds 20 MB/);assert.deepEqual(f.raw,f.before);assert.equal(f.sync.length,0);
 f.$('restore').files=[{size:20_000_000,text:async()=>JSON.stringify(createPantryBackup(value()))}];
 await f.$('restore').onchange();assert.match(f.messages.at(-1),/Backup restored/);
 await assert.rejects(f.context.readJSON({files:[{size:2_000_001,text:async()=> '{}'}]}),/under 2 MB/);
 const v=value();v.products['1111'].ingredients='米'.repeat(6_666_667);
 Object.assign(f.context,{lots:v.inventory,profile:v.profile,products:v.products,recipes:v.recipes,selections:v.selections});
 f.$('export').onclick();assert.equal(f.downloads.length,0);assert.match(f.messages.at(-1),/exceeds 20 MB/);
});
test('same-account typed member preferences survive the complete restore',async()=>{
 const f=fixture(),v=value(),preferences={version:1,scope:{accountId:'owner',memberId:'member'},likes:['rice'],textures:['soft'],spice:'mild'};
 v.profile.members=[{id:'member',name:'Synthetic',portion:1,avoid:[],advisors:[],mealPreferences:preferences}];
 f.context.user={id:'owner'};f.input(createPantryBackup(v,{accountId:'owner'}));await f.$('restore').onchange();
 assert.match(f.messages.at(-1),/Backup restored/);assert.deepEqual(JSON.parse(f.raw.get('profile')).members[0].mealPreferences,preferences);assert.equal(f.sync.length,1);
});
