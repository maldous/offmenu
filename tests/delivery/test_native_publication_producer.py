"""Bounded original-native producer; private real Git/Journal/Controller only."""
import asyncio
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import native_harness_contract as contract
import native_harness_runtime as runtime
import native_publisher_invocation as helper
import stokowski_adapter as adapter
import stokowski_operations as operations
import stokowski_unit_review as reviews
import protected_publisher_install as installer
from offmenu.delivery.integration import _publisher_transaction_request, Controller
from offmenu.delivery.engine import DeliveryError
import test_completed_native_transition as native_fixture

ROOT=Path(__file__).resolve().parents[2]


class NativePublicationProducerTests(unittest.TestCase):
    def setUp(self):
        f=native_fixture.CompletedNativeTransitionTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        f.test_completed_control_review_and_same_runtime_v1_contribution();self.f=f;self.current=c=f.current
        self.guard=patch.object(c,'guard');self.guard.start();self.addCleanup(self.guard.stop)
        self.issue=SimpleNamespace(identifier='UIF-102',id=f.entry['issue_id'])
        selected=adapter.read_record(f.runtime/'validation-bindings.json')['issues'][self.issue.identifier]
        self.journal=operations.Journal(f.runtime/'operations');self.key=selected['operation_key']
        self.spec,self.state=self.journal.read(self.key);spec=self.spec
        self.receipt=dict(status='succeeded',exit_code=0,child_tree_gone=True,reconcile_required=False,
            job_id=self.state['logical_job_id'],runner_sha256=spec['runner_sha256'],
            capacity_policy_sha256=spec['policy_sha256'],command_sha256=helper.sha(operations.bridge_arguments(spec)['command'].encode()))
        f.write(f.runtime/'validation-receipt.json',self.receipt)
        self.state.update(status='succeeded',accepted_output_sha256=spec['outputs'],acceptance_sha256=spec['acceptance_sha256'],
            receipt_sha256=adapter.digest(self.receipt));self.journal.save(self.key,self.state,'SYNTHETIC terminal')
        self.unit=c.gate_binding(self.issue,observation=True)
        policy=contract.load_release_policy(ROOT/'config/delivery-release-policy.json')
        self.source=dict(repository='maldous/offmenu',head=spec['head'],base=spec['base'],
            tree=f.git(f.candidate,'rev-parse','HEAD^{tree}'),branch=spec['branch'],target='develop',policy_sha256=contract.fingerprint(policy))
        native_ref=dict(path=str(f.directory/'receipt.json'),sha256=adapter.file_sha(f.directory/'receipt.json'))
        validation_ref=dict(path=str(f.runtime/'validation-receipt.json'),sha256=adapter.file_sha(f.runtime/'validation-receipt.json'))
        handoff=dict(version=1,kind='delivery-handoff-v1',issue_id=self.issue.id,project_id=f.manifest['project_id'],
            owner=c.config['owner'],origin=dict(kind='native-coding-v1',evidence=native_ref),source=self.source,
            outputs=[dict(path=p,sha256=h) for p,h in spec['outputs'].items()],evidence=[native_ref,validation_ref],
            operation=dict(id=self.key,backend='windmill',job_id=self.receipt['job_id'],status='succeeded',
                command_sha256=self.receipt['command_sha256'],runner_sha256=spec['runner_sha256'],
                policy_sha256=spec['policy_sha256'],receipt=validation_ref))
        self.packet=dict(policy=policy,handoff=handoff,candidate=None,linear={},release=None)
        f.write(f.runtime/'native-publication-packet.json',self.packet)
        self.review=dict(version=1,origin='native-readonly-review-v1',issue=self.issue.identifier,unit_binding=self.unit,
            source=dict(root=str(f.candidate),**{k:self.source[k] for k in ('head','base','tree','branch')},outputs=spec['outputs']),
            verdict='accept',findings=[],native_session_id='SYNTHETIC independent session',
            policy=dict(path=str(f.runtime/'original-review-policy.json'),sha256=''),
            receipt=dict(path=str(f.runtime/'original-review-receipt.json'),sha256=''))
        for name,value in (('policy',dict(reviewer_owner='SYNTHETIC independent owner',model='unknown',provider='unknown')),
                           ('receipt',dict(resolved_model=None))):
            f.write(Path(self.review[name]['path']),value);self.review[name]['sha256']=adapter.file_sha(self.review[name]['path'])
        # Native reviewer/host custody are independently tested original readers;
        # this focused producer fixture supplies their already-qualified boundary.
        reader=patch.object(reviews,'qualify_native_review',return_value=self.review)
        reader.start();self.addCleanup(reader.stop)
        c.state['tasks'][self.issue.identifier]['unit_gate']=dict(binding=self.unit,disposition='approved',
            review_sha256=adapter.digest(self.review))
        self.policy=dict(version=1,kind='native-source-publication-policy-v1',owner=c.config['owner'],
            automatic_integration_enabled=True,
            project_ids=['ce60c1ab-a732-4a71-8471-14c9dc393886','ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0'],controller_runtime='/home/user/src/offmenu/.delivery/stokowski/coordinator',
            source_head=c.config['source_head'],owner_python_sha256='a'*64,
            source_sha256={'tools/delivery/native_publisher_invocation.py':'b'*64},
            profiles={'enrichment-resilience-focused':dict(allowed_paths=[f.output]),
                      'delivery-unit-focused':dict(allowed_paths=['tools/delivery/stokowski_adapter.py'])})
        self.base=dict(version=1,appId=5554359,installationId=177187048,repositoryId=1416253963,publisherUid=984,publisherGid=976,
            logicalOwner=c.config['owner'],sourceHead=c.config['source_head'],pythonSha256='c'*64,
            codePins={n:'d'*64 for n in ('tools/delivery/github-app-publisher.mjs','tools/delivery/github-app-adapter.mjs',
                'tools/delivery/integration-gateway.mjs','src/offmenu/delivery/integration.py','src/offmenu/delivery/engine.py',
                'src/offmenu/__init__.py','src/offmenu/delivery/__init__.py')},
            binding={},snapshot={},plan={},workspace='/unused',integration_admission={},native_policy=self.policy)
        self.request=dict(version=1,mode='prepare',issue=self.issue.identifier,issue_id=self.issue.id,
            project_id=f.manifest['project_id'],owner=self.policy['owner'],unit_sha256=helper.fingerprint(self.unit),
            packet_sha256=helper.fingerprint(self.packet))
        self.root=f.root/'publisher';self.root.mkdir(mode=0o700)

    def qualify(self):
        # Only the configured actor runtime path is synthetic; original native
        # context, source ancestry, lease, receipt, Journal and review consumer run.
        with patch.object(self.current,'runtime',Path(self.policy['controller_runtime'])):
            return helper.qualify_native_publication(self.base,self.request,self.current)

    def test_real_objects_normal_controller_prepare_and_exact_idempotent_receipt(self):
        before={p:p.read_bytes() for p in (self.f.directory/'receipt.json',self.f.runtime/'validation-receipt.json',
            self.f.runtime/'native-publication-packet.json',self.f.runtime/'validation-bindings.json')}
        value=self.qualify();config=value['config'];objects=value['objects']
        self.assertNotIn('source_projection',config['binding'])
        prepare=lambda:_publisher_transaction_request(config,{'op':'prepare'},self.root)
        result=helper.commit_native_preparation(config,self.request,'e'*64,objects=objects,root=self.root,uid=os.getuid(),prepare=prepare)
        self.assertEqual(result['operation_id'],helper.fingerprint(config['binding']))
        self.assertEqual(helper.commit_native_preparation(config,self.request,'e'*64,objects=objects,root=self.root,
            uid=os.getuid(),prepare=lambda:self.fail('no replay')),result)
        file=self.f.root/'qualified.json';file.write_text(json.dumps(value))
        script="import fs from 'node:fs';import {validateConfig,qualifyPreparedObjects} from './tools/delivery/github-app-publisher.mjs';const v=JSON.parse(fs.readFileSync(process.argv[1]));validateConfig(v.config,{uid:984,euid:984,gid:976,egid:976});await qualifyPreparedObjects(v.config,v.objects);"
        result=subprocess.run(['/usr/bin/node','--input-type=module','-e',script,str(file)],cwd=ROOT,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())
        for p,raw in before.items():self.assertEqual(p.read_bytes(),raw)

    def test_unknown_validation_review_rework_scope_and_wire_selectors_hold(self):
        for changed in (dict(status='unknown'),dict(cancel_requested=True),dict(observation_intent=True)):
            self.journal.save(self.key,dict(self.state,**changed),'SYNTHETIC hold')
            with self.subTest(changed=changed),self.assertRaises((helper.InvocationHold,adapter.AdmissionError)):
                self.qualify()
        self.journal.save(self.key,self.state,'SYNTHETIC restored')
        self.review['verdict']='rework'
        with self.assertRaises(helper.InvocationHold):self.qualify()
        self.review['verdict']='accept'
        self.policy['profiles']['enrichment-resilience-focused']['allowed_paths']=['tests/web/foreign.mjs']
        with self.assertRaises(helper.InvocationHold):self.qualify()
        for field in ('path','config','command','claim_root'):
            with self.subTest(field=field),self.assertRaises(helper.InvocationHold):
                helper.prepare_request(dict(self.request,**{field:'/tmp/not-authority'}))
        self.assertEqual(list(self.root.iterdir()),[])

    def test_pending_claim_and_partial_admission_hold_without_replay(self):
        value=self.qualify();c=value['config'];objects=value['objects'];key=helper.fingerprint(c['binding'])
        helper.commit_native_preparation(c,self.request,'e'*64,objects=objects,root=self.root,uid=os.getuid(),
            prepare=lambda:_publisher_transaction_request(c,{'op':'prepare'},self.root))
        controller=Controller(self.root/('transaction-'+key),c['binding'],self.root)
        controller.publication_intent(0,c['plan']['operations'][0])
        other=copy.deepcopy(c);other['binding']['issue_id']='12345678-1234-1234-1234-123456789abc'
        with self.assertRaises(DeliveryError):
            helper.commit_native_preparation(other,self.request,'e'*64,objects=objects,root=self.root,uid=os.getuid(),
                prepare=lambda:_publisher_transaction_request(other,{'op':'prepare'},self.root))
        with self.assertRaisesRegex(helper.InvocationHold,'native_prepare_unknown'):
            helper.commit_native_preparation(other,self.request,'e'*64,objects=objects,root=self.root,uid=os.getuid(),
                prepare=lambda:self.fail('partial admission must not retry'))

    def test_normal_owner_transport_returns_existing_selection_shape(self):
        value=self.qualify();c=value['config'];self.current.read_only=False;self.current.stopping=False
        self.current.config['source_sha256']={'tools/delivery/native_publisher_invocation.py':adapter.file_sha(helper.__file__)}
        reply=dict(version=1,kind='native-publisher-prepared-v1',operation_id=helper.fingerprint(c['binding']),
            unit_sha256=self.request['unit_sha256'],packet_sha256=self.request['packet_sha256'],
            source_sha256=helper.fingerprint(self.source),integration_binding=c['binding'],closure_sha256='d'*64,
            host_confirmation_sha256='e'*64)
        async def transport(request):
            self.assertEqual(request,self.request);return helper.wire(reply)
        with patch.object(runtime,'fixed_invocation_wire',side_effect=transport):
            selection=asyncio.run(runtime.produce_native_publication(self.current,self.issue,self.packet))
        self.assertEqual(set(selection),{'binding','packet','context'})
        self.assertEqual(selection['context']['pending_unit_review']['publisher_review_binding'],c['binding'])
        self.assertEqual(selection['context']['native_runtime'],str(self.f.runtime))

    def test_generic_python_profile_and_dynamic_template_are_policy_bound(self):
        c=self.qualify()['config'];b=c['binding'];s=c['snapshot'];a=c['integration_admission']
        grant=copy.deepcopy(c)
        grant['native_policy']['profiles']['delivery-unit-focused']['allowed_paths'].append('docs/development/project-aware-intake.md')
        helper.native_policy(grant)
        grant['native_policy']['profiles']['delivery-unit-focused']['allowed_paths'].append('docs/development/foreign.md')
        with self.assertRaises(helper.InvocationHold):helper.native_policy(grant)
        # Codec association only: the existing profile executor and original
        # reviewer independently qualify the actual generic source in122/129.
        outputs={'tools/delivery/stokowski_adapter.py':'a'*64}
        b['outputs']=outputs;s['validation']['outputs']=outputs;s['review']['outputs']=outputs
        s['review']['evidence_sha256']=helper.fingerprint({k:v for k,v in s['review'].items() if k!='evidence_sha256'})
        a['native_origin'].update(profile='delivery-unit-focused',outputs=outputs)
        b['publication']['qualification_sha256']=helper.fingerprint(s)
        a['binding_sha256']=helper.fingerprint(b)
        installer._integration_metadata(c)
        for change in (
            lambda v:v.pop('native_policy'),
            lambda v:v['native_policy'].update(automatic_integration_enabled=False),
            lambda v:v['integration_admission'].update(permission_sha256='0'*64),
            lambda v:v['native_policy']['profiles']['delivery-unit-focused'].update(allowed_paths=['tools/delivery/foreign.py'])):
            bad=copy.deepcopy(c);change(bad)
            with self.subTest(change=change),self.assertRaises((installer.InstallError,helper.InvocationHold)):
                installer._integration_metadata(bad)
        path=self.f.root/'generic.json';path.write_text(json.dumps(c))
        script="""import fs from 'node:fs';import assert from 'node:assert/strict';
import {validateConfig,selectNativeConfig,fingerprint,qualifyNativePolicy} from './tools/delivery/github-app-publisher.mjs';
const c=JSON.parse(fs.readFileSync(process.argv[1]));c.workspace='/var/lib/offmenu-publisher/integration/transaction-'+fingerprint(c.binding);
const scoped=structuredClone(c);scoped.native_policy.profiles['delivery-unit-focused'].allowed_paths.push('docs/development/project-aware-intake.md');
qualifyNativePolicy(scoped);scoped.native_policy.profiles['delivery-unit-focused'].allowed_paths.push('docs/development/foreign.md');
assert.throws(()=>qualifyNativePolicy(scoped));
const who={uid:984,euid:984,gid:976,egid:976};validateConfig(c,who);
const base=structuredClone(c);base.binding.issue_id='12345678-1234-1234-1234-123456789abc';
const n=c.snapshot.native_runtime,request={version:1,mode:'observe',operation_id:fingerprint(c.binding),
issue_id:n.issue_id,project_id:n.project_id,owner:n.owner,unit_sha256:n.unit_sha256,packet_sha256:n.packet_sha256,
source_sha256:fingerprint(n.source)};
assert.equal(selectNativeConfig(base,request,{readAdmission:()=>c}),c);
for(const change of [v=>{v.appId=1},v=>{v.workspace='/tmp/caller'},v=>{v.codePins={}},
v=>{v.native_policy.owner='foreign'},v=>{v.integration_admission.permission_sha256='0'.repeat(64)}]) {
const bad=structuredClone(c);change(bad);assert.throws(()=>selectNativeConfig(base,request,{readAdmission:()=>bad}));}
"""
        result=subprocess.run(['/usr/bin/node','--input-type=module','-e',script,str(path)],cwd=ROOT,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr.decode())


if __name__=='__main__':unittest.main()
