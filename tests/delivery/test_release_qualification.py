"""Exact release source, finite execution and fail-closed aggregation behavior."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
import release_qualification as release


class ReleaseQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = release.load_release_policy(release.ROOT / 'config/delivery-release-policy.json')
        self.catalog = release.read_json(release.ROOT / 'config/release-validation-profile.json')
        self.source = dict(repository='maldous/offmenu', branch='develop', target='main',
                           base='1' * 40, head='2' * 40, tree='3' * 40,
                           policy_sha256=release.fingerprint(self.policy))
        (self.root / 'artifact.txt').write_text('qualified output\n')
        self.artifacts = [self.ref('artifact.txt')]
        self.candidate = release.cut(self.source, self.artifacts, self.policy, self.catalog)
        self.plan = release.plan(self.candidate, self.policy, self.catalog, '4' * 64, '5' * 64)

    def ref(self, name):
        return {'path': name, 'sha256': release.file_sha(self.root / name)}

    def result(self, index=0, status='succeeded', coverage='complete', **receipt_overrides):
        check = self.plan['checks'][index]
        job = release.bridge_request(self.plan, check['key'], self.policy, self.catalog)['job_id']
        receipt = dict(job_id=job, status=status, exit_code=0, child_tree_gone=True,
                       mode='write', timeout_seconds=check['timeout_seconds'], reconcile_required=False,
                       command_sha256=check['command_sha256'], runner_sha256='4' * 64,
                       capacity_policy_sha256='5' * 64, resources=check['resources'])
        # Match the original runner producer's file-byte request digest recipe.
        spec = {key: receipt[key] for key in ('command_sha256', 'mode', 'timeout_seconds',
                'runner_sha256', 'capacity_policy_sha256', 'resources')}
        receipt['request_sha256'] = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        receipt.update(receipt_overrides)
        name = 'receipt-' + str(index) + '.json'
        (self.root / name).write_text(json.dumps(receipt))
        ref = self.ref(name)
        handoff = dict(version=1, kind='delivery-handoff-v1', issue_id=str(uuid4()),
                       project_id=str(uuid4()), owner='release-owner',
                       origin={'kind': 'completed-native-validation-v1', 'evidence': ref},
                       source=copy.deepcopy(self.source), outputs=self.artifacts,
                       evidence=[ref], operation=dict(id='operation-' + str(index),
                       backend='windmill', job_id=job, status=status,
                       command_sha256=check['command_sha256'], runner_sha256='4' * 64,
                       policy_sha256='5' * 64, receipt=ref))
        return dict(check=check['key'], plan_sha256=release.fingerprint(self.plan),
                    coverage=coverage, handoff=handoff)

    def aggregate(self, results):
        return release.aggregate(self.plan, results, self.policy, self.catalog, self.root)

    def test_all_required_checks_are_needed_and_order_independent(self):
        first, second = self.result(), self.result(1)
        self.assertEqual(self.aggregate([second, first])['status'], 'qualified')
        self.assertEqual(self.aggregate([first])['status'], 'incomplete')
        self.assertEqual(len(self.aggregate([])['missing']), 2)

    def test_failed_unknown_partial_and_unstopped_results_never_qualify(self):
        for values in ({'status': 'failed'}, {'status': 'unknown'}, {'coverage': 'partial'},
                       {'child_tree_gone': False}, {'reconcile_required': True},
                       {'exit_code': 1}, {'exit_code': False}):
            with self.subTest(values=values):
                result = self.result(**values)
                self.assertFalse(release.reusable_result(self.plan, result, self.policy,
                                                        self.catalog, self.root))

    def test_original_runner_request_identity_is_required(self):
        for changes in ({'mode': 'read'}, {'timeout_seconds': 1},
                        {'timeout_seconds': float(self.plan['checks'][0]['timeout_seconds'])},
                        {'timeout_seconds': True}, {'request_sha256': '0' * 64},
                        {'mode': None}, {'request_sha256': None}):
            with self.subTest(changes=changes):
                with self.assertRaises(release.ContractError):
                    self.aggregate([self.result(**changes)])
        # Rehashing a different actual execution spec still cannot match the plan.
        result = self.result(mode='read', timeout_seconds=1)
        path = self.root / 'receipt-0.json'
        receipt = release.read_json(path)
        spec = {key: receipt[key] for key in ('command_sha256', 'mode', 'timeout_seconds',
                'runner_sha256', 'capacity_policy_sha256', 'resources')}
        receipt['request_sha256'] = hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest()
        path.write_text(json.dumps(receipt))
        result['handoff']['operation']['receipt']['sha256'] = release.file_sha(path)
        with self.assertRaises(release.ContractError):
            self.aggregate([result])

    def test_reconciliation_must_be_explicit_typed_false(self):
        for malformed in ('', 0, None, [], {}, 'false', True):
            with self.subTest(malformed=malformed):
                result = self.result(reconcile_required=malformed)
                self.assertEqual(self.aggregate([result])['accepted'], [])
        result = self.result()
        path = self.root / 'receipt-0.json'
        receipt = release.read_json(path)
        del receipt['reconcile_required']
        path.write_text(json.dumps(receipt))
        result['handoff']['operation']['receipt']['sha256'] = release.file_sha(path)
        self.assertEqual(self.aggregate([result])['accepted'], [])

    def test_duplicate_unknown_and_extra_results_are_rejected(self):
        result = self.result()
        for results in ([result, result], [dict(result, check='other')],
                        [dict(result, unexpected=True)]):
            with self.subTest(results=results):
                with self.assertRaises(release.ContractError):
                    self.aggregate(results)

    def test_advancing_develop_does_not_change_frozen_candidate(self):
        original = release.fingerprint(self.candidate)
        self.source['head'] = '6' * 40
        self.assertEqual(release.fingerprint(self.candidate), original)
        repaired = release.cut(self.source, self.artifacts, self.policy, self.catalog)
        self.assertNotEqual(release.fingerprint(repaired), original)
        with self.assertRaises(release.ContractError):
            release.plan(dict(self.candidate, observed_develop=self.source['head']),
                         self.policy, self.catalog, '4' * 64, '5' * 64)

    def test_integration_profile_cannot_qualify_a_release(self):
        candidate = dict(self.candidate, required_profiles=['integration'])
        with self.assertRaises(release.ContractError):
            release.plan(candidate, self.policy, self.catalog, '4' * 64, '5' * 64)
        with self.assertRaises(release.ContractError):
            release.cut(self.source, self.artifacts, self.policy, self.catalog, 'integration')

    def test_cache_revalidates_output_bytes(self):
        result = self.result()
        self.assertTrue(release.reusable_result(self.plan, result, self.policy, self.catalog, self.root))
        (self.root / 'artifact.txt').write_text('changed output')
        with self.assertRaises(release.ContractError):
            self.aggregate([result])

    def test_cache_revalidates_receipt_bytes_and_source(self):
        result = self.result()
        (self.root / 'receipt-0.json').write_text('{}')
        with self.assertRaises(release.ContractError):
            self.aggregate([result])
        result = self.result()
        result['handoff']['source']['head'] = '6' * 40
        with self.assertRaises(release.ContractError):
            self.aggregate([result])

    def test_changed_catalog_and_plan_cannot_reuse_evidence(self):
        result = self.result()
        altered = dict(self.plan, version=True)
        with self.assertRaises(release.ContractError):
            release.validate_plan(altered, self.policy, self.catalog)
        self.plan['checks'][0]['timeout_seconds'] += 1
        with self.assertRaises(release.ContractError):
            self.aggregate([result])
        self.plan['checks'][0]['timeout_seconds'] -= 1
        self.catalog['profiles']['release']['checks'][0]['argv'].append('--plan')
        with self.assertRaises(release.ContractError):
            self.aggregate([result])

    def test_execution_identity_and_raw_receipt_must_match(self):
        for field in ('command_sha256', 'runner_sha256', 'policy_sha256', 'job_id', 'backend'):
            result = self.result()
            result['handoff']['operation'][field] = 'github' if field == 'backend' else '9' * 64
            with self.subTest(field=field), self.assertRaises(release.ContractError):
                self.aggregate([result])
        result = self.result(resources={})
        with self.assertRaises(release.ContractError):
            self.aggregate([result])

    def test_plan_uses_independent_native_admissible_write_roots(self):
        import windmill_runner
        first, second = self.plan['checks']
        self.assertFalse(windmill_runner.overlap(first['workspace'], second['workspace']))
        for check in (first, second):
            request = release.bridge_request(self.plan, check['key'], self.policy, self.catalog)
            self.assertEqual(windmill_runner.validate_resources(request['resources'], 'write'),
                             check['resources'])
            self.assertLessEqual(len(request['job_id']), 80)
            self.assertEqual(request, release.bridge_request(self.plan, check['key'], self.policy, self.catalog))

    def test_resource_projection_opt_in_does_not_change_runner_request_digest(self):
        check = self.plan['checks'][0]
        request = release.bridge_request(self.plan, check['key'], self.policy, self.catalog)
        self.assertEqual(request['receipt_projection'], 'resources-v1')
        result = self.result()
        receipt = release.read_json(self.root / 'receipt-0.json')
        original_spec = dict(command_sha256=check['command_sha256'], mode=request['mode'],
            timeout_seconds=request['timeout_seconds'], runner_sha256=self.plan['runner_sha256'],
            capacity_policy_sha256=self.plan['capacity_policy_sha256'], resources=request['resources'])
        self.assertEqual(receipt['request_sha256'],
                         hashlib.sha256(json.dumps(original_spec, sort_keys=True).encode()).hexdigest())
        self.assertTrue(release.reusable_result(self.plan, result, self.policy, self.catalog, self.root))

    def test_symlink_and_traversal_evidence_cannot_pass(self):
        result = self.result()
        (self.root / 'outside').symlink_to(self.root / 'receipt-0.json')
        for name in ('../receipt-0.json', 'outside', '/tmp/receipt-0.json'):
            result['handoff']['operation']['receipt']['path'] = name
            with self.subTest(name=name), self.assertRaises(release.ContractError):
                self.aggregate([result])

    def test_actual_shell_guard_rejects_dirty_or_moved_candidate(self):
        repo = self.root / 'repo'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()
        git('init', '-q')
        (repo / 'source.txt').write_text('accepted')
        git('add', 'source.txt')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'candidate')
        self.source.update(head=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'))
        catalog = copy.deepcopy(self.catalog)
        catalog['profiles']['release']['checks'] = [dict(catalog['profiles']['release']['checks'][0], argv=['true'])]
        candidate = release.cut(self.source, self.artifacts, self.policy, catalog)
        plan = release.plan(candidate, self.policy, catalog, '4' * 64, '5' * 64)
        check = plan['checks'][0]
        command = check['command'].replace(check['workspace'], str(repo))
        def execute():
            return subprocess.run(['/bin/sh', '-c', command], capture_output=True).returncode
        self.assertEqual(execute(), 0)
        (repo / 'source.txt').write_text('unreviewed')
        self.assertNotEqual(execute(), 0)
        git('add', 'source.txt')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'develop advances')
        self.assertNotEqual(execute(), 0)

    def test_cli_plan_request_and_incomplete_exit(self):
        files = {'candidate.json': self.candidate, 'plan.json': self.plan, 'results.json': []}
        for name, value in files.items():
            (self.root / name).write_text(json.dumps(value))
        args = [sys.executable, str(release.ROOT / 'tools/delivery/release_qualification.py')]
        request = subprocess.run(args + ['request', '--plan', str(self.root / 'plan.json'),
                                '--check', self.plan['checks'][0]['key']], capture_output=True, text=True)
        self.assertEqual(request.returncode, 0, request.stdout + request.stderr)
        self.assertEqual(json.loads(request.stdout)['action'], 'run')
        aggregate = subprocess.run(args + ['aggregate', '--plan', str(self.root / 'plan.json'),
                                  '--results', str(self.root / 'results.json'),
                                  '--evidence-root', str(self.root)], capture_output=True, text=True)
        self.assertEqual(aggregate.returncode, 1, aggregate.stdout + aggregate.stderr)
        self.assertEqual(json.loads(aggregate.stdout)['status'], 'incomplete')

    def test_publisher_gate_recomputes_exact_complete_summary(self):
        results = [self.result(), self.result(1)]
        summary = self.aggregate(results)
        self.assertEqual(release.validate_qualification(summary, self.plan, results,
                         self.policy, self.catalog, self.root), summary)
        with self.assertRaises(release.ContractError):
            release.validate_qualification(dict(summary, outputs_sha256='9' * 64),
                         self.plan, results, self.policy, self.catalog, self.root)
        with self.assertRaises(release.ContractError):
            release.validate_qualification(summary, self.plan, results[:1],
                         self.policy, self.catalog, self.root)

    def test_post_execution_guard_rejects_command_source_mutation(self):
        # Reuse the real shell-guard test's setup, but execute an otherwise
        # successful command which modifies the tracked candidate.
        repo = self.root / 'post-guard'
        repo.mkdir()
        def git(*args):
            return subprocess.check_output(['git', '-C', str(repo), *args], stderr=subprocess.DEVNULL).decode().strip()
        git('init', '-q')
        (repo / 'source.txt').write_text('accepted')
        git('add', 'source.txt')
        git('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '-qm', 'candidate')
        self.source.update(head=git('rev-parse', 'HEAD'), tree=git('rev-parse', 'HEAD^{tree}'))
        catalog = copy.deepcopy(self.catalog)
        check = catalog['profiles']['release']['checks'][0]
        check['argv'] = [sys.executable, '-c', "from pathlib import Path; Path('source.txt').write_text('changed')"]
        catalog['profiles']['release']['checks'] = [check]
        candidate = release.cut(self.source, self.artifacts, self.policy, catalog)
        plan = release.plan(candidate, self.policy, catalog, '4' * 64, '5' * 64)
        check = plan['checks'][0]
        command = check['command'].replace(check['workspace'], str(repo))
        self.assertNotEqual(subprocess.run(['/bin/sh', '-c', command], capture_output=True).returncode, 0)

    def test_json_duplicate_and_oversize_rejected(self):
        path = self.root / 'invalid.json'
        for content in ('{"a":1,"a":2}', ' ' * (release.LIMIT + 1)):
            path.write_text(content)
            with self.assertRaises(ValueError):
                release.read_json(path)


if __name__ == '__main__':
    unittest.main()
