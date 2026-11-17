import {eligibleStock, normalize} from './model.js';

// These are computation limits, not serving, nutrition or food-safety advice.
const MAX_STATES = 20000;
const MAX_MEALS = 10000;
const EXACT_QUANTITY = 1000000;
const DAY = 86400000;
const units = new Set(['g', 'ml', 'count']);

// Fallback witnesses use the canonical decimal spelling of each finite Number,
// rather than tolerances or repeatedly rounded subtraction. No fractions escape
// this private computation. In the exact integer domain the two models coincide.
function fraction(n, d = 1n) {
  let a = n, b = d;
  while (b) [a, b] = [b, a % b];
  return {n: n / a, d: d / a};
}
function decimal(value) {
  const [mantissa, exponent = '0'] = value.toString().toLowerCase().split('e');
  const decimals = (mantissa.split('.')[1] || '').length;
  const power = decimals - Number(exponent);
  const numerator = BigInt(mantissa.replace('.', ''));
  return power >= 0 ? fraction(numerator, 10n ** BigInt(power)) :
    fraction(numerator * 10n ** BigInt(-power));
}
const add = (a, b) => fraction(a.n * b.d + b.n * a.d, a.d * b.d);
const subtract = (a, b) => fraction(a.n * b.d - b.n * a.d, a.d * b.d);
const compare = (a, b) => a.n * b.d - b.n * a.d;
const zero = {n: 0n, d: 1n};

function result(sequence, mealsPerDay, optimal, reason, proof = 'none', statesExplored = 0) {
  return {
    meals: sequence.length,
    days: Number.isFinite(mealsPerDay) && mealsPerDay > 0 ? Math.floor(sequence.length / mealsPerDay) : 0,
    sequence,
    limited: sequence.length === MAX_MEALS,
    optimal,
    optimization: {scope: 'measured_menu_count', reason, proof, statesExplored},
  };
}

function isoDay(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const time = Date.parse(value + 'T12:00:00Z');
  return Number.isFinite(time) && new Date(time).toISOString().slice(0, 10) === value ? time : null;
}

function mealDay(start, position, mealsPerDay) {
  const offset = Math.floor(position / mealsPerDay);
  const time = start + offset * DAY;
  if (!Number.isSafeInteger(offset) || !Number.isFinite(time) || Math.abs(time) > 8640000000000000) return null;
  const day = new Date(time).toISOString().slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(day) ? day : null;
}

const exactQuantity = value => Number.isSafeInteger(value) && value > 0 && value <= EXACT_QUANTITY;
const resourceKey = (ingredient, unit) => JSON.stringify([normalize(ingredient), unit]);

// Household/source eligibility is selected by pantryDuration, not inferred here.
// Exact proof covers repeated measured meals only. It is not a diet certificate.
export function optimizeMeasuredPantry(recipes, inventory, servings, date, mealsPerDay, options = {}) {
  const start = isoDay(date);
  if (!Array.isArray(recipes) || !Array.isArray(inventory) || start === null ||
      !Number.isFinite(servings) || servings <= 0 || !Number.isFinite(mealsPerDay) || mealsPerDay <= 0 ||
      !Number.isFinite(MAX_MEALS / mealsPerDay)) {
    return result([], mealsPerDay, false, 'invalid_input');
  }

  const candidates = [];
  let supported = true;
  for (const recipe of recipes) {
    if (!recipe || !Array.isArray(recipe.ingredients) || !Number.isFinite(recipe.servings) || recipe.servings <= 0) {
      supported = false;
      continue;
    }
    const demands = new Map(), rationalDemands = new Map();
    let exact = exactQuantity(servings) && exactQuantity(recipe.servings);
    let valid = true;
    for (const ingredient of recipe.ingredients) {
      if (!ingredient || typeof ingredient !== 'object') { valid = false; break; }
      if (ingredient.optional) continue;
      const scaled = ingredient.quantity * servings / recipe.servings;
      if (typeof ingredient.ingredient !== 'string' || !normalize(ingredient.ingredient) ||
          !units.has(ingredient.unit) || !Number.isFinite(scaled) || scaled <= 0) {
        valid = false;
        break;
      }
      const key = resourceKey(ingredient.ingredient, ingredient.unit);
      const required = (demands.get(key) || 0) + scaled;
      if (!Number.isFinite(required) || required <= 0) { valid = false; break; }
      demands.set(key, required);
      const amount = decimal(ingredient.quantity), portion = decimal(servings), yieldAmount = decimal(recipe.servings);
      const rational = fraction(amount.n * portion.n * yieldAmount.d, amount.d * portion.d * yieldAmount.n);
      rationalDemands.set(key, add(rationalDemands.get(key) || zero, rational));
      const product = ingredient.quantity * servings;
      exact &&= exactQuantity(ingredient.quantity) && Number.isSafeInteger(product) &&
        product % recipe.servings === 0 && Number.isSafeInteger(required);
    }
    // Optional-only recipes spend no measured resource; they cannot prove a
    // finite maximum. They also must not manufacture 10,000 free meal batches.
    if (!valid || !demands.size) { supported = false; continue; }
    supported &&= exact;
    candidates.push({title: recipe.title, order: candidates.length,
      ingredientCount: recipe.ingredients.length, demands, rationalDemands,
      cost: [...demands.values()].reduce((a, b) => a + b, 0)});
  }

  const resources = new Set(candidates.flatMap(recipe => [...recipe.demands.keys()]));
  const lots = [];
  for (const lot of inventory) {
    if (!lot || typeof lot !== 'object') { supported = false; continue; }
    if (!eligibleStock(lot, date)) continue;
    const key = resourceKey(lot.ingredient, lot.unit);
    if (!resources.has(key)) continue;
    if (lot.expires && isoDay(lot.expires) === null) { supported = false; continue; }
    supported &&= exactQuantity(lot.quantity);
    lots.push({key, quantity: lot.quantity, expires: lot.expires || null, order: lots.length});
  }
  lots.sort((a, b) => a.expires === b.expires ? a.order - b.order :
    a.expires === null ? 1 : b.expires === null ? -1 : a.expires.localeCompare(b.expires));
  const initial = lots.map(lot => lot.quantity);

  // Atomic, strict consumption: no epsilon, inferred conversion, input mutation,
  // or partial meal. FEFO is dominance-preserving for identical ingredient/unit
  // resources: a later-expiring leftover is available on every future day on
  // which the earlier-expiring leftover could be used. Days only advance.
  function consume(stock, recipe, day) {
    const next = stock.slice();
    for (const [key, required] of recipe.demands) {
      let available = 0;
      for (let i = 0; i < lots.length; i++) {
        if (lots[i].key === key && (!lots[i].expires || lots[i].expires >= day)) available += next[i];
      }
      if (!Number.isFinite(available) || available < required) return null;
      let remaining = required;
      for (let i = 0; i < lots.length && remaining > 0; i++) {
        if (lots[i].key !== key || lots[i].expires && lots[i].expires < day) continue;
        if (next[i] >= remaining) {
          next[i] -= remaining;
          remaining = 0;
        } else {
          remaining -= next[i];
          next[i] = 0;
        }
      }
      if (remaining > 0) return null;
    }
    return next;
  }

  function consumeFraction(stock, recipe, day) {
    const next = stock.slice();
    for (const [key, required] of recipe.rationalDemands) {
      let remaining = required;
      for (let i = 0; i < lots.length && remaining.n > 0n; i++) {
        if (lots[i].key !== key || lots[i].expires && lots[i].expires < day) continue;
        if (compare(next[i], remaining) >= 0n) {
          next[i] = subtract(next[i], remaining);
          remaining = zero;
        } else {
          remaining = subtract(remaining, next[i]);
          next[i] = zero;
        }
      }
      if (remaining.n > 0n) return null;
    }
    return next;
  }

  // Retain a validated, feasible incumbent even when exact search is unsupported
  // or spends its budget. Recipe-order ties preserve the old greedy preference.
  const greedyOrder = [...candidates].sort((a, b) => a.ingredientCount - b.ingredientCount || a.order - b.order);
  let stock = initial.map(decimal);
  const greedy = [];
  for (let i = 0; i < MAX_MEALS; i++) {
    const day = mealDay(start, greedy.length, mealsPerDay);
    if (day === null) { supported = false; break; }
    let chosen = null;
    for (const recipe of greedyOrder) {
      const next = consumeFraction(stock, recipe, day);
      if (next !== null) { chosen = {recipe, next}; break; }
    }
    if (chosen === null) break;
    stock = chosen.next;
    greedy.push(chosen.recipe.title);
  }

  const total = initial.reduce((a, b) => a + b, 0);
  const minCost = Math.min(...candidates.map(recipe => recipe.cost));
  // This pools unit-coordinate counts only as a relaxation/upper bound. It does
  // not convert grams to millilitres or permit cross-unit resource consumption.
  const upperBound = candidates.length ? Math.floor(total / minCost) : 0;
  const exactScope = supported && candidates.length <= 8 && resources.size <= 8 && lots.length <= 16 &&
    Number.isSafeInteger(mealsPerDay) && mealsPerDay <= 24 && Number.isSafeInteger(total) &&
    Number.isSafeInteger(upperBound) && upperBound <= 64 && mealDay(start, upperBound, mealsPerDay) !== null;
  if (!exactScope) return result(greedy, mealsPerDay, false, greedy.length === MAX_MEALS ? 'meal_limit' : 'outside_exact_scope');
  if (greedy.length === upperBound) return result(greedy, mealsPerDay, true, 'proven_optimal', 'integer_resource_upper_bound');

  const requested = options && typeof options === 'object' ? options.maxStates : undefined;
  const budget = requested === undefined ? MAX_STATES :
    Number.isSafeInteger(requested) && requested >= 0 ? Math.min(requested, MAX_STATES) : 0;
  const searchOrder = [...candidates].sort((a, b) => a.cost - b.cost || a.order - b.order);
  const seen = new Set();
  let best = greedy.slice(), statesExplored = 0, stopped = false;

  function visit(remaining, sequence) {
    if (best.length === upperBound) return;
    // Position is part of the state: equal stock at different meal positions
    // has different future expiry eligibility. Keep every FEFO lot coordinate.
    const key = sequence.length + ':' + remaining.join(',');
    if (seen.has(key)) return;
    if (statesExplored >= budget) { stopped = true; return; }
    seen.add(key);
    statesExplored++;
    if (sequence.length > best.length) best = sequence.slice();
    if (best.length === upperBound) return;
    const optimistic = sequence.length + Math.floor(remaining.reduce((a, b) => a + b, 0) / minCost);
    if (optimistic <= best.length) return;
    const day = mealDay(start, sequence.length, mealsPerDay);
    for (const recipe of searchOrder) {
      const next = consume(remaining, recipe, day);
      if (next !== null) visit(next, [...sequence, recipe.title]);
      if (stopped || best.length === upperBound) return;
    }
  }
  visit(initial, []);
  const attainedBound = best.length === upperBound;
  return result(best, mealsPerDay, attainedBound || !stopped,
    attainedBound || !stopped ? 'proven_optimal' : 'state_budget',
    attainedBound ? 'integer_resource_upper_bound' : !stopped ? 'exhaustive_integer_search' : 'none', statesExplored);
}
