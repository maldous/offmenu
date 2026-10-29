import {parse} from 'acorn';
import {readFile,writeFile,readdir} from 'node:fs/promises';
import {ARABIC} from '../apps/web/src/locales/ar.js';

const messages = new Map();
const arabicTree=parse(await readFile('apps/web/src/locales/ar.js','utf8'),{ecmaVersion:'latest',sourceType:'module'});
const catalogueKeys=new Set();
for(const entry of arabicTree.body[0].declaration.declarations[0].init.arguments[0].properties){
  if(catalogueKeys.has(entry.key.value))throw Error('Duplicate Arabic message key: '+entry.key.value);
  catalogueKeys.add(entry.key.value);
}
const decode = value => value.replace(/&quot;/g,'"').replace(/&#39;/g,"'").replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&amp;/g,'&');
const add = (key, file) => { if (key?.trim()) { if (!messages.has(key)) messages.set(key,new Set()); messages.get(key).add(file); } };
const files = (await readdir('apps/web/src')).filter(file => file.endsWith('.js') && !['i18n.js','content-locale.js','scanner-worker.js'].includes(file)).map(file => 'apps/web/src/'+file);
files.push('apps/web/src/integration-owner03.mjs');
files.push('apps/retailer-extension/popup-source.js');
files.push(...(await readdir('apps/web/server')).filter(file=>file.endsWith('.mjs')&&file!=='generated.mjs').map(file=>'apps/web/server/'+file));
for (const file of files) {
  const source = await readFile(file,'utf8');
  const tree = parse(source,{ecmaVersion:'latest',sourceType:'module'});
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (node.type === 'CallExpression' && node.callee.name === 't' && typeof node.arguments[0]?.value === 'string') add(node.arguments[0].value,file);
    if (node.type === 'CallExpression' && node.callee.name === 'setLocalizedText' && typeof node.arguments[1]?.value === 'string') add(node.arguments[1].value,file);
    // Labels and source descriptions passed through a variable still need a
    // translator entry. Record identifiers, URLs, CSS and HTML are excluded.
    if (node.type === 'Literal' && typeof node.value === 'string' && /[A-Za-z]/.test(node.value) &&
        !/[<>]|https?:\/\/|^urn:|^(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|PRAGMA|DROP|WITH)\b/.test(node.value) && (/[A-Za-z][ .,;:!?&]/.test(node.value) ||
        /^[A-Z][a-z]+$/.test(node.value))) add(node.value,file);
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(walk);
      else if (value && typeof value === 'object') walk(value);
    }
  }
  walk(tree);
}
for (const file of ['apps/web/assets/index.html','apps/web/assets/data-workspace.html','apps/retailer-extension/popup.html','deploy/auth-return/index.html']) {
  const source = await readFile(file,'utf8');
  for (const match of source.matchAll(/data-i18n(?:-[\w-]+)?="([^"]*)"/g)) add(decode(match[1]),file);
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
  arabicMissing:missing.length,arabicComplete:missing.length===0,
  entries:Object.fromEntries(keys.map(key => [key,{sources:[...messages.get(key)].sort(),arabic:!missing.includes(key)}]))};
const outputs = [['apps/web/assets/locales/en.json',JSON.stringify(english,null,2)+'\n'],['docs/i18n-coverage.json',JSON.stringify(report,null,2)+'\n']];
if (process.argv.includes('--check')) {
  for (const [path,expected] of outputs) if (await readFile(path,'utf8') !== expected) throw Error('Translation inventory changed. Run npm run i18n:extract: '+path);
} else for (const [path,content] of outputs) await writeFile(path,content);
console.log(JSON.stringify({messages:report.messages,arabicTranslated:report.arabicTranslated,arabicMissing:report.arabicMissing}));
if (process.argv.includes('--complete-ar') && missing.length) throw Error('Arabic catalogue is incomplete. See docs/i18n-coverage.json.');
