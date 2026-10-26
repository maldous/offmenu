import test from 'node:test';
import assert from 'node:assert/strict';
import {extractRetainedOFFPhotos,offPhotoStorageCode,retainedCataloguePhotoAttribution} from '../public/off-photo-metadata.js';
import {OFF_PHOTOS,selectedPublisherPhotos} from '../public/off-photo-catalogue.js';
import {associateProductVisual} from '../public/product-visual-association.js';
import {mountScannerProductVisual} from '../public/scanner-product-visuals.js';
import {photoFixture} from './fixtures/off-photos/context.mjs';
const C='3017620422003',D='4061464939738',base='https://images.openfoodfacts.org/images/products/301/762/042/2003/';
const url=(role='front',rev='7',size='400',lang='en')=>base+role+'_'+lang+'.'+rev+'.'+size+'.jpg';
const extract=(p,opts={})=>extractRetainedOFFPhotos(p,{selectedSourceCode:C,language:'en',...opts});
const front=p=>extract(p).photos.find(p=>p.role==='front');

test('requested-language legacy fallback uses matching English reconstruction instead of French URL',()=>{
 for(const field of ['image_front_url','image_front_small_url','image_front_thumb_url']){
  const input={code:C,[field]:url('front','7','400','fr'),images:{front_en:{rev:'19',sizes:{400:{}}}}},original=structuredClone(input);
  const result=front(input);assert.equal(result.language,'en');assert.equal(result.url,url('front','19'));assert.equal(result.selectionKind,'reconstructed-from-retained-image-revision-and-size');assert.deepEqual(input,original);
 }
});

test('requested-language legacy fallback is unavailable without matching English revision; unknown request preserves actual language',()=>{
 for(const field of ['image_front_url','image_front_small_url','image_front_thumb_url']){
  const input={code:C,[field]:url('front','7','400','fr')},original=structuredClone(input);
  assert.equal(front(input),undefined);
  assert.equal(extract(input,{language:null}).photos[0].language,'fr');
  assert.deepEqual(input,original);
 }
});

test('synthetic selected_images display/small/thumb order precedes retained image_front URLs, originals exact',()=>{
 for(const selected of [{display:{en:url('front','11')},small:{en:url('front','12')},thumb:{en:url('front','13')}},{small:{en:url('front','12')},thumb:{en:url('front','13')}},{thumb:{en:url('front','13')}}]){
  const product={code:C,selected_images:{front:selected},image_front_url:url('front','1')},copy=structuredClone(product),expected=Object.values(selected)[0].en;
  const result=front(product);assert.equal(result.url,expected);assert.equal(result.selectionKind,'retained-selected-image-url');assert.deepEqual(product,copy);assert.equal(extract(product).usePermissionEstablished,false);
 }
});

test('synthetic retained legacy front URLs preserved without revision rewrite',()=>{
 for(const field of ['image_front_url','image_front_small_url','image_front_thumb_url']){
  const product={code:C,[field]:url('front','3'),images:{front_en:{rev:'999',imgid:'2',sizes:{400:{}}},2:{uploader:'DO NOT BORROW FROM OTHER REVISION'}}};
  const result=front(product);assert.equal(result.url,product[field]);assert.equal(result.revision,'3');assert.equal(result.attribution.author,null);assert.deepEqual(result.attribution.adaptationProvenance.retainedSourceSelection,{});
 }
});

test('synthetic reconstruction requires actual retained role revision and size, no guessed default',()=>{
 const product={code:C,images:{front_en:{rev:'17',imgid:'2',sizes:{200:{}},angle:90},2:{uploader:'fixture-uploader',copyright_notice:'fixture notice',disclaimer:'fixture disclaimer'}}};
 const result=front(product);assert.equal(result.url,url('front','17','200'));assert.equal(result.sourcePointer,'/images/front_en/rev');assert.equal(result.imageId,'2');assert.equal(result.attribution.author.value,'fixture-uploader');assert.equal(result.attribution.adaptationProvenance.retainedSourceSelection.angle,90);assert.equal(result.attribution.notices.length,2);
 for(const images of [{front_en:{sizes:{400:{}}}},{front_en:{rev:'17'}},{front_en:{rev:true,sizes:{400:{}}}},{front_en:{rev:'NaN',sizes:{400:{}}}}])assert.equal(front({code:C,images}),undefined);
});

test('EAN8 storage differs from9–12 padding, identity strings unchanged',()=>{
 const cases=[['12345670','12345670'],['00123456','00123456'],['123456789','0000123456789'],['1234567890','0001234567890'],['12345678901','0012345678901'],['123456789012','0123456789012'],['3017620422003','3017620422003']];
 for(const [code,storage]of cases){assert.equal(offPhotoStorageCode(code),storage);const p={code,images:{front_en:{rev:'8',sizes:{400:{}}}}},packet=extract(p,{selectedSourceCode:code});assert.equal(packet.sourceCode,code);assert.equal(packet.photos[0].sourceCode,code);if(code.length===8)assert.match(packet.photos[0].url,new RegExp('/products/'+code+'/front_en'));else assert.notEqual(packet.photos[0].url.includes('/products/'+code+'/'),true);}
});

test('four image roles remain separate, never substitute nutrition/ingredients/packaging for front',()=>{
 const selected=Object.fromEntries(['front','nutrition','ingredients','packaging'].map(role=>[role,{display:{en:url(role)}}]));
 const result=extract({code:C,selected_images:selected});assert.deepEqual(result.photos.map(p=>p.role),['front','nutrition','ingredients','packaging']);
 assert.equal(front({code:C,selected_images:{nutrition:selected.nutrition}}),undefined);
 assert.equal(front({code:C,selected_images:{front:{display:{en:url('nutrition')}}}}),undefined);
});

test('exact selected sourcecode prevents301 photo association with406 and does not normalize identity joins',()=>{
 assert.equal(extract({code:C,image_front_url:url()},{selectedSourceCode:D}).photos.length,0);
 assert.equal(extract({code:D,image_front_url:url()},{selectedSourceCode:D}).photos.length,0);
 assert.equal(extract({code:'03017620422003',image_front_url:url()},{selectedSourceCode:C}).photos.length,0);
 assert.equal(retainedCataloguePhotoAttribution(OFF_PHOTOS[1],D),null);
});

test('URL safety and declared language are checked; unknown alternatives never acquire credentials or unrelated fields',()=>{
 for(const value of ['https://user:secret@images.openfoodfacts.org/images/products/301/762/042/2003/front_en.7.400.jpg',url()+'?x=1','http:'+url().slice(6),url('front','7','400','fr'),'https://example.invalid/front_en.7.400.jpg']){
  const packet=extract({code:C,selected_images:{front:{display:{en:value}}},credentials:'PRIVATE'});assert.equal(packet.photos.length,0);assert.ok(!JSON.stringify(packet).includes('secret'));assert.ok(!JSON.stringify(packet).includes('PRIVATE'));
 }
});

test('no language is invented for selected_images or revision reconstruction',()=>{
 const p={code:C,selected_images:{front:{display:{en:url()}}},images:{front_en:{rev:'7',sizes:{400:{}}}}};assert.equal(extract(p,{language:null}).photos.length,0);
});

test('photoCCBYSA3 separate fromODbL/DbCL, notices/adaptation and packaging limits stay explicit',()=>{
 const result=front({code:C,image_front_url:url()});const dto=result.attribution;
 assert.equal(dto.photoLicense.name,'CC BY-SA 3.0');assert.equal(dto.photoLicense.url,'https://creativecommons.org/licenses/by-sa/3.0/');assert.deepEqual(dto.databaseLicenses.map(x=>x.name),['ODbL','DbCL']);assert.equal(dto.productUrl,'https://world.openfoodfacts.org/product/'+C);assert.equal(dto.placement,'accessible-photo-details');assert.equal(dto.compactHeaderCredit,false);assert.equal(dto.packagingRights.status,'not-universally-cleared');assert.equal(dto.adaptationProvenance.imageBytesFetched,false);assert.equal(dto.adaptationProvenance.imageBytesChanged,false);
});

test('actual two retained catalogue entries map exact saved URLs/contributors/revisions without claiming raw API extraction or custody',()=>{
 const evidence=OFF_PHOTOS.map(entry=>{const before=structuredClone(entry),dto=retainedCataloguePhotoAttribution(entry,entry.sourceCode);assert.ok(dto);assert.equal(dto.retainedSourceUrl,entry.url);assert.equal(dto.author.value,entry.contributor);assert.equal(dto.revision,entry.revision);assert.deepEqual(entry,before);return {key:entry.key,sourceCode:entry.sourceCode,savedURL:entry.url,dto};});
 assert.equal(evidence.length,2);
});

test('existing catalogue exact observation binding retained; no301 on406 or private10300 enrichment',()=>{
 const f=photoFixture(),candidate=selectedPublisherPhotos(f.reference,f.detail)[0];assert.ok(candidate.rights.attributionDetails);assert.equal(candidate.provenance.sourceCode,'0078742003986');
 const packet=structuredClone(f);packet.reference.sourceLexicalValue=D;packet.reference.originalLexicalValue=D;packet.detail.sourceObservation.lexical_value=D;packet.detail.records[0].data.identifiers[0].value=D;assert.deepEqual(selectedPublisherPhotos(packet.reference,packet.detail),[]);
 const result=associateProductVisual(f);assert.equal(result.visual.tier,'product-photo');assert.equal(result.visual.caption,'Current publisher photo');assert.ok(!result.visual.caption.includes('foodless'));assert.equal(result.visual.rights.attributionDetails.author.value,'foodless');
});

class Node {constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.textContent='';}append(...n){this.children.push(...n);}replaceChildren(...n){this.children=[...n];}get firstChild(){return this.children[0];}}
test('credit/source/licence links are in native accessible details, compact caption contains no credit; no image network infakeDOM',()=>{
 const doc={documentElement:{dataset:{theme:'light'}},createElement:tag=>new Node(tag,doc)},thumb=new Node('div',doc),caption=new Node('div',doc);const mounted=mountScannerProductVisual(thumb,caption);mounted.show(photoFixture());
 assert.equal(caption.children[0].textContent,'Current publisher photo');const details=caption.children.find(n=>n.tagName==='details');assert.ok(details);assert.equal(details.children[0].tagName,'summary');assert.equal(details.children[0].textContent,'Photo source and licence');assert.ok(details.children.some(n=>n.textContent.includes('foodless')));assert.ok(details.children.some(n=>n.tagName==='a'&&n.href==='https://creativecommons.org/licenses/by-sa/3.0/'));assert.ok(details.children.some(n=>n.tagName==='a'&&n.href==='https://world.openfoodfacts.org/product/0078742003986'));assert.ok(details.children.some(n=>n.textContent.includes('Packaging artwork')));mounted.destroy();
});
