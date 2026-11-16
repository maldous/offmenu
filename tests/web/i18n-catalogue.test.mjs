import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {extractJavaScript,extractHTML} from '../../scripts/i18n-catalogue.mjs';

const extract=(source,file='fixture.js')=>extractJavaScript(source,file);
const keys=result=>result.entries.map(entry=>entry.key);

test('explicit UI keys survive SQL and shader syntax and override heuristic classification',()=>{
  const result=extract(`const label='SELECT a source'; t('SELECT a source');
    setLocalizedText(node,'UPDATE your profile'); t('uniform mat4 modelMatrix;');
    DB.prepare('SELECT a source');`, 'apps/web/src/scanner-three.js');
  for(const key of ['SELECT a source','UPDATE your profile','uniform mat4 modelMatrix;']) {
    assert.equal(result.entries.find(entry=>entry.key===key)?.classification,'explicit-ui');
  }
});

test('only direct SQL expression segments in recognized DB arguments are excluded',()=>{
  const result=extract("env.DB.prepare('SELECT name FROM items ' + 'WHERE active = ?').bind('Kitchen invitation');\n"+
    "DB.exec(`CREATE TABLE things (${columns})`); other.prepare('Prepare a meal');\n"+
    "env.DB.prepare(t('SELECT a source'));\n"+
    "const uncertain='SELECT uncertain FROM items'; DB.prepare(uncertain);\n"+
    "navigator.permissions.query({name:'Camera access'});\n"+
    "DB.prepare(buildQuery('Human helper label'));\n"+
    "DB.prepare(`SELECT * FROM items WHERE name = ${t('Human nested label')}`);");
  for(const key of ['SELECT name FROM items ','WHERE active = ?','CREATE TABLE things (','SELECT * FROM items WHERE name = '])assert.ok(!keys(result).includes(key),key);
  for(const key of ['Kitchen invitation','Prepare a meal','SELECT a source','SELECT uncertain FROM items','Camera access','Human helper label','Human nested label'])assert.ok(keys(result).includes(key),key);
  assert.equal(result.excludedTechnical.sql,4);
});

test('SQL-looking human labels and dynamic human text remain conservative candidates',()=>{
  const result=extract("const create='CREATE a recipe', update='UPDATE your profile'; const dynamic=`Welcome back, ${name}! Choose dinner.`;");
  for(const key of ['CREATE a recipe','UPDATE your profile','Welcome back, ','! Choose dinner.'])assert.equal(result.entries.find(entry=>entry.key===key)?.classification,'heuristic-candidate');
  assert.ok(!keys(result).includes('Welcome back, ${name}! Choose dinner.'));
});

test('reviewed shader signatures are excluded only from the bundled shader source',()=>{
  const source="const a='attribute vec3 position;', b='#define USE_COLOR', c='ToneMapping( color ); }';\n"+
    "const warning='THREE.WebGLRenderer: Unable to use linear filtering with floating point textures.';\n"+
    "const human='Choose uniform colours.';";
  const shader=extract(source,'apps/web/src/scanner-three.js');
  assert.equal(shader.excludedTechnical.shader,3);
  assert.deepEqual(keys(shader),['THREE.WebGLRenderer: Unable to use linear filtering with floating point textures.','Choose uniform colours.']);
  assert.equal(keys(extract(source)).length,5);
});

test('scanner HTML labels and accessibility keys are extracted and decoded',async()=>{
  assert.deepEqual(extractHTML('<button data-i18n="Scan &amp; save" data-i18n-aria-label="Open &quot;scanner&quot;">'),['Scan & save','Open "scanner"']);
  const source=await readFile(new URL('../../apps/web/assets/shelf-scanner.html',import.meta.url),'utf8');
  assert.ok(extractHTML(source).length>0);
  const script=await readFile(new URL('../../scripts/i18n-catalogue.mjs',import.meta.url),'utf8');
  assert.ok(script.includes("'apps/web/assets/shelf-scanner.html'"));
});
