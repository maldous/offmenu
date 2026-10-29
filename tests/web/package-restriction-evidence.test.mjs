import test from 'node:test';
import assert from 'node:assert/strict';
import {qualify} from '../../apps/web/src/evidence-model.js';
import {packageRestrictionEvidence} from '../../apps/web/src/package-restriction-evidence.js';

const now = Date.parse('2026-10-14T06:40:59.087Z');
const rule = {predicate: 'halal', operator: 'include', value: true, certifiedOnly: true};
const target = {kind: 'lot', subject: 'supplier:product:001', lotCode: 'B', owner: 'account-a', quantity: 2, unit: 'pack'};
const row = {id: 'supplier:assertion:7', sourceId: 'supplier', subject: target.subject, owner: target.owner,
  market: 'AU', scope: {kind: 'lot', lotCode: 'B'}, predicate: 'halal', value: true,
  matchStatus: 'verified', evidenceClass: 'certified', schemeId: 'scheme:1', certifierId: 'certifier:1',
  validFrom: '2026-10-01', validUntil: '2026-11-01', freshUntil: '2026-10-20'};
const policy = {active: true, actions: ['display', 'derive'], audiences: ['private'], countries: ['AU']};
const input = () => ({rule, target, evidence: [structuredClone(row)], policies: {supplier: policy},
  owner: 'account-a', consent: true, market: 'AU', now});
const evaluate = patch => packageRestrictionEvidence({...input(), ...patch});

test('negative baseline: existing evaluator passes another lot; adapter withholds it', () => {
  const otherLot = {...row, scope: {kind: 'lot', lotCode: 'A'}};
  assert.equal(qualify(rule, [otherLot], {subject: target.subject, market: 'AU', now}).status, 'pass');
  assert.equal(evaluate({evidence: [otherLot]}).status, 'unknown');
});
test('exact binding preserves source identity and inputs, without selection clearance', () => {
  const args = input(), before = structuredClone(args);
  const result = packageRestrictionEvidence(args);
  assert.equal(result.status, 'pass');
  assert.deepEqual(result.evidenceIds, [row.id]);
  assert.equal(result.automaticSelection, false);
  assert.deepEqual(args, before);
});
test('no concept, package, other product, market or missing lot inheritance', () => {
  for (const patch of [{scope: {kind: 'concept'}}, {scope: {kind: 'package'}}, {subject: 'other'},
    {market: 'GB'}, {scope: {kind: 'lot'}}, {matchStatus: 'candidate'}])
    assert.equal(evaluate({evidence: [{...row, ...patch}]}).status, 'unknown');
  assert.equal(evaluate({target: {...target, lotCode: null}}).status, 'unknown');
  assert.equal(evaluate({evidence: [], target: {...target, tags: ['halal']}}).status, 'unknown');
});
test('package and menu scope are explicit and never borrowed between menu items', () => {
  for (const binding of [{kind: 'package'}, {kind: 'menu', menuId: 'menu-1', menuItemId: 'item-1'}]) {
    const t = {...target, ...binding}, assertion = {...row, scope: binding};
    assert.equal(evaluate({target: t, evidence: [assertion]}).status, 'pass');
    if (binding.kind === 'menu') assert.equal(evaluate({target: {...t, menuItemId: 'item-2'}, evidence: [assertion]}).status, 'unknown');
  }
});
test('account, consent and rights fail closed independently of positive claims', () => {
  for (const patch of [{owner: 'account-b'}, {consent: false}, {consent: undefined}, {policies: {}},
    {policies: {supplier: {...policy, active: false}}}, {policies: {supplier: {...policy, actions: ['promote']}}},
    {policies: {supplier: {...policy, expiresAt: 'invalid'}}}, {now: undefined}, {policies: null},
    {policies: {supplier: {...policy, actions: ['display']}}}])
    assert.equal(evaluate(patch).status, 'unknown');
  for (const patch of [{owner: 'account-b'}, {dependencies: [{allowed: false}]}, {retainUntil: '2026-10-14'},
    {status: 'withdrawn'}, {status: 'quarantined'}, {dependencies: [null]},
    {dependencies: [{allowed: true, retainUntil: '2026-10-14'}]}])
    assert.equal(evaluate({evidence: [{...row, ...patch}]}).status, 'unknown');
});
test('invalid, future, stale and expired dates do not establish current evidence', () => {
  for (const patch of [{validFrom: 'invalid'}, {validFrom: '2026-11-01'}, {validUntil: '2026-10-14'},
    {freshUntil: '2026-10-14'}, {freshUntil: 'invalid'}, {retainUntil: 'invalid'},
    {freshUntil: null}, {validFrom: null}, {validUntil: null}])
    assert.equal(evaluate({evidence: [{...row, ...patch}]}).status, 'unknown');
});
test('conflict and negative evidence remain adverse; missing certification stays unknown', () => {
  assert.equal(evaluate({evidence: [row, {...row, id: 'supplier:assertion:8', value: false}]}).status, 'conflict');
  assert.equal(evaluate({evidence: [{...row, value: false}]}).status, 'fail');
  for (const patch of [{evidenceClass: 'label'}, {schemeId: null}, {certifierId: null}, {value: null}])
    assert.equal(evaluate({evidence: [{...row, ...patch}]}).status, 'unknown');
  assert.equal(evaluate({evidence: []}).status, 'unknown');
  assert.equal(evaluate({rule: {...rule, operator: 'exclude'}, evidence: []}).status, 'unknown');
});
test('bounded input and explicit operators; no interpretation of absent values', () => {
  assert.equal(evaluate({evidence: Array(201).fill(row)}).status, 'unknown');
  assert.equal(evaluate({rule: {...rule, operator: 'anything'}}).status, 'unknown');
  assert.equal(evaluate({rule: {...rule, value: undefined}}).status, 'unknown');
});
