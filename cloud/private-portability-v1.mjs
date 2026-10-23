/** Unmounted, data-free preparation. All callbacks are trusted server dependencies.
 * Never construct this adapter with functions or authority supplied by a request.
 * Existing verified principal IDs and BYOC AES-GCM/AAD are preserved.
 */
import schema from '../schemas/private-portable-package-v1.schema.json' with {type:'json'};
import {createEnvelopeCryptor} from './byoc-envelope-v1.mjs';

const fail = (code = 'DENIED') => { throw new Error(`Private portability unavailable (${code}).`); };
const atom = v => typeof v === 'string' && v.length > 0 && v.length <= 200 && !/[\u0000-\u001f]/u.test(v);
const safe = v => Number.isSafeInteger(v) && v >= 0;
const equal = (a,b) => canonical(a) === canonical(b);
const key = r => JSON.stringify([r.type,r.id]);
const history = new Set(['identity_link','connection_metadata','auth_history','consent_history','movement','waste']);
const group = type => ['space','location','item','lot','holding','movement','reservation','waste'].includes(type) ? 'inventory'
  : ['profile','medical_plan'].includes(type) ? 'profile.full'
  : ['identity_link','connection_metadata'].includes(type) ? 'auth_metadata'
  : ['auth_history','consent_history'].includes(type) ? 'history' : type;
const identityEqual = (a,b) => a && b && ['ownerUserId','issuer','subject'].every(k=>a[k]===b[k]);
const plain = v => v !== null && typeof v === 'object' && !Array.isArray(v) && [Object.prototype,null].includes(Object.getPrototypeOf(v));
const packageBinding = 'offmenu-private-package-manifest/1';
const restoreBinding = 'offmenu-private-restore-manifest/1';

// RFC 3986 Appendix A generic URI syntax, not WHATWG URL repair/normalization.
// Keep original text; scheme-specific validity, DNS and identity trust are separate.
const uriAtom = "(?:[A-Za-z0-9._~!$&'()*+,;=-]|%[0-9A-Fa-f]{2})";
const uriComponent = extra => new RegExp('^(?:'+uriAtom+'|['+extra+'])*$');
const uriPath = uriComponent(':@/'),uriQuery = uriComponent(':@/?');
const uriUser = uriComponent(':'),uriHost = new RegExp('^'+uriAtom+'*$');
function ipv6(address) {
  const halves=address.split('::');if(halves.length>2) return false;
  const groups=halves.flatMap(h=>h?h.split(':'):[]);let count=0;
  for(let i=0;i<groups.length;i++) {
    const g=groups[i];
    if(g.includes('.')) {
      if(i!==groups.length-1||!address.endsWith(g)) return false;
      const octets=g.split('.');
      if(octets.length!==4||octets.some(x=>!/^(?:0|[1-9][0-9]{0,2})$/.test(x)||Number(x)>255)) return false;
      count+=2;
    } else {if(!/^[0-9A-Fa-f]{1,4}$/.test(g)) return false;count++;}
  }
  return halves.length===2?count<8:count===8;
}
function validURI(value) {
  if(/[^A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]/.test(value)||/%(?![0-9A-Fa-f]{2})/.test(value)) return false;
  const match=/^[A-Za-z][A-Za-z0-9+.-]*:([^?#]*)(?:\?([^#]*))?(?:#(.*))?$/.exec(value);
  if(!match||!uriQuery.test(match[2]??'')||!uriQuery.test(match[3]??'')) return false;
  let path=match[1];
  if(path.startsWith('//')) {
    const end=path.indexOf('/',2);let authority=path.slice(2,end<0?undefined:end);path=end<0?'':path.slice(end);
    const at=authority.lastIndexOf('@');
    if(at>=0) {if(!uriUser.test(authority.slice(0,at))) return false;authority=authority.slice(at+1);}
    if(authority.startsWith('[')) {
      const close=authority.indexOf(']');if(close<0||!/^(?::[0-9]*)?$/.test(authority.slice(close+1))) return false;
      const literal=authority.slice(1,close);
      if(!/^[vV][0-9A-Fa-f]+\.[A-Za-z0-9._~!$&'()*+,;=:-]+$/.test(literal)&&!ipv6(literal)) return false;
    } else {
      const colon=authority.lastIndexOf(':');
      if(colon>=0) {if(!/^[0-9]*$/.test(authority.slice(colon+1))) return false;authority=authority.slice(0,colon);}
      if(!uriHost.test(authority)) return false;
    }
  }
  return uriPath.test(path);
}

// Canonical JSON for this version: sorted object keys, retained array ordering,
// finite JSON numbers only. Not a claim of RFC 8785 interoperability.
export function canonical(value) {
  let nodes = 0;
  function visit(v,depth) {
    if (++nodes > 100000 || depth > 40) fail('JSON_LIMIT');
    if (v===null || typeof v==='boolean' || typeof v==='string') return JSON.stringify(v);
    if (typeof v==='number' && Number.isFinite(v)) return JSON.stringify(v);
    if (Array.isArray(v)) return '['+v.map(x=>visit(x,depth+1)).join(',')+']';
    if (!plain(v)) fail('JSON_VALUE');
    return '{'+Object.keys(v).sort().map(k=>JSON.stringify(k)+':'+visit(v[k],depth+1)).join(',')+'}';
  }
  return visit(value,0);
}
const clone = v => JSON.parse(canonical(v));
export async function digest(value) {
  const bytes = typeof value==='string' ? new TextEncoder().encode(value) : new TextEncoder().encode(canonical(value));
  return hex(await crypto.subtle.digest('SHA-256',bytes));
}
const hex = bytes => [...new Uint8Array(bytes)].map(b=>b.toString(16).padStart(2,'0')).join('');
async function bytesDigest(bytes) { return hex(await crypto.subtle.digest('SHA-256',bytes)); }
function freeze(v) { if (v && typeof v==='object') { for(const x of Object.values(v)) freeze(x);Object.freeze(v); } return v; }

// The local schema deliberately uses only these JSON Schema keywords. This is
// a validator for THIS pinned schema, not a general JSON Schema implementation.
function conforms(v,s) {
  if (s.$ref) return conforms(v,schema.$defs[s.$ref.split('/').at(-1)]);
  if ('const' in s && !equal(v,s.const)) return false;
  if (s.enum && !s.enum.some(x=>equal(v,x))) return false;
  if (s.anyOf && !s.anyOf.some(x=>conforms(v,x))) return false;
  if (s.allOf && !s.allOf.every(x=>conforms(v,x))) return false;
  if (s.if && !conforms(v,conforms(v,s.if) ? (s.then ?? {}) : (s.else ?? {}))) return false;
  if (s.type) {
    const types=Array.isArray(s.type)?s.type:[s.type];
    if (!types.some(t=>t==='null'?v===null:t==='object'?plain(v):t==='array'?Array.isArray(v):t==='integer'?Number.isSafeInteger(v):t==='number'?typeof v==='number'&&Number.isFinite(v):typeof v===t)) return false;
  }
  if (plain(v)) {
    if (s.maxProperties!==undefined && Object.keys(v).length>s.maxProperties) return false;
    if (s.required?.some(k=>!Object.hasOwn(v,k))) return false;
    for (const [k,x] of Object.entries(v)) {
      if (Object.hasOwn(s.properties??{},k)) { if(!conforms(x,s.properties[k])) return false; }
      else if (s.additionalProperties===false) return false;
    }
  }
  if (Array.isArray(v)) {
    if (s.minItems!==undefined&&v.length<s.minItems || s.maxItems!==undefined&&v.length>s.maxItems) return false;
    if (s.items && !v.every(x=>conforms(x,s.items))) return false;
    if (s.uniqueItems && new Set(v.map(canonical)).size!==v.length) return false;
  }
  if (typeof v==='string') {
    if (s.minLength!==undefined&&[...v].length<s.minLength || s.maxLength!==undefined&&[...v].length>s.maxLength) return false;
    if (s.pattern && !new RegExp(s.pattern,'u').test(v)) return false;
    if (s.format==='date' && (!/^\d{4}-\d{2}-\d{2}$/.test(v) || !Number.isFinite(Date.parse(v)) || new Date(v).toISOString().slice(0,10)!==v)) return false;
    if (s.format==='date-time' && (!/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d+)?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)$/.test(v) || !Number.isFinite(Date.parse(v)) || !conforms(v.slice(0,10),{format:'date'}))) return false;
    if (s.format==='uri'&&!validURI(v)) return false;
  }
  if (typeof v==='number' && (s.minimum!==undefined&&v<s.minimum || s.maximum!==undefined&&v>s.maximum)) return false;
  return true;
}
function noSecrets(v) {
  if (!v || typeof v!=='object') return;
  for (const [k,x] of Object.entries(v)) {
    // Strict structural exclusion, not a claim to detect secrets hidden in prose.
    if (/^(?:password|passwordHash|api[_-]?key|token|oauth[_-]?token|secret|secret[_-]?key|access[_-]?token|refresh[_-]?token|id[_-]?token|session(?:Token|Cookie)?|cookie|authorization|bearer|client[_-]?secret|private[_-]?key|raw[_-]?key|wrapped[_-]?key|credentials?)$/iu.test(k)) fail('SECRET_FIELD');
    noSecrets(x);
  }
}
function unique(values) { if (new Set(values).size!==values.length) fail('DUPLICATE'); }
function bounded(v) { const text=canonical(v);if(new TextEncoder().encode(text).length>2_000_000) fail('SIZE');return JSON.parse(text); }

/** Validate decrypted owned data, including references and real byte checksums. */
export async function validatePrivatePayload(input) {
  const p=bounded(input);
  if (!conforms(p,schema.$defs.payload)) fail('PAYLOAD_SCHEMA');
  noSecrets(p);unique(p.records.map(key));unique(p.attachments.map(a=>a.id));
  const records=new Map(p.records.map(r=>[key(r),r]));
  const find=(type,id,owner,kitchen)=>{
    const r=records.get(key({type,id}));
    if(!r || r.ownerRef!==owner || r.householdRef!==kitchen) fail('REFERENCE_SCOPE');return r;
  };
  for(const r of p.records) {
    const d=r.data, lookup=(type,id)=>find(type,id,r.ownerRef,r.householdRef);
    if (r.lifecycle==='deleted'||r.lifecycle==='deletion_pending') fail('DELETED_RECORD');
    if (group(r.type)==='inventory' && r.householdRef===null) fail('KITCHEN_REQUIRED');
    if (r.type==='space' && r.id!==r.householdRef) fail('SPACE_ID');
    if (r.type==='location') {
      lookup('space',d.spaceId);
      if (d.spaceId!==r.householdRef) fail('LOCATION_SPACE');
      let id=d.parentId;const seen=new Set([r.id]);
      while(id!==null) {if(seen.has(id)) fail('HIERARCHY_CYCLE');seen.add(id);id=lookup('location',id).data.parentId;}
    }
    if (r.type==='lot') lookup('item',d.itemId);
    if (r.type==='holding') {
      lookup('location',d.locationId);lookup('item',d.itemId);
      if(lookup('lot',d.lotId).data.itemId!==d.itemId) fail('LOT_ITEM');
    }
    if (r.type==='movement') {
      const h=lookup('holding',d.holdingId);
      if(h.data.lotId!==d.lotId || h.data.quantity.unit!==d.unit) fail('MOVEMENT_BASIS');
      lookup('lot',d.lotId);
      if (['acquire','transfer_in'].includes(d.kind) && d.delta.startsWith('-') || ['consume','waste','transfer_out'].includes(d.kind)&&!d.delta.startsWith('-')) fail('MOVEMENT_SIGN');
      const [whole,fraction='']=d.delta.replace(/^-/,'').split('.');
      if(BigInt(whole)*1000000n+BigInt(fraction.padEnd(6,'0'))>9000000000000000n) fail('DELTA_RANGE');
    }
    if (r.type==='reservation') {
      const h=lookup('holding',d.holdingId);
      if(h.data.quantity.unit!==d.quantity.unit || h.data.quantity.dimension!==d.quantity.dimension) fail('QUANTITY_BASIS');
    }
    if (r.type==='waste') { const m=lookup('movement',d.movementId);if(m.data.kind!=='waste'||m.data.unit!==d.quantity.unit) fail('WASTE_BASIS'); }
    if (r.type==='medical_plan') {
      lookup('profile',d.profileId);
      if(d.effectiveUntil!==null && Date.parse(d.effectiveUntil)<=Date.parse(d.effectiveFrom)) fail('PLAN_TIME');
      if(d.planType==='recommendation'&&!d.recommendationProvenance.length) fail('RECOMMENDATION_PROVENANCE');
    }
    if (r.type==='consent_history' && Date.parse(d.expiresAt)<=Date.parse(d.validFrom)) fail('CONSENT_TIME');
    if (d.quantity) {
      const dimension={g:'mass',ml:'volume',count:'count',portion:'portion',package:'package'}[d.quantity.unit];
      if(dimension&&dimension!==d.quantity.dimension) fail('UNIT_DIMENSION');
      if ((d.quantity.value===null)!==(d.quantity.status==='unknown')) fail('UNKNOWN_QUANTITY');
      if(d.quantity.value!==null) {const [whole,fraction='']=d.quantity.value.split('.');if(BigInt(whole)*1000000n+BigInt(fraction.padEnd(6,'0'))>9000000000000000n) fail('QUANTITY_RANGE');}
    }
  }
  for(const edge of p.relationships) {
    const a=records.get(key(edge.from)),b=records.get(key(edge.to));
    if(!a||!b||a.ownerRef!==b.ownerRef||a.householdRef!==b.householdRef) fail('RELATIONSHIP_SCOPE');
  }
  for(const a of p.attachments) {
    if(!records.has(key(a.forRecord))) fail('ATTACHMENT_REFERENCE');
    const bytes=Uint8Array.from(atob(a.base64),c=>c.charCodeAt(0));
    if(bytes.length!==a.bytes) fail('ATTACHMENT_BYTES');
    // Canonical base64 without spreading arbitrary attachment bytes on the stack.
    let encoded='';for(let i=0;i<bytes.length;i+=8192) encoded+=String.fromCharCode(...bytes.subarray(i,i+8192));
    if(btoa(encoded)!==a.base64 || await bytesDigest(bytes)!==a.sha256) fail('ATTACHMENT_DIGEST');
  }
  return freeze(p);
}

function context(a,now) {
  if(!a || !atom(a.namespace) || !conforms(a.identity,schema.$defs.identity) || a.principal?.id!==a.identity.ownerUserId || !safe(a.revision)) fail('IDENTITY');
  if(!safe(a.auth?.reauthenticatedAt) || !safe(a.auth?.expiresAt) || a.auth.revokedAt!==null || a.auth.reauthenticatedAt>now || now-a.auth.reauthenticatedAt>300000 || a.auth.expiresAt<=now) fail('REAUTHENTICATION');
  if(!Array.isArray(a.kitchens)||!a.kitchens.every(atom)||!Array.isArray(a.allowedRecords)||!a.allowedRecords.every(atom)||!Array.isArray(a.tombstones)||!a.tombstones.every(atom)||!Array.isArray(a.recoveryRefs)||!a.recoveryRefs.every(atom)) fail('AUTHORITY_SCOPE');
  const c=a.consent;
  if(!c || !atom(c.id) || !Number.isSafeInteger(c.revision)||c.revision<1 || c.ownerUserId!==a.identity.ownerUserId || !conforms(c.recipient,schema.$defs.identity) || !Array.isArray(c.fields)||!c.fields.every(atom) || !safe(c.validFrom)||!safe(c.expiresAt)||c.validFrom>now||c.expiresAt<=now||c.revokedAt!==null||c.choice!=='granted') fail('CONSENT');
  return a;
}
function subject(p,identity=p.identity,kitchenId=null) {
  return {ownerUserId:identity.ownerUserId,kitchenId,objectType:'private-portable-package',objectId:p.packageId,purpose:'owned_data_portability/manifest1:'+p.manifestDigest,providerId:null};
}
async function manifestHash(value,domain) {
  const {envelope,checksum,manifestDigest,...immutable}=value;
  return digest([domain,immutable]);
}
function packageScope(p,a,operation,recipient) {
  if(a.namespace!==p.source.namespace || !identityEqual(a.identity,p.identity) || a.consent.id!==p.consent.id || a.consent.revision!==p.consent.revision || a.consent.purpose!==operation || !identityEqual(a.consent.recipient,recipient)) fail('SOURCE_BINDING');
  if(!a.recoveryRefs.includes(p.protection.recoveryRef) || p.scope.fields.some(f=>!a.consent.fields.includes(f))) fail('FIELD_SCOPE');
  for(const r of p.scope.records) if(!a.allowedRecords.includes(key(r))||a.tombstones.includes(key(r))) fail('RECORD_SCOPE');
}
async function payloadScope(payload,p,a) {
  if(!equal(payload.records.map(r=>({type:r.type,id:r.id})),p.scope.records)) fail('MANIFEST_SCOPE');
  if(payload.attachments.length&&!p.scope.fields.includes('attachments') || payload.relationships.length&&!p.scope.fields.includes('relationships') || (payload.extensions.length||payload.records.some(r=>r.extensions.length))&&!p.scope.fields.includes('extensions')) fail('AUXILIARY_SCOPE');
  for(const r of payload.records) {
    if(r.ownerRef!==a.identity.ownerUserId || (r.householdRef!==null&&!a.kitchens.includes(r.householdRef))) fail('TENANT_SCOPE');
    const fields=p.scope.fields;
    if(r.type==='profile') {
      for(const name of ['displayName','dietary','allergies','preferences','diagnoses']) if(r.data[name]!==null && !fields.includes('profile.full') && !fields.includes('profile.'+name)) fail('PROFILE_FIELD_SCOPE');
    } else if(r.type==='medical_plan') {if(!fields.includes('profile.full')&&!fields.includes('profile.medical_plans')) fail('MEDICAL_FIELD_SCOPE');}
    else if(!fields.includes(group(r.type))) fail('FIELD_SCOPE');
    if(p.kind==='portability'&&!['inventory','profile.full','derived_provenance'].includes(group(r.type))) fail('PORTABILITY_SCOPE');
  }
  if(p.kind==='owned-backup' && (Object.values(payload.coverage).includes('unavailable') || a.backupInventory?.complete!==true || a.backupInventory.payloadDigest!==await digest(payload))) fail('INCOMPLETE_BACKUP');
}
async function validatePackage(input) {
  const p=bounded(input);if(!conforms(p,schema)) fail('PACKAGE_SCHEMA');
  const {checksum,...rest}=p;if(await digest(rest)!==checksum) fail('PACKAGE_DIGEST');
  if(await manifestHash(p,packageBinding)!==p.manifestDigest) fail('MANIFEST_DIGEST');
  unique(p.scope.records.map(key));return p;
}
const authorityStamp = a => canonical(a);
function stable(a,b) { if(authorityStamp(a)!==authorityStamp(b)) fail('AUTHORITY_CHANGED'); }

/** Deterministic identity only; never an authorization decision or name match. */
export async function destinationRecordId({sourceNamespace,sourceIdentity,record,destinationNamespace,destinationIdentity,kitchenMap}) {
  return record.type==='space'?kitchenMap[record.id]:'p-'+await digest([sourceNamespace,sourceIdentity,record.type,record.id,destinationNamespace,destinationIdentity]);
}

/** Pure package/plan hooks. No routes, DB handles, keys, sessions or jobs created.
 * readAuthority MUST return fresh independent server/auth/storage evidence; this
 * module does not turn an object carrying authenticated:true into authentication.
 * atomicRestore, if adopted, owns the real transaction/CAS/tombstone fence.
 */
export function createPrivatePortability({readAuthority,resolveKey,custody='server-envelope',clock=()=>Date.now(),atomicRestore}={}) {
  if(typeof readAuthority!=='function'||typeof resolveKey!=='function'||typeof clock!=='function') fail('ADAPTER_REQUIRED');
  const crypt=createEnvelopeCryptor({resolveKey,custody});
  // Ephemeral issuance capabilities only, no durable session/job/record store.
  // A restarted adapter must revalidate and replan a retained encrypted package.
  const issued=new Map();
  async function read(operation,phase,packageId) {
    const a=clone(await readAuthority(Object.freeze({operation,phase,packageId})));
    const now=clock();if(!safe(now)) fail('CLOCK');
    if(operation==='restore') {context(a.source,now);context(a.destination,now);} else context(a,now);
    return a;
  }
  return Object.freeze({
    async exportPackage(request={}) {
      try {
        const {packageId,kind,sourceSchemaVersion,payload,recoveryRef,keyReference}=bounded(request);
        if(!atom(packageId)||!['privacy-access','portability','owned-backup'].includes(kind)||sourceSchemaVersion!=='offmenu-household-domain/1'||!atom(recoveryRef)) fail('UNSUPPORTED_VERSION');
        const a=await read(kind,'start',packageId),data=await validatePrivatePayload(payload);
        const p={schemaVersion:'offmenu-private-portable-package/1',packageId,kind,source:{namespace:a.namespace,schemaVersion:sourceSchemaVersion},identity:clone(a.identity),recipient:clone(a.consent.recipient),createdAt:new Date(clock()).toISOString(),scope:{fields:clone(a.consent.fields),records:data.records.map(r=>({type:r.type,id:r.id}))},consent:{id:a.consent.id,revision:a.consent.revision},protection:{recoveryRef,sourceInstanceOnly:false,destinationReencryptionRequired:true,reauthenticationRequired:true,downloadedCopiesRevocable:false,manifestBinding:packageBinding}};
        packageScope(p,a,kind,p.recipient);await payloadScope(data,p,a);
        if(kind==='privacy-access'&&!identityEqual(a.identity,p.recipient)) fail('REPORT_RECIPIENT');
        p.manifestDigest=await manifestHash(p,packageBinding);
        p.envelope=await crypt.seal(data,subject(p),clone(keyReference));p.checksum=await digest(p);
        await validatePackage(p);stable(a,await read(kind,'finish',packageId));return freeze(p);
      } catch {return fail('EXPORT_DENIED');}
    },
    async accessReport(input) {
      try {
        const p=await validatePackage(input);if(p.kind!=='privacy-access') fail('REPORT_KIND');
        const a=await read(p.kind,'start',p.packageId);packageScope(p,a,p.kind,p.recipient);
        if(!identityEqual(a.identity,p.recipient)) fail('REPORT_RECIPIENT');
        const data=await validatePrivatePayload(await crypt.open(p.envelope,subject(p)));await payloadScope(data,p,a);
        stable(a,await read(p.kind,'finish',p.packageId));return data;
      } catch {return fail('REPORT_DENIED');}
    },
    async planRestore(request={}) {
      try {
        const {package:input,destination,kitchenMap={},keyReference}=bounded(request);
        noSecrets(destination);
        if(!conforms(destination,schema.$defs.destination)) fail('DESTINATION_SCHEMA');
        const p=await validatePackage(input);if(p.kind==='privacy-access') fail('REPORT_NOT_IMPORTABLE');
        const a=await read('restore','start',p.packageId),src=a.source,dst=a.destination;
        packageScope(p,src,p.kind,dst.identity);
        if(!identityEqual(p.recipient,dst.identity)||!identityEqual(destination?.identity,dst.identity)||destination?.namespace!==dst.namespace || dst.consent.purpose!=='restore'||!identityEqual(dst.consent.recipient,dst.identity)||p.scope.fields.some(f=>!dst.consent.fields.includes(f))) fail('DESTINATION_BINDING');
        if(!Array.isArray(dst.records)||dst.records.some(r=>!atom(r.type)||!atom(r.id)||!/^([a-f0-9]{64})$/.test(r.digest))) fail('DESTINATION_RECORDS');
        const data=clone(await validatePrivatePayload(await crypt.open(p.envelope,subject(p))));await payloadScope(data,p,src);
        const kitchens=[...new Set(data.records.map(r=>r.householdRef).filter(x=>x!==null))].sort();
        if(!plain(kitchenMap)||!equal(Object.keys(kitchenMap).sort(),kitchens)||Object.values(kitchenMap).some(k=>!dst.kitchens.includes(k))) fail('KITCHEN_MAP');
        unique(Object.values(kitchenMap));
        const ids=new Map();
        for(const r of data.records) ids.set(key(r),await destinationRecordId({sourceNamespace:src.namespace,sourceIdentity:src.identity,record:r,destinationNamespace:dst.namespace,destinationIdentity:dst.identity,kitchenMap}));
        unique([...ids.values()]);
        const mapped=(type,id)=>{const value=ids.get(key({type,id}));if(!value) fail('MISSING_REBIND');return value;};
        const refs={location:{spaceId:'space',parentId:'location'},lot:{itemId:'item'},holding:{locationId:'location',itemId:'item',lotId:'lot'},movement:{holdingId:'holding',lotId:'lot'},reservation:{holdingId:'holding'},waste:{movementId:'movement'},medical_plan:{profileId:'profile'}};
        const original=clone(data.records);
        for(const r of data.records) {
          const oldId=r.id;r.id=mapped(r.type,r.id);r.ownerRef=dst.identity.ownerUserId;r.householdRef=r.householdRef===null?null:kitchenMap[r.householdRef];
          for(const [field,type] of Object.entries(refs[r.type]??{})) if(r.data[field]!==null) r.data[field]=mapped(type,r.data[field]);
          if(!dst.allowedRecords.includes(key(r))||dst.tombstones.includes(key(r))) fail('DESTINATION_RECORD_SCOPE');
          // Original provider/auth/grant status is evidence only, never effective state.
          if(r.type==='identity_link') r.data.status='unlinked';
          if(r.type==='connection_metadata') r.data.requiresReauthorization=true;
          // A typed first-import origin has its own fixed bound; it never consumes
          // or grows the caller's 100 permitted source-extension slots.
          r.importOrigin ??= {version:1,sourceNamespace:src.namespace,sourceIdentity:clone(src.identity),sourceId:oldId};
        }
        for(const edge of data.relationships) for(const side of ['from','to']) edge[side].id=mapped(edge[side].type,edge[side].id);
        for(const attachment of data.attachments) {attachment.id='a-'+await digest([src.namespace,attachment.id,dst.namespace]);attachment.forRecord.id=mapped(attachment.forRecord.type,attachment.forRecord.id);}
        await validatePrivatePayload(data);
        const operations=[];
        for(let i=0;i<data.records.length;i++) {
          const r=data.records[i],d=await digest(r),existing=dst.records.filter(x=>key(x)===key(r));
          if(existing.length>1) fail('DESTINATION_DUPLICATE');
          operations.push({type:r.type,id:r.id,sourceId:original[i].id,digest:d,disposition:history.has(r.type)?'history-only':r.type==='medical_plan'?'clinical-review-required':'owned-data',action:existing.length?(existing[0].digest===d?'skip-identical':'conflict'):'insert'});
        }
        const intent={packageChecksum:p.checksum,destination:clone(destination),kitchenMap:clone(kitchenMap)};
        const plan={schemaVersion:'offmenu-private-restore-plan/1',manifestBinding:restoreBinding,packageId:p.packageId,sourceChecksum:p.checksum,sourceManifestDigest:p.manifestDigest,source:clone(p.identity),destination:clone(destination),sourceConsent:clone(p.consent),destinationConsent:{id:dst.consent.id,revision:dst.consent.revision},sourceRevision:src.revision,destinationRevision:dst.revision,idempotencyKey:await digest(intent),operations,conflicts:operations.filter(x=>x.action==='conflict').map(x=>({type:x.type,id:x.id})),warnings:['Original grants, sessions, entitlements and credentials are never restored.','Unknown versioned extension values remain source-bound; no implicit reference interpretation.','Downloaded copies cannot be recalled.'],atomicRequirements:['fresh-source-and-destination-authority','revision-CAS-and-tombstone-fence','all-records-attachments-relationships-or-rollback','unique-idempotency-receipt-in-same-transaction']};
        plan.contentDigest=await digest({intent,records:operations.map(({action,...r})=>r),payload:data});
        plan.manifestDigest=await manifestHash(plan,restoreBinding);
        plan.envelope=await crypt.seal(data,subject(plan,dst.identity),clone(keyReference));plan.checksum=await digest(plan);
        stable(a,await read('restore','finish',p.packageId));
        if(issued.size>=100) issued.delete(issued.keys().next().value);
        issued.set(plan.checksum,clone(a));return freeze(plan);
      } catch {return fail('RESTORE_PLAN_DENIED');}
    },
    async commitRestore(input) {
      try {
        if(typeof atomicRestore!=='function') fail('EXECUTOR_UNMOUNTED');
        const plan=clone(input),{checksum,...body}=plan;
        if(plan.schemaVersion!=='offmenu-private-restore-plan/1'||plan.manifestBinding!==restoreBinding||await manifestHash(plan,restoreBinding)!==plan.manifestDigest||await digest(body)!==checksum||!Array.isArray(plan.conflicts)||plan.conflicts.length) fail('PLAN_CONFLICT');
        // A plan is untrusted input. A private capability below proves it was issued
        // by THIS adapter; arbitrary checksummed plans cannot reach an executor.
        if(!issued.has(checksum)) fail('PLAN_NOT_ISSUED');
        const a=await read('restore','commit',plan.packageId);
        const stamp=issued.get(checksum);
        const authorization=v=>({...v,destination:Object.fromEntries(Object.entries(v.destination).filter(([k])=>!['records','revision'].includes(k)))});
        stable(authorization(stamp),authorization(a));
        // No default executor. Adopter must atomically reread/CAS the same authority,
        // check independent deletion tombstones, stage only encrypted owned data and
        // write the idempotency receipt. Callback completion alone is not D1 proof.
        const result=await atomicRestore(freeze(plan),freeze({sourceRevision:plan.sourceRevision,destinationRevision:plan.destinationRevision,authorityDigest:await digest(a)}));
        if(!result||result.idempotencyKey!==plan.idempotencyKey||result.contentDigest!==plan.contentDigest||!['committed','already-committed'].includes(result.status)) fail('EXECUTOR_RECEIPT');
        return freeze({idempotencyKey:result.idempotencyKey,contentDigest:result.contentDigest,status:result.status});
      } catch {return fail('COMMIT_DENIED');}
    },
  });
}
