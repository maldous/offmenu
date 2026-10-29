import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createOffMenuAuthRuntime, offMenuAuthMode} from '../../apps/web/server/auth-runtime.mjs';
import {workerRuntimeBuildOptions} from '../../scripts/worker-build-options.mjs';

test('missing setting preserves exact legacy verifier without D1 or secrets', async () => {
  const expected = {id: 'Legacy-ID', app_metadata: {roles: ['offmenu-admin']}};
  let seen;
  const legacy = request => {seen = request; return expected;};
  for (const env of [undefined, {}, {OFFMENU_AUTH_MODE: 'netlify'}]) {
    const runtime = createOffMenuAuthRuntime(env, {legacyVerifiedUser: legacy});
    assert.equal(runtime.mode, 'netlify');
    assert.equal(runtime.verifiedUser, legacy);
    const request = new Request('https://offmenu.test/api/state');
    assert.equal(await runtime.verifiedUser(request), expected);
    assert.equal(seen, request);
    for (const path of ['/api/auth/get-session', '/.netlify/identity/user', '/api/state'])
      assert.equal(await runtime.handleAuthRequest(new Request('https://offmenu.test' + path)), null);
  }
});

test('only deployment-owned exact mode selects the new system; unknown settings fail closed', () => {
  for (const OFFMENU_AUTH_MODE of ['', false, true, null, 'Better-Auth', 'better-auth ', 'auto'])
    assert.throws(() => offMenuAuthMode({OFFMENU_AUTH_MODE}), /Unsupported/);
  assert.equal(offMenuAuthMode({OFFMENU_AUTH_MODE: 'better-auth'}), 'better-auth');
  assert.throws(() => createOffMenuAuthRuntime({}), /Legacy/);
  let called = 0;
  assert.throws(() => createOffMenuAuthRuntime({OFFMENU_AUTH_MODE: 'better-auth'},
    {legacyVerifiedUser: () => called++}), /D1/);
  assert.equal(called, 0);
});

test('workerd conditions are confined to the final Worker bundle', () => {
  assert.deepEqual(workerRuntimeBuildOptions, {conditions: ['workerd'], external: ['node:*']});
  assert(Object.isFrozen(workerRuntimeBuildOptions));
  const source = readFileSync(new URL('../../scripts/build.mjs', import.meta.url), 'utf8');
  assert.equal((source.match(/\.\.\.workerRuntimeBuildOptions/g) || []).length, 1);
  assert.match(source, /build\(\{\.\.\.workerRuntimeBuildOptions,entryPoints:\['apps\/web\/server\/generated\.mjs'\]/);
  assert.match(source, /build\(\{entryPoints:\['apps\/web\/src\/app\.js'\],bundle:true/);
});
