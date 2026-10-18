"""Authored metadata/profile fixtures only. No real manifest or payload access."""
import copy
import ast
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio26 as portfolio
from offmenu.refresh import execution
from offmenu.refresh.core import canonical
from offmenu.refresh.acceptance import Asset, SourceContract, qualify, ids_digest, fingerprint
from offmenu.refresh.field_provenance import datum_pointers

FIXTURES = Path(__file__).parent / 'fixtures/portfolio26'
NOW = '2026-01-15T00:00:00Z'


def binding(path=FIXTURES / 'manifest.json'):
    return {'bindingId': 'authored-cnf', 'country': 'CA', 'sourceId': 'cnf',
            'releaseId': '2015', 'types': ['nutrition'], 'sharedAdapter': 'cnf',
            'manifest': {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()},
            'manifestIdentity': {'sourceId': 'cnf', 'releaseId': '2015'},
            'holds': [], 'origins': [{'field': '/authored', 'sourceSelector': 'authored-only'}],
            'unknowns': ['fixture is not production'],
            'originalAcquiredAt': '2026-01-01T00:00:00Z',
            'validationObservedAt': '2026-01-14T00:00:00Z'}


class Portfolio26Tests(unittest.TestCase):
    def test_inspection_and_plan_preserve_declared_basis_and_unknowns(self):
        # Catalogue declarations only; every metadata call below is an authored stub.
        for spec in portfolio.configuration()['bindings']:
            with self.subTest(binding=spec['bindingId']):
                expected_basis = copy.deepcopy(spec['nativeBasis'])
                expected_unknowns = copy.deepcopy(spec['unknowns'])
                manifest = copy.deepcopy(spec.get('manifestIdentity') or {})
                with patch.object(portfolio, '_read_metadata', return_value=manifest):
                    inspected = portfolio.inspect_binding(spec, now='2026-10-18T00:00:00Z')
                    report = portfolio.plan({'bindings': [spec]}, now='2026-10-18T00:00:00Z')
                for row in (inspected, report['bindings'][0]):
                    self.assertEqual(expected_basis, row['nativeBasis'])
                    self.assertEqual(expected_unknowns, row['unknowns'])
                if spec['sourceId'] in ('cnf', 'germany-bls'):
                    self.assertEqual('succeeded', inspected['stage']['status'])
                if isinstance(expected_basis, dict):
                    inspected['nativeBasis']['authored-mutation'] = True
                    self.assertEqual(expected_basis, spec['nativeBasis'])
        spec = binding()  # Absence is preserved; no basis is inferred for this fixture.
        self.assertNotIn('nativeBasis', portfolio.inspect_binding(spec, now=NOW))

    def test_missing_secondary_evidence_is_distinct_private_and_peer_isolated(self):
        for location in ('provenance', 'origin'):
            with self.subTest(location=location), tempfile.TemporaryDirectory() as directory:
                missing = Path(directory) / 'private-authored-evidence.json'
                evidence = {'path': str(missing), 'sha256': '0' * 64}
                spec, peer = binding(), binding()
                if location == 'provenance':
                    spec['provenanceEvidence'] = [evidence]
                else:
                    spec['origins'][0]['evidence'] = evidence
                peer.update(bindingId='authored-held-peer', holds=['authored-hold'])
                report = portfolio.plan({'bindings': [spec, peer]}, now=NOW)
                row = report['bindings'][0]
                self.assertEqual('unsupported', row['stage']['status'])
                self.assertEqual('portfolio-evidence-missing', row['stage']['code'])
                self.assertEqual(['portfolio-evidence-missing'], row['errors'])
                diagnostics = canonical({'stage': row['stage'], 'errors': row['errors']}).decode()
                self.assertNotIn(str(missing), diagnostics)
                self.assertNotIn('private-authored-evidence', diagnostics)
                self.assertEqual('held', report['bindings'][1]['stage']['status'])
                self.assertEqual(24, len(report['countryTypes']))
                self.assertEqual(0, report['sourceBodyReads'])
                # Restoring just the authored secondary prerequisite restores binding.
                missing.write_bytes(b'{"fixture":"authored evidence"}')
                evidence['sha256'] = hashlib.sha256(missing.read_bytes()).hexdigest()
                self.assertEqual('succeeded', portfolio.inspect_binding(spec, now=NOW)['stage']['status'])

    def test_packaged_catalogue_is_literal_equivalent_and_default_needs_no_file(self):
        source = Path(portfolio.__file__).with_name('portfolio26_catalogue.py').read_text()
        tree = ast.parse(source)
        self.assertEqual(2, len(tree.body))  # docstring and inert assignment only
        literal = ast.literal_eval(tree.body[1].value)
        reviewed = json.loads(portfolio.CONFIG.read_bytes())
        self.assertEqual(reviewed, literal)
        with patch.object(Path, 'read_bytes', side_effect=AssertionError('catalogue file read')), \
             patch.object(Path, 'stat', side_effect=AssertionError('catalogue file stat')):
            self.assertEqual(reviewed, portfolio.configuration())

    def test_packaged_catalogue_returns_independent_nested_copies(self):
        original = portfolio.configuration()
        changed = portfolio.configuration()
        changed['bindings'][0]['holds'].append('authored mutation')
        changed['bindings'][0]['origins'][0]['sourceSelector'] = 'authored mutation'
        changed['bindings'][0]['unknowns'].append('authored mutation')
        self.assertEqual(original, portfolio.configuration())
        self.assertNotEqual(changed, original)

    def test_explicit_review_configuration_path_remains_supported_and_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'review.json'
            value = {'schemaVersion': 'portfolio26-bindings/1',
                     'countries': list(portfolio.COUNTRIES), 'bindings': []}
            path.write_bytes(canonical(value))
            self.assertEqual(value, portfolio.configuration(path))
            path.write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError, 'portfolio-config-invalid'):
                portfolio.configuration(path)

    def test_malformed_ids_fail_before_replay_lookup_and_preserve_held_peer(self):
        for identity in (['authored-invalid-key'], {'authored': 'invalid-key'}, None, 1):
            with self.subTest(identity=identity):
                bad, peer = binding(), binding()
                bad['bindingId'] = identity
                peer.update(bindingId='authored-held-peer', holds=['authored-hold'])
                with patch.object(portfolio, '_read_metadata', side_effect=AssertionError('no I/O')):
                    report = portfolio.plan({'bindings': [bad, peer]}, now=NOW,
                                            previous_keys={'authored-held-peer': 'old'})
                self.assertEqual(['failed', 'held'], [r['stage']['status'] for r in report['bindings']])
                self.assertEqual(['portfolio-identity-missing'], report['bindings'][0]['errors'])
                self.assertEqual(24, len(report['countryTypes']))
                self.assertTrue(all(not c['accepted'] for c in report['countryTypes']))
                self.assertTrue(all(c['bindings'] in ([], ['authored-held-peer'])
                                    for c in report['countryTypes']))

    def test_pinned_reader_uses_one_open_and_never_reopens_with_read_bytes(self):
        spec = binding()
        with patch.object(portfolio.os, 'open', wraps=os.open) as opened, \
             patch.object(Path, 'read_bytes', side_effect=AssertionError('unbounded reopen')):
            result = portfolio.inspect_binding(spec, now=NOW)
        self.assertEqual('succeeded', result['stage']['status'])
        self.assertEqual(1, opened.call_count)

    def test_reader_rejects_oversize_and_bounds_growth_during_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            raw = (FIXTURES / 'manifest.json').read_bytes()
            path.write_bytes(raw)
            spec = binding(path)
            path.write_bytes(b'x' * (portfolio.MAX_METADATA_BYTES + 1024))
            with patch.object(portfolio.os, 'read', side_effect=AssertionError('oversize read')):
                result = portfolio.inspect_binding(spec, now=NOW)
            self.assertEqual('asset-size-limit-exceeded', result['stage']['code'])
            path.write_bytes(raw)
            limit, actual_read, consumed = len(raw) + 10, os.read, []
            def grow_after_first_read(fd, count):
                block = actual_read(fd, count)
                consumed.append(len(block))
                if len(consumed) == 1:
                    with path.open('ab') as stream:
                        stream.write(b'x' * (limit + 1024))
                return block
            with patch.object(portfolio, 'MAX_METADATA_BYTES', limit), \
                 patch.object(portfolio.os, 'read', grow_after_first_read):
                result = portfolio.inspect_binding(spec, now=NOW)
            self.assertEqual('asset-size-limit-exceeded', result['stage']['code'])
            self.assertEqual(limit + 1, sum(consumed))

    def test_open_replacements_fail_promptly_and_do_not_hide_held_peer(self):
        actual_open = os.open
        for replacement in ('oversize', 'fifo', 'symlink'):
            with self.subTest(replacement=replacement), tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'metadata.json'
                path.write_bytes((FIXTURES / 'manifest.json').read_bytes())
                spec, peer = binding(path), binding()
                peer.update(bindingId='authored-held-peer', holds=['authored-hold'])
                def substitute_before_open(target, flags):
                    # Assert before calling the OS so a regression cannot hang this test.
                    self.assertTrue(flags & os.O_NONBLOCK)
                    self.assertTrue(flags & os.O_NOFOLLOW)
                    path.unlink()
                    if replacement == 'fifo':
                        os.mkfifo(path)
                    elif replacement == 'symlink':
                        path.symlink_to(FIXTURES / 'manifest.json')
                    else:
                        path.write_bytes(b'x' * (portfolio.MAX_METADATA_BYTES + 1024))
                    return actual_open(target, flags)
                with patch.object(portfolio.os, 'open', substitute_before_open), \
                     patch.object(portfolio.os, 'read', side_effect=AssertionError('replacement read')):
                    report = portfolio.plan({'bindings': [spec, peer]}, now=NOW)
                self.assertIn(report['bindings'][0]['stage']['status'], ('failed', 'quarantined'))
                self.assertEqual('held', report['bindings'][1]['stage']['status'])
                self.assertEqual(0, report['sourceBodyReads'])

    def test_path_replacement_after_open_is_stale_and_descriptor_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            raw = (FIXTURES / 'manifest.json').read_bytes()
            path.write_bytes(raw)
            spec, actual_read, calls = binding(path), os.read, []
            def replace_after_read(fd, count):
                block = actual_read(fd, count)
                if not calls:
                    path.unlink()
                    path.write_bytes(raw)
                calls.append(fd)
                return block
            with patch.object(portfolio.os, 'read', replace_after_read):
                result = portfolio.inspect_binding(spec, now=NOW)
            self.assertEqual('portfolio-metadata-stale', result['stage']['code'])
            with self.assertRaises(OSError):
                os.fstat(calls[0])

    def test_valid_metadata_binds_shared_adapter_without_execution_or_acceptance(self):
        with patch.object(execution, 'execute', side_effect=AssertionError('must not parse')):
            result = portfolio.inspect_binding(binding(), now=NOW)
        self.assertEqual('succeeded', result['stage']['status'])
        self.assertEqual('portfolio-metadata-bound', result['stage']['code'])
        self.assertTrue(result['metadataBytesVerified'])
        self.assertFalse(result['payloadBytesVerified'])
        self.assertEqual([], result['bodyOperations'])
        self.assertIsNone(result['acceptedRecords'])
        self.assertIsNone(result['qualificationContract'])
        self.assertFalse(result['countryComplete'])
        self.assertEqual('available-not-admitted', result['adapterStatus'])

    def test_missing_manifest_pointer_and_missing_file_are_typed(self):
        spec = binding()
        spec['manifest'] = None
        with patch.object(portfolio, '_read_metadata', side_effect=AssertionError('no I/O')):
            self.assertEqual('portfolio-manifest-missing', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])
        with tempfile.TemporaryDirectory() as directory:
            spec['manifest'] = {'path': str(Path(directory) / 'absent.json'), 'sha256': '0' * 64}
            result = portfolio.inspect_binding(spec, now=NOW)
        self.assertEqual('unsupported', result['stage']['status'])
        self.assertEqual('portfolio-manifest-missing', result['stage']['code'])

    def test_held_descriptor_does_not_touch_even_missing_path(self):
        spec = binding()
        spec['holds'] = ['403-no-retry', 'private-original-only']
        spec['manifest']['path'] = '/must-not-touch-held-body.json'
        with patch.object(portfolio, '_read_metadata', side_effect=AssertionError('hold bypass')):
            result = portfolio.inspect_binding(spec, now=NOW)
        self.assertEqual('held', result['stage']['status'])
        self.assertEqual(spec['holds'], result['holds'])
        self.assertFalse(result['metadataBytesVerified'])

    def test_malformed_and_duplicate_json_do_not_leak_data(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            for raw, code in [(b'{secret:', 'portfolio-metadata-malformed'),
                              (b'{"sourceId":"cnf","sourceId":"foreign"}', 'duplicate-json-key'),
                              (b'{"value":NaN}', 'nonfinite-json-number')]:
                path.write_bytes(raw)
                result = portfolio.inspect_binding(binding(path), now=NOW)
                self.assertEqual('failed', result['stage']['status'])
                self.assertEqual(code, result['stage']['code'])
                self.assertNotIn('secret', canonical(result).decode())

    def test_stale_bytes_quarantined_even_with_previous_key(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.write_bytes((FIXTURES / 'manifest.json').read_bytes())
            spec = binding(path)
            previous = portfolio.inspect_binding(spec, now=NOW)['bindingKey']
            path.write_text('{"sourceId":"cnf","releaseId":"2026"}')
            result = portfolio.inspect_binding(spec, now=NOW, previous_key=previous)
        self.assertEqual('quarantined', result['stage']['status'])
        self.assertEqual('portfolio-metadata-stale', result['stage']['code'])
        self.assertEqual('not-bound', result['packageAction'])

    def test_release_mismatch_is_not_discovery_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.write_text('{"sourceId":"cnf","releaseId":"2026"}')
            result = portfolio.inspect_binding(binding(path), now=NOW)
            self.assertEqual('portfolio-source-release-mismatch', result['stage']['code'])
            spec = binding(path)
            spec['manifestIdentity']['releaseId'] = '2026'
            self.assertEqual('portfolio-source-release-mismatch', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])
        spec = binding()
        spec['releaseId'] = '2026'
        self.assertEqual('portfolio-shared-adapter-mismatch', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])

    def test_origin_evidence_is_pinned_without_verifying_payload_or_rights(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'evidence.json'
            path.write_text('{"fixture":"authored definition locator only"}')
            evidence = {'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            spec = binding()
            spec['provenanceEvidence'] = [evidence]
            spec['origins'][0]['evidence'] = evidence
            result = portfolio.inspect_binding(spec, now=NOW)
            self.assertEqual(1, result['metadataEvidencePinsVerified'])
            self.assertFalse(result['rightsOperationsReviewedByThisTool'])
            self.assertEqual('declared-not-row-verified', result['fieldOriginsStatus'])
            path.write_text('{"fixture":"changed"}')
            result = portfolio.inspect_binding(spec, now=NOW)
            self.assertEqual('portfolio-metadata-stale', result['stage']['code'])

    def test_payload_suffix_and_symlink_rejected(self):
        spec = binding()
        spec['manifest']['path'] = '/not-read/raw.csv'
        self.assertEqual('portfolio-metadata-pin-invalid', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.symlink_to(FIXTURES / 'manifest.json')
            spec = binding()
            spec['manifest']['path'] = str(path)
            self.assertEqual('symlink-path-rejected', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])

    def test_replay_is_noop_for_metadata_only_and_validation_does_not_refresh(self):
        spec = binding()
        before = copy.deepcopy(spec)
        first = portfolio.inspect_binding(spec, now=NOW)
        second = portfolio.inspect_binding(spec, now=NOW, previous_key=first['bindingKey'])
        self.assertEqual('metadata-no-op', second['packageAction'])
        self.assertEqual(first['bindingKey'], second['bindingKey'])
        spec['validationObservedAt'] = '2026-02-01T00:00:00Z'
        later = portfolio.inspect_binding(spec, now='2026-02-01T00:00:00Z', previous_key=first['bindingKey'])
        self.assertEqual('metadata-no-op', later['packageAction'])
        self.assertEqual('unsupported-shared-cache-planner', later['cache']['decision'])
        self.assertEqual('30-days-or-older', later['cache']['retentionWindow'])
        self.assertEqual(0, later['cache']['networkRequests'])
        self.assertEqual('2026-01-01T00:00:00Z', later['cache']['originalAcquiredAt'])
        self.assertEqual(before['origins'], spec['origins'])

    def test_thirty_day_boundary_and_unknown_acquisition_time(self):
        spec = binding()
        self.assertEqual('under-30-days', portfolio.cache_metadata(spec, now='2026-01-30T23:59:59Z')['retentionWindow'])
        self.assertEqual('30-days-or-older', portfolio.cache_metadata(spec, now='2026-01-31T00:00:00Z')['retentionWindow'])
        spec['originalAcquiredAt'] = None
        cache = portfolio.cache_metadata(spec, now=NOW)
        self.assertEqual('unknown-acquisition-time', cache['retentionWindow'])
        self.assertEqual('unsupported-shared-cache-planner', cache['decision'])
        self.assertIsNone(cache['sharedPlanner'])
        self.assertNotIn('acquisitionAgeSeconds', cache)

    def test_clocks_and_malformed_binding_fail_closed(self):
        for key in ['originalAcquiredAt', 'validationObservedAt']:
            spec = binding()
            spec[key] = '2027-01-01T00:00:00Z'
            self.assertEqual('failed', portfolio.inspect_binding(spec, now=NOW)['stage']['status'])
        spec = binding()
        spec['originalAcquiredAt'] = '2026-01-01T00:00:00'
        self.assertEqual('acquisition-timestamp-must-be-utc', portfolio.inspect_binding(spec, now=NOW)['stage']['code'])
        report = portfolio.plan({'bindings': [None]}, now=NOW)
        self.assertEqual('failed', report['bindings'][0]['stage']['status'])

    def test_authored_profiles_use_shared_semantics_preserving_unknowns(self):
        row = json.loads((FIXTURES / 'profile.json').read_text())
        original = copy.deepcopy(row)
        self.assertEqual([], portfolio.diagnose_authored_profile('cnf', row))
        row['data']['nutrients']['protein'].update(value=None, unit='unknown', name='Unresolved CNF nutrient 328', qualifier='unknown')
        before = copy.deepcopy(row)
        errors = portfolio.diagnose_authored_profile('cnf', row)
        self.assertIn('national-nutrient-definition-unresolved', errors)
        self.assertIn('national-nutrient-unit-unqualified', errors)
        self.assertEqual(before, row)
        original['provenance'] = {'sourceId': 'germany-bls', 'releaseId': '4.0'}
        self.assertEqual([], portfolio.diagnose_authored_profile('germany-bls', original))
        original['data']['nutrients']['Hinweis'] = {'value': None, 'unit': 'unknown', 'qualifier': 'source-text'}
        self.assertIn('national-nutrient-unit-unqualified', portfolio.diagnose_authored_profile('germany-bls', original))

    def test_portfolio_config_is_not_an_admission_or_country_acceptance(self):
        config = portfolio.configuration()
        self.assertEqual(10, len(config['bindings']))
        # Force failure if this test accidentally touches ANY real source metadata.
        with patch.object(portfolio, '_read_metadata', side_effect=FileNotFoundError):
            report = portfolio.plan(config, now='2026-10-18T00:00:00Z')
        self.assertEqual(24, len(report['countryTypes']))
        self.assertTrue(all(not c['accepted'] for c in report['countryTypes']))
        self.assertEqual(0, report['sourceBodyReads'])
        self.assertEqual(0, report['acceptedCountryTypes'])
        self.assertFalse(execution.ADMISSIONS)
        cnf = next(b for b in config['bindings'] if b['sourceId'] == 'cnf')
        self.assertIsNone(cnf['originalAcquiredAt'])
        self.assertIn('Food534', ' '.join(cnf['unknowns']))

    def test_shared_per_datum_origins_cover_null_without_inventing_cells(self):
        digest = hashlib.sha256(b'authored fixture only').hexdigest()
        row = {'data': {'value': None}, 'provenance': {'sourceId': 'cnf', 'releaseId': '2015',
               'fieldOrigins': {'/data/value': {'kind': 'source', 'sourceId': 'cnf',
                   'releaseId': '2015', 'inputPath': 'authored.csv', 'inputSha256': digest,
                   'sourceRecordId': 'authored-food:authored-component', 'sourceField': 'NutrientValue'}}}}
        before = copy.deepcopy(row)
        self.assertEqual([], portfolio.diagnose_authored_origins(row, {'authored.csv': digest}))
        self.assertEqual(before, row)
        row['provenance']['fieldOrigins'].clear()
        self.assertIn('field-origin-inventory-mismatch', portfolio.diagnose_authored_origins(row, {'authored.csv': digest}))
        row = before
        row['provenance']['fieldOrigins']['/data/value']['releaseId'] = '2026'
        self.assertIn('field-origin-source-mismatch', portfolio.diagnose_authored_origins(row, {'authored.csv': digest}))

    def test_shared_qualification_is_authored_fixture_scope_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            raw = (FIXTURES / 'profile.json').read_bytes()
            assets = []
            for name, body in [('profile.json', raw), ('rights.json', b'{"authored":"fixture-only retain parse transform"}'),
                               ('scope.json', b'{"authoredIds":["authored-cnf-1"]}')]:
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
            row = json.loads(raw)
            row['provenance']['fetchedAt'] = '2026-01-01T00:00:00Z'
            row['provenance']['fieldOrigins'] = {
                pointer: {'kind': 'source', 'sourceId': 'cnf', 'releaseId': '2015',
                          'inputPath': 'profile.json', 'inputSha256': assets[0].sha256,
                          'sourceRecordId': 'authored-cnf-1', 'sourceField': pointer}
                for pointer in datum_pointers(row['data'])}
            def semantics(candidate):
                return (portfolio.diagnose_authored_profile('cnf', candidate)
                        + portfolio.diagnose_authored_origins(candidate, {'profile.json': assets[0].sha256}))
            schemas = {'nutrientProfile': {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                       'properties': {'schemaVersion': {'const': '1.0'}, 'kind': {'const': 'nutrientProfile'},
                                      'data': {'type': 'object', 'required': ['basis', 'nutrients']}}}}
            contract = SourceContract('cnf', '2015', 'authored-portfolio26-fixture',
                '2026-01-01T00:00:00Z', tuple(assets), 1, ids_digest([row['id']]), schemas,
                fingerprint(schemas), semantics, fingerprint({'authored': 'portfolio26-semantics'}),
                assets[1], assets[2], frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(canonical([row]))
            body = candidate.read_bytes()
            manifest = {'sourceId': 'cnf', 'releaseId': '2015', 'acquiredAt': contract.acquired_at,
                        'normalizedRecords': 1, 'candidateSha256': hashlib.sha256(body).hexdigest(),
                        'candidateBytes': len(body), 'inputFiles': [vars(a) for a in assets],
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256}
            result = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            self.assertNotIn('accepted', result)
            self.assertIn('source-held', qualify(replace(contract, holds=('authored-hold',)), bundle, candidate, manifest)['errors'])
            candidate.write_bytes(b'[]\n')
            self.assertIn('candidate-custody-mismatch', qualify(contract, bundle, candidate, manifest)['errors'])

    def test_deterministic_isolated_subprocess_uses_authored_fixture_only(self):
        script = ('from tests.test_portfolio26_bindings import binding, NOW; '
                  'from offmenu.refresh.portfolio26 import inspect_binding; '
                  'from offmenu.refresh.core import canonical; '
                  'print(canonical(inspect_binding(binding(), now=NOW)).decode(), end="")')
        # Load fixture support by path; tests is not an installed package.
        script = ('import sys; sys.path.insert(0,"tests"); ' + script.replace('from tests.test_portfolio26_bindings', 'from test_portfolio26_bindings'))
        a = subprocess.check_output([sys.executable, '-c', script], cwd=Path(__file__).parents[1])
        b = subprocess.check_output([sys.executable, '-c', script], cwd=Path(__file__).parents[1])
        self.assertEqual(a, b)
        self.assertEqual('portfolio-metadata-bound', json.loads(a)['stage']['code'])


if __name__ == '__main__':
    unittest.main()
