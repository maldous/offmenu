import {createQueueStateBridge, createQueueStateHttpHandler} from './queue-state-bridge-owner16.mjs';

/** Owner-only entrypoint composition. No route registration, schema setup,
 * automatic enrollment or credential transport default. Root must inject the
 * selected protocol and independently reviewed protected transport/policy hooks.
 * resolveBinding returns a server enrollment/public-selector readback; it grants
 * no detached admission. Protocol freshly authenticates and rechecks grant SQL.
 */
export function createQueueStateWorker({createProtocol, resolveBinding, protocolOptions, origin,
  path = '/api/private/v2/state'}) {
  if (typeof createProtocol !== 'function' || typeof resolveBinding !== 'function' || !protocolOptions)
    throw Error('Selected protocol and server transport hooks required');
  return {async fetch(request, env) {
    // Isolate credential headers before server lookup/body-reading awaits.
    const selected = new Request(request, {headers: new Headers(request.headers)});
    let captured;
    try {
      const resolved = await resolveBinding(selected, env);
      if (!resolved || Object.getPrototypeOf(resolved) !== Object.prototype) throw Error('Invalid server selector');
      captured = {};
      for (const key of ['subject', 'sessionId', 'realm', 'epoch', 'resource']) {
        const descriptor = Object.getOwnPropertyDescriptor(resolved, key);
        if (!descriptor || !Object.hasOwn(descriptor, 'value') ||
            (key === 'epoch' ? !Number.isSafeInteger(descriptor.value) || descriptor.value < 1 :
              typeof descriptor.value !== 'string' || !descriptor.value || descriptor.value.length > 200)) throw Error('Invalid server selector');
        captured[key] = descriptor.value;
      }
      Object.freeze(captured); // Never retain a hook-owned selector across body awaits.
    }
    catch { return Response.json({status: 'unknown', acknowledged: false, confirmed: false},
      {status: 503, headers: {'Cache-Control': 'private, no-store'}}); }
    const protocol = createProtocol({...protocolOptions, database: env.DB});
    const bridge = createQueueStateBridge({protocol, trustedBinding: () => captured});
    const handler = createQueueStateHttpHandler({bridge, origin, path});
    return handler(selected);
  }};
}
