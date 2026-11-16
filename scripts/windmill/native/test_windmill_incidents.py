import copy
import unittest
from windmill_incidents import record_incident, IncidentError

class Response:
    def __init__(self, status, data=None): self.status_code, self.data = status, data
    def json(self): return self.data

class Client:
    def __init__(self): self.items = {}; self.posts = []; self.race = False
    def get(self, url, **kwargs):
        path = url.removeprefix('/w/offmenu/resources/get/')
        return Response(200, copy.deepcopy(self.items[path])) if path in self.items else Response(404)
    def post(self, url, json, **kwargs):
        self.posts.append((url, copy.deepcopy(json)))
        assert url == '/w/offmenu/resources/create'
        path = json['path']
        if path in self.items: return Response(409)
        self.items[path] = dict(json, workspace_id='offmenu', created_by='admin', extra_perms={})
        return Response(409 if self.race else 201)

class Tests(unittest.TestCase):
    def record(self, c, **kwargs):
        return record_incident('testjob-1', 'run', 'BUSINESS_FAILED', 'u/admin/foo_jobs_20261027', client=c, **kwargs)
    def test_idempotency_and_no_aggregate_write(self):
        c=Client(); a=self.record(c); old=copy.deepcopy(c.items); b=self.record(c)
        self.assertTrue(a['created']); self.assertFalse(b['created']); self.assertEqual(c.items,old)
        self.assertEqual(a['resource_path'],b['resource_path']); self.assertEqual(len(c.posts),1)
        self.assertNotEqual(a['resource_path'],'u/admin/offmenu_platform')
    def test_race_is_reconciled_without_update(self):
        c=Client(); c.race=True; self.assertTrue(self.record(c)['recorded']); self.assertEqual(len(c.posts),1)
    def test_shared_existing_resource_refused(self):
        c=Client(); a=self.record(c); c.items[a['resource_path']]['extra_perms']={'g/all':False}
        with self.assertRaisesRegex(IncidentError,'OWNER_MISMATCH'): self.record(c)
        self.assertEqual(len(c.posts),1)
    def test_malformed_existing_resource_refused(self):
        c=Client(); a=self.record(c); c.items[a['resource_path']]['value']['raw_log']='secret'
        with self.assertRaisesRegex(IncidentError,'SCHEMA_INVALID'): self.record(c)
    def test_failure_messages_do_not_leak(self):
        class Bad(Client):
            def get(self,*a,**kw): raise RuntimeError('RAW_SECRET_SENTINEL')
        with self.assertRaises(IncidentError) as e: self.record(Bad())
        self.assertNotIn('RAW_SECRET',str(e.exception))
    def test_sdk_initialization_does_not_leak(self):
        from unittest.mock import patch
        with patch('windmill_incidents._incident_sdk', side_effect=RuntimeError('RAW_SDK_SECRET')):
            with self.assertRaisesRegex(IncidentError, 'PERSISTENCE_UNAVAILABLE') as e:
                self.record(None)
            self.assertNotIn('RAW_SDK',str(e.exception))
    def test_owner_identity_and_exact_scheduled_context(self):
        import os,sys,types
        from unittest.mock import patch
        from windmill_incidents import _incident_sdk
        sdk=types.SimpleNamespace(Windmill=lambda: "safe-client")
        base={"WM_WORKSPACE":"offmenu","WM_USERNAME":"admin","WM_PERMISSIONED_AS":"u/admin"}
        with patch.dict(sys.modules,{"wmill":sdk}),patch.dict(os.environ,base,clear=True):
            self.assertEqual(_incident_sdk(),"safe-client")
            for path in ("u/admin/offmenu_platform_health_15m","u/admin/offmenu_platform_verify_daily"):
                os.environ.update(WM_USERNAME="schedule-"+path.replace("/","-"),WM_SCHEDULE_PATH=path,WM_JOB_PATH="u/admin/offmenu_platform_check")
                self.assertEqual(_incident_sdk(),"safe-client")
            os.environ["WM_PERMISSIONED_AS"]="u/other"
            with self.assertRaisesRegex(IncidentError,"OWNER_REQUIRED"):_incident_sdk()
            os.environ["WM_PERMISSIONED_AS"]="u/admin";os.environ["WM_SCHEDULE_PATH"]="u/admin/unreviewed"
            with self.assertRaisesRegex(IncidentError,"OWNER_REQUIRED"):_incident_sdk()
            os.environ["WM_USERNAME"]="admin";os.environ.pop("WM_PERMISSIONED_AS")
            with self.assertRaisesRegex(IncidentError,"OWNER_REQUIRED"):_incident_sdk()
    def test_permission_denial_no_retry(self):
        class Denied(Client):
            def get(self,*a,**kw): return Response(403)
        c=Denied()
        with self.assertRaisesRegex(IncidentError,'READ_REFUSED'): self.record(c)
        self.assertEqual(c.posts,[])
    def test_only_allowlisted_fields_persisted(self):
        c=Client(); a=self.record(c); v=c.items[a['resource_path']]['value']
        self.assertNotIn('source_path',v); self.assertNotIn('command',v); self.assertNotIn('error',v)
        self.assertEqual(v['severity'],'error'); self.assertFalse(v['needs_reconciliation'])
    def test_unknown_code_input_and_test_mislabel_refused(self):
        c=Client()
        with self.assertRaises(IncidentError): record_incident('x','run','raw exception','u/admin/foo_jobs_20261027',client=c)
        with self.assertRaises(IncidentError): self.record(c,test=True)
        self.assertEqual(c.posts,[])
    def test_separate_jobs_and_codes_have_separate_records(self):
        c=Client(); a=self.record(c)
        b=record_incident('testjob-1','run','OUTCOME_UNKNOWN','u/admin/foo_jobs_20261027',client=c)
        d=record_incident('testjob-2','run','BUSINESS_FAILED','u/admin/foo_jobs_20261027',client=c)
        self.assertEqual(len({a['resource_path'],b['resource_path'],d['resource_path']}),3)
        self.assertTrue(b['needs_reconciliation'])

if __name__ == '__main__': unittest.main()
