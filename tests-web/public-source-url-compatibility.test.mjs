import test from 'node:test';
import assert from 'node:assert/strict';
import {PUBLIC_PRODUCT_REFERENCE,PUBLIC_PRODUCT_SELECTION,validPublicProductReference,copyPublicProductReference,createPublicScannerHandoff,publicHandoffFingerprint} from '../public/scanner-kitchen-handoff.js';
const raw='0000000013131',origin='https://world.openfoodfacts.org';
function reference(url=origin){return {schema:PUBLIC_PRODUCT_REFERENCE,...PUBLIC_PRODUCT_SELECTION,recordId:'offmenu:generated:url-compatibility',namespace:'barcode',lexicalValue:raw,provenance:{sourceId:'off',visibility:'public',license:'Generated licence',attribution:'Generated attribution',url,licenseUrl:null,sourceDate:null}};}
test('bare HTTPS source origin is valid and survives copy, handoff and fingerprint literally',()=>{
 const ref=reference(),before=structuredClone(ref);assert.equal(validPublicProductReference(ref,raw),true);const copy=copyPublicProductReference(ref,raw);assert.deepEqual(copy,before);assert.equal(copy.provenance.url,origin);assert.notEqual(copy.provenance.url,new URL(origin).href);
 const selected={name:'Generated source product',brand:null,publicRecord:{id:ref.recordId,kind:'product',data:{identifiers:[{system:'barcode',value:raw}]},provenance:ref.provenance}};const entry={id:'00000001-1111-4111-8111-111111111111',raw,namespace:'barcode',releaseId:ref.releaseId,manifestSha256:ref.manifestSha256,selectedRecord:selected,matches:[selected]};const handoff=createPublicScannerHandoff([entry]);assert.equal(handoff.items[0].publicProductReference.provenance.url,origin);assert.equal(handoff.items[0].barcode,raw);assert.equal(handoff.items[0].publicProductReference.releaseId,ref.releaseId);assert.equal(handoff.items[0].publicProductReference.manifestSha256,ref.manifestSha256);assert.equal(JSON.parse(publicHandoffFingerprint(handoff.items[0])).publicProductReference.provenance.url,origin);assert.deepEqual(ref,before);
});
test('existing canonical exact URLs and nullable metadata retain their prior behavior',()=>{
 for(const url of [origin+'/',origin+'/product/generated',origin+'/source?x=1#section',null]){const ref=reference(url);assert.equal(validPublicProductReference(ref,raw),true);assert.equal(copyPublicProductReference(ref,raw).provenance.url,url);}
 const ref=reference();ref.provenance.licenseUrl='https://creativecommons.org';assert.equal(validPublicProductReference(ref,raw),true);assert.equal(copyPublicProductReference(ref,raw).provenance.licenseUrl,'https://creativecommons.org');
});
test('unsafe, credentialed and other noncanonical URL forms remain denied',()=>{
 for(const url of ['http://world.openfoodfacts.org','https://reader@world.openfoodfacts.org/','https://WORLD.OPENFOODFACTS.ORG',' https://world.openfoodfacts.org',origin+'?x=1',origin+'#section',origin+'/a/../product','https://world.openfoodfacts.org:443',origin+'\n','javascript:alert(1)'])assert.equal(validPublicProductReference(reference(url),raw),false);
});
test('bare-origin compatibility does not relax barcode, source, release, manifest or namespace binding',()=>{
 for(const change of [{lexicalValue:'0000000013132'},{sourceId:'other'},{releaseId:'other'},{manifestSha256:'0'.repeat(64)},{namespace:'other'}])assert.equal(validPublicProductReference({...reference(),...change},raw),false);
});
