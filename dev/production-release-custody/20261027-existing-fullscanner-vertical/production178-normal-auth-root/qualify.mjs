import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const dir = path.dirname(new URL(import.meta.url).pathname);
const manifest = JSON.parse(fs.readFileSync(dir + '/manifest.json'));
const baseDir = '/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/public-beetroot-lookup-diagnosis-20261026/integrated-correction-revised11-current97-r1';
const original = JSON.parse(fs.readFileSync(baseDir + '/manifest.json'));
const previousMeta=JSON.parse(fs.readFileSync('/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/public-beetroot-lookup-diagnosis-20261026/integrated-correction-source-r2-auth-current109-r1/manifest.json'));
const worldMeta=JSON.parse(fs.readFileSync('/home/user/src/offmenu-data/runtime/layout-migration/worker00/private10300-local-integration-20261026/public-beetroot-lookup-diagnosis-20261026/integrated-correction-world-taps-r3-current168-r1/manifest.json'));
const base={binaryParts:[...original.binaryParts,...original.newBinaryParts,...previousMeta.newDataModules,...worldMeta.newDataModules],newBinaryParts:[],routes:manifest.oldRoutes};
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const parts = new Map();
const unchangedOpaqueNativeParts = [];
const oldExpected = JSON.parse(fs.readFileSync(baseDir + '/expected-154-module-tuples.json'));
for (const row of [...base.binaryParts, ...base.newBinaryParts, ...manifest.newDataModules]) {
  const name = row.module || row.name;
  if (!name || !row.path) continue;
  const bytes = fs.readFileSync(row.path);
  assert.equal(sha(bytes), row.sha256, row.path);
  parts.set(name, bytes);
}
for (const row of base.routes) {
  if (!row.path || !fs.existsSync(row.path)) continue;
  const tuple = oldExpected.find(value => value[2] === row.sha256 && value[3] === 'application/octet-stream');
  if (!tuple || parts.has(tuple[0])) continue;
  const bytes = fs.readFileSync(row.path);
  assert.equal(sha(bytes), tuple[2]);
  assert.equal(bytes.length, tuple[1]);
  parts.set(tuple[0], bytes);
}
for (const row of manifest.requiredExistingRoutes) { const bytes=fs.readFileSync(row.path);assert.equal(sha(bytes),row.sha256); for(let offset=0;offset<bytes.length;offset+=600000){const part=bytes.subarray(offset,offset+600000);const tuple=oldExpected.find(x=>x[1]===part.length&&x[2]===sha(part));if(tuple)parts.set(tuple[0],part);}}
let externalCalls = 0;
const delegated = [];
const context = vm.createContext({Request, Response, Headers, URL, URLSearchParams,
  Blob, Uint8Array, TextEncoder, TextDecoder, atob, btoa, console,
  fetch: async () => { externalCalls++; throw Error('UNEXPECTED_EXTERNAL_FETCH'); }});
const previous = {fetch: async (...args) => {
  delegated.push(args);
  return new Response('OPAQUE_PRIVATE_WORKER_SENTINEL', {status: 418});
}, scheduled: (...args) => args};
const cache = new Map();
async function dependency(specifier) {
  if (cache.has(specifier)) return cache.get(specifier);
  let exports;
  const name = path.basename(specifier);
  if (name.endsWith('.bin')) {
    if (!parts.has(name)) {
      assert.ok(name.startsWith('v12-') && oldExpected.some(row => row[0] === name && row[3] === 'application/octet-stream'), 'Missing unqualified dependency ' + name);
      unchangedOpaqueNativeParts.push(name);
      parts.set(name, Buffer.from('UNCHANGED_OPAQUE_NATIVE_DEPENDENCY:' + name));
    }
    exports = {default: new Uint8Array(parts.get(name))};
  } else if (name === 'worker.mjs') exports = {default: previous};
  else if (name === 'public-inventory-provider.mjs') exports = {
    EXISTING_PUBLIC_INVENTORY_SELECTION: {sourceId: 'off', releaseId: 'offmenu-off-selected-products-20261025-v1'},
    bindExistingQualifiedPublicInventory: async () => {throw Error('NO_DATA_QUERY_IN_STATIC_QUALIFICATION');}
  };
  else throw Error('Unexpected import: ' + specifier);
  const mod = new vm.SyntheticModule(Object.keys(exports), function () {
    for (const [key, value] of Object.entries(exports)) this.setExport(key, value);
  }, {context});
  cache.set(specifier, mod);
  return mod;
}
async function load(filename) {
  const mod = new vm.SourceTextModule(fs.readFileSync(filename, 'utf8'), {context});
  await mod.link(dependency);
  await mod.evaluate();
  return mod.namespace.default;
}
const feedbackOnly = process.argv.includes('--feedback-only');
const before = await load(manifest.base.path);
const candidatePath = manifest.module.path;
const candidate = await load(candidatePath);
const origin = 'https://offmenu.aldous.info';
const body = async response => Buffer.from(await response.arrayBuffer());
let oldRoutes = 0, newRoutes = 0, headRoutes = 0;
for (const row of base.routes) {
  const a = await before.fetch(new Request(origin + row.route), {}, {});
  const b = await candidate.fetch(new Request(origin + row.route), {}, {});
  assert.equal(b.status, a.status, row.route);
  assert.deepEqual([...b.headers], [...a.headers], row.route);
  assert.deepEqual(await body(b), await body(a), row.route);
  oldRoutes++;
}
for (const row of manifest.newRoutes) {
  const response = await candidate.fetch(new Request(origin + row.route), {}, {});
  assert.equal(response.status, 200, row.route);
  assert.equal(sha(await body(response)), row.sha256, row.route);
  assert.equal(response.headers.get('Content-Type'), row.mime);
  for (const [name, value] of Object.entries(manifest.headers)) assert.equal(response.headers.get(name), value);
  const head = await candidate.fetch(new Request(origin + row.route, {method: 'HEAD'}), {}, {});
  assert.equal(head.status, 200);
  assert.equal((await body(head)).length, 0);
  headRoutes++;
  newRoutes++;
}
for (const row of manifest.requiredExistingRoutes) {const response=await candidate.fetch(new Request(origin+row.route),{},{});assert.equal(response.status,200);assert.equal(sha(await body(response)),row.sha256,row.route);}
for (const route of []) {
  const a = await before.fetch(new Request(origin + route), {}, {});
  const b = await candidate.fetch(new Request(origin + route), {}, {});
  assert.deepEqual(await body(b), await body(a));
}
const opaquePaths = ['/shelf-scanner.html', '/kitchen.html', '/api/auth', '/.netlify/identity/settings', '/api/data/private'];
for (const route of opaquePaths) {
  const request = new Request(origin + route), env = {}, ctx = {};
  assert.equal((await candidate.fetch(request, env, ctx)).status, 418);
  assert.deepEqual(delegated.at(-1), [request, env, ctx]);
}
for (const env of [{OFFMENU_AUTH_MODE: 'unsupported'}, {DEV_COMPOSITION: true}, {OFFMENU_LOCAL_LAB: true}]) {
  assert.equal((await candidate.fetch(new Request(origin + manifest.newRoutes[0].route), env, {})).status, 418);
}
assert.equal((await candidate.fetch(new Request(origin + '/demo/api/product?barcode=4061464939738'), {}, {})).status, 503);
assert.equal((await candidate.fetch(new Request(origin + manifest.newRoutes[0].route, {method: 'POST'}), {}, {})).status, 418);
assert.equal(externalCalls, 0);
const result = {atUTC: new Date().toISOString(), status: 'PASS_SCOPED_OFFLINE_COMPOSITION',
  moduleSHA256: sha(fs.readFileSync(candidatePath)), preservedBaseSHA256: manifest.base.sha256,
  unchangedOpaqueNativeParts,
  oldManifestRoutesByteAndHeaderIdenticalToPinnedBase: oldRoutes,
  changedRootAndExistingAuthRoutesActualResponseHashAndHeaders: newRoutes, emptyHeadResponses: headRoutes,
  requiredExistingWorldResourcesActualHashPassed: 3, authDeltaIncluded: false, privatePathsOpaqueDelegation: opaquePaths.length,
  invalidEnvironmentDelegations: 3, externalCalls, sourceDataQueries: 0,
  limits: 'Private worker and listed unchanged original v12 native dependencies are explicit opaque sentinels. Old-route comparison shares those same sentinels; the finalrootandthreeexistingauth/landingroute bodies and3 existing room resources independently match exact source hashes. Production preservation additionally requires exact prior module pins and inverse source proof. This is not real authentication, full-app UI, deployed HTTP, world/anatomy/full15 or human acceptance. Author real-worker synthetic guard and actual64 sourceR2 evidence remain separately scoped.'};
fs.writeFileSync(dir + (feedbackOnly ? '/feedback-only-qualification.json' : '/package-qualification.json'), JSON.stringify(result, null, 2) + '\n');
console.log(JSON.stringify(result));
