import {mealAvailability} from './meal-availability.mjs';

// DEV producer contract for matchRecipeStock's source-batch row shape.
// No name/alias identity, serving scale, unit conversion or amountBasis inference.
// This adapter is not wired into the live matcher or persistence producers.
function field(row, key) {
  if (!row || typeof row !== 'object' || Array.isArray(row) ||
      ![Object.prototype, null].includes(Object.getPrototypeOf(row))) throw new TypeError('Plain row required');
  const d = Object.getOwnPropertyDescriptor(row, key);
  if (d && !Object.hasOwn(d, 'value')) throw new TypeError('Own-data field required');
  return d?.value;
}

function rows(value) {
  if (!Array.isArray(value) || value.length > 1000 ||
      Reflect.ownKeys(value).length !== value.length + 1) throw new TypeError('Bounded dense rows required');
  return Array.from({length:value.length}, (_, i) => {
    const d = Object.getOwnPropertyDescriptor(value, String(i));
    if (!d || !Object.hasOwn(d, 'value')) throw new TypeError('Own-data rows required');
    return d.value;
  });
}

export function matchRecipeStockInput(recipe, inventory, {today} = {}) {
  if (typeof today !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(today) ||
      !Number.isFinite(Date.parse(today)) || new Date(today).toISOString().slice(0, 10) !== today) throw new TypeError('Explicit valid snapshot date required');
  const complete = field(recipe, 'ingredientExtractionComplete');
  if (complete != null && typeof complete !== 'boolean') throw new TypeError('Boolean ingredient extraction completeness flag required');
  if (complete === false ||
      field(recipe, 'publisher') === 'smithsonian-archive' ||
      field(recipe, 'sourcePublisher') === 'smithsonian-archive') throw new TypeError('Complete ingredient extraction required');
  const project = (row, amountKey) => ({ingredientId:field(row, 'ingredientId') ?? null,
    amount:field(row, amountKey) ?? null, unit:field(row, 'unit') ?? null, basis:field(row, 'basis') ?? null});
  const requirements = rows(field(recipe, 'ingredients')).filter(row => {
    const optional = field(row, 'optional');
    if (optional != null && typeof optional !== 'boolean') throw new TypeError('Boolean optional flag required');
    return optional !== true;
  }).map(row => project(row, 'amount'));
  const stock = rows(inventory).filter(row => {
    const review = field(row, 'needsReview'), expires = field(row, 'expires');
    if (review != null && typeof review !== 'boolean') throw new TypeError('Boolean review flag required');
    if (expires != null && (typeof expires !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(expires) ||
        !Number.isFinite(Date.parse(expires)) || new Date(expires).toISOString().slice(0, 10) !== expires)) throw new TypeError('Valid expiry date required');
    return review !== true && (expires == null || expires >= today);
  }).map(row => ({...project(row, 'quantity'), lotId:field(row, 'id') ?? null}));
  const input = {requirements, inventory:stock};
  // Reuse the reviewed helper's exact field/amount validation; never coerce bad
  // evidence to zero or unknown. Validation computes no persistent side effect.
  mealAvailability(input);
  return input;
}
