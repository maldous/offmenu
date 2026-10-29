import test from 'node:test';
import assert from 'node:assert/strict';
import {associateProductVisual} from '../../apps/web/src/product-visual-association.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';
// Generated record IDs/evidence only. The native source record ID deliberately
// differs from the consumer's federated record ID; neither is inferred/rewritten.
function fixture(){
 const f={...photoFixture(),offline:true};f.reference.sourceRecordId='generated-native-record';
 f.detail.referenceRecordId='generated-consumer-record';f.detail.sourceObservation.source_record_id=f.reference.sourceRecordId;
 f.detail.sourceBinding.identifierSourceRecordId=f.reference.sourceRecordId;
 const visual={schema:'offmenu-product-visual-classification/1',sourceObservationReference:structuredClone(f.reference),productRecordId:f.detail.referenceRecordId,qualification:{state:'qualified',evidenceReference:'generated:visual-classification'},ingredientApplicability:{state:'applicable',evidenceReference:'generated:applicability'},ingredientMappings:[{sourceObservationReference:structuredClone(f.reference),productRecordId:f.detail.referenceRecordId,status:'qualified',relation:'exact',conceptId:'generated:ingredient',taxonomyVersion:'generated-taxonomy',crosswalkVersion:'generated-crosswalk',originalSource:{term:'Generated source class',language:'en'},provenance:{sourceId:'off',releaseId:f.reference.releaseId,pointer:'/generated/classification'}}],typeMappings:[],canonicalConcepts:[{conceptId:'generated:ingredient',taxonomyVersion:'generated-taxonomy',kind:'ingredient',definitionStatus:'accepted',preferredEnglishLabel:'Generated ingredient',presentation:{status:'approved',evidenceReference:'generated:presentation',emoji:'🫘'}}],permittedLocalAssets:[]};
 f.detail.classificationProjection={schema:'offmenu-source-classification-relationships/1',sourceBinding:{sourceRecordId:f.reference.sourceRecordId,snapshotSha256:'a'.repeat(64),sourceObservationReference:structuredClone(f.reference)},classification:{disposition:'ingredient',ingredientApplicability:'applicable',canonicalId:'generated:ingredient',idScope:'generated-only',relation:'exact',identityEquivalence:false,evidenceRefs:[{assertionId:'generated:source-class',admission:{path:'generated-admission',sha256:'b'.repeat(64)}}],reasonCodes:[]},relationships:[],visualClassification:visual};return f;
}
test('W06 source record binding: same native record is valid; wrong outer or supplied detail IDs remain unresolved',()=>{
 const valid=fixture(),before=structuredClone(valid);const result=associateProductVisual(valid);
 assert.notEqual(valid.reference.sourceRecordId,valid.detail.referenceRecordId);
 assert.equal(result.classification.state,'qualified');assert.equal(result.visual.tier,'ingredient-illustration');assert.deepEqual(valid,before);
 for(const mutate of [
  f=>f.detail.classificationProjection.sourceBinding.sourceRecordId='another-source-record',
  f=>f.detail.classificationProjection.sourceBinding.sourceRecordId=f.detail.referenceRecordId,
  f=>f.detail.sourceObservation.source_record_id='another-source-record',
  f=>f.detail.sourceBinding.identifierSourceRecordId='another-source-record',
  f=>f.detail.sourceBinding.sourceRecordId='another-source-record',
  f=>f.reference.sourceRecordId=null
 ]){const f=fixture();mutate(f);const value=associateProductVisual(f);assert.equal(value.classification.state,'unresolved');assert.equal(value.visual.tier,'app-fallback');assert.equal(value.classification.selectedIcon,null);}
 const consistent=fixture();consistent.detail.sourceBinding.sourceRecordId=consistent.reference.sourceRecordId;assert.equal(associateProductVisual(consistent).visual.tier,'ingredient-illustration');
});
