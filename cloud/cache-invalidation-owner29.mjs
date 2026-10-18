// Owner02 adoption required. D1 resolver_cache stores bounded envelopes only.
// Caller authenticates scope; permission and budget callbacks remain authoritative.
export function cacheInvalidationAdapter({DB, clock, evaluateDependencies, permit, reserve}) {
  if (![clock,evaluateDependencies,permit,reserve].every(f=>typeof f==='function')) throw Error('Required gates');
  const text=x=>typeof x==='string'&&x.length>0&&x.length<=256;
  let lastTime=-Infinity;
  const time=()=>{const n=clock();if(!Number.isFinite(n)||n<lastTime)throw Error('Invalid or decreasing clock');lastTime=n;return n;};
  const freeze=value=>{if(value&&typeof value==='object'){for(const v of Object.values(value))freeze(v);Object.freeze(value);}return value;};
  const snapshot=value=>freeze(JSON.parse(JSON.stringify(value)));
  const admittedUntil=(epochs,envelope)=>Math.min(envelope.freshUntil,...epochs.map(e=>e.until));
  async function key(scope) {
    if (!scope || !['private','public'].includes(scope.audience)||!text(scope.owner)||!text(scope.query)||!text(scope.producerEpoch)||!text(scope.sourceId)||scope.audience==='public'&&scope.owner!=='public') throw Error('Explicit scope required');
    const bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify([scope.owner,scope.audience,scope.sourceId,scope.query,scope.producerEpoch])));
    return 'owner29:'+Array.from(new Uint8Array(bytes),n=>n.toString(16).padStart(2,'0')).join('');
  }
  async function validate(envelope,scope,action) {
    if(!envelope||envelope.format!=='owner29/1'||JSON.stringify(envelope.scope)!==JSON.stringify(scope)||!Array.isArray(envelope.assertions)||!envelope.assertions.length||envelope.assertions.length>256||!Number.isFinite(envelope.freshUntil)||envelope.freshUntil<=time())return null;
    const epochs=[];const policies=new Map();
    for(const source of new Set(envelope.assertions.map(a=>a.sourceId))) {
      const row=await DB.prepare('SELECT document,revision,active FROM source_policies WHERE id=?').bind(source).first();
      if(!row||row.active!==1||!Number.isSafeInteger(row.revision))return null;
      const expected=envelope.epochs?.find(e=>e.sourceId===source);
      if(!expected||expected.document!==row.document||expected.revision!==row.revision)return null;
      const policy=JSON.parse(row.document);
      const expires=policy.expiresAt==null?null:Date.parse(policy.expiresAt);
      if(expires!==null&&!Number.isFinite(expires))return null;
      policies.set(source,freeze(policy));
      epochs.push({kind:'policy',sourceId:source,document:row.document,revision:row.revision,expires,until:expires??Infinity});
    }
    if(!epochs.some(e=>e.sourceId===scope.sourceId))return null;
    if(envelope.assertions.some(a=>a.owner!==scope.owner&&a.owner!=='public'))return null;
    for(const node of envelope.assertions) {
      const row=await DB.prepare('SELECT document,status,retain_until,fresh_until FROM evidence_assertions WHERE owner=? AND id=? AND source_id=?').bind(node.owner,node.id,node.sourceId).first();
      if(!row||row.document!==JSON.stringify(node)||['withdrawn','quarantined'].includes(row.status)||row.retain_until<=time()||row.fresh_until<=time())return null;
      const retained=node.retainUntil==null?Infinity:Date.parse(node.retainUntil);
      if(!Number.isFinite(row.retain_until)||!Number.isFinite(row.fresh_until)||Number.isNaN(retained))return null;
      epochs.push({kind:'assertion',node,document:row.document,until:Math.min(row.retain_until,row.fresh_until,retained)});
    }
    const decisions=evaluateDependencies(envelope.assertions,{clock:time,permit:(node,{now})=>permit(node,{now,scope,action,policy:policies.get(node.sourceId)})});
    if(decisions.length!==envelope.assertions.length||decisions.some(d=>d.allowed!==true))return null;
    return epochs;
  }
  function condition(epochs) {
    const sql=[],bindings=[];
    for(const e of epochs) {
      if(e.kind==='assertion') {
        sql.push("EXISTS(SELECT 1 FROM evidence_assertions WHERE owner=? AND id=? AND source_id=? AND document=? AND status NOT IN ('withdrawn','quarantined') AND retain_until>? AND fresh_until>?)");
        bindings.push(now=>[e.node.owner,e.node.id,e.node.sourceId,e.document,now,now]);
        if(e.node.retainUntil!=null) {
          const expiry=Date.parse(e.node.retainUntil);
          sql.push('? > ?');bindings.push(now=>[Number.isFinite(expiry)?expiry:0,now]);
        }
      } else {
        sql.push('EXISTS(SELECT 1 FROM source_policies WHERE id=? AND document=? AND revision=? AND active=1)');
        bindings.push(()=>[e.sourceId,e.document,e.revision]);
        if(e.expires!==null){sql.push('? > ?');bindings.push(now=>[e.expires,now]);}
      }
    }
    return {sql:sql.join(' AND '),args:now=>bindings.flatMap(bind=>bind(now))};
  }
  async function read(scope) {
    scope=snapshot(scope);
    const k=await key(scope),row=await DB.prepare('SELECT document,fresh_until FROM resolver_cache WHERE key=?').bind(k).first();
    if(!row?.document||!Number.isFinite(row.fresh_until)||row.fresh_until<=time()||new TextEncoder().encode(row.document).length>65536)return null;
    let envelope;try{envelope=snapshot(JSON.parse(row.document));}catch{return null;}
    const epochs=await validate(envelope,scope,'display');if(!epochs)return null;
    const c=condition(epochs);
    // Recheck epochs and same envelope in one SQL statement after async gates.
    const statement=DB.prepare(`SELECT document,fresh_until FROM resolver_cache WHERE key=? AND document=? AND fresh_until>? AND ${c.sql}`);
    const now=time(); // One trusted clock capture after preparation, shared by every expiry gate.
    const current=await statement.bind(k,row.document,now,...c.args(now)).first();
    if(!current||!Number.isFinite(current.fresh_until)||time()>=Math.min(current.fresh_until,admittedUntil(epochs,envelope)))return null;
    const {cacheWriteGeneration,...visible}=envelope;
    return snapshot(visible);
  }
  async function publish(scope,envelope) {
    scope=snapshot(scope);
    // Snapshot caller data before any await; never mutate producer data.
    const document=JSON.stringify(envelope);
    if(new TextEncoder().encode(document).length>65536)throw Error('Envelope exceeds 64 KiB');
    const copy=snapshot(JSON.parse(document)),k=await key(scope),epochs=await validate(copy,scope,'persist');if(!epochs)return false;
    const physicalDocument=JSON.stringify({...copy,cacheWriteGeneration:crypto.randomUUID()});
    if(new TextEncoder().encode(physicalDocument).length>65536)throw Error('Physical envelope exceeds 64 KiB');
    const c=condition(epochs);
    const statement=DB.prepare(`INSERT INTO resolver_cache(key,source_id,document,fresh_until,retry_after,failures,updated_at) SELECT ?,?,?,?,0,0,? WHERE ? > ? AND ${c.sql} ON CONFLICT(key) DO UPDATE SET document=excluded.document,fresh_until=excluded.fresh_until,source_id=excluded.source_id,updated_at=excluded.updated_at RETURNING key,document,fresh_until,updated_at`);
    const now=time();
    const row=await statement.bind(k,scope.sourceId,physicalDocument,copy.freshUntil,new Date(now).toISOString(),copy.freshUntil,now,...c.args(now)).first();
    if(!row)return false;
    if(time()>=admittedUntil(epochs,copy)) {
      // Remove only this exact expired envelope; preserve concurrent replacements.
      await DB.prepare('DELETE FROM resolver_cache WHERE key=? AND document=? AND fresh_until=? AND updated_at=? RETURNING key').bind(k,physicalDocument,row.fresh_until,row.updated_at).first();
      return false;
    }
    return true;
  }
  async function resolve(scope,prepared,produce) {
    scope=snapshot(scope);prepared=snapshot(prepared);
    const hit=await read(scope);if(hit)return {status:'hit',envelope:hit};
    // Before reserving or transport require a producer-supplied complete graph
    // with exact epochs. Prepared payload is not used as a cache response.
    if(!await validate(prepared,scope,'persist'))return {status:'withheld'};
    if((await reserve({scope,now:time()}))?.allowed!==true)return {status:'budget-denied'};
    if(!await validate(prepared,scope,'persist'))return {status:'withheld'};
    const envelope=await produce();
    if(!await publish(scope,envelope))return {status:'withheld'};
    const admitted=await read(scope);
    return admitted?{status:'miss',envelope:admitted}:{status:'withheld'};
  }
  return {read,publish,resolve};
}
