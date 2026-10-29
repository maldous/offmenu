import test from 'node:test';
import assert from 'node:assert/strict';
import {Miniflare} from 'miniflare';
import {readFileSync} from 'node:fs';
import {DatabaseSync} from 'node:sqlite';

test('compiled Worker uses canonical additive schema and exposes only configured capabilities',async()=>{
 const worker=new Miniflare({modules:true,scriptPath:'dist/worker.mjs',compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],d1Databases:['DB'],bindings:{THIRD_PARTY_CONFIG:JSON.stringify({seo:{googleSiteVerification:'offmenu-test-property'},client:{feedback:{productId:'123'}}}),BREVO_API_KEY:'private-test-secret',BREVO_SENDER_NAME:'OffMenu test',BREVO_SENDER_EMAIL:'sender@example.test',SUPPORT_EMAIL:'support@example.test',PROVIDER_VAULT_KEY:'f'.repeat(64)}});
 try {
  const db=await worker.getD1Database('DB');
  const source=new DatabaseSync(':memory:');
  for(const file of ['schema.sql','catalogue-schema.sql','corpus-schema.sql'])source.exec(readFileSync('apps/web/server/'+file,'utf8'));
  for(const {sql} of source.prepare("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY CASE type WHEN 'table' THEN 0 ELSE 1 END").all())await db.prepare(sql).run();
  source.close();
  const response=await worker.dispatchFetch('https://offmenu.test/api/services');assert.equal(response.status,200);
  const body=await response.json();assert.equal(body.services.find(s=>s.id==='brevo').status,'configured');assert(!JSON.stringify(body).includes('private-test-secret'));
  const page=await worker.dispatchFetch('https://offmenu.test/',{headers:{'Accept-Language':'en'}}),html=await page.text();
  assert(html.includes('id="third-party-services"'));assert(html.includes('id="document-email"'));assert(html.includes('name="google-site-verification" content="offmenu-test-property"'));
  assert(page.headers.get('Content-Security-Policy').includes('https://client.sleekplan.com'));assert(!html.includes('client.sleekplan.com/sdk/e.js')); // No vendor script loaded before explicit choice.
  const csrf=await worker.dispatchFetch('https://offmenu.test/api/services/support',{method:'POST',headers:{Origin:'https://other.test','Content-Type':'application/json'},body:JSON.stringify({confirmed:true})});assert.equal(csrf.status,403);
  const anonymous=await worker.dispatchFetch('https://offmenu.test/api/services/support');assert.equal(anonymous.status,401);
  assert.equal((await db.prepare("SELECT COUNT(*) AS count FROM service_requests").first()).count,0);
  const now=Date.now();for(const [table,key] of [['admin_mcp_proofs','token_id'],['oauth_admin_proofs','code_hash']]){
   await db.prepare(`INSERT INTO ${table}(${key},sealed,expires_at) VALUES(?,?,?)`).bind('expired','synthetic expired proof',now-60000).run();
   await db.prepare(`INSERT INTO ${table}(${key},sealed,expires_at) VALUES(?,?,?)`).bind('live','synthetic live proof',now+60000).run();
  }
  await (await worker.getWorker()).scheduled();
  for(const table of ['admin_mcp_proofs','oauth_admin_proofs'])assert.deepEqual((await db.prepare(`SELECT sealed FROM ${table}`).all()).results.map(row=>row.sealed),['synthetic live proof']);
  assert.equal((await db.prepare('SELECT COUNT(*) AS count FROM user_state').first()).count,0);
 } finally {await worker.dispose();}
});
