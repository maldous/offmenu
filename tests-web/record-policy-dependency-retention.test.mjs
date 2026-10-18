import test from 'node:test';
import assert from 'node:assert/strict';
import {recordPermission} from '../public/record-policy.js';

const now = Date.parse('2026-10-18T00:00:00Z');
const record = (sourceId, dependencies) => ({kind:'food', provenance:{sourceId, dependencies}});
const policy = {active:true, version:'synthetic-policy/1', actions:['display','persist','export','derive'], audiences:['private']};

test('malformed dependency retention cannot authorize any existing action or permission route', () => {
  for (const action of policy.actions) for (const sourceId of ['off','personal-import','synthetic-provider']) {
    const options = {now, action, confirmed:true, ...(sourceId === 'synthetic-provider' ? {policy} : {})};
    const result = recordPermission(record(sourceId, [{allowed:true, retainUntil:'not-a-date'}]), options);
    assert.equal(result.allowed, false, `${sourceId}: ${action}`);
    assert.equal(result.reason, 'An input dependency does not permit reuse');
  }
});

test('dependency expiry includes the exact boundary and every dependency', () => {
  for (const retainUntil of ['2026-10-17T23:59:59Z','2026-10-18T00:00:00Z','invalid']) {
    assert.equal(recordPermission(record('off', [{allowed:true}, {allowed:true, retainUntil}]), {now}).allowed, false);
  }
});

test('unexpired and untimed permitted inputs retain the existing decision and do not mutate', () => {
  const input = record('off', [{allowed:true}, {allowed:true, retainUntil:'2026-10-18T00:00:01Z'}]);
  const before = structuredClone(input);
  for (const dependency of input.provenance.dependencies) Object.freeze(dependency);
  Object.freeze(input.provenance.dependencies); Object.freeze(input.provenance); Object.freeze(input);
  assert.equal(recordPermission(input, {now}).allowed, true);
  assert.deepEqual(input, before);
});

test('unknown dependency permission and restricted sources remain denied', () => {
  for (const allowed of [false, undefined, 'true']) {
    assert.equal(recordPermission(record('off', [{allowed, retainUntil:'2026-10-19T00:00:00Z'}]), {now}).allowed, false);
  }
  assert.equal(recordPermission(record('synthetic-provider', [{allowed:true}]), {now, confirmed:true}).allowed, false);
  assert.equal(recordPermission({kind:'food', provenance:{sourceId:'off', retainUntil:'invalid'}}, {now}).allowed, false);
});
