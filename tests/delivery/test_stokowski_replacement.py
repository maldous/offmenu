"""Read-only replacement-chain qualification; no workers, provider or mutation."""
import copy
import asyncio
import hashlib
import json
import os
import shutil
import time
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools/delivery'))
from symphony_capacity import AdmissionError, digest
from symphony_tasks import runtime_lease_ids
from stokowski_replacement import SCHEMA, active_entries, refusal_witness


class ReplacementTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()/'stokowski'
        self.runtime = self.root/'old-unit'
        self.owner = 'existing-owner'
        self.issue = 'UIF-117'
        self.uuid = 'b2045e98-c477-4f1f-8ca0-06724efbe3f1'
        self.policy = {'symphony': {'pool_path': str(self.root.parent/'pool')}}
        policy_sha = self.write(self.runtime/'capacity-policy.json', self.policy)
        resources = dict(cpu_millis=1000, memory_bytes=1610612736, io_slots=1, output_bytes=16777216)
        self.manifest = dict(version=1, branch='bugfix/refused-unit', base_revision='a'*40,
            label='refused-unit', project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',
            tasks={self.issue: dict(issue_id=self.uuid, owner=self.owner, purpose='Useful correction',
                allowed_paths=['tools/fix.py'], acceptance=['Preserve exact receipt'],
                resources=resources, attempt_limit=1)})
        request = dict(prompt='Actual task, before a known binder refusal', timeout_seconds=60)
        manifest_sha = self.write(self.runtime/'manifest.json', self.manifest)
        request_sha = self.write(self.runtime/'requests'/f'{self.issue}.json', request)
        admission = dict(version=1, owner=self.owner, issue=self.issue, issue_id=self.uuid,
            source=str(self.root/'source'), manifest_sha256=manifest_sha,
            request_sha256=request_sha, policy_sha256=policy_sha,
            installation_sha256='c'*64, inputs={})
        self.previous = dict(issue=self.issue, issue_id=self.uuid, runtime=str(self.runtime),
            admission_sha256=self.write(self.runtime/'current-admission.json', admission))
        self.binding = dict(branch=self.manifest['branch'], head=self.manifest['base_revision'],
            owner=self.owner, write_roots=['tools/fix.py'], resources=resources,
            task_sha256=digest(dict(runtime=str(self.runtime), manifest=self.manifest, request=request)))
        self.lease = runtime_lease_ids(self.runtime, self.manifest)[self.issue]
        self.receipt = dict(status='failed', child_started=False, child_tree_gone=True,
            launch_classification='confinement-prelaunch-refusal', exit_code=None,
            scope_violations=[], output_sha256={}, source_identity_changed=False,
            origin='native-coding', issue=self.issue, parent_runtime=str(self.runtime),
            lease=self.lease, binding_sha256=digest(self.binding), parent_binding=self.binding,
            source_head=self.manifest['base_revision'], final_head=self.manifest['base_revision'],
            final_branch=self.manifest['branch'])
        self.receipt_path = self.runtime/'attempts'/self.issue/'receipt.json'
        self.relation = dict(schema=SCHEMA, entry_sha256=digest(self.previous),
            receipt=dict(path=str(self.receipt_path), sha256=self.write(self.receipt_path, self.receipt)),
            lease=self.lease, binding_sha256=digest(self.binding))
        self.write(self.runtime/'attempts'/self.issue/'intent.json', dict(lease=self.lease, binding=self.binding))
        self.dispatch_path = self.runtime/'attempts'/self.issue/'dispatch-intent.json'
        self.dispatch = dict(entry_sha256=digest(self.previous), expected_lease=self.lease,
            owner=self.owner, request_sha256=request_sha, manifest_sha256=manifest_sha)
        self.write(self.dispatch_path, self.dispatch)
        self.database = Path(self.policy['symphony']['pool_path'])/'state.sqlite'
        self.database.parent.mkdir()
        with sqlite3.connect(self.database) as db:
            db.execute('CREATE TABLE leases(id TEXT PRIMARY KEY,binding TEXT,fingerprint TEXT,status TEXT,outcome TEXT)')
            db.execute('INSERT INTO leases VALUES(?,?,?,?,?)',
                (self.lease, json.dumps(self.binding), digest(self.binding), 'failed', 'failed'))
        self.policy_sha = policy_sha
        self.next = dict(self.previous, runtime=str(self.root/'new-unit'), admission_sha256='d'*64,
                         replacement_of=self.relation)

    @staticmethod
    def write(path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
        path.write_bytes(raw)
        path.chmod(0o600)
        return hashlib.sha256(raw).hexdigest()

    def qualify(self, previous=None, relation=None):
        return refusal_witness(previous or self.previous, relation or self.relation,
            root=self.root, owner=self.owner, policy=self.policy, policy_sha256=self.policy_sha)

    def test_known_refusal_is_read_only_and_retains_original_binding(self):
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        before_database = self.database.read_bytes()
        witness = self.qualify()
        self.assertEqual(witness['receipt'], self.relation['receipt'])
        self.assertEqual(witness['lease'], self.lease)
        self.assertEqual(witness['project_id'], self.manifest['project_id'])
        self.assertEqual({p: p.read_bytes() for p in before}, before)
        self.assertEqual(self.database.read_bytes(), before_database)

    def test_repinned_started_uncertain_success_or_outputs_never_qualify(self):
        mutations = [dict(status='unknown'), dict(status='cancelled'), dict(status='succeeded'),
            dict(child_started=True), dict(child_started=None), dict(child_tree_gone=False),
            dict(session_id='started-session'), dict(output_sha256={'tools/fix.py': 'e'*64}),
            dict(scope_violations=['outside.py']), dict(source_identity_changed=True),
            dict(origin='native-readonly-review-v1'), dict(final_head='f'*40), dict(exit_code=126)]
        for change in mutations:
            with self.subTest(change=change):
                relation = copy.deepcopy(self.relation)
                relation['receipt']['sha256'] = self.write(self.receipt_path, dict(self.receipt, **change))
                with self.assertRaises(AdmissionError):
                    self.qualify(relation=relation)
        self.write(self.receipt_path, self.receipt)

    def test_missing_or_changed_receipt_and_symlink_are_rejected(self):
        raw = self.receipt_path.read_bytes()
        self.receipt_path.write_bytes(raw+b' ')
        with self.assertRaises(AdmissionError):
            self.qualify()
        self.receipt_path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.qualify()
        other = self.runtime/'copied-receipt.json'
        self.write(other, self.receipt)
        self.receipt_path.symlink_to(other)
        with self.assertRaises(AdmissionError):
            self.qualify()

    def test_nonterminal_or_mismatched_pool_and_dispatch_are_rejected(self):
        for status, outcome in [('running', None), ('finished', 'succeeded'), ('cancel_requested', None)]:
            with self.subTest(status=status), sqlite3.connect(self.database) as db:
                db.execute('UPDATE leases SET status=?,outcome=?', (status, outcome))
            with self.assertRaises(AdmissionError):
                self.qualify()
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE leases SET status=?,outcome=?,fingerprint=?', ('failed', 'failed', 'wrong'))
        with self.assertRaises(AdmissionError):
            self.qualify()
        with sqlite3.connect(self.database) as db:
            db.execute('UPDATE leases SET fingerprint=?', (digest(self.binding),))
        self.write(self.dispatch_path, dict(self.dispatch, entry_sha256='0'*64))
        with self.assertRaises(AdmissionError):
            self.qualify()

    def test_only_explicit_immediate_chain_has_one_active_view(self):
        catalog = dict(version=1, entries=[self.previous, self.next])
        original = copy.deepcopy(catalog)
        result = active_entries(catalog, lambda previous, entry: self.qualify(previous, entry['replacement_of']))
        self.assertEqual(result, {self.issue: self.next})
        self.assertEqual(catalog, original)

    def current_fixture(self):
        """Isolate the metadata writer; no root authority is granted by this fixture."""
        import stokowski_adapter as adapter
        import stokowski_replacement as replacement
        control = self.root/'control-source'
        self.write(control/'tools/delivery/capacity-policy.json', self.policy)
        self.enterContext(patch.object(adapter, 'SOURCE', control))
        new_runtime = Path(self.next['runtime'])
        manifest = copy.deepcopy(self.manifest)
        manifest.update(label='new-unit', branch='bugfix/replacement-unit', base_revision='b'*40)
        manifest_sha = self.write(new_runtime/'manifest.json', manifest)
        request_sha = self.write(new_runtime/'requests'/f'{self.issue}.json',
                                 dict(prompt='Fresh owner-qualified replacement', timeout_seconds=60))
        admission = dict(version=1, owner=self.owner, issue=self.issue, issue_id=self.uuid,
            source=str(self.root/'new-source'), manifest_sha256=manifest_sha,
            request_sha256=request_sha, policy_sha256=self.policy_sha,
            installation_sha256='c'*64, inputs={})
        self.next['admission_sha256'] = self.write(new_runtime/'current-admission.json', admission)
        current = object.__new__(adapter.CurrentWork)
        current.root = self.root
        current.runtime = self.root/'coordinator'
        current.runtime.mkdir()
        current.state_path = current.runtime/'current-owner.json'
        current.read_only = False
        current.owner_custody = {'schema': 'isolated protected-owner fixture'}
        current.config = dict(owner=self.owner, policy_sha256=self.policy_sha,
            project_route=dict(project_id=self.manifest['project_id'], project_slug='21558318e036'),
            source_sha256={'tools/delivery/stokowski_replacement.py': adapter.file_sha(replacement.__file__)},
            catalog_versions=[{'fixture': 'exact-grant validation is covered by protected catalog tests'}])
        current.state = dict(bindings={self.issue: digest(self.previous)},
            references={self.issue: self.previous}, tasks={self.issue: {'retained-refusal': self.relation['receipt']}})
        current.entries = {self.issue: self.previous}
        current.guard = Mock()
        current.catalog = self.root/'catalog.json'
        catalog = dict(version=1, entries=[self.previous, self.next])
        current._catalog_observed_sha256 = self.write(current.catalog, catalog)
        current.catalog_record = Mock(side_effect=lambda: json.loads(current.catalog.read_text()))
        return current

    def test_normal_metadata_boundary_preserves_old_generation_once(self):
        current = self.current_fixture()
        original = self.receipt_path.read_bytes()
        current.refresh()
        self.assertEqual(current.entries, {self.issue: self.next})
        self.assertEqual(current.state['references'][self.issue], self.next)
        self.assertEqual(current.state['bindings'][self.issue], digest(self.next))
        history, = current.state['replacement_history']
        self.assertEqual(history['entry'], self.previous)
        self.assertEqual(history['task']['retained-refusal'], self.relation['receipt'])
        self.assertEqual(history['refusal']['lease'], self.lease)
        self.assertNotIn('unit_gate', current.state['tasks'][self.issue])
        current.refresh()
        self.assertEqual(len(current.state['replacement_history']), 1)
        self.assertEqual(self.receipt_path.read_bytes(), original)
        persisted = json.loads(current.state_path.read_text())
        self.assertEqual(persisted['replacement_history'][0], history)
        self.assertEqual(persisted['references'][self.issue], self.next)
        self.assertFalse((Path(self.next['runtime'])/'attempts').exists())

    def test_wrong_new_project_cannot_advance_binding(self):
        current = self.current_fixture()
        original_receipt = self.receipt_path.read_bytes()
        admission_path = Path(self.next['runtime'])/'current-admission.json'
        admission = json.loads(admission_path.read_text())
        # Preserve valid file pins while changing the semantic project binding.
        manifest_path = Path(self.next['runtime'])/'manifest.json'
        manifest = json.loads(manifest_path.read_text())
        manifest['project_id'] = 'ce60c1ab-a732-4a71-8471-14c9dc393886'
        admission['manifest_sha256'] = self.write(manifest_path, manifest)
        self.next['admission_sha256'] = self.write(admission_path, admission)
        self.write(current.catalog, dict(version=1, entries=[self.previous, self.next]))
        with self.assertRaisesRegex(AdmissionError, 'current_fatal_binding'):
            current.refresh()
        self.assertEqual(current.state['references'][self.issue], self.previous)
        self.assertNotIn('replacement_history', current.state)
        self.assertEqual(self.receipt_path.read_bytes(), original_receipt)

    def test_later_invalid_reference_cannot_persist_partial_retirement(self):
        current = self.current_fixture()
        later = dict(issue='UIF-118', issue_id='00000000-0000-4000-8000-000000000118',
                     runtime=str(self.root/'other-unit'), admission_sha256='e'*64)
        # A retained reference collides only with the later active entry.
        current.state['references']['UIF-119'] = dict(later, issue='UIF-119',
                                                    runtime=str(self.root/'retained-unit'))
        before = copy.deepcopy(current.state)
        self.write(current.catalog, dict(version=1, entries=[self.previous, self.next, later]))
        with self.assertRaisesRegex(AdmissionError, 'current_fatal_binding'):
            current.refresh()
        persisted = json.loads(current.state_path.read_text())
        for field in ('references', 'bindings', 'tasks'):
            self.assertEqual(persisted[field], before[field])
        self.assertNotIn('replacement_history', persisted)

    def test_replacement_intake_tick_does_not_select_retired_runtime(self):
        current = self.current_fixture()
        current.refresh = Mock()
        current.config['normal_intake'] = {'fixture': True}
        current._intake_policy = Mock(return_value={'references': {'qualified': {}}})
        current._intake_authority = Mock(return_value=(None, dict(issue=self.issue,
                                                     replacement_of=self.relation)))
        current._intake = AsyncMock()
        current.context = Mock(return_value=(None, self.manifest, None))
        issue = SimpleNamespace(identifier=self.issue, id=self.uuid, state='In Progress')
        client = SimpleNamespace(_graphql=AsyncMock(return_value={'issue': dict(
            id=self.uuid, identifier=self.issue, project={'id': self.manifest['project_id']},
            state={'name': 'In Progress'})}))
        self.assertEqual(asyncio.run(current.candidates(client, [issue])), [])
        current._intake.assert_awaited_once_with(client, issue)
        current.context.assert_not_called()
        client._graphql.assert_not_awaited()

    def test_reused_request_or_unsealed_relation_cannot_advance(self):
        current = self.current_fixture()
        old_admission = json.loads((self.runtime/'current-admission.json').read_text())
        new_runtime = Path(self.next['runtime'])
        old_request = json.loads((self.runtime/'requests'/f'{self.issue}.json').read_text())
        request_sha = self.write(new_runtime/'requests'/f'{self.issue}.json', old_request)
        self.assertEqual(request_sha, old_admission['request_sha256'])
        admission_path = new_runtime/'current-admission.json'
        admission = json.loads(admission_path.read_text())
        admission['request_sha256'] = request_sha
        self.next['admission_sha256'] = self.write(admission_path, admission)
        with self.assertRaisesRegex(AdmissionError, 'replacement_new_identity'):
            current._replacement_witness(self.previous, self.next)
        current.owner_custody = None
        with self.assertRaisesRegex(AdmissionError, 'replacement_owner_grant_required'):
            current._replacement_witness(self.previous, self.next)

    def root_granted_publication(self):
        import stokowski_adapter as adapter
        import stokowski_prepare as prepare
        import stokowski_replacement as replacement
        from symphony_capacity import Pool
        from test_stokowski_current_dispatch import CurrentDispatchTests
        c = CurrentDispatchTests()
        c.setUp()
        self.addCleanup(c.doCleanups)
        f, _, _, _, _, review, _, _ = c.successor_fixture()
        # Discard an unsubmitted synthetic setup proposal, not a real effect.
        c.current.state.pop('successor_request', None)
        issue, runtime = c.qualify(117)
        previous = copy.deepcopy(c.current.state['references'][issue.identifier])
        manifest = adapter.read_record(runtime/'manifest.json')
        request = adapter.read_record(runtime/'requests'/f'{issue.identifier}.json')
        task = manifest['tasks'][issue.identifier]
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'], owner=task['owner'],
            write_roots=task['allowed_paths'], resources=task['resources'],
            task_sha256=digest(dict(runtime=str(runtime), manifest=manifest, request=request)))
        lease = runtime_lease_ids(runtime, manifest)[issue.identifier]
        proof = dict(route='codex-chatgpt', available=True, checked_at=time.time(), session_ceiling=8)
        pool = Pool(c.policy['symphony']['pool_path'], c.policy)
        pool.admit(lease, binding, proof, dict(cpu_millis=64000,
            available_memory_bytes=128*1024**3, available_disk_bytes=1024**4))
        pool.finish(lease, True, 'failed')
        refused = dict(status='failed', child_started=False, child_tree_gone=True,
            launch_classification='confinement-prelaunch-refusal', exit_code=None,
            scope_violations=[], output_sha256={}, source_identity_changed=False,
            origin='native-coding', issue=issue.identifier, parent_runtime=str(runtime),
            lease=lease, binding_sha256=digest(binding), parent_binding=binding,
            source_head=manifest['base_revision'], final_head=manifest['base_revision'], final_branch=manifest['branch'])
        receipt_path = runtime/'attempts'/issue.identifier/'receipt.json'
        receipt_sha = self.write(receipt_path, refused)
        self.write(receipt_path.with_name('intent.json'), dict(lease=lease, binding=binding))
        admission = adapter.read_record(runtime/'current-admission.json')
        self.write(receipt_path.with_name('dispatch-intent.json'), dict(entry_sha256=digest(previous),
            expected_lease=lease, owner=task['owner'], request_sha256=admission['request_sha256'],
            manifest_sha256=admission['manifest_sha256']))
        relation = dict(schema=SCHEMA, entry_sha256=digest(previous),
            receipt=dict(path=str(receipt_path),sha256=receipt_sha), lease=lease, binding_sha256=digest(binding))
        outcome = dict(identifier=issue.identifier, uuid=issue.id, project_id=manifest['project_id'])
        f.manifest['tasks'] = {'UIF-106': next(iter(f.manifest['tasks'].values()))}
        f.bind_successor(c.current, review, outcome=outcome)
        f.manifest['tasks'][issue.identifier]['allowed_paths'] = task['allowed_paths']
        f.write(f.qualified/'manifest.json', f.manifest)
        f.scope = task['allowed_paths']
        f.packet.update(scope=f.scope, replacement_of=relation)
        f.repin()
        shutil.copyfile(replacement.__file__, c.source/'tools/delivery/stokowski_replacement.py')
        cfg = c.current.config
        cfg['source_sha256']['tools/delivery/stokowski_replacement.py'] = adapter.file_sha(replacement.__file__)
        cfg['qualified_successor'] = dict(path=str(f.handoff_path),sha256=f.handoff_sha)
        seed = c.catalog.read_bytes()
        next_entry = c.current._successor_entry(f.packet)
        after = dict(version=1, entries=json.loads(seed)['entries']+[next_entry])
        cfg['catalog_versions'] = [dict(sha256=hashlib.sha256(prepare._publication_bytes(after)).hexdigest(),catalog=after)]
        protected = c.temp/'sealed-replacement-owner'
        protected.mkdir()
        (protected/'catalog.json').write_bytes(seed)
        c.write(protected/'current.json', cfg)
        python = b'synthetic sealed interpreter'
        seal = dict(schema='protected-current-owner-v1', runtime=str(c.runtime), source_root=str(c.source),
            config_sha256=adapter.file_sha(protected/'current.json'), catalog_sha256=hashlib.sha256(seed).hexdigest(),
            python_sha256=hashlib.sha256(python).hexdigest())
        c.write(protected/'binding.json', seal)
        c.current.state['config_sha256'] = seal['config_sha256']
        c.current.save()
        read = lambda path: python if Path(path) == Path(sys.executable) else Path(path).read_bytes()
        self.enterContext(patch.object(adapter, 'PROTECTED_OWNER', protected))
        self.enterContext(patch.object(adapter, 'protected_owner_bytes', side_effect=read))
        self.enterContext(patch.object(adapter, 'protected_owner_tree'))
        self.enterContext(patch.object(adapter, '_PROTECTED_CLOSURES', set()))
        current = adapter.CurrentWork(c.runtime)
        self.assertIn('successor_request', current.state, current.state.get('successor_hold'))
        self.assertEqual(current.state['successor_request']['status'], 'pending', current.state.get('successor_hold'))
        return SimpleNamespace(c=c, f=f, issue=issue, current=current, previous=previous,
            next_entry=next_entry, after=after, before=seed, pool=pool, lease=lease,
            receipt_path=receipt_path, receipt_sha=receipt_sha)

    def test_root_granted_metadata_publication_and_active_view_reopen(self):
        import stokowski_adapter as adapter
        x = self.root_granted_publication()
        self.assertEqual(x.f.publish()['status'], 'published')
        self.assertEqual(json.loads(x.c.catalog.read_bytes()), x.after)
        self.assertEqual(x.f.publish()['status'], 'duplicate')
        # Transport is outside this fixture; do not invent an accepted gate.
        with patch.object(adapter.CurrentWork, '_successor_boundary'):
            observed = adapter.CurrentWork(x.c.runtime)
            reopened = adapter.CurrentWork(x.c.runtime)
        self.assertEqual(observed.entries[x.issue.identifier], x.next_entry)
        self.assertEqual(reopened.state['replacement_history'], observed.state['replacement_history'])
        self.assertEqual(len(observed.state['replacement_history']), 1)
        # Duplicate publication remains read-only after the normal writer has
        # adopted the new generation; it must not propose another append edge.
        self.assertEqual(x.f.publish()['status'], 'duplicate')
        self.assertEqual(hashlib.sha256(x.receipt_path.read_bytes()).hexdigest(), x.receipt_sha)
        self.assertFalse((x.f.runtime/'attempts').exists() and any((x.f.runtime/'attempts').iterdir()))
        self.assertEqual(next(row for row in x.pool.status() if row['id'] == x.lease)['status'], 'failed')
        x.f.provider.assert_called_once()

    def test_preexposure_recovery_requalifies_refusal_pool_and_root_edge(self):
        import stokowski_prepare as prepare
        x = self.root_granted_publication()
        with patch.object(prepare.os, 'rename', side_effect=OSError('before exposure')):
            with self.assertRaisesRegex(OSError, 'before exposure'):
                x.f.publish()
        journal = x.c.root/(x.f.runtime.name+'-publication.json')
        retained = journal.read_bytes()
        old_receipt = x.receipt_path.read_bytes()
        x.receipt_path.write_bytes(old_receipt+b' ')
        with self.assertRaises(AdmissionError):
            x.f.publish()
        x.receipt_path.write_bytes(old_receipt)
        database = Path(x.c.policy['symphony']['pool_path'])/'state.sqlite'
        with sqlite3.connect(database) as db:
            db.execute("UPDATE leases SET status='running' WHERE id=?", (x.lease,))
        with self.assertRaises(AdmissionError):
            x.f.publish()
        with sqlite3.connect(database) as db:
            db.execute("UPDATE leases SET status='failed' WHERE id=?", (x.lease,))
        with patch.object(type(x.current), 'catalog_transition',
                          side_effect=AdmissionError('exact edge revoked')):
            with self.assertRaisesRegex(AdmissionError, 'exact edge revoked'):
                x.f.publish()
        self.assertEqual(x.c.catalog.read_bytes(), x.before)
        self.assertFalse(x.f.runtime.exists())
        self.assertEqual(journal.read_bytes(), retained)
        self.assertEqual(x.f.publish()['status'], 'published')
        self.assertEqual(x.f.publish()['status'], 'duplicate')
        x.f.provider.assert_called_once()

    def test_preexposure_recovery_rejects_damaged_plan_and_retained_runtime(self):
        import stokowski_prepare as prepare
        x = self.root_granted_publication()
        original_write = prepare._publication_write
        def fail_catalog(path, content):
            if path == x.c.catalog:
                raise OSError('before catalog')
            return original_write(path, content)
        with patch.object(prepare, '_publication_write', side_effect=fail_catalog):
            with self.assertRaisesRegex(OSError, 'before catalog'):
                x.f.publish()
        journal = x.c.root/(x.f.runtime.name+'-publication.json')
        retained = journal.read_bytes()
        damaged = json.loads(retained)
        damaged['catalog_after']['entries'][-1]['replacement_of']['entry_sha256'] = '0'*64
        self.write(journal, damaged)
        with self.assertRaisesRegex(AdmissionError, 'journal_catalog_binding'):
            x.f.publish()
        journal.write_bytes(retained)
        request_path = x.f.runtime/'requests'/(x.issue.identifier+'.json')
        request = request_path.read_bytes()
        request_path.write_bytes(request+b' ')
        with self.assertRaisesRegex(AdmissionError, 'runtime_drift'):
            x.f.publish()
        request_path.write_bytes(request)
        self.assertEqual(x.c.catalog.read_bytes(), x.before)
        self.assertEqual(x.f.publish()['status'], 'published')
        self.assertEqual(x.f.publish()['status'], 'duplicate')
        x.f.provider.assert_called_once()

    def test_native_rearm_archives_refusal_once_and_reopen_only_observes(self):
        import stokowski_adapter as adapter
        import stokowski_prepare as prepare
        import stokowski_replacement as replacement
        from symphony_capacity import Pool
        from test_stokowski_current_dispatch import NativeSuccessorBindingTests
        n = NativeSuccessorBindingTests()
        n.setUp()
        self.addCleanup(n.doCleanups)
        c, first = n.c, n.f
        c.current.refresh()
        prior = copy.deepcopy(c.current.state['successor_request'])
        c.current.refresh()  # Adopt the published entry before the refusal.
        issue = first.issue['identifier']
        previous = copy.deepcopy(c.current.state['references'][issue])
        manifest = adapter.read_record(first.runtime/'manifest.json')
        request = adapter.read_record(first.runtime/'requests'/(issue+'.json'))
        task = manifest['tasks'][issue]
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'], owner=task['owner'],
            write_roots=task['allowed_paths'], resources=task['resources'],
            task_sha256=digest(dict(runtime=str(first.runtime), manifest=manifest, request=request)))
        lease = runtime_lease_ids(first.runtime, manifest)[issue]
        pool = Pool(c.policy['symphony']['pool_path'], c.policy)
        pool.admit(lease, binding, dict(route='codex-chatgpt', available=True,
            checked_at=time.time(), session_ceiling=8), dict(cpu_millis=64000,
            available_memory_bytes=128*1024**3, available_disk_bytes=1024**4))
        pool.finish(lease, True, 'failed')
        receipt_path = first.runtime/'attempts'/issue/'receipt.json'
        receipt_sha = self.write(receipt_path, dict(status='failed', child_started=False,
            child_tree_gone=True, launch_classification='confinement-prelaunch-refusal',
            exit_code=None, scope_violations=[], output_sha256={}, source_identity_changed=False,
            origin='native-coding', issue=issue, parent_runtime=str(first.runtime), lease=lease,
            binding_sha256=digest(binding), parent_binding=binding, source_head=manifest['base_revision'],
            final_head=manifest['base_revision'], final_branch=manifest['branch']))
        self.write(receipt_path.with_name('intent.json'), dict(lease=lease, binding=binding))
        admission = adapter.read_record(first.runtime/'current-admission.json')
        self.write(receipt_path.with_name('dispatch-intent.json'), dict(entry_sha256=digest(previous),
            expected_lease=lease, owner=task['owner'], request_sha256=admission['request_sha256'],
            manifest_sha256=admission['manifest_sha256']))
        frozen = {p:p.read_bytes() for directory in (first.runtime, first.qualified)
                  for p in directory.rglob('*') if p.is_file()}
        for field in ('publication_journal', 'publication_result'):
            p = Path(prior[field]['path'])
            frozen[p] = p.read_bytes()
        second = copy.copy(first)
        second.qualified = c.root/'replacement-qualified'
        second.runtime = c.root/'replacement-task'
        def retarget(value):
            return json.loads(json.dumps(value).replace(str(first.qualified), str(second.qualified))
                              .replace(str(first.runtime), str(second.runtime)))
        for field in ('config', 'packet', 'handoff', 'manifest', 'issue'):
            setattr(second, field, retarget(getattr(first, field)))
        for p in first.qualified.rglob('*'):
            if p.is_file():
                second.write(second.qualified/p.relative_to(first.qualified), retarget(json.loads(p.read_bytes())))
        relation = dict(schema=SCHEMA, entry_sha256=digest(previous),
            receipt=dict(path=str(receipt_path), sha256=receipt_sha), lease=lease, binding_sha256=digest(binding))
        second.packet['replacement_of'] = relation
        second.write(second.qualified/'request.json', dict(prompt='Distinct replacement request',timeout_seconds=60))
        claim = second.config['repository_claim']
        binding_path = Path(claim['binding_path'])
        second.write(Path(claim['path']), dict(owner=second.owner, directory=str(binding_path.parent),
                                             binding_sha256=digest(adapter.read_record(binding_path))))
        claim['sha256'] = second.sha(Path(claim['path']))
        shutil.copyfile(replacement.__file__, c.source/'tools/delivery/stokowski_replacement.py')
        cfg = c.current.config
        cfg['source_sha256']['tools/delivery/stokowski_replacement.py'] = adapter.file_sha(replacement.__file__)
        second.config['native_publication']['source_sha256']['tools/delivery/stokowski_replacement.py'] = adapter.file_sha(replacement.__file__)
        second.repin()
        n.f = second
        cfg['qualified_successor'] = second.ref(second.handoff_path)
        seed = c.catalog.read_bytes()
        entry = c.current._successor_entry(second.packet)
        after = dict(version=1, entries=json.loads(seed)['entries']+[entry])
        cfg['catalog_versions'] = [dict(sha256=hashlib.sha256(prepare._publication_bytes(after)).hexdigest(), catalog=after)]
        protected = c.temp/'sealed-replacement-owner'
        protected.mkdir()
        (protected/'catalog.json').write_bytes(seed)
        c.write(protected/'current.json', cfg)
        python = b'synthetic sealed interpreter'
        c.write(protected/'binding.json', dict(schema='protected-current-owner-v1', runtime=str(c.runtime),
            source_root=str(c.source), config_sha256=adapter.file_sha(protected/'current.json'),
            catalog_sha256=hashlib.sha256(seed).hexdigest(), python_sha256=hashlib.sha256(python).hexdigest()))
        c.current.state['config_sha256'] = adapter.file_sha(protected/'current.json')
        c.current.save()
        read = lambda path: python if Path(path) == Path(sys.executable) else Path(path).read_bytes()
        with patch.object(adapter, 'PROTECTED_OWNER', protected), \
             patch.object(adapter, 'protected_owner_bytes', side_effect=read), \
             patch.object(adapter, 'protected_owner_tree'), patch.object(adapter, '_PROTECTED_CLOSURES', set()):
            c.current = adapter.CurrentWork(c.runtime)
            self.assertEqual(c.current.state['successor_request']['status'], 'published', c.current.state.get('successor_hold'))
            fresh = copy.deepcopy(c.current.state['successor_request']['native_request'])
            self.assertNotEqual(fresh['nonce'], prior['native_request']['nonce'])
            c.current.refresh()
            reopened = adapter.CurrentWork(c.runtime)
            self.assertEqual(reopened.state['successor_request']['native_request'], fresh)
            self.assertEqual(len(reopened.state['replacement_history']), 1)
            history, = reopened.state['successor_history']
            self.assertEqual(history['native_request'], prior['native_request'])
            self.assertEqual(history['terminal_refusal']['lease'], lease)
            self.assertNotIn('terminal_review', history)
            self.assertNotIn('unit_gate', reopened.state['tasks'][issue])
        self.assertEqual(json.loads(c.catalog.read_bytes()), after)
        self.assertEqual(n.api.call_count, 2)
        self.assertEqual(sum(call['mode'] == 'prepare' for call in n.calls), 2)
        first.provider.assert_has_calls([unittest.mock.call('gpt-6.1-sol',8)]*2)
        self.assertEqual(first.provider.call_count, 2)
        for p, raw in frozen.items():
            self.assertEqual(p.read_bytes(), raw, str(p))
        self.assertFalse(any((second.runtime/'attempts').iterdir()))

    def test_duplicate_identity_runtime_branching_and_skipping_are_rejected(self):
        plain = dict(self.next)
        plain.pop('replacement_of')
        branching = dict(self.next, runtime=str(self.root/'branching-unit'))
        missing = dict(self.next, replacement_of=dict(self.relation, entry_sha256='0'*64))
        catalogs = [dict(version=1, entries=[self.previous, plain]),
            dict(version=1, entries=[self.previous, dict(self.next, runtime=self.previous['runtime'])]),
            dict(version=1, entries=[self.previous, self.next, branching]),
            dict(version=1, entries=[self.previous, missing]),
            dict(version=1, entries=[self.previous, dict(self.next, issue='UIF-118')])]
        for catalog in catalogs:
            with self.subTest(catalog=catalog), self.assertRaises(AdmissionError):
                active_entries(catalog, lambda previous, entry: self.qualify(previous, entry['replacement_of']))


if __name__ == '__main__':
    unittest.main()
