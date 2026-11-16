import {validateState} from './state.mjs';

const FIELDS = ['likes', 'textures', 'spice'];
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);

// This boundary accepts parsed JSON, not proxies or class instances.
function dataRecord(value, allowed) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw Error('Invalid preference record.');
  const descriptors = Object.getOwnPropertyDescriptors(value), out = {};
  for (const key of Reflect.ownKeys(descriptors)) {
    const d = descriptors[key];
    if (typeof key !== 'string' || !allowed.includes(key) || !own(d, 'value') || !d.enumerable) throw Error('Invalid preference field.');
    out[key] = d.value;
  }
  return out;
}
function id(value) {
  if (typeof value !== 'string' || !value.trim() || value.length > 200) throw Error('Explicit preference scope required.');
  return value;
}
function terms(value, max = 32) {
  if (!Array.isArray(value) || Object.getPrototypeOf(value) !== Array.prototype) throw Error('Invalid preference terms.');
  const descriptors = Object.getOwnPropertyDescriptors(value), length = descriptors.length.value;
  if (length > max || Reflect.ownKeys(descriptors).length !== length + 1) throw Error('Invalid preference terms.');
  const result = [];
  for (let i = 0; i < length; i++) {
    const d = descriptors[String(i)];
    if (!d || !own(d, 'value') || !d.enumerable || typeof d.value !== 'string' || !d.value.trim() || d.value.length > 100) throw Error('Invalid preference term.');
    result.push(d.value);
  }
  return result;
}

export function validateMealPreferences(value, accountId, memberId) {
  const expected = {accountId: id(accountId), memberId: id(memberId)};
  const state = dataRecord(value, ['version', 'scope', ...FIELDS]);
  const scope = dataRecord(state.scope, ['accountId', 'memberId']);
  if (state.version !== 1 || scope.accountId !== expected.accountId || scope.memberId !== expected.memberId) throw Error('Preference scope/version mismatch.');
  const likes = terms(state.likes), textures = terms(state.textures), spice = state.spice;
  if (spice !== null && !['none', 'mild', 'medium', 'hot'].includes(spice)) throw Error('Invalid spice preference.');
  return {version: 1, scope: expected, likes, textures, spice};
}

// Use for private account PUT and restore only. accountId comes from verifiedUser,
// never a submitted profile. Existing validator continues to own every other field.
export function validateAccountMealState(value, accountId) {
  id(accountId);
  const preferences = new Map();
  const seen = new Set();
  for (const member of value?.profile?.members || []) {
    if (seen.has(member.id)) throw Error('Duplicate household member ID.');
    seen.add(member.id);
    const d = Object.getOwnPropertyDescriptor(member, 'mealPreferences');
    if (d) {
      if (!own(d, 'value') || !d.enumerable) throw Error('Invalid stored preference field.');
      preferences.set(member.id, validateMealPreferences(d.value, accountId, member.id));
    }
  }
  const state = validateState(value);
  if (state.profile.members) state.profile.members = state.profile.members.map(member =>
    preferences.has(member.id) ? {...member, mealPreferences: preferences.get(member.id)} : member);
  return state;
}

// Consumer for the existing household member editor/reset and private account save.
// Caller must establish authenticated account/member custody and consent first.
export function updateAccountMealPreferences(value, context, action) {
  const c = dataRecord(context, ['accountId', 'memberId', 'consent']);
  if (c.consent !== true) throw Error('Explicit preference consent required.');
  id(c.memberId);
  const state = validateAccountMealState(value, c.accountId);
  const member = state.profile.members?.find(m => m.id === c.memberId);
  if (!member) throw Error('Household member not found.');
  const command = dataRecord(action, ['type', 'patch', 'fields']);
  const current = member.mealPreferences || {version: 1, scope: {accountId: c.accountId, memberId: c.memberId}, likes: [], textures: [], spice: null};
  let patch;
  if (command.type === 'edit' && !own(command, 'fields')) {
    patch = dataRecord(command.patch, FIELDS);
  } else if (command.type === 'reset' && !own(command, 'patch')) {
    const fields = own(command, 'fields') ? terms(command.fields, 3) : FIELDS;
    if (fields.some(field => !FIELDS.includes(field))) throw Error('Invalid preference reset field.');
    patch = Object.fromEntries(fields.map(field => [field, field === 'spice' ? null : []]));
  } else throw Error('Invalid preference action.');
  const next = validateMealPreferences({...current, ...patch}, c.accountId, c.memberId);
  state.profile.members = state.profile.members.map(m => m.id === c.memberId ? {...m, mealPreferences: next} : m);
  return state;
}

// Read boundary only: validate stored preference custody without projecting or
// normalizing unrelated legacy state. The caller must not persist this read.
export function validateStoredAccountMealPreferences(value, accountId) {
  id(accountId);
  const members = value?.profile?.members;
  if (!Array.isArray(members)) return value;
  const scoped = members.filter(member => member && own(member, 'mealPreferences'));
  if (!scoped.length) return value;
  const seen = new Set();
  for (const member of members) {
    if (!member) continue;
    if (seen.has(member.id)) throw Error('Duplicate household member ID.');
    seen.add(member.id);
  }
  for (const member of scoped) {
    const d = Object.getOwnPropertyDescriptor(member, 'mealPreferences');
    if (!own(d, 'value') || !d.enumerable) throw Error('Invalid stored preference field.');
    validateMealPreferences(d.value, accountId, member.id);
  }
  return value;
}
