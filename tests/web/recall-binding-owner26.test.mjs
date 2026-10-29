import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import { createRecallConsumer, RECALL_HELPER_PIN } from '../../apps/web/src/recall-binding-owner26.mjs';

// Execute the selected integrated helper, verifying its retained exact bytes.
const helper=readFileSync(new URL('../../apps/web/src/recall-scope-model.js',import.meta.url));
assert.equal(createHash('sha1').update(`blob ${helper.length}\0`).update(helper).digest('hex'),'d83cdd7acb64b9ccece7549df2868fb29efc31b9');
assert.equal(RECALL_HELPER_PIN,'643c130eed6d4d64a7e755d6c233128fa978aaa8');
const {evaluateRecallScope}=await import('../../apps/web/src/recall-scope-model.js');
const consume = createRecallConsumer({ evaluateScope: evaluateRecallScope, helperPin: RECALL_HELPER_PIN, independentlyReviewed: true });
const asOf = '2026-10-14T06:00:00.100Z';
const lot = { id: 'lot-A', productId: 'product', productVersion: 'v1', barcode: '4006381333931', market: 'AU', lotCode: 'A', labelVersion: 'v1' };
function envelope() {
 const notice = { id: 'notice', provenance: { sourceId: 'synthetic', recordId: 'record', url: 'https://regulator.invalid/notice', retrievedAt: '2026-10-14T05:00:00Z' }, action: { type: 'recall', regulator: 'synthetic' }, evidence: { kind: 'current', validFrom: '2026-10-13T00:00:00Z', freshUntil: '2026-10-15T00:00:00Z' }, scope: { gtin: lot.barcode, markets: ['AU'], lots: ['A'], labelVersions: ['v1'] } };
 return { notice, sourceVersion: 's1', recordVersion: 'r1', policy: { sourceId: 'synthetic', sourceVersion: 's1', active: true, actions: ['display'], audiences: ['public'], countries: ['AU'], expiresAt: '2026-10-15T00:00:00Z' }, assertion: { sourceId: 'synthetic', recordId: 'record', sourceVersion: 's1', recordVersion: 'r1', status: 'active', personal: false, matchStatus: 'verified' }, review: { status: 'accepted', scopeComplete: true, conflictFree: true, checkedAt: '2026-10-14T05:00:00Z', freshUntil: '2026-10-15T00:00:00Z', sourceId: 'synthetic', sourceVersion: 's1', recordId: 'record', recordVersion: 'r1', noticeId: 'notice', productId: lot.productId, productVersion: lot.productVersion, lotId: lot.id } };
}
const run = (e = envelope(), l = lot, time = asOf) => consume({ lots: [l], notices: [e], asOf: time })[0];
test('consumer entrypoint emits actionable review with source evidence, never safety or selection', () => {
 const result = run(); assert.equal(result.decision, 'recall-match-review'); assert.equal(result.results[0].evidence.provenance.sourceId, 'synthetic');
 assert.equal(result.safety, 'unknown'); assert.equal(result.automaticSelection, false);
});
test('no notices and excluded notice cannot assert safe', () => {
 const empty = consume({ lots: [lot], notices: [], asOf })[0]; assert.equal(empty.decision, 'no-applicable-notice-established'); assert.equal(empty.safety, 'unknown');
 const e = envelope(); e.notice.scope.lots = ['B']; const result = run(e); assert.equal(result.results[0].decision, 'outside-this-notice'); assert.equal(result.safety, 'unknown');
});
test('every source, record, product and lot binding is required and exact', () => {
 for (const key of ['sourceId','sourceVersion','recordId','recordVersion','noticeId','productId','productVersion','lotId']) {
  const e = envelope(); e.review[key] = 'wrong'; assert.equal(run(e).decision, 'needs-review', key);
 }
 for (const key of ['sourceVersion','recordVersion']) { const e = envelope(); delete e[key]; assert.equal(run(e).decision, 'needs-review'); }
});
test('permissions and owner review cannot come from metadata-only CSV or stale review', () => {
 for (const mutate of [e=>e.policy.active=false,e=>e.assertion.status='withdrawn',e=>e.assertion.personal=true,e=>e.review.scopeComplete=false,e=>e.review.conflictFree=false,e=>e.review.freshUntil=asOf,e=>e.policy.sourceVersion='other',e=>delete e.review]) {
  const e=envelope();mutate(e);assert.equal(run(e).decision,'needs-review');
 }
});
test('historical, incomplete market and submillisecond instants are review decisions', () => {
 const e=envelope();e.notice.evidence.kind='historical';assert.equal(run(e).decision,'needs-review');
 assert.equal(run(envelope(),{...lot,market:undefined}).decision,'needs-review');
 for(const field of ['checkedAt','freshUntil']) { const e=envelope();e.review[field]='2026-10-14T05:00:00.0001Z';assert.equal(run(e).decision,'needs-review'); }
 assert.equal(run(envelope(),lot,'2026-10-14T06:00:00.0001Z').decision,'needs-review');
});
test('dependency gate, mixed unknowns and source snapshot isolation', () => {
 for(const cfg of [{},{evaluateScope:evaluateRecallScope,helperPin:'wrong',independentlyReviewed:true},{evaluateScope:evaluateRecallScope,helperPin:RECALL_HELPER_PIN,independentlyReviewed:false}]) {
  assert.equal(createRecallConsumer(cfg)({lots:[lot],notices:[],asOf})[0].decision,'needs-review');
 }
 const e=envelope(),before=structuredClone(e);const result=run(e);result.results[0].evidence.provenance.sourceId='changed';assert.deepEqual(e,before);
 const excluded=envelope();excluded.notice.scope.lots=['B'];const unresolved=envelope();delete unresolved.review;
 assert.equal(consume({lots:[lot],notices:[excluded,unresolved],asOf})[0].decision,'needs-review');
});
