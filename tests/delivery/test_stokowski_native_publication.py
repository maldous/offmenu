"""Synthetic process observations only; no authentication/provider/network calls.

Reuse only the existing temporary qualification fixture builder, never its test
suite. The actual prepare_publication consumes this caller's callback and writes
its normal lock/journal/catalog in that temporary fixture.
"""
import copy
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import stokowski_native_publication as native
import stokowski_prepare as prepare
import test_stokowski_prepare_publication as fixture
from symphony_capacity import digest


class NativePublicationTests(unittest.TestCase):
    def setUp(self):
        self.fixture = f = fixture.PublicationTests(methodName='runTest')
        self.addCleanup(f.doCleanups)
        f.setUp()
        self.root = f.source
        f.base, f.branch = native.BASE, 'feature/native-ssh-owner-publication'
        f.manifest.update(base_revision=f.base, branch=f.branch)
        f.write(f.qualified / 'manifest.json', f.manifest)
        f.config['repository'] = native.ROUTE['repository']
        f.config['caller_association'] = dict(native.CALLER,
            native_route=dict(native.ROUTE),
            authenticated_observation=f.ref(f.qualified / 'observation.json'))
        f.handoff.update(authenticated_principal=dict(id=native.CALLER['principal_id'], login='maldous'),
                         native_route=dict(native.ROUTE), source_base=f.base)
        claim = f.config['repository_claim']
        binding = dict(owner=f.owner, repository=native.ROUTE['repository'], issue_id=f.issue['uuid'])
        f.write(Path(claim['binding_path']), binding)
        claim.update(binding_sha256=f.sha(Path(claim['binding_path'])), binding_identity_sha256=digest(binding))
        f.write(Path(claim['path']), dict(owner=f.owner, directory=str(Path(claim['binding_path']).parent),
                                        binding_sha256=digest(binding)))
        claim['sha256'] = f.sha(Path(claim['path']))
        f.packet['source'].update(repository=native.ROUTE['repository'], base=f.base, branch=f.branch)
        self.blobs = {}
        for module in native.MODULES:
            name = 'tools/delivery/' + module + '.py'
            path = self.root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(('# synthetic accepted fixture ' + module + '\n').encode())
            self.blobs[name] = path.read_bytes()
        self.repin()
        self.installed_head = f.base
        self.installed_branch = f.branch
        self.process_calls = []
        self.run = Mock(side_effect=self.synthetic_process)
        self.api = Mock(wraps=prepare.prepare_publication)
        self.now = Mock(side_effect=lambda: time.time())
        self.adapters = native.Adapters(self.run, self.api, f.provider, self.now)
        self.request = dict(version=1, mode='prepare', nonce='a' * 64,
                            operation=f.handoff_sha, context=self.context())

    def repin(self):
        self.fixture.repin()

    def context(self):
        f = self.fixture
        return dict(source_base=native.BASE, source_head=f.base, source_branch=f.branch,
            source_sha256={name: native.sha(blob) for name, blob in self.blobs.items()},
            python_sha256=native.sha(Path(sys.executable).resolve().read_bytes()),
            handoff=f.ref(f.handoff_path), owner_config=f.packet['owner_config'],
            task_packet=f.handoff['task_packet'], claim={k: f.config['repository_claim'][k]
                for k in ('path', 'sha256')}, owner=f.owner)

    def refresh(self):
        self.repin()
        self.request.update(operation=self.fixture.handoff_sha, context=self.context())

    def synthetic_process(self, argv, *, env, timeout):
        self.assertLessEqual(timeout, 10)
        self.assertEqual(env['HOME'], '/home/user')
        self.assertEqual(set(env) - {'GIT_SSH_COMMAND'}, set(native.ENV))
        self.process_calls.append(tuple(argv))
        if argv[:3] == ('/usr/bin/git', '-C', str(self.root)):
            args = argv[3:]
            if args == ('rev-parse', 'HEAD'):
                return 0, (self.installed_head + '\n').encode(), b''
            if args == ('merge-base', native.BASE, self.installed_head):
                return 0, (native.BASE + '\n').encode(), b''
            if args == ('branch', '--show-current'):
                return 0, (self.installed_branch + '\n').encode(), b''
            self.assertEqual(args[0], 'show')
            head, name = args[1].split(':', 1)
            self.assertEqual(head, self.installed_head)
            return 0, self.blobs[name], b''
        if argv[0] == '/usr/bin/ssh':
            self.assertEqual(argv, (*native.SSH, '-T', 'git@github.com'))
            self.assertNotIn('GIT_SSH_COMMAND', env)
            return 1, b'', b"Hi maldous! You've successfully authenticated, but GitHub does not provide shell access.\n"
        self.assertEqual(argv, ('/usr/bin/git', 'ls-remote', '--exit-code',
            'git@github.com:maldous/offmenu.git', 'refs/heads/develop'))
        self.assertEqual(env['GIT_SSH_COMMAND'], native.shlex.join(native.SSH))
        return 0, (native.BASE + '\trefs/heads/develop\n').encode(), b''

    def invoke(self, request=None):
        return native.invoke(request or self.request, root=self.root, adapters=self.adapters)

    def assert_no_auth_or_effect(self):
        self.assertTrue(all(call[:2] == ('/usr/bin/git', '-C') for call in self.process_calls))
        self.api.assert_not_called()
        self.fixture.provider.assert_not_called()
        self.assertEqual(self.fixture.catalog.read_bytes(), self.fixture.catalog_before)

    def test_fixed_identity_argv_is_shared_by_both_auth_invocations(self):
        expected_ssh = ('/usr/bin/ssh', '-F', '/dev/null', '-o', 'BatchMode=yes',
            '-o', 'StrictHostKeyChecking=yes', '-o', 'IdentityAgent=none',
            '-i', '/home/user/.ssh/id_ed25519_maldous', '-o', 'IdentitiesOnly=yes',
            '-o', 'ForwardAgent=no', '-o', 'ForwardX11=no',
            '-o', 'ClearAllForwardings=yes', '-o', 'ProxyCommand=none',
            '-o', 'ProxyJump=none', '-o', 'PermitLocalCommand=no',
            '-o', 'ConnectionAttempts=1', '-o', 'ConnectTimeout=5')
        native.authenticate(self.run, self.now, 'synthetic-binding')
        self.assertEqual(self.run.call_count, 2)
        identity, repository = self.run.call_args_list
        self.assertEqual(identity.args, ((*expected_ssh, '-T', 'git@github.com'),))
        self.assertEqual(identity.kwargs, dict(env=dict(native.ENV), timeout=10))
        self.assertEqual(repository.args, (('/usr/bin/git', 'ls-remote', '--exit-code',
            'git@github.com:maldous/offmenu.git', 'refs/heads/develop'),))
        self.assertEqual(repository.kwargs, dict(env=dict(native.ENV,
            GIT_SSH_COMMAND=native.shlex.join(expected_ssh)), timeout=10))
        for argv in (identity.args[0][:-2],
                     tuple(native.shlex.split(repository.kwargs['env']['GIT_SSH_COMMAND']))):
            self.assertEqual(argv, expected_ssh)
            self.assertEqual(argv.count('-i'), 1)
            self.assertEqual(argv.count('/home/user/.ssh/id_ed25519_maldous'), 1)
            self.assertEqual(argv.count('IdentitiesOnly=yes'), 1)

    def test_actual_prepare_callback_publishes_and_duplicate_does_not_retry(self):
        result = self.invoke()
        self.assertEqual(result['result']['status'], 'published')
        self.assertEqual(result['dispatches'], 0)
        self.assertEqual(self.api.call_count, 1)
        self.fixture.provider.assert_called_once()
        self.assertEqual(self.fixture.snapshot(self.fixture.coordinator), self.fixture.original_coordinator)
        auth_count = sum(call[0] == '/usr/bin/ssh' for call in self.process_calls)
        self.assertEqual(self.invoke(), result)
        self.assertEqual(self.api.call_count, 1)
        self.assertEqual(sum(call[0] == '/usr/bin/ssh' for call in self.process_calls), auth_count)
        status = dict(self.request, mode='status')
        observation = self.invoke(status)
        self.assertEqual(observation['result'], result['result'])
        self.assertIn('journal_sha256', observation)
        self.assertEqual(observation['reconciliation'], 'existing-owner-required')
        self.assertEqual(self.api.call_count, 1)

    def test_mcp_configuration_refuses_before_authentication(self):
        self.fixture.config['caller_association'] = dict(service='github', principal_id='6347545', login='maldous',
            authenticated_observation=self.fixture.ref(self.fixture.qualified / 'observation.json'))
        self.refresh()
        with self.assertRaisesRegex(ValueError, 'fields'):
            self.invoke()
        self.assert_no_auth_or_effect()

    def test_unqualified_handoff_and_wrong_namespace_refuse(self):
        for delta in ({'native_route': {}}, {'authenticated_principal': dict(id='6347545', login='maldous')}):
            with self.subTest(delta=delta):
                old = copy.deepcopy(self.fixture.handoff)
                self.fixture.handoff.update(delta)
                self.refresh()
                with self.assertRaisesRegex(ValueError, 'route'):
                    self.invoke()
                self.fixture.handoff = old
        self.assert_no_auth_or_effect()

    def test_source_and_input_tamper_refuse_before_auth(self):
        path = self.root / next(iter(self.blobs))
        old = path.read_bytes()
        path.write_bytes(b'tamper')
        with self.assertRaisesRegex(ValueError, 'source_blob'):
            self.invoke()
        path.write_bytes(old)
        config = self.fixture.qualified / 'config.json'
        old_config = config.read_bytes()
        config.write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'pin'):
            self.invoke()
        config.write_bytes(old_config)
        (self.fixture.qualified / 'request.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError, 'pin'):
            self.invoke()
        self.assert_no_auth_or_effect()

    def test_context_conflicts_extra_fields_and_private_home_refuse(self):
        for change in ({'source_branch': 'develop'}, {'source_base': '0' * 40},
                       {'command': 'ssh'}, {'claim': dict(path='/home/user/.ssh/config', sha256='0' * 64)}):
            with self.subTest(change=change):
                request = copy.deepcopy(self.request)
                request['context'].update(change)
                with self.assertRaises(ValueError):
                    self.invoke(request)
        self.assert_no_auth_or_effect()

    def test_bad_process_observations_cannot_authenticate(self):
        original = self.synthetic_process
        banner = b"Hi maldous! You've successfully authenticated, but GitHub does not provide shell access.\n"
        for response in ((0, b'', b''), (1, b'principal', b''),
                         (1, b'', b'Hi someone!\n'), (1, b'', b'getProfile 6347545'),
                         (0, b'', banner), (1, b'unexpected', banner),
                         (1, b'', banner + b'\n')):
            with self.subTest(response=response):
                self.run.side_effect = lambda argv, **kw: response if argv[0] == '/usr/bin/ssh' else original(argv, **kw)
                with self.assertRaisesRegex(ValueError, 'ssh_identity'):
                    self.invoke()
        self.api.assert_not_called()
        self.fixture.provider.assert_not_called()

    def test_repository_read_is_separate_and_fixed(self):
        original = self.synthetic_process
        self.run.side_effect = lambda argv, **kw: (0, b'c' * 40 + b'\trefs/heads/other\n', b'') if argv[1] == 'ls-remote' else original(argv, **kw)
        with self.assertRaisesRegex(ValueError, 'repository_read'):
            self.invoke()
        self.api.assert_not_called()

    def test_advanced_repository_head_is_observed_without_source_authority(self):
        original = self.synthetic_process
        advanced = 'c' * 40
        self.run.side_effect = lambda argv, **kw: (0, (advanced + '\trefs/heads/develop\n').encode(), b'') if argv[1] == 'ls-remote' else original(argv, **kw)
        self.assertEqual(self.invoke()['result']['status'], 'published')
        custody = self.root / '.delivery/native-ssh-publication' / (self.request['operation'] + '.json')
        observation = json.loads(custody.read_bytes())['observation']
        self.assertEqual(observation['repository_read_head'], advanced)
        self.assertEqual(self.request['context']['source_head'], native.BASE)
        self.assertEqual(observation['write_permission'], 'unproven')

    def test_malformed_or_multiline_repository_reads_refuse(self):
        original = self.synthetic_process
        valid = b'c' * 40 + b'\trefs/heads/develop\n'
        for output in (b'', b'c' * 39 + b'\trefs/heads/develop\n',
                       b'g' * 40 + b'\trefs/heads/develop\n',
                       b'C' * 40 + b'\trefs/heads/develop\n',
                       valid + valid, valid + b'\n', b' ' + valid,
                       valid.replace(b'\t', b' '), valid.replace(b'\n', b'\r\n')):
            with self.subTest(output=output):
                self.run.side_effect = lambda argv, **kw: (0, output, b'') if argv[1] == 'ls-remote' else original(argv, **kw)
                with self.assertRaisesRegex(ValueError, 'repository_read'):
                    self.invoke()
        self.api.assert_not_called()
        self.fixture.provider.assert_not_called()

    def test_reviewed_installed_branch_and_head_can_advance(self):
        for branch in ('develop', 'feature/native-ssh-owner-publication-r2', 'bugfix/native-read'):
            with self.subTest(branch=branch):
                self.installed_branch, self.installed_head = branch, 'd' * 40
                context = dict(self.request['context'], source_branch=branch, source_head=self.installed_head)
                native.validate(context, self.root, self.run)
        self.assert_no_auth_or_effect()

    def test_source_head_branch_and_blob_mismatch_still_refuse(self):
        for change in ({'source_head': 'd' * 40}, {'source_branch': 'develop'},
                       {'source_branch': 'main'}, {'source_branch': 'feature/'},
                       {'source_branch': 'feature/a..b'}, {'source_branch': 'feature/a.lock'},
                       {'source_branch': 'feature/a//b'}, {'source_branch': 'feature/a\n'},
                       {'source_branch': 'feature/-option'}, {'source_branch': 'feature/a@{b'}):
            with self.subTest(change=change):
                context = dict(self.request['context'], **change)
                # Invalid syntax must refuse even when the installed name agrees.
                if change.get('source_branch') not in (None, 'develop'):
                    self.installed_branch = change['source_branch']
                with self.assertRaises(ValueError):
                    native.validate(context, self.root, self.run)
                self.installed_branch = self.fixture.branch
        self.assert_no_auth_or_effect()

    def test_protected_runtime_mapping_uses_sealed_owner_only(self):
        import stokowski_adapter as adapter
        root = Path('/opt/offmenu-stokowski-current/source')
        runtime_root = self.fixture.root
        # The fixture root is the private .delivery/stokowski namespace.
        selected = self.fixture.config['selected_current']
        coordinator = selected['coordinator_runtime']
        binding = dict(source_root=str(root), runtime=coordinator)
        sealed = dict(owner=self.fixture.owner,runtime_root=str(runtime_root))
        with patch.object(adapter,'protected_owner_bytes',return_value=native.encode(binding)), \
             patch.object(adapter,'current_config',return_value=(sealed,Path('/sealed'),binding)) as select:
            self.assertEqual(native.private_namespace(root,self.context()),(runtime_root.parent,runtime_root))
            select.assert_called_once_with(Path(coordinator))
            self.assertEqual(native.custody_directory(root,self.context()),runtime_root.parent/'native-ssh-publication')
            for changed in (dict(binding,source_root='/untrusted'),):
                with patch.object(adapter,'protected_owner_bytes',return_value=native.encode(changed)), \
                     self.assertRaisesRegex(ValueError,'protected_source'):
                    native.private_namespace(root,self.context())
            with patch.object(adapter,'current_config',return_value=(dict(sealed,owner='other'),Path('/sealed'),binding)), \
                 self.assertRaisesRegex(ValueError,'protected_owner'):
                native.private_namespace(root,self.context())
            self.fixture.packet['selected_current']['runtime_root']=str(runtime_root/'foreign')
            self.fixture.repin()
            with self.assertRaisesRegex(ValueError,'protected_runtime'):
                native.private_namespace(root,self.context())
        self.assert_no_auth_or_effect()

    def test_legacy_namespace_ignores_packet_runtime_assertions(self):
        self.assertEqual(native.private_namespace(self.root,dict(owner='untrusted')),
                         (self.root/'.delivery',self.root/'.delivery/stokowski'))
        self.assert_no_auth_or_effect()

    def test_protected_outside_reference_is_refused_without_open(self):
        context=dict(self.context(),owner_config=dict(path=str(self.root/'outside.json'),sha256='1'*64))
        runtime_root=self.fixture.root
        with patch.object(native,'pinned') as opened:
            self.assertFalse(native.packet_runtime_is_sealed(context,runtime_root,str(self.fixture.coordinator)))
            opened.assert_not_called()
        context['owner_config']=dict(path=str(runtime_root/'inside.json'),sha256='invalid')
        with patch.object(native,'pinned') as opened,self.assertRaises(ValueError):
            native.packet_runtime_is_sealed(context,runtime_root,str(self.fixture.coordinator))
        opened.assert_not_called()

    def test_source_process_cap_covers_actual_installed_module_lengths(self):
        lengths = [(Path(native.__file__).parent / (name + '.py')).stat().st_size
                   for name in native.MODULES]
        length = max(lengths)
        self.assertGreater(length, native.LIMIT)
        self.assertLessEqual(length, native.PROCESS_LIMIT)
        blob = b'x' * length  # Synthetic installed and Git source bytes only.
        name = 'tools/delivery/stokowski_adapter.py'
        self.blobs[name] = blob
        (self.root / name).write_bytes(blob)
        context = self.context()
        native.validate(context, self.root, self.run)
        self.assert_no_auth_or_effect()

    def test_stale_observation_and_callback_refuse(self):
        self.now.side_effect = [1, 27]
        with self.assertRaisesRegex(ValueError, 'observation_age'):
            self.invoke()
        self.api.assert_not_called()
        self.now.side_effect = [1, 2, 40]
        self.assertEqual(self.invoke()['result']['status'], 'uncertain')
        self.fixture.provider.assert_not_called()
        self.assertFalse(self.fixture.runtime.exists())

    def test_changed_nonce_cannot_replay_same_operation(self):
        self.invoke()
        request = dict(self.request, nonce='b' * 64)
        with self.assertRaisesRegex(ValueError, 'immutable_conflict'):
            self.invoke(request)
        self.assertEqual(self.api.call_count, 1)

    def test_partial_publication_is_held_and_status_uses_exact_journal(self):
        original = prepare._publication_write
        def fail_catalog(path, content):
            if path == self.fixture.catalog:
                raise OSError('synthetic interruption')
            original(path, content)
        with patch.object(prepare, '_publication_write', side_effect=fail_catalog):
            result = self.invoke()
        self.assertEqual(result['result']['status'], 'uncertain')
        self.assertTrue(self.fixture.runtime.exists())
        self.assertEqual(self.fixture.catalog.read_bytes(), self.fixture.catalog_before)
        self.assertEqual(self.invoke(), result)
        status = self.invoke(dict(self.request, mode='status'))
        self.assertIn('journal_sha256', status)
        self.assertEqual(self.api.call_count, 1)
        journal = self.fixture.root / 'task-publication.json'
        value = json.loads(journal.read_bytes())
        value['identity']['handoff_sha256'] = '0' * 64
        self.fixture.write(journal, value)
        with self.assertRaisesRegex(ValueError, 'journal_identity'):
            self.invoke(dict(self.request, mode='status'))
        self.assertEqual(self.api.call_count, 1)

    def test_lost_result_keeps_intent_and_never_retries(self):
        original = native.durable
        def lose_result(path, value):
            if 'result' in value:
                raise OSError('synthetic custody failure')
            original(path, value)
        with patch.object(native, 'durable', side_effect=lose_result):
            with self.assertRaises(OSError):
                self.invoke()
        self.assertEqual(self.invoke()['result']['status'], 'uncertain')
        self.assertEqual(self.api.call_count, 1)
        self.fixture.provider.assert_called_once()

    def test_original_admission_refuses_without_bypass(self):
        self.fixture.config['publication_authority']['automatic_start'] = True
        self.refresh()
        result = self.invoke()
        self.assertEqual(result['result']['status'], 'uncertain')
        self.assertEqual(self.api.call_count, 1)
        self.fixture.provider.assert_not_called()
        self.assertEqual(self.fixture.catalog.read_bytes(), self.fixture.catalog_before)

    def test_missing_module_and_git_blob_mismatch_refuse_before_auth(self):
        name = next(iter(self.blobs))
        request = copy.deepcopy(self.request)
        request['context']['source_sha256'].pop(name)
        with self.assertRaisesRegex(ValueError, 'modules'):
            self.invoke(request)
        self.blobs[name] = b'# different synthetic Git blob\n'
        with self.assertRaisesRegex(ValueError, 'source_blob'):
            self.invoke()
        self.assert_no_auth_or_effect()

    def test_uncovered_reference_and_wrong_provider_remain_refused(self):
        f = self.fixture
        f.packet['inputs'].pop(f.packet['request']['path'])
        f.write(f.qualified / 'packet.json', f.packet)
        f.handoff['task_packet'] = f.ref(f.qualified / 'packet.json')
        f.write(f.handoff_path, f.handoff)
        f.handoff_sha = f.sha(f.handoff_path)
        self.request.update(operation=f.handoff_sha, context=self.context())
        with self.assertRaisesRegex(ValueError, 'input_coverage'):
            self.invoke()
        self.assert_no_auth_or_effect()
        self.refresh()
        f.provider.side_effect = lambda model, ceiling: dict(route='wrong', available=True)
        self.assertEqual(self.invoke()['result']['status'], 'uncertain')
        self.assertFalse(f.runtime.exists())
        self.assertEqual(f.catalog.read_bytes(), f.catalog_before)

    def test_status_without_intent_and_caller_lock_conflict_do_not_authenticate(self):
        with self.assertRaisesRegex(ValueError, 'missing_intent'):
            self.invoke(dict(self.request, mode='status'))
        custody = self.root / '.delivery/native-ssh-publication'
        with (custody / 'caller.lock').open('rb') as stream:
            native.fcntl.flock(stream, native.fcntl.LOCK_EX | native.fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.invoke()
        self.assert_no_auth_or_effect()

    def test_environment_gate_refuses_normal_api_before_any_process(self):
        # No inherited values are read: a synthetic environment replaces it.
        with patch.object(native.os, 'environ', {'SYNTHETIC_TOKEN': 'synthetic'}):
            with self.assertRaisesRegex(ValueError, 'environment'):
                native.invoke(self.request, root=self.root)
        self.assert_no_auth_or_effect()

    def test_decode_rejects_duplicate_keys_nonfinite_and_oversize(self):
        for data in (b'{"version":1,"version":1}', b'{"x":NaN}', b' ' * (native.LIMIT + 1)):
            with self.subTest(data=data[:50]), self.assertRaises(ValueError):
                native.decode(data)
        self.assert_no_auth_or_effect()


class SyntheticSourceProcessTests(unittest.TestCase):
    def test_bounded_source_capture_above_generic_json_limit(self):
        length = max((Path(native.__file__).parent / (name + '.py')).stat().st_size
                     for name in native.MODULES)
        # Only this synthetic child runs: no Git/SSH/auth/provider invocation.
        code, blob, err = native.process((sys.executable, '-c',
            'import sys; sys.stdout.buffer.write(b"x" * ' + str(length) + ')'),
            env=dict(native.ENV), timeout=5)
        self.assertEqual((code, blob, err), (0, b'x' * length, b''))


if __name__ == '__main__':
    unittest.main()
