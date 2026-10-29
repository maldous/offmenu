import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare,createFetchMock} from 'miniflare';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';
test('compiled MCP enforces delegated tool scopes and fresh administrator roles',async()=>{
 const identity='x.'+Buffer.from(JSON.stringify({exp:Math.floor(Date.now()/1000)+600})).toString('base64url')+'.y';let role=true;
 const mock=createFetchMock();mock.disableNetConnect();
 mock.get('https://offmenu-accounts.netlify.app').intercept({path:'/.netlify/identity/user',method:'GET'}).reply(200,()=>JSON.stringify({id:'staff',app_metadata:{roles:role?['offmenu-admin']:[]}})).persist();
 const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],d1Databases:['DB'],fetchMock:mock,bindings:{PROVIDER_VAULT_KEY:'a'.repeat(64)}});
 try{
  const db=await worker.getD1Database('DB'),schema=new DatabaseSync(':memory:');schema.exec(readFileSync('apps/web/server/schema.sql','utf8'));
  for(const {sql} of schema.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all())await db.prepare(sql).run();schema.close();
  const post=(path,token,body)=>worker.dispatchFetch('https://offmenu.test'+path,{method:'POST',headers:{Authorization:'Bearer '+token,Origin:'https://offmenu.test','Content-Type':'application/json'},body:JSON.stringify(body)});
  const mint=async scopes=>{const r=await post('/api/integrations/tokens',identity,{name:'Compiled scoped test',scopes});assert.equal(r.status,201);return (await r.json()).access_token;};
  const read=await mint(['admin:community:read']);
  const invoke=async(token,name,args={})=>{const r=await post('/mcp',token,{jsonrpc:'2.0',id:1,method:'tools/call',params:{name,arguments:args}});assert.equal(r.status,200);return (await r.json()).result;};
  let result=await invoke(read,'configureCommunityAISettings',{revision:0,confirmed:true,settings:{enabled:true,provider:'mcp'}});assert.equal(result.isError,true);assert.equal((await db.prepare('SELECT count(*) n FROM community_ai_settings').first()).n,0);
  result=await invoke(read,'readServiceSettings');assert.equal(result.isError,true);
  result=await invoke(read,'runCommunityAIReview',{confirmed:true});assert.equal(result.isError,true);
  result=await invoke(read,'listCommunityAIDecisions');assert.equal(result.isError,false);assert.deepEqual(result.structuredContent.decisions,[]);
  const manage=await mint(['admin:settings:read','admin:settings:write','admin:community:manage']);
  const settings=(await invoke(manage,'readCommunityAISettings')).structuredContent;
  result=await invoke(manage,'configureCommunityAISettings',{revision:settings.revision,confirmed:true,settings:{...settings.settings,enabled:true,provider:'mcp'}});assert.equal(result.isError,false);
  result=await invoke(manage,'runCommunityAIReview',{confirmed:true});assert.equal(result.isError,false);assert.equal(result.structuredContent.ran,true);
  assert.equal((await db.prepare("SELECT count(*) n FROM admin_mcp_audit WHERE tool='configureCommunityAISettings' AND status='succeeded'").first()).n,1);
  const recipeId='00000000-0000-4000-8000-000000000001',commentId='00000000-0000-4000-8000-000000000002',stamp=new Date().toISOString();
  await db.prepare("INSERT INTO community_recipes(id,author_id,alias,recipe_json,source_ref,status,revision,write_id,created_at,updated_at) VALUES(?,?,?,?,?,'published',1,?,?,?)").bind(recipeId,'private-author','Chosen alias','{}','original','fixture',stamp,stamp).run();
  await db.prepare("INSERT INTO community_recipe_comments(id,recipe_id,author_id,alias,body,status,revision,write_id,created_at,updated_at) VALUES(?,?,?,?,?,'pending',1,?,?,?)").bind(commentId,recipeId,'private-author','Chosen alias','Public recipe comment.','fixture',stamp,stamp).run();
  result=await invoke(manage,'runCommunityAIReview',{confirmed:true});assert.equal(result.isError,false);assert.equal(result.structuredContent.outcomes[0].kind,'recipe-comment');assert.equal(result.structuredContent.outcomes[0].state,'awaiting_agent');
  result=await invoke(read,'completeCommunityAIDecision',{kind:'recipe-comment',id:commentId,revision:1,confirmed:true,action:'approve',reason:'Reviewed comment'});assert.equal(result.isError,true);
  assert.equal((await db.prepare('SELECT status FROM community_recipe_comments WHERE id=?').bind(commentId).first()).status,'pending');
  result=await invoke(manage,'completeCommunityAIDecision',{kind:'recipe-comment',id:commentId,revision:1,confirmed:true,action:'approve',reason:'Reviewed comment'});assert.equal(result.isError,false);assert.equal(result.structuredContent.completed,true);assert(!JSON.stringify(result).includes('private-author'));
  assert.equal((await db.prepare('SELECT status FROM community_recipe_comments WHERE id=?').bind(commentId).first()).status,'published');
  assert.equal((await db.prepare('SELECT state FROM community_ai_decisions WHERE candidate_id=?').bind(commentId).first()).state,'applied');
  assert.equal((await db.prepare("SELECT count(*) n FROM community_recipe_audit WHERE subject_id=? AND actor_id='staff'").bind(commentId).first()).n,1);
  role=false;const revoked=await post('/mcp',manage,{jsonrpc:'2.0',id:2,method:'tools/call',params:{name:'runCommunityAIReview',arguments:{confirmed:true}}});assert.equal(revoked.status,403);
 }finally{await worker.dispose();}
});
