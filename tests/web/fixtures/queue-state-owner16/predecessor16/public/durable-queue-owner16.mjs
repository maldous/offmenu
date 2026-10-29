/** Owner 16 consumer for queue pin 0e7279a7b3ba9e8d68f5aba546d2404fc3fc99a9.
 * Inject that pin's createDurableOperationQueue; never silently import a moving
 * candidate. Only IndexedDB transaction completion is a persistence receipt.
 * A Web Locks exclusive lock spans load/modify/send/save across SAME-origin tabs.
 * No credentials enter this module or its database. Public binding is a selector,
 * not authority. Worker04/02 must authenticate independently and atomically bind
 * grant admission + expectedRevision CAS + immutable outcome ledger.
 * Protocol below is an explicit composition seam, not a shipped endpoint.
 */
export function indexedDBQueueStorage(indexedDB = globalThis.indexedDB, name = 'offmenu-owner16-outbox-v1') {
  if (!indexedDB) throw Error('IndexedDB unavailable');
  let pending;
  const database = () => pending ??= new Promise((resolve, reject) => {
    let cancelled = false;
    const request = indexedDB.open(name, 1);
    request.onupgradeneeded = () => request.result.createObjectStore('queues');
    request.onerror = () => { pending = undefined; reject(request.error); };
    request.onblocked = () => { cancelled = true; pending = undefined; reject(Error('IndexedDB upgrade blocked')); };
    request.onsuccess = () => {
      const db = request.result;
      if (cancelled) { db.close(); return; }
      db.onversionchange = () => { db.close(); pending = undefined; };
      resolve(db);
    };
  });
  async function transaction(key, value, write) {
    const db = await database();
    return new Promise((resolve, reject) => {
      const tx = db.transaction('queues', write ? 'readwrite' : 'readonly', write ? {durability: 'strict'} : undefined);
      const request = write ? tx.objectStore('queues').put(value, key) : tx.objectStore('queues').get(key);
      tx.oncomplete = () => resolve(write ? undefined : request.result);
      tx.onabort = tx.onerror = () => reject(tx.error || Error('IndexedDB commit failed'));
    });
  }
  return {load: key => transaction(key, undefined, false), save: (key, value) => transaction(key, value, true)};
}

const fields = ['subject', 'sessionId', 'realm', 'epoch', 'resource'];
function binding(value) {
  const out = {};
  for (const field of fields) {
    const descriptor = Object.getOwnPropertyDescriptor(value || {}, field);
    if (!descriptor || !Object.hasOwn(descriptor, 'value')) throw Error('Invalid public binding');
    const item = descriptor.value;
    if (field === 'epoch' ? !Number.isSafeInteger(item) || item < 1 : typeof item !== 'string' || !item || item.length > 200)
      throw Error('Invalid public binding');
    out[field] = item;
  }
  return out;
}

/** service.mutate({binding, operationId, expectedVersion, state, expiresAt})
 * must return {acknowledged:true, operationId, binding, status:'committed', revision}.
 * The ledger must dedup the binding+ID+exact expectedRevision+validated state.
 * Conflicts/denials remain unresolved: never auto-rebase a queued mutation.
 * Caller must separately reconcile unknown/expired results and durable logout.
 */
export function createStateQueueClient({createQueue, storage, locks = globalThis.navigator?.locks,
  service, publicBinding, now = Date.now}) {
  if (!createQueue || !storage || !locks?.request || !service?.mutate) throw Error('Missing qualified consumer dependency');
  const captured = binding(publicBinding);
  const scope = {accountId: captured.subject, resourceId: captured.resource,
    grantId: JSON.stringify([captured.sessionId, captured.realm, captured.epoch])};
  const lockName = 'offmenu-owner16:' + JSON.stringify(scope);
  let stopped = false, active;
  const transport = {idempotent: true, async send(envelope) {
    if (stopped) throw Error('Local scope stopped');
    const {expectedRevision, state} = envelope.payload;
    const result = await service.mutate({binding: {...captured}, operationId: envelope.operationId,
      expectedVersion: expectedRevision, state, expiresAt: envelope.expiresAt});
    const returned = binding(result?.binding);
    if (stopped || result?.acknowledged !== true || result.operationId !== envelope.operationId ||
        fields.some(field => returned[field] !== captured[field]) || result.status !== 'committed' ||
        result.revision !== expectedRevision + 1) throw Error('Unqualified operation result');
    // Deliberately reordered identity fields exercise field-based helper ACK.
    return {acknowledged: true, operationId: result.operationId,
      scope: {grantId: scope.grantId, resourceId: scope.resourceId, accountId: scope.accountId}};
  }};
  const exclusive = fn => locks.request(lockName, {mode: 'exclusive'}, async () => {
    active = createQueue({scope, storage, transport, now});
    try { return await fn(active); } finally { active = undefined; }
  });
  return {
    enqueue({operationId, expectedRevision, state, expiresAt}) {
      if (stopped) return Promise.reject(Error('Local scope stopped'));
      if (!Number.isSafeInteger(expectedRevision) || expectedRevision < 0 || expectedRevision >= Number.MAX_SAFE_INTEGER)
        return Promise.reject(Error('Invalid expected revision'));
      // Queue captures/validates the JSON tree before the lock callback yields.
      // Use the pinned helper with nonpersistent staging to obtain that tree.
      const staging = createQueue({scope, storage: {load: async () => null, save: async () => {}}, transport, now});
      const capturedOperation = staging.enqueue({operationId, payload: {expectedRevision, state}, expiresAt});
      return capturedOperation.then(op => exclusive(q => {
        if (stopped) throw Error('Local scope stopped');
        return q.enqueue({operationId: op.operationId, payload: op.payload, expiresAt: op.expiresAt});
      }));
    },
    flush: () => exclusive(q => stopped ? {status: 'revoked'} : q.flush()),
    inspect: () => exclusive(q => q.inspect()),
    async stopLocal() {
      stopped = true;
      // Sets pinned queue's immediate flag to suppress a late response.
      const stopping = active?.revoke();
      if (stopping) await stopping;
      await exclusive(q => q.revoke());
      return {localStopped: true, serverRevocation: 'unconfirmed'};
    }
  };
}
