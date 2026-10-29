"""Scoped native Windmill MCP client; reuse configured OAuth without copying it.

Only the typed dispatcher script is callable. Coding children never import this
client or receive its authentication. Expired/refused access defers operations;
no credential/grant creation or alternate-protocol fallback occurs here.
"""
import asyncio
import json
from pathlib import Path
import re
import subprocess
from uuid import UUID

from stokowski_operations import OperationError, RequestRefused, TransportUnavailable

URL = 'https://windmill.aldous.info/api/mcp'
DISPATCHER = 'u/admin/offmenu_delivery_dispatch'


def configured_headers():
    # Codex owns the OAuth store. Read its current matching entry each time;
    # never copy, renew or overwrite the shared store from this adapter.
    result = subprocess.run(['codex','mcp','get','windmill','--json'],
                            capture_output=True,text=True,timeout=15,check=True)
    config = json.loads(result.stdout)
    if not config.get('enabled') or config.get('transport',{}).get('url') != URL:
        raise RequestRefused('Existing native Windmill MCP profile does not match')
    store = json.loads((Path.home()/'.codex/.credentials.json').read_text())
    entries = [v for v in store.values() if isinstance(v,dict)
               and v.get('server_name') == 'windmill' and v.get('server_url') == URL]
    if len(entries) != 1 or not entries[0].get('access_token'):
        raise RequestRefused('Existing Windmill MCP OAuth credential unavailable')
    return {'Authorization':'Bearer '+entries[0]['access_token'],
            'Accept':'application/json, text/event-stream'}


def rpc_result(response,request_id):
    if response.headers.get('content-type','').startswith('text/event-stream'):
        candidates = []
        for line in response.text.splitlines():
            if line.startswith('data:'):
                try:
                    candidates.append(json.loads(line[5:].strip()))
                except ValueError:
                    pass
        result = next((x for x in candidates if x.get('id') == request_id),None)
    else:
        result = response.json()
    if not isinstance(result,dict) or result.get('id') != request_id or 'error' in result:
        raise OperationError('MCP response identity/error')
    return result.get('result')


def tool_value(result):
    if not isinstance(result,dict) or result.get('isError'):
        raise OperationError('Typed Windmill MCP call failed')
    structured = result.get('structuredContent')
    if isinstance(structured,dict) and any(k in structured for k in ('found','submitted','error')):
        return structured
    for content in result.get('content',[]):
        if content.get('type') != 'text':
            continue
        text = content.get('text','')
        # Native tools render Result (...) followed by JSON and then logs/URL.
        start = text.find('{')
        if start >= 0:
            try:
                value,_ = json.JSONDecoder().raw_decode(text[start:])
                if isinstance(value,dict) and any(k in value for k in ('found','submitted','error')):
                    return value
            except ValueError:
                pass
    raise OperationError('Dispatcher result not completed; reconcile job before retry')


class WindmillMCP:
    def __init__(self,preview=False):
        # Explicit test mode only. Never fall back from a refused deployment or
        # failed deployed call into preview execution automatically.
        self.preview = preview

    async def call(self,action,job_id,request=None):
        import httpx
        headers = await asyncio.to_thread(configured_headers)
        async with httpx.AsyncClient(timeout=45,follow_redirects=False) as client:
            async def post(body):
                try:
                    response = await client.post(URL,headers=headers,json=body)
                except httpx.TransportError:
                    raise TransportUnavailable('Native Windmill MCP unavailable') from None
                if response.status_code in (401,403):
                    raise RequestRefused('Native Windmill MCP access refused')
                if response.status_code >= 500:
                    raise TransportUnavailable('Native Windmill MCP service unavailable')
                response.raise_for_status()
                return response
            init = await post({'jsonrpc':'2.0','id':1,'method':'initialize',
                'params':{'protocolVersion':'2025-03-26','capabilities':{},
                          'clientInfo':{'name':'offmenu-typed-dispatcher','version':'1'}}})
            rpc_result(init,1)
            if init.headers.get('mcp-session-id'):
                headers['Mcp-Session-Id'] = init.headers['mcp-session-id']
            await post({'jsonrpc':'2.0','method':'notifications/initialized'})
            arguments = {'action':action,'job_id':str(UUID(job_id))}
            if request is not None:
                arguments['request'] = request
            response = await post({'jsonrpc':'2.0','id':2,'method':'tools/call','params':{
                'name':'test_run_script' if self.preview else 'run_script',
                'arguments':{'workspace_id':'offmenu','path':DISPATCHER,
                'args':arguments,'wait_seconds':15}}})
            result = tool_value(rpc_result(response,2))
        if result.get('error') == 'refused':
            raise RequestRefused('Windmill SDK request refused')
        if result.get('error') == 'unavailable':
            raise TransportUnavailable('Windmill SDK observation unavailable')
        if result.get('error'):
            raise OperationError('Windmill operation requires reconciliation')
        return result

    async def inspect(self,job_id):
        value = await self.call('inspect',job_id)
        return value.get('job') if value.get('found') else None

    async def submit(self,job_id,args):
        value = await self.call('submit',job_id,args)
        if not value.get('submitted') or value.get('job_id') != job_id:
            raise OperationError('Windmill submission not confirmed')

    async def close(self):
        return None
