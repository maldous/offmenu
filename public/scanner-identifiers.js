// Off-live r3 client. Bind identity before optional, selected-observation detail.
import {IDENTIFIER_DB, DETAIL_SELECTION, projectIdentityPage, mergeIdentityPages,
  lookupIdentityPage, lookupExactObservationDetail, sourceObservationReference} from './scanner-identity-v2.js';
export {sourceObservationReference};

const BACKEND='retained-product-federation-v1';
const fieldValue=(product,key)=>product?.fields?.[key]?.state==='present'?product.fields[key].value:null;
const enriched=page=>({...page,detailSelectionSha256:DETAIL_SELECTION,detailBackend:BACKEND,
  detailDatabaseSha256:null,detailGenerationId:'worker00-identity-first-native58f9-20261025-v1',
  detailBackingStores:null,productDetailCoverage:null});

export function projectIdentifierPage(data,raw,generation,{cursor=null,symbology=null}={}){
  return enriched(projectIdentityPage(data,raw,generation,{requestCursor:cursor,symbology}));
}
export function sameDetailSelection(a,b){
  return a?.databaseSha256===IDENTIFIER_DB&&b?.databaseSha256===IDENTIFIER_DB&&
    a.detailSelectionSha256===DETAIL_SELECTION&&b.detailSelectionSha256===DETAIL_SELECTION&&
    a.original===b.original&&a.symbology===b.symbology&&a.runId===b.runId;
}
export function mergeIdentifierPages(previous,next){
  if(!sameDetailSelection(previous,next))throw Error('Selected identity release changed');
  return enriched(mergeIdentityPages(previous,next));
}
export function currentSavedReference(reference,page){
  return reference?.schema==='offmenu-identifier-observation/2'&&
    reference.detailSelectionSha256===DETAIL_SELECTION&&
    reference.databaseSha256===page?.databaseSha256&&reference.runId===page?.runId&&
    reference.originalLexicalValue===page?.original;
}
export async function lookupIdentifiers(raw,generation,cursor=null,symbology=null){
  const page=await lookupIdentityPage(raw,generation,{cursor,symbology});
  return page.status==='unavailable'?page:enriched(page);
}

// A failed enrichment never removes an identifier row, its disposition, or its source reference.
export async function loadSelectedDetails(match,page,generation){
  const reference=sourceObservationReference(match,page);
  const result=await lookupExactObservationDetail(reference,generation);
  if(result.status!=='detail-returned')return {reference,status:result.status,
    reasonCode:result.error||'DETAIL_UNAVAILABLE',variants:[],availability:null,details:null};
  const details=result.details,products=details.sourceProducts||[];
  const availability=(details.productDetailAvailability||[]).find(item=>
    item?.observationKey?.databaseSha256===IDENTIFIER_DB&&
    ['run_id','input_id','record_ordinal','assertion_id'].every(key=>
      item.observationKey[key]===reference.observationKey[key]))||null;
  const variants=products.map((product,index)=>({...match,
    id:match.id+':projection:'+(product.referenceRecordId||String(index+1)),
    name:typeof fieldValue(product,'name')==='string'?fieldValue(product,'name'):null,
    brand:typeof fieldValue(product,'brand')==='string'?fieldValue(product,'brand'):null,
    ingredientsText:typeof fieldValue(product,'ingredientDeclaration')==='string'?fieldValue(product,'ingredientDeclaration'):null,
    detail:product,availability,variantOrdinal:index+1,sourceObservationReference:reference}));
  return {reference,status:details.state||'not-loaded',reasonCode:details.error?.reasonCode||null,
    variants,availability,details};
}
