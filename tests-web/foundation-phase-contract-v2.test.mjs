import test from 'node:test';import assert from 'node:assert/strict';
import {FOUNDATION_CONTRACT,assessFoundation,summarizeFoundation}from'../corpus/foundation-phase-contract-v2.mjs';
const registry='a'.repeat(64),review='b'.repeat(64);
const subject={sourceId:'generated',releaseId:'generated-1',recordId:'generated:1',sourceObservationSha256:'c'.repeat(64),sourceDocumentSha256:'d'.repeat(64),inputDatabaseSha256:'e'.repeat(64),sourceQualificationSha256:'f'.repeat(64)};
const evidence=kind=>[{kind,pointer:'/generated/field',sourceBinding:structuredClone(subject)}];
const stamp=()=>({state:'reviewed',registrySha256:registry,independentReviewSha256:review,evidence:evidence('source-field')});
function fixture(){
  const assertions={fresh:'source-declared-fresh',homogenized:'homogenized',esl:'source-declared-esl'};
  const typeRelation={typeKey:'milk-products',canonicalEnglishLabel:'Milk products',conceptId:'generated:milk-products',relationshipId:'generated:milk-is-a-milk-product',relationshipKind:'is-a',subjectConceptId:'generated:milk',registrySha256:'2'.repeat(64),independentReviewSha256:'3'.repeat(64)};
  const policy={schema:FOUNDATION_CONTRACT,registrySha256:registry,independentReviewSha256:review,definitions:{milk:{classification:'ingredient',canonicalEnglishLabel:'Milk',conceptId:'generated:milk',typeKey:'milk-products',typeRelation,parameters:{
    baseMaterial:{kind:'concept-reference',values:['generated:milk-base']},
    processing:{kind:'assertion-list',assertions,nonexclusiveAssertionGroups:[Object.keys(assertions)]},
    fatPercentage:{kind:'number',minimum:0,maximum:100}}}}};
  const known=value=>({state:'known',value,independentReviewSha256:review,evidence:evidence('source-field')});
  const candidate={barcode:'0036000291452',identity:{namespace:'barcode',lexicalValue:'0036000291452',nativeRecordId:'generated-native',stageRecordId:'generated-stage',stageRecordWireSha256:'1'.repeat(64),sourceBinding:structuredClone(subject)},classification:{...stamp(),value:'ingredient'},base:{...stamp(),canonicalEnglishKey:'milk',canonicalEnglishLabel:'Milk',conceptId:'generated:milk',typeKey:'milk-products'},type:{state:'reviewed',...structuredClone(typeRelation),evidence:evidence('reviewed-type-rule')},parameters:{baseMaterial:known({conceptId:'generated:milk-base'}),processing:known(Object.entries(assertions).map(([assertionId,value])=>({assertionId,value,evidence:evidence('source-field')}))),fatPercentage:{state:'unknown',reason:'not-provided-in-qualified-representation',evidence:evidence('qualified-representation-omission')}}};
  return {candidate,policy};
}
test('typed base and all three nonexclusive processing assertions survive with unknown fat',()=>{
  const {candidate,policy}=fixture(),before=structuredClone({candidate,policy}),r=assessFoundation(candidate,policy);
  assert.equal(r.foundationComplete,true);assert.deepEqual(r.parameters.known,['baseMaterial','processing']);assert.deepEqual(r.parameters.unknown,['fatPercentage']);assert.deepEqual({candidate,policy},before);assert.equal(candidate.parameters.processing.value.length,3);
  for(const k of ['goldAdmitted','publicationAccepted','fullProductComplete','recipeNutritionJoinsAccepted'])assert.equal(r[k],false);
});
test('a known concept requires the exact selected object and independently selected concept ID',()=>{
  for(const v of ['generated:milk-base',{conceptId:'unreviewed'},{conceptId:'generated:milk-base',other:true},{}]){
    const {candidate,policy}=fixture();candidate.parameters.baseMaterial.value=v;assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
});
test('processing never chooses a winner or accepts unreviewed, duplicate, incompatible or altered assertions',()=>{
  for(const change of [r=>r.push(structuredClone(r[0])),r=>r[0].value='other',r=>r[0].assertionId='unreviewed',r=>r[0].extra=true,r=>r.splice(0,r.length)]){
    const {candidate,policy}=fixture();change(candidate.parameters.processing.value);assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
  const {candidate,policy}=fixture();policy.definitions.milk.parameters.processing.nonexclusiveAssertionGroups=[['fresh'],['homogenized'],['esl']];assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
});
test('every nested processing evidence item must retain the selected source subject and field provenance',()=>{
  for(const key of Object.keys(subject)){
    const {candidate,policy}=fixture();candidate.parameters.processing.value[1].evidence[0].sourceBinding[key]='other';assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
  for(const change of [r=>r.evidence=[],r=>r.evidence[0].kind='qualified-representation-omission']){
    const {candidate,policy}=fixture();change(candidate.parameters.processing.value[1]);assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
});
test('typed successor retains exact identity, unknown and version boundaries without a Gold count',()=>{
  const {candidate,policy}=fixture(),r=assessFoundation(candidate,policy);assert.equal(summarizeFoundation([r]).foundationComplete,1);assert.equal(summarizeFoundation([r]).goldAdmitted,0);
  candidate.identity.lexicalValue='036000291452';assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  assert.throws(()=>assessFoundation(candidate,{...policy,schema:'offmenu-barcode-foundation-phase/1'}));assert.throws(()=>summarizeFoundation([{...r,schema:'offmenu-barcode-foundation-phase/1'}]));
});
test('entity kind cannot substitute for an independently reviewed meaningful type/category relation',()=>{
  for(const change of [
    (c,p)=>{delete c.type;},
    (c,p)=>{delete p.definitions.milk.typeRelation;},
    (c,p)=>{c.type.typeKey=p.definitions.milk.typeKey=p.definitions.milk.typeRelation.typeKey=c.base.typeKey='ingredient';},
    (c,p)=>{c.type.subjectConceptId='generated:other-base';},
    (c,p)=>{c.type.evidence[0].sourceBinding.recordId='different-record';},
    (c,p)=>{c.type.evidence[0].kind='source-field';},
  ]){
    const {candidate,policy}=fixture();change(candidate,policy);const r=assessFoundation(candidate,policy);
    assert.equal(r.foundationComplete,false);assert.ok(r.reasons.includes('meaningful-type-category-relation-unqualified'));
  }
});
