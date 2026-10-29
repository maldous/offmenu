import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {adminOperationsRoutes} from '../../cloud/admin-operations.mjs';

const database=new DatabaseSync(':memory:');
database.exec(readFileSync(new URL('../../cloud/catalogue-schema.sql',import.meta.url),'utf8'));
database.exec(readFileSync(new URL('../../cloud/admin-operations-schema.sql',import.meta.url),'utf8'));
const queries=[];
let beforeBatch=null;
const DB={prepare(sql){queries.push(sql);const make=args=>({async first(){return database.prepare(sql).get(...args)||null;},async all(){return {results:database.prepare(sql).all(...args)};},async run(){return database.prepare(sql).run(...args);},_run(){const statement=database.prepare(sql);if(/^\s*(UPDATE|INSERT).*RETURNING/i.test(sql))return {results:statement.all(...args)};const meta=statement.run(...args);return {results:[],meta:{changes:meta.changes}};}});return {...make([]),bind(...args){return make(args);}}},async batch(statements){beforeBatch?.();beforeBatch=null;return statements.map(statement=>statement._run());}};
const users={admin:{id:'admin',app_metadata:{roles:['offmenu-admin']}},ordinary:{id:'ordinary',app_metadata:{roles:[]}},forged:{id:'forged',user_metadata:{roles:['admin']}}};
const origin='https://offmenu.example';
const options={verifiedUser:async request=>users[request.headers.get('Cookie')]||null,boundedJSON:request=>request.json()};
const request=(path,{method='GET',cookie='admin',body,originHeader=origin}={})=>new Request(origin+path,{method,headers:{Cookie:cookie,Origin:originHeader},body:body===undefined?undefined:JSON.stringify(body)});
const call=(path,args)=>adminOperationsRoutes(request(path,args),{DB},options);

test('only trusted administrator metadata may inspect reviewed public source policies',async()=>{
 assert.equal((await call('/api/admin/sources',{cookie:'ordinary'})).status,403);
 assert.equal((await call('/api/admin/sources',{cookie:'forged'})).status,403);
 const response=await call('/api/admin/sources');assert.equal(response.status,200);
 const body=await response.json();assert.deepEqual(body.sources.map(source=>source.id),['gleif','wikidata']);
  assert.equal(body.sources.every(source=>source.document.promotion==='user-contributed promotion disabled'),true);
 assert.deepEqual(body.audit,[]);
});
test('administrator can only CAS suspend and reactivate an unchanged public policy',async()=>{
 const source=(await(await call('/api/admin/sources')).json()).sources.find(item=>item.id==='gleif');
 assert.equal((await call('/api/admin/sources/gleif',{method:'PUT',body:{revision:source.revision,active:false,confirmed:true},originHeader:'https://evil.example'})).status,403);
 const updated=await call('/api/admin/sources/gleif',{method:'PUT',body:{revision:source.revision,active:false,confirmed:true}});assert.equal(updated.status,200);assert.deepEqual(await updated.json(),{id:'gleif',revision:2,active:false,action:'suspended'});
 assert.equal(database.prepare("SELECT active FROM source_policies WHERE id='gleif'").get().active,0);
 assert.equal(database.prepare("SELECT count(*) AS n FROM admin_operations_audit WHERE source_id='gleif' AND action='suspended'").get().n,1);
 assert.equal((await call('/api/admin/sources/gleif',{method:'PUT',body:{revision:1,active:false,confirmed:true}})).status,409);
 assert.equal(database.prepare("SELECT count(*) AS n FROM admin_operations_audit WHERE source_id='gleif'").get().n,1);
});
test('routes never query private account or credential tables and reject policy-shaped writes',async()=>{
 queries.length=0;
 const response=await call('/api/admin/sources/gleif',{method:'PUT',body:{revision:2,active:true,confirmed:true,document:{license:'changed'},owner:'alice'}});
 assert.equal(response.status,400);
 assert.equal(queries.some(sql=>/private_documents|provider_connections|user_state|unified_records|service_requests|health|credential/i.test(sql)),false);
});
test('a non-public or malformed policy is never made administrable',async()=>{
 database.prepare('INSERT INTO source_policies(id,document,revision,active) VALUES(?,?,?,?)').run('internal',JSON.stringify({id:'internal',version:'1',license:'private',actions:['display'],audiences:['private'],countries:[],evidenceUrl:'https://example.test',expiresAt:null,personalFields:'none',promotion:'user-contributed promotion disabled'}),1,1);
 assert.equal((await call('/api/admin/sources/internal',{method:'PUT',body:{revision:1,active:false,confirmed:true}})).status,404);
});
test('a stale operation that races after its precheck cannot write a loser audit row',async()=>{
 const prior=database.prepare("SELECT revision FROM source_policies WHERE id='wikidata'").get().revision;
 const before=database.prepare("SELECT count(*) AS n FROM admin_operations_audit WHERE source_id='wikidata'").get().n;
 beforeBatch=()=>database.prepare("UPDATE source_policies SET active=0,revision=revision+1 WHERE id='wikidata'").run();
 const response=await call('/api/admin/sources/wikidata',{method:'PUT',body:{revision:prior,active:false,confirmed:true}});
 assert.equal(response.status,409);
 assert.equal(database.prepare("SELECT count(*) AS n FROM admin_operations_audit WHERE source_id='wikidata'").get().n,before);
});
