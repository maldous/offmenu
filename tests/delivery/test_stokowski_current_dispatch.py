"""Current caller-owned polling, pinned native interfaces; no external effects.

Example (preparation only): stokowski_prepare.py --current --runtime
/repo/.delivery/stokowski/current --runtime-root /repo/.delivery/stokowski
--catalog /repo/.delivery/stokowski/catalog.json --owner existing-owner.
After independent review and live prerequisites, caller entry is
stokowski_adapter.py --current --runtime /repo/.delivery/stokowski/current.
CurrentWork documents the exact v1 schemas; qualified task requests are immutable.
"""
import asyncio
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import fcntl
import io
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_adapter as adapter
import stokowski_prepare as prepare
from symphony_capacity import AdmissionError
from symphony_tasks import runtime_lease_ids


@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Use pinned Stokowski environment')
class CurrentDispatchTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.temp = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.source = self.temp/'source'
        self.source.mkdir()
        for name in ('stokowski_adapter.py','stokowski_worker.py','stokowski_prepare.py',
                     'symphony_capacity.py','symphony_tasks.py','symphony_workspace.py',
                     'symphony_codex.py','symphony_protocol.py','windmill_runner.py','capacity-policy.json'):
            target = self.source/'tools/delivery'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(adapter.SOURCE/'tools/delivery'/name, target)
        self.policy = json.loads((self.source/'tools/delivery/capacity-policy.json').read_text())
        self.policy['symphony']['pool_path'] = str(self.temp/'pool')
        self.write(self.source/'tools/delivery/capacity-policy.json', self.policy)
        self.root = self.temp/'.delivery/stokowski'
        self.root.mkdir(parents=True)
        self.runtime = self.root/'current'
        self.catalog = self.root/'catalog.json'
        self.write(self.catalog, {'version':1,'entries':[]})
        self.stack.enter_context(patch.object(adapter, 'SOURCE', self.source))
        self.stack.enter_context(patch.object(prepare, 'SOURCE', self.source))
        self.git = self.stack.enter_context(patch.object(adapter.subprocess, 'check_output', side_effect=self.git_read))
        import stokowski
        installed = Path(stokowski.__file__).parent
        self.installation = {'source_revision':adapter.PIN, 'installed_source_sha256':{
            name:adapter.file_sha(installed/name) for name in ('__init__.py','orchestrator.py')}}
        self.write(self.root/'installation.json', self.installation)
        self.prepare_current()
        self.current = adapter.CurrentWork(self.runtime)
        self.entries = []

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def git_read(self, args, **kwargs):
        if args[3] == 'show':
            return (self.source/args[4].split(':',1)[1]).read_bytes()
        if args[-2:] == ['branch','--show-current']:
            return 'feature/test-current\n'
        return ('a'*40 if args[2] == str(self.source) else 'b'*40)+'\n'

    def prepare_current(self):
        self.stack.enter_context(patch.object(sys, 'argv', ['prepare','--current','--runtime',str(self.runtime),
            '--runtime-root',str(self.root),'--catalog',str(self.catalog),'--owner','existing-owner']))
        with redirect_stdout(io.StringIO()):
            prepare.main()

    def qualify(self, number, inputs=None):
        from stokowski.models import Issue
        issue = Issue(id=f'00000000-0000-4000-8000-{number:012d}', identifier=f'UIF-{number}',
                      title='Controlled fixture', state='Todo')
        runtime = self.root/f'task-{number}'
        runtime.mkdir()
        for name in ('workspaces','requests','attempts'):
            (runtime/name).mkdir()
        manifest = {'version':1,'project_id':adapter.PROJECT,'label':f'test-{number}',
            'branch':'feature/test-current','base_revision':'b'*40,'tasks':{issue.identifier:{
                'issue_id':issue.id,'owner':'existing-owner','purpose':'test fixture',
                'allowed_paths':[f'tests/task{number}.py'],'acceptance':['Independent output check'],
                'resources':self.policy['symphony']['default_resources'],'attempt_limit':1}}}
        self.write(runtime/'manifest.json',manifest)
        self.write(runtime/'requests'/(issue.identifier+'.json'), {'prompt':'Approved immutable request','timeout_seconds':5})
        self.write(runtime/'capacity-policy.json',self.policy)
        self.write(runtime/'installation.json',self.installation)
        self.write(runtime/'provider-proof.json', {'route':'codex-chatgpt','available':True,'checked_at':time.time(),'session_ceiling':8})
        checkout = self.temp/f'checkout-{number}'
        checkout.mkdir()
        admission = {'version':1,'owner':'existing-owner','issue':issue.identifier,'issue_id':issue.id,
            'source':str(checkout),'inputs':inputs or {},'manifest_sha256':adapter.file_sha(runtime/'manifest.json'),
            'request_sha256':adapter.file_sha(runtime/'requests'/(issue.identifier+'.json')),
            'policy_sha256':adapter.file_sha(runtime/'capacity-policy.json'),
            'installation_sha256':adapter.file_sha(runtime/'installation.json')}
        self.write(runtime/'current-admission.json',admission)
        self.entries.append({'issue':issue.identifier,'issue_id':issue.id,'runtime':str(runtime),
                             'admission_sha256':adapter.file_sha(runtime/'current-admission.json')})
        self.publish()
        return issue, runtime

    def publish(self):
        self.write(self.catalog, {'version':1,'entries':self.entries})
        self.current.refresh()

    def adapted(self, current=True):
        import stokowski.config as config
        import stokowski.linear as linear
        import stokowski.orchestrator as native
        import stokowski.workspace as workspace
        targets = [(config.ProjectConfig,'agent_env'),(config.ServiceConfig,'agent_env'),
                   (config.ProjectConfig,'resolved_api_key'),(config.ServiceConfig,'resolved_api_key'),
                   (linear.LinearClient,'fetch_candidate_issues'),(workspace,'run_hook')]
        targets += [(obj,name) for obj in (workspace,native) for name in ('ensure_workspace','remove_workspace')]
        targets += [(native.Orchestrator,name) for name in ('stop','start','_tick','_safe_transition','_publish_run_report','_transition','_enter_gate',
            '_handle_gate_responses','_rebuild_gates_from_linear','_resolve_current_state')]
        targets += [(native,'run_turn')]
        for obj,name in targets:
            self.stack.enter_context(patch.object(obj,name,getattr(obj,name)))
        fetch = self.stack.enter_context(patch.object(linear.LinearClient,'fetch_candidate_issues',new_callable=AsyncMock))
        native = adapter.install_adapters(self.runtime, {'tasks':{}}, 'in-memory-only', self.current if current else None)
        return native, linear, fetch

    def client(self, issue, project=None, state=None):
        return SimpleNamespace(_graphql=AsyncMock(return_value={'issue':{
            'id':issue.id,'identifier':issue.identifier,'project':{'id':project or adapter.PROJECT},
            'state':{'name':state or issue.state}}}))

    def select(self, issue, client=None):
        return asyncio.run(self.current.candidates(client or self.client(issue), [issue]))

    def test_partial_gate_never_closes_parent(self):
        issue, _ = self.qualify(219)
        native, _, _ = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        self.assertEqual(owner._load_workflow(), [])
        client = self.client(issue)
        client.update_issue_state = AsyncMock(return_value=True)
        client.post_comment = AsyncMock()
        owner._linear = client
        owner.ledger.record_terminal = unittest.mock.Mock()
        owner._issue_current_state[issue.id] = 'evidence-pending'
        asyncio.run(owner._transition(issue, 'approve'))
        client.update_issue_state.assert_not_awaited()
        owner.ledger.record_terminal.assert_not_called()

    def test_historical_native_gates_are_never_consumed(self):
        from stokowski.tracking import make_gate_comment
        issue, _ = self.qualify(220)
        native, _, _ = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        owner._load_workflow()
        client = self.client(issue)
        client.fetch_issues_by_states = AsyncMock(return_value=[issue])
        client.fetch_comments = AsyncMock(return_value=[{'body':make_gate_comment('evidence-pending','waiting')}])
        client.post_comment = AsyncMock()
        client.update_issue_state = AsyncMock(return_value=True)
        owner._linear = client
        asyncio.run(owner._rebuild_gates_from_linear())
        asyncio.run(owner._handle_gate_responses())
        client.post_comment.assert_not_awaited()
        client.update_issue_state.assert_not_awaited()
        client.fetch_comments.assert_not_awaited()
        self.assertEqual(owner._pending_gates, {})

    def bound_gate(self, number=221):
        from symphony_capacity import digest
        issue, runtime = self.qualify(number)
        manifest = json.loads((runtime/'manifest.json').read_text())
        request = json.loads((runtime/'requests'/(issue.identifier+'.json')).read_text())
        task = manifest['tasks'][issue.identifier]
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'],
            owner=task['owner'], write_roots=task['allowed_paths'], resources=task['resources'],
            task_sha256=digest(dict(runtime=str(runtime), manifest=manifest, request=request)))
        lease = runtime_lease_ids(runtime, manifest)[issue.identifier]
        directory = runtime/'attempts'/issue.identifier
        self.write(directory/'intent.json', {'binding':binding,'lease':lease})
        self.write(directory/'dispatch-intent.json', {
            'entry_sha256':digest(self.entries[-1]), 'owner':self.current.config['owner'],
            'request_sha256':adapter.file_sha(runtime/'requests'/(issue.identifier+'.json')),
            'manifest_sha256':adapter.file_sha(runtime/'manifest.json'), 'expected_lease':lease})
        self.write(directory/'receipt.json', {'issue':issue.identifier,'lease':lease,
            'binding_sha256':digest(binding),'status':'succeeded','child_tree_gone':True,'accepted_delivery':False})
        native, _, _ = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        self.assertEqual(owner._load_workflow(), [])
        client = self.client(issue)
        client.update_issue_state = AsyncMock()
        client.fetch_comments = AsyncMock()
        client.fetch_issues_by_states = AsyncMock()
        client.post_comment = AsyncMock()
        owner._linear = client
        owner._schedule_retry = unittest.mock.Mock()
        owner.ledger.record_terminal = unittest.mock.Mock()
        asyncio.run(owner._enter_gate(issue,'evidence-pending'))
        return issue, runtime, owner, client

    def test_exact_unit_verdict_is_durable_once_and_rebuild_uses_local_binding(self):
        issue, runtime, owner, client = self.bound_gate()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        owner._pending_gates.clear()
        asyncio.run(owner._rebuild_gates_from_linear())
        self.assertEqual(owner._pending_gates, {issue.id:'evidence-pending'})
        gate['disposition'] = 'approved'
        self.current.save()
        asyncio.run(owner._handle_gate_responses())
        saved = self.current.state_path.read_bytes()
        asyncio.run(owner._handle_gate_responses())
        self.assertEqual(self.current.state_path.read_bytes(),saved)
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(reopened.state['tasks'][issue.identifier]['unit_gate']['unit_review'],'approved')
        self.assertFalse(reopened.state['accepted_delivery'])
        self.assertEqual(self.select(issue),[])
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()
        client.fetch_comments.assert_not_awaited()
        owner.ledger.record_terminal.assert_not_called()
        owner._schedule_retry.assert_not_called()

    def test_completion_after_provider_expiry_enters_and_consumes_bound_gate(self):
        issue, runtime, owner, client = self.bound_gate()
        task = self.current.state['tasks'][issue.identifier]
        task.pop('unit_gate')
        self.current.save()
        owner._pending_gates.clear()
        proof_time = json.loads((runtime/'provider-proof.json').read_text())['checked_at']
        with patch.object(adapter.time, 'time', return_value=proof_time + 601):
            with self.assertRaisesRegex(AdmissionError, 'provider_unavailable_or_stale'):
                self.current.context(issue.identifier)
            asyncio.run(owner._enter_gate(issue, 'evidence-pending'))
            self.assertIn('unit_gate', task)
            task['unit_gate']['disposition'] = 'approved'
            self.current.save()
            asyncio.run(owner._handle_gate_responses())
        self.assertEqual(task['unit_gate']['unit_review'], 'approved')
        self.assertFalse(task['unit_gate']['accepted_delivery'])
        client.update_issue_state.assert_not_awaited()
        owner._schedule_retry.assert_not_called()

    def test_existing_gate_after_provider_expiry_recovers_and_reworks_without_dispatch(self):
        issue, runtime, owner, client = self.bound_gate()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        owner._pending_gates.clear()
        proof_time = json.loads((runtime/'provider-proof.json').read_text())['checked_at']
        with patch.object(adapter.time, 'time', return_value=proof_time + 601):
            asyncio.run(owner._rebuild_gates_from_linear())
            self.assertEqual(owner._pending_gates, {issue.id:'evidence-pending'})
            gate['disposition'] = 'rework'
            self.current.save()
            asyncio.run(owner._handle_gate_responses())
        self.assertEqual(gate['unit_review'], 'rework')
        self.assertFalse(gate['accepted_delivery'])
        client.update_issue_state.assert_not_awaited()
        client.fetch_comments.assert_not_awaited()
        owner._schedule_retry.assert_not_called()

    def test_old_or_missing_gate_operation_bindings_never_consume(self):
        issue, runtime, owner, client = self.bound_gate()
        task = self.current.state['tasks'][issue.identifier]
        original = json.loads(json.dumps(task['unit_gate']))
        for field in original['binding']:
            with self.subTest(field=field):
                task['unit_gate'] = json.loads(json.dumps(original))
                task['unit_gate']['disposition'] = 'approved'
                task['unit_gate']['binding'][field] = 'old-operation'
                self.current.save()
                owner._pending_gates[issue.id] = 'evidence-pending'
                asyncio.run(owner._handle_gate_responses())
                self.assertNotIn('handled',task['unit_gate'])
        task.pop('unit_gate')
        self.current.save()
        asyncio.run(owner._handle_gate_responses())
        self.assertNotIn('unit_gate',task)
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()
        client.fetch_comments.assert_not_awaited()

    def test_native_evidence_drift_defers_even_with_matching_local_gate(self):
        issue, runtime, owner, client = self.bound_gate()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        gate['disposition'] = 'approved'
        self.current.save()
        directory = runtime/'attempts'/issue.identifier
        for name in ('intent.json','dispatch-intent.json','receipt.json'):
            path = directory/name
            original = path.read_bytes()
            self.write(path, {'old_operation':True})
            asyncio.run(owner._handle_gate_responses())
            self.assertNotIn('handled',gate)
            path.write_bytes(original)
        client.update_issue_state.assert_not_awaited()

    def test_rework_records_unit_only_and_cannot_retry_completed_operation(self):
        issue, runtime, owner, client = self.bound_gate()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        gate['disposition'] = 'rework'
        self.current.save()
        asyncio.run(owner._handle_gate_responses())
        asyncio.run(owner._handle_gate_responses())
        self.assertEqual(gate['unit_review'],'rework')
        self.assertEqual(self.select(issue),[])
        owner._schedule_retry.assert_not_called()
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()

    def test_current_guard_blocks_supplied_terminal_workflow_independently(self):
        issue, runtime, owner, client = self.bound_gate()
        owner._states_for(issue)['evidence-pending'].transitions['approve'] = 'accepted'
        owner._issue_current_state[issue.id] = 'evidence-pending'
        asyncio.run(owner._transition(issue,'approve'))
        client.update_issue_state.assert_not_awaited()
        owner.ledger.record_terminal.assert_not_called()

    def test_finite_native_gate_still_consumes_legacy_comments_and_closes_parent(self):
        from stokowski.tracking import make_gate_comment
        issue, _ = self.qualify(222)
        native, _, _ = self.adapted(current=False)
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        owner._load_workflow()
        owner._states_for(issue)['evidence-pending'].transitions['approve'] = 'accepted'
        client = self.client(issue)
        client.fetch_issues_by_states = AsyncMock(side_effect=[[issue],[]])
        client.fetch_comments = AsyncMock(return_value=[{'body':make_gate_comment('evidence-pending','waiting')}])
        client.post_comment = AsyncMock()
        client.update_issue_state = AsyncMock(return_value=True)
        owner._linear = client
        owner.ledger.record_terminal = unittest.mock.Mock()
        owner.ledger.record_gate = unittest.mock.Mock()
        asyncio.run(owner._handle_gate_responses())
        client.update_issue_state.assert_awaited_once_with(issue.id,'Done')
        owner.ledger.record_terminal.assert_called_once()

    def test_native_tick_refreshes_after_completion_and_dependency_boundary(self):
        from stokowski.models import BlockerRef
        first, runtime = self.qualify(201)
        original = (runtime/'manifest.json').read_bytes()
        native, linear, fetch = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        self.assertEqual(owner._load_workflow(), [])
        client = self.client(first)
        client.fetch_candidate_issues = lambda *args: linear.LinearClient.fetch_candidate_issues(client,*args)
        owner._linear = client
        for name in ('_reconcile','_handle_gate_responses','_evict_terminal_gates'):
            self.stack.enter_context(patch.object(owner,name,new_callable=AsyncMock))
        owner._resolve_current_state = AsyncMock(return_value=('implement',1))
        dispatched = []
        owner._dispatch = lambda issue: dispatched.append(issue.identifier)
        fetch.return_value = [first]
        asyncio.run(owner._tick())
        self.assertEqual(dispatched, ['UIF-201'])
        self.write(runtime/'attempts/UIF-201/receipt.json', {'status':'succeeded','session_id':'native-session',
            'lease':'lease-reference','child_tree_gone':True,'accepted_delivery':False})
        second, second_runtime = self.qualify(202)
        second.blocked_by = [BlockerRef(id=first.id,state='In Review')]
        client._graphql.side_effect = lambda query, variables: {'issue':{
            'id':variables['id'],'identifier':first.identifier if variables['id']==first.id else second.identifier,
            'project':{'id':adapter.PROJECT},'state':{'name':'Todo'}}}
        fetch.return_value = [first,second]
        asyncio.run(owner._tick())
        self.assertEqual(dispatched,['UIF-201'])
        second.blocked_by[0].state = 'Done'
        asyncio.run(owner._tick())
        self.assertEqual(dispatched,['UIF-201','UIF-202'])
        self.assertEqual((runtime/'manifest.json').read_bytes(),original)
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(reopened.state['tasks']['UIF-201']['receipt.json']['record']['session_id'],'native-session')
        self.assertEqual(asyncio.run(reopened.candidates(client,[first])),[])

    def test_backlog_review_done_foreign_mismatched_and_unqualified_never_selected(self):
        issue, _ = self.qualify(203)
        for state in ('Backlog','In Review','Done'):
            issue.state = state
            self.assertEqual(self.select(issue),[])
        issue.state = 'Todo'
        self.assertEqual(self.select(issue,self.client(issue,project='foreign')),[])
        self.assertEqual(self.select(issue,self.client(issue,state='Backlog')),[])
        issue.id = 'mismatch'
        self.assertEqual(self.select(issue),[])
        issue.identifier = 'UIF-999'
        self.assertEqual(self.select(issue),[])

    def test_replaced_runtime_or_uuid_is_fatal_including_after_removal(self):
        issue, _ = self.qualify(204)
        prior = self.entries[0]
        self.entries = []
        self.publish()
        self.entries = [dict(prior, runtime=str(self.root/'replacement'))]
        with self.assertRaises(AdmissionError):
            self.publish()
        self.assertIsNotNone(self.current.fatal)
        self.assertIn(issue.identifier,self.current.state['bindings'])

    def test_same_entry_reread_and_reopen_are_idempotent(self):
        issue, _ = self.qualify(205)
        for _ in range(3):
            self.assertEqual(self.select(issue),[issue])
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(asyncio.run(reopened.candidates(self.client(issue),[issue])),[issue])

    def test_drift_and_missing_inputs_defer_without_spawn(self):
        issue, runtime = self.qualify(206)
        for relative in ('manifest.json','capacity-policy.json','requests/UIF-206.json','installation.json'):
            path = runtime/relative
            original = path.read_bytes()
            path.write_bytes(original+b' ')
            self.assertEqual(self.select(issue),[])
            path.write_bytes(original)
        admission = json.loads((runtime/'current-admission.json').read_text())
        admission['inputs'] = {str(self.temp/'unstaged-Library-input'):'0'*64}
        self.write(runtime/'current-admission.json',admission)
        self.entries[0]['admission_sha256'] = adapter.file_sha(runtime/'current-admission.json')
        # A new qualification must precede first registration. Bound entries cannot be replaced.
        with self.assertRaises(AdmissionError):
            self.publish()

    def test_declared_unavailable_input_is_durable_defer(self):
        path = self.temp/'unstaged-input'
        content = b'Controlled original Library input fixture'
        issue, runtime = self.qualify(207,inputs={str(path):hashlib.sha256(content).hexdigest()})
        self.assertEqual(self.select(issue),[])
        self.assertIn('defer',json.loads(self.current.state_path.read_text())['tasks'][issue.identifier])
        path.write_bytes(content)
        self.assertEqual(self.select(issue),[issue])

    def test_stale_refused_missing_proof_and_head_drift_defer(self):
        issue, runtime = self.qualify(208)
        proof = runtime/'provider-proof.json'
        original = proof.read_bytes()
        for update in ({'available':False},{'checked_at':0},{'checked_at':float('nan')},{'session_ceiling':0}):
            value = json.loads(original)
            value.update(update)
            self.write(proof,value)
            self.assertEqual(self.select(issue),[])
        proof.unlink()
        self.assertEqual(self.select(issue),[])
        proof.write_bytes(original)
        read_git = self.git_read
        self.git.side_effect = lambda args,**kwargs: read_git(args,**kwargs) if args[2] == str(self.source) else 'wrong-head'
        self.assertEqual(self.select(issue),[])

    def turn(self, native, issue, runtime, on_pid=None):
        from stokowski.models import RunAttempt
        return native.run_turn('codex',SimpleNamespace(model=adapter.MODEL,turn_timeout_ms=10000),
            SimpleNamespace(), 'upstream prompt must not replace approval',runtime/'workspaces'/issue.identifier,
            issue,RunAttempt(issue.id,issue.identifier),on_pid=on_pid)

    def test_prepared_request_consumed_once_same_worker_and_final_pool_stays_worker_owned(self):
        issue, runtime = self.qualify(209)
        original = (runtime/'requests/UIF-209.json').read_bytes()
        native, _, _ = self.adapted()
        async def spawn(*args, **kwargs):
            self.assertEqual(Path(args[1]),self.source/'tools/delivery/stokowski_worker.py')
            self.assertEqual(args[2:],('--runtime',str(runtime),'--issue',issue.identifier))
            self.assertNotIn('LINEAR_API_KEY',kwargs['env'])
            self.assertTrue((runtime/'attempts/UIF-209/dispatch-intent.json').exists())
            self.write(runtime/'attempts/UIF-209/intent.json',{'lease':'worker-owned'})
            self.write(runtime/'attempts/UIF-209/receipt.json',{'status':'succeeded','child_tree_gone':True,'lease':'worker-owned','session_id':'native'})
            return SimpleNamespace(pid=98765,returncode=0,communicate=AsyncMock())
        mocked = self.stack.enter_context(patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=spawn))
        result = asyncio.run(self.turn(native,issue,runtime))
        self.assertEqual(result.status,'succeeded')
        self.assertEqual((runtime/'requests/UIF-209.json').read_bytes(),original)
        self.assertFalse((self.temp/'pool').exists())
        self.assertEqual(self.select(issue),[])
        with self.assertRaises(AdmissionError):
            asyncio.run(self.turn(native,issue,runtime))
        self.assertEqual(mocked.call_count,1)
        self.assertEqual(self.current.state['tasks'][issue.identifier]['intent.json']['record']['lease'],'worker-owned')

    def test_unknown_spawn_window_and_missing_receipt_survive_restart(self):
        issue, runtime = self.qualify(210)
        native, _, _ = self.adapted()
        mocked = self.stack.enter_context(patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=OSError('unknown spawn')))
        with self.assertRaises(OSError):
            asyncio.run(self.turn(native,issue,runtime))
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(asyncio.run(reopened.candidates(self.client(issue),[issue])),[])
        with self.assertRaises(AdmissionError):
            asyncio.run(self.turn(native,issue,runtime))
        self.assertEqual(mocked.call_count,1)

    def test_worker_intent_receipt_and_lease_are_barriers_even_without_request_effect(self):
        issue, runtime = self.qualify(211)
        for name in ('intent.json','receipt.json'):
            self.write(runtime/'attempts/UIF-211'/name,{'child_tree_gone':False,'status':'uncertain'})
            self.assertEqual(self.select(issue),[])
        other, other_runtime = self.qualify(212)
        pool = self.temp/'pool'
        pool.mkdir()
        with sqlite3.connect(pool/'state.sqlite') as db:
            db.execute('CREATE TABLE leases (id TEXT)')
            lease = runtime_lease_ids(other_runtime,json.loads((other_runtime/'manifest.json').read_text()))[other.identifier]
            db.execute('INSERT INTO leases VALUES (?)',(lease,))
        self.assertEqual(self.select(other),[])

    def test_cancel_supervisor_backpressure_retains_unknown_cleanup(self):
        issue, runtime = self.qualify(213)
        native, _, _ = self.adapted()
        process = SimpleNamespace(pid=98765,returncode=None,communicate=AsyncMock(side_effect=asyncio.CancelledError),
            send_signal=lambda sig:None,wait=AsyncMock(side_effect=asyncio.TimeoutError))
        self.stack.enter_context(patch.object(adapter.asyncio,'create_subprocess_exec',return_value=process))
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run(self.turn(native,issue,runtime))
        self.assertEqual(self.select(issue),[])
        self.write(runtime/'cancel.json',{})
        self.assertEqual(self.select(issue),[])

    def test_stop_drains_turn_already_removed_by_native_reconciliation(self):
        issue, runtime = self.qualify(216)
        native, _, _ = self.adapted()
        async def scenario():
            entered, cleanup, release = asyncio.Event(), asyncio.Event(), asyncio.Event()
            async def communicate():
                entered.set()
                await asyncio.Future()
            async def wait():
                cleanup.set()
                await release.wait()
                process.returncode = 0
            process = SimpleNamespace(pid=98765,returncode=None,communicate=communicate,
                                      send_signal=lambda sig:None,wait=wait)
            owner = SimpleNamespace(_running=True,_retry_timers={},_tasks={},_linear=None)
            with patch.object(adapter.asyncio,'create_subprocess_exec',return_value=process):
                turn = asyncio.create_task(self.turn(native,issue,runtime))
                await entered.wait()
                turn.cancel()  # Native _reconcile has already removed it from _tasks.
                await cleanup.wait()
                stopping = asyncio.create_task(native.Orchestrator.stop(owner))
                await asyncio.sleep(.01)
                self.assertFalse(stopping.done())
                release.set()
                await stopping
                self.assertTrue(turn.done())
                self.assertEqual(self.current.state['tasks'][issue.identifier]['dispatch-intent.json']['record']['owner'],'existing-owner')
        asyncio.run(scenario())

    def test_tracker_unknown_and_malformed_inputs_are_durable_defer(self):
        issue, runtime = self.qualify(217)
        client = self.client(issue)
        client._graphql.side_effect = ConnectionError('unavailable')
        self.assertEqual(self.select(issue,client),[])
        self.assertIn('ConnectionError',self.current.state['tasks'][issue.identifier]['defer'])
        self.write(runtime/'provider-proof.json', [])
        self.assertEqual(self.select(issue),[])
        self.assertIn('AdmissionError',self.current.state['tasks'][issue.identifier]['defer'])

    def test_workspace_uses_each_task_source_branch_and_existing_identity(self):
        issue, runtime = self.qualify(218)
        native, _, _ = self.adapted()
        clone = self.stack.enter_context(patch.object(adapter.subprocess,'run'))
        workspace = asyncio.run(native.ensure_workspace(self.runtime/'workspaces',issue.identifier,SimpleNamespace()))
        self.assertEqual(workspace.path,runtime/'workspaces'/issue.identifier)
        args = clone.call_args.args[0]
        self.assertIn('feature/test-current',args)
        self.assertEqual(args[-2],str(self.temp/'checkout-218'))
        self.assertNotEqual(args[-2],str(self.source))
        workspace.path.mkdir()
        original_git = self.git_read
        self.git.side_effect = lambda args,**kwargs: ('wrong-head' if args[2] == str(workspace.path)
                                                    else original_git(args,**kwargs))
        with self.assertRaises(AdmissionError):
            asyncio.run(native.ensure_workspace(self.runtime/'workspaces',issue.identifier,SimpleNamespace()))
        self.assertEqual(clone.call_count,1)

    def test_current_owner_lock_excludes_second_caller(self):
        with (self.root/'coordinator.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                asyncio.run(adapter.run(self.runtime,1,current_mode=True))

    def test_default_finite_filter_does_not_scan_catalog(self):
        issue, _ = self.qualify(214)
        native, linear, fetch = self.adapted(current=False)
        fetch.return_value = [issue]
        with patch.object(self.current,'refresh',side_effect=AssertionError('finite scanned current catalog')):
            self.assertEqual(asyncio.run(linear.LinearClient.fetch_candidate_issues(None,adapter.SLUG,['Todo'])),[])

    def test_finite_stops_at_manifest_receipt_and_current_waits_for_explicit_cancel(self):
        from stokowski.linear import LinearClient
        from stokowski.config import ProjectConfig
        issue, task_runtime = self.qualify(215)
        self.write(self.runtime/'manifest.json',json.loads((task_runtime/'manifest.json').read_text()))
        self.write(self.runtime/'attempts/UIF-215/receipt.json',{'status':'succeeded'})
        async def scenario(current):
            stopped = asyncio.Event()
            coordinator = SimpleNamespace(orchestrators={},start=stopped.wait,stop=AsyncMock(side_effect=stopped.set))
            native = SimpleNamespace(MultiOrchestrator=lambda path:coordinator,_offmenu_pending_control=set())
            with patch.object(ProjectConfig,'resolved_api_key',return_value='memory-only'), \
                 patch.object(adapter,'credential',return_value='memory-only'), \
                 patch.object(adapter,'install_adapters',return_value=native), \
                 patch.object(LinearClient,'fetch_candidate_issues',new=AsyncMock(return_value=[] if current else [issue])):
                task = asyncio.create_task(adapter.run(self.runtime,1,current_mode=current))
                if current:
                    await asyncio.sleep(1.05)
                    self.assertFalse(task.done(), 'Current mode must outlive both duration and old receipts')
                    self.write(self.runtime/'cancel.json',{})
                await asyncio.wait_for(task,3)
                coordinator.stop.assert_awaited_once()
        asyncio.run(scenario(False))
        asyncio.run(scenario(True))

    def test_source_and_workflow_drift_are_fatal(self):
        path = self.runtime/'workflow.yaml'
        path.write_text(path.read_text()+'\n')
        with self.assertRaises(AdmissionError):
            self.current.refresh()
        self.assertIsNotNone(self.current.fatal)

    def test_finite_preparer_still_requires_manifest_and_prompt(self):
        with redirect_stderr(io.StringIO()), patch.object(sys,'argv',['prepare','--runtime',str(self.root/'finite')]):
            with self.assertRaises(SystemExit):
                prepare.main()


if __name__ == '__main__':
    unittest.main()
