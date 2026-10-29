import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {wasteInsight} from '../../public/integration-owner03.mjs';
import {setupInsights} from '../../public/insights-ui.js';
import {finishInventory} from '../../public/checkout-model.js';
import {validateState} from '../../cloud/state.mjs';
import {setLanguage,formatNumber} from '../../public/i18n.js';

const today='2026-10-14',dates=[today];
const context={accountId:'account-a',sessionEpoch:'epoch-1',consent:true,canReadWasteObservations:true};
const lot={id:'lot-1',barcode:'12345678',name:'Rice',ingredient:'rice',quantity:500,unit:'g',location:{area:'Bench',shelf:'Bowl'}};
const receipt={id:'receipt-1',mode:'waste',area:'Bench',shelf:'Bowl',startedAt:today+'T09:00:00.000Z',finishedAt:today+'T10:00:00.000Z',items:[{...lot,discardQuantity:125}]};
const observation={id:'obs-1',accountId:'account-a',receiptId:'receipt-1',sourceId:'lot-1',observedAt:receipt.finishedAt,quantity:125,unit:'g',reason:null,provenance:{sourceRef:'receipt-1/lot-1',method:'measured'}};

test('normal locale inventory includes consumer display templates and fallback diagnostics',()=>{
  const english=JSON.parse(readFileSync(new URL('../../public/locales/en.json',import.meta.url),'utf8'));
  const coverage=JSON.parse(readFileSync(new URL('../../docs/i18n-coverage.json',import.meta.url),'utf8'));
  for(const message of ['Recorded cleanup evidence',
    '{receipts} cleanup receipts · {items} recorded stock-removal items',
    '{unqualified} items without usable measured-waste coverage · {unknown} items with unknown waste value',
    '{quantity} {unit} · partial measured observations',
    'Stock removal is not a measured-waste or cost observation.',
    'Observation history is unavailable; missing history does not mean zero waste.',
    'Authoritative observation read context unavailable.',
    'Partial recorded observations only; not all waste or person-level attribution.',
    'Cost snapshots are not admitted by this observation contract; waste value remains unknown.']) {
    assert.equal(english[message],message);
    assert.ok(coverage.entries[message].sources.includes('public/integration-owner03.mjs'));
    assert.equal(coverage.entries[message].arabic,false);
  }
});

test('actual cleanup entrypoint stock removal does not establish measured-waste value',()=>{
  assert.equal(finishInventory([lot],receipt)[0].quantity,375);
  const profile={waste:[receipt]},before=structuredClone(profile),view=wasteInsight(profile,{dates});
  assert.equal(view.legacyItems,1);assert.equal(view.unqualifiedQuantityItems,1);assert.equal(view.unknownValueItems,1);
  assert.equal(view.quantityTotals,null);assert.equal(view.valueTotals,null);assert.deepEqual(profile,before);
});
test('qualified caller context and exact receipt/source yield partial quantities, never invented cost',()=>{
  const profile={waste:[receipt],wasteObservations:[observation]},before=structuredClone(profile);
  const view=wasteInsight(profile,{dates,context});
  assert.equal(view.status,'observation-quantities');assert.deepEqual(view.quantityTotals,[{unit:'g',quantity:125}]);
  assert.equal(view.unknownValueItems,1);assert.equal(view.valueTotals,null);
  assert.deepEqual(view.observations[0].provenance,observation.provenance);assert.deepEqual(profile,before);
  assert.equal(wasteInsight(profile,{dates}).quantityTotals,null);
});
test('mixed observed units stay separate; unknown measurement remains unknown and period is explicit',()=>{
  const other={...lot,id:'lot-2',unit:'kg',quantity:1,discardQuantity:.5};
  const two={...receipt,items:[...receipt.items,other]};
  const second={...observation,id:'obs-2',sourceId:'lot-2',quantity:.25,unit:'kg'};
  const profile={waste:[two],wasteObservations:[observation,second]};
  assert.deepEqual(wasteInsight(profile,{dates,context}).quantityTotals,[{unit:'g',quantity:125},{unit:'kg',quantity:.25}]);
  const unknown=wasteInsight({...profile,wasteObservations:[observation,{...second,quantity:null}]},{dates,context});
  assert.equal(unknown.unqualifiedQuantityItems,1);assert.equal(unknown.unknownValueItems,2);assert.equal(unknown.observations[1].quantity,null);
  assert.equal(wasteInsight(profile,{dates:['2026-10-13'],context}).quantityTotals,null);
  assert.throws(()=>wasteInsight(profile,{dates:null}),/explicit insight dates/);
});
test('cross-account, missing binding/provenance, duplicate and overlapping observations withhold all totals',()=>{
  for(const rows of [[{...observation,accountId:'other'}],[{...observation,sourceId:'other'}],[{...observation,quantity:126}],
    [{...observation,provenance:null}],[observation,observation],[observation,{...observation,id:'obs-2'}]]) {
    const view=wasteInsight({waste:[receipt],wasteObservations:rows},{dates,context});
    assert.equal(view.status,'analysis-unavailable');assert.equal(view.quantityTotals,null);assert.equal(view.valueTotals,null);
  }
});
test('overflow and measured zero are preserved as unavailable analysis, never zero/missing replacements',()=>{
  const max=Number.MAX_VALUE;
  const huge={...receipt,items:[{...lot,discardQuantity:max},{...lot,id:'lot-2',discardQuantity:max}]};
  const rows=[{...observation,quantity:max},{...observation,id:'obs-2',sourceId:'lot-2',quantity:max}];
  const view=wasteInsight({waste:[huge],wasteObservations:rows},{dates,context});
  assert.equal(view.status,'analysis-unavailable');assert.match(view.diagnostics[0],/overflow/);assert.equal(view.quantityTotals,null);
  const zero={waste:[receipt],wasteObservations:[{...observation,quantity:0}]},before=structuredClone(zero);
  assert.match(wasteInsight(zero,{dates,context}).diagnostics[0],/Explicit measured zero/);assert.deepEqual(zero,before);
});
test('actual validateState retains receipt identity while observation persistence remains gated',()=>{
  const validated=validateState({inventory:[lot],products:{},recipes:[],profile:{servings:1,waste:[receipt],wasteObservations:[observation]}});
  assert.equal(validated.profile.wasteObservations,undefined);assert.equal(validated.profile.waste[0].id,receipt.id);
  assert.equal(wasteInsight(validated.profile,{dates,context}).status,'legacy-unqualified');
});

class Node {
  constructor(tag,doc){this.tagName=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.style={};this.value='';this.textContent='';}
  append(...nodes){this.children.push(...nodes);}
  replaceChildren(...nodes){this.children=[...nodes];}
  setAttribute(key,value){this[key]=value;}
  get options(){return this.children;}
  get text(){return String(this.textContent)+this.children.map(n=>n instanceof Node?n.text:String(n)).join(' ');}
}
test('production setupInsights render invokes the consumer on existing completion target without writes',()=>{
  const previous=globalThis.document;const nodes=new Map();
  const doc={createElement:tag=>new Node(tag,doc),getElementById:id=>{
    if(!nodes.has(id)){const node=new Node('div',doc);node.id=id;if(id==='history-range')node.value='7';nodes.set(id,node);}return nodes.get(id);
  }};
  globalThis.document=doc;
  const profile={members:[],history:[],plan:[],goals:[],waste:[receipt]},before=structuredClone(profile);let writes=0;
  try {
    setLanguage('ar');
    const ui=setupInsights({getData:()=>({profile,inventory:[],products:{},recipes:[],date:today,usePantry:false}),persist:()=>writes++,download:()=>writes++,today:()=>today});
    ui.render();const target=doc.getElementById('completion-kpis');const panels=target.children.filter(n=>n.dataset.owner03==='waste-insight');
    assert.equal(panels.length,1);assert.ok(panels[0].text.includes(formatNumber(1)+' items with unknown waste value'));
    assert.match(panels[0].text,/Stock removal is not a measured-waste/);assert.equal(writes,0);assert.deepEqual(profile,before);
    assert.equal(panels[0].children[0].lang,'en');assert.equal(panels[0].children[0].dir,'auto');
    ui.render();assert.equal(target.children.filter(n=>n.dataset.owner03==='waste-insight').length,1);
    const app=readFileSync(new URL('../../public/app.js',import.meta.url),'utf8');assert.match(app,/import \{setupInsights\} from '.\/insights-ui.js'/);assert.match(app,/const insights=setupInsights/);
  } finally {setLanguage('en');globalThis.document=previous;}
});
