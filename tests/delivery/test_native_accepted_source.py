"""Publisher canonical facts from a real private Controller checkpoint."""
import asyncio
import copy
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4

import native_publisher_invocation as helper
import native_harness_runtime as runtime
import stokowski_prepare as preparation
from offmenu.delivery.integration import Controller, _publisher_transaction_request
import test_native_publication_producer as producer
from test_native_publisher_invocation import terminal


class AcceptedSourceTests(unittest.TestCase):
    def setUp(self):
        old=os.umask(0o077);self.addCleanup(os.umask,old)
        f=producer.NativePublicationProducerTests(methodName='runTest');f.setUp();self.addCleanup(f.doCleanups)
        self.fixture=f
        self.descriptor=dict(repository='maldous/offmenu',branch='develop',origin='git@github.com:maldous/offmenu.git',
            source_repository='/home/user/src/offmenu',seed=dict(head=f.spec['base'],
                tree=f.f.git(f.f.control,'rev-parse',f.spec['base']+'^{tree}')),
            accepted_facts_path=str(helper.ACCEPTED/'latest.json'))
        f.policy['project_source']=self.descriptor
        self.config=f.qualify()['config'];self.root=f.root;self.key=helper.fingerprint(self.config['binding'])
        self.directory=self.root/('transaction-'+self.key)
        _publisher_transaction_request(self.config,{'op':'prepare'},self.root)
        self.controller=Controller(self.directory,self.config['binding'],self.root)
        for i,action in enumerate(self.config['plan']['operations']):
            _publisher_transaction_request(self.config,dict(op='intent',index=i,action=action),self.root)
            _publisher_transaction_request(self.config,dict(op='consume',intent=action),self.root)
            if action['kind']=='create-pr':
                _publisher_transaction_request(self.config,dict(op='freeze-pr',index=i,action=action,number=204),self.root)
            _publisher_transaction_request(self.config,dict(op='reconcile',index=i,action=action,
                canonical=helper.fingerprint(action),final=i==len(self.config['plan']['operations'])-1),self.root)
        b=self.config['binding']
        self.observation=dict(self.config['snapshot'],observed_at=time.time(),automatic_integration_enabled=True,
            github=dict(repository='maldous/offmenu',number=204,state='open',merged=False,head=b['head'],base=b['base'],
                head_branch=b['head_branch'],base_branch='develop',mergeable=True,draft=False))
        self.assertEqual(self.controller.run(self.observation)['status'],'merge-intent')
        self.observation['github'].update(merged=True,merge_commit_sha='e'*40)
        self.observation.update(merge_commit=dict(sha='e'*40,tree=b['tree'],parents=[b['base'],b['head']]),
            develop_contains_merge=True)
        self.assertEqual(self.controller.run(self.observation)['status'],'merge-verified')
        n=self.config['snapshot']['native_runtime']
        self.inner=dict(version=1,mode='observe',operation_id=self.key,source_sha256=helper.fingerprint(n['source']),
            **{k:n[k] for k in ('issue_id','project_id','owner','unit_sha256','packet_sha256')})
        self.envelope=dict(version=1,mode='invoke',invocation_id=str(uuid4()),request=self.inner)
        proof=terminal(self.inner);proof['response']['status']='verified';proof['response_sha256']=helper.fingerprint(proof['response'])
        self.record=dict(version=1,kind='native-publisher-invocation-record-v1',intent=dict(operation_id=self.key,
            invocation_id=self.envelope['invocation_id'],request=self.inner,request_sha256=helper.fingerprint(self.inner),
            closure_sha256='f'*64,phase='integration',supervisor_pid=123,supervisor_starttime=1),terminal=proof)
        helper._write(self.directory/('native-invocation-'+self.envelope['invocation_id']+'.json'),self.record)
        self.value=helper._result(self.envelope,self.record)
        helper.validate_result(self.value,self.envelope,'f'*64)
        self.public=f.f.root/'accepted';self.public.mkdir(mode=0o755);self.public.chmod(0o755)

    def emit(self,*,write=True,value=None):
        return helper.publish_accepted_source(self.config,value or self.value,write=write,
            root=self.public,claim_root=self.root,uid=os.getuid())

    def test_canonical_fact_exact_retry_readonly_observe_and_public_custody(self):
        before={p:p.read_bytes() for p in (self.directory/'state.json',self.directory/'binding.json',
            self.directory/('native-invocation-'+self.envelope['invocation_id']+'.json'))}
        self.assertIsNone(self.emit(write=False));self.assertEqual(list(self.public.iterdir()),[])
        old=os.umask(0o077)
        try:facet=self.emit()
        finally:os.umask(old)
        fact=facet['fact'];path=Path(facet['reference']['path'])
        self.assertEqual(fact['helper_receipt']['sha256'],self.value['receipt']['sha256'])
        self.assertEqual(fact['head'],'e'*40);self.assertEqual(fact['parents'],[self.config['binding']['base'],self.config['binding']['head']])
        self.assertEqual(path.stat().st_mode&0o777,0o444);self.assertEqual(path.parent.stat().st_mode&0o777,0o755)
        raw=path.read_bytes();pointer=(self.public/'latest.json').read_bytes()
        self.assertEqual(self.emit(write=False),facet);self.assertEqual(self.emit(),facet)
        self.assertEqual(path.read_bytes(),raw);self.assertEqual((self.public/'latest.json').read_bytes(),pointer)
        for p,value in before.items():self.assertEqual(p.read_bytes(),value)
        self.assertEqual(helper.read_accepted_fact(facet['reference'],self.descriptor,
            root=self.public,claim_root=self.root,uid=os.getuid()),fact)
        with self.assertRaises(helper.InvocationHold):
            helper.read_accepted_fact(facet['reference'],self.descriptor,root=self.public,claim_root=self.root,uid=984)

    def test_unverified_or_wrong_canonical_parent_does_not_emit(self):
        self.observation['merge_commit']['parents']=['0'*40,self.config['binding']['head']]
        self.assertEqual(self.controller.run(self.observation)['status'],'repair-required')
        with self.assertRaisesRegex(helper.InvocationHold,'accepted_source_unverified'):self.emit()
        self.assertFalse((self.public/'latest.json').exists())

    def test_outer_facet_binds_metadata_and_preserves_legacy_response(self):
        facet=self.emit();fact=copy.deepcopy(facet['fact'])
        fact['helper_receipt']['path']=str(helper.CLAIM/('transaction-'+self.key)/
            ('native-invocation-'+self.envelope['invocation_id']+'.json'))
        public=dict(reference=dict(path=str(helper.ACCEPTED/'by-operation'/(self.key+'.json')),
            sha256=helper.sha(helper.wire(fact))),fact=fact)
        value=dict(self.value,accepted_source=public)
        self.assertEqual(helper.validate_result(value,self.envelope,'f'*64),value)
        bad=copy.deepcopy(value);bad['accepted_source']['fact']['packet_sha256']='0'*64
        bad['accepted_source']['reference']['sha256']=helper.sha(helper.wire(bad['accepted_source']['fact']))
        with self.assertRaises(helper.InvocationHold):helper.validate_result(bad,self.envelope,'f'*64)
        host=helper._Host()
        self.assertIs(host.accepted_source(self.value,write=True),self.value)
        self.assertNotIn('accepted_source',self.value)

    def test_fact_hash_chain_and_unit_corruption_hold(self):
        facet=self.emit();path=Path(facet['reference']['path']);original=path.read_bytes()
        changed=copy.deepcopy(facet['fact']);changed['previous']['head']='0'*40
        path.chmod(0o600);path.write_bytes(helper.wire(changed));path.chmod(0o444)
        with self.assertRaises(helper.InvocationHold):
            helper.read_accepted_fact(dict(path=str(path),sha256=helper.sha(path.read_bytes())),self.descriptor,
                root=self.public,claim_root=self.root,uid=os.getuid())
        path.chmod(0o600);path.write_bytes(original);path.chmod(0o444)
        with self.assertRaises(helper.InvocationHold):
            helper.read_accepted_fact(dict(facet['reference'],sha256='0'*64),self.descriptor,
                root=self.public,claim_root=self.root,uid=os.getuid())

    def test_fixed_runtime_reader_correlates_selection_and_seed(self):
        facet=self.emit();c=self.fixture.current;issue=self.fixture.issue
        n=self.config['snapshot']['native_runtime'];b=self.config['binding']
        binding=runtime.OwnerBinding(issue.id,n['project_id'],n['owner'],n['packet_sha256'],self.key,'integration',n['unit_sha256'])
        from dataclasses import asdict
        selection=dict(binding=asdict(binding),packet=dict(path=str(self.fixture.f.runtime/'native-publication-packet.json'),
            sha256=producer.adapter.file_sha(self.fixture.f.runtime/'native-publication-packet.json')),
            context=dict(pending_unit_review=dict(publisher_review_binding=b)))
        c.config['source_sha256']={'tools/delivery/native_publisher_invocation.py':producer.adapter.file_sha(helper.__file__),
            'tools/delivery/stokowski_prepare.py':producer.adapter.file_sha(preparation.__file__)}
        # Source/owner selection are existing qualified boundaries. Public-file
        # custody is exercised separately with the current test uid above.
        async def call():return await runtime.verified_canonical_source(c,issue,binding)
        original_read=helper._read
        def read(path,uid,mode,*args):
            if str(path).startswith(str(helper.ACCEPTED)):
                return original_read(Path(str(path).replace(str(helper.ACCEPTED),str(self.public),1)),os.getuid(),mode,*args)
            return original_read(path,uid,mode,*args)
        with patch.object(c,'_native_harness_selection',return_value=selection), \
             patch.object(preparation,'owner_intake_policy',return_value={'project_source':self.descriptor},create=True), \
             patch.object(helper,'_read',side_effect=read),patch.object(helper,'read_accepted_fact',return_value=facet['fact']):
            result=asyncio.run(call());self.assertEqual(result['fact']['head'],'e'*40)
            self.assertEqual(result['fact']['pr_url'],'https://github.com/maldous/offmenu/pull/204')
            bad=copy.deepcopy(facet['fact']);bad['packet_sha256']='0'*64
            with patch.object(helper,'read_accepted_fact',return_value=bad),self.assertRaises(runtime.RuntimeHold):asyncio.run(call())


if __name__=='__main__':unittest.main()
