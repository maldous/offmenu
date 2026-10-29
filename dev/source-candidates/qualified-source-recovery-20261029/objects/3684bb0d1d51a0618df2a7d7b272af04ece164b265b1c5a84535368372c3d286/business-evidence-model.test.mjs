import test from 'node:test';
import assert from 'node:assert/strict';
import {ownershipPath, parseIdentifier} from '../public/evidence-model.js';
import {adaptBusinessEvidence, businessOwnershipPath} from '../public/business-evidence-model.js';

const now = Date.parse('2026-10-14T00:00:00Z');
const entities = [
  {id: 'company:child', kind: 'company', name: 'Example', matchStatus: 'verified'},
  {id: 'company:parent', kind: 'company', name: 'Example', matchStatus: 'verified'},
  {id: 'company:other', kind: 'company', matchStatus: 'verified'},
  {id: 'brand:one', kind: 'brand', matchStatus: 'verified'},
  {id: 'site:one', kind: 'site', matchStatus: 'verified'},
  {id: 'product:one', kind: 'product', matchStatus: 'verified'}
];
const row = overrides => ({id: 'e:one', subject: 'company:child', predicate: 'control', value: 'company:parent',
  sourceId: 'synthetic:source', sourceRecordId: '0007', sourceCountry: 'NZ', jurisdiction: 'AU', market: 'AU',
  scope: 'entity', issuer: 'synthetic:issuer', evidenceClass: 'declared', rightsRevision: 'synthetic/1',
  retrievedAt: '2026-10-01', validFrom: '2026-01-01', freshUntil: '2027-01-01', status: 'active', matchStatus: 'verified', ...overrides});
const model = (rows, ids = entities) => adaptBusinessEvidence({entities: ids, assertions: rows});
const path = (data, options = {}) => businessOwnershipPath(data, 'company:child', 'company:parent', {now, ...options});

test('only explicit admitted active assertion state can establish ownership', () => {
  for (const status of ['invalid', 'expired', 'superseded', 'rejected', 'unknown', 'future-state',
    'withdrawn', 'quarantined', 'pending', undefined, null, '', 'ACTIVE']) {
    const input = row({status});
    if (status === undefined) delete input.status;
    const before = structuredClone(input), data = model([input]);
    assert.deepEqual(data.assertions[0], input, 'original state and provenance retained');
    assert.deepEqual(input, before, 'source assertion untouched');
    assert.deepEqual(data.errors, [{id: input.id, reason: 'Assertion state is not explicitly admitted active'}]);
    assert.equal(path(data).status, 'unknown', `state ${String(status)}`);
    // The path boundary must also protect callers holding legacy/unadapted rows.
    assert.equal(path({entities, assertions: [input]}).status, 'unknown');
  }
  assert.equal(path(model([row()])).status, 'matched');
  assert.equal(path(model([row({matchStatus: 'candidate'})])).status, 'unknown');
});

test('unusable competing parent cannot suppress an active path in either input order', () => {
  for (const status of ['invalid', 'expired', 'superseded', 'rejected', 'unknown', 'future-state', undefined]) {
    const invalid = row({id: 'unusable', value: 'company:other', status});
    for (const rows of [[row(), invalid], [invalid, row()]]) {
      assert.deepEqual(path(model(rows)), {status: 'matched', path: ['e:one']});
      assert.deepEqual(path({entities, assertions: rows}), {status: 'matched', path: ['e:one']});
    }
  }
  assert.equal(path(model([row(), row({id: 'active-other', value: 'company:other'})])).status, 'unknown');
});

test('existing path already supports control, dates, minority opt-in and missing parents', () => {
  assert.equal(ownershipPath([row()], 'company:child', 'company:parent', {now}).status, 'matched');
  assert.equal(ownershipPath([row({validUntil: '2026-10-14'})], 'company:child', 'company:parent', {now}).status, 'unknown');
  assert.equal(ownershipPath([row({predicate: 'minority'})], 'company:child', 'company:parent', {now}).status, 'unknown');
  assert.equal(ownershipPath([row({predicate: 'minority'})], 'company:child', 'company:parent', {now, includeMinority: true}).status, 'matched');
  assert.equal(ownershipPath([], 'company:child', 'company:parent', {now}).status, 'unknown');
  assert.equal(parseIdentifier('4006381333931').origin, null);
});

test('adapter preserves exact identity and provenance without changing the input', () => {
  const input = {entities, assertions: [row()]}, before = JSON.stringify(input);
  const data = adaptBusinessEvidence(input);
  assert.deepEqual(data.errors, []);
  assert.deepEqual(data.assertions[0], row());
  assert.deepEqual(path(data, {market: 'AU', jurisdiction: 'AU'}), {status: 'matched', path: ['e:one']});
  assert.equal(JSON.stringify(input), before);
  assert.equal(path(data, {market: 'NZ'}).status, 'unknown');
  assert.equal(path(data, {jurisdiction: 'NZ'}).status, 'unknown');
});

test('malformed and impossible dates cannot become ownership evidence', () => {
  // Documents the old helper gap without changing its shared contract.
  assert.equal(ownershipPath([row({validUntil: 'bad'})], 'company:child', 'company:parent', {now}).status, 'matched');
  for (const field of ['validFrom', 'validUntil', 'freshUntil', 'retrievedAt', 'retainUntil']) {
    for (const value of ['bad', '2026-02-30', '']) {
      const data = model([row({[field]: value})]);
      assert.equal(data.errors.length, 1, `${field}: ${value}`);
      assert.equal(path(data).status, 'unknown');
    }
  }
  assert.equal(model([row({validUntil: '2025-01-01'})]).errors.length, 1);
});

test('time boundaries, withdrawal, quarantine and pending acquisition fail closed', () => {
  for (const change of [{validFrom: '2026-10-15'}, {validUntil: '2026-10-14'},
    {freshUntil: '2026-10-14'}, {retainUntil: '2026-10-14'},
    {status: 'withdrawn'}, {status: 'quarantined'}, {status: 'pending'}])
    assert.equal(path(model([row(change)])).status, 'unknown');
  assert.equal(path(model([row()]), {now: NaN}).status, 'unknown');
});

test('company, site, operating brand and origin stay separate from control', () => {
  const rows = [row({predicate: 'operating-brand', value: 'brand:one'}),
    row({id: 'site', subject: 'site:one', predicate: 'site-operator', value: 'company:parent'}),
    row({id: 'origin', subject: 'product:one', predicate: 'manufactured-in', value: 'CN'}),
    row({id: 'hq', predicate: 'headquartered-in', value: 'AU'})];
  const data = model(rows);
  assert.deepEqual(data.errors, []);
  assert.equal(data.assertions[2].value, 'CN');
  assert.equal(path(data).status, 'unknown');
  assert.equal(model([row({subject: 'site:one'})]).errors.length, 1);
  assert.equal(model([row({predicate: 'manufactured-in', value: 'CN'})]).errors.length, 1);
  for (const predicate of ['franchise', 'licence', 'minority'])
    assert.equal(path(model([row({predicate})])).status, 'unknown');
  assert.equal(path(model([row({predicate: 'minority'})]), {includeMinority: true}).status, 'matched');
});

test('missing parent, similar names and candidate identities never imply ultimate ownership', () => {
  assert.equal(path(model([])).status, 'unknown');
  assert.equal(model([row({value: 'Example'})]).errors.length, 1);
  assert.equal(path(model([row()], entities.map(entity => entity.id === 'company:parent'
    ? {...entity, matchStatus: 'candidate'} : entity))).status, 'unknown');
  assert.equal(path(model([row({matchStatus: 'candidate'})])).status, 'unknown');
  assert.equal(model([row({predicate: 'ultimate-owner'})]).errors.length, 1);
});

test('size retains fiscal year, entity/group basis, method and currency without an independence verdict', () => {
  const value = {metric: 'revenue', amount: 1200, unit: 'currency', currency: 'AUD', fiscalYear: '2025', basis: 'group', method: 'estimated'};
  const data = model([row({predicate: 'size', value})]);
  assert.deepEqual(data.errors, []);
  assert.deepEqual(data.assertions[0].value, value);
  assert.equal(path(data).status, 'unknown');
  for (const change of [{amount: -1}, {amount: Infinity}, {currency: ''}, {basis: ''}, {fiscalYear: '25'}, {method: ''}])
    assert.equal(model([row({predicate: 'size', value: {...value, ...change}})]).errors.length, 1);
});

test('duplicates, personal records, missing source and missing rights stay rejected', () => {
  assert.equal(model([row(), row()]).assertions.length, 0);
  assert.equal(model([row()], [...entities, entities[0]]).assertions.length, 0);
  for (const change of [{personal: true}, {sourceId: ''}, {rightsRevision: ''}, {jurisdiction: ''}])
    assert.equal(model([row(change)]).assertions.length, 0);
  assert.equal(model([row()], entities.map(entity => ({...entity, personal: true}))).assertions.length, 0);
});

test('contradictory parents cannot select an arbitrary path; cycles terminate', () => {
  assert.equal(path(model([row(), row({id: 'other', value: 'company:other'})])).status, 'unknown');
  const data = model([row({value: 'company:other'}), row({id: 'cycle', subject: 'company:other', value: 'company:child'})]);
  assert.equal(path(data).status, 'unknown');
  const chain = model([row({value: 'company:other'}), row({id: 'next', subject: 'company:other', value: 'company:parent', predicate: 'accounting-parent'})]);
  assert.deepEqual(path(chain).path, ['e:one', 'next']);
});
