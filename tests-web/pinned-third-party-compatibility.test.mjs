import test from 'node:test';
import assert from 'node:assert/strict';
import { composeSnapshots } from '../scripts/lib/third-party-compatibility.mjs';

const entry = (oid, mode = '100644') => ({ oid, mode, type: 'blob', commit: 'fixture' });
test('composition preserves new main paths and applies only the third-party delta, including deletions', () => {
  const base = new Map([['shared', entry('base')], ['removed', entry('old')]]);
  const main = new Map([...base, ['main-only', entry('new-main')]]);
  const third = new Map([['shared', entry('updated')], ['third-only', entry('new-third')]]);
  const result = composeSnapshots(base, main, third);
  assert.equal(result.entries.get('main-only').oid, 'new-main');
  assert.equal(result.entries.get('shared').oid, 'updated');
  assert.equal(result.entries.get('third-only').oid, 'new-third');
  assert.equal(result.entries.has('removed'), false);
  assert.equal(main.get('shared').oid, 'base');
  assert.equal(result.manifestSHA256, composeSnapshots(base, main, third).manifestSHA256);
});
test('distinct simultaneous edits, delete/edit and executable-mode conflicts fail closed', () => {
  const base = new Map([['shared', entry('base')]]);
  for (const third of [new Map([['shared', entry('third')]]), new Map(), new Map([['shared', entry('main', '100755')]])]) {
    assert.throws(() => composeSnapshots(base, new Map([['shared', entry('main')]]), third), /overlapping edits: shared/);
  }
});
test('identical edits can compose and mode-only changes affect the manifest receipt', () => {
  const base = new Map([['shared', entry('base')]]), changed = new Map([['shared', entry('new')]]);
  assert.equal(composeSnapshots(base, changed, changed).entries.get('shared').oid, 'new');
  assert.notEqual(composeSnapshots(base, base, changed).manifestSHA256,
    composeSnapshots(base, base, new Map([['shared', entry('new', '100755')]])).manifestSHA256);
});
