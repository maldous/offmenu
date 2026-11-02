"""Real isolated Git acquisition; no network, provider, Pool or live control."""
from pathlib import Path
import subprocess
import hashlib
import json
from types import SimpleNamespace
from unittest.mock import Mock, patch
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_source as source
from symphony_capacity import AdmissionError


class ProjectSourceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.repository = self.root/'project'
        self.repository.mkdir()
        self.git('init','-b','develop')
        (self.repository/'file.txt').write_text('accepted\n')
        self.commit('accepted')
        self.accepted = self.git('rev-parse','HEAD')
        self.tree = self.git('rev-parse','HEAD^{tree}')
        (self.repository/'file.txt').write_text('unaccepted tip\n')
        self.commit('later unaccepted tip')
        self.later = self.git('rev-parse','HEAD')
        self.git('checkout','-b','bugfix/controller')
        (self.repository/'file.txt').write_text('different control revision\n')
        self.commit('controller')
        self.control = self.git('rev-parse','HEAD')

    def git(self,*arguments):
        return subprocess.check_output(['git','-C',str(self.repository),
            '-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
            '-c','commit.gpgsign=false',*arguments],text=True,stderr=subprocess.PIPE).strip()

    def commit(self,message):
        self.git('add','file.txt');self.git('commit','-m',message)

    def context(self):
        root = self.root/'private'
        root.mkdir(exist_ok=True)
        def private(value):
            path=Path(value)
            if path != path.resolve() or not path.is_relative_to(root):
                raise AdmissionError('fixture private path')
            return path
        current=SimpleNamespace(root=root,private=private,guard=Mock(),read_only=False,
            stopping=False,owner_custody={'fixture':'protected owner'},
            config={'owner':'fixture-owner','source_head':self.control,'runtime_root':str(root)})
        self.git('remote','add','origin','git@github.com:maldous/offmenu.git')
        policy={'project_source':dict(repository='maldous/offmenu',branch='develop',
            origin='git@github.com:maldous/offmenu.git',source_repository=str(self.repository),
            seed=dict(head=self.accepted,tree=self.tree),
            accepted_facts_path=str(root/'accepted-project-source.json'))}
        return current,policy

    def evidence(self,head,tree):
        path=self.root/(head+'.json')
        path.write_text(json.dumps({'synthetic_trusted_accessor_fact':head}))
        return dict(repository='maldous/offmenu',branch='develop',head=head,tree=tree,
            evidence=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))

    def test_accepted_advance_control_separation_frozen_selection_and_receipt_refusal(self):
        current,policy=self.context()
        accepted=self.evidence(self.accepted,self.tree)
        (self.repository/'file.txt').write_text('preserve dirty primary work\n')
        before=(self.git('rev-parse','HEAD'),self.git('status','--porcelain'),
                self.git('show-ref','--heads'))
        first=source.acquire_project_source(current,'UIF-138',policy,accepted)
        destination=Path(first['source_checkout'])
        self.assertEqual((destination/'file.txt').read_text(),'accepted\n')
        self.assertEqual(first['base'],self.accepted)
        self.assertEqual(first['tree'],self.tree)
        self.assertEqual(first['branch'],'bugfix/owner-policy-uif-138-'+self.accepted[:12])
        self.assertEqual(destination.stat().st_mode & 0o777,0o700)
        self.assertFalse((destination/'.git/objects/info/alternates').exists())
        later_tree=self.git('rev-parse',self.later+'^{tree}')
        later=self.evidence(self.later,later_tree)
        # The authority accessor advances; an existing issue stays on its pin.
        self.assertEqual(source.acquire_project_source(current,'UIF-138',policy,later),first)
        snapshot={str(p):p.read_bytes() for p in current.root.rglob('*') if p.is_file()}
        with patch.object(source,'clone_current_workspace',side_effect=AssertionError('creation helper forbidden')):
            self.assertEqual(source.read_project_source(current.config,'UIF-138',policy),first)
            with self.assertRaisesRegex(AdmissionError,'not_materialized'):
                source.read_project_source(current.config,'UIF-999',policy)
        self.assertEqual({str(p):p.read_bytes() for p in current.root.rglob('*') if p.is_file()},snapshot)
        current.read_only=True
        self.assertEqual(source.acquire_project_source(current,'UIF-138',policy,later),first)
        current.read_only=False
        second=source.acquire_project_source(current,'UIF-139',policy,later)
        self.assertEqual(second['base'],self.later)
        self.assertEqual(current.config['source_head'],self.control)
        self.assertEqual((self.git('rev-parse','HEAD'),self.git('status','--porcelain'),
                          self.git('show-ref','--heads')),before)
        receipt=Path(first['acquisition_ref']['path'])
        receipt.write_text('{}')
        with self.assertRaisesRegex(AdmissionError,'receipt_drift'):
            source.acquire_project_source(current,'UIF-138',policy,later)
        self.assertEqual(receipt.read_text(),'{}')

    def test_evidence_drift_refuses_before_selection_or_git_writes(self):
        current,policy=self.context()
        accepted=self.evidence(self.accepted,self.tree)
        Path(accepted['evidence']['path']).write_text('changed fact')
        before=self.git('show-ref')
        with self.assertRaisesRegex(AdmissionError,'evidence_drift'):
            source.acquire_project_source(current,'UIF-138',policy,accepted)
        self.assertFalse((current.root/'project-sources').exists())
        self.assertEqual(self.git('show-ref'),before)

    def test_unknown_object_fetch_retains_intent_without_network_retry(self):
        current,policy=self.context()
        accepted=self.evidence('d'*40,self.tree)
        original=subprocess.run
        attempts=[]
        def run(command,**kwargs):
            if 'fetch' in command and 'git@github.com:maldous/offmenu.git' in command:
                attempts.append(command)
                raise subprocess.TimeoutExpired(command,90)
            return original(command,**kwargs)
        with patch.object(source.subprocess,'run',side_effect=run):
            with self.assertRaises(subprocess.TimeoutExpired):
                source.acquire_project_source(current,'UIF-138',policy,accepted)
            with self.assertRaisesRegex(AdmissionError,'fetch_requires_reconciliation'):
                source.acquire_project_source(current,'UIF-138',policy,accepted)
            with self.assertRaisesRegex(AdmissionError,'not_materialized'):
                source.read_project_source(current.config,'UIF-138',policy)
        self.assertEqual(len(attempts),1)
        self.assertFalse(list(current.root.rglob('acquisition.json')))


if __name__ == '__main__':
    unittest.main()
