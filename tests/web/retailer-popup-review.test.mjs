import assert from 'node:assert/strict';
import test from 'node:test';

let instance = 0;
const product = name => [{result: {url: 'https://retailer.example/test', blocks: [
  JSON.stringify({'@type':'Product', name, sku:name}),
]}}];

function element() {
  return {
    children: [], textContent: '', checked: false, disabled: false,
    append(...nodes) {this.children.push(...nodes);},
    replaceChildren(...nodes) {this.children = nodes;},
  };
}

async function harness(t) {
  const nodes = Object.fromEntries(['read','confirm','download','review','status'].map(key => [key,element()]));
  nodes.download.disabled = true;
  const runs = [], blobs = [], clicks = [];
  const doc = {
    documentElement: {dataset:{}}, querySelector: () => null, querySelectorAll: () => [],
    getElementById: id => nodes[id],
    createElement(tag) {
      const node = element();
      if (tag === 'a') node.click = () => clicks.push(node.download);
      return node;
    },
  };
  const chromeStub = {tabs:{query:async () => [{id:1}]}, scripting:{
    executeScript: async () => new Promise((resolve,reject) => runs.push({resolve,reject})),
  }};
  for (const [key,value] of Object.entries({document:doc,chrome:chromeStub})) {
    const old = Object.getOwnPropertyDescriptor(globalThis,key);
    Object.defineProperty(globalThis,key,{value,configurable:true});
    t.after(() => {if(old)Object.defineProperty(globalThis,key,old);else delete globalThis[key];});
  }
  t.mock.method(URL,'createObjectURL', blob => {blobs.push(blob);return 'blob:test';});
  t.mock.method(URL,'revokeObjectURL', () => {});
  await import('../../apps/retailer-extension/popup-source.js?test=' + (++instance));
  async function start() {
    const finished = nodes.read.onclick();
    await Promise.resolve(); // pass the synthetic tab query
    const run = runs.shift();
    assert.ok(run,'current read reached its synthetic page');
    return {...run,finished};
  }
  function confirm() {nodes.confirm.checked=true;nodes.confirm.onchange();}
  return {nodes,blobs,clicks,start,confirm};
}

test('successful review exports only the confirmed records; unchecking bars another download',async t => {
  const {nodes,clicks,blobs,start,confirm}=await harness(t);
  const read=await start(); read.resolve(product('first')); await read.finished;
  assert.equal(nodes.review.children.length,1);
  assert.equal(nodes.download.disabled,true);
  nodes.download.onclick(); // the handler also enforces consent; no UI bypass
  assert.equal(clicks.length,0);
  confirm(); nodes.download.onclick();
  assert.deepEqual(clicks,['offmenu-retailer-import.json']);
  assert.deepEqual(JSON.parse(await blobs[0].text()).records.map(r=>r.data.name),['first']);
  nodes.confirm.checked=false; nodes.confirm.onchange(); nodes.download.onclick();
  assert.equal(clicks.length,1);
});

test('starting another read clears prior review before it resolves; failure cannot export stale data',async t=>{
  const {nodes,clicks,start,confirm}=await harness(t);
  const first=await start(); first.resolve(product('prior')); await first.finished; confirm();
  const second=await start();
  assert.equal(nodes.review.children.length,0);
  assert.equal(nodes.confirm.checked,false);
  assert.equal(nodes.download.disabled,true);
  confirm(); nodes.download.onclick(); assert.equal(clicks.length,0);
  second.reject(new Error('synthetic failure')); await second.finished;
  assert.match(nodes.status.textContent,/unable to read/i);
  assert.equal(nodes.confirm.checked,false);
  nodes.download.onclick(); assert.equal(clicks.length,0);
});

test('superseded responses cannot replace newer results, controls or status',async t=>{
  const {nodes,blobs,start,confirm}=await harness(t);
  const slow=await start(), failed=await start(), current=await start();
  current.resolve(product('latest')); await current.finished; confirm();
  const status=nodes.status.textContent;
  failed.reject(new Error('late failure')); await failed.finished;
  slow.resolve(product('superseded')); await slow.finished;
  assert.equal(nodes.status.textContent,status);
  assert.equal(nodes.confirm.checked,true);
  assert.equal(nodes.review.children[0].children[0].textContent,'latest');
  nodes.download.onclick();
  assert.deepEqual(JSON.parse(await blobs[0].text()).records.map(r=>r.data.name),['latest']);
});

test('empty extraction clears approval and never enables an export', async t=>{
  const {nodes,clicks,start,confirm}=await harness(t);
  const first=await start(); first.resolve(product('prior')); await first.finished; confirm();
  const empty=await start(); empty.resolve([{result:{url:'https://retailer.example/none',blocks:[]}}]); await empty.finished;
  assert.equal(nodes.review.children.length,0);
  assert.equal(nodes.confirm.checked,false);
  assert.match(nodes.status.textContent,/no supported/i);
  confirm();nodes.download.onclick();assert.equal(clicks.length,0);
});
