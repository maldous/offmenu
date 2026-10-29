// CANDIDATE shared projection contract. This module validates/serializes evidence;
// it never classifies names, resolves aliases, invents IDs, or admits source data.
export const CLASSIFICATION_CONTRACT='offmenu-source-classification-relationships/1';
const dispositions=new Set(['ingredient','type','nonfood','not-applicable','unresolved','conflict']);
const sha=x=>typeof x==='string'&&/^[0-9a-f]{64}$/.test(x);
const named=x=>typeof x==='string'&&x.length>0;
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&[Object.prototype,null].includes(Object.getPrototypeOf(x));
const pin=x=>object(x)&&named(x.path)&&sha(x.sha256)&&Object.keys(x).length===2;
function jsonData(v){
 if(v===null||typeof v==='string'||typeof v==='boolean')return true;
 if(typeof v==='number')return Number.isFinite(v);
 if(Array.isArray(v))return v.every(jsonData)&&Object.keys(v).length===v.length;
 return object(v)&&Object.values(v).every(jsonData);
}
export function validateClassificationProjection(value){
 if(!object(value)||!object(value.sourceBinding)||value.schema!==CLASSIFICATION_CONTRACT||!named(value.sourceBinding.sourceRecordId)||!sha(value.sourceBinding.snapshotSha256))throw Error('Exact source record/snapshot binding required');
 const c=value.classification;
 if(!object(c)||!dispositions.has(c.disposition)||!Array.isArray(c.reasonCodes)||!c.reasonCodes.every(named)||!Array.isArray(c.evidenceRefs)||!c.evidenceRefs.every(e=>object(e)&&named(e.assertionId)&&pin(e.admission))||!Array.isArray(value.relationships)||!value.relationships.every(object))throw Error('Explicit classification disposition/evidence required');
 if(typeof c.identityEquivalence!=='boolean'||![c.canonicalId,c.idScope,c.relation].every(x=>x===null||named(x)))throw Error('Explicit typed ID/scope/relation/identity state required');
 if(value.sourceBinding.sourceObservationReference!==undefined&&value.sourceBinding.sourceObservationReference!==null&&!object(value.sourceBinding.sourceObservationReference))throw Error('Observation reference must retain an object or null');
 if(!['applicable','nonfood','not-applicable','unresolved','conflict'].includes(c.ingredientApplicability))throw Error('Explicit ingredient applicability required');
 if(c.disposition==='ingredient'&&c.ingredientApplicability!=='applicable')throw Error('Nonfood cannot become an ingredient');
 if(['nonfood','not-applicable','unresolved','conflict'].includes(c.disposition)&&c.ingredientApplicability!==c.disposition)throw Error('Disposition/applicability conflict');
 if(['ingredient','type'].includes(c.disposition)&&(!named(c.canonicalId)||!named(c.idScope)||!named(c.relation)))throw Error('Supported ID requires explicit identity scope and relation');
 if(['unresolved','conflict','not-applicable','nonfood'].includes(c.disposition)&&c.canonicalId!==null)throw Error('Do not force an ingredient/type ID for unresolved/nonfood/not-applicable/conflict');
 if(c.disposition!=='unresolved'&&c.disposition!=='conflict'&&(!c.evidenceRefs.length||!c.evidenceRefs.every(e=>named(e.assertionId)&&pin(e.admission))))throw Error('Positive/nonfood/not-applicable decisions require qualified evidence and admission references');
 if(['unresolved','conflict','nonfood','not-applicable'].includes(c.disposition)&&!c.reasonCodes.length)throw Error('Unresolved/conflict/nonfood/not-applicable reason required');
 if(c.relation==='represents'&&c.identityEquivalence!==false)throw Error('Scoped class membership is not identity equivalence');
 if(value.visualClassification!==null&&!object(value.visualClassification))throw Error('Visual contract is separately bound or null');
 if(!jsonData(value))throw Error('Finite JSON data required; no silent coercion or dropped evidence');
 return value;
}
export function unresolvedProjection(sourceBinding,reasonCodes=['NO_ACCEPTED_CLASSIFICATION_EVIDENCE']){
 return validateClassificationProjection({schema:CLASSIFICATION_CONTRACT,sourceBinding:structuredClone(sourceBinding),
  classification:{disposition:'unresolved',ingredientApplicability:'unresolved',canonicalId:null,idScope:null,relation:null,identityEquivalence:false,evidenceRefs:[],reasonCodes:[...reasonCodes]},
  relationships:[],visualClassification:null});
}
