/** Queue/state composition for reviewed Owner04 pin 25543bd75c3812a203e0d3b865d51302bfe1854d.
 * Atomic admission/CAS/ledger/revoke belongs to protocol's SAME store transaction.
 * This bridge does not reserve admission, initialize schema, or mint authority.
 * Actual Request travels unchanged into protocol. trustedBinding is a synchronous
 * server-owned public selector from explicit enrollment, NEVER request body data.
 * Credentials stay inside protocol's synchronous protected readSession hook.
 * A successful HTTP response alone is insufficient: exact binding, operation,
 * expected-version successor and canonical digest must match before confirmation.
 */
const fields = ['subject', 'sessionId', 'realm', 'epoch', 'resource'];
function canonical(value, depth = 0) {
  if (depth > 64) throw Error('Invalid JSON tree');
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return JSON.stringify(value);
  if (typeof value === 'number' && Number.isFinite(value)) return JSON.stringify(value);
  if (Array.isArray(value)) {
    if (Object.getPrototypeOf(value) !== Array.prototype || Reflect.ownKeys(value).length !== value.length + 1) throw Error('Invalid JSON tree');
    const parts = [];
    for (let i = 0; i < value.length; i++) {
      const d = Object.getOwnPropertyDescriptor(value, String(i));
      if (!d || !Object.hasOwn(d, 'value')) throw Error('Invalid JSON tree');
      parts.push(canonical(d.value, depth + 1));
    }
    return '[' + parts.join(',') + ']';
  }
  if (value && Object.getPrototypeOf(value) === Object.prototype) {
    const keys = Reflect.ownKeys(value);
    if (keys.some(key => typeof key !== 'string')) throw Error('Invalid JSON tree');
    return '{' + keys.sort().map(key => {
      const d = Object.getOwnPropertyDescriptor(value, key);
      if (!d.enumerable || !Object.hasOwn(d, 'value')) throw Error('Invalid JSON tree');
      return JSON.stringify(key) + ':' + canonical(d.value, depth + 1);
    }).join(',') + '}';
  }
  throw Error('Invalid JSON tree');
}
function publicBinding(value) {
  const data = JSON.parse(canonical(value));
  if (!data || Array.isArray(data) || Object.keys(data).length !== fields.length ||
      fields.some(field => !Object.hasOwn(data, field) || (field === 'epoch' ?
        !Number.isSafeInteger(data[field]) || data[field] < 1 : typeof data[field] !== 'string' || !data[field] || data[field].length > 200)))
    throw Error('Invalid binding');
  const url = new URL(data.resource);
  if (url.protocol !== 'https:' || url.pathname !== '/api/state' || url.search || url.hash || url.username || url.password || url.href !== data.resource)
    throw Error('Invalid resource');
  return Object.freeze(Object.fromEntries(fields.map(field => [field, data[field]])));
}
function capture(command) {
  const serialized = canonical(command);
  if (new TextEncoder().encode(serialized).length > 2000000) throw Error('Command too large');
  const data = JSON.parse(serialized);
  if (!data || Array.isArray(data) || Object.keys(data).length !== 3 ||
      !Object.hasOwn(data, 'state') || !/^[A-Za-z0-9_-]{16,128}$/.test(data.operationId) ||
      typeof data.operationId !== 'string' || !Number.isSafeInteger(data.expectedVersion) ||
      data.expectedVersion < 0 || data.expectedVersion >= Number.MAX_SAFE_INTEGER)
    throw Error('Invalid command');
  return data;
}
const digest = async text => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))), b => b.toString(16).padStart(2, '0')).join('');

export function createQueueStateBridge({protocol, trustedBinding}) {
  if (!protocol?.mutate || !protocol?.status || typeof trustedBinding !== 'function') throw Error('Qualified protocol and server binding hook required');
  async function run(request, command, recover) {
    // Everything referenced by digest/CAS/ACK is privately captured before awaits.
    const captured = capture(command), binding = publicBinding(trustedBinding(request));
    const digestInput = canonical({audience: binding.resource, method: 'PUT', version: captured.expectedVersion, state: captured.state});
    const unknown = () => ({status: 'unknown', acknowledged: false, confirmed: false, operationId: captured.operationId});
    let expectedDigest, result;
    try {
      // Invoke Owner04 NOW: its command and protected credentials are captured
      // synchronously. Hashing first would leave Request credentials mutable
      // until a later microtask and recreate a detached-capture window.
      const pending = recover ? protocol.status(request, captured.operationId) : protocol.mutate(request, captured);
      const outcome = Promise.resolve(pending).then(value => ({value}), () => ({failed: true}));
      expectedDigest = await digest(digestInput);
      const resolved = await outcome;
      if (resolved.failed) return unknown();
      result = resolved.value;
      // Capture returned plain data without invoking getters/serialization hooks.
      result = JSON.parse(canonical(result));
      const returned = publicBinding(result.binding);
      if (fields.some(field => binding[field] !== returned[field]) || result.operationId !== captured.operationId) return unknown();
      if (result.status === 'unknown') return unknown();
      if (result.digest !== expectedDigest) return unknown();
      if (result.status === 'committed' && result.acknowledged === true && result.revision === captured.expectedVersion + 1)
        return {...result, confirmed: true};
      if (result.status === 'conflict' && result.acknowledged === false && Number.isSafeInteger(result.revision) && result.revision >= 0 && result.revision !== captured.expectedVersion)
        return {...result, confirmed: true}; // Terminal conflict, never queue ACK.
    } catch { /* Denial, storage failure, timeout or damaged result: no ACK. */ }
    return unknown();
  }
  return {submit: (request, command) => run(request, command, false), recover: (request, command) => run(request, command, true)};
}

/** Prepared private-v2 HTTP seam only. No central routing or unreviewed D1 import.
 * Root must select the qualified protocol, enrollment/CSRF/credential policies and
 * endpoint before adoption. Existing protocol policies still authorize every call.
 * Exact Request headers are captured synchronously before body-reading awaits.
 */
export function createQueueStateHttpHandler({bridge, origin, path = '/api/private/v2/state', maxBytes = 2000000}) {
  const configured = new URL(origin);
  if (configured.protocol !== 'https:' || configured.origin !== origin || !bridge?.submit || !bridge?.recover ||
      typeof path !== 'string' || !/^\/api\/[A-Za-z0-9_/-]+$/.test(path) || path.endsWith('/') ||
      !Number.isSafeInteger(maxBytes) || maxBytes < 1 || maxBytes > 2000000) throw Error('Invalid HTTP bridge configuration');
  const reply = (body, status) => Response.json(body, {status, headers: {'Cache-Control': 'private, no-store'}});
  return async request => {
    // Transfer the request body instead of teeing it with clone(): cancellation
    // of a tee can wait forever for the unused original branch to finish.
    const selected = new Request(request, {headers: new Headers(request.headers)}), url = new URL(selected.url);
    const recovery = url.pathname === path + '/status';
    if (url.origin !== origin || url.search || (!recovery && url.pathname !== path)) return reply({error: 'Not found'}, 404);
    if (selected.method !== (recovery ? 'POST' : 'PUT')) return reply({error: 'Method not allowed'}, 405);
    if (selected.headers.get('Origin') !== origin) return reply({error: 'Origin mismatch'}, 403);
    if (selected.headers.get('Content-Type')?.split(';')[0].trim().toLowerCase() !== 'application/json') return reply({error: 'JSON required'}, 415);
    const reader = selected.body?.getReader();
    if (!reader) return reply({error: 'Body required'}, 400);
    const chunks = []; let size = 0;
    try {
      for (;;) {
        const {value, done} = await reader.read(); if (done) break;
        size += value.byteLength;
        if (size > maxBytes) { await reader.cancel(); return reply({error: 'Body too large'}, 413); }
        chunks.push(value);
      }
      const bytes = new Uint8Array(size); let offset = 0;
      for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
      const command = JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes));
      let result;
      try { result = await (recovery ? bridge.recover(selected, command) : bridge.submit(selected, command)); }
      catch { return reply({status: 'unknown', acknowledged: false, confirmed: false}, 503); }
      if (result?.status === 'committed' && result.confirmed === true && result.acknowledged === true) return reply(result, 200);
      if (result?.status === 'conflict' && result.confirmed === true && result.acknowledged === false) return reply(result, 409);
      return reply({status: 'unknown', acknowledged: false, confirmed: false}, 503);
    } catch { return reply({error: 'Invalid command'}, 400); }
    finally { reader.releaseLock(); }
  };
}
