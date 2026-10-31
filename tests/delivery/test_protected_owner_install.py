"""Synthetic custody only: never install as root or invoke candidate code."""
from contextlib import ExitStack
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import protected_owner_install as producer


class SyntheticFilesystem(producer.Filesystem):
    def __init__(self, root=False):
        self.root = root
        self.fail = None
        self.corrupt = False

    def ids(self):
        return (0, 0) if self.root else (1000, 1000)

    def info(self, path):
        info = path.lstat()
        values = {name: getattr(info, name) for name in dir(info) if name.startswith('st_')}
        values.update(st_uid=0, st_gid=0)
        # Test fixture parents replace real root metadata, including /tmp.
        if stat.S_ISDIR(info.st_mode):
            values['st_mode'] &= ~0o022
        if self.fail == path:
            values['st_mode'] |= 0o002
        return SimpleNamespace(**values)

    def owned(self, path, mode):
        if self.fail == path:
            raise OSError('synthetic write failure')
        # A real root can append to its 0400 receipt. The nonroot test actor
        # needs owner write on this synthetic receipt only.
        os.chmod(path, mode | (0o200 if path == producer.RECEIPT else 0))
        if self.corrupt and path.name == 'current.json':
            os.chmod(path, 0o600)
            path.write_bytes(b'corrupt')
            os.chmod(path, mode)


class ProtectedOwnerInstallTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.source = self.temp / 'original-source'
        self.source.mkdir()
        self.db = self.source / '.git'
        (self.db / 'objects').mkdir(parents=True)
        self.files = {name: b'# accepted source, never executed\n' for name in producer.CODE}
        self.files['tools/delivery/capacity-policy.json'] = b'{"accepted":true}\n'
        self.files['src/offmenu/__init__.py'] = b'# accepted package\n'
        for name, raw in self.files.items():
            path = self.source / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self.tree = self.make_tree(self.files)
        self.parent = self.object('commit', ('tree ' + self.tree +
            '\nauthor Synthetic <synthetic@invalid> 0 +0000\ncommitter Synthetic <synthetic@invalid> 0 +0000\n\nparent\n').encode())
        self.head = self.object('commit', ('tree ' + self.tree + '\nparent ' + self.parent +
            '\nauthor Synthetic <synthetic@invalid> 0 +0000\ncommitter Synthetic <synthetic@invalid> 0 +0000\n\naccepted\n').encode())
        # These are deliberately invalid; preparation must not read/copy them.
        (self.db / 'config').write_text('[filter "bad"]\n clean = forbidden\n')
        (self.db / 'hooks').mkdir()
        (self.db / 'hooks/post-checkout').write_text('NEVER EXECUTE')
        self.runtime = self.temp / '.delivery/stokowski/current'
        self.runtime.mkdir(parents=True)
        self.catalog = self.runtime.parent / 'catalog.json'
        self.catalog.write_bytes(b'{ "version": 1, "entries": [] }\n')
        self.config = dict(version=1, owner='existing-owner', runtime_root=str(self.runtime.parent),
                           catalog=str(self.catalog), source_head=self.head,
                           source_sha256={name: producer.sha(raw) for name, raw in self.files.items()},
                           workflow_sha256='1' * 64, installation_sha256='2' * 64,
                           policy_sha256=producer.sha(self.files['tools/delivery/capacity-policy.json']),
                           completed_native_validations={'UIF-119': {
                               'path': str(self.runtime / 'retained-evidence.json'), 'sha256': '3' * 64}},
                           native_review_template={'unknown_nested_field': ['preserved']})
        (self.runtime / 'current.json').write_bytes(producer.encoded(self.config))
        self.venv = self.temp / 'qualified-venv'
        (self.venv / 'bin').mkdir(parents=True)
        (self.venv / 'lib/python3.12/site-packages').mkdir(parents=True)
        self.home = self.temp / 'qualified-system/bin'
        self.home.mkdir(parents=True)
        self.python = self.home / 'python3.12'
        self.python.write_bytes(b'synthetic-interpreter-not-executable')
        os.chmod(self.python, 0o755)
        (self.venv / 'bin/python').symlink_to(self.python)
        (self.venv / 'bin/python3.12').symlink_to(self.python)
        (self.venv / 'bin/python3').symlink_to('python3.12')
        (self.venv / 'lib64').symlink_to('lib')
        (self.venv / 'pyvenv.cfg').write_text('home = ' + str(self.home) +
            '\ninclude-system-site-packages = false\nversion = 3.12.3\n')
        (self.venv / 'lib/python3.12/site-packages/qualified.py').write_bytes(b'# dependency\n')
        self.fs = SyntheticFilesystem()
        self.stage = self.temp / 'stage'
        self.install_base = self.temp / 'opt/offmenu-stokowski-current'
        self.etc = self.temp / 'etc/offmenu-stokowski-current'
        self.receipt = self.temp / 'var/lib/offmenu-publisher/protected-current-install.json'
        for path in (self.install_base.parent, self.etc.parent, self.receipt.parent):
            path.mkdir(parents=True, exist_ok=True)
        for key, value in dict(SOURCE=self.install_base / 'source', VENV=self.install_base / 'venv',
                               CONFIG=self.etc, RECEIPT=self.receipt).items():
            self.stack.enter_context(patch.object(producer, key, value))

    def object(self, kind, raw):
        obj = kind.encode() + b' ' + str(len(raw)).encode() + b'\0' + raw
        oid = hashlib.sha1(obj).hexdigest()
        target = self.db / 'objects' / oid[:2] / oid[2:]
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(zlib.compress(obj))
        return oid

    def make_tree(self, files):
        tree = {}
        for name, raw in files.items():
            node = tree
            parts = name.split('/')
            for part in parts[:-1]:
                node = node.setdefault(part, {})
            node[parts[-1]] = raw

        def build(node):
            entries = []
            for name, value in sorted(node.items()):
                directory = isinstance(value, dict)
                oid = build(value) if directory else self.object('blob', value)
                entries.append((b'40000' if directory else b'100644') + b' ' + name.encode() +
                               b'\0' + bytes.fromhex(oid))
            return self.object('tree', b''.join(entries))
        return build(tree)

    def args(self):
        env = producer.environment_files(self.venv, self.python, self.fs)
        return dict(stage=self.stage, source=self.source, git_dir=self.db,
                    head=self.head, tree=self.tree, venv=self.venv, python=self.python,
                    runtime=self.runtime, config_sha256=producer.sha((self.runtime / 'current.json').read_bytes()),
                    catalog_sha256=producer.sha(self.catalog.read_bytes()),
                    python_sha256=producer.sha(self.python.read_bytes()),
                    dependency_sha256=producer.sha(producer.encoded({
                        name: {'sha256': producer.sha(raw), 'mode': mode}
                        for name, (raw, mode) in env.items()})), fs=self.fs)

    def prepare(self):
        return producer.prepare(**self.args())

    def install(self, digest):
        self.fs.root = True
        return producer.install(self.stage, digest, fs=self.fs)

    def rewrite_manifest(self, change):
        path = self.stage / 'manifest.json'
        value = producer.record(path.read_bytes())
        change(value)
        os.chmod(path, 0o600)
        path.write_bytes(producer.encoded(value))
        return producer.sha(path.read_bytes())

    def test_deterministic_preparation_and_complete_install(self):
        digest = self.prepare()
        args = self.args()
        args['stage'] = self.temp / 'stage2'
        self.assertEqual(digest, producer.prepare(**args))
        result = self.install(digest)
        self.assertEqual(result['state'], 'complete')
        self.assertEqual(len(result['readback']), len(producer.record((self.stage / 'manifest.json').read_bytes())['payload']))
        self.assertFalse((producer.SOURCE / '.git/hooks').exists())
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(self.temp), 'LC_ALL': 'C',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
        self.assertEqual(subprocess.check_output(['/usr/bin/git', '-C', str(producer.SOURCE),
                         'rev-parse', 'HEAD'], env=env).strip().decode(), self.head)
        self.assertEqual(subprocess.check_output(['/usr/bin/git', '-C', str(producer.SOURCE),
                         'show', self.head + ':tools/delivery/stokowski_adapter.py'], env=env),
                         self.files['tools/delivery/stokowski_adapter.py'])
        self.assertEqual(subprocess.check_output(['/usr/bin/git', '-C', str(producer.SOURCE),
                         'merge-base', self.parent, self.head], env=env).strip().decode(), self.parent)
        self.assertEqual((producer.SOURCE / '.git/config').read_bytes(),
                         b'[core]\n\trepositoryformatversion = 0\n\tbare = false\n')
        for root in (producer.SOURCE, producer.VENV, producer.CONFIG):
            for path in (root, *root.rglob('*')):
                info = path.lstat()
                self.assertFalse(stat.S_ISLNK(info.st_mode))
                self.assertFalse(info.st_mode & 0o6022)
                if path.is_file():
                    self.assertEqual(info.st_nlink, 1)
        self.assertEqual((producer.VENV / 'pyvenv.cfg').read_bytes(), (self.venv / 'pyvenv.cfg').read_bytes())
        self.assertEqual((producer.VENV / 'lib64/python3.12/site-packages/qualified.py').read_bytes(), b'# dependency\n')
        selected = producer.record((self.etc / 'current.json').read_bytes())
        self.assertEqual(selected, dict(self.config, catalog=str(self.etc / 'catalog.json')))
        self.assertEqual((self.etc / 'catalog.json').read_bytes(), self.catalog.read_bytes())
        receipt = self.receipt.read_bytes().splitlines()
        intent = producer.record(receipt[0])
        self.assertEqual(intent['state'], 'intent')
        self.assertEqual(intent['manifest_sha256'], digest)
        self.assertEqual(intent['rollback']['source'], str(self.source))
        self.assertEqual(producer.record(receipt[1])['readback'], result['readback'])
        with self.assertRaisesRegex(producer.Refused, 'prior receipt'):
            self.install(digest)

    def test_actual_accepted_consumer_binding_and_tree(self):
        digest = self.prepare()
        self.install(digest)
        import stokowski_adapter as adapter
        original_lstat, original_fstat = Path.lstat, os.fstat

        def root_metadata(info):
            values = list(info)
            values[4:6] = [0, 0]
            if stat.S_ISDIR(values[0]):
                values[0] &= ~0o022
            return os.stat_result(values)

        with patch.object(adapter, 'SOURCE', producer.SOURCE), patch.object(adapter, 'PROTECTED_OWNER', self.etc), \
             patch.object(adapter.sys, 'executable', str(producer.VENV / 'bin/python')), \
             patch.object(adapter.sys, 'prefix', str(producer.VENV)), \
             patch.object(Path, 'lstat', lambda path, **kw: root_metadata(original_lstat(path, **kw))), \
             patch.object(os, 'fstat', lambda fd: root_metadata(original_fstat(fd))), \
             patch.dict(adapter.os.environ, {'OFFMENU_PROTECTED_OWNER_REQUIRED': '1'}):
            adapter._PROTECTED_CLOSURES.clear()
            config, path, binding = adapter.current_config(self.runtime)
            self.assertEqual(config['completed_native_validations'], self.config['completed_native_validations'])
            self.assertEqual(path, self.etc / 'current.json')
            self.assertEqual(binding['python_sha256'], producer.sha(self.python.read_bytes()))
            self.assertEqual(set(binding), {'schema', 'runtime', 'config_sha256', 'catalog_sha256', 'source_root', 'python_sha256'})
            adapter._PROTECTED_CLOSURES.clear()

    def test_pins_dirty_source_and_identity_refuse(self):
        args = self.args()
        for key in ('head', 'tree', 'config_sha256', 'catalog_sha256', 'python_sha256', 'dependency_sha256'):
            with self.subTest(key=key):
                changed = dict(args, **{key: '0' * len(args[key])})
                with self.assertRaises((producer.Refused, subprocess.CalledProcessError)):
                    producer.prepare(**changed)
                self.assertFalse(self.stage.exists())
        (self.source / next(iter(producer.CODE))).write_bytes(b'dirty')
        with self.assertRaisesRegex(producer.Refused, 'dirty'):
            producer.prepare(**args)
        self.fs.root = True
        with self.assertRaisesRegex(producer.Refused, 'nonroot'):
            producer.prepare(**args)

    def test_unknown_config_and_executable_or_external_dependencies(self):
        self.config['invented_admission'] = True
        (self.runtime / 'current.json').write_bytes(producer.encoded(self.config))
        with self.assertRaisesRegex(producer.Refused, 'config fields'):
            self.prepare()
        package = self.venv / 'lib/python3.12/site-packages'
        for value in ('import hidden_source\n', '/actor/source\n', '../outside\n'):
            with self.subTest(value=value):
                (package / 'bad.pth').write_text(value)
                with self.assertRaisesRegex(producer.Refused, 'pth'):
                    producer.environment_files(self.venv, self.python, self.fs)
        (package / 'bad.pth').unlink()
        (package / 'secret-link').symlink_to(self.python)
        with self.assertRaisesRegex(producer.Refused, 'arbitrary environment link'):
            producer.environment_files(self.venv, self.python, self.fs)

    def test_git_links_alternates_and_source_exclusion(self):
        (self.db / 'objects/info').mkdir()
        (self.db / 'objects/info/alternates').write_text('/must-not-read')
        with self.assertRaisesRegex(producer.Refused, 'external or incomplete'):
            self.prepare()
        for name in ('data/raw.json', '.delivery/receipt.json', '.env.production', 'a/../b', '/absolute', '.', 'a//b'):
            with self.subTest(name=name), self.assertRaises(producer.Refused):
                producer.safe_source(name)

    def test_git_pack_sidecars_and_ancestry_do_not_copy_historical_payloads(self):
        info = self.db / 'objects/info'
        info.mkdir()
        for name in ('commit-graph', 'packs'):
            (info / name).write_bytes(b'ignored administrative metadata')
        pack = self.db / 'objects/pack'
        pack.mkdir()
        for suffix in ('pack', 'idx'):
            (pack / ('pack-' + '0' * 40 + '.' + suffix)).write_bytes(b'')
        for suffix in ('keep', 'rev'):
            (pack / ('pack-' + '0' * 40 + '.' + suffix)).write_bytes(b'administrative sidecar')
        held_blob = self.object('blob', b'held historical payload must not be staged')
        held_tree = self.make_tree({'data/held.json': b'held historical payload must not be staged'})
        parent = self.object('commit', ('tree ' + held_tree +
            '\nauthor Synthetic <synthetic@invalid> 0 +0000\ncommitter Synthetic <synthetic@invalid> 0 +0000\n\nold\n').encode())
        head = self.object('commit', ('tree ' + self.tree + '\nparent ' + parent +
            '\nauthor Synthetic <synthetic@invalid> 0 +0000\ncommitter Synthetic <synthetic@invalid> 0 +0000\n\naccepted\n').encode())
        tree, files, metadata = producer.git_closure(self.db, head)
        self.assertEqual(tree, self.tree)
        self.assertEqual({name: raw for name, (raw, mode) in files.items()}, self.files)
        self.assertIn('.git/objects/' + parent[:2] + '/' + parent[2:], metadata)
        for oid in (held_blob, held_tree):
            self.assertNotIn('.git/objects/' + oid[:2] + '/' + oid[2:], metadata)
        self.assertFalse(any(name.endswith(('.keep', '.rev')) for name in metadata))

    def test_root_controlled_os_home_alias_resolves_without_changing_cfg(self):
        alias = self.home.parent / 'bin-alias'
        alias.symlink_to(self.home)
        cfg = self.venv / 'pyvenv.cfg'
        cfg.write_text('home = ' + str(alias) +
            '\ninclude-system-site-packages = false\nversion = 3.12.3\n')
        original = cfg.read_bytes()
        with patch.object(producer, 'SYSTEM_PYTHON_HOME_ALIASES',
                          {alias: (self.home, str(self.home))}):
            env = producer.environment_files(self.venv, self.python, self.fs)
        self.assertEqual(env['pyvenv.cfg'][0], original)
        self.assertEqual(env['bin/python'][0], self.python.read_bytes())

    def test_pinned_archival_log_body_is_not_read_or_installed(self):
        name = 'archive/accepted-evidence.log'
        body = b'archival fixture remains in original custody'
        oid = self.object('blob', body)
        files = dict(self.files, **{name: body})
        self.tree = self.make_tree(files)
        self.head = self.object('commit', ('tree ' + self.tree +
            '\nauthor Synthetic <synthetic@invalid> 0 +0000\ncommitter Synthetic <synthetic@invalid> 0 +0000\n\naccepted\n').encode())
        self.config['source_head'] = self.head
        (self.runtime / 'current.json').write_bytes(producer.encoded(self.config))
        with patch.dict(producer.EXCLUDED_ARCHIVAL_EVIDENCE, {name: oid}, clear=True):
            digest = self.prepare()
            self.install(digest)
            self.assertFalse((producer.SOURCE / name).exists())
            self.assertFalse((producer.SOURCE / '.git/objects' / oid[:2] / oid[2:]).exists())

    def test_existing_publisher_parent_group_gets_no_write_permission(self):
        original = self.fs.info
        writable = False
        def info(path):
            value = original(path)
            if path == self.receipt.parent:
                value.st_gid = 976
                if writable:
                    value.st_mode |= 0o020
            return value
        with patch.object(self.fs, 'info', side_effect=info):
            producer.root_parents(self.receipt.parent, self.fs)
            writable = True
            with self.assertRaisesRegex(producer.Refused, 'unsafe root parent'):
                producer.root_parents(self.receipt.parent, self.fs)

    def test_frozen_digest_payload_drift_and_hardlinks_refuse_before_writes(self):
        digest = self.prepare()
        with self.assertRaisesRegex(producer.Refused, 'frozen manifest'):
            self.install('0' * 64)
        path = self.stage / 'payload/0'
        original = path.read_bytes()
        os.chmod(path, 0o600)
        path.write_bytes(b'drift')
        with self.assertRaisesRegex(producer.Refused, 'digest drift'):
            self.install(digest)
        path.write_bytes(original)
        os.link(path, self.temp / 'hardlink')
        with self.assertRaisesRegex(producer.Refused, 'single-link'):
            self.install(digest)
        self.assertFalse(self.receipt.exists())
        self.assertFalse(self.install_base.exists())

    def test_manifest_unknown_traversal_and_unsafe_git_metadata(self):
        self.prepare()
        original = (self.stage / 'manifest.json').read_bytes()
        for change in (lambda m: m.update(extra=True),
                       lambda m: m.update(schema='unknown-v2'),
                       lambda m: m['payload'][0].update(name='../escape'),
                       lambda m: m['payload'][0].update(name='/escape'),
                       lambda m: m['payload'][0].update(group='arbitrary-root'),
                       lambda m: m['payload'][0].update(name='.git/hooks/post-checkout')):
            with self.subTest(change=change):
                os.chmod(self.stage / 'manifest.json', 0o600)
                (self.stage / 'manifest.json').write_bytes(original)
                digest = self.rewrite_manifest(change)
                with self.assertRaises(producer.Refused):
                    self.install(digest)
                self.assertFalse(self.receipt.exists())

    def test_existing_targets_prior_receipts_unsafe_parents_and_nonroot(self):
        digest = self.prepare()
        with self.assertRaisesRegex(producer.Refused, 'root real/effective'):
            producer.install(self.stage, digest, fs=self.fs)
        self.install_base.mkdir()
        with self.assertRaisesRegex(producer.Refused, 'existing target'):
            self.install(digest)
        self.install_base.rmdir()
        self.fs.fail = self.install_base.parent
        with self.assertRaisesRegex(producer.Refused, 'unsafe root parent'):
            self.install(digest)
        self.fs.fail = None
        self.receipt.write_bytes(b'unknown previous effect')
        with self.assertRaisesRegex(producer.Refused, 'prior receipt'):
            self.install(digest)

    def test_symlink_payload_and_runtime_drift(self):
        digest = self.prepare()
        path = self.stage / 'payload/0'
        path.unlink()
        path.symlink_to(self.python)
        with self.assertRaises(OSError):
            self.install(digest)
        self.assertFalse(self.receipt.exists())
        digest = self.rewrite_manifest(lambda m: m['runtime_identity'].update(ino=-1))
        with self.assertRaisesRegex(producer.Refused, 'runtime identity drift'):
            self.install(digest)

    def test_partial_write_retains_intent_and_rollback_without_replay(self):
        digest = self.prepare()
        self.fs.fail = self.etc / 'current.json'
        with self.assertRaises(OSError):
            self.install(digest)
        intent, outcome = map(producer.record, self.receipt.read_bytes().splitlines())
        self.assertEqual(intent['state'], 'intent')
        self.assertEqual(outcome['state'], 'partial-or-unknown')
        self.assertEqual(intent['rollback']['config_sha256'], producer.sha((self.runtime / 'current.json').read_bytes()))
        self.assertTrue(self.install_base.exists())
        self.assertEqual((self.runtime / 'current.json').read_bytes(), producer.encoded(self.config))
        self.fs.fail = None
        with self.assertRaisesRegex(producer.Refused, 'prior receipt'):
            self.install(digest)

    def test_readback_drift_retains_unknown_and_intent_only_blocks_replay(self):
        digest = self.prepare()
        self.fs.corrupt = True
        with self.assertRaisesRegex(producer.Refused, 'readback drift'):
            self.install(digest)
        self.assertEqual(producer.record(self.receipt.read_bytes().splitlines()[1])['state'], 'partial-or-unknown')
        with self.assertRaisesRegex(producer.Refused, 'prior receipt'):
            self.install(digest)

    def test_lost_outcome_keeps_durable_intent_only_no_replay(self):
        digest = self.prepare()
        self.fs.fail = self.etc / 'current.json'
        with patch.object(producer, '_append_outcome', side_effect=OSError('synthetic lost outcome')):
            with self.assertRaises(OSError):
                self.install(digest)
        self.assertEqual(len(self.receipt.read_bytes().splitlines()), 1)
        self.assertEqual(producer.record(self.receipt.read_bytes())['state'], 'intent')
        with self.assertRaisesRegex(producer.Refused, 'prior receipt'):
            self.install(digest)


if __name__ == '__main__':
    unittest.main()
