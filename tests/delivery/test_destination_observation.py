"""Offline-only negative paths for release destination identity (UIF-269)."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools/delivery'))
from destination_observation import ObservationReport, ObservationRequest, observe_candidate_destination
import release_qualification as release


class DestinationObservationTests(unittest.TestCase):
    def setUp(self):
        self.policy = release.load_release_policy(release.ROOT / 'config/delivery-release-policy.json')
        catalog = release.read_json(release.ROOT / 'config/release-validation-profile.json')
        source = dict(repository='maldous/offmenu', branch='develop', target='main',
                      base='1' * 40, head='2' * 40, tree='3' * 40,
                      policy_sha256=release.fingerprint(self.policy))
        artifact = dict(path='synthetic/worker.mjs', sha256='4' * 64)
        self.candidate = release.cut(source, [artifact], self.policy, catalog)
        self.destination = dict(channel='web', environment='staging-fixture',
                                account_id='synthetic-account', destination_id='synthetic-site')
        self.proof = dict(destination=dict(self.destination),
                          credential_binding=dict(self.destination),
                          candidate_sha256=release.fingerprint(self.candidate),
                          source_head=source['head'], source_tree=source['tree'],
                          artifact=artifact, observed_at=90)
        self.reader = Mock(return_value={'result': 'synthetic-observation'})

    def check(self, proof, **overrides):
        options = dict(destination=self.destination, now=100, max_age_seconds=10, reader=self.reader,
                       approved_pairs=frozenset({('web', 'staging-fixture')}))
        options.update(overrides)
        return observe_candidate_destination(self.candidate, self.policy, proof=proof, **options)

    def test_exact_frozen_source_artifact_destination_allows_one_observation(self):
        outcome = self.check(self.proof)
        self.assertIsInstance(outcome, ObservationReport)
        self.assertEqual(outcome.stage, 'observation-reported')
        self.assertIs(outcome.publication_authorized, False)
        self.reader.assert_called_once_with(ObservationRequest(
            'web', 'staging-fixture', 'synthetic-account', 'synthetic-site',
            self.proof['candidate_sha256'], '2' * 40, '3' * 40,
            'synthetic/worker.mjs', '4' * 64,
        ))

    def test_missing_malformed_or_wrong_credential_binding_never_calls_reader(self):
        for binding in (None, {}, {**self.destination, 'environment': 'wrong-env'},
                        {**self.destination, 'channel': 'other'},
                        {**self.destination, 'account_id': 'other'},
                        {**self.destination, 'destination_id': 'other'},
                        {**self.destination, 'destination_id': 'synthetic invalid value'},
                        {**self.destination, 'unexpected_field': 'synthetic'}):
            with self.subTest(binding=binding):
                with self.assertRaises(release.ContractError):
                    self.check({**self.proof, 'credential_binding': binding})
                self.reader.assert_not_called()
        missing = dict(self.proof)
        del missing['credential_binding']
        with self.assertRaises(release.ContractError):
            self.check(missing)
        self.reader.assert_not_called()

    def test_missing_unknown_or_malformed_approved_pair_never_calls_reader(self):
        for pairs in (None, frozenset(), {('web', 'staging-fixture')},
                      frozenset({('web', 'other-env')}), frozenset({('mcp', 'staging-fixture')}),
                      frozenset({('web', '*')}), frozenset({'web'}),
                      frozenset({('web', 'staging-fixture', 'extra')})):
            with self.subTest(pairs=pairs), self.assertRaises(release.ContractError):
                self.check(self.proof, approved_pairs=pairs)
            self.reader.assert_not_called()

    def test_mock_result_cannot_promote_observation_to_publication_authority(self):
        self.reader.return_value = {'stage': 'publish-approved', 'publication_authorized': True}
        outcome = self.check(self.proof)
        self.assertEqual(outcome.stage, 'observation-reported')
        self.assertIs(outcome.publication_authorized, False)
        self.assertFalse(hasattr(outcome, 'reader_result'))
        self.reader.assert_called_once()

    def test_mismatched_destination_source_artifact_and_time_never_call_reader(self):
        for delta in (
            {'destination': {**self.destination, 'environment': 'different-environment'}},
            {'candidate_sha256': '5' * 64}, {'source_head': '6' * 40}, {'source_tree': '7' * 40},
            {'artifact': {'path': 'synthetic/worker.mjs', 'sha256': '8' * 64}},
            {'artifact': {'path': 'synthetic/not-frozen.mjs', 'sha256': '4' * 64}},
            {'artifact': {'path': 'synthetic/worker.mjs', 'sha256': 'bad-format'}},
            {'observed_at': 89}, {'observed_at': 101}, {'observed_at': True},
        ):
            with self.subTest(field=next(iter(delta))):
                with self.assertRaises(release.ContractError):
                    self.check({**self.proof, **delta})
                self.reader.assert_not_called()
        for parameters in (dict(max_age_seconds=0), dict(max_age_seconds=True), dict(now=False),
                           dict(now=89), dict(now=101)):
            with self.subTest(parameters=parameters), self.assertRaises(release.ContractError):
                self.check(deepcopy(self.proof), **parameters)
            self.reader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
