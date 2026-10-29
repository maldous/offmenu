/**
 * Isolated P0-05 outbox primitive; not wired to snapshot sync or cloud APIs.
 * Existing sync-ui.js checkpoints regenerate mutationId and PUT only revision/state.
 *
 * Integration contract:
 * - storage.load(key)/save(key, JSON record) must atomically persist a whole record;
 *   save resolves only after durable commit. One live writer per scoped key is
 *   required (a browser adapter must hold an exclusive cross-tab lock).
 * - transport = {idempotent: true, send(envelope)} must authenticate the captured
 *   scope and atomically deduplicate (scope, operationId) with the remote effect.
 *   A durable acknowledgement is {acknowledged:true, scope, operationId}.
 *   Scope field order is irrelevant; extra scope fields are rejected.
 *   HTTP success alone is not acknowledgement. Current state PUT APIs do not
 *   satisfy this contract. This helper alone does not provide exactly-once effects.
 * - scope includes accountId, resourceId and grantId (authorization generation).
 *   A new login/grant must use a new scope; never carry work across identities.
 *   Call revoke immediately when authorization is lost. Remote authorization
 *   still must reject revoked access; an already-sent request cannot be undone.
 * - Unknown results retain the same ID/payload. Expiry stops sends but retains
 *   evidence for explicit acknowledgement after reconciliation. FIFO blocks
 *   behind unresolved expired work. IDs/tombstones are never silently recycled;
 *   at capacity callers must reconcile/archive under a separate reviewed policy.
 * No timers, UI, credentials, storage adapter or server mutation is supplied.
 */
const copy = value => jsonPayload(value);
const equal = (a, b) => JSON.stringify(a) === JSON.stringify(b);
function identifier(value) {
  if (typeof value !== 'string' || !value || value.length > 200) throw Error('Invalid identifier');
  return value;
}
function captureScope(value) {
  const data = jsonPayload(value), fields = ['accountId', 'resourceId', 'grantId'];
  if (!data || Array.isArray(data) || typeof data !== 'object' ||
      Object.keys(data).length !== fields.length || fields.some(key => !Object.hasOwn(data, key)))
    throw Error('Invalid scope');
  return Object.fromEntries(fields.map(key => [key, identifier(data[key])]));
}
function jsonPayload(value) {
  // Capture descriptor values once into a fresh tree, never running getters or
  // toJSON. Reject hidden/symbol fields, sparse arrays, cycles and custom
  // prototypes rather than silently dropping or transforming caller data.
  const active = new Set();
  const invalid = () => { throw Error('Payload must be plain JSON data'); };
  function capture(item) {
    if (item === null || typeof item === 'string' || typeof item === 'boolean') return item;
    if (typeof item === 'number' && Number.isFinite(item)) return item;
    if (!item || typeof item !== 'object' || active.has(item)) return invalid();
    const array = Array.isArray(item), prototype = Object.getPrototypeOf(item);
    if (array ? prototype !== Array.prototype : prototype !== Object.prototype && prototype !== null) return invalid();
    active.add(item);
    const descriptors = Object.getOwnPropertyDescriptors(item), keys = Reflect.ownKeys(descriptors);
    const result = array ? [] : {};
    if (array && (keys.length !== descriptors.length.value + 1 ||
        keys.some(key => key !== 'length' && (typeof key !== 'string' || !/^(0|[1-9][0-9]*)$/.test(key) || Number(key) >= descriptors.length.value))))
      return invalid();
    for (const key of keys) {
      if (array && key === 'length') continue;
      const descriptor = descriptors[key];
      if (typeof key !== 'string' || !descriptor.enumerable || !Object.hasOwn(descriptor, 'value')) return invalid();
      // defineProperty preserves benign own __proto__/constructor/toJSON data.
      Object.defineProperty(result, key, {value: capture(descriptor.value), enumerable: true, writable: true, configurable: true});
    }
    active.delete(item);
    return result;
  }
  return capture(value);
}

export function createDurableOperationQueue({scope: inputScope, storage, transport, now = Date.now,
  retryDelay = 1000, maxRetryDelay = 60000, maxOperations = 1000}) {
  const scope = captureScope(inputScope), key = 'offmenu-operations-v1:' + JSON.stringify(scope);
  if (!storage?.load || !storage?.save || transport?.idempotent !== true || !transport?.send)
    throw Error('Durable storage and an idempotent transport are required');
  if (!Number.isSafeInteger(retryDelay) || retryDelay < 1 || !Number.isSafeInteger(maxRetryDelay) ||
      maxRetryDelay < retryDelay || !Number.isSafeInteger(maxOperations) || maxOperations < 1)
    throw Error('Invalid queue limits');
  let tail = Promise.resolve(), revoked = false;
  const serial = fn => { const result = tail.then(fn); tail = result.catch(() => {}); return result; };
  const time = () => { const value = now(); if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid clock'); return value; };
  async function load() {
    const stored = await storage.load(key);
    const record = stored == null ? {version: 1, scope, revoked: false, operations: []} : copy(stored);
    if (record.version !== 1 || !equal(captureScope(record.scope), scope) || typeof record.revoked !== 'boolean' ||
        !Array.isArray(record.operations) || record.operations.length > maxOperations)
      throw Error('Invalid scoped queue');
    const ids = new Set();
    for (const op of record.operations) {
      identifier(op.operationId);
      if (ids.has(op.operationId) || !['pending', 'unknown', 'expired', 'acknowledged'].includes(op.status) ||
          !Number.isSafeInteger(op.expiresAt) || op.expiresAt < 0 || !Number.isSafeInteger(op.attempts) ||
          op.attempts < 0 || !Number.isSafeInteger(op.nextAttemptAt) || op.nextAttemptAt < 0)
        throw Error('Invalid persisted operation');
      jsonPayload(op.payload); ids.add(op.operationId);
    }
    revoked ||= record.revoked;
    record.revoked ||= revoked;
    return record;
  }
  const save = record => storage.save(key, copy(record));
  const matches = (ack, op) => {
    try {
      const data = copy(ack);
      return data?.acknowledged === true && data.operationId === op.operationId && equal(captureScope(data.scope), scope);
    } catch { return false; }
  };
  return {
    enqueue({operationId, payload, expiresAt}) {
      // Capture caller input before yielding; pending envelopes are immutable.
      const id = identifier(operationId), data = jsonPayload(payload);
      if (!Number.isSafeInteger(expiresAt) || expiresAt <= time()) throw Error('Expiry must be in the future');
      return serial(async () => {
        const record = await load();
        if (revoked) throw Error('Scope revoked');
        const existing = record.operations.find(op => op.operationId === id);
        if (existing) {
          if (!equal(existing.payload, data) || existing.expiresAt !== expiresAt) throw Error('Operation ID already bound');
          return copy(existing);
        }
        if (expiresAt <= time()) throw Error('Operation expired before persistence');
        if (record.operations.length >= maxOperations) throw Error('Queue capacity reached');
        const op = {operationId: id, payload: data, expiresAt, attempts: 0, nextAttemptAt: 0, status: 'pending'};
        record.operations.push(op); await save(record); return copy(op);
      });
    },
    inspect: () => serial(async () => copy(await load())),
    revoke() {
      revoked = true; // Stops acceptance of in-flight responses before persistence.
      return serial(async () => { const record = await load(); record.revoked = true; await save(record); });
    },
    acknowledge(ack) {
      const captured = copy(ack);
      return serial(async () => {
        const record = await load(), op = record.operations.find(item => item.operationId === captured.operationId);
        if (revoked || !op || !matches(captured, op)) throw Error('Acknowledgement scope or operation mismatch');
        op.status = 'acknowledged'; await save(record); return copy(op);
      });
    },
    flush: () => serial(async () => {
      const record = await load();
      if (revoked) return {status: 'revoked'};
      const op = record.operations.find(item => item.status !== 'acknowledged');
      if (!op) return {status: 'idle'};
      const current = time();
      if (op.expiresAt <= current || op.status === 'expired') {
        op.status = 'expired'; await save(record); return {status: 'expired', operationId: op.operationId};
      }
      if (op.nextAttemptAt > current) return {status: 'backoff', operationId: op.operationId};
      // Commit uncertainty BEFORE transport. Crashes and lost responses must not
      // become a new operation or be mistaken for a confirmed failure.
      op.status = 'unknown'; op.attempts++;
      op.nextAttemptAt = Math.min(op.expiresAt, current + Math.min(maxRetryDelay, retryDelay * 2 ** Math.min(op.attempts - 1, 30)));
      await save(record);
      if (revoked) { record.revoked = true; await save(record); return {status: 'revoked'}; }
      if (time() >= op.expiresAt) {
        op.status = 'expired'; await save(record); return {status: 'expired', operationId: op.operationId};
      }
      let ack;
      try { ack = await transport.send(copy({scope, operationId: op.operationId, payload: op.payload, expiresAt: op.expiresAt})); }
      catch { /* Delivery/result is unknown; retry only under deduplication contract. */ }
      if (revoked) record.revoked = true;
      else if (matches(ack, op)) op.status = 'acknowledged';
      await save(record);
      return {status: revoked ? 'revoked' : op.status, operationId: op.operationId};
    })
  };
}
