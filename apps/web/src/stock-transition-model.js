// Caller-owned account envelope; no storage, transport or safety-date inference.
import {validateLot} from './model.js';

const actions = new Set(['opened', 'frozen', 'thawed', 'decanted']);
const text = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 100;
const instant = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) &&
  Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value;
const canonical = value => JSON.stringify(value, function (key, item) {
  return item && typeof item === 'object' && !Array.isArray(item)
    ? Object.fromEntries(Object.keys(item).sort().map(k => [k, item[k]])) : item;
});

/** Record an explicitly confirmed whole-lot observation against a reviewed snapshot.
 * state = {accountId, inventory, events}; caller must authenticate/authorize accountId.
 * command = {accountId, lotId, expectedLot, expectedEventCount, eventId, action,
 *            confirmed:true, containerId?}; clock returns a canonical UTC timestamp.
 */
export function transitionStock(state, command, {clock} = {}) {
  if (!state || !command || !text(state.accountId) || command.accountId !== state.accountId)
    throw Error('Account scope mismatch.');
  if (!Array.isArray(state.inventory) || state.inventory.length > 10000 ||
      !Array.isArray(state.events) || state.events.length >= 1000)
    throw Error('Invalid or full transition journal.');
  const ids = new Set();
  for (const lot of state.inventory) {
    if (!text(lot.id) || ids.has(lot.id)) throw Error('Invalid or duplicate lot identity.');
    validateLot(lot);
    ids.add(lot.id);
  }
  const eventIds = new Set();
  for (const event of state.events) {
    if (!text(event.id) || eventIds.has(event.id) || event.accountId !== state.accountId ||
        !text(event.lotId) || !actions.has(event.action) || !instant(event.at) ||
        (event.action === 'decanted' && !text(event.containerId)))
      throw Error('Invalid transition journal.');
    eventIds.add(event.id);
  }
  if (command.confirmed !== true || !actions.has(command.action) || !text(command.eventId) ||
      eventIds.has(command.eventId)) throw Error('Confirm a new supported transition.');
  const lot = state.inventory.find(item => item.id === command.lotId);
  if (!lot || lot.quantity <= 0 || canonical(lot) !== canonical(command.expectedLot) ||
      command.expectedEventCount !== state.events.length)
    throw Error('Stock or journal changed; review again.');
  const prior = state.events.filter(event => event.lotId === lot.id);
  const thermal = prior.filter(event => ['frozen', 'thawed'].includes(event.action)).at(-1)?.action;
  if (command.action === 'thawed' && thermal !== 'frozen')
    throw Error('No recorded frozen state; review source history.');
  if ((command.action === 'frozen' && thermal === 'frozen') ||
      (command.action === 'opened' && prior.some(event => event.action === 'opened')))
    throw Error('Transition already recorded.');
  if (command.action === 'decanted' && !text(command.containerId))
    throw Error('Explicit destination container required.');
  if (typeof clock !== 'function') throw Error('Observation clock required.');
  const at = clock();
  if (!instant(at)) throw Error('Invalid observation timestamp.');
  const last = prior.at(-1);
  if (last && at < last.at) throw Error('Observation precedes recorded history.');
  const event = {id: command.eventId, accountId: state.accountId, lotId: lot.id,
    action: command.action, at};
  if (command.action === 'decanted') event.containerId = command.containerId;
  return {...structuredClone(state), events: [...structuredClone(state.events), event]};
}
