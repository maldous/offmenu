import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {mkdtemp, mkdir, readFile, readdir, rm, stat, writeFile} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {build} from 'esbuild';
import {extensionBuildOptions} from '../scripts/extension-build-options.mjs';
import {checkGeneratedExtension, main} from '../scripts/check-generated-extension.mjs';

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'offmenu generated extension '));
  t.after(() => rm(root, {recursive: true, force: true}));
  await mkdir(join(root, 'extension'));
  await writeFile(join(root, 'extension/popup-source.js'), "import {message} from './message.js'; console.log(message);\n");
  await writeFile(join(root, 'extension/message.js'), "export const message = 'current';\n");
  return root;
}

async function generate(root) {
  await build({...extensionBuildOptions, absWorkingDir: root});
  return readFile(join(root, extensionBuildOptions.outfile));
}

function reporter() {
  const output = [], errors = [];
  return {output, errors, log: message => output.push(message), error: message => errors.push(message)};
}

test('application build and generated-file check share the original extension options', async () => {
  assert.deepEqual(extensionBuildOptions, {
    entryPoints: ['extension/popup-source.js'], bundle: true, minify: true, outfile: 'extension/popup.js',
  });
  const source = await readFile(new URL('../scripts/build.mjs', import.meta.url), 'utf8');
  assert.match(source, /await build\(extensionBuildOptions\)/);
});

test('current output is verified byte-for-byte without changing file metadata', async t => {
  const root = await fixture(t), bytes = await generate(root);
  const before = await stat(join(root, extensionBuildOptions.outfile));
  const result = await checkGeneratedExtension(root);
  assert.equal(result.status, 'current');
  assert.deepEqual(result.committed, result.generated);
  assert.equal(result.generated.sha256, createHash('sha256').update(bytes).digest('hex'));
  assert.equal(result.node, process.version);
  assert.match(result.esbuild, /^\d+\.\d+\.\d+/);
  const after = await stat(join(root, extensionBuildOptions.outfile));
  assert.equal(after.mtimeMs, before.mtimeMs);
  assert.deepEqual(await readFile(join(root, extensionBuildOptions.outfile)), bytes);
});

test('changed transitive input reports drift and leaves committed bytes untouched', async t => {
  const root = await fixture(t), bytes = await generate(root);
  await writeFile(join(root, 'extension/message.js'), "export const message = 'changed';\n");
  const result = await checkGeneratedExtension(root);
  assert.equal(result.status, 'drift');
  assert.notEqual(result.generated.sha256, result.committed.sha256);
  assert.deepEqual(await readFile(join(root, extensionBuildOptions.outfile)), bytes);
});

test('missing generated file is reported and is not recreated', async t => {
  const root = await fixture(t);
  const before = await readdir(join(root, 'extension'));
  const result = await checkGeneratedExtension(root);
  assert.equal(result.status, 'missing');
  assert.equal(result.committed, null);
  assert.deepEqual(await readdir(join(root, 'extension')), before);
});

test('empty committed output is drift rather than a missing file', async t => {
  const root = await fixture(t);
  await writeFile(join(root, extensionBuildOptions.outfile), '');
  const result = await checkGeneratedExtension(root);
  assert.equal(result.status, 'drift');
  assert.equal(result.committed.bytes, 0);
  assert.equal((await readFile(join(root, extensionBuildOptions.outfile))).length, 0);
});

test('CLI entry returns zero and reports matching hashes for current output', async t => {
  const root = await fixture(t);
  await generate(root);
  const output = reporter();
  assert.equal(await main(root, output), 0);
  assert.equal(JSON.parse(output.output[0]).status, 'current');
  assert.deepEqual(output.errors, []);
});

test('CLI entry returns one for drift with actionable read-only diagnostics', async t => {
  const root = await fixture(t), bytes = await generate(root);
  await writeFile(join(root, 'extension/message.js'), "export const message = 'drift';\n");
  const output = reporter();
  assert.equal(await main(root, output), 1);
  assert.equal(JSON.parse(output.output[0]).status, 'drift');
  assert.match(output.errors[0], /No files were written.*npm run build/);
  assert.deepEqual(await readFile(join(root, extensionBuildOptions.outfile)), bytes);
});

test('CLI entry returns one for missing output without creating it', async t => {
  const root = await fixture(t), output = reporter();
  assert.equal(await main(root, output), 1);
  assert.match(output.errors[0], /is missing/);
  await assert.rejects(readFile(join(root, extensionBuildOptions.outfile)), {code: 'ENOENT'});
});

test('syntax errors return two without masking the failure or overwriting output', async t => {
  const root = await fixture(t), bytes = await generate(root);
  await writeFile(join(root, 'extension/popup-source.js'), 'import {');
  const output = reporter();
  assert.equal(await main(root, output), 2);
  assert.match(output.errors[0], /could not complete/);
  assert.deepEqual(output.output, []);
  assert.deepEqual(await readFile(join(root, extensionBuildOptions.outfile)), bytes);
});

test('non-missing filesystem errors return two instead of claiming a drift result', async t => {
  const root = await fixture(t);
  await mkdir(join(root, extensionBuildOptions.outfile));
  const output = reporter();
  assert.equal(await main(root, output), 2);
  assert.match(output.errors[0], /could not complete/);
  assert.deepEqual(output.output, []);
});
