import {createHash} from 'node:crypto';
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {extensionBuildOptions} from './extension-build-options.mjs';

const repositoryRoot = fileURLToPath(new URL('../', import.meta.url));
const sha256 = bytes => createHash('sha256').update(bytes).digest('hex');

export async function checkGeneratedExtension(root = repositoryRoot) {
  const {build, version} = await import('esbuild');
  const {outputFiles} = await build({
    ...extensionBuildOptions,
    absWorkingDir: resolve(root),
    write: false,
    logLevel: 'silent',
  });
  const generated = Buffer.from(outputFiles[0].contents);
  let committed;
  try {
    committed = await readFile(resolve(root, extensionBuildOptions.outfile));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  return {
    path: extensionBuildOptions.outfile,
    status: !committed ? 'missing' : committed.equals(generated) ? 'current' : 'drift',
    node: process.version,
    esbuild: version,
    committed: committed ? {bytes: committed.length, sha256: sha256(committed)} : null,
    generated: {bytes: generated.length, sha256: sha256(generated)},
  };
}

export async function main(root = repositoryRoot, {
  log = message => console.log(message),
  error = message => console.error(message),
} = {}) {
  try {
    const result = await checkGeneratedExtension(root);
    log(JSON.stringify(result, null, 2));
    if (result.status === 'current') return 0;
    error(`${result.path} is ${result.status === 'missing' ? 'missing' : 'out of date'}. No files were written. Regenerate with npm run build and review the generated diff before committing.`);
    return 1;
  } catch (cause) {
    error(`Generated extension check could not complete: ${cause.message}`);
    return 2;
  }
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  process.exitCode = await main();
}
