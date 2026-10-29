import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {qualifyRetainedSourcePhoto} from '../../integrations/candidates/retained-source-photo-catalogue.mjs';
import {retainedSourcePhotoCandidate} from '../../apps/web/src/retained-source-photo-selection.js';
import {associateProductVisual} from '../../apps/web/src/product-visual-association.js';
import {mountScannerProductVisual} from '../../apps/web/src/scanner-product-visuals.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';
import {OFF_PHOTOS} from '../../apps/web/src/off-photo-catalogue.js';
const {parse}=createRequire(import.meta.url)('acorn');
const scannerSource=fs.readFileSync(new URL('../../apps/web/src/production-scanner/shelf-scanner.js',import.meta.url),'utf8');
function actualPhotoArguments(detail){let call;const walk=n=>{if(!n||typeof n!=='object')return;if(n.type==='CallExpression'&&n.callee.object?.name==='productVisual'&&n.callee.property?.name==='show')call=n;for(const v of Object.values(n))if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);};walk(parse(scannerSource,{ecmaVersion:'latest',sourceType:'module'}));assert.ok(call);return vm.runInNewContext('('+scannerSource.slice(call.arguments[0].start,call.arguments[0].end)+')',{selected:{detail,name:'Generated curated primary label'},current:{id:'generated-entry'},generation:1,document:{documentElement:{dataset:{theme:'light'}}},navigator:{onLine:true}});}
// Generated identity, source binding, admission and review fixtures only.
// No real private catalogue/native data is imported into this source test.
function fixture(){
 const f=photoFixture(),reference=f.reference,sha='a'.repeat(64),key=reference.observationKey;
 const sourceBinding={sourceId:'off',releaseId:reference.releaseId,identifierInputId:key.input_id,
  identifierRecordOrdinal:key.record_ordinal,identifierSourceRecordId:reference.sourceRecordId,
  identifierNativeRecordId:'off:sourceOccurrence:'+sha+':'+key.record_ordinal,
  originalSha256:sha,recordSha256:sha,identifierAssetSha256:sha,inputAssetSha256:sha,
  operationReceiptSha256:sha,rightsReceiptSha256:sha,custodyReceiptSha256:sha,componentDigests:{product:sha,profile:sha}};
 const detail={referenceRecordId:f.detail.referenceRecordId,observationKey:f.detail.observationKey,
  sourceObservation:{...f.detail.sourceObservation,artifact_sha256:sha,native_record_id:sourceBinding.identifierNativeRecordId},sourceBinding};
 const marker={state:'qualified',useSelectionRef:{id:'generated:private-use',sha256:'b'.repeat(64)},origin:'http://127.0.0.1:7645',runtimeSelectionSha256:'c'.repeat(64)};
 const imageObservation={sourceCode:reference.sourceLexicalValue,role:'front',imageId:'1',revision:'3',selectedKey:'front_en',resolution:'400',retrievedAt:'2026-10-26T09:00:00+11:00',sourceLocator:{sourceId:'off',releaseId:reference.releaseId,originalSha256:sha,ordinal:key.record_ordinal},image:{sha256:sha,bytes:12,type:'image/jpeg'}};
 const localAsset={path:'/api/off-photos/generated-native.jpg',sha256:sha,type:'image/jpeg'};
 const selected={schema:'offmenu-source-assertion-photo-selection/1',reference,detail,imageObservation,localAsset,useSelectionRef:marker.useSelectionRef};
 const photo=OFF_PHOTOS[0],rights={displayPermitted:true,license:photo.license,licenseUrl:photo.licenseUrl,attribution:'Generated attribution',evidenceReference:'generated:selected-photo-use',sourcePage:photo.sourcePage,photoLicensePage:photo.licensePage,
  changes:'Generated unchanged-byte fixture',attributionDetails:{productUrl:photo.sourcePage,notices:[],packagingRights:{qualification:'Generated underlying-rights qualification'}}};
 const catalogue={schema:'offmenu-retained-source-photo-catalogue/1',entries:[{...structuredClone(selected),rights}],adoption:{state:'admitted',receiptSha256:'d'.repeat(64),bindingReviewRef:{id:'generated:review',sha256:'e'.repeat(64)},currentOutputUse:structuredClone(marker)}};
 const context={currentOutputUse:marker,origin:marker.origin,runtimeSelectionSha256:marker.runtimeSelectionSha256};
 const qualify=()=>qualifyRetainedSourcePhoto(selected,{catalogue,...context});
 const browserDetail={referenceRecordId:'generated-curated-primary',currentOutputUse:marker,sourceAssertions:[{sourceObservationReference:reference,binding:detail,fields:{name:{state:'present',value:'Generated independent source label'}}}]};
 return {selected,catalogue,context,browserDetail,qualify};
}
test('generic private guard emits only an exact reviewed/adopted qualified DTO; public resolver uses explicit native assertion',()=>{
 const f=fixture(),before=structuredClone({selected:f.selected,catalogue:f.catalogue});const result=f.qualify();assert.equal(result.state,'qualified');assert.equal(Object.hasOwn(result.selection.detail,'records'),false);assert.equal(Object.hasOwn(result.selection.detail,'fields'),false);
 assert.deepEqual({selected:f.selected,catalogue:f.catalogue},before);
 const value=associateProductVisual({detail:f.browserDetail,sourcePhotoSelection:result.selection,origin:f.context.origin,name:'Primary label is not source identity'});
 assert.equal(value.visual.tier,'product-photo');assert.equal(value.visual.src,f.selected.localAsset.path);assert.equal(value.visual.caption,'Selected source photo');assert.match(value.visual.alt,/variant match unverified/);assert.equal(value.sourceObservationReference.sourceLexicalValue,f.selected.reference.sourceLexicalValue);assert.equal(f.browserDetail.referenceRecordId,'generated-curated-primary');
});
test('private guard refuses missing/held adoption, stale runtime, wrong source components, reference or asset',()=>{
 const changes=[f=>f.catalogue.adoption=null,f=>f.catalogue.entries=[null],f=>f.catalogue.adoption.state='held',f=>f.context.runtimeSelectionSha256='f'.repeat(64),f=>delete f.context.runtimeSelectionSha256,f=>f.context.currentOutputUse.state='held',f=>f.selected.reference.observationKey.assertion_id++,f=>f.selected.detail.sourceBinding.componentDigests.product='f'.repeat(64),f=>f.selected.localAsset.sha256='f'.repeat(64),f=>f.selected.imageObservation.sourceLocator.ordinal++,f=>f.catalogue.entries[0].rights.displayPermitted=false];
 for(const change of changes){const f=fixture();change(f);assert.equal(f.qualify().state,'unavailable');assert.equal(f.qualify().selection,null);}
});
test('public consumer refuses stale/missing current context, duplicate or wrong selected assertion, unsafe links and raw metadata',()=>{
 for(const change of [f=>f.browserDetail.currentOutputUse=null,f=>f.browserDetail.currentOutputUse={...f.browserDetail.currentOutputUse,runtimeSelectionSha256:'f'.repeat(64)},f=>f.browserDetail.sourceAssertions=[],f=>f.browserDetail.sourceAssertions=[null],f=>f.browserDetail.sourceAssertions.push(structuredClone(f.browserDetail.sourceAssertions[0])),f=>f.selection.rights.sourcePage='javascript:alert(1)',f=>f.selection.imageObservation.sourceLocator.ordinal++,f=>f.selection.localAsset.path='/api/off-photos/../other.jpg',f=>f.selection.qualification.bindingReviewRef=null]){
  const f=fixture();f.selection=f.qualify().selection;change(f);const result=retainedSourcePhotoCandidate(f.selection,f.browserDetail,{origin:f.context.origin});assert.equal(result.state,'unavailable');assert.equal(result.candidate,null);
 }
 const f=fixture();assert.equal(associateProductVisual({detail:{fields:{imageUrlReferences:{state:'present',value:OFF_PHOTOS[0].url}}}}).visual.tier,'app-fallback');
});
class Node{constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.textContent='';}append(...n){this.children.push(...n);}replaceChildren(...n){this.children=[...n];}get firstChild(){return this.children[0];}}
test('existing shared mount displays scoped credit then clears it on lost eligibility; stale image errors cannot restore it',t=>{
 const prior=globalThis.location;globalThis.location={origin:'http://127.0.0.1:7645'};t.after(()=>{if(prior===undefined)delete globalThis.location;else globalThis.location=prior;});
 const doc={documentElement:{dataset:{theme:'light'}},createElement:tag=>new Node(tag,doc)},thumb=new Node('div',doc),credit=new Node('div',doc),mounted=mountScannerProductVisual(thumb,credit);const f=fixture(),selection=f.qualify().selection;
 f.browserDetail.sourcePhotoSelection=selection;const args=actualPhotoArguments(f.browserDetail);assert.equal(args.reference,null);assert.equal(args.sourcePhotoSelection,selection);mounted.show(args);assert.equal(thumb.dataset.visualTier,'product-photo');const photo=thumb.firstChild;assert.ok(credit.children.some(n=>n.tagName==='details'));assert.ok(credit.children.find(n=>n.tagName==='details').children.some(n=>n.textContent.includes('author and notices were not captured')));
 const held={...f.browserDetail,currentOutputUse:null};mounted.show({sourcePhotoSelection:selection,detail:held,entryId:'generated-entry'});assert.equal(thumb.dataset.visualTier,'app-fallback');assert.ok(!credit.children.some(n=>n.tagName==='details'));const fallback=thumb.firstChild;photo.onerror();assert.equal(thumb.firstChild,fallback);mounted.destroy();
});
test('offline and failed native asset use the shared honest fallback without any image loader or extra request',()=>{
 const f=fixture(),selection=f.qualify().selection;const input={sourcePhotoSelection:selection,detail:f.browserDetail,origin:f.context.origin};assert.equal(associateProductVisual({...input,offline:true}).visual.tier,'app-fallback');
 const chosen=associateProductVisual(input);assert.equal(chosen.visual.tier,'product-photo');const result=associateProductVisual({...input}, {failedSources:[f.selected.localAsset.path]});assert.equal(result.visual.tier,'app-fallback');
});
