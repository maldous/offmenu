import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
const root=process.env.OFFMENU_SCANNER_SOURCE_ROOT||new URL('../..',import.meta.url).pathname;
const {createPublicLookup,mergeIdentifierPages}=await import(pathToFileURL(root+'/apps/web/src/production-scanner/scanner-production-lookup.js'));
const H=await import(pathToFileURL(root+'/apps/web/src/scanner-kitchen-handoff.js'));
const {validateLot}=await import(pathToFileURL(root+'/apps/web/src/model.js'));
const selection=H.PUBLIC_PRODUCT_SELECTION;
const id='11111111-1111-4111-8111-111111111111';
const record=(value,key='one')=>({id:'offmenu:product:'+key,kind:'product',countries:['AU'],data:{name:'Generated product',identifiers:[{system:'barcode',value}]},provenance:{sourceId:'off',visibility:'public',license:'ODbL',attribution:'Generated OFF attribution',sourceDate:null}});
function harness(responder){const requests=[];return {requests,lookup:createPublicLookup({selection,fetchImpl:async url=>{const u=new URL(url,'https://example.invalid');requests.push(u);const payload=await responder(u,requests.length);return {ok:true,text:async()=>JSON.stringify({...selection,...payload})};}})};}
const entry=(raw,result,selected=result.matches[0])=>({...result,id,raw,selectedRecord:selected});
test('one result with another source page stays ambiguous on first page and merge',async()=>{
 const h=harness(u=>({records:[record('12345678')],nextCursor:u.searchParams.get('cursor')?null:'source-next'}));
 const a=await h.lookup('12345678',1);assert.equal(a.status,'ambiguous');assert.equal(a.hasMore,true);
 const b=await h.lookup('12345678',1,a.nextCursor);assert.equal(b.status,'source-match');
 const empty={...a,matches:[],nextCursor:null};assert.equal(mergeIdentifierPages(empty,a).status,'ambiguous');
 assert.equal(H.createPublicScannerHandoff([entry('12345678',a)]).items.length,1);
 assert.throws(()=>H.createPublicScannerHandoff([entry('12345678',a,null)]),/Choose/);
});
for(const [raw,hint,matched] of [['01234558','UPC-E','012345000058'],['036000291452','UPC-A','0036000291452'],['0036000291452','EAN-13','036000291452'],['080442957X','ISBN-10','9780804429573']]){
 test('labelled '+hint+' preserves capture and matched source lexical form '+raw,async()=>{
  const h=harness(u=>({records:u.searchParams.get('barcode')===matched?[record(matched)]:[],nextCursor:null}));
  let page=await h.lookup(raw,7,null,hint);while(page.hasMore){const next=await h.lookup(raw,7,page.nextCursor,hint);page=mergeIdentifierPages(page,next);}
  assert.equal(page.original,raw);assert.equal(page.status,'source-match');assert.equal(page.matches.length,1);
  assert.equal(page.matches[0].matchContext.sourceLexicalValue,matched);assert.equal(page.matches[0].matchContext.originalLexicalValue,raw);
  assert.ok(h.requests.every(u=>/^\d{4,32}$/.test(u.searchParams.get('barcode'))));
  const handoff=H.createPublicScannerHandoff([entry(raw,page)]),item=handoff.items[0];assert.equal(item.barcode,raw);assert.equal(item.publicProductReference.lexicalValue,matched);assert.equal(item.publicProductReference.capturedLexicalValue,raw);assert.equal(item.publicProductReference.representationHint,hint);
  assert.deepEqual(H.parsePublicScannerHandoff(handoff),handoff);assert.equal(H.validPublicProductReference({...item.publicProductReference,representationHint:null},raw),false);
  assert.equal(validateLot({...item,quantity:1,unit:'count',ingredient:'unmapped'}).barcode,raw);
 });
}
test('unlabelled, bad-checksum and unsupported namespace never gain aliases',async()=>{
 for(const [raw,hint,namespace] of [['01234558',null,'barcode'],['036000291453','UPC-A','barcode'],['00036000291452','GTIN-14','barcode'],['080442957X',null,'barcode'],['036000291452','UPC-A','USDA-FDC']]){
  const h=harness(()=>({records:[],nextCursor:null}));const page=await h.lookup(raw,2,null,hint,namespace);assert.equal(page.hasMore,false);assert.ok(h.requests.length<=1);if(h.requests.length)assert.equal(h.requests[0].searchParams.get('barcode'),raw);
 }
});
test('other lexical forms and changed continuation hint cannot bind a returned record',async()=>{
 const h=harness(()=>({records:[record('36000291452')],nextCursor:null}));assert.equal((await h.lookup('036000291452',1,null,'UPC-A')).error,'PUBLIC_RECORD_BINDING');
 const p=harness(()=>({records:[],nextCursor:'source-next'}));const first=await p.lookup('036000291452',1,null,'UPC-A');assert.equal((await p.lookup('036000291452',1,first.nextCursor,'EAN-13')).status,'unavailable');
 assert.throws(()=>mergeIdentifierPages({...first,symbology:'EAN-13'},first));
 assert.throws(()=>mergeIdentifierPages(first,{...first,status:'unavailable',hasMore:false,matches:[]}));
});
test('ISBN X without a qualified public reference cannot enter a kitchen lot',()=>{
 const lot={barcode:'080442957X',name:'Generated',quantity:1,unit:'count',ingredient:'unmapped'};
 assert.throws(()=>validateLot(lot));assert.throws(()=>validateLot({...lot,publicProductReference:{lexicalValue:'9780804429573',capturedLexicalValue:lot.barcode,representationHint:'ISBN-10'}}));
});
test('same immutable source record found by two aliases remains one record after completion',async()=>{
 const r=record('036000291452');r.data.identifiers.push({system:'barcode',value:'0036000291452'});
 const h=harness(()=>({records:[r],nextCursor:null}));const a=await h.lookup('036000291452',9,null,'UPC-A');assert.equal(a.status,'ambiguous');
 const b=await h.lookup('036000291452',9,a.nextCursor,'UPC-A');const merged=mergeIdentifierPages(a,b);assert.equal(merged.status,'source-match');assert.equal(merged.matches.length,1);assert.equal(merged.matches[0].matchContext.sourceLexicalValue,'036000291452');
 assert.throws(()=>mergeIdentifierPages(a,{...b,matches:[{...b.matches[0],publicRecord:{...r,countries:['NZ']}}]}),/record changed/);
});
test('exact numeric handoff retains existing reference shape and rejects foreign selections',async()=>{
 const h=harness(()=>({records:[record('12345678')],nextCursor:null}));const page=await h.lookup('12345678',3);const item=H.createPublicScannerHandoff([entry('12345678',page)]).items[0];assert.equal(item.publicProductReference.lexicalValue,'12345678');assert.equal(Object.hasOwn(item.publicProductReference,'capturedLexicalValue'),false);
 assert.throws(()=>H.createPublicScannerHandoff([entry('12345678',page,{...page.matches[0]})]),/Choose/);
});
