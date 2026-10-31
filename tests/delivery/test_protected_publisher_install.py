"""Offline synthetic install only; never touch the actual fixed host paths."""
from contextlib import contextmanager
import copy
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('publisher_install',
    Path(__file__).resolve().parents[2] / 'tools/delivery/protected_publisher_install.py')
p = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(p)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))


class SyntheticHost(p._Host):
    """Real temporary bytes/descriptors, fake ownership and caller identity."""
    def __init__(self, root):
        self.root = root
        self.ids = (1001, 1001)
        self.owners = {}
        self.observed = []
        self.changed_metadata = None

    def identity(self):
        return self.ids

    def metadata(self, fd):
        s = os.fstat(fd)
        values = list(s)
        values[4], values[5] = self.owners.get(s.st_ino, (0, 0))
        fake = os.stat_result(values)
        return self.changed_metadata(fake) if self.changed_metadata else fake

    def owner(self, fd, uid, gid):
        self.owners[os.fstat(fd).st_ino] = (uid, gid)

    @contextmanager
    def directory(self, path):
        # Match production traversal, rooted only in a private temporary tree.
        p._check(path.startswith('/') and str(PurePosixPath(path)) == path
                 and '..' not in path.split('/'))
        self.observed.append(path)
        fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            self.controlled(fd)
            for part in PurePosixPath(path).parts[1:]:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new
                self.controlled(fd)
            yield fd
        finally:
            os.close(fd)


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.host = SyntheticHost(self.root)
        for directory in (p.SOURCE, p.VENV, '/opt', p.CONFIG_DIR, p.STATE, '/usr/bin'):
            self.local(directory).mkdir(parents=True, exist_ok=True)
        for directory in self.root.rglob('*'):
            if directory.is_dir():
                directory.chmod(0o755)
        self.local(p.CONFIG_DIR).chmod(0o750)
        self.host.owners[self.local(p.CONFIG_DIR).stat().st_ino] = (0, 976)
        self.source_pins = {}
        for path in p.SOURCE_FILES:
            self.put(p.SOURCE + '/' + path, b'synthetic source\n')
            self.source_pins[path] = p._hash(b'synthetic source\n')
        self.dependency_pins = {}
        for path, raw, mode in (
            ('bin/python', b'SYNTHETIC INTERPRETER NEVER EXECUTED', 0o555),
            ('pyvenv.cfg', b'home = /usr/bin\ninclude-system-site-packages = false\n', 0o444),
            ('lib/python3.12/site-packages/dummy/__init__.py', b'', 0o444),
            ('lib/python3.12/site-packages/dummy/native.so', b'SYNTHETIC NATIVE NEVER LOADED', 0o555),
        ):
            self.put(p.VENV + '/' + path, raw, mode)
            self.dependency_pins[path] = p._hash(raw)
        self.local(p.VENV + '/empty').mkdir()
        self.local(p.VENV + '/empty').chmod(0o755)
        b = dict(version=2, repository='maldous/offmenu', pr_number=None,
            issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32', owner='synthetic-owner',
            head_branch='feature/synthetic', head='a'*40, base='b'*40, tree='c'*40,
            policy_sha256='d'*64, capacity_policy_sha256='e'*64,
            validation_operation_key='f'*64, outputs={'a.txt': '1'*64})
        route = '/repos/maldous/offmenu'
        operations = [
            dict(kind='commit', method='POST', path=route+'/git/commits',
                 readPath=route+'/git/commits/'+b['head'], expected=b['head'],
                 body=dict(tree=b['tree'], parents=[b['base']], message='synthetic\n',
                           author={}, committer={})),
            dict(kind='ref', method='POST', path=route+'/git/refs',
                 readPath=route+'/git/ref/heads/'+b['head_branch'], expected=None,
                 body=dict(ref='refs/heads/'+b['head_branch'], sha=b['head'])),
            dict(kind='create-pr', method='POST', path=route+'/pulls', expected=b['head'],
                 readPath=route+'/pulls?state=all&head=maldous:'+b['head_branch']+'&base=develop',
                 body=dict(title='Synthetic', body='Synthetic', base='develop', head=b['head_branch'])),
        ]
        snapshot = dict(publisher_owner=b['owner'], source_tree=b['tree'],
            policy_sha256=b['policy_sha256'], capacity_policy_sha256=b['capacity_policy_sha256'],
            validation=dict(head=b['head'], base=b['base'], outputs=b['outputs'],
                            operation_key=b['validation_operation_key'], status='succeeded',
                            capacity_policy_sha256=b['capacity_policy_sha256'],
                            child_tree_gone=True, reconcile_required=False),
            review=dict(head=b['head'], base=b['base'], independent=True,
                        evidence_id='synthetic-review', verdict='accept', findings=[]),
            unresolved_findings=[], source_clean=True, publication_triggers_actions=False)
        plan = dict(operations=operations, changedFiles=b['outputs'])
        b['publication'] = dict(plan_sha256=p._hash(p._wire(plan)), qualification_sha256=p._hash(p._wire(snapshot)))
        self.config = dict(version=1, appId=5554359, installationId=177187048,
            repositoryId=1416253963, publisherUid=984, publisherGid=976,
            logicalOwner=b['owner'], sourceHead=p.SOURCE_HEAD, codePins={name: self.source_pins[name] for name in p.REQUIRED},
            pythonSha256=self.dependency_pins['bin/python'], binding=b,
            snapshot=snapshot, plan=plan, workspace='/synthetic/candidate')

    def local(self, path):
        return self.root / path.lstrip('/')

    def put(self, path, raw, mode=0o444):
        target = self.local(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        for directory in (target.parent, *target.parent.parents):
            if directory == self.root:
                break
            if directory != self.local(p.CONFIG_DIR):
                directory.chmod(0o755)
        if target.exists():
            target.chmod(0o644)
        target.write_bytes(raw)
        target.chmod(mode)

    def args(self):
        raw = p._wire(self.config)
        return dict(config_bytes=raw, config_sha256=p._hash(raw), source_pins=self.source_pins,
                    dependency_pins=self.dependency_pins, _host=self.host)

    def prepared(self):
        self.host.ids = (1001, 1001)
        return p.prepare(**self.args())

    def install(self, manifest=None, **changes):
        manifest = self.prepared() if manifest is None else manifest
        self.host.ids = (0, 0)
        args = dict(prepared_sha256=p._hash(manifest), **self.args())
        args.update(changes)
        return p.install(manifest, **args)

    def no_intent(self):
        self.assertFalse(self.local(p.STATE + '/' + p.RECEIPT).exists())
        self.assertFalse(self.local(p.TARGET).exists())

    def test_install_exact_captured_bytes_modes_empty_claim_and_no_replay(self):
        before = {path: self.local(p.VENV+'/'+path).read_bytes() for path in self.dependency_pins}
        manifest = self.prepared()
        self.no_intent()
        result = self.install(manifest)
        self.assertEqual(result['effect'], 'files-installed')
        target = self.local(p.TARGET)
        actual = {str(x.relative_to(target)) for x in target.rglob('*') if x.is_file()}
        self.assertEqual(actual, set(p.SOURCE_FILES) | {'venv/'+x for x in self.dependency_pins})
        for path in target.rglob('*'):
            mode = stat.S_IMODE(path.stat().st_mode)
            if path.is_dir():
                self.assertEqual(mode, 0o755)
            else:
                self.assertIn(mode, (0o444, 0o555))
                self.assertEqual(path.stat().st_nlink, 1)
        for path, raw in before.items():
            self.assertEqual((target/'venv'/path).read_bytes(), raw)
        self.assertTrue((target/'venv/empty').is_dir())
        config = self.local(p.CONFIG_DIR+'/config.json')
        self.assertEqual(config.read_bytes(), self.args()['config_bytes'])
        self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o440)
        self.assertEqual(self.host.owners[config.stat().st_ino], (0, 976))
        claim = self.local(p.STATE+'/integration')
        self.assertEqual({x.name for x in claim.iterdir()}, {'current'})
        self.assertEqual(list((claim/'current').iterdir()), [])
        for path in (claim, claim/'current'):
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
            self.assertEqual(self.host.owners[path.stat().st_ino], (984, 976))
        receipt = self.local(p.STATE+'/'+p.RECEIPT).read_bytes()
        self.assertEqual(json.loads(receipt)['effect'], 'intent')
        with self.assertRaises(p.InstallError):
            self.install(manifest)
        self.assertEqual(self.local(p.STATE+'/'+p.RECEIPT).read_bytes(), receipt)
        self.assertFalse(any('key' in path for path in self.host.observed))

    def test_independent_hashes_required_and_revalidated_before_intent(self):
        manifest = self.prepared()
        for changes in ({'prepared_sha256': None}, {'prepared_sha256': '0'*64},
                        {'config_sha256': None}, {'config_sha256': '0'*64},
                        {'prepared_sha256': p._hash(manifest+b' ')}):
            with self.subTest(changes=changes), self.assertRaises(p.InstallError):
                self.install(manifest, **changes)
            self.no_intent()
        self.put(p.VENV+'/bin/python', b'changed', 0o755)
        with self.assertRaises(p.InstallError):
            self.install(manifest)
        self.no_intent()

    def test_changed_closure_mode_or_config_even_with_new_hash_refused(self):
        manifest = self.prepared()
        self.local(p.VENV+'/lib/python3.12/site-packages/dummy/native.so').chmod(0o444)
        with self.assertRaises(p.InstallError):
            self.install(manifest)
        self.no_intent()
        self.local(p.VENV+'/lib/python3.12/site-packages/dummy/native.so').chmod(0o555)
        self.config['workspace'] = '/different/canonical/workspace'
        with self.assertRaises(p.InstallError):
            self.install(manifest)
        self.no_intent()

    def test_release_closure_requires_pinned_shared_schema_and_aggregator(self):
        # Only association is checked by this offline producer; no copied code
        # executes. Real candidate/aggregation validation is the runtime gate.
        c = self.config
        candidate = {'source': {'head':'a'*40}}
        qualification = {'summary': {'status':'qualified'}}
        b = dict(version=3,kind='release-promotion-v1',repository='maldous/offmenu',
                 owner=c['logicalOwner'],issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32',
                 project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',candidate=candidate,
                 policy={},qualification=qualification,pr_number=248,main_base='9'*40,tag='release/2026.11.01')
        b['authority'] = dict(version=1,kind='release-promotion-authority-v1',owner=b['owner'],
            issue_id=b['issue_id'],project_id=b['project_id'],candidate_sha256=p._hash(p._wire(candidate)),
            qualification_sha256=p._hash(p._wire(qualification)),pr_number=248,main_base=b['main_base'],tag=b['tag'])
        c.update(version=2,binding=b,plan={'kind':'release-promotion-v1'},snapshot=dict(
            publisher_owner=b['owner'],qualification_sha256=p._hash(p._wire(qualification)),
            publication_triggers_actions=False,unresolved_findings=[],review=dict(head='a'*40,base='9'*40,
            independent=True,verdict='accept',evidence_id='release-review',findings=[])))
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()
        for name in set(p.RELEASE_SOURCE_FILES)-set(p.SOURCE_FILES):
            raw = b'synthetic shared dependency never executed\n'
            self.put(p.SOURCE+'/'+name,raw);self.source_pins[name] = p._hash(raw)
        c['codePins'] = {name:self.source_pins[name] for name in p.RELEASE_REQUIRED}
        manifest = json.loads(self.prepared())
        self.assertTrue(set(p.RELEASE_REQUIRED) <= manifest['files'].keys())
        b['authority']['tag'] = 'release/other'
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()

    def test_config_identity_shape_pins_paths_and_association_fail_closed(self):
        original = copy.deepcopy(self.config)
        variants = [dict(appId=1), dict(installationId=1), dict(repositoryId=1),
            dict(publisherUid=0), dict(publisherUid=1000), dict(publisherGid=1),
            dict(sourceHead='a'*40), dict(version=True), dict(keyPath='/anything'),
            dict(pythonSha256='0'*64), dict(codePins={}), dict(workspace='/a/../b')]
        for changes in variants:
            self.config = {**original, **changes}
            with self.subTest(changes=changes), self.assertRaises(p.InstallError):
                self.prepared()
            self.no_intent()
        self.config = original
        for section, field, value in [('binding', 'head', '0'*40),
                                      ('binding', 'head_branch', 'develop'),
                                      ('snapshot', 'source_tree', '0'*40)]:
            self.config = copy.deepcopy(original)
            self.config[section][field] = value
            with self.assertRaises(p.InstallError):
                self.prepared()
        self.config = copy.deepcopy(original)
        self.config['plan']['operations'][1]['body']['sha'] = '0'*40
        self.config['binding']['publication']['plan_sha256'] = p._hash(p._wire(self.config['plan']))
        with self.assertRaises(p.InstallError):
            self.prepared()

    def test_duplicate_unsafe_numbers_and_bounded_json(self):
        raw = self.args()['config_bytes']
        for invalid in (raw[:-1]+b',"version":1}', raw.replace(b'5554359', b'1.0'),
                        raw.replace(b'5554359', b'NaN'), b' '* (p.MAX_JSON+1)):
            args = {**self.args(), 'config_bytes': invalid, 'config_sha256': p._hash(invalid)}
            with self.assertRaises(p.InstallError):
                p.prepare(**args)
        self.no_intent()

    def test_prepared_config_composes_with_existing_controller_at_temporary_root(self):
        from offmenu.delivery.integration import Controller, _publisher_request, fingerprint
        manifest = self.prepared()
        self.assertEqual(json.loads(manifest)['configSha256'], p._hash(p._wire(self.config)))
        root = self.root / 'synthetic-controller'
        controller = Controller(root/'current', self.config['binding'], root)
        result = _publisher_request(controller, self.config, {'op': 'prepare'})
        self.assertEqual(result['status'], 'publication-ready')
        self.assertEqual(result['publication']['plan_sha256'], fingerprint(self.config['plan']))
        self.no_intent()

    def test_copied_source_closure_contains_transitive_standards_import(self):
        manifest = json.loads(self.prepared())
        source_root = Path(__file__).resolve().parents[2]
        installed = self.root / 'import-smoke'
        for name in p.SOURCE_FILES:
            target = installed / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((source_root / name).read_bytes())
        code = ("import sys; from pathlib import Path; sys.path.insert(0, " + repr(str(installed/'src'))
                + "); import offmenu.delivery.integration as integration; "
                + "import offmenu.delivery.engine as engine; import offmenu.delivery.standards as standards; "
                + "assert all(Path(m.__file__).is_relative_to(" + repr(str(installed))
                + ") for m in (integration,engine,standards))")
        subprocess.run([sys.executable, '-I', '-B', '-c', code], check=True,
                       capture_output=True, text=True)
        args = self.args()
        args['source_pins'] = {k:v for k,v in args['source_pins'].items()
                               if k != 'src/offmenu/delivery/standards.py'}
        with self.assertRaises(p.InstallError):
            p.prepare(**args)
        self.no_intent()

    def test_unqualified_owner_bytes_are_not_promoted_to_success(self):
        for section, key, value in [('review', 'independent', False),
                                    ('review', 'verdict', 'reject'),
                                    ('validation', 'status', 'running'),
                                    ('validation', 'child_tree_gone', False)]:
            original = copy.deepcopy(self.config)
            self.config['snapshot'][section][key] = value
            self.config['binding']['publication']['qualification_sha256'] = p._hash(p._wire(self.config['snapshot']))
            with self.subTest(key=key), self.assertRaises(p.InstallError):
                self.prepared()
            self.config = original
        self.no_intent()

    def test_symlink_hardlink_writable_special_files_and_unpinned_closure(self):
        path = self.local(p.VENV+'/bin/python')
        raw = path.read_bytes()
        for kind in ('symlink', 'hardlink', 'writable', 'owner-writable', 'fifo', 'directory'):
            with self.subTest(kind=kind):
                path.unlink()
                if kind == 'symlink':
                    path.symlink_to(self.local(p.VENV+'/pyvenv.cfg'))
                elif kind == 'hardlink':
                    os.link(self.local(p.VENV+'/pyvenv.cfg'), path)
                elif kind == 'fifo':
                    os.mkfifo(path)
                elif kind == 'directory':
                    path.mkdir()
                else:
                    path.write_bytes(raw)
                    path.chmod(0o755 if kind == 'owner-writable' else 0o777)
                with self.assertRaises((p.InstallError, OSError)):
                    self.prepared()
                if path.is_dir():
                    path.rmdir()
                    path.write_bytes(raw)
                else:
                    path.unlink()
                    path.write_bytes(raw)
                path.chmod(0o555)
        self.put(p.VENV+'/unqualified.py', b'unpinned')
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()

    def test_source_parent_symlink_and_nonroot_metadata_refused(self):
        parent = self.local(p.SOURCE+'/tools')
        parent.rename(parent.with_name('saved-tools'))
        parent.symlink_to(parent.with_name('saved-tools'), target_is_directory=True)
        with self.assertRaises(OSError):
            self.prepared()
        parent.unlink()
        parent.with_name('saved-tools').rename(parent)
        with self.host.directory(p.SOURCE) as fd:
            self.host.owners[os.fstat(fd).st_ino] = (1001, 1001)
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()

    def test_limits_and_missing_dependency(self):
        with patch.object(p, 'MAX_TOTAL', 2), self.assertRaises(p.InstallError):
            self.prepared()
        with patch.object(p, 'MAX_ENTRIES', 1), self.assertRaises(p.InstallError):
            self.prepared()
        self.local(p.VENV+'/pyvenv.cfg').unlink()
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()

    def test_directory_custody_and_existing_config_directory_permissions(self):
        manifest = self.prepared()
        for path, mode in ((p.SOURCE, 0o777), (p.VENV, 0o775), (p.CONFIG_DIR, 0o755)):
            directory = self.local(path)
            original = stat.S_IMODE(directory.stat().st_mode)
            directory.chmod(mode)
            with self.subTest(path=path), self.assertRaises(p.InstallError):
                self.install(manifest)
            directory.chmod(original)
            self.no_intent()

    def test_source_metadata_race_refused(self):
        calls = 0
        def race(s):
            nonlocal calls
            if stat.S_ISREG(s.st_mode):
                calls += 1
                if calls == 2:
                    values = list(s)
                    values[6] += 1
                    return os.stat_result(values)
            return s
        self.host.changed_metadata = race
        with self.assertRaises(p.InstallError):
            self.prepared()
        self.no_intent()

    def test_root_prepare_and_nonroot_install_refused(self):
        args = self.args()
        self.host.ids = (0, 0)
        with self.assertRaises(p.InstallError):
            p.prepare(**args)
        manifest = self.prepared()
        with self.assertRaises(p.InstallError):
            p.install(manifest, prepared_sha256=p._hash(manifest), **args)
        self.no_intent()

    def test_existing_config_target_receipt_and_partial_state_preserved(self):
        manifest = self.prepared()
        for path in (p.CONFIG_DIR+'/config.json', p.STATE+'/'+p.RECEIPT, p.TARGET):
            self.put(path, b'unknown prior effect')
            with self.assertRaises(p.InstallError):
                self.install(manifest)
            self.assertEqual(self.local(path).read_bytes(), b'unknown prior effect')
            self.local(path).unlink()
        claim = self.local(p.STATE+'/integration')
        claim.mkdir(mode=0o700)
        self.host.owners[claim.stat().st_ino] = (984, 976)
        (claim/'state.json').write_text('{"unknown":true}')
        with self.assertRaises(p.InstallError):
            self.install(manifest)
        self.assertEqual((claim/'state.json').read_text(), '{"unknown":true}')
        self.no_intent()

    def test_pristine_existing_claim_and_current_are_not_reinitialized(self):
        claim = self.local(p.STATE+'/integration')
        (claim/'current').mkdir(parents=True)
        for path in (claim, claim/'current'):
            path.chmod(0o700)
            self.host.owners[path.stat().st_ino] = (984, 976)
        inodes = (claim.stat().st_ino, (claim/'current').stat().st_ino)
        self.install()
        self.assertEqual(inodes, (claim.stat().st_ino, (claim/'current').stat().st_ino))
        self.assertEqual(list((claim/'current').iterdir()), [])

    def test_intent_durable_before_mutations_and_interruption_never_replayed(self):
        manifest = self.prepared()
        original = p._mkdir
        def interrupted(*args, **kwargs):
            receipt = self.local(p.STATE+'/'+p.RECEIPT)
            self.assertEqual(json.loads(receipt.read_bytes())['effect'], 'intent')
            raise OSError('synthetic interruption')
        with patch.object(p, '_mkdir', interrupted), self.assertRaises(OSError):
            self.install(manifest)
        self.assertFalse(self.local(p.TARGET).exists())
        with patch.object(p, '_mkdir', original), self.assertRaises(p.InstallError):
            self.install(manifest)

    def test_install_uses_captured_bytes_after_intent_without_source_rereads(self):
        manifest = self.prepared()
        original = p._mkdir
        changed = False
        def after_capture(*args, **kwargs):
            nonlocal changed
            if not changed:
                changed = True
                self.put(p.VENV+'/bin/python', b'changed after intent', 0o555)
                for path in p.REQUIRED:
                    self.put(p.SOURCE+'/'+path, b'changed after intent')
            return original(*args, **kwargs)
        with patch.object(p, '_mkdir', after_capture):
            self.install(manifest)
        self.assertEqual(self.local(p.TARGET+'/venv/bin/python').read_bytes(),
                         b'SYNTHETIC INTERPRETER NEVER EXECUTED')
        for path in p.REQUIRED:
            self.assertEqual(self.local(p.TARGET+'/'+path).read_bytes(), b'synthetic source\n')


if __name__ == '__main__':
    unittest.main()
