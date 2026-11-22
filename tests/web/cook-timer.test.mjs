import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';
import vm from 'node:vm';

test('invalid restart reports native validity without replacing or interrupting completion', () => {
  const html=readFileSync(new URL('../../apps/web/assets/index.html',import.meta.url),'utf8');
  const input=html.match(/<input[^>]*id="timer-minutes"[^>]*>/)?.[0];
  assert.match(input,/\btype="number"/);
  assert.match(input,/\brequired\b/);
  assert.match(input,/\bmin="1"/);
  assert.match(input,/\bmax="240"/);
  const js=readFileSync(new URL('../../apps/web/src/journey-ui.js',import.meta.url),'utf8');
  const handlers=js.split('\n').find(line=>line.startsWith("$('timer-start').onclick="));
  const intervals=new Map(), controls={'timer-minutes':{},'timer-start':{},'timer-stop':{},'timer-status':{}};
  let now=0, id=0, reported=0;
  const duration=controls['timer-minutes'];
  duration.valueAsNumber=2;
  duration.reportValidity=()=>{reported++;return Number.isFinite(duration.valueAsNumber)&&Number.isInteger(duration.valueAsNumber)&&duration.valueAsNumber>=1&&duration.valueAsNumber<=240};
  vm.runInNewContext('let timer=null;'+handlers,{
    $:key=>controls[key], Date:{now:()=>now},
    setInterval:cb=>{intervals.set(++id,cb);return id},
    clearInterval:token=>intervals.delete(token),
    setLocalizedText:(target,text)=>{target.textContent=text},
  });
  const start=controls['timer-start'].onclick, status=controls['timer-status'];
  start();
  now=1000; intervals.get(1)(); assert.equal(status.textContent,'1:59');
  for(const invalid of [NaN,0,-1,1.5,241]){
    duration.valueAsNumber=invalid; start();
    assert.deepEqual([...intervals.keys()],[1]);
    assert.equal(status.textContent,'1:59');
  }
  assert.equal(reported,6);
  now=120000; intervals.get(1)(); assert.equal(status.textContent,'Timer finished. Check your food.');
  assert.equal(intervals.size,0);
  duration.valueAsNumber=1; start(); duration.valueAsNumber=3; start();
  assert.deepEqual([...intervals.keys()],[3]);
  controls['timer-stop'].onclick(); assert.equal(status.textContent,'Timer stopped');
  assert.equal(intervals.size,0);
});
