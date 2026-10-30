"""Typed SDK/MCP protocol boundary tests, without network or credentials."""
import asyncio
import copy
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import windmill_dispatcher as dispatcher
import stokowski_mcp as mcp


class Response:
    def __init__(self,status=200,value=None,text=None,headers=None):
        self.status_code = status
        self.value = value
        self.text = json.dumps(value) if text is None else text
        self.headers = headers or {'content-type':'application/json'}
    def json(self):
        return self.value if self.value is not None else json.loads(self.text)


class DispatcherBoundaryTests(unittest.TestCase):
    job_id = '00000000-0000-5000-8000-000000000001'
    request = {'action':'status','job_id':'offmenu-'+'a'*48}

    def test_sdk_submission_selects_exact_existing_bridge_and_uuid(self):
        calls = []
        def post(*args,**kwargs):
            calls.append((args,kwargs))
            return Response(201,text=self.job_id)
        result = dispatcher.dispatch(SimpleNamespace(post=post),'submit',self.job_id,self.request)
        self.assertTrue(result['submitted'])
        self.assertEqual(calls[0][0],('/w/offmenu/jobs/run/p/'+dispatcher.BRIDGE,))
        self.assertEqual(calls[0][1]['params'],{'job_id':self.job_id})
        self.assertEqual(calls[0][1]['json'],self.request)

    def test_duplicate_uuid_requires_readback_not_new_job(self):
        calls = []
        def post(*args,**kwargs):
            calls.append(kwargs)
            return Response(400,text='duplicate')
        result = dispatcher.dispatch(SimpleNamespace(post=post),'submit',self.job_id,self.request)
        self.assertEqual(result['error'],'reconcile')
        self.assertEqual(len(calls),1)

    def test_sdk_refusal_is_not_an_execution_receipt(self):
        client = SimpleNamespace(post=lambda *a,**k:Response(403))
        result = dispatcher.dispatch(client,'submit',self.job_id,self.request)
        self.assertEqual(result['error'],'refused')
        self.assertFalse(result.get('submitted',False))

    def test_foreign_job_metadata_is_not_exposed(self):
        client = SimpleNamespace(get=lambda *a,**k:Response(200,{
            'id':self.job_id,'workspace_id':'offmenu','script_path':'unrelated/script',
            'args':{'private':'should-not-return'}}))
        result = dispatcher.dispatch(client,'inspect',self.job_id)
        self.assertEqual(result['error'],'foreign-job')
        self.assertNotIn('private',json.dumps(result))

    def test_missing_job_is_explicit(self):
        result = dispatcher.dispatch(SimpleNamespace(get=lambda *a,**k:Response(404)),
                                     'inspect',self.job_id)
        self.assertFalse(result['found'])

    def test_control_request_cannot_add_commands_or_resources(self):
        with self.assertRaises(ValueError):
            dispatcher.validate_request(dict(self.request,command='arbitrary'))
        with self.assertRaises(ValueError):
            dispatcher.validate_request({'action':'status','job_id':'different-prefix'})

    def test_sse_response_selects_its_request_not_a_notification(self):
        body = 'data: {"jsonrpc":"2.0","method":"notice"}\n\n'
        body += 'data: {"jsonrpc":"2.0","id":2,"result":{"value":7}}\n\n'
        result = mcp.rpc_result(Response(text=body,headers={'content-type':'text/event-stream'}),2)
        self.assertEqual(result,{'value':7})

    def test_wrong_rpc_response_cannot_be_treated_as_this_operation(self):
        with self.assertRaises(mcp.OperationError):
            mcp.rpc_result(Response(value={'id':3,'result':{'submitted':True}}),2)

    def test_native_tool_rendering_extracts_only_completed_dispatcher_result(self):
        result = {'content':[{'type':'text','text':'Result (SUCCESS)\n\n{"found": false}\n\nLogs: omitted'}]}
        self.assertEqual(mcp.tool_value(result),{'found':False})
        with self.assertRaises(mcp.OperationError):
            mcp.tool_value({'content':[{'type':'text','text':'Job queued, not completed'}]})


class CompactObservationTests(unittest.TestCase):
    def remote(self):
        request = {'action':'run','job_id':'offmenu-'+'a'*48,
            'command':'cd /offmenu && export PYTHONPATH=/offmenu/src '+ 'x'*31900,
            'mode':'read','timeout_seconds':180,
            'resources':{'workers':1,'overhead_processes':8,'cpu_millis':1000,
                'memory_bytes':2147483648,'io_slots':1,'output_bytes':0,
                'read_roots':['/offmenu'],'write_roots':[]}}
        receipt = {'job_id':request['job_id'],'status':'succeeded','exit_code':0,
            'command_sha256':'a'*64,'request_sha256':'b'*64,
            'runner_sha256':'c'*64,'capacity_policy_sha256':'d'*64,
            'child_tree_gone':True,'reconcile_required':False}
        return {'id':DispatcherBoundaryTests.job_id,'workspace_id':'offmenu',
            'script_path':dispatcher.BRIDGE,'args':request,'type':'CompletedJob',
            'running':False,'success':True,'logs':'PRIVATE_UNBOUNDED'*32000,
            'result':{'job_id':request['job_id'],'job_succeeded':True,'receipt':receipt}}

    def test_authored_truncated_shapes_fail_without_fabricated_success(self):
        fixture_bytes = Path(__file__).with_name('observer-response-shapes.json').read_bytes()
        self.assertEqual(hashlib.sha256(fixture_bytes).hexdigest(),
                         'bc68417b7bcb26bbc13793ff85e17b1c43e550b0690f59c5d711c4ebcd2fb61f')
        fixture = json.loads(fixture_bytes)
        self.assertEqual(len(fixture['samples']),2)
        self.assertEqual([s['original_total_characters'] for s in fixture['samples']], [14015,12590])
        for sample in fixture['samples']:
            text = sample['authored_rendering']
            self.assertEqual(len(text),sample['original_rendered_characters'])
            self.assertEqual(hashlib.sha256(text.encode()).hexdigest(),sample['authored_sha256'])
            with self.assertRaises(json.JSONDecodeError):
                json.JSONDecoder().raw_decode(text[text.index('{'):])
            with self.assertRaises(mcp.ToolResultTruncatedError):
                mcp.tool_value({'content':[{'type':'text','text':text}]})

    def test_near_32k_command_compacts_below_native_limit_with_exact_digest(self):
        from stokowski_operations import digest
        remote = self.remote()
        self.assertGreater(len(remote['args']['command']),31000)
        original = copy.deepcopy(remote)
        value = dispatcher.dispatch(SimpleNamespace(get=lambda *a,**k:Response(value=remote)),
                                    'inspect',remote['id'])
        rendered = 'Result (SUCCESS)\n\n'+json.dumps(value)
        self.assertLess(len(rendered),12000)
        self.assertNotIn('args',value['job'])
        self.assertNotIn('PRIVATE_UNBOUNDED',rendered)
        self.assertEqual(value['job']['args_sha256'],digest(remote['args']))
        self.assertEqual(value['job']['result'],remote['result'])
        self.assertEqual(mcp.tool_value({'content':[{'type':'text','text':rendered}]}),value)
        self.assertEqual(remote,original)

    def test_receipt_fields_are_complete_typed_and_never_truncated(self):
        original = self.remote()['result']
        for key,value in [('command_sha256','a'*63),('runner_sha256','a'*65),
                          ('exit_code',True),('child_tree_gone',1),
                          ('arbitrary','SECRET'*10000),('logs','SECRET'*10000)]:
            result = copy.deepcopy(original)
            result['receipt'][key] = value
            with self.subTest(key=key),self.assertRaises(ValueError):
                dispatcher.compact_result(result)
        for field in ('stdout','stderr','logs','extra'):
            with self.subTest(field=field),self.assertRaises(ValueError):
                dispatcher.compact_result(dict(original,**{field:'SECRET'*10000}))
        self.assertEqual(dispatcher.compact_result(json.dumps(original)),original)

    def test_malformed_missing_inspect_never_becomes_absent_job(self):
        for value in ({'submitted':True},{'found':None},{'found':True},
                      {'found':True,'job':None},{'found':False,'job':{}}):
            client = mcp.WindmillMCP()
            async def call(*args):
                return value
            client.call = call
            with self.subTest(value=value),self.assertRaises(mcp.OperationError):
                asyncio.run(client.inspect(DispatcherBoundaryTests.job_id))

    def test_conflicting_backend_result_identity_is_rejected(self):
        remote = self.remote()
        remote['result']['job_id'] = 'offmenu-'+'b'*48
        remote['result']['receipt']['job_id'] = remote['result']['job_id']
        with self.assertRaises(ValueError):
            dispatcher.compact_job(remote)

    def test_safe_rpc_and_incomplete_error_classes(self):
        with self.assertRaises(mcp.RPCIdentityError):
            mcp.rpc_result(Response(text='not json'),2)
        with self.assertRaises(mcp.RPCIdentityError):
            mcp.rpc_result(Response(text='data: []',headers={'content-type':'text/event-stream'}),2)
        with self.assertRaises(mcp.ToolResultIncompleteError):
            mcp.tool_value({'content':[None,{'type':'text','text':'not completed'}]})


if __name__ == '__main__':
    unittest.main()
