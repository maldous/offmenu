import test from 'node:test';
import assert from 'node:assert/strict';
import {IDENTIFIER_DB, IDENTIFIER_RUN, DETAIL_SELECTION, expectedForms,
  lookupIdentityPage, projectIdentityPage, mergeIdentityPages,
  sourceObservationReference, validSourceObservationReference, exactDetailRequest} from '../public/scanner-identity-v2.js';
import {projectIdentifierPage, currentSavedReference} from '../public/scanner-identifiers.js';
import {validateLot} from '../public/model.js';

const key = (id, namespace, lexical) => ({assertion_id:id,run_id:IDENTIFIER_RUN,
  input_id:'invented-input',record_ordinal:id,namespace,lexical_value:lexical,
  disposition:'source-asserted',source_id:'usda-files',release_id:'invented-release',
  source_record_id:String(id),native_record_id:'invented:'+id});
function page(original, namespace, symbology, rows, {generation='7',hasMore=false,cursor=null}={}) {
  const forms=expectedForms(original,symbology,namespace);
  return {databaseSha256:IDENTIFIER_DB,generation,identitySearchPlanVersion:2,
    operation:'identifier-search',rows,identityMatches:rows.map(row=>({assertionId:row.assertion_id,
      sourceLexicalValue:row.lexical_value,disposition:row.disposition,
      matchType:forms.find(form=>form.lexicalValue===row.lexical_value)?.matchType,
      equivalence:forms.find(form=>form.lexicalValue===row.lexical_value)?.equivalence})),
    identityQuery:{namespace,originalLexicalValue:original,symbology,forms},
    identitySearchState:'available',identitySearchCoverage:{state:hasMore?'page-available':'complete-for-selected-index-and-query-plan',
      failures:[],physicalProductIdentityAsserted:false,ingredientQualificationAsserted:false},
    hasMore,nextCursor:hasMore?cursor:null};
}

test('explicit USDA-FDC stays exact, namespaced, selectable and reusable in kitchen lot', async () => {
  const original='1105904', row=key(4,'USDA-FDC',original), payload=page(original,'USDA-FDC',null,[row]);
  const requests=[];
  const fetchImpl=async (url, options) => {
    requests.push({url,options});
    return {ok:true,json:async()=>url.endsWith('/status')?
      {queryAvailable:true,identitySearchPlanVersion:2,databaseSha256:IDENTIFIER_DB,
        runId:IDENTIFIER_RUN,detailSelectionSha256:DETAIL_SELECTION}:payload};
  };
  const result=await lookupIdentityPage(original,7,{namespace:'USDA-FDC',fetchImpl});
  assert.equal(result.status,'source-match');
  assert.equal(result.namespace,'USDA-FDC');
  assert.deepEqual(JSON.parse(requests[1].options.body),{
    namespace:'USDA-FDC',lexical_value:original,limit:25,cursor:null,generation:'7',databaseSha256:IDENTIFIER_DB});
  const ref=sourceObservationReference(result.matches[0],result);
  assert.equal(validSourceObservationReference(ref,original),true);
  assert.equal(exactDetailRequest(ref,8).namespace,'USDA-FDC');
  assert.equal(exactDetailRequest(ref,8).symbology,undefined);
  const projected=projectIdentifierPage(payload,original,7,{namespace:'USDA-FDC'});
  assert.equal(currentSavedReference(ref,projected),true);
  assert.equal(currentSavedReference({...ref,namespace:'barcode'},projected),false);
  assert.equal(validateLot({barcode:original,name:'Invented non-food item',ingredient:'unmapped',
    quantity:1,unit:'count',sourceObservationReference:ref,needsReview:true}).sourceObservationReference.namespace,'USDA-FDC');
});

test('manual UPC-E requires its explicit hint; original, alias, cursor and detail remain bound', () => {
  const original='01234558',expanded='012345000058';
  assert.deepEqual(expectedForms(original).map(x=>x.lexicalValue),[original]);
  const forms=expectedForms(original,'UPC-E');
  assert.deepEqual(forms.map(x=>x.lexicalValue),[original,expanded,'0'+expanded]);
  assert.equal(forms[1].equivalence,'explicit-upc-e-to-upc-a');
  const first=projectIdentityPage(page(original,'barcode','UPC-E',[key(5,'barcode',original)],
    {hasMore:true,cursor:'opaque'}),original,7,{namespace:'barcode',symbology:'UPC-E'});
  const second=projectIdentityPage(page(original,'barcode','UPC-E',[key(6,'barcode',expanded)]),
    original,7,{namespace:'barcode',symbology:'UPC-E',requestCursor:'opaque'});
  const merged=mergeIdentityPages(first,second);
  assert.equal(merged.matches[1].matchContext.equivalence,'explicit-upc-e-to-upc-a');
  assert.equal(exactDetailRequest(sourceObservationReference(merged.matches[1],merged),8).detailLexicalValue,expanded);
  assert.throws(()=>mergeIdentityPages(first,{...second,namespace:'USDA-FDC'}),/Continuation binding mismatch/);
  assert.throws(()=>projectIdentityPage(page(original,'barcode',null,[]),original,7,
    {namespace:'barcode',symbology:'UPC-E'}),/binding mismatch/i);
});

test('namespace mismatch never becomes a completed scoped miss', async () => {
  const original='1105904',payload=page(original,'barcode',null,[]),requests=[];
  const result=await lookupIdentityPage(original,7,{namespace:'USDA-FDC',fetchImpl:async(url,options)=>{
    requests.push({url,options});return {ok:true,json:async()=>url.endsWith('/status')?
      {queryAvailable:true,identitySearchPlanVersion:2,databaseSha256:IDENTIFIER_DB,
        runId:IDENTIFIER_RUN,detailSelectionSha256:DETAIL_SELECTION}:payload};
  }});
  assert.equal(result.status,'unavailable');
  assert.equal(result.namespace,'USDA-FDC');
  assert.equal(requests.length,2);
  assert.deepEqual(expectedForms('01234558',null,'USDA-FDC').map(x=>x.lexicalValue),['01234558']);
});
