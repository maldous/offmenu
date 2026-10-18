import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {edibleMass} from '../public/basket-model.js';
import {convertQuantity} from '../public/dimensional-unit-engine.js';

const unit = name => 'urn:offmenu:unit:' + name;
const quantity = (value = 1500, name = 'mg', extra = {}) => ({
  kind: 'quantity', value, unitId: unit(name), dimension: 'mass',
  sourceValue: '1 500', sourceUnit: 'milligrammes', qualifiers: [], ...extra,
});

test('demonstrates existing mg gap and isolated conversion without altering basket code', () => {
  assert.equal(edibleMass({quantity: 1500, unit: 'mg', edibleFraction: 1}), null);
  const result = convertQuantity(quantity(), unit('g'));
  assert.equal(result.quantity.value, 1.5);
  assert.equal(edibleMass({quantity: result.quantity.value, unit: 'g', edibleFraction: 1}), 1.5);
});

test('supported units agree with the actual corpus registry and round trip', () => {
  const contract = JSON.parse(readFileSync(new URL('../corpus/common-data-contract.json', import.meta.url)));
  for (const [name, dimension, value, target, expected] of [
    ['kg', 'mass', 2, 'g', 2000], ['mg', 'mass', 1500, 'g', 1.5],
    ['microgram', 'mass', 1000, 'mg', 1], ['l', 'volume', 2, 'ml', 2000],
  ]) {
    assert.equal(contract.units[name].id, unit(name));
    assert.equal(contract.units[name].dimension, dimension);
    const source = quantity(value, name, {dimension});
    const result = convertQuantity(source, unit(target));
    assert.equal(result.quantity.value, expected);
    assert.equal(convertQuantity(result.quantity, unit(name)).quantity.value, value);
  }
});

test('retains source notation, basis, state, method, ranges and citation evidence without mutation', () => {
  const source = quantity(null, 'kg', {range: {min: 1, max: 2},
    sourceNotation: {value: 'one to two kilogrammes', citationIds: ['synthetic:source']},
    basis: quantity(2, 'count', {dimension: 'count', countedEntityId: 'synthetic:batch'}),
    preparationStateId: 'synthetic:raw', methodId: 'synthetic:weighed'});
  const before = structuredClone(source);
  const result = convertQuantity(source, unit('g'));
  assert.deepEqual(result.quantity.range, {min: 1000, max: 2000});
  assert.equal(result.quantity.value, null);
  for (const key of ['sourceValue', 'sourceUnit', 'sourceNotation', 'basis', 'preparationStateId', 'methodId']) {
    assert.deepEqual(result.quantity[key], source[key]);
  }
  assert.deepEqual(result.source, before);
  result.quantity.sourceNotation.citationIds.push('synthetic:other');
  assert.deepEqual(source, before);
  assert.deepEqual(result.source, before);
  assert.deepEqual(convertQuantity(quantity(null, 'kg', {range: {min: null, max: 2}}), unit('g')).quantity.range,
    {min: null, max: 2000});
});

test('density, unit mass and yield never authorize incompatible dimension conversion', () => {
  for (const [name, dimension, target] of [['ml', 'volume', 'g'], ['g', 'mass', 'ml'], ['count', 'count', 'g']]) {
    const result = convertQuantity(quantity(5, name, {dimension, densityGPerMl: 1, unitMassG: 20, yieldFactor: 2}), unit(target));
    assert.equal(result.status, 'unresolved');
    assert.equal(result.quantity, null);
  }
});

test('ambiguous measures, custom definitions, unknowns and qualifiers stay unresolved', () => {
  for (const source of [quantity(1, 'cup'), quantity(1, 'oz'), quantity(1, 'portion'),
    quantity(1, 'historical-pound'), quantity(null), quantity(0, 'g', {qualifiers: ['not-detected']}),
    quantity(1, 'g', {definitionId: 'synthetic:historical-definition'}),
    quantity(1, 'g', {dimension: 'volume'}), quantity(1, 'g', {qualifiers: ['below-quantification']})]) {
    const before = structuredClone(source), result = convertQuantity(source, unit('g'));
    assert.equal(result.quantity, null);
    assert.deepEqual(result.source, before);
    assert.deepEqual(source, before);
  }
});

test('rejects malformed values/ranges, overflow and underflow; measured zero is preserved', () => {
  for (const value of [-1, NaN, Infinity, '5', undefined]) {
    assert.equal(convertQuantity({...quantity(), value}, unit('g')).quantity, null);
  }
  for (const range of [{min: 2, max: 1}, {min: -1, max: 2}, {min: 0}, {min: 0, max: 2}]) {
    assert.equal(convertQuantity(quantity(3, 'kg', {range}), unit('g')).quantity, null);
  }
  assert.equal(convertQuantity(quantity(Number.MAX_VALUE, 'kg'), unit('microgram')).reason, 'numeric-overflow');
  assert.equal(convertQuantity(quantity(Number.MIN_VALUE, 'microgram'), unit('kg')).reason, 'numeric-underflow');
  assert.equal(convertQuantity(quantity(0), unit('g')).quantity.value, 0);
  assert.equal(convertQuantity(null, unit('g')).quantity, null);
});
