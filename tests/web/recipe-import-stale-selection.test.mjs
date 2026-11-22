import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const src=readFileSync(new URL('../../apps/web/src/app.js',import.meta.url),'utf8');
const code=src.slice(src.indexOf('let recipeImportGeneration=0;'),src.indexOf("\n};",src.indexOf('let recipeImportGeneration=0;'))+3);
const open=src.match(/if\(!\$\('account-dialog'\)\.open\)\{recipeImportGeneration\+\+;\$\('recipe-import'\)\.value='';\$\('account-dialog'\)\.showModal\(\);\}/)[0];
function fixture(){
 let requestIdentity={},recipes=[];
 const out=[], storage=[], close=[];
 const dialog={open:true,showModal(){this.open=true;},addEventListener(type,fn){close.push(fn);}};
 const field={value:'',files:[]}; const $=key=>key==='account-dialog'?dialog:field;
 const readJSON=async input=>JSON.parse(await input.files[0].text());
 const clearAccountFileErrors=()=>{};
 const showAccountFileError=(id,error)=>out.push(error.name);
 const validateRecipes=v=>v, RECIPES='mock',localStorage={setItem(k,v){storage.push(JSON.parse(v));}};
 const markDirty=()=>{},findMeals=()=>{},msg=m=>out.push(m),t=x=>x;
 const controls=eval(code+'\n({open:()=>{'+open+'}})');
 function select(name){
  let resolve;const p=new Promise(r=>resolve=r);
  field.value=name;field.files=[{text:()=>p}];
  return {resolve,done:field.onchange()};
 }
 return {select,storage,out,field,close(){dialog.open=false;}, notify(){close.forEach(fn=>fn());},open:controls.open,changeScope(){requestIdentity={};}};
}
test('current selection writes once and clears picker',async()=>{
 const f=fixture(), x=f.select('current');x.resolve('[{"id":"current"}]');await x.done;
 assert.deepEqual(f.storage,[[{id:'current'}]]);assert.equal(f.field.value,'');assert.deepEqual(f.out,['Recipes imported.']);
});
test('close and reopen before queued close event denies old valid read, preserves new selection',async()=>{
 const f=fixture(), x=f.select('old');f.close();f.open();const y=f.select('new');f.notify();
 x.resolve('[{"id":"old"}]');await x.done;assert.deepEqual(f.storage,[]);assert.equal(f.field.value,'new');
 y.resolve('[{"id":"new"}]');await y.done;assert.deepEqual(f.storage,[[{id:'new'}]]);
});
test('reselection suppresses stale error without clearing active picker',async()=>{
 const f=fixture(), x=f.select('old'), y=f.select('new');x.resolve('{');await x.done;
 assert.deepEqual(f.out,[]);assert.equal(f.field.value,'new');y.resolve('{');await y.done;
 assert.deepEqual(f.out,['SyntaxError']);assert.equal(f.field.value,'');
});
test('different actor prevents late old-scope mutation and status',async()=>{
 const f=fixture(), x=f.select('old');f.changeScope();x.resolve('[{"id":"old"}]');await x.done;
 assert.deepEqual(f.storage,[]);assert.deepEqual(f.out,[]);
});
