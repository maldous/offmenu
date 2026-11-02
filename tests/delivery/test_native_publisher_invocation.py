"""Only disposable, unprivileged Python fixtures; no sudo/installed publisher."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from uuid import uuid4

import native_publisher_invocation as module


ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('invocation_test_runner', ROOT/'tools/delivery/windmill_runner.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def fixture():
    source = dict(repository='maldous/offmenu', branch='feature/synthetic', base='a'*40,
                  head='b'*40, tree='c'*40, target='develop', policy_sha256='d'*64)
    binding = dict(repository=source['repository'], owner='fixture-owner',
                   issue_id='12345678-1234-1234-1234-123456789abc', project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',
                   head_branch=source['branch'], **{k: source[k] for k in ('base', 'head', 'tree')})
    native = dict(issue_id=binding['issue_id'], project_id=binding['project_id'], owner=binding['owner'],
                  unit_sha256='e'*64, packet_sha256='f'*64, source=source)
    config = dict(version=1, publisherUid=984, publisherGid=976, logicalOwner=binding['owner'],
                  binding=binding, snapshot={'native_runtime': native})
    inner = dict(version=1, mode='step', operation_id=module.fingerprint(binding),
                 issue_id=native['issue_id'], project_id=native['project_id'], owner=native['owner'],
                 unit_sha256=native['unit_sha256'], packet_sha256=native['packet_sha256'],
                 source_sha256=module.fingerprint(source))
    envelope = dict(version=1, mode='invoke', invocation_id=str(uuid4()), request=inner)
    return config, envelope


def response(inner):
    return dict(version=1, kind='native-publisher-response-v1', phase='integration', status='ready',
                request_sha256=module.fingerprint(inner),
                **{key: inner[key] for key in module.INNER - {'version', 'mode'}})


def terminal(inner):
    result = response(inner)
    return dict(outcome='succeeded', child_started=True, child_pid=123, child_starttime=1,
                subreaper_verified=True, direct_child_reaped=True, waitpid_echild=True,
                child_tree_gone=True, response=result, response_sha256=module.fingerprint(result))


class SyntheticHost:
    """In-process test fixture only, never selected through a request or CLI."""
    uid = os.getuid()
    runner = runner
    timeout = .25

    def __init__(self, root, scenario='normal'):
        self.root = Path(root).resolve()
        self.cwd = self.root
        self.config, _ = fixture()
        self.directory = self.root/'prepared-original-transaction'
        self.scenario = scenario
        body = '''import os,sys,json,time
from pathlib import Path
q=json.load(sys.stdin)
root=Path(ROOT)
(root/'computation-count').open('a').write('once\\n')
if SCENARIO in ('escape','doublefork','cancel'):
    child=os.fork()
    if child==0:
        os.setsid()
        if SCENARIO=='doublefork':
            descendant=os.fork()
            if descendant!=0: os._exit(0)
        (root/'descendant-pid').write_text(str(os.getpid()))
        time.sleep(30)
    (root/'direct-ready').write_text(str(os.getpid()))
    time.sleep(30)
if SCENARIO=='flood':
    sys.stdout.write('x'*20000);sys.stdout.flush();time.sleep(30)
if SCENARIO=='bad':
    print('private invalid output');sys.exit(0)
if SCENARIO=='nonzero':
    sys.stderr.write('private stderr');sys.exit(2)
r={k:v for k,v in q.items() if k not in ('mode','version')}
r.update(version=1,kind='native-publisher-response-v1',phase='integration',status='ready',request_sha256=HASH)
print(json.dumps(r))
'''
        self._body = body.replace('ROOT', repr(str(self.root))).replace('SCENARIO', repr(scenario))

    def prepare(self):
        self.directory.mkdir(mode=0o700)
        (self.directory/'binding.json').write_text('original binding\n')
        (self.directory/'binding.json').chmod(0o600)

    def admit(self, inner):
        phase = module.association(self.config, inner)
        module.require(self.directory.is_dir(), 'prepared_transaction_missing')
        self.command = [sys.executable, '-I', '-B', '-c', self._body.replace('HASH', repr(module.fingerprint(inner)))]
        return self.directory, phase, '1'*64


def isolated(raw, root, scenario):
    host = SyntheticHost(root, 'escape' if scenario == 'falsecleanup' else scenario)
    if scenario == 'crash':
        with patch.object(module, '_supervise', side_effect=lambda *_: os._exit(99)):
            module._invoke(raw, host)
    if scenario == 'falsecleanup':
        original = runner.cleanup
        def false_cleanup(proc):
            proc.kill(); proc.wait()
            return True
        try:
            runner.cleanup = false_cleanup
            result = module._invoke(raw, host)
        finally:
            runner.cleanup = original
            # Fixture-only cleanup after recording the real failed proof; do
            # not upgrade that receipt using this later observation.
            from types import SimpleNamespace
            pid = int((host.root/'direct-ready').read_text())
            original(SimpleNamespace(pid=pid, poll=lambda: 0))
    else:
        result = module._invoke(raw, host)
    print(json.dumps(result), flush=True)


class InvocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='publisher-invocation-')
        self.addCleanup(self.temp.cleanup)
        self.host = SyntheticHost(self.temp.name)
        self.host.prepare()
        self.config, self.envelope = fixture()

    def invoke(self, envelope=None):
        return module._invoke(module.wire(envelope or self.envelope), self.host)

    def driver(self, scenario='normal', envelope=None):
        data = module.wire(envelope or self.envelope)
        code = ('from test_native_publisher_invocation import isolated; '
                f'isolated({data!r},{self.temp.name!r},{scenario!r})')
        return subprocess.Popen([sys.executable, '-B', '-c', code], cwd=ROOT,
                                env={**module.ENV, 'PYTHONPATH': str(ROOT/'tools/delivery')+':'+str(ROOT/'tests/delivery')},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def finish(self, process):
        out, err = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 0, err)
        self.assertNotIn('private', out)
        return json.loads(out)

    def test_production_identity_refuses_before_protected_reads(self):
        with patch.object(module.os, 'getuid', return_value=1000), \
             patch.object(module.Path, 'lstat', side_effect=AssertionError('protected read')):
            with self.assertRaisesRegex(module.InvocationHold, 'publisher_identity'):
                module.invoke(module.wire(self.envelope))

    def test_pending_review_exports_original_checkpoint_readonly_and_restores_numbers(self):
        # Real graph/checkpoint, synthetic private custody and subprocess only.
        from test_integration_controller import IntegrationControllerTests
        from offmenu.delivery.integration import Controller
        import stokowski_unit_review as consumer
        f = IntegrationControllerTests(methodName='runTest'); f.setUp()
        self.addCleanup(f.doCleanups)
        snapshot = f.snapshot
        snapshot['original_numeric'] = 1.0
        plan = {'operations': [], 'changedFiles': f.binding['outputs']}
        binding = dict(f.binding, version=2, pr_number=None,
            publication=dict(plan_sha256=module.fingerprint(plan),
                             qualification_sha256=module.fingerprint(snapshot)))
        root = f.root/'integration'; root.mkdir(mode=0o700)
        directory = root/('transaction-'+module.fingerprint(binding))
        controller = Controller(directory,binding,root)
        controller.prepare_publication(plan,snapshot)
        state = controller.status()
        state['publication'].update(effect='verified',pr_number=145)
        controller._publication_checkpoint(state)  # Fixture publication, no API.
        controller.run(snapshot)
        for p in root.rglob('*'):
            p.chmod(0o700 if p.is_dir() else 0o600)
        n = dict(issue_id=binding['issue_id'],project_id=binding['project_id'],owner=binding['owner'],
            unit_sha256='e'*64,packet_sha256='f'*64,
            source=dict(repository=binding['repository'],branch=binding['head_branch'],
                base=binding['base'],head=binding['head'],tree=binding['tree'],target='develop',
                policy_sha256=binding['policy_sha256']))
        self.host.directory = directory
        self.host.config.update(binding=binding,logicalOwner=binding['owner'],snapshot={'native_runtime':n})
        inner = dict(version=1,mode='observe',operation_id=module.fingerprint(binding),
            **{k:n[k] for k in ('issue_id','project_id','owner','unit_sha256','packet_sha256')},
            source_sha256=module.fingerprint(n['source']))
        envelope = dict(version=1,mode='review',invocation_id=str(uuid4()),request=inner)
        self.host.review = lambda d,i,c: module.pending_review(d,i,c,root=root,uid=os.getuid())
        def retained():
            return {str(p.relative_to(root)):(p.read_bytes(),p.stat().st_mtime_ns,p.stat().st_mode)
                    for p in root.rglob('*') if p.is_file()}
        before = retained()
        with patch.object(module,'_supervise',side_effect=AssertionError('no child')):
            reply = self.invoke(envelope)
        self.assertEqual(retained(),before)
        calls = []
        def fixed_read(argv,**kwargs):
            calls.append((argv,kwargs))
            return subprocess.CompletedProcess(argv,0,stdout=module.wire(reply,1048576),stderr=b'')
        with patch.object(consumer.subprocess,'run',side_effect=fixed_read):
            b,decision,channels = consumer.protected_checkpoint(envelope)
        self.assertEqual(b,binding)
        self.assertEqual(decision['status'],'merge-intent')
        self.assertIs(type(channels['observation']['original_numeric']),float)
        self.assertEqual(channels['observation']['original_numeric'],1.0)
        self.assertEqual(calls[0][0],['/usr/bin/sudo','-n','-u','#984','-g','#976','--',
            '/opt/offmenu-publisher/venv/bin/python','-I','-B',
            '/opt/offmenu-publisher/tools/delivery/native_publisher_invocation.py'])
        self.assertEqual(json.loads(calls[0][1]['input']),envelope)
        # The later normal step requalifies this exact unconsumed intent;
        # observation never overwrites it with reconciliation-required.
        reader=Controller(directory,binding,root,_existing_only=True)
        reader.require_current_claim=True
        self.assertEqual(reader.pending_unconsumed(snapshot),decision)
        self.assertEqual(retained(),before)
        changed=copy.deepcopy(snapshot);changed['cancel_requested']=True
        with self.assertRaises(Exception):reader.pending_unconsumed(changed)
        self.assertEqual(retained(),before)
        # A reader response with a conflicting state cannot become unit evidence.
        original = copy.deepcopy(reply)
        reply['decision']['status']='merge-verified'
        with patch.object(consumer.subprocess,'run',side_effect=fixed_read):
            with self.assertRaises(Exception):consumer.protected_checkpoint(envelope)
        reply = original
        for path,mutate,reason in (
            (root/'active-owner.json',lambda d:d.update(binding_sha256='0'*64),'review_current_claim'),
            (directory/'repository-claim.json',lambda d:d.update(owner='foreign'),'review_immutable_claim'),
            (directory/'state.json',lambda d:d.update(merge_effect='verified'),'review_pending')):
            raw=path.read_bytes(); value=json.loads(raw);mutate(value);path.write_bytes(module.wire(value))
            with self.subTest(reason=reason):
                with self.assertRaisesRegex(module.InvocationHold,reason):self.invoke(envelope)
            path.write_bytes(raw)
        with sqlite3.connect(directory/'graph.sqlite') as db:
            db.execute("UPDATE checkpoints SET type='pickle'")
        with self.assertRaisesRegex(module.InvocationHold,'review_checkpoint'):self.invoke(envelope)
        invalid=copy.deepcopy(envelope);invalid['request']['mode']='step'
        with self.assertRaisesRegex(module.InvocationHold,'review_read_only'):self.invoke(invalid)

    def test_wire_rejects_extra_duplicate_path_and_bad_identity(self):
        self.assertEqual(module.request(module.wire(self.envelope)), self.envelope)
        values = [{**self.envelope, 'path': '/etc/config'},
                  {**self.envelope, 'invocation_id': '../x'},
                  {**self.envelope, 'version': True},
                  {**self.envelope, 'mode': 'run'},
                  {**self.envelope, 'request': {**self.envelope['request'], 'command': 'arbitrary'}},
                  {**self.envelope, 'request': {**self.envelope['request'], 'issue_id': 'UIF-130'}}]
        for value in values:
            with self.subTest(value=value.keys()), self.assertRaises(module.InvocationHold):
                module.request(module.wire(value))
        raw = module.wire(self.envelope).replace(b'"mode":"invoke"', b'"mode":"invoke","mode":"observe"')
        with self.assertRaises(module.InvocationHold):
            module.request(raw)
        with self.assertRaises(module.InvocationHold):
            module.request(b'x'*16385)

    def test_exact_root_sealed_config_source_and_policy_association(self):
        self.assertEqual(module.association(self.config, self.envelope['request']), 'integration')
        for key in ('operation_id', 'unit_sha256', 'packet_sha256', 'source_sha256'):
            value = {**self.envelope['request'], key: '0'*64}
            with self.subTest(key=key), self.assertRaises(module.InvocationHold):
                module.association(self.config, value)
        for key in ('head', 'tree', 'policy_sha256', 'target'):
            config = copy.deepcopy(self.config)
            config['snapshot']['native_runtime']['source'][key] = '0'*64
            with self.subTest(key=key), self.assertRaises(module.InvocationHold):
                module.association(config, self.envelope['request'])
        for key, value in [('publisherUid', 1000), ('publisherGid', 1000), ('version', True)]:
            with self.subTest(key=key), self.assertRaises(module.InvocationHold):
                module.association({**self.config, key: value}, self.envelope['request'])

    def manifest(self):
        files = {name: 'a'*64 for name in (
            'tools/delivery/native_publisher_invocation.py', 'tools/delivery/windmill_runner.py',
            'tools/delivery/capacity-policy.json', 'tools/delivery/github-app-publisher.mjs',
            'tools/delivery/github-app-adapter.mjs', 'tools/delivery/integration-gateway.mjs',
            'src/offmenu/delivery/integration.py', 'venv/bin/python')}
        return dict(version=1, kind='native-publisher-closure-v1', source_head='b'*40,
                    source_tree='c'*40, node_sha256='d'*64, files=files)

    def test_shared_manifest_bytes_and_large_dependency_map(self):
        value = self.manifest()
        for i in range(1200):
            value['files']['venv/lib/python3.12/site-packages/fixture/module'+str(i)+'.py'] = 'e'*64
        raw = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()+b'\n'
        self.assertGreater(len(raw), module.LIMIT)
        self.assertEqual(module.validate_closure(raw, 'b'*40), value)
        self.assertEqual(module.sha(raw), module.hashlib.sha256(raw).hexdigest())
        with self.assertRaisesRegex(module.InvocationHold, 'closure_canonical_bytes'):
            module.validate_closure(json.dumps(value).encode(), 'b'*40)

    def test_manifest_forbids_source_drift_self_reference_and_private_pem(self):
        value = self.manifest()
        with self.assertRaises(module.InvocationHold):
            module.validate_closure(module.wire(value), 'c'*40)
        for path in ('native-harness-closure.json', '../secret', '/etc/key',
                     'etc/offmenu-publisher/github-app-private-key.pem', 'other.pem'):
            changed = copy.deepcopy(value)
            changed['files'][path] = 'f'*64
            with self.subTest(path=path), self.assertRaises(module.InvocationHold):
                module.validate_closure(module.wire(changed), 'b'*40)
        changed = copy.deepcopy(value)
        changed['files'][module.PUBLIC_CA] = 'f'*64
        self.assertEqual(module.validate_closure(module.wire(changed), 'b'*40), changed)
        del value['files']['tools/delivery/windmill_runner.py']
        with self.assertRaisesRegex(module.InvocationHold, 'closure_required'):
            module.validate_closure(module.wire(value), 'b'*40)

    def test_public_ca_exception_requires_pinned_record_and_exact_size(self):
        import base64
        cert = self.host.root/module.PUBLIC_CA
        cert.parent.mkdir(parents=True)
        cert.write_bytes(b'PUBLIC SYNTHETIC CA')
        record_name = 'venv/lib/python3.12/site-packages/certifi-2026.1.dist-info/RECORD'
        record = self.host.root/record_name
        record.parent.mkdir(parents=True)
        pin = module.sha(cert.read_bytes())
        encoded = base64.urlsafe_b64encode(bytes.fromhex(pin)).rstrip(b'=').decode()
        record.write_text('certifi/cacert.pem,sha256='+encoded+','+str(cert.stat().st_size)+'\n')
        record.chmod(0o644)
        files = {module.PUBLIC_CA: pin, record_name: module.sha(record.read_bytes())}
        module._public_ca_record(self.host.root, files, self.host.uid)
        with self.assertRaisesRegex(module.InvocationHold, 'public_ca_record'):
            module._public_ca_record(self.host.root, {module.PUBLIC_CA: pin}, self.host.uid)
        record.write_text('certifi/cacert.pem,sha256='+encoded+',999\n')
        files[record_name] = module.sha(record.read_bytes())
        with self.assertRaisesRegex(module.InvocationHold, 'public_ca_record_pin'):
            module._public_ca_record(self.host.root, files, self.host.uid)

    def test_same_invocation_id_cannot_rebind_changed_inner_request(self):
        with patch.object(module, '_supervise', return_value=terminal(self.envelope['request'])):
            self.invoke()
        changed = copy.deepcopy(self.envelope)
        changed['request']['mode'] = 'observe'
        with patch.object(module, '_supervise', side_effect=AssertionError('replay')):
            with self.assertRaises(module.InvocationHold):
                self.invoke(changed)

    def test_missing_transaction_is_explicit_hold_no_controller_init(self):
        self.host.directory.rename(self.host.root/'preserved')
        with patch.object(module.subprocess, 'Popen', side_effect=AssertionError('spawn')):
            with self.assertRaisesRegex(module.InvocationHold, 'prepared_transaction_missing'):
                self.invoke()
        self.assertFalse(self.host.directory.exists())

    def test_intent_exists_before_spawn_and_exact_terminal_is_durable(self):
        def supervise(inner, phase, host):
            path = next(host.directory.glob('native-invocation-*.json'))
            record = module.decode(path.read_bytes())
            self.assertIsNone(record['terminal'])
            self.assertEqual(record['intent']['request'], inner)
            return terminal(inner)
        with patch.object(module, '_supervise', side_effect=supervise):
            result = self.invoke()
        path = next(self.host.directory.glob('native-invocation-*.json'))
        self.assertEqual(module.sha(path.read_bytes()), result['receipt']['sha256'])
        self.assertTrue(result['receipt']['body']['terminal']['child_tree_gone'])
        self.assertEqual(result['response'], response(self.envelope['request']))
        self.assertEqual(module.validate_result(result, self.envelope, '1'*64), result)

    def test_no_replay_and_observe_only_reads_same_terminal_record(self):
        with patch.object(module, '_supervise', return_value=terminal(self.envelope['request'])):
            result = self.invoke()
        before = {p.name: p.read_bytes() for p in self.host.directory.iterdir()}
        with patch.object(module, '_supervise', side_effect=AssertionError('new proof')), \
             patch.object(module, '_write', side_effect=AssertionError('write')), \
             patch.object(module, '_echild', side_effect=AssertionError('new observer ECHILD')):
            self.assertEqual(self.invoke(), result)
            self.assertEqual(self.invoke({**self.envelope, 'mode': 'observe'}), result)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.host.directory.iterdir()})

    def test_crash_missing_terminal_and_new_observer_echild_never_clear_old_intent(self):
        with patch.object(module, '_supervise', side_effect=RuntimeError('simulated crash')):
            with self.assertRaises(RuntimeError):
                self.invoke()
        before = {p.name: p.read_bytes() for p in self.host.directory.iterdir()}
        with patch.object(module, '_echild', side_effect=AssertionError('cannot prove old children')), \
             patch.object(module, '_supervise', side_effect=AssertionError('replay')):
            result = self.invoke({**self.envelope, 'mode': 'observe'})
            self.assertEqual(result['status'], 'unknown')
            self.assertIsNone(result['receipt']['body']['terminal'])
            self.assertEqual(self.invoke()['status'], 'unknown')
            with self.assertRaisesRegex(module.InvocationHold, 'prior_invocation_unresolved'):
                self.invoke({**self.envelope, 'invocation_id': str(uuid4())})
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.host.directory.iterdir()})

    def test_observe_not_found_never_creates_lock_receipt_or_child(self):
        before = list(self.host.directory.iterdir())
        with patch.object(module.os, 'open', wraps=module.os.open) as opens, \
             patch.object(module, '_supervise', side_effect=AssertionError('spawn')):
            result = self.invoke({**self.envelope, 'mode': 'observe'})
        self.assertEqual(result['status'], 'not-found')
        self.assertIsNone(result['receipt'])
        self.assertFalse(opens.called)
        self.assertEqual(before, list(self.host.directory.iterdir()))

    def test_terminal_write_failure_keeps_prior_intent_no_success(self):
        real = module._write
        count = []
        def write(path, value):
            count.append(1)
            if len(count) == 2:
                raise OSError('simulated fsync failure')
            return real(path, value)
        with patch.object(module, '_write', side_effect=write), \
             patch.object(module, '_supervise', return_value=terminal(self.envelope['request'])):
            with self.assertRaises(OSError):
                self.invoke()
        self.assertEqual(self.invoke({**self.envelope, 'mode': 'observe'})['status'], 'unknown')

    def test_source_receipt_response_and_boolean_tampering_rejected(self):
        with patch.object(module, '_supervise', return_value=terminal(self.envelope['request'])):
            result = self.invoke()
        changes = []
        for field in ('invocation_id', 'operation_id', 'request_sha256'):
            changes.append({**result, field: 'wrong'})
        changes.append({**result, 'receipt': {**result['receipt'], 'sha256': '0'*64}})
        for value in changes:
            with self.subTest(field=value.keys()), self.assertRaises(module.InvocationHold):
                module.validate_result(value, self.envelope, '1'*64)
        with self.assertRaises(module.InvocationHold):
            module.validate_result(result, self.envelope, '2'*64)
        value = copy.deepcopy(result)
        value['receipt']['body']['terminal']['waitpid_echild'] = False
        value['receipt']['sha256'] = module.sha(module.wire(value['receipt']['body']))
        with self.assertRaisesRegex(module.InvocationHold, 'terminal_proof'):
            module.validate_result(value, self.envelope, '1'*64)

    def test_private_custody_rejects_symlink_hardlink_and_permissive_receipts(self):
        with patch.object(module, '_supervise', return_value=terminal(self.envelope['request'])):
            self.invoke()
        path = next(self.host.directory.glob('native-invocation-*.json'))
        path.chmod(0o644)
        with self.assertRaises(module.InvocationHold):
            self.invoke({**self.envelope, 'mode': 'observe'})
        path.chmod(0o600)
        os.link(path, self.host.root/'hardlink')
        with self.assertRaises(module.InvocationHold):
            self.invoke({**self.envelope, 'mode': 'observe'})

    def test_real_normal_lifecycle_same_process_kernel_proof_and_recovery(self):
        result = self.finish(self.driver())
        proof = result['receipt']['body']['terminal']
        self.assertEqual(proof['outcome'], 'succeeded')
        self.assertTrue(proof['subreaper_verified'])
        self.assertTrue(proof['direct_child_reaped'])
        self.assertTrue(proof['waitpid_echild'])
        self.assertTrue(proof['child_tree_gone'])
        self.assertEqual((self.host.root/'computation-count').read_text(), 'once\n')
        self.assertEqual(self.finish(self.driver(envelope={**self.envelope, 'mode': 'observe'})), result)
        self.assertEqual((self.host.root/'computation-count').read_text(), 'once\n')

    def test_real_timeout_reaps_setsided_and_doubleforked_descendants(self):
        for scenario in ('escape', 'doublefork'):
            envelope = {**self.envelope, 'invocation_id': str(uuid4())}
            result = self.finish(self.driver(scenario, envelope))
            proof = result['receipt']['body']['terminal']
            self.assertEqual(proof['outcome'], 'timed_out')
            self.assertTrue(proof['child_tree_gone'])
            pid = (self.host.root/'descendant-pid').read_text()
            self.assertFalse(Path('/proc', pid).exists())
            self.assertIsNone(result['response'])

    def test_real_false_cleanup_success_cannot_claim_stopped_descendants(self):
        result = self.finish(self.driver('falsecleanup'))
        terminal = result['receipt']['body']['terminal']
        self.assertTrue(terminal['direct_child_reaped'])
        self.assertFalse(terminal['waitpid_echild'])
        self.assertFalse(terminal['child_tree_gone'])
        self.assertEqual(result['status'], 'unknown')
        self.assertFalse(Path('/proc', (self.host.root/'descendant-pid').read_text()).exists())
        # Later fixture cleanup did not replace the recorded missing proof.
        recovered = self.finish(self.driver(envelope={**self.envelope, 'mode': 'observe'}))
        self.assertEqual(recovered, result)

    def test_real_process_crash_preserves_intent_and_recovery_never_replays(self):
        process = self.driver('crash')
        _, err = process.communicate(timeout=8)
        self.assertEqual(process.returncode, 99, err)
        result = self.finish(self.driver(envelope={**self.envelope, 'mode': 'observe'}))
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['receipt']['body']['terminal'])
        self.assertFalse((self.host.root/'computation-count').exists())
        self.assertEqual(self.finish(self.driver()), result)

    def test_real_cancel_reaps_same_owner_descendant(self):
        process = self.driver('cancel')
        deadline = time.monotonic()+3
        while not (self.host.root/'descendant-pid').exists() and time.monotonic() < deadline:
            time.sleep(.01)
        self.assertTrue((self.host.root/'descendant-pid').exists())
        process.send_signal(signal.SIGTERM)
        result = self.finish(process)
        proof = result['receipt']['body']['terminal']
        self.assertEqual(proof['outcome'], 'cancelled')
        self.assertTrue(proof['child_tree_gone'])
        self.assertFalse(Path('/proc', (self.host.root/'descendant-pid').read_text()).exists())

    def test_real_invalid_nonzero_and_unbounded_output_have_no_inner_success(self):
        for scenario, outcome in [('bad', 'invalid_response'), ('nonzero', 'publisher_error'), ('flood', 'output_limit')]:
            envelope = {**self.envelope, 'invocation_id': str(uuid4())}
            result = self.finish(self.driver(scenario, envelope))
            self.assertEqual(result['receipt']['body']['terminal']['outcome'], outcome)
            self.assertTrue(result['receipt']['body']['terminal']['child_tree_gone'])
            self.assertIsNone(result['response'])

    def test_kernel_live_child_refuses_false_cleanup_success(self):
        child = subprocess.Popen([sys.executable, '-c', 'import time;time.sleep(30)'])
        try:
            self.assertFalse(module._echild())
        finally:
            child.kill(); child.wait()
        self.assertTrue(module._echild())
        proof = terminal(self.envelope['request'])
        proof.update(waitpid_echild=False, child_tree_gone=False)
        with patch.object(module, '_supervise', return_value=proof):
            result = self.invoke()
        self.assertEqual(result['status'], 'unknown')


if __name__ == '__main__':
    unittest.main()
