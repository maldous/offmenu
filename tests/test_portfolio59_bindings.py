import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio59_bindings import bind_portfolio, COUNTRIES, DATA_TYPES

NOW = '2026-10-18T00:00:00Z'


def authored_planner(metadata, *, now):
    """Authored seam fixture, NOT the missing production/shared cache planner."""
    return {'decision': 'reuse', 'minimumReuseSeconds': 2592000,
            'downloadAllowed': False, 'originalAcquiredAt': metadata['originalAcquiredAt']}


class Portfolio59BindingTests(unittest.TestCase):
    def fixture(self):
        raw = canonical({'source': 'prices', 'release': '2026-10-12',
                         'native': {'unit': None, 'price': '0.00', 'pricePer': 'KILOGRAM'}})
        source = {'sourceId': 'prices', 'releaseId': '2026-10-12', 'scope': 'authored-metadata',
                  'sourceManifestSha256': sha(raw),
                  'documents': {'manifest.json': {'path': 'fixture-metadata.json',
                                                 'sha256': sha(raw), 'role': 'manifest'}},
                  'fields': {'source': {'document': 'manifest.json', 'selector': '/source',
                                       'expected': 'prices'},
                             'release': {'document': 'manifest.json', 'selector': '/release',
                                        'expected': '2026-10-12'},
                             'native': {'document': 'manifest.json', 'selector': '/native'}},
                  'applicability': {c: ['prices/baskets'] for c in COUNTRIES},
                  'originalAcquiredAt': '2026-10-12T00:00:00Z',
                  'validatedAt': '2026-10-17T00:00:00Z', 'holds': [],
                  'requiredInputs': [], 'unknowns': ['Authored metadata fixture only']}
        return {'schemaVersion': 'offmenu-portfolio59-bindings/1',
                'countries': list(COUNTRIES), 'dataTypes': list(DATA_TYPES),
                'sources': [source]}, {'fixture-metadata.json': raw}

    def run_binding(self, config=None, evidence=None, **kwargs):
        default_config, default_evidence = self.fixture()
        return bind_portfolio(config if config is not None else default_config,
                              evidence if evidence is not None else default_evidence,
                              now=NOW, **kwargs)

    def test_valid_binding_has_shared_metadata_origins_no_admission(self):
        result = self.run_binding(cache_planner=authored_planner)
        source = result['sources'][0]
        self.assertEqual(source['stage']['status'], 'succeeded')
        self.assertTrue(source['metadataBinding']['bound'])
        self.assertEqual(source['metadataRecord']['data']['native'],
                         {'unit': None, 'price': '0.00', 'pricePer': 'KILOGRAM'})
        self.assertEqual(field_origin_errors(source['metadataRecord'],
                         {'manifest.json': source['sourceManifestSha256']}), [])
        self.assertEqual(source['metadataRecord']['provenance']['fieldOrigins']
                         ['/data/native/unit']['sourceField'], '/native/unit')
        self.assertFalse(source['dataBodyProcessingAllowed'])
        self.assertFalse(source['datasetAccepted'])
        self.assertEqual(len(result['countryTypes']), 24)
        self.assertEqual(sum(bool(c['sourceIds']) for c in result['countryTypes']), 4)
        self.assertTrue(all(not c['datasetAccepted'] for c in result['countryTypes']))

    def test_missing_metadata_is_explicit_not_an_empty_success(self):
        source = self.run_binding(evidence={}, cache_planner=authored_planner)['sources'][0]
        self.assertEqual(source['stage']['status'], 'unsupported')
        self.assertIn('metadata-document-missing', source['diagnostics'])
        self.assertIn('metadata-field-inventory-incomplete', source['diagnostics'])

    def test_changed_metadata_pin_is_stale_not_revalidated_or_repaired(self):
        config, evidence = self.fixture()
        evidence['fixture-metadata.json'] += b' '
        result = self.run_binding(config, evidence, cache_planner=authored_planner)
        self.assertIn('metadata-input-stale', result['sources'][0]['diagnostics'])
        self.assertFalse(result['sources'][0]['metadataBinding']['bound'])
        self.assertEqual(result['networkRequests'], 0)

    def test_held_source_never_calls_planner(self):
        config, evidence = self.fixture()
        config['sources'][0]['holds'] = ['explicit-source-read-denial']
        def forbidden(*args, **kwargs):
            self.fail('Held source called planner')
        source = self.run_binding(config, evidence, cache_planner=forbidden)['sources'][0]
        self.assertEqual(source['stage']['status'], 'held')
        self.assertEqual(source['holds'], ['explicit-source-read-denial'])

    def test_malformed_one_source_does_not_hide_independent_source(self):
        config, evidence = self.fixture()
        second = copy.deepcopy(config['sources'][0])
        second['sourceId'] = 'wfp-food-prices-for-libya'
        malformed = b'{"native":NaN}'
        second['sourceManifestSha256'] = sha(malformed)
        second['documents'] = {'manifest.json': {'path': 'bad.json',
                                               'sha256': sha(malformed), 'role': 'manifest'}}
        config['sources'].append(second)
        evidence['bad.json'] = malformed
        result = self.run_binding(config, evidence, cache_planner=authored_planner)
        self.assertEqual(result['sources'][0]['stage']['status'], 'succeeded')
        self.assertEqual(result['sources'][1]['stage']['status'], 'failed')
        self.assertIn('metadata-document-malformed', result['sources'][1]['diagnostics'])

    def test_duplicate_keys_and_overflow_are_malformed(self):
        for raw in (b'{"source":1,"source":2}', b'{"number":1e9999}'):
            config, _ = self.fixture()
            config['sources'][0]['sourceManifestSha256'] = sha(raw)
            config['sources'][0]['documents']['manifest.json']['sha256'] = sha(raw)
            source = self.run_binding(config, {'fixture-metadata.json': raw})['sources'][0]
            self.assertEqual(source['stage']['status'], 'failed')
            self.assertIn('metadata-document-malformed', source['diagnostics'])

    def test_selector_missing_and_identity_mismatch_are_distinct(self):
        config, evidence = self.fixture()
        config['sources'][0]['fields']['release']['selector'] = '/absent'
        source = self.run_binding(config, evidence)['sources'][0]
        self.assertIn('metadata-selector-missing', source['diagnostics'])
        config['sources'][0]['fields']['release']['selector'] = '/release'
        config['sources'][0]['fields']['release']['expected'] = 'other-release'
        source = self.run_binding(config, evidence)['sources'][0]
        self.assertIn('metadata-declaration-mismatch', source['diagnostics'])

    def test_noop_requires_current_valid_binding(self):
        first = self.run_binding(cache_planner=authored_planner)
        fingerprint = first['sources'][0]['bindingFingerprint']
        second = self.run_binding(cache_planner=authored_planner, previous={'prices': fingerprint})
        self.assertEqual(second['sources'][0]['stage']['status'], 'reused')
        third = self.run_binding(evidence={}, cache_planner=authored_planner,
                                 previous={'prices': fingerprint})
        self.assertNotEqual(third['sources'][0]['stage']['status'], 'reused')
        self.assertEqual(canonical(first), canonical(self.run_binding(cache_planner=authored_planner)))

    def test_missing_shared_planner_stays_typed_dependency(self):
        source = self.run_binding()['sources'][0]
        self.assertEqual(source['stage']['status'], 'unsupported')
        self.assertIn('shared-cache-planner-required', source['diagnostics'])
        self.assertTrue(source['metadataBinding']['bound'])
        self.assertFalse(source['cache']['downloadAllowed'])

    def test_original_acquisition_clock_not_validation_clock(self):
        observed = []
        def capture(metadata, *, now):
            observed.append(metadata)
            return authored_planner(metadata, now=now)
        config, evidence = self.fixture()
        config['sources'][0]['validatedAt'] = NOW
        source = self.run_binding(config, evidence, cache_planner=capture)['sources'][0]
        self.assertEqual(observed[0]['originalAcquiredAt'], '2026-10-12T00:00:00Z')
        self.assertFalse(source['cache']['validationResetsAcquisitionAge'])
        config['sources'][0]['originalAcquiredAt'] = None
        source = self.run_binding(config, evidence, cache_planner=capture)['sources'][0]
        self.assertIn('original-acquisition-time-missing', source['diagnostics'])
        self.assertEqual(len(observed), 1)

    def test_stale_cache_decision_is_not_download_authority(self):
        def stale(metadata, *, now):
            return {**authored_planner(metadata, now=now), 'decision': 'revalidation-required'}
        source = self.run_binding(cache_planner=stale)['sources'][0]
        self.assertIn('cache-revalidation-required', source['diagnostics'])
        self.assertFalse(source['cache']['downloadAllowed'])

    def test_untrusted_planner_contract_rejected(self):
        for change in ({'minimumReuseSeconds': 1}, {'downloadAllowed': True},
                       {'originalAcquiredAt': NOW}, {'decision': 'download'},
                       {'validationResetsAcquisitionAge': True}, {'privateLog': 'not-allowed'}):
            def invalid(metadata, *, now):
                return {**authored_planner(metadata, now=now), **change}
            source = self.run_binding(cache_planner=invalid)['sources'][0]
            self.assertIn('shared-cache-planner-invalid', source['diagnostics'])
            self.assertEqual(source['stage']['status'], 'failed')

    def test_country_consumption_does_not_fork_source_identity(self):
        first = self.run_binding(cache_planner=authored_planner)['sources'][0]
        config, evidence = self.fixture()
        del config['sources'][0]['applicability']['MC']
        second = self.run_binding(config, evidence, cache_planner=authored_planner)['sources'][0]
        self.assertEqual(first['sourceIdentityKey'], second['sourceIdentityKey'])
        self.assertNotEqual(first['bindingFingerprint'], second['bindingFingerprint'])

    def test_invalid_country_or_undeclared_evidence_fails(self):
        config, evidence = self.fixture()
        config['sources'][0]['applicability']['MD'] = ['prices/baskets']
        with self.assertRaises(RefreshError):
            self.run_binding(config, evidence)
        with self.assertRaises(RefreshError):
            self.run_binding(evidence={'unexpected.json': b'{}'})

    def test_country_requirement_evidence_is_pending_never_acceptance(self):
        config, evidence = self.fixture()
        config['countryRequirements'] = [{'country': 'LV', 'dataType': 'recipes',
            'state': 'held', 'missingInput': 'Exact derivative-use scope missing',
            'evidence': {'path': 'retained-gap.json', 'sha256': 'a' * 64, 'selector': '/categories/1'}}]
        report = self.run_binding(config, evidence, cache_planner=authored_planner)
        cell = next(c for c in report['countryTypes'] if c['country'] == 'LV' and c['dataType'] == 'recipes')
        self.assertEqual(cell['diagnostic'], 'source-binding-missing')
        self.assertEqual(cell['retainedRequirement']['state'], 'held')
        self.assertFalse(cell['datasetAccepted'])
        config['countryRequirements'].append(copy.deepcopy(config['countryRequirements'][0]))
        with self.assertRaises(RefreshError):
            self.run_binding(config, evidence)

    def test_escaped_field_selector_preserves_exact_metadata_coordinate(self):
        config, _ = self.fixture()
        raw = canonical({'source': 'prices', 'release': '2026-10-12', 'a/b': {'~key': 0}})
        config['sources'][0]['sourceManifestSha256'] = sha(raw)
        config['sources'][0]['documents']['manifest.json']['sha256'] = sha(raw)
        config['sources'][0]['fields']['native']['selector'] = '/a~1b'
        row = self.run_binding(config, {'fixture-metadata.json': raw},
                               cache_planner=authored_planner)['sources'][0]['metadataRecord']
        self.assertEqual(row['provenance']['fieldOrigins']['/data/native/~0key']['sourceField'],
                         '/a~1b/~0key')

    def test_no_filesystem_or_network_inside_pure_binding(self):
        config, evidence = self.fixture()
        with patch('builtins.open', side_effect=AssertionError('unexpected I/O')), \
                patch('socket.socket', side_effect=AssertionError('unexpected network')):
            self.run_binding(config, evidence, cache_planner=authored_planner)

    def test_cli_is_bounded_and_deterministic_without_plugin_loading(self):
        config, evidence = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'config.json').write_bytes(canonical(config))
            (root / 'metadata.json').write_bytes(canonical({k: v.decode() for k, v in evidence.items()}))
            command = [sys.executable, '-m', 'offmenu.refresh.portfolio59_bindings',
                       '--config', str(root / 'config.json'), '--metadata-envelope',
                       str(root / 'metadata.json'), '--now', NOW]
            a = subprocess.run(command, capture_output=True, check=True).stdout
            b = subprocess.run(command, capture_output=True, check=True).stdout
            self.assertEqual(a, b)
            self.assertEqual(json.loads(a)['sources'][0]['stage']['status'], 'unsupported')
            (root / 'metadata.json').write_text('{bad-json')
            failure = subprocess.run(command, capture_output=True)
            self.assertEqual(failure.returncode, 2)
            self.assertEqual(json.loads(failure.stdout)['diagnostics'], ['portfolio59-input-invalid'])

    def test_cli_rejects_fifo_inputs_without_waiting_for_a_writer(self):
        config, evidence = self.fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config_path = root / 'config.json'
            metadata_path = root / 'metadata.json'
            config_path.write_bytes(canonical(config))
            metadata_path.write_bytes(canonical({k: v.decode() for k, v in evidence.items()}))
            fifo = root / 'input.fifo'
            os.mkfifo(fifo)
            for flag in ('--config', '--metadata-envelope'):
                with self.subTest(flag=flag):
                    command = [sys.executable, '-m', 'offmenu.refresh.portfolio59_bindings',
                               '--config', str(fifo if flag == '--config' else config_path),
                               '--metadata-envelope',
                               str(fifo if flag == '--metadata-envelope' else metadata_path),
                               '--now', NOW]
                    result = subprocess.run(command, capture_output=True, timeout=2)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(json.loads(result.stdout), {
                        'status': 'failed', 'diagnostics': ['portfolio59-input-invalid'],
                        'sourceBodyReads': 0, 'networkRequests': 0})
                    self.assertEqual(result.stderr, b'')

    def test_cli_rejects_regular_path_replaced_by_fifo_at_open(self):
        config, evidence = self.fixture()
        script = '''
import os
from pathlib import Path
import sys
from unittest.mock import patch
from offmenu.refresh.portfolio59_bindings import main
real_open = os.open
def replace_then_open(path, flags):
    if Path(path) == Path(sys.argv[1]):
        Path(path).unlink()
        os.mkfifo(path)
    return real_open(path, flags)
with patch('offmenu.refresh.portfolio59_bindings.os.open', replace_then_open):
    raise SystemExit(main(sys.argv[2:]))
'''
        for flag in ('--config', '--metadata-envelope'):
            with self.subTest(flag=flag), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                config_path, metadata_path = root / 'config.json', root / 'metadata.json'
                config_path.write_bytes(canonical(config))
                metadata_path.write_bytes(canonical({k: v.decode() for k, v in evidence.items()}))
                replaced = config_path if flag == '--config' else metadata_path
                result = subprocess.run([
                    sys.executable, '-c', script, str(replaced), '--config', str(config_path),
                    '--metadata-envelope', str(metadata_path), '--now', NOW],
                    capture_output=True, timeout=2)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(json.loads(result.stdout)['diagnostics'], ['portfolio59-input-invalid'])
                self.assertEqual(result.stderr, b'')


if __name__ == '__main__':
    unittest.main()
