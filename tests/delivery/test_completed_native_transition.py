"""Same-runtime native validation transition, using real Git and read-only SQL."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/delivery')]
import stokowski_adapter as adapter
import stokowski_operations as operations
import stokowski_stage as stage
import stokowski_mcp as mcp
from symphony_capacity import AdmissionError,digest
from symphony_tasks import runtime_lease_ids


@unittest.skipUnless(importlib.util.find_spec('stokowski'),'Use pinned Stokowski environment')
class CompletedNativeTransitionTests(unittest.TestCase):
    def git(self,root,*args):
        return subprocess.check_output(['git','-C',str(root),'-c','core.hooksPath=/dev/null',
            '-c','user.name=Fixture','-c','user.email=fixture@example.invalid','-c','commit.gpgsign=false',*args],
            stderr=subprocess.PIPE).decode().strip()

    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value))

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.control=self.root/'control';self.control.mkdir()
        self.git(self.control,'init','-b','bugfix/control')
        for module in (operations,stage,mcp):
            target=self.control/'tools/delivery'/Path(module.__file__).name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(module.__file__,target)
        shutil.copyfile(ROOT/'tools/delivery/windmill_runner.py',self.control/'tools/delivery/windmill_runner.py')
        self.output='tests/web/enrichment-resilience.test.mjs'
        target=self.control/self.output;target.parent.mkdir(parents=True);target.write_text('// baseline\n')
        self.git(self.control,'add','.');self.git(self.control,'commit','-qm','SYNTHETIC original control')
        self.base=self.git(self.control,'rev-parse','HEAD')
        self.runtime=self.root/'native';self.workspace=self.runtime/'workspaces/UIF-102'
        self.workspace.parent.mkdir(parents=True)
        self.git(self.root,'clone','--shared',str(self.control),str(self.workspace))
        self.candidate=self.root/'candidate';self.git(self.root,'clone','--shared',str(self.control),str(self.candidate))
        self.git(self.candidate,'checkout','-b','bugfix/contribution')
        for repo in (self.workspace,self.candidate):(repo/self.output).write_text('// SYNTHETIC native output\n')
        self.git(self.candidate,'add','.');self.git(self.candidate,'commit','-qm','SYNTHETIC original output')
        self.head=self.git(self.candidate,'rev-parse','HEAD')
        (self.control/'control-only').write_text('new reviewed control code\n')
        self.git(self.control,'add','.');self.git(self.control,'commit','-qm','SYNTHETIC control adoption')
        self.control_head=self.git(self.control,'rev-parse','HEAD')
        policy=json.loads((ROOT/'tools/delivery/capacity-policy.json').read_text())
        policy['symphony']['pool_path']=str(self.root/'pool')
        self.policy=policy;self.write(self.runtime/'capacity-policy.json',policy)
        task=dict(issue_id='00000000-0000-4000-8000-000000000102',owner='fixture-owner',purpose='Fixture',
            allowed_paths=[self.output],acceptance=['Exact native bytes'],resources=policy['symphony']['default_resources'],attempt_limit=1)
        self.manifest=dict(version=1,project_id=adapter.PROJECT,label='fixture',branch='bugfix/control',
            base_revision=self.base,tasks={'UIF-102':task})
        self.write(self.runtime/'manifest.json',self.manifest)
        request={'prompt':'Approved fixture','timeout_seconds':5};self.write(self.runtime/'requests/UIF-102.json',request)
        import stokowski
        installed=Path(stokowski.__file__).parent
        self.write(self.runtime/'installation.json',dict(source_revision=adapter.PIN,
            installed_source_sha256={n:adapter.file_sha(installed/n) for n in ('__init__.py','orchestrator.py')}))
        self.write(self.runtime/'provider-proof.json',dict(route='codex-chatgpt',available=True,checked_at=time.time(),session_ceiling=8))
        admission=dict(version=1,owner=task['owner'],issue='UIF-102',issue_id=task['issue_id'],source=str(self.control),inputs={},
            manifest_sha256=adapter.file_sha(self.runtime/'manifest.json'),request_sha256=adapter.file_sha(self.runtime/'requests/UIF-102.json'),
            policy_sha256=adapter.file_sha(self.runtime/'capacity-policy.json'),installation_sha256=adapter.file_sha(self.runtime/'installation.json'))
        self.write(self.runtime/'current-admission.json',admission)
        self.entry=dict(issue='UIF-102',issue_id=task['issue_id'],runtime=str(self.runtime),admission_sha256=adapter.file_sha(self.runtime/'current-admission.json'))
        self.binding=dict(branch=self.manifest['branch'],head=self.base,owner=task['owner'],write_roots=task['allowed_paths'],
            resources=task['resources'],task_sha256=digest(dict(runtime=str(self.runtime),manifest=self.manifest,request=request)))
        self.lease=runtime_lease_ids(self.runtime,self.manifest)['UIF-102'];self.directory=self.runtime/'attempts/UIF-102'
        self.write(self.directory/'intent.json',dict(lease=self.lease,binding=self.binding))
        self.write(self.directory/'dispatch-intent.json',dict(entry_sha256=digest(self.entry),owner=task['owner'],
            expected_lease=self.lease,request_sha256=admission['request_sha256'],manifest_sha256=admission['manifest_sha256']))
        self.receipt=dict(status='succeeded',child_tree_gone=True,accepted_delivery=False,issue='UIF-102',lease=self.lease,
            binding_sha256=digest(self.binding),parent_binding=self.binding,source_head=self.base,final_head=self.base,
            final_branch=self.manifest['branch'],source_identity_changed=False,scope_violations=[],session_id='SYNTHETIC-session',
            turn_completed=True,exit_code=0,output_sha256={self.output:adapter.file_sha(self.workspace/self.output)})
        self.write(self.directory/'receipt.json',self.receipt)
        database=self.root/'pool/state.sqlite';database.parent.mkdir()
        with sqlite3.connect(database) as db:
            db.execute('CREATE TABLE leases(id TEXT,binding TEXT,fingerprint TEXT,status TEXT,outcome TEXT)')
            db.execute('INSERT INTO leases VALUES(?,?,?,?,?)',(self.lease,json.dumps(self.binding),digest(self.binding),'finished','succeeded'))
        c=adapter.CurrentWork.__new__(adapter.CurrentWork);self.current=c
        c.root=self.root;c.runtime=self.root/'coordinator';c.runtime.mkdir();c.read_only=True;c.stopping=False
        c.config=dict(owner=task['owner'],source_head=self.control_head,policy_sha256=admission['policy_sha256'],installation_sha256=admission['installation_sha256'])
        c.owner_custody={'source_root':str(self.control)};c.entries={'UIF-102':self.entry};c.state={'tasks':{'UIF-102':{}},'references':{'UIF-102':self.entry}}
        self.addCleanup(patch.stopall);patch.object(adapter,'SOURCE',self.control).start()

    def test_completed_control_review_and_same_runtime_v1_contribution(self):
        before={p:p.read_bytes() for p in (self.runtime/'current-admission.json',self.runtime/'manifest.json',self.directory/'intent.json',self.directory/'receipt.json')}
        with patch.object(self.current,'guard') as guard:
            self.current.context('UIF-102',review=True);guard.assert_called()
            with self.assertRaisesRegex(AdmissionError,'current_task_source_drift'):self.current.context('UIF-102')
        profile='enrichment-resilience-focused';task=self.manifest['tasks']['UIF-102']
        spec=dict(version=1,issue='UIF-102',issue_id=task['issue_id'],owner=task['owner'],stage='validate',
            head=self.head,base=self.base,branch='bugfix/contribution',profile=profile,outputs=self.receipt['output_sha256'],
            acceptance_sha256=digest(dict(task=task,native_receipt_sha256=adapter.file_sha(self.directory/'receipt.json'),profile=profile)),
            policy_sha256=self.current.config['policy_sha256'],runner_sha256=adapter.file_sha(self.control/'tools/delivery/windmill_runner.py'),
            executor_sha256=adapter.file_sha(operations.__file__))
        # Profile execution/command/dispatcher are129-owned; this test supplies
        # only its agreed whitelist interface to exercise the actual v1 reader.
        with patch.dict(operations.PROFILES,{profile:['/bin/node','--test','--test-concurrency=1',self.output]}),patch.object(self.current,'guard'):
            journal=operations.Journal(self.runtime/'operations');key=journal.prepare(spec)
            selected=dict(operation_key=key,source_head=self.head,native_receipt_sha256=adapter.file_sha(self.directory/'receipt.json'),
                native_output_sha256=self.receipt['output_sha256'],derivation={},derivation_reason=None,candidate_root=str(self.candidate))
            self.write(self.runtime/'validation-bindings.json',dict(version=1,issues={'UIF-102':selected},history=[]))
            runtime,identity=self.current.validation_binding('UIF-102',self.entry)
            self.assertEqual(runtime,self.runtime);self.assertEqual(len(identity),64)
            self.assertEqual(self.current._native_review_branch('UIF-102',self.entry,self.runtime,self.manifest),'bugfix/contribution')
        for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)

    def test_unfinished_forged_or_drifted_native_proof_refuses_control_advance(self):
        for field,value in (('status','running'),('child_tree_gone',False),('lease','foreign'),
            ('parent_binding',{}),('source_head','f'*40),('scope_violations',['foreign']),('turn_completed',False)):
            changed=copy.deepcopy(self.receipt);changed[field]=value;self.write(self.directory/'receipt.json',changed)
            with self.subTest(field=field),self.assertRaises(AdmissionError):
                self.current._check_task_control_source('UIF-102',self.manifest,self.control,review=True)
        self.write(self.directory/'receipt.json',self.receipt)
        with sqlite3.connect(self.root/'pool/state.sqlite') as db:db.execute("UPDATE leases SET status='running'")
        with self.assertRaisesRegex(AdmissionError,'completed_native_lease'):
            self.current._check_task_control_source('UIF-102',self.manifest,self.control,review=True)

    def test_candidate_branch_output_drift_and_unrelated_profile_refuse(self):
        selected={'candidate_root':str(self.candidate)}
        spec=dict(version=1,profile='enrichment-resilience-focused',head=self.head,base=self.base,
            branch='bugfix/contribution',outputs=self.receipt['output_sha256'])
        self.current._native_contribution('UIF-102',self.runtime,self.manifest,selected,spec)
        for field,value in (('profile','delivery-suite'),('branch','bugfix/control'),('head',self.control_head),('outputs',{})):
            changed=dict(spec,**{field:value})
            with self.subTest(field=field),self.assertRaises(AdmissionError):
                self.current._native_contribution('UIF-102',self.runtime,self.manifest,selected,changed)
        (self.candidate/self.output).write_text('// changed after review\n')
        with self.assertRaisesRegex(AdmissionError,'native_contribution_source'):
            self.current._native_contribution('UIF-102',self.runtime,self.manifest,selected,spec)
