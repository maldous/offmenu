"""Real Git source/target proofs and finite Controller decisions; no API jobs."""
import copy
import hashlib
from pathlib import Path
import subprocess
import tempfile
import time
import unittest

from offmenu.delivery.engine import atomic, DeliveryError
from offmenu.delivery.identity_source_projection import qualify_projection, validate_projection
from offmenu.delivery.integration import Controller, fingerprint, _publisher_request


class IdentityProjectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root/'repository'
        self.repo.mkdir()
        self.git('init', '-b', 'develop')
        self.write('apps/web/server/handler.mjs', 'export default {};\n')
        self.output = 'tests/edge/handler-auth-dispatch.test.mjs'
        self.write(self.output, '// original identity fixture\n')
        self.commit('original base')
        self.original = self.git('rev-parse', 'HEAD')
        self.git('checkout', '-b', 'bugfix/identity-unit')
        self.write(self.output, '// independently reviewed identity fixture\n')
        self.commit('reviewed unit')
        self.head = self.git('rev-parse', 'HEAD')
        self.git('checkout', 'develop')
        self.write('tools/delivery/accepted.py', '# accepted delivery change\n')
        self.commit('accepted advanced target')
        self.target = self.git('rev-parse', 'HEAD')
        self.merge_tree = self.git('merge-tree', '--write-tree', self.target, self.head)
        self.outputs = {self.output:hashlib.sha256(
            self.git_bytes('show', self.head+':'+self.output)).hexdigest()}
        self.projection = dict(version=1,profile='identity-client-focused',
            source=dict(head=self.head,base=self.original,
                tree=self.git('rev-parse', self.head+'^{tree}'),branch='bugfix/identity-unit'),
            target=dict(base=self.target,tree=self.git('rev-parse', self.target+'^{tree}')),
            merge_tree=self.merge_tree,outputs=self.outputs,unit_sha256='1'*64,
            operation_key='2'*64,receipt=dict(path=str(self.root/'original-receipt.json'),
                sha256='3'*64),review_sha256='4'*64)
        self.snapshot = dict(observed_at=time.time(),publisher_owner='owner',
            policy_sha256='5'*64,capacity_policy_sha256='6'*64,
            validation=dict(operation_key='2'*64,status='succeeded',head=self.head,
                base=self.original,capacity_policy_sha256='6'*64,outputs=self.outputs,
                child_tree_gone=True,reconcile_required=False),
            review=dict(head=self.head,base=self.original,independent=True,
                evidence_id='original-independent-review',verdict='accept',findings=[]),
            unresolved_findings=[],source_tree=self.projection['source']['tree'],
            source_clean=True,publication_triggers_actions=False,
            automatic_integration_enabled=True,
            github=dict(repository='maldous/offmenu',number=200,merged=False,state='open',
                draft=False,head=self.head,base=self.target,head_branch='bugfix/identity-unit',
                base_branch='develop',mergeable=True))
        self.plan = dict(operations=[])
        self.binding = dict(version=2,repository='maldous/offmenu',pr_number=None,
            issue_id='8daac134-01ab-4a02-a4d2-c0c417d0bd32',owner='owner',
            head=self.head,base=self.target,tree=self.projection['source']['tree'],
            head_branch='bugfix/identity-unit',policy_sha256='5'*64,
            capacity_policy_sha256='6'*64,validation_operation_key='2'*64,
            outputs=self.outputs,source_projection=self.projection,
            publication=dict(plan_sha256=fingerprint(self.plan),
                qualification_sha256=fingerprint(self.snapshot)))

    def git_bytes(self, *args):
        return subprocess.check_output(['git','-C',str(self.repo),
            '-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',*args],
            stderr=subprocess.PIPE)

    def git(self, *args):
        return self.git_bytes(*args).decode().strip()

    def write(self, name, value):
        path = self.repo/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(value)

    def commit(self, message):
        self.git('add','.')
        self.git('commit','-qm',message)

    def controller(self, name='selected', binding=None):
        return Controller(self.root/name,binding or self.binding)

    def published(self, controller):
        # Synthetic canonical publication observation in an isolated test claim.
        # The real publisher owns these transitions; no live operation is issued.
        state = controller.status()
        state['publication'] = dict(effect='verified',pr_number=200)
        atomic(controller.directory/'state.json',state)

    def test_original_validation_publication_and_expected_merge_are_distinct(self):
        before = self.git('rev-parse','HEAD')
        self.assertIs(qualify_projection(self.repo,self.projection,self.binding),self.projection)
        self.assertEqual(self.git('rev-parse','HEAD'),before)
        controller = self.controller()
        config = dict(binding=self.binding,logicalOwner='owner',plan=self.plan,
                      snapshot=self.snapshot,workspace=str(self.repo))
        prepared = _publisher_request(controller,config,dict(op='prepare'))
        self.assertEqual(prepared['status'],'publication-ready')
        self.published(controller)
        result = controller.run(self.snapshot)
        self.assertEqual(result['status'],'merge-intent',result)
        self.assertEqual(result['action']['expected_base_sha'],self.target)
        self.assertEqual(result['action']['expected_head_sha'],self.head)
        merged = copy.deepcopy(self.snapshot)
        merged['github'].update(merged=True,merge_commit_sha='7'*40)
        merged.update(develop_contains_merge=True,merge_commit=dict(sha='7'*40,
            parents=[self.target,self.head],tree=self.merge_tree))
        result = controller.run(merged)
        self.assertEqual(result['status'],'merge-verified',result)
        self.assertIsNone(result.get('action'))  # Unit merge is not full-issue Done.
        self.assertEqual(self.snapshot['validation']['base'],self.original)

    def test_relabelled_validation_or_review_base_is_refused(self):
        for kind in ('validation','review'):
            with self.subTest(kind=kind):
                controller = self.controller(kind)
                self.published(controller)
                snapshot = copy.deepcopy(self.snapshot)
                snapshot[kind]['base'] = self.target
                result = controller.run(snapshot)
                self.assertEqual(result['status'],
                    'awaiting-validation' if kind == 'validation' else 'awaiting-independent-review')

    def test_wrong_canonical_merge_tree_is_refused(self):
        controller = self.controller()
        self.published(controller)
        self.assertEqual(controller.run(self.snapshot)['status'],'merge-intent')
        snapshot = copy.deepcopy(self.snapshot)
        snapshot['github'].update(merged=True,merge_commit_sha='7'*40)
        snapshot.update(develop_contains_merge=True,merge_commit=dict(sha='7'*40,
            parents=[self.target,self.head],tree=self.projection['source']['tree']))
        result = controller.run(snapshot)
        self.assertEqual(result['status'],'repair-required',result)
        self.assertEqual(result['reason'],'merged-tree-or-parent-readback-mismatch')

    def test_changed_inputs_owned_target_or_merge_result_are_refused(self):
        bad = copy.deepcopy(self.projection)
        bad['merge_tree'] = self.projection['target']['tree']
        with self.assertRaises(DeliveryError):
            qualify_projection(self.repo,bad)
        for name in ('apps/web/server/handler.mjs',self.output):
            with self.subTest(path=name):
                self.git('checkout','--detach',self.target)
                self.write(name,'// target drift\n')
                self.commit('target drift')
                bad = copy.deepcopy(self.projection)
                bad['target'] = dict(base=self.git('rev-parse','HEAD'),
                    tree=self.git('rev-parse','HEAD^{tree}'))
                if name != self.output:
                    bad['merge_tree'] = self.git('merge-tree','--write-tree',
                        bad['target']['base'],self.head)
                with self.assertRaises(DeliveryError):
                    qualify_projection(self.repo,bad)

    def test_other_profiles_and_default_binding_remain_strict(self):
        bad = copy.deepcopy(self.projection)
        bad['profile'] = 'current-journal-focused'
        with self.assertRaises(DeliveryError):
            validate_projection(bad)
        binding = copy.deepcopy(self.binding)
        del binding['source_projection']
        controller = self.controller(binding=binding)
        self.published(controller)
        self.assertEqual(controller.run(self.snapshot)['status'],'awaiting-validation')
        projected = self.controller('missing-workspace')
        with self.assertRaisesRegex(DeliveryError,'protected publisher workspace'):
            projected.prepare_publication(self.plan,self.snapshot)


if __name__ == '__main__':
    unittest.main()
