// UI-owned HTTP integration around Worker13's pinned pure query engine.
import {executeQuery,CONTRACT} from './perf-query-engine.mjs';
import {createTimingAdapter} from './perf-timing-adapter.mjs';
const encoder=new TextEncoder();
const sources={
 'recipes:body':{type:'recipes',source:'world-recipes',recordClass:'body-record-reference'},
 'recipes:titles':{type:'recipes',source:'recipe-concepts',recordClass:'title-only-discovery'},
 'ingredients:occurrences':{type:'ingredients',source:'world-recipes',recordClass:'recipe-ingredient-occurrence'},
 'nutrition:fineli':{type:'nutrition',source:'fineli',country:'FI'},
 'nutrition:mext':{type:'nutrition',source:'mext',country:'JP'}
};
function fault(message,status=400,code=-32602){throw Object.assign(new Error(message),{status,code});}
async function boundedBody(request){if(Number(request.headers.get('Content-Length')||0)>8192)fault('Request exceeds8192 bytes',413);if(!request.body)fault('JSON request required');const reader=request.body.getReader(),chunks=[];let bytes=0;while(true){const {done,value}=await reader.read();if(done)break;bytes+=value.byteLength;if(bytes>8192){await reader.cancel();fault('Request exceeds8192 bytes',413);}chunks.push(value);}const joined=new Uint8Array(bytes);let offset=0;for(const chunk of chunks){joined.set(chunk,offset);offset+=chunk.byteLength;}try{return JSON.parse(new TextDecoder().decode(joined));}catch{fault('Invalid JSON',400,-32700);}}
export async function handleQueryRPC(request){const begin=performance.now(),attribution=createTimingAdapter({enabled:request.headers.get('X-OffMenu-Timing')==='1',now:()=>performance.now(),clockDomain:'local-workerd'});let id=null,hydrationMs=0,queryMs=0,parseMs=0,serializeMs=0;
 const respond=(body,status=200)=>{const at=performance.now(),wire=attribution.runSync('serialization',()=>JSON.stringify(body));serializeMs+=performance.now()-at;const extraTiming=attribution.serverTiming();return new Response(wire,{status,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff','Server-Timing':`rpc_hydrate;dur=${hydrationMs.toFixed(3)}, rpc_query;dur=${queryMs.toFixed(3)}, rpc_parse;dur=${parseMs.toFixed(3)}, rpc_serialize;dur=${serializeMs.toFixed(3)}, rpc_total;dur=${(performance.now()-begin).toFixed(3)}${extraTiming?', '+extraTiming:''}`}});};
 try{
  if(request.method!=='POST')fault('Use POST for records.query',405,-32600);
  if(new URL(request.url).search)fault('Query parameters are not supported');
  const origin=request.headers.get('Origin');if(origin&&origin!==new URL(request.url).origin||request.headers.get('Sec-Fetch-Site')==='cross-site')fault('Same-origin query use only',403,-32600);
  if(request.headers.get('Content-Type')?.split(';')[0].trim()!=='application/json')fault('Content-Type application/json required',415,-32600);
  const body=await boundedBody(request);
  if(!body||Array.isArray(body)||typeof body!=='object'||body.jsonrpc!=='2.0'||!['records.query','records.batch'].includes(body.method)||Object.keys(body).some(k=>!['jsonrpc','id','method','params'].includes(k)))fault('Expected one records.query RPC request',400,-32600);
  if(!(Number.isSafeInteger(body.id)||typeof body.id==='string'&&body.id.length<=64))fault('Bounded explicit request ID required');id=body.id;
  const params=body.params;if(!params||Array.isArray(params)||Object.keys(params).some(k=>!(body.method==='records.batch'?['snapshot','queries']:['snapshot','query']).includes(k))||typeof params.snapshot!=='string'||!/^[a-f0-9]{64}$/.test(params.snapshot))fault('Pinned snapshot and query are required');
  const queries=body.method==='records.batch'?params.queries:[params.query];
  if(!Array.isArray(queries)||queries.length<1||queries.length>2)fault('One or two bounded queries required');
  for(const q of queries)if(!q||typeof q!=='object'||Array.isArray(q)||!Object.hasOwn(sources,q.collection)||!Number.isSafeInteger(q.window?.offset)||q.window.offset<0||!Number.isSafeInteger(q.window?.limit)||q.window.limit<1||q.window.limit>25)fault('Collection/window outside contract');
  let pages=0,hydratedBytes=0;const pageCache=new Map();
  async function page(collection,window){const key=JSON.stringify([collection,window.offset,window.limit]);if(pageCache.has(key))return pageCache.get(key);if(++pages>2)fault('At most two bounded pages',413);const url=new URL('https://offmenu-retained-records.invalid/__dev/records');url.search=new URLSearchParams({...sources[collection],offset:String(window.offset),limit:String(window.limit),snapshot:params.snapshot}).toString();const start=performance.now();let response;const text=await attribution.runAsync('hydration',async()=>{response=await fetch(new Request(url,{method:'GET',headers:{Accept:'application/json'},redirect:'manual'}));const reader=response.body.getReader(),chunks=[];let size=0;while(true){const part=await reader.read();if(part.done)break;size+=part.value.byteLength;if(size+hydratedBytes>CONTRACT.limits.inputBytes){await reader.cancel();fault('Hydrated pages exceed input budget',413);}chunks.push(part.value);}const bytes=new Uint8Array(size);let cursor=0;for(const chunk of chunks){bytes.set(chunk,cursor);cursor+=chunk.byteLength;}return new TextDecoder().decode(bytes);});hydrationMs+=performance.now()-start;hydratedBytes+=encoder.encode(text).length;if(!response.ok)fault('Retained page unavailable: HTTP '+response.status,response.status);if(hydratedBytes>CONTRACT.limits.inputBytes)fault('Hydrated pages exceed input budget',413);let data;try{const at=performance.now();data=attribution.runSync('parse',()=>JSON.parse(text));parseMs+=performance.now()-at;}catch{fault('Retained page JSON unavailable',502);}if(data.snapshot!==params.snapshot)fault('Retained snapshot changed',409);pageCache.set(key,data);return data;}
  const results=[];
  for(const q of queries){
   const input={page:await page(q.collection,q.window)};
   if(q.collection==='ingredients:occurrences'&&Array.isArray(q.include)&&q.include.includes('recipeParent'))input.relations={recipeParent:await page('recipes:body',{offset:0,limit:25})};
   const queryStart=performance.now(),result=attribution.runSync('query',()=>executeQuery(q,input));queryMs+=performance.now()-queryStart;
   if(!result.ok)return respond({jsonrpc:'2.0',id,error:{code:-32602,message:result.error.message,data:{code:result.error.code,cost:result.cost}}},result.error.status);
   results.push(result);
  }
  const packet={jsonrpc:'2.0',id,integration:{runtime:'local-workerd-node-adapter',hydratedPages:pages,hydratedBytes,queryScope:'bounded-fetched-window-only',providerDeployment:false,batchQueries:queries.length}};
  if(body.method==='records.batch')packet.results=results;else packet.result=results[0];
  if(attribution.runSync('response_limit_serialization',()=>encoder.encode(JSON.stringify(packet)).length)>CONTRACT.limits.outputBytes)fault('Combined output exceeds4MiB',413);
  return respond(packet);

 }catch(e){const known=Number.isInteger(e.status);return respond({jsonrpc:'2.0',id,error:{code:known?(e.code??-32602):-32603,message:known?e.message:'Local query unavailable'}},known?e.status:500);}
}
