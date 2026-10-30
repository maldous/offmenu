"""Typed stages consume original native operations, with no coding authority."""
import asyncio
import copy
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_stokowski_current_dispatch as fixtures
import stokowski_adapter as adapter
import stokowski_prepare as prepare
import stokowski_worker as worker
from symphony_capacity import AdmissionError, digest
from symphony_tasks import load_manifest, manifest_digest


@unittest.skipUnless(importlib.util.find_spec('stokowski'), 'Use pinned Stokowski environment')
class TypedStageTests(unittest.TestCase):
    # Reuse deterministic native evidence builders, not mocked admission/routes.
    for _name in ('setUp','write','git_read','prepare_current','qualify','publish','adapted',
                  'client','select','bound_gate','review_fixture','continuation_fixture','turn'):
        locals()[_name] = getattr(fixtures.CurrentDispatchTests, _name)

    def stage_fixture(self, stage='validation'):
        issue, original, owner, journal, key, spec, remote, factory, upstream = self.continuation_fixture(106)
        entry = copy.deepcopy(self.entries[0])
        _, identity = self.current.validation_binding(issue.identifier, entry)
        names = ['current-admission.json','manifest.json','requests/UIF-106.json',
                 'capacity-policy.json','installation.json','provider-proof.json',
                 'validation-bindings.json','attempts/UIF-106/dispatch-intent.json',
                 'attempts/UIF-106/intent.json','attempts/UIF-106/receipt.json']
        binding = dict(entry=entry, identity=identity,
                       inputs={str(original/n):adapter.file_sha(original/n) for n in names})
        self.stage_task = dict(issue_id=issue.id,owner='existing-owner',purpose='Only continue original evidence',
            allowed_paths=[],input_paths=list(spec['outputs']),stage=stage,stage_binding=binding,
            resources=self.policy['symphony']['default_resources'],attempt_limit=1,
            acceptance=['Independent evidence, no parent closure'])
        self.stage_manifest = dict(version=1,project_id=adapter.PROJECT,label='synthetic-stage',
            branch='feature/test-current',base_revision='a'*40,tasks={issue.identifier:self.stage_task})
        # A fresh coordinator selection: no in-flight catalog identity is upgraded.
        self.entries=[]
        self.write(self.catalog,dict(version=1,entries=[]))
        self.current.state['bindings']={}
        self.current.state['references']={}
        self.current.state['tasks']={}
        self.current.save()
        self.current.refresh()
        return issue,original,owner,journal,key,spec,remote,factory

    def publish_stage(self):
        root=self.root
        qualified=root/'qualified'; qualified.mkdir()
        runtime=root/'stage'
        def write(name,value):
            path=qualified/name; self.write(path,value); return self.ref(path)
        selected=dict(runtime_root=str(root),task_runtime=str(runtime),
                      coordinator_runtime=str(self.runtime),catalog_path=str(self.catalog))
        observation=write('observation.json',dict(service='github',principal_id='123',login='synthetic'))
        claim_binding=write('claim-binding.json',dict(owner='existing-owner',repository='synthetic/offmenu',
            issue_id=self.stage_task['issue_id']))
        binding=json.loads(Path(claim_binding['path']).read_text())
        claim=write('claim.json',dict(owner='existing-owner',directory=str(qualified),binding_sha256=digest(binding)))
        config=dict(schema='offmenu-source-owner-publication-config/1',owner='existing-owner',
            repository='synthetic/offmenu',selected_current=selected,stage_binding=self.stage_task['stage_binding'],
            caller_association=dict(service='github',principal_id='123',login='synthetic',authenticated_observation=observation),
            publication_authority=dict(automatic_start=False,historical_workers_resume=False,require_normal_execution_admission=True),
            repository_claim=dict(claim,binding_path=claim_binding['path'],binding_sha256=claim_binding['sha256'],
                                  binding_identity_sha256=digest(binding)))
        config_ref=write('config.json',config)
        manifest=write('manifest.json',self.stage_manifest)
        request=write('request.json',dict(prompt='No coding',timeout_seconds=5))
        provider=write('provider.json',dict(requested_model='gpt-6.1-sol',requested_effort='medium',
            route='codex-chatgpt',session_ceiling=8,max_age_seconds=300,checked_at_max_future_skew_seconds=5))
        outcome=dict(identifier='UIF-106',uuid=self.stage_task['issue_id'],project_id=adapter.PROJECT)
        source_issue=dict(identifier='UIF-119',uuid='source-only',project_id='other-project')
        installation=dict(manifest_path=str(root/'installation.json'),manifest_sha256=adapter.file_sha(root/'installation.json'),
                          source_revision=self.installation['source_revision'],installed_files_verified_statically=2)
        packet=dict(schema='offmenu-owner-bound-preexecution-task/1',owner='existing-owner',
            stage=self.stage_task['stage'],unit_id='synthetic-stage',scope=self.stage_task['input_paths'],
            acceptance=self.stage_task['acceptance'],resources=self.stage_task['resources'],
            source_issue=source_issue,execution_outcome=outcome,selected_current=selected,
            source=dict(repository='synthetic/offmenu',source_checkout=str(self.source),base='a'*40,branch='feature/test-current'),
            manifest=manifest,request=request,owner_config=config_ref,provider_requirements=provider,installation=installation)
        paths=[Path(r['path']) for r in (observation,claim_binding,claim,config_ref,manifest,request,provider)]
        paths += [self.catalog,root/'installation.json',self.source/'tools/delivery/capacity-policy.json']
        packet['inputs']={str(p):adapter.file_sha(p) for p in paths}
        packet['inputs'].update(self.stage_task['stage_binding']['inputs'])
        packet_ref=write('packet.json',packet)
        handoff=write('handoff.json',dict(directory=str(qualified),authenticated_principal=dict(id='123',login='synthetic'),
            task_packet=packet_ref,owner_config=config_ref,manifest=manifest,request=request,
            source_issue=source_issue,execution_outcome=outcome,source_base='a'*40))
        import time
        def publish():
            return prepare.prepare_publication(handoff['path'],handoff_sha256=handoff['sha256'],
                authenticated_caller=lambda:dict(service='github',principal_id='123',login='synthetic'),
                provider_proof=lambda model,ceiling:dict(route='codex-chatgpt',available=True,
                    requested_model=model,session_ceiling=ceiling,checked_at=time.time()))
        self.assertEqual(publish()['status'],'published')
        self.assertEqual(publish()['status'],'duplicate')
        self.current.refresh()
        return runtime

    @staticmethod
    def ref(path):
        return dict(path=str(path),sha256=adapter.file_sha(path))

    def test_publication_route_tick_restart_and_worker_refusal(self):
        issue,original,owner,journal,key,spec,remote,factory=self.stage_fixture()
        native_bytes=(original/'attempts/UIF-106/receipt.json').read_bytes()
        runtime=self.publish_stage()
        self.assertEqual(asyncio.run(owner._resolve_current_state(issue)),('evidence-pending',1))
        native=__import__('stokowski.orchestrator',fromlist=['x'])
        with patch.object(adapter.asyncio,'create_subprocess_exec',side_effect=AssertionError('coding spawn')):
            with self.assertRaisesRegex(AdmissionError,'nonimplementation_worker_refused'):
                asyncio.run(self.turn(native,issue,runtime))
            with patch.object(worker,'Pool',side_effect=AssertionError('lease')):
                with self.assertRaisesRegex(AdmissionError,'nonimplementation_worker_refused'):
                    worker.execute(runtime,issue.identifier,{})
            asyncio.run(owner._tick())
        remote.inspect.assert_awaited_once()
        remote.submit.assert_not_awaited()
        self.current=adapter.CurrentWork(self.runtime)
        asyncio.run(self.current.continue_validation())
        remote.submit.assert_not_awaited()
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        self.assertEqual((original/'attempts/UIF-106/receipt.json').read_bytes(),native_bytes)
        self.assertFalse((runtime/'attempts/UIF-106').exists())
        self.assertFalse((runtime/'operations').exists())
        task=self.current.state['tasks']['UIF-106']
        self.assertEqual(task['unit_gate']['disposition'],'waiting')
        self.assertIsNone(task['validation']['provider'])
        self.assertFalse(self.current.state['accepted_delivery'])

    def test_review_waits_and_foreign_missing_drifted_inputs_hold(self):
        issue,original,owner,journal,key,spec,remote,factory=self.stage_fixture('review')
        runtime=self.publish_stage()
        asyncio.run(owner._tick())
        factory.assert_not_called()
        self.assertEqual(self.current.state['tasks']['UIF-106']['validation']['status'],'awaiting-independent-review')
        self.assertEqual(journal.read(key)[1]['status'],'submit-intent')
        task=self.stage_task
        for mutation in ('missing','foreign','identity','scope','origin'):
            candidate=copy.deepcopy(task)
            if mutation=='missing': candidate['stage_binding']['inputs'].pop(str(original/'manifest.json'))
            elif mutation=='foreign': candidate['stage_binding']['entry']['issue_id']='foreign'
            elif mutation=='identity': candidate['stage_binding']['identity']='0'*64
            elif mutation=='scope': candidate['input_paths']=['tests/foreign.py']
            else: candidate['stage_binding']['inputs'][str(original/'manifest.json')]='0'*64
            with self.subTest(mutation=mutation),self.assertRaises(AdmissionError):
                self.current.stage_origin('UIF-106',candidate)
        (runtime/'cancel.json').write_text('{}')
        asyncio.run(owner._tick())
        factory.assert_not_called()
        self.assertEqual(journal.read(key)[1]['status'],'submit-intent')

    def independent_packet(self, issue, journal, key, spec):
        from stokowski_operations import bridge_arguments
        unit=self.current.gate_binding(issue)
        _,state=journal.read(key)
        receipt=dict(status='succeeded',exit_code=0,child_tree_gone=True,reconcile_required=False,
            job_id=state['logical_job_id'],runner_sha256=spec['runner_sha256'],
            capacity_policy_sha256=spec['policy_sha256'],
            command_sha256=__import__('hashlib').sha256(bridge_arguments(spec)['command'].encode()).hexdigest())
        state.update(status='succeeded',receipt_sha256=digest(receipt),accepted_output_sha256=spec['outputs'],
                     acceptance_sha256=spec['acceptance_sha256'])
        journal.save(key,state,'synthetic-independent-result')
        b=dict(version=1,repository='synthetic/offmenu',pr_number=145,issue_id=issue.id,
            owner='existing-owner',head=spec['head'],base=spec['base'],tree='f'*40,
            policy_sha256='1'*64,capacity_policy_sha256=spec['policy_sha256'],
            validation_operation_key=key,outputs=spec['outputs'],head_branch=spec['branch'])
        review=dict(head=spec['head'],base=spec['base'],outputs=spec['outputs'],independent=True,
            evidence_id='synthetic-independent',reviewer='other-owner',author='existing-owner',
            model='synthetic-review-observation',provider='synthetic',findings=[],verdict='accept')
        review['evidence_sha256']=digest(review)
        validation=dict(operation_key=key,status='succeeded',head=spec['head'],base=spec['base'],
            capacity_policy_sha256=spec['policy_sha256'],outputs=spec['outputs'],child_tree_gone=True,reconcile_required=False)
        snapshot=dict(review=review,validation=validation,publisher_owner='existing-owner',source_tree='f'*40,
            source_clean=True,publication_triggers_actions=False,policy_sha256='1'*64,
            capacity_policy_sha256=spec['policy_sha256'])
        decision=dict(status='merge-intent',merge_effect='pending',binding_sha256=digest(b),
            qualification_sha256=digest(dict(validation=validation,review=review,tree='f'*40,policy='1'*64)),
            action=dict(kind='merge-pr',expected_head_sha=spec['head'],expected_base_sha=spec['base']))
        return dict(issue=issue.identifier,unit_binding=unit,integration_binding=b,
                    snapshot=snapshot,decision=decision,validation_receipt=receipt)

    def test_independent_review_consumed_without_parent_close_or_coding(self):
        issue,original,owner,journal,key,spec,remote,factory=self.stage_fixture('review')
        self.publish_stage()
        asyncio.run(owner._tick())
        packet=self.independent_packet(issue,journal,key,spec)
        for field,value in [('head','d'*40),('reviewer','existing-owner'),('outputs',{})]:
            bad=copy.deepcopy(packet)
            bad['snapshot']['review'][field]=value
            with self.subTest(field=field),self.assertRaises(AdmissionError):
                self.current.unit_review_writer(lambda envelope:bad)(bad)
        writer=self.current.unit_review_writer(lambda envelope:packet)
        self.assertEqual(writer(packet)['status'],'retained')
        self.assertEqual(writer(packet)['status'],'retained')
        self.current.refresh()
        gate=self.current.state['tasks']['UIF-106']['unit_gate']
        self.assertEqual(gate['disposition'],'approved')
        asyncio.run(owner._handle_gate_responses())
        self.assertTrue(gate['handled'])
        self.assertFalse(gate['accepted_delivery'])
        owner._linear.update_issue_state.assert_not_awaited()
        owner._linear.post_comment.assert_not_awaited()
        factory.assert_not_called()

    def test_completed_validation_uses_original_journal_without_resubmit(self):
        issue,original,owner,journal,key,spec,remote,factory=self.stage_fixture()
        self.publish_stage()
        self.independent_packet(issue,journal,key,spec)
        asyncio.run(owner._tick())
        asyncio.run(owner._tick())
        remote.submit.assert_not_awaited()
        remote.inspect.assert_not_awaited()
        self.assertEqual(self.current.state['tasks']['UIF-106']['validation']['status'],'succeeded')
        self.assertEqual(self.current.state['tasks']['UIF-106']['unit_gate']['disposition'],'waiting')

    def test_original_cancel_and_evidence_drift_do_not_replace_operation(self):
        issue,original,owner,journal,key,spec,remote,factory=self.stage_fixture()
        self.publish_stage()
        journal.cancel(key)
        _,before=journal.read(key)
        path=original/'attempts/UIF-106/receipt.json'
        path.write_bytes(path.read_bytes()+b' ')
        asyncio.run(owner._tick())
        factory.assert_not_called()
        self.assertEqual(journal.read(key)[1],before)
        self.assertTrue(before['cancel_requested'])
        self.assertEqual(self.current.state['tasks']['UIF-106']['validation']['status'],'held')

    def test_legacy_manifest_bytes_and_digest_are_unchanged(self):
        issue,runtime=self.qualify(120)
        raw=(runtime/'manifest.json').read_bytes()
        original=json.loads(raw)
        self.assertEqual(load_manifest(runtime/'manifest.json',expected_branch=None),original)
        self.assertEqual(manifest_digest(original),manifest_digest(load_manifest(runtime/'manifest.json',expected_branch=None)))
        self.assertEqual((runtime/'manifest.json').read_bytes(),raw)
