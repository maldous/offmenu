import test from 'node:test';
import assert from 'node:assert/strict';
import {matchRecipeStockInput} from '../../integrations/candidates/match-recipe-stock-input.mjs';
import {mealAvailability} from '../../integrations/candidates/meal-availability.mjs';

// Synthetic source-batch contracts only; no recipe/pantry bodies.
const options = {today:'2026-10-16'};
const ingredient = (extra = {}) => ({name:'synthetic label', ingredientId:'Synthetic:Exact|ID', amount:10, unit:'g', basis:'synthetic:raw', ...extra});
const lot = (extra = {}) => ({id:'synthetic-lot', ingredient:'unrelated display label', ingredientId:'Synthetic:Exact|ID', quantity:10, unit:'g', basis:'synthetic:raw', ...extra});
const produce = (ingredients = [ingredient()], inventory = [lot()]) => matchRecipeStockInput({ingredients}, inventory, options);
const result = (...args) => mealAvailability(produce(...args));

test('W18-PRODUCER22-F1: completeness is absent/null/boolean only and false stays blocked', () => {
  const run = recipe => matchRecipeStockInput(recipe, [lot()], options);
  for (const flag of ['false', 'true', 0, 1, {}, []]) {
    assert.throws(() => run({ingredients:[ingredient()], ingredientExtractionComplete:flag}),
      {name:'TypeError', message:'Boolean ingredient extraction completeness flag required'});
  }
  for (const flag of [undefined, null, true]) {
    assert.equal(mealAvailability(run({ingredients:[ingredient()], ingredientExtractionComplete:flag})).status, 'ready-now');
  }
  assert.equal(mealAvailability(run({ingredients:[ingredient()]})).status, 'ready-now');
  assert.throws(() => run({ingredients:[ingredient()], ingredientExtractionComplete:false}),
    {name:'TypeError', message:'Complete ingredient extraction required'});
});

test('preserves exact IDs, basis and source-batch quantities without label or serving inference', () => {
  const recipe = {ingredients:[ingredient()], servings:100, yield:{value:200}};
  const input = matchRecipeStockInput(recipe, [lot()], options);
  assert.deepEqual(input, {requirements:[{ingredientId:'Synthetic:Exact|ID', amount:10, unit:'g', basis:'synthetic:raw'}],
    inventory:[{ingredientId:'Synthetic:Exact|ID', amount:10, unit:'g', basis:'synthetic:raw', lotId:'synthetic-lot'}]});
  assert.equal(mealAvailability(input).status, 'ready-now');
  assert.equal(result([ingredient()], [lot({ingredientId:'synthetic:exact|id'})]).status, 'missing-ingredients');
  assert.equal(result([ingredient()], [lot({basis:'synthetic:cooked'})]).status, 'unknown');
});

test('unknown quantities survive; zero is known and malformed quantities are refused', () => {
  for (const quantity of [null, undefined]) {
    const input = produce([ingredient()], [lot({quantity})]);
    assert.equal(input.inventory[0].amount, null);
    assert.equal(mealAvailability(input).status, 'unknown');
    assert.equal(result([ingredient({amount:quantity})]).status, 'unknown');
  }
  assert.equal(result([ingredient()], [lot({quantity:0})]).status, 'missing-ingredients');
  for (const quantity of ['', '10', false, -1, NaN, Infinity]) assert.throws(() => produce([ingredient()], [lot({quantity})]), TypeError);
});

test('legacy names and amountBasis never manufacture ingredient identity or physical basis', () => {
  const input = produce([ingredient({ingredientId:undefined, basis:undefined})], [lot({ingredientId:undefined, basis:undefined, amountBasis:'manual'})]);
  assert.equal(input.requirements[0].ingredientId, null);
  assert.equal(input.inventory[0].ingredientId, null);
  assert.equal(input.inventory[0].basis, null);
  assert.equal(mealAvailability(input).status, 'unknown');
});

test('matches source-batch optional/review/expiry scope while retaining unknown and zero stock', () => {
  const input = produce([ingredient(), ingredient({optional:true})], [lot({id:'unknown', quantity:null}),
    lot({id:'zero', quantity:0}), lot({id:'today', expires:options.today}),
    lot({id:'expired', expires:'2026-10-15'}), lot({id:'review', needsReview:true})]);
  assert.equal(input.requirements.length, 1);
  assert.deepEqual(input.inventory.map(x => x.lotId), ['unknown', 'zero', 'today']);
  assert.equal(mealAvailability(input).status, 'ready-now');
  assert.throws(() => matchRecipeStockInput({ingredients:[ingredient()], ingredientExtractionComplete:false}, [], options));
  assert.throws(() => matchRecipeStockInput({ingredients:[ingredient()], publisher:'smithsonian-archive'}, [], options));
  assert.throws(() => matchRecipeStockInput({ingredients:[ingredient()], sourcePublisher:'smithsonian-archive'}, [], options));
});

test('duplicate demand and lots use the reviewed helper without mutation or aliasing', () => {
  const recipe = {ingredients:[ingredient({amount:6}), ingredient({amount:6})]}, stock = [lot()];
  Object.freeze(recipe.ingredients[0]); Object.freeze(recipe.ingredients[1]); Object.freeze(recipe.ingredients); Object.freeze(recipe);
  Object.freeze(stock[0]); Object.freeze(stock);
  const input = matchRecipeStockInput(recipe, stock, options);
  assert.equal(mealAvailability(input).deficits[0].quantities[0].deficit, 2);
  input.requirements[0].amount = 0;
  assert.equal(recipe.ingredients[0].amount, 6);
  assert.throws(() => produce([ingredient()], [lot(), lot()]), /Duplicate lotId/);
});

test('rejects malformed scope and accessors without executing selected getters', () => {
  for (const today of [undefined, '2026-02-30', 'yesterday']) assert.throws(() => matchRecipeStockInput({ingredients:[ingredient()]}, [], {today}), TypeError);
  assert.throws(() => produce([ingredient()], [lot({expires:'2026-02-30'})]), TypeError);
  assert.throws(() => produce([ingredient({optional:'false'})]), TypeError);
  assert.throws(() => produce([ingredient()], [lot({needsReview:'false'})]), TypeError);
  assert.throws(() => produce(Array(1)), TypeError);
  let calls = 0; const row = ingredient();
  Object.defineProperty(row, 'ingredientId', {get(){calls++; return 'wrong';}});
  assert.throws(() => produce([row]), TypeError); assert.equal(calls, 0);
});
