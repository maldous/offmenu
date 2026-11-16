import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {build} from 'esbuild';
import {Miniflare,createFetchMock} from 'miniflare';
import {parse} from 'acorn';
import {workerRuntimeBuildOptions} from '../../scripts/worker-build-options.mjs';
import {setLanguage,t,setLocalizedText,setupLanguage,getLanguage} from '../../apps/web/src/i18n.js';

const page=await readFile(new URL('../../apps/web/assets/shelf-scanner.html',import.meta.url),'utf8');

test('scanner language selection retains identifier controls and canonical option values',()=>{
  assert.match(page,/<select id="scanner-language"[^>]*data-ui-language/);
  for(const value of ['Explore','Buy','Stock','Audit','Discard','barcode','USDA-FDC','UPC-E','UPC-A','EAN-13','EAN-8','GTIN-14']) {
    assert.ok(page.includes('value="'+value+'"'),value);
  }
  assert.match(page,/<input id="barcode"[^>]*dir="ltr"[^>]*maxlength="128"[^>]*required/);
  assert.match(page,/<button id="session-button"[^>]*>.*<span id="queue-count">0<\/span><\/button>/);
});

test('scanner device selection falls back to URL without changing captured identifiers',()=>{
  const previous=globalThis.location;
  let change,assigned;
  const select={value:'',addEventListener(_,callback){change=callback;}};
  const root={cookie:'',documentElement:{dataset:{}},querySelector(){return null;},querySelectorAll(selector){return selector==='[data-ui-language]'?[select]:[];}};
  globalThis.location={href:'https://offmenu.test/shelf-scanner.html?original=00123456#manual',assign(value){assigned=value;}};
  try {
    setupLanguage(root,{getItem(){return 'ar';},setItem(){throw Error('storage unavailable');}},{languages:['en']});
    assert.equal(getLanguage(),'ar');
    select.value='en';change();
    const next=new URL(assigned);
    assert.equal(next.pathname,'/shelf-scanner.html');assert.equal(next.searchParams.get('original'),'00123456');
    assert.equal(next.searchParams.get('uiLanguage'),'en');assert.equal(next.hash,'#manual');
  } finally {globalThis.location=previous;setLanguage('en');}
});

test('scanner UI labels reuse Arabic resources and mark untranslated labels as English',()=>{
  setLanguage('ar');
  try {
    const translated={},fallback={};
    setLocalizedText(translated,'Cancel');
    setLocalizedText(fallback,'Finish scanning');
    assert.notEqual(translated.textContent,'Cancel');assert.equal(translated.lang,'ar');
    assert.equal(fallback.textContent,'Finish scanning');assert.equal(fallback.lang,'en');
  } finally {setLanguage('en');}
});

test('actual scanner display helpers translate UI labels without translating source values',async()=>{
  const source=await readFile(new URL('../../apps/web/src/shelf-scanner.js',import.meta.url),'utf8');
  const names=['el','ui','btn','field','displayValue'];
  const functions=parse(source,{ecmaVersion:'latest',sourceType:'module'}).body.filter(node=>node.type==='FunctionDeclaration'&&names.includes(node.id.name)).map(node=>source.slice(node.start,node.end));
  const nodes=new Map();
  const document={createElement(tag){return {tag,children:[],append(...children){this.children.push(...children);}};}};
  const helpers=Function('document','t','setLocalizedText','$',functions.join('\n')+';return {el,ui,btn,field,displayValue};')(document,t,setLocalizedText,id=>{if(!nodes.has(id))nodes.set(id,{});return nodes.get(id);});
  setLanguage('ar');
  try {
    assert.equal(helpers.el('p','Cancel').textContent,'Cancel');
    assert.notEqual(helpers.btn('Cancel',()=>{}).textContent,'Cancel');
    const field=helpers.field('Brand','Cancel');assert.equal(field.children[1].textContent,'Cancel');
    helpers.displayValue('product','Cancel');assert.equal(nodes.get('product').textContent,'Cancel');
    assert.equal(nodes.get('product').lang,'und');assert.equal(nodes.get('product').dir,'auto');
  } finally {setLanguage('en');}
});

test('actual scanner entry bundles with the existing locale resources',async()=>{
  const result=await build({entryPoints:['apps/web/src/shelf-scanner.js'],bundle:true,format:'esm',write:false});
  assert.equal(result.errors.length,0);
  assert.ok(result.outputFiles[0].text.includes('offmenu-ui-language-v1'));
  assert.ok(result.outputFiles[0].text.includes('offmenu-scanner-kitchen-handoff/1'));
});

test('actual Worker route localizes scanner HTML while preserving source namespace and nested controls',async()=>{
  const template=await readFile(new URL('../../apps/web/server/handler.mjs',import.meta.url),'utf8');
  const result=await build({...workerRuntimeBuildOptions,stdin:{contents:'const ASSETS='+JSON.stringify({'shelf-scanner.html':page})+';const RELEASE={};\n'+template,resolveDir:new URL('../../apps/web/server/',import.meta.url).pathname,sourcefile:'scanner-locale-worker.mjs'},bundle:true,minify:true,format:'esm',platform:'browser',write:false});
  const fetchMock=createFetchMock();fetchMock.disableNetConnect();
  const worker=new Miniflare({modules:true,script:result.outputFiles[0].text,compatibilityDate:'2026-08-06',compatibilityFlags:['nodejs_compat'],host:'127.0.0.1',port:0,fetchMock,cf:{country:'EG'}});
  try {
    const response=await worker.dispatchFetch('https://offmenu.test/shelf-scanner.html?uiLanguage=ar');
    const body=await response.text();
    assert.equal(response.status,200);assert.equal(response.headers.get('content-language'),'ar');
    assert.equal(response.headers.get('cache-control'),'private, no-store');
    assert.match(body,/<html[^>]*lang="ar"[^>]*dir="rtl"/);
    assert.match(body,/لغة الواجهة/);
    assert.match(body,/<h1[^>]*lang="en"[^>]*>Choose your scanner mode<\/h1>/);
    assert.match(body,/<option value="USDA-FDC"/);assert.match(body,/<option value="UPC-E"/);
    assert.match(body,/<span id="queue-count">0<\/span>/);
    const english=await worker.dispatchFetch('https://offmenu.test/shelf-scanner.html?uiLanguage=en');
    assert.equal(english.headers.get('content-language'),'en');assert.match(await english.text(),/Interface language/);
  } finally {await worker.dispose();}
});
