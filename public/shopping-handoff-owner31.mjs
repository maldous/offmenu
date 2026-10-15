import {shoppingItems} from './integrations.js';
export const RETAINED_HELPER_PIN = 'ac19b0c863ca486b9e6139cd2cad8497694fa368';

// Reject accessors/toJSON and non-JSON inputs before the retained helper sees them.
function copy(value, depth = 0, budget = {nodes: 0}) {
  if (++budget.nodes > 10000 || depth > 20) throw Error('Readback exceeds bounds');
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value || typeof value !== 'object') throw Error('Plain readback required');
  const array = Array.isArray(value);
  if (Object.getPrototypeOf(value) !== (array ? Array.prototype : Object.prototype)) throw Error('Plain readback required');
  const out = array ? [] : {};
  for (const key of Reflect.ownKeys(value)) {
    if (array && key === 'length') continue;
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key !== 'string' || !d.enumerable || !Object.hasOwn(d, 'value') || ['__proto__', 'constructor', 'toJSON'].includes(key)) throw Error('Plain readback required');
    if (array && !/^(0|[1-9]\d*)$/.test(key)) throw Error('Dense array required');
    out[key] = copy(d.value, depth + 1, budget);
  }
  if (array && Object.keys(out).length !== value.length) throw Error('Dense array required');
  return out;
}
const required = value => typeof value === 'string' && value.trim() && value.length <= 256;

// In-memory proposal/confirmation only. No purchase, persistence, URL navigation,
// provider transport or clipboard operation. Owners supply trusted session readback.
export function createShoppingHandoff({read, now, helper}) {
  if (typeof read !== 'function' || typeof now !== 'function' || helper?.pin !== RETAINED_HELPER_PIN || !required(helper.reviewRef) || typeof helper.propose !== 'function' || typeof helper.confirm !== 'function') throw Error('Reviewed pinned helper and readback required');
  const previews = new WeakMap();
  function build(request) {
    const state = copy(read());
    const req = copy(request);
    for (const field of ['accountId', 'kitchenId', 'revision', 'sessionEpoch']) if (!required(state[field])) throw Error('Authenticated account/kitchen/revision/session readback required');
    if (state.canExport !== true || state.demo !== false) throw Error('Export scope unavailable');
    if (!required(req.id) || req.kind !== 'retailer' || !required(req.destinationId)) throw Error('Retailer proposal required');
    if (!state.data || !Array.isArray(state.bindings)) throw Error('Source bindings required');
    const {profile, recipes, inventory, products, date, usePantry} = state.data;
    const items = shoppingItems(profile, recipes, inventory, products, date, usePantry).filter(item => !item.checked);
    if (!items.length || items.length > 100 || new Set(items.map(i => i.id)).size !== items.length) throw Error('Supply 1–100 unique uncollected shopping lines');
    const records = new Map();
    const lines = items.map(item => {
      const bindings = state.bindings.filter(b => b.lineId === item.id);
      if (!bindings.length) throw Error('Reviewed provenance binding required for every line');
      for (const binding of bindings) {
        if (binding.accountId !== state.accountId || binding.kitchenId !== state.kitchenId || binding.revision !== state.revision || binding.admitted !== true || !required(binding.record?.id)) throw Error('Source binding is not admitted in current scope/revision');
        const record = binding.record;
        if (records.has(record.id) && JSON.stringify(records.get(record.id)) !== JSON.stringify(record)) throw Error('Conflicting source record');
        records.set(record.id, record);
      }
      if ((item.quantity != null && (!Number.isFinite(item.quantity) || item.quantity <= 0)) || (item.unit != null && !required(item.unit))) throw Error('Invalid shopping quantity');
      return {id:item.id, name:item.name, amount:item.amount, quantity:item.quantity ?? null, unit:item.unit ?? null,
        uncertainty:item.quantity == null || !item.unit ? ['Source quantity/unit unresolved'] : [], sourceRecordIds:bindings.map(b => b.record.id)};
    });
    const draft = {id:req.id, scope:JSON.stringify([state.accountId,state.kitchenId]), revision:state.revision, kind:'retailer', records:[...records.values()],
      detail:{destinationId:req.destinationId, sessionEpoch:state.sessionEpoch, date, usePantry, lines}};
    return {draft, options:{now:now(), policies:state.policies, market:profile.country || ''}};
  }
  return {
    preview(request) {
      const {draft, options} = build(request);
      const proposal = helper.propose(draft, options);
      const view = copy(proposal);
      previews.set(view, {request:copy(request), snapshot:proposal.snapshot});
      return view;
    },
    confirm(view, {confirmed = false} = {}) {
      const pending = previews.get(view);
      if (!pending || confirmed !== true) throw Error('Explicit confirmation of this preview required');
      const {draft, options} = build(pending.request);
      const current = helper.propose(draft, options);
      if (current.snapshot !== pending.snapshot || JSON.stringify(view) !== JSON.stringify(current)) throw Error('Readback changed; review a fresh preview');
      const result = helper.confirm(draft, {confirmed:true, scope:draft.scope, revision:draft.revision, proposalId:draft.id, snapshot:pending.snapshot}, options);
      previews.delete(view);
      return copy(result);
    },
  };
}
