// Transport-neutral server consumer. No route, schema, authentication issuer or
// D1 transaction implementation is installed here; owners 02/04 supply those.
export class LotOperationError extends Error {
  constructor(code, status = 400) { super(code); this.status = status; }
}
const fail = (code, status) => { throw new LotOperationError(code, status); };
const id = value => typeof value === 'string' && /^[A-Za-z0-9:_-]{1,100}$/.test(value);

// Bound JSON data only, without invoking accessors or coercion hooks.
function snapshot(value, depth = 0) {
  if (depth > 32) fail('JSON_TOO_DEEP');
  if (value === null || typeof value === 'string' || typeof value === 'boolean') return value;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (!value || typeof value !== 'object') fail('JSON_REQUIRED');
  const array = Array.isArray(value);
  if (!array && Object.getPrototypeOf(value) !== Object.prototype) fail('PLAIN_JSON_REQUIRED');
  const descriptors = Object.getOwnPropertyDescriptors(value);
  if (Object.values(descriptors).some(d => !('value' in d))) fail('JSON_ACCESSOR');
  if (Reflect.ownKeys(value).some(k => typeof k !== 'string')) fail('JSON_SYMBOL');
  const keys = Object.keys(value);
  if (array && (keys.length !== value.length || keys.some((k, i) => k !== String(i)))) fail('DENSE_ARRAY_REQUIRED');
  if (array && Reflect.ownKeys(value).length !== keys.length + 1) fail('PLAIN_ARRAY_REQUIRED');
  if (!array && Reflect.ownKeys(value).length !== keys.length) fail('ENUMERABLE_JSON_REQUIRED');
  return array ? keys.map(k => snapshot(descriptors[k].value, depth + 1)) :
    Object.fromEntries(keys.sort().map(k => [k, snapshot(descriptors[k].value, depth + 1)]));
}
const canonical = value => JSON.stringify(snapshot(value));
const timestamp = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/.test(value) &&
  Number.isFinite(Date.parse(value)) && new Date(value).toISOString() === value;

// Nine decimal places, same observed unit only. No floating-point subtraction,
// density, count-to-mass conversion or implicit precision rounding.
function scaled(value) {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1e9) fail('QUANTITY_OUT_OF_RANGE');
  const [digits, exponent = '0'] = String(value).split('e');
  const [whole, fraction = ''] = digits.split('.');
  const shift = 9 + Number(exponent) - fraction.length;
  if (shift < 0) fail('QUANTITY_PRECISION_UNSUPPORTED');
  return BigInt(whole + fraction) * 10n ** BigInt(shift);
}
function unscaled(value) {
  const text = value.toString().padStart(10, '0');
  const result = Number(text.slice(0, -9) + '.' + text.slice(-9));
  if (scaled(result) !== value) fail('QUANTITY_NOT_REPRESENTABLE');
  return result;
}
function commandSnapshot(input) {
  const command = snapshot(input);
  if (!command || !id(command.operationId) || !id(command.lotId) ||
      !['consume', 'decant'].includes(command.action) || command.confirmed !== true ||
      !Number.isSafeInteger(command.expectedVersion) || command.expectedVersion < 1 ||
      command.expectedVersion >= Number.MAX_SAFE_INTEGER || !command.expectedLot)
    fail('INVALID_COMMAND');
  const allowed = ['operationId', 'lotId', 'action', 'confirmed', 'expectedVersion', 'expectedLot', 'amount', 'destination'];
  if (Object.keys(command).some(k => !allowed.includes(k))) fail('UNSUPPORTED_COMMAND_FIELD');
  if (!command.amount || !['g', 'ml', 'count'].includes(command.amount.unit) || scaled(command.amount.value) <= 0n)
    fail('MEASURED_AMOUNT_REQUIRED');
  if (!command.amount.provenance || !id(command.amount.provenance.sourceId) ||
      !['user-measured', 'label-measured'].includes(command.amount.provenance.method))
    fail('AMOUNT_PROVENANCE_REQUIRED');
  if (command.action === 'consume' && command.destination !== undefined) fail('UNEXPECTED_DESTINATION');
  if (command.action === 'decant' && (!command.destination || !id(command.destination.id) ||
      !id(command.destination.containerId) || !command.destination.location ||
      !['area', 'shelf'].every(k => typeof command.destination.location[k] === 'string' &&
        command.destination.location[k].trim() && command.destination.location[k].length <= 60)))
    fail('DESTINATION_REQUIRED');
  if (new TextEncoder().encode(JSON.stringify(command)).length > 65536) fail('COMMAND_TOO_LARGE', 413);
  return command;
}

/** Physical stock change only; consumption here never computes nutritional intake.
 * Exact source snapshot and source unit are required. Existing metadata is retained.
 * Cooked lots require owner 19's batch/serving reconciliation and are rejected.
 */
export function reduceLotConsumption(input, inputCommand, observedAt) {
  const state = snapshot(input), command = commandSnapshot(inputCommand);
  if (!timestamp(observedAt)) fail('CLOCK_UNAVAILABLE', 503);
  if (!state || !Array.isArray(state.inventory) || state.inventory.length > 10000) fail('INVALID_INVENTORY');
  const ids = new Set();
  for (const lot of state.inventory) {
    if (!lot || !id(lot.id) || ids.has(lot.id) || !['g', 'ml', 'count'].includes(lot.unit)) fail('INVALID_LOT_IDENTITY');
    scaled(lot.quantity); ids.add(lot.id);
  }
  const lot = state.inventory.find(item => item.id === command.lotId);
  if (!lot || canonical(lot) !== canonical(command.expectedLot)) fail('LOT_CHANGED', 409);
  if (lot.cookBatchId) fail('COOKED_BATCH_RECONCILIATION_REQUIRED', 409);
  if (lot.unit !== command.amount.unit) fail('UNIT_MISMATCH');
  const before = scaled(lot.quantity), amount = scaled(command.amount.value);
  if (amount > before) fail('INSUFFICIENT_STOCK', 409);
  const remaining = unscaled(before - amount);
  if (command.action === 'decant' && ids.has(command.destination.id)) fail('DESTINATION_ID_EXISTS', 409);
  if (command.action === 'decant' && remaining > 0 && state.inventory.length === 10000) fail('INVENTORY_FULL', 409);
  const observation = {operationId:command.operationId, action:command.action, at:observedAt,
    sourceLotId:lot.id, before:lot.quantity, remaining, amount:command.amount};
  const inventory = state.inventory.flatMap(item => item.id !== lot.id ? [item] : remaining === 0 ? [] :
    [{...item, quantity:remaining, quantityObservation21:observation}]);
  if (command.action === 'decant') {
    inventory.push({...lot, id:command.destination.id, quantity:command.amount.value,
      location:command.destination.location, quantityObservation21:observation,
      lotLineage21:{sourceLotId:lot.id, rootLotId:lot.lotLineage21?.rootLotId ?? lot.id,
        sourceQuantity:lot.quantity, sourceUnit:lot.unit, sourceAmountBasis:lot.amountBasis ?? null,
        sourceUnitProvenance:lot.unitProvenance ?? null, containerId:command.destination.containerId}});
  }
  const next = {...state, inventory};
  if (new TextEncoder().encode(JSON.stringify(next)).length > 2000000) fail('STATE_TOO_LARGE', 413);
  // The immutable receipt keeps exhausted source evidence. Do not nest that full
  // snapshot in every remaining lot's observation and grow it on each mutation.
  return {state:next, observation:{...observation, sourceSnapshot:lot},
    destinationLotId:command.destination?.id ?? null};
}

/** Owner 04 must bind transact to fresh authenticated subject + protected session,
 * admitting/rechecking revocation inside the same transaction as state/ledger writes.
 * tx: admit(), state(), operation(id), write(version,json,at), record(id,digest,result).
 * state(): {revision,state_json}; operation(): {digest,result_json}.
 * SQL and schema authority remain with the persistence owner.
 */
export function createLotConsumptionConsumer({authenticate, authorizeRequest, transact, clock} = {}) {
  if ([authenticate, authorizeRequest, transact, clock].some(fn => typeof fn !== 'function'))
    throw Error('Trusted request and transaction hooks required');
  return async function consume(request, input) {
    // Capture reviewed inputs before asynchronous hooks can mutate them.
    const command = commandSnapshot(input);
    const user = await authenticate(request);
    if (!user || typeof user.id !== 'string' || !user.id.trim() || user.id.length >= 200) fail('UNAUTHENTICATED', 401);
    const accountId = user.id;
    if (await authorizeRequest(request, {id:accountId}) !== true) fail('REQUEST_DENIED', 403);
    const at = clock(); if (!timestamp(at)) fail('CLOCK_UNAVAILABLE', 503);
    const digest = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',
      new TextEncoder().encode(canonical({accountId, resource:'lot-consumption/1', command})))),
      b => b.toString(16).padStart(2, '0')).join('');
    return await transact({request, accountId}, tx => {
      if (tx.admit() !== true) fail('SESSION_DENIED', 403);
      const prior = tx.operation(command.operationId);
      if (prior) {
        if (prior.digest !== digest) fail('OPERATION_ID_REUSED', 409);
        return JSON.parse(prior.result_json);
      }
      const current = tx.state();
      if (!current || !Number.isSafeInteger(current.revision) || current.revision < 1) fail('STATE_UNAVAILABLE', 409);
      if (current.revision !== command.expectedVersion) fail('VERSION_CONFLICT', 409);
      const result = reduceLotConsumption(JSON.parse(current.state_json), command, at);
      const receipt = {status:'committed', acknowledged:true, accountId,
        operationId:command.operationId, revision:current.revision + 1,
        observation:result.observation, destinationLotId:result.destinationLotId, digest};
      // State and immutable replay receipt must both commit, or both roll back.
      tx.write(current.revision, JSON.stringify(result.state), at);
      tx.record(command.operationId, digest, receipt);
      return receipt;
    });
  };
}
