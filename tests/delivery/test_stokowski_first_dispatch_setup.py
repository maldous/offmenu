"""First coding setup only: synthetic provider authority and real local Git.

No provider, Pool, protected writer, service or coding child is invoked.
"""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import test_stokowski_current_dispatch as fixtures
import stokowski_adapter as adapter
from symphony_capacity import AdmissionError

REAL_CHECK_OUTPUT = subprocess.check_output


class FirstDispatchSetupTests(unittest.TestCase):
    def fixture(self):
        fixture = fixtures.CurrentDispatchTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def provider_fixture(self):
        f = self.fixture()
        issue, runtime = f.qualify(934)
        c = f.current
        # These seams represent separately qualified protected publication;
        # immutable task/admission checks and the actual refresh code still run.
        f.stack.enter_context(patch.object(c, 'guard'))
        f.stack.enter_context(patch.object(c, '_check_task_control_source'))
        producer = f.source/'tools/delivery/symphony_launch.py'
        shutil.copyfile(Path(__file__).resolve().parents[2]/'tools/delivery/symphony_launch.py', producer)
        c.config['source_sha256']['tools/delivery/symphony_launch.py'] = adapter.file_sha(producer)
        task = json.loads((runtime/'manifest.json').read_text())['tasks'][issue.identifier]
        authority = dict(decision='owner-qualified', issue_id=issue.id,
                         accepted_scope=task['allowed_paths'], acceptance=task['acceptance'],
                         handoff={'fixture':'handoff'})
        c.state['intake'] = {issue.identifier:dict(reference='fixture',status='qualified',authority=authority)}
        c.state['successor_request'] = dict(status='published',handoff=authority['handoff'])
        f.stack.enter_context(patch.object(c,'_intake_authority',return_value=(None,authority)))
        f.stack.enter_context(patch.object(c,'_private_pin',side_effect=[
            {'task_packet':{'fixture':'packet'}},
            dict(selected_current=dict(task_runtime=str(runtime)),
                 execution_outcome=dict(uuid=issue.id),expires_at=time.time()+600)]))
        probe = Mock(side_effect=lambda *args:dict(route='codex-chatgpt',available=True,
            requested_model=adapter.MODEL,checked_at=time.time(),session_ceiling=1))
        f.stack.enter_context(patch.dict(sys.modules, symphony_launch=SimpleNamespace(
            __file__=str(producer), provider_proof=probe)))
        f.write(runtime/'provider-proof.json',dict(route='codex-chatgpt',available=True,
            checked_at=time.time()-600,session_ceiling=1))
        return f, issue.identifier, runtime, probe

    def test_stale_published_first_coding_refreshes_and_archives_exact_bytes(self):
        f, issue, runtime, probe = self.provider_fixture()
        original = (runtime/'provider-proof.json').read_bytes()
        immutable = {name:(runtime/name).read_bytes() for name in
                     ('current-admission.json','manifest.json','requests/'+issue+'.json')}
        selected, _, _ = f.current.context(issue)
        self.assertEqual(selected,runtime)
        probe.assert_called_once_with(adapter.MODEL,f.policy['symphony']['provider_session_ceiling'])
        archived = runtime/'provider-proof-history'/(hashlib.sha256(original).hexdigest()+'.json')
        self.assertEqual(archived.read_bytes(),original)
        self.assertEqual(json.loads((runtime/'provider-proof.json').read_text())['requested_model'],adapter.MODEL)
        self.assertEqual(immutable,{name:(runtime/name).read_bytes() for name in immutable})

    def test_retained_attempt_and_readonly_do_not_probe(self):
        f, issue, runtime, probe = self.provider_fixture()
        original = (runtime/'provider-proof.json').read_bytes()
        f.current.read_only = True
        with self.assertRaisesRegex(AdmissionError,'provider_unavailable_or_stale'):
            f.current.context(issue)
        f.current.read_only = False
        (runtime/'attempts'/issue).mkdir()
        with self.assertRaisesRegex(AdmissionError,'provider_unavailable_or_stale'):
            f.current.context(issue)
        probe.assert_not_called()
        self.assertEqual((runtime/'provider-proof.json').read_bytes(),original)
        self.assertFalse((runtime/'provider-proof-history').exists())

    def test_producer_pin_and_review_do_not_probe(self):
        f, issue, runtime, probe = self.provider_fixture()
        f.current.context(issue,review=True)
        f.current.config['source_sha256']['tools/delivery/symphony_launch.py'] = '0'*64
        with self.assertRaisesRegex(AdmissionError,'provider_source_pin'):
            f.current.context(issue)
        probe.assert_not_called()

    def test_normal_workspace_seam_uses_self_contained_bundle_and_refuses_dirty_retained(self):
        f = self.fixture()
        issue, runtime = f.qualify(935)
        source = f.temp/'real-source'
        source.mkdir()
        def git(*args):
            return REAL_CHECK_OUTPUT(['git','-C',str(source),*args],text=True).strip()
        git('init','-b','bugfix/first-dispatch-test')
        (source/'owned.txt').write_text('source\n')
        git('add','owned.txt')
        git('-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-m','fixture')
        head, tree = git('rev-parse','HEAD'), git('rev-parse','HEAD^{tree}')
        manifest = json.loads((runtime/'manifest.json').read_text())
        manifest.update(base_revision=head,branch='bugfix/first-dispatch-test')
        f.adapted()
        import stokowski.workspace as workspace
        with patch.object(f.current,'context',return_value=(runtime,manifest,source)), \
             patch.object(subprocess,'check_output',REAL_CHECK_OUTPUT):
            result = asyncio.run(workspace.ensure_workspace(f.runtime/'workspaces',issue.identifier,None))
            target = runtime/'workspaces'/issue.identifier
            self.assertEqual(result.path,target)
            self.assertEqual(REAL_CHECK_OUTPUT(['git','-C',str(target),'rev-parse','HEAD^{tree}'],text=True).strip(),tree)
            self.assertFalse((target/'.git/objects/info/alternates').exists())
            self.assertEqual(target.stat().st_mode & 0o777,0o700)
            self.assertFalse(adapter.clone_current_workspace(source,target,head,manifest['branch']))
            (target/'owned.txt').write_text('retained edit\n')
            with self.assertRaisesRegex(AdmissionError,'needs reconciliation'):
                adapter.clone_current_workspace(source,target,head,manifest['branch'])
            self.assertEqual((target/'owned.txt').read_text(),'retained edit\n')
            self.assertEqual(git('rev-parse','HEAD'),head)


if __name__ == '__main__':
    unittest.main()
