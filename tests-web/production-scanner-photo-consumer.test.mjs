import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {mountScannerProductVisual} from '../public/production-scanner/scanner-product-visuals-production.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';
import {OFF_PHOTOS} from '../public/off-photo-catalogue.js';
const {parse}=createRequire(import.meta.url)('acorn');
const source=fs.readFileSync(new URL('../public/production-scanner/shelf-scanner.js',import.meta.url),'utf8');
class Node {
 constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.textContent='';}
 append(...nodes){this.children.push(...nodes);}replaceChildren(...nodes){this.children=[...nodes];}get firstChild(){return this.children[0];}
}
function dom(){const doc={documentElement:{dataset:{theme:'light'}},createElement:tag=>new Node(tag,doc)},thumbnail=new Node('div',doc),caption=new Node('div',doc);return {doc,thumbnail,caption,mounted:mountScannerProductVisual(thumbnail,caption)};}
// Generated observation/detail fixture from the accepted adapter tests. This is
// synthetic identity evidence, not a retained product observation or image fetch.
function qualified(){return {...photoFixture(),entryId:'generated-entry',generation:1,name:'Generated retained label'};}
function showInput(selected){
 const ast=parse(source,{ecmaVersion:'latest',sourceType:'module'});let call;
 const walk=n=>{if(!n||typeof n!=='object')return;if(n.type==='CallExpression'&&n.callee.type==='MemberExpression'&&n.callee.object.name==='productVisual'&&n.callee.property.name==='show')call=n;for(const [k,v]of Object.entries(n))if(!['start','end'].includes(k)){if(Array.isArray(v))v.forEach(walk);else if(v&&typeof v==='object')walk(v);}};walk(ast);assert.ok(call);
 return vm.runInNewContext('('+source.slice(call.arguments[0].start,call.arguments[0].end)+')',{selected,current:{id:'generated-entry'},generation:1,document:{documentElement:{dataset:{theme:'light'}}},navigator:{onLine:true}});
}
test('actual scanner photo-call forwards only an actually supplied typed reference; no reference is synthesized',()=>{
 const fixture=qualified(),selected={name:fixture.name,sourceObservationReference:fixture.reference,detail:fixture.detail};const input=showInput(selected);assert.equal(input.reference,fixture.reference);assert.equal(input.detail,fixture.detail);
 assert.equal(showInput({name:'Generated public record',publicRecord:{data:{identifiers:[{system:'barcode',value:OFF_PHOTOS[0].sourceCode}]}}}).reference,null);
});
test('production slot uses accepted exact-contract photo selection and accessible attribution with no image network',()=>{
 const h=dom();const fixture=qualified();h.mounted.show(showInput({name:fixture.name,sourceObservationReference:fixture.reference,detail:fixture.detail}));
 assert.equal(h.thumbnail.dataset.visualTier,'product-photo');assert.equal(h.thumbnail.firstChild.src,OFF_PHOTOS[0].path);assert.match(h.thumbnail.firstChild.alt,/photo/);assert.equal(h.thumbnail.firstChild.referrerPolicy,'no-referrer');
 const details=h.caption.children.find(n=>n.tagName==='details');assert.ok(details);assert.equal(details.children[0].tagName,'summary');assert.ok(details.children.some(n=>n.tagName==='a'&&n.href===OFF_PHOTOS[0].licenseUrl&&n.rel==='noopener noreferrer'));assert.ok(details.children.some(n=>n.textContent.includes(OFF_PHOTOS[0].contributor)));
 assert.equal(h.caption.children[0].textContent,'Current publisher photo');h.mounted.destroy?.();
});
test('current public unknown shape, raw metadata and mismatched or held evidence cannot grant a photo',()=>{
 const fixture=qualified();for(const selected of [
  {name:'Unknown public product',detail:{fields:{imageUrlReferences:{state:'missing',value:null}}}},
  {name:'Raw reference is not display permission',publicRecord:{data:{identifiers:[{system:'barcode',value:OFF_PHOTOS[0].sourceCode}]}},detail:{fields:{imageUrlReferences:{state:'present',value:[OFF_PHOTOS[0].url]}}}},
  {sourceObservationReference:fixture.reference,detail:{...fixture.detail,referenceRecordId:null}},
  {sourceObservationReference:fixture.reference,detail:{...fixture.detail,sourceObservation:{...fixture.detail.sourceObservation,lexical_value:'4061464939738'}}},
  {detail:{fields:{imageUrlReferences:{state:'rights-held',value:[OFF_PHOTOS[0].url]}}}}
 ]){const h=dom();h.mounted.show(showInput(selected));assert.equal(h.thumbnail.dataset.visualTier,'app-fallback');assert.equal(h.thumbnail.firstChild.src,'/scanner-balanced-final.svg');assert.ok(!h.caption.children.some(n=>n.tagName==='details'));h.mounted.destroy?.();}
});
test('photo load failure uses existing fallback then text; stale photo errors cannot replace a new selection',()=>{
 const h=dom();h.mounted.show(qualified());const photo=h.thumbnail.firstChild;assert.equal(h.thumbnail.dataset.visualTier,'product-photo');photo.onerror();assert.equal(h.thumbnail.dataset.visualTier,'app-fallback');assert.equal(h.thumbnail.firstChild.src,'/scanner-balanced-final.svg');h.thumbnail.firstChild.onerror();assert.equal(h.thumbnail.firstChild.tagName,'span');assert.equal(h.thumbnail.firstChild.textContent,'OffMenu');
 h.mounted.show({...qualified(),entryId:'new-generated-entry'});const old=h.thumbnail.firstChild;h.mounted.show({entryId:'new-unknown',reference:null});const next=h.thumbnail.firstChild;old.onerror();assert.equal(h.thumbnail.firstChild,next);h.mounted.destroy?.();
});
test('offline uncached photo and changed observation identity keep honest fallback; inputs remain exact',()=>{
 const h=dom(),f=qualified(),before=structuredClone(f);h.mounted.show({...f,offline:true});assert.equal(h.thumbnail.dataset.visualTier,'app-fallback');assert.deepEqual(f,before);
 const changed=structuredClone(f);changed.reference.observationKey.assertion_id++;h.mounted.show(changed);assert.equal(h.thumbnail.dataset.visualTier,'app-fallback');h.mounted.destroy?.();
});
