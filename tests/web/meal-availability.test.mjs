import test from 'node:test';
import assert from 'node:assert/strict';
import {mealAvailability} from '../../integrations/candidates/meal-availability.mjs';

// Synthetic opaque identifiers only; no recipe or pantry bodies.
const r = (ingredientId = 'synthetic-a', amount = 100, unit = 'g', basis = 'synthetic-edible') => ({ingredientId, amount, unit, basis});
const run = (requirements, inventory = []) => mealAvailability({requirements, inventory});
const freeze = x => {if (x && typeof x === 'object') {Object.values(x).forEach(freeze); Object.freeze(x);} return x;};

test('exact stock match, measured zero and zero requirement remain known', () => {
  assert.equal(run([r()], [r()]).status, 'ready-now');
  const absent = run([r()], [r(undefined, 0)]);
  assert.equal(absent.status, 'missing-ingredients');
  assert.equal(absent.requirements[0].evidence.deficit, 100);
  assert.equal(run([r(undefined, 0)]).status, 'ready-now');
});

test('duplicate requirements share summed demand; multiple lots share available stock', () => {
  const req = [r(undefined, 60), r(undefined, 60)];
  const missing = run(req, [r()]);
  assert.equal(missing.status, 'missing-ingredients');
  assert.equal(missing.deficits[0].quantities[0].deficit, 20);
  assert.deepEqual(missing.requirements.map(x => x.evidence.groupRequired), [120, 120]);
  const ready = run(req, [{...r(undefined, 50), lotId:'s1'}, {...r(undefined, 70), lotId:'s2'}]);
  assert.equal(ready.status, 'ready-now');
  assert.deepEqual(ready.requirements[0].evidence.inventoryIndices, [0, 1]);
});

test('unknown amounts are not zero; sufficient known stock proves readiness despite extra unknown stock', () => {
  assert.equal(run([r(undefined, null)], [r()]).status, 'unknown');
  assert.equal(run([r()], [r(undefined, null)]).status, 'unknown');
  assert.equal(run([r()], [r(), r(undefined, null)]).status, 'ready-now');
  assert.equal(run([r(undefined, 10), r(undefined, null)], [r()]).status, 'unknown');
  const {amount, ...withoutAmount} = r();
  assert.equal(run([withoutAmount], [r()]).status, 'unknown');
});

test('exact identity, unit and basis required; no mass/volume/package/name conversion', () => {
  for (const bad of [r(undefined, 1, 'kg'), r(undefined, 100, 'ml'), r(undefined, 1, 'package'),
    r(undefined, 100, 'g', 'synthetic-other-basis'), r(null), r(undefined, 100, null), r(undefined, 100, 'g', null)]) {
    assert.equal(run([r()], [bad]).status, 'unknown');
  }
  assert.equal(run([r()], [r('SYNTHETIC-A')]).status, 'missing-ingredients');
  for (const req of [r(null), r(undefined, 100, null), r(undefined, 100, 'g', null)]) {
    assert.equal(run([req], [r()]).status, 'unknown');
    assert.equal(run([r(), req], [r()]).status, 'unknown');
  }
});

test('exactly one distinct evidenced deficit versus multiple ingredients and uncertainty', () => {
  const one = run([r(), r(undefined, 20), r('synthetic-b')], [r('synthetic-b')]);
  assert.equal(one.oneExtraItem, true);
  assert.deepEqual(one.deficits.map(x => x.ingredientId), ['synthetic-a']);
  const two = run([r('synthetic-b'), r()]);
  assert.equal(two.oneExtraItem, false);
  assert.deepEqual(two.deficits.map(x => x.ingredientId), ['synthetic-a', 'synthetic-b']);
  const unknown = run([r(), r('synthetic-b', null)]);
  assert.equal(unknown.status, 'unknown'); assert.equal(unknown.oneExtraItem, false);
  assert.equal(unknown.deficits[0].ingredientId, 'synthetic-a');
});

test('decimal quantities compare without false floating deficits; overflow never becomes ready', () => {
  assert.equal(run([r(undefined, 0.1), r(undefined, 0.2)], [r(undefined, 0.3)]).status, 'ready-now');
  assert.equal(run([r(undefined, 0.3)], [r(undefined, 0.1), r(undefined, 0.2)]).status, 'ready-now');
  assert.equal(run([r(undefined, Number.MIN_VALUE)], [r(undefined, Number.MIN_VALUE)]).status, 'ready-now');
  assert.equal(run([r(undefined, Number.MAX_VALUE), r(undefined, Number.MAX_VALUE)]).status, 'unknown');
  assert.equal(run([r()], [r(undefined, Number.MAX_VALUE), r(undefined, Number.MAX_VALUE)]).status, 'unknown');
  const tiny = run([r(undefined, 1.0000000000000002e-308)], [r(undefined, 1e-308)]);
  assert.equal(tiny.status, 'missing-ingredients');
  assert.equal(tiny.requirements[0].evidence.deficit, Number.MIN_VALUE);
});

test('W18-MEAL22-F1: exact near-maximum aggregates are bounded before Number rounding', () => {
  const maxBinary64 = ((1n << 53n) - 1n) * (1n << 971n);
  const maxDecimalSpelling = 17976931348623157n * 10n ** 292n;
  const outside = maxDecimalSpelling + 10n ** 292n;
  assert.ok(outside > maxBinary64);
  assert.equal(Number(outside), Number.MAX_VALUE, 'Finite conversion alone misses this overflow');
  for (const values of [[Number.MAX_VALUE, 1e292], [1e292, Number.MAX_VALUE]]) {
    const aggregate = values.map(value => r(undefined, value));
    for (const [requirements, inventory] of [[aggregate, aggregate], [aggregate, [r(undefined, Number.MAX_VALUE)]],
      [[r(undefined, Number.MAX_VALUE)], aggregate]]) {
      const result = run(requirements, inventory);
      assert.equal(result.status, 'unknown');
      assert.equal(result.oneExtraItem, false);
      assert.equal(result.requirements[0].reason, 'unrepresentable-amount');
      assert.equal(result.requirements[0].evidence.deficit, null);
    }
  }
  assert.equal(run([r(undefined, Number.MAX_VALUE)], [r(undefined, Number.MAX_VALUE)]).status, 'ready-now');
  assert.ok(maxDecimalSpelling + 10n ** 290n < maxBinary64);
  const within = [r(undefined, Number.MAX_VALUE), r(undefined, 1e290)];
  assert.equal(run(within, within).status, 'ready-now', 'In-domain aggregate remains supported');
});

test('stable output, detached evidence and frozen input preservation', () => {
  const input = freeze({requirements:[r('synthetic-b'), r()], inventory:[r('synthetic-b')]});
  const before = structuredClone(input), a = mealAvailability(input), b = mealAvailability(input);
  assert.deepEqual(a, b); assert.deepEqual(input, before);
  assert.deepEqual(a.requirements.map(x => x.index), [0, 1]);
  a.requirements[0].evidence.inventoryIndices.push(100);
  assert.deepEqual(b.requirements[0].evidence.inventoryIndices, [0]);
});

test('malformed inputs and duplicate lot identities refused without coercion or getter execution', () => {
  for (const amount of [-1, NaN, Infinity, -Infinity, '1', false, {}]) assert.throws(() => run([r(undefined, amount)]), TypeError);
  for (const input of [null, [], {}, {requirements:[], inventory:[]}, {requirements:[r()], inventory:{}},
    {requirements:[r()], inventory:[], extra:true}]) assert.throws(() => mealAvailability(input), TypeError);
  assert.throws(() => run([r()], [{...r(), lotId:'s1'}, {...r(), lotId:'s1'}]), TypeError);
  assert.throws(() => run([{...r(), ingredientId:42}]), TypeError);
  assert.throws(() => run(Array(2)), TypeError);
  assert.throws(() => run(Array.from({length:1001}, () => r())), TypeError);
  assert.throws(() => run([{...r(), basis:' synthetic-edible'}]), TypeError);
  let calls = 0; const bad = {...r()};
  Object.defineProperty(bad, 'amount', {enumerable:true, get(){calls++; return 1;}});
  assert.throws(() => run([bad]), TypeError); assert.equal(calls, 0);
});
