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
from unittest.mock import patch, mock_open

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

    def process_bound(self, pid, runtime):
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
        source.snapshot['runtime_path'] = '/private/.delivery/stokowski/current'
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
        self.runtime = '/private/.delivery/stokowski/current'
        self.runtime_root = '/private/.delivery/stokowski'
        for absolute in (self.runtime + '/coordinator.lock', self.runtime_root + '/coordinator.lock',
                         upgrade.STATE+'/integration/repository-owner.lock'):
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
        self.refresh_custody()

    def refresh_custody(self, historical=False):
        roles = ('runtime-coordinator', 'shared-root-coordinator', 'publisher-repository')
        paths = (self.runtime+'/coordinator.lock', self.runtime_root+'/coordinator.lock',
                 upgrade.STATE+'/integration/repository-owner.lock')
        records = []
        for role, absolute in zip(roles, paths):
            path = self.root/absolute[1:]
            parents = tuple(upgrade.ParentCustody(str(parent),
                upgrade.identity((self.root/str(parent)[1:]).lstat()))
                for parent in reversed(Path(absolute).parents))
            old = historical and role == 'runtime-coordinator'
            policy = ('caller-historical-0664-v1' if old else
                      'publisher-existing-v1' if role == 'publisher-repository' else 'caller-private-v1')
            writers = ('uid:'+str(os.geteuid()), 'gid:'+str(os.getegid())) if old else ('uid:'+str(os.geteuid()),)
            records.append(upgrade.LockRecord(role, absolute, parents, upgrade.identity(path.lstat()), policy, writers))
        self.custody = upgrade.LockCustody(self.runtime, self.runtime_root,
            self.source.snapshot['config_sha256'], '6'*64, self.quiet.evidence_sha256,
            time.time(), tuple(records))
        from dataclasses import asdict
        self.admission = replace(self.admission, lock_custody_sha256=upgrade.upgrade_digest(asdict(self.custody)))

    def repin_custody(self):
        from dataclasses import asdict
        self.admission = replace(self.admission,
            lock_custody_sha256=upgrade.upgrade_digest(asdict(self.custody)))

    def execute(self, **kwargs):
        args = dict(admission=self.admission, quiescence=self.quiet,
                    lock_custody=self.custody, host=self.host)
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
        self.assertEqual(active['host_scope'], 'synthetic')
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
        lock=self.root/self.runtime[1:]/'coordinator.lock'
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

    def test_expiry_during_verification_blocks_first_move_and_preserves_intent(self):
        clock = [time.time()]
        verify = self.host.verify
        count = [0]
        def slow_verify(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                clock[0] = self.admission.expires_at + 1
            return result
        with patch.object(upgrade.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(self.host, 'verify', side_effect=slow_verify):
            with self.assertRaisesRegex(ValueError, 'admission_expired'):
                self.execute()
        self.assertEqual(self.host.moves, 0)
        observed = upgrade.observe(self.manifest, host=self.host)
        self.assertTrue(observed['intent_verified'])
        self.assertFalse(observed['installed_verified'])
        with self.assertRaisesRegex(ValueError, 'prior_upgrade_no_replay'):
            self.execute()

    def test_expiry_between_renames_prevents_second_move_retains_original_custody(self):
        clock = [time.time()]
        move = self.host.move
        def expire_after_first(*args):
            move(*args)
            clock[0] = self.admission.expires_at + 1
        with patch.object(upgrade.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(self.host, 'move', side_effect=expire_after_first):
            with self.assertRaisesRegex(ValueError, 'admission_expired'):
                self.execute()
        self.assertEqual(self.host.moves, 1)
        target, stage, backup = upgrade.locations('owner_source', self.operation)
        self.assertFalse((self.root / target[1:]).exists())
        self.host.verify(stage, self.manifest['new']['owner_source'])
        self.host.verify(backup, self.manifest['old']['owner_source'])
        with self.assertRaisesRegex(ValueError, 'prior_upgrade_no_replay'):
            self.execute()

    def test_witness_stales_during_verification_without_admission_expiry(self):
        clock = [time.time()]
        quiet = replace(self.quiet, observed_at=clock[0] - 250)
        verify = self.host.verify
        count = [0]
        def slow_verify(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                clock[0] += 60
            return result
        with patch.object(upgrade.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(self.host, 'verify', side_effect=slow_verify):
            with self.assertRaisesRegex(ValueError, 'native_quiescence_required'):
                self.execute(quiescence=quiet)
        self.assertEqual(self.host.moves, 0)

    def test_service_changes_during_verification_blocks_mutation(self):
        verify = self.host.verify
        count = [0]
        def service_changes(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                self.host.state = dict(ActiveState='active', SubState='running', MainPID='99')
            return result
        with patch.object(self.host, 'verify', side_effect=service_changes):
            with self.assertRaisesRegex(ValueError, 'actual_service_not_stopped'):
                self.execute()
        self.assertEqual(self.host.moves, 0)

    def test_service_changes_between_renames_blocks_second_mutation(self):
        move = self.host.move
        def start_between_moves(*args):
            move(*args)
            self.host.state = dict(ActiveState='active', SubState='running', MainPID='99')
        with patch.object(self.host, 'move', side_effect=start_between_moves):
            with self.assertRaisesRegex(ValueError, 'actual_service_not_stopped'):
                self.execute()
        self.assertEqual(self.host.moves, 1)
        self.assertTrue(upgrade.observe(self.manifest, host=self.host)['intent_verified'])

    def test_expiry_during_service_readback_blocks_first_intent_write(self):
        clock = [time.time()]
        count = [0]
        def slow_service():
            count[0] += 1
            if count[0] == 2:
                clock[0] = self.admission.expires_at + 1
            return dict(ActiveState='inactive', SubState='dead', MainPID='0')
        with patch.object(upgrade.time, 'time', side_effect=lambda: clock[0]), \
             patch.object(self.host, 'service_state', side_effect=slow_service):
            with self.assertRaisesRegex(ValueError, 'admission_expired'):
                self.execute()
        self.assertEqual(self.host.moves, 0)
        self.assertFalse(upgrade.observe(self.manifest, host=self.host)['intent_verified'])

    def test_all_three_existing_locks_contend_and_acquire_in_native_order(self):
        import fcntl
        for record in self.custody.locks:
            with self.subTest(role=record.role), (self.root/record.path[1:]).open('r') as stream:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError):
                    self.execute()
        observed = []
        flock = fcntl.flock
        by_inode = {(record.identity.dev, record.identity.ino):record.role for record in self.custody.locks}
        def record_order(fd, operation):
            info = os.fstat(fd)
            observed.append(by_inode[(info.st_dev, info.st_ino)])
            return flock(fd, operation)
        with patch.object(upgrade.fcntl, 'flock', side_effect=record_order):
            self.execute()
        self.assertEqual(observed, ['runtime-coordinator', 'shared-root-coordinator', 'publisher-repository'])

    def test_historical_0664_requires_exact_admitted_policy_and_writers(self):
        path = self.root/self.runtime[1:]/'coordinator.lock'
        path.chmod(0o664)
        self.refresh_custody()  # Pinning mode alone is not a policy exemption.
        with self.assertRaisesRegex(ValueError, 'lock_mode'):
            self.execute()
        self.refresh_custody(historical=True)
        record = self.custody.locks[0]
        self.custody = replace(self.custody, locks=(replace(record, permitted_writers=('uid:1000',)),)
                               + self.custody.locks[1:])
        self.repin_custody()
        with self.assertRaisesRegex(ValueError, 'lock_permitted_writers'):
            self.execute()
        self.refresh_custody(historical=True)
        original = upgrade.identity(path.stat())
        self.assertTrue(self.execute()['installed_verified'])
        self.assertEqual(upgrade.identity(path.stat()), original)

    def test_missing_unknown_or_unadmitted_custody_never_opens_lock_path(self):
        with patch.object(upgrade.os, 'open', side_effect=AssertionError('no unknown metadata access')):
            with self.assertRaisesRegex(ValueError, 'lock_custody_required'):
                self.execute(lock_custody=None)
            with self.assertRaisesRegex(ValueError, 'lock_custody_admission'):
                self.execute(admission=replace(self.admission,lock_custody_sha256='0'*64))
        original = self.custody
        for index in (1,2):  # Actual shared-root/publisher observations are unavailable.
            records = list(original.locks)
            records[index] = replace(records[index], identity=None)
            self.custody = replace(original, locks=tuple(records))
            self.repin_custody()
            with self.subTest(role=records[index].role), \
                 patch.object(upgrade.os, 'open', side_effect=AssertionError('no unknown metadata access')):
                with self.assertRaisesRegex(ValueError,'lock_metadata'):
                    self.execute()

    def test_lock_identity_or_mode_drift_is_not_requalified_from_filesystem(self):
        path = self.root/self.runtime[1:]/'coordinator.lock'
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'existing_lock_drift'):
            self.execute()
        path.chmod(0o600)
        path.rename(path.with_name('old-coordinator.lock'))
        path.write_bytes(b'')
        path.chmod(0o600)
        with self.assertRaisesRegex(ValueError,'existing_lock_drift'):
            self.execute()
        self.assertEqual(self.host.moves,0)

    def test_symlink_and_hardlink_locks_are_rejected_without_replacement(self):
        path = self.root/self.runtime[1:]/'coordinator.lock'
        original = path.with_name('original.lock')
        path.rename(original)
        path.symlink_to(original)
        with self.assertRaises(OSError):
            self.execute()
        path.unlink()
        original.rename(path)
        os.link(path,path.with_name('alias.lock'))
        with self.assertRaisesRegex(ValueError,'existing_lock_drift'):
            self.execute()
        self.assertEqual(self.host.moves,0)

    def test_lock_replacement_after_verification_holds_before_rename(self):
        verify = self.host.verify
        count = [0]
        def replace_lock(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                path = self.root/self.runtime[1:]/'coordinator.lock'
                path.rename(path.with_name('original.lock'))
                path.write_bytes(b'')
                path.chmod(0o600)
            return result
        with patch.object(self.host,'verify',side_effect=replace_lock):
            with self.assertRaisesRegex(ValueError,'lock_name_identity_drift'):
                self.execute()
        self.assertEqual(self.host.moves,0)
        self.assertTrue(upgrade.observe(self.manifest,host=self.host)['intent_verified'])

    def test_parent_replacement_after_verification_is_detected_by_held_descriptors(self):
        verify = self.host.verify
        count = [0]
        def replace_parent(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                path = self.root/self.runtime[1:]
                path.rename(path.with_name('original-runtime'))
                path.mkdir(mode=0o755)
                path.chmod(0o755)
                (path/'coordinator.lock').write_bytes(b'')
                (path/'coordinator.lock').chmod(0o600)
            return result
        with patch.object(self.host,'verify',side_effect=replace_parent):
            with self.assertRaisesRegex(ValueError,'lock_.*drift'):
                self.execute()
        self.assertEqual(self.host.moves,0)

    def test_static_mutation_paths_do_not_use_relaxed_lock_custody(self):
        parent = self.root/'opt/offmenu-stokowski-current'
        parent.chmod(0o775)
        with self.assertRaisesRegex(ValueError,'host_parent_custody'):
            self.execute()
        self.assertEqual(self.host.moves,0)

    def test_stale_custody_or_wrong_binding_is_not_admission(self):
        self.custody = replace(self.custody, observed_at=time.time()-301)
        self.repin_custody()
        with self.assertRaisesRegex(ValueError,'lock_custody_binding'):
            self.execute()
        self.refresh_custody()
        self.custody = replace(self.custody, protected_binding_evidence_sha256=None)
        self.repin_custody()
        with self.assertRaises(ValueError):
            self.execute()

    def test_omitted_shared_root_lock_fails_before_any_lookup(self):
        self.custody = replace(self.custody, locks=(self.custody.locks[0],self.custody.locks[2]))
        self.repin_custody()
        with patch.object(upgrade.os,'open',side_effect=AssertionError('no incomplete lock set access')):
            with self.assertRaisesRegex(ValueError,'three_existing_locks_required'):
                self.execute()

    def test_custody_expiry_during_verification_holds_before_first_move(self):
        clock = [time.time()]
        self.custody = replace(self.custody, observed_at=clock[0]-250)
        self.repin_custody()
        verify = self.host.verify
        count = [0]
        def slow_verify(*args):
            result = verify(*args)
            count[0] += 1
            if count[0] == 12:
                clock[0] += 60
            return result
        with patch.object(upgrade.time,'time',side_effect=lambda:clock[0]), \
             patch.object(self.host,'verify',side_effect=slow_verify):
            with self.assertRaisesRegex(ValueError,'lock_custody_stale'):
                self.execute()
        self.assertEqual(self.host.moves,0)

    def test_production_lock_predicates_are_fixed_not_selected_by_test_uid(self):
        # Pure metadata qualification only: no production Host construction,
        # actual privileged lookup, chown or synthetic execution as UID984.
        from types import SimpleNamespace
        prod = SimpleNamespace(synthetic=False, uid=0)
        records = []
        for record in self.custody.locks:
            publisher = record.role == 'publisher-repository'
            node = replace(record.identity, uid=984 if publisher else 1000,
                           gid=976 if publisher else 1000)
            parents = []
            for parent in record.parents:
                delegated = publisher and parent.path == upgrade.STATE+'/integration'
                parents.append(replace(parent, identity=replace(parent.identity,
                    uid=984 if delegated else 0, gid=976 if delegated else 0,
                    mode=0o700 if delegated else 0o755)))
            records.append(replace(record,identity=node,parents=tuple(parents),
                                   permitted_writers=('uid:984',) if publisher else ('uid:1000',)))
        self.custody = replace(self.custody, locks=tuple(records))
        self.repin_custody()
        upgrade.qualify_lock_custody(self.custody,self.admission,json.loads(self.plan),
                                     self.quiet,prod,time.time())
        publisher = records[-1]
        self.custody = replace(self.custody,locks=tuple(records[:-1])+(
            replace(publisher,identity=replace(publisher.identity,uid=1000)),))
        self.repin_custody()
        with self.assertRaisesRegex(ValueError,'lock_owner'):
            upgrade.qualify_lock_custody(self.custody,self.admission,json.loads(self.plan),
                                         self.quiet,prod,time.time())


class ProcessBindingTests(unittest.TestCase):
    def test_real_process_reader_requires_exact_entrypoint_and_runtime_arguments(self):
        interpreter = upgrade.TARGETS['owner_venv'] + '/bin/python'
        script = upgrade.TARGETS['owner_source'] + '/tools/delivery/stokowski_adapter.py'
        runtime = '/private/legacy-runtime'
        correct = [interpreter, script, '--current', '--runtime', runtime]
        variants = [
            (correct, True),
            ([interpreter, '/tmp/unrelated.py', '--data', script, '--current'], False),
            ([interpreter, '-c', 'pass', script, '--current', '--runtime', runtime], False),
            ([interpreter, '-m', 'unrelated', script, '--current', '--runtime', runtime], False),
            ([interpreter, script, '--runtime', runtime, '--current'], False),
            (correct + ['--dry-run'], False),
            ([interpreter, '-I'] + correct[1:], False),
            (correct[:-1] + ['/other/runtime'], False),
        ]
        for argv, expected in variants:
            raw = b'\0'.join(os.fsencode(arg) for arg in argv) + b'\0'
            with self.subTest(argv=argv), \
                 patch.object(upgrade.os, 'readlink', return_value=interpreter), \
                 patch('builtins.open', mock_open(read_data=raw)):
                self.assertEqual(upgrade.Host.process_bound(object(), 123, runtime), expected)
        for raw, executable in ((b'\0'.join(os.fsencode(arg) for arg in correct), interpreter),
                                (b'\0'.join(os.fsencode(arg) for arg in correct) + b'\0', '/wrong/python')):
            with patch.object(upgrade.os, 'readlink', return_value=executable), \
                 patch('builtins.open', mock_open(read_data=raw)):
                self.assertFalse(upgrade.Host.process_bound(object(), 123, runtime))
