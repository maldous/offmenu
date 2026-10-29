import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {readFileSync} from 'node:fs';
import schema from '../../schemas/private-portable-package-v1.schema.json' with {type:'json'};
import {createEnvelopeCryptor} from '../../cloud/byoc-envelope-v1.mjs';
import {createPrivatePortability,validatePrivatePayload,digest,canonical,destinationRecordId} from '../../cloud/private-portability-v1.mjs';

// Generated fixtures only. No DB, provider, credential, auth route or network use.
const now=1800000000000,at=new Date(now).toISOString();
const src={ownerUserId:'fixture-owner',issuer:'https://fixture-source.invalid/idp',subject:'same-subject'};
const dst={ownerUserId:'fixture-destination',issuer:'https://fixture-destination.invalid/idp',subject:'same-subject'};
const fields=schema.properties.scope.properties.fields.items.enum;
const source={sourceId:'generated',version:'1',recordId:'fixture',recordedAt:at};
const clone=v=>JSON.parse(JSON.stringify(v));
const recordKey=r=>JSON.stringify([r.type,r.id]);
const quantity={value:'2.500000',unit:'g',dimension:'mass',status:'measured'};
function record(type,id,data,kitchen=null) {return {type,id,ownerRef:src.ownerUserId,householdRef:kitchen,revision:1,lifecycle:'active',provenance:clone(source),extensions:[],data};}
async function payload() {
  const records=[
    record('space','kitchen-a',{label:'Fixture home'},'kitchen-a'),
    record('location','location-a',{spaceId:'kitchen-a',parentId:null,kind:'pantry',label:'Fixture pantry'},'kitchen-a'),
    record('item','item-a',{label:'Fixture oats',productRef:null,ingredientRef:null,identityStatus:'unknown'},'kitchen-a'),
    record('lot','lot-a',{itemId:'item-a',lotCode:'FIXTURE-LOT',useBy:null,bestBefore:'2027-03-01',storage:'ambient'},'kitchen-a'),
    record('holding','holding-a',{locationId:'location-a',itemId:'item-a',lotId:'lot-a',quantity:clone(quantity),availability:'available'},'kitchen-a'),
    record('movement','movement-a',{holdingId:'holding-a',lotId:'lot-a',kind:'acquire',delta:'2.5',unit:'g',occurredAt:at},'kitchen-a'),
    record('reservation','reservation-a',{holdingId:'holding-a',quantity:clone(quantity),status:'released',expiresAt:null},'kitchen-a'),
    record('movement','waste-movement',{holdingId:'holding-a',lotId:'lot-a',kind:'waste',delta:'-0.1',unit:'g',occurredAt:at},'kitchen-a'),
    record('waste','waste-a',{movementId:'waste-movement',quantity:{...quantity,value:'0.1'},reason:null},'kitchen-a'),
    record('profile','profile-a',{displayName:'Generated fixture person',dietary:['Fixture declaration'],allergies:[{substance:'Fixture substance',kind:'intolerance',verification:'declared'}],preferences:[],diagnoses:[]}),
    record('medical_plan','plan-a',{profileId:'profile-a',planType:'recommendation',status:'active',intent:'proposal',effectiveFrom:at,effectiveUntil:null,source:clone(source),authorRef:null,goals:['Fixture goal'],activities:['Fixture activity'],recommendationProvenance:[clone(source)]}),
    record('settings','settings-a',{uiLanguage:'en',dataLanguage:'en',units:'metric'}),
    record('content','content-a',{contentType:'note',text:'Generated content, not actual private data.'}),
    record('identity_link','identity-a',{issuer:src.issuer,subject:src.subject,status:'linked'}),
    record('connection_metadata','connection-a',{providerId:'fixture-provider',authentication:'oauth2',toolProtocol:'none',capabilities:['lookup'],scopes:['read'],sourceStatus:'revoked',requiresReauthorization:true}),
    record('auth_history','auth-a',{action:'revoke',occurredAt:at,outcome:'complete'}),
    record('consent_history','consent-a',{purpose:'fixture-private-use',sourceStatus:'withdrawn',effectiveAuthority:'none',consentId:'historic-consent',revision:1,recipient:clone(src),fields:['inventory'],validFrom:new Date(now-1000).toISOString(),expiresAt:new Date(now+1000).toISOString(),revokedAt:at,auditRef:'fixture-audit'}),
    record('derived_provenance','derived-a',{source:clone(source),method:'Generated derivation'})
  ];
  records.find(r=>r.type==='profile').extensions.push({namespace:'fixture.future',version:'2',value:{unknownFutureAttribute:{originalLabel:'Preserved fixture'}}});
  const text='Generated attachment';
  return {records,attachments:[{id:'attachment-a',forRecord:{type:'content',id:'content-a'},mediaType:'text/plain',bytes:new TextEncoder().encode(text).length,sha256:await digest(text),base64:btoa(text),provenance:clone(source)}],relationships:[{type:'fixture-provenance',from:{type:'profile',id:'profile-a'},to:{type:'medical_plan',id:'plan-a'},provenance:clone(source)}],extensions:[],coverage:{content:'included',settings:'included',attachments:'included',relationships:'included',history:'included',derived_provenance:'included'},lossWarnings:[]};
}
function authority(identity,namespace,purpose,recipient,records) {
  return {principal:{id:identity.ownerUserId},identity:clone(identity),namespace,revision:1,auth:{reauthenticatedAt:now-100,expiresAt:now+10000,revokedAt:null},kitchens:identity.ownerUserId===src.ownerUserId?['kitchen-a']:['kitchen-b'],allowedRecords:records.map(recordKey),tombstones:[],recoveryRefs:['independent-fixture-recovery'],consent:{id:identity.ownerUserId===src.ownerUserId?'source-consent':'destination-consent',revision:1,ownerUserId:identity.ownerUserId,recipient:clone(recipient),purpose,fields:clone(fields),validFrom:now-1000,expiresAt:now+10000,revokedAt:null,choice:'granted'},records:[]};
}
async function fixture({kind='owned-backup',executor=false}={}) {
  const data=await payload();
  if(kind==='portability') {data.records=data.records.filter(r=>['space','location','item','lot','holding','movement','reservation','waste','profile','medical_plan','derived_provenance'].includes(r.type));data.attachments=[];}
  const recipient=kind==='privacy-access'?src:dst;
  const s=authority(src,'fixture-source',kind,recipient,data.records),d=authority(dst,'fixture-destination','restore',dst,[]);
  s.backupInventory={complete:true,payloadDigest:await digest(data)};
  for(const r of data.records) d.allowedRecords.push(recordKey({type:r.type,id:await destinationRecordId({sourceNamespace:s.namespace,sourceIdentity:src,record:r,destinationNamespace:d.namespace,destinationIdentity:dst,kitchenMap:{'kitchen-a':'kitchen-b'}})}));
  const keys=new Map([['source-key',await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt'])],['destination-key',await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt'])]]);
  const state={source:s,destination:d,resolveCalls:0,reads:[],onRead:null,onResolve:null,failAfter:null,rows:[],receipts:new Map(),commits:0,executorCalls:0};
  const resolveKey=async r=>{state.resolveCalls++;if(state.onResolve) await state.onResolve(r);return keys.get(r.keyRef)??null;};
  const atomicRestore=async (plan,fence)=>{
    state.executorCalls++;
    // GENERATED in-memory adapter model, not an actual D1/remote transaction proof.
    assert.equal(fence.authorityDigest,await digest({source:state.source,destination:state.destination}));
    const existing=state.receipts.get(plan.idempotencyKey);
    if(existing) {assert.equal(existing.contentDigest,plan.contentDigest);return {...existing,status:'already-committed'};}
    assert.equal(fence.sourceRevision,state.source.revision);assert.equal(fence.destinationRevision,state.destination.revision);
    const staged=clone(state.rows);
    for(const op of plan.operations) {if(op.action==='insert') staged.push(op);if(state.failAfter!==null&&staged.length>=state.failAfter) throw Error('GENERATED_TRANSACTION_FAILURE');}
    const receipt={idempotencyKey:plan.idempotencyKey,contentDigest:plan.contentDigest,status:'committed'};
    // One generated commit point; simulated earlier failures never publish staging.
    state.rows=staged;state.receipts.set(plan.idempotencyKey,receipt);state.commits++;state.destination.revision++;
    state.destination.records=state.rows.map(({type,id,digest})=>({type,id,digest}));return receipt;
  };
  const api=createPrivatePortability({readAuthority:async q=>{state.reads.push(q);if(state.onRead) await state.onRead(q);return q.operation==='restore'?{source:state.source,destination:state.destination}:state.source;},resolveKey,clock:()=>now,...(executor?{atomicRestore}:{})});
  const exportRequest={packageId:'fixture-package',kind,sourceSchemaVersion:'offmenu-household-domain/1',payload:data,recoveryRef:'independent-fixture-recovery',keyReference:{keyRef:'source-key',keyVersion:1}};
  const make=()=>api.exportPackage(exportRequest);
  const restore=p=>({package:p,destination:{namespace:d.namespace,identity:clone(dst)},kitchenMap:{'kitchen-a':'kitchen-b'},keyReference:{keyRef:'destination-key',keyVersion:1}});
  const openPlan=async plan=>createEnvelopeCryptor({resolveKey}).open(plan.envelope,{ownerUserId:dst.ownerUserId,kitchenId:null,objectType:'private-portable-package',objectId:'fixture-package',purpose:'owned_data_portability/manifest1:'+plan.manifestDigest,providerId:null});
  return {data,state,api,exportRequest,make,restore,openPlan};
}
async function rechecksum(p) {const {checksum,...rest}=p;p.checksum=await digest(rest);return p;}
async function rewritePublicManifest(p) {
  // The digest algorithm is public: an attacker can recompute it and the outer
  // checksum, but cannot produce a valid GCM tag for a changed manifest.
  if(Object.hasOwn(p,'manifestDigest')) {
    const {checksum,envelope,manifestDigest,...header}=p;
    p.manifestDigest=await digest(['offmenu-private-package-manifest/1',header]);
  }
  return rechecksum(p);
}

test('provider P1 authenticates immutable manifest even when rewritten metadata matches fresh authority',async()=>{
  const clean=await fixture({kind:'privacy-access'});assert.deepEqual(await clean.api.accessReport(await clean.make()),clean.data);
  const mutations=[
    (p,a)=>{p.identity.issuer=a.identity.issuer='https://relinked-fixture.invalid';p.recipient.issuer=a.consent.recipient.issuer=a.identity.issuer;},
    (p,a)=>{p.identity.subject=a.identity.subject='Relinked:Opaque_Subject';p.recipient.subject=a.consent.recipient.subject=a.identity.subject;},
    (p,a)=>{p.consent.revision=++a.consent.revision;},
    (p,a)=>{p.consent.id=a.consent.id='replacement-consent';},
    p=>{p.scope.fields=p.scope.fields.filter(f=>f!=='profile.displayName');},
    (p,a)=>{p.protection.recoveryRef='another-qualified-recovery';a.recoveryRefs.push(p.protection.recoveryRef);},
    (p,a)=>{p.source.namespace=a.namespace='replacement-fixture-namespace';},
    p=>{p.createdAt=new Date(now+1).toISOString();}
  ];
  for(const mutate of mutations) {const f=await fixture({kind:'privacy-access'}),p=clone(await f.make());mutate(p,f.state.source);await rewritePublicManifest(p);await assert.rejects(f.api.accessReport(p),/REPORT_DENIED/);}
  const f=await fixture(),p=clone(await f.make()),newIdentity={...dst,issuer:'https://new-recipient-fixture.invalid'};
  p.recipient=clone(newIdentity);f.state.source.consent.recipient=clone(newIdentity);f.state.destination.identity=clone(newIdentity);f.state.destination.consent.recipient=clone(newIdentity);
  f.state.destination.allowedRecords=[];
  for(const r of f.data.records) f.state.destination.allowedRecords.push(recordKey({type:r.type,id:await destinationRecordId({sourceNamespace:f.state.source.namespace,sourceIdentity:src,record:r,destinationNamespace:f.state.destination.namespace,destinationIdentity:newIdentity,kitchenMap:{'kitchen-a':'kitchen-b'}})}));
  await rewritePublicManifest(p);const request=f.restore(p);request.destination.identity=clone(newIdentity);await assert.rejects(f.api.planRestore(request),/RESTORE_PLAN_DENIED/);
});
test('provider P1 excludes generic credential fields recursively from extension data',async()=>{
  for(const name of ['token','oauthToken','secret','secretKey','oauth_token','oauth-token','SECRET_KEY']) {
    const f=await fixture();f.data.extensions.push({namespace:'fixture',version:'1',value:{nested:[{[name]:'GENERATED-ONLY-NONSECRET-SENTINEL'}]}});f.state.source.backupInventory.payloadDigest=await digest(f.data);
    await assert.rejects(validatePrivatePayload(f.data),/SECRET_FIELD/);await assert.rejects(f.make(),/EXPORT_DENIED/);assert.equal(f.state.resolveCalls,0);
  }
  const p=await payload();p.extensions.push({namespace:'fixture',version:'1',value:{tokenCount:3,secretary:'Fixture text'}});assert(await validatePrivatePayload(p));
});
test('provider P2 validates raw RFC URI syntax and retains accepted issuer text exactly',async()=>{
  const invalid=['https://example.invalid/a b','https://example.invalid/a\nb','https://example.invalid/a\\b','https://example.invalid/%zz','https://user@@example.invalid/','https://[2001:db8:::1]/','https://[v1.]/','https://example.invalid/path[bad]','https://example.invalid/?x=[bad]','https://example.invalid/#a#b','https://example.invalid/café'];
  for(const uri of invalid) {const p=await payload();p.records.find(r=>r.type==='identity_link').data.issuer=uri;await assert.rejects(validatePrivatePayload(p),/PAYLOAD_SCHEMA/);}
  const valid=['https://Example.COM/A%20B?x=a%2Fb#Frag','urn:example:Original-Subject_01','mailto:fixture@example.invalid','https://[2001:db8::1]/path','https://[::ffff:192.0.2.1]/','https://[v1.a:b]/','file:///fixture'];
  for(const uri of valid) {const p=await payload();p.records.find(r=>r.type==='identity_link').data.issuer=uri;assert.equal((await validatePrivatePayload(p)).records.find(r=>r.type==='identity_link').data.issuer,uri);}
  const script="import json,sys,jsonschema\nd=json.load(sys.stdin);v=jsonschema.FormatChecker()\nif 'uri' in v.checkers:\n assert all(v.conforms(x,'uri') for x in d['valid'])\n assert all(not v.conforms(x,'uri') for x in d['invalid'])\n print('independent URI format controls PASS')\nelse:\n print('independent URI format checker NOT_AVAILABLE; runtime RFC sample controls run separately')\n";
  const r=spawnSync('python3',['-B','-c',script],{input:JSON.stringify({valid,invalid}),encoding:'utf8'});assert.equal(r.status,0,r.stderr);
});
test('provider P2 medical-plan consent matches owner, exact profile, private purpose and granted choice on insert/update',()=>{
  const script=`import sqlite3,pathlib
c=sqlite3.connect(':memory:');c.execute('PRAGMA foreign_keys=ON')
for p in ['cloud/schema.sql','cloud/migrations/20261022-byoc-security-v1.sql','cloud/migrations/20261022-household-domain-v1.sql','cloud/migrations/20261023-private-portability-v2.sql']:c.executescript(pathlib.Path(p).read_text())
c.execute("INSERT INTO sec_key_references VALUES ('key','owner','server-envelope','external',1,'AES-256-GCM','active',0,200,NULL,NULL)")
def envelope(i,t,o,p,n):c.execute('INSERT INTO sec_envelopes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'owner',None,t,o,p,'',1,'server-envelope','key',1,'AES-256-GCM',bytes([n])*12,bytes(17),0,200,1))
for n,profile in enumerate(['profile','other-profile'],1):
 envelope(profile+'-envelope','household_profiles',profile,'household-profile/1',n)
 c.execute('INSERT INTO household_profiles VALUES (?,?,?,?,?,?,?)',('owner',profile,profile+'-envelope',1,'active','date','date'))
def consent(i,obj,oid,purpose,choice):c.execute('INSERT INTO sec_consents VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'owner','owner',obj,oid,purpose,'grantee' if purpose=='profile_share' else None,None,'notice',choice,1,0,200,1))
consent('valid','household_profile','profile','private_use','granted')
consent('valid-new','household_profile','profile','private_use','granted')
consent('denied','household_profile','profile','private_use','denied')
consent('withdrawn','household_profile','profile','private_use','withdrawn')
consent('connection','connection','fixture-connection','private_use','granted')
consent('other-profile','household_profile','other-profile','private_use','granted')
consent('contribute','household_profile','profile','contribute_facts','granted')
consent('sharing','household_profile','profile','profile_share','granted')
envelope('plan-envelope','household_medical_plans','plan','household-medical-plan/1',3)
def denied(sql,args):
 try:c.execute(sql,args)
 except sqlite3.IntegrityError:return
 raise AssertionError('Expected exact medical consent denial')
for bad in ['denied','withdrawn','connection','other-profile','contribute','sharing']:
 denied('INSERT INTO household_medical_plans VALUES (?,?,?,?,?,?,?,?,?)',('owner','plan','profile','plan-envelope',bad,1,'active','date',200))
c.execute('INSERT INTO household_medical_plans VALUES (?,?,?,?,?,?,?,?,?)',('owner','plan','profile','plan-envelope','valid',1,'active','date',200))
for bad in ['denied','withdrawn','connection','other-profile','contribute','sharing']:denied('UPDATE household_medical_plans SET consent_id=?',(bad,))
denied('UPDATE household_medical_plans SET profile_id=?',('other-profile',))
c.execute("UPDATE household_medical_plans SET consent_id='valid-new'")
assert c.execute('SELECT consent_id FROM household_medical_plans').fetchone()[0]=='valid-new'
assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
print('generated exact medical consent insert/update controls PASS')
`;
  const r=spawnSync('python3',['-B','-c',script],{cwd:new URL('../../',import.meta.url),encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/PASS/);
});

test('all 17 typed kinds, original provenance, versioned unknown attributes and byte manifests validate',async()=>{
  const data=await payload();assert.equal(new Set(data.records.map(r=>r.type)).size,17);assert.equal((await validatePrivatePayload(data)).records.length,18);
  assert.deepEqual(JSON.parse(canonical(data)),data);
});
test('encrypted backup round trip rebinds every internal reference, preserves unknowns and reencrypts at destination',async()=>{
  const f=await fixture(),p=await f.make(),plan=await f.api.planRestore(f.restore(p)),restored=await f.openPlan(plan);
  assert.equal(p.kind,'owned-backup');assert.equal(restored.records.length,18);assert.equal(plan.conflicts.length,0);
  assert.equal(plan.envelope.keyRef,'destination-key');assert.notEqual(plan.envelope.nonce,p.envelope.nonce);
  assert(!JSON.stringify(p).includes('Generated fixture person'));assert(!JSON.stringify(plan).includes('Fixture substance'));
  for(const r of restored.records) {assert.equal(r.ownerRef,dst.ownerUserId);assert([null,'kitchen-b'].includes(r.householdRef));assert.deepEqual(r.provenance,source);}
  const profile=restored.records.find(r=>r.type==='profile'),medical=restored.records.find(r=>r.type==='medical_plan');
  assert.equal(medical.data.profileId,profile.id);assert.equal(restored.relationships[0].to.id,medical.id);
  assert.deepEqual(profile.extensions[0],f.data.records.find(r=>r.type==='profile').extensions[0]);
  assert.deepEqual(restored.attachments[0].provenance,source);assert.equal(restored.attachments[0].base64,f.data.attachments[0].base64);
  assert.equal(restored.records.find(r=>r.type==='identity_link').data.status,'unlinked');
  for(const t of ['connection_metadata','identity_link','consent_history','auth_history','movement','waste']) assert(plan.operations.filter(r=>r.type===t).every(r=>r.disposition==='history-only'));
  assert.equal(plan.operations.find(r=>r.type==='medical_plan').disposition,'clinical-review-required');
});
test('access report is owner-only readable data and can never be imported as restore input',async()=>{
  const f=await fixture({kind:'privacy-access'}),p=await f.make();assert.deepEqual(await f.api.accessReport(p),f.data);
  await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  const other=await fixture();await assert.rejects(other.api.accessReport(await other.make()),/REPORT_DENIED/);
});
for(const count of [99,100]) test(`review R1 preserves all ${count} source extensions with separately bounded import origin`,async()=>{
  const f=await fixture(),profile=f.data.records.find(r=>r.type==='profile');
  profile.extensions=Array.from({length:count},(_,i)=>({namespace:`fixture.future.${i}`,version:'1',value:{originalAttribute:`Fixture ${i}`}}));
  f.state.source.backupInventory.payloadDigest=await digest(f.data);
  const p=await f.make(),plan=await f.api.planRestore(f.restore(p)),restored=await f.openPlan(plan),imported=restored.records.find(r=>r.type==='profile');
  assert.equal(imported.extensions.length,count);assert.deepEqual(imported.extensions,profile.extensions);
  assert.deepEqual(imported.importOrigin,{version:1,sourceNamespace:f.state.source.namespace,sourceIdentity:src,sourceId:profile.id});
  assert(await validatePrivatePayload(restored));
  // Subsequent imports retain the first origin without growing either collection.
  profile.importOrigin={version:1,sourceNamespace:'fixture-original-instance',sourceIdentity:{...src,subject:'Original:Opaque_Subject'},sourceId:'original-profile'};
  f.state.source.backupInventory.payloadDigest=await digest(f.data);
  const again=await f.openPlan(await f.api.planRestore(f.restore(await f.make()))),againProfile=again.records.find(r=>r.type==='profile');
  assert.deepEqual(againProfile.importOrigin,profile.importOrigin);assert.deepEqual(againProfile.extensions,profile.extensions);
  const invalid=clone(again);invalid.records.find(r=>r.type==='profile').importOrigin.extra='untyped-origin';await assert.rejects(validatePrivatePayload(invalid));
});
test('review R2 rejects unknown and credential destination properties before decryption; clean exact shape succeeds',async()=>{
  const f=await fixture(),p=await f.make(),clean=f.restore(p),plan=await f.api.planRestore(clean);
  assert.deepEqual(plan.destination,clean.destination);assert.deepEqual(Object.keys(plan.destination).sort(),['identity','namespace']);
  const calls=f.state.resolveCalls,reads=f.state.reads.length,sentinel='GENERATED-ONLY-NONSECRET-SENTINEL';
  const mutations=[
    d=>d.apiKey=sentinel,
    d=>d.unknown='unrecognized',
    d=>d.extra={nested:{apiKey:sentinel}},
    d=>d.identity.apiKey=sentinel,
    d=>d.identity.unknown='unrecognized',
    d=>d.identity.extra={nested:{access_token:sentinel}},
    d=>d.identity.roles=['administrator'],
    d=>d.identity.issuer={value:dst.issuer,clientSecret:sentinel},
    d=>d.namespace={value:'fixture-destination',password:sentinel},
    d=>d.namespace=7,
    d=>delete d.identity.subject,
    d=>d.identity=null
  ];
  for(const mutate of mutations) {const request=f.restore(p);mutate(request.destination);await assert.rejects(f.api.planRestore(request),/^Error: Private portability unavailable \(RESTORE_PLAN_DENIED\)\.$/);}
  assert.equal(f.state.resolveCalls,calls);assert.equal(f.state.reads.length,reads);assert.equal(f.state.executorCalls,0);
});
test('portable transfer accepts profile/inventory data while full backup cannot hide unavailable coverage',async()=>{
  const f=await fixture({kind:'portability'});assert.equal((await f.api.planRestore(f.restore(await f.make()))).conflicts.length,0);
  f.exportRequest.payload.records.push(record('settings','forbidden-settings',{uiLanguage:'en',dataLanguage:'en',units:'metric'}));f.state.source.allowedRecords.push(recordKey(f.exportRequest.payload.records.at(-1)));
  await assert.rejects(f.make(),/EXPORT_DENIED/);
  const b=await fixture();b.exportRequest.payload.coverage.content='unavailable';await assert.rejects(b.make(),/EXPORT_DENIED/);
  const partial=await fixture();partial.data.records=partial.data.records.filter(r=>r.type!=='settings');await assert.rejects(partial.make(),/EXPORT_DENIED/);
});
test('opaque owner, issuer and subject are independently enforced; same subject at another issuer is not identity',async()=>{
  for(const mutate of [a=>a.principal.id='other',a=>a.identity.issuer='https://collision.invalid',a=>a.identity.subject='other',a=>a.identity.ownerUserId='other']) {
    const f=await fixture(),p=await f.make();mutate(f.state.source);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  }
  const f=await fixture(),p=await f.make(),r=f.restore(p);r.destination.identity.issuer=src.issuer;await assert.rejects(f.api.planRestore(r),/RESTORE_PLAN_DENIED/);
});
test('unverified identity/session state, expired auth and missing independent key recovery fail closed',async()=>{
  for(const mutate of [a=>delete a.principal,a=>delete a.identity.issuer,a=>a.auth.revokedAt=now-1,a=>a.auth.expiresAt=now,a=>a.auth.reauthenticatedAt=now-300001,a=>a.auth.reauthenticatedAt=now+1,a=>a.recoveryRefs=[]]) {
    const f=await fixture();mutate(f.state.source);await assert.rejects(f.make(),/EXPORT_DENIED/);
  }
});
test('recipient, purpose, exact field scope, record allowlist and kitchens are mandatory',async()=>{
  for(const mutate of [a=>a.consent.recipient.issuer='other',a=>a.consent.purpose='other',a=>a.consent.fields=['inventory'],a=>a.allowedRecords=[],a=>a.kitchens=[]]) {
    const f=await fixture(),p=await f.make();mutate(f.state.source);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  }
  for(const mutate of [a=>a.consent.recipient.subject='other',a=>a.consent.purpose='owned-backup',a=>a.consent.fields=[],a=>a.allowedRecords=[],a=>a.kitchens=[]]) {
    const f=await fixture(),p=await f.make();mutate(f.state.destination);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  }
});
test('partial profile fields require explicit redactions; medical plans have separate field permission',async()=>{
  const f=await fixture({kind:'privacy-access'});f.data.records=f.data.records.filter(r=>r.type==='profile');f.data.attachments=[];f.data.relationships=[];
  const profile=f.data.records[0];profile.extensions=[];f.state.source.consent.fields=['profile.allergies'];f.state.source.allowedRecords=[recordKey(profile)];
  await assert.rejects(f.make(),/EXPORT_DENIED/);
  for(const name of ['displayName','dietary','preferences','diagnoses']) profile.data[name]=null;
  assert.deepEqual((await f.api.accessReport(await f.make())).records[0].data.allergies,profile.data.allergies);
});
test('revoked/expired consent and tombstones cannot be restored from a downloaded package',async()=>{
  for(const mutate of [a=>a.consent.revokedAt=now,a=>a.consent.choice='withdrawn',a=>a.consent.expiresAt=now,a=>a.consent.validFrom=now+1,a=>a.tombstones.push(a.allowedRecords[0])]) {
    for(const side of ['source','destination']) {const f=await fixture(),p=await f.make();mutate(f.state[side]);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);}
  }
  const f=await fixture(),p=await f.make();f.state.source.consent.revision++;await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  const g=await fixture(),q=await g.make();g.state.destination.consent.revision++;const plan=await g.api.planRestore(g.restore(q));assert.equal(plan.destinationConsent.revision,2);
});
test('revocation during key-resolution await denies export/plan and never invokes a restore executor',async()=>{
  const f=await fixture();f.state.onResolve=async()=>{f.state.source.consent.revokedAt=now;};await assert.rejects(f.make(),/EXPORT_DENIED/);
  const g=await fixture({executor:true}),p=await g.make();g.state.onResolve=async()=>{g.state.destination.consent.revision++;};await assert.rejects(g.api.planRestore(g.restore(p)),/RESTORE_PLAN_DENIED/);assert.equal(g.state.executorCalls,0);
});
test('destination/source bindings and ciphertext digests cannot be relabeled',async()=>{
  for(const mutate of [p=>p.identity.issuer='other',p=>p.identity.ownerUserId='other',p=>p.source.namespace='other',p=>p.envelope.keyRef='destination-key',p=>p.envelope.ciphertext=p.envelope.ciphertext.replace(/^./,p.envelope.ciphertext[0]==='A'?'B':'A'),p=>p.scope.records.pop(),p=>p.recipient.subject='other']) {
    const f=await fixture(),p=clone(await f.make());mutate(p);await rechecksum(p);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
  }
  const f=await fixture(),p=clone(await f.make());p.checksum='0'.repeat(64);await assert.rejects(f.api.planRestore(f.restore(p)),/RESTORE_PLAN_DENIED/);
});
test('unknown versions and untyped records are rejected rather than coerced',async()=>{
  const f=await fixture();f.exportRequest.sourceSchemaVersion='future/2';await assert.rejects(f.make(),/EXPORT_DENIED/);assert.equal(f.state.resolveCalls,0);
  const p=await payload();p.records[0].type='grant';await assert.rejects(validatePrivatePayload(p),/PAYLOAD_SCHEMA/);
  const g=await fixture(),q=clone(await g.make());q.schemaVersion='future/2';await rechecksum(q);await assert.rejects(g.api.planRestore(g.restore(q)),/RESTORE_PLAN_DENIED/);
});
test('hierarchy cycles, foreign kitchens, duplicate stable IDs and dangling relationships fail',async()=>{
  for(const mutate of [p=>p.records.find(r=>r.type==='location').data.parentId='location-a',p=>p.records.find(r=>r.type==='lot').data.itemId='not-in-package',p=>p.records.find(r=>r.type==='location').householdRef='other-kitchen',p=>p.records.push(clone(p.records[0])),p=>p.relationships[0].to.id='missing']) {const p=await payload();mutate(p);await assert.rejects(validatePrivatePayload(p));}
  const p=await payload(),a=p.records.find(r=>r.type==='location');a.data.parentId='location-b';const b=clone(a);b.id='location-b';b.data.parentId='location-a';p.records.push(b);await assert.rejects(validatePrivatePayload(p),/HIERARCHY_CYCLE/);
});
test('quantities preserve decimal precision, unknowns and source basis; invalid signs/dates/basis fail',async()=>{
  for(const mutate of [p=>p.records.find(r=>r.type==='holding').data.quantity.value='2.1234567',p=>p.records.find(r=>r.type==='holding').data.quantity.value=null,p=>p.records.find(r=>r.type==='holding').data.quantity.value='9000000001',p=>p.records.find(r=>r.type==='movement').data.delta='-1',p=>p.records.find(r=>r.type==='movement').data.unit='ml',p=>p.records.find(r=>r.type==='lot').data.bestBefore='2027-02-30',p=>p.records.find(r=>r.type==='reservation').data.quantity.dimension='volume']) {const p=await payload();mutate(p);await assert.rejects(validatePrivatePayload(p));}
  const p=await payload();p.records.find(r=>r.type==='holding').data.quantity={...quantity,value:null,status:'unknown'};assert(await validatePrivatePayload(p));
});
test('attachment byte/checksum mismatch, missing parent and unsafe path properties fail',async()=>{
  for(const mutate of [a=>a.bytes++,a=>a.sha256='0'.repeat(64),a=>a.forRecord.id='missing',a=>a.path='/actual/private/file',a=>a.base64+='=']) {const p=await payload();mutate(p.attachments[0]);await assert.rejects(validatePrivatePayload(p));}
});
test('medical recommendations need provenance, and invalid URI/date-time forms are rejected',async()=>{
  for(const mutate of [p=>p.records.find(r=>r.type==='medical_plan').data.recommendationProvenance=[],p=>p.records.find(r=>r.type==='medical_plan').data.effectiveUntil=p.records.find(r=>r.type==='medical_plan').data.effectiveFrom,p=>p.records.find(r=>r.type==='identity_link').data.issuer='relative-issuer',p=>p.records[0].provenance.recordedAt='2027-01-01T24:00:00Z']) {const p=await payload();mutate(p);await assert.rejects(validatePrivatePayload(p));}
});
test('BYOC/service/session/key secrets and live grant record kinds never enter a package',async()=>{
  for(const name of ['apiKey','access_token','refreshToken','password','session','cookie','clientSecret','privateKey','wrappedKey','credentials']) {const f=await fixture();f.data.extensions.push({namespace:'fixture.extension',version:'1',value:{[name]:'GENERATED-SECRET-SENTINEL'}});await assert.rejects(f.make(),/EXPORT_DENIED/);assert.equal(f.state.resolveCalls,0);}
  const f=await fixture();f.data.records.find(r=>r.type==='connection_metadata').data.credentialRef='not-allowed';await assert.rejects(f.make(),/EXPORT_DENIED/);
  assert.throws(()=>createPrivatePortability(),/ADAPTER_REQUIRED/);
});
test('dry run does not write; conflicts are explicit and cannot reach executor',async()=>{
  const f=await fixture({executor:true}),p=await f.make(),first=await f.api.planRestore(f.restore(p));
  assert.equal(f.state.commits,0);assert.equal(f.state.rows.length,0);assert.equal(f.state.executorCalls,0);
  f.state.destination.records=[{type:first.operations[0].type,id:first.operations[0].id,digest:'0'.repeat(64)}];
  const conflict=await f.api.planRestore(f.restore(p));assert.equal(conflict.conflicts.length,1);await assert.rejects(f.api.commitRestore(conflict),/COMMIT_DENIED/);assert.equal(f.state.executorCalls,0);
});
test('generated transaction model rolls back all staged rows on failure, then replays idempotently',async()=>{
  const f=await fixture({executor:true}),p=await f.make(),plan=await f.api.planRestore(f.restore(p));
  f.state.failAfter=3;await assert.rejects(f.api.commitRestore(plan),/COMMIT_DENIED/);assert.equal(f.state.rows.length,0);assert.equal(f.state.receipts.size,0);assert.equal(f.state.destination.revision,1);
  f.state.failAfter=null;assert.equal((await f.api.commitRestore(plan)).status,'committed');assert.equal(f.state.rows.length,18);
  assert.equal((await f.api.commitRestore(plan)).status,'already-committed');assert.equal(f.state.commits,1);
  const repeated=await f.api.planRestore(f.restore(p));assert(repeated.operations.every(o=>o.action==='skip-identical'));assert.equal(repeated.contentDigest,plan.contentDigest);assert.equal((await f.api.commitRestore(repeated)).status,'already-committed');
});
test('commit requires a trusted executor and same-instance issued capability; forged checksums do not authorize',async()=>{
  const f=await fixture(),p=await f.make(),plan=await f.api.planRestore(f.restore(p));await assert.rejects(f.api.commitRestore(plan),/COMMIT_DENIED/);
  const g=await fixture({executor:true});await assert.rejects(g.api.commitRestore(plan),/COMMIT_DENIED/);assert.equal(g.state.executorCalls,0);
  const h=await fixture({executor:true}),q=await h.api.planRestore(h.restore(await h.make())),forged=clone(q);forged.operations[0].disposition='owned-data';forged.operations[0].id='attacker';await rechecksum(forged);await assert.rejects(h.api.commitRestore(forged),/COMMIT_DENIED/);assert.equal(h.state.executorCalls,0);
});
test('commit rechecks consent/deletion fences; changed destination revision fails generated CAS atomically',async()=>{
  for(const mutate of [a=>a.consent.revokedAt=now,a=>a.consent.revision++,a=>a.tombstones.push(a.allowedRecords[0])]) {const f=await fixture({executor:true}),q=await f.api.planRestore(f.restore(await f.make()));mutate(f.state.destination);await assert.rejects(f.api.commitRestore(q),/COMMIT_DENIED/);assert.equal(f.state.executorCalls,0);assert.equal(f.state.rows.length,0);}
  const f=await fixture({executor:true}),q=await f.api.planRestore(f.restore(await f.make()));f.state.destination.revision++;await assert.rejects(f.api.commitRestore(q),/COMMIT_DENIED/);assert.equal(f.state.rows.length,0);
});
test('request mutation during await cannot redirect destination or alter retained input',async()=>{
  const f=await fixture(),p=await f.make(),request=f.restore(p);f.state.onRead=async q=>{if(q.operation==='restore'&&q.phase==='start') request.destination.identity.ownerUserId='mutated-after-call';};
  const plan=await f.api.planRestore(request);assert.equal(plan.destination.identity.ownerUserId,dst.ownerUserId);assert.equal(p.identity.ownerUserId,src.ownerUserId);
});
test('errors sanitize trusted resolver/executor details and source AAD remains incompatible with destination',async()=>{
  const f=await fixture(),p=await f.make();f.state.onResolve=async()=>{throw Error('DO-NOT-EXPOSE-KEY-SERVICE-DETAIL');};await assert.rejects(f.api.planRestore(f.restore(p)),/^Error: Private portability unavailable \(RESTORE_PLAN_DENIED\)\.$/);
  const g=await fixture(),q=await g.make(),plan=await g.api.planRestore(g.restore(q));await assert.rejects(g.openPlan({...plan,envelope:q.envelope}),/Protected data unavailable/);
});
test('bounded/deep/non-JSON data are rejected',async()=>{
  const p=await payload();p.extensions.push({namespace:'fixture',version:'1',value:{text:'x'.repeat(2000001)}});await assert.rejects(validatePrivatePayload(p));
  const cyclic={};cyclic.self=cyclic;await assert.rejects(validatePrivatePayload(cyclic));assert.throws(()=>canonical({value:undefined}));assert.throws(()=>canonical({value:Infinity}));
});
test('pinned JSON Schema agrees with generated public package and decrypted payload acceptance/rejection',async()=>{
  const f=await fixture(),p=await f.make();const input={package:p,payload:f.data};
  const script=`import json,sys,jsonschema\ns=json.load(open('schemas/private-portable-package-v1.schema.json'));jsonschema.Draft202012Validator.check_schema(s)\nd=json.load(sys.stdin);v=jsonschema.Draft202012Validator(s,format_checker=jsonschema.FormatChecker());v.validate(d['package'])\nps=dict(s);ps['$ref']='#/$defs/payload';ps.pop('type');ps.pop('properties');ps.pop('required');ps.pop('additionalProperties');pv=jsonschema.Draft202012Validator(ps,format_checker=jsonschema.FormatChecker());pv.validate(d['payload'])\nd['payload']['records'][0]['data']['unexpected']='x';assert list(pv.iter_errors(d['payload']))\nprint('metaschema/package/payload/negative PASS')\n`;
  const r=spawnSync('python3',['-B','-c',script],{cwd:new URL('../../',import.meta.url),input:JSON.stringify(input),encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/PASS/);
});
test('SQL proposal applies only to generated in-memory SQLite and enforces scopes, bindings, dispositions and rollback',()=>{
  // Deliberately no filesystem DB path and no actual D1/service binding.
  const script=`import sqlite3,pathlib\nc=sqlite3.connect(':memory:');c.execute('PRAGMA foreign_keys=ON')\nfor p in ['cloud/schema.sql','cloud/migrations/20261022-byoc-security-v1.sql','cloud/migrations/20261022-household-domain-v1.sql','cloud/migrations/20261023-private-portability-v2.sql']: c.executescript(pathlib.Path(p).read_text())\nc.execute("INSERT INTO sec_consents VALUES ('c','owner','owner','private_record','fixture','private_use',NULL,NULL,'notice','granted',1,0,200,1)")\nscope=('owner','c',1,'destination','issuer','subject','owned-backup','inventory',0,200,'audit')\nc.execute('INSERT INTO private_portability_consent_fields VALUES (?,?,?,?,?,?,?,?,?,?,?)',scope)\ndef denied(sql,args=()):\n try: c.execute(sql,args)\n except sqlite3.IntegrityError: return\n raise AssertionError('Expected constraint denial')\ndenied('INSERT INTO private_portability_consent_fields VALUES (?,?,?,?,?,?,?,?,?,?,?)',tuple(2 if i==2 else x for i,x in enumerate(scope)))\ndenied("UPDATE private_portability_consent_fields SET recipient_issuer='other'")\nc.execute("INSERT INTO sec_key_references VALUES ('key','owner','server-envelope','external',1,'AES-256-GCM','active',0,200,NULL,NULL)")\nc.execute("INSERT INTO sec_envelopes VALUES ('bundle','owner',NULL,'private-portable-package','package','owned_data_portability/manifest1:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','',1,'server-envelope','key',1,'AES-256-GCM',zeroblob(12),zeroblob(17),0,200,1)")\nreceipt=('owner','i'*64,'d'*64,'source','s'*64,'destination','issuer','subject',1,1,1,2,10,'a'*64,'a'*64)\nrow=('owner','identity_link','identity','i'*64,'source','original','package','bundle','r'*64,'history-only')\nc.commit();c.execute('BEGIN');c.execute('INSERT INTO private_restore_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',receipt);c.execute('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',row);c.rollback()\nassert c.execute('SELECT count(*) FROM private_restore_receipts').fetchone()[0]==0\nassert c.execute('SELECT count(*) FROM private_owned_imports').fetchone()[0]==0\nc.execute('INSERT INTO private_restore_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',receipt);c.execute('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',row);c.commit()\ndenied('INSERT INTO private_restore_receipts VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',receipt)\ndenied("UPDATE private_restore_receipts SET content_digest=?",('f'*64,))\ndenied('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',tuple('owned-data' if i==9 else 'identity2' if i==2 else x for i,x in enumerate(row)))\ndenied('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',tuple('other-owner' if i==0 else 'identity3' if i==2 else x for i,x in enumerate(row)))\ndenied('INSERT INTO household_medical_plans VALUES (?,?,?,?,?,?,?,?,?)',('owner','plan','missing-profile','bundle','c',1,'active','date',200))\nc.execute("INSERT INTO sec_envelopes VALUES ('wrong-manifest','owner',NULL,'private-portable-package','package','owned_data_portability/manifest1:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb','',1,'server-envelope','key',1,'AES-256-GCM',?,zeroblob(17),0,200,1)",(bytes([9])*12,))\ndenied('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',tuple('wrong-manifest' if i==7 else 'wrong-digest-record' if i==2 else x for i,x in enumerate(row)))\ndenied('INSERT INTO private_owned_imports VALUES (?,?,?,?,?,?,?,?,?,?)',tuple('wrong-package' if i==6 else 'wrong-package-record' if i==2 else x for i,x in enumerate(row)))\nassert c.execute('PRAGMA foreign_key_check').fetchall()==[]\nassert c.execute("SELECT count(*) FROM household_schema_versions WHERE version='offmenu-private-portability/1'").fetchone()[0]==1\nprint('generated in-memory SQLite constraints/rollback PASS; not native D1 qualification')\n`;
  const r=spawnSync('python3',['-B','-c',script],{cwd:new URL('../../',import.meta.url),encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/PASS/);
});
test('source-only seam imports existing cryptor and exposes no network, route, process or persistence activation',()=>{
  const text=readFileSync(new URL('../../cloud/private-portability-v1.mjs',import.meta.url),'utf8');assert.match(text,/from '\.\/byoc-envelope-v1\.mjs'/);assert(!/\b(?:fetch|createServer|spawn|execSync|setInterval|setTimeout)\s*\(/.test(text));
});
test('generated SQL medical-plan rows reuse the exact private profile owner and versioned envelope binding',()=>{
  const script=`import sqlite3,pathlib
c=sqlite3.connect(':memory:');c.execute('PRAGMA foreign_keys=ON')
for p in ['cloud/schema.sql','cloud/migrations/20261022-byoc-security-v1.sql','cloud/migrations/20261022-household-domain-v1.sql','cloud/migrations/20261023-private-portability-v2.sql']:c.executescript(pathlib.Path(p).read_text())
c.execute("INSERT INTO sec_key_references VALUES ('key','owner','server-envelope','external',1,'AES-256-GCM','active',0,200,NULL,NULL)")
c.execute("INSERT INTO sec_consents VALUES ('c','owner','owner','household_profile','profile','private_use',NULL,NULL,'notice','granted',1,0,200,1)")
def envelope(i,t,o,p,n,provider=''):
 c.execute('INSERT INTO sec_envelopes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(i,'owner',None,t,o,p,provider,1,'server-envelope','key',1,'AES-256-GCM',bytes([n])*12,bytes(17),0,200,1))
envelope('profile-envelope','household_profiles','profile','household-profile/1',1)
c.execute("INSERT INTO household_profiles VALUES ('owner','profile','profile-envelope',1,'active','date','date')")
envelope('plan-envelope','household_medical_plans','plan','household-medical-plan/1',2)
c.execute("INSERT INTO household_medical_plans VALUES ('owner','plan','profile','plan-envelope','c',1,'active','date',200)")
def denied(sql,args=()):
 try:c.execute(sql,args)
 except sqlite3.IntegrityError:return
 raise AssertionError('Expected denial')
denied("UPDATE household_medical_plans SET owner_user_id='other'")
denied("UPDATE household_medical_plans SET envelope_id='profile-envelope'")
envelope('provider-bound','household_medical_plans','plan2','household-medical-plan/1',3,'provider')
denied("INSERT INTO household_medical_plans VALUES ('owner','plan2','profile','provider-bound','c',1,'active','date',200)")
assert c.execute('SELECT count(*) FROM household_medical_plans').fetchone()[0]==1
assert c.execute('PRAGMA foreign_key_check').fetchall()==[]
print('medical owner/envelope/version/provider constraints PASS')
`;
  const r=spawnSync('python3',['-B','-c',script],{cwd:new URL('../../',import.meta.url),encoding:'utf8'});assert.equal(r.status,0,r.stderr);assert.match(r.stdout,/PASS/);
});
