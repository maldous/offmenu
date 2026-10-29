import test from 'node:test';
import assert from 'node:assert/strict';
import {associateProductVisual,afterProductVisualAssociationFailure,
  PRODUCT_VISUAL_ASSOCIATION} from '../../public/product-visual-association.js';
import {PRODUCT_VISUAL_SELECTOR,appProductVisualFallback} from '../../public/product-visual-selector.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';

test('all future consumers get the same exact qualified association, credit and versions',()=>{
  const input={...photoFixture(),name:'Authored source label'};
  const first=associateProductVisual(input);
  for(const consumer of ['scanner','search','kitchen','review','details'])
    assert.deepEqual(associateProductVisual({...input,consumer}),first);
  assert.equal(first.schema,PRODUCT_VISUAL_ASSOCIATION);
  assert.equal(first.selectorVersion,PRODUCT_VISUAL_SELECTOR);
  assert.equal(first.visual.tier,'product-photo');
  assert.equal(first.visual.provenance.revision,'5');
  assert.equal(first.visual.rights.license,'CC BY-SA 3.0');
  assert.ok(first.visual.rights.attribution.includes('foodless'));
  assert.equal(first.visual.provenance.releaseId,null);
  assert.match(first.visual.provenance.relationship,/retained-snapshot-image-membership-unverified/);
  assert.equal(first.productRecordId,input.detail.referenceRecordId);
  assert.equal(first.sourceObservationReference.originalLexicalValue,'078742003986');
  assert.equal(first.sourceObservationReference.sourceLexicalValue,'0078742003986');
  assert.equal(first.sourceObservationReference.matchType,'representation-alias');
  assert.equal(first.sourceObservationReference.equivalence,'upc-a-as-leading-zero-ean-13');
});

test('name and bare barcode or ambiguous selections never create a photo join',()=>{
  for(const input of [null,{}, {name:'Nutella',barcode:'3017620422003'},
    {reference:[photoFixture().reference],detail:photoFixture().detail},
    {...photoFixture(),detail:[photoFixture().detail,photoFixture().detail]}])
    assert.equal(associateProductVisual(input).visual.tier,'app-fallback');
});

test('reference namespace, labelled equivalence, database and selection versions stay strict',()=>{
  for(const change of [{databaseSha256:'0'.repeat(64)},{detailSelectionSha256:'0'.repeat(64)},
    {namespace:'USDA-FDC'},{equivalence:null},{matchType:'exact'},{schema:'offmenu-identifier-observation/1'},
    {runId:'other'},{sourceId:''}]) {
    const fixture=photoFixture();fixture.reference={...fixture.reference,...change};
    const value=associateProductVisual(fixture);
    assert.equal(value.visual.tier,'app-fallback');assert.equal(value.productRecordId,null);
  }
});

test('same lexical value with another provider, release, record or observation cannot match',()=>{
  for(const mutate of [f=>f.reference.sourceId='usda-files',
    f=>f.detail.sourceBinding.releaseId='other-release',
    f=>f.detail.sourceObservation.source_record_id='other-record',
    f=>f.detail.observationKey.assertion_id++,f=>f.detail.sourceObservation.record_ordinal++,
    f=>f.detail.records[0].data.identifiers=[{system:'USDA-FDC',value:f.reference.sourceLexicalValue}],
    f=>f.detail.sourceObservation.namespace='USDA-FDC']) {
    const fixture=photoFixture();mutate(fixture);
    assert.equal(associateProductVisual(fixture).visual.tier,'app-fallback');
  }
});

test('descriptor snapshots only typed reference and approved photo evidence, no private caller data',()=>{
  const fixture=photoFixture();fixture.reference.privateProfile='PRIVATE';
  fixture.reference.observationKey.privateToken='PRIVATE';fixture.detail.privateProfile='PRIVATE';
  fixture.detail.records[0].data.private='PRIVATE';
  const before=structuredClone(fixture),value=associateProductVisual(fixture);
  assert.deepEqual(fixture,before);assert.ok(!JSON.stringify(value).includes('PRIVATE'));
  fixture.reference.observationKey.assertion_id++;
  assert.equal(value.sourceObservationReference.observationKey.assertion_id,9);
});

test('current input is revalidated after a failure; stale descriptor cannot authorize a new source',()=>{
  const first=associateProductVisual(photoFixture());
  const next=photoFixture();next.reference.databaseSha256='0'.repeat(64);
  const result=afterProductVisualAssociationFailure(next,first);
  assert.equal(result.visual.tier,'app-fallback');assert.equal(result.sourceObservationReference,null);
});

test('offline, failed photo and failed app icon retain existing selector behavior',()=>{
  const input={...photoFixture(),theme:'dark'};
  assert.equal(associateProductVisual({...input,offline:true}).visual.src,'/scanner-balanced-final-dark.svg');
  const first=associateProductVisual(input),failed=afterProductVisualAssociationFailure(input,first);
  assert.equal(failed.visual.src,'/scanner-balanced-final-dark.svg');
  const text=afterProductVisualAssociationFailure(input,failed,{failedSources:[first.visual.src]});
  assert.equal(text.visual.kind,'text');assert.equal(text.visual.text,'OffMenu');
  const unknown=associateProductVisual({theme:'dark'});
  assert.deepEqual(unknown.visual,appProductVisualFallback({theme:'dark'}));
  assert.equal(afterProductVisualAssociationFailure({theme:'dark'},unknown).visual.kind,'text');
});

test('caller guesses cannot replace catalogue rights or add category/ingredient authority',()=>{
  const value=associateProductVisual({...photoFixture(),
    photoCandidates:[{sourceUrl:'https://example.invalid/guess.jpg',rights:{displayPermitted:true}}],
    categoryMappings:[{status:'qualified',conceptId:'guessed'}],
    ingredientMatch:{state:'nonfood',qualified:true},category:'Food from a name'});
  assert.equal(value.visual.tier,'product-photo');
  assert.equal(value.visual.rights.license,'CC BY-SA 3.0');
  assert.equal(value.category.label,'Category');assert.equal(value.category.display,'Not yet identified');
  assert.equal(value.category.sourceCategory.claims,null);
  assert.equal(value.category.normalizedCategory.conceptId,null);
  assert.match(value.category.normalizedCategory.reasonCode,/NO_ACCEPTED_BACKING_STORE/);
  assert.equal(value.ingredientMatch.label,'Ingredient match');
  assert.equal(value.ingredientMatch.display,'Not yet identified');
  assert.equal(value.ingredientMatch.composition,null);
  assert.match(value.ingredientMatch.reasonCode,/NO_ACCEPTED_BACKING_STORE/);
  assert.notEqual(value.ingredientMatch.display,'Not applicable');
});
