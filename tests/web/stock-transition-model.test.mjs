import test from 'node:test';
import assert from 'node:assert/strict';
import {validateLot} from '../../apps/web/src/model.js';
import {finishInventory} from '../../apps/web/src/checkout-model.js';
import {transitionStock} from '../../apps/web/src/stock-transition-model.js';

const at = '2026-10-14T06:40:46.000Z';
const lot = () => ({id:'lot-a',barcode:'12345678',name:'Milk',ingredient:'milk',quantity:125.5,
  unit:'ml',expires:null,needsReview:true,location:{area:'Fridge',shelf:'Top'},
  provenance:{sourceId:'synthetic-label',rights:'unknown',consent:'private'},
  nutrition:null,allergens:null});
const state = () => ({accountId:'account-a',inventory:[lot(),{...lot(),id:'lot-b'}],events:[]});
const command = (s, action, extra = {}) => ({accountId:s.accountId,lotId:'lot-a',
  expectedLot:structuredClone(s.inventory[0]),expectedEventCount:s.events.length,
  eventId:`event-${s.events.length}`,action,confirmed:true,...extra});
const apply = (s, action, extra) => transitionStock(s,command(s,action,extra),{clock:()=>at});

test('baseline gap: lot validation discards transitions; waste removes quantity', () => {
  const source = {...lot(),openedAt:at,frozenAt:at,containerId:'jar'};
  const projected = validateLot(source);
  for (const key of ['openedAt','frozenAt','containerId']) assert.equal(key in projected,false);
  const removed = finishInventory([source],{mode:'waste',area:'Fridge',shelf:'Top',
    items:[{...source,discardQuantity:25.5}]});
  assert.equal(removed[0].quantity,100); // Waste cannot substitute for a quantity-preserving transition.
});

test('opened/frozen/thawed/decanted preserve every lot field and uncertain dates', () => {
  const initial = state(), snapshot = structuredClone(initial);
  let next = initial;
  for (const action of ['opened','frozen','thawed','decanted'])
    next = apply(next,action,action==='decanted'?{containerId:'jar-1'}:{});
  assert.deepEqual(next.inventory,initial.inventory);
  assert.deepEqual(initial,snapshot);
  assert.equal(next.events.length,4);
  assert.ok(next.events.every(e=>e.lotId==='lot-a' && e.accountId==='account-a' && e.at===at));
  assert.equal(next.events[3].containerId,'jar-1');
  next.inventory[0].provenance.rights='changed';
  assert.equal(initial.inventory[0].provenance.rights,'unknown');
});

test('label dates and reminders are preserved even when already past', () => {
  const s=state(); Object.assign(s.inventory[0],{expires:'2026-10-01',dateType:'best-before',
    freshnessReminder:'2026-10-02',freshnessDays:2,freshnessNote:'User chosen'});
  assert.deepEqual(apply(s,'frozen').inventory,s.inventory);
});

test('unknown thermal state, repeated open/freeze and missing destination reject', () => {
  assert.throws(()=>apply(state(),'thawed'),/No recorded frozen state/);
  assert.throws(()=>apply(apply(state(),'opened'),'opened'),/already recorded/);
  assert.throws(()=>apply(apply(state(),'frozen'),'frozen'),/already recorded/);
  assert.throws(()=>apply(state(),'decanted'),/container/);
  assert.equal(apply(apply(apply(state(),'frozen'),'thawed'),'frozen').events.length,3);
});

test('scope, consent, stale snapshot/history, identity and quantity guards', () => {
  const s=state();
  for (const change of [{accountId:'other'},{confirmed:false},{action:'consume'},
    {lotId:'missing'},{expectedLot:{...lot(),quantity:100}},{expectedEventCount:1}])
    assert.throws(()=>apply(s,'opened',change));
  const changed=state(); changed.inventory[0].provenance.rights='CC0';
  assert.throws(()=>transitionStock(changed,command(s,'opened'),{clock:()=>at}),/changed/);
  const duplicate=state(); duplicate.inventory[1].id='lot-a';
  assert.throws(()=>apply(duplicate,'opened'),/duplicate/);
  const empty=state(); empty.inventory[0].quantity=0;
  assert.throws(()=>apply(empty,'opened'),/changed/);
});

test('clock, journal bounds, cross-account events and replay guard', () => {
  const s=state();
  assert.throws(()=>transitionStock(s,command(s,'opened')),/clock/);
  for (const value of ['tomorrow','2026-02-30T00:00:00.000Z'])
    assert.throws(()=>transitionStock(s,command(s,'opened'),{clock:()=>value}),/timestamp/);
  const next=apply(s,'opened');
  assert.throws(()=>apply(next,'frozen',{eventId:'event-0'}),/new supported/);
  assert.throws(()=>transitionStock(next,command(next,'frozen'),
    {clock:()=> '2026-10-13T00:00:00.000Z'}),/precedes/);
  next.events[0].accountId='other'; assert.throws(()=>apply(next,'frozen'),/journal/);
  const full=state(); full.events=Array(1000).fill({});
  assert.throws(()=>apply(full,'opened'),/full/);
});
