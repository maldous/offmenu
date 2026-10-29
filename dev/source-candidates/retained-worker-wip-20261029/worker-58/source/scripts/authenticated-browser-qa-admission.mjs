import assert from 'node:assert/strict';
import { readFileSync, readlinkSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
export const sourcePins = Object.freeze({'02':'c996bb469621c57820007c261585aba5faddd519','03':'e1de8e839954905d82f939730ac5ea79412bc805','05':'8dc49b2b3683f2532ee4e3581d105c446f6f575e','06':'be166bb61483825498094d496e2caed9d8b775bb'});

const hash = (b, algorithm = 'sha256') => createHash(algorithm).update(b).digest('hex');
const owner = '01a138a5-6210-7ad3-af85-b50eb97eaf38';
const producer = 'd4f80213d35ad3ce5109b24a43ac3e70efeac5d3';
const root = '/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/interactive/ecc963ff-6c73-44d1-ab3e-96e6d6e87886';
export const mockRoot = '/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/mock-preparation/f810ffea-c0fd-4917-bd66-56de4577023f';
const sourceRoot = '/home/user/src/offmenu-workers/worker-05';
export const refs = Object.freeze({
  composition: { path: `${root}/composition-1897020.json`, sha256: '34b8262810ead55dcd57964a3b931e7ab0769f9b8d5a37be2c98d5feeb882e62' },
  inputs: { path: `${root}/inputs-browser58-cca3f660-e8ba-42f4-8393-a8676bfa5f70.json`, sha256: 'd207d436ac8f66b1775f30c1b82e241268f7555edda127b416d1e9d60c6d36a9' },
  mock: { path: `${mockRoot}/dev/wiremock/.runtime/run-19088-1619970d-d071-472b-914c-8b92b4d03774/interactive-qualification.json`, sha256: '086aba9eca0b0983fffca522f366b835671d31eb99eea271678a85cae08f034a' },
  runner: { path: '/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/runs/c996-browser58-20261015-cca3f660/current-run.json', sha256: 'c9ae84196e0fdf9779cb0443898cbf9e5a8e4310ec470b27632a1987eb4e3074' },
});
const environment = () => Object.fromEntries(Object.entries(process.env).filter(([k]) => !k.startsWith('GIT_')));
const git = (...args) => execFileSync('git', ['--no-optional-locks', ...args], { env: environment(), maxBuffer: 16 * 1024 * 1024 });
export function readRef(ref) {
  assert.ok(path.isAbsolute(ref.path)); assert.match(ref.sha256, /^[a-f0-9]{64}$/);
  const b = readFileSync(ref.path); assert.equal(hash(b), ref.sha256, `receipt changed: ${path.basename(ref.path)}`);
  return JSON.parse(b);
}
function birth(pid, boot, ticks, cwd) {
  assert.ok(Number.isInteger(pid) && pid > 1);
  assert.equal(readFileSync('/proc/sys/kernel/random/boot_id', 'utf8').trim(), boot);
  const text = readFileSync(`/proc/${pid}/stat`, 'utf8');
  assert.equal(text.slice(text.lastIndexOf(')') + 2).trim().split(/\s+/)[19], ticks);
  assert.equal(readlinkSync(`/proc/${pid}/cwd`), cwd);
  return readFileSync(`/proc/${pid}/cmdline`, 'utf8').split('\0').filter(Boolean);
}
export function primaryCustody() {
  const index = '/home/user/src/offmenu/.git/index', s = statSync(index);
  return { head: git('-C', '/home/user/src/offmenu', 'rev-parse', 'HEAD').toString().trim(), main: git('rev-parse', 'refs/heads/main').toString().trim(), index: { dev: s.dev, ino: s.ino, size: s.size, mtimeMs: s.mtimeMs, sha256: hash(readFileSync(index)) } };
}
export function inspectPacket() {
  const d = readRef(refs.composition), m = readRef(refs.inputs), mock = readRef(refs.mock), run = readRef(refs.runner);
  assert.equal(d.schema, 'offmenu-owner05-interactive-composition/2');
  assert.equal(mock.schema, 'offmenu-owner05-mock-runtime/2');
  assert.equal(run.schema, 'offmenu.worker05.lifecycle.v2');
  assert.equal(d.ownerThread, owner); assert.equal(mock.ownerThread, owner); assert.equal(run.ownerThread, owner);
  assert.equal(d.sourceRoot, sourceRoot); assert.equal(run.sourceRoot, sourceRoot); assert.equal(run.sourceCommit, producer);
  assert.equal(d.accepted, false); assert.equal(run.accepted, false); assert.equal(d.developmentPendingAcceptance, true);
  assert.equal(m.root, root); assert.equal(m.base, '5f5bdb6ae716cbf80fab1e174d1af2e354468ead');
  for (const pins of [d.pins, m.pins, run.authorPins, run.pins, d.authority.pins]) assert.deepEqual(pins, sourcePins);
  assert.deepEqual(d.inputs, refs.inputs); assert.equal(d.mock.path, refs.mock.path); assert.equal(d.mock.sha256, refs.mock.sha256);
  assert.equal(run.compositionSha256, refs.composition.sha256); assert.equal(run.compositionMode, 'pinned-synthetic'); assert.equal(run.mode, 'pinned-synthetic-mocks');
  assert.equal(run.applicationCommit, sourcePins['02']); assert.equal(d.app.commit, sourcePins['02']);
  assert.equal(d.app.root, `${root}/app`); assert.equal(m.artifact.path, `${root}/app/dist/worker.mjs`);
  for (const a of [d.app.artifact, run.applicationArtifact, d.authority.applicationArtifact]) assert.deepEqual(a, m.artifact);
  assert.equal(run.applicationArtifactSha256, m.artifact.sha256); assert.equal(hash(readFileSync(m.artifact.path)), m.artifact.sha256);
  assert.deepEqual(d.app.schemas, m.schemas);
  for (const [name, expected] of Object.entries(m.schemas)) assert.equal(hash(readFileSync(`${root}/app/${name}`)), expected);
  assert.equal(d.compositionSha256, m.compositionSha256); assert.equal(d.authority.compositionSha256, m.compositionSha256);
  assert.equal(m.compositionSha256, hash(JSON.stringify({ base: m.base, pins: m.pins, trees: m.trees, files: m.files })));
  assert.deepEqual(run.grantBinding, d.authority); assert.equal(d.authority.sourceThread, '01a137cf-2242-761d-8fd7-6e6fc5658013');
  assert.equal(d.authority.boundSession, owner); assert.equal(d.authority.boundRoot, sourceRoot);
  assert.equal(d.authority.grant, 'Explicit current native root task: owner05 interactive isolated private DEV; selected02/03/05/06 pins; no production/provider/paid/security changes.');
  assert.deepEqual([...d.authority.permittedActions].sort(), ['owned-loopback-preview', 'synthetic-fixture-account-flows', 'fresh-isolated-synthetic-state', 'independent58-read/flow-checks', 'birth-verified-own-process-stop'].sort());
  assert.equal(d.authority.actualSuppliedControls.mandatoryReviewer, 'auto_review');
  assert.equal(d.authority.actualSuppliedControls.namedProfile, null); assert.equal(d.authority.actualSuppliedControls.approvalPolicy, null);
  assert.equal(d.authority.environmentProfile, null); assert.equal(d.authority.notNewAccountGrant, true);
  assert.equal(d.scenario, 'success'); assert.equal(mock.status, 'qualified-live');
  assert.equal(mock.sourceOwner, '06'); assert.equal(mock.sourceCommit, sourcePins['06']);
  assert.equal(mock.identity.assertions, 176); assert.equal(mock.resetCheck.assertions, 2);
  assert.equal(mock.custody.schemaVersion, 2); assert.equal(mock.custody.cwd, `${mockRoot}`);
  assert.equal(mock.custody.root, `${mockRoot}/dev/wiremock/.runtime/run-19088-1619970d-d071-472b-914c-8b92b4d03774`);
  assert.equal(mock.nativeCustody.path, `${mock.custody.root}/custody.json`);
  assert.deepEqual(readRef(mock.nativeCustody), mock.custody);
  const c = mock.custody;
  assert.equal(c.jar, '/home/user/src/offmenu-workers/worker-06/dev/wiremock/.cache/wiremock-standalone-3.13.2.jar');
  assert.equal(hash(readFileSync(c.jar), 'sha512'), mock.jarSha512);
  assert.equal(c.jarSha512, mock.jarSha512);
  assert.equal(mock.runtimeSource.path, `${mockRoot}/dev/wiremock/runtime.mjs`);
  assert.equal(hash(readFileSync(mock.runtimeSource.path)), mock.runtimeSource.sha256);
  const started = Date.parse(c.startedAt), qualified = Date.parse(mock.qualifiedAt), composed = Date.parse(d.qualifiedAt);
  assert.ok(Number.isFinite(started) && Number.isFinite(qualified) && Number.isFinite(composed));
  assert.ok(started <= qualified && qualified <= composed && composed <= Date.now(), 'qualification must follow this runtime start');
  for (const receipt of [d, mock]) if (receipt.expiresAt !== undefined) assert.ok(Number.isFinite(Date.parse(receipt.expiresAt)) && Date.parse(receipt.expiresAt) > Date.now() && Date.parse(receipt.expiresAt) >= Date.parse(receipt.qualifiedAt), 'explicit qualification expired');
  const hz = Number(execFileSync('getconf', ['CLK_TCK'], { env: environment(), encoding: 'utf8' }));
  const bootTime = Number(readFileSync('/proc/stat', 'utf8').match(/^btime (\d+)$/m)[1]);
  assert.ok(Math.abs(started - (bootTime + Number(c.birthTicks) / hz) * 1000) <= 5000, 'native timestamp must match kernel birth');
  const execution = readRef(mock.executionEvidence);
  assert.equal(mock.executionEvidence.path, `${c.root}/identity-execution.json`);
  assert.equal(execution.schema, 'offmenu-owner05-identity-execution/1'); assert.equal(execution.ownerThread, owner);
  assert.equal(execution.sourceCommit, sourcePins['06']); assert.deepEqual(execution.custody, c);
  assert.deepEqual(execution.identity, mock.identity); assert.deepEqual(execution.reset, mock.reset); assert.deepEqual(execution.resetCheck, mock.resetCheck);
  assert.equal(execution.validator.path, `${mockRoot}/dev/wiremock/identity-validation.mjs`);
  assert.equal(hash(readFileSync(execution.validator.path)), execution.validator.sha256);
  const reset = readRef({ path: mock.reset.receipt, sha256: mock.reset.sha256 });
  const audit = readRef({ path: mock.reset.previousAudit, sha256: mock.reset.previousAuditSha256 });
  assert.equal(reset.operation, 'reset'); assert.equal(reset.result.reset, true); assert.deepEqual(reset.custody, c);
  assert.equal(audit.operation, 'audit'); assert.deepEqual(audit.custody, c);
  assert.ok(started <= Date.parse(audit.at) && Date.parse(audit.at) <= Date.parse(reset.at) && Date.parse(reset.at) <= Date.parse(execution.completedAt) && Date.parse(execution.completedAt) <= qualified);
  const lock = JSON.parse(readFileSync(`${mockRoot}/dev/wiremock/runtime-lock.json`));
  assert.equal(lock.sha512, mock.jarSha512); assert.equal(lock.version, mock.version); assert.equal(c.version, mock.version);
  assert.equal(hash(readFileSync(m.scannerDependency.path)), m.scannerDependency.sha256);
  assert.ok(m.files.length === 134 && m.inputBytes < 16 * 1024 * 1024);
  const fileHashes = [];
  for (const f of m.files) {
    assert.ok(['app', 'mock', 'audit', 'producer-input'].includes(f.part)); assert.ok(!path.isAbsolute(f.path) && !f.path.split('/').includes('..'));
    assert.equal(f.commit, sourcePins[{ app: '02', mock: '06', audit: '03', 'producer-input': '05' }[f.part]]);
    assert.equal(git('rev-parse', `${f.commit}:${f.path}`).toString().trim(), f.blob);
    assert.equal(hash(git('cat-file', 'blob', f.blob)), f.sha256);
    if (f.materialized) assert.equal(hash(readFileSync(f.part === 'mock' ? `${mockRoot}/${f.path}` : `${root}/${f.part}/${f.path}`)), f.sha256);
    fileHashes.push({ part: f.part, path: f.path, commit: f.commit, sha256: f.sha256 });
  }
  for (const [name, commit] of Object.entries(sourcePins)) assert.equal(git('rev-parse', `${commit}^{tree}`).toString().trim(), m.trees[name]);
  assert.equal(run.status, 'ready'); assert.equal(run.url, 'http://127.0.0.1:18818/'); assert.equal(run.port, 18818);
  assert.equal(run.runId, 'c996-browser58-20261015-cca3f660'); assert.equal(run.freshState, true);
  assert.equal(run.stateId, `worker-05-${run.runId}`); assert.equal(run.stateNamespace, run.stateId);
  assert.equal(run.statePath, `/home/user/src/offmenu-data/dev-preview-20261014/states/${run.stateId}`);
  assert.equal(run.lifecycleLeaseId, `${run.runId}-${run.pid}-${run.startTicks}`);
  const runnerArgs = birth(run.pid, run.bootId, run.startTicks, sourceRoot);
  assert.ok(runnerArgs.includes('dev-server.mjs') || runnerArgs.includes(`${sourceRoot}/dev-server.mjs`));
  const mockArgs = birth(c.pid, c.bootId, c.birthTicks, c.cwd);
  for (const [flag, value] of [['--root-dir', c.root], ['--port', String(c.port)], ['--bind-address', '127.0.0.1']]) assert.equal(mockArgs[mockArgs.indexOf(flag) + 1], value);
  assert.ok(mockArgs.includes(c.jar));
  const actorsSource = git('show', `${sourcePins['06']}:dev/wiremock/fixtures.mjs`);
  const packet = { descriptor: d, manifest: m, mock, runner: run, refs, producer, fileHashes, actorsSourceSha256: hash(actorsSource), actorsSource }; verifyPreparation(m); verifySelectedEvidence(packet); return packet;
}
export async function createAdmission() {
  verifyBrowserReservation();
  const packet = inspectPacket(), observedAt = Date.now();
  const review = readRef(reviewRef); assert.equal(review.verdict, 'PASS_SCOPED_EXCLUSIVE_QA_PAIRED_ADMISSION'); assert.equal(review.producer, producer); assert.deepEqual(review.descriptor, refs.composition); assert.deepEqual(review.inputs, refs.inputs); assert.equal(review.qualification.sha256, refs.mock.sha256);
  const { runner: run, mock, manifest: m } = packet;
  const producerFiles = ['dev-server.mjs', 'dev-entry.mjs', 'dev-lifecycle.mjs', 'interactive-preview.mjs'].map(name => ({ name, sha256: hash(git('show', `${producer}:${name}`)) }));
  const { createMappings } = await import(pathToFileURL(`${mockRoot}/dev/wiremock/mappings.mjs`).href);
  const mappings = createMappings().map(value => value.request.urlPath === '/__offmenu_fixture_health' ? { ...value, response: { ...value.response, jsonBody: { ...value.response.jsonBody, custodyToken: mock.custody.token } } } : value);
  assert.equal(hash(JSON.stringify(mappings)), mock.custody.mappingsSha256);
  // New observation lease bounds this consumer run; it is not an owner-issued expiry.
  const assertQualified = async () => {
    assert.ok(Date.now() - observedAt <= 15 * 60 * 1000, 'consumer observation window expired');
    verifyBrowserReservation();
    readRef(reviewRef);
    for (const ref of Object.values(refs)) readRef(ref);
    verifySelectedEvidence(packet);
    verifyPreparation(packet.manifest);
    for (const f of producerFiles) assert.equal(hash(readFileSync(`${sourceRoot}/${f.name}`)), f.sha256, 'producer source changed');
    for (const receipt of [packet.descriptor, mock]) if (receipt.expiresAt !== undefined) assert.ok(Date.parse(receipt.expiresAt) > Date.now(), 'explicit qualification expired');
    assert.equal(hash(readFileSync(mock.custody.jar), 'sha512'), mock.jarSha512);
    assert.equal(hash(readFileSync(m.scannerDependency.path)), m.scannerDependency.sha256);
    assert.equal(hash(readFileSync(m.artifact.path)), m.artifact.sha256);
    for (const f of m.files.filter(f => f.materialized)) assert.equal(hash(readFileSync(f.part === 'mock' ? `${mockRoot}/${f.path}` : `${root}/${f.part}/${f.path}`)), f.sha256);
    const runnerArgs = birth(run.pid, run.bootId, run.startTicks, sourceRoot);
    assert.ok(runnerArgs.includes('dev-server.mjs') || runnerArgs.includes(`${sourceRoot}/dev-server.mjs`));
    const mockArgs = birth(mock.custody.pid, mock.custody.bootId, mock.custody.birthTicks, mock.custody.cwd);
    for (const [flag, value] of [['--root-dir', mock.custody.root], ['--port', String(mock.custody.port)], ['--bind-address', '127.0.0.1']]) assert.equal(mockArgs[mockArgs.indexOf(flag) + 1], value);
    assert.ok(mockArgs.includes(mock.custody.jar));
    readRef(mock.nativeCustody);
    readRef(mock.executionEvidence);
    readRef({ path: mock.reset.receipt, sha256: mock.reset.sha256 });
    readRef({ path: mock.reset.previousAudit, sha256: mock.reset.previousAuditSha256 });
    for (const mapping of mappings) assert.deepEqual(JSON.parse(readFileSync(`${mock.custody.root}/mappings/${mapping.id}.json`)), mapping);
    const health = await fetch(`http://127.0.0.1:${mock.custody.port}/__offmenu_fixture_health`, { redirect: 'error', signal: AbortSignal.timeout(1500) });
    assert.equal(health.status, 200); assert.equal((await health.json()).custodyToken, mock.custody.token);
    const live = await fetch(new URL('/__dev/status', run.url), { redirect: 'error', signal: AbortSignal.timeout(1500) });
    assert.equal(live.status, 200); const status = await live.json();
    for (const key of ['ownerThread', 'sourceCommit', 'runId', 'stateId', 'applicationCommit', 'applicationArtifactSha256', 'compositionSha256']) assert.equal(status[key], run[key], `live status ${key}`);
    // Current producer status omits root/port; receipt plus /proc and actual URL bind them.
    for (const key of ['sourceRoot', 'port']) if (status[key] !== undefined) assert.equal(status[key], run[key], `conflicting optional live ${key}`);
    assert.equal(status.productionCredentials, false); assert.equal(status.freshState, true);
    assert.equal(status.composition, run.compositionMode); assert.deepEqual(status.authorPins, sourcePins);
    assert.deepEqual(status.applicationArtifact, m.artifact); if (status.pins !== undefined) assert.deepEqual(status.pins, sourcePins);
    return status;
  };
  const status = await assertQualified();
  const { ACTORS } = await import(`data:text/javascript;base64,${packet.actorsSource.toString('base64')}`);
  return { packet, status, actors: ACTORS, assertQualified, observedAt: new Date(observedAt).toISOString() };
}

export const reviewRef = {path:'/home/user/src/offmenu-workers/worker-58/docs/authenticated-browser-exclusive-review.json',sha256:'95b40e52afb3a9718ee7f1189a1144842e8abd4c32de015aaf6973d23c6886d0'};
function verifyPreparation(m) {
 assert.equal(m.mockRoot,mockRoot); const p=readRef(m.mockPreparation); assert.equal(p.root,mockRoot); assert.equal(p.sourceOwner,'06'); assert.equal(p.sourceCommit,sourcePins['06']); assert.equal(p.ownerThread,owner); assert.equal(p.files.length,21);
 for(const f of p.files){assert.ok(!path.isAbsolute(f.path)&&!f.path.split('/').includes('..'));assert.equal(hash(readFileSync(`${mockRoot}/${f.path}`)),f.sha256);assert.equal(hash(git('cat-file','blob',f.blob)),f.sha256);assert.equal(git('rev-parse',`${sourcePins['06']}:${f.path}`).toString().trim(),f.blob);}
}
function verifySelectedEvidence(packet) {
 const q=packet.mock,x=readRef(q.selectedExecution);assert.equal(x.schema,'offmenu-owner05-selected-mock-execution/1');assert.equal(x.ownerThread,owner);assert.equal(x.sourceCommit,sourcePins['06']);assert.deepEqual(x.custody,q.custody);assert.deepEqual(x.identity,q.identity);assert.deepEqual(x.reset,q.reset);assert.deepEqual(x.resetCheck,q.resetCheck);assert.equal(x.callback.assertions,28);
 const audit=readRef({path:x.audit.receipt,sha256:x.audit.sha256});assert.deepEqual(audit.custody,q.custody);assert.equal(audit.operation,'audit');assert.equal(audit.result.unmatched.length,0);assert.ok(Date.parse(audit.at)<=Date.parse(x.completedAt)&&Date.parse(x.completedAt)<=Date.parse(q.qualifiedAt));if(q.qualificationPreparation)readRef(q.qualificationPreparation);
}

export const reservationRef={path:'/home/user/src/offmenu-data/dev-preview-20261014/workers/worker-05/c996-browser-qa/cca3f660-e8ba-42f4-8393-a8676bfa5f70/reservation.json',sha256:'8e606a531ba1d6f44af4492e4dca8bc596246ab8945e3e9826d11c46fe1fa45d'};
export function verifyBrowserReservation(){
 const r=readRef(reservationRef);assert.equal(process.env.CODEX_THREAD_ID,'01a139aa-f2c2-73b0-b45f-cbbafe2e326c');assert.equal(r.consumerThread,process.env.CODEX_THREAD_ID);assert.equal(r.ownerThread,owner);assert.equal(r.rootSourceThread,'01a137cf-2242-761d-8fd7-6e6fc5658013');assert.equal(r.exclusive,true);assert.equal(r.app.pid,1898059);assert.equal(r.app.birth.startTicks,'4721279');assert.equal(r.mock.pid,1897020);assert.equal(r.mock.birth.startTicks,'4720917');assert.equal(r.app.port,18818);assert.equal(r.mock.port,19088);assert.equal(r.app.runId,'c996-browser58-20261015-cca3f660');assert.equal(r.app.statePath,'/home/user/src/offmenu-data/dev-preview-20261014/states/worker-05-c996-browser58-20261015-cca3f660');assert.deepEqual(r.actors,['alice','bob','admin']);assert.deepEqual(r.permittedJourneys,['password-account-isolation-logout','care','community','admin']);assert.deepEqual(r.app.receipt,refs.runner);assert.equal(r.descriptor.path,refs.composition.path);assert.equal(r.descriptor.sha256,refs.composition.sha256);return r;
}
