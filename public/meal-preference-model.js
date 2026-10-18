// Explicit taste preferences only. No safety, suitability, or persistence decision.
const FIELDS = ['likes', 'textures', 'spice'];
const SPICE = ['none', 'mild', 'medium', 'hot'];
const own = (value, key) => Object.prototype.hasOwnProperty.call(value, key);

// Capture plain JSON data through descriptors, never getters or array hooks.
// Proxies are outside this API's contract (reflection can execute proxy traps).
function plainData(value, ancestors = new Set()) {
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value || typeof value !== 'object' || ancestors.has(value)) throw new TypeError('Expected acyclic plain JSON data');
  const array = Array.isArray(value), prototype = Object.getPrototypeOf(value);
  if (array ? prototype !== Array.prototype : prototype !== Object.prototype && prototype !== null) {
    throw new TypeError('Expected plain JSON data');
  }
  const descriptors = Object.getOwnPropertyDescriptors(value);
  const keys = Reflect.ownKeys(descriptors);
  for (const key of keys) {
    const descriptor = descriptors[key];
    if (typeof key !== 'string' || !own(descriptor, 'value') || (!descriptor.enumerable && !(array && key === 'length'))) {
      throw new TypeError('Accessors, symbols and hidden fields are not plain JSON data');
    }
  }
  ancestors.add(value);
  try {
    if (array) {
      const length = descriptors.length.value;
      if (keys.length !== length + 1) throw new TypeError('Expected a dense ordinary array');
      const result = [];
      for (let index = 0; index < length; index++) {
        const descriptor = descriptors[String(index)];
        if (!descriptor) throw new TypeError('Expected a dense ordinary array');
        result.push(plainData(descriptor.value, ancestors));
      }
      return result;
    }
    return Object.fromEntries(keys.map(key => [key, plainData(descriptors[key].value, ancestors)]));
  } finally {
    ancestors.delete(value);
  }
}
function record(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new TypeError('Expected a record');
  return plainData(value);
}
function identity(value) {
  if (typeof value !== 'string' || !value.trim() || value.length > 200) throw new TypeError('Explicit scope required');
  return value; // Never normalize account/member identifiers.
}
function scopeOf(scope) {
  scope = record(scope);
  return {accountId: identity(scope.accountId), memberId: identity(scope.memberId)};
}
function list(value) {
  if (!Array.isArray(value) || value.length > 32 || value.some(x => typeof x !== 'string' || !x.trim() || x.length > 100)) {
    throw new TypeError('Expected at most 32 explicit terms of 1–100 characters');
  }
  return [...value]; // Retain entered terms; no ingredient/safety identity inference.
}
function values(value) {
  value = record(value);
  const likes = list(value.likes), textures = list(value.textures);
  const spice = value.spice;
  if (spice !== null && !SPICE.includes(spice)) throw new TypeError('Invalid spice preference');
  return {likes, textures, spice};
}
function checked(state, scope) {
  state = record(state);
  const expected = scopeOf(scope), actual = scopeOf(state.scope);
  if (state.version !== 1 || actual.accountId !== expected.accountId || actual.memberId !== expected.memberId) {
    throw new TypeError('Preference scope/version mismatch');
  }
  if (Object.keys(state).some(key => !['version', 'scope', ...FIELDS].includes(key))) throw new TypeError('Unexpected preference field');
  return {version: 1, scope: actual, ...values(state)};
}

export function createMealPreferences(scope) {
  return {version: 1, scope: scopeOf(scope), likes: [], textures: [], spice: null};
}

export function setMealPreferences(state, scope, patch) {
  const current = checked(state, scope);
  patch = record(patch);
  if (Object.keys(patch).some(key => !FIELDS.includes(key))) throw new TypeError('Only explicit taste fields may change');
  const next = Object.fromEntries(FIELDS.map(key => [key, own(patch, key) ? patch[key] : current[key]]));
  return {...current, ...values(next)};
}

export function resetMealPreferences(state, scope, fields = FIELDS) {
  const current = checked(state, scope);
  fields = plainData(fields);
  if (!Array.isArray(fields) || fields.length > FIELDS.length || fields.some(key => !FIELDS.includes(key))) {
    throw new TypeError('Invalid reset fields');
  }
  const empty = createMealPreferences(scope);
  return setMealPreferences(current, scope, Object.fromEntries(fields.map(key => [key, empty[key]])));
}

// Adoption adapter: the caller owns authentication, consent and persistence.
// It must gate selection with P0-07 independently of these taste values.
export function withMealPreferences(member, state, scope) {
  member = record(member);
  const preferences = checked(state, scope);
  if (member.id !== preferences.scope.memberId) throw new TypeError('Member mismatch');
  return {...structuredClone(member), mealPreferences: preferences};
}
