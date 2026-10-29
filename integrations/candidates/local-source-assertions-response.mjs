import {decoratePublicPayload,makeSourcePhotoSelection} from '../../apps/web/src/production-scanner/scanner-source-assertions.js';

// Root owns the current frozen producer. This separate wrapper only decorates
// its already completed LOCAL response; it performs no fetch or corpus query.
export function createLocalSourceAssertionsResponder({producer,selection,assertions=[],runtimeSelectionSha256,
  authorizeOutput,photoSelections=[]}={}){
  if(typeof producer!=='function')throw Error('LOCAL_PRODUCER_REQUIRED');
  return async function localSourceAssertionsResponse(request,env){
    const url=new URL(request.url);
    const response=await producer(request,env);
    if(!response||!response.ok||!['http://localhost:7645','http://127.0.0.1:7645'].includes(url.origin)||
      url.pathname!=='/api/data/public'||request.method!=='GET')return response;
    if(url.searchParams.get('source')!==selection?.sourceId||url.searchParams.get('releaseId')!==selection?.releaseId||
      url.searchParams.get('manifestSha256')!==selection?.manifestSha256)return response;
    const reader=response.clone().body.getReader(),parts=[];let bytes=0;
    for(;;){const{done,value}=await reader.read();if(done)break;bytes+=value.byteLength;
      if(bytes>262144){await reader.cancel();throw Error('LOCAL_PRODUCER_RESPONSE_BOUND');}parts.push(value);}
    const joined=new Uint8Array(bytes);let offset=0;for(const part of parts){joined.set(part,offset);offset+=part.length;}
    const payload=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(joined));
    let result,state='separate-attributed-assertions';
    try{
      // This is a dependency on the existing owner's current source-operation
      // checker, not an authentication implementation or a license inference.
      // No raw assertion is emitted without exact output-purpose qualification.
      if(typeof authorizeOutput!=='function'||!/^[a-f0-9]{64}$/.test(runtimeSelectionSha256||''))
        throw Error('LOCAL_ASSERTION_OUTPUT_USE_UNQUALIFIED');
      const expected={operation:'local-scanner-source-assertion-display',outputScope:'private-local-app',origin:url.origin,
        runtimeSelectionSha256,publicSelection:selection,
        sourceBindings:assertions.map(a=>({sourceObservationReference:a.sourceObservationReference,
          sourceBinding:a.binding?.sourceBinding,selectedFields:Object.keys(a.fields||{}).sort(),
          representationSchema:a.schema}))};
      let decision;
      try{decision=await authorizeOutput(request,expected);}catch{throw Error('LOCAL_ASSERTION_OUTPUT_USE_UNAVAILABLE');}
      const stable=value=>Array.isArray(value)?'['+value.map(stable).join(',')+']':value&&typeof value==='object'?
        '{'+Object.keys(value).sort().map(k=>JSON.stringify(k)+':'+stable(value[k])).join(',')+'}':JSON.stringify(value);
      if(decision?.permitted!==true||decision.current!==true||
        !/^[a-f0-9]{64}$/.test(decision.receiptSha256||'')||stable(decision.binding)!==stable(expected))
        throw Error('LOCAL_ASSERTION_OUTPUT_USE_NOT_PERMITTED');
      if(decision.authenticationRequired!==true||decision.authenticationSatisfied!==true)
        throw Error('LOCAL_ASSERTION_EXISTING_AUTH_REQUIRED');
      if(typeof decision.useSelectionRef?.id!=='string'||!decision.useSelectionRef.id||
        !/^[a-f0-9]{64}$/.test(decision.useSelectionRef?.sha256||''))throw Error('LOCAL_ASSERTION_USE_SELECTION_REFERENCE');
      result=decoratePublicPayload(payload,{assertions,selection,lexicalValue:url.searchParams.get('barcode')});
      result.localSourceAssertions.currentOutputUse={state:'qualified',useSelectionRef:decision.useSelectionRef,
        origin:url.origin,runtimeSelectionSha256};
      if(new TextEncoder().encode(JSON.stringify(result)).length>262144)throw Error('LOCAL_ASSERTION_OUTPUT_BOUND');
      if(!Array.isArray(photoSelections)||photoSelections.length)try{
        if(photoSelections.length!==1)throw Error('LOCAL_ASSERTION_PHOTO_SELECTION_NOT_UNIQUE');
        const photoRequest=photoSelections[0],photoExpected={...expected,
          operation:'local-scanner-selected-source-photo-display',photoSelection:photoRequest};
        let photoDecision;try{photoDecision=await authorizeOutput(request,photoExpected);}catch{throw Error('LOCAL_ASSERTION_PHOTO_USE_UNAVAILABLE');}
        if(photoDecision?.permitted!==true||photoDecision.current!==true||
          !/^[a-f0-9]{64}$/.test(photoDecision.receiptSha256||'')||
          stable(photoDecision.binding)!==stable(photoExpected)||photoDecision.authenticationRequired!==true||
          photoDecision.authenticationSatisfied!==true||stable(photoDecision.useSelectionRef)!==stable(decision.useSelectionRef))
          throw Error('LOCAL_ASSERTION_PHOTO_USE_NOT_PERMITTED');
        result.localSourceAssertions.sourcePhotoSelection=makeSourcePhotoSelection(result.localSourceAssertions.assertions,
          photoRequest,result.localSourceAssertions.currentOutputUse);
        if(new TextEncoder().encode(JSON.stringify(result)).length>262144){
          delete result.localSourceAssertions.sourcePhotoSelection;throw Error('LOCAL_ASSERTION_PHOTO_RESPONSE_BOUND');}
      }catch(error){if(!/^LOCAL_ASSERTION_/.test(error.message))throw error;
        result.localSourceAssertions.sourcePhotoSelectionAvailability={state:'unavailable',reasonCode:error.message};}
    }
    catch(error){
      if(!/^LOCAL_ASSERTION_/.test(error.message))throw error;
      state='unavailable';result={...payload,localSourceAssertions:{schema:'offmenu-local-source-assertions/1',
        publicSelection:selection,assertions:[],state,reasonCode:error.message}};
    }
    // A near-limit original public response must remain usable. Source facts
    // are withheld rather than truncating either payload or growing past the
    // existing reader's wire bound.
    if(new TextEncoder().encode(JSON.stringify(result)).length>262144)return response;
    const headers=new Headers(response.headers);headers.set('Cache-Control','no-store');
    headers.set('Vary',[headers.get('Vary'),'Cookie','Authorization'].filter(Boolean).join(', '));
    for(const name of ['Content-Length','Content-Encoding','Content-MD5','ETag','Digest'])headers.delete(name);
    headers.set('Content-Type','application/json');headers.set('X-OffMenu-Local-Source-Assertions',state);
    return new Response(JSON.stringify(result),{status:response.status,headers});
  };
}
