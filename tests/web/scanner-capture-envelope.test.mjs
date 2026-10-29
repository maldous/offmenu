import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {captureFromDecoder,captureEvidence,projectZXingResult,requiresUPCEConfirmation,selectableCaptures,verifyCaptureEvidence} from '../../public/scanner-capture-envelope.js';
import {expectedForms,projectIdentityPage,sourceObservationReference,
 validSourceObservationReference,exactDetailRequest,IDENTIFIER_DB,IDENTIFIER_RUN} from '../../public/scanner-identity-v2.js';
import {setupScanner} from '../../public/scanner-ui.js';

// Worker19 decoder-fixtures-verified/generation-and-decode-proof.json,
// reviewed by Worker56. These are invented symbols, never catalogue records.
const upce={text:'0012345000058',format:'UPCE',error:null,extra:'{"UPCE":"01234558"}'};
const upca={text:'0012345000058',format:'UPCA',error:null,extra:null};

test('worker projection retains exact ZXing text, format, error and extra; UPC-E lookup stays compressed',()=>{
 const worker=readFileSync(new URL('../../public/scanner-worker.js',import.meta.url),'utf8');
 assert.match(worker,/results\.map\(projectZXingResult\)/);
 assert.deepEqual(projectZXingResult(upce),upce);
 const capture=captureFromDecoder(projectZXingResult(upce),'zxing-wasm');
 assert.equal(capture.schema,'offmenu-decoder-capture/1');
 assert.equal(capture.decoderText,upce.text);
 assert.equal(capture.returnedFormat,upce.format);
 assert.equal(capture.rawExtra,upce.extra);
 assert.equal(capture.lookupLexicalValue,'01234558');
 assert.equal(capture.lookupSymbology,'UPC-E');
 assert.equal(capture.lookupOrigin,'validated-decoder-extra.UPCE');
 assert.equal(capture.typed.status,'checksum-valid');
 assert.deepEqual(expectedForms(capture.lookupLexicalValue,capture.lookupSymbology)
   .map(x=>x.lexicalValue),['01234558','012345000058','0012345000058']);
 const evidence=captureEvidence(capture);
 assert.equal(verifyCaptureEvidence(evidence,'01234558','UPC-E'),true);
 assert.equal(verifyCaptureEvidence(evidence,'0012345000058','UPC-E'),false);
 assert.equal(verifyCaptureEvidence(evidence,'01234558',null),false);
});

test('missing or conflicting UPC-E extra never fabricates compressed original',()=>{
 for(const extra of [null,'{}','{"UPCE":"01234559"}','{"UPCE":"01234558"'.repeat(2000)]){
  const capture=captureFromDecoder({...upce,extra},'zxing-wasm');
  assert.equal(capture.status,'manual-required');
  assert.equal(capture.lookupLexicalValue,null);
  assert.equal(captureEvidence(capture),null);
 }
 assert.deepEqual(selectableCaptures([{...upce,extra:null}],'zxing-wasm'),[]);
 assert.equal(requiresUPCEConfirmation([{...upce,extra:null},{text:upce.text,format:'EAN13'}],'zxing-wasm'),true);
});

test('validated worker capture binds exact lookup, continuation inputs and saved observation detail',()=>{
 const capture=captureFromDecoder(projectZXingResult(upce),'zxing-wasm');
 const raw=capture.lookupLexicalValue,symbology=capture.lookupSymbology,generation=7;
 const forms=expectedForms(raw,symbology),row={run_id:IDENTIFIER_RUN,input_id:'synthetic',
   record_ordinal:1,assertion_id:901,namespace:'barcode',lexical_value:forms[0].lexicalValue,
   disposition:'source-asserted',source_id:'invented-test',release_id:'fixture-v1',
   source_record_id:'synthetic-901',native_record_id:'synthetic-901'};
 const page=projectIdentityPage({databaseSha256:IDENTIFIER_DB,generation:String(generation),
   identitySearchPlanVersion:2,operation:'identifier-search',rows:[row],
   identityMatches:[{assertionId:901,sourceLexicalValue:raw,disposition:'source-asserted',
     matchType:'exact',equivalence:null}],
   identityQuery:{namespace:'barcode',originalLexicalValue:raw,symbology,forms},
   identitySearchState:'available',identitySearchCoverage:{state:'complete-for-selected-index-and-query-plan',
     failures:[],physicalProductIdentityAsserted:false,ingredientQualificationAsserted:false},
   hasMore:false,nextCursor:null},raw,generation,{namespace:'barcode',symbology});
 const reference=sourceObservationReference(page.matches[0],page);
 assert.equal(reference.originalLexicalValue,'01234558');
 assert.equal(reference.symbology,'UPC-E');
 assert.equal(reference.sourceLexicalValue,'01234558');
 assert.equal(validSourceObservationReference(reference,raw),true);
 assert.equal(exactDetailRequest(reference,8).lexical_value,raw);
 assert.equal(validSourceObservationReference(reference,upce.text),false);
});

test('UPC-A leading-zero decoder text is looked up as returned, with derived 12 digits labelled separately',()=>{
 const capture=captureFromDecoder(projectZXingResult(upca),'zxing-wasm');
 assert.equal(capture.decoderText,'0012345000058');
 assert.equal(capture.returnedFormat,'UPCA');
 assert.equal(capture.labelledDerived.value,'012345000058');
 assert.equal(capture.lookupLexicalValue,'0012345000058');
 assert.equal(capture.lookupSymbology,null);
 assert.equal(capture.status,'ready');
 assert.match(capture.lookupOrigin,/printed-original-unverified/);
 assert.equal(selectableCaptures([upca],'zxing-wasm')[0].lookupLexicalValue,'0012345000058');
 const evidence=captureEvidence(capture);
 assert.equal(verifyCaptureEvidence(evidence,'0012345000058',null),true);
 assert.equal(verifyCaptureEvidence({...evidence,labelledDerived:{value:'999999999999'}},'0012345000058',null),false);
});

test('generic ITF stays untyped even for a 14-digit checksum-valid symbol; invalid retail never queries',()=>{
 for(const text of ['10078742003983','00078742003986','123457']){
  const capture=captureFromDecoder({text,format:'ITF',extra:null},'zxing-wasm');
  assert.equal(capture.status,'literal-untyped');
  assert.equal(capture.lookupSymbology,null);
  assert.deepEqual(selectableCaptures([{text,format:'ITF'}],'zxing-wasm'),[]);
 }
 assert.equal(captureFromDecoder({text:'01234559',format:'UPCE'},'native').status,'manual-required');
});

test('ITF-14 decoder aliases remain untyped in diagnostics and unselectable',()=>{
 for(const format of ['ITF14','ITF-14']){
  const result={text:'10078742003983',format,extra:null};
  const capture=captureFromDecoder(result,'zxing-wasm');
  assert.equal(capture.returnedFormat,format);
  assert.equal(capture.status,'literal-untyped');
  assert.equal(capture.lookupSymbology,null);
  assert.equal(capture.typed.status,'untyped');
  assert.equal(capture.typed.comparisonGTIN14,null);
  assert.deepEqual(selectableCaptures([result],'zxing-wasm'),[]);
  assert.equal(captureEvidence(capture),null);
 }
});

test('photo worker result reaches scanner callback with separate envelope and exact original',async()=>{
 const elements=new Map();
 class Element {
  constructor(){this.hidden=false;this.disabled=false;this.value='';this.options=[];this.style={};this.classList={add(){},remove(){}};this.files=[];}
  getContext(){return {drawImage(){},getImageData:()=>({data:new Uint8ClampedArray(4)})};}
  add(option){this.options.push(option);} replaceChildren(...children){this.options=children;} setAttribute(){}
 }
 const $=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 globalThis.document={getElementById:$,createElement:()=>new Element(),addEventListener(){}};
 globalThis.window={isSecureContext:true,addEventListener(){}};
 Object.defineProperty(globalThis,'navigator',{configurable:true,value:{}});
 globalThis.localStorage={getItem:()=>null,setItem(){}};
 globalThis.Option=class{constructor(label,value){this.label=label;this.value=value;}};
 globalThis.createImageBitmap=async()=>({width:1,height:1,close(){}});
 globalThis.Worker=class{postMessage({id}){queueMicrotask(()=>this.onmessage({data:{id,results:[projectZXingResult(upce)]}}));}terminate(){}};
 const accepted=[];
 const scanner=setupScanner({canScan:()=>true,onCode:(code,metadata)=>accepted.push({code,metadata}),onStream(){}});
 $('scanner-photo').files=[{size:100}];
 await $('scanner-photo').onchange();
 assert.equal(accepted.length,1);
 assert.equal(accepted[0].code,'01234558');
 assert.equal(accepted[0].metadata.captureEnvelope.decoderText,'0012345000058');
 assert.deepEqual(accepted[0].metadata.originalCaptures,[{value:'01234558',symbology:'UPC-E'}]);
 scanner.stop();
});
