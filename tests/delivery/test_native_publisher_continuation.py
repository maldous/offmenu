"""Finite same-operation source continuity; disposable local evidence only."""
import asyncio
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/delivery'),str(Path(__file__).parent)]
import native_harness_runtime as runtime
import native_publisher_invocation as helper
import stokowski_adapter as adapter
from test_native_publisher_invocation import SyntheticHost,terminal


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='publisher-continuation-');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name).resolve();self.host=SyntheticHost(self.root);self.host.prepare()
        self.config=self.host.config
        self.config['binding']['project_id']=adapter.PROJECT
        self.config['snapshot']['native_runtime']['project_id']=adapter.PROJECT
        self.unit={'synthetic':'original-unit'}
        self.packet={'handoff':{'source':self.config['snapshot']['native_runtime']['source']}}
        n=self.config['snapshot']['native_runtime'];n['unit_sha256']=runtime.fingerprint(self.unit)
        n['packet_sha256']=runtime.fingerprint(self.packet)
        self.binding=runtime.OwnerBinding(n['issue_id'],n['project_id'],n['owner'],n['packet_sha256'],
            helper.fingerprint(self.config['binding']),'integration',n['unit_sha256'])
        self.oldcap=dict(version=1,closure_sha256='1'*64,host_confirmation_sha256='2'*64)
        self.newcap=dict(version=1,closure_sha256='3'*64,host_confirmation_sha256='4'*64)
        self.old=dict(version=1,binding=asdict(self.binding),selection_sha256='5'*64,
                      capability=self.oldcap,invocations=[])
        # Use the actual receipt publisher/wire format, with explicitly
        # synthetic terminal proofs. Existing lifecycle regressions use real OS proof.
        for failed in (True,False):
            envelope=dict(version=1,mode='invoke',invocation_id=str(uuid4()),
                request=runtime.publisher_request(self.binding,self.packet,'observe'))
            proof=terminal(envelope['request'])
            if failed:proof.update(outcome='publisher_error',response=None,response_sha256=None)
            with patch.object(helper,'_supervise',return_value=proof):
                value=helper._invoke(helper.wire(envelope),self.host)
            self.old['invocations'].append(dict(envelope=envelope,last_request=envelope,status='complete',result=value))
        self.current=adapter.CurrentWork.__new__(adapter.CurrentWork)
        c=self.current;c.root=self.root;c.runtime=self.root;c.state_path=self.root/'current-owner.json'
        c.read_only=False;c.stopping=False;c.owner_custody={'source_root':str(ROOT)};c._native_harness_refill=None
        c.config={'owner':self.binding.owner,'native_harness_boundaries':{},'source_sha256':{
            'tools/delivery/native_publisher_invocation.py':hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest()}}
        c.entries={'UIF-96':{'issue_id':self.binding.issue_id}}
        c.state={'tasks':{'UIF-96':{'native_harness':{'selection_sha256':self.old['selection_sha256']}}},
            runtime.INVOCATIONS:{self.binding.operation_id:copy.deepcopy(self.old)}}
        self.grant=self.descriptor(self.old)
        self.selection=dict(binding=asdict(self.binding),packet=self.pin('packet.json',self.packet),
            context=dict(reviewed_runtime=str(self.root),unit_review=self.pin('review.json',{}),
                publisher_invocation=self.newcap,publisher_continuation=self.grant))
        c.config['native_harness_boundaries']['UIF-96']=self.pin('selection.json',self.selection)
        self.calls=[]

    def pin(self,name,value):
        p=self.root/name;p.write_text(json.dumps(value))
        return dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest())

    def descriptor(self,record):
        claim=dict(binding_sha256=self.binding.operation_id,
            directory=str(helper.CLAIM/('transaction-'+self.binding.operation_id)),owner=self.binding.owner)
        return dict(version=1,operation_id=self.binding.operation_id,unit_sha256=self.binding.unit_sha256,
            packet_sha256=self.binding.packet_sha256,claim_sha256=helper.fingerprint(claim),
            previous_selection_sha256=record['selection_sha256'],previous_capability=record['capability'],
            previous_record_sha256=helper.fingerprint(record),receipts=[dict(
                invocation_id=v['envelope']['invocation_id'],closure_sha256=record['capability']['closure_sha256'],
                receipt_sha256=v['result']['receipt']['sha256']) for v in record['invocations']])

    def upgraded(self):
        return runtime.invocation_continuation_record(self.current,self.binding,self.packet,self.selection)

    async def transport(self,envelope):
        self.calls.append(copy.deepcopy(envelope))
        self.host.continuation=self.grant
        original=self.host.admit
        def admit(inner):
            directory,phase,_=original(inner);return directory,phase,self.newcap['closure_sha256']
        with patch.object(self.host,'admit',side_effect=admit),patch.object(helper,'_supervise',
                return_value=terminal(envelope['request'])):
            value=helper._invoke(helper.wire(envelope),self.host)
        return helper.wire(value)

    def test_normal_consumer_atomic_history_and_new_readonly_before_step(self):
        old=copy.deepcopy(self.old)
        oldbytes={p:p.read_bytes() for p in self.host.directory.glob('native-invocation-*.json')}
        async def consume(current,issue,*,binding,adapters):
            saved=json.loads(current.state_path.read_text())
            record=saved[runtime.INVOCATIONS][binding.operation_id]
            self.assertEqual(record['history'],[old])
            self.assertEqual(saved['tasks']['UIF-96']['native_harness']['selection_sha256'],runtime.fingerprint(self.selection))
            self.assertTrue(await adapters.authorize(current,issue,binding))
            value=await runtime.invocation_transaction(current,binding,self.packet,self.selection,'observe',[0],lambda *_:True)
            return dict(status=value['status'],operation_id=binding.operation_id)
        module=SimpleNamespace(OwnerBinding=runtime.OwnerBinding,OwnerAdapters=runtime.OwnerAdapters,
            fingerprint=runtime.fingerprint,INVOCATIONS=runtime.INVOCATIONS,
            invocation_continuation_record=runtime.invocation_continuation_record,consume_boundary=consume)
        admitted=runtime.OwnerAdapters(lambda *_:True,lambda _:self.packet,lambda _:None,
            lambda *_:None,lambda _:None,lambda *_:None)
        with patch.object(adapter,'SOURCE',ROOT),patch.object(self.current,'_native_harness_module',return_value=module), \
             patch.object(self.current,'guard'),patch.object(self.current,'context'), \
             patch.object(self.current,'gate_binding',return_value=self.unit), \
             patch.object(runtime,'fixed_invocation_wire',side_effect=self.transport):
            asyncio.run(self.current.continue_native_harness(lambda *a,**kw:admitted))
            self.assertEqual(len(self.calls),1)
            self.assertEqual(self.calls[0]['request']['mode'],'observe')
            # A restart validates the retained historical epoch at its old pin.
            self.current.state=json.loads(self.current.state_path.read_text())
            asyncio.run(self.current.continue_native_harness(lambda *a,**kw:admitted))
            self.assertEqual(len(self.calls),1)
            asyncio.run(runtime.invocation_transaction(self.current,self.binding,self.packet,
                self.selection,'step',[0],lambda *_:True))
        self.assertEqual(len(self.calls),2)
        record=self.current.state[runtime.INVOCATIONS][self.binding.operation_id]
        self.assertEqual(record['history'],[old])
        for v in record['invocations']:
            self.assertEqual(v['result']['receipt']['body']['intent']['closure_sha256'],'3'*64)
        for p,raw in oldbytes.items():self.assertEqual(p.read_bytes(),raw)

    def test_record_claim_receipt_and_unresolved_grants_refuse(self):
        for key in ('previous_record_sha256','previous_selection_sha256','claim_sha256','unit_sha256'):
            selected=copy.deepcopy(self.selection);selected['context']['publisher_continuation'][key]='0'*64
            with self.subTest(key=key),self.assertRaises((runtime.RuntimeHold,helper.InvocationHold)):
                runtime.invocation_continuation_record(self.current,self.binding,self.packet,selected)
        for change in ('unknown','pending_response','contradiction','missing_receipt','wrong_receipt'):
            record=copy.deepcopy(self.old);old=record['invocations'][-1]
            if change=='unknown':old['status']='unknown'
            elif change=='missing_receipt':old['result']=None
            elif change=='pending_response':
                result=old['result'];result['response']['status']='unknown'
                terminal=result['receipt']['body']['terminal'];terminal['response']=copy.deepcopy(result['response'])
                terminal['response_sha256']=helper.fingerprint(result['response'])
                result['receipt']['sha256']=helper.sha(helper.wire(result['receipt']['body']))
            elif change=='contradiction':
                old['result']['receipt']['body']['terminal']['waitpid_echild']=False
                old['result']['receipt']['sha256']=helper.sha(helper.wire(old['result']['receipt']['body']))
            self.current.state[runtime.INVOCATIONS][self.binding.operation_id]=record
            grant=copy.deepcopy(self.grant);grant['previous_record_sha256']=helper.fingerprint(record)
            if change=='wrong_receipt':grant['receipts'][0]['receipt_sha256']='0'*64
            selected=copy.deepcopy(self.selection);selected['context']['publisher_continuation']=grant
            with self.subTest(change=change),self.assertRaises((runtime.RuntimeHold,helper.InvocationHold)):
                runtime.invocation_continuation_record(self.current,self.binding,self.packet,selected)

    def test_old_ready_cannot_step_until_new_observation_and_helper_requires_real_old_files(self):
        self.current.state[runtime.INVOCATIONS][self.binding.operation_id]=self.upgraded()
        with patch.object(runtime,'fixed_invocation_wire',side_effect=AssertionError('no dispatch')):
            with self.assertRaisesRegex(runtime.RuntimeHold,'publisher_readiness_required'):
                asyncio.run(runtime.invocation_transaction(self.current,self.binding,self.packet,
                    self.selection,'step',[0],lambda *_:True))
        self.host.continuation=self.grant
        envelope=dict(version=1,mode='invoke',invocation_id=str(uuid4()),
            request=runtime.publisher_request(self.binding,self.packet,'observe'))
        # Deleting even a failed-read original proof cannot be papered over by
        # a coordinator cached receipt or same-closure-looking fake new proof.
        path=self.host.directory/('native-invocation-'+self.old['invocations'][0]['envelope']['invocation_id']+'.json')
        path.unlink()
        original=self.host.admit
        def admit(inner):
            d,phase,_=original(inner);return d,phase,'3'*64
        with patch.object(self.host,'admit',side_effect=admit),patch.object(helper,'_supervise',side_effect=AssertionError('no child')):
            with self.assertRaisesRegex(helper.InvocationHold,'continuation_receipt_missing'):
                helper._invoke(helper.wire(envelope),self.host)
