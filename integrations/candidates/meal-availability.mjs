// Pure DEV slice: availability within a caller-supplied inventory snapshot only.
// Input: {requirements:[{ingredientId,amount,unit,basis}], inventory:[same + lotId?]}.
// IDs, units and basis are exact opaque strings; null/absent fields are unknown.
// Amounts are null/absent or finite nonnegative numbers. Malformed data throws.
// This does not validate source identity, recipe admission, nutrition or safety.
const MAX_ROWS = 1000;
const SCALE = 340; // Covers every finite JS number's shortest decimal spelling.
const MAX_UNITS = ((1n << 53n) - 1n) * (1n << 971n) * 10n ** BigInt(SCALE);

function record(value, allowed) {
  if (!value || typeof value !== 'object' || Array.isArray(value) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(value))) throw new TypeError('Plain own-data record required');
  const result = Object.create(null);
  for (const key of Reflect.ownKeys(value)) {
    const d = Object.getOwnPropertyDescriptor(value, key);
    if (!allowed.includes(key) || !d.enumerable || !Object.hasOwn(d, 'value')) throw new TypeError('Unexpected field or accessor');
    result[key] = d.value;
  }
  return result;
}

function text(value) {
  if (value === null || value === undefined) return null;
  if (typeof value !== 'string' || !value || value.trim() !== value || value.length > 500) throw new TypeError('Nonempty exact identifier required');
  return value;
}

function rows(value, inventory = false) {
  if (!Array.isArray(value) || value.length > MAX_ROWS ||
      Reflect.ownKeys(value).length !== value.length + 1) throw new TypeError('Bounded dense array required');
  const result = [];
  for (let i = 0; i < value.length; i++) {
    const d = Object.getOwnPropertyDescriptor(value, String(i));
    if (!d || !d.enumerable || !Object.hasOwn(d, 'value')) throw new TypeError('Own-data array entries required');
    const r = record(d.value, inventory ? ['ingredientId', 'amount', 'unit', 'basis', 'lotId'] : ['ingredientId', 'amount', 'unit', 'basis']);
    if (r.amount != null && (typeof r.amount !== 'number' || !Number.isFinite(r.amount) || r.amount < 0)) throw new TypeError('Finite nonnegative amount required');
    result.push({ingredientId:text(r.ingredientId), amount:r.amount ?? null, unit:text(r.unit), basis:text(r.basis),
      ...(inventory ? {lotId:text(r.lotId)} : {})});
  }
  return result;
}

// Compare/add the supplied number spellings exactly, avoiding 0.1+0.2 deficits.
// No tolerance, unit conversion or rounding is used in the decision.
function units(number) {
  const [mantissa, exponent = '0'] = String(number).split('e');
  const [whole, fraction = ''] = mantissa.split('.');
  return BigInt(whole + fraction) * 10n ** BigInt(SCALE + Number(exponent) - fraction.length);
}
const amount = value => {
  // An out-of-domain exact sum can round down to finite MAX_VALUE.
  if (value > MAX_UNITS) return null;
  const n = Number(`${value}e-${SCALE}`);
  return Number.isFinite(n) && (n !== 0 || value === 0n) ? n : null;
};
const key = r => JSON.stringify([r.ingredientId, r.unit, r.basis]);
const identified = r => r.ingredientId !== null && r.unit !== null && r.basis !== null;

/** Unknowns dominate the overall status; evidenced deficits stay visible.
 * Requirement evidence refers to the combined demand for its exact ID/unit/basis,
 * so duplicates cannot reuse the same stock. Output rows keep request order;
 * deficit ingredients sort by exact ID. Caller inputs are never retained/mutated.
 * Reported sums use JS numbers; overflow/underflow withholds unrepresentable amounts.
 */
export function mealAvailability(input) {
  const data = record(input, ['requirements', 'inventory']);
  const requirements = rows(data.requirements), inventory = rows(data.inventory, true);
  if (!requirements.length) throw new TypeError('At least one requirement required');
  const lotIds = new Set();
  for (const lot of inventory) if (lot.lotId !== null) {
    if (lotIds.has(lot.lotId)) throw new TypeError('Duplicate lotId');
    lotIds.add(lot.lotId);
  }
  const groups = new Map();
  requirements.forEach((r, index) => {
    if (!identified(r)) return;
    const k = key(r), g = groups.get(k) ?? {ingredientId:r.ingredientId, unit:r.unit, basis:r.basis, required:0n, unknownAmount:false, indices:[]};
    g.indices.push(index);
    if (r.amount === null) g.unknownAmount = true;
    else g.required += units(r.amount);
    groups.set(k, g);
  });
  const decisions = new Map();
  for (const [k, g] of groups) {
    let available = 0n, uncertain = false;
    const inventoryIndices = [];
    inventory.forEach((lot, index) => {
      if (lot.ingredientId !== null && lot.ingredientId !== g.ingredientId) return;
      if (!identified(lot) || key(lot) !== k || lot.amount === null) {uncertain = true; return;}
      available += units(lot.amount); inventoryIndices.push(index);
    });
    let status, reason;
    const requiredAmount = amount(g.required), availableAmount = amount(available),
      deficitAmount = amount(g.required > available ? g.required - available : 0n);
    if (g.unknownAmount) {status = 'unknown'; reason = 'unknown-requirement-amount';}
    else if (requiredAmount === null || availableAmount === null || deficitAmount === null) {status = 'unknown'; reason = 'unrepresentable-amount';}
    else if (available >= g.required) {status = 'ready-now'; reason = 'known-compatible-stock-sufficient';}
    else if (uncertain) {status = 'unknown'; reason = 'unresolved-inventory-identity-amount-unit-or-basis';}
    else {status = 'missing-ingredients'; reason = 'known-compatible-stock-insufficient';}
    decisions.set(k, {status, reason, evidence:{groupRequired:g.unknownAmount ? null : requiredAmount,
      knownAvailable:availableAmount, deficit:status === 'unknown' ? null : deficitAmount,
      requirementIndices:[...g.indices], inventoryIndices}});
  }
  // A requirement with unknown identity/unit/basis may consume any otherwise
  // compatible stock. Withhold known groups too, preventing duplicate allocation.
  const unboundRequirements = requirements.some(r => !identified(r));
  const evidence = requirements.map((r, index) => {
    const decision = !identified(r) ? {status:'unknown', reason:'missing-requirement-identity-unit-or-basis', evidence:null}
      : unboundRequirements ? {status:'unknown', reason:'unresolved-other-requirement', evidence:null}
        : decisions.get(key(r));
    return {index, ...r, ...structuredClone(decision)};
  });
  const deficits = new Map();
  if (!unboundRequirements) for (const [k, g] of groups) {
    const decision = decisions.get(k);
    if (decision.status !== 'missing-ingredients') continue;
    const deficit = deficits.get(g.ingredientId) ?? {ingredientId:g.ingredientId, quantities:[]};
    deficit.quantities.push({unit:g.unit, basis:g.basis, ...structuredClone(decision.evidence)});
    deficits.set(g.ingredientId, deficit);
  }
  const hasUnknown = evidence.some(r => r.status === 'unknown');
  const missing = [...deficits.values()].sort((a, b) => a.ingredientId < b.ingredientId ? -1 : a.ingredientId > b.ingredientId ? 1 : 0);
  return {version:'meal-availability/1', status:hasUnknown ? 'unknown' : missing.length ? 'missing-ingredients' : 'ready-now',
    oneExtraItem:!hasUnknown && missing.length === 1, requirements:evidence, deficits:missing,
    scope:'Caller-supplied snapshot and exact identities/units/basis only. No recipe admission, conversion, nutrition or allergy safety claim.'};
}
