import test from'node:test';import assert from'node:assert/strict';
import {assessProducerProjection}from'../corpus/foundation-projection-adapter.mjs';
const hash=x=>x.repeat(64),review=hash('b'),registry=hash('c'),types=hash('d'),receipt=hash('e');
const R2='f4a0068bf79cd93c5e198a3ae94cc1a0ef11d14c9843bdb1a47bfa00ae5e7efd';
function fixture(){
  const binding={sourceId:'off',releaseId:'generated',recordId:'generated-native',sourceObservationSha256:hash('1'),sourceDocumentSha256:hash('2'),inputDatabaseSha256:hash('3'),sourceQualificationSha256:hash('4')};
  const typeRelation={typeKey:'milk-products',canonicalEnglishLabel:'Milk products',conceptId:'generated:milk-products',relationshipId:'generated:milk-is-milk-products',relationshipKind:'is-a',subjectConceptId:'generated:milk',registrySha256:types,independentReviewSha256:review};
  const assertions=Object.fromEntries(['fresh','homogenized','esl'].map(x=>['generated:'+x,{ruleId:'generated:milk',assertionId:'generated:'+x,typeKey:'processing',value:x,evidenceCondition:{field:'name',sourceQuoteOrMember:'GENERATED MILK'}}]));
  const variants=Object.values(assertions).map(c=>({...structuredClone(c),semanticAccepted:true}));
  const parameters={baseMaterial:{kind:'concept-reference',values:['generated:milk-base']},processing:{kind:'assertion-list',assertions:Object.fromEntries(variants.map(x=>[x.assertionId,x.value])),nonexclusiveAssertionGroups:[variants.map(x=>x.assertionId)]},fatClass:{kind:'string',values:[]}};
  const policy={schema:'offmenu-barcode-foundation-phase/2',registrySha256:registry,independentReviewSha256:review,policyReceiptSha256:receipt,typeRelationReceiptSha256:types,sourceQualifications:{off:{releaseId:'generated',qualificationSha256:hash('4')}},ruleScopes:{'generated:milk':{sourceId:'off',releaseId:'generated',sourceQualificationSha256:hash('4')}},assertionCatalog:assertions,definitions:{milk:{classification:'ingredient',canonicalEnglishLabel:'Milk',conceptId:'generated:milk',typeKey:'milk-products',typeRelation,parameters,allowedRuleIds:['generated:milk']}}};
  const row={schema:'offmenu-exact-reviewed-meaningful-type-producer-projection/1',stageRecordId:'generated-stage',stageRecordWireSha256:hash('5'),sourceBinding:binding,nativeRecordId:'generated-native',barcodeIdentity:{exactSourceKeys:['0036000291452'],qualifiedGtinKeys:['0036000291452']},applicationEligibility:{state:'reviewed',entityKind:'ingredient',reviewReceiptSha256:R2},englishBase:{conceptId:'generated:milk',canonicalEnglishKey:'milk',canonicalEnglishLabel:'Milk'},meaningfulTypeRelation:{state:'reviewed-declarative-exact-source-target-linked',relation:{baseConceptId:'generated:milk',canonicalEnglishBaseKey:'milk',canonicalEnglishBaseLabel:'Milk',typeId:'generated:milk-products',meaningfulTypeKey:'milk-products',relation:'is-a-food-type'},relationReceiptSha256:types,correctedDeclarativePolicyReceiptSha256:receipt,matchedActualAcceptedR2RuleIds:['generated:milk']},parametersByAxis:{baseMaterial:{state:'unknown'},processing:{state:'known',acceptedAssertions:variants},fatClass:{state:'unknown'}},rawAcceptedVariantAssertions:variants,sourceAttributeClaims:[],sourceEvidenceRefs:[{ruleId:'generated:milk',sourceBinding:structuredClone(binding),fieldEvidence:[{field:'name',sourcePointer:'/data/name',valueSha256:hash('6')}]}]};
  return{row,policy,barcode:'0036000291452'};
}
test('closed source projection preserves three processing facts and scoped unknowns without publication or mutation',()=>{
  const {row,policy,barcode}=fixture(),before=structuredClone({row,policy}),r=assessProducerProjection(row,barcode,policy);
  assert.equal(r.assessment.foundationComplete,true);assert.equal(r.candidate.parameters.processing.value.length,3);
  assert.deepEqual(r.assessment.parameters.unknown,['baseMaterial','fatClass']);assert.equal(r.acceptedAssertions.length,3);
  assert.deepEqual({row,policy},before);assert.equal(r.publicationAccepted,false);assert.equal(r.goldAdmitted,false);
});
test('every source subject field and stage wire is checked, with no barcode alias propagation',()=>{
  for(const key of Object.keys(fixture().row.sourceBinding)){
    const {row,policy,barcode}=fixture();row.sourceBinding[key]='different';assert.throws(()=>assessProducerProjection(row,barcode,policy));
  }
  const {row,policy}=fixture();row.stageRecordWireSha256='invalid';assert.throws(()=>assessProducerProjection(row,'0036000291452',policy));
  row.stageRecordWireSha256=hash('5');assert.throws(()=>assessProducerProjection(row,'036000291452',policy));
});
test('generic entity kind, foreign relation receipt and wrong-source rule cannot qualify the type',()=>{
  for(const mutate of [r=>r.meaningfulTypeRelation.relation.meaningfulTypeKey='ingredient',r=>r.meaningfulTypeRelation.relationReceiptSha256=hash('f'),r=>r.applicationEligibility.entityKind=null]){
    const {row,policy,barcode}=fixture();mutate(row);assert.throws(()=>assessProducerProjection(row,barcode,policy));
  }
  const {row,policy,barcode}=fixture();policy.ruleScopes['generated:milk'].sourceId='usda-files';assert.throws(()=>assessProducerProjection(row,barcode,policy));
});
test('assertion value, source condition, duplicate and typed field commitment cannot be substituted',()=>{
  for(const mutate of [r=>r.rawAcceptedVariantAssertions[0].value='other',r=>r.rawAcceptedVariantAssertions[0].evidenceCondition.sourceQuoteOrMember='OTHER',r=>r.rawAcceptedVariantAssertions.push(structuredClone(r.rawAcceptedVariantAssertions[0])),r=>r.sourceEvidenceRefs[0].fieldEvidence[0].valueSha256='invalid',r=>delete r.parametersByAxis.fatClass]){
    const {row,policy,barcode}=fixture();mutate(row);assert.throws(()=>assessProducerProjection(row,barcode,policy));
  }
});
test('conflicting unreviewed multiplicity stays an explicit unknown axis with all alternatives, while base/type survives',()=>{
  const {row,policy,barcode}=fixture();policy.definitions.milk.parameters.processing.nonexclusiveAssertionGroups=[['generated:fresh'],['generated:homogenized'],['generated:esl']];row.parametersByAxis.processing={state:'unknown'};
  const r=assessProducerProjection(row,barcode,policy);assert.equal(r.assessment.foundationComplete,true);assert.deepEqual(r.unresolvedAxes,['processing']);
  assert.equal(r.candidate.parameters.processing.state,'unknown');assert.equal(r.candidate.parameters.processing.acceptedAlternatives.length,3);assert.equal(r.acceptedAssertions.length,3);
});
