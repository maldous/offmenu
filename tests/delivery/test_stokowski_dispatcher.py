"""Typed SDK/MCP protocol boundary tests, without network or credentials."""
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


if __name__ == '__main__':
    unittest.main()
