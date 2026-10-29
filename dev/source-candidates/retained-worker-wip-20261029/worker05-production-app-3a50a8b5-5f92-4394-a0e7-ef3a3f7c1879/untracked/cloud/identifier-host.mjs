// Node-host adapter. Requires registration in the existing native owner callback.
import {spawn} from 'node:child_process';
import {Buffer} from 'node:buffer';
const DB='97c2f7390f75d8d187b49c927652515cd829e095301d7b305a0081120c7502f0';
const SCRIPT='/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app/cloud/identifier-query.py';
const FEDERATED_SCRIPT='/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/live-dev/3a50a8b5-5f92-4394-a0e7-ef3a3f7c1879/production-app/cloud/identifier-federated-query.py';
const BACKEND='retained-product-federation-v1';
export function createIdentifierAdapter({Response:ResponseClass=Response,scriptPath=SCRIPT,federatedScriptPath=FEDERATED_SCRIPT}={}){let active=0;
 const reply=(data,status=200)=>{
  const headers={'Cache-Control':'private, no-store','X-Content-Type-Options':'nosniff'};
  let bytes;try{bytes=Buffer.byteLength(JSON.stringify(data),'utf8');}catch{bytes=Infinity;}
  if(bytes>262144&&Array.isArray(data?.rows)&&data?.details?.detailBackend===BACKEND){
   const d=data.details;data={...data,details:{detailDatabaseSha256:null,detailBackend:BACKEND,detailSelectionSha256:d.detailSelectionSha256,detailGenerationId:d.detailGenerationId,accepted:false,state:'unavailable',error:{reasonCode:'DETAIL_RESPONSE_BOUND'},sourceProducts:[],productDetailAvailability:[]}};
   try{bytes=Buffer.byteLength(JSON.stringify(data),'utf8');}catch{bytes=Infinity;}
  }
  if(bytes>262144)return ResponseClass.json({error:'API_RESPONSE_BOUND'},{status:503,headers});
  return ResponseClass.json(data,{status,headers});
 };
 function run(payload,script=scriptPath){return new Promise((resolve,reject)=>{if(active>=2){reject(Object.assign(Error('Busy'),{status:429}));return;}active++;const p=spawn('python3',script===federatedScriptPath?['-I','-B',script]:['-B',script],{stdio:['pipe','pipe','ignore']});let chunks=[],size=0,done=false;const finish=(err,value)=>{if(done)return;done=true;active--;clearTimeout(timer);err?reject(err):resolve(value);};const timer=setTimeout(()=>{p.kill('SIGTERM');finish(Error('Timeout'));},7000);p.on('error',e=>finish(e));p.stdout.on('data',b=>{size+=b.length;if(size>262144){p.kill('SIGTERM');finish(Error('Response bound'));}else chunks.push(b);});p.on('close',code=>{if(done)return;try{if(code!==0)throw Error('Child failed');const x=JSON.parse(Buffer.concat(chunks).toString('utf8'));finish(null,x);}catch(e){finish(e);}});p.stdin.on('error',()=>{});p.stdin.end(JSON.stringify(payload));});}
 return async request=>{const u=new URL(request.url);if(u.hostname!=='offmenu-identifiers.invalid'||!['/__dev/identifiers','/__dev/identifiers/status'].includes(u.pathname))return null;
 try{if(u.pathname.endsWith('/status')){if(request.method!=='GET')return reply({error:'METHOD_NOT_ALLOWED'},405);const result=await run({action:'status'},federatedScriptPath);result.productDetailsSupported=true;return reply(result,result.status||200);}
 if(request.method!=='POST')return reply({error:'METHOD_NOT_ALLOWED'},405);if(request.headers.get('Content-Type')?.split(';')[0]!=='application/json')return reply({error:'JSON_REQUIRED'},415);
 const text=await request.text();if(Buffer.byteLength(text)>8192)return reply({error:'REQUEST_BOUND'},413);let q;try{q=JSON.parse(text);}catch{return reply({error:'INVALID_JSON'},400);}
 if(!q||Array.isArray(q)||Object.keys(q).some(k=>!['namespace','lexical_value','limit','cursor','generation','databaseSha256','include'].includes(k))||!['barcode','USDA-FDC'].includes(q.namespace)||!(typeof q.lexical_value==='string'&&q.lexical_value.length>=1&&q.lexical_value.length<=128)||!Number.isInteger(q.limit)||q.limit<1||q.limit>25||typeof q.generation!=='string'||q.generation.length>64)return reply({error:'INVALID_IDENTIFIER_QUERY'},400);
 if(q.include!==undefined&&(!Array.isArray(q.include)||q.include.length!==1||!['source-native-product-details',BACKEND].includes(q.include[0])))return reply({error:'INVALID_DETAIL_INCLUDE'},400);
 if(q.databaseSha256!==DB)return reply({error:'DATABASE_BINDING_MISMATCH'},409);
 let after=0;if(q.cursor!==null&&q.cursor!==undefined){try{const c=JSON.parse(Buffer.from(q.cursor,'base64url').toString('utf8'));if(c.db!==DB||c.generation!==q.generation||c.namespace!==q.namespace||c.lexical!==q.lexical_value||c.limit!==q.limit||!Number.isSafeInteger(c.after)||c.after<0)throw Error();after=c.after;}catch{return reply({error:'CURSOR_BINDING_MISMATCH'},400);}}
 const result=await run({action:'query',namespace:q.namespace,lexical_value:q.lexical_value,limit:q.limit,after,...(q.include?{include:q.include}:{})},q.include?.[0]===BACKEND?federatedScriptPath:scriptPath);if(result.error)return reply(result,result.status||503);
 result.generation=q.generation;result.nextCursor=result.hasMore?Buffer.from(JSON.stringify({db:DB,generation:q.generation,namespace:q.namespace,lexical:q.lexical_value,limit:q.limit,after:result.nextAssertionId})).toString('base64url'):null;return reply(result);
 }catch(e){return reply({error:'PRIVATE_IDENTIFIER_HOST_UNAVAILABLE'},e.status||503);}};
}
