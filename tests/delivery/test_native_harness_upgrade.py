"""Executable upgrade tests on disposable filesystem and fixed fake service only."""
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from dataclasses import replace
from unittest.mock import patch

import native_harness_upgrade as upgrade
import protected_owner_install as protected
import test_native_harness_adoption as preflight_tests


class FixtureHost(upgrade.Host):
    state = dict(ActiveState='inactive', SubState='dead', MainPID='0')
    bound = True
    moves = 0
    fail_move = None

    def service_state(self):
        return dict(self.state)

    def process_bound(self, pid):
        return self.bound

    def move(self, old, new):
        self.moves += 1
        if self.moves == self.fail_move:
            raise OSError('synthetic interrupted rename')
        super().move(old, new)


def closure(root):
    directories, files = {}, {}
    for path in (root, *root.rglob('*')):
        name = str(path.relative_to(root)) if path != root else ''
        if path.is_dir():
            path.chmod(0o755)
        info = path.stat()
        item = dict(mode=stat.S_IMODE(info.st_mode), uid=info.st_uid, gid=info.st_gid)
        if path.is_dir():
            directories[name] = item
        else:
            files[name] = dict(item, size=info.st_size, sha256=protected.sha(path.read_bytes()))
    return dict(directories=directories, files=files)


class UpgradeTests(unittest.TestCase):
    def setUp(self):
        self.source = preflight_tests.AdoptionTests()
        self.source.setUp()
        self.addCleanup(self.source.doCleanups)
        self.temp = tempfile.TemporaryDirectory(prefix='offmenu-upgrade-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.host = FixtureHost(_synthetic=self.root)
        self.operation = '9' * 64
        self.manifest = dict(version=1, kind='native-harness-upgrade-v1',
            operation_id=self.operation, preflight_sha256='', old={}, new={}, legacy_receipts={})
        for role in upgrade.TARGETS:
            target, stage, _ = upgrade.locations(role, self.operation)
            for side, absolute in (('old', target), ('new', stage)):
                path = self.root / absolute[1:]
                path.mkdir(parents=True)
                (path/'module.txt').write_text(side + role)
                (path/'module.txt').chmod(0o444)
                if role == 'owner_source':
                    (path/'.git').mkdir()
                    (path/'.git/HEAD').write_text(('1' if side == 'old' else 'b') * 40 + '\n')
                    (path/'.git/HEAD').chmod(0o444)
                    if side == 'new':
                        (path/'source').mkdir()
                        (path/'source/fixture.py').write_bytes(b'coherent source artifact')
                        (path/'source/fixture.py').chmod(0o444)
                self.manifest[side][role] = closure(path)
        source = self.source
        for role, key in (('owner_source','source'), ('owner_venv','runtime'), ('owner_config','config')):
            ref = source.write(protected.encoded(self.manifest['old'][role]))
            source.snapshot[key+'_sha256'] = ref['sha256']
            source.rollback['artifacts'][key] = ref
        source.request['legacy_snapshot'] = source.write(source.snapshot)
        source.stop.update(snapshot_sha256=source.request['legacy_snapshot']['sha256'], observed_at=time.time())
        source.request['stop_witness'] = source.write(source.stop)
        source.rollback['snapshot_sha256'] = source.request['legacy_snapshot']['sha256']
        source.request['rollback'] = source.write(source.rollback)
        target = source.request['target']
        target['dependencies'] = source.write(protected.encoded(self.manifest['new']['owner_venv']))
        target['config'] = source.write(protected.encoded(self.manifest['new']['owner_config']))
        from native_harness_contract import fingerprint
        source.request['readback'].update(closure_sha256=fingerprint(target),
            config_sha256=target['config']['sha256'], dependencies_sha256=target['dependencies']['sha256'])
        from native_harness_adoption import prepare
        self.plan = prepare(source.request, source.policy, evidence_root=source.root,
                            accepted=source.accepted)
        self.manifest['preflight_sha256'] = protected.sha(self.plan)
        for absolute in (str(protected.RECEIPT), upgrade.STATE + '/publisher-install.jsonl'):
            path = self.root / absolute[1:]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('original permanent receipt\n')
            path.chmod(0o600)
            self.manifest['legacy_receipts'][absolute] = protected.sha(path.read_bytes())
        for absolute in ('/private/legacy-runtime/coordinator.lock', upgrade.STATE+'/integration/repository-owner.lock'):
            path = self.root / absolute[1:]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'')
            path.chmod(0o600)
        for directory in self.root.rglob('*'):
            if directory.is_dir():
                directory.chmod(0o755)
        self.admission = upgrade.OwnerAdmission('root-owner', protected.sha(self.plan),
            upgrade.upgrade_digest(self.manifest), '7'*64, time.time()+200)
        self.quiet = upgrade.Quiescence(source.request['legacy_snapshot']['sha256'],
            '8'*64, time.time(), 0, True, ())

    def execute(self, **kwargs):
        args = dict(admission=self.admission, quiescence=self.quiet, host=self.host)
        args.update(kwargs)
        return upgrade.execute(self.plan,self.manifest,**args)

    def test_real_temp_moves_exact_readback_and_permanent_nonreplay(self):
        result = self.execute()
        self.assertTrue(result['installed_verified'])
        self.assertTrue(result['rollback_verified'])
        self.assertFalse(result['active_observed'])
        for path,pin in self.manifest['legacy_receipts'].items():
            self.assertEqual(protected.sha((self.root/path[1:]).read_bytes()),pin)
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.execute()
        self.host.state = dict(ActiveState='active', SubState='running', MainPID='123')
        active = upgrade.verify_active(self.manifest,host=self.host)
        self.assertTrue(active['active_observed'])
        self.assertFalse(active['legacy_retired'])

    def test_partial_move_keeps_intent_old_custody_and_unknown_no_retry(self):
        self.host.fail_move = 2
        with self.assertRaises(OSError):
            self.execute()
        _,stage,backup = upgrade.locations('owner_source',self.operation)
        self.assertTrue((self.root/backup[1:]).exists())
        self.assertTrue((self.root/stage[1:]).exists())
        observation = upgrade.observe(self.manifest,host=self.host)
        self.assertFalse(observation['installed_verified'])
        self.assertFalse(observation['replay_authorized'])
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.execute()
        self.manifest['operation_id'] = 'a' * 64
        self.admission = replace(self.admission, upgrade_sha256=upgrade.upgrade_digest(self.manifest))
        with self.assertRaisesRegex(ValueError,'prior_upgrade_no_replay'):
            self.execute()

    def test_admission_unknown_inflight_and_actual_service_hold_before_intent(self):
        for quiet in (replace(self.quiet,inflight=1),replace(self.quiet,children_gone=False),
                      replace(self.quiet,observed_at=time.time()-301),
                      replace(self.quiet,unresolved_operation_ids=('original-job',))):
            with self.subTest(quiet=quiet),self.assertRaises(ValueError):
                self.execute(quiescence=quiet)
        with self.assertRaises(ValueError):
            self.execute(admission=replace(self.admission,upgrade_sha256='0'*64))
        self.host.state = dict(ActiveState='active',SubState='running',MainPID='99')
        with self.assertRaisesRegex(ValueError,'actual_service_not_stopped'):
            self.execute()
        self.assertEqual(self.host.moves,0)

    def test_stage_extra_link_mode_or_bytes_drift_refuses_before_writes(self):
        _,stage,_ = upgrade.locations('publisher',self.operation)
        path = self.root/stage[1:]/'module.txt'
        original = path.read_bytes()
        path.chmod(0o644)
        path.write_bytes(b'changed')
        path.chmod(0o444)
        with self.assertRaises(ValueError):
            self.execute()
        path.chmod(0o644);path.write_bytes(original);path.chmod(0o444)
        path.unlink();path.symlink_to('/etc/passwd')
        with self.assertRaises((ValueError,OSError)):
            self.execute()
        self.assertEqual(self.host.moves,0)

    def test_old_closure_rebinding_and_backup_conflict_never_overwrite(self):
        self.manifest['old']['owner_source']['files']['module.txt']['sha256']='0'*64
        self.admission=replace(self.admission,upgrade_sha256=upgrade.upgrade_digest(self.manifest))
        with self.assertRaisesRegex(ValueError,'old_snapshot_closure'):
            self.execute()

    def test_no_intent_is_not_installed_and_active_process_must_match(self):
        self.assertFalse(upgrade.observe(self.manifest,host=self.host)['installed_verified'])
        self.execute()
        self.host.state=dict(ActiveState='active',SubState='running',MainPID='123')
        self.host.bound=False
        with self.assertRaisesRegex(ValueError,'active_process_binding'):
            upgrade.verify_active(self.manifest,host=self.host)
        self.host.bound=True
        path=self.root/upgrade.TARGETS['owner_source'][1:]/'module.txt'
        path.chmod(0o644);path.write_bytes(b'wrong');path.chmod(0o444)
        with self.assertRaisesRegex(ValueError,'active_closure_mismatch'):
            upgrade.verify_active(self.manifest,host=self.host)

    def test_no_replace_rename_and_preexisting_receipt_are_permanent_fences(self):
        target,stage,backup=upgrade.locations('owner_config',self.operation)
        (self.root/backup[1:]).mkdir(mode=0o755)
        (self.root/backup[1:]).chmod(0o755)
        with self.assertRaisesRegex(ValueError,'rollback_slot_exists'):
            self.execute()
        with self.assertRaises(OSError):
            self.host.move(stage,target)
        self.assertTrue((self.root/stage[1:]).exists())

    def test_production_host_never_available_to_unprivileged_test(self):
        with self.assertRaisesRegex(ValueError,'root_owner_required'):
            upgrade.Host()

    def test_legacy_receipt_drift_after_install_remains_unknown(self):
        self.execute()
        path=self.root/str(protected.RECEIPT)[1:]
        path.write_text('changed original receipt')
        observation=upgrade.observe(self.manifest,host=self.host)
        self.assertFalse(observation['legacy_receipts_verified'])
        self.assertFalse(observation['installed_verified'])

    def test_permission_drift_and_contended_existing_lock_hold(self):
        import fcntl
        lock=self.root/'private/legacy-runtime/coordinator.lock'
        with lock.open('r+') as stream:
            fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.execute()
        _,stage,_=upgrade.locations('owner_source',self.operation)
        path=self.root/stage[1:]/'module.txt'
        path.chmod(0o666)
        with self.assertRaises(ValueError):
            self.execute()
        self.assertEqual(self.host.moves,0)
