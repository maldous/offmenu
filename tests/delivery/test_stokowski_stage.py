"""Native-output/candidate binding tests with real Git and immutable receipts."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0,str(TOOLS))
import stokowski_stage as stage
import stokowski_operations as operations


class StageBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.issue = 'UIF-92'
        self.runtime = self.root/'.delivery/stokowski/run'
        self.environment = dict(os.environ,GIT_AUTHOR_NAME='Fixture',GIT_COMMITTER_NAME='Fixture',
            GIT_AUTHOR_EMAIL='fixture@example.invalid',GIT_COMMITTER_EMAIL='fixture@example.invalid')
        self.git(self.root,'init','-b','feature/langgraph-delivery-standardization')
        (self.root/'repository-standard.json').write_text('{"runtime_hold_paths":[]}')
        (self.root/'.gitignore').write_text('.delivery/\n')
        (self.root/'tests').mkdir()
        (self.root/'tests/proof.py').write_text('baseline\n')
        self.git(self.root,'add','.')
        self.git(self.root,'commit','-m','Accepted fixture baseline')
        self.base = self.git(self.root,'rev-parse','HEAD')
        self.workspace = self.runtime/'workspaces'/self.issue
        self.workspace.parent.mkdir(parents=True)
        self.git(self.root,'clone','--shared',str(self.root),str(self.workspace))
        (self.workspace/'tests/proof.py').write_text('native output\n')
        (self.root/'tests/proof.py').write_text('native output\n')
        self.git(self.root,'add','tests/proof.py')
        self.git(self.root,'commit','-m','Integrate native output')
        task = {'issue_id':'8daac134-01ab-4a02-a4d2-c0c417d0bd32','owner':'coding-owner',
            'purpose':'Meaningful fixture','allowed_paths':['tests/proof.py'],
            'acceptance':['Behavior verified'],'resources':{'cpu_millis':1,'memory_bytes':1024,
            'io_slots':1,'output_bytes':0},'attempt_limit':1}
        manifest = {'version':1,'project_id':'ce60c1ab-a732-4a71-8471-14c9dc393886',
            'label':'offmenu-fixture','base_revision':self.base,
            'branch':'feature/langgraph-delivery-standardization','tasks':{self.issue:task}}
        (self.runtime/'manifest.json').write_text(json.dumps(manifest))
        self.receipt_path = self.runtime/'attempts'/self.issue/'receipt.json'
        self.receipt_path.parent.mkdir(parents=True)
        receipt = {'status':'succeeded','child_tree_gone':True,'scope_violations':[],
            'source_head':self.base,'output_sha256':{'tests/proof.py':stage.file_hash(self.workspace/'tests/proof.py')}}
        self.receipt_path.write_text(json.dumps(receipt))
        self.spec = {'version':1,'issue':self.issue,'issue_id':task['issue_id'],'stage':'verify',
            'owner':'integration-writer','head':self.git(self.root,'rev-parse','HEAD'),'base':self.base,
            'policy_sha256':stage.file_hash(operations.POLICY),
            'runner_sha256':stage.file_hash(TOOLS/'windmill_runner.py'),
            'executor_sha256':stage.file_hash(Path(operations.__file__)),
            'acceptance_sha256':operations.digest({'task':task,'native_receipt_sha256':stage.file_hash(self.receipt_path),'profile':'delivery-suite'}),
            'profile':'delivery-suite','outputs':{'tests/proof.py':stage.file_hash(self.root/'tests/proof.py')}}
        self.source_patch = patch.object(stage,'SOURCE',self.root)
        self.source_patch.start()
        self.addCleanup(self.source_patch.stop)

    def git(self,root,*args):
        return subprocess.check_output(['git','-c','core.hooksPath=/dev/null',
            '-c','commit.gpgsign=false','-C',str(root),*args],env=self.environment,
            text=True,stderr=subprocess.PIPE).strip()

    def test_exact_native_output_binds_once_and_reopens_same_operation(self):
        key = stage.bind(self.runtime,self.spec)
        self.assertEqual(stage.bind(self.runtime,self.spec),key)
        record = json.loads((self.runtime/'validation-bindings.json').read_text())
        self.assertEqual(record['issues'][self.issue]['operation_key'],key)
        self.assertEqual(record['history'],[])

    def test_modified_native_output_is_not_accepted_from_old_receipt(self):
        (self.workspace/'tests/proof.py').write_text('drift\n')
        with self.assertRaisesRegex(operations.OperationError,'Coding output changed'):
            stage.bind(self.runtime,self.spec)

    def test_untracked_maintained_source_is_not_part_of_the_published_candidate(self):
        (self.root/'tests/unpublished.py').write_text('unpublished\n')
        with self.assertRaisesRegex(operations.OperationError,'Uncommitted maintained source'):
            stage.bind(self.runtime,self.spec)

    def test_changed_integrated_output_requires_explicit_derivation(self):
        (self.root/'tests/proof.py').write_text('reviewed derived output\n')
        self.git(self.root,'add','tests/proof.py')
        self.git(self.root,'commit','-m','Reviewed integration adjustment')
        self.spec.update(head=self.git(self.root,'rev-parse','HEAD'),
                         outputs={'tests/proof.py':stage.file_hash(self.root/'tests/proof.py')})
        with self.assertRaisesRegex(operations.OperationError,'explicit reviewed derivation'):
            stage.bind(self.runtime,self.spec)
        stage.bind(self.runtime,self.spec,'Explicit fixture adaptation without changing accepted behavior')
        record = json.loads((self.runtime/'validation-bindings.json').read_text())
        self.assertIn('tests/proof.py',record['issues'][self.issue]['derivation'])

    def test_acceptance_cannot_be_replaced_by_an_arbitrary_hash(self):
        self.spec['acceptance_sha256'] = '0'*64
        with self.assertRaisesRegex(operations.OperationError,'Acceptance is not bound'):
            stage.bind(self.runtime,self.spec)


if __name__ == '__main__':
    unittest.main()
