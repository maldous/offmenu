"""Honest execution identity and finite, read-only refill observations."""
import asyncio
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parents[2]/'tools/delivery'
sys.path.insert(0,str(TOOLS))
import stokowski_worker as worker
import stokowski_stage as stage
import stokowski_refill as refill
import test_stokowski_worker_regressions as regressions
import test_reviewed_extraction as extraction
from symphony_capacity import Pool


REAL_SUPERVISE = worker.supervise


class ExecutionMetadataTests(unittest.TestCase):
    # Reuse the offline Git/pool fixture while keeping its cases in their suite.
    issue = regressions.WorkerRegressions.issue
    setUp = regressions.WorkerRegressions.setUp
    git = regressions.WorkerRegressions.git
    make_runtime = regressions.WorkerRegressions.make_runtime
    lease = regressions.WorkerRegressions.lease
    directory = regressions.WorkerRegressions.directory
    completed_process = staticmethod(regressions.WorkerRegressions.completed_process)

    def test_requested_identity_is_separate_from_unknown_observed_identity(self):
        with patch.object(worker.os,'sched_setaffinity'):
            result = worker.execute(self.runtime,self.issue,self.request)
        self.assertEqual(result['requested_model'],'gpt-6.1-sol')
        self.assertEqual(result['requested_effort'],'medium')
        self.assertEqual(result['provider_route'],'codex-chatgpt')
        self.assertIsNone(result['resolved_model'])
        self.assertEqual(result['resolution_status'],'unobserved')
        self.assertEqual(result['parent_runtime'],str(self.runtime.resolve()))
        self.assertEqual(result['attempt'],self.issue)
        self.assertEqual(result['lease'],self.lease())
        self.assertEqual(result['declared_resources'],self.manifest['tasks'][self.issue]['resources'])
        self.assertIsNone(result['observed_resources'])
        intent = json.loads((self.directory()/'intent.json').read_text())
        self.assertEqual(result['parent_binding'],intent['binding'])

    def test_only_explicit_event_model_identity_is_observed(self):
        path = self.root/'events.jsonl'
        path.write_text(json.dumps({'type':'item.completed','model':'not-a-model-observation'})+'\n'+
                        json.dumps({'type':'turn.completed','usage':{}})+'\n')
        self.assertEqual(worker.summarize_events(path)['resolution_status'],'unobserved')
        path.write_text(json.dumps({'type':'turn.completed','model':'explicit-event-model','usage':{}})+'\n')
        observed = worker.summarize_events(path)
        self.assertEqual(observed['resolved_model'],'explicit-event-model')
        self.assertEqual(observed['resolution_status'],'observed')

    def test_sampled_resources_are_separate_from_declaration(self):
        directory = self.root/'observed/attempts/UIF-92'
        directory.mkdir(parents=True)
        with patch.object(worker,'capacity_usage',return_value={'processes':2,'rss_bytes':300}):
            result = REAL_SUPERVISE([sys.executable,'-c','import time; time.sleep(.08)'],
                '',self.root,worker.child_environment(os.environ),directory,5,{'memory_bytes':1024},64)
        self.assertEqual(result['status'],'succeeded')
        self.assertEqual(result['observed_resources']['peak_processes'],2)
        self.assertEqual(result['observed_resources']['peak_rss_bytes'],300)
        self.assertEqual(result['observed_resources']['cpu_affinity'],sorted(os.sched_getaffinity(0)))


class RefillTests(unittest.TestCase):
    def setUp(self):
        self.policy = json.loads((TOOLS/'capacity-policy.json').read_text())
        self.manifest = {'tasks':{'UIF-1':{'allowed_paths':['src/one'],
            'resources':{'cpu_millis':1000,'memory_bytes':1024,'io_slots':1,'output_bytes':0}}}}
        self.provider = {'route':'codex-chatgpt','available':True,'checked_at':1000,'session_ceiling':8}
        self.host = dict(cpu_millis=32000,available_memory_bytes=64*1024**3,available_disk_bytes=200*1024**3)
        self.rows = []

    def decide(self,**kwargs):
        with patch.object(Pool,'admit',side_effect=AssertionError('refill must not admit')):
            return refill.ready_refill(self.manifest,self.provider,self.rows,self.host,self.policy,now=1000,**kwargs)

    def test_one_provisional_disjoint_ready_decision_never_dispatches(self):
        result = self.decide()
        self.assertEqual(result['status'],'ready-refill')
        self.assertFalse(result['dispatch'])
        self.assertTrue(result['provisional'])
        self.assertEqual(result['write_roots'],['src/one'])
        self.assertEqual(self.decide(retained={'UIF-1'})['status'],'no-ready-work')
        self.assertEqual(self.decide(cancelled=True)['status'],'no-ready-work')

    def test_missing_stale_unavailable_future_provider_explicitly_defers(self):
        for provider in (None,{},dict(self.provider,checked_at=0),dict(self.provider,available=False),
                         dict(self.provider,checked_at=1010),dict(self.provider,checked_at=float('nan'))):
            self.provider = provider
            self.assertEqual(self.decide()['status'],'deferred')

    def test_overlap_cancellation_uncertainty_and_host_pressure_preserve_ownership(self):
        row = {'id':'other-runtime','status':'running','binding':{'write_roots':['src'],
            'resources':dict(self.manifest['tasks']['UIF-1']['resources'])}}
        for status in ('running','cancel_requested','uncertain'):
            self.rows = [dict(row,status=status)]
            before = copy.deepcopy(self.rows)
            self.assertEqual(self.decide()['status'],'no-ready-work')
            self.assertEqual(self.rows,before)
        self.rows = []
        self.host['available_memory_bytes'] = 1
        self.assertEqual(self.decide()['status'],'no-ready-work')

    def test_terminal_projection_caches_one_decision_across_reopen(self):
        fixture = extraction.ExtractionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        key = fixture.bind()
        from test_stokowski_operations import FaultedWindmill
        remote = FaultedWindmill()
        from unittest.mock import AsyncMock
        remote.close = AsyncMock()
        journal = stage.Journal(fixture.runtime/'operations')
        state = asyncio.run(journal.tick(key,remote))
        remote.complete(state['windmill_job_id'],fixture.spec)
        with patch.object(refill,'observe_refill',return_value={'status':'no-ready-work','dispatch':False}) as observe:
            first = asyncio.run(stage.tick(fixture.runtime,remote))
            second = asyncio.run(stage.tick(fixture.runtime,remote))
        self.assertEqual(first,second)
        observe.assert_called_once()
        self.assertEqual(len(remote.submissions),1)
