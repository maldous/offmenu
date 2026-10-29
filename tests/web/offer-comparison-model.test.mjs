import test from 'node:test';
import assert from 'node:assert/strict';
import { evaluateOfferBasket } from '../../public/offer-comparison-model.js';

const date = '2026-10-14';
const provenance = { sourceId: 'synthetic', recordId: '001', license: 'test-only', rights: 'fixture', visibility: 'private' };
const need = { id: 'rice-gap', productId: 'rice-001', quantity: 600, unit: 'g' };
const offer = { id: 'offer-001', productId: 'rice-001', storeId: 'store-a', accountId: 'alice', currency: 'AUD', observedOn: date, pack: { quantity: 500, unit: 'g' }, priceMinor: 300, provenance };
const input = () => ({ accountId: 'alice', date, currency: 'AUD', lines: [{ need: structuredClone(need), offer: structuredClone(offer) }], fees: [{ storeId: 'store-a', currency: 'AUD', date, amountMinor: 50 }], maxStoreStops: 1, budgetMinor: 650 });
const run = changes => evaluateOfferBasket({ ...input(), ...changes });

test('600 g needs two 500 g packs, retains leftovers and distinguishes consumed cost', () => {
  const result = run();
  assert.equal(result.lines[0].packs, 2);
  assert.equal(result.lines[0].leftoverQuantity, 400);
  assert.equal(result.lines[0].consumedCostMinor, 360);
  assert.equal(result.totalMinor, 650);
  assert.equal(result.budgetStatus, 'within');
  assert.deepEqual(result.lines[0].provenance, provenance);
  assert.equal(result.lines[0].offerId, offer.id);
  assert.equal(result.lines[0].observedOn, date);
});
test('same dimension conversions only; density and identity are never inferred', () => {
  const i = input(); i.lines[0].offer.pack = { quantity: 0.5, unit: 'kg' };
  assert.equal(evaluateOfferBasket(i).totalMinor, 650);
  i.lines[0].offer.pack.unit = 'l';
  assert.equal(evaluateOfferBasket(i).totalMinor, null);
  i.lines[0].offer = { ...offer, productId: 'other' };
  assert.ok(evaluateOfferBasket(i).lines[0].reasons.includes('product-mismatch'));
});
test('missing quantity/price/fees/budget stays unknown, zero fee and budget are explicit', () => {
  for (const field of ['quantity', 'price']) {
    const i = input(); if (field === 'quantity') i.lines[0].need.quantity = null; else i.lines[0].offer.priceMinor = null;
    const r = evaluateOfferBasket(i); assert.equal(r.totalMinor, null); assert.equal(r.budgetStatus, 'unknown');
  }
  assert.equal(run({ fees: [] }).totalMinor, null);
  assert.equal(run({ budgetMinor: null }).budgetStatus, 'unknown');
  assert.equal(run({ budgetMinor: 0 }).budgetStatus, 'exceeded');
  assert.equal(run({ fees: [{ storeId: 'store-a', currency: 'AUD', date, amountMinor: 0 }] }).totalMinor, 600);
});
test('dated observations require exact date; explicit validity windows permit estimates only', () => {
  const i = input(); i.lines[0].offer.observedOn = '2026-10-13';
  assert.equal(evaluateOfferBasket(i).totalMinor, null);
  Object.assign(i.lines[0].offer, { validFrom: '2026-10-13', validThrough: date });
  assert.equal(evaluateOfferBasket(i).totalMinor, 650);
  i.lines[0].offer.validThrough = '2026-10-13';
  assert.equal(evaluateOfferBasket(i).totalMinor, null);
  i.lines[0].offer.observedOn = '2026-10-15';
  assert.ok(evaluateOfferBasket(i).lines[0].reasons.includes('date-incompatible'));
});
test('currency, account and provenance incompatibilities withhold totals', () => {
  for (const change of [{ currency: 'USD' }, { accountId: 'bob' }, { provenance: null }, { observedOn: '2026-02-30' }]) {
    const i = input(); Object.assign(i.lines[0].offer, change); assert.equal(evaluateOfferBasket(i).totalMinor, null);
  }
  for (const change of [{ date: '2026-10-13' }, { currency: 'USD' }, { amountMinor: null }]) {
    const i = input(); Object.assign(i.fees[0], change); assert.equal(evaluateOfferBasket(i).totalMinor, null);
  }
});
test('store fees counted once; explicit stop bound evaluates independently of budget', () => {
  const i = input(); i.lines.push({ need: { ...need, id: 'second', quantity: 1 }, offer: { ...offer, id: 'second-offer' } });
  assert.equal(evaluateOfferBasket(i).totalMinor, 950);
  i.lines[1].offer.storeId = 'store-b'; i.fees.push({ ...i.fees[0], storeId: 'store-b' });
  const r = evaluateOfferBasket(i); assert.equal(r.totalMinor, 1000); assert.equal(r.storeStopStatus, 'exceeded'); assert.equal(r.withinBounds, false);
  assert.equal(run({ maxStoreStops: null }).storeStopStatus, 'unknown');
});
test('unsafe arithmetic, duplicate needs/fees, malformed dates and excess input are rejected', () => {
  const i = input(); i.lines[0].offer.priceMinor = Number.MAX_SAFE_INTEGER;
  assert.equal(evaluateOfferBasket(i).totalMinor, null);
  assert.throws(() => run({ date: '2026-02-30' }));
  assert.throws(() => run({ lines: Array(101).fill(input().lines[0]) }));
  assert.throws(() => run({ lines: Array(2).fill(input().lines[0]) }));
  assert.throws(() => run({ fees: Array(2).fill(input().fees[0]) }));
});
test('pure calculation leaves caller input unchanged and preserves unknown metadata', () => {
  const i = input(); i.lines[0].offer.uncertainty = 'unverified observation'; const before = structuredClone(i);
  const result = evaluateOfferBasket(i); assert.deepEqual(i, before);
  assert.equal(result.lines[0].uncertainty, 'unverified observation');
  assert.equal(result.status, 'cost-estimate');
});
