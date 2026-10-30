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


def reviewed_records(case, candidate, base, head, outputs, issue_name="UIF-106", issue_id="00000000-0000-4000-8000-000000000106", prior_reviewer="independent-prior-reviewer"):
    """SYNTHETIC owner inputs and manual provenance; no real acceptance claim."""
    import hashlib
    import subprocess
    import stokowski_operations as operations
    import stokowski_stage as stage
    runtime = case.root/'fresh-reviewed-validation'
    evidence = case.root/'synthetic-manual-history'
    def git(*args):
        return subprocess.run(['git','-C',str(candidate),*args],check=True,capture_output=True).stdout
    refs = []
    # Explicit SYNTHETIC receipts describe actual fixture commits, never inferred
    # real admission. Use each committed delta, including intermediate bytes.
    commits=git('rev-list','--reverse',base+'..'+head).decode().splitlines()
    for index, contribution in enumerate(commits):
        source=git('rev-parse',contribution+'^').decode().strip()
        names=git('diff','--no-renames','--name-only',source,contribution).decode().splitlines()
        contributed={name:hashlib.sha256(git('show',contribution+':'+name)).hexdigest() for name in names}
        author=('manual-author-one','manual-author-two')[min(index,1)]
        parent = dict(owner=author,branch='feature/test-current',head=source)
        receipt = dict(issue=issue_name,status='succeeded',child_tree_gone=True,accepted_delivery=False,
            scope_violations=[],session_id='synthetic-session-'+str(index),source_head=source,
            parent_binding=parent,binding_sha256=digest(parent),lease='synthetic-old-lease-'+str(index),
            output_sha256=contributed)
        path=evidence/(str(index)+'.json'); case.write(path,receipt)
        refs.append(dict(path=str(path),sha256=adapter.file_sha(path),author=author,owner=parent['owner'],
            session=receipt['session_id'],source_head=source,outputs=contributed,
            contribution_head=contribution,path_mapping={name:name for name in names},derivation=None))
    # Build the acyclic payload before the independent review exists. The prior
    # reviewer attests exact source and all transformations, without future hashes.
    for ref in refs:
        if ref['outputs'] != {name:outputs[name] for name in ref['path_mapping']}:
            ref['derivation']=dict(owner=ref['owner'],contribution_head=ref['contribution_head'],
                path_mapping=ref['path_mapping'],head=head,outputs={name:outputs[name] for name in ref['path_mapping']},
                reason='SYNTHETIC reviewed second contribution transforms the first committed output.')
    review=dict(reviewer=prior_reviewer,decision='accepted',head=head,base=base,outputs=outputs,
        derivations=operations.canonical_derivations(refs))
    path=evidence/'accepted-review.json'; case.write(path,review)
    review.update(path=str(path),sha256=adapter.file_sha(path))
    for ref in refs:
        if ref['derivation'] is not None:
            ref['derivation']['review_sha256']=digest(review)
    files=['tests/delivery/'+n+'.py' for n in operations.REVIEWED_TESTS]
    archive=subprocess.run(['git','-C',str(candidate),'archive',base,*files],check=True,capture_output=True).stdout
    admission=dict(version=1,issue=issue_name,issue_id=issue_id,
        owner='existing-owner',head=head,base=base,branch='feature/test-current',
        workspace='/offmenu/data/.offmenu-platform/workspaces/synthetic-reviewed-source',local_source_root=str(candidate),
        outputs=outputs,author=refs[0]['author'],authors=[r['author'] for r in refs],provenance=refs,review=review,
        control_sha256=hashlib.sha256(archive).hexdigest(),policy_sha256=case.current.config['policy_sha256'],
        runner_sha256=adapter.file_sha(case.source/'tools/delivery/windmill_runner.py'),
        executor_sha256=adapter.file_sha(operations.__file__),execution=dict(task_fit='deterministic reviewed source validation',
            requested_model=None,requested_effort=None,provider_route='none',resolved_model=None,resolution_status='not-applicable'))
    path=evidence/'new-admission.json';case.write(path,admission)
    spec={k:v for k,v in admission.items() if k not in ('author','authors','provenance','review')}
    spec.update(version=3,stage='validate',profile=operations.REVIEWED_PROFILE,acceptance_sha256=adapter.file_sha(path),
        origin=dict(kind='reviewed-source-v1',admission_sha256=adapter.file_sha(path),review_sha256=digest(review),
            author=admission['author'],authors=admission['authors'],provenance=refs))
    key=stage.bind_reviewed_source(runtime,spec,path)
    case.assertEqual(stage.bind_reviewed_source(runtime,spec,path),key)
    selected=json.loads((runtime/'validation-bindings.json').read_text())['issues'][issue_name]
    entry=dict(issue=issue_name,issue_id=spec['issue_id'],runtime=str(runtime),origin='reviewed-source-v1',admission_sha256=adapter.file_sha(path))
    pins={str(p):adapter.file_sha(p) for p in [path,Path(review['path']),runtime/'validation-bindings.json',*[Path(r['path']) for r in refs]]}
    binding=dict(entry=entry,inputs=pins,identity=digest(dict(entry=entry,selected=selected,spec=spec,inputs=pins)))
    return runtime,spec,key,binding


class ReviewedSourceTests(TypedStageTests):
    # Inherit the native regression checks, plus exercise the new actual callers.
    def new_fixture(self, stage_name='validation', **record_options):
        import subprocess
        import hashlib
        import stokowski_operations as operations
        from stokowski_operations import Journal
        issue,_,owner,_,_,_,remote,factory=self.stage_fixture(stage_name)
        import shutil
        for module in (operations,__import__('stokowski_stage')):
            shutil.copyfile(module.__file__,self.source/'tools/delivery'/Path(module.__file__).name)
        candidate=self.temp/'immutable-manual-candidate';candidate.mkdir()
        def git(*args):
            return subprocess.run(['git','-C',str(candidate),*args],check=True,capture_output=True,text=True).stdout.strip()
        git('init','-b','feature/test-current')
        for name in operations.REVIEWED_TESTS:
            path=candidate/'tests/delivery'/(name+'.py');path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text('"""SYNTHETIC fixed consumer oracle."""\nimport unittest\nclass CurrentDispatchTests(unittest.TestCase):\n'+''.join(' def '+n+'(self): self.assertTrue(True)\n' for n in ('test_normal_tick_rejects_invalid_validation_before_transport','test_normal_tick_continues_original_intent_and_reopen','test_qualified_prepared_submits_once_and_refusal_retains_identity','test_validation_state_identity_drift_and_cancel_flag_preserved'))+'\nclass OperationRecoveryTests(unittest.TestCase):\n'+''.join(' def '+n+'(self): self.assertTrue(True)\n' for n in ('test_unknown_missing_remote_job_is_not_blindly_resubmitted','test_second_owner_cannot_create_duplicate_operation','test_cancel_before_submission_does_not_start_a_job')))
        git('add','.')
        def commit(message):
            git('-c','user.name=Synthetic','-c','user.email=synthetic@example.invalid','-c','commit.gpgsign=false','commit','-m',message)
            return git('rev-parse','HEAD')
        base=commit('synthetic accepted base')
        target=candidate/'tools/delivery/manual.py';target.parent.mkdir(parents=True);target.write_text('synthetic = False\n')
        second=candidate/'tools/delivery/second_manual.py';second.write_text('synthetic_second = False\n')
        git('add','.');commit('synthetic first manual contribution')
        target.write_text('synthetic = True\n');second.write_text('synthetic_second = True\n')
        git('add','.');head=commit('synthetic second manual contribution')
        outputs={str(path.relative_to(candidate)):hashlib.sha256(path.read_bytes()).hexdigest() for path in (target,second)}
        self.stack.enter_context(patch.object(operations,'POLICY',self.source/'tools/delivery/capacity-policy.json'))
        runtime,spec,key,binding=reviewed_records(self,candidate,base,head,outputs,**record_options)
        self.stage_task.update(stage_binding=binding,input_paths=list(outputs))
        return issue,runtime,owner,Journal(runtime/'operations'),key,spec,remote,factory

    def test_new_origin_publication_current_journal_restart_review(self):
        import stokowski_operations as operations
        issue,runtime,owner,journal,key,spec,remote,factory=self.new_fixture()
        selected=self.publish_stage()
        self.assertFalse((selected/'operations').exists())
        self.assertFalse((runtime/'current-admission.json').exists())
        self.assertFalse((runtime/'attempts').exists())
        self.assertNotIn('native_receipt_sha256',self.current.gate_binding(issue))
        # Genuine fixed local subprocess, with only the canonical service root
        # substituted by this labelled synthetic mirror. External jobs are fake.
        args=operations.bridge_arguments(spec)
        command=args['command'].replace(spec['workspace'],spec['local_source_root']).replace('/offmenu/.venv-delivery/bin/python',sys.executable).replace('/offmenu/.delivery/stokowski/venv/lib/python3.12/site-packages','/home/user/src/offmenu/.delivery/stokowski/venv/lib/python3.12/site-packages')
        import subprocess,os
        env=dict(os.environ,PYTHONPATH='/home/user/src/offmenu/.delivery/stokowski/venv/lib/python3.12/site-packages')
        result=subprocess.run(['/bin/sh','-c',command],capture_output=True,text=True,env=env,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        # Current tick prepares no replacement and submits this new operation once.
        remote.inspect.return_value=None
        asyncio.run(owner._tick())
        remote.submit.assert_awaited_once()
        self.current=adapter.CurrentWork(self.runtime)
        asyncio.run(self.current.continue_validation())
        remote.submit.assert_awaited_once()
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        packet=self.independent_packet(issue,journal,key,spec)
        packet['snapshot']['review']['author']=spec['origin']['author']
        packet['snapshot']['review']['evidence_sha256']=digest({k:v for k,v in packet['snapshot']['review'].items() if k!='evidence_sha256'})
        b=packet['integration_binding'];packet['decision']['qualification_sha256']=digest(dict(validation=packet['snapshot']['validation'],review=packet['snapshot']['review'],tree=b['tree'],policy=b['policy_sha256']))
        self.current.unit_review_writer(lambda value:packet)(packet)
        self.current.refresh()
        self.assertEqual(self.current.state['tasks']['UIF-106']['unit_gate']['disposition'],'approved')
        self.assertFalse(self.current.state['accepted_delivery'])
        self.assertFalse((selected/'attempts/UIF-106').exists())

    def test_new_origin_contribution_proof_rejects_before_prepare(self):
        import subprocess
        import stokowski_operations as operations
        import stokowski_stage as stage
        _,runtime,_,_,_,original,_,_=self.new_fixture()
        candidate=Path(original['local_source_root'])
        admission_path=runtime.parent/'synthetic-manual-history/new-admission.json'
        original_admission=json.loads(admission_path.read_text())
        # A genuine successful unrelated same-issue/claimed-native-owner receipt
        # must fail even after all self-declared reference hashes are repinned.
        tree=subprocess.run(['git','-C',str(candidate),'rev-parse',original['head']+'^{tree}'],check=True,capture_output=True,text=True).stdout.strip()
        foreign=subprocess.run(['git','-C',str(candidate),'-c','user.name=Synthetic',
            '-c','user.email=synthetic@example.invalid','commit-tree',tree],input='SYNTHETIC unrelated root\n',check=True,capture_output=True,text=True).stdout.strip()
        receipt_path=Path(original['origin']['provenance'][0]['path'])
        raw=receipt_path.read_bytes()
        for label in ('unrelated-source','unrelated-contribution','wrong-blob','wrong-output-path',
                      'wrong-contribution','fake-review','fake-derivation','missing-derivation',
                      'no-relevant-output','unrelated-receipt','aliased-path'):
            spec=copy.deepcopy(original)
            ref=spec['origin']['provenance'][0]
            if label=='unrelated-source':ref['source_head']=foreign
            elif label=='unrelated-contribution':ref['contribution_head']=foreign
            elif label=='wrong-blob':ref['outputs'][next(iter(ref['outputs']))]='0'*64
            elif label=='wrong-output-path':
                ref['outputs']={'tools/delivery/wrong.py':next(iter(ref['outputs'].values()))}
                ref['path_mapping']={'tools/delivery/wrong.py':next(iter(original['outputs']))}
            elif label=='wrong-contribution':ref['contribution_head']=spec['head']
            elif label=='fake-review':ref['derivation']['review_sha256']='0'*64
            elif label=='fake-derivation':ref['derivation']['owner']='foreign-owner'
            elif label=='missing-derivation':ref['derivation']=None
            elif label=='no-relevant-output':ref['path_mapping']={name:'tools/unrelated.py' for name in ref['outputs']}
            elif label=='aliased-path':ref['path_mapping']={'tools/../manual.py':next(iter(original['outputs']))}
            else:
                ref.update(source_head=foreign,contribution_head=foreign,
                    outputs={'tools/unrelated.py':'a'*64},path_mapping={'tools/unrelated.py':'tools/unrelated.py'},derivation=None)
            # Repin derivative metadata to isolate Git proof from schema proof.
            if ref['derivation'] and label not in ('fake-review','fake-derivation'):
                ref['derivation'].update(contribution_head=ref['contribution_head'],path_mapping=ref['path_mapping'])
            receipt=json.loads(raw)
            receipt.update(source_head=ref['source_head'],output_sha256=ref['outputs'])
            receipt['parent_binding']['head']=ref['source_head']
            receipt['binding_sha256']=digest(receipt['parent_binding'])
            self.write(receipt_path,receipt);ref['sha256']=adapter.file_sha(receipt_path)
            admission=copy.deepcopy(original_admission);admission['provenance']=spec['origin']['provenance']
            self.write(admission_path,admission)
            spec['acceptance_sha256']=spec['origin']['admission_sha256']=adapter.file_sha(admission_path)
            destination=self.root/('refused-'+label)
            with self.subTest(label=label),patch.object(operations.Journal,'prepare') as prepare_operation:
                with self.assertRaises(operations.OperationError):
                    stage.bind_reviewed_source(destination,spec,admission_path)
                prepare_operation.assert_not_called()
                self.assertFalse((destination/'operations').exists())
            receipt_path.write_bytes(raw)
        self.write(admission_path,original_admission)

    def test_new_origin_unattested_derivations_refuse_before_prepare(self):
        import stokowski_operations as operations
        import stokowski_stage as stage
        _,runtime,_,_,_,original,_,_=self.new_fixture()
        admission_path=runtime.parent/'synthetic-manual-history/new-admission.json'
        original_admission=json.loads(admission_path.read_text())
        review_path=Path(original_admission['review']['path'])
        review_bytes=review_path.read_bytes()
        for label in ('reason','mapping'):
            spec=copy.deepcopy(original)
            ref=spec['origin']['provenance'][0]
            if label=='reason':
                ref['derivation']['reason']+=' Unattested owner amendment.'
            else:
                # Both real committed outputs remain relevant; swap their targets.
                # Receipt, Git delta, blobs, ancestry and final outputs stay valid.
                names=sorted(ref['path_mapping'])
                ref['path_mapping']={names[0]:names[1],names[1]:names[0]}
                ref['derivation']['path_mapping']=ref['path_mapping']
                ref['derivation']['outputs']={v:spec['outputs'][v] for v in ref['path_mapping'].values()}
            admission=copy.deepcopy(original_admission)
            admission['provenance']=spec['origin']['provenance']
            self.write(admission_path,admission)
            spec['acceptance_sha256']=spec['origin']['admission_sha256']=adapter.file_sha(admission_path)
            # Exercise the real Git proof too: mapping mutation is independently
            # coherent, so refusal must come from the prior attestation check.
            import subprocess
            proof=subprocess.run([sys.executable,'-c',operations.reviewed_check_code(spec,Path(spec['local_source_root']))],capture_output=True)
            self.assertEqual(proof.returncode,0,proof.stderr)
            with self.subTest(label=label),patch.object(operations.Journal,'prepare') as prepared:
                with self.assertRaisesRegex(operations.OperationError,'Independent derivation attestation mismatch'):
                    stage.bind_reviewed_source(self.root/('unattested-'+label),spec,admission_path)
                prepared.assert_not_called()
            self.assertEqual(review_path.read_bytes(),review_bytes)
        self.write(admission_path,original_admission)

    def test_new_origin_canonical_derivation_order_and_duplicates(self):
        import stokowski_operations as operations
        import stokowski_stage as stage
        _,runtime,_,_,_,spec,_,_=self.new_fixture()
        refs=spec['origin']['provenance']
        # Canonical ordering depends on payload bytes, never receipt list order
        # or dictionary insertion order. Distinct contributions stay distinct.
        other=copy.deepcopy(refs[0])
        other['derivation']['reason']='Another exact independently reviewed reason.'
        left=operations.canonical_derivations([refs[0],other])
        right=operations.canonical_derivations([other,refs[0]])
        self.assertEqual(left,right)
        self.assertEqual(len(left),2)
        self.assertTrue(all('review_sha256' not in entry for entry in left))
        spec=copy.deepcopy(spec)
        spec['origin']['provenance'].append(copy.deepcopy(refs[0]))
        admission_path=runtime.parent/'synthetic-manual-history/new-admission.json'
        admission=json.loads(admission_path.read_text())
        admission['provenance']=spec['origin']['provenance']
        self.write(admission_path,admission)
        spec['acceptance_sha256']=spec['origin']['admission_sha256']=adapter.file_sha(admission_path)
        with patch.object(operations.Journal,'prepare') as prepared:
            with self.assertRaisesRegex(operations.OperationError,'Duplicate contribution derivation'):
                stage.bind_reviewed_source(self.root/'duplicate-derivation',spec,admission_path)
            prepared.assert_not_called()

    def test_new_origin_intermediate_proof_in_service_mirror(self):
        import shutil
        import subprocess
        import stokowski_operations as operations
        _,runtime,_,_,_,spec,_,_=self.new_fixture()
        refs=spec['origin']['provenance']
        self.assertEqual(len(refs),2)
        self.assertNotEqual(refs[0]['outputs'],spec['outputs'])
        self.assertEqual(refs[1]['outputs'],spec['outputs'])
        self.assertNotEqual(refs[0]['owner'],refs[1]['owner'])
        self.assertNotIn(spec['owner'],[r['owner'] for r in refs])
        self.assertEqual(refs[1]['source_head'],refs[0]['contribution_head'])
        mirror=self.temp/'jailed-synthetic-mirror'
        shutil.copytree(spec['local_source_root'],mirror)
        proof=operations.reviewed_check_code(spec,mirror)
        self.assertNotIn('read_record',proof)
        # Service proof requires no host receipt reads.
        for ref in refs:Path(ref['path']).unlink()
        result=subprocess.run([sys.executable,'-c',proof],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        wrong=copy.deepcopy(spec);wrong['origin']['provenance'][0]['contribution_head']=spec['head']
        result=subprocess.run([sys.executable,'-c',operations.reviewed_check_code(wrong,mirror)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        wrong=copy.deepcopy(spec)
        wrong['origin']['provenance'][0]['derivation']['review_sha256']='0'*64
        result=subprocess.run([sys.executable,'-c',operations.reviewed_check_code(wrong,mirror)],capture_output=True)
        self.assertNotEqual(result.returncode,0)
        changed=copy.deepcopy(spec)
        changed['origin']['provenance'][0]['derivation']['reason']+=' Additional synthetic review context.'
        self.assertNotEqual(operations.operation_key(changed),operations.operation_key(spec))

    def test_new_origin_prior_review_rejects_retained_owner_before_prepare(self):
        import stokowski_operations as operations
        with patch.object(operations.Journal, 'prepare', autospec=True,
                          side_effect=operations.Journal.prepare) as prepare_operation:
            with self.assertRaisesRegex(operations.OperationError, 'Independent accepted exact-head review required'):
                self.new_fixture(prior_reviewer='manual-author-one')
            self.assertFalse(any(call.args[1]['version']==3 for call in prepare_operation.call_args_list))

    def test_new_origin_later_review_rejects_all_retained_owners(self):
        issue,runtime,owner,journal,key,spec,remote,factory=self.new_fixture('review')
        self.publish_stage()
        packet=self.independent_packet(issue,journal,key,spec)
        for ref in spec['origin']['provenance']:
            receipt=json.loads(Path(ref['path']).read_text())
            reviewer=receipt['parent_binding']['owner']
            self.assertEqual(ref['owner'],reviewer)
            self.assertNotEqual(reviewer,'independent-prior-reviewer')
            changed=copy.deepcopy(packet)
            review=changed['snapshot']['review']
            review.update(author=spec['origin']['author'],reviewer=reviewer)
            review['evidence_sha256']=digest({k:v for k,v in review.items() if k!='evidence_sha256'})
            b=changed['integration_binding']
            changed['decision']['qualification_sha256']=digest(dict(validation=changed['snapshot']['validation'],review=review,tree=b['tree'],policy=b['policy_sha256']))
            with self.subTest(reviewer=reviewer),self.assertRaisesRegex(AdmissionError,'unit_review_qualification'):
                self.current.unit_review_writer(lambda value:changed)(changed)

    def test_new_origin_exact_negatives_and_cancellation(self):
        import stokowski_stage as stage
        import stokowski_operations as operations
        issue,runtime,owner,journal,key,spec,remote,factory=self.new_fixture()
        self.publish_stage()
        for label in ('owner','source','review','provenance','identity','origin'):
            task=copy.deepcopy(self.stage_task)
            if label=='owner':task['owner']='foreign'
            elif label=='source':task['input_paths']=['tools/wrong.py']
            elif label=='identity':task['stage_binding']['identity']='0'*64
            elif label=='origin':task['stage_binding']['entry']['origin']='unsupported'
            else:task['stage_binding']['inputs'].pop(next(p for p in task['stage_binding']['inputs'] if ('review.json' if label=='review' else '0.json') in p))
            with self.subTest(label=label),self.assertRaises((AdmissionError,operations.OperationError)):
                self.current.stage_origin(issue.identifier,task)
        path=Path(spec['local_source_root'])/'tools/delivery/manual.py';raw=path.read_bytes();path.write_bytes(raw+b' ')
        with self.assertRaises(operations.OperationError):stage.qualify_reviewed_source(spec,runtime.parent/'synthetic-manual-history/new-admission.json')
        path.write_bytes(raw)
        journal.cancel(key);asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'cancelled')
        remote.submit.assert_not_awaited()

    def test_new_origin_missing_native_dependency_fails_fixed_subprocess(self):
        import subprocess
        import stokowski_operations as operations
        _,_,_,_,_,spec,_,_=self.new_fixture()
        command=operations.bridge_arguments(spec)['command'].replace(spec['workspace'],spec['local_source_root'])
        command=command.replace('/offmenu/.venv-delivery/bin/python',sys.executable+' -S')
        result=subprocess.run(['/bin/sh','-c',command],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(result.returncode,0)
        self.assertIn("No module named 'stokowski'",result.stderr)

    def drifted_job_recovery(self, drift, coordinator):
        import hashlib
        import stokowski_operations as operations
        issue,runtime,owner,journal,key,spec,remote,_=self.new_fixture()
        self.publish_stage()
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'submitted')
        original_spec,original_state=journal.read(key)
        admission=runtime.parent/'synthetic-manual-history/new-admission.json'
        target=(Path(spec['local_source_root'])/'tools/delivery/manual.py' if drift=='candidate' else admission)
        target.write_bytes(target.read_bytes()+b' ')
        journal.cancel(key)
        self.assertEqual(journal.read(key)[1]['status'],'submitted')
        self.assertTrue(journal.read(key)[1]['cancel_requested'])
        remote.inspect.reset_mock();remote.submit.reset_mock()
        def tick():
            return asyncio.run(owner._tick() if coordinator else journal.tick(key,remote))
        # Lost transport/state is reconciled against the original UUID, never resubmitted.
        remote.inspect.return_value=None
        tick()
        self.assertGreater(remote.inspect.await_count,0)
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        remote.submit.assert_not_awaited()
        self.current=adapter.CurrentWork(self.runtime)
        asyncio.run(self.current.continue_validation())
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        remote.submit.assert_not_awaited()
        remote.inspect.side_effect=operations.TransportUnavailable('synthetic outage')
        tick()
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        remote.inspect.side_effect=None
        journal.cancel(key)
        args=operations.bridge_arguments(spec)
        def observed(job,expected,**extra):
            return dict(id=job,args=expected,workspace_id='offmenu',script_path=operations.BRIDGE,**extra)
        running=observed(original_state['windmill_job_id'],args,type='QueuedJob',running=True)
        remote.inspect.side_effect=lambda job: running if job==original_state['windmill_job_id'] else None
        tick()
        self.assertEqual(journal.read(key)[1]['status'],'cancel-requested')
        remote.submit.assert_awaited_once_with(original_state['cancel_job_id'],operations.bridge_arguments(spec,'cancel'))
        tick()
        self.assertEqual(remote.submit.await_count,1)
        receipt=dict(status='cancelled',child_tree_gone=False,job_id=original_state['logical_job_id'],
            command_sha256=hashlib.sha256(args['command'].encode()).hexdigest(),
            runner_sha256=spec['runner_sha256'],capacity_policy_sha256=spec['policy_sha256'])
        result=dict(job_id=original_state['logical_job_id'],receipt=receipt)
        remote.inspect.side_effect=None
        remote.inspect.return_value=observed(original_state['windmill_job_id'],args,type='CompletedJob',result=result)
        tick()
        self.assertEqual(journal.read(key)[1]['status'],'unknown')
        receipt['child_tree_gone']=True
        tick()
        saved_spec,state=journal.read(key)
        self.assertEqual(state['status'],'cancelled')
        self.assertEqual(state['accepted_output_sha256'],{})
        self.assertEqual(saved_spec,original_spec)
        for name in ('windmill_job_id','cancel_job_id','logical_job_id'):
            self.assertEqual(state[name],original_state[name])
        with self.assertRaises((AdmissionError,operations.OperationError)):
            self.current.gate_binding(issue)
        self.assertEqual(remote.submit.await_count,1)

    def test_drifted_candidate_coordinator_recovers_original_job(self):
        self.drifted_job_recovery('candidate',True)

    def test_drifted_admission_coordinator_recovers_original_job(self):
        self.drifted_job_recovery('admission',True)

    def test_drifted_candidate_journal_recovers_original_job(self):
        self.drifted_job_recovery('candidate',False)

    def test_drifted_admission_journal_recovers_original_job(self):
        self.drifted_job_recovery('admission',False)

    def drift_blocks_submission_and_acceptance(self, drift):
        import hashlib
        import stokowski_operations as operations
        issue,runtime,owner,journal,key,spec,remote,_=self.new_fixture()
        self.publish_stage()
        target=(Path(spec['local_source_root'])/'tools/delivery/manual.py' if drift=='candidate'
                else runtime.parent/'synthetic-manual-history/new-admission.json')
        raw=target.read_bytes();target.write_bytes(raw+b' ')
        asyncio.run(owner._tick())
        remote.submit.assert_not_awaited()
        self.assertNotEqual(journal.read(key)[1]['status'],'succeeded')
        # A successful original backend receipt must not accept drifted bytes.
        _,state=journal.read(key)
        args=operations.bridge_arguments(spec)
        receipt=dict(status='succeeded',exit_code=0,child_tree_gone=True,reconcile_required=False,
            job_id=state['logical_job_id'],command_sha256=hashlib.sha256(args['command'].encode()).hexdigest(),
            runner_sha256=spec['runner_sha256'],capacity_policy_sha256=spec['policy_sha256'])
        remote.inspect.return_value=dict(id=state['windmill_job_id'],args=args,workspace_id='offmenu',
            script_path=operations.BRIDGE,type='CompletedJob',
            result=dict(job_id=state['logical_job_id'],job_succeeded=True,receipt=receipt))
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'quarantined')
        self.assertEqual(journal.read(key)[1]['accepted_output_sha256'],{})
        remote.submit.assert_not_awaited()
        self.assertFalse(self.current.state['accepted_delivery'])
        with self.assertRaises((AdmissionError,operations.OperationError)):
            self.current.gate_binding(issue)
        # Historical success also loses current acceptance when bytes drift.
        target.write_bytes(raw)
        state.update(status='succeeded',accepted_output_sha256=spec['outputs'])
        journal.save(key,state,'synthetic-prior-success')
        target.write_bytes(raw+b' ')
        asyncio.run(journal.tick(key,remote))
        self.assertEqual(journal.read(key)[1]['status'],'quarantined')
        self.assertEqual(journal.read(key)[1]['accepted_output_sha256'],{})

    def test_drifted_candidate_blocks_new_submit_and_acceptance(self):
        self.drift_blocks_submission_and_acceptance('candidate')

    def test_drifted_admission_blocks_new_submit_and_acceptance(self):
        self.drift_blocks_submission_and_acceptance('admission')

    def test_drift_recovery_refuses_tampered_binding_and_foreign_job(self):
        import stokowski_operations as operations
        issue,runtime,owner,journal,key,spec,remote,_=self.new_fixture()
        selected=self.publish_stage()
        asyncio.run(owner._tick())
        target=Path(spec['local_source_root'])/'tools/delivery/manual.py'
        target.write_bytes(target.read_bytes()+b' ')
        _,state=journal.read(key)
        # Mutable journal identities and canonical spec bytes are never authority.
        for field in ('windmill_job_id','cancel_job_id','logical_job_id'):
            remote.inspect.reset_mock()
            journal.save(key,dict(state,**{field:'foreign'}),'synthetic-tamper')
            with self.subTest(field=field),self.assertRaises(operations.OperationError):
                asyncio.run(journal.tick(key,remote))
            asyncio.run(owner._tick())
            remote.inspect.assert_not_awaited()
        journal.save(key,state,'synthetic-restore')
        for field,value in (('issue_id','00000000-0000-4000-8000-000000000999'),):
            changed=dict(spec,**{field:value})
            with journal.db() as db:
                db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(changed,sort_keys=True),key))
            with self.subTest(field=field),self.assertRaises(operations.OperationError):
                asyncio.run(journal.tick(key,remote))
            asyncio.run(owner._tick())
            remote.inspect.assert_not_awaited()
        with journal.db() as db:
            db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(spec,sort_keys=True),key))
        for path in (selected/'manifest.json',selected/'requests/UIF-106.json',runtime/'validation-bindings.json',
                     self.source/'tools/delivery/stokowski_worker.py'):
            raw=path.read_bytes();path.write_bytes(raw+b' ')
            try:
                if path.is_relative_to(self.source):
                    with self.assertRaises(AdmissionError):
                        asyncio.run(owner._tick())
                else:
                    asyncio.run(owner._tick())
                remote.inspect.assert_not_awaited()
            finally:
                path.write_bytes(raw)
            self.current.fatal=None
            self.current.state.pop('fatal',None)
        # Owner is deliberately excluded from the semantic key: the original
        # remote command and coordinator binding must refuse its replacement.
        with journal.db() as db:
            db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(dict(spec,owner='foreign'),sort_keys=True),key))
        asyncio.run(owner._tick())
        remote.inspect.assert_not_awaited()
        remote.inspect.return_value=dict(id=state['windmill_job_id'],workspace_id='offmenu',
            script_path=operations.BRIDGE,type='QueuedJob',running=True,args=operations.bridge_arguments(spec))
        result=asyncio.run(journal.tick(key,remote))
        self.assertEqual(result['status'],'quarantined')
        with journal.db() as db:
            db.execute('UPDATE operations SET spec=? WHERE key=?',(json.dumps(spec,sort_keys=True),key))
        journal.save(key,state,'synthetic-restore-owner')
        remote.inspect.reset_mock()
        catalog_raw=self.catalog.read_bytes()
        catalog=json.loads(catalog_raw)
        catalog['entries'][0]['issue_id']='00000000-0000-4000-8000-000000000999'
        self.write(self.catalog,catalog)
        with self.assertRaises(AdmissionError):
            asyncio.run(owner._tick())
        remote.inspect.assert_not_awaited()
        self.catalog.write_bytes(catalog_raw)
        self.current.fatal=None
        self.current.state.pop('fatal',None)
        task=copy.deepcopy(self.stage_task);task['stage_binding']['identity']='0'*64
        with self.assertRaises(AdmissionError):
            self.current.reviewed_origin(issue.identifier,task,observation=True)
        remote.inspect.return_value=dict(id=state['windmill_job_id'],workspace_id='offmenu',
            script_path=operations.BRIDGE,type='QueuedJob',running=True,args=dict(action='run',job_id='foreign'))
        remote.submit.reset_mock()
        asyncio.run(owner._tick())
        self.assertEqual(journal.read(key)[1]['status'],'quarantined')
        remote.submit.assert_not_awaited()
