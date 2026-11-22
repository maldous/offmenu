import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import {serveBatch} from '../../apps/web/src/cooking-model.js';
import {setLanguage,t} from '../../apps/web/src/i18n.js';
const source=readFileSync(new URL('../../apps/web/src/journey-ui.js',import.meta.url),'utf8');
const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
const extract=(a,b)=>source.slice(source.indexOf(a),source.indexOf(b,source.indexOf(a)));

test('equivalent tenths keep the intended amount and invalid formats never commit',()=>{
 const portions='Enter portions in tenths, for example 1.5.';
 assert.match(html,/aria-describedby="serve-portion-hint serve-notice"><small id="serve-portion-hint"/);
 for(const [locale,valid] of [['en','1.50'],['ar','١٫٥٠']]){
  setLanguage(locale);
  const batch={id:'synthetic',title:'Fixture',totals:{},remaining:2,servings:2,events:[],undone:false};
  const profile={batches:[batch],history:[]};
  const stock=[{cookBatchId:'synthetic',quantity:2}];
  const fields=Object.fromEntries(['serve-portions','serve-date','serve-member','serve-remainder','serve-completion','serve-form','serve-dialog','serve-notice'].map(id=>[id,{value:'',close(){}}]));
  fields['serve-date'].value='2026-11-22';
  fields['serve-remainder'].value='unspecified';
  const writes=[];
  const context={t,$:id=>fields[id],getData:()=>({profile,inventory:stock}),selectedBatch:batch,serveBatch:args=>serveBatch({...args,eventId:'synthetic-event'}),
   commit:x=>writes.push(x),setLocalizedText:(e,v)=>{e.textContent=v},renderBatches(){}};
  runInNewContext(extract('function servingPortions','function openServe')+extract("$('serve-form').onsubmit=", 'function renderBatches'),context);
  const submit=value=>{fields['serve-portions'].value=value;fields['serve-form'].onsubmit({preventDefault(){}});};
  for(const input of ['1,200','1.200','1.55','١٬٢٠٠','١٫٥٥','1e1','2.10']){
   submit(input);assert.equal(writes.length,0);assert.equal(profile.batches[0].remaining,2);assert.equal(profile.history.length,0);
  }
  submit('1.55');assert.equal(fields['serve-notice'].textContent,t(portions));
  submit(valid);assert.equal(writes.length,1,fields['serve-notice'].textContent);assert.equal(profile.batches[0].remaining,.5);
  assert.equal(writes[0].inventory[0].quantity,.5);
  assert.equal(profile.history.length,1);
 }
 setLanguage('en');
});
