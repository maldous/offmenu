// Native-only paths and selected source receipts; HTTP never selects a store or script.
import {spawn} from 'node:child_process';
import {unknownCategoryDisposition} from '../public/source-category-claims.js';
import {Buffer} from 'node:buffer';
import {isDeepStrictEqual} from 'node:util';
const DB='97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0';
const ROOT='/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app/cloud/';
const BACKEND='retained-product-federation-v1';
const CAP=262144;
async function boundedRequestText(request,deadline){
 if(!request.body)return '';
 const reader=request.body.getReader();let timer,total=0;const chunks=[];
 try{
  while(true){
   if(Date.now()>=deadline)throw Error('REQUEST_TIME_BOUND');
   const {done,value}=await new Promise((resolve,reject)=>{
    timer=setTimeout(()=>reject(Error('REQUEST_TIME_BOUND')),Math.max(0,deadline-Date.now()));
    reader.read().then(resolve,reject);
   });
   clearTimeout(timer);
   if(done)break;
   total+=value.byteLength;
   if(total>8192)throw Error('REQUEST_BOUND');
   if(value.byteLength)chunks.push(value);
  }
  return new TextDecoder('utf-8',{fatal:true}).decode(Buffer.concat(chunks,total));
 }catch(error){
  // A stream's cancellation hook can itself stall; cancellation must not extend the deadline.
  void reader.cancel().catch(()=>{});throw error;
 }finally{clearTimeout(timer);reader.releaseLock();}
}
// Same checksum and UPC-E expansion as the retained scanner model.
// These representations never establish one physical product or ingredient.
function validGTIN(value) {
  if (!/^(?:\d{8}|\d{12}|\d{13}|\d{14})$/.test(value)) return false;
  let sum = 0;
  for (let i = value.length - 2, weight = 3; i >= 0; i--, weight = 4 - weight) sum += Number(value[i]) * weight;
  return (10 - sum % 10) % 10 === Number(value.at(-1));
}
export function identifierForms(namespace, original, symbology) {
  const forms = [{lexicalValue: original, matchType: 'exact', equivalence: null}];
  if (namespace !== 'barcode') return forms;
  const add = (value, rule) => {
    if (!forms.some(form => form.lexicalValue === value)) forms.push({lexicalValue: value, matchType: 'representation-alias', equivalence: rule});
  };
  let expanded = original;
  // Eight digits alone can be EAN-8 or UPC-E. Expand only an explicit UPC-E capture.
  if (symbology === 'UPC-E' && /^[01]\d{7}$/.test(original)) {
    const [n,a,b,c,d,e,f,k] = original;
    expanded = f <= '2' ? n+a+b+f+'0000'+c+d+e+k : f === '3' ? n+a+b+c+'00000'+d+e+k : f === '4' ? n+a+b+c+d+'00000'+e+k : n+a+b+c+d+e+'0000'+f+k;
    if (!validGTIN(expanded)) return forms;
    add(expanded, 'explicit-upc-e-to-upc-a');
  } else if (symbology === 'UPC-E') return forms;
  if (!validGTIN(expanded)) return forms;
  if (expanded.length === 12 && (!symbology || symbology === 'UPC-A' || symbology === 'UPC-E')) {
    add('0' + expanded, 'upc-a-as-leading-zero-ean-13');
  } else if (expanded.length === 13 && expanded[0] === '0' && (!symbology || symbology === 'EAN-13')) {
    add(expanded.slice(1), 'leading-zero-ean-13-as-upc-a');
  }
  return forms;
}

const selection={detailBackend:BACKEND,detailSelectionSha256:'d9a08c3b2b9eec880418b8108d60c177a253b53802e8ea0453eb8fd502498290',detailGenerationId:'worker00-identity-first-native58f9-20261025-v1'};
const unavailable=reasonCode=>({...selection,detailDatabaseSha256:null,accepted:false,state:'unavailable',error:{reasonCode},sourceProducts:[],productDetailAvailability:[]});
export function createIdentifierAdapter({Response:ResponseClass=Response,scriptPath=ROOT+'identifier-query.py',federatedScriptPath=ROOT+'identifier-federated-query.py',timeoutMs=7000}={}){
 if(!Number.isInteger(timeoutMs)||timeoutMs<1||timeoutMs>7000)throw Error('Invalid native deadline');
 let active=0;
 const reply=(data,status=200)=>{
  const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
  let bytes=Buffer.byteLength(JSON.stringify(data),'utf8');
  if(bytes>CAP&&Array.isArray(data?.rows)&&data.details){data={...data,details:unavailable('DETAIL_RESPONSE_BOUND')};bytes=Buffer.byteLength(JSON.stringify(data),'utf8');}
  if(bytes>CAP)return ResponseClass.json({error:'IDENTITY_RESPONSE_BOUND',scope:'selected-index-page-unavailable',identitySearchState:'unavailable'},{status:503,headers});
  return ResponseClass.json(data,{status,headers});
 };
 function run(payload,script,deadline){return new Promise((resolve,reject)=>{
  const remaining=deadline-Date.now();if(remaining<=0){reject(Error('CHILD_TIME_BOUND'));return;}
  // Both stages ignore Python environment flags, including optimization that disables assertions.
  const child=spawn('python3',['-I','-B',script],{stdio:['pipe','pipe','ignore']});
  let chunks=[],size=0,settled=false,pendingError;
  const finish=(error,value)=>{if(settled)return;settled=true;clearTimeout(timer);error?reject(error):resolve(value);};
  // Wait for close after killing this owned child, so the two-request pool cannot outlive its process bound.
  const stop=code=>{pendingError=Error(code);child.kill('SIGKILL');};
  const timer=setTimeout(()=>stop('CHILD_TIME_BOUND'),remaining);
  child.on('error',()=>finish(Error('CHILD_UNAVAILABLE')));
  child.stdout.on('data',chunk=>{size+=chunk.length;if(size>CAP)stop('CHILD_RESPONSE_BOUND');else chunks.push(chunk);});
  child.on('close',code=>{
   if(pendingError)return finish(pendingError);
   if(code!==0)return finish(Error('CHILD_UNAVAILABLE'));
   try{finish(null,JSON.parse(Buffer.concat(chunks).toString('utf8')));}catch{finish(Error('CHILD_RESPONSE_INVALID'));}
  });
  child.stdin.on('error',()=>{});child.stdin.end(JSON.stringify(payload));
 });}
 const dispositions=['source-asserted','unresolved','invalid'];
 function planFor(query){return identifierForms(query.namespace,query.lexical_value,query.symbology).flatMap(form=>dispositions.map(disposition=>({...form,disposition})));}
 function cursor(query,lane,after){return Buffer.from(JSON.stringify({version:2,db:DB,generation:query.generation,namespace:query.namespace,lexical:query.lexical_value,symbology:query.symbology??null,limit:query.limit,lane,after})).toString('base64url');}
 function identityValid(result,query,lane,limit,after){
  if(!result||typeof result!=='object'||Array.isArray(result)||result.error||result.databaseSha256!==DB||!Array.isArray(result.rows)||result.rows.length>limit||typeof result.hasMore!=='boolean')return false;
  let previous=after;
  for(const row of result.rows){if(!row||typeof row!=='object'||!Number.isSafeInteger(row.assertion_id)||row.assertion_id<=previous||row.namespace!==query.namespace||row.lexical_value!==lane.lexicalValue||row.disposition!==lane.disposition)return false;previous=row.assertion_id;}
  return result.hasMore?result.rows.length>0&&result.nextAssertionId===previous:result.nextAssertionId===null;
 }
 return async request=>{
  const url=new URL(request.url);if(url.hostname!=='offmenu-identifiers.invalid'||!['/__dev/identifiers','/__dev/identifiers/status'].includes(url.pathname))return null;
  const deadline=Date.now()+timeoutMs;
  let reserved=false;
  try{
   const isStatus=url.pathname.endsWith('/status');
   if(request.method!==(isStatus?'GET':'POST'))return reply({error:'METHOD_NOT_ALLOWED'},405);
   let query,after=0,laneIndex=0,plan;
   if(!isStatus){
    if(request.headers.get('Content-Type')?.split(';')[0]!=='application/json')return reply({error:'JSON_REQUIRED'},415);
    let text;
    try{text=await boundedRequestText(request,deadline);}catch(error){return reply({error:error.message==='REQUEST_BOUND'?'REQUEST_BOUND':error.message==='REQUEST_TIME_BOUND'?'REQUEST_TIME_BOUND':'INVALID_JSON'},error.message==='REQUEST_BOUND'?413:error.message==='REQUEST_TIME_BOUND'?408:400);}
    try{query=JSON.parse(text);}catch{return reply({error:'INVALID_JSON'},400);}
    if(!query||typeof query!=='object'||Array.isArray(query)||Object.keys(query).some(k=>!['namespace','lexical_value','limit','cursor','generation','databaseSha256','include','detailAssertionId','detailLexicalValue','detailDisposition','symbology'].includes(k))||!['barcode','USDA-FDC'].includes(query.namespace)||typeof query.lexical_value!=='string'||query.lexical_value.length<1||query.lexical_value.length>128||/[\x00-\x1f\x7f]/.test(query.lexical_value)||!Number.isInteger(query.limit)||query.limit<1||query.limit>25||typeof query.generation!=='string'||query.generation.length>64)return reply({error:'INVALID_IDENTIFIER_QUERY'},400);
    if(query.symbology!==undefined&&(query.namespace!=='barcode'||!['EAN-13','EAN-8','UPC-A','UPC-E','GTIN-14'].includes(query.symbology)))return reply({error:'INVALID_SYMBOLOGY'},400);
    plan=planFor(query);
    if(query.include!==undefined&&(!Array.isArray(query.include)||query.include.length!==1||!['source-native-product-details',BACKEND].includes(query.include[0])))return reply({error:'INVALID_DETAIL_INCLUDE'},400);
    if(query.databaseSha256!==DB)return reply({error:'DATABASE_BINDING_MISMATCH'},409);
    if(query.detailAssertionId!==undefined&&(!Number.isSafeInteger(query.detailAssertionId)||query.detailAssertionId<=0||!query.include||query.cursor))return reply({error:'INVALID_OBSERVATION_DETAIL_QUERY'},400);
    if((query.detailLexicalValue!==undefined||query.detailDisposition!==undefined)&&query.detailAssertionId===undefined)return reply({error:'INVALID_OBSERVATION_DETAIL_QUERY'},400);
    if(query.detailAssertionId!==undefined){laneIndex=plan.findIndex(lane=>lane.lexicalValue===(query.detailLexicalValue??query.lexical_value)&&lane.disposition===(query.detailDisposition??'source-asserted'));if(laneIndex<0)return reply({error:'INVALID_OBSERVATION_DETAIL_QUERY'},400);}
    if(query.cursor!==null&&query.cursor!==undefined){try{const c=JSON.parse(Buffer.from(query.cursor,'base64url').toString('utf8'));if(c.version!==2||c.symbology!==(query.symbology??null)||!Number.isSafeInteger(c.lane)||c.lane<0||c.lane>=plan.length||c.db!==DB||c.generation!==query.generation||c.namespace!==query.namespace||c.lexical!==query.lexical_value||c.limit!==query.limit||!Number.isSafeInteger(c.after)||c.after<0)throw Error();after=c.after;laneIndex=c.lane;}catch{return reply({error:'CURSOR_BINDING_MISMATCH'},400);}}
   }
   if(active>=2)return reply({error:'PRIVATE_IDENTIFIER_HOST_BUSY'},429);
   active++;reserved=true;
   if(isStatus){
    const status=await run({action:'status'},scriptPath,deadline);
    // Detail-store status cannot prevent a valid identifier search.
    return reply({...status,...selection,productDetailsSupported:true,detailAvailability:'not-assessed',identitySearchIndependentOfDetails:true,identitySearchPlanVersion:2},status.status||200);
   }
   const detailOnly=query.detailAssertionId!==undefined;
   const startLane=laneIndex;
   // Reserve within the existing identifier-stage VM ceiling across all remaining lanes.
   // The helper checks progress every100 VM instructions; leave that quantum in each reservation.
   const plannedLanes=detailOnly?1:plan.length-startLane;
   const laneMaxSteps=Math.max(1,Math.floor(100000/plannedLanes)-100);
   let result={databaseSha256:DB,rows:[],assurance:'lexical-source-observations-only',queryMatchTotal:null};
   const matches=[],failures=[];
   if(detailOnly)after=query.detailAssertionId-1;
   // Each lane has an independent keyset. A failed lane never advances and cannot skip observations.
   while(laneIndex<plan.length&&result.rows.length<(detailOnly?1:query.limit)){
    const lane=plan[laneIndex],limit=detailOnly?1:query.limit-result.rows.length;
    let page;
    try{
     page=await run({action:'query',namespace:query.namespace,lexical_value:lane.lexicalValue,disposition:lane.disposition,limit,after,max_steps:laneMaxSteps},scriptPath,deadline);
     if(!identityValid(page,query,lane,limit,after))throw Error('IDENTITY_RESPONSE_INVALID');
    }catch{
     failures.push({lane:laneIndex,lexicalValue:lane.lexicalValue,disposition:lane.disposition,reasonCode:'IDENTITY_LANE_UNAVAILABLE'});break;
    }
    if(!result.metadata&&page.metadata)result.metadata=page.metadata;
    const rows=detailOnly?page.rows.filter(row=>row.assertion_id===query.detailAssertionId):page.rows;
    result.rows.push(...rows);
    matches.push(...rows.map(row=>({assertionId:row.assertion_id,sourceLexicalValue:row.lexical_value,matchType:lane.matchType,equivalence:lane.equivalence,disposition:lane.disposition,categoryDisposition:unknownCategoryDisposition()})));
    if(detailOnly)break;
    if(page.hasMore){after=page.nextAssertionId;break;}
    laneIndex++;after=0;
   }
   const hasMore=!detailOnly&&laneIndex<plan.length;
   result={...result,generation:query.generation,hasMore,nextAssertionId:null,nextCursor:hasMore?cursor(query,laneIndex,after):null,
    identitySearchState:failures.length?'partial':'available',identitySearchIndependentOfDetails:true,
    identitySearchPlanVersion:2,identityQuery:{namespace:query.namespace,originalLexicalValue:query.lexical_value,symbology:query.symbology??null,forms:identifierForms(query.namespace,query.lexical_value,query.symbology)},
    identityMatches:matches,categoryDispositionCoverage:{scope:'returned-identifier-observations-only',returnedOccurrences:result.rows.length,mappedIngredientCategory:0,nonIngredientNotApplicable:0,ambiguousUnknown:result.rows.length,unreturnedPopulation:null},identitySearchCoverage:{state:failures.length?'partial':hasMore?'page-available':'complete-for-selected-index-and-query-plan',startLane,nextLane:hasMore?laneIndex:null,lanes:plan,failures,identifierVMStepReservation:{limit:100000,plannedLanes,perLaneMaxSteps:laneMaxSteps,progressQuantumAllowancePerLane:100,measured:false},physicalProductIdentityAsserted:false,ingredientQualificationAsserted:false},
    operation:detailOnly?'observation-detail':'identifier-search'};
   if(detailOnly&&!result.rows.length)result.details=unavailable(failures.length?'SELECTED_OBSERVATION_LOOKUP_UNAVAILABLE':'NO_CURRENT_SELECTED_OBSERVATION');
   else if(query.include&&result.rows.length){
    try{
     const wire=await run({action:'enrich',identity:result},federatedScriptPath,deadline);
     if(!wire||wire.error||wire.databaseSha256!==DB||!isDeepStrictEqual(wire.rows,result.rows)||!wire.details||typeof wire.details!=='object'||wire.details.detailBackend!==BACKEND||!Array.isArray(wire.details.sourceProducts))throw Error('DETAIL_RESPONSE_INVALID');
     result.details=wire.details;
    }catch(error){result.details=unavailable(['CHILD_TIME_BOUND','CHILD_RESPONSE_BOUND','CHILD_RESPONSE_INVALID'].includes(error.message)?'DETAIL_'+error.message.slice(6):'DETAIL_UNAVAILABLE');}
   }else if(query.include)result.details={...unavailable(failures.length?'IDENTITY_SEARCH_INCOMPLETE':'NO_OBSERVATIONS_IN_SELECTED_PAGE'),state:failures.length?'unavailable':'not-loaded'};
   return reply(result);
  }catch{return reply({error:'PRIVATE_IDENTIFIER_HOST_UNAVAILABLE',identitySearchState:'unavailable'},503);}
  finally{if(reserved)active--;}
 };
}
