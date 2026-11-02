"""Two sealed contracts through the native candidate and real publication seam."""
import asyncio
import copy
import json
from pathlib import Path
import time
import unittest
from unittest.mock import patch

import stokowski_adapter as adapter
import stokowski_prepare as prepare
from symphony_capacity import AdmissionError, digest, Pool, host_snapshot
from stokowski.models import Issue
import test_stokowski_current_dispatch as fixtures


class OwnerPolicyIntakeTests(unittest.TestCase):
    def test_two_contracts_native_boundary_and_refusals(self):
        fixture = fixtures.CurrentDispatchTests('runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        native = fixture.native_harness_fixture()
        current = fixture.current
        protected = fixture.temp/'sealed'
        protected.mkdir()
        seed = current.catalog.read_bytes()
        seed_count=len(json.loads(seed)['entries'])
        current.catalog.write_bytes(seed)
        (protected/'catalog.json').write_bytes(seed)
        fixture.write(protected/'binding.json', dict(runtime=str(current.runtime)))
        policy_path = protected/'owner-policy.json'
        proof_path = fixture.root/'fresh-provider.json'
        fixture.write(proof_path, dict(route='codex-chatgpt',available=True,
            checked_at=time.time(),requested_model=adapter.MODEL,session_ceiling=8))
        resources = dict(cpu_millis=1000,memory_bytes=1610612736,io_slots=1,output_bytes=536870912)
        matthew='00000000-0000-4000-8000-000000000901'
        first = Issue(id='00000000-0000-4000-8000-000000000801',identifier='UIF-801',title='Synthetic',state='Todo')
        second = Issue(id='00000000-0000-4000-8000-000000000802',identifier='UIF-802',title='Synthetic',state='Todo')
        def contract(issue, dependencies):
            return dict(issue_id=issue.id,project_id=adapter.PROJECT,purpose='Approved synthetic regression',
                scope=['tests/delivery/test_stokowski_owner_policy_intake.py'],input_paths=[],acceptance=['Exact sealed synthetic acceptance'],
                prompt='Implement only the sealed synthetic regression.',timeout_seconds=30,
                resources=resources,dependencies=dependencies,assignee_id=matthew)
        policy = dict(schema='offmenu-owner-policy-intake/1',owner=current.config['owner'],
            source_head=current.config['source_head'],source_branch='feature/test-current',
            coordinator_runtime=str(current.runtime),expires_at=time.time()+300,
            resource_ceiling=resources,
            installation=dict(path=str(fixture.root/'installation.json'),sha256=adapter.file_sha(fixture.root/'installation.json')),
            provider_requirements=dict(requested_model=adapter.MODEL,requested_effort='medium',route='codex-chatgpt',
                session_ceiling=8,max_age_seconds=300,checked_at_max_future_skew_seconds=5),
            contracts={first.identifier:contract(first,[])},workclass=dict(assignee_id=matthew,
                project_ids=[adapter.PROJECT],allowed_files=sorted(prepare.OWNER_CODE_FILES),max_files=4,
                resources=resources,timeout_seconds=60,acceptance=prepare.OWNER_CODE_ACCEPTANCE,selection_label='offmenu-source-bau'))
        fixture.write(policy_path,policy)
        current.config['owner_intake_policy']=dict(path=str(policy_path),sha256=adapter.file_sha(policy_path))
        fixture.write(current.config_path,current.config)
        current.config_sha=adapter.file_sha(current.config_path)
        custody={'synthetic-root-boundary':True}
        current.owner_custody=custody
        self.enterContext(patch.object(adapter,'PROTECTED_OWNER',protected))
        # Only the root-owned filesystem boundary is synthetic. Source checks,
        # compiler, manifest/admission hashes, publication locks/journal, catalog
        # derivation and native candidate selection all execute their real code.
        self.enterContext(patch.object(adapter,'protected_owner_bytes',side_effect=lambda p:Path(p).read_bytes()))
        self.enterContext(patch.object(adapter,'current_config',return_value=(current.config,current.config_path,custody)))
        states={first.id:'Todo',second.id:'Todo'}
        class Client:
            async def _graphql(self, query, variables):
                selected=next((i for i in (first,second) if i.id==variables['id']),None)
                if selected is None:
                    return dict(issue=dict(id=variables['id'],identifier='UIF-899',project=dict(id='foreign'),
                        state=dict(name='Todo'),inverseRelations=dict(nodes=[])))
                deps=[] if selected==first else [dict(type='blocks',issue=dict(id=first.id,state=dict(name=states[first.id])))]
                return dict(issue=dict(id=selected.id,identifier=selected.identifier,project=dict(id=adapter.PROJECT),
                    title='Source-only synthetic regression',description='Qualify one bounded code path.',delegate=None,
                    labels=dict(nodes=[dict(name='offmenu-source-bau')]),
                    assignee=dict(id=matthew),state=dict(name=states[selected.id]),inverseRelations=dict(nodes=deps)))
        client=Client()
        # Metadata provider boundary only; production calls the existing pinned
        # symphony_launch.provider_proof, never a manually refreshed file.
        self.enterContext(patch.object(prepare,'owner_policy_provider_proof',side_effect=lambda *args:
            dict(route='codex-chatgpt',available=True,checked_at=time.time(),requested_model=adapter.MODEL,session_ceiling=8)))
        selected=lambda issues:asyncio.run(current.candidates(client,issues))
        callbacks=[]
        original_refill=prepare.owner_policy_refill
        async def observed_refill(owner, client):
            self.assertTrue(owner._native_harness_refill_allowed(native.issue.identifier))
            callbacks.append(True)
            await original_refill(owner,client)
        self.enterContext(patch.object(prepare,'owner_policy_refill',new=observed_refill))
        consume=lambda:asyncio.run(current.continue_native_harness(native.factory,linear_client=client))
        self.assertEqual(selected([first]),[])
        self.assertEqual(len(current.catalog_record()['entries']),seed_count)
        self.assertFalse(current._native_harness_refill_allowed(native.issue.identifier))
        consume()
        self.assertEqual(len(current.catalog_record()['entries']),seed_count+1,
            (callbacks,current.state['tasks'][first.identifier]))
        self.assertFalse(current._native_harness_refill_allowed(native.issue.identifier))
        self.assertEqual(selected([second]),[])
        self.assertEqual(len(current.catalog_record()['entries']),seed_count+1)
        # Native terminal reconciliation remains an independent authority. A
        # tracker Done alone is insufficient; no fixture launches a child.
        states[first.id]='Done'
        reconciled=set()
        self.enterContext(patch.object(current,'_reconciled_unit',side_effect=lambda issue:issue in reconciled))
        self.assertEqual(selected([second]),[])
        consume()
        self.assertEqual(len(current.catalog_record()['entries']),seed_count+1)
        reconciled.add(first.identifier)
        def clone(source,path,head,branch):
            path.mkdir(parents=True,mode=0o700)
        self.enterContext(patch.object(adapter,'clone_current_workspace',new=clone,create=True))
        launches=[]
        def qualification(record, delegated, authority):
            spec=current._private_pin(authority['qualification']);workspace=Path(spec['workspace'])
            directory=workspace/'qualification-runtime';directory.mkdir()
            record['qualification_intent']=dict(spec=authority['qualification'],directory=str(directory))
            binding=dict(branch=spec['branch'],head=spec['head'],owner=current.config['owner'],
                write_roots=[spec['output']],resources=spec['resources'],task_sha256=digest(spec))
            lease='qualification-'+digest(dict(runtime=str(current.runtime),reference=record['reference']))[:48]
            pool=Pool(fixture.policy['symphony']['pool_path'],fixture.policy)
            pool.admit(lease,binding,json.loads(proof_path.read_bytes()),host_snapshot(workspace))
            fixture.write(directory/'intent.json',dict(lease=lease,binding=binding))
            proposal=dict(schema='offmenu-owner-policy-plan/1',issue_id=second.id,source_head=current.config['source_head'],
                rights='source-only-synthetic',scope=contract(second,[])['scope'],input_paths=[],
                purpose='Synthetic delegated regression',behavior='Preserve approved synthetic behavior',
                check='test_stokowski_owner_policy_intake.OwnerPolicyIntakeTests.test_two_contracts_native_boundary_and_refusals')
            output=dict(schema='offmenu-qualification-proposal/1',proposal=json.dumps(proposal),missing_inputs=[])
            fixture.write(workspace/spec['output'],output)
            fixture.write(directory/'result.json',dict(lease=lease,origin='native-qualification',status='succeeded',
                child_tree_gone=True,exit_code=0,turn_completed=True,requested_model=adapter.MODEL,requested_effort='medium',provider_route='codex-chatgpt',
                authority='proposal-only',proposal=output,output_sha256=adapter.file_sha(workspace/spec['output'])))
            pool.finish(lease,True,'succeeded');current.save();launches.append(lease)
            raise AdmissionError('synthetic_native_qualification_completed')
        # Native model execution is the explicit fixture seam. The original
        # Pool lease/binding/receipt/output verifier and promotion are real.
        self.enterContext(patch.object(current,'_qualification_boundary',side_effect=qualification))
        consume()
        entries=current.catalog_record()['entries']
        self.assertEqual([e['issue'] for e in entries][seed_count:],[first.identifier,second.identifier],current.state)
        self.assertEqual(selected([second]),[second])
        runtime=Path(entries[-1]['runtime'])
        self.assertEqual(adapter.load_manifest(runtime/'manifest.json',expected_branch=None)['tasks'][second.identifier]['allowed_paths'],
                         contract(second,[])['scope'])
        self.assertEqual(len(launches),1)
        self.assertEqual(adapter.file_sha(current.config_path),current.config_sha)
        self.assertEqual(adapter.file_sha(policy_path),current.config['owner_intake_policy']['sha256'])
        self.assertEqual(current.state.get('successor_request'),None)
        before=current.catalog.read_bytes()
        with self.assertRaises(AdmissionError):
            asyncio.run(prepare.owner_policy_candidate(current,client,first,current.route))
        foreign=Issue(id='00000000-0000-4000-8000-000000000899',identifier='UIF-899',title='Unapproved',state='Todo')
        selected([foreign]);consume()
        self.assertIn('tracker_binding',current.state['tasks'][foreign.identifier]['defer'])
        changed=copy.deepcopy(entries);changed[-1]['admission_sha256']='0'*64
        with self.assertRaises(AdmissionError):
            current.catalog_transition(before,prepare._publication_bytes(dict(version=1,entries=changed)))
        self.assertEqual(current.catalog.read_bytes(),before)
        with patch.object(prepare.time,'time',return_value=policy['expires_at']+1):
            # Expiry closes new compilation, never rewrites admitted history.
            self.assertEqual(current.catalog_bytes(),before)
            with self.assertRaisesRegex(AdmissionError,'owner_policy_binding'):
                asyncio.run(prepare.owner_policy_candidate(current,client,foreign,current.route))


if __name__ == '__main__':
    unittest.main()
