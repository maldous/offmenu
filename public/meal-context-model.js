// P2-01 descriptive declarations only. Caller supplies verified account/authority.
const kinds = new Set(['home', 'carer', 'taste', 'culture', 'fasting']);
const statuses = new Set(['declared', 'unknown', 'withdrawn']);
const fail = message => { throw new TypeError(message); };
function text(value, max = 1024) {
  if (typeof value !== 'string' || !value.trim() || value.length > max) fail('Explicit bounded text required');
  return value; // Preserve spelling, whitespace and source language.
}
function capture(value, depth = 0, budget = {nodes: 0, chars: 0}) {
  if (++budget.nodes > 10000 || depth > 12) fail('Context exceeds bounds');
  if (value === null || typeof value === 'boolean') return value;
  if (typeof value === 'string') { budget.chars += value.length; if (budget.chars > 65536) fail('Context exceeds bounds'); return value; }
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value || typeof value !== 'object') fail('Ordinary JSON required');
  if (Array.isArray(value)) {
    if (value.length > 256 || Object.getPrototypeOf(value) !== Array.prototype) fail('Bounded ordinary array required');
    const descriptors = Object.getOwnPropertyDescriptors(value);
    if (Reflect.ownKeys(descriptors).length !== value.length + 1) fail('Dense ordinary array required');
    return Array.from({length: value.length}, (_, i) => {
      const d = descriptors[i]; if (!d || !('value' in d)) fail('Accessor/sparse input rejected');
      return capture(d.value, depth + 1, budget);
    });
  }
  if (Object.getPrototypeOf(value) !== Object.prototype) fail('Ordinary object required');
  const result = {};
  for (const key of Reflect.ownKeys(value)) {
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (typeof key !== 'string' || ['__proto__', 'constructor', 'prototype'].includes(key) || !d.enumerable || !('value' in d)) fail('Unsafe object property');
    result[key] = capture(d.value, depth + 1, budget);
  }
  return result;
}
function fields(value, expected) {
  if (!value || Array.isArray(value) || typeof value !== 'object' || Object.keys(value).some(k => !expected.includes(k))) fail('Unsupported context fields');
}
function freeze(value) {
  if (value && typeof value === 'object') { Object.values(value).forEach(freeze); Object.freeze(value); }
  return value;
}
function instant(value) {
  text(value, 40);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{3})?(?:Z|[+-]\d{2}:\d{2})$/.test(value) || !Number.isFinite(Date.parse(value))) fail('Dated instant with explicit offset required');
  // Date.parse can normalize impossible calendar dates; reject that normalization.
  const local = value.slice(0, 19), normalized = new Date(Date.parse(local + 'Z')).toISOString().slice(0, 19);
  if (normalized !== local) fail('Invalid calendar instant');
  return Date.parse(value);
}
function window(value) {
  if (value === null) return;
  fields(value, ['start', 'end', 'timeZone']);
  const start = instant(value.start), end = instant(value.end);
  if (end <= start) fail('Window end must follow start');
  text(value.timeZone, 128);
  let format;
  try { format = new Intl.DateTimeFormat('en-CA', {timeZone: value.timeZone, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit', hourCycle: 'h23'}); }
  catch { fail('Unknown time zone'); }
  for (const input of [value.start, value.end]) {
    const p = Object.fromEntries(format.formatToParts(new Date(instant(input))).map(p => [p.type, p.value]));
    if (`${p.year}-${p.month}-${p.day}T${p.hour}:${p.minute}:${p.second}` !== input.slice(0, 19)) fail('Offset does not match declared time zone');
  }
}
function declaration(d) {
  fields(d, ['id', 'kind', 'label', 'source', 'qualifiers', 'status', 'homeIds', 'window']);
  text(d.id, 128); text(d.label);
  if (!kinds.has(d.kind) || !statuses.has(d.status)) fail('Explicit declaration kind/status required');
  fields(d.source, ['label', 'reference']);
  for (const k of ['label', 'reference']) if (d.source[k] !== null) text(d.source[k], 2048);
  if (!Array.isArray(d.qualifiers) || d.qualifiers.length > 32) fail('Explicit qualifiers required');
  d.qualifiers.forEach(q => text(q));
  if (d.kind === 'carer') {
    if (d.homeIds !== null && (!Array.isArray(d.homeIds) || d.homeIds.length > 64 || new Set(d.homeIds).size !== d.homeIds.length)) fail('Explicit home scope required');
    d.homeIds?.forEach(id => text(id, 128));
  } else if ('homeIds' in d) fail('Home scopes belong to carer declarations');
  if (d.kind === 'fasting') window(d.window);
  else if ('window' in d) fail('Windows belong to fasting declarations');
}
function validate(value, accountId) {
  text(accountId, 128); fields(value, ['version', 'accountId', 'declarations', 'selection']);
  if (value.version !== 1 || value.accountId !== accountId || !Array.isArray(value.declarations) || value.declarations.length > 128) fail('Versioned same-account context required');
  const ids = new Set();
  for (const d of value.declarations) { declaration(d); if (ids.has(d.id)) fail('Duplicate declaration'); ids.add(d.id); }
  const homes = new Set(value.declarations.filter(d => d.kind === 'home').map(d => d.id));
  for (const d of value.declarations) if (d.kind === 'carer' && d.homeIds?.some(id => !homes.has(id))) fail('Unknown carer home scope');
  fields(value.selection, ['homeId', 'carerId']);
  const find = (id, kind) => value.declarations.find(d => d.id === id && d.kind === kind && d.status === 'declared');
  const {homeId, carerId} = value.selection;
  if (homeId !== null && !find(homeId, 'home')) fail('Selected home unavailable');
  if (carerId !== null) { const carer = find(carerId, 'carer'); if (!homeId || !carer || !carer.homeIds?.includes(homeId)) fail('Selected carer unavailable for home'); }
  return value;
}
export function validateMealContext(value, accountId) { return freeze(validate(capture(value), accountId)); }
export function emptyMealContext(accountId) { return validateMealContext({version: 1, accountId, declarations: [], selection: {homeId: null, carerId: null}}, accountId); }
export function transitionMealContext(value, {accountId, actorId, permit} = {}, action) {
  const next = capture(validateMealContext(value, accountId)), intent = freeze(capture(action));
  text(actorId, 128); if (typeof permit !== 'function') fail('Authoritative permission callback required');
  fields(intent, ['type', 'declaration', 'id', 'homeId', 'carerId']);
  if (!['declare', 'withdraw', 'choose'].includes(intent.type)) fail('Unknown context action');
  fields(intent, intent.type === 'declare' ? ['type', 'declaration'] : intent.type === 'withdraw' ? ['type', 'id'] : ['type', 'homeId', 'carerId']);
  const homeId = intent.type === 'choose' ? intent.homeId : next.selection.homeId;
  const carerId = intent.type === 'choose' ? intent.carerId : next.selection.carerId;
  // Labels and declaration IDs are never authenticated rights or grants.
  if (permit(freeze({accountId, actorId, action: intent, homeId, carerId}))?.allowed !== true) fail('Context choice not authorized');
  if (intent.type === 'declare') {
    declaration(intent.declaration);
    const index = next.declarations.findIndex(d => d.id === intent.declaration.id);
    if (index >= 0) { if (next.declarations[index].kind !== intent.declaration.kind) fail('Declaration kind cannot change'); next.declarations[index] = capture(intent.declaration); }
    else next.declarations.push(capture(intent.declaration));
  } else if (intent.type === 'withdraw') {
    text(intent.id, 128); const d = next.declarations.find(d => d.id === intent.id);
    if (!d) fail('Unknown declaration'); d.status = 'withdrawn';
  } else next.selection = {homeId: intent.homeId, carerId: intent.carerId};
  if (intent.type !== 'choose') {
    const home = next.declarations.find(d => d.id === next.selection.homeId && d.kind === 'home' && d.status === 'declared');
    if (!home) next.selection = {homeId: null, carerId: null};
    const carer = next.declarations.find(d => d.id === next.selection.carerId && d.kind === 'carer' && d.status === 'declared' && d.homeIds?.includes(next.selection.homeId));
    if (!carer) next.selection.carerId = null;
  }
  return freeze(validate(next, accountId));
}
export function mealContextAt(value, {accountId, at} = {}) {
  const context = validateMealContext(value, accountId), now = instant(at);
  return freeze({selection: context.selection, declarations: context.declarations, fasting: context.declarations.filter(d => d.kind === 'fasting').map(d => ({id: d.id, label: d.label, source: d.source, qualifiers: d.qualifiers,
    status: d.status !== 'declared' ? d.status : d.window === null ? 'unknown' : now >= instant(d.window.start) && now < instant(d.window.end) ? 'inside-declared-window' : 'outside-declared-window'}))});
}
