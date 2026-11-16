import copy
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
import types
sys.modules.setdefault('paramiko',types.ModuleType('paramiko'))
sys.modules.setdefault('wmill',types.ModuleType('wmill'))
import platform_check as host
import windmill_platform_check as client

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
        (self.root/'jobs').mkdir();(self.root/'locks').mkdir()
    def tearDown(self):self.t.cleanup()
    def job(self,name,state):
        p=self.root/'jobs'/name;p.mkdir()
        (p/'receipt.json').write_text(json.dumps(dict(job_id=name,status=state,child_tree_gone=True,heartbeat_at=time.time())))
    def test_highest_marker_included(self):
        self.job('slot63','running')
        (self.root/'locks/execution-slot-63.inflight.json').write_text(json.dumps({'job_id':'slot63'}))
        report=host.audit('health',root=self.root)
        self.assertEqual(report['counts']['markers_checked'],1)
        self.assertTrue(any(f.get('job_id')=='slot63' and f['code']=='ACTIVE_INFLIGHT_JOB' for f in report['findings']))
        self.assertEqual(client._check_receipt(report,'health',100),report)
    def test_all64_metadata_markers_plus100_selected_findings(self):
        # Metadata fixtures only, not64running processes or a load test.
        for n in range(64):
            name='active'+str(n);self.job(name,'running')
            (self.root/('locks/execution-slot-%s.inflight.json'%n)).write_text(json.dumps({'job_id':name}))
        for n in range(100):self.job('oldfailure'+str(n),'failed')
        report=host.audit('health',root=self.root)
        self.assertEqual(report['counts']['markers_checked'],64)
        self.assertEqual(report['counts']['jobs_checked'],100)
        self.assertEqual(len(report['findings']),164)
        self.assertEqual(client._check_receipt(report,'health',100),report)
        invalid=copy.deepcopy(report);invalid['counts']['markers_checked']=65
        with self.assertRaises(client.PlatformCheckFailure):client._check_receipt(invalid,'health',100)
        invalid=copy.deepcopy(report);invalid['findings']=[{'code':'ACTIVE_INFLIGHT_JOB','severity':'info'}]*173
        with self.assertRaises(client.PlatformCheckFailure):client._check_receipt(invalid,'health',100)
    def test_slot63_stale_or_malformed_fails_closed(self):
        path=self.root/'locks/execution-slot-63.inflight.json';path.write_text('{}')
        report=host.audit('health',root=self.root)
        self.assertFalse(report['ok']);self.assertEqual(report['counts']['markers_checked'],1)
        self.assertIn('INVALID_INFLIGHT_MARKER',[f['code'] for f in report['findings']])
        self.assertEqual(client._check_receipt(report,'health',100),report)

if __name__=='__main__':unittest.main()
