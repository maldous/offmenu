import test from 'node:test';
import assert from 'node:assert/strict';
import {runInNewContext} from 'node:vm';
import {compareDatedCosts} from '../public/dated-cost-comparison-owner35.mjs';

const clone = x => structuredClone(x);
const conditions = {tax:'included', delivery:'included', promotion:'none', loyalty:'none'};
function fixture(view = 'local') {
  const purpose = view === 'ppp' ? 'ppp-analysis' : 'dated-price-comparison';
  const period = {start:'2026-10-12', end:'2026-10-12'};
  const quantities = [{id:'rice', quantity:{value:'600', unit:'g'}}, {id:'oil', quantity:{value:'100', unit:'ml'}}];
  return {view, purpose, targetCurrency:view === 'ppp' ? 'international-dollar' : 'AUD',
    cohort:{id:'synthetic-cohort', version:'1', specificationId:'synthetic-food-spec', specificationVersion:'1',
      evidenceTrack:'source-price-observation', population:'synthetic-household', foodState:'as-sold',
      period, date:'2026-10-12', amountBasis:'pack', level:'aggregate-basket', channel:'store', conditions,
      denominator:{kind:'basket', unit:'basket', value:'1'}, comparisonResolution:'0.01', quantities},
    candidates:['a','b'].map((id, i) => ({id, geography:{country:i ? 'US' : 'AU', region:'synthetic-region'},
      outlet:'synthetic-shop-' + id, channel:'store', conditions:clone(conditions), period:clone(period), date:'2026-10-12',
      currency:view === 'local' || !i ? 'AUD' : 'USD',
      lines:quantities.map((q, j) => ({id:q.id, quantity:clone(q.quantity),
        source:{sourceId:'synthetic-source', version:'1', rights:'synthetic-only', observationDate:'2026-10-12'},
        cost:{value:i ? '4' : j ? '4' : '6', currency:view === 'local' || !i ? 'AUD' : 'USD', basis:'pack'}}))})),
    rates:view === 'fx' ? [{id:'synthetic-fx', version:'v1', from:'USD', to:'AUD', direction:'target-per-source',
      date:'2026-10-12', value:'1.5', purpose}] : view === 'ppp' ? ['AUD','USD'].map((from, i) => ({
        id:'synthetic-ppp-' + from, version:'v1', from, to:'international-dollar', direction:'local-per-international-dollar',
        value:i ? '2' : '1.5', purpose, series:'synthetic-series', component:'household-consumption', referenceYear:2026,
        methodology:'synthetic aggregate contextual measure', geography:{country:i ? 'US' : 'AU', region:'synthetic-region'}})) : []};
}
// Synthetic owner qualification ONLY. Production owner must independently verify
// binding/rights; reflecting requests, as this fixture does, is not a production gate.
const qualify = ({binding}) => ({status:'qualified', binding:clone(binding),
  provenance:{sourceId:'synthetic-only-owner', version:'v1', sha256:'1'.repeat(64), rights:{derivedUse:true}}});
const calculate = input => compareDatedCosts(input, {resolveEvidence:qualify});
const reason = (r, value) => r.blockers.some(b => b.reason === value);

test('same-specification dated pack costs retain separate g/ml coverage and exact order', () => {
  const input = fixture(), before = clone(input), result = calculate(input);
  assert.equal(result.status, 'complete');
  assert.deepEqual(result.ranking, [['b'], ['a']]);
  assert.equal(result.rows[0].total.decimal, '10');
  assert.equal(result.rows[1].total.decimal, '8');
  assert.equal(result.rows[0].coverage.byUnit.g.required.decimal, '600');
  assert.equal(result.rows[0].coverage.byUnit.ml.required.decimal, '100');
  assert.deepEqual(result.sourceSnapshot, before); assert.deepEqual(input, before);
});
test('one unknown cost blocks ALL cohort totals and rank; exact known subtotal remains labelled', () => {
  const input = fixture(); input.candidates[1].lines[1].cost.value = null;
  const result = calculate(input);
  assert.equal(result.status, 'blocked'); assert.equal(result.ranking, null);
  assert.ok(result.rows.every(r => r.total === null));
  assert.equal(result.rows[1].knownSubtotal.value.decimal, '4');
  assert.deepEqual(result.rows[1].coverage.unknownLineIds, ['oil']);
  assert.equal(result.rows[1].coverage.byUnit.ml.known.decimal, '0');
  assert.equal(result.rows[1].coverage.byUnit.ml.required.decimal, '100');
});
test('qualified observed zero cost is distinct from missing and no client flag qualifies prices', () => {
  const input = fixture(); input.candidates[0].lines[0].cost.value = '0';
  assert.equal(calculate(input).rows[0].total.decimal, '4');
  input.candidates[0].lines[0].approved = true;
  const result = compareDatedCosts(input);
  assert.equal(result.ranking, null); assert.ok(reason(result, 'denominator-unqualified'));
  assert.ok(result.rows.every(r => r.coverage.knownLines === 0));
});
test('dated direct FX uses target-per-source; inverted, missing, stale and ambiguous rates block', () => {
  assert.equal(calculate(fixture('fx')).rows[1].total.decimal, '12');
  for (const mutate of [x => x.rates = [], x => x.rates.push(clone(x.rates[0])),
    x => x.rates[0].direction = 'source-per-target', x => x.rates[0].date = '2026-10-11',
    x => x.rates[0].date = '2026-10-12T00:00:00Z', x => x.rates[0].version = null,
    x => x.rates[0].value = '0', x => x.rates[0].value = '1e3']) {
    const input = fixture('fx'); mutate(input); const result = calculate(input);
    assert.equal(result.ranking, null); assert.ok(result.rows.every(r => r.total === null));
  }
});
test('PPP divides ONLY qualified aggregate contextual amounts; recurring precision stays exact', () => {
  const result = calculate(fixture('ppp'));
  assert.equal(result.currency, 'international-dollar'); assert.deepEqual(result.ranking, [['b'], ['a']]);
  assert.deepEqual(result.rows[0].total, {numerator:'20', denominator:'3', decimal:null});
  assert.equal(result.rows[1].total.decimal, '4');
  for (const mutate of [x => x.rates[0].referenceYear = 2025, x => x.rates[0].component = null,
    x => x.rates[0].methodology = null, x => x.rates[0].geography.country = 'US',
    x => x.rates[0].purpose = 'dated-price-comparison', x => x.rates[0].direction = 'target-per-source']) {
    const input = fixture('ppp'); mutate(input); assert.equal(calculate(input).ranking, null);
  }
  const checkout = fixture('ppp'); checkout.purpose = 'dated-price-comparison'; assert.throws(() => calculate(checkout));
  const sku = fixture('ppp'); sku.cohort.level = 'single-sku'; assert.throws(() => calculate(sku));
});
test('pack and consumed bases cannot mix; source quantities require same unit and value', () => {
  for (const mutate of [x => x.candidates[1].lines[0].cost.basis = 'consumed',
    x => x.candidates[1].lines[0].quantity.unit = 'kg', x => x.candidates[1].lines[0].quantity.value = '500',
    x => x.cohort.quantities[0].quantity.value = null]) {
    const input = fixture(); mutate(input); assert.equal(calculate(input).ranking, null);
  }
  const missing = fixture(); missing.cohort.quantities[0].quantity.value = null;
  assert.equal(calculate(missing).rows[0].coverage.byUnit.g.required, null);
  assert.deepEqual(calculate(missing).rows[0].coverage.byUnit.g.unresolvedQuantityLineIds, ['rice']);
});
test('person-day/energy denominators require positive qualified consumed basis, never default one', () => {
  const input = fixture(); input.cohort.amountBasis = 'consumed';
  for (const c of input.candidates) for (const l of c.lines) l.cost.basis = 'consumed';
  input.cohort.denominator = {kind:'person-days', unit:'person-day', value:'4'};
  assert.equal(calculate(input).rows[0].total.decimal, '2.5');
  input.cohort.denominator = {kind:'energy', unit:'kcal', value:'2000'};
  assert.equal(calculate(input).rows[0].total.decimal, '5');
  for (const denominator of [null, {kind:'energy', unit:'kcal', value:'0'}, {kind:'energy', unit:'kJ', value:'2000'}]) {
    input.cohort.denominator = denominator; assert.equal(calculate(input).ranking, null);
  }
  const pack = fixture(); pack.cohort.denominator = {kind:'person-days', unit:'person-day', value:'4'};
  assert.ok(reason(calculate(pack), 'denominator-missing-or-incompatible'));
});
test('different periods/observations/conditions/geography and currencies are incompatible', () => {
  for (const mutate of [x => x.candidates[1].date = '2026-10-13',
    x => x.candidates[1].period.end = '2026-10-13', x => x.candidates[1].conditions.tax = 'excluded',
    x => x.candidates[1].conditions.loyalty = 'membership-only', x => x.candidates[1].geography = null,
    x => x.candidates[1].currency = 'USD']) {
    const input = fixture(); mutate(input); assert.equal(calculate(input).ranking, null);
  }
  const input = fixture(); input.cohort.date = '2026-02-30'; assert.throws(() => calculate(input));
});
test('CPI weights and incompatible evidence tracks cannot become quantities or cost cohorts', () => {
  const input = fixture(); input.cohort.evidenceTrack = 'cpi-expenditure-weights'; assert.throws(() => calculate(input));
  const amounts = fixture(); amounts.cohort.quantities[0].quantity.unit = 'weight-percent';
  assert.equal(calculate(amounts).ranking, null);
});
test('qualification is exact-bound, rights-aware, conflict-aware and synchronous', () => {
  for (const resolver of [x => ({...qualify(x), binding:{wrong:true}}), x => ({...qualify(x), status:'conflict'}),
    x => {const r = qualify(x); r.provenance.rights.derivedUse = false; return r;}, async x => qualify(x)]) {
    assert.equal(compareDatedCosts(fixture(), {resolveEvidence:resolver}).ranking, null);
  }
});
test('rejected accidental async evidence blocks without an unhandled rejection', async () => {
  const result = compareDatedCosts(fixture(), {resolveEvidence:async () => { throw Error('async authority unavailable'); }});
  assert.equal(result.status, 'blocked'); assert.equal(result.ranking, null);
  await new Promise(resolve => setImmediate(resolve));
});
test('foreign-realm rejected/fulfilled promises and thenables are observed but never qualified', async () => {
  const foreignReject = runInNewContext('(async function(){throw Error("foreign authority unavailable");})');
  const foreignFulfill = runInNewContext('(async function(){return {status:"qualified"};})');
  for (const resolver of [() => foreignReject(), () => foreignFulfill(),
    () => ({then(_yes, no){ no(Error('thenable unavailable')); }}),
    () => ({then(){ throw Error('thenable failed'); }})]) {
    const result = compareDatedCosts(fixture(), {resolveEvidence:resolver});
    assert.equal(result.status, 'blocked'); assert.equal(result.ranking, null);
  }
  let hits = 0;
  const result = compareDatedCosts(fixture(), {resolveEvidence:x => {
    const verdict = qualify(x);
    Object.defineProperty(verdict, 'then', {get(){hits++; throw Error('getter must not execute');}, enumerable:true});
    return verdict;
  }});
  assert.equal(result.status, 'blocked'); assert.equal(hits, 0);
  await new Promise(resolve => setImmediate(resolve));
});
test('input captured before resolver effects; frozen result and evidence detach in both directions', () => {
  const input = fixture('fx'), before = clone(input), verdicts = [];
  const result = compareDatedCosts(input, {resolveEvidence:x => {
    input.rates[0].value = '999'; input.candidates[1].lines[0].cost.value = '999';
    assert.ok(Object.isFrozen(x.binding)); const r = qualify(x); verdicts.push(r); return r;
  }});
  assert.equal(result.rows[1].total.decimal, '12'); assert.deepEqual(result.sourceSnapshot, before);
  verdicts[0].provenance.sourceId = 'changed'; assert.equal(result.rows[0].lines[0].qualification.provenance.sourceId, 'synthetic-only-owner');
  assert.throws(() => { result.rows[0].lines[0].source.cost.value = '100'; }, TypeError);
  assert.throws(() => { result.sourceSnapshot.cohort.conditions.tax = 'excluded'; }, TypeError);
});
test('bounded precision and aggregates block rather than round, overflow or coerce', () => {
  for (const value of [null, '1.0000001', '01', '-1', 'NaN', 'Infinity', '1e10', 1]) {
    const input = fixture(); input.candidates[0].lines[0].cost.value = value; assert.equal(calculate(input).ranking, null);
  }
  const huge = fixture('fx'); huge.rates[0].value = '999999999999';
  assert.ok(reason(calculate(huge), 'aggregate-out-of-range'));
  const sum = fixture(); for (const l of sum.candidates[0].lines) l.cost.value = '999999999999';
  assert.ok(reason(calculate(sum), 'aggregate-out-of-range'));
  const qty = fixture(); qty.cohort.quantities[0].quantity.value = '999999999999';
  qty.cohort.quantities[1].quantity = {unit:'g', value:'999999999999'};
  for (const c of qty.candidates) for (let i = 0; i < c.lines.length; i++) c.lines[i].quantity = clone(qty.cohort.quantities[i].quantity);
  assert.ok(reason(calculate(qty), 'quantity-aggregate-out-of-range'));
});
test('declared resolution groups close observed costs without a rounding-level winner', () => {
  const input = fixture(); input.candidates[1].lines[0].cost.value = '6.005';
  input.candidates[1].lines[1].cost.value = '4';
  assert.deepEqual(calculate(input).ranking, [['a', 'b']]);
});
test('PPP factors are geography-specific even when two candidates share a local currency', () => {
  const input = fixture('ppp'); input.candidates[1].currency = 'AUD'; input.rates[1].from = 'AUD';
  for (const line of input.candidates[1].lines) line.cost.currency = 'AUD';
  assert.equal(calculate(input).rows[1].total.decimal, '4');
});
test('sparse/cyclic/accessor inputs and excessive candidate count fail without invoking getters', () => {
  const sparse = fixture(); sparse.candidates = Array(2); assert.throws(() => calculate(sparse), /Dense/);
  const cycle = fixture(); cycle.self = cycle; assert.throws(() => calculate(cycle));
  const many = fixture(); many.candidates = Array.from({length:51}, (_, i) => ({...many.candidates[0], id:String(i)})); assert.throws(() => calculate(many));
  const hostile = fixture(); let hits = 0;
  Object.defineProperty(hostile, 'cohort', {enumerable:true, get(){hits++; return {};}});
  assert.throws(() => calculate(hostile)); assert.equal(hits, 0);
});
