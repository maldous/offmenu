import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {createLotRestrictionConsumer, RETAINED_HELPER_PIN} from '../../cloud/lot-restriction-owner28.mjs';
// Exercise the integrated source, without a historical Git object dependency.
// Keep an exact retained-helper byte check alongside its historical commit pin.
const source = readFileSync(new URL('../../public/package-restriction-evidence.js', import.meta.url));
const blob = createHash('sha1').update(`blob ${source.length}\0`).update(source).digest('hex');
assert.equal(blob, '4dce5090bc16af30bd667398e639401d92ce71c8');
assert.equal(RETAINED_HELPER_PIN, 'e829f61c181a5965ffba70462433d4b446f226c7');
const {packageRestrictionEvidence} = await import('../../public/package-restriction-evidence.js');
const now = Date.parse('2026-10-14T10:00:00Z');
const account = {owner:'a', market:'AU', evidenceConsent:true, lots:[{id:'l',owner:'a',productId:'p',lotCode:'B',quantity:3}], products:[{id:'p',owner:'a',sourceId:'supplier',assertionSubject:'supplier:p',matchStatus:'verified'}], preferences:[{id:'pref',owner:'a',sourceId:'user:a',revision:'r1',recordedAt:'2026-10-01',rule:{predicate:'halal',operator:'include',value:true,certifiedOnly:true}}], policies:{supplier:{active:true,actions:['display','derive'],audiences:['private']}}, assertions:[{id:'supplier:e',sourceId:'supplier',subject:'supplier:p',owner:'a',market:'AU',scope:{kind:'lot',lotCode:'B'},predicate:'halal',value:true,matchStatus:'verified',evidenceClass:'certified',schemeId:'s',certifierId:'c',validFrom:'2026-10-01',validUntil:'2026-11-01',freshUntil:'2026-11-01'}]};
const request = (body={lotId:'l',preferenceId:'pref'},origin='https://app.example') => new Request('https://app.example/api/catalogue/lot-restriction',{method:'POST',headers:{Origin:origin},body:JSON.stringify(body)});
const route = (data=account,user={id:'a'}) => createLotRestrictionConsumer({verifiedUser:async()=>user,loadAccount:async()=>data,clock:()=>now,evaluateScoped:packageRestrictionEvidence});
test('HTTP adapter executes retained evaluator with account lot and preference provenance',async()=>{
 const before=structuredClone(account), response=await route()(request()), body=await response.json();
 assert.equal(response.status,200); assert.equal(response.headers.get('Cache-Control'),'no-store');
 assert.equal(body.status,'pass');assert.equal(body.binding.preferenceRevision,'r1');assert.deepEqual(body.evidenceIds,['supplier:e']);assert.equal(body.automaticSelection,false);assert.deepEqual(account,before);
});
test('another lot, revoked rights and missing consent withhold positive source claims',async()=>{
 for(const change of [a=>a.assertions[0].scope.lotCode='A',a=>a.evidenceConsent=false,a=>a.policies={}]){const a=structuredClone(account);change(a);assert.equal((await (await route(a)(request())).json()).status,'unknown');}
});
test('authentication, origin and request-provided assertions cannot bypass account binding',async()=>{
 assert.equal((await route(account,null)(request())).status,401);
 assert.equal((await route()(request(undefined,'https://evil.example'))).status,403);
 assert.equal((await route()(request({lotId:'l',preferenceId:'pref',assertions:[]}))).status,400);
 assert.equal((await route({...account,owner:'b'})(request())).status,403);
});
test('missing preference provenance or foreign product withholds decisions',async()=>{
 for(const change of [a=>delete a.preferences[0].revision,a=>a.preferences[0].recordedAt='2027-01-01',a=>a.products[0].owner='b']){const a=structuredClone(account);change(a);assert.equal((await (await route(a)(request())).json()).status,'unknown');}
});
test('streaming body cap and unrelated route',async()=>{
 assert.equal((await route()(request({lotId:'x'.repeat(5000),preferenceId:'pref'}))).status,413);
 assert.equal(await route()(new Request('https://app.example/elsewhere')),null);
});
