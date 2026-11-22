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

// Run at the repository root. Fixtures are authored and exist only in memory.
// They do not select an account, installation, source dataset or live provider.
let networkAttempts=0;
const blocked=()=>{networkAttempts++;throw Error('Network is disabled in this example');};
globalThis.fetch=blocked;
http.request=http.get=https.request=https.get=blocked;
net.connect=net.createConnection=tls.connect=blocked;
syncBuiltinESMExports();
const root=process.cwd();
const sourceManifest=JSON.parse(readFileSync(new URL('./openapi-contract-source.json',import.meta.url),'utf8'));
assert.equal(sourceManifest.schema,'offmenu-openapi-example-source/1');
for(const [file,expected]of Object.entries(sourceManifest.files)){
  assert.equal(createHash('sha256').update(readFileSync(resolve(root,file))).digest('hex'),expected,'Source drift: '+file);
}
const {integrationRoutes,digest}=await import(pathToFileURL(resolve(root,'apps/web/server/integrations.mjs')).href);
const db=new DatabaseSync(':memory:');
for(const file of ['schema.sql','catalogue-schema.sql'])db.exec(readFileSync(resolve(root,'apps/web/server',file),'utf8'));
const env={DB:{prepare(sql){const make=params=>({
  async first(){return db.prepare(sql).get(...params)||null;},
  async all(){return {results:db.prepare(sql).all(...params)};}
});return {...make([]),bind(...params){return make(params);}};}}};
const origin='https://offmenu.example.invalid',owner='authored-openapi-example';
const kinds=['inventory','plans','history','directory','data','health','baskets','evidence'];
const token='om_AUTHORED_OPENAPI_EXAMPLE';
db.prepare('INSERT INTO integration_tokens(id,token_hash,user_id,name,scopes,resource,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)')
  .run('authored-openapi',await digest(token),owner,'In-memory fixture',JSON.stringify(kinds.map(kind=>kind+':read')),origin+'/api/v1',0,4102444800000);
db.prepare('INSERT INTO user_state VALUES(?,?,?,?)').run(owner,3,JSON.stringify({
  inventory:[{id:'authored-rice',name:'Authored rice',quantity:100,unit:'g'}],recipes:[{id:'authored-recipe'}],
  profile:{locations:[{id:'authored-pantry'}],plan:[{id:'plan-one',date:'2026-01-01'},{id:'plan-two',date:'2026-01-02'}],
    history:[{id:'authored-meal',date:'2026-01-02'}],waste:[{id:'authored-cleanup',finishedAt:'2026-01-01T10:00:00Z'}]}
}),'2026-01-02T00:00:00Z');
for(const kind of ['health','baskets','evidence'])for(const id of ['a','b']){
  db.prepare('INSERT INTO private_documents VALUES(?,?,?,?,?,?)').run(owner,kind,id,1,JSON.stringify({authored:true,kind}),'2026-01-02T00:00:00Z');
}
for(const [id,country,status,kind,source]of [['a','AU','active','product','off'],['b','AU','withdrawn','product','off'],
  ['c','US','active','product','off'],['d','AU','active','recipe','wikibooks']]){
  const value={id,kind,countries:[country],provenance:{sourceId:source,status},data:{name:'Authored '+id}};
  db.prepare('INSERT INTO unified_records(owner,id,kind,source_id,countries,document,updated_at) VALUES(?,?,?,?,?,?,?)')
    .run(owner,id,kind,source,JSON.stringify(value.countries),JSON.stringify(value),'2026-01-02T00:00:00Z');
}
const options={verifiedUser:async()=>null,boundedJSON:request=>request.json(),assets:{}};
const call=(path,authorized=true)=>integrationRoutes(new Request(origin+path,{headers:authorized?{Authorization:'Bearer '+token}:{}}),env,options);
const checks=[];
function check(label,actual,expected){assert.deepEqual(actual,expected,label);checks.push(label);}
const openapi=await(await call('/openapi.json',false)).json();
check('OpenAPI version',openapi.openapi,'3.1.0');
check('Eight personal GET resources',Object.keys(openapi.paths).sort(),kinds.map(kind=>'/api/v1/'+kind).sort());
check('Bearer scheme retained',openapi.components.securitySchemes.personalToken,{type:'http',scheme:'bearer'});
const operation=kind=>openapi.paths['/api/v1/'+kind].get;
const schema=kind=>operation(kind).responses['200'].content['application/json'].schema;

// Only the emitted envelope keywords are checked. This is not a general
// OpenAPI/JSON Schema validator, nor qualification of arbitrary nested records.
function envelope(value,shape,path='$'){
  if(shape.type){const types=Array.isArray(shape.type)?shape.type:[shape.type];
    assert.ok(types.some(type=>type==='null'?value===null:type==='array'?Array.isArray(value):
      type==='integer'?Number.isInteger(value):type==='object'?value!==null&&typeof value==='object'&&!Array.isArray(value):typeof value===type),path+' type');}
  if(Object.hasOwn(shape,'const'))assert.deepEqual(value,shape.const,path+' constant');
  if(shape.minimum!==undefined)assert.ok(value>=shape.minimum,path+' minimum');
  for(const key of shape.required||[])assert.ok(Object.hasOwn(value,key),path+'.'+key+' required');
  for(const [key,child]of Object.entries(shape.properties||{}))if(Object.hasOwn(value,key))envelope(value[key],child,path+'.'+key);
  if(shape.items)for(const [index,item]of value.entries())envelope(item,shape.items,path+'['+index+']');
}
const responses={};
for(const kind of kinds){
  const response=await call('/api/v1/'+kind);check(kind+' status',response.status,200);
  const value=await response.json();envelope(value,schema(kind));
  check(kind+' declared envelope keys',Object.keys(schema(kind).properties).sort(),Object.keys(value).sort());
  check(kind+' guaranteed envelope keys',schema(kind).required.slice().sort(),Object.keys(value).sort());
  responses[kind]=value;
}
for(const kind of ['plans','history'])check(kind+' date parameters',operation(kind).parameters.map(p=>p.name),['from','to']);
for(const kind of ['health','baskets','evidence'])check(kind+' page parameters',operation(kind).parameters.map(p=>p.name),['cursor','limit']);
check('Unified record parameters',operation('data').parameters.map(p=>p.name),['cursor','limit','kind','source','country']);
check('Inventory parameters',operation('inventory').parameters,[]);
check('Directory parameters',operation('directory').parameters,[]);
const pages={};
for(const kind of ['health','baskets','evidence']){
  const first=await(await call('/api/v1/'+kind+'?limit=1')).json();envelope(first,schema(kind));
  check(kind+' first page',first.documents.map(doc=>doc.id),['a']);check(kind+' next cursor',first.nextCursor,'a');
  const last=await(await call('/api/v1/'+kind+'?limit=1&cursor='+first.nextCursor)).json();envelope(last,schema(kind));
  check(kind+' next page',last.documents.map(doc=>doc.id),['b']);check(kind+' final cursor',last.nextCursor,null);
  pages[kind]=[first,last];
}
const query='/api/v1/data?kind=product&source=off&country=AU&limit=1';
const first=await(await call(query)).json(),withheld=await(await call(query+'&cursor=a')).json(),countryFiltered=await(await call(query+'&cursor=b')).json();
for(const page of [first,withheld,countryFiltered])envelope(page,schema('data'));
check('Filtered first record',first.records.map(record=>record.id),['a']);
check('Rights-withheld page has an advancing cursor',{records:withheld.records,withheld:withheld.withheld,nextCursor:withheld.nextCursor},{records:[],withheld:1,nextCursor:'b'});
check('Country-filtered final page',{records:countryFiltered.records,withheld:countryFiltered.withheld,nextCursor:countryFiltered.nextCursor},{records:[],withheld:1,nextCursor:null});
const recipe=await(await call('/api/v1/data?kind=recipe&source=wikibooks&country=AU')).json();envelope(recipe,schema('data'));
check('Kind and source filters',recipe.records.map(record=>record.id),['d']);
const plans=await(await call('/api/v1/plans?from=2026-01-02&to=2026-01-02')).json();
check('Inclusive date filters',plans.data.map(plan=>plan.id),['plan-two']);
check('Schema discovery grants no private read',(await call('/api/v1/inventory',false)).status,401);
check('No network attempt',networkAttempts,0);
db.close();
console.log(JSON.stringify({
  schema:'offmenu-openapi-example/1',fixture:'Authored synthetic data; ephemeral SQLite; no external effects',
  qualifiedCode:sourceManifest,verifiedSourceFiles:Object.keys(sourceManifest.files).length,
  assertionCount:checks.length,checks,networkAttempts,openapi,responses,documentPages:pages,
  unifiedRecordPages:[first,withheld,countryFiltered],
  limits:['Only the emitted envelope schema keywords are checked; no general OpenAPI/JSON Schema certification.',
    'Nested record/document schemas, all possible source policies and rights combinations are not exhaustively validated.',
    'No hosted transport, account sign-in, provider invocation, administrative action, mutation or device behavior is qualified.',
    'The immutable code pin is a reviewed code candidate, not proof of accepted develop or deployment.']
},null,2));
