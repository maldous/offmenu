import test from 'node:test';
import assert from 'node:assert/strict';
import * as fixed from '../../public/unified-data.js';
import {storePrivateRecords} from '../../cloud/provider-data.mjs';

const source = {id: 'personal-import', name: 'Authored synthetic regional price fixture',
  url: 'https://example.invalid/synthetic', license: 'Authored test data only', countries: []};
const mapping = {kind: 'priceObservation', id: 'observation', name: 'name', barcode: 'barcode',
  price: 'price', currency: 'currency', date: 'date', retailer: 'store'};
const csv = 'observation,name,barcode,price,currency,date,store\n' +
  'obs-1,Example 500 g,00123,0,EUR,2026-10-01,Store A\n' +
  'obs-2,Example 500 g,00123,3,EUR,2026-10-02,Store B\n';
test('price CSV fails closed without mapped nonblank unique observation IDs', () => {
  assert.throws(() => fixed.normalizeCSV(csv, source, {...mapping, id: undefined}), /source observation ID/);
  assert.throws(() => fixed.normalizeCSV(csv.replace('obs-1,', ' ,'), source, mapping), /source observation ID/);
  assert.throws(() => fixed.normalizeCSV(csv.replace('obs-2,', 'obs-1,'), source, mapping), /unique/);
});
test('distinct IDs preserve lexical product join, dated location and zero; repeat local import is idempotent', () => {
  const first = fixed.normalizeCSV(csv, source, mapping), second = fixed.normalizeCSV(csv, source, mapping);
  const saved = [...new Map([...first, ...second].map(r => [r.id, r])).values()];
  assert.equal(saved.length, 2);
  assert.ok(saved.every(r => r.data.identifiers[0].value === '00123'));
  assert.deepEqual(saved.map(r => [r.data.amount, r.data.currency, r.data.observedAt, r.data.retailer.name]),
    [[0, 'EUR', '2026-10-01', 'Store A'], [3, 'EUR', '2026-10-02', 'Store B']]);
  assert.ok(saved.every(r => r.data.availability === 'unknown' && r.provenance.visibility === 'private'));
});
test('existing owner/id upsert keeps two observations on repeat import, with provenance and conditions intact', async () => {
  const rows = fixed.normalizeCSV(csv, source, mapping);
  rows[0].data = {...rows[0].data, retailerSku: '0007', variant: 'plain', pack: {value: 500, unit: 'g'},
    taxIncluded: null, unitPrice: 0, unit: 'kg', channel: 'in-store', language: 'fr',
    observationTimezone: 'Europe/Paris', promotion: false, loyalty: {required: false},
    serviceArea: 'synthetic-region', fulfilment: {mode: 'collection', shipping: null}};
  const expected = structuredClone(rows[0].data), stored = new Map();
  const env = {DB: {prepare(sql) {return {bind(...args) {return {
    first: async () => null,
    run: async () => {assert.match(sql, /ON CONFLICT\(owner,id\)/); stored.set(args[0] + ':' + args[1], JSON.parse(args[5]));}
  };}};}}};
  await storePrivateRecords(env, 'synthetic-owner', rows, {rightsConfirmed: true});
  await storePrivateRecords(env, 'synthetic-owner', rows, {rightsConfirmed: true});
  assert.equal(stored.size, 2);
  assert.deepEqual([...stored.values()][0].data, expected);
  assert.equal([...stored.values()][0].provenance.sourceId, 'personal-import');
  assert.equal([...stored.values()][0].provenance.privateUseConfirmed, true);
});
test('Open Prices native zero location ID remains a lexical join key, false/null/zero remain distinct', () => {
  const row = fixed.normalizePrices({items: [{id: 0, product_code: '00123', location_id: 0,
    price: 0, currency: 'JPY', date: '2026-10-01', price_is_discounted: false,
    price_per_unit: null, price_per: null}]}, {...source, id: 'prices'})[0];
  assert.equal(row.provenance.recordId, '0'); assert.equal(row.data.retailer.externalId, '0');
  assert.equal(row.data.identifiers[0].value, '00123'); assert.equal(row.data.amount, 0);
  assert.equal(row.data.promotion, false); assert.equal(row.data.unitPrice, null);
  assert.equal(row.data.availability, 'unknown'); assert.equal(row.data.priceType, 'dated-observation');
});
