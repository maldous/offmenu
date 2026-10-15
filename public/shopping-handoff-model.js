import {recordPermission} from './record-policy.js';

const kinds = new Set(['substitute', 'calendar', 'retailer']);
function text(value, field) {
  if (typeof value !== 'string' || !value.trim() || value.length > 256) throw Error(`Invalid ${field}`);
}
function explicitInstant(value) {
  if (typeof value !== 'string') return false;
  const match = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{3})?(Z|[+-](\d{2}):(\d{2}))$/.exec(value);
  if (!match || +match[2] > 23 || +match[3] > 59 || +match[4] > 59 || +(match[6] || 0) > 23 || +(match[7] || 0) > 59) return false;
  const day = Date.parse(match[1] + 'T00:00:00Z');
  return Number.isFinite(day) && new Date(day).toISOString().slice(0, 10) === match[1] && Number.isFinite(Date.parse(value));
}
function snapshot(value) {
  // Accept bounded plain JSON only, without converting unknown numeric values to null.
  const encoded = JSON.stringify(value, (_key, item) => {
    if (typeof item === 'number' && !Number.isFinite(item)) throw Error('Invalid numeric value');
    if (item === undefined || typeof item === 'function' || typeof item === 'symbol' || typeof item === 'bigint') throw Error('Plain JSON required');
    return item;
  });
  if (!encoded || encoded.length > 65536) throw Error('Proposal exceeds bounds');
  return JSON.parse(encoded);
}

// No clock, storage, transport, inventory mutation or provider action is implicit.
export function proposeShoppingHandoff(draft, {now, policies = {}, market = ''} = {}) {
  if (!Number.isFinite(now)) throw Error('Injected clock required');
  const value = snapshot(draft);
  for (const field of ['id', 'scope', 'revision']) text(value[field], field);
  if (!kinds.has(value.kind)) throw Error('Unsupported proposal kind');
  if (!Array.isArray(value.records) || !value.records.length || value.records.length > 100) throw Error('Supply 1–100 source records');
  const ids = new Set();
  for (const record of value.records) {
    text(record.id, 'source record ID');
    text(record.provenance?.sourceId, 'source identity');
    if (ids.has(record.id)) throw Error('Duplicate source record ID');
    ids.add(record.id);
    const permission = recordPermission(record, {
      action: value.kind === 'substitute' ? 'derive' : 'export',
      now, market, policy: Object.hasOwn(policies, record.provenance.sourceId) ? policies[record.provenance.sourceId] : undefined,
    });
    if (!permission.allowed) throw Error(permission.reason);
  }
  const detail = value.detail;
  if (!detail || typeof detail !== 'object' || Array.isArray(detail)) throw Error('Proposal detail required');
  if (value.kind === 'substitute') {
    if (!ids.has(detail.originalId) || !ids.has(detail.candidateId) || detail.originalId === detail.candidateId) throw Error('Distinct original and candidate records required');
  } else {
    text(detail.destinationId, 'destination');
    if (value.kind === 'calendar') {
      // A caller supplies an explicit interval with offset; no inferred timezone.
      if (!explicitInstant(detail.start) || !explicitInstant(detail.end) || Date.parse(detail.end) <= Date.parse(detail.start)) throw Error('Explicit calendar interval required');
    }
  }
  return {
    version: 1, status: 'proposed', draft: value, snapshot: JSON.stringify(value),
    limitations: ['No purchase authority', 'No inferred availability, expiry, ownership, allergy or nutrition equivalence'],
  };
}

// Consent is local review evidence, not authentication or provider authorization.
// Rebuild from current data and recheck rights rather than trusting a stored preview.
export function confirmShoppingHandoff(currentDraft, consent, options) {
  const proposal = proposeShoppingHandoff(currentDraft, options);
  if (consent?.confirmed !== true || consent.scope !== proposal.draft.scope || consent.revision !== proposal.draft.revision || consent.proposalId !== proposal.draft.id || consent.snapshot !== proposal.snapshot) throw Error('Explicit confirmation of the current scoped proposal required');
  return {...proposal, status: 'confirmed-proposal'};
}
