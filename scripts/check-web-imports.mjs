// Validate maintained JavaScript modules without importing or activating them.
import {parse} from 'acorn';
import {readdir, readFile, stat} from 'node:fs/promises';
import {dirname, extname, resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const roots = ['apps', 'deploy', 'integrations', 'tools/corpus', 'tools/diagnostics',
  'scripts', 'tests/web', 'tests/edge', 'tests/support'];
const excluded = new Set(['apps/web/server/generated.mjs', 'apps/retailer-extension/popup.js']);
const modules = [];
async function collect(directory) {
  for (const entry of await readdir(resolve(root, directory), {withFileTypes: true})) {
    const path = directory + '/' + entry.name;
    if (entry.isDirectory()) {
      if (!['node_modules', 'dist', 'fixtures', '__pycache__'].includes(entry.name)) await collect(path);
    } else if (['.js', '.mjs'].includes(extname(path)) && !excluded.has(path)) modules.push(path);
  }
}
for (const directory of roots) await collect(directory);
const issues = [];
const retainedCandidateHolds = [];
const dependencies = new Map();
const missing = [];
const runtimeRoots = ['apps/web/src/app.js', 'apps/web/src/data-workspace.js',
  'apps/web/src/sw.js', 'apps/web/src/scanner-worker.js', 'apps/web/src/shelf-scanner.js',
  'apps/web/server/handler.mjs', 'apps/retailer-extension/popup-source.js',
  'deploy/auth-return/i18n-source.js', 'deploy/auth-return/return.js'];
let relativeImports = 0;
for (const name of modules) {
  const source = await readFile(resolve(root, name), 'utf8');
  let tree;
  try { tree = parse(source, {ecmaVersion: 'latest', sourceType: 'module'}); }
  catch (error) { issues.push({path: name, error: error.message}); continue; }
  const references = [];
  function walk(node) {
    if (!node || typeof node !== 'object') return;
    if (['ImportDeclaration', 'ExportNamedDeclaration', 'ExportAllDeclaration'].includes(node.type) && node.source) references.push(node.source.value);
    if (node.type === 'ImportExpression' && typeof node.source.value === 'string') references.push(node.source.value);
    for (const value of Object.values(node)) {
      if (Array.isArray(value)) value.forEach(walk);
      else if (value && typeof value === 'object') walk(value);
    }
  }
  walk(tree);
  dependencies.set(name, []);
  for (const specifier of references) {
    if (!specifier.startsWith('.')) continue;
    relativeImports++;
    const target = resolve(root, dirname(name), specifier.split(/[?#]/, 1)[0]);
    dependencies.get(name).push(relative(root, target));
    try {
      if (!(await stat(target)).isFile()) throw Error('not a file');
    } catch {
      missing.push({path: name, import: specifier, error: 'relative module missing', target: relative(root, target)});
    }
  }
}
const reachable = new Set();
const queue = [...runtimeRoots];
while (queue.length) {
  const path = queue.pop();
  if (reachable.has(path)) continue;
  reachable.add(path);
  queue.push(...(dependencies.get(path) || []));
}
for (const issue of missing) {
  // This unmounted scanner candidate already lacked this helper at c3e75993b.
  // Preserve its unfinished state; introducing it to a build root fails here.
  if (issue.path === 'apps/web/src/production-scanner/scanner-worker.js' &&
      issue.import === './scanner-decode.js' && !reachable.has(issue.path)) {
    retainedCandidateHolds.push({...issue, status: 'unmounted-existing-source-hold'});
  } else issues.push(issue);
}
console.log(JSON.stringify({modules: modules.length, relativeImports,
  runtimeReachable: reachable.size, retainedCandidateHolds, issues}, null, 2));
if (issues.length) process.exitCode = 1;
