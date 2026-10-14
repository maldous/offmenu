import test from 'node:test';
import assert from 'node:assert/strict';
import {execFileSync} from 'node:child_process';
const env=Object.fromEntries(Object.entries(process.env).filter(([k])=>!k.startsWith('GIT_')));
const pin='b207e6e1ae9b59c5fe5bf283465fd8209b7cd2ec';
const blob=(p,ref=pin)=>execFileSync('git',['show',`${ref}:${p}`],{env,encoding:'utf8'});
const uri=s=>'data:text/javascript;base64,'+Buffer.from(s).toString('base64');
const evidence=uri(blob('public/evidence-model.js'));
const adapter=uri(blob('public/recall-binding-owner26.mjs').replace("'./evidence-model.js'",JSON.stringify(evidence)));
let fixture=blob('tests-web/recall-binding-owner26.test.mjs').split("test('consumer entrypoint")[0];
fixture=fixture.replace("'../public/recall-binding-owner26.mjs'",JSON.stringify(adapter))
 .replace("new URL('../public/evidence-model.js', import.meta.url).href",JSON.stringify(evidence));
const {consume,run,envelope,lot,asOf}=await import(uri(fixture+'\nexport {consume,run,envelope,lot,asOf};'));
test('frozen inputs, output mutation and subsequent source mutation preserve snapshot isolation',()=>{
 const deepFreeze=o=>{if(o&&typeof o==='object'){Object.values(o).forEach(deepFreeze);Object.freeze(o);}return o;};
 const e=envelope(),before=structuredClone(e);deepFreeze(e);deepFreeze(lot);
 const result=run(e);assert.equal(result.decision,'recall-match-review');
 result.results[0].evidence.declaredAction.regulator='changed';assert.deepEqual(e,before);
 const mutable=envelope(),r=run(mutable);mutable.notice.provenance.recordId='changed';
 assert.equal(r.results[0].evidence.provenance.recordId,'record');
});
test('exclusive policy expiry and absent/changed product versions do not become permission',()=>{
 const e=envelope();e.policy.expiresAt=asOf;assert.equal(run(e).decision,'needs-review');
 for(const productVersion of [undefined,null,'v2'])assert.equal(run(envelope(),{...lot,productVersion}).decision,'needs-review');
 const corrected=envelope();corrected.recordVersion='r2';assert.equal(run(corrected).decision,'needs-review');
});
test('inspection action and missing lot remain unresolved despite accepted display grant',()=>{
 const e=envelope();e.notice.action.type='inspection';assert.equal(run(e).decision,'needs-review');
 assert.equal(run(envelope(),{...lot,lotCode:undefined}).decision,'needs-review');
 const empty=consume({lots:[lot],notices:[],asOf})[0];assert.equal(empty.safety,'unknown');assert.equal(empty.exhaustiveCoverage,false);
});
test('known match plus unresolved second source retains both outcomes without safety permission',()=>{
 const e=envelope(),unknown=envelope();unknown.notice.id='second';delete unknown.review;
 const r=consume({lots:[lot],notices:[e,unknown],asOf})[0];
 assert.equal(r.decision,'recall-match-review');assert.equal(r.results[1].decision,'needs-review');
 assert.equal(r.safety,'unknown');assert.equal(r.automaticSelection,false);
});
