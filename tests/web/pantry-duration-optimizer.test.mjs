import test from 'node:test';
import assert from 'node:assert/strict';
import {pantryDuration} from '../../apps/web/src/household-model.js';

// Synthetic measured-menu contracts only. No inventory, provider, UI, nutrition
// or food-safety qualification is inferred from a maximum repeated meal count.
const DATE = '2026-11-17';
const ingredient = (name, quantity, unit = 'g', extra = {}) => ({ingredient: name, quantity, unit, ...extra});
const recipe = (title, ingredients, extra = {}) => ({id: title, title, servings: 1, ingredients, ...extra});
const lot = (name, quantity, unit = 'g', extra = {}) => ({id: name, ingredient: name, quantity, unit, ...extra});
const run = (recipes, inventory, {members = [], servings = 1, date = DATE, mealsPerDay = 1, maxStates} = {}) =>
  pantryDuration(recipes, inventory, members, servings, date, mealsPerDay,
    maxStates === undefined ? {} : {maxStates});
const dayAt = (start, position, mealsPerDay) =>
  new Date(Date.parse(start + 'T12:00:00Z') + Math.floor(position / mealsPerDay) * 86400000).toISOString().slice(0, 10);

function shape(value, mealsPerDay = 1) {
  assert.ok(Number.isSafeInteger(value.meals) && value.meals >= 0 && value.meals <= 10000);
  assert.equal(value.sequence.length, value.meals);
  assert.equal(value.days, Math.floor(value.meals / mealsPerDay));
  assert.equal(value.limited, value.meals === 10000);
  assert.equal(typeof value.optimal, 'boolean');
  assert.equal(value.optimization.scope, 'measured_menu_count');
  assert.ok(Number.isSafeInteger(value.optimization.statesExplored));
  assert.ok(value.optimization.statesExplored >= 0 && value.optimization.statesExplored <= 20000);
  assert.ok(['proven_optimal', 'outside_exact_scope', 'state_budget', 'invalid_input', 'meal_limit']
    .includes(value.optimization.reason));
  assert.ok(['none', 'exhaustive_integer_search', 'integer_resource_upper_bound'].includes(value.optimization.proof));
  assert.equal(value.optimal, value.optimization.reason === 'proven_optimal');
  assert.equal(value.optimization.proof === 'none', !value.optimal);
}

// Independent tiny oracle: enumerate EVERY integer allocation among lots, not
// the implementation's FEFO rule, pooled resource bound or greedy/search order.
// Fixtures entering this oracle use canonical names and small positive integer
// quantities/scaled demands, with no household exclusion or optional-only meal.
function tinyOracle(recipes, inventory, {servings = 1, date = DATE, mealsPerDay = 1} = {}) {
  const requirements = recipes.map(row => {
    const result = new Map();
    for (const item of row.ingredients.filter(item => !item.optional)) {
      const quantity = item.quantity * servings / row.servings;
      assert.ok(Number.isSafeInteger(quantity) && quantity > 0, 'Integer oracle fixture required');
      const key = JSON.stringify([item.ingredient, item.unit]);
      result.set(key, (result.get(key) || 0) + quantity);
    }
    assert.ok(result.size > 0);
    return [...result];
  });
  const initial = inventory.map(item => item.quantity);
  for (const amount of initial) assert.ok(Number.isSafeInteger(amount) && amount >= 0 && amount <= 12);
  const memo = new Map();

  function successors(stock, recipeIndex, position) {
    const day = dayAt(date, position, mealsPerDay);
    let possibilities = [stock];
    for (const [key, required] of requirements[recipeIndex]) {
      const indices = inventory.flatMap((item, i) =>
        JSON.stringify([item.ingredient, item.unit]) === key && (!item.expires || item.expires >= day) ? [i] : []);
      const allocations = [];
      function distribute(next, at, remaining) {
        if (at === indices.length) {
          if (remaining === 0) allocations.push(next);
          return;
        }
        const i = indices[at];
        for (let used = 0; used <= Math.min(next[i], remaining); used++) {
          const copy = next.slice();
          copy[i] -= used;
          distribute(copy, at + 1, remaining - used);
        }
      }
      for (const candidate of possibilities) distribute(candidate, 0, required);
      possibilities = [...new Map(allocations.map(row => [row.join(','), row])).values()];
    }
    return possibilities;
  }

  function maximum(stock, position) {
    const key = JSON.stringify([position, stock]);
    if (memo.has(key)) return memo.get(key);
    let best = 0;
    for (let i = 0; i < recipes.length; i++) {
      for (const next of successors(stock, i, position)) best = Math.max(best, 1 + maximum(next, position + 1));
    }
    memo.set(key, best);
    return best;
  }

  function accepts(sequence) {
    let possibilities = [initial];
    for (let position = 0; position < sequence.length; position++) {
      const i = recipes.findIndex(row => row.title === sequence[position]);
      if (i < 0) return false;
      possibilities = [...new Map(possibilities.flatMap(stock => successors(stock, i, position))
        .map(row => [row.join(','), row])).values()];
      if (!possibilities.length) return false;
    }
    return true;
  }

  return {maximum: () => maximum(initial, 0), accepts};
}

function exactAgainstOracle(recipes, inventory, options = {}) {
  const oracle = tinyOracle(recipes, inventory, options);
  const result = run(recipes, inventory, options);
  shape(result, options.mealsPerDay || 1);
  assert.equal(result.meals, oracle.maximum(), 'Must maximize count, not a first feasible greedy menu');
  assert.ok(oracle.accepts(result.sequence), 'Every reported batch needs a feasible same-day resource allocation');
  assert.equal(result.optimal, true);
  return result;
}

test('pantry_duration_optimizer_replaces_the_greedy_counterexample', () => {
  const menus = [recipe('large rice', [ingredient('rice', 10)]), recipe('small rice', [ingredient('rice', 1)])];
  const stock = [lot('rice', 10)];
  const result = exactAgainstOracle(menus, stock);
  assert.equal(result.meals, 10);
  assert.deepEqual(result.sequence, Array(10).fill('small rice'));
  assert.equal(result.optimization.proof, 'integer_resource_upper_bound');
  assert.equal(exactAgainstOracle([...menus].reverse(), stock).meals, result.meals);
});

test('pantry_duration_optimizer_matches_an_independent_tiny_multiresource_oracle', () => {
  const menus = [
    recipe('mixed', [ingredient('rice', 2), ingredient('water', 1, 'ml')]),
    recipe('rice only', [ingredient('rice', 1)]),
    recipe('water only', [ingredient('water', 2, 'ml')]),
  ];
  for (const rice of [0, 1, 3, 5]) {
    for (const water of [0, 2, 5]) {
      const stock = [lot('rice', rice), lot('water', water, 'ml')];
      const forward = exactAgainstOracle(menus, stock);
      const reverse = exactAgainstOracle([...menus].reverse(), [...stock].reverse());
      assert.equal(reverse.meals, forward.meals, 'Optimum count cannot depend on menu/lot ordering');
    }
  }
  // Surplus water makes the scalar relaxation loose. Exhausting the reachable
  // allocation graph, rather than attaining that bound, can still prove a max.
  const coupled = [recipe('coupled', [ingredient('rice', 2), ingredient('water', 2, 'ml')])];
  const result = exactAgainstOracle(coupled, [lot('rice', 2), lot('water', 8, 'ml')]);
  assert.equal(result.meals, 1);
  assert.equal(result.optimization.proof, 'exhaustive_integer_search');
});

test('pantry_duration_optimizer_proves_expiry_sensitive_sequences_not_static_stock_counts', () => {
  const menus = [recipe('water first in input', [ingredient('water', 1, 'ml')]),
    recipe('rice before expiry', [ingredient('rice', 1)])];
  const stock = [lot('rice', 2, 'g', {expires: DATE}), lot('water', 2, 'ml')];
  const result = exactAgainstOracle(menus, stock);
  assert.equal(result.meals, 3, 'One expiring rice batch must precede the two water batches');
  assert.equal(result.sequence[0], 'rice before expiry');
  assert.equal(result.optimization.proof, 'exhaustive_integer_search');
  assert.equal(exactAgainstOracle(menus, stock, {mealsPerDay: 2}).meals, 4);

  // The oracle permits every legal allocation, so this also independently
  // checks that FEFO never throws away a better identical-resource future.
  const lots = [lot('rice', 1, 'g', {id: 'short', expires: DATE}),
    lot('rice', 2, 'g', {id: 'long', expires: '2026-11-19'})];
  const one = [recipe('rice', [ingredient('rice', 1)])];
  assert.equal(exactAgainstOracle(one, lots).meals, 3);
  assert.equal(exactAgainstOracle(one, [...lots].reverse()).meals, 3);
});

test('pantry_duration_optimizer_reports_budget_lower_bounds_and_real_zero_search_proofs', () => {
  const menus = [recipe('large', [ingredient('rice', 10)]), recipe('small', [ingredient('rice', 1)])];
  const stock = [lot('rice', 10)];
  const oracle = tinyOracle(menus, stock);
  for (const maxStates of [0, 1, 2]) {
    const result = run(menus, stock, {maxStates});
    shape(result);
    assert.ok(oracle.accepts(result.sequence));
    assert.ok(result.meals <= oracle.maximum());
    assert.ok(result.optimization.statesExplored <= maxStates);
    assert.equal(result.limited, false, 'A search budget is not the 10000-batch display cap');
    if (maxStates === 0) {
      assert.equal(result.meals, 1);
      assert.equal(result.optimal, false);
      assert.equal(result.optimization.reason, 'state_budget');
    }
    if (result.optimal) assert.equal(result.meals, oracle.maximum());
  }
  const alreadyAttained = run([menus[1]], [lot('rice', 3)], {maxStates: 0});
  shape(alreadyAttained);
  assert.equal(alreadyAttained.meals, 3);
  assert.equal(alreadyAttained.optimal, true);
  assert.equal(alreadyAttained.optimization.proof, 'integer_resource_upper_bound');
  assert.equal(alreadyAttained.optimization.statesExplored, 0);
  exactAgainstOracle(menus, stock, {maxStates: Number.MAX_SAFE_INTEGER});
});

test('pantry_duration_optimizer_keeps_finite_scope_limits_honest_even_for_good_incumbents', () => {
  const names = ['rice', 'water', 'carrot', 'peas', 'onion', 'potato', 'salt', 'sugar', 'apple'];
  const one = recipe('one', [ingredient('rice', 1)]);
  const cases = [
    {name: 'nine recipes', recipes: Array.from({length: 9}, (_, i) => recipe('rice ' + i, one.ingredients)), stock: [lot('rice', 2)], meals: 2},
    {name: 'nine resources', recipes: [recipe('nine', names.map(name => ingredient(name, 1)))], stock: names.map(name => lot(name, 1)), meals: 1},
    {name: 'seventeen relevant lots', recipes: [one], stock: Array.from({length: 17}, (_, i) => lot('rice', 1, 'g', {id: String(i)})), meals: 17},
    {name: 'quantity beyond exact bound', recipes: [recipe('large', [ingredient('rice', 1000001)])], stock: [lot('rice', 1000001)], meals: 1},
    {name: 'fractional stock', recipes: [one], stock: [lot('rice', 2.5)], meals: 2},
    {name: 'nonintegral scaled demand', recipes: [recipe('third', [ingredient('rice', 1)], {servings: 3})], stock: [lot('rice', 1)], meals: 3},
    {name: 'relaxation beyond 64 meals', recipes: [one], stock: [lot('rice', 65)], meals: 65},
    {name: 'fractional meals per day', recipes: [one], stock: [lot('rice', 3)], meals: 3, options: {mealsPerDay: 1.5}},
    {name: 'more than 24 meals per day', recipes: [one], stock: [lot('rice', 3)], meals: 3, options: {mealsPerDay: 25}},
  ];
  for (const row of cases) {
    const result = run(row.recipes, row.stock, {...row.options, maxStates: 0});
    shape(result, row.options?.mealsPerDay || 1);
    assert.equal(result.meals, row.meals, row.name);
    assert.equal(result.optimal, false, row.name);
    assert.equal(result.optimization.reason, 'outside_exact_scope', row.name);
    assert.equal(result.optimization.proof, 'none', row.name);
    assert.equal(result.optimization.statesExplored, 0, row.name);
  }
  const eight = names.slice(0, 8);
  const atBoundary = run(eight.map(name => recipe(name, [ingredient(name, 1)])),
    eight.flatMap(name => [lot(name, 1, 'g', {id: name + '-a'}), lot(name, 1, 'g', {id: name + '-b'})]), {maxStates: 0});
  shape(atBoundary);
  assert.equal(atBoundary.meals, 16);
  assert.equal(atBoundary.optimal, true, 'Eight recipes/eight resources/sixteen lots are inside the domain');
  const irrelevant = run([one], [lot('rice', 2), ...Array.from({length: 20}, (_, i) => lot('water', 1, 'ml', {id: 'water-' + i}))]);
  assert.equal(irrelevant.meals, 2);
  assert.equal(irrelevant.optimal, true, 'Only relevant usable lots count towards the exact domain');
});

test('pantry_duration_optimizer_preserves_household_resource_scaling_and_input_identity', () => {
  const adult = {id: 'fixture-adult', name: 'Fixture adult', advisors: ['vegan'], restrictions: []};
  const safe = recipe('scaled rice', [ingredient('rice', 2), ingredient('cheese', 50, 'g', {optional: true})], {servings: 2});
  const menus = [recipe('blocked dairy', [ingredient('cheese', 1)]),
    recipe('unknown', [ingredient('unclassified synthetic ingredient', 1)]),
    recipe('review recipe', [ingredient('rice', 1)], {needsReview: true}),
    recipe('unknown yield', [ingredient('rice', 1)], {servingsUnknown: true}), safe];
  const stock = [lot('rice', 6), lot('cheese', 100), lot('unclassified synthetic ingredient', 100),
    lot('rice', 100, 'g', {id: 'review', needsReview: true}),
    lot('rice', 100, 'g', {id: 'expired', expires: '2026-11-16'}),
    lot('rice', 100, 'ml', {id: 'wrong-unit'})];
  const input = {menus, stock, members: [adult]};
  const before = structuredClone(input);
  const freeze = value => {
    if (value && typeof value === 'object') {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  };
  freeze(input);
  const result = run(menus, stock, {members: input.members, servings: 3});
  shape(result);
  assert.equal(result.meals, 2);
  assert.deepEqual(result.sequence, ['scaled rice', 'scaled rice']);
  assert.equal(result.optimal, true);
  assert.deepEqual(input, before);

  const duplicates = [recipe('duplicate needs', [ingredient('rice', 1), ingredient('rice', 1)])];
  assert.equal(exactAgainstOracle(duplicates, [lot('rice', 3)]).meals, 1);
  const wrongUnit = run([recipe('water ml', [ingredient('water', 1, 'ml')])], [lot('water', 10, 'g')]);
  assert.equal(wrongUnit.meals, 0, 'No inferred gram/millilitre conversion');
  const optionalOnly = run([recipe('optional only', [ingredient('rice', 1, 'g', {optional: true})])], [lot('rice', 1)]);
  shape(optionalOnly);
  assert.equal(optionalOnly.meals, 0);
  assert.equal(optionalOnly.optimal, false);
  assert.equal(optionalOnly.optimization.reason, 'outside_exact_scope');
});

test('pantry_duration_optimizer_fractional_fallback_never_spends_an_epsilon_or_invents_a_proof', () => {
  const tenth = [recipe('tenth', [ingredient('rice', 0.1)])];
  for (const [amount, expected] of [[0.3, 3], [0.29999999999999993, 2]]) {
    const result = run(tenth, [lot('rice', amount)]);
    shape(result);
    assert.equal(result.meals, expected, 'Canonical finite decimal amounts cannot be rounded into extra stock');
    assert.equal(result.optimal, false);
    assert.equal(result.optimization.reason, 'outside_exact_scope');
    assert.deepEqual(result.sequence, Array(expected).fill('tenth'));
  }
  const cap = run([recipe('one rice', [ingredient('rice', 1)])], [lot('rice', 10001)]);
  shape(cap);
  assert.equal(cap.meals, 10000);
  assert.equal(cap.optimization.reason, 'meal_limit');
  assert.equal(cap.optimal, false);
  assert.ok(cap.meals < 10001, 'The bounded witness is not the actual available maximum');
});

test('pantry_duration_optimizer_invalid_inputs_return_finite_unproven_empty_results', () => {
  const menus = [recipe('rice', [ingredient('rice', 1)])], stock = [lot('rice', 3)];
  const inputs = [
    [null, stock, [], 1, DATE, 1],
    [menus, null, [], 1, DATE, 1],
    [menus, stock, null, 1, DATE, 1],
    [menus, stock, [null], 1, DATE, 1],
    ...[0, -1, NaN, Infinity, '1'].map(servings => [menus, stock, [], servings, DATE, 1]),
    ...[0, -1, NaN, Infinity, '1'].map(perDay => [menus, stock, [], 1, DATE, perDay]),
    ...['2026-02-30', '2026-1-1', 'not-a-date', null].map(date => [menus, stock, [], 1, date, 1]),
  ];
  for (const args of inputs) {
    const result = pantryDuration(...args);
    assert.equal(result.meals, 0);
    assert.equal(result.days, 0);
    assert.deepEqual(result.sequence, []);
    assert.equal(result.limited, false);
    assert.equal(result.optimal, false);
    assert.equal(result.optimization.reason, 'invalid_input');
    assert.equal(result.optimization.proof, 'none');
    assert.equal(result.optimization.statesExplored, 0);
  }
});
