import copy
from dataclasses import replace
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import unittest

from offmenu.refresh import portfolio18 as p
from offmenu.refresh.acceptance import (Asset, SourceContract, accept, canonical as packet,
                                       fingerprint, ids_digest, qualify)
from offmenu.refresh.core import canonical, sha, strict_json
from offmenu.refresh.field_provenance import field_origin_errors


class Portfolio18Tests(unittest.TestCase):
    def setUp(self):
        self.manifest = strict_json((Path(__file__).parent / 'fixtures/portfolio18/metadata.json').read_bytes())
        self.spec = {'bindingId': 'authored-only', 'sourceId': 'authored-source',
                     'releaseId': 'fixture-v1', 'inputs': {'tiny.csv': 'a' * 64},
                     'originalAcquiredAt': '2026-10-01T00:00:00Z',
                     'holds': [], 'dependencies': [], 'scope': 'authored-test-only'}
        self.now = '2026-10-02T00:00:00Z'

    def check(self, **kwargs):
        return p._inspect(self.spec, canonical(self.manifest), now=self.now, **kwargs)

    def test_valid_metadata_and_replay_excludes_validation_age(self):
        first = self.check()
        self.assertEqual(first['state'], 'ready')
        self.now = '2026-10-03T00:00:00Z'
        self.manifest['validatedAt'] = self.now
        replay = self.check(previous_plan=first['planSha256'])
        self.assertEqual(replay['state'], 'no-op')
        self.assertEqual(replay['inputAgeSeconds'], 2 * 86400)
        self.assertEqual(replay['metadataValidationAgeSeconds'], 0)
        self.assertFalse(replay['sourceBytesVerified'])
        self.assertEqual(replay['admission'], 'not-assessed')

    def test_thirty_day_boundary_cannot_be_reset_by_recent_validation(self):
        self.now = '2026-10-30T23:59:59Z'
        self.assertEqual(self.check()['state'], 'ready')
        self.now = '2026-10-31T00:00:00Z'
        self.manifest['validatedAt'] = self.now
        self.assertEqual(self.check()['state'], 'stale')

    def test_unknown_acquisition_is_missing_not_fresh(self):
        self.manifest['originalAcquiredAt'] = self.spec['originalAcquiredAt'] = None
        self.assertEqual(self.check()['state'], 'missing')
        self.assertIsNone(self.check()['inputAgeSeconds'])

    def test_missing_and_held_are_distinct_and_noop_does_not_clear_holds(self):
        self.assertEqual(p._inspect(self.spec, None, now=self.now)['state'], 'missing')
        prior = self.check()['planSha256']
        self.spec['holds'] = [{'code': 'use-held', 'owner': 'publisher'}]
        result = self.check(previous_plan=prior)
        self.assertEqual(result['state'], 'held')
        self.assertNotEqual(result['planSha256'], prior)

    def test_pin_release_and_extra_authority_fields_fail(self):
        for field, value in [('inputs', {'tiny.csv': 'b' * 64}), ('releaseId', 'new'),
                             ('rightsApproved', True), ('originalAcquiredAt', self.now)]:
            with self.subTest(field=field):
                original = copy.deepcopy(self.manifest)
                self.manifest[field] = value
                self.assertEqual(self.check()['state'], 'malformed')
                self.manifest = original

    def test_strict_bounded_json_and_times(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":1e999}', b'[]',
                    b'\xff', b'{' * 2000, b'x' * (p.MAX_METADATA + 1)):
            with self.subTest(raw=raw[:20]):
                self.assertEqual(p._inspect(self.spec, raw, now=self.now)['state'], 'malformed')
        for value in ('2026-10-03T00:00:00Z', '2026-10-02', '2026-10-02T00:00:00+11:00'):
            self.manifest['validatedAt'] = value
            self.assertEqual(self.check()['state'], 'malformed')

    def test_all_real_bindings_remain_held_and_declarations_are_exact(self):
        for key, spec in p.catalogue()['bindings'].items():
            raw = canonical(p.request_for(key, '2026-10-18T00:00:00Z'))
            result = p.inspect(key, raw, now='2026-10-18T00:00:00Z')
            self.assertEqual(result['state'], 'held', key)
            self.assertEqual(result['holds'], spec['holds'])
            self.assertFalse(result['countryComplete'])
            self.assertFalse(result['sourceProcessingDispatched'])
            self.assertEqual(len(spec['retainedManifest']['sha256']), 64)
        with self.assertRaises(KeyError):
            p.inspect('authored-only', b'{}', now=self.now)

    def test_held_cache_and_origin_coverage_do_not_claim_semantics(self):
        spec = p.catalogue()['bindings']['BS-cpi-literals']
        result = p.inspect('BS-cpi-literals', canonical(p.request_for('BS-cpi-literals',
                           '2026-12-01T00:00:00Z')), now='2026-12-01T00:00:00Z')
        self.assertEqual(result['state'], 'held')
        self.assertIsNone(result['inputAgeSeconds'])
        self.assertEqual(spec['retainedSnapshotAt'], '2026-10-14T22:11:41.072046+00:00')
        result = p.origin_diagnostics('BS-cpi-literals', {'data': {'value': None},
                                     'provenance': {'sourceId': spec['sourceId']}})
        self.assertIn('field-origins-required', result['structuralErrors'])
        self.assertFalse(result['sourceAccepted'])

    def test_cli_isolated_process_is_bounded_and_cannot_open_source_paths(self):
        raw = canonical(p.request_for('BR-taco4-literals', '2026-10-18T00:00:00Z'))
        def limits():
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024**2,) * 2)
            resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
            resource.setrlimit(resource.RLIMIT_FSIZE, (0, 0))
        run = subprocess.run([sys.executable, '-B', '-m', 'offmenu.refresh.portfolio18',
                              '--binding', 'BR-taco4-literals', '--now', '2026-10-18T00:00:00Z'],
                             input=raw, capture_output=True, timeout=5, preexec_fn=limits,
                             env={'PYTHONDONTWRITEBYTECODE': '1', 'LC_ALL': 'C.UTF-8'})
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertEqual(strict_json(run.stdout)['state'], 'held')
        self.assertLess(len(run.stdout), p.MAX_METADATA)
        self.assertEqual(run.stderr, b'')


class AuthoredProjectionTests(unittest.TestCase):
    """Actual generic qualification on tiny invented assets, never country data."""
    def test_source_contract_field_origins_qualify_and_reject_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            bundle.mkdir()
            assets = []
            for name, body in [('tiny.csv', b'id,value\nr1,0\n'),
                               ('rights.txt', b'authored fixture retain parse transform'),
                               ('scope.txt', b'only r1, invented data')]:
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), sha(body)))
            policy = sha(b'authored unknown marker policy')
            row = {'id': 'r1', 'kind': 'portfolio18Literal', 'schemaVersion': '1.0',
                   'data': {'literal': '0', 'basis': None},
                   'provenance': {'sourceId': 'authored-source', 'releaseId': 'fixture-v1',
                                  'fetchedAt': '2026-10-01T00:00:00Z', 'fieldOrigins': {
                       '/data/literal': {'kind': 'source', 'sourceId': 'authored-source',
                                        'releaseId': 'fixture-v1', 'inputPath': 'tiny.csv',
                                        'inputSha256': assets[0].sha256, 'sourceRecordId': 'r1',
                                        'sourceField': 'row:2/column:2'},
                       '/data/basis': {'kind': 'constant', 'policySha256': policy,
                                       'symbol': 'unknown-basis'}}}}
            def semantics(item):
                errors = field_origin_errors(item, {'tiny.csv': assets[0].sha256}, policy_pins=(policy,))
                if item['data'] != {'literal': '0', 'basis': None}:
                    errors.append('authored-cell-mismatch')
                if item['provenance']['fieldOrigins'].get('/data/literal', {}).get('sourceField') != 'row:2/column:2':
                    errors.append('authored-selector-mismatch')
                return errors
            schemas = {'portfolio18Literal': {'type': 'object', 'required': ['data', 'provenance']}}
            contract = SourceContract('authored-source', 'fixture-v1', 'authored-private-only',
                                      '2026-10-01T00:00:00Z', tuple(assets), 1, ids_digest(['r1']),
                                      schemas, fingerprint(schemas), semantics, policy,
                                      assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                                      fixture=True)
            candidate = root / 'candidate.jsonl'
            def write():
                body = packet([row]) + b'\n'
                candidate.write_bytes(body)
                return {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'candidateSha256': sha(body), 'candidateBytes': len(body),
                        'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets]}
            manifest = write()
            receipt = accept(contract, bundle, candidate, manifest)
            self.assertEqual(receipt['status'], 'accepted-fixture-scope')
            self.assertFalse(receipt['productionAccepted'])
            self.assertEqual(receipt, accept(contract, bundle, candidate, manifest))
            row['provenance']['fieldOrigins']['/data/literal']['sourceField'] = 'wrong'
            failed = qualify(contract, bundle, candidate, write())
            self.assertIn('authored-selector-mismatch', failed['errors'])
            held = qualify(replace(contract, holds=('source-held',)), bundle, candidate, write())
            self.assertIn('source-held', held['errors'])


if __name__ == '__main__':
    unittest.main()
