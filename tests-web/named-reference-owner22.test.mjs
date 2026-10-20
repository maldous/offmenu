import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveNamedReference} from '../cloud/named-reference-owner22.mjs';
import {calculateBasket} from '../public/basket-model.js';

test('null and non-object input is withheld before invoking owner dependencies', async () => {
  let calls = 0;
  const dependencies = Object.fromEntries(['readRegistry', 'admitSource', 'qualifyContext', 'clock']
    .map(name => [name, () => {calls++; throw Error('must not run');}]));
  for (const input of [null, undefined, true, false, 0, 42, 'invalid', []]) {
    const result = await resolveNamedReference(input, dependencies);
    assert.equal(result.status, 'withheld');
    assert.equal(result.reason, 'invalid-own-input');
    assert.deepEqual(result.metrics, {});
    assert.equal(result.referenceProfile, null);
  }
  assert.equal(calls, 0);
});
const copy = x => structuredClone(x);

function fixture() {
  const cohort={id:'synthetic-cohort',lifeStage:'synthetic-stage',ageBand:'synthetic-age-band',
    sexIfApplicable:'synthetic-source-not-applicable',pregnancyLactationIfApplicable:'synthetic-source-not-applicable'};
  const nutrient=(value,unit)=>({value,unit,definition:'synthetic-definition',sourceId:'synthetic-composition',
    basisAmount:100,basisUnit:'g',state:'cooked',status:'recipe-calculated'});
  const calculation=calculateBasket({id:'synthetic-basket',version:1,track:'synthetic-model',purpose:'synthetic-analysis',
    state:'cooked',population:cohort.lifeStage,referencePeriod:'synthetic-period',personDays:2,
    lines:[{id:'synthetic-line',edibleG:200,state:'cooked',nutrients:{protein_g:nutrient(10,'g'),energy_kcal:nutrient(100,'kcal')}}]},
    [{metric_id:'protein_g',unit:'g'},{metric_id:'energy_kcal',unit:'kcal'}]);
  const selection={system:'synthetic-system',profileId:'synthetic-profile',version:'v1',issuerId:'synthetic-issuer',
    referenceType:'synthetic-reference-type',cohortId:cohort.id};
  const request={selection,calculation,context:{accountScope:'synthetic-account',audience:'private',action:'derive',
    cohort:copy(cohort),policyId:'synthetic-policy',policyVersion:'p1'}};
  const registry={system:selection.system,id:selection.profileId,version:selection.version,name:'Synthetic target, no intake guidance',
    sourceId:'synthetic-target-source',basis:'person-day',referenceType:selection.referenceType,cohort:copy(cohort),
    issuer:{id:selection.issuerId,documentId:'synthetic-document',documentVersion:'doc1',documentSha256:'a'.repeat(64),
      documentUrl:'https://example.invalid/synthetic-issuer'},
    rights:{sourceId:'synthetic-target-source',revision:'r1',evidenceUrl:'https://example.invalid/synthetic-rights',
      status:'active',actions:['derive'],audiences:['private']},
    contextPolicy:{id:'synthetic-policy',version:'p1',tracks:['synthetic-model'],purposes:['synthetic-analysis'],
      states:['cooked'],referencePeriods:['synthetic-period']},metricCells:{}};
  for (const [id,value,unit] of [['protein_g',50,'g'],['energy_kcal',1000,'kcal']]) registry.metricCells[id]={
    metricId:id,amount:value,unit,componentDefinition:'synthetic-definition',status:'source-issued',issuerId:selection.issuerId,
    documentVersion:'doc1',sourceSha256:'a'.repeat(64),sourceUrl:registry.issuer.documentUrl,sourceId:registry.sourceId,
    rightsRevision:'r1',referenceType:selection.referenceType,cohortId:cohort.id,basis:'person-day',
    tableId:'synthetic-table',rowId:id,columnId:'synthetic-column',cellId:'synthetic-cell:'+id};
  const decision=(status,binding)=>({status,decisionId:'synthetic-'+status,revision:'decision1',binding,
    checkedAt:1000,validUntil:2000});
  const dependencies={clock:()=>1000,readRegistry:()=>registry,
    admitSource:binding=>decision('admitted',binding),qualifyContext:binding=>decision('compatible',binding)};
  return {request,registry,dependencies,decision};
}

test('explicit synthetic owner-qualified issuer cells yield descriptive percentages and helper contract',async()=>{
  const f=fixture(), r=await resolveNamedReference(f.request,f.dependencies);
  assert.equal(r.status,'qualified');assert.equal(r.metrics.protein_g.denominator,50);
  assert.equal(r.metrics.protein_g.percentReference,20);assert.equal(r.metrics.energy_kcal.percentReference,10);
  assert.equal(r.metrics.protein_g.rankEligible,false);
  assert.deepEqual(r.referenceProfile.metrics.protein_g,{value:50,unit:'g',definition:'synthetic-definition',status:'complete',
    referenceType:'synthetic-reference-type',issuerCell:f.registry.metricCells.protein_g});
  assert.equal(r.referenceProfile.lifeStage,f.request.calculation.population);
  assert.equal(r.referenceProfile.basis,'person-day');
});

test('no registry or owner gates: client declarations/admission flags cannot select a target',async()=>{
  const f=fixture();f.request.referenceProfile=f.registry;f.request.admitted=true;f.request.context.compatible=true;
  assert.equal((await resolveNamedReference(f.request)).referenceProfile,null);
  f.dependencies.readRegistry=()=>null;
  const r=await resolveNamedReference(f.request,f.dependencies);
  assert.equal(r.status,'withheld');assert.equal(r.metrics.protein_g.denominator,null);
  f.dependencies.readRegistry=()=>({kind:'sourceAssertion',sourceId:'dietary-guidelines',
    data:{referenceType:'national-dietary-guideline-directory-entry',reviewStatus:'directory-entry-observed'}});
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).referenceProfile,null);
});

test('finite positive target gate is per metric; unknown does not become zero',async()=>{
  for (const value of [null,0,-1,NaN,Infinity,'50']) {
    const f=fixture();f.registry.metricCells.protein_g.amount=value;
    const r=await resolveNamedReference(f.request,f.dependencies);
    assert.equal(r.status,'partial');assert.equal(r.metrics.protein_g.denominator,null);
    assert.equal(r.metrics.protein_g.percentReference,null);assert.equal(r.metrics.energy_kcal.status,'qualified');
  }
  const f=fixture();f.request.calculation.metrics.protein_g.total=0;f.request.calculation.metrics.protein_g.perPersonDay=0;
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).metrics.protein_g.percentReference,0);
});

test('quarantined cells do not spend the capture budget of valid cells in either order',async()=>{
  for (const failure of ['characters','nodes','cycle']) {
    for (const invalidFirst of [true,false]) {
      const f=fixture(), invalid=f.registry.metricCells.protein_g, valid=f.registry.metricCells.energy_kcal;
      if (failure==='characters') invalid.note='x'.repeat(250001);
      if (failure==='nodes') invalid.note=Array.from({length:21},()=>Array(1000).fill(null));
      if (failure==='cycle') {
        invalid.note='x'.repeat(240000);
        invalid.self=invalid;
        valid.note='y'.repeat(20000);
      }
      f.registry.metricCells=Object.fromEntries(invalidFirst
        ? [['protein_g',invalid],['energy_kcal',valid]] : [['energy_kcal',valid],['protein_g',invalid]]);
      let admitted;
      f.dependencies.admitSource=b=>{admitted=b;return f.decision('admitted',b);};
      const r=await resolveNamedReference(f.request,f.dependencies), label=`${failure}, invalidFirst=${invalidFirst}`;
      assert.equal(r.status,'partial',label);
      assert.equal(r.metrics.protein_g.denominator,null,label);
      assert.equal(r.metrics.protein_g.reason,'missing-or-invalid-issuer-cell',label);
      assert.equal(r.metrics.energy_kcal.status,'qualified',label);
      assert.equal(r.metrics.energy_kcal.percentReference,10,label);
      assert.deepEqual(admitted.registry.metricCells.protein_g,{invalidCellData:true},label);
      assert.equal(admitted.registry.metricCells.energy_kcal.amount,1000,label);
    }
  }
});

test('successful cells still share the aggregate registry capture budget',async()=>{
  const f=fixture();
  f.registry.metricCells.protein_g.note='x'.repeat(130000);
  f.registry.metricCells.energy_kcal.note='y'.repeat(130000);
  let admitted;
  f.dependencies.admitSource=b=>{admitted=b;return f.decision('admitted',b);};
  const r=await resolveNamedReference(f.request,f.dependencies);
  assert.equal(r.status,'partial');
  assert.equal(r.metrics.protein_g.status,'qualified');
  assert.equal(r.metrics.energy_kcal.denominator,null);
  assert.deepEqual(admitted.registry.metricCells.energy_kcal,{invalidCellData:true});
  assert.equal(admitted.registry.metricCells.protein_g.note.length,130000);
});

test('issuer/version/cell/reference-type/cohort/definition/unit/rights mismatches withhold affected cell',async()=>{
  for (const [key,value] of [['issuerId','other'],['documentVersion','other'],['sourceSha256','b'.repeat(64)],
    ['sourceUrl','https://example.invalid/other'],['sourceId','other'],['rightsRevision','other'],['referenceType','other'],
    ['metricId','other'],['cohortId','other'],['basis','per100g'],['componentDefinition','other'],['unit','mg'],['cellId',null],['conflict',true]]) {
    const f=fixture();f.registry.metricCells.protein_g[key]=value;
    const r=await resolveNamedReference(f.request,f.dependencies);
    assert.equal(r.metrics.protein_g.denominator,null,key);assert.equal(r.metrics.energy_kcal.status,'qualified',key);
  }
});

test('exact track/purpose/state/period/personDays/cohort and profile selector required',async()=>{
  for (const mutate of [r=>r.calculation.track='other',r=>r.calculation.purpose='other',r=>r.calculation.state='raw',
    r=>r.calculation.referencePeriod='other',r=>r.calculation.personDays=null,r=>r.calculation.personDays=0,
    r=>r.calculation.population='other',r=>r.context.cohort.ageBand='other',r=>r.context.policyVersion='other',
    r=>r.selection.version='other',r=>r.selection.issuerId='other',r=>r.selection.referenceType='other']) {
    const f=fixture();mutate(f.request);
    assert.equal((await resolveNamedReference(f.request,f.dependencies)).status,'withheld');
  }
  const f=fixture();f.dependencies.admitSource=b=>f.decision('admitted',{...b,request:{...b.request,
    calculation:{...b.request.calculation,personDays:1}}});
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).reason,'source-not-admitted');
});

test('admission/context decisions bind all captured source/context data and require fresh explicit windows',async()=>{
  for (const mutate of [d=>d.status='supported',d=>d.validUntil=1000,d=>d.checkedAt=1001,
    d=>d.binding.request.context.accountScope='other',d=>d.binding.registry.metricCells.protein_g.amount=999]) {
    const f=fixture();f.dependencies.admitSource=b=>{const d=f.decision('admitted',b);mutate(d);return d;};
    assert.equal((await resolveNamedReference(f.request,f.dependencies)).reason,'source-not-admitted');
  }
  const f=fixture();f.dependencies.qualifyContext=b=>({...f.decision('compatible',b),binding:{...b,evaluatedAt:999}});
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).reason,'context-not-qualified');
  const denied=fixture();let calls=0;
  denied.dependencies.admitSource=b=>denied.decision('denied',b);
  denied.dependencies.qualifyContext=()=>{calls++;throw Error('Do not forward unadmitted cells');};
  assert.equal((await resolveNamedReference(denied.request,denied.dependencies)).reason,'source-not-admitted');
  assert.equal(calls,0);
  const expired=fixture();let time=1000;
  expired.dependencies.clock=()=>time;
  expired.dependencies.qualifyContext=b=>{time=2001;return expired.decision('compatible',b);};
  assert.equal((await resolveNamedReference(expired.request,expired.dependencies)).reason,'source-not-admitted');
});

test('own data: accessors/inherited authority unsupported without invoking hooks; cell getter isolated',async()=>{
  const f=fixture();let calls=0;
  Object.defineProperty(f.request,'selection',{enumerable:true,get(){calls++;return {};}});
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).reason,'invalid-own-input');assert.equal(calls,0);
  const g=fixture();g.dependencies.admitSource=b=>Object.create(g.decision('admitted',b));
  assert.equal((await resolveNamedReference(g.request,g.dependencies)).status,'withheld');
  const h=fixture();Object.defineProperty(h.registry.metricCells,'protein_g',{enumerable:true,get(){calls++;return {};}});
  const r=await resolveNamedReference(h.request,h.dependencies);assert.equal(r.status,'partial');assert.equal(calls,0);
});

test('async mutation capture and detached callback/result ownership',async()=>{
  const f=fixture(), original=copy(f.registry);let release;
  f.dependencies.admitSource=async b=>{await new Promise(resolve=>{release=resolve;});return f.decision('admitted',b);};
  const run=resolveNamedReference(f.request,f.dependencies);
  await new Promise(resolve=>setImmediate(resolve));
  f.request.calculation.personDays=99;f.registry.metricCells.protein_g.amount=999;release();
  const r=await run;assert.equal(r.metrics.protein_g.percentReference,20);
  assert.equal(r.binding.registry.metricCells.protein_g.amount,original.metricCells.protein_g.amount);
  r.referenceProfile.metrics.protein_g.issuerCell.amount=777;
  assert.equal(f.registry.metricCells.protein_g.amount,999);
  assert.equal(r.metrics.protein_g.issuerCell.amount,50);
  const g=fixture();g.dependencies.readRegistry=(s,x)=>{s.version='mutated';x.accountScope='mutated';return g.registry;};
  assert.equal((await resolveNamedReference(g.request,g.dependencies)).status,'qualified');
});

test('partial numerator, missing definitions, stale person-day subtotal and clock errors stay withheld',async()=>{
  for (const mutate of [m=>m.status='partial',m=>m.total=null,m=>m.definitions=[],m=>m.perPersonDay=999]) {
    const f=fixture();mutate(f.request.calculation.metrics.protein_g);
    const r=await resolveNamedReference(f.request,f.dependencies);assert.equal(r.metrics.protein_g.percentReference,null);
  }
  const f=fixture();f.dependencies.clock=()=>NaN;assert.equal((await resolveNamedReference(f.request,f.dependencies)).reason,'unknown-clock');
});

test('rights/policy lists do not grant permission by substring; dependency failures do not default',async()=>{
  for (const mutate of [p=>p.rights.actions='derive',p=>p.rights.audiences=['public'],p=>p.rights.status='withdrawn',
    p=>p.contextPolicy.tracks='synthetic-model',p=>p.issuer.documentSha256=null,p=>p.issuer.documentUrl='https://']) {
    const f=fixture();mutate(f.registry);assert.equal((await resolveNamedReference(f.request,f.dependencies)).status,'withheld');
  }
  const f=fixture();f.dependencies.qualifyContext=()=>{throw Error('Unavailable owner policy');};
  assert.equal((await resolveNamedReference(f.request,f.dependencies)).referenceProfile,null);
});
