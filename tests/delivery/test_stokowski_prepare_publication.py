"""Offline qualification of the consumed owner publication seam, never execution."""
import copy
import fcntl
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import stokowski_prepare as prepare
from symphony_capacity import AdmissionError, digest


class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        self.source = self.directory / 'source'
        self.root = self.source / '.delivery/stokowski'
        self.qualified = self.root / 'qualified'
        self.qualified.mkdir(parents=True, mode=0o700)
        self.runtime = self.root / 'task'
        self.coordinator = self.root / 'current'
        self.coordinator.mkdir(mode=0o700)
        self.write(self.coordinator / 'current-owner.json', {'existing': 'untouched'})
        (self.coordinator / 'owner.lock').write_bytes(b'existing lock')
        self.original_coordinator = self.snapshot(self.coordinator)
        self.owner = 'synthetic-owner'
        self.base = '1' * 40
        self.branch = 'feature/uif119-preexecution-publication'
        self.scope = ['tools/delivery/stokowski_prepare.py',
                      'tests/delivery/test_stokowski_prepare_publication.py']
        self.caller = dict(service='github', principal_id='123', login='synthetic')
        self.authenticated = Mock(return_value=self.caller)
        self.provider = Mock(side_effect=lambda model, ceiling: dict(
            route='codex-chatgpt', available=True, checked_at=time.time(),
            requested_model=model, session_ceiling=ceiling,
            quota_metadata_available=False, vendor_parallel_entitlement_claimed=False))
        self.issue = dict(identifier='UIF-106', uuid='15e24665-0449-4080-981d-270398195465',
                          project_id='ce60c1ab-a732-4a71-8471-14c9dc393886')
        self.source_issue = dict(identifier='UIF-119', uuid='3e6839ad-2f22-4ab1-8f6f-973c882daabd',
                                 project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0')
        self.resources = dict(cpu_millis=1000, memory_bytes=2147483648, io_slots=1,
                              output_bytes=16777216)
        self.manifest = dict(version=1, branch=self.branch, base_revision=self.base,
                             project_id=self.issue['project_id'], label='synthetic-publication',
                             tasks={'UIF-106': dict(issue_id=self.issue['uuid'], owner=self.owner,
                                 purpose='Offline synthetic publication', allowed_paths=self.scope,
                                 acceptance=['Preserve this exact acceptance'], resources=self.resources,
                                 attempt_limit=1)})
        self.write(self.qualified / 'manifest.json', self.manifest)
        self.write(self.qualified / 'request.json', dict(prompt='Synthetic only', timeout_seconds=60))
        self.catalog = self.qualified / 'catalog.json'
        self.write(self.catalog, dict(version=1, entries=[]))
        self.catalog_before = self.catalog.read_bytes()
        self.write(self.qualified / 'observation.json', dict(id='123', login='synthetic'))
        self.write(self.qualified / 'provider.json', dict(requested_model='gpt-6.1-sol',
            requested_effort='medium', route='codex-chatgpt', session_ceiling=8,
            max_age_seconds=300, checked_at_max_future_skew_seconds=5))
        self.write(self.root / 'installation.json', dict(source_revision='2' * 40,
                                                       installed_source_sha256={'synthetic.py': '3' * 64}))
        self.write(self.source / 'tools/delivery/capacity-policy.json', {'synthetic': 'policy'})
        binding_path = self.source / '.delivery/integration/bound/selected-binding.json'
        binding = dict(owner=self.owner, repository='synthetic/offmenu', issue_id=self.issue['uuid'])
        self.write(binding_path, binding)
        claim_path = binding_path.parent.parent / 'repository-claim.json'
        self.write(claim_path, dict(owner=self.owner, directory=str(binding_path.parent),
                                    binding_sha256=digest(binding)))
        selected = dict(runtime_root=str(self.root), task_runtime=str(self.runtime),
                        coordinator_runtime=str(self.coordinator), catalog_path=str(self.catalog))
        self.config = dict(schema='offmenu-source-owner-publication-config/1', owner=self.owner,
            repository='synthetic/offmenu', owner_lane=dict(task_id='synthetic-existing-owner'),
            caller_association=dict(self.caller, authenticated_observation=self.ref(self.qualified / 'observation.json')),
            repository_claim=dict(self.ref(claim_path), binding_path=str(binding_path),
                binding_sha256=self.sha(binding_path), binding_identity_sha256=digest(binding)),
            publication_authority=dict(automatic_start=False, historical_workers_resume=False,
                                       require_normal_execution_admission=True), selected_current=selected)
        self.write(self.qualified / 'config.json', self.config)
        self.packet = dict(schema='offmenu-owner-bound-preexecution-task/1', owner=self.owner,
            unit_id=self.manifest['label'], scope=self.scope, acceptance=self.manifest['tasks']['UIF-106']['acceptance'],
            resources=self.resources, source_issue=self.source_issue, execution_outcome=self.issue,
            source=dict(repository='synthetic/offmenu', source_checkout=str(self.source),
                        base=self.base, branch=self.branch), selected_current=selected,
            owner_config=self.ref(self.qualified / 'config.json'), manifest=self.ref(self.qualified / 'manifest.json'),
            request=self.ref(self.qualified / 'request.json'), provider_requirements=self.ref(self.qualified / 'provider.json'),
            installation=dict(manifest_path=str(self.root / 'installation.json'),
                manifest_sha256=self.sha(self.root / 'installation.json'), source_revision='2' * 40,
                installed_files_verified_statically=1), inputs={})
        self.handoff = dict(directory=str(self.qualified), authenticated_principal=dict(id='123', login='synthetic'),
            source_issue=self.source_issue, execution_outcome=self.issue, source_base=self.base,
            owner_config=self.packet['owner_config'], manifest=self.packet['manifest'], request=self.packet['request'])
        self.repin()
        # Only the two read-only Git observations are synthesized. All files,
        # pins, validation, locks, journal, fsync and catalog operations are real.
        def git_observation(argv, **kwargs):
            self.assertEqual(argv[:3], ['git', '-C', str(self.source)])
            if argv[3:] == ['rev-parse', 'HEAD']:
                return self.base + '\n'
            self.assertEqual(argv[3:], ['branch', '--show-current'])
            return self.branch + '\n'
        self.enterContext(patch.object(prepare.subprocess, 'check_output', side_effect=git_observation))
        self.enterContext(patch.object(prepare.subprocess, 'Popen', side_effect=AssertionError('No processes')))
        self.enterContext(patch.object(prepare, 'CurrentWork', side_effect=AssertionError('No owner state construction')))

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.write_bytes(prepare._publication_bytes(value))

    @staticmethod
    def sha(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def ref(self, path):
        return dict(path=str(path), sha256=self.sha(path))

    @staticmethod
    def snapshot(root):
        return {str(p.relative_to(root)): p.read_bytes() for p in root.rglob('*') if p.is_file()}

    def repin(self):
        self.write(self.qualified / 'config.json', self.config)
        for key, filename in [('owner_config', 'config.json'), ('manifest', 'manifest.json'),
                              ('request', 'request.json'), ('provider_requirements', 'provider.json')]:
            self.packet[key] = self.ref(self.qualified / filename)
        paths = [self.qualified / n for n in ('config.json', 'manifest.json', 'request.json',
                                             'provider.json', 'observation.json', 'catalog.json')]
        paths += [self.root / 'installation.json', self.source / 'tools/delivery/capacity-policy.json',
                  Path(self.config['repository_claim']['path']), Path(self.config['repository_claim']['binding_path'])]
        self.packet['inputs'] = {str(p): self.sha(p) for p in paths}
        self.write(self.qualified / 'packet.json', self.packet)
        for key in ('owner_config', 'manifest', 'request'):
            self.handoff[key] = self.packet[key]
        self.handoff['task_packet'] = self.ref(self.qualified / 'packet.json')
        self.handoff_path = self.qualified / 'handoff.json'
        self.write(self.handoff_path, self.handoff)
        self.handoff_sha = self.sha(self.handoff_path)

    def publish(self, **overrides):
        arguments = dict(handoff_sha256=self.handoff_sha, authenticated_caller=self.authenticated,
                         provider_proof=self.provider)
        arguments.update(overrides)
        return prepare.prepare_publication(self.handoff_path, **arguments)

    def assert_unexposed(self):
        self.assertEqual(self.catalog.read_bytes(), self.catalog_before)
        self.assertEqual(self.snapshot(self.coordinator), self.original_coordinator)

    def test_legacy_unrelated_scope_still_has_original_refusal(self):
        task = self.manifest['tasks']['UIF-106']
        task['allowed_paths'] = ['tools/delivery/stokowski_adapter.py']
        self.packet['scope'] = task['allowed_paths']
        self.write(self.qualified/'manifest.json', self.manifest)
        self.repin()
        with self.assertRaisesRegex(AdmissionError, 'publication_task_binding'):
            self.publish()
        self.provider.assert_not_called()
        self.assert_unexposed()

    def test_typed_scope_requires_owner_binding_before_any_publication(self):
        task = self.manifest['tasks']['UIF-106']
        task.update(stage='validation', allowed_paths=[], input_paths=['tools/delivery/stokowski_adapter.py'],
                    stage_binding=dict(entry={}, identity='0'*64, inputs={}))
        self.packet.update(stage='validation', scope=task['input_paths'])
        self.write(self.qualified/'manifest.json', self.manifest)
        self.repin()
        with self.assertRaisesRegex(AdmissionError, 'publication_stage_owner_binding'):
            self.publish()
        self.provider.assert_not_called()
        self.assert_unexposed()
        self.assertFalse(self.runtime.exists())

    def test_publish_then_duplicate_is_immutable_and_preserves_existing_owner(self):
        self.assertEqual(self.publish()['status'], 'published')
        files = self.snapshot(self.root)
        self.assertEqual(self.publish()['status'], 'duplicate')
        self.assertEqual(self.snapshot(self.root), files)
        self.provider.assert_called_once_with('gpt-6.1-sol', 8)
        self.authenticated.assert_called_with()
        self.assertEqual(self.snapshot(self.coordinator), self.original_coordinator)
        self.assertEqual((self.runtime / 'manifest.json').read_bytes(), (self.qualified / 'manifest.json').read_bytes())
        journal = json.loads((self.root / 'task-publication.json').read_bytes())
        self.assertEqual(journal['requested']['effort'], 'medium')
        self.assertIsNone(journal['observed']['resolved_model'])
        self.assertIsNone(journal['observed']['resources'])
        self.assertEqual(journal['execution_admission'], 'required-before-execution')
        entry, = json.loads(self.catalog.read_bytes())['entries']
        self.assertEqual(entry['admission_sha256'], self.sha(self.runtime / 'current-admission.json'))
        self.assertEqual(set(json.loads((self.runtime / 'current-admission.json').read_bytes())),
            {'version', 'owner', 'issue', 'issue_id', 'source', 'manifest_sha256', 'request_sha256',
             'policy_sha256', 'installation_sha256', 'inputs'})

    def test_saved_json_uid_and_owner_strings_cannot_authenticate(self):
        for value in (None, self.caller, self.owner, 1000):
            with self.subTest(value=value), self.assertRaisesRegex(AdmissionError, 'trusted_adapters_required'):
                self.publish(authenticated_caller=value)
        for value in ({'uid': 1000}, dict(self.caller, login='other'), {'owner': self.owner}):
            with self.subTest(value=value), self.assertRaisesRegex(AdmissionError, 'publication_caller'):
                self.publish(authenticated_caller=lambda: value)
        self.provider.assert_not_called()
        self.assert_unexposed()
        self.assertFalse(self.runtime.exists())

    def test_all_declared_input_pins_are_consumed(self):
        for name in self.packet['inputs']:
            path = Path(name)
            original = path.read_bytes()
            path.write_bytes(original + b' ')
            with self.subTest(path=path.name), self.assertRaises(AdmissionError):
                self.publish()
            path.write_bytes(original)
            self.assert_unexposed()
        self.provider.assert_not_called()

    def test_rebound_owner_issue_source_scope_and_acceptance_are_refused(self):
        original = copy.deepcopy(self.packet)
        changes = [('owner', 'other'), ('source_issue', dict(self.source_issue, uuid='wrong')),
                   ('execution_outcome', dict(self.issue, project_id='wrong')),
                   ('scope', ['tools/other.py']), ('acceptance', ['different']),
                   ('source', dict(original['source'], base='4' * 40)),
                   ('selected_current', dict(original['selected_current'], task_runtime=str(self.coordinator)))]
        for key, value in changes:
            self.packet = copy.deepcopy(original)
            self.packet[key] = value
            self.repin()
            with self.subTest(key=key), self.assertRaises(AdmissionError):
                self.publish()
            self.assert_unexposed()
        self.provider.assert_not_called()

    def test_claim_mismatch_and_automatic_start_are_refused(self):
        for change in ('claim', 'authority'):
            original = copy.deepcopy(self.config)
            if change == 'claim':
                self.config['repository_claim']['binding_identity_sha256'] = '0' * 64
            else:
                self.config['publication_authority']['automatic_start'] = True
            self.repin()
            with self.subTest(change=change), self.assertRaises(AdmissionError):
                self.publish()
            self.assert_unexposed()
            self.config = original
        self.provider.assert_not_called()

    def test_stale_unavailable_or_wrong_provider_proof_is_refused(self):
        good = self.provider('gpt-6.1-sol', 8)
        for delta in (dict(checked_at=time.time()-301), dict(checked_at=time.time()+60),
                      dict(checked_at=float('nan')), dict(available=False),
                      dict(route='other'), dict(requested_model='other'), dict(session_ceiling=9)):
            with self.subTest(delta=delta), self.assertRaisesRegex(AdmissionError, 'provider_proof'):
                self.publish(provider_proof=lambda *args: dict(good, **delta))
            self.assert_unexposed()
            self.assertFalse(self.runtime.exists())

    def test_canonical_paths_and_symlinks_are_refused(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.qualified, target_is_directory=True)
        with self.assertRaisesRegex(AdmissionError, 'canonical_path'):
            prepare.prepare_publication(alias / 'handoff.json', handoff_sha256=self.handoff_sha,
                authenticated_caller=self.authenticated, provider_proof=self.provider)
        self.assert_unexposed()

    def test_wrong_handoff_pin_and_missing_input_coverage_are_refused(self):
        with self.assertRaisesRegex(AdmissionError, 'publication_pin'):
            self.publish(handoff_sha256='0' * 64)
        del self.packet['inputs'][self.packet['request']['path']]
        self.write(self.qualified / 'packet.json', self.packet)
        self.handoff['task_packet'] = self.ref(self.qualified / 'packet.json')
        self.write(self.handoff_path, self.handoff)
        self.handoff_sha = self.sha(self.handoff_path)
        with self.assertRaisesRegex(AdmissionError, 'input_coverage'):
            self.publish()
        self.provider.assert_not_called()
        self.assert_unexposed()

    def test_overlapping_catalog_scope_is_refused(self):
        other = self.root / 'other'
        self.write(other / 'manifest.json', self.manifest)
        self.write(other / 'current-admission.json',
                   dict(manifest_sha256=self.sha(other / 'manifest.json')))
        entry = dict(issue='UIF-107', issue_id='synthetic-other', runtime=str(other),
                     admission_sha256=self.sha(other / 'current-admission.json'))
        self.write(self.catalog, dict(version=1, entries=[entry]))
        self.catalog_before = self.catalog.read_bytes()
        self.repin()
        with self.assertRaisesRegex(AdmissionError, 'scope_overlap'):
            self.publish()
        self.provider.assert_not_called()
        self.assert_unexposed()

    def test_existing_runtime_is_preserved_without_publication(self):
        self.write(self.runtime / 'existing.json', {'state': 'retained'})
        before = self.snapshot(self.runtime)
        with self.assertRaisesRegex(AdmissionError, 'runtime_exists'):
            self.publish()
        self.assertEqual(self.snapshot(self.runtime), before)
        self.assert_unexposed()

    def test_publication_lock_serializes_without_touching_owner_lock(self):
        with (self.root / 'publication.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                self.publish()
        self.assert_unexposed()
        self.provider.assert_not_called()

    def test_conflicting_immutable_binding_is_held(self):
        self.publish()
        before = self.snapshot(self.root)
        self.packet['resources']['io_slots'] = 2
        self.manifest['tasks']['UIF-106']['resources']['io_slots'] = 2
        self.write(self.qualified / 'manifest.json', self.manifest)
        self.repin()
        catalog = self.catalog.read_bytes()
        with self.assertRaisesRegex(AdmissionError, 'immutable_binding_conflict'):
            self.publish()
        self.assertEqual(self.catalog.read_bytes(), catalog)
        for name, content in before.items():
            if name.startswith('task/') or name == 'task-publication.json':
                self.assertEqual((self.root / name).read_bytes(), content)
        self.provider.assert_called_once()

    def test_failure_before_catalog_exposure_recovers_without_new_provider_call(self):
        original_write = prepare._publication_write
        def fail_catalog(path, content):
            if path == self.catalog:
                self.assertTrue((self.runtime / 'current-admission.json').is_file())
                raise OSError('synthetic crash before catalog')
            return original_write(path, content)
        with patch.object(prepare, '_publication_write', side_effect=fail_catalog):
            with self.assertRaisesRegex(OSError, 'synthetic crash'):
                self.publish()
        self.assert_unexposed()
        self.assertEqual(self.publish()['status'], 'published')
        self.provider.assert_called_once()

    def test_failure_before_runtime_rename_recovers_from_journal(self):
        with patch.object(prepare.os, 'rename', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                self.publish()
        self.assert_unexposed()
        self.assertFalse(self.runtime.exists())
        self.assertEqual(self.publish()['status'], 'published')
        self.provider.assert_called_once()

    def test_failure_after_catalog_replace_reconciles_as_duplicate(self):
        original_sync = prepare._publication_sync
        def crash_after_exposure(path):
            if path == self.catalog.parent and self.catalog.read_bytes() != self.catalog_before:
                raise OSError('synthetic durability uncertainty')
            return original_sync(path)
        with patch.object(prepare, '_publication_sync', side_effect=crash_after_exposure):
            with self.assertRaises(OSError):
                self.publish()
        before = self.snapshot(self.root)
        self.assertEqual(self.publish()['status'], 'duplicate')
        self.assertEqual(self.snapshot(self.root), before)
        self.provider.assert_called_once()

    def test_persistent_runtime_root_fsync_failure_holds_until_durable_recovery(self):
        original_sync = prepare._publication_sync
        def fail_root_after_rename(path):
            if path == self.root and self.runtime.exists():
                raise OSError('synthetic runtime root durability failure')
            return original_sync(path)
        with patch.object(prepare, '_publication_sync', side_effect=fail_root_after_rename):
            for attempt in range(2):
                with self.subTest(attempt=attempt), self.assertRaisesRegex(OSError, 'runtime root durability'):
                    self.publish()
                self.assertTrue(self.runtime.is_dir())
                self.assert_unexposed()
        retained = self.snapshot(self.runtime)
        synced = []
        def record_sync(path):
            original_sync(path)
            synced.append(path)
        original_write = prepare._publication_write
        def check_catalog_barrier(path, content):
            if path == self.catalog:
                self.assertIn(self.root, synced)
            return original_write(path, content)
        with patch.object(prepare, '_publication_sync', side_effect=record_sync), \
                patch.object(prepare, '_publication_write', side_effect=check_catalog_barrier):
            result = self.publish()
        self.assertEqual(result['status'], 'published')
        self.assertEqual(result['dispatches'], 0)
        self.assertIn(self.root, synced)
        self.assertEqual(self.snapshot(self.runtime), retained)
        self.assertEqual(self.snapshot(self.coordinator), self.original_coordinator)
        self.provider.assert_called_once()

    def test_persistent_catalog_parent_fsync_failure_holds_until_durable_duplicate(self):
        original_sync = prepare._publication_sync
        def fail_parent_after_replace(path):
            if path == self.catalog.parent and self.catalog.read_bytes() != self.catalog_before:
                raise OSError('synthetic catalog parent durability failure')
            return original_sync(path)
        with patch.object(prepare, '_publication_sync', side_effect=fail_parent_after_replace):
            for attempt in range(2):
                with self.subTest(attempt=attempt), self.assertRaisesRegex(OSError, 'catalog parent durability'):
                    self.publish()
                self.assertNotEqual(self.catalog.read_bytes(), self.catalog_before)
                self.assertEqual(self.snapshot(self.coordinator), self.original_coordinator)
        retained = self.snapshot(self.root)
        with patch.object(prepare, '_publication_sync', wraps=original_sync) as sync, \
                patch.object(prepare, '_publication_write', side_effect=AssertionError('No replacement on duplicate')):
            result = self.publish()
        self.assertEqual(result['status'], 'duplicate')
        self.assertEqual(result['dispatches'], 0)
        self.assertIn(self.root, [call.args[0] for call in sync.call_args_list])
        self.assertIn(self.catalog.parent, [call.args[0] for call in sync.call_args_list])
        self.assertEqual(self.snapshot(self.root), retained)
        self.provider.assert_called_once()

    def test_retained_execution_effects_or_runtime_drift_hold_without_replay(self):
        self.publish()
        before = self.catalog.read_bytes()
        receipt = self.runtime / 'attempts/receipt.json'
        self.write(receipt, {'synthetic': 'uncertain effect'})
        with self.assertRaisesRegex(AdmissionError, 'retained_effect_requires_reconciliation'):
            self.publish()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.assertTrue(receipt.is_file())
        self.provider.assert_called_once()

    def test_catalog_drift_holds_without_replay(self):
        self.publish()
        self.write(self.catalog, {'version': 1, 'entries': []})
        # A pinned original catalog can be reconciled, but a third value cannot.
        self.catalog.write_bytes(b'{"version":1,"entries":[],"unexpected":true}')
        before = self.catalog.read_bytes()
        with self.assertRaisesRegex(AdmissionError, 'catalog_drift'):
            self.publish()
        self.assertEqual(self.catalog.read_bytes(), before)
        self.provider.assert_called_once()

    def test_runtime_file_drift_holds_without_repair_or_replay(self):
        self.publish()
        manifest = self.runtime / 'manifest.json'
        manifest.write_bytes(b'changed runtime input')
        before = self.snapshot(self.root)
        with self.assertRaisesRegex(AdmissionError, 'runtime_drift'):
            self.publish()
        self.assertEqual(self.snapshot(self.root), before)
        self.provider.assert_called_once()

    def test_missing_exposed_runtime_requires_reconciliation(self):
        self.publish()
        retained = self.root / 'retained-runtime'
        self.runtime.rename(retained)
        before = self.snapshot(self.root)
        with self.assertRaisesRegex(AdmissionError, 'exposed_runtime_missing_reconcile'):
            self.publish()
        self.assertFalse(self.runtime.exists())
        self.assertEqual(self.snapshot(self.root), before)
        self.provider.assert_called_once()

    def test_damaged_journal_cannot_materialize_unpinned_files(self):
        with patch.object(prepare.os, 'rename', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                self.publish()
        journal_path = self.root / 'task-publication.json'
        journal = json.loads(journal_path.read_bytes())
        journal['files']['manifest.json'] = '{}'
        self.write(journal_path, journal)
        with self.assertRaisesRegex(AdmissionError, 'journal_file_binding'):
            self.publish()
        self.assertFalse(self.runtime.exists())
        self.assert_unexposed()
        self.provider.assert_called_once()


if __name__ == '__main__':
    unittest.main()
