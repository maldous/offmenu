import copy
import os
import unittest
from pathlib import Path
from unittest.mock import patch
import schedule_receipt as m

class Response:
    def __init__(self,body,code=200):self.body,self.status_code=body,code
    def json(self):return self.body
class Client:
    def __init__(self):
        self.posts=[]
        self.schedules={p:dict(workspace_id='offmenu',path=p,edited_by='admin',extra_perms={},
            permissioned_as='u/admin',schedule=cron,timezone='Australia/Melbourne',
            script_path='u/admin/offmenu_platform_check',is_flow=False,
            args={'mode':mode,'max_items':100},cron_version='v2',enabled=False)
            for p,(cron,mode) in m.DEFINITIONS.items()}
    def get(self,path,**kw):
        if '/scripts/get/' in path:return Response(dict(path='u/admin/offmenu_platform_check',workspace_id='offmenu',created_by='admin',extra_perms={},content=Path(m.__file__).with_name('windmill_platform_check.py').read_text(),hash='1234567890abcdef'))
        if '/queue/' in path:return Response([])
        return Response(copy.deepcopy(self.schedules[path.split('/schedules/get/')[1]]))
    def post(self,path,json,**kw):
        self.posts.append((path,json));self.schedules[path.split('/setenabled/')[1]]['enabled']=json['enabled']
        return Response(None)
class Tests(unittest.TestCase):
    def setUp(self):
        self.env=patch.dict(os.environ,{'WM_WORKSPACE':'offmenu','WM_USERNAME':'admin'});self.env.start()
        self.addCleanup(self.env.stop)
        self.c=Client()
    def test_read_only_default(self):
        r=m.inspect_or_enable(client=self.c);self.assertEqual(self.c.posts,[]);self.assertEqual(r['activated'],[])
    def test_enable_exact_and_idempotent(self):
        r=m.inspect_or_enable(True,self.c);self.assertEqual(len(r['activated']),2)
        self.assertTrue(all(b=={'enabled':True} for _,b in self.c.posts))
        self.assertEqual(m.inspect_or_enable(True,self.c)['activated'],[]);self.assertEqual(len(self.c.posts),2)
    def test_validate_all_before_mutation(self):
        list(self.c.schedules.values())[1]['args']['raw_log']='private'
        with self.assertRaisesRegex(m.ScheduleCheckError,'DEFINITION_MISMATCH'):m.inspect_or_enable(True,self.c)
        self.assertEqual(self.c.posts,[])
    def test_refusal_no_retry(self):
        def refuse(*args,**kw):self.c.posts.append(1);return Response('secret',403)
        self.c.post=refuse
        with self.assertRaisesRegex(m.ScheduleCheckError,'ENABLE_REFUSED'):m.inspect_or_enable(True,self.c)
        self.assertEqual(len(self.c.posts),1)
    def test_network_sanitized(self):
        self.c.get=lambda *a,**kw:(_ for _ in ()).throw(RuntimeError('SECRET'))
        with self.assertRaisesRegex(m.ScheduleCheckError,'SCHEDULE_OPERATION_UNAVAILABLE') as err:m.inspect_or_enable(False,self.c)
        self.assertNotIn('SECRET',str(err.exception))
    def test_sharing_callback_run_as_refused(self):
        for key,val in [('extra_perms',{'g/all':False}),('on_failure','u/admin/foo'),('permissioned_as','u/other')]:
            c=Client();list(c.schedules.values())[0][key]=val
            with self.assertRaises(m.ScheduleCheckError):m.inspect_or_enable(True,c)
            self.assertEqual(c.posts,[])
if __name__=='__main__':unittest.main()
