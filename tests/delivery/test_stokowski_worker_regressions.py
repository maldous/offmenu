"""Local restart and ownership checks: real Git/SQLite, no model or tracker calls."""
from contextlib import ExitStack, nullcontext
import asyncio
import copy
import json
import importlib.util
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

TOOLS = Path(__file__).resolve().parents[2] / 'tools/delivery'
sys.path.insert(0, str(TOOLS))
import stokowski_adapter as adapter
import stokowski_worker as worker
from symphony_capacity import AdmissionError, BRANCH, Pool, digest
from symphony_tasks import PROJECT_ID, runtime_lease_ids


class WorkerRegressions(unittest.TestCase):
    issue = 'UIF-92'

    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.policy = json.loads((TOOLS / 'capacity-policy.json').read_text())
        self.policy['symphony']['pool_path'] = str(self.root / 'pool')
        # Use real host admission and leave the test process's affinity unchanged.
        self.policy['host'].update(cpu_reserve=0, memory_reserve_bytes=0,
                                   disk_reserve_bytes=0)
        self.policy['symphony']['cpu_budget_millis'] = len(os.sched_getaffinity(0)) * 1000
        self.proof = dict(route='codex-chatgpt', available=True,
                          checked_at=time.time(), session_ceiling=8)
        self.request = dict(prompt='Bounded offline test', timeout_seconds=5)
        self.runtime, self.manifest = self.make_runtime('run', 'tests/first.py')
        # These are the only execution/provider boundaries replaced in worker tests.
        self.provider = self.enterContext(patch.object(
            worker, 'isolated_codex_environment', side_effect=lambda *args: nullcontext({})))
        self.real_supervise = worker.supervise
        self.process = self.enterContext(patch.object(
            worker, 'supervise', side_effect=self.completed_process))

    def git(self, workspace, *args):
        # Ignore user Git configuration/hooks and supply only synthetic identity.
        environment = {'PATH': os.defpath, 'HOME': str(self.root),
                       'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull,
                       'GIT_AUTHOR_NAME': 'Regression', 'GIT_AUTHOR_EMAIL': 'test@example.invalid',
                       'GIT_COMMITTER_NAME': 'Regression',
                       'GIT_COMMITTER_EMAIL': 'test@example.invalid'}
        return subprocess.check_output(
            ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false',
             '-C', str(workspace), *args], env=environment, text=True,
            stderr=subprocess.PIPE).strip()

    def make_runtime(self, relative, allowed_path):
        runtime = self.root / relative
        workspace = runtime / 'workspaces' / self.issue
        workspace.mkdir(parents=True)
        self.git(workspace, 'init', '-b', BRANCH)
        (workspace / 'README.md').write_text('Offline source fixture\n')
        self.git(workspace, 'add', 'README.md')
        self.git(workspace, 'commit', '-m', 'Fixture')
        manifest = dict(version=1, branch=BRANCH,
                        base_revision=self.git(workspace, 'rev-parse', 'HEAD'),
                        project_id=PROJECT_ID, label='offline-regression', tasks={
            self.issue: dict(issue_id='00000000-0000-4000-8000-000000000092',
                             owner='test-owner', purpose='Offline regression',
                             allowed_paths=[allowed_path], acceptance=['Local checks'],
                             resources=dict(cpu_millis=1, memory_bytes=1024,
                                            io_slots=1, output_bytes=0), attempt_limit=1)})
        for name, value in [('manifest.json', manifest),
                            ('capacity-policy.json', self.policy),
                            ('provider-proof.json', self.proof)]:
            (runtime / name).write_text(json.dumps(value))
        return runtime, manifest

    def directory(self, runtime=None):
        return (runtime or self.runtime) / 'attempts' / self.issue

    def lease(self, runtime=None, manifest=None):
        return runtime_lease_ids(runtime or self.runtime, manifest or self.manifest)[self.issue]

    def pool(self):
        # Every observation reopens the actual durable database, as after restart.
        return Pool(self.policy['symphony']['pool_path'], self.policy)

    def rows(self):
        return {row['id']: row for row in self.pool().status()}

    def events(self):
        with sqlite3.connect(Path(self.policy['symphony']['pool_path']) / 'state.sqlite') as db:
            return db.execute('SELECT id,event FROM events ORDER BY sequence').fetchall()

    def admit(self, runtime=None, manifest=None, request=None):
        runtime = runtime or self.runtime
        manifest = manifest or self.manifest
        task = manifest['tasks'][self.issue]
        binding = dict(branch=manifest['branch'], head=manifest['base_revision'],
                       owner=task['owner'], write_roots=task['allowed_paths'],
                       resources=task['resources'], task_sha256=digest(dict(
                           runtime=str(runtime.resolve()), manifest=manifest,
                           request=request or self.request)))
        lease = self.lease(runtime, manifest)
        self.pool().admit(lease, binding, self.proof, worker.host_snapshot(runtime))
        directory = self.directory(runtime)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'intent.json').write_text(json.dumps(dict(lease=lease, binding=binding)))
        return lease

    @staticmethod
    def completed_process(command, prompt, workspace, environment, directory, *args):
        (directory / 'stdout.jsonl').write_text(
            json.dumps(dict(type='turn.completed', usage={'input_tokens': 3})) + '\n')
        return dict(status='succeeded', child_tree_gone=True, exit_code=0)

    def test_active_lease_and_intent_block_restart_without_changing_durable_state(self):
        lease = self.admit()
        before = self.events()
        intent = (self.directory() / 'intent.json').read_bytes()
        with self.assertRaisesRegex(AdmissionError, 'Existing resource lease'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.provider.assert_not_called()
        self.assertEqual(self.rows()[lease]['status'], 'running')
        self.assertEqual(self.events(), before)
        self.assertEqual((self.directory() / 'intent.json').read_bytes(), intent)
        self.assertFalse((self.directory() / 'receipt.json').exists())

    def test_changed_request_cannot_rebind_an_existing_lease(self):
        lease = self.admit()
        before = self.rows()[lease]
        with self.assertRaisesRegex(AdmissionError, 'immutable_binding_conflict'):
            worker.execute(self.runtime, self.issue, dict(self.request, prompt='Different task'))
        self.process.assert_not_called()
        self.assertEqual(self.rows()[lease], before)

    def test_cancel_requested_lease_blocks_restart(self):
        lease = self.admit()
        self.pool().cancel(lease)
        with self.assertRaisesRegex(AdmissionError, 'reconcile_or_new_task_required'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual(self.rows()[lease]['status'], 'cancel_requested')

    def test_completed_receipt_blocks_replay_after_lease_release(self):
        first = worker.execute(self.runtime, self.issue, self.request)
        self.assertEqual(first['status'], 'succeeded')
        self.assertFalse(first['accepted_delivery'])
        self.assertEqual(self.rows()[self.lease()]['status'], 'finished')
        receipt = (self.directory() / 'receipt.json').read_bytes()
        before = self.events()
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual((self.directory() / 'receipt.json').read_bytes(), receipt)
        self.assertEqual(self.events(), before)

    def test_confinement_refusal_finishes_pool_with_no_child_and_retains_intent(self):
        self.process.side_effect = self.real_supervise
        with patch.object(worker, 'bind_native', side_effect=ValueError('fixture policy absent')) as bind:
            result = worker.execute(self.runtime, self.issue, self.request)
        bind.assert_called_once()
        self.assertEqual(result['launch_classification'], 'confinement-prelaunch-refusal')
        self.assertFalse(result['child_started'])
        self.assertTrue(result['child_tree_gone'])
        self.assertEqual(self.rows()[self.lease()]['status'], 'failed')
        self.assertEqual(self.rows()[self.lease()]['outcome'], 'failed')
        self.assertTrue((self.directory()/'intent.json').exists())
        self.assertIsNone(result['resolved_model'])
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)

    def test_uncertain_cleanup_retains_lease_and_blocks_replay(self):
        self.process.side_effect = None
        self.process.return_value = dict(status='uncertain', child_tree_gone=False)
        result = worker.execute(self.runtime, self.issue, self.request)
        self.assertFalse(result['child_tree_gone'])
        self.assertEqual(result['status'], 'uncertain')
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')

    def test_stopped_cancellation_preserves_outcome_and_cannot_replay(self):
        self.process.side_effect = None
        self.process.return_value = dict(status='cancelled', child_tree_gone=True)
        result = worker.execute(self.runtime, self.issue, self.request)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(self.rows()[self.lease()]['outcome'], 'cancelled')
        before = self.events()
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual(self.events(), before)

    def test_stopped_timeout_preserves_outcome_without_claiming_completion(self):
        self.process.side_effect = None
        self.process.return_value = dict(status='timed_out', child_tree_gone=True)
        result = worker.execute(self.runtime, self.issue, self.request)
        self.assertEqual(result['status'], 'timed_out')
        self.assertFalse(result['accepted_delivery'])
        self.assertEqual(self.rows()[self.lease()]['status'], 'failed')
        self.assertEqual(json.loads((self.directory()/'receipt.json').read_text())['status'], 'timed_out')

    def test_process_boundary_exception_persists_uncertainty_and_reservation(self):
        self.process.side_effect = OSError('synthetic process start failure')
        with self.assertRaisesRegex(OSError, 'synthetic process start failure'):
            worker.execute(self.runtime, self.issue, self.request)
        saved = json.loads((self.directory() / 'receipt.json').read_text())
        self.assertEqual(saved, dict(status='uncertain', child_tree_gone=False))
        self.assertEqual(self.rows()[self.lease()]['status'], 'running')
        self.process.reset_mock()
        with self.assertRaisesRegex(AdmissionError, 'no replay'):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()

    def test_intent_without_pool_record_must_not_start_another_process(self):
        self.admit()
        intent = (self.directory() / 'intent.json').read_bytes()
        # Simulate an intact runtime recovered with a fresh/lost pool database.
        self.policy['symphony']['pool_path'] = str(self.root / 'recovered-pool')
        (self.runtime / 'capacity-policy.json').write_text(json.dumps(self.policy))
        with self.assertRaises(AdmissionError):
            worker.execute(self.runtime, self.issue, self.request)
        self.process.assert_not_called()
        self.assertEqual((self.directory() / 'intent.json').read_bytes(), intent)

    def test_finishing_runtime_cannot_release_prefix_or_same_basename_lease(self):
        for relative in ('run-other', 'another-parent/run'):
            with self.subTest(runtime=relative):
                other, manifest = self.make_runtime(relative, 'tests/' + relative + '.py')
                lease = self.admit(other, manifest)
                before = self.rows()[lease]
                # A fresh runtime finishes while the other runtime remains active.
                if relative == 'run-other':
                    selected, selected_manifest = self.runtime, self.manifest
                else:
                    selected, selected_manifest = self.make_runtime(
                        'first-parent/run', 'tests/selected.py')
                result = worker.execute(selected, self.issue, self.request)
                self.assertEqual(result['status'], 'succeeded')
                self.assertEqual(self.rows()[self.lease(selected, selected_manifest)]['status'], 'finished')
                self.assertEqual(self.rows()[lease], before)
                self.assertEqual([event for event in self.events() if event[0] == lease],
                                 [(lease, 'admitted')])
                # Its ownership remains enforced, not merely its status string.
                conflict = copy.deepcopy(before['binding'])
                conflict['task_sha256'] = digest('competing task ' + relative)
                with self.assertRaisesRegex(AdmissionError, 'ownership_conflict'):
                    self.pool().admit('competitor-' + str(len(self.rows())), conflict,
                                      self.proof, worker.host_snapshot(other))

    def test_wrong_branch_fails_before_admission_or_coding(self):
        workspace = self.runtime / 'workspaces' / self.issue
        self.git(workspace, 'switch', '-c', 'feature/unreviewed')
        self.assert_source_rejected()

    def test_committed_out_of_scope_change_is_observed_against_admitted_base(self):
        workspace = self.runtime/'workspaces'/self.issue
        def committed(command,prompt,selected,environment,directory,*args):
            (workspace/'outside.txt').write_text('unexpected committed output\n')
            self.git(workspace,'add','outside.txt')
            self.git(workspace,'commit','-m','Unexpected worker commit')
            return self.completed_process(command,prompt,selected,environment,directory,*args)
        self.process.side_effect = committed
        result = worker.execute(self.runtime,self.issue,self.request)
        self.assertEqual(result['status'],'failed')
        self.assertTrue(result['source_identity_changed'])
        self.assertIn('outside.txt',result['scope_violations'])
        self.assertIn('outside.txt',result['output_sha256'])
        self.assertNotEqual(result['final_head'],result['source_head'])

    def test_branch_change_at_same_head_is_not_success(self):
        workspace = self.runtime/'workspaces'/self.issue
        def switched(command,prompt,selected,environment,directory,*args):
            self.git(workspace,'switch','-c','feature/unselected-final')
            return self.completed_process(command,prompt,selected,environment,directory,*args)
        self.process.side_effect = switched
        result = worker.execute(self.runtime,self.issue,self.request)
        self.assertEqual(result['status'],'failed')
        self.assertEqual(result['final_head'],result['source_head'])
        self.assertTrue(result['source_identity_changed'])
        self.assertEqual(result['final_branch'],'feature/unselected-final')

    def test_changed_head_fails_before_admission_or_coding(self):
        workspace = self.runtime / 'workspaces' / self.issue
        self.git(workspace, 'commit', '--allow-empty', '-m', 'Unselected revision')
        self.assert_source_rejected()

    def assert_source_rejected(self):
        with self.assertRaisesRegex(AdmissionError, 'Source identity changed'):
            worker.execute(self.runtime, self.issue, self.request)
        self.provider.assert_not_called()
        self.process.assert_not_called()
        self.assertFalse(self.directory().exists())
        self.assertFalse(Path(self.policy['symphony']['pool_path']).exists())

    def review_fixture(self):
        """Real author Pool receipt, independent immutable Git candidate."""
        def author(command,prompt,workspace,environment,directory,*args):
            target=workspace/'tests/first.py'; target.parent.mkdir()
            target.write_text('# reviewed output\n')
            self.completed_process(command,prompt,workspace,environment,directory,*args)
            with (directory/'stdout.jsonl').open('a') as stream:
                stream.write(json.dumps(dict(type='thread.started',thread_id='author-session'))+'\n')
            return dict(status='succeeded',child_tree_gone=True,exit_code=0)
        self.process.side_effect=author
        authored=worker.execute(self.runtime,self.issue,self.request)
        self.assertEqual(authored['status'],'succeeded')
        runtime,manifest=self.make_runtime('review','tests/first.py')
        candidate=self.root/'candidate'; candidate.mkdir()
        self.git(candidate,'init','-b',BRANCH)
        target=candidate/'tests/first.py';target.parent.mkdir()
        target.write_text('# reviewed output\n')
        self.git(candidate,'add','.')
        self.git(candidate,'commit','-m','Synthetic accepted candidate')
        files={'tests/first.py':worker.hashlib.sha256(target.read_bytes()).hexdigest()}
        head=self.git(candidate,'rev-parse','HEAD')
        source=dict(root=str(candidate),head=head,base=head,branch=BRANCH,
                    tree=self.git(candidate,'rev-parse','HEAD^{tree}'),outputs=files,files_sha256=digest(files))
        task=manifest['tasks'][self.issue]
        task.update(stage='review',allowed_paths=[],input_paths=['tests/first.py'],
            stage_binding=dict(entry={},identity='a'*64,inputs={}))
        task['resources']['output_bytes']=1024*1024
        task['resources']['memory_bytes']=2*1024**3
        (runtime/'manifest.json').write_text(json.dumps(manifest))
        author_path=self.directory()/'receipt.json'
        policy=dict(schema=worker.REVIEW_ORIGIN,owner='test-owner',reviewer_owner='independent-native-owner',
            project_id=PROJECT_ID,issue=self.issue,stage_identity='a'*64,unit_binding={'fixture':'unit'},
            validation_identity='b'*64,source=source,
            author_receipts=[dict(path=str(author_path),sha256=adapter.file_sha(author_path))],
            excluded_sessions=['author-session'],excluded_owners=['test-owner'],provider='codex-chatgpt',
            model=worker.MODEL,effort='medium',resources=task['resources'],acceptance=task['acceptance'],
            timeout_seconds=5,require_stopped_child=True)
        policy_path=runtime/'native-policy.json';policy_path.write_text(json.dumps(policy));policy_path.chmod(0o600)
        request=dict(kind=worker.REVIEW_ORIGIN,policy=dict(path=str(policy_path),sha256=adapter.file_sha(policy_path)))
        self.process.side_effect=self.review_process
        self.review_policy=policy
        self.process.reset_mock()
        return runtime,manifest,request,policy

    def review_process(self,command,prompt,workspace,environment,directory,*args):
        self.assertEqual(command[command.index('--sandbox')+1],'read-only')
        self.assertIn('untrusted data',prompt)
        (directory/'stdout.jsonl').write_text(
            json.dumps(dict(type='thread.started',thread_id='independent-session'))+'\n'+
            json.dumps(dict(type='turn.completed'))+'\n')
        (directory/'final-message.txt').write_text(json.dumps(dict(schema=worker.REVIEW_ORIGIN,
            source=self.review_policy['source'],verdict='accept',findings=[])))
        return dict(status='succeeded',child_tree_gone=True,exit_code=0)

    def test_native_review_real_lease_distinct_session_immutable_restart(self):
        runtime,manifest,request,policy=self.review_fixture()
        original=(self.directory()/'receipt.json').read_bytes()
        first=worker.execute(runtime,self.issue,request)
        self.assertEqual(first['status'],'succeeded')
        self.assertNotEqual(first['lease'],self.lease())
        row=self.rows()[first['lease']]
        self.assertEqual(row['status'],'finished')
        self.assertEqual(row['binding']['write_roots'],[])
        self.assertEqual(row['binding']['owner'],'independent-native-owner')
        self.assertEqual(worker.execute(runtime,self.issue,request),first)
        self.process.assert_called_once()
        self.assertEqual((self.directory()/'receipt.json').read_bytes(),original)
        self.assertEqual(worker.qualify_review(runtime,self.issue,request),first)
        self.assertNotIn('reviewer',first)
        intent_path=runtime/'attempts'/('review-'+self.issue)/'intent.json'
        typed=json.loads(intent_path.read_text())
        worker.checkpoint(intent_path,{k:typed[k] for k in ('lease','binding','request')})
        self.assertEqual(worker.qualify_review(runtime,self.issue,request),first)
        worker.checkpoint(intent_path,typed)

    def test_native_review_reuses_author_or_changes_source_refused(self):
        for mutation in ('author','source','policy','artifact'):
            # Independent fixture per refusal, no immutable task ID reuse.
            with self.subTest(mutation=mutation):
                self.setUp()
                runtime,manifest,request,policy=self.review_fixture()
                def process(*args):
                    result=self.review_process(*args)
                    directory=args[4]
                    if mutation=='author':
                        events=directory/'stdout.jsonl'
                        events.write_text(events.read_text().replace('independent-session','author-session'))
                    elif mutation=='source':
                        (Path(policy['source']['root'])/'tests/first.py').write_text('tampered')
                    elif mutation=='policy':
                        Path(request['policy']['path']).write_text('{}')
                    else:
                        artifact=directory/'final-message.txt'
                        data=json.loads(artifact.read_text());data['source']['head']='f'*40
                        artifact.write_text(json.dumps(data))
                    return result
                self.process.side_effect=process
                result=worker.execute(runtime,self.issue,request)
                self.assertEqual(result['status'],'failed')
                with self.assertRaises((AdmissionError,KeyError)):
                    worker.qualify_review(runtime,self.issue,request)

    def test_native_review_uncertain_cleanup_retains_lease_and_no_restart(self):
        runtime,manifest,request,policy=self.review_fixture()
        def process(*args):
            result=self.review_process(*args)
            return dict(result,status='uncertain',child_tree_gone=False)
        self.process.side_effect=process
        result=worker.execute(runtime,self.issue,request)
        self.assertEqual(self.rows()[result['lease']]['status'],'running')
        with self.assertRaises(AdmissionError):worker.execute(runtime,self.issue,request)
        self.process.assert_called_once()

    def test_native_review_cancelled_child_retains_until_cleanup(self):
        runtime,manifest,request,policy=self.review_fixture()
        def cancelled(*args):
            self.review_process(*args)
            (runtime/'cancel.json').write_text('{}')
            return dict(status='cancelled',child_tree_gone=False)
        self.process.side_effect=cancelled
        result=worker.execute(runtime,self.issue,request)
        self.assertEqual(self.rows()[result['lease']]['status'],'running')
        with self.assertRaises(AdmissionError):worker.qualify_review(runtime,self.issue,request)
        with self.assertRaises(AdmissionError):worker.execute(runtime,self.issue,request)
        self.process.assert_called_once()

    def test_native_review_intent_unknown_never_acquires_a_second_lease(self):
        runtime,manifest,request,policy=self.review_fixture()
        directory=runtime/'attempts'/('review-'+self.issue);directory.mkdir(parents=True)
        (directory/'intent.json').write_text('{}')
        before=self.events()
        with self.assertRaisesRegex(AdmissionError,'uncertain_launch'):
            worker.execute(runtime,self.issue,request)
        self.process.assert_not_called()
        self.assertEqual(self.events(),before)

    def test_native_review_capacity_refusal_then_same_operation_finite_child(self):
        self.test_native_review_finite_python_child_and_tamper_checks(capacity_defer=True)

    def test_native_review_unknown_admission_outcomes_never_retry(self):
        for outcome in ('admitted-exception','unknown-exception','other-refusal','old-intent',
                        'artifact','inspection-unavailable','row-present','late-artifact','late-row'):
            with self.subTest(outcome=outcome):
                self.setUp()
                runtime,manifest,request,policy=self.review_fixture()
                _,binding,lease=worker.review_contract(runtime,self.issue,request)
                directory=runtime/'attempts'/('review-'+self.issue)
                original=Pool.admit
                def fail(pool,*args):
                    if outcome in ('admitted-exception','row-present'):
                        original(pool,*args)
                    if outcome=='artifact':
                        (directory/'launch.json').write_text('{}')
                    if outcome=='unknown-exception':
                        raise RuntimeError('lost response')
                    raise AdmissionError('capacity_sessions' if outcome in (
                        'artifact','inspection-unavailable','row-present','late-artifact','late-row') else 'unknown')
                if outcome=='old-intent':
                    directory.mkdir(parents=True)
                    worker.checkpoint(directory/'intent.json',dict(lease=lease,binding=binding,request=request))
                else:
                    with patch.object(Pool,'admit',fail):
                        if outcome=='inspection-unavailable':
                            with patch.object(Pool,'status',side_effect=OSError('unavailable')):
                                with self.assertRaises(OSError):worker.execute(runtime,self.issue,request)
                        else:
                            with self.assertRaises((AdmissionError,RuntimeError)):
                                worker.execute(runtime,self.issue,request)
                if outcome=='late-artifact':
                    (directory/'stdout.jsonl').write_text('')
                if outcome=='late-row':
                    original(Pool(self.policy['symphony']['pool_path'],self.policy),
                             lease,binding,self.proof,worker.host_snapshot(runtime))
                raw=(directory/'intent.json').read_bytes()
                with self.assertRaisesRegex(AdmissionError,'uncertain_launch'):
                    worker.execute(runtime,self.issue,request)
                self.assertEqual((directory/'intent.json').read_bytes(),raw)
                self.process.assert_not_called()
                self.assertFalse((directory/'receipt.json').exists())
                if outcome in ('admitted-exception','row-present'):
                    self.assertEqual(self.rows()[lease]['status'],'running')

    def test_native_review_confinement_refusal_records_no_child_and_releases_pool(self):
        runtime, manifest, request, policy = self.review_fixture()
        self.process.side_effect = self.real_supervise
        with patch.object(worker, 'bind_native', side_effect=ValueError('fixture policy absent')):
            result = worker.execute(runtime, self.issue, request)
        self.assertEqual(result['status'], 'failed')
        self.assertEqual(result['launch_classification'], 'confinement-prelaunch-refusal')
        self.assertTrue(result['child_tree_gone'])
        self.assertFalse(result['child_started'])
        self.assertEqual(self.rows()[result['lease']]['status'], 'failed')
        directory = runtime/'attempts'/('review-'+self.issue)
        self.assertTrue((directory/'intent.json').exists())
        self.assertFalse((directory/'stdout.jsonl').exists())
        self.assertIsNone(result['resolved_model'])

    def test_native_review_finite_python_child_and_tamper_checks(self,capacity_defer=False):
        runtime,manifest,request,policy=self.review_fixture()
        artifact=dict(schema=worker.REVIEW_ORIGIN,source=policy['source'],verdict='accept',findings=[])
        def command(workspace,final_message,**kwargs):
            return [sys.executable,'-c',
                'import json,sys; from pathlib import Path; sys.stdin.read(); '
                'print(json.dumps({"type":"thread.started","thread_id":"finite-offline-session"})); '
                'print(json.dumps({"type":"turn.completed"})); '
                'Path(sys.argv[1]).write_text(sys.argv[2])',str(final_message),json.dumps(artifact)]
        with patch.object(worker,'codex_command',side_effect=command):
            # Recover the actual function behind the test process boundary patch.
            self.process.side_effect=self.real_supervise
            if capacity_defer:
                proof_path=runtime/'provider-proof.json'
                original=proof_path.read_bytes()
                proof=json.loads(original);proof['session_ceiling']=1
                proof_path.write_text(json.dumps(proof))
                # Real local Pool occupancy, no manufactured review lease.
                pool=Pool(self.policy['symphony']['pool_path'],self.policy)
                blocker='capacity-blocker'
                _,binding,lease=worker.review_contract(runtime,self.issue,request)
                pool.admit(blocker,binding,self.proof,worker.host_snapshot(runtime))
                before=self.events()
                with self.assertRaisesRegex(AdmissionError,'capacity_sessions'):
                    worker.execute(runtime,self.issue,request)
                self.process.assert_not_called()
                self.assertNotIn(lease,self.rows())
                self.assertEqual(self.events(),before)
                directory=runtime/'attempts'/('review-'+self.issue)
                retained=json.loads((directory/'intent.json').read_text())
                self.assertEqual(retained['phase'],'confirmed-pre-admission-refusal')
                self.assertTrue(worker.confirmed_review_refusal(runtime,self.issue,request))
                pool.finish(blocker,True,'stopped')
                proof_path.write_bytes(original)
            result=worker.execute(runtime,self.issue,request)
            if capacity_defer:
                intent=json.loads((directory/'intent.json').read_text())
                for key in ('lease','binding','request'):self.assertEqual(intent[key],retained[key])
                self.assertEqual(intent['history'][:2],retained['history'])
                self.assertEqual(intent['history'][2:],[{'phase':'admission-pending'},
                    {'phase':'admitted'},{'phase':'spawn-pending'}])
                before=self.events()
                self.assertEqual(worker.execute(runtime,self.issue,request),result)
                self.assertEqual(self.events(),before)
                self.process.assert_called_once()
        self.assertEqual(result['status'],'succeeded')
        self.assertTrue(result['child_tree_gone'])
        directory=runtime/'attempts'/('review-'+self.issue)
        for path in (directory/'receipt.json',directory/'stdout.jsonl',directory/'final-message.txt'):
            original=path.read_bytes();path.write_text('{}')
            with self.assertRaises((AdmissionError,KeyError)):
                worker.qualify_review(runtime,self.issue,request)
            path.write_bytes(original)



@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Run native adapter checks in the pinned Stokowski environment')
class AdapterModelGuard(unittest.TestCase):
    def test_unreviewed_model_or_runner_fails_before_request_or_worker_spawn(self):
        import stokowski.config as config
        import stokowski.linear as linear
        import stokowski.orchestrator as orchestration
        import stokowski.workspace as workspace

        # Restore every upstream adaptation after exercising the real run_turn closure.
        targets = [(config.ProjectConfig, 'agent_env'), (config.ServiceConfig, 'agent_env'),
                   (config.ProjectConfig, 'resolved_api_key'), (config.ServiceConfig, 'resolved_api_key'),
                   (workspace, 'run_hook'), (linear.LinearClient, 'fetch_candidate_issues'),
                   (orchestration, 'ensure_workspace'), (orchestration, 'remove_workspace'),
                   (workspace, 'ensure_workspace'), (workspace, 'remove_workspace'),
                   (orchestration.Orchestrator, 'stop'),
                   (orchestration.Orchestrator, 'start'),
                   (orchestration.Orchestrator, '_safe_transition'),
                   (orchestration.Orchestrator, '_publish_run_report'), (orchestration, 'run_turn')]
        with tempfile.TemporaryDirectory() as temporary, ExitStack() as stack:
            for owner, name in targets:
                stack.enter_context(patch.object(owner, name, getattr(owner, name)))
            spawn = stack.enter_context(patch.object(
                adapter.asyncio, 'create_subprocess_exec', new_callable=AsyncMock))
            runtime = Path(temporary)
            adapted = adapter.install_adapters(runtime, {'tasks': {}, 'project_id':PROJECT_ID}, 'synthetic-key')
            stack.enter_context(patch.object(adapter,'load_manifest',return_value={'tasks':{'UIF-92':{}}}))
            for runner, model in [('codex', 'unapproved-model'), ('claude', worker.MODEL)]:
                with self.subTest(runner=runner, model=model):
                    attempt = SimpleNamespace(turn_count=0)
                    with self.assertRaisesRegex(AdmissionError, 'reviewed existing Codex'):
                        asyncio.run(adapted.run_turn(
                            runner, SimpleNamespace(model=model), SimpleNamespace(),
                            'Offline prompt', runtime, SimpleNamespace(identifier='UIF-92'), attempt))
                    self.assertEqual(attempt.turn_count, 0)
                    self.assertEqual(list(runtime.iterdir()), [])
            spawn.assert_not_called()


if __name__ == '__main__':
    unittest.main()
