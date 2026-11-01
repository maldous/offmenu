"""UIF-133 dispatcher qualification for the frozen identity-profile producer."""
import ast
import copy
import hashlib
import json
import shlex
import unittest
from unittest.mock import patch

import stokowski_operations as operations
import windmill_dispatcher as dispatcher


class IdentityDispatcherTests(unittest.TestCase):
    def spec(self, **changes):
        outputs = {'tests/edge/handler-auth-dispatch.test.mjs':
            'c21c818ec8aab81ac55cdd391f6dd373551b8df583148d04dc537e271beca715'}
        spec = dict(version=3, issue='UIF-96',
            issue_id='c82fda68-a594-4855-8b68-7e220f7fa517', stage='validate',
            owner='offmenu-cloud-github-owner-01a1866b',
            head='bff58041239eb52a2fd8b9989e7d8ce391078082',
            base='7aac2240cdc6487412d3f19fc8dbefb3894fbc25',
            branch='bugfix/uif96-native-journey-source',
            policy_sha256='9f9f08b1c3e1ddf36fcdff3da72f40d5d0bde49012c847404deb228cc7e85635',
            runner_sha256='b7cf2455c48eff40c3eaf7eaddffbe018011f8ae0e8172e33ac5e75b10df202d',
            executor_sha256='01f50d80cf5359af79c695e342c5c6998331a092b0a90f31b26868ab2296e8a0',
            control_sha256='8560a5cd72b3016f3891a590a578add33bf3ef11b011e9adfe9b6c0ed45b8fd9',
            acceptance_sha256='e' * 64, outputs=outputs, profile='identity-client-focused',
            workspace='/offmenu/data/.offmenu-platform/workspaces/uif96-identity-bff58041',
            local_source_root='/synthetic/root-candidate',
            execution=dict(task_fit='deterministic reviewed source validation',
                requested_model=None, requested_effort=None, provider_route='none',
                resolved_model=None, resolution_status='not-applicable'),
            origin=dict(kind='reviewed-source-v1', admission_sha256='e' * 64,
                review_sha256='3' * 64, author='synthetic-native-author',
                authors=['synthetic-native-author'], provenance=[dict(
                    path='/synthetic/original-native-receipt.json', sha256='4' * 64,
                    author='synthetic-native-author', owner='synthetic-native-author',
                    session='original-session', source_head='7aac2240cdc6487412d3f19fc8dbefb3894fbc25',
                    contribution_head='bff58041239eb52a2fd8b9989e7d8ce391078082', outputs=outputs,
                    path_mapping={name:name for name in outputs}, derivation=None)]))
        return dict(spec, **changes)

    def test_real_frozen_producer_request_qualifies_without_execution(self):
        request = operations.bridge_arguments(self.spec())
        with patch('builtins.exec', side_effect=AssertionError('dispatcher must not execute bodies')):
            self.assertIs(dispatcher.validate_request(request), request)
        self.assertEqual(dispatcher._reviewed_command(request['command'], request['job_id']),
                         operations.operation_key(self.spec()))

    def request_body(self, body, spec=None):
        spec = self.spec() if spec is None else spec
        request = operations.bridge_arguments(self.spec())
        request['command'] = '/offmenu/.venv-delivery/bin/python -c '+shlex.quote(body)
        key = hashlib.sha256(json.dumps({k:v for k,v in spec.items() if k != 'owner'},
            sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        request['job_id'] = 'offmenu-'+key[:48]
        return request

    def test_fixed_body_rejects_node_environment_scratch_and_source_oracle_changes(self):
        body = shlex.split(operations.bridge_arguments(self.spec())['command'])[2]
        oracle = ast.literal_eval(ast.parse(body).body[2].value)
        bad_oracle = oracle.replace('root.resolve()==root', 'True', 1)
        mutations = [
            body.replace("'/bin/node'", "'/bin/sh'", 1),
            body.replace("'--test-isolation=none'", "'--test-isolation=process'", 1),
            body.replace("'CLOUDFLARE_CF_FETCH_ENABLED':'false'", "'CLOUDFLARE_CF_FETCH_ENABLED':'true'", 1),
            body.replace("'HOME':str(scratch)", "'HOME':'/home/user'", 1),
            body.replace("dir='/tmp'", "dir=str(root)", 1),
            body.replace(repr(oracle), repr(bad_oracle), 1),
            body.replace("'tests':14", "'tests':0", 1),
            body + "\n__import__('os').system('arbitrary')\n",
        ]
        for mutated in mutations:
            self.assertNotEqual(mutated, body)
            with self.subTest(body_hash=hashlib.sha256(mutated.encode()).hexdigest()), \
                 self.assertRaises(ValueError):
                dispatcher.validate_request(self.request_body(mutated))

    def test_workspace_control_base_and_job_identity_are_all_bound(self):
        spec = self.spec()
        body = shlex.split(operations.bridge_arguments(spec)['command'])[2]
        for old, new in [(spec['workspace'], '/tmp/arbitrary'),
                         (spec['base'], '0' * 40),
                         (spec['control_sha256'], '0' * 64)]:
            # Change only the outer literal, leaving the embedded spec/oracle.
            mutated = body.replace(repr(old), repr(new), 1)
            self.assertNotEqual(mutated, body)
            with self.subTest(parameter=old), self.assertRaises(ValueError):
                dispatcher.validate_request(self.request_body(mutated))
        request = operations.bridge_arguments(spec)
        for change in ({'job_id':'offmenu-'+'0'*48}, {'timeout_seconds':181},
                       {'mode':'write'}, {'resources':dict(request['resources'],write_roots=['/offmenu'])}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                dispatcher.validate_request(dict(request, **change))

    def test_embedded_spec_provenance_and_profile_cannot_be_smuggled(self):
        for bad in (self.spec(profile='identity-client-focused.other'),
                    self.spec(profile='current-journal-focused')):
            body = operations.identity_validation_code(bad, bad['workspace'])
            with self.subTest(profile=bad['profile']), self.assertRaises(ValueError):
                dispatcher.validate_request(self.request_body(body,bad))
        bad = copy.deepcopy(self.spec())
        bad['origin']['provenance'][0]['owner'] = 'different-owner'
        with self.assertRaises(ValueError):
            dispatcher.validate_request(self.request_body(
                operations.identity_validation_code(bad,bad['workspace']),bad))

    def test_original_profiles_keep_original_body_and_identity_profile_cannot_use_them(self):
        for profile in ('current-journal-focused','protected-publisher-bootstrap'):
            old = self.spec(profile=profile)
            request = operations.bridge_arguments(old)
            self.assertIs(dispatcher.validate_request(request), request)
            tokens = shlex.split(request['command'])
            old_check = tokens[10]
            identity = self.spec()
            new_check = operations.reviewed_check_code(identity,identity['workspace'])
            request['command'] = request['command'].replace(shlex.quote(old_check),shlex.quote(new_check))
            request['job_id'] = 'offmenu-'+operations.operation_key(identity)[:48]
            with self.subTest(profile=profile), self.assertRaises(ValueError):
                dispatcher.validate_request(request)

    def test_legitimate_literal_parameters_remain_canonical(self):
        spec = self.spec(workspace='/offmenu/data/.offmenu-platform/workspaces/another-reviewed-candidate',
                         base='6'*40,control_sha256='7'*64)
        request = operations.bridge_arguments(spec)
        self.assertIs(dispatcher.validate_request(request),request)
        tokens = shlex.split(request['command'])
        for command in ('python -c '+shlex.quote(tokens[2]),
                        request['command']+' && true',
                        'env EXTRA=1 '+request['command']):
            with self.subTest(command_prefix=command[:30]), self.assertRaises(ValueError):
                dispatcher.validate_request(dict(request,command=command))


if __name__ == '__main__':
    unittest.main()
