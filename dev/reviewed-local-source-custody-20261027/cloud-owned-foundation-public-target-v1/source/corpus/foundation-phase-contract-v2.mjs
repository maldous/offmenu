// Explicit typed successor. The independently reviewed v1 assessor remains
// unchanged; this adapter qualifies typed values before passing them to it.
import {assessFoundation as assessV1,summarizeFoundation as summarizeV1,
  FOUNDATION_CONTRACT as V1} from './foundation-phase-contract.mjs';

export const FOUNDATION_CONTRACT='offmenu-barcode-foundation-phase/2';
const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v);
const own=(v,k)=>Object.hasOwn(v,k);
const text=v=>typeof v==='string'&&v.length>0&&v.length<=512&&!/[\x00-\x1f\x7f]/.test(v);
const exactKeys=(v,keys)=>object(v)&&Object.keys(v).length===keys.length&&keys.every(k=>own(v,k));
const SUBJECT=['sourceId','releaseId','recordId','sourceObservationSha256',
  'sourceDocumentSha256','inputDatabaseSha256','sourceQualificationSha256'];
const SHA=/^[a-f0-9]{64}$/;

function typeRelation(candidate,definition){
  const selected=definition?.typeRelation,actual=candidate?.type,subject=candidate?.identity?.sourceBinding;
  if(!object(selected)||!object(actual)||!object(subject)||actual.state!=='reviewed'||
      !text(selected.typeKey)||['ingredient','noningredient'].includes(selected.typeKey)||
      selected.typeKey!==definition.typeKey||selected.subjectConceptId!==definition.conceptId||
      !['is-a','category-member'].includes(selected.relationshipKind)||
      !SHA.test(selected.registrySha256)||!SHA.test(selected.independentReviewSha256))return false;
  for(const key of ['typeKey','canonicalEnglishLabel','conceptId','relationshipId',
    'relationshipKind','subjectConceptId','registrySha256','independentReviewSha256'])
    if(!text(selected[key])||actual[key]!==selected[key])return false;
  return Array.isArray(actual.evidence)&&actual.evidence.length>0&&actual.evidence.length<=32&&
    actual.evidence.every(e=>object(e)&&e.kind==='reviewed-type-rule'&&text(e.pointer)&&
      object(e.sourceBinding)&&SUBJECT.every(k=>own(e.sourceBinding,k)&&e.sourceBinding[k]===subject[k]));
}

function conceptValue(value,definition){
  return exactKeys(value,['conceptId'])&&text(value.conceptId)&&
    Array.isArray(definition.values)&&definition.values.includes(value.conceptId);
}

function assertionList(value,definition){
  if(!Array.isArray(value)||value.length<1||value.length>16||
      !object(definition.assertions)||!Array.isArray(definition.nonexclusiveAssertionGroups))return false;
  const ids=[];
  for(const row of value){
    if(!exactKeys(row,['assertionId','value','evidence'])||!text(row.assertionId)||
        !own(definition.assertions,row.assertionId)||!text(row.value)||
        row.value!==definition.assertions[row.assertionId]||
        !Array.isArray(row.evidence)||row.evidence.length<1||row.evidence.length>32||
        ids.includes(row.assertionId))return false;
    ids.push(row.assertionId);
  }
  return definition.nonexclusiveAssertionGroups.some(group=>Array.isArray(group)&&
    group.length<=16&&ids.every(id=>group.includes(id)));
}

export function assessFoundation(candidate,policy){
  if(!object(policy)||policy.schema!==FOUNDATION_CONTRACT)throw Error('FOUNDATION_V2_POLICY_REQUIRED');
  const selected=structuredClone(policy),record=structuredClone(candidate);
  selected.schema=V1;
  if(object(selected.definitions))for(const [key,base]of Object.entries(selected.definitions)){
    if(!object(base)||!object(base.parameters))continue;
    for(const [axis,definition]of Object.entries(base.parameters)){
      if(!object(definition)||!['concept-reference','assertion-list'].includes(definition.kind))continue;
      const row=record?.base?.canonicalEnglishKey===key&&object(record.parameters)&&own(record.parameters,axis)
        ?record.parameters[axis]:null;
      const originalKind=definition.kind;
      definition.kind='string';
      if(!object(row)||row.state!=='known')continue;
      if(originalKind==='concept-reference'){
        row.value=conceptValue(row.value,definition)?row.value.conceptId:null;
      }else{
        const valid=assertionList(row.value,definition);
        // The v1 evidence validator checks every nested assertion's source
        // subject and source-field kind as well as the outer evidence.
        const nested=valid?row.value.flatMap(v=>v.evidence):[];
        const encoded=valid?JSON.stringify(row.value.map(v=>[v.assertionId,v.value])):null;
        row.evidence=Array.isArray(row.evidence)?[...row.evidence,...nested]:null;
        row.value=encoded;
        definition.values=valid?[encoded]:[];
      }
    }
  }
  const result=assessV1(record,selected),key=candidate?.base?.canonicalEnglishKey;
  const definition=object(policy.definitions)&&typeof key==='string'&&own(policy.definitions,key)
    ?policy.definitions[key]:null;
  if(!typeRelation(candidate,definition))return {...result,schema:FOUNDATION_CONTRACT,
    state:'incomplete',foundationComplete:false,ingredientApplicationEligible:null,classification:null,
    reasons:[...new Set([...result.reasons,'meaningful-type-category-relation-unqualified'])]};
  return {...result,schema:FOUNDATION_CONTRACT};
}

export function summarizeFoundation(assessments){
  if(!Array.isArray(assessments)||assessments.some(r=>r?.schema!==FOUNDATION_CONTRACT))
    throw Error('FOUNDATION_V2_ASSESSMENTS_REQUIRED');
  return {...summarizeV1(assessments.map(r=>({...r,schema:V1}))),schema:FOUNDATION_CONTRACT};
}
