"""One synthetic native result through candidate, Journal, review and selection.

Real Git/SQLite/bundle/test execution; explicit provider/publisher boundaries.
No live service, credential, Pool admission, API or deployment evidence.
"""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

import stokowski_adapter as adapter
import stokowski_operations as operations
import stokowski_stage as stage
import native_harness_runtime as runtime
import native_harness_contract as contract
import stokowski_unit_review as review_writer
import native_publisher_invocation as publisher
import windmill_dispatcher as dispatcher
from symphony_tasks import runtime_lease_ids
from test_stokowski_operations import FaultedWindmill


class NativeProgressionTests(unittest.TestCase):
    def test_original_result_candidate_journal_review_and_derived_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo=root/'repository';repo.mkdir()
            def git(where,*args):
                return subprocess.check_output(['git','-C',str(where),'-c','user.name=Synthetic',
                    '-c','user.email=synthetic@example.invalid',*args],stderr=subprocess.PIPE).decode().strip()
            def write(path,value):
                path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,sort_keys=True)+'\n');path.chmod(0o600)
            git(repo,'init','-b','bugfix/original-native')
            write(repo/'repository-standard.json',{'runtime_hold_paths':[]})
            policy=contract.load_release_policy(Path(__file__).resolve().parents[2]/'config/delivery-release-policy.json')
            write(repo/'config/delivery-release-policy.json',policy)
            (repo/'src').mkdir()
            output='tests/delivery/test_synthetic.py'
            target=repo/output;target.parent.mkdir(parents=True)
            target.write_text('import unittest\nclass Example(unittest.TestCase):\n def test_ok(self): self.assertEqual(40+2,42)\n')
            git(repo,'add','.');git(repo,'commit','-qm','base')
            base=git(repo,'rev-parse','HEAD')
            original=root/'native';workspace=original/'workspaces/UIF-138';workspace.parent.mkdir(parents=True)
            subprocess.run(['git','clone','--quiet',str(repo),str(workspace)],check=True)
            (workspace/output).write_text('import unittest\nclass Example(unittest.TestCase):\n def test_ok(self): self.assertEqual(sum([20,22]),42)\n')
            outputs={output:stage.file_hash(workspace/output)}
            resources=dict(cpu_millis=1000,memory_bytes=1610612736,io_slots=1,output_bytes=536870912)
            task=dict(issue_id='418060d3-ef43-491d-ac8e-70747129b448',owner='synthetic-owner',purpose='source only',
                allowed_paths=[output],acceptance=['synthetic fix'],resources=resources,attempt_limit=1)
            manifest=dict(version=1,project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',branch='bugfix/original-native',
                base_revision=base,label='native-fixture',tasks={'UIF-138':task})
            request=dict(prompt='synthetic only',timeout_seconds=600)
            write(original/'manifest.json',manifest);write(original/'requests/UIF-138.json',request)
            pool=root/'pool';pool.mkdir();write(original/'capacity-policy.json',{'symphony':{'pool_path':str(pool)}})
            write(original/'provider-proof.json',{'fixture_only':True})
            write(original/'current-admission.json',dict(manifest_sha256=stage.file_hash(original/'manifest.json'),request_sha256=stage.file_hash(original/'requests/UIF-138.json')))
            entry=dict(issue='UIF-138',issue_id=task['issue_id'],runtime=str(original),admission_sha256=stage.file_hash(original/'current-admission.json'))
            binding=dict(branch=manifest['branch'],head=base,owner=task['owner'],write_roots=[output],resources=resources,
                task_sha256=operations.digest(dict(runtime=str(original),manifest=manifest,request=request)))
            lease=runtime_lease_ids(original,manifest)['UIF-138'];attempt=original/'attempts/UIF-138'
            receipt=dict(status='succeeded',child_tree_gone=True,scope_violations=[],source_head=base,origin='native-coding',
                exit_code=0,turn_completed=True,session_id='synthetic-author-session',source_identity_changed=False,
                final_head=base,final_branch=manifest['branch'],parent_runtime=str(original),issue='UIF-138',parent_binding=binding,
                binding_sha256=operations.digest(binding),lease=lease,output_sha256=outputs,accepted_delivery=False)
            write(attempt/'receipt.json',receipt);write(attempt/'intent.json',dict(lease=lease,binding=binding))
            write(attempt/'dispatch-intent.json',dict(expected_lease=lease,owner=task['owner'],entry_sha256=operations.digest(entry),
                manifest_sha256=stage.file_hash(original/'manifest.json'),request_sha256=stage.file_hash(original/'requests/UIF-138.json'),provider_proof_sha256=stage.file_hash(original/'provider-proof.json')))
            with sqlite3.connect(pool/'state.sqlite') as db:
                db.execute('CREATE TABLE leases(id TEXT,status TEXT,outcome TEXT,binding TEXT,fingerprint TEXT)')
                db.execute('INSERT INTO leases VALUES(?,?,?,?,?)',(lease,'finished','succeeded',json.dumps(binding),operations.digest(binding)))
            native_before={p:p.read_bytes() for p in (original/'manifest.json',original/'current-admission.json',attempt/'receipt.json',attempt/'intent.json',attempt/'dispatch-intent.json')}
            template=dict(profile=operations.UNIT_PROFILE,policy_sha256=stage.file_hash(operations.POLICY),
                runner_sha256=stage.file_hash(Path(operations.__file__).with_name('windmill_runner.py')),
                executor_sha256=stage.file_hash(operations.__file__),git_author=dict(name='Synthetic',email='synthetic@example.invalid'),
                validation_targets=['test_synthetic.Example.test_ok'],validation_scope=[output],source_repository=str(repo))
            candidate=original/'contributions/UIF-138/candidate'
            with patch.object(stage,'SOURCE',repo):
                made=stage.prepare_completed_native(original,'UIF-138',candidate_root=candidate,template=template)
                self.assertEqual(stage.prepare_completed_native(original,'UIF-138',candidate_root=candidate,template=template),made)
            self.assertEqual(git(repo,'rev-parse','HEAD'),base)
            self.assertEqual(git(workspace,'rev-parse','HEAD'),base)
            self.assertTrue(all(p.read_bytes()==v for p,v in native_before.items()))
            spec=json.loads(Path(made['spec_path']).read_bytes());args=operations.bridge_arguments(spec)
            self.assertEqual(dispatcher.validate_request(args),args)
            # Same frozen body, only host mount/Python installation relocated.
            code=operations.unit_validation_code(spec).replace("source=pathlib.Path('/offmenu')",'source=pathlib.Path('+repr(str(repo))+')')
            code=code.replace("'/offmenu/.venv-delivery/bin/python'",repr(sys.executable))
            subprocess.run([sys.executable,'-B','-c',code],check=True,capture_output=True,text=True)
            journal=operations.Journal(original/'operations');remote=FaultedWindmill();key=made['operation_key']
            asyncio.run(journal.tick(key,remote))
            state=journal.read(key)[1];remote.complete(state['windmill_job_id'],spec)
            state=asyncio.run(journal.tick(key,remote));self.assertEqual(state['status'],'succeeded')
            validation=json.loads((original/'validation-receipt.json').read_bytes())
            coordinator=root/'coordinator';coordinator.mkdir()
            unit=dict(operation_sha256=operations.digest(binding),project_id=manifest['project_id'],issue_id=task['issue_id'],native_receipt_sha256=stage.file_hash(attempt/'receipt.json'))
            source=dict(root=str(candidate),head=spec['head'],base=base,tree=spec['tree'],branch=spec['branch'],outputs=outputs)
            reviewed=dict(version=1,origin='native-readonly-review-v1',issue='UIF-138',unit_binding=unit,source=source,
                verdict='accept',findings=[],native_session_id='synthetic-independent-session',accepted_delivery=False)
            write(coordinator/'unit-review-UIF-138.json',reviewed)
            config=dict(owner=task['owner'],policy_sha256=spec['policy_sha256'],source_sha256={'tools/delivery/native_publisher_invocation.py':stage.file_hash(publisher.__file__)})
            current=SimpleNamespace(runtime=coordinator,config=config,read_only=False,stopping=False,entries={'UIF-138':entry},state={'tasks':{'UIF-138':{}}},
                guard=lambda:None,postcoding_template=lambda i:None,postcoding_contract=lambda i:({},dict(dependencies=[]),{}),
                context=lambda *a,**k:(original,manifest,repo),gate_binding=lambda *a,**k:unit,validation_binding=lambda *a:(original,'identity'),
                _completed_native_evidence=lambda *a:receipt,private=lambda value:Path(value),save=lambda:None)
            current._check_reviewed_terminal=lambda *a,**k:adapter.CurrentWork._check_reviewed_terminal(current,*a,**k)
            # Root seal and contract are explicit authority boundaries; actual
            # generic template derivation/source/Journal/author checks run here.
            config.update(source_head=base,installation_sha256='f'*64)
            generic=dict(schema='native-review-template-v2',owner=task['owner'],reviewer_owner='independent-reviewer',project_id='derived',
                source_head=base,source_sha256=config['source_sha256'],installation_sha256=config['installation_sha256'],source_root='derived',
                validation_receipt_name='validation-receipt.json',provider='codex-chatgpt',model=adapter.MODEL,effort='medium',resources='derived',
                acceptance='derived',timeout_seconds=300,require_stopped_child=True,role='native-review-read-only',
                producer=dict(git_author=template['git_author'],source_repository=str(repo)))
            write(coordinator/'template.json',generic)
            config['native_review_template']=dict(path=str(coordinator/'template.json'),sha256=stage.file_hash(coordinator/'template.json'))
            current.postcoding_contract=lambda i:({},dict(dependencies=[],resources=resources,acceptance=task['acceptance']),{})
            current.validation_binding=lambda *a:(original,'e'*64)
            current.state['tasks']['UIF-138']['unit_gate']=dict(binding=unit,disposition='waiting')
            with patch.object(adapter,'current_config',return_value=(config,None)):
                policyref=adapter.CurrentWork.native_review_template_policy(current,'UIF-138',materialize=True)
                derived=json.loads(Path(policyref['path']).read_bytes())
                self.assertEqual(derived['source']['head'],spec['head'])
                self.assertEqual(derived['excluded_sessions'],['synthetic-author-session'])
                self.assertEqual(derived['acceptance'],task['acceptance'])
            current._native_harness_selection=lambda i:json.loads(Path(current.state['tasks'][i]['native_publication']['selection']['path']).read_bytes())
            async def produce(c,issue,packet):
                # Protected publisher is an explicit boundary double; inspect
                # exact inputs rather than granting actual owner custody.
                runtime.native_journal_acceptance(c,issue,str(original),packet['handoff'])
                runtime.review_coverage(reviewed,packet['handoff'],None)
                return dict(binding=dict(issue_id=issue.id,project_id=manifest['project_id'],owner=task['owner'],packet_sha256=contract.fingerprint(packet),
                    operation_id='a'*64,phase='integration',unit_sha256=contract.fingerprint(unit)),
                    packet=dict(path=str(original/'native-publication-packet.json'),sha256=stage.file_hash(original/'native-publication-packet.json')),
                    context=dict(native_runtime=str(original),pending_unit_review={'fixture_only':True},publisher_invocation={'fixture_only':True}))
            client=SimpleNamespace(_graphql=AsyncMock(return_value={'issue':dict(id=task['issue_id'],identifier='UIF-138',team={'id':'53f584e7-70a1-4b1e-b982-b815210e47d4'},project={'id':manifest['project_id'],'name':'OffMenu'},state={'type':'started'},inverseRelations={'nodes':[],'pageInfo':{'hasNextPage':False}},attachments={'nodes':[],'pageInfo':{'hasNextPage':False}})}))
            with patch.object(runtime,'pinned_private',lambda c,ref:json.loads(Path(ref['path']).read_bytes())),patch.object(adapter,'SOURCE',repo),patch.object(review_writer,'qualify_native_review',return_value=reviewed),patch.object(runtime,'produce_native_publication',produce,create=True):
                selected=asyncio.run(runtime.prepare_native_unit(current,'UIF-138',linear_client=client))
                self.assertEqual(selected['binding']['unit_sha256'],contract.fingerprint(unit))
            self.assertEqual(validation['status'],'succeeded')
            self.assertFalse(reviewed['accepted_delivery'])
            self.assertTrue(all(p.read_bytes()==v for p,v in native_before.items()))
            # One changed body and one unsafe target are rejected at admission.
            with self.assertRaises(ValueError):dispatcher.validate_request(dict(args,command=args['command']+' '))
            with self.assertRaises(operations.OperationError):operations.validated(dict(spec,validation_targets=['os.system']))
            (workspace/output).write_text('drift')
            with self.assertRaises(operations.OperationError):stage.prepare_completed_native(original,'UIF-138',candidate_root=candidate,template=template)


class PostcodingFiniteAssociationTests(unittest.TestCase):
    def test_explicit_finite_targets_preserve_original_authority_and_scope(self):
        import stokowski_prepare as prepare
        path='tests/delivery/test_stokowski_current_dispatch.py'
        target='test_stokowski_current_dispatch.CurrentDispatchTests.test_owned_turn_private_dispatch_intent_under_permissive_umask'
        original=dict(issue_id='418060d3-ef43-491d-ac8e-70747129b448',project_id='ce60c1ab-a732-4a71-8471-14c9dc393886',
            scope=[path],input_paths=[],resources={'cpu_millis':1000},acceptance=['finite source fix'],validation_targets=[target])
        policy=dict(contracts={'UIF-138':original})  # No workclass or qualification.
        task=dict(issue_id=original['issue_id'],owner='root-owner',allowed_paths=[path],acceptance=original['acceptance'],resources=original['resources'])
        current=SimpleNamespace(config={'owner':'root-owner'},guard=lambda:None,
            context=lambda *a,**k:(Path('/synthetic/native'),dict(project_id=original['project_id'],base_revision='a'*40,tasks={'UIF-138':task}),None))
        before=copy.deepcopy((policy,task))
        # Compiler/seal accessors are the owned authority boundary. This check
        # exercises the postcoding consumer only; it invents no native proof.
        with patch.object(prepare,'owner_intake_policy',return_value=policy,create=True), \
             patch.object(prepare,'owner_policy_contract',side_effect=lambda c,p,i:p['contracts'][i],create=True), \
             patch.object(prepare,'owner_policy_validation_targets',return_value=[target],create=True), \
             patch.object(prepare,'OWNER_CODE_FILES',{path},create=True):
            _,retained,selection=adapter.CurrentWork.postcoding_contract(current,'UIF-138')
            self.assertIs(retained,original)
            self.assertEqual(selection,dict(authority_origin='root-finite-contract',validation_targets=[target],validation_scope=[path]))
            self.assertEqual((policy,task),before)
            del original['validation_targets']
            with self.assertRaisesRegex(adapter.AdmissionError,'postcoding_source_only_contract_required'):
                adapter.CurrentWork.postcoding_contract(current,'UIF-138')
            original['validation_targets']=[target]
            original['input_paths']=['data/held/private.json']
            with self.assertRaisesRegex(adapter.AdmissionError,'postcoding_source_only_contract_required'):
                adapter.CurrentWork.postcoding_contract(current,'UIF-138')
            original['input_paths']=[]
            task['acceptance']=['a different outcome']
            with self.assertRaisesRegex(adapter.AdmissionError,'postcoding_original_task_outside_contract'):
                adapter.CurrentWork.postcoding_contract(current,'UIF-138')
