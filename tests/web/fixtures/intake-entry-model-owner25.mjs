// Independent intake records; adoption requires an owner-controlled persistence boundary.
// This module does not compute nutrients, deduct stock, or authorize source access.
const KINDS = ['meal', 'water', 'snack', 'restaurant', 'substitution'];
const STATES = ['planned', 'consumed', 'unknown-consumed'];
const UNITS = ['g', 'ml', 'count', 'portion'];

function text(value, name, limit = 200, allowEmpty = false) {
  if (typeof value !== 'string' || value.length > limit || (!allowEmpty && !value.trim())) {
    throw new TypeError(`Invalid ${name}`);
  }
}

// Retain JSON provenance/rights/consent detail without silently dropping unknown fields.
function snapshot(value) {
  let nodes = 0;
  function visit(item, depth) {
    if (++nodes > 2000 || depth > 8) throw new TypeError('Intake entry exceeds bounds');
    if (item === null || typeof item === 'boolean') return;
    if (typeof item === 'string' && item.length <= 4000) return;
    if (typeof item === 'number' && Number.isFinite(item)) return;
    if (Array.isArray(item)) { for (const child of item) visit(child, depth + 1); return; }
    if (item && Object.getPrototypeOf(item) === Object.prototype) {
      for (const [key, child] of Object.entries(item)) {
        text(key, 'field name');
        visit(child, depth + 1);
      }
      return;
    }
    throw new TypeError('Intake entry must contain bounded JSON data');
  }
  visit(value, 0);
  return structuredClone(value);
}

function food(value) {
  text(value?.id, 'food ID');
  text(value?.label, 'food label');
  text(value?.source?.id, 'source ID');
  text(value?.source?.recordId, 'source record ID');
  // A recorded rights assertion is retained, never interpreted as permission.
  text(value?.source?.rights, 'source rights assertion', 2000);
}

function validate(input, accountId) {
  text(accountId, 'account scope');
  if (input.accountId !== accountId) throw new TypeError('Account scope mismatch');
  text(input.id, 'entry ID');
  text(input.memberId, 'member scope', 200, true);
  if (!KINDS.includes(input.kind) || !STATES.includes(input.state)) throw new TypeError('Invalid intake kind or state');
  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.date) ||
      !Number.isFinite(Date.parse(input.date)) || new Date(input.date).toISOString().slice(0, 10) !== input.date) {
    throw new TypeError('Invalid intake date');
  }
  if (typeof input.createdAt !== 'string' || !/^\d{4}-\d{2}-\d{2}T/.test(input.createdAt) ||
      !/(Z|[+-]\d{2}:\d{2})$/.test(input.createdAt) || !Number.isFinite(Date.parse(input.createdAt))) {
    throw new TypeError('Invalid intake timestamp');
  }
  text(input.consent?.id, 'consent ID');
  if (input.consent.purpose !== 'intake-recording' || typeof input.consent.granted !== 'boolean') {
    throw new TypeError('Explicit intake recording consent required');
  }
  food(input.food);
  const q = input.quantity;
  if (!q || !UNITS.includes(q.unit) ||
      !(q.value === null || (Number.isFinite(q.value) && q.value >= 0 && q.value <= 1e9))) {
    throw new TypeError('Invalid intake quantity');
  }
  if (input.state === 'unknown-consumed' && q.value !== null) throw new TypeError('Unknown consumed quantity must be null');
  if (input.state === 'consumed' && q.value === null) throw new TypeError('Consumed quantity must be explicit');
  if (input.kind === 'substitution') {
    food(input.substitution?.planned);
    food(input.substitution?.actual);
    const actual = input.substitution.actual;
    if (actual.id !== input.food.id || actual.source.id !== input.food.source.id ||
        actual.source.recordId !== input.food.source.recordId) throw new TypeError('Substitution actual food must match entry food');
  } else if (input.substitution != null) {
    throw new TypeError('Substitution detail requires substitution kind');
  }
  // Nutrients require a separately reviewed evidence/quantity contract. Never use
  // original-recipe totals for a substituted food, or manufacture zeros for water.
  if (Object.hasOwn(input, 'totals')) throw new TypeError('Nutrient totals require separate evidence integration');
  return input;
}

export function createIntakeEntry(input, {accountId, clock} = {}) {
  if (typeof clock !== 'function') throw new TypeError('An injected clock is required');
  const entry = snapshot({...input, createdAt: clock()});
  return validate(entry, accountId);
}

// Callers receive separate buckets; plans and unknown amounts never become
// measured consumption. Cross-account and withdrawn-consent records are withheld.
export function partitionIntakeEntries(entries, {accountId, memberId} = {}) {
  text(accountId, 'account scope');
  if (memberId !== undefined) text(memberId, 'member scope', 200, true);
  if (!Array.isArray(entries) || entries.length > 1000) throw new TypeError('Invalid intake entry collection');
  const result = {planned: [], consumed: [], unknownConsumed: []};
  const ids = new Set();
  for (const input of entries) {
    if (input?.accountId !== accountId) continue;
    const entry = validate(snapshot(input), accountId);
    if (ids.has(entry.id)) throw new TypeError('Duplicate intake entry ID');
    ids.add(entry.id);
    if (!entry.consent.granted || (memberId !== undefined && entry.memberId !== memberId)) continue;
    result[entry.state === 'unknown-consumed' ? 'unknownConsumed' : entry.state].push(entry);
  }
  return result;
}
