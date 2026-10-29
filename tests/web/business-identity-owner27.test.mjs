import test from 'node:test';
import assert from 'node:assert/strict';
import {evaluateBusinessIdentity} from '../../apps/web/server/business-identity-owner27.mjs';
const ref = id => ({sourceId: 'synthetic:registry', recordId: id});
const common = {status: 'active', reviewStatus: 'admitted', matchStatus: 'verified', rightsRevision: 'fixture/1',
  sourceRecordId: 'record-proof', validFrom: '2026-01-01', freshUntil: '2027-01-01', jurisdiction: 'AU', market: 'AU'};
const identity = (id, extra = {}) => ({...common, ...ref(id), canonicalId: `company:${id}`, role: 'company', ...extra});
const edge = extra => ({...common, id: 'edge:1', sourceId: 'synthetic:filing', subject: ref('001'), object: ref('002'), predicate: 'control', ...extra});
const projection = (relationships = [edge()]) => ({identities: [identity('001'), identity('002'), identity('003')], relationships});
const options = {subject: ref('001'), target: ref('002'), now: Date.parse('2026-10-14'), jurisdiction: 'AU', market: 'AU'};
const run = (p, o = {}) => evaluateBusinessIdentity(p, {...options, ...o});

test('W09-BI-F1 accounting consolidation requires company roles on both sides', () => {
  const p = projection([edge({predicate: 'accounting-parent'})]);
  assert.equal(run(p).ownership.status, 'matched');
  p.identities[0] = identity('001', {canonicalId: 'brand:001', role: 'brand'});
  const result = run(p);
  assert.equal(result.ownership.status, 'unknown');
  assert.ok(result.errors.some(e => e.reason === 'Relationship role mismatch'));
  // A separately evidenced brand-control -> legal entity -> accounting parent remains valid.
  p.relationships = [edge({object: ref('003')}), edge({id: 'parent', subject: ref('003'), predicate: 'accounting-parent'})];
  assert.deepEqual(run(p).ownership.path, ['edge:1', 'parent']);
});

test('W09-BI-F2 minority opt-in accepts only literal Boolean true', () => {
  const p = projection([edge({predicate: 'minority'})]);
  for (const includeMinority of ['false', 'true', 1, 0, null, {}, [], false, undefined])
    assert.equal(run(p, {includeMinority}).ownership.status, 'unknown');
  assert.equal(run(p, {includeMinority: true}).ownership.status, 'matched');
});

test('source-qualified aliases preserve leading zeros, exact IDs and all relationship provenance', () => {
  const p = projection(), before = structuredClone(p), result = run(p);
  assert.deepEqual(result.ownership, {status: 'matched', path: ['edge:1']});
  assert.deepEqual(result.evidence[0].source, p.relationships[0]);
  assert.deepEqual(result.crosswalk[0].source, ref('001'));
  assert.deepEqual(p, before);
  assert.equal(run(p, {subject: ref('1')}).ownership.status, 'unknown');
  assert.equal(run(p, {subject: {...ref('001'), sourceId: 'another'}}).ownership.status, 'unknown');
});

test('unavailable states and missing admission never become control or suppress valid parent', () => {
  for (const status of [undefined, null, 'invalid', 'expired', 'superseded', 'rejected', 'unknown', 'future-state']) {
    assert.equal(run(projection([edge({status})])).ownership.status, 'unknown');
    const bad = edge({id: 'bad', status, object: ref('003')});
    for (const rows of [[edge(), bad], [bad, edge()]]) assert.equal(run(projection(rows)).ownership.status, 'matched');
  }
  for (const patch of [{reviewStatus: undefined}, {matchStatus: 'candidate'}, {rightsRevision: ''}, {personal: true}])
    assert.equal(run(projection([edge(patch)])).ownership.status, 'unknown');
});

test('dated identity mappings, conflicting roles and ambiguous aliases withhold resolution', () => {
  for (const patch of [{status: undefined}, {validFrom: '2026-10-15'}, {validUntil: '2026-10-14'},
    {freshUntil: '2026-10-14'}, {validFrom: '2026-02-30'}, {matchStatus: 'candidate'}]) {
    const p = projection(); p.identities[0] = identity('001', patch);
    assert.equal(run(p).ownership.status, 'unknown');
  }
  for (const extra of [identity('001', {canonicalId: 'company:003'}), identity('different', {canonicalId: 'company:001', role: 'site'})]) {
    const p = projection();p.identities.push(extra);assert.equal(run(p).ownership.status, 'unknown');
  }
});

test('relationship dates, explicit scope and duplicate IDs fail closed', () => {
  for (const patch of [{validFrom: 'bad'}, {validUntil: '2026-10-14'}, {freshUntil: '2026-10-14'}, {market: 'NZ'}, {jurisdiction: 'NZ'}])
    assert.equal(run(projection([edge(patch)])).ownership.status, 'unknown');
  assert.equal(run(projection([edge(), edge()])).ownership.status, 'unknown');
  assert.equal(run(projection(), {jurisdiction: ''}).ownership.status, 'unknown');
});

test('active conflicting parents, cycles and non-control roles never imply independence', () => {
  assert.equal(run(projection([edge(), edge({id: 'other', object: ref('003')})])).ownership.status, 'unknown');
  assert.equal(run(projection([edge({object: ref('003')}), edge({id: 'cycle', subject: ref('003'), object: ref('001')})])).ownership.status, 'unknown');
  for (const predicate of ['franchise', 'licence', 'minority', 'operating-brand', 'site-operator'])
    assert.equal(run(projection([edge({predicate})])).ownership.status, 'unknown');
  assert.equal(run(projection([edge({predicate: 'minority'})]), {includeMinority: true}).ownership.status, 'matched');
});

test('dataset discovery metadata is not an admissible identity projection', () => {
  assert.equal(run({dataset_id: 'indonesia-tkpi', qualification_status: 'blocked-metadata-only'}).ownership.status, 'unknown');
});
