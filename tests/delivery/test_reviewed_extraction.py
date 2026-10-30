"""Owner admission fixtures contain only authored source, never datasets."""
import asyncio
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0,str(TOOLS))
import stokowski_operations as operations
import stokowski_stage as stage
from test_stokowski_operations import FaultedWindmill


class ExtractionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.workspace = self.root/'workspaces/candidate'
        self.workspace.mkdir(parents=True)
        self.runtime = self.root/'runtime'
        self.runtime.mkdir()
        self.patch = patch.object(operations,'WORKSPACES',PurePosixPath(self.root/'workspaces'))
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.git('init','-qb','feature/retained-source')
        (self.workspace/'baseline').write_text('accepted\n')
        self.git('add','.')
        self.git('commit','-qm','authored baseline')
        base = self.git('rev-parse','HEAD')
        outputs = {}
        mapping = {}
        for index,name in enumerate(sorted(operations.WFP_OUTPUTS)):
            path = self.workspace/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('authored retained source '+str(index)+'\n')
            old = 'retained/source'+str(index)+'.py'
            original = self.workspace/old
            original.parent.mkdir(exist_ok=True)
            original.write_bytes(path.read_bytes())
            outputs[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            mapping[old] = name
        self.git('add','retained')
        self.git('commit','-qm','authored original source')
        base = self.git('rev-parse','HEAD')
        self.git('add','.')
        self.git('commit','-qm','authored retained extraction')
        head = self.git('rev-parse','HEAD')
        self.admission = dict(version=1,issue='UIF-95',issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32',
            owner='source-owner',head=head,base=base,branch='feature/retained-source',
            workspace=str(self.workspace),source_commit=base,mapping=mapping,outputs=outputs,author='source-author',
            review=dict(record='independent-review/exact-head',reviewer='independent-reviewer',
                        decision='accepted',head=head,base=base))
        self.admission_path = self.root/'owner-admission.json'
        self.spec = {k:v for k,v in self.admission.items() if k in
                     ('issue','issue_id','owner','head','base','branch','workspace','outputs')}
        self.spec.update(version=2,stage='verify',profile=operations.EXTRACTION_PROFILE,
            policy_sha256=stage.file_hash(operations.POLICY),
            runner_sha256=stage.file_hash(TOOLS/'windmill_runner.py'),
            executor_sha256=stage.file_hash(TOOLS/'stokowski_operations.py'),
            execution=dict(task_fit='deterministic retained byte mapping validation',requested_model=None,
                           requested_effort=None,provider_route='none',
                           resolved_model=None,resolution_status='not-applicable'))
        self.pin()

    def git(self,*args):
        return subprocess.check_output(['git','-C',str(self.workspace),'-c','core.hooksPath=/dev/null',
            '-c','commit.gpgsign=false','-c','user.name=Fixture','-c','user.email=fixture@example.invalid',*args],
            text=True,stderr=subprocess.PIPE).strip()

    def pin(self):
        self.admission_path.write_text(json.dumps(self.admission,sort_keys=True))
        self.spec['acceptance_sha256'] = stage.file_hash(self.admission_path)
        self.spec['origin'] = dict(kind='reviewed-extraction',
            admission_sha256=self.spec['acceptance_sha256'],
            review_sha256=operations.digest(self.admission['review']),
            **{k:self.admission[k] for k in ('source_commit','mapping','author')})

    def bind(self):
        return stage.bind_extraction(self.runtime,self.spec,self.admission_path,self.workspace)

    def test_source_only_binds_without_coding_receipt_and_reopens_without_replay(self):
        key = self.bind()
        self.assertEqual(self.bind(),key)
        record = json.loads((self.runtime/'validation-bindings.json').read_text())
        self.assertEqual(record['history'],[])
        self.assertEqual(record['issues']['UIF-95']['origin'],'reviewed-extraction')
        self.assertNotIn('native_receipt_sha256',record['issues']['UIF-95'])
        self.assertFalse((self.runtime/'attempts').exists())
        remote = FaultedWindmill()
        journal = operations.Journal(self.runtime/'operations')
        state = asyncio.run(journal.tick(key,remote))
        remote.complete(state['windmill_job_id'],self.spec)
        self.assertEqual(asyncio.run(journal.tick(key,remote))['status'],'succeeded')
        self.assertEqual(asyncio.run(operations.Journal(self.runtime/'operations').tick(key,remote))['status'],'succeeded')
        self.assertEqual(len(remote.submissions),1)

    def test_rejected_stale_missing_and_self_review_fail_even_when_repinned(self):
        original = copy.deepcopy(self.admission)
        for changes in ({'decision':'rejected'},{'head':'0'*40},{'base':'0'*40},
                        {'reviewer':'source-author'},{'record':''}):
            self.admission = copy.deepcopy(original)
            self.admission['review'].update(changes)
            self.pin()
            with self.assertRaises(operations.OperationError): self.bind()
        self.admission['review'] = {}
        self.pin()
        with self.assertRaises(operations.OperationError): self.bind()

    def test_changed_admission_or_origin_identity_is_rejected(self):
        for field,value in [('owner','foreign-owner'),('head','0'*40),('base','0'*40),
                            ('workspace',str(self.root/'workspaces/other'))]:
            spec = copy.deepcopy(self.spec)
            spec[field] = value
            with self.assertRaises(operations.OperationError):
                stage.bind_extraction(self.runtime,spec,self.admission_path)
        self.admission_path.write_text(self.admission_path.read_text()+' ')
        with self.assertRaises(operations.OperationError): self.bind()
        self.admission_path.unlink()
        with self.assertRaises(operations.OperationError): self.bind()

    def test_wrong_mapping_hash_dirty_branch_head_and_workspace_rejected(self):
        original = copy.deepcopy(self.spec)
        for key,value in [('kind','native-coding'),('source_commit','0'*40),('review_sha256','0'*64)]:
            self.spec = copy.deepcopy(original)
            self.spec['origin'][key] = value
            with self.assertRaises(operations.OperationError): self.bind()
        self.spec = original
        with self.assertRaises(operations.OperationError):
            stage.bind_extraction(self.runtime,self.spec,self.admission_path,self.root)
        path = self.workspace/next(iter(self.spec['outputs']))
        path.write_text('altered source')
        with self.assertRaises(operations.OperationError): self.bind()
        self.git('add','.')
        self.git('commit','-qm','drift')
        with self.assertRaises(operations.OperationError): self.bind()

    def test_mapping_and_outputs_are_verified_against_original_commit(self):
        old = next(iter(self.admission['mapping']))
        self.admission['mapping']['retained/absent.py'] = self.admission['mapping'].pop(old)
        self.pin()
        with self.assertRaises(operations.OperationError): self.bind()

    def test_workspace_canonical_schema_and_fixed_candidate_commands(self):
        for root in ('/tmp/anything','/offmenu/data/.offmenu-platform/workspaces/../x',
                     '/offmenu/data/.offmenu-platform/workspaces/a/b',str(self.workspace)+'/'):
            with self.assertRaises(operations.OperationError):
                operations.validated(dict(self.spec,workspace=root))
        command = operations.bridge_arguments(self.spec)['command']
        self.assertTrue(command.startswith('cd /offmenu && export PYTHONPATH=/offmenu/src GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0=/offmenu &&'))
        self.assertIn('cd '+str(self.workspace),command)
        self.assertIn(str(self.workspace)+'/src',command)
        self.assertIn('/offmenu/.venv-delivery/bin/python',command)
        self.assertIn('PYTHONDONTWRITEBYTECODE=1',command)
        self.assertIn(self.spec['base'],command)
        self.assertIn('wfp_retained',command)
        self.assertNotIn(str(self.workspace)+'/.venv-delivery',command)
        self.assertNotIn('git clone',command)
        args = operations.bridge_arguments(self.spec)
        self.assertEqual(args['mode'],'read')
        self.assertEqual(args['resources']['write_roots'],[])
        self.assertEqual(args['timeout_seconds'],180)

    def test_accepted_validators_import_exact_candidate_source(self):
        tests = self.workspace/'tests/delivery'
        tests.mkdir(parents=True)
        (self.workspace/'src/target.py').write_text('answer=42\n')
        validator = tests/'test_baseline.py'
        validator.write_text('import unittest, target\nclass Baseline(unittest.TestCase):\n def test_answer(self): self.assertEqual(target.answer,42)\n')
        self.git('add','.')
        self.git('commit','-qm','accepted authored validator')
        accepted_base = self.git('rev-parse','HEAD')
        (self.workspace/'src/target.py').write_text('answer=0\n')
        validator.write_text('import unittest\nclass Weakened(unittest.TestCase):\n def test_empty(self): pass\n')
        command = operations.bridge_arguments(dict(self.spec,base=accepted_base))['command']
        tokens = shlex.split(command)
        code = next(token for token in tokens if 'ACCEPTED_CONTROL_VALIDATORS' in token)
        code = code.replace("'/offmenu/.venv-delivery/bin/python'",repr(sys.executable))
        result = subprocess.run([sys.executable,'-c',code],cwd=self.workspace,
            env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=20)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('ACCEPTED_CONTROL_VALIDATORS '+accepted_base,result.stdout)
        self.assertIn('0 != 42',result.stderr)

    def test_symlink_workspace_and_extra_source_are_rejected(self):
        alias = self.root/'workspaces/alias'
        alias.symlink_to(self.workspace,target_is_directory=True)
        self.admission['workspace'] = str(alias)
        self.spec['workspace'] = str(alias)
        self.pin()
        with self.assertRaises(operations.OperationError):
            stage.bind_extraction(self.runtime,self.spec,self.admission_path)
        self.admission['workspace'] = str(self.workspace)
        self.spec['workspace'] = str(self.workspace)
        (self.workspace/'extra.py').write_text('unreviewed source')
        self.git('add','extra.py')
        self.git('commit','-qm','unexpected extra source')
        self.admission['head'] = self.git('rev-parse','HEAD')
        self.admission['review']['head'] = self.admission['head']
        self.spec['head'] = self.admission['head']
        self.pin()
        with self.assertRaises(operations.OperationError): self.bind()

    def test_host_mirror_keeps_exact_jailed_workspace_in_remote_command(self):
        remote = '/offmenu/data/.offmenu-platform/workspaces/reviewed-candidate'
        self.admission['workspace'] = self.spec['workspace'] = remote
        self.pin()
        with patch.object(operations,'WORKSPACES',PurePosixPath('/offmenu/data/.offmenu-platform/workspaces')):
            key = self.bind()
            self.assertEqual(self.bind(),key)
            selected = json.loads((self.runtime/'validation-bindings.json').read_text())['issues']['UIF-95']
            self.assertEqual(selected['workspace'],remote)
            self.assertEqual(selected['local_source_root'],str(self.workspace))
            command = operations.bridge_arguments(self.spec)['command']
            self.assertIn('cd '+remote,command)
            self.assertIn(remote+'/src',command)
            self.assertNotIn(str(self.workspace),command)
            spec,_ = operations.Journal(self.runtime/'operations').read(key)
            self.assertEqual(spec,self.spec)

    def test_local_mirror_aliases_and_nested_git_root_are_rejected(self):
        alias = self.root/'alias'
        alias.symlink_to(self.workspace,target_is_directory=True)
        nested = self.workspace/'retained'
        for root in (alias, nested, 'relative/path', str(self.workspace)+'/',
                     str(self.workspace)+'/../candidate'):
            with self.subTest(root=str(root)), self.assertRaises(operations.OperationError):
                stage.bind_extraction(self.runtime,self.spec,self.admission_path,root)

    def test_admission_must_be_outside_both_candidates(self):
        for root in (self.workspace,self.runtime):
            path = root/'admission.json'
            path.write_bytes(self.admission_path.read_bytes())
            spec = copy.deepcopy(self.spec)
            admission = copy.deepcopy(self.admission)
            admission['workspace'] = spec['workspace'] = str(root)
            path.write_text(json.dumps(admission,sort_keys=True))
            spec['acceptance_sha256'] = spec['origin']['admission_sha256'] = stage.file_hash(path)
            with patch.object(operations,'WORKSPACES',PurePosixPath(root.parent)):
                with self.assertRaisesRegex(operations.OperationError,'outside local and remote'):
                    stage.bind_extraction(self.runtime,spec,path,self.workspace)
            path.unlink()

    def test_clean_mirror_with_wrong_branch_or_untracked_source_is_rejected(self):
        self.git('checkout','-qb','feature/wrong-branch')
        with self.assertRaises(operations.OperationError): self.bind()
        self.git('checkout','feature/retained-source')
        (self.workspace/'untracked.py').write_text('unreviewed')
        with self.assertRaises(operations.OperationError): self.bind()

    def test_historical_source_object_need_not_be_candidate_ancestor(self):
        source = self.git('commit-tree',self.git('rev-parse',self.spec['base']+'^{tree}'),
                          '-m','separate historical source')
        self.git('branch','feature/historical-source',source)
        self.admission['source_commit'] = source
        self.pin()
        self.bind()

    def test_nonancestor_base_wrong_source_bytes_and_output_symlink_rejected(self):
        original = copy.deepcopy(self.admission)
        unrelated = self.git('commit-tree',self.git('rev-parse',self.spec['base']+'^{tree}'),
                             '-m','unrelated base')
        self.admission['base'] = self.admission['review']['base'] = self.spec['base'] = unrelated
        self.pin()
        with self.assertRaises(operations.OperationError): self.bind()
        self.admission = original
        self.spec['base'] = original['base']
        old = next(iter(self.admission['mapping']))
        self.admission['mapping']['baseline'] = self.admission['mapping'].pop(old)
        self.pin()
        with self.assertRaises(operations.OperationError): self.bind()
        self.admission['mapping'][old] = self.admission['mapping'].pop('baseline')
        self.pin()
        output = self.workspace/self.admission['mapping'][old]
        output.unlink()
        output.symlink_to(self.workspace/old)
        with self.assertRaises(operations.OperationError): self.bind()

    def test_command_runs_one_control_suite_without_wfp_fixture_replay(self):
        tokens = shlex.split(operations.bridge_arguments(self.spec)['command'])
        code = [tokens[index+1] for index,token in enumerate(tokens) if token == '-c']
        controls = [value for value in code if 'ACCEPTED_CONTROL_VALIDATORS' in value]
        self.assertEqual(len(controls),1)
        self.assertEqual(sum(value.count("'unittest'") for value in code),1)
        self.assertNotIn('-m unittest', ' '.join(tokens))
        self.assertIn("str(control/'tests/delivery')",controls[0])
        self.assertNotIn('test_wfp_retained.py', '\n'.join(code).replace(json.dumps(self.spec,sort_keys=True),''))
        self.assertNotIn('wfp-retained-authored-fixtures.json',controls[0])
        self.assertEqual(code[0],code[-1])

    def test_v1_key_command_and_executor_hash_remain_byte_identical(self):
        accepted = subprocess.check_output(['git','show','7780c8602b52e9f2fc7e6a38e5d08d8ad74f09e1:tools/delivery/stokowski_operations.py'])
        original_path = self.root/'original_operations.py'
        original_path.write_bytes(accepted)
        module_spec = importlib.util.spec_from_file_location('original_operations',original_path)
        original = importlib.util.module_from_spec(module_spec)
        module_spec.loader.exec_module(original)
        v1 = {k:v for k,v in self.spec.items() if k not in ('origin','workspace','execution')}
        v1.update(version=1,profile='delivery-suite',executor_sha256=hashlib.sha256(accepted).hexdigest())
        self.assertEqual(v1['executor_sha256'],'9b9bc4a40c16c6f31e15b947fcb78aeb3f299f96fdf446d498aaed30d3888785')
        self.assertEqual(original.operation_key(v1),operations.operation_key(v1))
        for action in ('run','status','cancel'):
            self.assertEqual(original.bridge_arguments(v1,action),operations.bridge_arguments(v1,action))
