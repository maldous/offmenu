"""Offline retained PUBLIC metadata only; no producer lifecycle is inferred.

Request/owner/observer identities and attestation digests below are fixture-only
syntheses: original producer bindings are unavailable. They are not release or
independent-review acceptance. No raw release package or runtime state is read.
"""
import copy
from dataclasses import FrozenInstanceError, replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.delivery.effect_observations import (
    AssetPin, EffectBinding, EffectContext, TrustedEvidence,
    observation_digest, project_effect,
)
from offmenu.delivery.engine import DeliveryError, digest
from offmenu.delivery.status import inspect_task


# Fixed minimal constants transcribed only from sanitized-release-metadata.json.
RELEASES = (
    (210, '7780c8602b52e9f2fc7e6a38e5d08d8ad74f09e1',
     'e4e1385ec81bc0a97fa52bbf1f29fbd6c5a16a77a325d664856243ac7c933237',
     '09d8d2a3-c017-43e6-8039-fdc1a70da58b', 'd54f38f3-274f-42d8-bcf9-fe74bf93cdab',
     '9745e6a6ef21ac0f3275b58782724a9d34f8c50b768107f92b2db3c17b905e5c',
     'b187c38999c12da51166b6ea16ce6eaed897d1f0507f2bd1891f6e165f69a3b8',
     1793320948.722761),
    (211, '2c70e7f01fb3e5ff9cc6c8084b79101f5a7aec21',
     '5dff04cd101d78ad058a09023cda01dcf1b86fde8eba87a43e74c29e4fdfeeef',
     '926a5f85-b519-419e-8d08-9db0eadf6dd6', '452a263d-2eed-41f4-a0c5-403751f8297a',
     '58c74f712b0a15878ab6a117b1dd2bfbeed68fefde2ea223a9baa16e5f90baa8',
     'a4622eff15ffbecd4fb45b179540c09c4156a92efdbac83731533473e87424ef',
     1793323861.450895),
)
OBSERVER = 'fixture-only-independent-observer'


def fixture(index=1):
    version, source, package, version_id, deployment, pin, receipt, at = RELEASES[index]
    binding = EffectBinding('fixture-request', 'fixture-owner', source, package,
                            version, version_id, deployment, (AssetPin('/app.js', pin),))
    observation = {
        'schema_version': 1,
        'binding': {key: value for key, value in vars(binding).items() if key != 'assets'},
        'observed_at': at, 'receipt_sha256': receipt,
        'assets': [{'name': '/app.js', 'sha256': pin, 'raw_sha256': pin, 'status': 200}],
    }
    context = EffectContext(binding, at + 10, 60, OBSERVER,
                            (TrustedEvidence('deployment', binding, OBSERVER,
                                             observation_digest(observation)),))
    return observation, context


def attest(observation, context):
    """Fixture-only owner attestation; production must obtain independent evidence."""
    return replace(context, evidence=(TrustedEvidence(
        'deployment', context.expected, OBSERVER, observation_digest(observation)),))


class EffectObservationTests(unittest.TestCase):
    def test_retained_versions_keep_six_axes_and_selective_phases(self):
        for index in (0, 1):
            with self.subTest(version=RELEASES[index][0]):
                observation, context = fixture(index)
                result = project_effect(observation, context, ('deployment', 'served_bytes'))
                self.assertEqual(len(result['axes']), 6)
                self.assertEqual(result['axes']['deployment'], 'observed')
                self.assertEqual(result['axes']['candidate_binding'], 'bound')
                self.assertEqual(result['axes']['served_bytes'], 'equal')
                self.assertTrue(result['normalized_pins_match'])
                self.assertEqual(result['axes']['functional_acceptance'], 'unknown')
                self.assertEqual(result['axes']['source_acceptance'], 'unknown')
                self.assertEqual(result['axes']['lifecycle'], {'owner': 'unknown', 'child': 'unknown'})
                self.assertEqual({name for name, state in result['phases'].items() if state == 'closed'},
                                 {'deployment', 'served_bytes'})
                self.assertEqual(result['phases']['candidate_binding'], 'open')
                self.assertEqual(json.loads(json.dumps(result))['receipt_sha256'], RELEASES[index][6])

    def test_default_has_no_observation_authority(self):
        observation, context = fixture()
        for observer in (None, OBSERVER):
            untrusted = EffectContext(context.expected, context.now, 60, observer)
            result = project_effect(observation, untrusted, ('deployment', 'served_bytes'))
            self.assertEqual(result['axes']['deployment'], 'unknown')
            self.assertFalse(result['normalized_pins_match'])
            self.assertTrue(all(value == 'open' for value in result['phases'].values()))

    def test_raw_equality_is_not_normalized_equality(self):
        for raw in (None, '0' * 64):
            observation, context = fixture()
            observation['assets'][0]['raw_sha256'] = raw
            result = project_effect(observation, attest(observation, context), ('served_bytes',))
            self.assertTrue(result['normalized_pins_match'])
            self.assertEqual(result['axes']['served_bytes'], 'unknown')
            self.assertEqual(result['phases']['served_bytes'], 'open')

    def test_separate_functional_source_and_partial_lifecycle_evidence(self):
        observation, context = fixture()
        source_only = TrustedEvidence('source_acceptance', context.expected, OBSERVER, '2' * 64)
        result = project_effect(observation, replace(context, evidence=(source_only,)),
                                ('source_acceptance', 'functional_acceptance', 'deployment'))
        self.assertEqual(result['phases']['source_acceptance'], 'closed')
        self.assertEqual(result['axes']['functional_acceptance'], 'unknown')
        self.assertEqual(result['phases']['functional_acceptance'], 'open')
        self.assertEqual(result['phases']['deployment'], 'open')
        extra = tuple(TrustedEvidence(axis, context.expected, OBSERVER, digit * 64)
                      for axis, digit in (('functional_acceptance', '1'), ('source_acceptance', '2')))
        lifecycle = TrustedEvidence('lifecycle', context.expected, OBSERVER, '3' * 64,
                                    owner_state='terminal')
        context = replace(context, evidence=context.evidence + extra + (lifecycle,))
        result = project_effect(observation, context, ('functional_acceptance', 'lifecycle'))
        self.assertEqual(result['axes']['functional_acceptance'], 'accepted')
        self.assertEqual(result['phases']['functional_acceptance'], 'closed')
        self.assertEqual(result['axes']['source_acceptance'], 'accepted')
        self.assertEqual(result['phases']['source_acceptance'], 'open')
        self.assertEqual(result['axes']['lifecycle'], {'owner': 'terminal', 'child': 'unknown'})
        self.assertEqual(result['phases']['lifecycle'], 'open')
        stopped = replace(lifecycle, child_state='gone')
        result = project_effect(observation, replace(context, evidence=context.evidence[:-1] + (stopped,)),
                                ('lifecycle',))
        self.assertEqual(result['phases']['lifecycle'], 'closed')
        self.assertEqual(result['phases']['deployment'], 'open')

    def test_v210_v211_substitution_and_reused_deployment_are_rejected(self):
        old, _ = fixture(0)
        observation, context = fixture()
        with self.assertRaises(ValueError):
            project_effect(old, context)
        for key, value in old['binding'].items():
            if value != observation['binding'][key]:
                changed = copy.deepcopy(observation)
                changed['binding'][key] = value
                with self.subTest(field=key), self.assertRaises(ValueError):
                    project_effect(changed, context)
        changed = copy.deepcopy(observation)
        changed['binding']['request_id'] = 'other-request'
        with self.assertRaises(ValueError):
            project_effect(changed, context)

    def test_missing_extra_nested_and_self_authority_fields_are_rejected(self):
        observation, context = fixture()
        for container, key, value in (
                ((), 'success', True), ((), 'observer', OBSERVER), ((), 'authority', True),
                ((), 'functional_acceptance', True), ((), 'max_age_seconds', 3600),
                (('binding',), 'extra', {}), (('assets', 0), 'child_tree_gone', True)):
            changed = copy.deepcopy(observation)
            target = changed
            for part in container:
                target = target[part]
            target[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                project_effect(changed, context)
        for key in observation:
            changed = copy.deepcopy(observation)
            del changed[key]
            with self.subTest(missing=key), self.assertRaises(ValueError):
                project_effect(changed, context)

    def test_bounded_freshness_and_strict_timestamp_types(self):
        observation, context = fixture()
        for at in (context.now - 61, context.now + .01, float('nan'), float('inf'),
                   True, 'now', -1, 10**1000):
            changed = {**observation, 'observed_at': at}
            with self.subTest(at=at), self.assertRaises(ValueError):
                project_effect(changed, context)
        for key, values in (('now', (True, float('nan'), -1, 10**13)),
                            ('max_age_seconds', (True, 0, 3601, 1.5))):
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    replace(context, **{key: value})
        boundary = replace(context, now=observation['observed_at'] + 60)
        self.assertEqual(project_effect(observation, boundary)['axes']['deployment'], 'observed')

    def test_pin_sets_hashes_status_and_versions_are_strict(self):
        observation, context = fixture()
        variants = []
        for assets in ([], observation['assets'] * 2, [{'name': '/extra.js', **{
                key: value for key, value in observation['assets'][0].items() if key != 'name'}}]):
            variants.append({**observation, 'assets': assets})
        for key, values in (('sha256', ('bad', 'A' * 64, '0' * 64)),
                            ('raw_sha256', ('bad', True)), ('status', (True, 600, '200'))):
            for value in values:
                changed = copy.deepcopy(observation)
                changed['assets'][0][key] = value
                variants.append(changed)
        for version in (True, 0, 212, '211'):
            changed = copy.deepcopy(observation)
            changed['binding']['version_number'] = version
            variants.append(changed)
        for schema in (True, 2, '1'):
            variants.append({**observation, 'schema_version': schema})
        variants.append({**observation, 'receipt_sha256': 'bad'})
        for changed in variants:
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                project_effect(changed, context)
        changed = copy.deepcopy(observation)
        changed['assets'][0]['sha256'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'Asset pin mismatch'):
            project_effect(changed, attest(changed, context))
        for assets in ((), [], (context.expected.assets[0],) * 2):
            with self.assertRaises(ValueError):
                replace(context.expected, assets=assets)
        for key, value in (('source_commit', 'a' * 39), ('package_sha256', 'a' * 63),
                           ('owner', ''), ('request_id', '../path'), ('version_id', 'bad'),
                           ('deployment_id', 'bad'), ('version_number', True)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                replace(context.expected, **{key: value})
        with self.assertRaises(ValueError):
            AssetPin('/app.js', '')
        with self.assertRaises(ValueError):
            AssetPin('/../private', '0' * 64)

    def test_digest_observer_and_evidence_cannot_be_reused(self):
        observation, context = fixture()
        changed = copy.deepcopy(observation)
        changed['assets'][0]['raw_sha256'] = None
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            project_effect(changed, context)
        for item in (replace(context.evidence[0], observer='impostor'),
                     replace(context.evidence[0], binding=replace(context.expected, owner='other')),
                     replace(context.evidence[0], axis='functional_acceptance')):
            with self.assertRaises(ValueError):
                replace(context, evidence=context.evidence + (item,))
        with self.assertRaises(ValueError):
            replace(context, approved_observer=None)

    def test_inputs_and_results_are_detached_and_frozen(self):
        observation, context = fixture()
        original = copy.deepcopy(observation)
        result = project_effect(observation, context)
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(observation, original)
        with self.assertRaises(FrozenInstanceError):
            context.expected.owner = 'changed'
        with self.assertRaises(FrozenInstanceError):
            context.expected.assets[0].sha256 = '0' * 64
        result['binding']['assets'][0]['sha256'] = '0' * 64
        result['axes']['deployment'] = 'changed'
        self.assertEqual(project_effect(observation, context)['axes']['deployment'], 'observed')
        self.assertEqual(context.expected.assets[0].sha256, RELEASES[1][5])
        observation['binding']['owner'] = 'changed'
        self.assertEqual(context.expected.owner, 'fixture-owner')

    def test_phase_names_are_finite_and_explicit(self):
        observation, context = fixture()
        for phases in (('umbrella_done',), ('deployment',) * 2, ['deployment'], (True,)):
            with self.assertRaises(ValueError):
                project_effect(observation, context, phases)


class StatusEffectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offmenu-effect-status-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.observation, self.context = fixture()
        self.task = {'version': 1, 'id': 'fixture-request', 'owner': 'fixture-owner',
                     'purpose': 'Offline read-only effect fixture',
                     'base_revision': RELEASES[1][1], 'checks': [
                         {'id': 'check', 'argv': ['unused'], 'timeout': 1}],
                     'accepted_outputs': {'app.js': RELEASES[1][5]}}
        # Fixture Git identity only; inspection still reads actual fixture receipts
        # and bytes. No Engine, execution or graph checkpoint is constructed.
        self.git_patch = patch('offmenu.delivery.status.git', side_effect=lambda root, *args:
                               'feature/fixture' if args[0] == 'branch' else RELEASES[1][1])
        self.git_patch.start()
        self.addCleanup(self.git_patch.stop)

    def snapshot(self):
        return {str(path.relative_to(self.root)): path.read_bytes()
                for path in self.root.rglob('*') if path.is_file()}

    def inspect(self, **kwargs):
        before = self.snapshot()
        result = inspect_task(self.root, self.task, effect_observation=self.observation,
                              effect_context=self.context, **kwargs)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(result['authority'], 'observation_only')
        self.assertFalse(result['source_and_execution_evidence_verified'])
        return result

    def bind(self):
        directory = self.root / '.delivery' / self.task['id']
        directory.mkdir(parents=True)
        (directory / 'binding.json').write_text(json.dumps({
            'task_sha256': digest(self.task), 'root': str(self.root),
            'owner': self.task['owner'], 'branch': 'feature/fixture'}))
        return directory

    def test_missing_local_binding_stays_not_found_with_effect_known(self):
        default = inspect_task(self.root, self.task)
        self.assertNotIn('external_effect', default)
        result = self.inspect(effect_phases=('deployment', 'functional_acceptance'))
        self.assertEqual(result['recorded_status'], 'not_found')
        self.assertFalse(result['acceptance_record_present'])
        self.assertFalse(result['identity_matches'])
        self.assertEqual(result['reasons'], ['binding_not_found'])
        self.assertEqual(result['external_effect']['axes']['deployment'], 'observed')
        self.assertEqual(result['external_effect']['phases']['functional_acceptance'], 'open')
        self.assertFalse((self.root / '.delivery').exists())

    def test_current_bound_task_receipt_and_effect_remain_distinct(self):
        directory = self.bind()
        (directory / 'check.json').write_text('{"status":"uncertain"}')
        result = self.inspect(effect_phases=('deployment', 'served_bytes'))
        self.assertTrue(result['identity_matches'])
        self.assertFalse(result['outputs_match'])
        self.assertEqual(result['recorded_status'], 'not_accepted')
        self.assertEqual(result['reconciliation_required'], ['check'])
        self.assertEqual(result['external_effect']['axes']['served_bytes'], 'equal')
        self.assertEqual(result['external_effect']['axes']['lifecycle']['child'], 'unknown')
        self.assertFalse((directory / 'graph.sqlite').exists())
        (directory / 'accepted.json').write_text(json.dumps({
            'task_sha256': digest(self.task), 'revision': self.task['base_revision'],
            'owner': self.task['owner'], 'branch': 'feature/fixture',
            'outputs': self.task['accepted_outputs'], 'status': 'accepted'}))
        result = self.inspect()
        self.assertEqual(result['recorded_status'], 'accepted')
        self.assertEqual(result['external_effect']['axes']['source_acceptance'], 'unknown')
        self.assertEqual(result['external_effect']['axes']['functional_acceptance'], 'unknown')

    def test_task_context_caller_mismatch_and_current_identity_drift_fail_closed(self):
        for key, value in (('request_id', 'unrelated'), ('owner', 'unrelated'),
                           ('source_commit', RELEASES[0][1])):
            expected = replace(self.context.expected, **{key: value})
            context = EffectContext(expected, self.context.now, 60)
            with self.subTest(key=key), self.assertRaises(DeliveryError):
                inspect_task(self.root, self.task, effect_observation=self.observation,
                             effect_context=context)
        with self.assertRaises(DeliveryError):
            inspect_task(self.root, self.task, effect_observation=self.observation)
        self.bind()
        before = self.snapshot()
        with patch('offmenu.delivery.status.git', return_value='develop'):
            with self.assertRaisesRegex(DeliveryError, 'current task binding mismatch'):
                self.inspect()
        self.assertEqual(before, self.snapshot())

    def test_untrusted_success_cannot_supply_functional_acceptance_via_status(self):
        self.bind()
        self.observation['success'] = True
        before = self.snapshot()
        with self.assertRaises(DeliveryError):
            self.inspect(effect_phases=('functional_acceptance',))
        self.assertEqual(before, self.snapshot())
        del self.observation['success']
        functional = TrustedEvidence('functional_acceptance', self.context.expected, OBSERVER, 'f' * 64)
        self.context = replace(self.context, evidence=self.context.evidence + (functional,))
        result = self.inspect(effect_phases=('functional_acceptance',))
        self.assertEqual(result['external_effect']['phases']['functional_acceptance'], 'closed')
        self.assertEqual(result['recorded_status'], 'not_accepted')
