import test from 'node:test';
import assert from 'node:assert/strict';
import {FOUNDATION_CONTRACT,assessFoundation,summarizeFoundation} from '../corpus/foundation-phase-contract.mjs';
const registry='a'.repeat(64), review='b'.repeat(64);
const subject={sourceId:'generated',releaseId:'generated-1',recordId:'generated:1',
  sourceObservationSha256:'c'.repeat(64),inputDatabaseSha256:'d'.repeat(64),
  sourceQualificationSha256:'e'.repeat(64),sourceDocumentSha256:'f'.repeat(64)};
const evidence=kind=>[{kind,pointer:'/generated/selected-field',sourceBinding:structuredClone(subject)}];
const stamp=()=>({state:'reviewed',registrySha256:registry,independentReviewSha256:review,evidence:evidence('source-field')});
function fixture(){
  const policy={schema:FOUNDATION_CONTRACT,registrySha256:registry,independentReviewSha256:review,definitions:{
    'milk.cow':{classification:'ingredient',canonicalEnglishLabel:'Cow milk',conceptId:'generated:milk-cow',typeKey:'milk',parameters:{fatPercentage:{kind:'number',minimum:0,maximum:100},flavour:{kind:'string',values:['plain','vanilla']}}},
    'packaging.container':{classification:'noningredient',canonicalEnglishLabel:'Packaging container',conceptId:'generated:container',typeKey:'packaging',parameters:{fatPercentage:{kind:'number',notApplicable:true}}}}};
  const candidate={barcode:'036000291452',identity:{namespace:'barcode',lexicalValue:'036000291452',nativeRecordId:'generated-native-1',stageRecordId:'offmenu:product:generated-1',stageRecordWireSha256:'1'.repeat(64),sourceBinding:structuredClone(subject)},
    classification:{...stamp(),value:'ingredient'},base:{...stamp(),canonicalEnglishKey:'milk.cow',canonicalEnglishLabel:'Cow milk',conceptId:'generated:milk-cow',typeKey:'milk'},parameters:{
      fatPercentage:{state:'unknown',reason:'not-provided-in-qualified-representation',evidence:evidence('qualified-representation-omission')},
      flavour:{state:'known',value:'plain',independentReviewSha256:review,evidence:evidence('source-field')}}};
  return {policy,candidate};
}
test('unknown fat and absent optional nutrition/allergen/recipe facts preserve qualified milk foundation',()=>{
  const {candidate,policy}=fixture(),before=structuredClone({candidate,policy});const a=assessFoundation(candidate,policy);
  assert.equal(a.foundationComplete,true);assert.equal(a.ingredientApplicationEligible,true);assert.deepEqual(a.parameters.unknown,['fatPercentage']);
  assert.deepEqual({candidate,policy},before);for(const key of ['fullProductComplete','goldAdmitted','publicationAccepted','recipeNutritionJoinsAccepted'])assert.equal(a[key],false);
});
test('reviewed noningredient is foundation-qualified but ineligible for ingredient application',()=>{
  const {candidate:c,policy:p}=fixture();c.classification.value='noningredient';c.base={...stamp(),canonicalEnglishKey:'packaging.container',canonicalEnglishLabel:'Packaging container',conceptId:'generated:container',typeKey:'packaging'};
  c.parameters={fatPercentage:{state:'not-applicable',independentReviewSha256:review,evidence:evidence('reviewed-type-rule')}};
  const a=assessFoundation(c,p);assert.equal(a.foundationComplete,true);assert.equal(a.ingredientApplicationEligible,false);assert.deepEqual(a.parameters.notApplicable,['fatPercentage']);
});
test('unresolved classification or base cannot become complete from a known type or optional facts',()=>{
  for(const change of [c=>c.classification.value=null,c=>delete c.base,c=>c.base.canonicalEnglishKey='constructor',c=>c.classification.independentReviewSha256='2'.repeat(64)]){
    const {candidate,policy}=fixture();change(candidate);candidate.nutrition={allKnown:true};const a=assessFoundation(candidate,policy);assert.equal(a.foundationComplete,false);assert.equal(a.ingredientApplicationEligible,null);
  }
});
test('exact GTIN lexical association preserves leading zeros and rejects alias/invalid/number input',()=>{
  const {candidate,policy}=fixture();candidate.barcode=candidate.identity.lexicalValue='0036000291452';assert.equal(assessFoundation(candidate,policy).foundationComplete,true);
  for(const value of ['036000291453',36000291452,' 036000291452','1234']){const {candidate:c,policy:p}=fixture();c.barcode=c.identity.lexicalValue=value;assert.equal(assessFoundation(c,p).foundationComplete,false);}
  candidate.identity.lexicalValue='036000291452';assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
});
test('all evidence must belong to the selected source subject; arbitrary classifications cannot cross records',()=>{
  for(const field of Object.keys(subject)){
    const {candidate,policy}=fixture();candidate.base.evidence[0].sourceBinding[field]='different';assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
  const {candidate,policy}=fixture();candidate.identity.stageRecordWireSha256='not-a-hash';assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
});
test('missing parameter state differs from explicitly scoped unknown and unknown never carries an invented value',()=>{
  for(const change of [c=>delete c.parameters.fatPercentage,c=>c.parameters.fatPercentage.value=0,c=>c.parameters.fatPercentage.reason='globally-absent',c=>c.parameters.fatPercentage.evidence=[]]){
    const {candidate,policy}=fixture();change(candidate);assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
  }
});
test('known zero is preserved, while wrong units/types/ranges/review or invented N/A remain incomplete',()=>{
  const {candidate,policy}=fixture();candidate.parameters.fatPercentage={state:'known',value:0,independentReviewSha256:review,evidence:evidence('source-field')};assert.equal(assessFoundation(candidate,policy).foundationComplete,true);
  for(const value of ['0',-1,101,NaN,Infinity]){candidate.parameters.fatPercentage.value=value;assert.equal(assessFoundation(candidate,policy).foundationComplete,false);}
  candidate.parameters.fatPercentage={state:'not-applicable',independentReviewSha256:review,evidence:evidence('reviewed-type-rule')};assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
});
test('source attributes and extra unreviewed variant dimensions cannot silently become selected parameter facts',()=>{
  const {candidate,policy}=fixture();candidate.parameters.origin={state:'known',value:'FR',independentReviewSha256:review,evidence:evidence('source-field')};assert.equal(assessFoundation(candidate,policy).foundationComplete,false);
});
test('separate counts keep incomplete foundation and later Gold/product/publication acceptance distinct',()=>{
  const {candidate,policy}=fixture(),ready=assessFoundation(candidate,policy);candidate.classification.value=null;const incomplete=assessFoundation(candidate,policy);
  assert.deepEqual(summarizeFoundation([ready,incomplete]),{schema:FOUNDATION_CONTRACT,scope:'selected-assessments-only',observations:2,foundationComplete:1,ingredient:1,noningredient:0,incomplete:1,fullProductComplete:0,goldAdmitted:0,publicationAccepted:false});
  assert.throws(()=>summarizeFoundation([{...ready,goldAdmitted:true}]));assert.throws(()=>assessFoundation(candidate,{}));
});
