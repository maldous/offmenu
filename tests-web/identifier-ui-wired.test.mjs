import test from 'node:test';
import assert from 'node:assert/strict';
import {IDENTIFIER_DB,IDENTIFIER_RUN,DETAIL_SELECTION,expectedForms} from '../public/scanner-identity-v2.js';
import {projectIdentifierPage,mergeIdentifierPages,loadSelectedDetails,sourceObservationReference,currentSavedReference} from '../public/scanner-identifiers.js';
import {validSourceObservationReference,validateLot} from '../public/model.js';

const original='036000291452',alias='0036000291452';
const row=(id,lexical=original,disposition='source-asserted')=>({assertion_id:id,run_id:IDENTIFIER_RUN,
 input_id:'synthetic:input',record_ordinal:id,namespace:'barcode',lexical_value:lexical,
 disposition,source_id:'off',release_id:'synthetic-release',source_record_id:String(id),native_record_id:'synthetic:'+id});
function packet(rows,{raw=original,generation=3,hasMore=false,cursor=null,partial=false}={}){
 const forms=expectedForms(raw);
 return {databaseSha256:IDENTIFIER_DB,generation:String(generation),identitySearchPlanVersion:2,
  operation:'identifier-search',rows,identityMatches:rows.map(r=>({assertionId:r.assertion_id,
   sourceLexicalValue:r.lexical_value,matchType:forms.find(f=>f.lexicalValue===r.lexical_value)?.matchType,
   equivalence:forms.find(f=>f.lexicalValue===r.lexical_value)?.equivalence,disposition:r.disposition})),
  identityQuery:{namespace:'barcode',originalLexicalValue:raw,symbology:null,forms},
  identitySearchState:partial?'partial':'available',identitySearchCoverage:{state:partial?'partial':hasMore?'page-available':'complete-for-selected-index-and-query-plan',
   failures:partial?[{lane:1,reasonCode:'IDENTITY_LANE_UNAVAILABLE'}]:[],physicalProductIdentityAsserted:false,ingredientQualificationAsserted:false},
  hasMore,nextCursor:hasMore?cursor:null,nextAssertionId:null};
}

test('wired selected-index pages retain alias, uncertain disposition and empty continuation',()=>{
 const first=projectIdentifierPage(packet([row(1)],{hasMore:true,cursor:'opaque'}),original,3);
 const second=projectIdentifierPage(packet([row(2,alias,'unresolved')],{hasMore:true,cursor:'next'}),original,3,{cursor:'opaque'});
 const merged=mergeIdentifierPages(first,second);
 assert.equal(merged.matches.length,2);assert.equal(merged.matches[1].matchContext.matchType,'representation-alias');
 assert.equal(merged.matches[1].identifier.disposition,'unresolved');assert.equal(merged.nextCursor,'next');
 const empty=projectIdentifierPage(packet([],{hasMore:true,cursor:'opaque'}),original,3);
 assert.equal(empty.status,'searching');assert.equal(empty.hasMore,true);
 const partial=projectIdentifierPage(packet([],{hasMore:true,cursor:'opaque',partial:true}),original,3);
 assert.equal(partial.status,'partial');
 assert.equal(projectIdentifierPage(packet([]),original,3).status,'scoped-miss');
});

test('selected source reference survives kitchen and pantry validation with both lexical forms',()=>{
 const page=projectIdentifierPage(packet([row(2,alias,'unresolved')]),original,3);
 const ref=sourceObservationReference(page.matches[0],page);
 assert.equal(ref.detailSelectionSha256,DETAIL_SELECTION);
 assert.equal(ref.originalLexicalValue,original);assert.equal(ref.sourceLexicalValue,alias);
 assert.equal(validSourceObservationReference(ref,original),true);
 const lot=validateLot({barcode:original,name:'Synthetic observation',ingredient:'unmapped',quantity:1,
  unit:'count',sourceObservationReference:ref,needsReview:true});
 assert.deepEqual(lot.sourceObservationReference,ref);
 assert.equal(validSourceObservationReference({...ref,sourceLexicalValue:'arbitrary'},original),false);
 assert.equal(currentSavedReference(ref,page),true);
 assert.equal(currentSavedReference({...ref,schema:'offmenu-identifier-observation/1'},page),false);
 assert.equal(currentSavedReference({...ref,detailSelectionSha256:'12c2c7c8406807aaece00c1bbf7f9f0d025e06be6ca39403798169f4df8f5fa2'},page),false);
 const historical={schema:'offmenu-identifier-observation/1',databaseSha256:IDENTIFIER_DB,runId:IDENTIFIER_RUN,
  namespace:'barcode',lexicalValue:original,sourceId:'off',releaseId:'synthetic-release',sourceRecordId:'2',
  observationKey:ref.observationKey,detailSelectionSha256:'12c2c7c8406807aaece00c1bbf7f9f0d025e06be6ca39403798169f4df8f5fa2'};
 assert.equal(validSourceObservationReference(historical,original),true);
 assert.equal(currentSavedReference(historical,page),false);
});

test('lazy selected detail carries all source variants; typed failure leaves original row',async()=>{
 const page=projectIdentifierPage(packet([row(2,alias,'unresolved')]),original,3);
 const match=page.matches[0],originalFetch=globalThis.fetch,calls=[];
 const observationKey={databaseSha256:IDENTIFIER_DB,run_id:IDENTIFIER_RUN,input_id:'synthetic:input',record_ordinal:2,assertion_id:2};
 const product=(id,name)=>({referenceRecordId:id,observationKey,sourceObservation:{source_id:'off',release_id:'synthetic-release',namespace:'barcode',lexical_value:alias},fields:{name:{state:'present',value:name},brand:{state:'missing'}}});
 try{
  const responses=[{queryAvailable:true,identitySearchPlanVersion:2,databaseSha256:IDENTIFIER_DB,runId:IDENTIFIER_RUN,detailSelectionSha256:DETAIL_SELECTION},
   {...packet([row(2,alias,'unresolved')]),operation:'observation-detail',details:{state:'ambiguous',detailBackend:'retained-product-federation-v1',detailSelectionSha256:DETAIL_SELECTION,
    sourceProducts:[product('one','Synthetic A'),product('two','Synthetic B')],productDetailAvailability:[]}}];
  globalThis.fetch=async(url,options)=>{calls.push({url,options});return {ok:true,json:async()=>responses.shift()};};
  const result=await loadSelectedDetails(match,page,3);
  assert.equal(result.variants.length,2);assert.equal(result.variants[0].name,'Synthetic A');
  assert.equal(match.identifier.assertion_id,2);
  const request=JSON.parse(calls[1].options.body);
  assert.deepEqual([request.lexical_value,request.detailLexicalValue,request.detailDisposition,request.detailAssertionId],
   [original,alias,'unresolved',2]);
  globalThis.fetch=async url=>url.endsWith('/status')?{ok:true,json:async()=>responses[0]||{queryAvailable:true,identitySearchPlanVersion:2,databaseSha256:IDENTIFIER_DB,runId:IDENTIFIER_RUN,detailSelectionSha256:DETAIL_SELECTION}}:{ok:false,json:async()=>({error:'DETAIL_RESPONSE_BOUND'})};
  const failed=await loadSelectedDetails(match,page,3);
  assert.equal(failed.status,'detail-unavailable');assert.equal(failed.reference.observationKey.assertion_id,2);
  assert.equal(match.identifier.assertion_id,2);
 }finally{globalThis.fetch=originalFetch;}
});
