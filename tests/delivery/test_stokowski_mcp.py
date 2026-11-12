"""New-generation foo routing only; synthetic tokens and no live MCP calls."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, patch

import httpx

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import stokowski_mcp as mcp
import stokowski_operations as operations

JOB = '00000000-0000-4000-8000-000000000001'


class FooRouteTests(unittest.TestCase):
    def test_mcp_uses_exact_foo_dispatcher_without_changing_product_identity(self):
        calls=[]
        def handler(request):
            body=json.loads(request.content)
            calls.append(body)
            if body['method']=='initialize':
                return httpx.Response(200,json={'jsonrpc':'2.0','id':1,'result':{}})
            if body['method']=='notifications/initialized':
                return httpx.Response(202)
            return httpx.Response(200,json={'jsonrpc':'2.0','id':2,
                'result':{'structuredContent':{'found':False}}})
        async def run():
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
            with patch.object(mcp,'configured_headers',return_value={'Authorization':'Bearer synthetic'}), \
                 patch.object(httpx,'AsyncClient',return_value=client):
                self.assertIsNone(await mcp.WindmillMCP().inspect(JOB))
        asyncio.run(run())
        self.assertEqual(calls[-1]['params'],{'name':'run_script','arguments':{
            'workspace_id':'foo','path':'u/admin/offmenu_delivery_dispatch',
            'args':{'action':'inspect','job_id':JOB},'wait_seconds':15}})

    def test_mcp_rejects_foreign_or_retired_job_metadata(self):
        good=dict(id=JOB,workspace_id='foo',script_path=operations.BRIDGE)
        for changes in ({'workspace_id':'offmenu'},{'workspace_id':'other'},
                        {'id':'00000000-0000-4000-8000-000000000002'},
                        {'script_path':'u/admin/other'}):
            with self.subTest(changes=changes):
                client=mcp.WindmillMCP()
                client.call=AsyncMock(return_value={'found':True,'job':dict(good,**changes)})
                with self.assertRaises(operations.ObservationBindingError):
                    asyncio.run(client.inspect(JOB))
                client.call.assert_awaited_once_with('inspect',JOB)

    def test_mcp_foo_observation_is_not_relabelled(self):
        job=dict(id=JOB,workspace_id='foo',script_path=operations.BRIDGE)
        client=mcp.WindmillMCP()
        client.call=AsyncMock(return_value={'found':True,'job':job})
        self.assertIs(asyncio.run(client.inspect(JOB)),job)

    def test_mcp_refusal_does_not_try_preview_or_another_route(self):
        calls=[]
        def handler(request):
            calls.append(json.loads(request.content))
            return httpx.Response(403)
        async def run():
            client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
            with patch.object(mcp,'configured_headers',return_value={'Authorization':'Bearer synthetic'}), \
                 patch.object(httpx,'AsyncClient',return_value=client):
                with self.assertRaises(operations.RequestRefused):
                    await mcp.WindmillMCP().inspect(JOB)
        asyncio.run(run())
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0]['method'],'initialize')

    def test_api_get_and_submit_use_foo_with_original_bridge_and_uuid(self):
        calls=[]
        job=dict(id=JOB,workspace_id='foo',script_path=operations.BRIDGE)
        request_args={'action':'status','job_id':'offmenu-'+'a'*48}
        def handler(request):
            calls.append(request)
            return httpx.Response(200,json=job) if request.method=='GET' else httpx.Response(201,text=JOB)
        async def run():
            async with httpx.AsyncClient(base_url=operations.BASE_URL+'/api',
                    transport=httpx.MockTransport(handler)) as client:
                api=operations.WindmillAPI('synthetic',client)
                self.assertEqual(await api.inspect(JOB),job)
                await api.submit(JOB,request_args)
        asyncio.run(run())
        self.assertEqual(calls[0].url.path,'/api/w/foo/jobs_u/get/'+JOB)
        self.assertEqual(calls[1].url.path,'/api/w/foo/jobs/run/p/'+operations.BRIDGE)
        self.assertEqual(calls[1].url.params['job_id'],JOB)
        self.assertEqual(json.loads(calls[1].content),request_args)

    def test_api_foreign_metadata_is_conflict_not_absence(self):
        async def run():
            for workspace in ('offmenu','other'):
                with self.subTest(workspace=workspace):
                    response=dict(id=JOB,workspace_id=workspace,script_path=operations.BRIDGE)
                    async with httpx.AsyncClient(base_url=operations.BASE_URL+'/api',
                            transport=httpx.MockTransport(lambda request:httpx.Response(200,json=response))) as client:
                        with self.assertRaises(operations.ObservationBindingError):
                            await operations.WindmillAPI('synthetic',client).inspect(JOB)
        asyncio.run(run())

    def test_api_refusal_stops_without_fallback(self):
        async def run():
            for status in (401,403):
                for action in ('inspect','submit'):
                    with self.subTest(status=status,action=action):
                        calls=[]
                        def handler(request):
                            calls.append(request)
                            return httpx.Response(status)
                        async with httpx.AsyncClient(base_url=operations.BASE_URL+'/api',
                                transport=httpx.MockTransport(handler)) as client:
                            api=operations.WindmillAPI('synthetic',client)
                            with self.assertRaises(operations.RequestRefused):
                                if action=='inspect':
                                    await api.inspect(JOB)
                                else:
                                    await api.submit(JOB,{'action':'status','job_id':'offmenu-'+'a'*48})
                        self.assertEqual(len(calls),1)
                        expected='/api/w/foo/jobs_u/get/'+JOB if action=='inspect' else '/api/w/foo/jobs/run/p/'+operations.BRIDGE
                        self.assertEqual(calls[0].url.path,expected)
        asyncio.run(run())

    def test_injected_generic_token_and_exact_worker_context_only(self):
        class Capture(operations.WindmillAPI):
            def __init__(self,token):
                if not token:
                    raise operations.OperationError('Existing authentication absent')
                self.selected=token
        for environment,expected in (
            ({'WINDMILL_TOKEN':'generic-canary','OFFMENU_WINDMILL_TOKEN':'retired-canary'},'generic-canary'),
            ({'WM_WORKSPACE':'foo','WM_TOKEN':'worker-canary'},'worker-canary')):
            with patch.dict(os.environ,environment,clear=True):
                self.assertEqual(Capture.injected().selected,expected)
        for environment in ({'OFFMENU_WINDMILL_TOKEN':'retired-canary'},
                            {'WM_WORKSPACE':'offmenu','WM_TOKEN':'retired-canary'}):
            with patch.dict(os.environ,environment,clear=True):
                with self.assertRaises(operations.OperationError):
                    Capture.injected()

    def test_existing_mounted_credential_selector_is_retained(self):
        class Capture(operations.WindmillAPI):
            def __init__(self,token):
                self.selected=token
        with patch.dict(os.environ,{'CREDENTIALS_DIRECTORY':'/synthetic-credentials'},clear=True), \
             patch.object(Path,'is_file',return_value=True) as is_file, \
             patch.object(Path,'read_text',return_value='mounted-canary\n') as read:
            self.assertEqual(Capture.injected().selected,'mounted-canary')
        is_file.assert_called_once_with()
        read.assert_called_once_with()


if __name__=='__main__':
    unittest.main()
