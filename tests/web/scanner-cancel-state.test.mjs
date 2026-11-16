import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../../apps/web/src/shelf-scanner.js', import.meta.url), 'utf8');

// Exercise the real two wired callbacks, not a copy of their state updates.
// This is a bounded source-callback contract, not a rendered dialog/camera test.
function callback(kind) {
  const pattern = kind === 'button'
    ? /\$\('close-mode'\)\.onclick=(\(\)=>\{[^}]*\});/
    : /\$\('mode-dialog'\)\.addEventListener\('cancel',(\(\)=>\{[^}]*\})\);/;
  const match = source.match(pattern);
  assert.ok(match, `Expected the selected ${kind} callback; update this bounded harness if its shape changes`);
  return match[1];
}

function cancel(kind, initial = {}) {
  const events = [];
  const state = {
    active: false, paused: false, finished: true,
    mode: 'Explore', connection: 'live', generation: 7,
    queue: [{id:'retained-capture'}], ...initial,
  };
  const queue = state.queue;
  state.close = id => events.push({kind:'close', id});
  state.render = () => events.push({kind:'render', active:state.active, paused:state.paused, finished:state.finished});
  state.scanner = {start:() => events.push({kind:'start'}), stop:() => events.push({kind:'stop'})};
  vm.runInNewContext(`(${callback(kind)})()`, state, {timeout:100});
  return {state, events, queue};
}

test('scanner Cancel button clears stale finished status before capture resumes', () => {
  const {state, events} = cancel('button');
  assert.equal(state.active, true);
  assert.equal(state.paused, false);
  assert.equal(state.finished, false);
  assert.deepEqual(events, [
    {kind:'close', id:'mode-dialog'},
    {kind:'render', active:true, paused:false, finished:false},
    {kind:'start'},
  ]);
});

test('scanner native dialog cancel clears stale finished status before capture resumes', () => {
  const {state, events} = cancel('native');
  assert.equal(state.active, true);
  assert.equal(state.paused, false);
  assert.equal(state.finished, false);
  assert.deepEqual(events, [
    {kind:'render', active:true, paused:false, finished:false},
    {kind:'start'},
  ]);
});

test('scanner cancel paths retain current mode connection and captured events', () => {
  for (const kind of ['button', 'native']) {
    const {state, events, queue} = cancel(kind, {finished:false, paused:true});
    assert.equal(state.finished, false);
    assert.equal(state.active, true);
    assert.equal(state.paused, false);
    assert.equal(state.mode, 'Explore');
    assert.equal(state.connection, 'live');
    assert.equal(state.generation, 7);
    assert.equal(state.queue, queue);
    assert.deepEqual(state.queue, [{id:'retained-capture'}]);
    assert.equal(events.filter(event => event.kind === 'start').length, 1);
    assert.equal(events.some(event => event.kind === 'stop'), false);
  }
});
