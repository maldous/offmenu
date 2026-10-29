import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
import {parse} from 'acorn';
import * as identity from '../../public/scanner-identity-v2.js';
import * as shim from '../../public/scanner-identifiers.js';
import {PUBLIC_SCANNER_HANDOFF} from '../../public/scanner-kitchen-handoff.js';
const source=readFileSync(new URL('../../public/shelf-scanner.js',import.meta.url),'utf8');
const nodes=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body;
const fn=name=>{const n=nodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name===name);assert.ok(n);return source.slice(n.start,n.end);};
const assignment=(id,property)=>{const n=nodes.find(n=>n.type==='ExpressionStatement'&&n.expression.type==='AssignmentExpression'&&n.expression.left.type==='MemberExpression'&&n.expression.left.property.name===property&&n.expression.left.object.type==='CallExpression'&&n.expression.left.object.arguments[0]?.value===id);assert.ok(n,id);return source.slice(n.start,n.end);};
const formats=nodes.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='CAPTURE_FORMATS'));
const prefill=nodes.find(n=>n.type==='VariableDeclaration'&&n.declarations.some(d=>d.id.name==='kitchenPrefill'));
const prefillIf=nodes.find(n=>n.type==='IfStatement'&&n.test.type==='Identifier'&&n.test.name==='kitchenPrefill');
function wire(raw,namespace,symbology,generation){
 const forms=identity.expectedForms(raw,symbology,namespace),rows=[1,2].map(id=>({assertion_id:id,run_id:identity.IDENTIFIER_RUN,input_id:'generated-only',record_ordinal:id,namespace,lexical_value:raw,disposition:'source-asserted',source_id:'off',release_id:'generated-only',source_record_id:String(id),native_record_id:'generated:'+id}));
 return {databaseSha256:identity.IDENTIFIER_DB,generation:String(generation),identitySearchPlanVersion:2,operation:'identifier-search',rows,identityMatches:rows.map(row=>({assertionId:row.assertion_id,sourceLexicalValue:raw,disposition:row.disposition,matchType:'exact',equivalence:null})),identityQuery:{namespace,originalLexicalValue:raw,symbology,forms},identitySearchState:'available',identitySearchCoverage:{state:'complete-for-selected-index-and-query-plan',failures:[],physicalProductIdentityAsserted:false,ingredientQualificationAsserted:false},hasMore:false,nextCursor:null};
}
function harness(namespace,symbology,raw){
 const oldPage=shim.projectIdentifierPage(wire(raw,namespace,symbology,1),raw,1,{namespace,symbology});
 const ref=shim.sourceObservationReference(oldPage.matches[0],oldPage);assert.equal(identity.validSourceObservationReference(ref,raw),true);
 const values=new Map(),$=id=>{if(!values.has(id))values.set(id,{value:'',disabled:false});return values.get(id);};
 const key='generated-prefill',storage=new Map([[key,JSON.stringify({schema:'offmenu-kitchen-scanner-prefill/1',raw,namespace,sourceObservationReference:ref})]]),queries=[];
 const ctx={$,SCANNER_PREFILL:key,sessionStorage:{getItem:k=>storage.get(k)??null,removeItem:k=>storage.delete(k)},validSourceObservationReference:identity.validSourceObservationReference,currentSavedReference:shim.currentSavedReference,requestedSourceReference:null,open(){},close(){},message(v){ctx.lastMessage=v;},crypto,sheetTouched:false,setSheetSnap(){},innerWidth:900,active:true,paused:false,processed:new Set(),generation:0,queue:[],current:null,selected:null,mode:'Explore',connection:'live',render(){},readTone(){},scanner:{noteAccepted(){}},lookupIdentifiers:async(value,generation,cursor,representation,ns)=>{queries.push({value,generation,cursor,representation,ns});return shim.projectIdentifierPage(wire(value,ns,representation,generation),value,generation,{namespace:ns,symbology:representation});},inspectMatch:async()=>{}};
 vm.createContext(ctx);vm.runInContext([fn('readKitchenPrefill'),fn('capture'),source.slice(formats.start,formats.end),assignment('manual-namespace','onchange'),assignment('manual','onsubmit'),source.slice(prefill.start,prefill.end),source.slice(prefillIf.start,prefillIf.end)].join('\n'),ctx);
 return {ctx,$,ref,queries};
}
for(const [namespace,symbology,raw] of [
 ['barcode','UPC-A','036000291452'],['barcode','EAN-13','0036000291452'],
 ['barcode','EAN-8','96385074'],['barcode','GTIN-14','00036000291452'],
 ['barcode','UPC-E','01234558'],['USDA-FDC',null,'1105904']
])test('actual unchanged manual prefill preserves '+namespace+' '+symbology,async()=>{
 const h=harness(namespace,symbology,raw);h.$('manual').onsubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.queries[0].ns,namespace);assert.equal(h.queries[0].representation,symbology);assert.equal(h.ctx.selected.identifier.assertion_id,h.ref.observationKey.assertion_id);assert.equal(shim.currentSavedReference(h.ref,h.ctx.current),true);
});

test('supported saved camera hints are actual manual choices, not inferred from eight digits',()=>{
 const html=readFileSync(new URL('../../public/shelf-scanner.html',import.meta.url),'utf8');
 for(const format of ['UPC-A','EAN-13','EAN-8','GTIN-14','UPC-E'])
  assert.match(html,new RegExp('<option value="'+format+'">'));
 assert.deepEqual(identity.expectedForms('01234558',null).map(form=>form.lexicalValue),['01234558']);
});

for(const edit of ['lexical','namespace','representation'])test('genuine '+edit+' edit clears the saved assertion choice',async()=>{
 const h=harness('barcode','UPC-A','036000291452');
 if(edit==='lexical')h.$('barcode').value='036000291453';
 if(edit==='namespace'){h.$('manual-namespace').value='USDA-FDC';h.$('manual-namespace').onchange();}
 if(edit==='representation')h.$('manual-representation').value='';
 h.$('manual').onsubmit({preventDefault(){}});await new Promise(resolve=>setImmediate(resolve));
 assert.equal(h.ctx.requestedSourceReference,null);
 assert.equal(h.ctx.selected,null);
 assert.equal(h.ctx.current.matches.length,2);
 assert.doesNotMatch(h.ctx.lastMessage||'',/Historical source reference retained/);
});

for(const [namespace,symbology,raw] of [['USDA-FDC',null,'001105904'],['barcode','UPC-E','01234558']])test('lazy selected detail and actual kitchen reader preserve '+namespace+' '+symbology,async()=>{
 const page=shim.projectIdentifierPage(wire(raw,namespace,symbology,7),raw,7,{namespace,symbology}),match=page.matches[0],ref=shim.sourceObservationReference(match,page),requests=[];
 const previous=globalThis.fetch;globalThis.fetch=async(path,options)=>{
  requests.push({path,options});if(path.endsWith('/status'))return Response.json({queryAvailable:true,identitySearchPlanVersion:2,databaseSha256:identity.IDENTIFIER_DB,runId:identity.IDENTIFIER_RUN,detailSelectionSha256:identity.DETAIL_SELECTION});
  const q=JSON.parse(options.body);assert.equal(q.namespace,namespace);assert.equal(q.lexical_value,raw);assert.equal(q.symbology,symbology??undefined);
  const row=match.identifier,product={observationKey:{databaseSha256:identity.IDENTIFIER_DB,...ref.observationKey},sourceObservation:row,fields:{name:{state:'present',value:'Generated selected source'},brand:{state:'null',value:null},ingredientDeclaration:{state:'missing',value:null}}};
  return Response.json({databaseSha256:identity.IDENTIFIER_DB,generation:'7',operation:'observation-detail',rows:[row],identityMatches:[{assertionId:row.assertion_id,sourceLexicalValue:row.lexical_value,disposition:row.disposition,matchType:'exact',equivalence:null}],details:{detailSelectionSha256:identity.DETAIL_SELECTION,detailBackend:'retained-product-federation-v1',state:'loaded',sourceProducts:[product],productDetailAvailability:[]}});
 };
 try{
  const detail=await shim.loadSelectedDetails(match,page,7);assert.equal(detail.status,'loaded');assert.equal(detail.variants.length,1);assert.equal(detail.reference.namespace,namespace);assert.equal(detail.reference.originalLexicalValue,raw);
  assert.equal(requests[0].path,'/__dev/identifiers/status');assert.equal(requests[0].options.body,undefined);
  const app=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8'),appNodes=parse(app,{ecmaVersion:'latest',sourceType:'module'}).body,reader=appNodes.find(n=>n.type==='FunctionDeclaration'&&n.id.name==='readScannerImport');
  const payload={schema:'offmenu-scanner-kitchen-handoff/1',operationId:'11111111-1111-4111-8111-111111111111',barcode:raw,identifierNamespace:namespace,representationHint:symbology,sourceId:ref.sourceId,releaseId:ref.releaseId,name:'Generated',brand:null,assertionId:ref.observationKey.assertion_id,sourceObservationReference:ref};let stored=JSON.stringify(payload);
  const ctx={PUBLIC_SCANNER_HANDOFF,lifecycleFixture:false,location:{search:'?scan=staged'},URLSearchParams,KITCHEN_HANDOFF:'generated-handoff',validSourceObservationReference:identity.validSourceObservationReference,sessionStorage:{getItem:()=>stored},crypto};vm.createContext(ctx);vm.runInContext(app.slice(reader.start,reader.end),ctx);
  const result=ctx.readScannerImport();assert.ok(result);assert.equal(result.barcode,raw);assert.equal(result.identifierNamespace,namespace);assert.equal(result.representationHint,symbology);assert.equal(result.sourceObservationReference.namespace,namespace);
  stored=JSON.stringify({...payload,identifierNamespace:namespace==='barcode'?'USDA-FDC':'barcode'});assert.equal(ctx.readScannerImport(),null);
 }finally{globalThis.fetch=previous;}
});
