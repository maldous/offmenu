import test from 'node:test';
import assert from 'node:assert/strict';
import {validateHealthImport,HEALTH_IMPORT_SCHEMA} from '../../apps/web/server/health-import-owner28.mjs';
// SYNTHETIC ONLY: no native or vendor export fixture has been qualified.
const ctx={owner:'a',memberId:'m',revision:2,now:Date.parse('2026-10-15T00:00:00Z'),consent:{id:'grant:1',status:'active',owner:'a',memberId:'m',expiresAt:'2026-11-01T00:00:00Z',purposes:['health-import'],sources:['vendor:1'],types:['weight','steps']}};
const envelope={schemaVersion:HEALTH_IMPORT_SCHEMA,owner:'a',memberId:'m',revision:2,source:{kind:'manual-export',sourceId:'vendor:1',exportId:'export:1'},records:[{id:'r',sourceRecordId:'native:r',type:'weight',unit:'kg',value:80,observedAt:'2026-10-14T00:00:00Z'}]};
const run=(e=envelope,c=ctx)=>validateHealthImport(JSON.stringify(e),c);
test('missing or null trusted context blocks without throwing or returning records',()=>{
  const serialized=JSON.stringify(envelope);
  const blocked={status:'blocked',reason:'Trusted account context required',records:[],rejected:[],writes:false};
  assert.deepEqual(validateHealthImport(serialized),blocked);
  for(const context of [undefined,null,{}])assert.deepEqual(validateHealthImport(serialized,context),blocked);
});
test('synthetic private preview preserves identities and does not write or mutate',()=>{const before=structuredClone(envelope),r=run();assert.equal(r.status,'preview');assert.equal(r.records[0].sourceRecordId,'native:r');assert.equal(r.records[0].status,'imported-unverified');assert.equal(r.writes,false);assert.deepEqual(envelope,before);});
test('synthetic account member revision and current consent fail closed',()=>{for(const patch of [{owner:'b'},{memberId:'other'},{revision:3},{consent:{...ctx.consent,status:'revoked'}},{consent:{...ctx.consent,expiresAt:'2026-10-01T00:00:00Z'}}])assert.equal(run(envelope,{...ctx,...patch}).status,'blocked');});
test('native sources and browser OAuth are not portable export authority',()=>{for(const kind of ['health-connect','healthkit','browser-oauth'])assert.equal(run({...envelope,source:{...envelope.source,kind}}).status,'blocked');});
test('unknown records, units, null values, impossible dates and duplicates need review',()=>{for(const patch of [{type:'clinicalDiagnosis'},{unit:'lb'},{value:null},{observedAt:'2026-02-30T00:00:00Z'},{observedAt:'2027-01-01T00:00:00Z'}]){const r=run({...envelope,records:[{...envelope.records[0],...patch}]});assert.equal(r.status,'needs-review');assert.equal(r.records.length,0);assert.deepEqual(Object.keys(r.rejected[0]),['index','reason']);}assert.equal(run({...envelope,records:[envelope.records[0],envelope.records[0]]}).rejected.length,1);});
test('bounded JSON strict fields and version; zero preserved as observed zero',()=>{assert.equal(validateHealthImport('x'.repeat(65537),ctx).status,'blocked');assert.equal(run({...envelope,schemaVersion:'unknown'}).status,'blocked');assert.equal(run({...envelope,token:'secret'}).status,'blocked');assert.equal(run({...envelope,records:[{...envelope.records[0],value:0}]}).records[0].value,0);});
