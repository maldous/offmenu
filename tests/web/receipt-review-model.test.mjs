import test from 'node:test';
import assert from 'node:assert/strict';
import {finishInventory} from '../../public/checkout-model.js';
import {prepareReceipt, reviewReceipt, receiptRetentionPlan} from '../../public/receipt-review-model.js';

const context = (overrides = {}) => ({accountId: 'account-a', now: 100,
  consent: {accountId: 'account-a', receiptReview: true, expiresAt: 500},
  rights: {sourceId: 'private-receipt', privateUse: true, expiresAt: 500}, ...overrides});
const input = () => ({accountId: 'account-a', sourceId: 'private-receipt', contentDigest: 'synthetic-exact-byte-digest', retainUntil: 400,
  ocr: {lines: [{id: 'line-1', originalText: 'R1CE 2 ?', name: 'R1CE', quantity: 2, unit: null, confidence: 0.4},
    {id: 'line-2', originalText: 'TOTAL 12', name: 'TOTAL', quantity: 12, unit: null}]}});
const review = () => ({confirmed: true, lines: [{id: 'line-1', decision: 'include', name: 'Rice', quantity: 2, unit: null}, {id: 'line-2', decision: 'exclude'}]});
const draft = () => prepareReceipt(input(), context());

test('shopping receipt replay is rejected and review blocks the same source bytes', () => {
  const s = {mode: 'shopping', area: 'Pantry', shelf: 'Top', items: [{id: 'receipt-line-1', quantity: 2, unit: 'count'}]};
  const stock=finishInventory([],s);assert.equal(stock.length,1);assert.throws(()=>finishInventory(stock,s),/Duplicate checkout items/);assert.equal(stock.length,1);
  const first = reviewReceipt(draft(), review(), [], context());
  const replay = reviewReceipt(draft(), review(), [first.ledgerEntry], context());
  assert.deepEqual(replay, {status: 'duplicate', receipt: null, ledgerEntry: null});
});

test('review corrects fields, preserves source quantities and uncertainty, and infers no stock authority', () => {
  const source = input();
  source.ocr.lines[0].expires = '2099-01-01';
  source.ocr.lines[0].allergenSafe = true;
  const before = structuredClone(source);
  const d = prepareReceipt(source, context());
  const r = review();
  const result = reviewReceipt(d, r, [], context());
  assert.deepEqual(source, before);
  assert.equal(d.status, 'needs-review');
  const line = result.receipt.lines[0];
  assert.deepEqual(line.extracted, {name: 'R1CE', quantity: 2, unit: null});
  assert.deepEqual(line.reviewed, {name: 'Rice', quantity: 2, unit: null});
  assert.equal(line.originalText, 'R1CE 2 ?');
  assert.equal(line.confidence, 0.4);
  assert.equal(result.receipt.lines[1].reviewed, null);
  assert.equal('expires' in line, false);
  assert.equal('allergenSafe' in line, false);
  assert.equal(result.receipt.rights.sharedPublication, false);
  r.lines[0].name = 'changed';
  d.lines[0].extracted.quantity = 99;
  assert.equal(line.extracted.quantity, 2);
  assert.equal(line.reviewed.name, 'Rice');
});

test('missing quantity remains unknown; included line is not automatically an inventory lot', () => {
  const r = review(); r.lines[0].quantity = null;
  const result = reviewReceipt(draft(), r, [], context());
  assert.equal(result.receipt.lines[0].reviewed.quantity, null);
  assert.equal('inventory' in result, false);
});

test('every line requires an explicit decision and confirmation', () => {
  assert.throws(() => reviewReceipt(draft(), {...review(), confirmed: false}, [], context()), /Explicit/);
  assert.throws(() => reviewReceipt(draft(), {confirmed: true, lines: [review().lines[0]]}, [], context()), /every/);
  const r = review(); r.lines[1].id = 'line-1';
  assert.throws(() => reviewReceipt(draft(), r, [], context()), /Duplicate/);
  const bad = review(); bad.lines[0].quantity = -1;
  assert.throws(() => reviewReceipt(draft(), bad, [], context()), /quantity/);
});

test('account scope, current consent and current rights fail closed at preparation and review', () => {
  for (const ctx of [context({accountId: 'account-b'}), context({consent: null}), context({rights: null}),
    context({consent: {...context().consent, expiresAt: 100}}), context({rights: {...context().rights, privateUse: false}})]) {
    assert.throws(() => prepareReceipt(input(), ctx));
    assert.throws(() => reviewReceipt(draft(), review(), [], ctx));
  }
  assert.throws(() => reviewReceipt(draft(), review(), [], context({now: 400})), /retention/);
});

test('duplicate scope preserves account and source identity, not guessed names or normalized quantities', () => {
  const entry = reviewReceipt(draft(), review(), [], context()).ledgerEntry;
  for (const other of [{...entry, accountId: 'account-b'}, {...entry, sourceId: 'other'}, {...entry, contentDigest: 'other-bytes'}])
    assert.equal(reviewReceipt(draft(), review(), [other], context()).status, 'reviewed');
});

test('images are absent by default; retention requires separate consent and never outlives receipt', () => {
  assert.equal(draft().image, null);
  const i = {...input(), image: {id: 'image-1', retainUntil: 200, pixels: 'not copied'}};
  assert.throws(() => prepareReceipt(i, context()), /image consent/);
  const c = context({consent: {...context().consent, retainImage: true}});
  const d = prepareReceipt(i, c);
  assert.deepEqual(d.image, {id: 'image-1', retainUntil: 200});
  assert.throws(() => prepareReceipt({...i, image: {...i.image, retainUntil: 401}}, c), /bounded/);
  assert.deepEqual(receiptRetentionPlan(d, {accountId: 'account-a', now: 200, retainImage: true}),
    {deleteReceipt: false, deleteLedger: false, deleteImage: true});
  const reviewed = reviewReceipt(d, review(), [], {...c, now: 200});
  assert.equal(reviewed.receipt.image, null);
  assert.equal(reviewed.retention.deleteImage, true);
  assert.deepEqual(receiptRetentionPlan(d, {accountId: 'account-a', now: 101, withdrawn: true}),
    {deleteReceipt: true, deleteLedger: true, deleteImage: true});
  assert.deepEqual(receiptRetentionPlan(d, {accountId: 'account-a', now: 400, retainImage: true}),
    {deleteReceipt: true, deleteLedger: true, deleteImage: true});
  assert.throws(() => receiptRetentionPlan(d, {accountId: 'account-b', now: 100}));
});

test('bounded extraction rejects duplicate source identities and invalid confidence', () => {
  const i = input(); i.ocr.lines[1].id = 'line-1';
  assert.throws(() => prepareReceipt(i, context()), /Duplicate/);
  const huge = input(); huge.ocr.lines = Array.from({length: 201}, (_, n) => ({...huge.ocr.lines[0], id: String(n)}));
  assert.throws(() => prepareReceipt(huge, context()), /1–200/);
  const bad = input(); bad.ocr.lines[0].confidence = NaN;
  assert.throws(() => prepareReceipt(bad, context()), /confidence/);
});
