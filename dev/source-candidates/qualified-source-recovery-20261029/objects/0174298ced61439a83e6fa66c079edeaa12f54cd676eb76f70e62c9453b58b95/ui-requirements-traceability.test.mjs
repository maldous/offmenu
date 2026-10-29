import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
const matrix = JSON.parse(readFileSync(new URL('../docs/ui/requirements-traceability.json', import.meta.url)));
test('UI acceptance IDs and historical crosswalk are unique and resolvable', () => {
  const ids = new Set(matrix.requirements.map(row => row.id));
  assert.equal(ids.size, matrix.requirements.length);
  assert.equal(matrix.historicalCrosswalk.length, 105);
  assert.equal(new Set(matrix.historicalCrosswalk.map(row => row.legacyId)).size, 105);
  for (const row of matrix.historicalCrosswalk) {
    assert.ok(row.uiContracts.length);
    for (const id of row.uiContracts) assert.ok(ids.has(id), `${row.legacyId}: ${id}`);
  }
});
test('every contract carries scope, sources, owner and acceptance; verified routes need evidence', () => {
  for (const row of matrix.requirements) {
    for (const key of ['title','priority','applicability','disposition','existingCoverage','acceptanceCriteria','owner','playgroundArea','status']) assert.ok(row[key], `${row.id}: ${key}`);
    assert.ok(row.sources.length);
    for (const key of row.sources) assert.ok(new URL(matrix.sources[key]).protocol === 'https:');
    assert.ok(Array.isArray(row.evidence));
    if (row.status === 'accepted' || row.status === 'rendered-verified') {
      assert.ok(row.playgroundRoute);
      assert.ok(row.evidence.length, `${row.id}: no acceptance evidence`);
    }
  }
});
