// Pure adapter for exact, closed producer projections. The caller must verify
// the selected projection-file/subject/wire pins and actual publication scope.
import {assessFoundation,FOUNDATION_CONTRACT} from './foundation-phase-contract-v2.mjs';
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256',
  'sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
const SHA=/^[a-f0-9]{64}$/;
const R2_REVIEW='f4a0068bf79cd93c5e198a3ae94cc1a0ef11d14c9843bdb1a47bfa00ae5e7efd';
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
const own=(x,k)=>Object.hasOwn(x,k);
const text=x=>typeof x==='string'&&x.length>0&&x.length<=512&&!/[\x00-\x1f\x7f]/.test(x);
function demand(ok,reason){if(!ok)throw Error('FOUNDATION_PROJECTION:'+reason);}
function equal(a,b){
  if(a===b)return true;
  if(!object(a)||!object(b))return false;
  const keys=Object.keys(a);return keys.length===Object.keys(b).length&&keys.every(k=>own(b,k)&&equal(a[k],b[k]));
}
function sameSubject(a,b){return object(a)&&object(b)&&SUBJECT.every(k=>own(a,k)&&own(b,k)&&text(a[k])&&a[k]===b[k])&&SUBJECT.slice(3).every(k=>SHA.test(a[k]));}

export function assessProducerProjection(row,barcode,policy){
  demand(policy?.schema===FOUNDATION_CONTRACT&&object(policy.definitions)&&object(policy.ruleScopes),'policy');
  demand(row?.schema==='offmenu-exact-reviewed-meaningful-type-producer-projection/1','schema');
  const binding=row.sourceBinding;
  demand(sameSubject(binding,binding)&&text(row.stageRecordId)&&SHA.test(row.stageRecordWireSha256)&&text(row.nativeRecordId),'source-stage');
  const source=own(policy.sourceQualifications||{},binding.sourceId)?policy.sourceQualifications[binding.sourceId]:null;
  demand(source?.releaseId===binding.releaseId&&source.qualificationSha256===binding.sourceQualificationSha256,'source-scope');
  demand(typeof barcode==='string'&&Array.isArray(row.barcodeIdentity?.exactSourceKeys)&&
    Array.isArray(row.barcodeIdentity?.qualifiedGtinKeys)&&row.barcodeIdentity.exactSourceKeys.includes(barcode)&&
    row.barcodeIdentity.qualifiedGtinKeys.includes(barcode),'exact-identifier');
  demand(row.applicationEligibility?.state==='reviewed'&&row.applicationEligibility.entityKind==='ingredient'&&
    row.applicationEligibility.reviewReceiptSha256===R2_REVIEW,'eligibility');
  const base=row.englishBase;
  const def=object(base)&&own(policy.definitions,base.canonicalEnglishKey)?policy.definitions[base.canonicalEnglishKey]:null;
  demand(def&&def.classification==='ingredient'&&base.conceptId===def.conceptId&&base.canonicalEnglishLabel===def.canonicalEnglishLabel,'base');
  const typed=row.meaningfulTypeRelation,relation=typed?.relation;
  demand(typed?.state==='reviewed-declarative-exact-source-target-linked'&&
    typed.relationReceiptSha256===policy.typeRelationReceiptSha256&&
    typed.correctedDeclarativePolicyReceiptSha256===policy.policyReceiptSha256&&
    relation?.baseConceptId===def.conceptId&&relation.canonicalEnglishBaseKey===base.canonicalEnglishKey&&
    relation.canonicalEnglishBaseLabel===def.canonicalEnglishLabel&&relation.typeId===def.typeRelation?.conceptId&&
    relation.meaningfulTypeKey===def.typeKey&&relation.relation==='is-a-food-type','type-relation');
  const matched=typed.matchedActualAcceptedR2RuleIds;
  demand(Array.isArray(matched)&&matched.length>0&&matched.every(id=>def.allowedRuleIds.includes(id)),'matched-rules');
  for(const id of matched){const scope=policy.ruleScopes[id];demand(scope?.sourceId===binding.sourceId&&
    scope.releaseId===binding.releaseId&&scope.sourceQualificationSha256===binding.sourceQualificationSha256,'rule-source');}
  demand(Array.isArray(row.sourceEvidenceRefs)&&row.sourceEvidenceRefs.length>0,'source-evidence');
  const refs=row.sourceEvidenceRefs;
  demand(refs.every(e=>sameSubject(e.sourceBinding,binding))&&matched.every(id=>refs.some(e=>e.ruleId===id)),'evidence-subject');
  function fields(ruleId=null,field=null){
    const selected=refs.filter(e=>matched.includes(e.ruleId)&&(!ruleId||e.ruleId===ruleId));
    const out=[];
    for(const r of selected){
      demand(Array.isArray(r.fieldEvidence)&&r.fieldEvidence.length>0,'field-evidence');
      for(const f of r.fieldEvidence){
        demand(text(f.field)&&text(f.sourcePointer)&&SHA.test(f.valueSha256),'field-commitment');
        if(!field||f.field===field)out.push({kind:'source-field',pointer:f.sourcePointer,
          sourceBinding:structuredClone(binding),valueSha256:f.valueSha256,ruleId:r.ruleId});
      }
    }
    demand(out.length>0,'selected-field-evidence');return out;
  }
  const baseEvidence=fields(),stamp={state:'reviewed',registrySha256:policy.registrySha256,
    independentReviewSha256:policy.independentReviewSha256,evidence:baseEvidence};
  const candidate={barcode,identity:{namespace:'barcode',lexicalValue:barcode,nativeRecordId:row.nativeRecordId,
    stageRecordId:row.stageRecordId,stageRecordWireSha256:row.stageRecordWireSha256,sourceBinding:structuredClone(binding)},
    classification:{...stamp,value:'ingredient'},base:{...stamp,...base,typeKey:def.typeKey},
    type:{state:'reviewed',...structuredClone(def.typeRelation),evidence:[{kind:'reviewed-type-rule',
      pointer:def.typeRelation.relationshipId,sourceBinding:structuredClone(binding)}]},parameters:{}};
  demand(Array.isArray(row.rawAcceptedVariantAssertions),'variant-list');
  demand(object(row.parametersByAxis)&&Object.keys(def.parameters).every(k=>
    own(row.parametersByAxis,k)&&object(row.parametersByAxis[k])),'explicit-axis-representation');
  const byAxis=new Map(),seen=new Set();
  for(const v of row.rawAcceptedVariantAssertions){
    demand(v?.semanticAccepted===true&&text(v.assertionId)&&!seen.has(v.assertionId),'variant-id');seen.add(v.assertionId);
    const c=own(policy.assertionCatalog||{},v.assertionId)?policy.assertionCatalog[v.assertionId]:null;
    demand(c&&matched.includes(c.ruleId)&&c.typeKey===v.typeKey&&equal(c.value,v.value)&&equal(c.evidenceCondition,v.evidenceCondition),'variant-contract');
    demand(own(def.parameters,v.typeKey),'variant-axis');
    const entry={assertionId:v.assertionId,value:structuredClone(v.value),evidence:fields(c.ruleId,c.evidenceCondition.field)};
    if(!byAxis.has(v.typeKey))byAxis.set(v.typeKey,[]);byAxis.get(v.typeKey).push(entry);
  }
  const unresolvedAxes=[];
  for(const [axis,definition]of Object.entries(def.parameters)){
    const values=byAxis.get(axis)||[];
    let value,known=false;
    if(definition.kind==='assertion-list'&&values.length){
      known=definition.nonexclusiveAssertionGroups.some(g=>values.every(v=>g.includes(v.assertionId)));
      if(known)value=values;
    }else if(values.length&&values.every(v=>equal(v.value,values[0].value))){known=true;value=values[0].value;}
    if(known){
      const projected=row.parametersByAxis[axis];
      demand(projected.state==='known'&&Array.isArray(projected.acceptedAssertions)&&
        projected.acceptedAssertions.length===values.length&&values.every(v=>
          projected.acceptedAssertions.some(a=>a.assertionId===v.assertionId&&equal(a.value,v.value))),'projected-known-axis');
      candidate.parameters[axis]={state:'known',value,independentReviewSha256:policy.independentReviewSha256,
      evidence:definition.kind==='assertion-list'?baseEvidence:values.flatMap(v=>v.evidence)};}
    else{
      demand(row.parametersByAxis[axis].state==='unknown','projected-unknown-axis');
      if(values.length)unresolvedAxes.push(axis);
      candidate.parameters[axis]={state:'unknown',reason:'not-provided-in-qualified-representation',
        qualificationDisposition:values.length?'no-single-qualified-controlled-value':'no-accepted-controlled-value',
        acceptedAlternatives:values,evidence:[{kind:'qualified-representation-omission',
          pointer:'/parametersByAxis/'+axis,sourceBinding:structuredClone(binding)}]};
    }
  }
  const assessment=assessFoundation(candidate,policy);
  return {candidate,assessment,unresolvedAxes,
    acceptedAssertions:structuredClone(row.rawAcceptedVariantAssertions),
    sourceAttributeClaims:structuredClone(row.sourceAttributeClaims||[]),
    publicationAccepted:false,goldAdmitted:false};
}
