import {accessSync, constants, readFileSync, realpathSync, statSync} from 'node:fs';
import {delimiter, join} from 'node:path';
import {fileURLToPath} from 'node:url';

const targets = Object.freeze({
  android: {host: ['linux', 'darwin'], tools: ['java', 'adb', 'emulator', 'sdkmanager'],
    artifact: 'debug-apk', target: 'android-emulator', driver: 'android-instrumentation'},
  ios: {host: ['darwin'], tools: ['xcodebuild', 'xcrun'],
    artifact: 'unsigned-simulator-app', target: 'ios-simulator', driver: 'xcuitest'},
});
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const hash = (value, digits) => typeof value === 'string' && value.length === digits && /^[0-9a-f]+$/.test(value);
const nonempty = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
const bound = (record, source) => object(record) && record.commit === source.commit && record.tree === source.tree;
const sources = source => object(source) && hash(source.commit, 40) && hash(source.tree, 40);

// This checks local file availability only. Executable shims do not prove a
// usable toolchain, a pinned SDK image, successful signing, or a real device.
export function hostPreflight({platform, executable, linuxKvmAccessible = false}) {
  return Object.fromEntries(Object.entries(targets).map(([name, spec]) => {
    if (!spec.host.includes(platform)) return [name, {stage: 'unsupported-host', missing: []}];
    const missing = spec.tools.filter(tool => !executable(tool));
    if (missing.length) return [name, {stage: 'toolchain-missing', missing}];
    if (name === 'android' && platform === 'linux' && !linuxKvmAccessible) {
      return [name, {stage: 'acceleration-unverified', missing: []}];
    }
    return [name, {stage: 'tools-present-unverified', missing: []}];
  }));
}

// A receipt reports evidence; this does not attest artifacts or the issuer.
export function readEvidence(expected, envelope) {
  if (!sources(expected)) throw new TypeError('Expected full commit and tree are required.');
  if (envelope === undefined) return {android: {stage: 'not-run'}, ios: {stage: 'not-run'}};
  if (!object(envelope) || envelope.schema !== 'offmenu.native-preflight/1' ||
      !bound(envelope.source, expected) || !object(envelope.records)) {
    throw new TypeError('Receipt schema or source revision does not match.');
  }
  if (Object.keys(envelope.records).some(platform => !Object.hasOwn(targets, platform))) {
    throw new TypeError('Unknown platform in native receipt.');
  }
  return Object.fromEntries(Object.entries(targets).map(([name, spec]) => {
    if (!Object.hasOwn(envelope.records, name)) return [name, {stage: 'not-run'}];
    const entry = envelope.records[name];
    if (!object(entry) || !object(entry.compile) || !bound(entry.compile, expected) ||
        entry.compile.result !== 'pass' || entry.compile.artifact !== spec.artifact ||
        !hash(entry.compile.artifactSha256, 64) || !nonempty(entry.compile.toolchainPin)) {
      throw new TypeError(name + ': no valid exact-source compile receipt.');
    }
    const sameArtifact = record => bound(record, expected) &&
      record.artifactSha256 === entry.compile.artifactSha256;
    if (!Object.hasOwn(entry, 'install') && !Object.hasOwn(entry, 'journey')) return [name, {stage: 'compile-reported'}];
    if (!sameArtifact(entry.install) || entry.install.result !== 'pass' || entry.install.target !== spec.target ||
        !nonempty(entry.install.simulatorId) || !nonempty(entry.install.runtimePin)) {
      throw new TypeError(name + ': install receipt does not match simulated target and compiled artifact.');
    }
    if (!Object.hasOwn(entry, 'journey')) return [name, {stage: 'install-reported'}];
    if (!sameArtifact(entry.journey) || entry.journey.result !== 'pass' || entry.journey.driver !== spec.driver ||
        entry.journey.simulatorId !== entry.install.simulatorId || entry.journey.runtimePin !== entry.install.runtimePin ||
        !hash(entry.journey.reportSha256, 64) || !Array.isArray(entry.journey.cases) || !entry.journey.cases.length ||
        !entry.journey.cases.every(nonempty) || new Set(entry.journey.cases).size !== entry.journey.cases.length) {
      throw new TypeError(name + ': no matching native runner journey report.');
    }
    return [name, {stage: 'journey-reported', cases: entry.journey.cases}];
  }));
}

function availablePlatformTools(name, env = process.env) {
  const dirs = (env.PATH ?? '').split(delimiter).filter(Boolean);
  for (const sdk of [env.ANDROID_HOME, env.ANDROID_SDK_ROOT].filter(Boolean)) {
    dirs.push(join(sdk, 'platform-tools'), join(sdk, 'emulator'), join(sdk, 'cmdline-tools', 'latest', 'bin'));
  }
  return dirs.some(dir => {
    const path = join(dir, name);
    try { accessSync(path, constants.X_OK); return statSync(path).isFile(); } catch { return false; }
  });
}

function run(args) {
  if (args.length !== 0 && args.length !== 3) {
    throw new TypeError('Usage: node scripts/mobile-preflight.mjs [<expected-commit> <expected-tree> <receipt.json>]');
  }
  let linuxKvmAccessible = false;
  if (process.platform === 'linux') {
    try { accessSync('/dev/kvm', constants.R_OK | constants.W_OK); linuxKvmAccessible = true; } catch {}
  }
  const host = hostPreflight({platform: process.platform, executable: availablePlatformTools, linuxKvmAccessible});
  const evidence = args.length ? readEvidence({commit: args[0], tree: args[1]}, JSON.parse(readFileSync(args[2], 'utf8'))) :
    {android: {stage: 'not-run'}, ios: {stage: 'not-run'}};
  console.log(JSON.stringify({host, evidence}, null, 2));
}

if (process.argv[1] && realpathSync(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { run(process.argv.slice(2)); }
  catch (error) {
    console.error(error instanceof TypeError ? error.message : 'Could not read or parse the receipt.');
    process.exitCode = 1;
  }
}
