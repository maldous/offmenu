import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {test} from 'node:test';
import vm from 'node:vm';
import {rankedTopics} from '../../apps/web/assets/help.js';
import {validateRecipes} from '../../apps/web/src/model.js';
import {restorePantryBackup} from '../../apps/web/src/pantry-backup.js';

const read=path=>readFileSync(new URL('../../'+path,import.meta.url),'utf8');
const html=read('apps/web/assets/help.html'), panel=read('apps/web/assets/index.html');
const plain=markup=>markup.replace(/<[^>]+>/g,' ').replaceAll('&amp;','&').replace(/\s+/g,' ').trim();
const [[,id,aliases,article]]=[...html.matchAll(/<article id="([^"]+)" data-alias="([^"]+)">([\s\S]*?)<\/article>/g)];
const topic={id,aliases:aliases.split(';'),title:plain(article.match(/<h2[^>]*>(.*?)<\/h2>/s)[1]),
  summary:plain(article.match(/<p>(.*?)<\/p>/s)[1]),body:plain(article)};
const find=query=>rankedTopics([topic],query).map(x=>x.id);

test('the actual wrong-picker notice for a recipe-only JSON file leads to the one recovery topic',async()=>{
  const recipe={id:'synthetic-rice',title:'Synthetic rice',source:'Generated test fixture',license:'Synthetic test fixture',servings:1,
    ingredients:[{ingredient:'rice',quantity:1,unit:'g'}],instructions:['Stir.']};
  const recipeFile=[recipe],text=JSON.stringify(recipeFile);
  assert.equal(validateRecipes(recipeFile)[0].id,recipe.id,'input should be a recipe-file fixture, not arbitrary invalid JSON');
  const app=read('apps/web/src/app.js');
  const start=app.indexOf('const PANTRY_BACKUP_MAX_BYTES='),end=app.indexOf("$('recipe-import').onchange",start);
  assert(start>=0&&end>start);
  const picker={files:[{size:new Blob([text]).size,text:async()=>text}],value:'synthetic-recipes.json'};
  const exportControl={},messages=[];
  const seen={reads:0,writes:0,confirmation:0,sync:0};
  vm.runInNewContext(app.slice(start,end),{
    $(id){if(id==='restore')return picker;assert.equal(id,'export');return exportControl;},
    restorePantryBackup,t:x=>x,requestIdentity:{owner:null},user:null,lots:[{id:'retained-synthetic'}],
    confirm(){seen.confirmation++;return false;},msg:s=>messages.push(s),markDirty(){seen.sync++;},
    localStorage:{getItem(){seen.reads++;return null;},setItem(){seen.writes++;},removeItem(){seen.writes++;}}
  });
  await picker.onchange();
  assert.deepEqual(messages,['Invalid pantry backup.']);
  assert.deepEqual(seen,{reads:0,writes:0,confirmation:0,sync:0});
  assert.equal(picker.value,'');
  assert.deepEqual(find(messages[0]),['account-backup'],'Help must index the actual restore notice');
  assert.deepEqual(find('restore backup'),['account-backup']);
  assert.deepEqual(find('shopping'),[]);
});

test('the linked article uses the actual local backup and recipe picker names for that failure',()=>{
  assert.equal(id,'account-backup');
  assert.match(panel,/<a href="\/help\.html#account-backup" lang="en">Kitchen backup help \(English\)<\/a>/);
  const restore=panel.match(/<label for="restore"[^>]*>([^<]+)<\/label>/)[1];
  const imported=panel.match(/<label for="recipe-import"[^>]*>([^<]+)<\/label>/)[1];
  const exported=panel.match(/<button id="export"[^>]*>([^<]+)<\/button>/)[1];
  const notice=article.match(/<p><b>Invalid pantry backup\.<\/b>[\s\S]*?<\/p>/)?.[0];
  assert(notice,'troubleshooting must quote the actual failure');
  for(const label of [restore,exported,imported]) assert(notice.includes('<b>'+label+'</b>'),label);
});
