"""Typed SDK/MCP protocol boundary tests, without network or credentials."""
import asyncio
import copy
import hashlib
import json
import ast
import shlex
import subprocess
from uuid import NAMESPACE_URL, uuid5
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/delivery'))
import windmill_dispatcher as dispatcher
import stokowski_mcp as mcp
import stokowski_operations as operations


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


class ReviewedEnvelopeTests(unittest.TestCase):
    job_id = DispatcherBoundaryTests.job_id

    def request(self, **changes):
        # Synthetic lineage and pins, passed through the real profile validator
        # and command generator; no source checkout, receipts or SDK needed.
        outputs = {'tools/delivery/example.py':'a'*64}
        spec = dict(version=3,issue='UIF-119',
            issue_id='00000000-0000-5000-8000-000000000119',stage='validate',
            owner='synthetic-owner',branch='feature/synthetic-reviewed',
            head='b'*40,base='c'*40,policy_sha256='d'*64,
            acceptance_sha256='e'*64,runner_sha256='f'*64,executor_sha256='1'*64,
            control_sha256='2'*64,profile=operations.REVIEWED_PROFILE,outputs=outputs,
            workspace='/offmenu/data/.offmenu-platform/workspaces/synthetic-reviewed-source',
            local_source_root='/synthetic/source',
            execution=dict(task_fit='deterministic reviewed source validation',
                requested_model=None,requested_effort=None,provider_route='none',
                resolved_model=None,resolution_status='not-applicable'),
            origin=dict(kind='reviewed-source-v1',admission_sha256='e'*64,
                review_sha256='3'*64,author='synthetic-author',authors=['synthetic-author'],
                provenance=[dict(path='/synthetic/provenance.json',sha256='4'*64,
                    author='synthetic-author',owner='synthetic-author',session='synthetic-session',
                    source_head='5'*40,contribution_head='6'*40,outputs=outputs,
                    path_mapping={name:name for name in outputs},derivation=None)]))
        spec.update(changes)
        return operations.bridge_arguments(operations.validated(spec))

    def test_generated_v3_preserves_exact_request_command_and_reserved_uuid(self):
        request = self.request()
        original = copy.deepcopy(request)
        command_hash = hashlib.sha256(request['command'].encode()).hexdigest()
        request_bytes = json.dumps(request,sort_keys=True,separators=(',', ':')).encode()
        self.assertIs(dispatcher.validate_request(request),request)
        calls = []
        def post(*args,**kwargs):
            calls.append((args,kwargs))
            return Response(201,text=reserved)
        spec = json.loads(ast.literal_eval(ast.parse(shlex.split(request['command'])[10]).body[1].value.args[0]))
        reserved = str(uuid5(NAMESPACE_URL,'offmenu:run:'+operations.operation_key(spec)))
        result = dispatcher.dispatch(SimpleNamespace(post=post),'submit',reserved,request)
        self.assertTrue(result['submitted'])
        self.assertEqual(len(calls),1)
        self.assertEqual(calls[0],(('/w/offmenu/jobs/run/p/'+dispatcher.BRIDGE,),
            dict(params={'job_id':reserved},json=original,raise_for_status=False)))
        self.assertIs(calls[0][1]['json'],request)
        self.assertEqual(request,original)
        self.assertEqual(json.dumps(calls[0][1]['json'],sort_keys=True,
                                   separators=(',', ':')).encode(),request_bytes)
        self.assertEqual(hashlib.sha256(request['command'].encode()).hexdigest(),command_hash)

    def test_generated_v3_mismatched_reserved_uuid_refuses_before_post(self):
        request = self.request()
        spec = json.loads(ast.literal_eval(ast.parse(shlex.split(request['command'])[10]).body[1].value.args[0]))
        reserved = str(uuid5(NAMESPACE_URL,'offmenu:run:'+operations.operation_key(spec)))
        self.assertNotEqual(self.job_id,reserved)
        calls = []
        def post(*args,**kwargs):
            calls.append((args,kwargs))
            return Response(201,text=self.job_id)
        try:
            with self.assertRaises(ValueError):
                dispatcher.dispatch(SimpleNamespace(post=post),'submit',self.job_id,request)
        finally:
            self.assertEqual(len(calls),0)

    def test_invalid_v3_envelopes_refuse_before_post(self):
        request = self.request()
        root = '/offmenu/data/.offmenu-platform/workspaces/synthetic-reviewed-source'
        command = request['command']
        commands = []
        for bad_root in ('/tmp/synthetic-reviewed-source', root+'/../other',root+'/./alias',
                         root+'//alias',root+'/link/../alias',root+';id',root+'$(id)',
                         root+'`id`',root+'\nother',root+'*',root+'.suffix',
                         root.rsplit('/',1)[0]+'/_invalid',
                         root.rsplit('/',1)[0]+'/'+ 'a'*81):
            commands.append(command.replace(root,bad_root))
        commands.extend([
            command.replace(root+'/src',root+'-other/src',1),
            command.replace('PYTHONDONTWRITEBYTECODE=1','PYTHONDONTWRITEBYTECODE=0',1),
            command.replace('GIT_OPTIONAL_LOCKS=0 ','',1),
            command.replace('GIT_OPTIONAL_LOCKS=0 ','GIT_OPTIONAL_LOCKS=0 EXTRA=1 ',1),
            command.replace('export PYTHONDONTWRITEBYTECODE=1 ','',1),
            command.replace(' && /offmenu/.venv-delivery/bin/python',
                            ' EXTRA=1 && /offmenu/.venv-delivery/bin/python',1),
            command+'x'*32000,command+'\0',command+'é'*16000])
        invalid = [dict(request,command=value) for value in commands]
        invalid.extend([dict(request,mode='write'),dict(request,timeout_seconds=181)])
        for name,value in [('workers',2),('write_roots',['/offmenu']),
                           ('read_roots',['/tmp']),('output_bytes',1)]:
            invalid.append(dict(request,resources=dict(request['resources'],**{name:value})))
        for index,value in enumerate(invalid):
            with self.subTest(case=index):
                def post(*args,**kwargs):
                    self.fail('Rejected envelope reached SDK post')
                with self.assertRaises(ValueError):
                    dispatcher.dispatch(SimpleNamespace(post=post),'submit',self.job_id,value)

    def assert_rejected(self, request):
        def post(*args,**kwargs):
            self.fail('Rejected command reached SDK post')
        with self.assertRaises(ValueError):
            dispatcher.dispatch(SimpleNamespace(post=post),'submit',self.job_id,request)

    def test_exact_prefix_bypass_and_shell_tails_are_rejected(self):
        request = self.request()
        prefix = request['command'][:request['command'].index(' -c ')+4]
        for command in (prefix+shlex.quote('print(1)'),
                        prefix+shlex.quote('print(1)')+' && /bin/true',
                        request['command']+' && /bin/true'):
            with self.subTest(command=command[-50:]):
                self.assert_rejected(dict(request,command=command))

    def test_each_candidate_body_and_complete_template_are_pinned(self):
        request = self.request()
        body = shlex.split(request['command'])[10]
        for changed in (body+'print(1)\n',
                        body.replace('if transformed or detached:', 'if transformed:'),
                        body.replace('ancestor(source,contribution)', 'pass'),
                        body.replace("assert root.resolve()==root", "assert True or root.resolve()==root"),
                        body.replace("assert git('rev-parse','HEAD').decode().strip()==spec['head'], 'head drift'\n",'')):
            for position in ('first','last','both'):
                quoted,new = shlex.quote(body),shlex.quote(changed)
                command = request['command']
                if position == 'last':
                    command = new.join(command.rsplit(quoted,1))
                else:
                    command = command.replace(quoted,new,1 if position == 'first' else 2)
                with self.subTest(position=position,change=changed[-30:]):
                    self.assert_rejected(dict(request,command=command))

    def test_complete_oracle_profile_is_pinned(self):
        request = self.request()
        body = shlex.split(request['command'])[14]
        for changed in (body+'print(1)\n',
                        body.replace('result.testsRun>0','result.testsRun>=0'),
                        body.replace("root=pathlib.Path(","root=pathlib.PurePath("),
                        body.replace(repr('c'*40),repr('9'*40)),
                        body.replace(repr('2'*64),repr('9'*64)),
                        body.replace(' and not result.skipped',''),
                        body.replace('test_normal_tick_continues_original_intent_and_reopen',
                                     'test_other_profile'),
                        body.replace("assert hashlib.sha256(archive).hexdigest()==",'assert True or hashlib.sha256(archive).hexdigest()==')):
            with self.subTest(change=changed[-50:]):
                self.assert_rejected(dict(request,command=request['command'].replace(
                    shlex.quote(body),shlex.quote(changed))))

    def test_embedded_spec_is_qualified_and_bound_to_workspace_and_digest(self):
        request = self.request()
        body = shlex.split(request['command'])[10]
        original = json.loads(ast.literal_eval(ast.parse(body).body[1].value.args[0]))
        for changes in ({'workspace':original['workspace']+'-other'}, {'head':'9'*40},
                        {'version':1}, {'version':True}, {'profile':'arbitrary'},
                        {'control_sha256':'bad'}, {'execution':{}},
                        {'origin':dict(original['origin'],admission_sha256='0'*64)}):
            spec = dict(original,**changes)
            changed = operations.reviewed_check_code(spec,original['workspace'])
            command = request['command'].replace(shlex.quote(body),shlex.quote(changed))
            # Recompute digest for malformed specs too, isolating qualification.
            key = operations.digest({k:v for k,v in spec.items() if k != 'owner'})
            logical_id = request['job_id'] if 'head' in changes else 'offmenu-'+key[:48]
            with self.subTest(changes=changes):
                self.assert_rejected(dict(request,command=command,job_id=logical_id))
        self.assert_rejected(dict(request,job_id='offmenu-'+'0'*48))

    def test_embedded_json_duplicates_and_nonliteral_python_are_rejected(self):
        request = self.request()
        body = shlex.split(request['command'])[10]
        literal = ast.literal_eval(ast.parse(body).body[1].value.args[0])
        assignment = 'spec=json.loads('+repr(literal)+')'
        for replacement in ('spec=json.loads('+repr('{"version": 3, '+literal[1:])+')',
                            "spec=json.loads(__import__('os').getcwd())"):
            changed = body.replace(assignment,replacement)
            self.assert_rejected(dict(request,command=request['command'].replace(
                shlex.quote(body),shlex.quote(changed))))

    def test_equivalent_shell_requoting_and_reframing_are_rejected(self):
        request = self.request()
        root = shlex.split(request['command'])[1]
        for command in (request['command'].replace('cd '+root,'cd "'+root+'"',1),
                        request['command'].replace(' && ','  && ',1),
                        '('+request['command']+')',request['command']+'\n',
                        request['command']+"'",request['command']+'\\'):
            self.assert_rejected(dict(request,command=command))

    def test_fixed_templates_accept_multiple_synthetic_spec_variants(self):
        for changes in ({},dict(workspace='/offmenu/data/.offmenu-platform/workspaces/Other_42',
                                head='7'*40,base='8'*40,control_sha256='9'*64,
                                owner='other synthetic owner',branch='bugfix/other-synthetic'),
                        dict(issue='UIF-120',issue_id='00000000-0000-5000-8000-000000000120',
                             local_source_root='/another/synthetic/source')):
            request = self.request(**changes)
            original = copy.deepcopy(request)
            self.assertIs(dispatcher.validate_request(request),request)
            self.assertEqual(request,original)

    def test_standalone_deployed_script_needs_no_checkout_imports(self):
        script = ("import json,runpy,sys; "
                  "module=runpy.run_path(sys.argv[1]); "
                  "request=json.load(sys.stdin); "
                  "assert module['validate_request'](request) is request; "
                  "assert 'stokowski_operations' not in sys.modules")
        result = subprocess.run([sys.executable,'-I','-c',script,dispatcher.__file__],
            input=json.dumps(self.request()),text=True,capture_output=True)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_v3_duplicate_responses_keep_uuid_and_require_reconciliation(self):
        for status in (400,409):
            calls = []
            request = self.request()
            spec = json.loads(ast.literal_eval(ast.parse(shlex.split(request['command'])[10]).body[1].value.args[0]))
            reserved = str(uuid5(NAMESPACE_URL,'offmenu:run:'+operations.operation_key(spec)))
            def post(*args,**kwargs):
                calls.append(kwargs)
                return Response(status,text='duplicate')
            result = dispatcher.dispatch(SimpleNamespace(post=post),'submit',reserved,request)
            self.assertEqual(result['error'],'reconcile')
            self.assertEqual(result['job_id'],reserved)
            self.assertEqual(len(calls),1)
            self.assertEqual(calls[0]['params'],{'job_id':reserved})
            self.assertIs(calls[0]['json'],request)


class PublisherEnvelopeTests(ReviewedEnvelopeTests):
    # Exercise the same exact-envelope, transport, UUID, duplicate/reconcile and
    # isolated standalone-import regressions for the second fixed v3 enum.
    def request(self, **changes):
        return super().request(**dict({'profile':operations.PUBLISHER_PROFILE},**changes))

    def test_complete_oracle_profile_is_pinned(self):
        request = self.request()
        body = shlex.split(request['command'])[14]
        replacements = [
            ('result.testsRun>0','result.testsRun>=0'),
            ('result.wasSuccessful()','True'),
            (' and not result.skipped',''),
            (repr('c'*40),repr('9'*40)),
            (repr('2'*64),repr('9'*64)),
            ("for module in (", "for module in tuple("),
        ]
        replacements.extend((name,name+'.SelectedTests.test_one')
                            for name in operations.PUBLISHER_TESTS)
        replacements.extend((name,'test_other_baseline') for name in (
            'test_unknown_missing_remote_job_is_not_blindly_resubmitted',
            'test_second_owner_cannot_create_duplicate_operation',
            'test_cancel_before_submission_does_not_start_a_job'))
        for before,after in replacements:
            self.assertIn(before,body)
            with self.subTest(before=before):
                self.assert_rejected(dict(request,command=request['command'].replace(
                    shlex.quote(body),shlex.quote(body.replace(before,after)))))

    def test_profiles_cannot_exchange_oracles_or_accept_unknown_selectors(self):
        current = super().request(profile=operations.REVIEWED_PROFILE)
        publisher = self.request()
        for request,other in ((current,publisher),(publisher,current)):
            body = shlex.split(request['command'])[14]
            replacement = shlex.split(other['command'])[14]
            self.assert_rejected(dict(request,command=request['command'].replace(
                shlex.quote(body),shlex.quote(replacement))))
        body = shlex.split(publisher['command'])[10]
        original = json.loads(ast.literal_eval(ast.parse(body).body[1].value.args[0]))
        for changes in ({'profile':operations.PUBLISHER_PROFILE+'-other'},
                        {'profile':operations.PUBLISHER_PROFILE+'.test_one'},
                        {'argv':['test_protected_owner_install']},
                        {'test_selectors':list(operations.PUBLISHER_TESTS)},
                        {'modules':list(operations.PUBLISHER_TESTS)}):
            spec = dict(original,**changes)
            with self.subTest(changes=changes):
                with self.assertRaises(operations.OperationError):
                    operations.validated(spec)
                with self.assertRaises(ValueError):
                    dispatcher._qualified_reviewed_spec(spec)
                changed = operations.reviewed_check_code(spec,original['workspace'])
                key = operations.digest({k:v for k,v in spec.items() if k != 'owner'})
                self.assert_rejected(dict(publisher,job_id='offmenu-'+key[:48],
                    command=publisher['command'].replace(shlex.quote(body),shlex.quote(changed))))


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

    def test_completed_schema_without_running_normalizes_and_binds_exact_args(self):
        from stokowski_operations import digest, observation_matches
        remote = self.remote()
        del remote['running']  # Windmill 1.850.0 CompletedJob has no running field.
        original = copy.deepcopy(remote)
        compact = dispatcher.compact_job(remote)
        self.assertIs(compact['running'],False)
        self.assertEqual(compact['args_sha256'],digest(remote['args']))
        self.assertTrue(observation_matches(compact,remote['id'],remote['args']))
        self.assertEqual(remote,original)

    def test_status_job_completion_keeps_backend_cleanup_uncertainty(self):
        remote = self.remote()
        remote['args'] = {'action':'status', 'job_id':remote['args']['job_id']}
        receipt = remote['result']['receipt']
        receipt.update(status='running', child_tree_gone=False, reconcile_required=True)
        remote['result']['job_succeeded'] = False
        calls = []
        def get(*args, **kwargs):
            calls.append(args[0])
            return Response(value=remote)
        # A completed successful API wrapper is only a status observation.
        result = dispatcher.dispatch(SimpleNamespace(get=get), 'inspect', remote['id'])
        self.assertTrue(result['job']['success'])
        self.assertEqual(result['job']['result']['receipt'], receipt)
        self.assertFalse(result['job']['result']['job_succeeded'])
        self.assertEqual(calls, ['/w/offmenu/jobs_u/get/' + remote['id']])

    def test_contradictory_or_malformed_job_states_are_rejected(self):
        for fields in ({'running':True}, {'running':None}, {'success':None},
                       {'type':'QueuedJob','success':True},
                       {'type':'QueuedJob','running':None,'success':None}):
            with self.subTest(fields=fields),self.assertRaises(ValueError):
                dispatcher.compact_job(dict(self.remote(),**fields))
        remote = dict(self.remote(),type='QueuedJob',success=None)
        del remote['running']
        with self.assertRaises(ValueError):
            dispatcher.compact_job(remote)

    def test_absent_or_error_results_emit_only_fixed_classification(self):
        for payload in (None, {'error':{'message':'SENSITIVE wrapper failure'}},
                        'SENSITIVE string error', json.dumps('SENSITIVE string error'),
                        'null', {'ok':True}, {'error':'SENSITIVE'*100}):
            remote = self.remote()
            del remote['running']
            remote.update(success=False,result=payload)
            with self.subTest(payload=payload):
                compact = dispatcher.compact_job(remote)
                self.assertEqual(compact['result'],{'classification':'no-authoritative-receipt'})
                self.assertEqual(dispatcher.compact_result(compact['result']),compact['result'])
                self.assertNotIn('SENSITIVE',json.dumps(compact))
        for payload in ({'receipt':None}, {'receipt':{'status':'succeeded'}},
                        {'job_id':'offmenu-'+'b'*48}, 'x'*10001,
                        {'error':'x'*10001}, '{"receipt":'):
            remote = dict(self.remote(),result=payload)
            with self.subTest(payload=type(payload)),self.assertRaises(ValueError):
                dispatcher.compact_job(remote)

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
