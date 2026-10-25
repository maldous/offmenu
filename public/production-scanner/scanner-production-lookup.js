import {projectPublishedRecord} from './scanner-source-assertions.js';
import {analyzeIdentifier} from './typed-identifier-contract.mjs';
// Production scanner boundary. No private retained index, fixture session, or live provider fallback.
// A release may be selected only after its exact published manifest bytes and rights are qualified.
const SELECTED_PUBLIC_RELEASE = Object.freeze({sourceId:'off',releaseId:'offmenu-off-selected-products-20261025-v1',manifestSha256:'1bf09a371a164ebd8215fd9b44a1b2ac9816caaa65cd13504086defad76d4e8f'});
const HEX = /^[a-f0-9]{64}$/;
const RELEASE = /^[-A-Za-z0-9.]{1,128}$/;
const PUBLIC_SOURCE = 'off';
const unavailable = (generation, reasonCode) => ({generation,status:'unavailable',matches:[],hasMore:false,nextCursor:null,error:reasonCode});
function selected(selection) {return selection && RELEASE.test(selection.releaseId||'') && HEX.test(selection.manifestSha256||'') && selection.sourceId===PUBLIC_SOURCE;}
function projected(record,context) {
  return projectPublishedRecord(record,context);
}
// Only explicit, checksum-valid labels supply aliases. The existing public index accepts digits.
function lookupForms(raw,namespace,symbology) {
  if(namespace!=='barcode'||typeof raw!=='string'||!raw.length||raw.length>128||symbology!==null&&typeof symbology!=='string')return [];
  const typed=analyzeIdentifier({original:raw,namespace,representationHint:symbology});
  const forms=[{value:raw,rule:null},...(typed.status==='checksum-valid'?typed.labelledEquivalents:[])];
  return forms.filter((form,index)=>/^\d{4,32}$/.test(form.value)&&forms.findIndex(x=>x.value===form.value)===index);
}
const pageStatus=(matches,hasMore)=>matches.length?(matches.length>1||hasMore?'ambiguous':'source-match'):hasMore?'searching':'scoped-miss';
function continuation(raw,symbology,selection,index,sourceCursor){return JSON.stringify({version:1,raw,symbology,releaseId:selection.releaseId,manifestSha256:selection.manifestSha256,index,sourceCursor});}
export function createPublicLookup({selection,fetchImpl=fetch}={}) {
  return async function lookup(raw,generation,cursor=null,symbology=null,namespace='barcode') {
    if(!selected(selection))return unavailable(generation,'PUBLIC_RELEASE_NOT_SELECTED');
    const forms=lookupForms(raw,namespace,symbology);
    if(!forms.length)return unavailable(generation,'UNSUPPORTED_PUBLIC_IDENTIFIER');
    let index=0,sourceCursor=null;
    if(cursor!==null){
      try{
        if(typeof cursor!=='string'||cursor.length>2048)throw Error('cursor');
        const c=JSON.parse(cursor);
        if(c.version!==1||c.raw!==raw||c.symbology!==symbology||c.releaseId!==selection.releaseId||c.manifestSha256!==selection.manifestSha256||!Number.isSafeInteger(c.index)||c.index<0||c.index>=forms.length||c.sourceCursor!==null&&(typeof c.sourceCursor!=='string'||!c.sourceCursor.length||c.sourceCursor.length>600))throw Error('cursor');
        index=c.index;sourceCursor=c.sourceCursor;
      }catch{return unavailable(generation,'PUBLIC_CURSOR_INVALID');}
    }
    // At most three labelled forms; an empty completed form advances locally. No new provider or index.
    while(index<forms.length){
    const form=forms[index];
    const url=new URL('/api/data/public',globalThis.location?.origin||'https://offmenu.invalid');
    for(const [k,v] of Object.entries({source:PUBLIC_SOURCE,barcode:form.value,releaseId:selection.releaseId,manifestSha256:selection.manifestSha256,kind:'product',limit:'25'}))url.searchParams.set(k,v);
    if(sourceCursor)url.searchParams.set('cursor',sourceCursor);
    try {
      const response=await fetchImpl(url.pathname+url.search,{method:'GET',cache:'no-store',headers:{Accept:'application/json'}});
      if(!response.ok)return unavailable(generation,response.status===409?'PUBLIC_RELEASE_MISMATCH':response.status===400?'PUBLIC_QUERY_INVALID':'PUBLIC_LOOKUP_UNAVAILABLE');
      const body=await response.text();if(new TextEncoder().encode(body).byteLength>262144)return unavailable(generation,'PUBLIC_RESPONSE_BOUND');
      const data=JSON.parse(body);
      if(data.releaseId!==selection.releaseId||data.manifestSha256!==selection.manifestSha256||!Array.isArray(data.records))return unavailable(generation,'PUBLIC_RESPONSE_MISMATCH');
      const matches=[];
      for(const record of data.records){
        if(record?.kind!=='product'||typeof record.id!=='string'||!record.id.length||record.provenance?.sourceId!==PUBLIC_SOURCE||record.provenance?.visibility!=='public'||record.data?.identifiers?.some(id=>id.system==='barcode'&&id.value===form.value)!==true)return unavailable(generation,'PUBLIC_RECORD_BINDING');
        matches.push(projected({...record,releaseId:selection.releaseId},{assertions:data.localSourceAssertions,selection}));
      }
      for(const match of matches)match.matchContext={originalLexicalValue:raw,sourceLexicalValue:form.value,symbology,matchType:form.value===raw?'exact':'representation-alias',equivalence:form.rule};
      if(data.nextCursor!==null&&data.nextCursor!==undefined&&typeof data.nextCursor!=='string')return unavailable(generation,'PUBLIC_CURSOR_INVALID');
      if(data.nextCursor&&data.nextCursor.length>600)return unavailable(generation,'PUBLIC_CURSOR_INVALID');
      if(!data.nextCursor&&!matches.length&&index+1<forms.length){index++;sourceCursor=null;continue;}
      const nextIndex=data.nextCursor?index:index+1;
      const hasMore=nextIndex<forms.length;
      const nextCursor=hasMore?continuation(raw,symbology,selection,nextIndex,data.nextCursor||null):null;
      return {generation,status:pageStatus(matches,hasMore),matches,hasMore,nextCursor,requestCursor:cursor,original:raw,namespace,symbology,releaseId:selection.releaseId,manifestSha256:selection.manifestSha256};
    }catch{return unavailable(generation,'PUBLIC_LOOKUP_UNAVAILABLE');}
    }
  };
}
export const lookupIdentifiers=createPublicLookup({selection:SELECTED_PUBLIC_RELEASE});
export function mergeIdentifierPages(previous,next){
  if(next.status==='unavailable'||previous.generation!==next.generation||previous.nextCursor!==next.requestCursor||previous.original!==next.original||previous.namespace!==next.namespace||previous.symbology!==next.symbology||previous.releaseId!==next.releaseId||previous.manifestSha256!==next.manifestSha256)throw Error('Selected public release changed');
  const byId=new Map();
  for(const match of [...previous.matches,...next.matches]){
    const retained=byId.get(match.id);
    if(retained&&JSON.stringify(retained.publicRecord)!==JSON.stringify(match.publicRecord))throw Error('Published source record changed');
    if(!retained)byId.set(match.id,match);
  }
  const matches=[...byId.values()];return {...next,matches,status:pageStatus(matches,next.hasMore)};
}
