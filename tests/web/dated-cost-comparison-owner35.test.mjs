import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {compareDatedCosts} from '../../public/dated-cost-comparison-owner35.mjs';

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
// Owned plain synthetic fixtures only. This is NOT an authenticated producer.
const NOW = 1791979200000, OP = 'synthetic-operation';
function receiptEnvelope(input) {
  const {cohort} = input, receipts = [];
  const append = (kind, binding) => receipts.push({kind, binding:clone(binding), status:'supported-claim',
    operationId:OP, issuedAt:NOW - 1000, expiresAt:NOW + 1000,
    provenance:{sourceId:'synthetic-only', version:'1', sha256:'1'.repeat(64), rights:{derivedUse:true}}});
  for (const c of input.candidates) {
    for (const line of c.lines) append('price', {purpose:input.purpose, cohort, candidateId:c.id,
      geography:c.geography ?? null, date:c.date ?? null, period:c.period ?? null, outlet:c.outlet ?? null,
      currency:c.currency ?? null, channel:c.channel ?? null, conditions:c.conditions ?? null, line});
    for (const rate of input.rates.filter(r => r.from === c.currency && r.to === input.targetCurrency &&
      (input.view !== 'ppp' || JSON.stringify(r.geography) === JSON.stringify(c.geography))))
      append(input.view, {purpose:input.purpose, cohort, candidateId:c.id, geography:c.geography ?? null, date:c.date ?? null, rate});
  }
  if (cohort.denominator) append('denominator', {purpose:input.purpose, cohort, denominator:cohort.denominator});
  return {schema:'dated-cost-receipts/2', operationId:OP, receipts};
}
const calculate = (input, envelope = receiptEnvelope(input)) => compareDatedCosts(JSON.stringify(input), JSON.stringify(envelope), NOW, OP);
const amount = (r, i = 0) => r.conditionalArithmetic.values[i].amount;
const groups = r => r.conditionalArithmetic.comparisonGroups;
const reason = (r, value) => r.blockers.some(b => b.reason === value);
function incomplete(result) {
  assert.equal(groups(result), null); assert.equal(result.ranking, null);
  assert.ok(result.conditionalArithmetic.values.every(row => row.amount === null));
}

test('conditional exact same-specification arithmetic never authenticates receipts or releases ranking', () => {
  const input = fixture(), before = clone(input), result = calculate(input);
  assert.equal(result.version, 'dated-cost-comparison/2'); assert.equal(result.status, 'blocked');
  assert.equal(result.authority.authenticated, false); assert.equal(result.authority.producerIntegration, 'not-implemented');
  assert.equal(result.ranking, null); assert.ok(result.rows.every(row => row.total === null));
  assert.equal(result.conditionalArithmetic.status, 'claims-complete');
  assert.deepEqual(groups(result), [['b'], ['a']]); assert.equal(amount(result).decimal, '10'); assert.equal(amount(result,1).decimal, '8');
  assert.equal(result.rows[0].coverage.byUnit.g.required.decimal, '600');
  assert.equal(result.rows[0].coverage.byUnit.ml.required.decimal, '100');
  assert.deepEqual(result.sourceSnapshot, before); assert.deepEqual(input, before);
});
test('default-denied receipt boundary cannot be activated by forged shape or client status', () => {
  const input = fixture(), forged = receiptEnvelope(input); forged.authenticated = true; forged.admitted = true;
  input.authenticated = true; input.approved = true;
  const fake = calculate(input, forged); assert.equal(fake.authority.authenticated, false); assert.equal(fake.ranking, null);
  const empty = compareDatedCosts(JSON.stringify(input), undefined, NOW, OP); incomplete(empty);
  assert.equal(empty.rows[0].coverage.knownLines, 0);
  assert.ok(empty.rows.every(row => row.total === null));
});
test('one missing claim/cost withholds all conditional cohort totals, preserving exact unknown coverage', () => {
  const input = fixture(); input.candidates[1].lines[1].cost.value = null;
  const result = calculate(input); incomplete(result);
  assert.equal(result.rows[1].knownSubtotal.value.decimal, '4');
  assert.equal(result.rows[1].knownSubtotal.authority, 'unverified-receipt-claims');
  assert.deepEqual(result.rows[1].coverage.unknownLineIds, ['oil']);
  assert.equal(result.rows[1].coverage.byUnit.ml.known.decimal, '0');
  assert.equal(result.rows[1].coverage.byUnit.ml.required.decimal, '100');
  const source = fixture(), receipts = receiptEnvelope(source); receipts.receipts = receipts.receipts.filter(r => r.kind !== 'price');
  incomplete(calculate(source, receipts));
});
test('observed zero is distinct from missing, unsupported precision and nonfinite input', () => {
  const zero = fixture(); zero.candidates[0].lines[0].cost.value = '0'; assert.equal(amount(calculate(zero)).decimal, '4');
  for (const value of [null, '1.0000001', '01', '-1', 'NaN', 'Infinity', '1e10', 1]) {
    const input = fixture(); input.candidates[0].lines[0].cost.value = value; incomplete(calculate(input));
  }
  assert.throws(() => compareDatedCosts('{"x":1e400}', '[]', NOW, OP), /finite/);
});
test('direct dated FX multiplication retains direction/version/date/missing/ambiguity gates', () => {
  assert.equal(amount(calculate(fixture('fx')),1).decimal, '12');
  for (const mutate of [x => x.rates = [], x => x.rates.push(clone(x.rates[0])),
    x => x.rates[0].direction = 'source-per-target', x => x.rates[0].date = '2026-10-11',
    x => x.rates[0].date = '2026-10-12T00:00:00Z', x => x.rates[0].version = null,
    x => x.rates[0].value = '0', x => x.rates[0].value = '1e3']) {
    const input = fixture('fx'); mutate(input); incomplete(calculate(input));
  }
});
test('PPP remains conditional aggregate context with exact recurring fractions and geography factors', () => {
  const result = calculate(fixture('ppp'));
  assert.equal(result.currency, 'international-dollar'); assert.deepEqual(amount(result), {numerator:'20',denominator:'3',decimal:null});
  assert.equal(amount(result,1).decimal, '4'); assert.equal(result.ranking, null);
  for (const mutate of [x => x.rates[0].referenceYear = 2025, x => x.rates[0].component = null,
    x => x.rates[0].methodology = null, x => x.rates[0].geography.country = 'US',
    x => x.rates[0].purpose = 'dated-price-comparison', x => x.rates[0].direction = 'target-per-source']) {
    const input = fixture('ppp'); mutate(input); incomplete(calculate(input));
  }
  const shared = fixture('ppp'); shared.candidates[1].currency = 'AUD'; shared.rates[1].from = 'AUD';
  for (const line of shared.candidates[1].lines) line.cost.currency = 'AUD';
  assert.equal(amount(calculate(shared),1).decimal, '4');
  const checkout = fixture('ppp'); checkout.purpose = 'dated-price-comparison'; assert.throws(() => calculate(checkout));
  const sku = fixture('ppp'); sku.cohort.level = 'single-sku'; assert.throws(() => calculate(sku));
});
test('pack/consumed and exact quantity/unit/date/period/conditions distinctions survive the contract break', () => {
  for (const mutate of [x => x.candidates[1].lines[0].cost.basis = 'consumed',
    x => x.candidates[1].lines[0].quantity.unit = 'kg', x => x.candidates[1].lines[0].quantity.value = '500',
    x => x.cohort.quantities[0].quantity.value = null, x => x.candidates[1].date = '2026-10-13',
    x => x.candidates[1].period.end = '2026-10-13', x => x.candidates[1].conditions.tax = 'excluded',
    x => x.candidates[1].conditions.loyalty = 'membership-only', x => x.candidates[1].geography = null,
    x => x.candidates[1].currency = 'USD']) {
    const input = fixture(); mutate(input); incomplete(calculate(input));
  }
  const input = fixture(); input.cohort.date = '2026-02-30'; assert.throws(() => calculate(input));
  const missing = fixture(); missing.cohort.quantities[0].quantity.value = null;
  assert.equal(calculate(missing).rows[0].coverage.byUnit.g.required, null);
});
test('person-day/energy denominator arithmetic requires positive consumed evidence and never defaults one', () => {
  const input = fixture(); input.cohort.amountBasis = 'consumed';
  for (const c of input.candidates) for (const l of c.lines) l.cost.basis = 'consumed';
  input.cohort.denominator = {kind:'person-days',unit:'person-day',value:'4'}; assert.equal(amount(calculate(input)).decimal, '2.5');
  input.cohort.denominator = {kind:'energy',unit:'kcal',value:'2000'}; assert.equal(amount(calculate(input)).decimal, '5');
  for (const d of [null,{kind:'energy',unit:'kcal',value:'0'},{kind:'energy',unit:'kJ',value:'2000'}]) {input.cohort.denominator=d;incomplete(calculate(input));}
  const pack = fixture(); pack.cohort.denominator = {kind:'person-days',unit:'person-day',value:'4'}; incomplete(calculate(pack));
});
test('malformed JSON, duplicate keys, stale/future/conflicting/unbound/rights-denied receipt claims withhold', () => {
  const input = fixture();
  for (const text of ['{','null','[]','{"schema":"dated-cost-receipts/2","receipts":[],"receipts":[]}'])
    incomplete(compareDatedCosts(JSON.stringify(input), text, NOW, OP));
  for (const mutate of [e => e.operationId = 'other', e => e.receipts.push(clone(e.receipts[0])),
    e => e.receipts[0].operationId = 'other', e => e.receipts[0].expiresAt = NOW,
    e => e.receipts[0].issuedAt = NOW + 1, e => e.receipts[0].expiresAt = NOW + 900000,
    e => e.receipts[0].status = 'conflict', e => e.receipts[0].status = 'qualified',
    e => e.receipts[0].binding.candidateId = 'wrong', e => e.receipts[0].provenance.rights.derivedUse = false]) {
    const e = receiptEnvelope(input); mutate(e); incomplete(calculate(input,e));
  }
  assert.throws(() => compareDatedCosts('{"x":1,"x":2}', '{}', NOW, OP), /Duplicate/);
});
test('captured primitive time/operation and input/output bounds reject before arithmetic', () => {
  const input = JSON.stringify(fixture()), receipts = JSON.stringify(receiptEnvelope(fixture()));
  for (const now of [null,undefined,NaN,-1,1.5]) assert.throws(() => compareDatedCosts(input, receipts, now, OP));
  for (const op of [null,'',{},()=>OP]) assert.throws(() => compareDatedCosts(input, receipts, NOW, op));
  assert.throws(() => compareDatedCosts(' '.repeat(2000001), receipts, NOW, OP), /Bounded/);
  assert.throws(() => compareDatedCosts('['.repeat(34)+'0'+']'.repeat(34),receipts,NOW,OP), /depth/);
  const wrong = fixture(); wrong.cohort.evidenceTrack = 'cpi-expenditure-weights'; assert.throws(() => calculate(wrong));
  const unit = fixture(); unit.cohort.quantities[0].quantity.unit = 'weight-percent'; incomplete(calculate(unit));
});
test('legacy callbacks and nonJSON objects are rejected without invoking functions/getters/stringification', () => {
  let calls = 0; const callback = () => {calls++; throw Error('must not execute');};
  const options = {}; Object.defineProperty(options,'resolveEvidence',{get(){calls++;return callback;}});
  assert.throws(() => compareDatedCosts(fixture(),options));
  assert.throws(() => compareDatedCosts(JSON.stringify(fixture()),options,NOW,OP));
  assert.throws(() => compareDatedCosts(JSON.stringify(fixture()),callback,NOW,OP));
  const dangerousFactory = () => {calls++; return Object.defineProperty(Promise.reject(Error('must never be created')),
    'constructor',{get(){calls++;throw Error('must never read');}});};
  assert.throws(() => compareDatedCosts(JSON.stringify(fixture()),{resolveEvidence:dangerousFactory},NOW,OP));
  assert.throws(() => compareDatedCosts(JSON.stringify(fixture()),'{}',NOW,OP,callback));
  const hostile = {toJSON(){calls++;throw Error('must not stringify');}};
  assert.throws(() => compareDatedCosts(hostile,'{}',NOW,OP));
  assert.throws(() => compareDatedCosts(Promise.resolve('{}'),'{}',NOW,OP));
  assert.equal(calls,0);
});
test('serialized snapshots and returned receipt claims detach and freeze with no caller-object mutation', () => {
  const input = fixture('fx'), e = receiptEnvelope(input), before = clone({input,e});
  const result = calculate(input,e); assert.deepEqual({input,e},before);
  input.rates[0].value = '999'; e.receipts[0].provenance.sourceId = 'changed';
  assert.equal(amount(result,1).decimal,'12'); assert.equal(result.sourceSnapshot.rates[0].value,'1.5');
  assert.throws(() => {result.receiptSnapshot.receipts[0].provenance.sourceId='changed';},TypeError);
  assert.throws(() => {result.rows[0].lines[0].source.cost.value='999';},TypeError);
});
test('aggregate/precision ceilings and conservative resolution groups remain exact conditional diagnostics', () => {
  const huge = fixture('fx'); huge.rates[0].value='999999999999'; assert.ok(reason(calculate(huge),'aggregate-out-of-range'));
  const sum=fixture();for(const l of sum.candidates[0].lines)l.cost.value='999999999999';incomplete(calculate(sum));
  const qty=fixture();for(const q of qty.cohort.quantities)q.quantity={unit:'g',value:'999999999999'};
  for(const c of qty.candidates)for(let i=0;i<c.lines.length;i++)c.lines[i].quantity=clone(qty.cohort.quantities[i].quantity);
  assert.ok(reason(calculate(qty),'quantity-aggregate-out-of-range'));
  const close=fixture();close.candidates[1].lines[0].cost.value='6.005';close.candidates[1].lines[1].cost.value='4';
  assert.deepEqual(groups(calculate(close)),[['a','b']]);assert.equal(calculate(close).ranking,null);
});

// Test-only parent containment adapter; no production producer/runtime is shipped.
// Source strings are owned benign fixtures. Hostile child values are NEVER serialized
// in this parent. Only successful bounded stdout text is parsed by the JSON boundary.
function containedEnvelope(source) {
  const child=spawnSync(process.execPath,['--unhandled-rejections=strict','--input-type=module','--eval',source],
    {encoding:'utf8',timeout:1000,maxBuffer:32768,env:{}});
  if(child.error||child.signal||child.status!==0)return {state:'unknown',reason:child.error?.code ?? child.signal ?? 'exit-'+child.status,text:'{"schema":"dated-cost-receipts/2","operationId":null,"receipts":[]}'};
  try{const parsed=JSON.parse(child.stdout);if(!parsed||parsed.schema!=='dated-cost-receipts/2')throw Error('invalid');}
  catch{return {state:'unknown',reason:'invalid-json',text:'{"schema":"dated-cost-receipts/2","operationId":null,"receipts":[]}'};}
  return {state:'unverified-json',text:child.stdout};
}
test('disposable synthetic producer constructor/species rejection/crash cannot kill parent; result unknown', () => {
  const cases=[
    [`const p=Object.defineProperty(Promise.reject(Error('constructor-held')),'constructor',{get(){throw Error('constructor read');}});try{Promise.prototype.then.call(p,()=>{},()=>{});}catch{}`,'exit-1'],
    [`import {runInNewContext} from 'node:vm';const p=runInNewContext('(class P extends Promise {static get [Symbol.species](){throw Error("species read");}}).reject(Error("species-held"))');try{Promise.prototype.then.call(p,()=>{},()=>{});}catch{}`,'exit-1'],
    [`throw Error('producer crash');`,'exit-1'],
    [`process.stdout.write('{');`,'invalid-json'],
    [`process.stdout.write('x'.repeat(65536));`,'ENOBUFS'],
    [`setInterval(()=>{},1000);`,'ETIMEDOUT']
  ];
  for(const [source,expected] of cases){const result=containedEnvelope(source);assert.equal(result.state,'unknown');assert.equal(result.reason,expected);
    const projection=compareDatedCosts(JSON.stringify(fixture()),result.text,NOW,OP);incomplete(projection);assert.equal(projection.authority.authenticated,false);}
});
test('successful bounded child JSON remains unverified; contained success is not authority admission', () => {
  const text=JSON.stringify(receiptEnvelope(fixture()));
  const result=containedEnvelope('process.stdout.write('+JSON.stringify(text)+');');
  assert.equal(result.state,'unverified-json');const projection=compareDatedCosts(JSON.stringify(fixture()),result.text,NOW,OP);
  assert.equal(projection.conditionalArithmetic.status,'claims-complete');assert.equal(projection.status,'blocked');
  assert.equal(projection.ranking,null);assert.equal(projection.authority.authenticated,false);
});
