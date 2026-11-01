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
import subprocess
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
        # Legacy fixtures never inspect the actual installed host binding.
        self.stack.enter_context(patch.object(adapter,'PROTECTED_OWNER',self.temp/'no-installed-owner'))
        self.source = self.temp/'source'
        self.source.mkdir()
        for name in ('stokowski_adapter.py','stokowski_worker.py','stokowski_prepare.py',
                     'symphony_capacity.py','symphony_tasks.py','symphony_workspace.py',
                     'symphony_codex.py','symphony_protocol.py','windmill_runner.py',
                     'stokowski_operations.py','stokowski_stage.py','stokowski_unit_review.py',
                     'integration-gateway.mjs','capacity-policy.json'):
            target = self.source/'tools/delivery'/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(adapter.SOURCE/'tools/delivery'/name, target)
        target = self.source/'src/offmenu/delivery/integration.py'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(adapter.SOURCE/'src/offmenu/delivery/integration.py', target)
        self.policy = json.loads((self.source/'tools/delivery/capacity-policy.json').read_text())
        self.policy['symphony']['pool_path'] = str(self.temp/'pool')
        self.write(self.source/'tools/delivery/capacity-policy.json', self.policy)
        self.root = (self.source if getattr(self,'successor_real',False) else self.temp)/'.delivery/stokowski'
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

    def test_real_constructor_completed_native_field_and_strict_schema(self):
        config = json.loads((self.runtime/'current.json').read_text())
        proof = self.runtime/'prepared-completed-evidence.json'
        self.write(proof, {'fixture':'owner-selected; no consumption at construction'})
        config['completed_native_validations'] = {'UIF-119':{
            'path':str(proof),'sha256':adapter.file_sha(proof)}}
        def select(value):
            self.write(self.runtime/'current.json', value)
            state = json.loads(json.dumps(self.current.state))
            state['config_sha256'] = adapter.file_sha(self.runtime/'current.json')
            self.write(self.runtime/'current-owner.json', state)
        select(config)
        before = (self.runtime/'current-owner.json').read_bytes()
        observed = adapter.CurrentWork(self.runtime, read_only=True)
        self.assertEqual(observed.config['completed_native_validations'], config['completed_native_validations'])
        self.assertEqual((self.runtime/'current-owner.json').read_bytes(), before)
        for malformed in ([], {'UIF-119':{'path':str(proof),'sha256':'invalid'}},
                          {'foreign':config['completed_native_validations']['UIF-119']}):
            select(dict(config,completed_native_validations=malformed))
            with self.assertRaises(AdmissionError):adapter.CurrentWork(self.runtime,read_only=True)
        select(dict(config,unrecognized_configuration=True))
        with self.assertRaisesRegex(AdmissionError,'current_config_fields'):
            adapter.CurrentWork(self.runtime,read_only=True)
        missing = dict(config);missing.pop('owner');select(missing)
        with self.assertRaisesRegex(AdmissionError,'current_config_fields'):
            adapter.CurrentWork(self.runtime,read_only=True)

    def test_protected_owner_real_constructor_ignores_mutable_config(self):
        protected = self.temp/'protected-owner'
        protected.mkdir()
        cfg = json.loads((self.runtime/'current.json').read_text())
        cfg['catalog'] = str(protected/'catalog.json')
        self.write(protected/'catalog.json', {'version':1, 'entries':[]})
        self.write(protected/'current.json', cfg)
        python = b'synthetic interpreter bytes'
        binding = dict(schema='protected-current-owner-v1', runtime=str(self.runtime),
            config_sha256=adapter.file_sha(protected/'current.json'),
            catalog_sha256=adapter.file_sha(protected/'catalog.json'),
            source_root=str(self.source), python_sha256=hashlib.sha256(python).hexdigest())
        self.write(protected/'binding.json', binding)
        state = json.loads(json.dumps(self.current.state))
        state['config_sha256'] = binding['config_sha256']
        self.write(self.runtime/'current-owner.json', state)
        self.write(self.runtime/'current.json', {'untrusted':'must not be selected'})
        def read(path):
            return python if Path(path) == Path(sys.executable) else Path(path).read_bytes()
        with patch.object(adapter, 'PROTECTED_OWNER', protected), patch.object(
                adapter, 'protected_owner_bytes', side_effect=read), patch.object(
                adapter, 'protected_owner_tree') as closure, patch.dict(
                os.environ, OFFMENU_PROTECTED_OWNER_REQUIRED='1'), patch.object(
                adapter, '_PROTECTED_CLOSURES', set()):
            actual = adapter.CurrentWork(self.runtime, read_only=True)
            self.assertEqual(actual.config, cfg)
            self.assertEqual(actual.config_path, protected/'current.json')
            self.assertEqual(actual.catalog, protected/'catalog.json')
            self.assertEqual(closure.call_count, 2)
            original = (protected/'catalog.json').read_bytes()
            self.write(protected/'catalog.json', {'version':1, 'entries':[{'untrusted':True}]})
            with self.assertRaisesRegex(AdmissionError, 'protected_owner_digest'):
                actual.guard()
            (protected/'catalog.json').write_bytes(original)
            changed = dict(binding, source_root=str(self.temp/'foreign'))
            self.write(protected/'binding.json', changed)
            with self.assertRaisesRegex(AdmissionError, 'protected_owner_binding'):
                actual.guard()

    def test_protected_owner_required_missing_or_wrong_runtime_refuses(self):
        protected = self.temp/'protected-owner'
        protected.mkdir()
        with patch.object(adapter, 'PROTECTED_OWNER', protected), patch.dict(
                os.environ, OFFMENU_PROTECTED_OWNER_REQUIRED='1'):
            with self.assertRaisesRegex(AdmissionError, 'protected_owner_missing'):
                adapter.current_config(self.runtime)
            self.write(protected/'binding.json', dict(schema='protected-current-owner-v1',
                runtime=str(self.temp/'foreign'), config_sha256='a'*64,
                catalog_sha256='b'*64, source_root=str(self.source), python_sha256='c'*64))
            with patch.object(adapter, 'protected_owner_bytes', side_effect=lambda path:Path(path).read_bytes()):
                with self.assertRaisesRegex(AdmissionError, 'protected_owner_runtime'):
                    adapter.current_config(self.runtime)

    def test_protected_granted_catalog_real_constructor_and_rollback(self):
        protected=self.temp/'sealed-owner';protected.mkdir()
        seed=self.catalog.read_bytes();(protected/'catalog.json').write_bytes(seed)
        cfg=json.loads((self.runtime/'current.json').read_bytes())
        future=dict(version=1,entries=[dict(issue='UIF-341',issue_id='00000000-0000-4000-8000-000000000341',
            runtime=str(self.root/'future-341'),admission_sha256='1'*64)])
        cfg['catalog_versions']=[dict(sha256=hashlib.sha256(prepare._publication_bytes(future)).hexdigest(),catalog=future)]
        self.write(protected/'current.json',cfg)
        python=b'synthetic sealed interpreter'
        binding=dict(schema='protected-current-owner-v1',runtime=str(self.runtime),source_root=str(self.source),
            config_sha256=adapter.file_sha(protected/'current.json'),catalog_sha256=hashlib.sha256(seed).hexdigest(),
            python_sha256=hashlib.sha256(python).hexdigest())
        self.write(protected/'binding.json',binding)
        self.current.state['config_sha256']=binding['config_sha256'];self.current.save()
        def read(path):return python if Path(path)==Path(sys.executable) else Path(path).read_bytes()
        with patch.object(adapter,'PROTECTED_OWNER',protected),patch.object(adapter,'protected_owner_bytes',side_effect=read), \
             patch.object(adapter,'protected_owner_tree'),patch.object(adapter,'_PROTECTED_CLOSURES',set()):
            actual=adapter.CurrentWork(self.runtime,read_only=True)
            self.assertEqual(actual.catalog,self.catalog)
            actual.catalog_transition(seed,prepare._publication_bytes(future))
            state=json.loads((self.runtime/'current-owner.json').read_bytes())
            state['bindings']['UIF-341']='2'*64
            self.write(self.runtime/'current-owner.json',state)
            with self.assertRaisesRegex(AdmissionError,'catalog_rollback'):
                adapter.CurrentWork(self.runtime,read_only=True)
            self.catalog.write_text('{"ungranted":true}')
            with self.assertRaisesRegex(AdmissionError,'catalog_snapshot'):
                adapter.current_config(self.runtime)

    def test_protected_owner_file_and_tree_reject_mutable_custody(self):
        # The actual test files are deliberately user-owned, never privileged.
        path = self.temp/'untrusted.json'
        path.write_text('{}')
        path.chmod(0o666)  # Refuse mutable custody regardless of the runner UID.
        with self.assertRaisesRegex(AdmissionError, 'protected_owner_(parent|file)'):
            adapter.protected_owner_bytes(path)
        with self.assertRaisesRegex(AdmissionError, 'protected_owner_closure'):
            adapter.protected_owner_tree(self.temp)
        link = self.temp/'symlink.json'
        link.symlink_to(path)
        with self.assertRaisesRegex(AdmissionError, 'protected_owner_path'):
            adapter.protected_owner_bytes(link)

    def test_protected_review_transport_source_and_catalog_custody(self):
        import stokowski_unit_review as transport
        source = self.temp/'root-source.py'
        catalog = self.temp/'root-catalog.json'
        current = SimpleNamespace(owner_custody={'validated':'root'}, catalog=catalog)
        # Exercise the real transport custody helper with explicit metadata.
        # No chown/root operation is performed by this source-only fixture.
        def info(path):
            return SimpleNamespace(st_uid=0, st_mode=0o100444)
        with patch.object(transport, 'canonical', side_effect=lambda path:Path(path)), patch.object(
                Path, 'stat', autospec=True, side_effect=info):
            transport.control_custody(current, 1000, [source])
            with self.assertRaises(AdmissionError):
                transport.control_custody(SimpleNamespace(owner_custody=None,catalog=catalog),1000,[source])
        with patch.object(transport, 'canonical', side_effect=lambda path:Path(path)), patch.object(
                Path, 'stat', return_value=SimpleNamespace(st_uid=1000,st_mode=0o100600)):
            transport.control_custody(SimpleNamespace(owner_custody=None,catalog=catalog),1000,[source])
            with self.assertRaises(AdmissionError):
                transport.control_custody(current,1000,[source])

    def test_review_transport_interpreter_selected_only_by_fixed_imported_source(self):
        entry=Path(__file__).resolve().parents[2]/'tools/delivery/stokowski_unit_review.py'
        fixed=Path('/opt/offmenu-stokowski-current/source')
        for source in (fixed, self.source, Path(str(fixed)+'-other')):
            with self.subTest(source=source),patch.object(adapter,'SOURCE',source):
                spec=importlib.util.spec_from_file_location('review_interpreter_fixture',entry)
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                expected=(Path('/opt/offmenu-stokowski-current/venv/bin/python') if source==fixed
                    else Path('/home/user/src/offmenu/.delivery/stokowski/venv/bin/python'))
                self.assertEqual(module.PYTHON,expected)

    UIF_ROUTE = dict(project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',
                     project_slug='21558318e036')
    UIF119 = dict(identifier='UIF-119', uuid='3e6839ad-2f22-4ab1-8f6f-973c882daabd',
                  project_id=UIF_ROUTE['project_id'])

    def set_project_route(self, route):
        self.current.config['project_route'] = route
        self.write(self.runtime/'current.json', self.current.config)
        self.current.config_sha = adapter.file_sha(self.runtime/'current.json')
        self.current.state['config_sha256'] = self.current.config_sha
        self.current.save()

    def test_uif_authoritative_candidate_and_wrong_project_refusal(self):
        from stokowski.models import Issue
        issue, runtime = self.qualify(119)
        manifest = json.loads((runtime/'manifest.json').read_text())
        manifest['project_id'] = self.UIF119['project_id']
        manifest['tasks']['UIF-119']['issue_id'] = self.UIF119['uuid']
        self.write(runtime/'manifest.json', manifest)
        admission = json.loads((runtime/'current-admission.json').read_text())
        admission.update(issue_id=self.UIF119['uuid'], manifest_sha256=adapter.file_sha(runtime/'manifest.json'))
        self.write(runtime/'current-admission.json', admission)
        entry = self.entries.pop()
        entry.update(issue_id=self.UIF119['uuid'], admission_sha256=adapter.file_sha(runtime/'current-admission.json'))
        # New admission identity is prepared before catalog consumption.
        self.current.state['bindings'].pop('UIF-119')
        self.current.state['references'].pop('UIF-119')
        self.current.state['tasks'].pop('UIF-119')
        self.entries.append(entry)
        self.set_project_route(self.UIF_ROUTE)
        self.publish()
        issue = Issue(id=self.UIF119['uuid'], identifier='UIF-119', title='Synthetic', state='Todo')
        client = self.client(issue, project=self.UIF119['project_id'])
        self.assertEqual(self.select(issue, client), [issue])
        self.assertEqual(client._graphql.await_count, 1)
        _, linear, fetch = self.adapted()
        fetch.return_value = [issue]
        self.assertEqual(asyncio.run(linear.LinearClient.fetch_candidate_issues(
            client, self.UIF_ROUTE['project_slug'], ['Todo'])), [issue])
        fetch.assert_awaited_once_with(client, self.UIF_ROUTE['project_slug'], ['Todo', 'In Progress'])
        with self.assertRaisesRegex(AdmissionError, 'Wrong Linear project'):
            asyncio.run(linear.LinearClient.fetch_candidate_issues(client, adapter.SLUG, ['Todo']))
        self.assertEqual(self.select(issue, self.client(issue)), [])
        substituted = Issue(id='00000000-0000-4000-8000-000000000119', identifier='UIF-119', title='Wrong UUID', state='Todo')
        self.assertEqual(self.select(substituted, client), [])
        self.set_project_route(dict(project_id=adapter.PROJECT, project_slug=adapter.SLUG))
        self.assertEqual(self.select(issue, client), [])

    def test_uif_successor_preserves_offmenu106_trigger(self):
        f, issue, original, owner, client, review, journal, key = self.successor_fixture()
        frozen = {p:p.read_bytes() for p in original.rglob('*') if p.is_file()}
        # Neither an unselected UIF project nor the handled trigger may become
        # a successor, even when the owner/source references otherwise match.
        for outcome in (self.UIF119, dict(identifier=issue.identifier, uuid=issue.id, project_id=adapter.PROJECT)):
            with self.subTest(outcome=outcome), self.assertRaisesRegex(AdmissionError, 'successor_identity_collision'):
                self.current.qualify_successor(f.ref(f.handoff_path), dict(f.packet, execution_outcome=outcome), f.config)
        self.set_project_route(self.UIF_ROUTE)
        with self.assertRaisesRegex(AdmissionError, 'successor_identity_collision'):
            self.current.qualify_successor(f.ref(f.handoff_path), f.packet, f.config)
        self.current.state.pop('successor_request')
        # Rebuild only synthetic successor inputs with the actual UIF identity.
        f.manifest['tasks']['UIF-106'] = f.manifest['tasks'].pop('UIF-231')
        f.bind_successor(self.current, review, outcome=self.UIF119)
        self.assertEqual(self.current.state.get('successor_request', {}).get('status'), 'pending', self.current.state.get('successor_hold'))
        self.assertEqual(f.publish()['status'], 'published')
        self.assertEqual(f.publish()['status'], 'duplicate')
        self.current.refresh()
        self.assertEqual(self.current.gate_binding(issue)['project_id'], adapter.PROJECT)
        self.assertEqual({p:p.read_bytes() for p in original.rglob('*') if p.is_file()}, frozen)
        from stokowski.models import Issue
        candidate = Issue(id=self.UIF119['uuid'], identifier='UIF-119', title='Synthetic', state='Todo')
        self.assertEqual(self.select(candidate, self.client(candidate, project=self.UIF119['project_id'])), [candidate])
        self.assertEqual(json.loads((f.runtime/'manifest.json').read_text())['project_id'], self.UIF119['project_id'])
        f.provider.assert_called_once()

    def test_finite_uif_candidates_require_exact_slug_and_fresh_project(self):
        from stokowski.models import Issue
        issue = Issue(id=self.UIF119['uuid'], identifier='UIF-119', title='Synthetic', state='Todo')
        manifest = dict(project_id=self.UIF_ROUTE['project_id'], tasks={
            'UIF-119':dict(issue_id=self.UIF119['uuid'])})
        _, linear, fetch = self.adapted(current=False, manifest=manifest)
        fetch.return_value = [issue]
        client = self.client(issue, project=self.UIF_ROUTE['project_id'])
        def select(client, slug=self.UIF_ROUTE['project_slug']):
            return asyncio.run(linear.LinearClient.fetch_candidate_issues(client, slug, ['Todo']))
        self.assertEqual(select(client), [issue])
        with self.assertRaisesRegex(AdmissionError, 'finite_authoritative_identity_or_state'):
            select(self.client(issue))
        with self.assertRaisesRegex(AdmissionError, 'Wrong Linear project'):
            select(client, adapter.SLUG)

    def test_selected_route_pairs_fail_closed(self):
        for route in (None, self.UIF_ROUTE['project_id'],
                      dict(project_id=self.UIF_ROUTE['project_id'], project_slug=adapter.SLUG),
                      dict(project_id=adapter.PROJECT, project_slug=self.UIF_ROUTE['project_slug']),
                      dict(project_id='foreign', project_slug='foreign'),
                      dict(self.UIF_ROUTE, owner='unqualified')):
            with self.subTest(route=route):
                self.set_project_route(route)
                with self.assertRaises(AdmissionError):
                    adapter.CurrentWork(self.runtime, read_only=True)

    def test_explicit_current_preparation_consumes_exact_project_route(self):
        runtime = self.root/'uif-current'
        argv = ['prepare', '--current', '--runtime', str(runtime), '--runtime-root', str(self.root),
                '--catalog', str(self.catalog), '--owner', 'existing-owner',
                '--project-id', self.UIF_ROUTE['project_id']]
        with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()) as output:
            prepare.main()
        config = json.loads((runtime/'current.json').read_text())
        workflow = json.loads((runtime/'workflow.yaml').read_text())
        self.assertEqual(config['project_route'], self.UIF_ROUTE)
        self.assertEqual(workflow['tracker']['project_slug'], self.UIF_ROUTE['project_slug'])
        self.assertEqual(json.loads(output.getvalue())['project_id'], self.UIF_ROUTE['project_id'])
        self.assertEqual(adapter.CurrentWork(runtime).route, self.UIF_ROUTE)
        self.assertNotIn('project_route', json.loads((self.runtime/'current.json').read_text()))
        self.assertEqual(self.current.route, dict(project_id=adapter.PROJECT, project_slug=adapter.SLUG))
        argv[-1] = 'foreign'
        with patch.object(sys, 'argv', argv), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            prepare.main()

    def test_finite_preparation_derives_uif_route_from_manifest(self):
        issue, task_runtime = self.qualify(119)
        manifest = json.loads((task_runtime/'manifest.json').read_text())
        manifest.update(project_id=self.UIF_ROUTE['project_id'], base_revision='a'*40)
        manifest['tasks']['UIF-119']['issue_id'] = self.UIF119['uuid']
        self.write(self.temp/'manifest.json', manifest)
        (self.temp/'prompt.md').write_text('Synthetic only')
        runtime = self.source/'.delivery/stokowski/finite-uif'
        runtime.parent.mkdir(parents=True, exist_ok=True)
        self.write(runtime.parent/'installation.json', self.installation)
        argv = ['prepare', '--runtime', str(runtime), '--manifest', str(self.temp/'manifest.json'),
                '--prompt', str(self.temp/'prompt.md')]
        with patch.object(sys, 'argv', argv), redirect_stdout(io.StringIO()):
            prepare.main()
        self.assertEqual(json.loads((runtime/'workflow.yaml').read_text())['tracker']['project_slug'], self.UIF_ROUTE['project_slug'])
        self.assertEqual(json.loads((runtime/'manifest.json').read_text()), manifest)
        with patch.object(sys, 'argv', argv+['--project-id', adapter.PROJECT]), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            prepare.main()

    def test_uif_source_only_qualification_has_no_native_attempt_or_job(self):
        from test_stokowski_nonimplementation_stage import ReviewedSourceTests
        from stokowski.models import Issue
        c = ReviewedSourceTests(methodName='runTest')
        c.setUp()
        self.addCleanup(c.doCleanups)
        _, original, _, journal, key, spec, remote, factory = c.new_fixture(
            issue_name='UIF-119', issue_id=self.UIF119['uuid'])
        _, runtime = c.qualify(119)
        manifest = json.loads((runtime/'manifest.json').read_text())
        task = dict(c.stage_task, issue_id=self.UIF119['uuid'])
        manifest.update(project_id=self.UIF_ROUTE['project_id'], tasks={'UIF-119':task})
        c.write(runtime/'manifest.json', manifest)
        admission = json.loads((runtime/'current-admission.json').read_text())
        admission.update(issue_id=self.UIF119['uuid'], inputs=task['stage_binding']['inputs'],
                         manifest_sha256=adapter.file_sha(runtime/'manifest.json'))
        c.write(runtime/'current-admission.json', admission)
        entry = c.entries[-1]
        entry.update(issue_id=self.UIF119['uuid'], admission_sha256=adapter.file_sha(runtime/'current-admission.json'))
        c.current.state['bindings'].pop('UIF-119')
        c.current.state['references'].pop('UIF-119')
        c.current.state['tasks'].pop('UIF-119')
        CurrentDispatchTests.set_project_route(c, self.UIF_ROUTE)
        c.publish()
        issue = Issue(id=self.UIF119['uuid'], identifier='UIF-119', title='Synthetic source', state='Todo')
        binding = c.current.gate_binding(issue)
        self.assertEqual(binding['project_id'], self.UIF_ROUTE['project_id'])
        self.assertEqual(binding['issue_id'], self.UIF119['uuid'])
        self.assertEqual(binding['origin'], 'reviewed-source-v1')
        self.assertNotIn('native_receipt_sha256', binding)
        self.assertFalse((original/'attempts').exists())
        self.assertEqual(list((runtime/'attempts').iterdir()), [])
        self.assertEqual(journal.read(key)[1]['status'], 'prepared')
        remote.submit.assert_not_awaited()
        factory.assert_not_called()

    def test_missing_successor_route_regression(self):
        # A terminal unit alone must never infer a backlog successor. The
        # explicit owner-qualified boundary must exist on the consumed adapter.
        self.assertTrue(callable(getattr(self.current, '_successor_boundary', None)),
                        'MISSING_QUALIFIED_SUCCESSOR_BOUNDARY')

    def successor_fixture(self, real=False, fault=None):
        from test_stokowski_prepare_publication import PublicationTests
        from symphony_capacity import digest
        if real:
            original = Path(__file__).resolve().parents[2]
            shutil.copytree(original/'tools/delivery',self.source/'tools/delivery',dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__'), copy_function=self.copy_fixture_source)
            shutil.copytree(original/'src',self.source/'src',dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns('__pycache__'), copy_function=self.copy_fixture_source)
            self.write(self.source/'tools/delivery/capacity-policy.json',self.policy)
            # Only this temporary, committed fixture replaces the provider.
            launch = self.source/'tools/delivery/symphony_launch.py'
            code = launch.read_text()
            a,b = code.index('def provider_proof('),code.index('\ndef default_manifest(')
            code = code[:a]+"""def provider_proof(model, ceiling):
    marker=SOURCE/'.delivery/provider-calls'
    marker.write_text(marker.read_text()+'x' if marker.exists() else 'x')
    return dict(route='codex-chatgpt',available=True,checked_at=time.time(),requested_model=model,session_ceiling=ceiling)
"""+code[b:]
            if fault == 'uncertain':
                code = code.replace("    return dict(route='codex-chatgpt',available=True,checked_at=time.time(),requested_model=model,session_ceiling=ceiling)",
                                    "    raise OSError('synthetic uncertainty')")
            launch.write_text(code)
            (self.source/'.gitignore').write_text('.delivery/\n__pycache__/\n')
            (self.source/'package.json').write_text('{"type":"module"}')
            def git(path,*args):
                return subprocess.run(['/usr/bin/git','-C',str(path),*args],check=True,
                    stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True).stdout.strip()
            def commit(path):
                git(path,'init','-b','feature/test-current')
                git(path,'add','.')
                git(path,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    '-c','commit.gpgsign=false','commit','-m','Temporary synthetic source')
                return git(path,'rev-parse','HEAD')
            source_head = commit(self.source)
            checkout = self.temp/'checkout-106'
            checkout.mkdir()
            (checkout/'fixture.txt').write_text('synthetic original')
            self.task_head = commit(checkout)
            self.git.side_effect = lambda args,**kw: subprocess.run(args,check=True,
                stdout=subprocess.PIPE,**dict({'stderr':subprocess.PIPE},**kw)).stdout
            config = self.current.config
            config['source_head'] = source_head
            config['source_sha256'] = {str(p.relative_to(self.source)):adapter.file_sha(p)
                for p in (self.source/'tools/delivery').glob('*') if p.suffix in ('.py','.mjs')}
            self.write(self.runtime/'current.json',config)
            self.current.config_sha = adapter.file_sha(self.runtime/'current.json')
            self.current.state['config_sha256'] = self.current.config_sha
            self.current.save()
        issue,runtime,owner,client,review,journal,key = self.review_fixture(106)
        self.current.unit_review_writer(lambda envelope:review)({k:review[k] for k in ('snapshot','decision')})
        self.current.refresh()
        asyncio.run(owner._handle_gate_responses())
        f = PublicationTests()
        f.setUp()
        # Remove fixture-only patches before exercising actual adapter code.
        for function,args,kwargs in reversed(f._cleanups):
            if getattr(function,'__name__','') == '__exit__':
                function(*args,**kwargs)
        f._cleanups = [item for item in f._cleanups if getattr(item[0],'__name__','') != '__exit__']
        self.addCleanup(f.doCleanups)
        f.bind_successor(self.current,review)
        return f,issue,runtime,owner,client,review,journal,key

    def test_successor_pending_once_and_reopen(self):
        f,*_ = self.successor_fixture()
        pending = dict(self.current.state['successor_request'])
        self.assertEqual(pending['status'],'pending')
        self.current.refresh()
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(reopened.state['successor_request'],pending)
        self.assertEqual(len(json.loads(self.catalog.read_text())['entries']),1)
        f.provider.assert_not_called()

    def test_successor_trigger_drift_cancel_uncertain_and_rework_held(self):
        f,issue,runtime,owner,client,review,journal,key = self.successor_fixture()
        pending = dict(self.current.state['successor_request'])
        _,state = journal.read(key)
        for delta in ({'cancel_requested':True},{'status':'unknown'},{'reconcile_required':True}):
            journal.save(key,dict(state,**delta),'synthetic hold')
            self.current.refresh()
            self.assertEqual(self.current.state['successor_request']['status'],'held')
            self.assertEqual(self.current.state['successor_request']['identity'],pending['identity'])
        journal.save(key,state,'synthetic restore')
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        gate['disposition']='rework'
        self.current.refresh()
        self.assertEqual(self.current.state['successor_request']['status'],'held')
        f.provider.assert_not_called()

    def test_successor_qualified_publication_uses_existing_producer(self):
        f,*_ = self.successor_fixture()
        frozen = {p:p.read_bytes() for p in (self.root/'task-106').rglob('*') if p.is_file()}
        result = f.publish()
        self.assertEqual(result['status'],'published')
        f.provider.assert_called_once()
        self.current.refresh()
        self.assertIn('UIF-231',self.current.entries)
        for path,raw in frozen.items():
            self.assertEqual(path.read_bytes(),raw)

    def test_successor_provider_interleaving_refuses_changed_terminal_trigger(self):
        f,issue,runtime,owner,client,review,journal,key = self.successor_fixture()
        _,state = journal.read(key)
        proof = f.provider.side_effect
        def interleave(*args):
            # The provider can need the same lock as tick/cancel. It must be
            # available during the callback, then authoritative at exposure.
            with journal.claim(key):
                journal.save(key,dict(state,cancel_requested=True),'synthetic-provider-cancel')
            return proof(*args)
        f.provider.side_effect = interleave
        with self.assertRaises(AdmissionError):
            f.publish()
        self.assertEqual(self.catalog.read_bytes(),f.catalog_before)
        self.assertTrue(journal.read(key)[1]['cancel_requested'])
        f.provider.assert_called_once()

    def test_successor_final_claim_contention_and_exposure_serialization(self):
        from stokowski_operations import OperationError
        f,issue,runtime,owner,client,review,journal,key = self.successor_fixture()
        before = journal.path.read_bytes()
        with journal.claim(key):
            with self.assertRaisesRegex(OperationError,'already owned'):
                f.publish()
        self.assertEqual(self.catalog.read_bytes(),f.catalog_before)
        f.provider.assert_called_once()
        write = prepare._publication_write
        exposures = []
        def expose(path,content):
            if path == self.catalog:
                # A competing authoritative writer cannot acquire the original
                # claim between final qualification and actionable visibility.
                with self.assertRaisesRegex(OperationError,'already owned'):
                    with journal.claim(key):
                        self.fail('original claim released before exposure')
                exposures.append(path)
            return write(path,content)
        with patch.object(prepare,'_publication_write',side_effect=expose):
            self.assertEqual(f.publish()['status'],'published')
        self.assertEqual(exposures,[self.catalog])
        f.provider.assert_called_once()  # Recovery uses the retained plan.
        self.assertEqual(journal.path.read_bytes(),before)
        with journal.claim(key):
            pass

    def test_successor_published_duplicate_reconciles_after_trigger_changes(self):
        f,issue,runtime,owner,client,review,journal,key = self.successor_fixture()
        self.assertEqual(f.publish()['status'],'published')
        _,state = journal.read(key)
        with journal.claim(key):
            journal.save(key,dict(state,reconcile_required=True),'synthetic-later-hold')
            before = journal.path.read_bytes()
            self.assertEqual(f.publish()['status'],'duplicate')
        self.assertEqual(journal.path.read_bytes(),before)
        f.provider.assert_called_once()

    def test_successor_native_worker_normal_admission_once_and_capacity_hold(self):
        self.successor_native_worker_admission()

    def test_successor_native_worker_uncertain_lease_held_without_replay(self):
        self.successor_native_worker_admission(uncertain=True)

    def successor_native_worker_admission(self, uncertain=False):
        from contextlib import nullcontext
        from stokowski.models import Issue
        from symphony_capacity import Pool, digest
        import stokowski_worker as worker
        f,_,predecessor,*_ = self.successor_fixture(real=True)
        before = {p:p.read_bytes() for p in predecessor.rglob('*') if p.is_file()}
        self.assertEqual(f.publish()['status'],'published')
        self.current.refresh()
        issue = Issue(id=f.issue['uuid'],identifier='UIF-231',title='Synthetic successor',state='Todo')
        self.assertEqual(self.select(issue),[issue])
        workspace = f.runtime/'workspaces'/issue.identifier
        subprocess.run(['/usr/bin/git','clone','--local',str(self.source),str(workspace)],
                       check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        request = json.loads((f.runtime/'requests/UIF-231.json').read_text())
        manifest = json.loads((f.runtime/'manifest.json').read_text())
        pool = Pool(self.policy['symphony']['pool_path'],self.policy)
        proof = json.loads((f.runtime/'provider-proof.json').read_text())
        blocker = dict(branch=manifest['branch'],head=manifest['base_revision'],owner='fixture-blocker',
            write_roots=['tests/unrelated.py'],resources=manifest['tasks']['UIF-231']['resources'],
            task_sha256=digest({'synthetic':'blocker'}))
        host = dict(cpu_millis=64000,available_memory_bytes=10**12,available_disk_bytes=10**12)
        pool.admit('synthetic-blocker',blocker,dict(proof,session_ceiling=1),host)
        # Same real pool, exhausted session ceiling: no successor intent/lease.
        with patch.object(worker,'host_snapshot',return_value=host), \
             patch.object(worker,'supervise',side_effect=AssertionError('capacity must hold')):
            self.write(f.runtime/'provider-proof.json',dict(proof,session_ceiling=1))
            with self.assertRaisesRegex(AdmissionError,'capacity_sessions'):
                worker.execute(f.runtime,issue.identifier,request)
        self.assertEqual(len(pool.status()),1)
        pool.finish('synthetic-blocker',True,'stopped')
        self.write(f.runtime/'provider-proof.json',proof)
        def complete(command,prompt,path,environment,directory,*args):
            self.assertEqual(prompt,request['prompt'])
            (directory/'stdout.jsonl').write_text(json.dumps(dict(type='turn.completed'))+'\n')
            return dict(status='uncertain' if uncertain else 'succeeded',
                        child_tree_gone=not uncertain,exit_code=0)
        native,_,_ = self.adapted()
        async def spawn(*args,**kwargs):
            worker.execute(f.runtime,issue.identifier,request)
            return SimpleNamespace(pid=98765,returncode=0,communicate=AsyncMock())
        with patch.object(worker,'host_snapshot',return_value=host), \
             patch.object(worker.os,'sched_setaffinity'), \
             patch.object(worker,'isolated_codex_environment',return_value=nullcontext({})), \
             patch.object(worker,'supervise',side_effect=complete) as computation, \
             patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=spawn) as spawned:
            self.assertEqual(asyncio.run(self.turn(native,issue,f.runtime)).status,
                             'failed' if uncertain else 'succeeded')
            reopened = adapter.CurrentWork(self.runtime)
            self.assertEqual(asyncio.run(reopened.candidates(self.client(issue),[issue])),[])
            with self.assertRaises(AdmissionError):
                asyncio.run(self.turn(native,issue,f.runtime))
            with self.assertRaisesRegex(AdmissionError,'no replay'):
                worker.execute(f.runtime,issue.identifier,request)
        computation.assert_called_once()
        spawned.assert_called_once()
        lease = runtime_lease_ids(f.runtime,manifest)[issue.identifier]
        self.assertEqual({r['id']:r['status'] for r in pool.status()}[lease],
                         'running' if uncertain else 'finished')
        with pool._transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE id=? AND event='admitted'",(lease,)).fetchone()[0],1)
        for path,raw in before.items():
            self.assertEqual(path.read_bytes(),raw)

    def test_successor_scope_overlap_and_exact_handoff_allowlist(self):
        f,*_ = self.successor_fixture()
        # Even a freshly pinned packet cannot appoint itself as the successor.
        f.packet['scope'] = ['tests/task106.py']
        f.manifest['tasks']['UIF-231']['allowed_paths'] = f.packet['scope']
        f.write(f.qualified/'manifest.json', f.manifest)
        f.repin()
        self.current.refresh()
        self.assertEqual(self.current.state['successor_request']['status'],'held')
        with self.assertRaises(AdmissionError):
            f.publish()
        # Independently qualify the overlapping handoff out of band in fixture
        # configuration. Scope admission still refuses it at the boundary.
        config = dict(self.current.config,qualified_successor=f.ref(f.handoff_path))
        self.write(self.runtime/'current.json',config)
        self.current.config=config
        self.current.config_sha=adapter.file_sha(self.runtime/'current.json')
        self.current.state['config_sha256']=self.current.config_sha
        self.current.state.pop('successor_request')
        self.current.save()
        self.current.refresh()
        self.assertNotIn('successor_request',self.current.state)
        self.assertIn('successor_scope_overlap',self.current.state['successor_hold'])
        f.provider.assert_not_called()

    def test_shared_fixture_producer_full_review_closure(self):
        from stokowski_unit_review import REQUIRED
        pins = self.current.config['source_sha256']
        self.assertEqual(len(pins), 14)
        self.assertTrue(REQUIRED.issubset(pins))
        self.assertIn('src/offmenu/delivery/integration.py', pins)
        for name, sha in pins.items():
            self.assertEqual(adapter.file_sha(self.source/name), sha)
        self.current.guard()
        for name in REQUIRED:
            target = self.source/name
            raw = target.read_bytes()
            try:
                target.write_bytes(raw+b'\n# SYNTHETIC source drift\n')
                with self.subTest(source=name), self.assertRaisesRegex(AdmissionError,'current_source_drift'):
                    self.current.guard()
            finally:
                target.write_bytes(raw)
        original_git = self.git.side_effect
        self.git.side_effect = lambda args, **kw: (
            b'SYNTHETIC different accepted blob' if args[3] == 'show' and
            args[-1].endswith(':tools/delivery/stokowski_stage.py') else original_git(args,**kw))
        with self.assertRaisesRegex(AdmissionError,'current_source_not_reviewed_revision'):
            self.current.guard()

    @staticmethod
    def copy_fixture_source(source, destination):
        # The service mirror deliberately has read-only files. These copies
        # belong to a mutable synthetic fixture, including its private policy.
        copied = shutil.copy2(source, destination)
        path = Path(copied)
        path.chmod(path.stat().st_mode | 0o200)
        if path.name == 'integration-gateway.mjs':
            # Pin the selected fixture interpreter before committing synthetic
            # source; the service host's fixed interpreter is absent in jails.
            code = path.read_text()
            original = "const reviewPython = '/home/user/src/offmenu/.delivery/stokowski/venv/bin/python';"
            assert code.count(original) == 1
            path.write_text(code.replace(original, f'const reviewPython = {json.dumps(sys.executable)};'))
        elif path.name == 'stokowski_unit_review.py':
            code = path.read_text()
            original = "Path('/home/user/src/offmenu/.delivery/stokowski/venv/bin/python')"
            assert code.count(original) == 1
            path.write_text(code.replace(original, f'Path({sys.executable!r})'))
        elif path.name == 'stokowski_adapter.py':
            # Child processes need the same installed-owner isolation as setUp.
            code = path.read_text()
            original = "PROTECTED_OWNER = Path('/etc/offmenu-stokowski-current')"
            assert code.count(original) == 1
            path.write_text(code.replace(original,
                "PROTECTED_OWNER = SOURCE/'.delivery/no-installed-owner'"))
        return copied

    def write(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))

    def intake_fixture(self, decision='qualification-only'):
        from stokowski.models import Issue
        issue = Issue(id='00000000-0000-4000-8000-000000000341', identifier='UIF-341',
                      title='Controlled uncatalogued issue', state='Todo')
        workspace = self.root/'qualification-341'
        workspace.mkdir()
        spec = dict(workspace=str(workspace), branch='feature/test-current', head='a'*40,
            prompt='Propose acceptance gaps only. Return the declared proposal JSON.',
            resources=self.policy['symphony']['default_resources'], output='qualification-output.json')
        self.write(self.root/'qualification-spec.json', spec)
        ref = lambda path:dict(path=str(path), sha256=adapter.file_sha(path))
        authority = dict(schema='offmenu-intake-authority/1', owner=self.current.config['owner'],
            source_head='a'*40, issue=issue.identifier, issue_id=issue.id, project_id=adapter.PROJECT,
            accepted_scope=['tests/finite-task.py'], acceptance=['Owner accepted bounded scope'],
            dependencies=[], decision=decision, handoff=None, qualification=ref(self.root/'qualification-spec.json'))
        self.write(self.root/'intake-authority.json', authority)
        policy = dict(schema='offmenu-normal-intake/1', enabled=True, owner=authority['owner'],
            source_head='a'*40, project_route=self.current.route, expires_at=time.time()+300,
            references={'owner/finite-341':ref(self.root/'intake-authority.json')},
            resources=spec['resources'], timeout_seconds=5)
        self.write(self.root/'intake-policy.json', policy)
        module = 'tools/delivery/symphony_launch.py'
        shutil.copyfile(Path(adapter.__file__).resolve().parents[2]/module, self.source/module)
        self.current.config['source_sha256'][module] = adapter.file_sha(self.source/module)
        self.current.config['normal_intake'] = ref(self.root/'intake-policy.json')
        self.write(self.runtime/'current.json', self.current.config)
        self.current.config_sha = adapter.file_sha(self.runtime/'current.json')
        self.current.state['config_sha256'] = self.current.config_sha
        self.current.save()
        client = self.client(issue)
        remote = client._graphql.return_value['issue']
        remote.update(description='```offmenu-intake\n'+json.dumps(dict(
            schema='offmenu-intake-reference/1', reference='owner/finite-341'))+'\n```',
            inverseRelations=dict(nodes=[]))
        return issue, client, authority, spec

    def test_native_poll_uncatalogued_missing_reference_is_actionable(self):
        issue, client, _, _ = self.intake_fixture()
        client._graphql.return_value['issue']['description'] = 'Assignment is not authority'
        native, linear, fetch = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        self.assertEqual(owner._load_workflow(), [])
        owner._linear = client
        client.fetch_candidate_issues = lambda *args:linear.LinearClient.fetch_candidate_issues(client,*args)
        for name in ('_reconcile','_handle_gate_responses','_evict_terminal_gates'):
            self.stack.enter_context(patch.object(owner,name,new_callable=AsyncMock))
        owner._dispatch = unittest.mock.Mock()
        fetch.return_value = [issue]
        asyncio.run(owner._tick())
        owner._dispatch.assert_not_called()
        held = adapter.read_record(self.current.state_path)['intake'][issue.identifier]
        self.assertEqual(held['status'], 'held')
        self.assertIn('intake_reference_missing', held['reason'])
        self.assertEqual(held['required_actor'], self.current.config['owner'])

    def test_intake_authority_and_fresh_dependency_drift_never_launch(self):
        issue, client, authority, _ = self.intake_fixture()
        remote = client._graphql.return_value['issue']
        with patch.object(adapter.subprocess, 'Popen') as launch:
            for field, value in (('owner', 'foreign'), ('source_head', 'd'*40),
                                 ('issue_id', 'foreign'), ('accepted_scope', []), ('acceptance', [])):
                changed = dict(authority, **{field:value})
                self.write(self.root/'intake-authority.json', changed)
                self.assertEqual(self.select(issue, client), [])
                self.assertEqual(self.current.state['intake'][issue.identifier]['status'], 'held')
            self.write(self.root/'intake-authority.json', authority)
            remote['inverseRelations']['nodes'] = [dict(type='blocks', issue=dict(id='dependency',state=dict(name='Todo')))]
            self.assertEqual(self.select(issue, client), [])
            self.assertIn('dependency_drift', self.current.state['intake'][issue.identifier]['reason'])
            remote['inverseRelations']['nodes'] = []
            remote['project']['id'] = 'foreign'
            self.assertEqual(self.select(issue, client), [])
            launch.assert_not_called()

    def test_native_qualification_intent_once_readonly_proposal_no_approval(self):
        self.controlled_qualification()

    def test_native_qualification_unknown_cleanup_retains_lease_and_blocks_retry(self):
        self.controlled_qualification(uncertain=True)

    def controlled_qualification(self, uncertain=False):
        issue, client, authority, spec = self.intake_fixture()
        import stokowski_worker as worker
        with patch.object(adapter.subprocess, 'Popen') as launch:
            launch.return_value.pid = 12345
            self.assertEqual(self.select(issue, client), [])
            self.assertEqual(self.select(issue, client), [])
            launch.assert_called_once()
        commands = []
        def supervised(command, prompt, workspace, environment, directory, timeout, resources, ceiling):
            commands.append(command)
            self.write(workspace/'qualification-output.json', dict(
                schema='offmenu-qualification-proposal/1', proposal='Owner must supply plan', missing_inputs=['plan']))
            (directory/'stdout.jsonl').write_text(json.dumps(dict(type='thread.started',thread_id='fake-session'))+'\n')
            return dict(status='uncertain' if uncertain else 'succeeded', child_tree_gone=not uncertain)
        from contextlib import contextmanager
        @contextmanager
        def isolated(environment, directory):
            yield environment
        host = dict(cpu_millis=64000, available_memory_bytes=128*1024**3, available_disk_bytes=1024**4)
        with patch.object(worker,'supervise',side_effect=supervised), \
             patch.object(worker,'git',side_effect=lambda root,*args:'a'*40 if args[0]=='rev-parse' else spec['branch']), \
             patch.object(worker,'changed_paths',return_value=[]), \
             patch('symphony_codex.isolated_codex_environment',isolated), \
             patch('symphony_capacity.host_snapshot',return_value=host), \
             patch('symphony_launch.provider_proof',return_value=dict(route='codex-chatgpt', available=True,
                checked_at=time.time(), session_ceiling=8)) as provider:
            result = adapter.qualification_child(self.runtime, 'owner/finite-341')
            self.assertEqual(result['origin'], 'native-qualification')
            self.assertEqual(result['session_id'], 'fake-session')
            self.assertFalse(result['accepted_delivery'])
            from symphony_capacity import Pool
            rows = Pool(self.policy['symphony']['pool_path'],self.policy).status()
            self.assertEqual(next(r['status'] for r in rows if r['id']==result['lease']),
                             'running' if uncertain else 'finished')
            self.assertEqual(commands[0][commands[0].index('--sandbox')+1], 'read-only')
            with self.assertRaises(AdmissionError):adapter.qualification_child(self.runtime, 'owner/finite-341')
            provider.assert_called_once()
        self.assertNotIn('successor_request', self.current.state)
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(asyncio.run(reopened.candidates(client,[issue])), [])
        self.assertIn('requires_owner_handoff', reopened.state['intake'][issue.identifier]['reason'])

    def test_rearm_refuses_nonterminal_request_and_preserves_original(self):
        f, *_ = self.successor_fixture()
        original = json.loads(json.dumps(self.current.state['successor_request']))
        for status in ('held', 'uncertain', 'refused', 'pending', 'cancel_requested'):
            pending = dict(original, status=status)
            self.current.state['successor_request'] = pending
            with self.assertRaisesRegex(AdmissionError, 'successor_request_rebind'):
                self.current._rearm_successor(pending)
            self.assertEqual(self.current.state['successor_request'], pending)
            self.assertNotIn('successor_history', self.current.state)
        pending = dict(original, status='published')
        self.current.state['successor_request'] = pending
        with self.assertRaisesRegex(AdmissionError, 'prior_unit_unreconciled'):
            self.current._rearm_successor(pending)
        self.assertEqual(self.current.state['successor_request'], pending)

    def git_read(self, args, **kwargs):
        if args[3] == 'merge-base':
            if args[4:] == ['--is-ancestor', 'b'*40, 'c'*40]:
                return ''
            raise subprocess.CalledProcessError(1, args)
        if args[3] == 'show':
            head, name = args[4].split(':',1)
            if head == 'c'*40:
                try:
                    return self.candidate_objects[name]
                except KeyError:
                    raise subprocess.CalledProcessError(128, args)
            if head != 'a'*40:
                raise subprocess.CalledProcessError(128, args)
            return (self.source/name).read_bytes()
        if args[-2:] == ['branch','--show-current']:
            return ('feature/test-current' if args[2] == str(self.source) else getattr(self,'task_branch','feature/test-current'))+'\n'
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
            'branch':getattr(self,'task_branch','feature/test-current'),'base_revision':getattr(self,'task_head','b'*40),'tasks':{issue.identifier:{
                'issue_id':issue.id,'owner':'existing-owner','purpose':'test fixture',
                'allowed_paths':[f'tests/task{number}.py'],'acceptance':['Independent output check'],
                'resources':self.policy['symphony']['default_resources'],'attempt_limit':1}}}
        self.write(runtime/'manifest.json',manifest)
        self.write(runtime/'requests'/(issue.identifier+'.json'), {'prompt':'Approved immutable request','timeout_seconds':5})
        self.write(runtime/'capacity-policy.json',self.policy)
        self.write(runtime/'installation.json',self.installation)
        self.write(runtime/'provider-proof.json', {'route':'codex-chatgpt','available':True,'checked_at':time.time(),'session_ceiling':8})
        checkout = self.temp/f'checkout-{number}'
        checkout.mkdir(exist_ok=True)
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

    def adapted(self, current=True, manifest=None, native_harness_adapter_factory=None):
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
        native = adapter.install_adapters(self.runtime, manifest or {'project_id':adapter.PROJECT, 'tasks':{}}, 'in-memory-only', self.current if current else None,
            native_harness_adapter_factory=native_harness_adapter_factory)
        return native, linear, fetch

    def native_harness_fixture(self):
        """Actual consumer, original native gates, synthetic sealed OS boundary."""
        import native_harness_contract as contract
        source = Path(os.environ.get('OFFMENU_TEST_NATIVE_HARNESS_RUNTIME',
                                     str(Path(__file__).resolve().parents[2]/'tools/delivery/native_harness_runtime.py')))
        self.assertTrue(source.is_file(),
                        'Required native runtime missing: compose it or supply its exact explicit test source')
        issue, runtime, _, _ = self.bound_gate(388)
        for name in ('tools/delivery/native_harness_runtime.py',
                     'tools/delivery/native_harness_contract.py', 'tools/delivery/linear_delivery.py',
                     'tools/delivery/release_qualification.py', 'src/offmenu/delivery/engine.py',
                     'src/offmenu/delivery/status.py'):
            target = self.source/name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source if name.endswith('/native_harness_runtime.py')
                            else Path(__file__).resolve().parents[2]/name, target)
        installed = self.source/'tools/delivery/native_harness_runtime.py'
        spec = importlib.util.spec_from_file_location('native_harness_runtime', installed)
        module = importlib.util.module_from_spec(spec)
        self.stack.enter_context(patch.dict(sys.modules, native_harness_runtime=module))
        spec.loader.exec_module(module)
        policy = contract.load_release_policy(Path(__file__).resolve().parents[2]/'config/delivery-release-policy.json')
        ref = dict(path='.delivery/original.json', sha256='a'*64)
        handoff = dict(version=1,kind='delivery-handoff-v1',issue_id=issue.id,
            project_id=self.current.route['project_id'], owner=self.current.config['owner'],
            origin=dict(kind='reviewed-source-v1',evidence=ref),
            source=dict(repository='maldous/offmenu',branch='feature/test-current',base='b'*40,
                head='c'*40,tree='f'*40,target='develop',policy_sha256=contract.fingerprint(policy)),
            outputs=[],evidence=[ref])
        linear = dict(version=1,projects=[dict(id=handoff['project_id'],name='OffMenu',
            team_id='53f584e7-70a1-4b1e-b982-b815210e47d4')],
            outcomes=[dict(id=issue.id,identifier=issue.identifier,project_id=handoff['project_id'],
                team_id='53f584e7-70a1-4b1e-b982-b815210e47d4',state_type='started',
                blocked_by=[],pr_urls=[],milestone_ids=[])],
            changes=[dict(handoff=handoff,pull_request=dict(url='https://github.com/maldous/offmenu/pull/388',
                head='c'*40,tree='f'*40,base='develop',merged=False,canonical_verified=False))],
            dependencies=[],effects=[])
        packet = dict(policy=policy,handoff=handoff,candidate=None,linear=linear,release=None)
        action = module.plan_delivery(linear,policy)['actions'][0]
        binding = dict(issue_id=issue.id,project_id=handoff['project_id'],owner=handoff['owner'],
            packet_sha256=contract.fingerprint(packet),operation_id=action['action_id'],phase='linear',
            unit_sha256=contract.fingerprint(self.current.gate_binding(issue,observation=True)))
        packet_path, selected = self.root/'harness-packet.json', self.root/'harness-selection.json'
        self.write(packet_path,packet)
        engine_root = runtime/'workspaces'/issue.identifier
        engine_root.mkdir(parents=True,exist_ok=True)
        task_path, review_path = self.root/'unqualified-engine-task.json',self.root/'unqualified-unit-review.json'
        for path in (task_path,review_path):
            self.write(path,{'fixture':'unqualified context; not source or runtime acceptance'})
        context = dict(engine_root=str(engine_root),
            engine_task=dict(path=str(task_path),sha256=adapter.file_sha(task_path)),
            unit_review=dict(path=str(review_path),sha256=adapter.file_sha(review_path)))
        self.write(selected,dict(binding=binding,packet=dict(path=str(packet_path),sha256=adapter.file_sha(packet_path)),
                                 context=context))
        config = json.loads(json.dumps(self.current.config))
        config['native_harness_boundaries'] = {issue.identifier:dict(path=str(selected),sha256=adapter.file_sha(selected))}
        for path in (self.source/'tools/delivery').glob('*.py'):
            name = str(path.relative_to(self.source))
            if path.name in ('native_harness_runtime.py','native_harness_contract.py','linear_delivery.py','release_qualification.py'):
                config['source_sha256'][name] = adapter.file_sha(path)
        for name in ('engine.py','status.py'):
            path = self.source/'src/offmenu/delivery'/name
            config['source_sha256'][str(path.relative_to(self.source))] = adapter.file_sha(path)
        sealed = self.root/'sealed-current.json'
        self.write(sealed,config)
        state = json.loads(self.current.state_path.read_text())
        state['config_sha256'] = adapter.file_sha(sealed)
        self.write(self.current.state_path,state)
        # Only the kernel/sealed-file qualification is synthetic; all config,
        # source, native receipt, catalog and consumer checks remain real.
        self.stack.enter_context(patch.object(adapter,'PROTECTED_OWNER',self.root))
        self.stack.enter_context(patch.object(adapter,'protected_owner_bytes',side_effect=lambda p:Path(p).read_bytes()))
        self.stack.enter_context(patch.object(adapter,'current_config',side_effect=lambda r:
            (adapter.read_record(sealed),sealed,{'synthetic':'sealed owner'})))
        self.current = adapter.CurrentWork(self.runtime)
        effect = dict(operation_id=binding['operation_id'],status='ready',child_tree_gone=True)
        authorize = unittest.mock.Mock(return_value=True)
        def step(binding, context):
            effect['status'] = 'verified'
            return dict(effect)
        step = unittest.mock.Mock(side_effect=step)
        adapters = module.OwnerAdapters(authorize,lambda b:json.loads(json.dumps(packet)),
            lambda b:None,lambda *args:None,lambda b:dict(effect),step)
        factory = unittest.mock.Mock(return_value=adapters)
        return SimpleNamespace(issue=issue,runtime=runtime,module=module,packet=packet,
            binding=binding,selected=selected,sealed=sealed,effect=effect,authorize=authorize,
            step=step,factory=factory,packet_path=packet_path)

    def test_native_harness_absent_binding_neither_imports_nor_writes(self):
        before = self.current.state_path.read_bytes()
        with patch.object(adapter.importlib,'import_module') as load:
            asyncio.run(self.current.continue_native_harness())
        load.assert_not_called()
        self.assertEqual(before,self.current.state_path.read_bytes())

    def reseal_native_harness_selection(self, fixture, selection):
        self.write(fixture.selected,selection)
        config = json.loads(fixture.sealed.read_text())
        config['native_harness_boundaries'][fixture.issue.identifier]['sha256'] = adapter.file_sha(fixture.selected)
        self.write(fixture.sealed,config)
        state = json.loads(self.current.state_path.read_text())
        state['config_sha256'] = adapter.file_sha(fixture.sealed)
        self.write(self.current.state_path,state)

    def test_linear_empty_context_keeps_original_native_gate_without_unused_artifacts(self):
        f = self.native_harness_fixture()
        selection = json.loads(f.selected.read_text())
        # Remove only disposable unqualified test artifacts; they are neither
        # needed nor fabricated as evidence for a metadata-only transaction.
        for name in ('engine_task','unit_review'):
            Path(selection['context'][name]['path']).unlink()
        selection['context'] = {}
        self.reseal_native_harness_selection(f,selection)
        self.current = adapter.CurrentWork(self.runtime)
        self.assertEqual(self.current._native_harness_selection(f.issue.identifier)['context'],{})
        asyncio.run(self.current.continue_native_harness(f.factory))
        self.assertEqual(f.step.call_count,1)
        self.assertEqual(self.current.state['tasks'][f.issue.identifier]['native_harness']['projection']['effect']['status'],
                         'verified')
        self.assertFalse(self.current.state['accepted_delivery'])
        # Empty context is not a replacement for the original stopped native unit.
        f.factory.reset_mock(); f.step.reset_mock()
        self.write(f.runtime/'attempts'/f.issue.identifier/'receipt.json',{'status':'unknown'})
        asyncio.run(self.current.continue_native_harness(f.factory))
        f.factory.assert_not_called(); f.step.assert_not_called()
        self.assertFalse(self.current._native_harness_refill_allowed(f.issue.identifier))

    def test_linear_empty_context_rejects_wrong_phase_type_and_invocation_only(self):
        f = self.native_harness_fixture()
        original = json.loads(f.selected.read_text())
        invocation = dict(version=1,closure_sha256='a'*64,host_confirmation_sha256='b'*64)
        for phase,context in (('integration',{}),('release',{}),('linear',[]),('linear',None),
                              ('linear',{'publisher_invocation':invocation})):
            with self.subTest(phase=phase,context=context):
                selection = json.loads(json.dumps(original))
                selection['binding']['phase'], selection['context'] = phase, context
                self.reseal_native_harness_selection(f,selection)
                with self.assertRaisesRegex(AdmissionError,'native_harness_context'):
                    adapter.CurrentWork(self.runtime,read_only=True)
        f.factory.assert_not_called(); f.step.assert_not_called()

    def test_linear_empty_context_preserves_nonempty_reference_checks(self):
        f = self.native_harness_fixture()
        original = self.current._native_harness_selection(f.issue.identifier)
        self.assertEqual(set(original['context']),{'engine_root','engine_task','unit_review'})
        self.assertEqual(adapter.CurrentWork(self.runtime,read_only=True)._native_harness_selection(f.issue.identifier),
                         original)
        # A nonempty legacy Linear context still qualifies every original ref.
        Path(original['context']['unit_review']['path']).unlink()
        with self.assertRaises(FileNotFoundError):
            adapter.CurrentWork(self.runtime,read_only=True)

    def test_publisher_invocation_ingress_preserves_exact_metadata_and_selection_pin(self):
        f = self.native_harness_fixture()
        selection = json.loads(f.selected.read_text())
        invocation = dict(version=1,closure_sha256='a'*64,host_confirmation_sha256='b'*64)
        selection['context']['publisher_invocation'] = invocation
        self.reseal_native_harness_selection(f,selection)
        with patch.object(f.module,'fixed_publisher_rpc') as rpc:
            current = adapter.CurrentWork(self.runtime,read_only=True)
            current.guard()
            actual = current._native_harness_selection(f.issue.identifier)
        self.assertEqual(actual,selection)
        self.assertEqual(f.module.fingerprint(actual['context']['publisher_invocation']),
                         f.module.fingerprint(invocation))
        rpc.assert_not_called()
        # Editing valid metadata without the sealed selection's new byte pin
        # cannot change the owner-admitted context, even with valid hash syntax.
        selection['context']['publisher_invocation']['closure_sha256'] = 'c'*64
        self.write(f.selected,selection)
        with self.assertRaisesRegex(AdmissionError,'intake_reference_drift'):
            adapter.CurrentWork(self.runtime,read_only=True)

    def test_publisher_invocation_ingress_rejects_malformed_or_executable_selectors(self):
        f = self.native_harness_fixture()
        original = json.loads(f.selected.read_text())
        valid = dict(version=1,closure_sha256='a'*64,host_confirmation_sha256='b'*64)
        malformed = [None,False,[],{},dict(valid,version=True),dict(valid,version=1.0),
                     dict(valid,version='1'),dict(valid,version=2),dict(valid,closure_sha256='A'*64),
                     dict(valid,closure_sha256='a'*63),dict(valid,host_confirmation_sha256=False),
                     {k:v for k,v in valid.items() if k != 'host_confirmation_sha256'}]
        malformed += [dict(valid,**{key:value}) for key,value in (
            ('command','sudo anything'),('path','/tmp/helper'),('uid',2345),
            ('env',{}),('callback','issue-selected'),('enabled',True))]
        for invocation in malformed:
            with self.subTest(invocation=invocation):
                selection = json.loads(json.dumps(original))
                selection['context']['publisher_invocation'] = invocation
                self.reseal_native_harness_selection(f,selection)
                with self.assertRaisesRegex(AdmissionError,'native_harness_publisher_invocation'):
                    adapter.CurrentWork(self.runtime,read_only=True)
        f.factory.assert_not_called()
        f.step.assert_not_called()

    def test_publisher_invocation_ingress_requires_seal_and_absence_preserves_uid_hold(self):
        f = self.native_harness_fixture()
        original = self.current._native_harness_selection(f.issue.identifier)
        self.assertNotIn('publisher_invocation',original['context'])
        # Exercise only the existing early refusal, never protected config or a child.
        with patch.object(adapter.os,'getuid',return_value=1000), \
             patch.object(adapter,'protected_owner_bytes') as read:
            with self.assertRaisesRegex(f.module.RuntimeHold,'publisher_owner_identity_required'):
                f.module.publisher_identity({},'integration')
        read.assert_not_called()
        original['context']['publisher_invocation'] = dict(
            version=1,closure_sha256='a'*64,host_confirmation_sha256='b'*64)
        self.reseal_native_harness_selection(f,original)
        config = json.loads(f.sealed.read_text())
        with patch.object(adapter,'current_config',return_value=(config,f.sealed,None)):
            with self.assertRaisesRegex(AdmissionError,'native_harness_owner_config'):
                adapter.CurrentWork(self.runtime,read_only=True)

    def test_native_harness_config_rejects_unsealed_malformed_and_unpinned_inputs(self):
        f = self.native_harness_fixture()
        config = json.loads(f.sealed.read_text())
        for value in ([], {}, {'foreign':config['native_harness_boundaries'][f.issue.identifier]},
                      {f.issue.identifier:{'path':42,'sha256':'a'*64}}):
            self.write(f.sealed,dict(config,native_harness_boundaries=value))
            with self.assertRaises(AdmissionError):
                adapter.CurrentWork(self.runtime,read_only=True)
        self.write(f.sealed,config)
        with patch.object(adapter,'current_config',return_value=(config,f.sealed,None)):
            with self.assertRaisesRegex(AdmissionError,'native_harness_owner_config'):
                adapter.CurrentWork(self.runtime,read_only=True)
        missing = json.loads(json.dumps(config))
        missing['source_sha256'].pop('tools/delivery/native_harness_runtime.py')
        self.write(f.sealed,missing)
        with self.assertRaisesRegex(AdmissionError,'native_harness_source_pin'):
            adapter.CurrentWork(self.runtime,read_only=True)

    def test_native_harness_missing_factory_is_explicit_without_effect(self):
        f = self.native_harness_fixture()
        with patch.object(f.module,'owner_adapters',None,create=True):
            asyncio.run(self.current.continue_native_harness())
        state = self.current.state['tasks'][f.issue.identifier]['native_harness']
        self.assertEqual(state['status'],'held')
        self.assertEqual(state['reason'],'native_harness_adapters_unavailable')
        self.assertEqual(state['operation_id'],f.binding['operation_id'])
        f.step.assert_not_called()
        self.assertFalse(self.current._native_harness_refill_allowed(f.issue.identifier))

    def test_native_harness_normal_poll_uses_fixed_installed_factory_and_existing_client(self):
        f = self.native_harness_fixture()
        import stokowski.orchestrator as native
        client = self.client(f.issue)
        with patch.object(f.module,'owner_adapters',f.factory,create=True), \
             patch.object(native.Orchestrator,'_tick',new=AsyncMock()):
            installed, _, _ = self.adapted()
            with patch.object(self.current,'continue_validation',new=AsyncMock()):
                asyncio.run(installed.Orchestrator._tick(SimpleNamespace(_linear=client)))
        self.assertIs(f.factory.call_args.kwargs['linear_client'],client)
        self.assertEqual(f.step.call_count,1)

    def test_native_harness_context_and_binding_are_closed_owner_inputs(self):
        f = self.native_harness_fixture()
        selection = json.loads(f.selected.read_text())
        for section, name, value in (('binding','owner','foreign-owner'),
                                     ('binding','phase','execute-arbitrary'),
                                     ('binding','unit_sha256','invalid'),
                                     ('context','engine_root',str(self.temp)),
                                     ('context','callback','issue-selected-function')):
            changed = json.loads(json.dumps(selection))
            changed[section][name] = value
            self.write(f.selected,changed)
            config = json.loads(f.sealed.read_text())
            config['native_harness_boundaries'][f.issue.identifier]['sha256'] = adapter.file_sha(f.selected)
            self.write(f.sealed,config)
            with self.assertRaises(AdmissionError):
                adapter.CurrentWork(self.runtime,read_only=True)
        f.factory.assert_not_called()

    def test_native_harness_different_unit_and_permission_loss_never_step(self):
        f = self.native_harness_fixture()
        f.authorize.side_effect = [True,False]
        asyncio.run(self.current.continue_native_harness(f.factory))
        f.step.assert_not_called()
        self.assertEqual(self.current.state['tasks'][f.issue.identifier]['native_harness']['status'],'held')
        # A same-shaped but different original unit cannot use an admitted binding.
        f.authorize.side_effect = None
        f.authorize.return_value = True
        f.factory.reset_mock()
        original_gate = self.current.gate_binding
        def drift(*args, **kwargs):
            return dict(original_gate(*args, **kwargs),native_receipt_sha256='0'*64)
        with patch.object(self.current,'gate_binding',side_effect=drift):
            asyncio.run(self.current.continue_native_harness(f.factory))
        f.factory.assert_not_called()
        f.step.assert_not_called()
        self.assertFalse(self.current._native_harness_refill_allowed(f.issue.identifier))

    def test_native_harness_poll_consumes_actual_runtime_once_after_validation(self):
        f = self.native_harness_fixture()
        import stokowski.orchestrator as native
        order = []
        async def tick(owner):
            order.append('native')
        f.factory.side_effect = lambda *args, **kwargs:(order.append('consume') or f.factory.return_value)
        with patch.object(native.Orchestrator,'_tick',side_effect=tick):
            installed, _, _ = self.adapted(native_harness_adapter_factory=f.factory)
            with patch.object(self.current,'continue_validation',new=AsyncMock(side_effect=lambda:order.append('validation'))):
                asyncio.run(installed.Orchestrator._tick(SimpleNamespace()))
                asyncio.run(installed.Orchestrator._tick(SimpleNamespace()))
        self.assertEqual(order,['validation','consume','native']*2)
        self.assertEqual(f.step.call_count,1)
        self.assertEqual(self.current.state['tasks'][f.issue.identifier]['native_harness']['projection']['effect']['status'],'verified')

    def test_native_harness_source_and_selection_drift_hold_before_factory(self):
        f = self.native_harness_fixture()
        for path in (self.source/'tools/delivery/native_harness_runtime.py', f.selected, f.packet_path):
            before = path.read_bytes()
            path.write_bytes(before+b' ')
            asyncio.run(self.current.continue_native_harness(f.factory))
            self.assertEqual(self.current.state['tasks'][f.issue.identifier]['native_harness']['status'],'held')
            path.write_bytes(before)
        f.factory.assert_not_called()
        f.step.assert_not_called()

    def test_native_harness_permission_unknown_and_unstopped_results_cannot_refill(self):
        f = self.native_harness_fixture()
        with patch.object(self.current,'_successor_boundary') as successor:
            for status, gone in (('unknown',True),('pending',True),('denied',True),('verified',False)):
                f.effect.update(status=status,child_tree_gone=gone)
                asyncio.run(self.current.continue_native_harness(f.factory))
            f.effect.update(operation_id='0'*64,status='verified',child_tree_gone=True)
            asyncio.run(self.current.continue_native_harness(f.factory))
            self.assertEqual(self.current.state['tasks'][f.issue.identifier]['native_harness']['projection']['reason'],
                             'transaction_identity')
            f.effect['operation_id'] = f.binding['operation_id']
            f.effect.update(status='ready',child_tree_gone=True)
            f.authorize.return_value = 1  # Truthiness is insufficient authority.
            asyncio.run(self.current.continue_native_harness(f.factory))
        f.step.assert_not_called()
        successor.assert_not_called()

    def test_native_harness_verified_permit_is_ephemeral_and_unit_bound(self):
        f = self.native_harness_fixture()
        allowed = []
        with patch.object(self.current,'_successor_boundary',side_effect=lambda:
                allowed.append(self.current._native_harness_refill_allowed(f.issue.identifier))):
            asyncio.run(self.current.continue_native_harness(f.factory))
        self.assertEqual(allowed,[True])
        self.assertFalse(self.current._native_harness_refill_allowed(f.issue.identifier))
        # Even a saved verified projection on restart cannot bypass fresh consumption.
        reopened = adapter.CurrentWork(self.runtime)
        self.assertFalse(reopened._native_harness_refill_allowed(f.issue.identifier))
        before = (f.runtime/'attempts'/f.issue.identifier/'receipt.json').read_bytes()
        self.write(f.runtime/'attempts'/f.issue.identifier/'receipt.json',{'status':'unknown'})
        with patch.object(self.current,'_successor_boundary') as successor:
            asyncio.run(self.current.continue_native_harness(f.factory))
        successor.assert_not_called()
        (f.runtime/'attempts'/f.issue.identifier/'receipt.json').write_bytes(before)
        self.assertEqual(f.step.call_count,1)

    def test_native_harness_sync_successor_cannot_use_saved_verified_projection(self):
        f = self.native_harness_fixture()
        config, packet, handoff = self.root/'next-config.json',self.root/'next-packet.json',self.root/'next-handoff.json'
        self.write(config,{'native_publication':{}})
        config_ref = dict(path=str(config),sha256=adapter.file_sha(config))
        self.write(packet,dict(owner_config=config_ref,trigger={'issue':f.issue.identifier}))
        self.write(handoff,dict(owner_config=config_ref,task_packet=dict(path=str(packet),sha256=adapter.file_sha(packet))))
        self.current.state['intake_handoff'] = dict(path=str(handoff),sha256=adapter.file_sha(handoff))
        self.current.state['tasks'][f.issue.identifier]['native_harness'] = dict(status='verified',
            operation_id=f.binding['operation_id'],unit_sha256=f.binding['unit_sha256'])
        with patch.object(self.current,'_native_successor') as publish:
            self.current._successor_boundary()
        publish.assert_not_called()
        self.assertEqual(self.current.state['successor_hold'],'AdmissionError: native_harness_refill_readback_required')

    def client(self, issue, project=None, state=None):
        return SimpleNamespace(_graphql=AsyncMock(return_value={'issue':{
            'id':issue.id,'identifier':issue.identifier,'project':{'id':project or adapter.PROJECT},
            'state':{'name':state or issue.state}}}))

    def select(self, issue, client=None):
        return asyncio.run(self.current.candidates(client or self.client(issue), [issue]))

    def review_fixture(self, number=230, completed=None, template_coding=False):
        from symphony_capacity import digest
        from stokowski_operations import Journal, operation_key, bridge_arguments
        if template_coding:
            import stokowski_worker as worker
            from contextlib import nullcontext
            issue,runtime=self.qualify(number)
            manifest=adapter.read_record(runtime/'manifest.json');task=manifest['tasks'][issue.identifier]
            static=dict(schema='native-review-template-v1',role='native-review-read-only',
                owner='existing-owner',reviewer_owner='synthetic-native-review-owner',project_id=manifest['project_id'],
                source_root=str(self.temp/'candidate'),validation_receipt_name='original-validation-receipt.json',
                provider='codex-chatgpt',model=worker.MODEL,effort='medium',resources=task['resources'],
                acceptance=task['acceptance'],timeout_seconds=5,require_stopped_child=True,
                **{k:self.current.config[k] for k in ('source_head','source_sha256','installation_sha256')})
            template_path=self.runtime/'native-review-template.json';self.write(template_path,static);template_path.chmod(0o600)
            self.current.config['native_review_template']=dict(path=str(template_path),sha256=adapter.file_sha(template_path))
            self.write(self.runtime/'current.json',self.current.config)
            self.current.config_sha=adapter.file_sha(self.runtime/'current.json')
            self.current.state['config_sha256']=self.current.config_sha;self.current.save()
            workspace=runtime/'workspaces'/issue.identifier
            subprocess.run(['/usr/bin/git','clone','--no-hardlinks',str(self.temp/'checkout-230'),str(workspace)],check=True,capture_output=True)
            request=adapter.read_record(runtime/'requests'/(issue.identifier+'.json'))
            self.write(runtime/'attempts'/issue.identifier/'dispatch-intent.json',dict(
                entry_sha256=digest(self.entries[-1]),owner=self.current.config['owner'],
                request_sha256=adapter.file_sha(runtime/'requests'/(issue.identifier+'.json')),
                manifest_sha256=adapter.file_sha(runtime/'manifest.json'),
                expected_lease=runtime_lease_ids(runtime,manifest)[issue.identifier]))
            def coding_command(workspace,final_message,**kwargs):
                script=('import json,sys; from pathlib import Path; sys.stdin.read(); '
                    'p=Path("tests/task230.py"); p.parent.mkdir(exist_ok=True); '
                    'p.write_text("independent immutable output\\n"); '
                    'print(json.dumps({"type":"thread.started","thread_id":"synthetic-author-session"})); '
                    'print(json.dumps({"type":"turn.completed"}))')
                return [sys.executable,'-c',script]
            host=dict(cpu_millis=64000,available_memory_bytes=128*1024**3,available_disk_bytes=1024**4)
            with patch.object(worker,'codex_command',side_effect=coding_command), \
                 patch.object(worker,'isolated_codex_environment',side_effect=lambda *a:nullcontext({})), \
                 patch.object(worker,'host_snapshot',return_value=host),patch.object(worker.os,'sched_setaffinity'):
                result=worker.execute(runtime,issue.identifier,request)
            self.assertEqual(result['status'],'succeeded',result)
            self.assertEqual(result['session_id'],'synthetic-author-session')
            completed=(issue,runtime,None,None)
            self.current.state['tasks'][issue.identifier]['unit_gate']=dict(binding=self.current.gate_binding(issue),disposition='waiting')
            self.current.save()
        if completed is None:
            issue, runtime, owner, client = self.bound_gate(number)
            directory = runtime/'attempts'/issue.identifier
            native = json.loads((directory/'receipt.json').read_text())
            output = b'independent immutable output\n'
            outputs = {f'tests/task{number}.py':hashlib.sha256(output).hexdigest()}
            target = runtime/'workspaces'/issue.identifier/f'tests/task{number}.py'
            target.parent.mkdir(parents=True)
            target.write_bytes(output)
            native.update(source_head=getattr(self,'task_head','b'*40), output_sha256=outputs, scope_violations=[])
            self.write(directory/'receipt.json', native)
            unit = self.current.gate_binding(issue)
            self.current.state['tasks'][issue.identifier]['unit_gate']['binding'] = unit
            self.current.save()
        else:
            # Synthetic validation/reviewer actors consume the real worker's
            # unchanged receipt, outputs, admission and native unit binding.
            issue, runtime, owner, client = completed
            unit = self.current.gate_binding(issue)
            outputs = adapter.read_record(runtime/'attempts'/issue.identifier/'receipt.json')['output_sha256']
        spec = dict(version=1, issue=issue.identifier, issue_id=issue.id, stage='validate',
            owner='existing-owner', head='c'*40, base=getattr(self,'task_head','b'*40), branch='feature/test-current',
            policy_sha256=self.current.config['policy_sha256'], outputs=outputs, profile='delivery-suite',
            runner_sha256='d'*64, executor_sha256='e'*64,
            acceptance_sha256=digest(dict(task=json.loads((runtime/'manifest.json').read_text())['tasks'][issue.identifier],
                native_receipt_sha256=unit['native_receipt_sha256'],profile='delivery-suite')))
        journal = Journal(runtime/'operations'); key = journal.prepare(spec)
        _, state = journal.read(key)
        receipt = dict(status='succeeded', exit_code=0, child_tree_gone=True, reconcile_required=False,
            job_id=state['logical_job_id'], runner_sha256=spec['runner_sha256'],
            capacity_policy_sha256=spec['policy_sha256'],
            command_sha256=hashlib.sha256(bridge_arguments(spec)['command'].encode()).hexdigest())
        state.update(status='succeeded', receipt_sha256=digest(receipt),
            accepted_output_sha256=outputs, acceptance_sha256=spec['acceptance_sha256'])
        journal.save(key,state,'controlled-test-proof')
        self.write(runtime/'validation-bindings.json',dict(version=1,issues={issue.identifier:dict(
            operation_key=key,source_head='c'*40,native_receipt_sha256=unit['native_receipt_sha256'],
            native_output_sha256=outputs,derivation={})}))
        b = dict(version=1, repository='maldous/offmenu',pr_number=145,issue_id=issue.id,
            owner='existing-owner', head='c'*40,base=getattr(self,'task_head','b'*40),tree='f'*40,
            policy_sha256='1'*64,capacity_policy_sha256=spec['policy_sha256'],
            validation_operation_key=key,outputs=outputs,head_branch='feature/test-current')
        review = dict(head='c'*40,base=getattr(self,'task_head','b'*40),outputs=outputs,independent=True,evidence_id='immutable-review-230',
            reviewer='independent-reviewer',author='existing-owner',model='review-model',provider='existing-route',
            findings=[],verdict='accept')
        if completed is not None:
            review.update(requested_model='synthetic-independent-review', requested_effort=None,
                requested_provider='synthetic-offline', resolved_model=None, resolution_status='unknown')
        review['evidence_sha256'] = digest(review)
        validation = dict(operation_key=key,status='succeeded',head='c'*40,base=getattr(self,'task_head','b'*40),
            capacity_policy_sha256=spec['policy_sha256'],outputs=outputs,child_tree_gone=True,reconcile_required=False)
        snapshot = dict(review=review,validation=validation,publisher_owner='existing-owner',source_tree='f'*40,
            source_clean=True,publication_triggers_actions=False,policy_sha256='1'*64,
            capacity_policy_sha256=spec['policy_sha256'])
        decision = dict(status='merge-intent',merge_effect='pending',binding_sha256=digest(b),
            qualification_sha256=digest(dict(validation=validation,review=review,tree='f'*40,policy='1'*64)),
            action=dict(kind='merge-pr',expected_head_sha='c'*40,expected_base_sha=getattr(self,'task_head','b'*40)))
        packet = dict(issue=issue.identifier,unit_binding=unit,integration_binding=b,
            snapshot=snapshot,decision=decision,validation_receipt=receipt)
        return issue,runtime,owner,client,packet,journal,key

    def continuation_fixture(self, number=230):
        import stokowski_operations as operations
        import stokowski_stage as stage
        import stokowski_mcp as mcp
        for module in (operations, stage, mcp):
            shutil.copyfile(module.__file__, self.source/'tools/delivery'/Path(module.__file__).name)
        self.stack.enter_context(patch.object(mcp, 'configured_headers', side_effect=AssertionError('offline')))
        self.stack.enter_context(patch('socket.socket.connect', side_effect=AssertionError('offline')))
        # Control only upstream scheduling; the installed wrapper, stage and Journal are real.
        import stokowski.orchestrator as native
        upstream = self.stack.enter_context(patch.object(native.Orchestrator, '_tick', new_callable=AsyncMock))
        self.task_branch = 'feature/independent-candidate'
        issue, runtime, owner, client, packet, journal, old_key = self.review_fixture(number)
        spec, _ = journal.read(old_key)
        spec.update(branch=self.task_branch, runner_sha256=adapter.file_sha(self.source/'tools/delivery/windmill_runner.py'),
                    executor_sha256=adapter.file_sha(operations.__file__))
        self.stack.enter_context(patch.object(operations, 'POLICY', self.source/'tools/delivery/capacity-policy.json'))
        key = journal.prepare(spec)
        _, state = journal.read(key)
        state['status'] = 'submit-intent'
        journal.save(key, state, 'synthetic-lost-reply')
        bindings = json.loads((runtime/'validation-bindings.json').read_text())
        bindings.update(history=[])
        bindings['issues'][issue.identifier].update(operation_key=key, source_head=spec['head'], derivation_reason=None)
        self.write(runtime/'validation-bindings.json', bindings)
        self.candidate_objects = getattr(self, 'candidate_objects', {})
        for name in spec['outputs']:
            self.candidate_objects[name] = (runtime/'workspaces'/issue.identifier/name).read_bytes()
        remote = SimpleNamespace(inspect=AsyncMock(return_value=None), submit=AsyncMock(), close=AsyncMock())
        factory = self.stack.enter_context(patch.object(stage, 'WindmillMCP', return_value=remote))
        return issue, runtime, owner, journal, key, spec, remote, factory, upstream

    def test_direct_worker_refuses_typed_stage_before_any_other_input(self):
        import stokowski_worker as worker
        issue, runtime = self.qualify(249)
        manifest = json.loads((runtime/'manifest.json').read_text())
        task = manifest['tasks'][issue.identifier]
        task.update(stage='review', input_paths=task['allowed_paths'], allowed_paths=[],
                    stage_binding=dict(entry={}, identity='0'*64, inputs={}))
        self.write(runtime/'manifest.json', manifest)
        # An absent policy would otherwise fail before lease admission. The
        # typed refusal must win without reading it or constructing a pool.
        (runtime/'capacity-policy.json').unlink()
        with patch.object(worker, 'Pool', side_effect=AssertionError('No lease')), \
             patch.object(worker, 'git', side_effect=AssertionError('No computation')):
            with self.assertRaisesRegex(AdmissionError, 'native_review_request'):
                worker.execute(runtime, issue.identifier, {})
        self.assertEqual(list((runtime/'attempts').iterdir()), [])

    def test_independent_candidate_ignores_control_output_disk(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        self.assertNotEqual(spec['head'], self.current.config['source_head'])
        self.assertNotEqual(spec['branch'], 'feature/test-current')
        target = self.source/'tests/task230.py'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b'unrelated coordinator output')
        asyncio.run(owner._tick())
        remote.inspect.assert_awaited_once()
        remote.submit.assert_not_awaited()

    def test_candidate_committed_output_and_ancestry_hold_before_transport(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        name = next(iter(spec['outputs']))
        original = self.candidate_objects[name]
        for contents in (None, b'wrong committed bytes'):
            if contents is None:
                del self.candidate_objects[name]
            else:
                self.candidate_objects[name] = contents
            asyncio.run(owner._tick())
            factory.assert_not_called()
        self.candidate_objects[name] = original
        original_git = self.git.side_effect
        def reject_ancestry(args, **kwargs):
            if args[3] == 'merge-base':
                raise subprocess.CalledProcessError(1, args)
            return original_git(args, **kwargs)
        self.git.side_effect = reject_ancestry
        asyncio.run(owner._tick())
        factory.assert_not_called()

    def test_validation_phase_rotates_after_slow_effect_and_reopen(self):
        first = self.continuation_fixture()
        second = self.continuation_fixture(231)
        clock = [0.0]
        async def slow_unknown(*args, **kwargs):
            clock[0] += 11
            raise asyncio.TimeoutError()
        first[6].inspect.side_effect = slow_unknown
        second[7].side_effect = [first[6], second[6]]
        with patch.object(adapter.time, 'monotonic', side_effect=lambda: clock[0]):
            asyncio.run(self.current.continue_validation())
            first[6].inspect.assert_awaited_once()
            second[6].inspect.assert_not_awaited()
            self.current = adapter.CurrentWork(self.runtime)
            asyncio.run(self.current.continue_validation())
        second[6].inspect.assert_awaited_once()
        self.assertEqual(second[6].inspect.await_args.args[0],
                         second[3].read(second[4])[1]['windmill_job_id'])
        first[6].submit.assert_not_awaited()
        second[6].submit.assert_not_awaited()

    def test_normal_tick_continues_original_intent_and_reopen(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        asyncio.run(owner._tick())
        self.assertEqual(remote.inspect.await_count, 1, 'NORMAL_CURRENT_VALIDATION_JOURNAL_NOT_CONTINUED')
        self.assertEqual(journal.read(key)[1]['status'], 'unknown')
        self.current = adapter.CurrentWork(self.runtime)
        # New adapter and owner lifetime, same durable operation and original UUID.
        import stokowski.orchestrator as native
        native.Orchestrator._tick = upstream
        native, _, _ = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        asyncio.run(owner._tick())
        self.assertEqual(remote.inspect.await_count, 2)
        self.assertEqual(remote.inspect.await_args_list[0], remote.inspect.await_args_list[1])
        remote.submit.assert_not_awaited()
        self.assertEqual(upstream.await_count, 2)

    def test_normal_tick_observes_queued_then_completed_without_resubmit(self):
        from stokowski_operations import bridge_arguments, BRIDGE
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        _, state = journal.read(key)
        job = dict(id=state['windmill_job_id'], workspace_id='offmenu', script_path=BRIDGE,
                   args=bridge_arguments(spec), type='QueuedJob', running=False)
        remote.inspect.return_value = job
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'], 'queued')
        receipt = dict(status='succeeded', job_id=state['logical_job_id'], exit_code=0,
            child_tree_gone=True, reconcile_required=False, runner_sha256=spec['runner_sha256'],
            capacity_policy_sha256=spec['policy_sha256'],
            command_sha256=hashlib.sha256(bridge_arguments(spec)['command'].encode()).hexdigest())
        remote.inspect.return_value = dict(job, type='CompletedJob', success=True,
            result=dict(job_id=state['logical_job_id'], job_succeeded=True, receipt=receipt))
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'], 'succeeded')
        self.assertEqual(json.loads((runtime/'validation-stage.json').read_text())['issues'][issue.identifier]['status'], 'succeeded')
        asyncio.run(owner._tick())  # Terminal progress is reused, never replayed.
        self.assertEqual(remote.inspect.await_count, 2)
        remote.submit.assert_not_awaited()
        self.assertEqual(self.current.state['tasks'][issue.identifier]['unit_gate']['disposition'], 'waiting')

    def test_normal_tick_rejects_invalid_validation_before_transport(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        path = runtime/'validation-bindings.json'
        bindings = json.loads(path.read_text())
        original_receipt = (runtime/'attempts'/issue.identifier/'receipt.json').read_bytes()
        original_output = (runtime/'workspaces'/issue.identifier/'tests/task230.py').read_bytes()
        bad_specs = [dict(spec, **{field:value}) for field,value in (
            ('issue_id','00000000-0000-4000-8000-000000000999'), ('owner','foreign'),
            ('head','f'*40), ('branch','feature/wrong-candidate'), ('base','f'*40), ('policy_sha256','f'*64), ('executor_sha256','f'*64),
            ('runner_sha256','f'*64), ('acceptance_sha256','f'*64), ('outputs',{'tests/task230.py':'f'*64}))]
        for bad in bad_specs:
            with self.subTest(spec=next(k for k in spec if spec[k] != bad[k])):
                with journal.db() as db:
                    db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(bad,sort_keys=True),key))
                asyncio.run(owner._tick())
                factory.assert_not_called()
        with journal.db() as db:
            db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(spec,sort_keys=True),key))
        for bad in ({}, dict(bindings,version=2), dict(bindings,issues={**bindings['issues'],'UIF-999':bindings['issues'][issue.identifier]}),
                    dict(bindings,history=[dict(issue='UIF-999')]),
                    *(dict(bindings,issues={issue.identifier:dict(bindings['issues'][issue.identifier],**{field:value})})
                      for field,value in (('operation_key','f'*64), ('source_head','f'*40),
                        ('native_receipt_sha256','f'*64), ('native_output_sha256',{}),
                        ('derivation',{'unsupported':'derivation'})))):
            with self.subTest(binding=bad):
                self.write(path,bad)
                asyncio.run(owner._tick())
                factory.assert_not_called()
        self.write(path,bindings)
        for target in (runtime/'requests'/(issue.identifier+'.json'),
                       runtime/'attempts'/issue.identifier/'receipt.json', runtime/'workspaces'/issue.identifier/'tests/task230.py'):
            original = target.read_bytes()
            target.write_text('{}')
            asyncio.run(owner._tick())
            factory.assert_not_called()
            target.write_bytes(original)
        path.unlink()
        asyncio.run(owner._tick())
        factory.assert_not_called()  # Completed coding never creates validation authority.
        self.assertEqual((runtime/'attempts'/issue.identifier/'receipt.json').read_bytes(),original_receipt)
        self.assertEqual((runtime/'workspaces'/issue.identifier/'tests/task230.py').read_bytes(),original_output)

    def test_unbound_current_tick_never_creates_journal(self):
        import stokowski.orchestrator as native
        import stokowski_stage as stage
        self.stack.enter_context(patch.object(native.Orchestrator,'_tick',new_callable=AsyncMock))
        issue, runtime, owner, client = self.bound_gate(239)
        with patch.object(stage,'WindmillMCP',side_effect=AssertionError('unqualified')):
            asyncio.run(owner._tick())
        self.assertFalse((runtime/'operations').exists())

    def test_validation_identity_drift_after_observation_holds(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        asyncio.run(owner._tick())
        path = runtime/'validation-bindings.json'
        # Semantically same JSON with changed original bytes is still drift.
        path.write_text(json.dumps(json.loads(path.read_text()), indent=2))
        asyncio.run(owner._tick())
        self.assertEqual(remote.inspect.await_count,1)
        self.assertEqual(self.current.state['tasks'][issue.identifier]['validation']['status'],'held')

    def test_run_current_entrypoint_consumes_stage_and_cancels(self):
        from stokowski.linear import LinearClient
        from stokowski.config import ProjectConfig
        import stokowski.orchestrator as native
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        native.Orchestrator._tick = upstream
        async def start():
            actual = native.Orchestrator(self.runtime/'workflow.yaml')
            await actual._tick()
            self.write(self.runtime/'cancel.json',{})
        coordinator = SimpleNamespace(orchestrators={}, start=start, stop=AsyncMock())
        with patch.object(native,'MultiOrchestrator',return_value=coordinator), \
             patch.object(ProjectConfig,'resolved_api_key',return_value='memory-only'), \
             patch.object(adapter,'credential',return_value='memory-only'), \
             patch.object(LinearClient,'fetch_candidate_issues',new=AsyncMock(return_value=[])):
            asyncio.run(adapter.run(self.runtime,1,current_mode=True))
        self.assertEqual(remote.inspect.await_count,1)
        remote.submit.assert_not_awaited()
        coordinator.stop.assert_awaited_once()
        self.assertTrue(json.loads((self.runtime/'current-owner.json').read_text())['stopped'])

    def test_qualified_prepared_submits_once_and_refusal_retains_identity(self):
        from stokowski_operations import RequestRefused
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        _, state = journal.read(key)
        state['status'] = 'prepared'
        journal.save(key,state,'synthetic-unexecuted')
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'submitted')
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        remote.submit.assert_awaited_once()
        remote.inspect.side_effect = RequestRefused('synthetic refusal')
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        self.assertEqual(journal.read(key)[1]['windmill_job_id'],state['windmill_job_id'])
        remote.submit.assert_awaited_once()

    def test_validation_state_identity_drift_and_cancel_flag_preserved(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        _, state = journal.read(key)
        for field in ('windmill_job_id','cancel_job_id','logical_job_id'):
            journal.save(key,dict(state,**{field:'foreign'}),'synthetic-conflict')
            asyncio.run(owner._tick())
            factory.assert_not_called()
        state['cancel_requested'] = True
        journal.save(key,state,'synthetic-cancel-request')
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        self.assertTrue(journal.read(key)[1]['cancel_requested'])
        remote.submit.assert_not_awaited()

    def test_validation_phase_cancellation_propagates(self):
        issue, runtime, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture()
        remote.inspect.side_effect = asyncio.CancelledError()
        with self.assertRaises(asyncio.CancelledError):
            asyncio.run(owner._tick())
        remote.close.assert_awaited_once()
        remote.submit.assert_not_awaited()
        upstream.assert_not_awaited()

    def test_transport_v2_byte_oracle_and_domain(self):
        import stokowski_unit_review as transport
        from symphony_capacity import digest
        raw = '{"duration_seconds":1e-7}'
        self.assertEqual(hashlib.sha256(raw.encode()).hexdigest(),
                         'd69596f32f2541138b93f4d3b73427f7c2345864eab139ba7bdd22da962b5084')
        self.assertEqual(digest(transport.decode(raw)),
                         'c11819de64a85012c9d89df355b705b1f2a1207b477d6f21d69f477073177a19')
        self.assertTrue(transport.same_wire({'2':1.0,'10':1e-7,'𐀀':'😀','\ue000':'é'},
                                            {'\ue000':'é','𐀀':'😀','10':1e-7,'2':1}))
        self.assertFalse(transport.same_wire(True,1))
        for v in (float('nan'),float('inf'),-float('inf'),-0.0,2**53,1e100):
            with self.assertRaises(AdmissionError):
                transport.wire_value(v)
        with self.assertRaises(AdmissionError):
            transport.handle({'mode':'status','context':{},'envelope':{}})

    def test_fixed_gateway_process_fixture(self):
        self.fixed_gateway_process_fixture(staged=False)

    def test_native_review_actual_phase_worker_qualifier_and_unit_gate(self):
        self.fixed_gateway_process_fixture(staged=True,native_review=True)

    def test_normal_coding_terminal_validation_native_review(self):
        self.fixed_gateway_process_fixture(staged='normal',native_review=True)

    def test_normal_coding_static_template_native_review(self):
        self.fixed_gateway_process_fixture(staged='normal',native_review='template')

    def test_normal_template_rework_survives_refresh_and_response(self):
        self.fixed_gateway_process_fixture(staged='normal',native_review='template-rework')

    def test_normal_template_capacity_deferred_same_operation(self):
        self.fixed_gateway_process_fixture(staged='normal',native_review='capacity-defer')

    def test_native_review_rework_is_only_a_local_unit_verdict(self):
        self.fixed_gateway_process_fixture(staged=True,native_review='rework')

    def native_review_phase_fixture(self,issue,origin_runtime,runtime,candidate,spec,verdict='accept',template=False,capacity_defer=False):
        from symphony_capacity import Pool
        import stokowski_worker as worker
        import stokowski_unit_review as unit_review
        from contextlib import nullcontext
        # No external reviewer profile, snapshot or connector is supplied.
        files={name:adapter.file_sha(candidate/name)
               for name in worker.git(candidate,'ls-files','-z').split('\0') if name}
        source=dict(root=str(candidate),head=spec['head'],base=spec['base'],branch=spec['branch'],
            tree=worker.git(candidate,'rev-parse','HEAD^{tree}'),outputs=spec['outputs'],files_sha256=adapter.digest(files))
        _,identity=self.current.validation_binding(issue.identifier,self.current.entries[issue.identifier])
        manifest=json.loads((runtime/'manifest.json').read_text())
        task=manifest['tasks'][issue.identifier]
        native_path=origin_runtime/'attempts'/issue.identifier/'receipt.json'
        policy=dict(schema=worker.REVIEW_ORIGIN,owner='existing-owner',reviewer_owner='synthetic-native-review-owner',
            project_id=manifest['project_id'],issue=issue.identifier,stage_identity=task['stage_binding']['identity'] if 'stage' in task else identity,
            unit_binding=self.current.gate_binding(issue),validation_identity=identity,source=source,
            author_receipts=[dict(path=str(native_path),sha256=adapter.file_sha(native_path))],
            excluded_sessions=['synthetic-author-session'],excluded_owners=['existing-owner'],
            provider='codex-chatgpt',model=worker.MODEL,effort='medium',resources=task['resources'],
            acceptance=task['acceptance'],timeout_seconds=5,require_stopped_child=True)
        if 'stage' not in task:
            (origin_runtime/'original-validation-receipt.json').chmod(0o600)
            policy.update(current_runtime=str(self.runtime),validation_receipt=dict(
                path=str(origin_runtime/'original-validation-receipt.json'),
                sha256=adapter.file_sha(origin_runtime/'original-validation-receipt.json')))
        native_path.chmod(0o600)
        if template:
            static={k:policy[k] for k in ('owner','reviewer_owner','project_id','provider','model','effort',
                'resources','acceptance','timeout_seconds','require_stopped_child')}
            static.update(schema='native-review-template-v1',role='native-review-read-only',
                source_root=str(candidate),validation_receipt_name='original-validation-receipt.json',
                **{k:self.current.config[k] for k in ('source_head','source_sha256','installation_sha256')})
            template_path=self.runtime/'native-review-template.json'
            self.assertEqual(adapter.read_record(template_path),static)
            self.current.config['native_review_template']=dict(path=str(template_path),sha256=adapter.file_sha(template_path))
            self.assertNotIn('native_review_policies',self.current.config)
            path=runtime/'native-review-derived-policy.json'
            self.assertFalse(path.exists())
            ref=None
        else:
            path=runtime/'native-review-policy.json';self.write(path,policy);path.chmod(0o600)
            ref=dict(path=str(path),sha256=adapter.file_sha(path))
            self.current.config['native_review_policies']={issue.identifier:ref}
        self.write(self.runtime/'current.json',self.current.config)
        self.current.config_sha=adapter.file_sha(self.runtime/'current.json')
        self.current.state['config_sha256']=self.current.config_sha
        self.current.save()
        original_native=native_path.read_bytes()
        if template:
            database=origin_runtime/'operations/operations.sqlite'
            with sqlite3.connect(database) as db:
                key,raw=db.execute('SELECT key,state FROM operations WHERE key=?',
                    (adapter.read_record(origin_runtime/'validation-bindings.json')['issues'][issue.identifier]['operation_key'],)).fetchone()
                for status in ('unknown','failed','cancelled','running'):
                    state=json.loads(raw);state['status']=status
                    db.execute('UPDATE operations SET state=? WHERE key=?',(json.dumps(state),key));db.commit()
                    with self.assertRaises(AdmissionError):
                        self.current.native_review_template_policy(issue.identifier,materialize=True)
                    self.assertFalse(path.exists())
                db.execute('UPDATE operations SET state=? WHERE key=?',(raw,key));db.commit()
        preserved = [origin_runtime/'attempts'/issue.identifier/name for name in ('intent.json','dispatch-intent.json')]
        preserved += [origin_runtime/'operations/operations.sqlite',origin_runtime/'manifest.json',
                      origin_runtime/'requests'/(issue.identifier+'.json'),self.catalog]
        before = {p:p.read_bytes() for p in preserved}
        self.assertEqual('stage' in task, runtime != origin_runtime)
        def command(workspace,final_message,**kwargs):
            self.assertTrue(kwargs['read_only'])
            artifact=dict(schema=worker.REVIEW_ORIGIN,source=source,verdict=verdict,
                findings=['Synthetic bounded finding'] if verdict=='rework' else [])
            return [sys.executable,'-c',
                'import json,sys; from pathlib import Path; sys.stdin.read(); '
                'print(json.dumps({"type":"thread.started","thread_id":"synthetic-independent-native-session"})); '
                'print(json.dumps({"type":"turn.completed"})); '
                'Path(sys.argv[1]).write_text(sys.argv[2])',str(final_message),json.dumps(artifact)]
        async def launch(*args,**kwargs):
            # Only the external process/provider boundary is controlled; worker,
            # Pool, policy/source qualification and gate consumption are real.
            self.assertIn('--native-review-policy',args)
            actual_ref=dict(path=args[args.index('--native-review-policy')+1],
                sha256=args[args.index('--native-review-policy-sha256')+1])
            request=dict(kind=worker.REVIEW_ORIGIN,policy=actual_ref)
            try:
                worker.execute(runtime,issue.identifier,request)
            except AdmissionError as error:
                if str(error) != 'capacity_sessions':raise
                return SimpleNamespace(wait=AsyncMock(return_value=2),returncode=2)
            return SimpleNamespace(wait=AsyncMock(return_value=0),returncode=0)
        host=dict(cpu_millis=64000,available_memory_bytes=128*1024**3,available_disk_bytes=1024**4)
        with patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=launch) as spawn, \
             patch.object(worker,'codex_command',side_effect=command) as native_command, \
             patch.object(worker,'isolated_codex_environment',side_effect=lambda *a:nullcontext({})), \
             patch.object(worker,'host_snapshot',return_value=host), \
             patch.object(worker.os,'sched_setaffinity'):
            if capacity_defer:
                capacity=json.loads((runtime/'capacity-policy.json').read_text())
                pool=Pool(capacity['symphony']['pool_path'],capacity)
                # Consume the actual provider ceiling using existing Pool bindings.
                proof_path=runtime/'provider-proof.json';proof_raw=proof_path.read_bytes()
                proof=json.loads(proof_raw);proof['session_ceiling']=1
                proof_path.write_text(json.dumps(proof))
                blocker_binding=next(iter(pool.status()))['binding']
                pool.admit('capacity-blocker',blocker_binding,json.loads(proof_raw),host)
                asyncio.run(self.current.continue_validation())
                state=self.current.state['tasks'][issue.identifier]
                self.assertEqual(state['native_review']['status'],'deferred',state['native_review'])
                self.assertNotEqual(state.get('unit_gate',{}).get('disposition'),'approved')
                directory=runtime/'attempts'/('review-'+issue.identifier)
                self.assertFalse((directory/'receipt.json').exists())
                intent=adapter.read_record(directory/'intent.json')
                self.assertFalse(any(r['id']==intent['lease'] for r in pool.status()))
                spawn.assert_awaited_once()
                pool.finish('capacity-blocker',True,'stopped')
                proof_path.write_bytes(proof_raw)
                self.current=adapter.CurrentWork(self.runtime)
            asyncio.run(self.current.continue_validation())
            state=self.current.state['tasks'][issue.identifier]
            self.assertEqual(state['native_review']['status'],'qualified',state['native_review'])
            native_command.assert_called_once()
            if capacity_defer:
                completed=adapter.read_record(directory/'intent.json')
                for key in ('lease','binding','request'):self.assertEqual(completed[key],intent[key])
                self.assertEqual(completed['history'][:2],intent['history'])
            self.assertEqual(state['unit_gate']['disposition'],'rework' if verdict=='rework' else 'approved')
            self.assertFalse(state['unit_gate']['accepted_delivery'])
            if template and verdict == 'rework':
                self.current.refresh()
                self.assertEqual(state['unit_gate']['disposition'],'rework')
            packet=unit_review.qualify_native_review(self.current,issue.identifier)
            self.assertNotIn('snapshot',packet)
            self.assertIsNone(packet['action'])
            self.assertEqual(native_path.read_bytes(),original_native)
            for p, raw in before.items():self.assertEqual(p.read_bytes(),raw,str(p))
            self.current=adapter.CurrentWork(self.runtime)
            asyncio.run(self.current.continue_validation())
            self.assertEqual(spawn.await_count,2 if capacity_defer else 1)
            self.assertEqual(self.current._check_unit_review(packet),packet['unit_binding'])
            tampered=dict(packet,native_session_id='invented-external-reviewer')
            with self.assertRaises(AdmissionError):self.current._check_unit_review(tampered)
            original=path.read_bytes();path.write_text('{}')
            with self.assertRaises(AdmissionError):self.current._check_unit_review(packet)
            path.write_bytes(original)
            incoming=self.runtime/('unit-review-'+issue.identifier+'.json')
            self.assertEqual(adapter.read_record(incoming),packet)
            if template and verdict == 'rework':
                native, _, _ = self.adapted()
                owner = native.Orchestrator(self.runtime/'workflow.yaml')
                self.assertEqual(owner._load_workflow(), [])
                client = self.client(issue)
                for name in ('update_issue_state','post_comment','fetch_comments'):
                    setattr(client,name,AsyncMock())
                owner._linear = client
                owner._schedule_retry = unittest.mock.Mock()
                owner._publish_run_report = AsyncMock()
                owner.ledger.record_terminal = unittest.mock.Mock()
                task = self.current.state['tasks'][issue.identifier]
                receipt = runtime/'attempts'/('review-'+issue.identifier)/'receipt.json'
                saved = receipt.read_bytes()
                for change in ('tampered','missing'):
                    with self.subTest(receipt=change):
                        if change == 'tampered':receipt.write_text('{}')
                        else:receipt.unlink()
                        self.current.refresh()
                        self.assertEqual(task['unit_gate']['disposition'],'waiting')
                        self.assertEqual(task['defer'],'unit_review_held')
                        asyncio.run(owner._handle_gate_responses())
                        self.assertNotIn('handled',task['unit_gate'])
                        receipt.write_bytes(saved)
                        self.current.refresh()
                        self.assertEqual(task['unit_gate']['disposition'],'rework')
                capacity = adapter.read_record(runtime/'capacity-policy.json')
                leases = Pool(capacity['symphony']['pool_path'],capacity).status()
                with self.assertRaisesRegex(AdmissionError,'terminal_hold'):
                    self.current.native_review_template_policy(issue.identifier,materialize=True)
                asyncio.run(self.current.continue_native_review(issue.identifier))
                self.assertEqual(task['native_review']['status'],'held')
                self.assertEqual(task['native_review']['hold'],'native_review_template_terminal_hold')
                asyncio.run(owner._handle_gate_responses())
                gate = task['unit_gate']
                self.assertTrue(gate['handled'])
                self.assertEqual(gate['disposition'],'rework')
                self.assertEqual(gate['unit_review'],'rework')
                self.assertFalse(gate['accepted_delivery'])
                retained_gate = dict(gate)
                for _ in range(2):
                    self.current.refresh()
                    asyncio.run(owner._handle_gate_responses())
                    asyncio.run(self.current.continue_native_review(issue.identifier))
                self.assertEqual(task['unit_gate'],retained_gate)
                self.assertFalse(self.current.state['accepted_delivery'])
                self.assertEqual(Pool(capacity['symphony']['pool_path'],capacity).status(),leases)
                self.assertEqual(spawn.await_count,1)
                native_command.assert_called_once()
                owner._schedule_retry.assert_not_called()
                owner._publish_run_report.assert_not_awaited()
                owner.ledger.record_terminal.assert_not_called()
                client.update_issue_state.assert_not_awaited()
                client.post_comment.assert_not_awaited()
                client.fetch_comments.assert_not_awaited()
            # Unknown launch recovery cannot create another computation or lease.
            receipt=runtime/'attempts'/('review-'+issue.identifier)/'receipt.json'
            saved=receipt.read_bytes();receipt.unlink()
            asyncio.run(self.current.continue_validation())
            self.assertEqual(self.current.state['tasks'][issue.identifier]['native_review']['status'],'held')
            self.assertEqual(spawn.await_count,2 if capacity_defer else 1)
            receipt.write_bytes(saved)
            if template:
                bound=state['native_review']['derivation']
                self.assertEqual(bound['author_receipt']['sha256'],adapter.file_sha(native_path))
                for target in (template_path,native_path,origin_runtime/'original-validation-receipt.json',candidate/'tests/task230.py'):
                    raw=target.read_bytes();target.write_bytes(raw+b' ')
                    with self.assertRaises(Exception):self.current.native_review_context(issue.identifier)
                    target.write_bytes(raw)
                self.current.config['native_review_template']=dict(path=str(path),sha256=adapter.file_sha(path))
                with self.assertRaises(AdmissionError):self.current.native_review_context(issue.identifier)
            else:
                self.current.config.pop('native_review_policies')
                with self.assertRaisesRegex(AdmissionError,'policy_unavailable'):
                    self.current.native_review_context(issue.identifier)

    def test_fixed_gateway_process_fixture_staged_native_original(self):
        self.fixed_gateway_process_fixture(staged=True)

    def test_fixed_gateway_process_fixture_reviewed_source(self):
        self.fixed_gateway_process_fixture(staged=True, reviewed=True)

    def fixed_gateway_process_fixture(self, *, staged, reviewed=False, native_review=False):
        """Fixture custody is controlled here; this is not live authentication."""
        from offmenu.delivery.integration import Controller
        from symphony_capacity import digest
        # A private controlled commit pins candidate transport bytes, without
        # touching this workspace's HEAD or using shell interpolation.
        original_source = Path(__file__).resolve().parents[2]
        shutil.copytree(original_source/'tools/delivery', self.source/'tools/delivery', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'), copy_function=self.copy_fixture_source)
        shutil.copytree(original_source/'src', self.source/'src', dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns('__pycache__'), copy_function=self.copy_fixture_source)
        self.write(self.source/'tools/delivery/capacity-policy.json', self.policy)
        def git_at(path, *args):
            result = subprocess.run(['/usr/bin/git','-C',str(path),*args], check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                env={'PATH':'/usr/bin:/bin','HOME':str(self.temp),'LANG':'C.UTF-8'})
            return result.stdout.strip()
        def commit(path):
            git_at(path,'init','-b','feature/test-current')
            git_at(path,'add','.')
            git_at(path,'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                   '-c','commit.gpgsign=false','commit','-m','Controlled fixture')
            return git_at(path,'rev-parse','HEAD')
        checkout = self.temp/'checkout-230'
        checkout.mkdir()
        (checkout/'fixture.txt').write_text('immutable fixture\n')
        if reviewed:
            import stokowski_operations as operations
            for name in operations.REVIEWED_TESTS:
                target=checkout/'tests/delivery'/(name+'.py')
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_text('# SYNTHETIC accepted control fixture\n')
        self.task_head = commit(checkout)
        # Fault only in the committed private fixture: publish succeeds, then
        # the writer never replies before the real gateway deadline. The fixed
        # transport must kill/reap it and reconcile via a status-only child.
        entry = self.source/'tools/delivery/stokowski_unit_review.py'
        code = entry.read_text().replace(
            'result = handle(decode(raw))',
            'request = decode(raw)\n'
            '        result = handle(request)\n'
            '        if request["mode"] == "write":\n'
            '            import time; time.sleep(20)')
        entry.write_text(code)
        source_head = commit(self.source)
        self.git.side_effect = lambda args, **kw: (
            subprocess.run(args, check=True, stdout=subprocess.PIPE,
                **dict({'stderr':subprocess.PIPE}, **kw)).stdout)
        config = json.loads((self.runtime/'current.json').read_text())
        config['source_head'] = source_head
        config['source_sha256'] = {str(p.relative_to(self.source)):adapter.file_sha(p)
            for base in ('tools/delivery','src/offmenu/delivery')
            for p in (self.source/base).rglob('*') if p.is_file() and p.suffix in ('.py','.mjs','.json') and '__pycache__' not in p.parts}
        self.write(self.runtime/'current.json',config)
        state = json.loads(self.current.state_path.read_text())
        state['config_sha256'] = adapter.file_sha(self.runtime/'current.json')
        self.write(self.current.state_path,state)
        self.current = adapter.CurrentWork(self.runtime)
        issue,runtime,owner,client,packet,journal,key = self.review_fixture(template_coding=native_review in ('template','capacity-defer','template-rework'))
        snapshot = packet['snapshot']
        # Original typed Python authorities, deliberately lossy through JS JSON.
        numbers = {'duration_seconds':1e-7, 'integral':1.0,
                   'large':9007199254740991, 'large_float':1e15,
                   'fraction':1.5, 'zero':0, 'threshold':1e-6,
                   '10':'ten', '2':'two', '\ue000':'BMP', '\U00010000':'astral',
                   'text':'café \U0001f600'}
        snapshot['review']['metadata'] = numbers
        packet['validation_receipt']['metadata'] = numbers
        _, operation_state = journal.read(key)
        operation_state['receipt_sha256'] = digest(packet['validation_receipt'])
        journal.save(key,operation_state,'controlled-original-numeric-receipt')
        receipt_path = runtime/'original-validation-receipt.json'
        self.write(receipt_path,packet['validation_receipt'])
        original_receipt_sha = digest(packet['validation_receipt'])
        snapshot['review'].update(requested_model='review-model',requested_provider='existing-route',
            resolved_model=None,resolution_status='unknown')
        snapshot['review']['evidence_sha256'] = digest({k:v for k,v in snapshot['review'].items()
            if k != 'evidence_sha256'})
        if native_review:
            native_path=runtime/'attempts'/issue.identifier/'receipt.json'
            native=json.loads(native_path.read_text())
            author_binding=adapter.read_record(native_path.parent/'intent.json')['binding']
            from symphony_capacity import Pool
            author_pool=Pool(self.policy['symphony']['pool_path'],self.policy)
            proof=adapter.read_record(runtime/'provider-proof.json')
            if native_review not in ('template','capacity-defer','template-rework'):
                author_pool.admit(native['lease'],author_binding,proof,
                    dict(cpu_millis=64000,available_memory_bytes=128*1024**3,available_disk_bytes=1024**4))
                author_pool.finish(native['lease'],True,'succeeded')
            if native_review not in ('template','capacity-defer','template-rework'):
                native.update(origin='native-coding',session_id='synthetic-author-session',
                              parent_binding=author_binding)
                self.write(native_path,native)
            packet['unit_binding']=self.current.gate_binding(issue)
            bindings=json.loads((runtime/'validation-bindings.json').read_text())
            bindings['issues'][issue.identifier]['native_receipt_sha256']=adapter.file_sha(native_path)
            self.write(runtime/'validation-bindings.json',bindings)
        if staged:
            # Fully qualified synthetic native-v1 original, including actual Git
            # candidate objects and an original workspace at its admitted base.
            import stokowski_operations as operations
            from stokowski_operations import bridge_arguments
            candidate = self.temp/'candidate'
            git_at(self.temp, 'clone', str(checkout), str(candidate))
            for name in packet['integration_binding']['outputs']:
                target = candidate/name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((runtime/'workspaces'/issue.identifier/name).read_bytes())
            git_at(candidate, 'add', '.')
            git_at(candidate, '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                   '-c','commit.gpgsign=false','commit','-m','Synthetic native output')
            candidate_head = git_at(candidate, 'rev-parse', 'HEAD')
            git_at(checkout, 'fetch', str(candidate), 'feature/test-current')
            shutil.copytree(checkout/'.git', runtime/'workspaces'/issue.identifier/'.git',dirs_exist_ok=True)
            spec, _ = journal.read(key)
            if native_review:
                original_task=json.loads((runtime/'manifest.json').read_text())['tasks'][issue.identifier]
                spec['acceptance_sha256']=digest(dict(task=original_task,
                    native_receipt_sha256=adapter.file_sha(native_path),profile=spec['profile']))
            spec.update(head=candidate_head,
                runner_sha256=adapter.file_sha(self.source/'tools/delivery/windmill_runner.py'),
                executor_sha256=adapter.file_sha(operations.__file__))
            self.stack.enter_context(patch.object(operations, 'POLICY', self.source/'tools/delivery/capacity-policy.json'))
            key = journal.prepare(spec)
            _, operation_state = journal.read(key)
            receipt = packet['validation_receipt']
            receipt.update(job_id=operation_state['logical_job_id'], runner_sha256=spec['runner_sha256'],
                command_sha256=hashlib.sha256(bridge_arguments(spec)['command'].encode()).hexdigest())
            operation_state.update(status='succeeded', receipt_sha256=digest(receipt),
                accepted_output_sha256=spec['outputs'], acceptance_sha256=spec['acceptance_sha256'])
            journal.save(key, operation_state, 'synthetic-native-stage-proof')
            self.write(receipt_path, receipt)
            original_receipt_sha = digest(receipt)
            bindings = json.loads((runtime/'validation-bindings.json').read_text())
            bindings['history'] = []
            bindings['issues'][issue.identifier].update(operation_key=key, source_head=candidate_head,
                derivation_reason=None)
            self.write(runtime/'validation-bindings.json', bindings)
            packet['integration_binding'].update(head=candidate_head, validation_operation_key=key)
            snapshot['validation'].update(head=candidate_head, operation_key=key)
            snapshot['review']['head'] = candidate_head
            snapshot['review']['evidence_sha256'] = digest({k:v for k,v in snapshot['review'].items()
                if k != 'evidence_sha256'})
            original_entry = self.entries[0]
            _, identity = self.current.validation_binding(issue.identifier, original_entry)
            stage_runtime = runtime
            if staged != 'normal':
                stage_runtime = self.root/'review-stage'
                stage_runtime.mkdir()
                for name in ('requests','attempts','workspaces'):
                    (stage_runtime/name).mkdir()
                for name in ('capacity-policy.json','installation.json','provider-proof.json'):
                    shutil.copyfile(runtime/name, stage_runtime/name)
                shutil.copyfile(runtime/'requests'/f'{issue.identifier}.json',
                                stage_runtime/'requests'/f'{issue.identifier}.json')
                pins = {str(runtime/name):adapter.file_sha(runtime/name) for name in (
                    'current-admission.json','manifest.json','capacity-policy.json','installation.json',
                    'provider-proof.json','requests/'+issue.identifier+'.json','validation-bindings.json',
                    *['attempts/'+issue.identifier+'/'+n for n in ('intent.json','dispatch-intent.json','receipt.json')],
                    *(['original-validation-receipt.json'] if native_review else []))}
                manifest = json.loads((runtime/'manifest.json').read_text())
                task = manifest['tasks'][issue.identifier]
                task.update(stage='review', input_paths=task['allowed_paths'], allowed_paths=[],
                    stage_binding=dict(entry=original_entry, identity=identity, inputs=pins))
                # Stage admission selects a distinct actual source at the same base.
                stage_source = self.temp/'stage-source'
                git_at(self.temp, 'clone', str(checkout), str(stage_source))
                self.write(stage_runtime/'manifest.json', manifest)
                admission = json.loads((runtime/'current-admission.json').read_text())
                admission.update(source=str(stage_source), inputs=pins,
                    manifest_sha256=adapter.file_sha(stage_runtime/'manifest.json'))
                self.write(stage_runtime/'current-admission.json', admission)
                self.runtime = self.root/'stage-current'
                self.runtime.mkdir()
                for name in ('current.json','installation.json','workflow.yaml','capacity-policy.json'):
                    shutil.copyfile(self.root/'current'/name, self.runtime/name)
                self.write(self.catalog, dict(version=1, entries=[dict(original_entry,
                    runtime=str(stage_runtime), admission_sha256=adapter.file_sha(stage_runtime/'current-admission.json'))]))
                self.current = adapter.CurrentWork(self.runtime)
                self.current.state['tasks'][issue.identifier]['unit_gate'] = dict(
                    binding=self.current.gate_binding(issue), disposition='waiting', accepted_delivery=False)
                self.current.save()
                for name in ('validation-bindings.json','operations','original-validation-receipt.json'):
                    self.assertFalse((stage_runtime/name).exists())
                self.assertEqual(list((stage_runtime/'attempts').iterdir()), [])
                self.assertEqual(list((stage_runtime/'workspaces').iterdir()), [])
        if native_review:
            if staged == 'normal':
                self.current.state['tasks'][issue.identifier]['unit_gate'] = dict(
                    binding=self.current.gate_binding(issue),disposition='waiting',accepted_delivery=False)
                self.current.save()
            self.native_review_phase_fixture(issue,runtime,stage_runtime,candidate,spec,
                                             verdict='rework' if native_review in ('rework','template-rework') else 'accept',template=native_review in ('template','capacity-defer','template-rework'),
                                             capacity_defer=native_review=='capacity-defer')
            return
        if reviewed:
            from test_stokowski_nonimplementation_stage import reviewed_records
            mirror=runtime/'workspaces'/issue.identifier
            shutil.copytree(candidate,mirror,dirs_exist_ok=True,
                copy_function=lambda src,dst: dst if Path(dst).exists() and '/objects/' in str(dst) else shutil.copy2(src,dst))
            origin_runtime,spec,key,binding=reviewed_records(self,mirror,self.task_head,candidate_head,
                packet['integration_binding']['outputs'],issue.identifier,issue.id)
            # New validation operation, with historical manual receipt files only.
            from stokowski_operations import Journal,bridge_arguments
            journal=Journal(origin_runtime/'operations')
            _,state=journal.read(key)
            receipt=packet['validation_receipt']
            receipt.update(job_id=state['logical_job_id'],runner_sha256=spec['runner_sha256'],
                command_sha256=hashlib.sha256(bridge_arguments(spec)['command'].encode()).hexdigest())
            state.update(status='succeeded',receipt_sha256=digest(receipt),accepted_output_sha256=spec['outputs'],
                acceptance_sha256=spec['acceptance_sha256'])
            journal.save(key,state,'SYNTHETIC-independent-completed-validation')
            receipt_path=origin_runtime/'original-validation-receipt.json';self.write(receipt_path,receipt)
            original_receipt_sha=digest(receipt)
            packet['integration_binding'].update(validation_operation_key=key)
            snapshot['validation'].update(operation_key=key)
            snapshot['review']['author']=spec['origin']['author']
            snapshot['review']['evidence_sha256']=digest({k:v for k,v in snapshot['review'].items() if k!='evidence_sha256'})
            manifest['tasks'][issue.identifier]['stage_binding']=binding
            self.write(stage_runtime/'manifest.json',manifest)
            admission.update(inputs=binding['inputs'],manifest_sha256=adapter.file_sha(stage_runtime/'manifest.json'))
            self.write(stage_runtime/'current-admission.json',admission)
            catalog=json.loads(self.catalog.read_text())
            catalog['entries'][0]['admission_sha256']=adapter.file_sha(stage_runtime/'current-admission.json')
            self.write(self.catalog,catalog)
            owner_state=json.loads(self.current.state_path.read_text())
            owner_state['references'][issue.identifier]=catalog['entries'][0]
            owner_state['bindings'][issue.identifier]=digest(catalog['entries'][0])
            self.write(self.current.state_path,owner_state)
            self.current=adapter.CurrentWork(self.runtime)
            packet['unit_binding']=self.current.gate_binding(issue)
            self.current.state['tasks'][issue.identifier]['unit_gate']=dict(binding=packet['unit_binding'],disposition='waiting',accepted_delivery=False)
            self.current.save()
            self.assertFalse((origin_runtime/'current-admission.json').exists())
            self.assertFalse((origin_runtime/'attempts').exists())
        b = packet['integration_binding']
        snapshot.update(observed_at=time.time(), automatic_integration_enabled=True,
            github=dict(repository=b['repository'],number=b['pr_number'],state='open',draft=False,
                head=b['head'],base=b['base'],head_branch=b['head_branch'],base_branch='develop',mergeable=True))
        claim = self.temp/'.delivery/integration'
        predecessor = Controller(claim/'previous',dict(b,head='9'*40),claim)
        predecessor.run(snapshot)  # Safe stale candidate, retained as historical shared evidence.
        controller = Controller(claim/'fixture',b,claim)
        control_input = self.temp/'control-input.json'
        self.write(control_input,dict(binding=b,snapshot=snapshot,directory=str(controller.directory),claim=str(claim)))
        controlled = subprocess.run([sys.executable,'-c',
            'import json,sys; from offmenu.delivery.integration import Controller; '
            'v=json.load(open(sys.argv[1])); '
            'print(json.dumps(Controller(v["directory"],v["binding"],v["claim"]).run(v["snapshot"])))',
            str(control_input)],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            env={'PATH':'/usr/bin:/bin','PYTHONPATH':str(original_source/'src'),'LANG':'C.UTF-8'})
        packet['decision'] = json.loads(controlled.stdout)
        self.assertEqual(packet['decision']['status'],'merge-intent')
        context = dict(source_head=source_head,source_sha256=config['source_sha256'],
            python_sha256=adapter.file_sha(Path(sys.executable).resolve()), actor_uid=os.getuid(),
            runtime=str(self.runtime), runtime_root=str(self.root), workspace_roots=([str(stage_source),str(mirror)] if reviewed else ([str(stage_source),str(checkout)] if staged else [str(checkout)])),
            claim_root=str(claim),controller_directory=str(controller.directory),issue=issue.identifier,
            unit_binding=packet['unit_binding'],validation_receipt=packet['validation_receipt'],
            validation_receipt_source=dict(path=str(receipt_path),sha256=adapter.file_sha(receipt_path)))
        for p in self.temp.rglob('*'):
            if not p.is_symlink():
                p.chmod(0o700 if p.is_dir() else 0o600)
        owner_before = self.current.state_path.read_bytes()
        native_path = runtime/'attempts'/issue.identifier/'receipt.json'
        frozen = {p:p.read_bytes() for p in (receipt_path,native_path,runtime/'operations/operations.sqlite',
            controller.directory/'graph.sqlite',controller.directory/'state.json',
            controller.directory/'repository-claim.json',claim/'repository-claim.json',claim/'active-owner.json')}
        def local_status(selected_context=context):
            request = dict(version=2, mode='status',
                payload=json.dumps(dict(context=selected_context,
                    envelope={k:packet[k] for k in ('snapshot','decision')})),
                evidence=json.dumps(packet))
            return subprocess.run([sys.executable,str(entry)],
                input=json.dumps(request), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                timeout=10, env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        before = local_status()
        self.assertEqual((before.returncode, json.loads(before.stdout).get('status')),
                         (0, 'absent'), before.stdout+before.stderr)
        if staged and not reviewed:
            def refused(selected_context=context):
                result = local_status(selected_context)
                self.assertEqual(result.returncode, 1, result.stdout+result.stderr)
                self.assertEqual(json.loads(result.stdout), {'error':'local_review_refused'})
                self.assertEqual(result.stderr, '')
                self.assertFalse((self.runtime/('unit-review-'+issue.identifier+'.json')).exists())
            # The selected stage still needs its own admitted inputs and custody.
            for target in (stage_runtime/'current-admission.json', stage_runtime/'manifest.json',
                           stage_runtime/'requests'/f'{issue.identifier}.json',
                           stage_runtime/'installation.json', stage_runtime/'capacity-policy.json'):
                raw = target.read_bytes()
                with self.subTest(stage_drift=target.name):
                    target.write_bytes(raw+b' ')
                    refused()
                    target.write_bytes(raw)
            stage_proof = stage_runtime/'provider-proof.json'
            stage_proof.chmod(0o644)
            refused()
            stage_proof.chmod(0o600)
            # Original pinned bytes and original OS custody both remain gates.
            for target in (runtime/'requests'/f'{issue.identifier}.json', native_path, receipt_path):
                raw = target.read_bytes()
                with self.subTest(original_drift=target.name):
                    target.write_bytes(raw+b' ')
                    refused()
                    target.write_bytes(raw)
            receipt_path.chmod(0o644)
            refused()
            receipt_path.chmod(0o600)
            misplaced = stage_runtime/'mislocated-receipt.json'
            misplaced.write_bytes(receipt_path.read_bytes())
            misplaced.chmod(0o600)
            refused(dict(context, validation_receipt_source=dict(
                path=str(misplaced), sha256=adapter.file_sha(misplaced))))
            for permitted in ([str(checkout)], [str(stage_source)]):
                refused(dict(context, workspace_roots=permitted))
            output_path = runtime/'workspaces'/issue.identifier/next(iter(b['outputs']))
            moved_output = self.temp/'mislocated-output'
            output_path.rename(moved_output)
            output_path.symlink_to(moved_output)
            refused()
            output_path.unlink()
            moved_output.rename(output_path)
            output_path.chmod(0o644)
            refused()
            output_path.chmod(0o600)
            # Even an owner-pinned stage cannot select a foreign original entry.
            # Rebind only synthetic admission records; do not bypass qualification.
            records = (stage_runtime/'manifest.json', stage_runtime/'current-admission.json',
                       self.catalog, self.current.state_path)
            originals = {p:p.read_bytes() for p in records}
            manifest['tasks'][issue.identifier]['stage_binding']['entry'] = dict(
                original_entry, issue_id='00000000-0000-4000-8000-000000000999')
            self.write(records[0], manifest)
            admission['manifest_sha256'] = adapter.file_sha(records[0])
            self.write(records[1], admission)
            catalog = json.loads(self.catalog.read_text())
            catalog['entries'][0]['admission_sha256'] = adapter.file_sha(records[1])
            self.write(self.catalog, catalog)
            state = json.loads(self.current.state_path.read_text())
            state['references'][issue.identifier] = catalog['entries'][0]
            state['bindings'][issue.identifier] = digest(catalog['entries'][0])
            self.write(self.current.state_path, state)
            refused()
            for path, raw in originals.items():
                path.write_bytes(raw)
            self.assertEqual(json.loads(local_status().stdout)['status'], 'absent')
        payload = self.temp/'gateway-input.json'
        self.write(payload,dict(context=context,packet=packet))
        result = subprocess.run(['/usr/bin/node',str(original_source/'tests/delivery/test-integration-gateway.mjs'),
            '--local-review-fixture',str(payload),str(self.source/'tools/delivery/integration-gateway.mjs')],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=45,
            env={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8'})
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('tests 18',result.stdout)
        incoming = self.runtime/('unit-review-'+issue.identifier+'.json')
        self.assertTrue(incoming.exists())
        expected = json.dumps(packet,sort_keys=True,separators=(',', ':')).encode()
        self.assertEqual(incoming.read_bytes(),expected)
        retained = json.loads(incoming.read_bytes())
        self.assertIs(type(retained['snapshot']['review']['metadata']['integral']),float)
        self.assertEqual(digest(retained['validation_receipt']),original_receipt_sha)
        _, unchanged_state = journal.read(key)
        self.assertEqual(unchanged_state['receipt_sha256'],original_receipt_sha)
        self.assertEqual(self.current.state_path.read_bytes(),owner_before)
        for path,raw in frozen.items():
            self.assertEqual(path.read_bytes(),raw)
        read_only = adapter.CurrentWork(self.runtime, read_only=True)
        read_only._check_unit_review(retained)
        self.assertEqual(self.current.state_path.read_bytes(), owner_before)
        incoming_stat = incoming.stat()
        self.assertEqual(json.loads(local_status().stdout)['status'], 'retained')
        self.assertEqual((incoming.stat().st_ino, incoming.stat().st_mtime_ns),
                         (incoming_stat.st_ino, incoming_stat.st_mtime_ns))
        reopened = adapter.CurrentWork(self.runtime)
        gate = reopened.state['tasks'][issue.identifier]['unit_gate']
        self.assertEqual(gate['disposition'],'approved')
        self.assertFalse(gate['accepted_delivery'])
        consumed = incoming.read_bytes()
        reopened.refresh()
        self.assertEqual(incoming.read_bytes(),consumed)
        client.update_issue_state.assert_not_awaited()
        owner.ledger.record_terminal.assert_not_called()

    def test_owner_observation_once_reopen_and_native_consumption(self):
        issue,runtime,owner,client,packet,journal,key = self.review_fixture()
        writer = self.current.unit_review_writer(lambda envelope:packet)
        envelope = {k:packet[k] for k in ('snapshot','decision')}
        with (self.root/'coordinator.lock').open('a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
            writer(envelope)  # No root lock reacquisition/deadlock.
            writer(envelope)
        self.assertEqual(self.current.state['tasks'][issue.identifier]['unit_gate']['disposition'],'waiting')
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(reopened.state['tasks'][issue.identifier]['unit_gate']['disposition'],'approved')
        asyncio.run(owner._handle_gate_responses())
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        self.assertTrue(gate['handled'])
        asyncio.run(owner._handle_gate_responses())
        self.assertFalse(gate['accepted_delivery'])
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()
        owner._schedule_retry.assert_not_called()
        owner.ledger.record_terminal.assert_not_called()

    def test_evidence_hold_revokes_unhandled_output_approval_until_restored(self):
        issue,runtime,owner,client,packet,journal,key = self.review_fixture()
        self.current.unit_review_writer(lambda envelope:packet)({k:packet[k] for k in ('snapshot','decision')})
        self.current.refresh()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        self.assertEqual(gate['disposition'],'approved')
        target = runtime/'workspaces'/issue.identifier/'tests/task230.py'
        original = target.read_bytes()
        target.write_bytes(b'changed after approval')
        asyncio.run(owner._handle_gate_responses())
        self.assertNotIn('handled',gate)
        self.assertEqual(gate['disposition'],'waiting')
        self.assertEqual(self.current.state['tasks'][issue.identifier]['defer'],'unit_review_held')
        target.write_bytes(original)
        asyncio.run(owner._handle_gate_responses())
        self.assertTrue(gate['handled'])
        self.assertNotIn('defer',self.current.state['tasks'][issue.identifier])
        client.update_issue_state.assert_not_awaited()
        owner._schedule_retry.assert_not_called()

    def test_evidence_hold_revokes_unhandled_journal_approval(self):
        issue,runtime,owner,client,packet,journal,key = self.review_fixture()
        self.current.unit_review_writer(lambda envelope:packet)({k:packet[k] for k in ('snapshot','decision')})
        self.current.refresh()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        spec,state = journal.read(key)
        journal.save(key,dict(state,status='unknown'),'controlled-post-approval-drift')
        asyncio.run(owner._handle_gate_responses())
        self.assertNotIn('handled',gate)
        self.assertEqual(gate['disposition'],'waiting')
        client.update_issue_state.assert_not_awaited()
        owner._schedule_retry.assert_not_called()

    def test_missing_incoming_evidence_cannot_consume_earlier_approval(self):
        issue,runtime,owner,client,packet,journal,key = self.review_fixture()
        self.current.unit_review_writer(lambda envelope:packet)({k:packet[k] for k in ('snapshot','decision')})
        self.current.refresh()
        gate = self.current.state['tasks'][issue.identifier]['unit_gate']
        (self.runtime/('unit-review-'+issue.identifier+'.json')).unlink()
        asyncio.run(owner._handle_gate_responses())
        self.assertNotIn('handled',gate)
        self.assertEqual(gate['disposition'],'waiting')
        client.update_issue_state.assert_not_awaited()

    def test_review_mismatches_hold_and_never_write_disposition(self):
        import copy
        issue,runtime,owner,client,packet,journal,key = self.review_fixture()
        with self.assertRaises(AdmissionError):
            self.current.unit_review_writer()
        mutations = [
            ('unit_binding','request_sha256','0'*64),('unit_binding','native_receipt_sha256','0'*64),
            ('unit_binding','admission_sha256','0'*64),('unit_binding','project_id','foreign'),
            ('integration_binding','issue_id','00000000-0000-4000-8000-000000000999'),
            ('integration_binding','owner','foreign-owner'),('review','author','foreign-author'),
            ('integration_binding','outputs',{}),('integration_binding','head','0'*40),
            ('decision','status','awaiting-validation'),('decision','merge_effect','refused'),
            ('review','reviewer','existing-owner'),('review','evidence_sha256','0'*64),
            ('review','model','changed'),('review','verdict','changes-requested')]
        for section,name,value in mutations:
            bad = copy.deepcopy(packet)
            (bad['snapshot']['review'] if section=='review' else bad[section])[name] = value
            with self.subTest(section=section,name=name), self.assertRaises((AdmissionError,KeyError)):
                self.current.unit_review_writer(lambda envelope:bad)({k:bad[k] for k in ('snapshot','decision')})
        spec,state = journal.read(key)
        for change in [dict(status='unknown'),dict(cancel_requested=True),dict(accepted_output_sha256={})]:
            journal.save(key,dict(state,**change),'controlled-drift')
            with self.assertRaises(AdmissionError):
                self.current._check_unit_review(packet)
        journal.save(key,state,'restored')
        original_database = (runtime/'operations/operations.sqlite').read_bytes()
        with journal.db() as db:
            changed = dict(spec, head='9'*40)
            db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(changed),key))
        with self.assertRaises(AdmissionError):
            self.current._check_unit_review(packet)
        (runtime/'operations/operations.sqlite').write_bytes(original_database)
        output = runtime/'workspaces'/issue.identifier/'tests/task230.py'
        original_output = output.read_bytes()
        output.write_bytes(b'changed output')
        with self.assertRaises(AdmissionError):
            self.current._check_unit_review(packet)
        output.write_bytes(original_output)
        directory = runtime/'attempts'/issue.identifier
        original = (directory/'receipt.json').read_bytes()
        for change in [dict(status='cancelled'),dict(status='unknown'),dict(child_tree_gone=False)]:
            self.write(directory/'receipt.json',dict(json.loads(original),**change))
            with self.assertRaises(AdmissionError):
                self.current._check_unit_review(packet)
        (directory/'receipt.json').write_bytes(original)
        writer = self.current.unit_review_writer(lambda envelope:packet)
        writer({k:packet[k] for k in ('snapshot','decision')})
        conflict = copy.deepcopy(packet); conflict['extra']='conflicting replay'
        with self.assertRaises(AdmissionError):
            self.current.unit_review_writer(lambda envelope:conflict)({k:conflict[k] for k in ('snapshot','decision')})
        self.assertEqual(self.current.state['tasks'][issue.identifier]['unit_gate']['disposition'],'waiting')

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

    def test_absent_gate_restart_rebuilds_durable_waiting_binding_once(self):
        issue, runtime, _, _ = self.bound_gate()
        expected = self.current.gate_binding(issue)
        self.current.state['tasks'][issue.identifier].pop('unit_gate')
        self.current.save()
        self.current = adapter.CurrentWork(self.runtime)
        native, _, _ = self.adapted()
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        owner._load_workflow()
        client = self.client(issue)
        for name in ('update_issue_state','post_comment','fetch_comments','fetch_issues_by_states'):
            setattr(client, name, AsyncMock())
        owner._linear = client
        save = self.current.save
        def durable_save():
            # The new gate reaches disk before the pending memory registry.
            self.assertEqual(owner._pending_gates, {})
            save()
        with patch.object(native, 'run_turn') as coding, \
             patch.object(self.current, 'save', side_effect=durable_save):
            asyncio.run(owner._rebuild_gates_from_linear())
            coding.assert_not_called()
        gate = {'binding':expected,'disposition':'waiting'}
        saved = self.current.state_path.read_bytes()
        self.assertEqual(json.loads(saved)['tasks'][issue.identifier]['unit_gate'], gate)
        self.assertEqual(owner._pending_gates, {issue.id:'evidence-pending'})
        self.assertEqual(owner._issue_current_state[issue.id], 'evidence-pending')
        owner._pending_gates.clear()
        owner._issue_current_state.clear()
        asyncio.run(owner._rebuild_gates_from_linear())
        self.assertEqual(self.current.state_path.read_bytes(), saved)
        self.assertEqual(owner._pending_gates, {issue.id:'evidence-pending'})
        reopened = adapter.CurrentWork(self.runtime)
        self.assertEqual(reopened.state['tasks'][issue.identifier]['unit_gate'], gate)
        self.assertFalse(reopened.state['accepted_delivery'])
        self.assertEqual(self.select(issue), [])
        for name in ('update_issue_state','post_comment','fetch_comments','fetch_issues_by_states'):
            getattr(client, name).assert_not_awaited()

    def test_absent_gate_rebuild_holds_unqualified_original_evidence(self):
        issue, runtime, owner, client = self.bound_gate()
        task = self.current.state['tasks'][issue.identifier]
        task.pop('unit_gate')
        self.current.save()
        owner._pending_gates.clear()
        owner._issue_current_state.clear()
        directory = runtime/'attempts'/issue.identifier
        cases = [
            ('receipt.json', None), ('receipt.json', {}),
            ('receipt.json', {'status':'unknown'}),
            ('receipt.json', {'status':'running'}),
            ('receipt.json', {'status':'cancelled'}),
            ('receipt.json', {'child_tree_gone':False}),
            ('receipt.json', {'accepted_delivery':True}),
            ('receipt.json', {'binding_sha256':'0'*64}),
            ('receipt.json', {'lease':'wrong-operation'}),
            ('dispatch-intent.json', None),
            ('dispatch-intent.json', {'expected_lease':'wrong-operation'}),
            ('dispatch-intent.json', {'request_sha256':'0'*64}),
            (runtime/'requests'/(issue.identifier+'.json'), {'prompt':'changed request'}),
            ('intent.json', None),
            ('intent.json', {'binding':{}}),
        ]
        for name, change in cases:
            with self.subTest(name=name, change=change):
                path = directory/name
                original = path.read_bytes()
                if change is None:
                    path.unlink()
                else:
                    self.write(path, dict(json.loads(original), **change) if change else {})
                asyncio.run(owner._rebuild_gates_from_linear())
                self.assertNotIn('unit_gate', task)
                self.assertEqual(owner._pending_gates, {})
                self.assertEqual(owner._issue_current_state, {})
                path.write_bytes(original)
        for cancel in (runtime/'cancel.json', self.runtime/'cancel.json'):
            self.write(cancel, {'reason':'synthetic cancellation'})
            asyncio.run(owner._rebuild_gates_from_linear())
            self.assertNotIn('unit_gate', task)
            cancel.unlink()
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()
        client.fetch_comments.assert_not_awaited()
        owner._schedule_retry.assert_not_called()
        owner.ledger.record_terminal.assert_not_called()

    def test_rebuild_never_overwrites_existing_conflicting_or_handled_gate(self):
        issue, _, owner, client = self.bound_gate()
        task = self.current.state['tasks'][issue.identifier]
        original = json.loads(json.dumps(task['unit_gate']))
        gates = [{}, dict(original, handled=True),
                 dict(original, binding=dict(original['binding'], request_sha256='0'*64))]
        for gate in gates:
            with self.subTest(gate=gate):
                task['unit_gate'] = gate
                self.current.save()
                owner._pending_gates.clear()
                asyncio.run(owner._rebuild_gates_from_linear())
                self.assertEqual(task['unit_gate'], gate)
                self.assertEqual(json.loads(self.current.state_path.read_text())['tasks'][issue.identifier]['unit_gate'], gate)
                self.assertEqual(owner._pending_gates, {})
        client.update_issue_state.assert_not_awaited()
        client.post_comment.assert_not_awaited()

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

    def test_native_service_delegation_keeps_project_credentials_out_of_child_environment(self):
        import stokowski.config as config
        original_env = config.ServiceConfig.agent_env
        original_key = config.ServiceConfig.resolved_api_key
        native, _, _ = self.adapted()
        self.assertIs(config.ServiceConfig.agent_env, original_env)
        self.assertIs(config.ServiceConfig.resolved_api_key, original_key)
        project = config.ProjectConfig(name='selected')
        service = config.ServiceConfig(projects=[project])
        with patch.dict(os.environ, LINEAR_API_KEY='synthetic-secret', UNKNOWN_TOKEN='synthetic-secret'):
            self.assertEqual(service.resolved_api_key(), 'in-memory-only')
            self.assertEqual(service.agent_env(), project.agent_env())
            self.assertNotIn('LINEAR_API_KEY', service.agent_env())
            self.assertNotIn('UNKNOWN_TOKEN', service.agent_env())

    def test_model_observation_and_stopped_child_control_native_projection(self):
        native, _, _ = self.adapted()
        for number, receipt, expected_status, expected_model in (
            (381, {'status':'succeeded','child_tree_gone':True}, 'succeeded', None),
            (382, {'status':'succeeded','child_tree_gone':True,
                   'resolved_model':'observed-route','resolution_status':'observed'}, 'succeeded', 'observed-route'),
            (383, {'status':'succeeded','child_tree_gone':True,
                   'resolved_model':adapter.MODEL,'resolution_status':'unknown'}, 'succeeded', None),
            (384, {'status':'succeeded','child_tree_gone':False}, 'failed', None),
            (385, {'status':'uncertain','child_tree_gone':False}, 'failed', None),
        ):
            with self.subTest(receipt=receipt):
                issue, runtime = self.qualify(number)
                async def spawn(*args, **kwargs):
                    self.write(runtime/'attempts'/issue.identifier/'receipt.json', receipt)
                    return SimpleNamespace(pid=98765,returncode=0,communicate=AsyncMock())
                with patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=spawn):
                    attempt = asyncio.run(self.turn(native,issue,runtime))
                self.assertEqual(attempt.status, expected_status)
                self.assertEqual(attempt.model, expected_model)
                self.assertEqual(self.select(issue), [])

    def test_native_caps_and_backoff_remain_authoritative(self):
        import stokowski.orchestrator as native
        methods = {name:getattr(native.Orchestrator,name) for name in (
            '_has_slot','_claim_slot','_release_slot','_is_eligible',
            '_dispatch','_on_worker_exit','_schedule_retry','_handle_retry')}
        issue, _ = self.qualify(386)
        native, _, _ = self.adapted()
        for name, method in methods.items():
            self.assertIs(getattr(native.Orchestrator,name), method)
        owner = native.Orchestrator(self.runtime/'workflow.yaml')
        self.assertEqual(owner._load_workflow(), [])
        owner.running = {str(i):object() for i in range(owner.cfg.agent.max_concurrent_agents)}
        self.assertFalse(owner._has_slot()[0])
        from stokowski.models import RunAttempt
        owner._schedule_retry = unittest.mock.Mock()
        owner._on_worker_exit(issue, RunAttempt(issue.id,issue.identifier,attempt=10,status='failed'))
        self.assertEqual(owner._schedule_retry.call_args.kwargs['delay_ms'],
                         owner.cfg.agent.max_retry_backoff_ms)

    def test_native_report_records_observed_model_and_preserves_request_fact(self):
        issue, runtime = self.qualify(387)
        native, _, _ = self.adapted()
        receipt = dict(status='succeeded',child_tree_gone=True,requested_model=adapter.MODEL,
                       resolved_model=None,resolution_status='unknown',accepted_delivery=False)
        self.write(runtime/'attempts'/issue.identifier/'receipt.json', receipt)
        client = SimpleNamespace(post_comment=AsyncMock())
        owner = SimpleNamespace(ledger=SimpleNamespace(record_stage=unittest.mock.Mock()),
                                _ensure_linear_client=lambda:client)
        attempt = SimpleNamespace(status='succeeded',total_tokens=0,model=None)
        asyncio.run(native.Orchestrator._publish_run_report(owner,issue,attempt,
                    runtime/'workspaces'/issue.identifier,'implement'))
        self.assertIsNone(owner.ledger.record_stage.call_args.kwargs['model'])
        summary = json.loads(client.post_comment.call_args.args[1].split('\n\n',1)[1])
        self.assertEqual(summary['requested_model'],adapter.MODEL)
        self.assertIsNone(summary['resolved_model'])
        self.assertEqual(summary['resolution_status'],'unknown')

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
        clone = self.stack.enter_context(patch.object(adapter.subprocess,'run',
            side_effect=lambda argv,**kwargs: Path(argv[-1]).mkdir(mode=0o775)))
        workspace = asyncio.run(native.ensure_workspace(self.runtime/'workspaces',issue.identifier,SimpleNamespace()))
        self.assertEqual(workspace.path,runtime/'workspaces'/issue.identifier)
        args = clone.call_args.args[0]
        self.assertIn('feature/test-current',args)
        self.assertEqual(args[-2],str(self.temp/'checkout-218'))
        self.assertNotEqual(args[-2],str(self.source))
        original_git = self.git_read
        self.git.side_effect = lambda args,**kwargs: ('wrong-head' if args[2] == str(workspace.path)
                                                    else original_git(args,**kwargs))
        with self.assertRaises(AdmissionError):
            asyncio.run(native.ensure_workspace(self.runtime/'workspaces',issue.identifier,SimpleNamespace()))
        self.assertEqual(clone.call_count,1)

    @unittest.skipUnless(shutil.which('setfacl'), 'POSIX ACL fixture needs setfacl')
    def test_new_workspace_removes_inherited_write_and_retains_coding_uid_gate(self):
        from coding_child_launch import owned_path
        import coding_child_launch
        issue, runtime = self.qualify(218)
        native, _, _ = self.adapted()
        runtime.chmod(0o700)
        (runtime/'workspaces').mkdir(mode=0o700, exist_ok=True)
        (runtime/'workspaces').chmod(0o700)
        # A clone may inherit ACL write bits despite the service's umask.
        def inherited_clone(argv, **kwargs):
            path = Path(argv[-1])
            path.mkdir()
            path.chmod(0o775)
            subprocess.check_call(['setfacl', '-m', 'd:u::rwx,d:g::rwx,d:o::---', str(path)])
            (path/'source-directory').mkdir()
            (path/'source-directory/checked-out.py').write_text('source')
            (path/'source-directory/run.sh').write_text('executable')
            (path/'source-directory/run.sh').chmod(0o775)
            self.assertTrue((path/'source-directory/checked-out.py').stat().st_mode & 0o020)
        with patch.object(adapter.subprocess, 'run', side_effect=inherited_clone):
            workspace = asyncio.run(native.ensure_workspace(
                self.runtime/'workspaces', issue.identifier, SimpleNamespace()))
        # Check the real confinement path contract, without a provider or child.
        with patch.object(coding_child_launch, 'RUNTIME', runtime):
            if os.getuid() == 1000:
                self.assertEqual(owned_path(workspace.path), str(workspace.path))
            else:
                # Deterministic Windmill checks run as UID985. Hardening a
                # fixture does not turn that identity into the coding UID.
                with self.assertRaisesRegex(coding_child_launch.ConfinementError,
                                            'confinement_runtime_owner'):
                    owned_path(workspace.path)
        self.assertEqual(workspace.path.stat().st_mode & 0o777, 0o700)
        self.assertEqual((workspace.path/'source-directory/checked-out.py').stat().st_mode & 0o777, 0o600)
        self.assertEqual((workspace.path/'source-directory/run.sh').stat().st_mode & 0o777, 0o700)
        # Later writes under both the root and an already-cloned directory obey
        # the service umask rather than the formerly inherited default ACL.
        mask = os.umask(0o077)
        try:
            for parent in (workspace.path, workspace.path/'source-directory'):
                child = parent/'later-directory'
                child.mkdir()
                (child/'later-file').write_text('private')
                self.assertFalse(child.stat().st_mode & 0o077)
                self.assertFalse((child/'later-file').stat().st_mode & 0o077)
        finally:
            os.umask(mask)

    def test_existing_group_writable_workspace_is_held_without_changing_it(self):
        issue, runtime = self.qualify(218)
        path = runtime/'workspaces'/issue.identifier
        path.mkdir(parents=True)
        path.chmod(0o775)
        (path/'retained-output').write_text('preserved')
        native, _, _ = self.adapted()
        with patch.object(adapter.subprocess, 'run') as clone:
            with self.assertRaisesRegex(AdmissionError, 'Workspace ownership or permissions'):
                asyncio.run(native.ensure_workspace(
                    self.runtime/'workspaces', issue.identifier, SimpleNamespace()))
        clone.assert_not_called()
        self.assertEqual(path.stat().st_mode & 0o777, 0o775)
        self.assertEqual((path/'retained-output').read_text(), 'preserved')

    @unittest.skipUnless(shutil.which('setfacl'), 'POSIX ACL fixture needs setfacl')
    def test_retained_default_acl_is_held_without_rewriting_it(self):
        issue, runtime = self.qualify(218)
        path = runtime/'workspaces'/issue.identifier
        path.mkdir(parents=True)
        subprocess.check_call(['setfacl', '-m', 'd:u::rwx,d:g::rwx,d:o::---', str(path)])
        path.chmod(0o700)
        before = os.getxattr(path, 'system.posix_acl_default')
        native, _, _ = self.adapted()
        with self.assertRaisesRegex(AdmissionError, 'Workspace inherited default ACL'):
            asyncio.run(native.ensure_workspace(
                self.runtime/'workspaces', issue.identifier, SimpleNamespace()))
        self.assertEqual(os.getxattr(path, 'system.posix_acl_default'), before)
        self.assertEqual(path.stat().st_mode & 0o777, 0o700)

    def test_new_workspace_acl_removal_error_prevents_exposure(self):
        issue, runtime = self.qualify(218)
        native, _, _ = self.adapted()
        with patch.object(adapter.subprocess, 'run',
                          side_effect=lambda argv,**kwargs: Path(argv[-1]).mkdir()), \
             patch.object(adapter.os, 'removexattr', side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                asyncio.run(native.ensure_workspace(
                    self.runtime/'workspaces', issue.identifier, SimpleNamespace()))

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


@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Use pinned Stokowski environment')
class NativeSuccessorBindingTests(unittest.TestCase):
    def setUp(self):
        import stokowski_native_publication as native
        from symphony_capacity import digest
        from unittest.mock import Mock
        self.native = native
        c = self.c = CurrentDispatchTests(methodName='runTest')
        c.successor_real = True
        self.addCleanup(c.doCleanups)
        c.setUp()
        for module in native.MODULES:
            name = 'tools/delivery/'+module+'.py'
            shutil.copyfile(Path(adapter.__file__).parents[2]/name, c.source/name)
            c.current.config['source_sha256'][name] = adapter.file_sha(c.source/name)
        self.bind_config()
        f,*self.original = c.successor_fixture()
        self.f = f
        # Qualify this route explicitly; the ordinary MCP fixture stays unchanged.
        f.config['repository'] = native.ROUTE['repository']
        f.config['caller_association'] = dict(native.CALLER, native_route=dict(native.ROUTE),
            authenticated_observation=f.ref(f.qualified/'observation.json'))
        f.config['native_publication'] = dict(source_base=native.BASE,
            source_head=c.current.config['source_head'], source_branch=f.branch,
            source_sha256={k:v for k,v in c.current.config['source_sha256'].items() if k.endswith('.py')},
            python_sha256=adapter.file_sha(Path(sys.executable).resolve()))
        f.packet['source']['repository'] = native.ROUTE['repository']
        claim = f.config['repository_claim']
        binding = dict(owner=f.owner, repository=native.ROUTE['repository'], issue_id=f.issue['uuid'])
        f.write(Path(claim['binding_path']), binding)
        claim.update(binding_sha256=f.sha(Path(claim['binding_path'])), binding_identity_sha256=digest(binding))
        f.write(Path(claim['path']), dict(owner=f.owner, directory=str(Path(claim['binding_path']).parent),
                                        binding_sha256=digest(binding)))
        claim['sha256'] = f.sha(Path(claim['path']))
        f.handoff.update(native_route=dict(native.ROUTE),
            authenticated_principal=dict(id=native.CALLER['principal_id'], login=native.CALLER['login']))
        f.repin()
        c.current.config['qualified_successor'] = f.ref(f.handoff_path)
        c.current.state.pop('successor_request')  # New qualification, before any native call.
        self.bind_config()
        self.calls = []
        self.process_calls = []
        self.run = Mock(side_effect=self.process)
        self.api = Mock(wraps=prepare.prepare_publication)
        self.adapters = native.Adapters(self.run, self.api, f.provider)
        c.stack.enter_context(patch.object(native, 'process', self.run))
        self.launch = c.stack.enter_context(patch.object(adapter.CurrentWork, '_native_publication_cli',
                                                        side_effect=self.invoke))

    def bind_config(self):
        c = self.c
        c.write(c.runtime/'current.json', c.current.config)
        c.current.config_sha = adapter.file_sha(c.runtime/'current.json')
        c.current.state['config_sha256'] = c.current.config_sha
        c.current.save()

    def process(self, argv, *, env, timeout):
        n,c = self.native,self.c
        self.assertLessEqual(timeout, 10)
        self.assertEqual({k:v for k,v in env.items() if k != 'GIT_SSH_COMMAND'}, n.ENV)
        self.process_calls.append(argv)
        if argv[:3] == ('/usr/bin/git', '-C', str(c.source)):
            args = argv[3:]
            if args == ('rev-parse','HEAD'):
                out = c.current.config['source_head']+'\n'
            elif args == ('branch','--show-current'):
                out = self.f.branch+'\n'
            elif args == ('merge-base',n.BASE,c.current.config['source_head']):
                out = n.BASE+'\n'
            else:
                self.assertEqual(args[0], 'show')
                head,name = args[1].split(':',1)
                self.assertEqual(head,c.current.config['source_head'])
                return 0,(c.source/name).read_bytes(),b''
            return 0,out.encode(),b''
        if argv[0] == '/usr/bin/ssh':
            self.assertEqual(argv, (*n.SSH,'-T','git@github.com'))
            return 1,b'',b"Hi maldous! You've successfully authenticated, but GitHub does not provide shell access.\n"
        self.assertEqual(argv,('/usr/bin/git','ls-remote','--exit-code',
            'git@github.com:maldous/offmenu.git','refs/heads/develop'))
        self.assertEqual(env['GIT_SSH_COMMAND'],n.shlex.join(n.SSH))
        return 0,(n.BASE+'\trefs/heads/develop\n').encode(),b''

    def invoke(self, data):
        n,c = self.native,self.c
        request = n.decode(data)
        persisted = json.loads(c.current.state_path.read_bytes())['successor_request']
        self.assertEqual(persisted['native_request'], {k:v for k,v in request.items() if k != 'mode'})
        self.assertEqual(persisted['native_binding'], n.sha(n.encode(persisted['native_request'])))
        self.calls.append(request)
        return n.encode(n.invoke(request, root=c.source, adapters=self.adapters))

    def test_normal_intake_owner_reference_native_publication_and_restart(self):
        from stokowski.models import Issue
        c, f = self.c, self.f
        authority = dict(schema='offmenu-intake-authority/1', owner=c.current.config['owner'],
            source_head=c.current.config['source_head'], issue=f.issue['identifier'],
            issue_id=f.issue['uuid'], project_id=f.issue['project_id'], accepted_scope=f.packet['scope'],
            acceptance=f.packet['acceptance'], dependencies=[], decision='owner-qualified',
            handoff=f.ref(f.handoff_path), qualification=None)
        c.write(c.root/'normal-authority.json', authority)
        policy = dict(schema='offmenu-normal-intake/1', enabled=True, owner=authority['owner'],
            source_head=authority['source_head'], project_route=c.current.route, expires_at=time.time()+300,
            references={'owner/native-fixture':f.ref(c.root/'normal-authority.json')},
            resources=f.packet['resources'], timeout_seconds=5)
        c.write(c.root/'normal-policy.json', policy)
        c.current.config.pop('qualified_successor')
        c.current.config['normal_intake'] = f.ref(c.root/'normal-policy.json')
        self.bind_config()
        issue = Issue(id=f.issue['uuid'],identifier=f.issue['identifier'],title='Controlled intake',state='Todo')
        client = c.client(issue)
        client._graphql.return_value['issue'].update(description='```offmenu-intake\n'+json.dumps(dict(
            schema='offmenu-intake-reference/1',reference='owner/native-fixture'))+'\n```',
            inverseRelations=dict(nodes=[]))
        native, linear, fetch = c.adapted()
        owner = native.Orchestrator(c.runtime/'workflow.yaml')
        owner._load_workflow()
        owner._linear = client
        client.fetch_candidate_issues = lambda *args:linear.LinearClient.fetch_candidate_issues(client,*args)
        for name in ('_reconcile','_handle_gate_responses','_evict_terminal_gates'):
            c.stack.enter_context(patch.object(owner,name,new_callable=AsyncMock))
        owner._dispatch = unittest.mock.Mock()
        fetch.return_value = [issue]
        asyncio.run(owner._tick())
        self.assertEqual(c.current.state['successor_request']['status'], 'published', c.current.state.get('successor_hold'))
        before = json.loads(json.dumps(c.current.state['successor_request']['native_request']))
        adapter.CurrentWork(c.runtime)
        self.assertEqual(c.current.state['successor_request']['native_request'], before)
        self.api.assert_called_once()
        f.provider.assert_called_once()
        self.assertEqual(c.current.state['intake'][issue.identifier]['authority'],authority)

    def test_protected_publication_refuses_ungranted_append_before_runtime_exposure(self):
        c,f=self.c,self.f
        protected=c.temp/'transition-seed';protected.mkdir()
        before=f.catalog.read_bytes();baseline=json.loads(before)
        (protected/'catalog.json').write_bytes(before)
        c.write(protected/'binding.json',dict(runtime=str(c.runtime)))
        other=dict(version=1,entries=baseline['entries']+[dict(issue='UIF-999',issue_id='unrelated',
            runtime=str(c.root/'unrelated'),admission_sha256='f'*64)])
        config=dict(runtime_root=str(c.root),catalog=str(f.catalog),catalog_versions=[dict(
            sha256=hashlib.sha256(prepare._publication_bytes(other)).hexdigest(),catalog=other)])
        transition=adapter.CurrentWork.catalog_transition
        attempted=[]
        def granted_edge(view,old,new):
            attempted.append((old,new))
            shadow=object.__new__(adapter.CurrentWork)
            shadow.owner_custody=True;shadow.config=config;shadow.guard=lambda:None
            with patch.object(adapter,'PROTECTED_OWNER',protected),patch.object(
                    adapter,'protected_owner_bytes',side_effect=lambda p:Path(p).read_bytes()):
                return transition(shadow,old,new)
        with patch.object(adapter.CurrentWork,'catalog_transition',new=granted_edge):
            c.current._successor_boundary()
        self.assertEqual(f.catalog.read_bytes(),before)
        self.assertFalse(f.runtime.exists())
        self.assertEqual(len(attempted),1)
        self.assertEqual(attempted[0][0],before)
        self.assertNotEqual(c.current.state['successor_request']['status'],'published')

    def test_protected_catalog_swap_after_capture_writes_no_journal_or_runtime(self):
        c,f=self.c,self.f
        before=f.catalog.read_bytes();changed=json.loads(before)
        changed['entries'].append(dict(issue='UIF-998',issue_id='other',runtime=str(c.root/'other'),admission_sha256='f'*64))
        changed=prepare._publication_bytes(changed)
        constructor=adapter.CurrentWork
        captures=[]
        def capture():
            raw=f.catalog.read_bytes();captures.append(raw)
            if len(captures)==1:f.catalog.write_bytes(changed)
            return raw
        def view(*args,**kwargs):
            actual=constructor(*args,**kwargs)
            # Synthetic root grants are isolated to catalog capture; all
            # publication inputs, provider checks and write ordering stay real.
            actual.owner_custody={'synthetic':'root grant'}
            actual.catalog_bytes=capture
            return actual
        with patch.object(prepare,'CurrentWork',side_effect=view):
            c.current._successor_boundary()
        self.assertGreaterEqual(len(captures),2)
        self.assertEqual(captures[0],before)
        self.assertEqual(f.catalog.read_bytes(),changed)
        self.assertFalse((f.root/(f.runtime.name+'-publication.json')).exists())
        self.assertFalse(f.runtime.exists())

    def test_protected_existing_publication_journal_recovers_without_before_capture(self):
        c,f=self.c,self.f
        c.current._successor_boundary()
        self.assertEqual(c.current.state['successor_request']['status'],'published')
        constructor=adapter.CurrentWork
        def view(*args,**kwargs):
            actual=constructor(*args,**kwargs)
            actual.owner_custody={'synthetic':'root grant'}
            actual.catalog_bytes=lambda:f.catalog.read_bytes()
            return actual
        calls=f.provider.call_count
        with patch.object(prepare,'CurrentWork',side_effect=view):
            result=prepare.prepare_publication(f.handoff_path,handoff_sha256=f.handoff_sha,
                authenticated_caller=lambda:dict(self.native.CALLER),provider_proof=f.provider)
        self.assertEqual(result['status'],'duplicate')
        self.assertEqual(f.provider.call_count,calls)

    def test_rearm_native_custody_exact_path_hash_and_binding_required(self):
        import copy
        c, f = self.c, self.f
        c.current.refresh()
        prior = copy.deepcopy(c.current.state['successor_request'])
        path = Path(prior['publication_result']['path'])
        original = path.read_bytes()
        # A valid coordinator-private JSON cannot replace native custody even
        # when its bytes/hash match. Symlinks and altered pins also stay held.
        replacement = c.root/'copied-custody.json'
        replacement.write_bytes(original)
        symlink = path.with_name('synthetic-link.json')
        symlink.symlink_to(path)
        for ref in (f.ref(replacement), dict(path=str(symlink), sha256=adapter.file_sha(path)),
                    dict(prior['publication_result'], sha256='0'*64)):
            changed = dict(prior, publication_result=ref)
            with self.assertRaisesRegex(AdmissionError, 'successor_prior_publication_unreconciled'):
                c.current._rearm_successor(changed)
            self.assertEqual(c.current.state['successor_request'], prior)
            self.assertNotIn('successor_history', c.current.state)
        for field in ('request', 'binding', 'result'):
            record = json.loads(original)
            record[field] = {} if field != 'binding' else '0'*64
            c.write(path, record)
            changed = dict(prior, publication_result=f.ref(path))
            with self.assertRaisesRegex(AdmissionError, 'successor_prior_publication_unreconciled'):
                c.current._rearm_successor(changed)
            self.assertEqual(c.current.state['successor_request'], prior)
            self.assertNotIn('successor_history', c.current.state)
        path.write_bytes(original)
        self.assertEqual(self.api.call_count, 1)

    def test_two_terminal_reviewed_handoffs_through_normal_intake(self):
        """Synthetic external actors only; real intake, qualifier, pool and worker.

        No model JSON grants authority. Each validation/review packet is built
        independently from the retained native output as in review_fixture.
        """
        import copy
        from contextlib import nullcontext
        from stokowski.models import Issue
        from symphony_capacity import Pool
        import stokowski_worker as worker
        c, first = self.c, self.f
        original_runtime = self.original[1]
        original_bytes = first.snapshot(original_runtime)
        self.test_normal_intake_owner_reference_native_publication_and_restart()
        native, _, _ = c.adapted()
        pool = Pool(c.policy['symphony']['pool_path'], c.policy)
        host = dict(cpu_millis=64000, available_memory_bytes=10**12, available_disk_bytes=10**12)
        computations = []
        receipts = []
        reviews = []
        frozen = {}
        real_supervise = worker.supervise

        def admit_and_review(f):
            issue = Issue(id=f.issue['uuid'], identifier=f.issue['identifier'], title='Synthetic finite task', state='Todo')
            self.assertEqual(c.select(issue), [issue])
            runtime = f.runtime
            workspace = runtime/'workspaces'/issue.identifier
            workspace.mkdir()
            manifest = adapter.read_record(runtime/'manifest.json')
            request = adapter.read_record(runtime/'requests'/(issue.identifier+'.json'))
            scope = manifest['tasks'][issue.identifier]['allowed_paths']
            prior_git = c.git.side_effect
            finished = [False]
            def observe(argv, **kwargs):
                if argv[2] == str(workspace):
                    if argv[3] == 'diff':
                        return ('\0'.join(scope)+'\0').encode() if finished[0] else b''
                    if argv[3] == 'ls-files':
                        return b''
                    return (manifest['branch'] if argv[3] == 'branch' else manifest['base_revision'])+'\n'
                return prior_git(argv, **kwargs)
            c.git.side_effect = observe
            def complete(command, prompt, path, environment, directory, *args):
                self.assertEqual(prompt, request['prompt'])
                computations.append(issue.identifier)
                # The real supervisor runs a finite Python fixture process,
                # never the constructed model command, and proves cleanup.
                script = """import json, pathlib, sys
scope, issue = json.loads(sys.argv[1]), sys.argv[2]
for name in scope:
    target = pathlib.Path(name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text('Synthetic independently checked output '+issue+'\\n')
print(json.dumps(dict(type='turn.completed')), flush=True)
"""
                result = real_supervise([sys.executable, '-c', script, json.dumps(scope), issue.identifier],
                    prompt, path, environment, directory, *args)
                finished[0] = True
                return result
            async def spawn(*args, **kwargs):
                worker.execute(runtime, issue.identifier, request)
                return SimpleNamespace(pid=98765, returncode=0, communicate=AsyncMock())
            with patch.object(worker, 'host_snapshot', return_value=host), \
                 patch.object(worker.os, 'sched_setaffinity'), \
                 patch.object(worker, 'isolated_codex_environment', return_value=nullcontext({})), \
                 patch.object(worker, 'supervise', side_effect=complete), \
                 patch.object(adapter.asyncio, 'create_subprocess_exec', side_effect=spawn) as spawned:
                self.assertEqual(asyncio.run(c.turn(native, issue, runtime)).status, 'succeeded', adapter.read_record(runtime/'attempts'/issue.identifier/'receipt.json'))
                with self.assertRaises(AdmissionError):
                    asyncio.run(c.turn(native, issue, runtime))
                with self.assertRaises(AdmissionError):
                    worker.execute(runtime, issue.identifier, request)
            spawned.assert_called_once()
            receipt_path = runtime/'attempts'/issue.identifier/'receipt.json'
            receipt = adapter.read_record(receipt_path)
            self.assertTrue(receipt['child_tree_gone'])
            self.assertIsNone(receipt['resolved_model'])
            self.assertEqual(receipt['resolution_status'], 'unobserved')
            self.assertEqual(receipt['requested_model'], 'gpt-6.1-sol')
            self.assertEqual(receipt['declared_resources'], f.packet['resources'])
            receipts.append(receipt)
            owner = native.Orchestrator(c.runtime/'workflow.yaml')
            self.assertEqual(owner._load_workflow(), [])
            client = c.client(issue)
            for name in ('update_issue_state', 'fetch_comments', 'fetch_issues_by_states', 'post_comment'):
                setattr(client, name, AsyncMock())
            owner._linear = client
            owner._schedule_retry = unittest.mock.Mock()
            owner.ledger.record_terminal = unittest.mock.Mock()
            asyncio.run(owner._enter_gate(issue, 'evidence-pending'))
            c.task_head = manifest['base_revision']
            _, _, _, _, review, journal, key = c.review_fixture(completed=(issue, runtime, owner, client))
            # The actual unit-review consumer qualifies the synthetic independent
            # validation operation, receipt and reviewer; no gate is fabricated.
            c.current.unit_review_writer(lambda envelope: review)({k:review[k] for k in ('snapshot','decision')})
            c.current.refresh()
            asyncio.run(owner._handle_gate_responses())
            self.assertTrue(c.current._reconciled_unit(issue.identifier))
            self.assertFalse(c.current.state['tasks'][issue.identifier]['unit_gate']['accepted_delivery'])
            reviews.append(review)
            client.update_issue_state.assert_not_awaited()
            owner.ledger.record_terminal.assert_not_called()
            return issue, runtime, journal, key

        task_a, runtime_a, journal_a, key_a = admit_and_review(first)
        prior = copy.deepcopy(c.current.state['successor_request'])
        # Preserve every first-task input, nonce/custody/publication journal and
        # review byte before building a distinct owner-qualified handoff.
        for directory in (first.qualified, runtime_a):
            frozen.update({p:p.read_bytes() for p in directory.rglob('*') if p.is_file()})
        for key in ('publication_result', 'publication_journal'):
            path = Path(prior[key]['path'])
            frozen[path] = path.read_bytes()
        second = copy.copy(first)
        second.qualified = c.root/'second-qualified'
        second.runtime = c.root/'second-task'
        def retarget(value):
            return json.loads(json.dumps(value).replace(str(first.qualified), str(second.qualified))
                .replace(str(first.runtime), str(second.runtime))
                .replace(first.issue['uuid'], '00000000-0000-4000-8000-000000000232')
                .replace('UIF-231', 'UIF-232'))
        for name in ('config', 'packet', 'handoff', 'manifest', 'issue'):
            setattr(second, name, retarget(getattr(first, name)))
        second.packet['trigger'] = dict(issue=task_a.identifier,
            entry=c.current.state['references'][task_a.identifier], unit_binding=reviews[0]['unit_binding'],
            review_sha256=adapter.digest(reviews[0]))
        # Exact scope reuse is intentional and must wait for fully reconciled A.
        self.assertEqual(second.packet['scope'], first.packet['scope'])
        for path in first.qualified.rglob('*'):
            if path.is_file():
                second.write(second.qualified/path.relative_to(first.qualified), retarget(json.loads(path.read_bytes())))
        claim = second.config['repository_claim']
        binding_path = Path(claim['binding_path'])
        binding = adapter.read_record(binding_path)
        claim.update(binding_sha256=second.sha(binding_path), binding_identity_sha256=adapter.digest(binding))
        second.write(Path(claim['path']), dict(owner=second.owner, directory=str(binding_path.parent), binding_sha256=adapter.digest(binding)))
        claim['sha256'] = second.sha(Path(claim['path']))
        second.repin()
        self.f = second
        issue_b = Issue(id=second.issue['uuid'], identifier=second.issue['identifier'], title='Second synthetic intake', state='Todo')
        authority = dict(schema='offmenu-intake-authority/1', owner=c.current.config['owner'],
            source_head=c.current.config['source_head'], issue=issue_b.identifier, issue_id=issue_b.id,
            project_id=second.issue['project_id'], accepted_scope=second.packet['scope'],
            acceptance=second.packet['acceptance'], dependencies=[], decision='owner-qualified',
            handoff=second.ref(second.handoff_path), qualification=None)
        c.write(c.root/'second-authority.json', authority)
        policy = adapter.read_record(c.root/'normal-policy.json')
        policy['references']['owner/second-fixture'] = second.ref(c.root/'second-authority.json')
        c.write(c.root/'second-policy.json', policy)
        c.current.config['normal_intake'] = second.ref(c.root/'second-policy.json')
        self.bind_config()
        client_b = c.client(issue_b)
        client_b._graphql.return_value['issue'].update(description='```offmenu-intake\n'+json.dumps(dict(
            schema='offmenu-intake-reference/1', reference='owner/second-fixture'))+'\n```', inverseRelations=dict(nodes=[]))
        # Negative evidence mutations are restored, never accepted/reconciled as
        # success. Each blocks B before any publication or computation.
        lease_a = receipts[0]['lease']
        for status in ('running', 'unknown', 'cancelled', 'refused'):
            with pool._transaction() as db:
                db.execute('UPDATE leases SET status=? WHERE id=?', (status, lease_a))
            self.assertEqual(c.select(issue_b, client_b), [])
            self.assertEqual(self.api.call_count, 1)
            self.assertEqual(c.current.state['successor_request'], prior)
            self.assertIn('successor_prior_unit_unreconciled', c.current.state['successor_hold'])
        with pool._transaction() as db:
            db.execute("UPDATE leases SET status='finished' WHERE id=?", (lease_a,))
        _, operation = journal_a.read(key_a)
        for change in (dict(status='unknown'), dict(cancel_requested=True), dict(reconcile_required=True), dict(observation_intent={'synthetic':True})):
            journal_a.save(key_a, dict(operation, **change), 'synthetic-negative-observation')
            self.assertEqual(c.select(issue_b, client_b), [])
            self.assertEqual(self.api.call_count, 1)
            self.assertEqual(c.current.state['successor_request'], prior)
            self.assertIn('successor_prior_unit_unreconciled', c.current.state['successor_hold'])
        journal_a.save(key_a, operation, 'synthetic-restored-observation')
        # Freeze the final reconciled operation bytes after mutation tests.
        frozen[runtime_a/'operations/operations.sqlite'] = (runtime_a/'operations/operations.sqlite').read_bytes()
        self.assertEqual(c.select(issue_b, client_b), [])  # Intake publishes, next poll admits.
        self.assertEqual(c.current.state['successor_request']['status'], 'published', c.current.state.get('successor_hold'))
        self.assertIn('successor_history', c.current.state, c.current.state['intake'][issue_b.identifier].get('reason'))
        self.assertEqual(c.current.state['successor_history'][0]['native_request'], prior['native_request'])
        self.assertNotEqual(c.current.state['successor_request']['native_request']['nonce'], prior['native_request']['nonce'])
        task_b, runtime_b, _, _ = admit_and_review(second)
        self.assertEqual(computations, [task_a.identifier, task_b.identifier])
        for _ in range(2):
            c.current.refresh()
            adapter.CurrentWork(c.runtime)
            self.assertEqual(c.select(issue_b, client_b), [])
        self.assertEqual(self.api.call_count, 2)
        self.assertEqual(first.provider.call_count, 2)
        self.assertEqual(computations, [task_a.identifier, task_b.identifier])
        for receipt in receipts:
            with pool._transaction() as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE id=? AND event='admitted'", (receipt['lease'],)).fetchone()[0], 1)
            self.assertEqual(next(r['status'] for r in pool.status() if r['id']==receipt['lease']), 'finished')
        for path, data in frozen.items():
            self.assertEqual(path.read_bytes(), data, str(path))
        self.assertEqual(first.snapshot(original_runtime), original_bytes)
        self.assertEqual(len(c.current.state['successor_history']), 1)
        # A runner may retain this explicitly synthetic trace after temporary
        # runtime cleanup. It is proof data, never an admission/approval input.
        self.synthetic_proof = dict(schema='offmenu-synthetic-succession-proof/1', synthetic_only=True,
            publications=self.api.call_count, computations=computations, original_106_preserved=True,
            accepted_delivery=False, history=copy.deepcopy(c.current.state['successor_history']),
            tasks=[dict(issue=issue.identifier, owner=c.current.config['owner'],
                request=adapter.read_record(runtime/'requests'/(issue.identifier+'.json')),
                admission=c.current.state['references'][issue.identifier], native_receipt=receipt,
                validation_operation=review['integration_binding']['validation_operation_key'],
                synthetic_candidate_commit=review['integration_binding']['head'],
                independent_review=review['snapshot']['review'],
                terminal_gate=copy.deepcopy(c.current.state['tasks'][issue.identifier]['unit_gate']))
                for issue, runtime, receipt, review in zip((task_a, task_b), (runtime_a, runtime_b), receipts, reviews)])


    def test_actual_adapter_native_publication_once_reopen_and_custody(self):
        c,f,n = self.c,self.f,self.native
        issue,runtime,owner,client,review,journal,key = self.original
        before = {p:p.read_bytes() for p in runtime.rglob('*') if p.is_file()}
        c.current.refresh()
        self.assertEqual(c.current.state['successor_request']['status'],'published',c.current.state.get('successor_hold'))
        request = dict(c.current.state['successor_request']['native_request'])
        c.current.refresh()
        reopened = adapter.CurrentWork(c.runtime)
        self.assertEqual(reopened.state['successor_request']['native_request'],request)
        self.assertEqual([r['mode'] for r in self.calls],['prepare','status','status'])
        self.api.assert_called_once()
        f.provider.assert_called_once()
        self.assertEqual(sum(a[0] == '/usr/bin/ssh' for a in self.process_calls),1)
        self.assertEqual(len(json.loads(c.catalog.read_bytes())['entries']),2)
        for path, data in before.items():
            self.assertEqual(path.read_bytes(),data)
        custody = n.decode((c.source/'.delivery/native-ssh-publication'/(f.handoff_sha+'.json')).read_bytes())
        self.assertEqual(custody['request'],request)
        self.assertEqual(custody['result'],dict(status='published',runtime=str(f.runtime),dispatches=0))

    def lost_reply(self, failure):
        original = self.invoke
        def lost(data):
            original(data)
            if failure == 'malformed':
                return b'{invalid'
            raise TimeoutError('synthetic lost reply')
        self.launch.side_effect = lost
        self.c.current.refresh()
        request = dict(self.c.current.state['successor_request']['native_request'])
        self.assertNotEqual(self.c.current.state['successor_request']['status'],'published')
        self.launch.side_effect = self.invoke
        self.c.current.refresh()
        self.assertEqual([r['mode'] for r in self.calls],['prepare','status'])
        self.assertEqual(self.c.current.state['successor_request']['native_request'],request)
        self.assertEqual(self.c.current.state['successor_request']['status'],'published')
        self.api.assert_called_once()

    def test_lost_reply_is_status_only(self):
        self.lost_reply('timeout')

    def test_malformed_reply_is_status_only(self):
        self.lost_reply('malformed')

    def test_timeout_before_custody_never_retries_prepare(self):
        self.launch.side_effect = TimeoutError('synthetic timeout before delivery')
        self.c.current.refresh()
        request = dict(self.c.current.state['successor_request']['native_request'])
        self.launch.side_effect = self.invoke
        self.c.current.refresh()
        self.c.current.refresh()
        self.assertEqual([r['mode'] for r in self.calls],['status','status'])
        self.assertEqual(self.c.current.state['successor_request']['native_request'],request)
        self.assertNotEqual(self.c.current.state['successor_request']['status'],'published')
        self.api.assert_not_called()
        self.f.provider.assert_not_called()

    def test_intent_directory_sync_failure_prevents_launch_and_new_prepare(self):
        fsync = os.fsync
        def fail_directory(fd):
            if Path('/proc/self/fd/'+str(fd)).resolve() == self.c.runtime:
                raise OSError('synthetic intent directory durability failure')
            return fsync(fd)
        with patch.object(adapter.os,'fsync',side_effect=fail_directory):
            self.c.current.refresh()
        self.launch.assert_not_called()
        request = dict(self.c.current.state['successor_request']['native_request'])
        self.c.current.refresh()
        self.assertEqual(self.calls[0]['mode'],'status')
        self.assertEqual(self.c.current.state['successor_request']['native_request'],request)
        self.api.assert_not_called()

    def test_partial_publication_uncertainty_stays_status_only(self):
        write = prepare._publication_write
        def fail_catalog(path, data):
            if path == self.c.catalog:
                raise OSError('synthetic partial publication')
            return write(path,data)
        with patch.object(prepare,'_publication_write',side_effect=fail_catalog):
            self.c.current.refresh()
        request = dict(self.c.current.state['successor_request']['native_request'])
        self.c.current.refresh()
        adapter.CurrentWork(self.c.runtime)
        self.assertEqual([r['mode'] for r in self.calls],['prepare','status','status'])
        self.assertEqual(self.c.current.state['successor_request']['native_request'],request)
        self.assertEqual(self.c.current.state['successor_request']['status'],'uncertain')
        self.api.assert_called_once()
        self.f.provider.assert_called_once()
        self.assertEqual(self.c.catalog.read_bytes(),self.f.catalog_before)

    def test_intent_nonce_context_custody_result_catalog_and_runtime_mismatch_refuse(self):
        import copy
        c,n,f = self.c,self.native,self.f
        c.current.refresh()
        pending = copy.deepcopy(c.current.state['successor_request'])
        custody_path = c.source/'.delivery/native-ssh-publication'/(f.handoff_sha+'.json')
        custody_bytes = custody_path.read_bytes()
        catalog_bytes = c.catalog.read_bytes()
        for target in ('nonce','context','owner','source','custody','result','catalog','admission','manifest','request'):
            with self.subTest(target=target):
                c.current.state['successor_request'] = copy.deepcopy(pending)
                c.current.save()
                custody_path.write_bytes(custody_bytes)
                c.catalog.write_bytes(catalog_bytes)
                restore = None
                request = c.current.state['successor_request']['native_request']
                if target == 'nonce':
                    request['nonce'] = '0'*64
                elif target in ('context','owner','source'):
                    request['context'][{'context':'source_branch','owner':'owner','source':'source_head'}[target]] = 'changed'
                elif target in ('custody','result'):
                    record = n.decode(custody_bytes)
                    if target == 'custody':
                        record['request']['nonce'] = '0'*64
                    else:
                        record['result']['runtime'] = str(c.root/'wrong')
                    custody_path.write_bytes(n.encode(record))
                elif target == 'catalog':
                    c.write(c.catalog,dict(version=1,entries=[]))
                else:
                    path = {'admission':f.runtime/'current-admission.json', 'manifest':f.runtime/'manifest.json',
                            'request':f.runtime/'requests/UIF-231.json'}[target]
                    restore = (path,path.read_bytes())
                    path.write_bytes(b'{}')
                c.current._successor_boundary()
                self.assertNotEqual(c.current.state['successor_request']['status'],'published')
                if restore:
                    restore[0].write_bytes(restore[1])
        self.api.assert_called_once()

    def test_cancelled_original_never_launches(self):
        issue,runtime,owner,client,review,journal,key = self.original
        _,state = journal.read(key)
        journal.save(key,dict(state,cancel_requested=True),'synthetic cancel')
        self.c.current.refresh()
        self.launch.assert_not_called()
        self.api.assert_not_called()
        self.f.provider.assert_not_called()

    def test_missing_native_config_does_not_launch(self):
        self.f.config.pop('native_publication')
        self.f.repin()
        self.c.current.config['qualified_successor'] = self.f.ref(self.f.handoff_path)
        self.bind_config()
        self.c.current.refresh()
        self.launch.assert_not_called()
        self.api.assert_not_called()
        self.f.provider.assert_not_called()

    def test_changed_qualified_source_or_owner_config_refuses_before_launch(self):
        c,f = self.c,self.f
        paths = [c.source/'tools/delivery/stokowski_native_publication.py',f.qualified/'config.json']
        for path in paths:
            with self.subTest(path=path):
                original = path.read_bytes()
                try:
                    path.write_bytes(original+b'\n')
                    c.current._successor_boundary()
                    self.assertNotIn('native_request',c.current.state.get('successor_request',{}))
                finally:
                    path.write_bytes(original)
        self.launch.assert_not_called()
        self.api.assert_not_called()

    def test_publication_journal_identity_mismatch_cannot_be_observed(self):
        c,f = self.c,self.f
        c.current.refresh()
        path = c.root/(f.runtime.name+'-publication.json')
        plan = json.loads(path.read_bytes())
        plan['identity']['handoff_sha256'] = '0'*64
        c.write(path,plan)
        c.current.refresh()
        self.assertNotEqual(c.current.state['successor_request']['status'],'published')
        self.assertEqual([r['mode'] for r in self.calls],['prepare','status'])
        self.api.assert_called_once()

    def test_reply_cannot_override_custody(self):
        self.c.current.refresh()
        original = self.invoke
        def lie(data):
            result = self.native.decode(original(data))
            result['result']['runtime'] = str(self.c.root/'wrong')
            return self.native.encode(result)
        self.launch.side_effect = lie
        self.c.current.refresh()
        self.assertNotEqual(self.c.current.state['successor_request']['status'],'published')
        self.assertIn('successor_native_result_binding',self.c.current.state['successor_hold'])
        self.api.assert_called_once()

    def worker_admission(self, uncertain=False):
        from contextlib import nullcontext
        from stokowski.models import Issue
        from symphony_capacity import Pool, digest
        import stokowski_worker as worker
        c,f = self.c,self.f
        c.current.refresh()
        c.current.refresh()
        issue = Issue(id=f.issue['uuid'],identifier='UIF-231',title='Synthetic successor',state='Todo')
        self.assertEqual(c.select(issue),[issue])
        workspace = f.runtime/'workspaces'/issue.identifier
        workspace.mkdir()
        request = json.loads((f.runtime/'requests/UIF-231.json').read_bytes())
        manifest = json.loads((f.runtime/'manifest.json').read_bytes())
        # Fixed Git observations only: no Git/auth/network subprocess is launched.
        git_read = c.git.side_effect
        def observe(argv, **kwargs):
            if argv[2] == str(workspace):
                if argv[3] in ('diff','ls-files'):
                    return b''
                return (manifest['branch'] if argv[3] == 'branch' else manifest['base_revision'])+'\n'
            return git_read(argv,**kwargs)
        c.git.side_effect = observe
        pool = Pool(c.policy['symphony']['pool_path'],c.policy)
        proof = json.loads((f.runtime/'provider-proof.json').read_bytes())
        host = dict(cpu_millis=64000,available_memory_bytes=10**12,available_disk_bytes=10**12)
        blocker = dict(branch=manifest['branch'],head=manifest['base_revision'],owner='fixture-blocker',
            write_roots=['tests/unrelated.py'],resources=manifest['tasks']['UIF-231']['resources'],
            task_sha256=digest({'synthetic':'blocker'}))
        pool.admit('synthetic-blocker',blocker,dict(proof,session_ceiling=1),host)
        with patch.object(worker,'host_snapshot',return_value=host), \
             patch.object(worker,'supervise',side_effect=AssertionError('capacity must hold')):
            c.write(f.runtime/'provider-proof.json',dict(proof,session_ceiling=1))
            with self.assertRaisesRegex(AdmissionError,'capacity_sessions'):
                worker.execute(f.runtime,issue.identifier,request)
        pool.finish('synthetic-blocker',True,'stopped')
        c.write(f.runtime/'provider-proof.json',proof)
        def complete(command,prompt,path,environment,directory,*args):
            self.assertEqual(prompt,request['prompt'])
            (directory/'stdout.jsonl').write_text(json.dumps(dict(type='turn.completed'))+'\n')
            return dict(status='uncertain' if uncertain else 'succeeded',child_tree_gone=not uncertain,exit_code=0)
        orchestrator,_,_ = c.adapted()
        async def spawn(*args,**kwargs):
            worker.execute(f.runtime,issue.identifier,request)
            return SimpleNamespace(pid=98765,returncode=0,communicate=AsyncMock())
        with patch.object(worker,'host_snapshot',return_value=host), \
             patch.object(worker.os,'sched_setaffinity'), \
             patch.object(worker,'isolated_codex_environment',return_value=nullcontext({})), \
             patch.object(worker,'supervise',side_effect=complete) as computation, \
             patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=spawn) as spawned:
            self.assertEqual(asyncio.run(c.turn(orchestrator,issue,f.runtime)).status,
                             'failed' if uncertain else 'succeeded')
            reopened = adapter.CurrentWork(c.runtime)
            self.assertEqual(asyncio.run(reopened.candidates(c.client(issue),[issue])),[])
            with self.assertRaises(AdmissionError):
                asyncio.run(c.turn(orchestrator,issue,f.runtime))
            with self.assertRaisesRegex(AdmissionError,'no replay'):
                worker.execute(f.runtime,issue.identifier,request)
        computation.assert_called_once()
        spawned.assert_called_once()
        self.api.assert_called_once()
        f.provider.assert_called_once()
        lease = runtime_lease_ids(f.runtime,manifest)[issue.identifier]
        with pool._transaction() as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM events WHERE id=? AND event='admitted'",(lease,)).fetchone()[0],1)
        self.assertEqual({r['id']:r['status'] for r in pool.status()}[lease],
                         'running' if uncertain else 'finished')

    def test_native_published_task_normal_admission_once_and_capacity_hold(self):
        self.worker_admission()

    def test_native_published_task_uncertain_worker_lease_no_replay(self):
        self.worker_admission(uncertain=True)


class NativePublicationLaunchTests(unittest.TestCase):
    def setUp(self):
        import stokowski_native_publication as native
        self.native = native
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.source = Path(self.temporary.name).resolve()
        self.script = self.source/'tools/delivery/stokowski_native_publication.py'
        self.script.parent.mkdir(parents=True)
        self.current = object.__new__(adapter.CurrentWork)

    def test_fixed_launch_sanitizes_environment_and_preserves_sibling_imports(self):
        (self.script.parent/'synthetic_sibling.py').write_text('VALUE = "synthetic"\n')
        self.script.write_text('import os,sys,json\nfrom synthetic_sibling import VALUE\n'
            'request=json.load(sys.stdin)\njson.dump(dict(value=VALUE,request=request,env=dict(os.environ)),sys.stdout)\n')
        popen = subprocess.Popen
        def launch(argv, **kwargs):
            self.assertEqual(argv,[sys.executable,'-E','-s',str(self.script)])
            self.assertEqual(kwargs['env'],self.native.ENV)
            self.assertEqual(kwargs['cwd'],self.source)
            self.assertNotIn('shell',kwargs)
            return popen(argv,**kwargs)
        with patch.object(adapter,'SOURCE',self.source), \
             patch.object(adapter.subprocess,'Popen',side_effect=launch), \
             patch.dict(os.environ,{'SYNTHETIC_SECRET':'must-not-leak'}):
            result = self.native.decode(self.current._native_publication_cli(b'{"synthetic":1}\n'))
        self.assertEqual(result,dict(value='synthetic',request={'synthetic':1},env=self.native.ENV))

    def test_process_output_is_bounded(self):
        self.script.write_text('import sys\nsys.stdin.buffer.read()\nsys.stdout.buffer.write(b"x"*65537)\n')
        with patch.object(adapter,'SOURCE',self.source), self.assertRaisesRegex(AdmissionError,'native_reply_size'):
            self.current._native_publication_cli(b'{}\n')

    def test_process_deadline_terminates_synthetic_child(self):
        self.script.write_text('import time\ntime.sleep(60)\n')
        monotonic = time.monotonic
        calls = 0
        def expired():
            nonlocal calls
            calls += 1
            return monotonic() + (91 if calls > 1 else 0)
        with patch.object(adapter,'SOURCE',self.source), \
             patch.object(adapter.time,'monotonic',side_effect=expired), \
             self.assertRaisesRegex(AdmissionError,'native_reply_timeout'):
            self.current._native_publication_cli(b'{}\n')


class ProtectedCatalogTransitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.protected = self.base/'protected'
        self.protected.mkdir()
        self.root = self.base/'.delivery/stokowski'
        self.root.mkdir(parents=True)
        self.coordinator = self.root/'current'
        self.coordinator.mkdir()
        self.catalog = self.root/'catalog.json'
        self.seed = dict(version=1,entries=[])
        self.first = dict(version=1,entries=[dict(issue='UIF-341',issue_id='a',runtime='first',admission_sha256='1'*64)])
        self.second = dict(version=1,entries=self.first['entries']+[dict(issue='UIF-342',issue_id='b',runtime='second',admission_sha256='2'*64)])
        self.raw = prepare._publication_bytes
        self.seed_bytes = self.raw(self.seed)
        self.catalog.write_bytes(self.seed_bytes)
        (self.protected/'catalog.json').write_bytes(self.seed_bytes)
        (self.protected/'binding.json').write_text(json.dumps(dict(runtime=str(self.coordinator))))
        self.config = dict(runtime_root=str(self.root),catalog=str(self.catalog),catalog_versions=[
            dict(sha256=hashlib.sha256(self.raw(value)).hexdigest(),catalog=value)
            for value in (self.first,self.second)])
        self.patch = patch.object(adapter,'PROTECTED_OWNER',self.protected)
        self.patch.start();self.addCleanup(self.patch.stop)
        self.read_patch=patch.object(adapter,'protected_owner_bytes',side_effect=lambda p:Path(p).read_bytes())
        self.read_patch.start();self.addCleanup(self.read_patch.stop)
        self.current=object.__new__(adapter.CurrentWork)
        self.current.owner_custody=True
        self.current.config=self.config
        self.current.guard=lambda:None

    def test_only_exact_next_granted_snapshot_can_be_published(self):
        self.assertEqual(adapter.protected_catalog_bytes(self.config,self.seed_bytes),self.seed_bytes)
        self.current.catalog_transition(self.seed_bytes,self.raw(self.first))
        with self.assertRaisesRegex(AdmissionError,'catalog_transition'):
            self.current.catalog_transition(self.seed_bytes,self.raw(self.second))
        self.catalog.write_bytes(self.raw(self.first))
        self.current.catalog_transition(self.raw(self.first),self.raw(self.second))
        with self.assertRaisesRegex(AdmissionError,'catalog_transition'):
            self.current.catalog_transition(self.raw(self.first),self.seed_bytes)
        with self.assertRaisesRegex(AdmissionError,'catalog_transition'):
            self.current.catalog_transition(self.seed_bytes,self.raw(self.first))

    def test_ungranted_bytes_or_changed_prior_entry_fail_closed(self):
        self.catalog.write_bytes(self.raw(dict(version=1,entries=[dict(untrusted=True)])))
        with self.assertRaisesRegex(AdmissionError,'catalog_snapshot'):
            adapter.protected_catalog_bytes(self.config,self.seed_bytes)
        self.catalog.write_bytes(self.seed_bytes)
        self.config['catalog_versions'][1]['catalog']['entries'][0]=dict(replaced=True)
        with self.assertRaisesRegex(AdmissionError,'catalog_grants'):
            adapter.protected_catalog_bytes(self.config,self.seed_bytes)

    def test_catalog_symlink_and_coordinator_private_substitution_refuse(self):
        self.catalog.unlink();self.catalog.symlink_to(self.protected/'catalog.json')
        with self.assertRaisesRegex(AdmissionError,'catalog_grants'):
            adapter.protected_catalog_bytes(self.config,self.seed_bytes)

    def test_snapshot_swap_cannot_change_captured_parse_or_digest(self):
        self.catalog.write_bytes(self.raw(self.first))
        captured=self.current.catalog_bytes()
        self.catalog.write_bytes(self.raw(self.second))
        with patch.object(self.current,'catalog_bytes',return_value=captured):
            self.assertEqual(self.current.catalog_record(),self.first)
            self.assertEqual(self.current._catalog_observed_sha256,hashlib.sha256(captured).hexdigest())
        with self.assertRaisesRegex(AdmissionError,'catalog_transition'):
            self.current.catalog_transition(captured,self.raw(self.second))
        self.config['catalog']=str(self.coordinator/'catalog.json')
        with self.assertRaisesRegex(AdmissionError,'catalog_grants'):
            adapter.protected_catalog_bytes(self.config,self.seed_bytes)


if __name__ == '__main__':
    unittest.main()
