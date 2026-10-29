// ISOLATED GENERATED OWNER ONLY. Never configure for normal/real-user runtime.
// No verifier, credential, grant, real key or real durable attestation is created.
const identity=Object.freeze({ownerUserId:'synthetic-owner',
  issuer:'https://synthetic.invalid/issuer',subject:'opaque-subject'});
const namespace='synthetic-instance',packageId='synthetic-package';
const keyReference=Object.freeze({keyRef:'synthetic-existing-key-ref',keyVersion:1});
const stable=x=>Array.isArray(x)?'['+x.map(stable).join(',')+']':x&&typeof x==='object'?
  '{'+Object.keys(x).sort().map(k=>JSON.stringify(k)+':'+stable(x[k])).join(',')+'}':JSON.stringify(x);
const same=(a,b)=>stable(a)===stable(b),copy=x=>structuredClone(x);
const requireThat=(v,c)=>{if(!v)throw Error(c);};
const digest=async bytes=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
  .map(x=>x.toString(16).padStart(2,'0')).join('');

export async function createIsolatedSyntheticOwnedBackupAdapters({createFixture,
  independentReference,clock}={}){
  requireThat(typeof createFixture==='function'&&typeof clock==='function','EXISTING_DECLARED_FIXTURE_REQUIRED');
  const bytes=new Uint8Array(independentReference?.bytes||[]);
  requireThat(independentReference?.receipt?.sha256==='5de5991e56408c8c6b7c81ff9c9ca70a70ef9814273e6fa03cb0719faeeef961'&&
    await digest(bytes)===independentReference.receipt.sha256,'EXISTING_INDEPENDENT_GENERATED_REFERENCE_REQUIRED');
  const reference=JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes));
  requireThat(reference.inventory?.complete===true&&/^[a-f0-9]{64}$/.test(reference.payloadDigest),
    'GENERATED_REFERENCE_ATTESTATION_REQUIRED');
  const requests=new WeakMap();
  function bindVerifiedPrincipal(principal){
    requireThat(principal?.id===identity.ownerUserId,'DECLARED_SYNTHETIC_OWNER_ONLY');
    // Explicit existing declaration, not an issuer/subject inferred from email/ID.
    return {identity:copy(identity),namespace};
  }
  function stateFor(context){
    bindVerifiedPrincipal(context?.principal);
    requireThat(context.request&&typeof context.request.url==='string','ORIGINAL_SERVER_REQUEST_REQUIRED');
    const url=new URL(context.request.url);
    requireThat(['http://127.0.0.1:7645','http://127.0.0.1:17645'].includes(url.origin)&&
      context.request.method==='POST','ISOLATED_LOCAL_EXPORT_REQUEST_ONLY');
    let state=requests.get(context.request);
    if(!state){
      const f=createFixture();
      requireThat(same(f.state?.authority?.identity,identity)&&f.state.authority.namespace===namespace&&
        f.state.authority.principal?.id===identity.ownerUserId&&f.snapshot?.ownerUserId===identity.ownerUserId&&
        f.snapshot.namespace===namespace,'EXACT_EXISTING_GENERATED_FIXTURE_REQUIRED');
      requireThat(same(f.snapshot.sources,reference.inventory.sources)&&
        f.snapshot.revision===reference.inventory.snapshotRevision,'GENERATED_SNAPSHOT_REFERENCE_MISMATCH');
      requireThat(!Object.hasOwn(f.state.authority,'backupInventory'),'INDEPENDENT_ATTESTATION_MUST_NOT_BE_REPLACED');
      f.state.authority.recoveryRefs=['synthetic-recovery'];
      f.state.authority.backupInventory={complete:true,payloadDigest:reference.payloadDigest};
      state={fixture:f,key:null};requests.set(context.request,state);
    }
    const a=state.fixture.state.authority;
    requireThat(same(a.identity,identity)&&a.namespace===namespace&&a.principal?.id===identity.ownerUserId,
      'DECLARED_IDENTITY_CHANGED');
    return state;
  }
  return Object.freeze({clock,bindVerifiedPrincipal,
    async readAuthority(query,context){
      requireThat(query.operation==='owned-backup'&&query.packageId===packageId,'SELECTED_GENERATED_PACKAGE_ONLY');
      return copy(stateFor(context).fixture.state.authority);
    },
    async openSnapshot(query,context){
      requireThat(query.ownerUserId===identity.ownerUserId&&query.namespace===namespace&&
        query.packageId===packageId,'SELECTED_GENERATED_SNAPSHOT_ONLY');
      return stateFor(context).fixture.snapshot;
    },
    async authorizeSourceRecord(query,context){
      const f=stateFor(context).fixture;
      return query.action==='export'&&same(query.authority.identity,identity)&&
        query.authority.namespace===namespace&&Array.isArray(f.state.rows[query.sourceId])&&
        f.state.rows[query.sourceId].some(row=>same(row,query.record));
    },
    async resolveKey(query,context){
      const state=stateFor(context);
      const current=()=>{const a=stateFor(context).fixture.state.authority;
        requireThat(a.auth.revokedAt===null&&a.auth.expiresAt>clock()&&
          a.consent.choice==='granted'&&a.consent.revokedAt===null,'GENERATED_CUSTODY_REVOKED');};
      requireThat(query.version===1&&query.algorithm==='AES-256-GCM'&&
        query.operation==='encrypt'&&query.keyRef===keyReference.keyRef&&
        query.keyVersion===keyReference.keyVersion&&query.custody==='server-envelope'&&
        query.subject?.ownerUserId===identity.ownerUserId&&query.subject.objectType==='private-portable-package'&&
        query.subject.objectId===packageId&&query.subject.kitchenId===null&&query.subject.providerId===null&&
        /^owned_data_portability\/manifest1:[a-f0-9]{64}$/.test(query.subject.purpose),'SELECTED_GENERATED_KEY_USE_ONLY');
      current();
      if(!state.key)state.key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
      current();return state.key;
    }
  });
}
