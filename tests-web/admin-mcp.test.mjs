import test from 'node:test';
import assert from 'node:assert/strict';
import {DatabaseSync} from 'node:sqlite';
import {readFileSync} from 'node:fs';
import {integrationRoutes} from '../cloud/integrations.mjs';

const database=new DatabaseSync(':memory:');
database.exec(readFileSync(new URL('../cloud/schema.sql',import.meta.url),'utf8'));
database.exec(readFileSync(new URL('../cloud/admin-mcp-schema.sql',import.meta.url),'utf8'));
function statement(sql,params=[]){return {async first(){return database.prepare(sql).get(...params)||null;},async run(){return database.prepare(sql).run(...params);},async all(){return {results:database.prepare(sql).all(...params)};},_sql:sql,_params:params,bind(...values){return statement(sql,values);}};}
const env={PROVIDER_VAULT_KEY:'a'.repeat(64),DB:{prepare:sql=>statement(sql),async batch(items){return items.map(item=>{const result=database.prepare(item._sql).all(...item._params);return {results:result,meta:{changes:database.prepare('SELECT changes() AS changes').get().changes}};});}}};
const origin='https://offmenu.test',exp=Math.floor(Date.now()/1000)+600;
const identity='x.'+btoa(JSON.stringify({exp})).replaceAll('+','-').replaceAll('/','_').replaceAll('=','')+'.y';
let admin=true;
const options={verifiedUser:async request=>request.headers.get('Authorization')==='Bearer '+identity?{id:'staff',app_metadata:{roles:admin?['offmenu-admin']:[]}}:request.headers.get('Cookie')?.includes('nf_jwt='+identity)||request.headers.get('Cookie')==='staff'?{id:'staff',app_metadata:{roles:admin?['offmenu-admin']:[]}}:request.headers.get('Cookie')==='member'?{id:'member',app_metadata:{roles:['admin']}}:null,boundedJSON:request=>request.json(),assets:{}};
const request=(path,{method='POST',body,authorization,cookie}={})=>new Request(origin+path,{method,headers:{Origin:origin,...(authorization?{Authorization:'Bearer '+authorization}:{}),...(cookie?{Cookie:cookie}:{})},body:body===undefined?undefined:typeof body==='string'?body:JSON.stringify(body)});
const call=(path,options0)=>integrationRoutes(request(path,options0),env,options);

test('administrative grants need a fresh trusted role, stay MCP-only, and expose no private tools',async()=>{
 const denied=await call('/api/integrations/tokens',{body:{scopes:['admin:community:read']},cookie:'staff'});assert.equal(denied.status,403);
 const mixed=await call('/api/integrations/tokens',{body:{scopes:['admin:community:read','inventory:read']},authorization:identity});assert.equal(mixed.status,400);
 const apiAudience=await call('/api/integrations/tokens',{body:{resource:'api',scopes:['admin:community:read']},authorization:identity});assert.equal(apiAudience.status,403);
 const issued=await (await call('/api/integrations/tokens',{body:{scopes:['admin:community:read']},authorization:identity})).json();assert.ok(issued.access_token);assert.ok(issued.expires_in<=900);
 const tools=await (await call('/mcp',{authorization:issued.access_token,body:{jsonrpc:'2.0',id:1,method:'tools/list'}})).json();assert.deepEqual(tools.result.tools.map(row=>row.name),['listCommunityQueue']);assert.equal(JSON.stringify(tools).includes(identity),false);
 admin=false;
 const revoked=await call('/mcp',{authorization:issued.access_token,body:{jsonrpc:'2.0',id:2,method:'tools/list'}});assert.equal(revoked.status,403);
});
test('OAuth transfers only a sealed, short-lived administrator proof to its one-time MCP token',async()=>{
 admin=true;const client=await (await call('/oauth/register',{body:{redirect_uris:['https://client.example/callback']}})).json(),verifier='b'.repeat(43),query=new URLSearchParams({client_id:client.client_id,redirect_uri:'https://client.example/callback',response_type:'code',code_challenge:await (await import('../cloud/integrations.mjs')).digest(verifier),code_challenge_method:'S256',resource:origin+'/mcp',scope:'admin:community:read'}),approved=await (await call('/oauth/approve',{body:{query:query.toString()},cookie:'nf_jwt='+identity})).json(),code=new URL(approved.redirect).searchParams.get('code'),form=new URLSearchParams({grant_type:'authorization_code',code,client_id:client.client_id,redirect_uri:'https://client.example/callback',code_verifier:verifier,resource:origin+'/mcp'}),token=await (await call('/oauth/token',{body:form.toString()})).json();assert.ok(token.access_token,JSON.stringify(token));assert.equal(database.prepare('SELECT count(*) AS n FROM oauth_admin_proofs').get().n,0);const listed=await (await call('/mcp',{authorization:token.access_token,body:{jsonrpc:'2.0',id:3,method:'tools/list'}})).json();assert.deepEqual(listed.result.tools.map(row=>row.name),['listCommunityQueue']);
});
test('a browser Identity cookie can mint an admin proof and malformed cookie authority is refused',async()=>{
 admin=true;const cookie='nf_jwt='+identity,issued=await (await call('/api/integrations/tokens',{cookie,body:{scopes:['admin:updates:manage']}})).json();assert.ok(issued.access_token);const malformed=await call('/api/integrations/tokens',{cookie:'nf_jwt=%E0%A4%A',body:{scopes:['admin:updates:manage']}});assert.equal(malformed.status,401);
});
test('administrative tool attempts are correlated to each opaque delegation',async()=>{
 admin=true;const first=await (await call('/api/integrations/tokens',{authorization:identity,body:{name:'First delegation',scopes:['admin:community:read']}})).json(),second=await (await call('/api/integrations/tokens',{authorization:identity,body:{name:'Second delegation',scopes:['admin:community:read']}})).json();for(const token of [first,second])await call('/mcp',{authorization:token.access_token,body:{jsonrpc:'2.0',id:7,method:'tools/call',params:{name:'listCommunityQueue',arguments:{}}}});const rows=database.prepare('SELECT DISTINCT token_id FROM admin_mcp_audit WHERE tool=?').all('listCommunityQueue');assert.ok(rows.some(row=>row.token_id===first.id));assert.ok(rows.some(row=>row.token_id===second.id));
});
