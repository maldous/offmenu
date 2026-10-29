import { build } from 'esbuild';
import { spawnSync } from 'node:child_process';
import { mkdtemp, mkdir, readFile, writeFile, symlink, realpath, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve, join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';
import { randomUUID } from 'node:crypto';
import { PINNED_MAIN, PINNED_THIRD_PARTY, MIGRATIONS, git, snapshot, composeSnapshots, blob, sha256 } from './lib/third-party-compatibility.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
if (args.length && (args.length !== 2 || args[0] !== '--report')) throw Error('Usage: node scripts/run-third-party-compatibility.mjs [--report path.json]');
const runID = randomUUID();
const logs = join(root, 'output/third-party-compatibility', runID);
const reportPath = args.length ? resolve(args[1]) : join(logs, 'report.json');
const fixture = await mkdtemp(join(tmpdir(), 'offmenu-third-party-compat-'));
const report = {
  schemaVersion: 1, runID, checkedAt: new Date().toISOString(), state: 'failed',
  command: 'node scripts/run-third-party-compatibility.mjs',
  sources: { main: PINNED_MAIN, thirdParty: PINNED_THIRD_PARTY },
  runtime: { node: process.version, platform: process.platform, architecture: process.arch },
  runnerFiles: {}, checks: [],
  qualification: 'Pinned synthetic compatibility only; READY FOR MORGAN REVIEW on success, not accepted or integrated.',
  gates: ['No branch merge or deployment acceptance.', 'Google IDP and Mock Services peer changes are not composed.',
    'Actual corpus transport/data, scanner binaries, extension package and real browser/device flows are not qualified.',
    'Local runtime compatibility date 2026-08-06; deployed 2026-10-12 runtime remains unqualified.',
    'Live origin access, subscriptions/billing/headroom, outbound sender/quota and trusted production admin role remain external gates.'],
};

async function put(name, bytes) {
  const path = join(fixture, name);
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, bytes);
}

function suite(name, files) {
  const result = spawnSync(process.execPath, ['--test', '--test-concurrency=1', '--test-reporter=tap', ...files], {
    cwd: fixture, timeout: 120_000, maxBuffer: 8 * 1024 * 1024,
    env: { ...process.env, OFFMENU_COMPAT_FIXTURE: '1' },
  });
  const output = (result.stdout?.toString() || '') + (result.stderr?.toString() || '');
  const counts = {};
  for (const key of ['tests', 'pass', 'fail', 'cancelled', 'skipped', 'todo']) {
    const match = output.match(new RegExp('^# ' + key + ' (\\d+)$', 'm'));
    counts[key] = match ? Number(match[1]) : null;
  }
  const passed = result.status === 0 && counts.tests > 0 && counts.pass === counts.tests &&
    counts.fail === 0 && counts.cancelled === 0 && counts.skipped === 0 && counts.todo === 0;
  const check = { name, files, command: [process.execPath, '--test', '--test-concurrency=1', '--test-reporter=tap', ...files],
    exitCode: result.status, signal: result.signal, error: result.error?.message, counts, passed,
    log: relative(root, join(logs, name + '.tap')), logSHA256: sha256(output) };
  report.checks.push(check);
  console.log(name + ': ' + JSON.stringify(counts) + (passed ? ' PASS' : ' FAIL'));
  return { check, output };
}

try {
  await mkdir(logs, { recursive: true });
  for (const name of ['scripts/run-third-party-compatibility.mjs', 'scripts/lib/third-party-compatibility.mjs', 'tests/compat/pinned-schema-runtime.test.mjs']) {
    report.runnerFiles[name] = sha256(await readFile(join(root, name)));
  }
  const main = snapshot(root, PINNED_MAIN), thirdParty = snapshot(root, PINNED_THIRD_PARTY);
  const baseSHA = git(root, 'merge-base', PINNED_MAIN, PINNED_THIRD_PARTY).toString().trim();
  const composed = composeSnapshots(snapshot(root, baseSHA), main, thirdParty);
  report.sources.base = baseSHA;
  report.sources.mainTree = git(root, 'rev-parse', PINNED_MAIN + '^{tree}').toString().trim();
  report.sources.thirdPartyTree = git(root, 'rev-parse', PINNED_THIRD_PARTY + '^{tree}').toString().trim();
  report.composition = { manifestSHA256: composed.manifestSHA256, mainChanges: composed.mainChanges,
    thirdPartyChanges: composed.thirdPartyChanges, leafCount: composed.entries.size, overlappingEdits: [],
    manifestFile: relative(root, join(logs, 'composed-manifest.json')),
    method: 'Main leaf entries plus third-party delta from common ancestor; distinct overlapping edits fail closed. No Git merge/tree objects written.' };
  await writeFile(join(logs, 'composed-manifest.json'), JSON.stringify(composed.manifest, null, 2) + '\n');
  const read = name => blob(root, composed.entries.get(name));
  // These are paths inside immutable historical commit snapshots, not today's
  // checkout. Keep their original spelling so source-pin replay stays truthful.
  const unitFiles = ['third-party-schema', 'care-cases', 'care-community', 'care-updates', 'recipe-community',
    'community-ai', 'personal-ai', 'admin-settings', 'admin-operations', 'admin-mcp', 'admin-runtime',
    'service-system', 'service-support', 'services-config-check', 'locale-negotiation', 'i18n']
    .map(name => 'tests-web/' + name + '.test.mjs');
  const edgeFiles = ['care', 'admin', 'admin-mcp', 'services', 'locale-html'].map(name => 'tests-edge/' + name + '.test.mjs');
  const specific = new Set([...unitFiles, ...edgeFiles, 'tests-web/fixtures/pre-care-schema.sql',
    'scripts/verify-third-party-config.mjs', 'config/third-party.example.json',
    'docs/third-party-service-disposition.json', 'docs/third-party-service-inventory.json',
    'public/index.html', 'public/data-workspace.html', 'public/style.css', 'public/icon.svg',
    'public/manifest.webmanifest', 'public/manifest-ar.webmanifest', 'public/locales/en.json',
    'public/recipe-ingredient-aliases.json', 'research/manifest.json']);
  // A bounded code/schema/test fixture, not a clone, worktree, full build or corpus copy.
  let fixtureBytes = 0, fixtureFiles = 0;
  const fixtureReceipts = [];
  for (const [name, entry] of composed.entries) {
    if (!specific.has(name) && !/^(cloud|corpus)\/.*\.mjs$/.test(name) && !/^cloud\/.*\.sql$/.test(name) && !/^public\/.*\.js$/.test(name)) continue;
    const bytes = blob(root, entry);
    fixtureBytes += bytes.length;
    if (fixtureBytes > 16 * 1024 * 1024) throw Error('Synthetic source fixture exceeded 16 MiB; no bulk copy permitted.');
    await put(name, bytes); fixtureFiles++;
    fixtureReceipts.push({ path: name, sourceCommit: entry.commit, gitBlob: entry.oid, sha256: sha256(bytes) });
  }
  report.fixture = { files: fixtureFiles, bytes: fixtureBytes, maximumBytes: 16 * 1024 * 1024,
    dependencies: await realpath(join(root, 'node_modules')), receipts: fixtureReceipts };
  await put('package.json', '{"type":"module","private":true}\n');
  await symlink(report.fixture.dependencies, join(fixture, 'node_modules'), 'dir');
  const mainSchema = blob(root, main.get('cloud/schema.sql'));
  await put('tests/compat/main-schema.sql', mainSchema);
  await put('tests/compat/pinned-schema-runtime.test.mjs', await readFile(join(root, 'tests/compat/pinned-schema-runtime.test.mjs')));
  report.schema = { baseline: 'Actual pinned main cloud/schema.sql', mainSchemaSHA256: sha256(mainSchema),
    canonicalSchemaSHA256: sha256(read('cloud/schema.sql')),
    migrations: MIGRATIONS.map(name => ({ path: 'cloud/' + name, sha256: sha256(read('cloud/' + name)) })) };
  await put('tests/compat/inputs.json', JSON.stringify({ ...report.sources, migrations: MIGRATIONS }));
  const assets = { 'recipes.json': '[]', 'afcd-nutrient-details.json': '{}', 'scanner.wasm': '', 'retailer-extension.zip': '' };
  for (const name of ['index.html', 'data-workspace.html', 'style.css', 'icon.svg', 'manifest.webmanifest', 'manifest-ar.webmanifest']) assets[name] = read('public/' + name).toString();
  for (const [name, format] of [['app', 'esm'], ['data-workspace', 'esm'], ['sw', 'iife']]) {
    const built = await build({ entryPoints: [join(fixture, 'public', name + '.js')], bundle: true, minify: true, write: false, format, platform: 'browser' });
    assets[name + '.js'] = built.outputFiles[0].text;
  }
  const release = { sourceCommit: PINNED_THIRD_PARTY, compatibilityMain: PINNED_MAIN, syntheticCompatibility: true };
  await put('cloud/generated.mjs', 'const ASSETS=' + JSON.stringify(assets) + ';\nconst RELEASE=' + JSON.stringify(release) + ';\n' + read('cloud/handler.mjs'));
  await mkdir(join(fixture, 'dist'));
  await build({ entryPoints: [join(fixture, 'cloud/generated.mjs')], bundle: true, minify: true, format: 'esm', platform: 'browser', outfile: join(fixture, 'dist/worker.mjs') });
  report.bundle = { sha256: sha256(await readFile(join(fixture, 'dist/worker.mjs'))), syntheticAssets: ['recipes.json', 'afcd-nutrient-details.json', 'scanner.wasm', 'retailer-extension.zip'],
    compiledBrowserEntries: ['app.js', 'data-workspace.js', 'sw.js'], compatibilityDate: '2026-08-06' };
  for (const name of ['esbuild', 'miniflare', 'workerd']) report.fixture[name + 'Version'] = JSON.parse(await readFile(join(report.fixture.dependencies, name, 'package.json'), 'utf8')).version;
  const results = [suite('targeted-unit', unitFiles), suite('compiled-worker', edgeFiles),
    suite('pinned-main-replay-runtime', ['tests/compat/pinned-schema-runtime.test.mjs'])];
  for (const { check, output } of results) await writeFile(join(root, check.log), output);
  report.state = results.every(({ check }) => check.passed) ? 'ready-for-morgan-review' : 'failed';
} catch (error) {
  report.error = error.stack;
  console.error(error.message);
} finally {
  await rm(fixture, { recursive: true, force: true });
  report.fixtureRemoved = true;
  await mkdir(dirname(reportPath), { recursive: true });
  await writeFile(reportPath, JSON.stringify(report, null, 2) + '\n');
  console.log('Evidence: ' + reportPath);
}
if (report.state !== 'ready-for-morgan-review') process.exitCode = 1;
