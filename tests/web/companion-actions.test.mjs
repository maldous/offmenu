import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {setupRecipeLibrary} from '../../apps/web/src/recipe-library-ui.js';
import {setupInsights} from '../../apps/web/src/insights-ui.js';

function controls(t, host) {
  const elements = new Map();
  function element() {
    return {
      value: '', children: [], dataset: {},
      append(...nodes) { this.children.push(...nodes); },
      replaceChildren(...nodes) { this.children = nodes; },
      addEventListener(name, handler) { this['on' + name] = handler; },
      setAttribute() {}, showModal() { this.open = true; },
      focus() { document.activeElement = this; }
    };
  }
  function get(id) {
    if (!elements.has(id)) elements.set(id, element());
    return elements.get(id);
  }
  for (const [key, value] of Object.entries({
    document: {getElementById: get, createElement: element, createTextNode: String},
    navigator: host
  })) {
    const original = Object.getOwnPropertyDescriptor(globalThis, key);
    Object.defineProperty(globalThis, key, {value, configurable: true});
    t.after(() => original ? Object.defineProperty(globalThis, key, original) : delete globalThis[key]);
  }
  return get;
}

test('unsupported recipe share leaves export available and Escape preserves confirmation and focus', async t => {
  const get = controls(t, {});
  const record = {id:'offmenu:fixture:rice', kind:'recipe',
    data:{name:'Rice', languages:['en'], ingredients:[], directions:['Cook rice.']},
    provenance:{sourceId:'world-recipes', visibility:'public', url:'https://example.org/rice', license:'Fixture', attribution:'Fixture'},
    curation:{schema:'offmenu-curation/1',rawSourcePayloadPublished:false}};
  t.mock.method(globalThis,'fetch', async url => {
    if(url==='/recipes/manifest.json') return Response.json({
      format:'offmenu-curated/1', status:'curated-release-ready', privateProviderData:false, acquisitionAtRuntime:false,
      curatedAcceptance:{status:'all-curated-records-exercised'},releaseId:'fixture',records:1,
      library:{schema:'offmenu-recipe-library/1',records:1,languages:['en']}});
    const query = new URL(url,'https://example.org').searchParams;
    return Response.json({source:'world-recipes',releaseId:'fixture',manifestSha256:query.get('manifestSha256'),records:[record],nextCursor:null});
  });
  const exports = [];
  const library = setupRecipeLibrary({inventory:()=>[], download:(...args)=>exports.push(args)});
  await get('world-recipe-load').onclick();
  await get('world-recipe-results').children[0].children.at(-1).onclick();
  const context = library.reportContext();
  assert.equal(context.resourceId,record.id);
  get('world-recipe-confirm').checked = true;
  const actions = get('world-recipe-actions');
  const summary = get('summary');
  actions.querySelector = selector => { assert.equal(selector,'summary'); return summary; };
  // Native HTML supplies disclosure activation. Exercise the app's dismissal handler.
  actions.open = true;
  assert.equal(get('world-recipe-share').hidden,true);
  let canceled=false;
  actions.onkeydown({key:'Escape',preventDefault(){canceled=true;},stopPropagation(){}});
  assert.equal(canceled,true);
  assert.equal(document.activeElement,summary);
  assert.equal(actions.open,false);
  assert.equal(get('world-recipe-dialog').open,true);
  assert.equal(get('world-recipe-confirm').checked,true);
  assert.deepEqual(library.reportContext(),context);
  assert.deepEqual(exports,[]);
  actions.open=true;
  get('world-recipe-jsonld').onclick();
  assert.equal(exports.length,1);
  assert.equal(JSON.parse(exports[0][1]).name,'Rice');
});

test('declining native share never writes the clipboard and copy permission can be revoked', async t => {
  let writes=0;
  const get=controls(t,{
    share:async payload=>{assert.equal(payload.text,'offmenu shopping list\nRice — 1 kg');throw new DOMException('Canceled','AbortError');},
    clipboard:{async writeText(){writes++;throw new DOMException('Denied','NotAllowedError');}}
  });
  setupInsights({today:()=>'2026-11-22', getData:()=>({profile:{shopping:[{name:'Rice',amount:'1 kg',checked:false},{name:'Tea',amount:'1 box',checked:true}]},date:'2026-11-22',recipes:[],inventory:[],products:{}})});
  await get('share-shopping').onclick();
  assert.equal(writes,0);
  assert.equal(get('integration-notice').textContent,undefined);
  await get('copy-shopping').onclick();
  assert.equal(writes,1);
  assert.match(get('integration-notice').textContent,/Download the list/);
});

test('both launcher manifests use the same two read-only destinations and generic labels',()=>{
  for(const [manifest,names] of [['manifest',['Meal plan','Shopping list']],['manifest-ar',['خطة الوجبات','قائمة التسوق']]]) {
    const source=JSON.parse(readFileSync(new URL('../../apps/web/assets/'+manifest+'.webmanifest',import.meta.url)));
    assert.deepEqual(source.shortcuts,[{name:names[0],url:'/?view=plan'},{name:names[1],url:'/?view=shopping'}]);
    assert.equal(source.start_url,'/');
  }
});
