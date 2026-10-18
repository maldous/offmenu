"""Authored metadata only; no retained original source body is opened."""
import copy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio31 import (COUNTRIES, TYPES, diagnose_binding,
                                        plan_portfolio, pointer, read_metadata,
                                        load_catalogue)

NOW = datetime(2026, 10, 18, 12, tzinfo=timezone.utc)


class Portfolio31Tests(unittest.TestCase):
    def test_installed_catalogue_equals_json_mirror_and_is_deeply_independent(self):
        from offmenu.refresh.portfolio31 import CONFIG
        expected = json.loads(CONFIG.read_bytes())
        with patch('offmenu.refresh.portfolio31.read_json_bytes',
                   side_effect=AssertionError('source metadata read forbidden')):
            first = load_catalogue()
            self.assertEqual(canonical(first), canonical(expected))
            first['bindings'][0]['metadata']['sha256'] = 'changed'
            first['bindings'][0]['holds'].append('mutation')
            first['requirements'].clear()
            self.assertEqual(canonical(load_catalogue()), canonical(expected))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'authored-metadata.json'
        acquired = (NOW - timedelta(days=2)).isoformat()
        self.path.write_bytes(canonical({'release': 'fixture-1', 'code': 0, 'acquiredAt': acquired,
                                        'name': None, 'unit': 'g', 'basis': '100g'}))
        self.spec = {'key': 'co-authored', 'country': 'CO', 'sourceId': 'authored-only',
                     'releaseId': 'fixture-1',
                     'metadata': {'path': str(self.path), 'sha256': sha(self.path.read_bytes())},
                     'originalAcquiredAt': acquired, 'acquisitionSelector': '/acquiredAt',
                     'validatedAt': NOW.isoformat(), 'holds': [],
                     'rightsDecision': {'scope': 'authored-fixture-only'},
                     'custodyAcceptance': {'scope': 'authored-fixture-only'},
                     'semanticSelectorEvidence': {'scope': 'authored-fixture-only'},
                     'unit': 'g', 'basis': '100g',
                     'nativeUnitSelector': '/unit', 'nativeBasisSelector': '/basis',
                     'sourceAssetPin': {'path': '/NEVER-OPEN/raw.pdf', 'sha256': 'a' * 64},
                     'fields': {'foodCode': {'selector': '/code'},
                                'name': {'selector': '/name'}}}

    def config(self, specs=None):
        specs = specs or [self.spec]
        return {'schemaVersion': 'offmenu-worker31-input-bindings/1',
                'selectedBase': 'authored-fixture', 'portfolio': list(COUNTRIES),
                'sourceProcessingEnabled': False, 'minimumReuseSeconds': 30 * 86400,
                'bindings': specs,
                'requirements': [{'country': c, 'dataType': t, 'bindings': [],
                                  'applicability': 'unaccepted', 'missingInput': 'fixture-only'}
                                 for c in COUNTRIES for t in TYPES]}

    def test_valid_metadata_uses_shared_origins_including_zero_and_null(self):
        r = diagnose_binding(self.spec, now=NOW)
        self.assertEqual((r['status'], r['errors']), ('succeeded', []))
        self.assertEqual(r['data'], {'foodCode': 0, 'name': None})
        self.assertEqual(set(r['fieldOrigins']), {'/data/foodCode', '/data/name'})
        self.assertEqual(r['fieldOrigins']['/data/foodCode']['sourceField'], '/code')
        self.assertFalse(r['stagingActivated'])
        self.assertFalse(r['datasetAccepted'])
        self.assertEqual(r['stageReceipt']['observedCount'], 0)

    def test_valid_missing_held_malformed_stale_peers_are_isolated(self):
        specs = []
        for i in range(5):
            s = copy.deepcopy(self.spec); s['key'] = str(i); specs.append(s)
        specs[1]['metadata']['path'] = str(self.path.with_name('missing.json'))
        specs[2]['holds'] = ['actual-denial-no-retry']
        specs[3]['metadata']['sha256'] = 'b' * 64
        specs[4]['originalAcquiredAt'] = (NOW - timedelta(days=30)).isoformat()
        stale_path = self.path.with_name('stale.json')
        stale_data = json.loads(self.path.read_text())
        stale_data['acquiredAt'] = specs[4]['originalAcquiredAt']
        stale_path.write_bytes(canonical(stale_data))
        specs[4]['metadata'] = {'path': str(stale_path), 'sha256': sha(stale_path.read_bytes())}
        r = plan_portfolio(self.config(specs), now=NOW)
        self.assertEqual([x['status'] for x in r['sources']],
                         ['succeeded', 'held', 'held', 'failed', 'held'])
        self.assertIn('metadata-input-missing', r['sources'][1]['errors'])
        self.assertIn('source-held', r['sources'][2]['errors'])
        self.assertIn('metadata-input-invalid', r['sources'][3]['errors'])
        self.assertIn('stale-input-review-required', r['sources'][4]['errors'])
        self.assertEqual(len(r['requirements']), 24)
        self.assertFalse(r['countryCoverageComplete'])

    def test_no_network_or_original_body_open_even_if_held_or_valid(self):
        original = os.open
        def guarded(path, *args, **kwargs):
            self.assertEqual(path, self.path)
            return original(path, *args, **kwargs)
        with patch.object(os, 'open', guarded), patch.object(socket, 'socket', side_effect=AssertionError('network')):
            self.assertEqual(diagnose_binding(self.spec, now=NOW)['status'], 'succeeded')
            self.spec['holds'] = ['source-copy-restricted']
            self.assertEqual(diagnose_binding(self.spec, now=NOW)['status'], 'held')

    def test_original_age_not_validation_age_and_exact_30_day_boundary(self):
        self.spec['originalAcquiredAt'] = (NOW - timedelta(days=30)).isoformat()
        metadata = json.loads(self.path.read_text())
        metadata['acquiredAt'] = self.spec['originalAcquiredAt']
        self.path.write_bytes(canonical(metadata))
        self.spec['metadata']['sha256'] = sha(self.path.read_bytes())
        a = diagnose_binding(self.spec, now=NOW - timedelta(seconds=1))
        # Do not let a future validation timestamp supply artificial freshness.
        self.assertIn('acquisition-validation-time-invalid', a['errors'])
        self.spec['validatedAt'] = (NOW - timedelta(seconds=1)).isoformat()
        self.assertEqual(diagnose_binding(self.spec, now=NOW - timedelta(seconds=1))['cache']['decision'], 'reuse-no-download')
        self.assertEqual(diagnose_binding(self.spec, now=NOW)['cache']['decision'], 'stale-input-review-no-download')

    def test_replay_is_no_op_but_cannot_bypass_changed_pin_or_hold(self):
        first = diagnose_binding(self.spec, now=NOW)
        self.assertEqual(diagnose_binding(self.spec, now=NOW, previous=first)['replay'], 'unchanged-declaration-no-op')
        self.path.write_text('{"bad":"SECRET-EXCEPTION-TEXT"}')
        r = diagnose_binding(self.spec, now=NOW, previous=first)
        self.assertEqual(r['replay'], 'blocked-not-reusable')
        self.assertNotIn('SECRET', json.dumps(r))

    def test_revalidation_does_not_change_content_identity_or_acquisition(self):
        self.spec['validatedAt'] = (NOW - timedelta(days=1)).isoformat()
        a = diagnose_binding(self.spec, now=NOW)
        self.spec['validatedAt'] = NOW.isoformat()
        b = diagnose_binding(self.spec, now=NOW, previous=a)
        self.assertEqual(a['inputStateSha256'], b['inputStateSha256'])
        self.assertEqual(a['cache']['acquisitionAgeSeconds'], b['cache']['acquisitionAgeSeconds'])

    def test_missing_units_and_basis_remain_unknown_not_zero(self):
        self.spec['unit'] = self.spec['basis'] = None
        r = diagnose_binding(self.spec, now=NOW)
        self.assertEqual(r['errors'], ['native-basis-unknown', 'native-unit-unknown'])
        self.assertIsNone(r['data']['name'])

    def test_original_acquisition_must_match_its_pinned_metadata_origin(self):
        self.spec['originalAcquiredAt'] = NOW.isoformat()
        self.assertIn('acquisition-origin-mismatch', diagnose_binding(self.spec, now=NOW)['errors'])
        del self.spec['acquisitionSelector']
        self.assertIn('acquisition-origin-missing', diagnose_binding(self.spec, now=NOW)['errors'])

    def test_malformed_source_contract_does_not_hide_healthy_peer(self):
        broken = copy.deepcopy(self.spec); broken['key'] = 'broken'
        broken['fields'] = {'x': {'selector': '/code'}, 1: {'selector': '/name'}}
        r = plan_portfolio(self.config([broken, self.spec]), now=NOW)
        self.assertEqual(r['sources'][0]['errors'], ['metadata-binding-contract-invalid'])
        self.assertEqual(r['sources'][1]['status'], 'succeeded')

    def test_requirement_evidence_corruption_stays_explicit(self):
        c = self.config()
        c['requirements'][0]['evidence'] = {'path': str(self.path), 'sha256': 'b' * 64,
                                          'selector': '/code'}
        r = plan_portfolio(c, now=NOW)
        cell = next(x for x in r['requirements'] if x['country'] == 'CO' and x['dataType'] == 'ingredients')
        self.assertEqual(cell['evidenceStatus'], 'requirement-evidence-invalid')
        self.assertEqual(r['sources'][0]['status'], 'succeeded')
        self.assertFalse(r['countryCoverageComplete'])

    def test_retained_manifest_evidence_is_checked_without_opening_body_pins(self):
        c = self.config()
        c['evidence'] = [{'path': str(self.path), 'sha256': self.spec['metadata']['sha256'],
                          'selector': '/code'}]
        r = plan_portfolio(c, now=NOW)
        self.assertEqual(r['portfolioEvidence'][0]['status'], 'verified-metadata-pin')
        c['evidence'][0]['sha256'] = 'b' * 64
        self.assertEqual(plan_portfolio(c, now=NOW)['portfolioEvidence'][0]['status'],
                         'requirement-evidence-invalid')

    def test_unit_basis_drift_and_selector_failure_have_fixed_errors(self):
        self.spec['unit'] = 'kg'
        self.spec['nativeBasisSelector'] = '/unknown'
        r = diagnose_binding(self.spec, now=NOW)
        self.assertIn('native-unit-declaration-mismatch', r['errors'])
        self.assertIn('native-basis-selector-missing', r['errors'])
        self.spec['fields']['name']['selector'] = '/missing'
        self.assertIn('field-selector-missing-or-invalid', diagnose_binding(self.spec, now=NOW)['errors'])

    def test_duplicate_json_and_non_json_asset_fail_without_source_values(self):
        self.path.write_text('{"code":0,"code":1}')
        self.spec['metadata']['sha256'] = sha(self.path.read_bytes())
        self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])
        self.spec['metadata']['path'] = '/NEVER-OPEN/raw.pdf'
        self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])

    def test_pointer_escaping_and_invalid_paths(self):
        self.assertEqual(pointer({'a/b': {'~': [0]}}, '/a~1b/~0/0'), 0)
        for p in ('/a~2b', '/x/01', 'x'):
            with self.assertRaises((ValueError, KeyError)):
                pointer({'x': [1, 2]}, p)

    def test_contract_cannot_enable_source_processing_or_drop_country_type(self):
        c = self.config(); c['sourceProcessingEnabled'] = True
        with self.assertRaisesRegex(ValueError, 'portfolio-contract-invalid'):
            plan_portfolio(c, now=NOW)
        c = self.config(); c['requirements'].pop()
        with self.assertRaisesRegex(ValueError, 'portfolio-requirements-invalid'):
            plan_portfolio(c, now=NOW)

    def test_deterministic_full_plan_and_no_input_mutation(self):
        c = self.config(); before = copy.deepcopy(c)
        a = plan_portfolio(c, now=NOW); b = plan_portfolio(c, now=NOW)
        self.assertEqual(canonical(a), canonical(b))
        self.assertEqual(c, before)
        self.assertEqual(a['networkRequests'], 0)

    def test_fifo_replay_and_metadata_fail_promptly_with_fixed_errors(self):
        from offmenu.refresh import portfolio31 as module
        config = self.path.with_name('config.json')
        config.write_bytes(canonical(self.config()))
        fifo = self.path.with_name('fifo.json')
        os.mkfifo(fifo)
        for mode in ('replay', 'metadata'):
            code = '''
import json,sys
from pathlib import Path
from offmenu.refresh import portfolio31 as m
m.CONFIG=Path(sys.argv[1])
m.load_catalogue=lambda: json.loads(m.CONFIG.read_bytes())
if sys.argv[3]=='replay':
    raise SystemExit(m.main(['--now',sys.argv[4],'--previous',sys.argv[2]]))
config=json.loads(m.CONFIG.read_bytes());s=config['bindings'][0]
s['metadata']['path']=sys.argv[2]
print(json.dumps(m.plan_portfolio(config,now=m.timestamp(sys.argv[4]))))
'''
            child = subprocess.run([sys.executable, '-B', '-c', code, str(config),
                str(fifo), mode, NOW.isoformat()], capture_output=True, text=True,
                timeout=2, cwd=Path(module.__file__).resolve().parents[2])
            self.assertEqual(child.stderr, '')
            r = json.loads(child.stdout)
            if mode == 'replay':
                self.assertEqual(child.returncode, 2)
                self.assertEqual(r, {'status': 'failed', 'errors': ['metadata-request-invalid']})
            else:
                self.assertEqual(child.returncode, 0)
                self.assertEqual(r['sources'][0]['errors'], ['metadata-input-invalid'])

    def test_replacement_before_open_is_rejected_without_blocking(self):
        real_open = os.open
        fifo = self.path.with_name('replacement.json')
        os.mkfifo(fifo)
        def replace_before_open(path, *args, **kwargs):
            os.replace(fifo, path)
            return real_open(path, *args, **kwargs)
        with patch.object(os, 'open', replace_before_open):
            self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])

    def test_replacement_after_hash_never_reopens_or_parses_replacement(self):
        from offmenu.refresh import portfolio31 as module
        fifo = self.path.with_name('replacement.json')
        os.mkfifo(fifo)
        real_sha = module.sha
        def replace_after_hash(raw):
            observed = real_sha(raw)
            os.replace(fifo, self.path)
            return observed
        with patch.object(module, 'sha', replace_after_hash), patch.object(Path, 'read_bytes',
                side_effect=AssertionError('unbounded reopen')):
            r = read_metadata(self.spec['metadata'])
        self.assertEqual(r['code'], 0)
        self.assertIsNone(r['name'])

    def test_reader_rejects_oversize_symlink_directory_and_nonfinite(self):
        for raw in (b'x' * (1024 * 1024 + 1), b'{"x":NaN}'):
            self.path.write_bytes(raw)
            self.spec['metadata']['sha256'] = sha(raw)
            self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])
        link = self.path.with_name('link.json'); link.symlink_to(self.path)
        self.spec['metadata']['path'] = str(link)
        self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])
        directory = self.path.with_name('directory.json'); directory.mkdir()
        self.spec['metadata']['path'] = str(directory)
        self.assertIn('metadata-input-invalid', diagnose_binding(self.spec, now=NOW)['errors'])

    def test_malformed_prior_entries_do_not_hide_healthy_peers(self):
        c = self.config()
        first = plan_portfolio(c, now=NOW)
        valid = first['sources'][0]
        for bad in (None, [], {}, {'key': []}, {'key': 'unknown'},
                    {'key': self.spec['key'], 'inputStateSha256': None}):
            previous = {'sources': [bad, valid]}
            r = plan_portfolio(c, now=NOW, previous=previous)
            self.assertEqual(r['replayDiagnostics'], ['prior-state-entry-invalid'])
            self.assertEqual(r['sources'][0]['status'], 'succeeded')
            self.assertEqual(canonical(r), canonical(plan_portfolio(c, now=NOW, previous=previous)))
        # An invalid hint for another key leaves this healthy replay usable.
        r = plan_portfolio(c, now=NOW, previous={'sources': [None, valid]})
        self.assertEqual(r['sources'][0]['replay'], 'unchanged-declaration-no-op')

    def test_invalid_prior_envelopes_and_duplicates_do_not_grant_replay(self):
        c = self.config()
        for previous in ([], False, {'sources': None}, {'schemaVersion': 'wrong'}):
            r = plan_portfolio(c, now=NOW, previous=previous)
            self.assertEqual(r['replayDiagnostics'], ['prior-state-invalid'])
            self.assertEqual(r['sources'][0]['status'], 'succeeded')
            self.assertEqual(r['sources'][0]['replay'], 'new-or-changed-declaration')
        first = plan_portfolio(c, now=NOW)
        r = plan_portfolio(c, now=NOW, previous={'sources': first['sources'] * 2})
        self.assertEqual(r['replayDiagnostics'], ['prior-state-entry-invalid'])
        self.assertEqual(r['sources'][0]['replay'], 'new-or-changed-declaration')
        self.assertEqual(plan_portfolio(c, now=NOW, previous=first)['sources'][0]['replay'],
                         'unchanged-declaration-no-op')

    def test_shared_fixture_qualification_covers_metadata_origins_only(self):
        declaration = diagnose_binding(self.spec, now=NOW)
        asset = Asset(self.path.name, self.path.stat().st_size, self.spec['metadata']['sha256'])
        row = {'id': 'fixture-one', 'kind': 'FixtureMetadata', 'schemaVersion': 'authored/1',
               'data': declaration['data'], 'provenance': {
                   'sourceId': self.spec['sourceId'], 'releaseId': self.spec['releaseId'],
                   'fetchedAt': self.spec['originalAcquiredAt'],
                   'fieldOrigins': declaration['fieldOrigins']}}
        # Shared origin helper expects the independently pinned logical input name.
        for origin in row['provenance']['fieldOrigins'].values():
            origin['inputPath'] = self.path.name
        schemas = {'FixtureMetadata': {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                   'properties': {'kind': {'const': 'FixtureMetadata'},
                                  'data': {'type': 'object', 'required': ['foodCode', 'name'],
                                           'properties': {'foodCode': {'const': 0}, 'name': {'type': 'null'}},
                                           'additionalProperties': False}}}}
        contract = SourceContract(self.spec['sourceId'], self.spec['releaseId'], 'authored-metadata-only',
            self.spec['originalAcquiredAt'], (asset,), 1, ids_digest(['fixture-one']), schemas,
            fingerprint(schemas), lambda r: field_origin_errors(r, {asset.path: asset.sha256}),
            'a' * 64, asset, asset, frozenset(('retain', 'parse', 'transform')), fixture=True)
        candidate_dir = Path(self.temp.name).parent / (Path(self.temp.name).name + '-output')
        candidate_dir.mkdir(); self.addCleanup(lambda: __import__('shutil').rmtree(candidate_dir))
        candidate = candidate_dir / 'candidate.jsonl'
        raw = canonical([row]); candidate.write_bytes(raw)
        manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                    'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                    'candidateSha256': sha(raw), 'candidateBytes': len(raw),
                    'rightsEvidenceSha256': asset.sha256, 'scopeEvidenceSha256': asset.sha256,
                    'inputFiles': [vars(asset)]}
        result = qualify(contract, self.temp.name, candidate, manifest)
        self.assertTrue(result['qualified'], result['errors'])
        self.assertTrue(result['fixture'])
        self.assertEqual(result['normalizedRecords'], 1)
        self.assertNotIn('productionAccepted', result)


if __name__ == '__main__':
    unittest.main()
