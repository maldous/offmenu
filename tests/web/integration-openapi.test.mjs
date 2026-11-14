import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {integrationRoutes,digest} from '../../apps/web/server/integrations.mjs';

const db=new DatabaseSync(':memory:');
for(const file of ['schema.sql','catalogue-schema.sql'])db.exec(readFileSync(new URL('../../apps/web/server/'+file,import.meta.url),'utf8'));
const env={DB:{prepare(sql){const make=params=>({async first(){return db.prepare(sql).get(...params)||null;},
  async all(){return {results:db.prepare(sql).all(...params)};}});return {...make([]),bind(...params){return make(params);}};}}};
const origin='https://offmenu.example.invalid',owner='authored-openapi-account';
const kinds=['inventory','plans','history','directory','data','health','baskets','evidence'];
const token='om_AUTHORED_OPENAPI_FIXTURE';
db.prepare('INSERT INTO integration_tokens(id,token_hash,user_id,name,scopes,resource,created_at,expires_at) VALUES(?,?,?,?,?,?,?,?)')
  .run('authored-openapi',await digest(token),owner,'Synthetic contract fixture',JSON.stringify(kinds.map(kind=>kind+':read')),origin+'/api/v1',0,4102444800000);
db.prepare('INSERT INTO user_state VALUES(?,?,?,?)').run(owner,7,JSON.stringify({inventory:[{id:'rice',quantity:3}],
  recipes:[{id:'fixture-recipe'}],profile:{locations:[{id:'pantry'}],plan:[{id:'plan-a',date:'2026-01-01'},{id:'plan-b',date:'2026-01-02'}],
  history:[{id:'meal',date:'2026-01-02'}],waste:[{id:'cleanup',finishedAt:'2026-01-01T10:00:00Z'}]}}),'2026-01-02T00:00:00Z');
for(const kind of ['health','baskets','evidence'])for(const id of ['a','b'])db.prepare('INSERT INTO private_documents VALUES(?,?,?,?,?,?)')
  .run(owner,kind,id,1,JSON.stringify({authored:true,kind}),'2026-01-02T00:00:00Z');
for(const [id,country,status,kind,source]of [['a','AU','active','product','off'],['b','AU','withdrawn','product','off'],
  ['c','US','active','product','off'],['d','AU','active','recipe','wikibooks']]){
  const record={id,kind,countries:[country],provenance:{sourceId:source,status},data:{name:'Authored '+id}};
  db.prepare('INSERT INTO unified_records(owner,id,kind,source_id,countries,document,updated_at) VALUES(?,?,?,?,?,?,?)')
    .run(owner,id,kind,source,JSON.stringify(record.countries),JSON.stringify(record),'2026-01-02T00:00:00Z');
}
const options={verifiedUser:async()=>null,boundedJSON:request=>request.json(),assets:{}};
const call=(path,authorized=true,method='GET')=>integrationRoutes(new Request(origin+path,{method,
  headers:authorized?{Authorization:'Bearer '+token}:{}}),env,options);
const spec=await(await call('/openapi.json',false)).json();
const operation=kind=>spec.paths['/api/v1/'+kind].get;
const schema=kind=>operation(kind).responses['200'].content['application/json'].schema;

// Envelope checks against actual route responses. This covers the schema
// keywords emitted here; it is not a general OpenAPI/JSON Schema validator.
function assertEnvelope(value,shape,path='$'){
  if(shape.type){const types=Array.isArray(shape.type)?shape.type:[shape.type];
    assert.ok(types.some(type=>type==='null'?value===null:type==='array'?Array.isArray(value):
      type==='integer'?Number.isInteger(value):type==='object'?value!==null&&typeof value==='object'&&!Array.isArray(value):typeof value===type),path+' type');}
  if(Object.hasOwn(shape,'const'))assert.deepEqual(value,shape.const,path+' constant');
  if(shape.minimum!==undefined)assert.ok(value>=shape.minimum,path+' minimum');
  if(shape.required)for(const key of shape.required)assert.ok(Object.hasOwn(value,key),path+'.'+key+' required');
  if(shape.properties)for(const [key,child]of Object.entries(shape.properties))if(Object.hasOwn(value,key))assertEnvelope(value[key],child,path+'.'+key);
  if(shape.items)for(const [index,item]of value.entries())assertEnvelope(item,shape.items,path+'['+index+']');
}

test('OpenAPI retains eight GET resources, bearer scheme and per-resource scope',()=>{
  assert.equal(spec.openapi,'3.1.0');
  assert.deepEqual(Object.keys(spec.paths).sort(),kinds.map(kind=>'/api/v1/'+kind).sort());
  assert.deepEqual(spec.servers,[{url:origin}]);
  assert.deepEqual(spec.security,[{personalToken:[]}]);
  assert.deepEqual(spec.components.securitySchemes.personalToken,{type:'http',scheme:'bearer'});
  for(const kind of kinds){assert.deepEqual(Object.keys(spec.paths['/api/v1/'+kind]),['get']);
    assert.ok(operation(kind).description.includes('Requires '+kind+':read.'));}
});

test('all populated REST response envelopes match their advertised required fields and types',async()=>{
  for(const kind of kinds){const response=await call('/api/v1/'+kind);assert.equal(response.status,200);
    assert.equal(response.headers.get('Cache-Control'),'no-store');const result=await response.json();
    assert.deepEqual(Object.keys(schema(kind).properties).sort(),Object.keys(result).sort(),kind+' envelope keys');
    assert.deepEqual(schema(kind).required.slice().sort(),Object.keys(result).sort(),kind+' guaranteed envelope fields');
    assertEnvelope(result,schema(kind));
  }
  assert.deepEqual(schema('history').properties.data.required,['food','cleanup']);
  assert.deepEqual(schema('directory').properties.data.required,['locations','recipes']);
  assert.throws(()=>assertEnvelope({version:1,revision:7,updatedAt:null,data:[]},schema('data')),/schemaVersion required/);
  assert.throws(()=>assertEnvelope({documents:[],nextCursor:42,scope:'private account'},schema('health')),/nextCursor type/);
});

test('document queries advertise and preserve cursor pagination for every document kind',async()=>{
  for(const kind of ['health','baskets','evidence']){
    assert.deepEqual(operation(kind).parameters.map(p=>p.name),['cursor','limit']);
    const first=await(await call('/api/v1/'+kind+'?limit=1')).json();
    assertEnvelope(first,schema(kind));assert.deepEqual(first.documents.map(doc=>doc.id),['a']);assert.equal(first.nextCursor,'a');
    const last=await(await call('/api/v1/'+kind+'?limit=1&cursor='+first.nextCursor)).json();
    assertEnvelope(last,schema(kind));assert.deepEqual(last.documents.map(doc=>doc.id),['b']);assert.equal(last.nextCursor,null);
    const limit=operation(kind).parameters.find(p=>p.name==='limit');
    assert.ok(limit.description.includes('zero values default to 100'));
    assert.deepEqual(limit.schema,{type:'integer',minimum:1,maximum:1000,default:100});
  }
});

test('unified-record schema describes filters and rights-withheld pages without inventing completion',async()=>{
  assert.deepEqual(operation('data').parameters.map(p=>p.name),['cursor','limit','kind','source','country']);
  const first=await(await call('/api/v1/data?kind=product&source=off&country=AU&limit=1')).json();
  assertEnvelope(first,schema('data'));assert.deepEqual(first.records.map(r=>r.id),['a']);assert.equal(first.nextCursor,'a');
  const withheld=await(await call('/api/v1/data?kind=product&source=off&country=AU&limit=1&cursor=a')).json();
  assertEnvelope(withheld,schema('data'));assert.deepEqual(withheld.records,[]);assert.equal(withheld.withheld,1);assert.equal(withheld.nextCursor,'b');
  const countryFiltered=await(await call('/api/v1/data?kind=product&source=off&country=AU&limit=1&cursor=b')).json();
  assertEnvelope(countryFiltered,schema('data'));assert.deepEqual(countryFiltered.records,[]);assert.equal(countryFiltered.withheld,1);assert.equal(countryFiltered.nextCursor,null);
  const recipe=await(await call('/api/v1/data?kind=recipe&source=wikibooks&country=AU')).json();
  assertEnvelope(recipe,schema('data'));assert.deepEqual(recipe.records.map(r=>r.id),['d']);
});

test('date filters retain inclusive behavior and are not advertised on unrelated resources',async()=>{
  for(const kind of ['plans','history']){assert.deepEqual(operation(kind).parameters.map(p=>p.name),['from','to']);
    for(const parameter of operation(kind).parameters){assert.equal(parameter.schema.format,'date');assert.ok(parameter.description.includes('without calendar validation'));}}
  assert.deepEqual(operation('inventory').parameters,[]);assert.deepEqual(operation('directory').parameters,[]);
  const plans=await(await call('/api/v1/plans?from=2026-01-02&to=2026-01-02')).json();assert.deepEqual(plans.data.map(p=>p.id),['plan-b']);
  const history=await(await call('/api/v1/history?from=2026-01-02&to=2026-01-02')).json();assert.deepEqual(history.data,{food:[{id:'meal',date:'2026-01-02'}],cleanup:[]});
});

test('schema discovery does not authorize private reads or change unsupported methods/storage failures',async()=>{
  for(const kind of kinds){assert.equal((await call('/api/v1/'+kind,false)).status,401);
    assert.equal((await call('/api/v1/'+kind,true,'POST')).status,405);}
  const missing=await integrationRoutes(new Request(origin+'/openapi.json'),{},options);assert.equal(missing.status,503);
});
