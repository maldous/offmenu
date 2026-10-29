export const RETAINED_HELPER_PIN = 'e829f61c181a5965ffba70462433d4b446f226c7';
const text = x => typeof x === 'string' && x.length > 0 && x.length <= 300;

// Dependencies must be provided by the authenticated production owner, never
// request JSON. Independent exact-pin review is required before wiring this route.
export function createLotRestrictionConsumer({verifiedUser, loadAccount, clock, evaluateScoped}) {
  if (![verifiedUser, loadAccount, clock, evaluateScoped].every(x => typeof x === 'function')) throw Error('Trusted dependencies required');
  return async function lotRestrictionRoute(request) {
    if (new URL(request.url).pathname !== '/api/catalogue/lot-restriction') return null;
    const reply = (body, status = 200) => new Response(JSON.stringify(body), {status, headers: {'Content-Type': 'application/json', 'Cache-Control': 'no-store'}});
    if (request.method !== 'POST') return reply({error: 'POST required'}, 405);
    if (request.headers.get('Origin') !== new URL(request.url).origin) return reply({error: 'Origin mismatch'}, 403);
    const user = await verifiedUser(request);
    if (!text(user?.id)) return reply({error: 'Sign-in required'}, 401);
    // Streaming cap includes bodies with no Content-Length.
    const reader = request.body?.getReader();
    if (!reader) return reply({error: 'Selection required'}, 400);
    let bytes = 0, chunks = [];
    while (true) {
      const {done, value} = await reader.read();
      if (done) break;
      bytes += value.byteLength;
      if (bytes > 4096) { await reader.cancel(); return reply({error: 'Selection too large'}, 413); }
      chunks.push(value);
    }
    let selection;
    try { const all = new Uint8Array(bytes); let offset = 0; for (const chunk of chunks) {all.set(chunk, offset); offset += chunk.length;} selection = JSON.parse(new TextDecoder().decode(all)); }
    catch { return reply({error: 'Invalid selection'}, 400); }
    if (!selection || Object.keys(selection).some(k => !['lotId', 'preferenceId'].includes(k)) || !text(selection.lotId) || !text(selection.preferenceId)) return reply({error: 'Only lot and preference IDs allowed'}, 400);
    const account = await loadAccount(user.id);
    if (account?.owner !== user.id) return reply({error: 'Account unavailable'}, 403);
    const lot = account.lots?.find(x => x.id === selection.lotId);
    const preference = account.preferences?.find(x => x.id === selection.preferenceId);
    const product = account.products?.find(x => x.id === lot?.productId);
    const unknown = reason => reply({status: 'unknown', reason, automaticSelection: false, evidenceIds: []});
    if (!lot || !preference || !product || lot.owner !== user.id || preference.owner !== user.id || product.owner !== user.id) return unknown('Account selection binding unavailable');
    if (!text(lot.lotCode) || !text(product.assertionSubject) || product.matchStatus !== 'verified' || !text(product.sourceId)) return unknown('Verified actual lot/product identity required');
    const now = clock();
    if (!Number.isFinite(now) || !text(preference.sourceId) || !text(preference.recordedAt) || !Number.isFinite(Date.parse(preference.recordedAt)) || Date.parse(preference.recordedAt) > now || !text(preference.revision)) return unknown('Current preference provenance required');
    const result = evaluateScoped({rule: preference.rule, target: {kind: 'lot', subject: product.assertionSubject, lotCode: lot.lotCode, owner: user.id}, evidence: account.assertions, policies: account.policies, owner: user.id, consent: account.evidenceConsent === true, market: account.market, now});
    return reply({...result, automaticSelection: false, binding: {lotId: lot.id, productId: product.id, productSourceId: product.sourceId, preferenceId: preference.id, preferenceSourceId: preference.sourceId, preferenceRevision: preference.revision, preferenceRecordedAt: preference.recordedAt}, notice: 'Scoped restriction decision; no medical or cross-contact guarantee'});
  };
}
