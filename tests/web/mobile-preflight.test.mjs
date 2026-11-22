import assert from 'node:assert/strict';
import test from 'node:test';
import {hostPreflight, readEvidence} from '../../scripts/mobile-preflight.mjs';

const source = {commit: '1'.repeat(40), tree: '2'.repeat(40)};
const artifactSha256 = '3'.repeat(64);
const reportSha256 = '4'.repeat(64);
const pass = {...source, artifactSha256, result: 'pass'};
const android = {
  compile: {...pass, artifact: 'debug-apk', toolchainPin: 'Android fixture pin'},
  install: {...pass, target: 'android-emulator', simulatorId: 'ephemeral-fixture', runtimePin: 'Android fixture image'},
  journey: {...pass, driver: 'android-instrumentation', simulatorId: 'ephemeral-fixture', runtimePin: 'Android fixture image',
    reportSha256, cases: ['cold-launch', 'camera-denied-manual-recovery']},
};
const ios = {
  compile: {...pass, artifact: 'unsigned-simulator-app', toolchainPin: 'Xcode fixture pin'},
  install: {...pass, target: 'ios-simulator', simulatorId: 'ephemeral-ios', runtimePin: 'iOS fixture image'},
  journey: {...pass, driver: 'xcuitest', simulatorId: 'ephemeral-ios', runtimePin: 'iOS fixture image',
    reportSha256, cases: ['cold-launch']},
};
const envelope = records => ({schema: 'offmenu.native-preflight/1', source, records});

test('local host caps distinguish missing tools, wrong host, unavailable KVM and tools only', () => {
  const foo = hostPreflight({platform: 'linux', executable: t => t === 'adb'});
  assert.deepEqual(foo.android, {stage: 'toolchain-missing', missing: ['java', 'emulator', 'sdkmanager']});
  assert.equal(foo.ios.stage, 'unsupported-host');
  assert.equal(hostPreflight({platform: 'linux', executable: () => true}).android.stage, 'acceleration-unverified');
  assert.equal(hostPreflight({platform: 'linux', executable: () => true, linuxKvmAccessible: true}).android.stage, 'tools-present-unverified');
  assert.equal(hostPreflight({platform: 'darwin', executable: () => true}).ios.stage, 'tools-present-unverified');
});

test('no receipt, compile, install and platform-specific native journey are distinct', () => {
  assert.deepEqual(readEvidence(source), {android: {stage: 'not-run'}, ios: {stage: 'not-run'}});
  assert.equal(readEvidence(source, envelope({android: {compile: android.compile}})).android.stage, 'compiled');
  assert.equal(readEvidence(source, envelope({android: {compile: android.compile, install: android.install}})).android.stage, 'installed');
  assert.deepEqual(readEvidence(source, envelope({android, ios})), {
    android: {stage: 'simulator-journey-reported', cases: android.journey.cases},
    ios: {stage: 'simulator-journey-reported', cases: ios.journey.cases},
  });
});

test('mismatched pinned revision, artifact, device and WebView-only evidence are refused', () => {
  assert.throws(() => readEvidence({...source, tree: '9'.repeat(40)}, envelope({android})), /revision/);
  assert.throws(() => readEvidence(source, envelope({android: {...android, compile: null}})), /compile/);
  assert.throws(() => readEvidence(source, envelope({android: {...android, install: {...android.install, artifactSha256: '5'.repeat(64)}}})), /install/);
  assert.throws(() => readEvidence(source, envelope({android: {...android, install: {...android.install, target: 'physical-android'}}})), /install/);
  assert.throws(() => readEvidence(source, envelope({android: {...android, journey: {...android.journey, simulatorId: 'other'}}})), /native runner/);
  assert.throws(() => readEvidence(source, envelope({android: {...android, journey: {...android.journey, driver: 'webview-dom'}}})), /native runner/);
  assert.throws(() => readEvidence(source, envelope({ios: {...ios, journey: {...ios.journey, cases: []}}})), /native runner/);
  assert.throws(() => readEvidence(source, envelope({other: android})), /Unknown platform/);
});
