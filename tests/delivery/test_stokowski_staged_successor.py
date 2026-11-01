"""Existing staged producer through native successor; all actors are synthetic."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import Mock, patch

import test_stokowski_current_dispatch as fixtures
from test_stokowski_nonimplementation_stage import reviewed_records
import stokowski_adapter as adapter
import stokowski_operations as operations
import stokowski_worker as worker
from symphony_capacity import AdmissionError, digest


class StagedSuccessorTests(unittest.TestCase):
    def setUp(self):
        n = self.native = fixtures.NativeSuccessorBindingTests(methodName='runTest')
        n.setUp()
        self.addCleanup(n.doCleanups)
        c, f = self.c, self.f = n.c, n.f
        self.original_issue, self.original_runtime = n.original[:2]
        self.original_bytes = f.snapshot(self.original_runtime)
        # Finish the synthetic trigger's actual resource-pool lease as required
        # by normal rearm; no lease is created for the new read-only stage.
        from symphony_capacity import Pool
        intent = adapter.read_record(self.original_runtime/'attempts'/self.original_issue.identifier/'intent.json')
        pool = Pool(c.policy['symphony']['pool_path'],c.policy)
        pool.admit(intent['lease'],intent['binding'],adapter.read_record(self.original_runtime/'provider-proof.json'),
                   dict(cpu_millis=64000,available_memory_bytes=10**12,available_disk_bytes=10**12))
        pool.finish(intent['lease'],True,'succeeded')
        # Real v3 qualification: committed output, independent typed review,
        # original synthetic provenance, immutable selection and prepared Journal.
        candidate = c.temp/'reviewed-stage-candidate'
        candidate.mkdir()
        def git(*args):
            return subprocess.run(['git','-C',str(candidate),*args],check=True,
                capture_output=True,text=True).stdout.strip()
        git('init','-b','feature/test-current')
        for name in operations.REVIEWED_TESTS:
            p = candidate/'tests/delivery'/(name+'.py')
            p.parent.mkdir(parents=True,exist_ok=True)
            p.write_text('# Synthetic accepted control source, never executed here.\n')
        git('add','.')
        def commit(message):
            git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid',
                '-c','commit.gpgsign=false','commit','-m',message)
            return git('rev-parse','HEAD')
        base = commit('Synthetic accepted source')
        target = candidate/'tools/delivery/manual.py'
        target.parent.mkdir(parents=True)
        target.write_text('synthetic_reviewed_output = True\n')
        git('add','.')
        head = commit('Synthetic exact reviewed contribution')
        c.stack.enter_context(patch.object(operations,'POLICY',c.source/'tools/delivery/capacity-policy.json'))
        self.validation, self.spec, self.key, binding = reviewed_records(c,candidate,base,head,
            {'tools/delivery/manual.py':adapter.file_sha(target)},
            issue_name=f.issue['identifier'],issue_id=f.issue['uuid'])
        task = f.manifest['tasks'][f.issue['identifier']]
        task.update(stage='validation',allowed_paths=[],input_paths=list(self.spec['outputs']),stage_binding=binding)
        f.scope = task['input_paths']
        f.config['stage_binding'] = binding
        f.packet.update(stage='validation',scope=f.scope)
        f.write(f.qualified/'manifest.json',f.manifest)
        self.repin()
        n.bind_config()
        # Use the actual native consumer and its ephemeral permit on the real
        # terminal trigger, rather than treating a cached projection as a permit.
        harness = c.native_harness_fixture()
        module = self.module = harness.module
        packet = json.loads(json.dumps(harness.packet).replace(harness.issue.id,self.original_issue.id)
                            .replace(harness.issue.identifier,self.original_issue.identifier))
        action = module.plan_delivery(packet['linear'],packet['policy'])['actions'][0]
        c.write(harness.packet_path,packet)
        selected = dict(binding=dict(issue_id=self.original_issue.id,project_id=adapter.PROJECT,
            owner=c.current.config['owner'],packet_sha256=module.fingerprint(packet),
            operation_id=action['action_id'],phase='linear',
            unit_sha256=module.fingerprint(c.current.gate_binding(self.original_issue,observation=True))),
            packet=f.ref(harness.packet_path),context={})
        c.write(harness.selected,selected)
        c.current.config['native_harness_boundaries'] = {self.original_issue.identifier:f.ref(harness.selected)}
        self.effect = dict(operation_id=action['action_id'],status='ready',child_tree_gone=True)
        def step(*args):
            self.effect['status']='verified'
            return dict(self.effect)
        self.step = Mock(side_effect=step)
        adapters = module.OwnerAdapters(lambda *args:True,lambda b:adapter.read_record(harness.packet_path),
            lambda b:None,lambda *args:None,lambda b:dict(self.effect),self.step)
        self.factory = Mock(return_value=adapters)
        self.sealed = harness.sealed
        self.protected = c.root/'sealed-stage-owner'
        self.protected.mkdir()
        (self.protected/'catalog.json').write_bytes(c.catalog.read_bytes())
        c.write(self.protected/'binding.json',{'runtime':str(c.runtime)})
        c.stack.enter_context(patch.object(adapter,'PROTECTED_OWNER',self.protected))
        self.repin()  # Capture the final original catalog after the harness fixture.
        self.seal()
        self.prior = self.prior_publication()
        c.current.state['successor_request'] = copy.deepcopy(self.prior)
        c.current.save()

    def repin(self):
        c, f = self.c, self.f
        f.repin()
        binding = f.manifest['tasks'][f.issue['identifier']].get('stage_binding')
        if binding is not None:
            f.packet['inputs'].update(binding['inputs'])
        f.write(f.qualified/'packet.json',f.packet)
        f.handoff['task_packet'] = f.ref(f.qualified/'packet.json')
        f.write(f.handoff_path,f.handoff)
        f.handoff_sha = f.sha(f.handoff_path)
        c.current.config['qualified_successor'] = f.ref(f.handoff_path)

    def seal(self):
        c, f = self.c, self.f
        after = adapter.read_record(c.catalog)
        after['entries'].append(c.current._successor_entry(f.packet))
        c.current.config['catalog_versions'] = [dict(catalog=after,
            sha256=hashlib.sha256(__import__('stokowski_prepare')._publication_bytes(after)).hexdigest())]
        c.write(self.sealed,c.current.config)
        c.current.config_sha = adapter.file_sha(self.sealed)
        c.current.state['config_sha256'] = c.current.config_sha
        c.current.save()

    def prior_publication(self):
        c, f, n = self.c, self.f, self.native.native
        packet = dict(execution_outcome=dict(identifier=self.original_issue.identifier,
            uuid=self.original_issue.id,project_id=adapter.PROJECT))
        c.write(c.root/'prior-task-packet.json',packet)
        c.write(c.root/'prior-handoff.json',{'task_packet':f.ref(c.root/'prior-task-packet.json')})
        handoff = f.ref(c.root/'prior-handoff.json')
        request = dict(version=1,nonce='a'*64,operation=handoff['sha256'],context={'synthetic':'retained old owner context'})
        native_binding = n.sha(n.encode(request))
        custody = c.root.parent/'native-ssh-publication'/(handoff['sha256']+'.json')
        c.write(custody,dict(request=request,binding=native_binding,
            result=dict(status='published',runtime=str(self.original_runtime),dispatches=0)))
        c.write(c.root/'prior-publication.json',{'synthetic':'original publication metadata retained'})
        return dict(identity='b'*64,handoff=handoff,owner_config={'synthetic':'unchanged prior owner'},
            status='published',native_request=request,native_binding=native_binding,
            publication_result=f.ref(custody),publication_journal=f.ref(c.root/'prior-publication.json'))

    def consume(self):
        asyncio.run(self.c.current.continue_native_harness(self.factory))

    def test_prepermit_tick_preserves_terminal_publication_then_actual_permit_archives_once(self):
        c, f = self.c, self.f
        c.current.refresh()
        self.assertEqual(c.current.state['successor_request'],self.prior)
        self.assertNotIn('successor_history',c.current.state)
        self.native.launch.assert_not_called()
        self.assertIn('native_harness_refill_readback_required',c.current.state['successor_hold'])
        with patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=AssertionError('No coding child')):
            self.consume()
        self.assertEqual(c.current.state['successor_request']['status'],'published',c.current.state.get('successor_hold'))
        self.assertEqual(len(c.current.state['successor_history']),1)
        history = c.current.state['successor_history'][0]
        self.assertEqual(history['native_request'],self.prior['native_request'])
        self.assertEqual(history['terminal_unit'],c.current.state['tasks'][self.original_issue.identifier]['unit_gate']['binding'])
        self.assertEqual(self.step.call_count,1)
        self.native.api.assert_called_once()
        f.provider.assert_called_once()
        published = copy.deepcopy(c.current.state['successor_request'])
        c.current.refresh()
        self.assertEqual(c.current.state['successor_request'],published)
        self.consume()
        self.assertEqual(len(c.current.state['successor_history']),1)
        self.assertEqual(c.current.state['successor_request']['identity'],published['identity'])
        self.assertEqual(c.current.state['successor_request']['native_request'],published['native_request'])
        self.native.api.assert_called_once()
        self.assertEqual(f.snapshot(self.original_runtime),self.original_bytes)
        self.assertFalse((f.runtime/'attempts'/f.issue['identifier']/'intent.json').exists())
        self.assertEqual(adapter.read_record(self.validation/'validation-bindings.json')['issues'][f.issue['identifier']]['operation_key'],self.key)
        from stokowski.models import Issue
        candidate = Issue(id=f.issue['uuid'],identifier=f.issue['identifier'],title='Validation only',state='Todo')
        self.assertEqual(c.select(candidate),[])
        with self.assertRaisesRegex(AdmissionError,'nonimplementation_worker_refused'):
            worker.execute(f.runtime,candidate.identifier,{'prompt':'forged coding attempt','timeout_seconds':1})

    def test_actual_native_consumer_can_publish_genuine_stage_without_coding(self):
        # Isolate stage publication from the separately tested old-cache rearm.
        self.c.current.state.pop('successor_request')
        self.c.current.save()
        self.consume()
        self.assertEqual(self.c.current.state.get('successor_request',{}).get('status'),'published',
                         self.c.current.state.get('successor_hold'))
        self.native.api.assert_called_once()
        self.assertFalse((self.f.runtime/'attempts'/self.f.issue['identifier']/'intent.json').exists())

    def test_normal_intake_wait_remains_authoritative_until_real_native_permit(self):
        import time
        from stokowski.models import Issue
        c, f = self.c, self.f
        authority = dict(schema='offmenu-intake-authority/1',owner=c.current.config['owner'],
            source_head=c.current.config['source_head'],issue=f.issue['identifier'],issue_id=f.issue['uuid'],
            project_id=f.issue['project_id'],accepted_scope=f.packet['scope'],acceptance=f.packet['acceptance'],
            dependencies=[],decision='owner-qualified',handoff=f.ref(f.handoff_path),qualification=None)
        c.write(c.root/'stage-intake-authority.json',authority)
        policy=dict(schema='offmenu-normal-intake/1',enabled=True,owner=authority['owner'],
            source_head=authority['source_head'],project_route=c.current.route,expires_at=time.time()+300,
            references={'owner/stage':f.ref(c.root/'stage-intake-authority.json')},
            resources=f.packet['resources'],timeout_seconds=5)
        c.write(c.root/'stage-intake-policy.json',policy)
        c.current.config.pop('qualified_successor')
        c.current.config['normal_intake']=f.ref(c.root/'stage-intake-policy.json')
        c.current.state['intake_handoff']=self.prior['handoff']
        self.seal()
        issue=Issue(id=f.issue['uuid'],identifier=f.issue['identifier'],title='Stage only',state='Todo')
        client=c.client(issue)
        client._graphql.return_value['issue'].update(description='```offmenu-intake\n'+json.dumps(
            dict(schema='offmenu-intake-reference/1',reference='owner/stage'))+'\n```',
            inverseRelations={'nodes':[]})
        asyncio.run(c.current._intake(client,issue))
        self.assertEqual(c.current.state['intake_handoff'],f.ref(f.handoff_path))
        self.assertEqual(c.current.state['successor_request'],self.prior)
        self.native.launch.assert_not_called()
        self.consume()
        self.assertEqual(len(c.current.state.get('successor_history',[])),1,c.current.state.get('successor_hold'))
        self.assertEqual(c.current.state['successor_request']['status'],'published')
        self.assertEqual(c.current.state['intake'][issue.identifier]['authority'],authority)
        self.native.api.assert_called_once()

    def test_forged_stage_or_input_does_not_archive_terminal_request(self):
        c, f = self.c, self.f
        task = f.manifest['tasks'][f.issue['identifier']]
        good_task,good_config,good_packet = copy.deepcopy(task),copy.deepcopy(f.config),copy.deepcopy(f.packet)
        for mutation in ('owner','packet-stage','config-binding','missing-input','forged-origin','coding-path','coding-conversion'):
            with self.subTest(mutation=mutation):
                task.clear();task.update(copy.deepcopy(good_task))
                f.config=copy.deepcopy(good_config);f.packet=copy.deepcopy(good_packet)
                if mutation=='owner':task['owner']='foreign-owner'
                elif mutation=='packet-stage':f.packet['stage']='review'
                elif mutation=='config-binding':f.config['stage_binding']=dict(task['stage_binding'],identity='0'*64)
                elif mutation=='forged-origin':task['stage_binding']['identity']='0'*64;f.config['stage_binding']=task['stage_binding']
                elif mutation=='coding-path':task['allowed_paths']=['tools/forged.py']
                elif mutation=='coding-conversion':
                    for name in ('stage','input_paths','stage_binding'):task.pop(name)
                    task['allowed_paths']=list(f.packet['scope'])
                f.write(f.qualified/'manifest.json',f.manifest)
                self.repin()
                if mutation=='missing-input':
                    f.packet['inputs'].pop(next(iter(task['stage_binding']['inputs'])))
                    f.write(f.qualified/'packet.json',f.packet)
                    f.handoff['task_packet']=f.ref(f.qualified/'packet.json');f.write(f.handoff_path,f.handoff)
                    f.handoff_sha=f.sha(f.handoff_path);c.current.config['qualified_successor']=f.ref(f.handoff_path)
                self.seal()
                self.consume()
                self.assertEqual(c.current.state['successor_request'],self.prior,c.current.state.get('successor_hold'))
                self.assertNotIn('successor_history',c.current.state)
                self.native.launch.assert_not_called()
                self.assertFalse(f.runtime.exists())

    def test_published_and_duplicate_configuration_refusal_never_downgrade_or_rearm(self):
        c, f = self.c, self.f
        f.config['native_publication']['source_head']='0'*40
        self.repin();self.seal()
        for status in ('published','duplicate'):
            with self.subTest(status=status):
                prior=dict(self.prior,status=status)
                c.current.state['successor_request']=copy.deepcopy(prior)
                c.current.save()
                self.consume()
                self.assertEqual(c.current.state['successor_request'],prior)
                self.assertNotIn('successor_history',c.current.state)
                self.assertIn('successor_native_configuration',c.current.state['successor_hold'])
                self.native.launch.assert_not_called()

    def test_pinned_stage_input_drift_refuses_before_archiving(self):
        task=self.f.manifest['tasks'][self.f.issue['identifier']]
        path=Path(next(iter(task['stage_binding']['inputs'])))
        before=path.read_bytes()
        try:
            path.write_bytes(before+b'\n')
            self.consume()
            self.assertEqual(self.c.current.state['successor_request'],self.prior)
            self.assertNotIn('successor_history',self.c.current.state)
            self.native.launch.assert_not_called()
        finally:
            path.write_bytes(before)

    def test_unpublished_refusal_still_holds_without_terminal_status_upgrade(self):
        c, f = self.c, self.f
        for status in ('pending','uncertain','refused'):
            with self.subTest(status=status):
                c.current.state['successor_request']=dict(self.prior,status=status)
                c.current.save()
                c.current.refresh()
                self.assertEqual(c.current.state['successor_request']['status'],'held')
                self.assertNotIn('successor_history',c.current.state)
                self.native.launch.assert_not_called()


if __name__=='__main__':unittest.main()
