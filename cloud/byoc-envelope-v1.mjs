/** OffMenu preparation only. Unmounted; no persistence, provider calls or key creation.
 * resolveKey is a trusted custody adapter, NEVER a request-supplied function.
 * It resolves an external DEK after KEK unwrapping outside the application database.
 */
const encoder = new TextEncoder();
const decoder = new TextDecoder('utf-8', {fatal:true});
const fail = () => { throw new Error('Protected data unavailable.'); };
const atom = value => typeof value === 'string' && value.length > 0 && value.length <= 256 && !/[\u0000-\u001f]/u.test(value);
const integer = value => Number.isSafeInteger(value) && value >= 1;
const fields = ['ownerUserId','kitchenId','objectType','objectId','purpose','providerId'];
function binding(value) {
  if (!value || Object.keys(value).some(k => !fields.includes(k))) fail();
  if (!fields.every(k => k === 'kitchenId' || k === 'providerId' ? value[k] === null || value[k] === '' || atom(value[k]) : atom(value[k]))) fail();
  return fields.map(k => value[k] ?? '');
}
function metadata(value) {
  if (!value || value.version !== 1 || value.algorithm !== 'AES-256-GCM' || !['server-envelope','client'].includes(value.custody) || !atom(value.keyRef) || !integer(value.keyVersion)) fail();
  return [value.version,value.algorithm,value.custody,value.keyRef,value.keyVersion];
}
function aad(value, subject) { return encoder.encode(JSON.stringify(['offmenu-sealed/1', ...metadata(value), ...binding(subject)])); }
function b64(bytes) { let text=''; for(let i=0;i<bytes.length;i+=8192) text+=String.fromCharCode(...bytes.subarray(i,i+8192)); return btoa(text); }
function unb64(value, min, max) {
  if (typeof value !== 'string' || value.length > Math.ceil(max/3)*4 || !/^[A-Za-z0-9+/]*={0,2}$/.test(value)) fail();
  const bytes = Uint8Array.from(atob(value), c => c.charCodeAt(0));
  if (bytes.length < min || bytes.length > max || b64(bytes) !== value) fail();
  return bytes;
}
function validKey(key, operation) {
  if (!(key instanceof CryptoKey) || key.type !== 'secret' || key.extractable || key.algorithm?.name !== 'AES-GCM' || key.algorithm?.length !== 256 || !key.usages.includes(operation)) fail();
  return key;
}
export function createEnvelopeCryptor({resolveKey, custody = 'server-envelope'} = {}) {
  if (typeof resolveKey !== 'function' || !['server-envelope','client'].includes(custody)) fail();
  // resolveKey must freshly enforce key status, expiry and authorized subject/operation.
  // No cache fallback, inline raw key, env default, or generated replacement is provided.
  return Object.freeze({
    async seal(payload, subject, reference) {
      try {
        const capturedSubject = structuredClone(subject);
        const value = {version:1,algorithm:'AES-256-GCM',custody,keyRef:reference?.keyRef,keyVersion:reference?.keyVersion};
        const associated = aad(value,capturedSubject);
        const bytes = encoder.encode(JSON.stringify(payload));
        if (!bytes.length || bytes.length > 1_048_576) fail();
        const key = validKey(await resolveKey({...value,subject:capturedSubject,operation:'encrypt'}),'encrypt');
        const nonce = crypto.getRandomValues(new Uint8Array(12));
        const cipher = new Uint8Array(await crypto.subtle.encrypt({name:'AES-GCM',iv:nonce,additionalData:associated,tagLength:128},key,bytes));
        // Encode in chunks: do not spread a potentially MiB-sized cipher onto the stack.
        let text=''; for(let i=0;i<cipher.length;i+=8192) text+=String.fromCharCode(...cipher.subarray(i,i+8192));
        return {...value,nonce:b64(nonce),ciphertext:btoa(text)};
      } catch { return fail(); }
    },
    async open(envelope, subject) {
      try {
        const value = structuredClone(envelope), capturedSubject = structuredClone(subject);
        if (Object.keys(value).sort().join(',') !== 'algorithm,ciphertext,custody,keyRef,keyVersion,nonce,version' || value.custody !== custody) fail();
        const associated = aad(value,capturedSubject);
        const nonce = unb64(value.nonce,12,12), cipher = unb64(value.ciphertext,17,1_048_592);
        const key = validKey(await resolveKey({...value,subject:capturedSubject,operation:'decrypt'}),'decrypt');
        const plain = await crypto.subtle.decrypt({name:'AES-GCM',iv:nonce,additionalData:associated,tagLength:128},key,cipher);
        return JSON.parse(decoder.decode(plain));
      } catch { return fail(); }
    },
  });
}

/** Pure snapshot predicate, NOT authentication/authorization or a future-use lease.
 * The adopting transaction must freshly authenticate and atomically couple this gate
 * to use; every job start, commit and serve must re-read policy/consent/session.
 * No public/aggregate publication permission is ever returned by this helper.
 */
export function credentialUseAllowed({context,connection,consent,session,policy,scopes,key,now} = {}) {
  try {
    if (!Number.isSafeInteger(now) || now < 0 || !context || context.authenticated !== true || context.requestAuthorized !== true || !atom(context.ownerUserId)) return false;
    if (!['providerId','connectionId','sessionId','issuer','audience','realm','scope','resource','purpose'].every(k=>atom(context[k])) || !integer(context.sessionEpoch) || !integer(context.entitlementRevision)) return false;
    if (![connection.entitlementRevision,connection.consentRevision,connection.sourcePolicyRevision,connection.keyVersion,session.epoch,consent.revision,policy.revision,key.version].every(integer)) return false;
    if (!['consentId','sourcePolicyId','keyRef'].every(k=>atom(connection[k]))) return false;
    const owner=context.ownerUserId;
    if (connection.ownerUserId!==owner || connection.providerId!==context.providerId || connection.id!==context.connectionId || connection.entitlementRevision!==context.entitlementRevision || context.purpose!=='private_use' || connection.status!=='active' || connection.custody!=='server-envelope' || connection.expiresAt<=now || connection.revokedAt!=null) return false;
    if (session.ownerUserId!==owner || session.id!==context.sessionId || session.issuer!==context.issuer || session.audience!==context.audience || session.realm!==context.realm || session.epoch!==context.sessionEpoch || session.revokedAt!=null || session.expiresAt<=now) return false;
    if (consent.ownerUserId!==owner || consent.id!==connection.consentId || consent.revision!==connection.consentRevision || consent.objectType!=='connection' || consent.objectId!==connection.id || consent.purpose!=='private_use' || consent.choice!=='granted' || consent.validFrom>now || consent.expiresAt<=now) return false;
    if (policy.id!==connection.sourcePolicyId || policy.revision!==connection.sourcePolicyRevision || policy.active!==true || policy.proxyAllowed!==true || policy.expiresAt<=now) return false;
    if (key.ownerUserId!==owner || key.id!==connection.keyRef || key.version!==connection.keyVersion || !['active','decrypt-only'].includes(key.status) || key.expiresAt<=now) return false;
    if (![connection.expiresAt,session.expiresAt,consent.validFrom,consent.expiresAt,policy.expiresAt,key.expiresAt].every(Number.isSafeInteger)) return false;
    return Array.isArray(scopes) && scopes.some(s=>s.ownerUserId===owner && s.connectionId===connection.id && s.scope===context.scope && s.resource===context.resource && s.purpose===context.purpose);
  } catch { return false; }
}
