import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {analyzeIdentifier, validateGTIN, validateISBN10, validateISBN13,
  expandUPCE, isbn10To13, isbn13To10, janNaming, representationFromCarrier,
  CONTRACT_VERSION, CITATIONS} from '../public/typed-identifier-contract.mjs';

const fixtures=JSON.parse(readFileSync(new URL('./fixtures/typed-identifier-contract.generated.json',import.meta.url),'utf8'));
const input=(original,representationHint=null,extra={})=>({original,namespace:'barcode',representationHint,...extra});
const badCheck=value=>value.slice(0,-1)+String((Number(value.at(-1))+1)%10);

test('official explicit UPC-E expands to GTIN-12, never the raw GTIN-8 interpretation',()=>{
  const {UPCE,GTIN12}=fixtures.official;
  assert.equal(expandUPCE(UPCE),GTIN12);
  const typed=analyzeIdentifier(input(UPCE,'UPC-E'));
  assert.equal(typed.comparisonGTIN14,GTIN12.padStart(14,'0'));
  assert.notEqual(typed.comparisonGTIN14,UPCE.padStart(14,'0'));
  assert.equal(typed.original,UPCE);
  assert.equal(typed.validatedRepresentation,'UPC-E');
  assert.deepEqual(typed.labelledEquivalents.map(x=>x.value),[GTIN12,'0'+GTIN12]);
});
test('same eight characters remain ambiguous without a hint even when both checksums fit',()=>{
  const value=fixtures.official.UPCE;
  assert.equal(validateGTIN(value),true);
  const unknown=analyzeIdentifier(input(value));
  assert.equal(unknown.status,'ambiguous');
  assert.equal(unknown.comparisonGTIN14,null);
  assert.equal(unknown.possibleRepresentations.length,2);
  const ean=analyzeIdentifier(input(value,'EAN-8'));
  assert.equal(ean.comparisonGTIN14,value.padStart(14,'0'));
  assert.equal(ean.labelledEquivalents.length,0);
});
test('an explicit hint conflicting with a decoder label is not silently preferred',()=>{
  const value=fixtures.official.UPCE;
  for(const [hint,carrier] of [['EAN-8','UPC-E'],['UPC-E','EAN-8']]){
    const r=analyzeIdentifier(input(value,hint,{observedCarrier:carrier}));
    assert.equal(r.status,'conflict'); assert.equal(r.comparisonGTIN14,null);
  }
});
test('official ISBN conversion and terminal-X arithmetic do not assert allocation',()=>{
  const {ISBN10,ISBN13}=fixtures.official;
  assert.equal(validateISBN10(ISBN10),true);
  assert.equal(isbn10To13(ISBN10),ISBN13);
  assert.deepEqual(isbn13To10(ISBN13),{status:'converted',value:ISBN10,allocationStatus:'not-verified'});
  assert.equal(validateISBN10('000000006X'),true);
  assert.equal(validateISBN10('000000006x'),false);
  const r=analyzeIdentifier(input('000000006X','ISBN-10',{namespace:'ISBN'}));
  assert.equal(r.allocationStatus,'not-verified'); assert.equal(r.catalogueStatus,'not-queried');
  assert.equal(r.namespace,'ISBN'); assert.equal(r.productIdentityAsserted,false);
});
test('979 has no ISBN-10 equivalent and arbitrary valid EAN is not ISBN',()=>{
  const r=analyzeIdentifier(input(fixtures.isbn979[0],'ISBN-13'));
  assert.equal(r.status,'checksum-valid'); assert.equal(r.isbn10Availability,'no-equivalent');
  assert.equal(r.isbn10Equivalent,null); assert.equal(r.allocationStatus,'not-verified');
  assert.equal(validateISBN13('078742003986'),false);
  assert.equal(validateISBN13('0078742003986'),false);
  assert.equal(analyzeIdentifier(input('0078742003986','ISBN-13')).status,'invalid');
  assert.equal(isbn13To10(badCheck(fixtures.isbn979[0])).status,'invalid');
});
test('JAN is explicit EAN naming, never a manufacture-country inference',()=>{
  for(const [name,width,ean] of [['JAN-8',8,'EAN-8'],['JAN-13',13,'EAN-13']]){
    const value=fixtures.gtins.find(x=>x.hint==='GTIN-'+width).value;
    const r=analyzeIdentifier(input(value,name));
    assert.equal(r.effectiveHint,ean); assert.equal(r.namingRelationship.representation,ean);
    assert.equal(r.countryOfManufacture,null); assert.equal(r.namingRelationship.countryOfManufacture,null);
  }
  assert.equal(janNaming('JAN').representation,null);
  assert.equal(analyzeIdentifier(input(fixtures.official.UPCE,'JAN')).status,'hint-required');
});
test('generic ITF never automatically becomes GTIN, while a specific ITF-14 label is typed',()=>{
  const value=fixtures.packaging.otherPackagingGTIN14;
  assert.equal(representationFromCarrier('ITF'),null);
  assert.equal(representationFromCarrier('itf'),null);
  const generic=analyzeIdentifier(input(value,null,{observedCarrier:'ITF'}));
  assert.equal(generic.status,'untyped'); assert.equal(generic.comparisonGTIN14,null);
  const specific=analyzeIdentifier(input(value,null,{observedCarrier:'ITF-14'}));
  assert.equal(specific.status,'checksum-valid'); assert.equal(specific.comparisonGTIN14,value);
  assert.equal(specific.physicalCarrierStatus,'caller-label-only');
  const declared=analyzeIdentifier(input(value,'GTIN-14',{observedCarrier:'ITF'}));
  assert.equal(declared.observedCarrier,'ITF'); assert.equal(declared.physicalCarrierStatus,'caller-label-only');
});
test('comparison padding never collapses a nonzero packaging indicator or invents a pack relation',()=>{
  const p=fixtures.packaging;
  const unit=analyzeIdentifier(input(p.unitOriginal,'UPC-A'));
  const pack=analyzeIdentifier(input(p.otherPackagingGTIN14,'GTIN-14'));
  assert.equal(unit.comparisonGTIN14,p.unitComparisonGTIN14);
  assert.notEqual(unit.comparisonGTIN14,pack.comparisonGTIN14);
  assert.equal(pack.gtin14LeadingDigit,'1'); assert.equal(pack.packagingRelationship,'not-established');
});
test('original/source/namespace/provider lookup input survive without coercion or mutation',()=>{
  const original=fixtures.official.UPCE;
  const context=Object.freeze(input(original,'UPC-E',{
    namespace:'source-specific:barcode',sourceLexicalValue:fixtures.official.GTIN12,sourceId:'retained-source',
  }));
  const r=analyzeIdentifier(context);
  assert.equal(r.original,original); assert.equal(r.lookupOriginal,original);
  assert.equal(r.sourceLexicalValue,context.sourceLexicalValue); assert.equal(r.sourceId,'retained-source');
  assert.equal(r.namespace,'source-specific:barcode'); assert.equal(r.lookupContract,'caller-owned');
  assert.equal(Object.isFrozen(r),true); assert.equal(Object.isFrozen(r.labelledEquivalents),true);
  assert.equal(Object.isFrozen(r.labelledEquivalents[0]),true);
  assert.throws(()=>{r.original='changed';},TypeError);
  const literal=analyzeIdentifier(input(' javascript:alert(1) '));
  assert.equal(literal.lookupOriginal,' javascript:alert(1) '); assert.equal(literal.status,'untyped');
  assert.equal(analyzeIdentifier(input('078742003986',null,{namespace:'USDA-FDC'})).comparisonGTIN14,null);
});
test('invalid syntax/checksum produces no validated aliases but preserves the input',()=>{
  for(const value of [' 078742003986','078742003986 ','０78742003986','07874200398X']){
    const r=analyzeIdentifier(input(value,'UPC-A'));
    assert.equal(r.status,'invalid'); assert.equal(r.syntaxValid,false); assert.equal(r.checksumValid,null);
    assert.equal(r.original,value); assert.equal(r.comparisonGTIN14,null);
  }
  const bad=badCheck('078742003986'); const r=analyzeIdentifier(input(bad,'UPC-A'));
  assert.equal(r.syntaxValid,true); assert.equal(r.checksumValid,false); assert.equal(r.labelledEquivalents.length,0);
  assert.equal(expandUPCE('21234558'),null);
  assert.equal(isbn10To13('0471384292'),null);
});
test('explicit caller metadata is required; no numeric identifier coercion',()=>{
  for(const value of [null,{},[],{original:123,namespace:'barcode'},{original:'001',namespace:''}])
    assert.throws(()=>analyzeIdentifier(value),TypeError);
  assert.equal(analyzeIdentifier(input('001','__proto__')).status,'invalid');
  assert.throws(()=>analyzeIdentifier(input('001',null,{sourceId:{id:1}})),TypeError);
  assert.equal(CONTRACT_VERSION,'offmenu-typed-identifier/1');
  assert.equal(Object.isFrozen(CITATIONS),true);
});

for(const row of fixtures.gtins) test(`generated ${row.hint} ${row.value}`,()=>{
  assert.equal(validateGTIN(row.value),true);
  const r=analyzeIdentifier(input(row.value,row.hint));
  assert.equal(r.status,'checksum-valid'); assert.equal(r.comparisonGTIN14,row.comparisonGTIN14);
  assert.equal(r.allocationStatus,'not-verified'); assert.equal(r.catalogueStatus,'not-queried');
  assert.equal(r.productIdentityAsserted,false); assert.equal(r.ingredientClassification,'not-assessed');
  assert.equal(validateGTIN(badCheck(row.value)),false);
});
for(const row of fixtures.upces) test(`generated explicit UPC-E ${row.original}`,()=>{
  assert.equal(expandUPCE(row.original),row.expandedGTIN12);
  const r=analyzeIdentifier(input(row.original,'UPC-E'));
  assert.equal(r.comparisonGTIN14,row.expandedGTIN12.padStart(14,'0'));
  assert.equal(r.original,row.original); assert.equal(r.labelledEquivalents[0].representation,'GTIN-12');
  assert.equal(expandUPCE(badCheck(row.original)),null);
});
for(const row of fixtures.isbns) test(`generated ISBN pair ${row.ISBN10}`,()=>{
  assert.equal(validateISBN10(row.ISBN10),true); assert.equal(validateISBN13(row.ISBN13),true);
  assert.equal(isbn10To13(row.ISBN10),row.ISBN13); assert.equal(isbn13To10(row.ISBN13).value,row.ISBN10);
  assert.equal(validateISBN13(badCheck(row.ISBN13)),false);
});
for(const value of fixtures.isbn979) test(`generated 979 no inverse ${value}`,()=>{
  assert.equal(validateISBN13(value),true); assert.equal(isbn13To10(value).status,'no-equivalent');
  const r=analyzeIdentifier(input(value,'ISBN-13'));
  assert.equal(r.isbn10Equivalent,null); assert.equal(r.allocationStatus,'not-verified');
});
