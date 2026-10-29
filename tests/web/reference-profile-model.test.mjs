import test from 'node:test';
import assert from 'node:assert/strict';
import {calculateBasket} from '../../apps/web/src/basket-model.js';
import {referenceViews, COMPARISON_VIEWS} from '../../apps/web/src/reference-profile-model.js';

const metrics = [{metric_id:'protein_g', unit:'g'}, {metric_id:'energy_kcal', unit:'kcal'}];
function fixture() {
  const observation = (value, unit) => ({value, unit, definition:'synthetic-v1', sourceId:'synthetic',
    basisAmount:100, basisUnit:'g', state:'cooked'});
  const basket = {id:'synthetic:001', version:2, track:'synthetic-model', state:'cooked',
    population:'adult-demo', personDays:2,
    lines:[{id:'00001', quantity:200, unit:'g', edibleG:200, state:'cooked',
      nutrients:{protein_g:observation(10, 'g'), energy_kcal:observation(100, 'kcal')}}]};
  const serving = {basketId:basket.id, basketVersion:2, recipeId:'demo-recipe', recipeVersion:'r1',
    state:'cooked', sourceId:'synthetic', fraction:0.25};
  const referenceProfile = {system:'synthetic-only', id:'demo-profile', name:'Demonstration only',
    version:'v1', lifeStage:'adult-demo', sourceId:'synthetic', basis:'person-day',
    rights:{permittedUse:'test-only'}, metrics:{protein_g:{value:50, unit:'g',
      definition:'synthetic-v1', status:'complete'}}};
  return {basket, options:{serving, referenceProfile}};
}
const adapt = ({basket, options}) => referenceViews(calculateBasket(basket, metrics), options);

test('existing source gap: five views present but declared serving/reference absent', () => {
  const {basket, options} = fixture();
  const original = calculateBasket({...basket, ...options}, metrics);
  assert.equal(original.metrics.protein_g.total, 20);
  assert.equal(original.metrics.protein_g.perServing, undefined);
  assert.equal(original.metrics.protein_g.percentReference, undefined);
  const result = referenceViews(original, options);
  const views = result.views.protein_g;
  assert.deepEqual(Object.keys(views), COMPARISON_VIEWS);
  assert.deepEqual(Object.values(views).map(view => view.value), [20, 10, 100, 200, 10, 5, 20]);
  assert.equal(result.views.energy_kcal.percentReference.value, null);
  assert.deepEqual(result.calculation, original);
});

test('missing denominators remain explicit while independent serving stays available', () => {
  const f = fixture();
  delete f.basket.personDays;
  delete f.basket.lines[0].nutrients.energy_kcal;
  const result = adapt(f).views.protein_g;
  assert.equal(result.total.value, 20);
  assert.equal(result.perServing.value, 5);
  for (const key of ['per1000kcal', 'equivalent2000kcal', 'perPersonDay', 'percentReference']) {
    assert.equal(result[key].value, null);
    assert.equal(result[key].status, 'withheld');
  }
  assert.equal(result.per1000kcal.denominator.amount, null);
  assert.equal(result.percentReference.denominator.personDays, null);
});

test('partial numerator preserves subtotal and lineage but withholds every view', () => {
  const f = fixture();
  f.basket.lines.push({...structuredClone(f.basket.lines[0]), id:'00002', nutrients:{}});
  const result = adapt(f);
  assert.equal(result.calculation.metrics.protein_g.knownSubtotal, 20);
  assert.equal(result.calculation.lineage[1].id, '00002');
  assert.equal(result.views.protein_g.per100g.denominator.amount, 400);
  for (const view of Object.values(result.views.protein_g)) assert.equal(view.value, null);
});

test('reference requires named version/system, compatible definition, unit and life stage', () => {
  const mutations = [
    f => delete f.options.referenceProfile,
    ...['id', 'name', 'version', 'system', 'lifeStage', 'sourceId'].map(key => f => delete f.options.referenceProfile[key]),
    f => f.options.referenceProfile.lifeStage = 'child-demo',
    f => f.options.referenceProfile.basis = 'adult-equivalent-energy',
    f => f.options.referenceProfile.metrics.protein_g.unit = 'mg',
    f => f.options.referenceProfile.metrics.protein_g.definition = 'other',
    f => f.options.referenceProfile.metrics.protein_g.status = 'missing',
    ...[0, -1, null, '50', Infinity, NaN].map(value => f => f.options.referenceProfile.metrics.protein_g.value = value),
  ];
  for (const mutate of mutations) {
    const f = fixture(); mutate(f);
    assert.equal(adapt(f).views.protein_g.percentReference.status, 'withheld');
  }
  const f = fixture(); delete f.basket.population;
  assert.equal(adapt(f).views.protein_g.percentReference.value, null);
});

test('serving evidence is version/state bound; measured mass is allowed without invented count', () => {
  const f = fixture(); delete f.options.serving.fraction; f.options.serving.massG = 50;
  assert.equal(adapt(f).views.protein_g.perServing.value, 5);
  const mutations = [
    f => delete f.options.serving,
    ...['recipeId', 'recipeVersion', 'sourceId'].map(key => f => delete f.options.serving[key]),
    f => f.options.serving.basketVersion = 1,
    f => f.options.serving.basketId = 'other',
    f => f.options.serving.state = 'raw',
    f => f.options.serving.massG = 50,
    ...[0, -1, 1.1, null, '0.25', Infinity, NaN].map(value => f => f.options.serving.fraction = value),
  ];
  for (const mutate of mutations) {
    const item = fixture(); mutate(item);
    assert.equal(adapt(item).views.protein_g.perServing.status, 'withheld');
  }
});

test('zero and incomplete mass/energy do not become finite densities; measured zero nutrient survives', () => {
  const f = fixture(); f.basket.lines[0].nutrients.energy_kcal.value = 0;
  f.basket.lines[0].nutrients.protein_g.value = 0;
  const result = adapt(f).views.protein_g;
  assert.equal(result.total.value, 0);
  assert.equal(result.percentReference.value, 0);
  assert.equal(result.per1000kcal.value, null);
  assert.equal(result.per1000kcal.denominator.amount, 0);
  delete f.basket.lines[0].edibleG; f.basket.lines[0].unit = 'ml';
  assert.equal(adapt(f).views.protein_g.per100g.denominator.amount, null);
});

test('custody is retained without mutation, defaults, I/O or implied qualification', () => {
  const f = fixture();
  const calculation = calculateBasket(f.basket, metrics);
  calculation.custody = {accountScope:'synthetic-account', consent:'test-only', rights:{redistribute:false},
    uncertainty:'modelled', sourceIdentity:'00001'};
  const before = structuredClone({calculation, options:f.options});
  const result = referenceViews(calculation, f.options);
  assert.deepEqual({calculation, options:f.options}, before);
  assert.deepEqual(result.calculation.custody, before.calculation.custody);
  assert.deepEqual(result.referenceProfileKey, ['synthetic-only', 'demo-profile', 'v1', 'adult-demo']);
  result.calculation.custody.rights.redistribute = true;
  result.basis.referenceProfile.rights.permittedUse = 'changed';
  assert.equal(calculation.custody.rights.redistribute, false);
  assert.equal(f.options.referenceProfile.rights.permittedUse, 'test-only');
  assert.equal(referenceViews(calculation).views.protein_g.perServing.value, null);
  assert.throws(() => referenceViews({...calculation, calculationVersion:'unreviewed/2'}), /basket\/1.1/);
});
