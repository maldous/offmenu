"""Finite owner-selected contexts and trusted adapter callback preservation."""
import asyncio
import copy
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'src'),str(ROOT/'tools/delivery')]
import stokowski_adapter as adapter
import native_harness_runtime as runtime
from native_harness_contract import fingerprint
from symphony_capacity import AdmissionError


class HarnessContextTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        root=Path(self.temp.name).resolve()
        self.current=adapter.CurrentWork.__new__(adapter.CurrentWork)
        c=self.current;c.root=root;c.runtime=root;c.state_path=root/'state.json'
        c.owner_custody={'source_root':'synthetic-protected-source'}
        c.read_only=False;c.stopping=False;c._native_harness_refill=None
        c.config={'owner':'synthetic-owner','native_harness_boundaries':{}}
        c.entries={'UIF-96':{'issue_id':'00000000-0000-4000-8000-000000000096'}}
        c.state={'tasks':{'UIF-96':{}}}
        self.packet={'synthetic':'packet'};self.unit={'synthetic':'unit'}
        self.binding=dict(issue_id=c.entries['UIF-96']['issue_id'],project_id=c.routes[0]['project_id'],
            owner=c.config['owner'],packet_sha256=fingerprint(self.packet),operation_id='a'*64,
            phase='integration',unit_sha256=fingerprint(self.unit))
        self.review=self.pin('review.json',{'synthetic':'review'})
        self.context={'reviewed_runtime':str(root),'unit_review':self.review}
        self.packet_ref=self.pin('packet.json',self.packet)

    def pin(self,name,value):
        p=self.current.root/name;p.write_text(json.dumps(value))
        return {'path':str(p),'sha256':adapter.file_sha(p)}

    def select(self,context=None,phase='integration'):
        selection=dict(binding=dict(self.binding,phase=phase),packet=self.packet_ref,
            context=copy.deepcopy(self.context if context is None else context))
        ref=self.pin('selection.json',selection)
        self.current.config['native_harness_boundaries']['UIF-96']=ref
        return selection

    def test_exact_reviewed_context_only_integration_and_pins_required(self):
        expected=self.select()
        self.assertEqual(self.current._native_harness_selection('UIF-96'),expected)
        invocation=dict(version=1,closure_sha256='b'*64,host_confirmation_sha256='c'*64)
        expected=self.select(dict(self.context,publisher_invocation=invocation))
        self.assertEqual(self.current._native_harness_selection('UIF-96'),expected)
        alias=self.current.root/'alias';alias.symlink_to(self.current.root,target_is_directory=True)
        cases=[(self.context,'release'),(self.context,'linear'),({},'integration'),
            ({'reviewed_runtime':str(self.current.root)},'integration'),
            (dict(self.context,engine_task=self.review),'integration'),
            (dict(self.context,callback='arbitrary'),'integration'),
            (dict(self.context,reviewed_runtime=str(alias)),'integration'),
            (dict(self.context,reviewed_runtime=str(self.current.root/'missing')),'integration'),
            (dict(self.context,reviewed_runtime=str(self.current.root/'review.json')),'integration'),
            (dict(self.context,reviewed_runtime='/tmp'),'integration'),
            (dict(self.context,unit_review={'path':self.review['path'],'sha256':'0'*64}),'integration'),
            (dict(self.context,unit_review={'path':self.review['path']}),'integration')]
        for context,phase in cases:
            self.select(context,phase)
            with self.subTest(context=context,phase=phase),self.assertRaises(AdmissionError):
                self.current._native_harness_selection('UIF-96')
        self.select({},'linear')
        self.assertEqual(self.current._native_harness_selection('UIF-96')['context'],{})
        old=dict(engine_root=str(self.current.root),engine_task=self.pin('task.json',{}),unit_review=self.review)
        for phase in ('integration','release'):
            self.select(old,phase)
            self.assertEqual(self.current._native_harness_selection('UIF-96')['context'],old)

    def test_trusted_wrapper_preserves_admitted_last_callback(self):
        self.select()
        # Joint-runtime interface fixture only:129 owns the actual dataclass.
        @dataclass(frozen=True)
        class JointAdapters(runtime.OwnerAdapters):
            integration_acceptance: object = None
        callback=lambda binding: {'synthetic':'acceptance'}
        authorize=lambda *args:True
        admitted=JointAdapters(authorize,lambda b:self.packet,lambda b:None,
            lambda *a:None,lambda b:None,lambda *a:None,callback)
        seen=[]
        async def consume(current,issue,*,binding,adapters):
            seen.append(adapters.integration_acceptance)
            self.assertTrue(await adapters.authorize(current,issue,binding))
            self.assertEqual(await adapters.load(binding),self.packet)
            return {'status':'observed','operation_id':binding.operation_id}
        module=SimpleNamespace(OwnerBinding=runtime.OwnerBinding,OwnerAdapters=JointAdapters,
            fingerprint=fingerprint,consume_boundary=consume)
        with patch.object(self.current,'_native_harness_module',return_value=module), \
             patch.object(self.current,'guard') as guard,patch.object(self.current,'context'), \
             patch.object(self.current,'gate_binding',return_value=self.unit):
            asyncio.run(self.current.continue_native_harness(lambda *a,**kw:admitted))
            guard.assert_called()
        self.assertEqual(seen,[callback])
        self.assertEqual(self.current.state['tasks']['UIF-96']['native_harness']['status'],'observed')
