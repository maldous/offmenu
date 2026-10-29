import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createCommonCorpus} from '/tmp/offmenu-dk-m002-922-20261017/public/common-corpus-locale.js';
const root='/home/user/Documents/Codex/2026-10-17/offmenu-dk-m002-composition';
const graphs=JSON.parse(fs.readFileSync(root+'/synthetic-caller-input.json','utf8'));
const results=[];
for(const [index,graph] of graphs.entries()){
 const adapter=await createCommonCorpus(graph);
 const q=graph.assertions.find(a=>a.propertyId.endsWith(':metricValue')).value;
 const shown=adapter.displayValue(q,'en');
 assert.match(shown,/Unknown/);assert.ok(!shown.includes('1.25'));
 assert.equal(q.sourceValue,1.25);assert.equal(q.value,null);assert.ok(!Object.hasOwn(q,'basis'));
 results.push({index,display:shown,sourceValueNotUsedAsQualifiedAmount:true,passed:true});
}
fs.writeFileSync(root+'/caller-results.json',JSON.stringify({status:'PASS',node:process.version,groups:results.length,scope:'Actual pinned createCommonCorpus/displayValue invoked on synthetic graph; no browser, hosted binding or UI runtime activation',results},null,2)+'\n');
console.log(JSON.stringify({status:'PASS',groups:results.length}));
