import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare,createFetchMock} from 'miniflare';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';

test('compiled administrator controls preserve private ownership, fresh roles, CAS audit and atomic rollback',async()=>{
 const mock=createFetchMock();mock.disableNetConnect();
 let adminRole=true,sentryCalls=0;
 mock.get('https://o1.ingest.sentry.io').intercept({path:'/api/2/envelope/',method:'POST'}).reply(200,()=>{sentryCalls++;return '';}).persist();
 mock.get('https://offmenu-accounts.netlify.app').intercept({path:'/.netlify/identity/user',method:'GET'}).reply(200,({headers})=>{const token=headers.authorization||headers.Authorization;return JSON.stringify(token==='Bearer admin'?{id:'admin',app_metadata:{roles:adminRole?['offmenu-admin']:[]}}:{id:'ordinary',app_metadata:{roles:[]},user_metadata:{roles:['admin']}});}).persist();
 const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],d1Databases:['DB'],fetchMock:mock,bindings:{THIRD_PARTY_CONFIG:JSON.stringify({client:{diagnostics:{enabled:true}}}),SENTRY_DSN:'https://0123456789abcdef@o1.ingest.sentry.io/2',PROVIDER_VAULT_KEY:'a'.repeat(64),BREVO_API_KEY:'environment-secret-key',BREVO_SENDER_NAME:'OffMenu',BREVO_SENDER_EMAIL:'sender@example.test',SUPPORT_EMAIL:'support@example.test'}});
 try{
  const db=await worker.getD1Database('DB'),schema=new DatabaseSync(':memory:');
  for(const file of ['schema.sql','catalogue-schema.sql','corpus-schema.sql'])schema.exec(readFileSync('cloud/'+file,'utf8'));
  for(const {sql} of schema.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all())await db.prepare(sql).run();
  for(const row of schema.prepare('SELECT id,document,revision,active FROM source_policies').all())await db.prepare('INSERT INTO source_policies(id,document,revision,active) VALUES(?,?,?,?)').bind(row.id,row.document,row.revision,row.active).run();schema.close();
  await db.prepare("INSERT INTO user_state(user_id,revision,state_json,updated_at) VALUES('alice',1,?,?)").bind(JSON.stringify({private:'ALICE_PRIVATE_RESULT'}),new Date().toISOString()).run();
  await db.prepare("INSERT INTO provider_connections(user_id,source_id,label,sealed,updated_at) VALUES('alice','usda','ALICE_PRIVATE_CONNECTION','ALICE_SEALED_SECRET',?)").bind(new Date().toISOString()).run();
  const request=(path,token='admin',body)=>worker.dispatchFetch('https://offmenu.test'+path,{method:body?'PUT':'GET',headers:{Authorization:'Bearer '+token,Origin:'https://offmenu.test','Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  assert.equal((await request('/api/admin/settings','ordinary')).status,403);
  const initial=await (await request('/api/admin/settings')).json();assert.equal(initial.revision,0);assert(!JSON.stringify(initial).includes('environment-secret-key'));
  for(const path of ['/api/state?userId=alice','/api/data/connections?userId=alice','/api/data/records?owner=alice','/api/services/support?owner=alice']){const response=await request(path);const text=await response.text();assert.equal(response.status,200,path);assert(!text.includes('ALICE_'),path);}
  const settings={services:{seo:{googleSiteVerification:'admin-property'}},global:{defaults:{country:'AU',units:'imperial',servings:3,uiLanguage:'ar'},features:{supportEmail:false,documentEmail:false}}};
  const body={revision:0,confirmed:true,settings};
  const concurrent=await Promise.all([request('/api/admin/settings','admin',body),request('/api/admin/settings','admin',body)]);assert.deepEqual(concurrent.map(x=>x.status).sort(),[200,409]);
  assert.equal((await db.prepare('SELECT count(*) AS n FROM app_settings_audit').first()).n,1);
  const config=await(await request('/api/services')).json();assert.equal(config.globalDefaults.country,'AU');assert.equal(config.services.find(x=>x.id==='support').status,'setup_required');assert(!JSON.stringify(config).includes('environment-secret-key'));
  const html=await worker.dispatchFetch('https://offmenu.test/');assert.equal(html.headers.get('Content-Language'),'ar');assert((await html.text()).includes('admin-property'));
  const edit={...body,revision:1,settings:{...settings,global:{defaults:{country:'GB'}}}};
  const race=await Promise.all([request('/api/admin/settings','admin',edit),request('/api/admin/settings','admin',edit)]);assert.deepEqual(race.map(x=>x.status).sort(),[200,409]);assert.equal((await db.prepare('SELECT count(*) AS n FROM app_settings_audit').first()).n,2);
  const sourceResult=await(await request('/api/admin/sources')).json(),gleif=sourceResult.sources.find(x=>x.id==='gleif');assert(gleif);
  const sourceBody={revision:gleif.revision,active:false,confirmed:true};
  const sourceRace=await Promise.all([request('/api/admin/sources/gleif','admin',sourceBody),request('/api/admin/sources/gleif','admin',sourceBody)]);assert.deepEqual(sourceRace.map(x=>x.status).sort(),[200,409]);assert.equal((await db.prepare('SELECT count(*) AS n FROM admin_operations_audit').first()).n,1);
  assert.equal((await request('/api/admin/sources/gleif','admin',{revision:gleif.revision+1,active:true,confirmed:true})).status,200);assert.equal((await db.prepare('SELECT count(*) AS n FROM admin_operations_audit').first()).n,2);
  await db.prepare('DROP TABLE admin_operations_audit').run();assert.equal((await request('/api/admin/sources/gleif','admin',{revision:gleif.revision+2,active:false,confirmed:true})).status,503);assert.equal((await db.prepare("SELECT active FROM source_policies WHERE id='gleif'").first()).active,1);
  adminRole=false;assert.equal((await request('/api/admin/settings')).status,403);assert.equal((await request('/api/admin/settings','admin',{...edit,revision:2})).status,403);adminRole=true;
  await db.prepare('DROP TABLE app_settings_audit').run();assert.equal((await request('/api/admin/settings','admin',{...edit,revision:2})).status,503);assert.equal((await db.prepare('SELECT revision FROM app_settings').first()).revision,2);
  await db.prepare('DROP TABLE recipes').run();assert.equal((await request('/api/recipes')).status,503);assert.equal(sentryCalls,0);
  await db.prepare("UPDATE app_settings SET sealed_credentials='corrupt'").run();assert.equal((await request('/api/recipes')).status,503);assert.equal(sentryCalls,0);
  assert.equal((await db.prepare("SELECT count(*) AS n FROM user_state WHERE user_id='alice'").first()).n,1);assert.equal((await db.prepare("SELECT sealed FROM provider_connections WHERE user_id='alice'").first()).sealed,'ALICE_SEALED_SECRET');
 }finally{await worker.dispose();}
});
