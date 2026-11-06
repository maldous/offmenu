import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {syncBuiltinESMExports} from 'node:module';
import http from 'node:http';
import https from 'node:https';
import net from 'node:net';
import tls from 'node:tls';

// Run from the exact repository root. All accounts, records and bearer strings
// below are public authored fixtures. They never leave this process.
let networkAttempts = 0;
const blocked = () => { networkAttempts++; throw Error('Network is disabled in this example'); };
globalThis.fetch = blocked;
http.request = http.get = https.request = https.get = blocked;
net.connect = net.createConnection = tls.connect = blocked;
syncBuiltinESMExports();
const root = process.cwd();
const source = path => pathToFileURL(resolve(root,path)).href;
const sourceManifest = JSON.parse(readFileSync(new URL('./developer-interface-source.json',import.meta.url),'utf8'));
for (const [file,expected] of Object.entries(sourceManifest.files)) {
 assert.equal(createHash('sha256').update(readFileSync(resolve(root,file))).digest('hex'),expected,'Source drift: '+file);
}

const {integrationRoutes,digest,SCOPES} = await import(source('apps/web/server/integrations.mjs'));
const {adminTools,ADMIN_SCOPES} = await import(source('apps/web/server/admin-mcp.mjs'));
const {PERSONAL_AI_TOOLS} = await import(source('apps/web/server/personal-ai.mjs'));
const db = new DatabaseSync(':memory:');
for (const file of ['schema.sql','catalogue-schema.sql']) db.exec(readFileSync(resolve(root,'apps/web/server',file),'utf8'));
const env = {DB:{prepare(sql){const make = args => ({
  async first(){return db.prepare(sql).get(...args)||null;},
  async run(){return db.prepare(sql).run(...args);},
  async all(){return {results:db.prepare(sql).all(...args)};}
});return {...make([]),bind(...args){return make(args);}};}}};
const origin = 'https://offmenu.example.invalid';
const opts = {verifiedUser:async()=>null,boundedJSON:request=>request.json(),assets:{}};
const fixtureState = {
 inventory:[{barcode:'0000000000001',name:'Authored rice',amount:400,unit:'g'}],
 recipes:[{id:'authored-recipe',title:'Authored recipe'}],
 profile:{locations:[{id:'authored-pantry',name:'Pantry'}],
 plan:[{id:'plan-one',date:'2026-01-01'},{id:'plan-two',date:'2026-01-02'}],
 history:[{title:'Authored meal',date:'2026-01-01'}],waste:[]}
};
db.prepare('INSERT INTO user_state VALUES(?,?,?,?)').run('example-alice',7,JSON.stringify(fixtureState),'2026-01-01T00:00:00Z');
db.prepare('INSERT INTO user_state VALUES(?,?,?,?)').run('example-bob',1,JSON.stringify({inventory:[{name:'Other account fixture'}],profile:{},recipes:[]}),'2026-01-01T00:00:00Z');
for (const kind of ['health','baskets','evidence']) {
 for (const [id,owner] of [['one','example-alice'],['two','example-alice'],['other','example-bob']]) {
  db.prepare('INSERT INTO private_documents VALUES(?,?,?,?,?,?)').run(owner,kind,id,1,JSON.stringify({fixture:true,kind}),'2026-01-01T00:00:00Z');
 }
}
async function bearer(id,scopes,audience,owner='example-alice') {
 const literal='om_AUTHORED_FIXTURE_'+id;
 db.prepare('INSERT INTO integration_tokens(id,token_hash,user_id,name,scopes,resource,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)')
 .run(id,await digest(literal),owner,'Authored in-memory example',JSON.stringify(scopes),origin+audience,0,4102444800000);
 return literal;
}
const readScopes=['inventory','plans','history','directory','data','health','baskets','evidence'].map(k=>k+':read');
const api=await bearer('api',readScopes,'/api/v1');
const mcp=await bearer('mcp',readScopes,'/mcp');
const limited=await bearer('limited',['inventory:read'],'/api/v1');
const bob=await bearer('bob',['inventory:read'],'/api/v1','example-bob');
const allPersonal=await bearer('personal',SCOPES.filter(x=>!x.startsWith('admin:')),'/mcp');
const call=async(path,{token,method='GET',body,headers={}}={})=>integrationRoutes(new Request(origin+path,{
 method,headers:{Origin:origin,...(token?{Authorization:'Bearer '+token}:{}),...headers},
 ...(body===undefined?{}:{body:typeof body==='string'?body:JSON.stringify(body)})
}),env,opts);
const rpc=async(method,params={},token=mcp)=>call('/mcp',{method:'POST',token,body:{jsonrpc:'2.0',id:1,method,params}});
const checkResults=[];
function check(label,actual,expected){assert.deepEqual(actual,expected,label);checkResults.push(label);}
const openapi=await (await call('/openapi.json')).json();
check('OpenAPI lists all eight implemented personal read paths',Object.keys(openapi.paths).sort(),readScopes.map(x=>'/api/v1/'+x.split(':')[0]).sort());
check('OpenAPI advertises version 3.1.0',openapi.openapi,'3.1.0');
const rest={};
for(const scope of readScopes){
 const kind=scope.split(':')[0];
 const response=await call('/api/v1/'+kind,{token:api});
 check('REST '+kind+' succeeds',response.status,200);
 rest[kind]=await response.json();
}
check('Inventory preserves barcode and quantity',rest.inventory.data,fixtureState.inventory);
check('Plans expose authored entries',rest.plans.data,fixtureState.profile.plan);
check('History separates food and cleanup',rest.history.data,{food:fixtureState.profile.history,cleanup:[]});
check('Directory separates locations and recipes',rest.directory.data,{locations:fixtureState.profile.locations,recipes:fixtureState.recipes});
check('Unified records empty fixture reports withholding count',rest.data,{schemaVersion:'1.0',records:[],nextCursor:null,withheld:0,scope:'private account'});
for(const kind of ['health','baskets','evidence']){
 check(kind+' is owner isolated',rest[kind].documents.map(x=>x.id),['one','two']);
 const first=await(await call('/api/v1/'+kind+'?limit=1',{token:api})).json();
 check(kind+' first page cursor',first.nextCursor,'one');
 const second=await(await call('/api/v1/'+kind+'?limit=1&cursor='+first.nextCursor,{token:api})).json();
 check(kind+' second page',second.documents.map(x=>x.id),['two']);
 check(kind+' final cursor',second.nextCursor,null);
}
check('Date range is inclusive',(await(await call('/api/v1/plans?from=2026-01-02&to=2026-01-02',{token:api})).json()).data,[fixtureState.profile.plan[1]]);
check('Missing bearer is rejected',(await call('/api/v1/inventory')).status,401);
check('Missing scope is rejected',(await call('/api/v1/history',{token:limited})).status,403);
check('REST rejects MCP audience',(await call('/api/v1/inventory',{token:mcp})).status,401);
check('REST write is unsupported',(await call('/api/v1/inventory',{token:api,method:'POST',body:{}})).status,405);
check('Unknown REST route is unsupported',(await call('/api/v1/unknown',{token:api})).status,404);
check('Other account cannot read example Alice inventory',(await(await call('/api/v1/inventory',{token:bob})).json()).data,[{name:'Other account fixture'}]);
const initialized=await(await rpc('initialize',{protocolVersion:'2025-11-25'})).json();
check('MCP initialize negotiates supported protocol',initialized.result.protocolVersion,'2025-11-25');
check('Unsupported MCP protocol falls back',(await(await rpc('initialize',{protocolVersion:'unsupported'})).json()).result.protocolVersion,'2025-11-25');
const tools=(await(await rpc('tools/list')).json()).result.tools;
const names={get_inventory:'inventory',get_meal_plan:'plans',get_food_history:'history',get_directory:'directory',get_unified_records:'data',get_health_observations:'health',get_saved_baskets:'baskets',get_private_evidence:'evidence'};
check('MCP read scopes expose exactly eight tools',tools.map(t=>t.name).sort(),Object.keys(names).sort());
const mcpExamples={};
for(const [name,kind]of Object.entries(names)){
 const response=await rpc('tools/call',{name,arguments:{}});
 check('MCP '+name+' succeeds',response.status,200);
 const result=(await response.json()).result;
 check('MCP '+name+' is non-error',result.isError,false);
 check('MCP '+name+' matches REST output',result.structuredContent,rest[kind]);
 check('MCP '+name+' text matches structured output',JSON.parse(result.content[0].text),result.structuredContent);
 mcpExamples[name]=result;
}
check('MCP invalid date is rejected',(await(await rpc('tools/call',{name:'get_meal_plan',arguments:{from:'bad'}})).json()).error.code,-32602);
check('MCP invalid pagination is rejected',(await(await rpc('tools/call',{name:'get_saved_baskets',arguments:{limit:0}})).json()).error.code,-32602);
check('MCP unknown tool is rejected',(await(await rpc('tools/call',{name:'unknown',arguments:{}})).json()).error.code,-32602);
check('MCP unknown method is rejected',(await(await rpc('unknown')).json()).error.code,-32601);
check('MCP rejects API audience',(await rpc('tools/list',{},api)).status,401);
check('MCP rejects foreign Origin',(await call('/mcp',{token:mcp,method:'POST',headers:{Origin:'https://other.example.invalid'},body:{jsonrpc:'2.0',id:1,method:'tools/list'}})).status,403);
check('MCP SSE is unsupported',(await call('/mcp',{token:mcp})).status,405);
check('MCP DELETE is stateless acknowledgment',(await call('/mcp',{token:mcp,method:'DELETE'})).status,204);
check('MCP notification is accepted',(await call('/mcp',{token:mcp,method:'POST',body:{jsonrpc:'2.0',method:'notifications/initialized'}})).status,202);
check('MCP malformed JSON is rejected',(await call('/mcp',{token:mcp,method:'POST',body:'{'})).status,400);
check('MCP batch is unsupported',(await call('/mcp',{token:mcp,method:'POST',body:[]})).status,400);
const fullTools=(await(await rpc('tools/list',{},allPersonal)).json()).result.tools;
check('Personal schemas match exported authorized tools',fullTools.map(t=>t.name).sort(),[...Object.keys(names),...PERSONAL_AI_TOOLS.map(t=>t.name)].sort());
for(const scope of SCOPES.filter(x=>!x.startsWith('admin:'))){
 const scoped=await bearer('scope_'+scope.replaceAll(':','_'),[scope],'/mcp');
 const listed=(await(await rpc('tools/list',{},scoped)).json()).result.tools;
 const expected=[...Object.entries(names).filter(([,kind])=>scope===kind+':read').map(([name])=>name),...PERSONAL_AI_TOOLS.filter(t=>t.scope===scope).map(t=>t.name)];
 check('Discovery for '+scope,listed.map(t=>t.name).sort(),expected.sort());
}
const adminSchemas=adminTools(ADMIN_SCOPES);
const adminToolScopes=Object.fromEntries(adminSchemas.map(t=>[t.name,ADMIN_SCOPES.filter(s=>adminTools([s]).some(a=>a.name===t.name))]));

check('No administrative tool appears in personal discovery',fullTools.some(t=>adminSchemas.some(a=>a.name===t.name)),false);
db.prepare('UPDATE integration_tokens SET revoked_at=1 WHERE id=?').run('api');
check('Revoked API fixture is rejected',(await call('/api/v1/inventory',{token:api})).status,401);
db.prepare('UPDATE integration_tokens SET expires_at=0 WHERE id=?').run('mcp');
check('Expired MCP fixture is rejected',(await rpc('ping')).status,401);
check('No network call attempted',networkAttempts,0);
const documentedKeys=Object.keys(openapi.paths['/api/v1/inventory'].get.responses['200'].content['application/json'].schema.properties).sort();
const shapeGaps=['data','health','baskets','evidence'].map(kind=>({
 path:'/api/v1/'+kind,documentedKeys,actualKeys:Object.keys(rest[kind]).sort(),
 reason:'The advertised common envelope is incomplete for this pagination-specific response; schema has no required fields and accepts arbitrary additional properties.'
}));
db.close();
console.log(JSON.stringify({
 schema:'offmenu-developer-example/1',fixture:'authored synthetic data; ephemeral SQLite; no external effects',
 qualifiedSource:sourceManifest,
 checks:checkResults,checkCount:checkResults.length,networkAttempts,
 openapi,rest,mcpExamples,personalTools:fullTools,adminTools:adminSchemas,adminToolScopes,
 schemaCoverageGaps:shapeGaps,
 limits:['No hosted HTTP transport, provider invocation, OAuth sign-in, administrative proof or writes executed.',
 'Unified-record export fixture is empty; rights filtering and nonempty record schema are not validated.',
 'Only exported schema discovery is checked for extra personal and administrative tools; their actions are not executed.',
 'This is source-bound example verification, not deployment or full JSON Schema certification.']
},null,2));
