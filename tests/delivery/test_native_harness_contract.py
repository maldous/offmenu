"""Synthetic v1 contract checks; no jobs, service calls or legacy receipt edits."""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

import native_harness_contract as contract


ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / 'config/delivery-release-policy.json'
SCHEMA = ROOT / 'contracts/schemas/delivery-handoff-v1.schema.json'


class NativeHarnessContractTests(unittest.TestCase):
    def setUp(self):
        self.policy = contract.load_release_policy(POLICY)
        self.ref = {'path': '.delivery/original/receipt.json', 'sha256': 'a' * 64}
        self.source = dict(repository='maldous/offmenu', branch='feature/bounded-contract',
                           base='b' * 40, head='c' * 40, tree='d' * 40,
                           target='develop', policy_sha256=contract.fingerprint(self.policy))
        self.value = dict(version=1, kind='delivery-handoff-v1',
                          issue_id='12345678-1234-1234-1234-123456789abc',
                          project_id='ffb6c7d9-4eff-46eb-a805-99f0cc2edfa0',
                          owner='coding-owner', origin={'kind': 'native-coding-v1', 'evidence': self.ref},
                          source=self.source, outputs=[{'path': 'tools/delivery/contract.py', 'sha256': 'e' * 64}],
                          evidence=[self.ref])
        self.candidate = dict(version=1, kind='release-candidate-v1',
                              source={**self.source, 'branch': 'develop', 'target': 'main'},
                              required_profiles=['unit', 'recovery'],
                              artifacts=[{'path': 'dist/offmenu.tar.gz', 'sha256': 'f' * 64}])

    def validate(self, value=None):
        return contract.validate_handoff(self.value if value is None else value, self.policy)

    def operation(self, status='unknown'):
        return dict(id='original-operation-1', backend='windmill', job_id='original-job-1',
                    status=status, command_sha256='1' * 64, runner_sha256='2' * 64,
                    policy_sha256='3' * 64, receipt=self.ref)

    def review(self):
        return dict(reviewer='independent-reviewer', author=self.value['owner'], verdict='accept',
                    source_sha256=contract.fingerprint(self.value['source']),
                    outputs_sha256=contract.fingerprint(self.value['outputs']), evidence=self.ref)

    def test_positive_native_identity_and_detached_return(self):
        self.value['attempt'] = dict(id='coding-attempt-1', lease_id='lease-1', admission=self.ref)
        result = self.validate()
        self.assertEqual(result, self.value)
        result['source']['head'] = '0' * 40
        self.assertEqual(self.value['source']['head'], 'c' * 40)

    def test_reviewed_and_readonly_origins_need_no_coding_attempt(self):
        for kind in ('reviewed-source-v1', 'native-readonly-review-v1'):
            with self.subTest(kind=kind):
                self.value['origin']['kind'] = kind
                self.value['outputs'] = []
                self.assertNotIn('attempt', self.validate())
                forged = copy.deepcopy(self.value)
                forged['attempt'] = dict(id='fabricated', lease_id='fake', admission=self.ref)
                with self.assertRaises(contract.ContractError):
                    self.validate(forged)

    def test_completed_native_keeps_original_attempt_and_opaque_receipt(self):
        self.value['origin']['kind'] = 'completed-native-validation-v1'
        self.value['attempt'] = dict(id='original-attempt', lease_id='original-lease', admission=self.ref)
        self.assertEqual(self.validate()['attempt']['id'], 'original-attempt')

    def test_missing_and_extra_identity_fields_fail_closed(self):
        for key in self.value:
            with self.subTest(missing=key):
                value = copy.deepcopy(self.value)
                del value[key]
                with self.assertRaises(contract.ContractError):
                    self.validate(value)
        for key, item in [('issue', 'UIF-122'), ('raw_transcript', 'secret'), ('dispatch', True)]:
            with self.subTest(extra=key), self.assertRaises(contract.ContractError):
                self.validate({**self.value, key: item})

    def test_canonical_uuid_not_issue_label_branch_or_empty_uuid(self):
        for key in ('issue_id', 'project_id'):
            for bad in ('UIF-122', self.source['branch'], '0' * 36,
                        '00000000-0000-0000-0000-000000000000', self.value[key].upper()):
                if bad == self.value[key]:
                    continue
                with self.subTest(key=key, bad=bad), self.assertRaises(contract.ContractError):
                    self.validate({**self.value, key: bad})

    def test_wrong_version_origin_and_boolean_version(self):
        for bad in (True, 1.0, 2, '1'):
            with self.subTest(version=bad), self.assertRaises(contract.ContractError):
                self.validate({**self.value, 'version': bad})
        for bad in ('native', 'reviewed-source', '', None):
            value = copy.deepcopy(self.value)
            value['origin']['kind'] = bad
            with self.subTest(origin=bad), self.assertRaises(contract.ContractError):
                self.validate(value)

    def test_source_repository_branch_target_and_hash_validation(self):
        mutations = [('repository', 'other/offmenu'), ('branch', 'main'), ('branch', 'feature/a/'),
                     ('branch', 'feature/a//b'), ('branch', 'feature/../b'), ('target', 'release'),
                     ('head', 'moving-tip'), ('base', 'b' * 39), ('tree', 'D' * 40),
                     ('policy_sha256', 'f' * 64)]
        for key, bad in mutations:
            value = copy.deepcopy(self.value)
            value['source'][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(contract.ContractError):
                self.validate(value)
        value = copy.deepcopy(self.value)
        value['source'].update(branch='develop', target='main')
        self.assertEqual(self.validate(value)['source']['target'], 'main')

    def test_review_binds_exact_source_and_outputs(self):
        self.value['review'] = self.review()
        self.validate()
        for key in ('base', 'head', 'tree', 'branch', 'target', 'policy_sha256'):
            value = copy.deepcopy(self.value)
            value['source'][key] = 'feature/changed' if key == 'branch' else 'f' * (64 if key == 'policy_sha256' else 40)
            with self.subTest(source=key), self.assertRaises(contract.ContractError):
                self.validate(value)
        for change in ('hash', 'path', 'append'):
            value = copy.deepcopy(self.value)
            if change == 'hash':
                value['outputs'][0]['sha256'] = 'f' * 64
            elif change == 'path':
                value['outputs'][0]['path'] = 'tools/delivery/another.py'
            else:
                value['outputs'].append({'path': 'new.py', 'sha256': 'f' * 64})
            with self.subTest(output=change), self.assertRaisesRegex(contract.ContractError, 'review_outputs'):
                self.validate(value)

    def test_self_review_rejected_and_accept_is_only_source_evidence(self):
        for identity in ('coding-owner', 'CODING-OWNER'):
            self.value['review'] = {**self.review(), 'reviewer': identity}
            with self.subTest(identity=identity), self.assertRaisesRegex(contract.ContractError, 'independent_reviewer'):
                self.validate()
        self.value['review'] = self.review()
        self.assertNotIn('accepted_delivery', self.validate())
        self.value['review']['author'] = self.value['review']['reviewer']
        with self.assertRaises(contract.ContractError):
            self.validate()

    def test_unknown_effect_retains_operation_job_and_never_becomes_success(self):
        self.value['operation'] = self.operation()
        self.value['effect'] = {'operation_id': 'original-operation-1', 'status': 'unknown'}
        result = self.validate()
        self.assertEqual(result['operation']['id'], 'original-operation-1')
        self.assertEqual(result['operation']['job_id'], 'original-job-1')
        self.assertEqual(result['effect']['status'], 'unknown')
        self.assertNotIn('retry', result)
        for key, bad in [('operation_id', 'replacement-operation'), ('status', 'verified')]:
            value = copy.deepcopy(self.value)
            value['effect'][key] = bad
            with self.subTest(key=key), self.assertRaises(contract.ContractError):
                self.validate(value)
        del self.value['operation']
        with self.assertRaises(contract.ContractError):
            self.validate()

    def test_effect_state_consistency(self):
        pairs = [('not-attempted', 'planned'), ('pending', 'submitted'), ('pending', 'running'),
                 ('unknown', 'submitted'), ('unknown', 'unknown'), ('verified', 'succeeded'),
                 ('failed', 'failed'), ('failed', 'cancelled')]
        for effect, status in pairs:
            self.value['operation'] = self.operation(status)
            self.value['effect'] = dict(operation_id='original-operation-1', status=effect)
            with self.subTest(effect=effect, operation=status):
                self.validate()
        self.value['operation'] = self.operation('unknown')
        self.value['effect'] = dict(operation_id='original-operation-1', status='failed')
        with self.assertRaises(contract.ContractError):
            self.validate()

    def test_blank_attempt_job_and_review_identities_rejected(self):
        values = []
        for key in ('id', 'lease_id'):
            values.append({**self.value, 'attempt': {**dict(id='attempt', lease_id='lease', admission=self.ref), key: ' '}})
        for key in ('id', 'job_id'):
            values.append({**self.value, 'operation': {**self.operation(), key: ' '}})
        for key in ('reviewer', 'author'):
            values.append({**self.value, 'review': {**self.review(), key: ' '}})
        for value in values:
            with self.subTest(value=value.keys()), self.assertRaises(contract.ContractError):
                self.validate(value)

    def test_legacy_byte_digest_is_not_reinterpreted_or_read(self):
        original = b'{ "legacy": true, "operation": "original" }\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'legacy.json'
            path.write_bytes(original)
            ref = {'path': str(path), 'sha256': hashlib.sha256(original).hexdigest()}
            self.value['origin'] = {'kind': 'completed-native-validation-v1', 'evidence': ref}
            self.value['operation'] = self.operation('succeeded')
            self.value['operation']['policy_sha256'] = hashlib.sha256(b'legacy policy bytes').hexdigest()
            with patch.object(Path, 'open', side_effect=AssertionError('evidence must stay opaque')):
                result = self.validate()
            self.assertEqual(result['origin']['evidence'], ref)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(result['operation']['policy_sha256'], self.value['operation']['policy_sha256'])

    def test_paths_are_bounded_local_canonical_and_outputs_relative(self):
        for bad in ('https://secret@example.com/x', '../escape', 'a/../b', '/a//b', 'a/./b',
                    '/a/', 'C:\\private', 'a\nsecret', '~/.token', 'x?token=secret', ' x', '/', '.'):
            value = copy.deepcopy(self.value)
            value['evidence'] = [{'path': bad, 'sha256': 'a' * 64}]
            with self.subTest(path=bad), self.assertRaises(contract.ContractError):
                self.validate(value)
        value = copy.deepcopy(self.value)
        value['evidence'] = [{'path': '/private/absent/receipt.json', 'sha256': 'a' * 64}]
        self.validate(value)
        value['outputs'] = value['evidence']
        with self.assertRaisesRegex(contract.ContractError, 'relative_output_path'):
            self.validate(value)

    def test_duplicate_paths_with_different_hashes_and_extra_ref_data_rejected(self):
        for key in ('outputs', 'evidence'):
            value = copy.deepcopy(self.value)
            value[key].append({**value[key][0], 'sha256': 'f' * 64})
            with self.subTest(key=key), self.assertRaises(contract.ContractError):
                self.validate(value)
        value = copy.deepcopy(self.value)
        value['origin']['evidence'] = {**self.ref, 'raw_log': 'secret'}
        with self.assertRaises(contract.ContractError):
            self.validate(value)

    def test_fingerprint_canonical_json_and_policy_identity(self):
        value = {'z': 'é', 'a': [1, None, True]}
        expected = hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        self.assertEqual(contract.fingerprint(value), expected)
        self.assertEqual(contract.fingerprint(value), contract.fingerprint({'a': [1, None, True], 'z': 'é'}))
        self.assertNotEqual(contract.fingerprint(self.policy), hashlib.sha256(POLICY.read_bytes()).hexdigest())
        self.assertEqual(self.validate()['source']['policy_sha256'], contract.fingerprint(self.policy))

    def test_non_json_nan_cycles_depth_and_size_are_bounded(self):
        cycle = []
        cycle.append(cycle)
        depth = None
        for _ in range(20):
            depth = [depth]
        for bad in (float('nan'), float('inf'), {1: 'key'}, object(), (1,), 2**100,
                    'x' * 4097, list(range(129)), cycle, depth, ['x' * 4096] * 128):
            with self.subTest(kind=type(bad).__name__), self.assertRaises(contract.ContractError):
                contract.fingerprint(bad)
        with self.assertRaises(contract.ContractError) as raised:
            self.validate({'private secret input': 'sensitive transcript'})
        self.assertLess(len(str(raised.exception)), 80)
        self.assertNotIn('secret', str(raised.exception))

    def test_policy_cannot_relax_holds_or_change_v1_shape(self):
        for key, change in [('activation', {'github_actions': True}),
                            ('recovery', {'unknown_effect_requires_reconciliation': False}),
                            ('release', {'tag_updates_allowed': True}),
                            ('ownership', {'integration_writers': True})]:
            value = copy.deepcopy(self.policy)
            value[key].update(change)
            with self.subTest(section=key), self.assertRaises(contract.ContractError):
                contract.validate_handoff(self.value, value)
        for extra in ({**self.policy, 'new_flag': True}, {**self.policy, 'version': True}):
            with self.assertRaises(contract.ContractError):
                contract.validate_release_candidate(self.candidate, extra)

    def test_policy_loader_rejects_duplicate_json_oversize_bad_json_and_missing_file(self):
        for raw in (b'{"version":1,"version":1}', b'{', b'x' * (contract.MAX_BYTES + 1), b'\xff'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'policy.json'
                path.write_bytes(raw)
                with self.subTest(bytes=len(raw)), self.assertRaises(contract.ContractError):
                    contract.load_release_policy(path)
        with self.assertRaisesRegex(contract.ContractError, 'policy_read'):
            contract.load_release_policy('/no/such/policy.json')

    def test_frozen_candidate_independent_of_moving_develop(self):
        frozen = contract.validate_release_candidate(self.candidate, self.policy)
        identity = contract.fingerprint(frozen)
        observations = {'develop_head': '1' * 40}
        observations['develop_head'] = '2' * 40
        self.assertEqual(contract.fingerprint(contract.validate_release_candidate(frozen, self.policy)), identity)
        for key, bad in [('head', 'e' * 40), ('tree', 'e' * 40), ('base', 'e' * 40)]:
            changed = copy.deepcopy(frozen)
            changed['source'][key] = bad
            self.assertNotEqual(contract.fingerprint(contract.validate_release_candidate(changed, self.policy)), identity)
        changed = copy.deepcopy(frozen)
        changed['artifacts'][0]['sha256'] = 'e' * 64
        self.assertNotEqual(contract.fingerprint(contract.validate_release_candidate(changed, self.policy)), identity)
        self.assertEqual(frozen, self.candidate)

    def test_release_candidate_rejects_mutable_or_incomplete_assertions(self):
        for key in ('source', 'artifacts', 'required_profiles'):
            value = copy.deepcopy(self.candidate)
            del value[key]
            with self.subTest(missing=key), self.assertRaises(contract.ContractError):
                contract.validate_release_candidate(value, self.policy)
        for key in ('accepted', 'develop_head', 'candidate_id', 'release_tag'):
            with self.subTest(extra=key), self.assertRaises(contract.ContractError):
                contract.validate_release_candidate({**self.candidate, key: True}, self.policy)
        for change in ({'required_profiles': []}, {'required_profiles': ['unit', 'unit']},
                       {'required_profiles': ['Main Branch']}, {'artifacts': []}):
            with self.subTest(change=change), self.assertRaises(contract.ContractError):
                contract.validate_release_candidate({**self.candidate, **change}, self.policy)
        value = copy.deepcopy(self.candidate)
        value['source']['branch'] = 'feature/unreleased'
        with self.assertRaises(contract.ContractError):
            contract.validate_release_candidate(value, self.policy)

    def test_published_schema_resolves_locally_and_matches_structural_contract(self):
        schema = json.loads(SCHEMA.read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        validator.validate(self.value)
        validator = Draft202012Validator({'$ref': '#/$defs/releaseCandidate', '$defs': schema['$defs']})
        validator.validate(self.candidate)
        self.assertFalse(Draft202012Validator(schema).is_valid({**self.value, 'extra': True}))


if __name__ == '__main__':
    unittest.main()
