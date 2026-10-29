import test from 'node:test';
import assert from 'node:assert/strict';
import {createEnvelopeCryptor,credentialUseAllowed} from '../../apps/web/server/byoc-envelope-v1.mjs';
const subject={ownerUserId:'owner-a',kitchenId:null,objectType:'connection',objectId:'connection-a',purpose:'provider_credentials',providerId:'fixture-provider'};
const reference={keyRef:'opaque-fixture-key',keyVersion:1};
async function fixture(){ const key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);return createEnvelopeCryptor({resolveKey:async request=>request.keyRef===reference.keyRef&&request.keyVersion===1?key:null}); }
test('synthetic round trip; encrypted payload never appears in envelope; random nonce',async()=>{
 const crypt=await fixture(),value={apiKey:'SYNTHETIC-NOT-A-REAL-SECRET'};
 const a=await crypt.seal(value,subject,reference),b=await crypt.seal(value,subject,reference);
 assert.deepEqual(await crypt.open(a,subject),value);assert.notEqual(a.nonce,b.nonce);assert(!JSON.stringify(a).includes(value.apiKey));
});
test('every AAD boundary blocks swapped ciphertext',async()=>{
 const crypt=await fixture(),sealed=await crypt.seal({fixture:true},subject,reference);
 for(const field of ['ownerUserId','kitchenId','objectType','objectId','purpose','providerId']) await assert.rejects(crypt.open(sealed,{...subject,[field]:'other'}),/^Error: Protected data unavailable\.$/);
});
test('missing key, version, malformed/tampered bytes and custody mismatch fail closed',async()=>{
 const crypt=await fixture(),sealed=await crypt.seal({fixture:true},subject,reference);
 const missing=createEnvelopeCryptor({resolveKey:async()=>null});
 await assert.rejects(missing.open(sealed,subject),/Protected data unavailable/);
 await assert.rejects(missing.seal({fixture:true},subject,reference),/Protected data unavailable/);
 for(const changed of [{version:2},{keyVersion:2},{custody:'client'},{nonce:'AAAA'},{ciphertext:'?not-base64'},{ciphertext:sealed.ciphertext.replace(/^./,sealed.ciphertext[0]==='A'?'B':'A')},{extra:'not permitted'}]) await assert.rejects(crypt.open({...sealed,...changed},subject),/Protected data unavailable/);
});
test('key adapter failures and extractable/raw key material are sanitized',async()=>{
 for(const resolver of [async()=>{throw Error('DO-NOT-DISCLOSE');},async()=>new Uint8Array(32),async()=>crypto.subtle.generateKey({name:'AES-GCM',length:256},true,['encrypt','decrypt'])]){
  const crypt=createEnvelopeCryptor({resolveKey:resolver});await assert.rejects(crypt.seal({fixture:true},subject,reference),/^Error: Protected data unavailable\.$/);
 }
});
test('client custody is explicit and cannot use server decrypt instance',async()=>{
 const key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
 const client=createEnvelopeCryptor({resolveKey:async()=>key,custody:'client'}),server=createEnvelopeCryptor({resolveKey:async()=>key});
 const sealed=await client.seal({fixture:true},subject,reference);assert.deepEqual(await client.open(sealed,subject),{fixture:true});await assert.rejects(server.open(sealed,subject));
});
test('bounded larger synthetic payload works without stack spread; oversize denied',async()=>{
 const crypt=await fixture(),value={fixture:'x'.repeat(100000)};const sealed=await crypt.seal(value,subject,reference);assert.deepEqual(await crypt.open(sealed,subject),value);
 await assert.rejects(crypt.seal({fixture:'x'.repeat(1048576)},subject,reference));
});
function useFixture(){return {now:100,context:{authenticated:true,requestAuthorized:true,ownerUserId:'a',providerId:'p',connectionId:'c',sessionId:'s',issuer:'idp',audience:'offmenu',realm:'r',sessionEpoch:1,entitlementRevision:1,scope:'lookup',resource:'p/foods',purpose:'private_use'},connection:{id:'c',ownerUserId:'a',providerId:'p',status:'active',custody:'server-envelope',expiresAt:200,revokedAt:null,entitlementRevision:1,consentId:'consent',consentRevision:1,sourcePolicyId:'policy',sourcePolicyRevision:1,keyRef:'key',keyVersion:1},session:{id:'s',issuer:'idp',ownerUserId:'a',audience:'offmenu',realm:'r',epoch:1,expiresAt:200,revokedAt:null},consent:{id:'consent',ownerUserId:'a',revision:1,objectType:'connection',objectId:'c',purpose:'private_use',choice:'granted',validFrom:50,expiresAt:200},policy:{id:'policy',revision:1,active:true,proxyAllowed:true,expiresAt:200},key:{id:'key',ownerUserId:'a',version:1,status:'active',expiresAt:200},scopes:[{ownerUserId:'a',connectionId:'c',scope:'lookup',resource:'p/foods',purpose:'private_use'}]};}
test('fresh private-use snapshot passes; owner/provider/entitlement/session/consent/policy/key/scope changes deny',()=>{
 assert.equal(credentialUseAllowed(useFixture()),true);
 const mutations=[['context','ownerUserId','other'],['context','providerId','other'],['context','requestAuthorized',false],['context','purpose','background_refresh'],['connection','entitlementRevision',2],['connection','status','revoked'],['connection','custody','client'],['connection','expiresAt',100],['session','epoch',2],['session','issuer','other'],['session','revokedAt',99],['consent','choice','withdrawn'],['consent','revision',2],['consent','expiresAt',100],['consent','validFrom',101],['policy','proxyAllowed',false],['policy','revision',2],['key','status','revoked'],['key','expiresAt',100]];
 for(const [group,field,value] of mutations){const f=useFixture();f[group][field]=value;assert.equal(credentialUseAllowed(f),false,`${group}.${field}`);}
 for (const field of ['ownerUserId','connectionId']) {const f=useFixture(); f.scopes[0][field]='other'; assert.equal(credentialUseAllowed(f),false,`scope.${field}`);}
 const noScope=useFixture();noScope.scopes=[];assert.equal(credentialUseAllowed(noScope),false);assert.equal(credentialUseAllowed(),false);
});
