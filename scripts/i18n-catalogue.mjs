import {parse} from 'acorn';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {ARABIC} from '../apps/web/src/locales/ar.js';

// These exact shader fragments were reviewed in the bundled Three.js source.
// Scope them to that file: the same words elsewhere can be human UI text.
const shaderFragments = new Set([
  'return dot( weights, rgb );','( vec3 color ) { return','ToneMapping( color ); }',
  'float luminance( const in vec3 rgb ) {',
  'gl_FragColor = linearToOutputTexel( gl_FragColor );',
  'layout(location = 0) out highp vec4 pc_fragColor;'
]);
function reviewedShader(key,file) {
  if(file !== 'apps/web/src/scanner-three.js') return false;
  const text=key.trim();
  return shaderFragments.has(text) ||
    /^(?:attribute|uniform) (?:mat[34]|vec[234]|bool|sampler2D) [A-Za-z_][\w]*;$/.test(text) ||
    /^#(?:define(?: [A-Za-z_][\w]*)*(?: )?|ifdef [A-Za-z_][\w]*|if defined\( [A-Za-z_][\w]* \)|elif defined\( [A-Za-z_][\w]* \)|version|extension GL_ANGLE_(?:clip_cull_distance|multi_draw) : require)$/.test(text);
}
const candidate = key => /[A-Za-z]/.test(key) &&
  !/[<>]|https?:\/\/|^urn:/.test(key) &&
  (/[A-Za-z][ .,;:!?&]/.test(key) || /^[A-Z][a-z]+$/.test(key));
const propertyName = node => node?.type==='MemberExpression' ?
  (node.computed ? node.property.value : node.property.name) : null;
const databaseReceiver = node => (node?.type==='Identifier' && node.name==='DB') || propertyName(node)==='DB';
const sqlCall = node => node.type==='CallExpression' &&
  ['prepare','exec'].includes(propertyName(node.callee)) && databaseReceiver(node.callee.object);

export function extractJavaScript(source,file) {
  const entries=new Map(), excludedTechnical={sql:0,shader:0};
  const record=(key,classification) => {
    if(key?.trim() && (classification==='explicit-ui' || !entries.has(key))) entries.set(key,classification);
  };
  function walk(node,sqlSegment=false) {
    if(!node || typeof node!=='object') return;
    if(node.type==='CallExpression') {
      if(node.callee.name==='t' && typeof node.arguments[0]?.value==='string') record(node.arguments[0].value,'explicit-ui');
      if(node.callee.name==='setLocalizedText' && typeof node.arguments[1]?.value==='string') record(node.arguments[1].value,'explicit-ui');
      // Only direct string-expression segments of recognized DB APIs are SQL.
      // Calls nested inside the argument, bindings and uncertain dataflow remain
      // ordinary candidates; explicit translation calls always take precedence.
      walk(node.callee);
      node.arguments.forEach((arg,index)=>walk(arg,index===0 && sqlCall(node)));
      return;
    }
    if(node.type==='Literal' && typeof node.value==='string' && candidate(node.value)) {
      if(sqlSegment) excludedTechnical.sql++;
      else if(reviewedShader(node.value,file)) excludedTechnical.shader++;
      else record(node.value,'heuristic-candidate');
    }
    if(node.type==='TemplateLiteral') {
      // Preserve the existing literal inventory boundary for static templates.
      // SQL templates are still classified, and interpolation expressions are
      // walked below; this does not ingest bundled multiline shader programs.
      if(!sqlSegment && node.expressions.length===0) return;
      // A dynamic template is not a complete message key. Preserve its human
      // fragments as candidates rather than silently discarding human text.
      for(const part of node.quasis) {
        const key=part.value.cooked;
        if(typeof key==='string' && candidate(key)) {
          if(sqlSegment) excludedTechnical.sql++;
          else if(reviewedShader(key,file)) excludedTechnical.shader++;
          else record(key,'heuristic-candidate');
        }
      }
      node.expressions.forEach(part=>walk(part));
      return;
    }
    for(const [field,value] of Object.entries(node)) {
      const propagate=sqlSegment && node.type==='BinaryExpression' && node.operator==='+' && ['left','right'].includes(field);
      if(Array.isArray(value)) value.forEach(part=>walk(part));
      else if(value && typeof value==='object') walk(value,propagate);
    }
  }
  walk(parse(source,{ecmaVersion:'latest',sourceType:'module'}));
  return {entries:[...entries].map(([key,classification])=>({key,classification})),excludedTechnical};
}

export function extractHTML(source) {
  return [...source.matchAll(/data-i18n(?:-[\w-]+)?="([^"]*)"/g)].map(match=>decode(match[1]));
}
const decode = value => value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');

async function main() {
const messages = new Map(), classifications = new Map();
const excludedTechnical={sql:0,shader:0};
const arabicTree=parse(await readFile('apps/web/src/locales/ar.js','utf8'),{ecmaVersion:'latest',sourceType:'module'});
const catalogueKeys=new Set();
for(const entry of arabicTree.body[0].declaration.declarations[0].init.arguments[0].properties){
  if(catalogueKeys.has(entry.key.value))throw Error('Duplicate Arabic message key: '+entry.key.value);
  catalogueKeys.add(entry.key.value);
}

const add = (key, file, classification='explicit-ui') => { if (key?.trim()) { if(!classifications.has(key)) classifications.set(key,new Set()); classifications.get(key).add(classification); if (!messages.has(key)) messages.set(key,new Set()); messages.get(key).add(file); } };
const files = (await readdir('apps/web/src')).filter(file => file.endsWith('.js') && !['i18n.js','content-locale.js','scanner-worker.js'].includes(file)).map(file => 'apps/web/src/'+file);
files.push('apps/web/src/integration-owner03.mjs');
files.push('apps/retailer-extension/popup-source.js');
files.push(...(await readdir('apps/web/server')).filter(file=>file.endsWith('.mjs')&&file!=='generated.mjs').map(file=>'apps/web/server/'+file));
for (const file of files) {
  const result=extractJavaScript(await readFile(file,'utf8'),file);
  for(const {key,classification} of result.entries) add(key,file,classification);
  for(const reason of Object.keys(excludedTechnical)) excludedTechnical[reason]+=result.excludedTechnical[reason];
}
for (const file of ['apps/web/assets/index.html','apps/web/assets/shelf-scanner.html','apps/web/assets/data-workspace.html','apps/retailer-extension/popup.html','deploy/auth-return/index.html']) {
  const source = await readFile(file,'utf8');
  for (const key of extractHTML(source)) add(key,file);
}
for (const key of Object.keys(ARABIC)) add(key,'apps/web/src/locales/ar.js');
const keys = [...messages.keys()].sort();
const english = Object.fromEntries(keys.map(key => [key,key]));
const placeholders = text => [...String(text).matchAll(/\{(\w+)\}/g)].map(match => match[1]).sort().join(',');
for (const [key,entry] of Object.entries(ARABIC)) {
  for (const translation of typeof entry === 'string' ? [entry] : Object.values(entry)) {
    if (placeholders(key) !== placeholders(translation)) throw Error('Translation placeholders differ: '+key);
  }
  if (typeof entry === 'object' && !entry.other) throw Error('Plural translation requires other: '+key);
}
const missing = keys.filter(key => !Object.hasOwn(ARABIC,key));
const report = {schema:'offmenu-ui-catalogue/1',sourceLanguage:'en',messages:keys.length,arabicTranslated:keys.length-missing.length,
  arabicMissing:missing.length,arabicComplete:missing.length===0,excludedTechnical,
  entries:Object.fromEntries(keys.map(key => [key,{sources:[...messages.get(key)].sort(),arabic:!missing.includes(key),classification:classifications.get(key).has('explicit-ui')?'explicit-ui':'heuristic-candidate'}]))};
const outputs = [['apps/web/assets/locales/en.json',JSON.stringify(english,null,2)+'\n'],['docs/i18n-coverage.json',JSON.stringify(report,null,2)+'\n']];
if (process.argv.includes('--check')) {
  for (const [path,expected] of outputs) if (await readFile(path,'utf8') !== expected) throw Error('Translation inventory changed. Run npm run i18n:extract: '+path);
} else for (const [path,content] of outputs) await writeFile(path,content);
console.log(JSON.stringify({messages:report.messages,arabicTranslated:report.arabicTranslated,arabicMissing:report.arabicMissing}));
if (process.argv.includes('--complete-ar') && missing.length) throw Error('Arabic catalogue is incomplete. See docs/i18n-coverage.json.');

}
if(process.argv[1] && import.meta.url===pathToFileURL(process.argv[1]).href) await main();
