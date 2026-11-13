import copy
from dataclasses import replace
from datetime import datetime, timezone
from functools import partial
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import (Asset, SourceContract, fingerprint,
                                        ids_digest, qualify)
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio34 import (Binding, MetadataPin, diagnose, pointer,
                                         report, semantic_errors)
from offmenu.refresh.portfolio34_bindings import BINDINGS
from offmenu.refresh.serialization import encode_records

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)
ROOT = Path(__file__).resolve().parents[1]


class Portfolio34Tests(unittest.TestCase):
    def fixture(self, **changes):
        # All content authored here; no publisher body or retained data is read.
        doc = {'acquiredAt': '2026-10-01T00:00:00Z', 'validatedAt': '2026-10-17T00:00:00Z',
               'table': {'label': 'Authored sample', 'unit': None, 'basis': None,
                         'value': '0', 'qualifier': 'unknown'},
               'rights': 'Authored fixture only'}
        doc.update(changes)
        raw = canonical(doc)
        spec = Binding('GT', 'authored-source', 'authored-release', 'authored-metadata-only',
                       (MetadataPin('metadata.json', '/unused-authored-metadata', sha(raw)),),
                       (('table', 'metadata.json', '/table'),
                        ('rights', 'metadata.json', '/rights')),
                       ('metadata.json', '/acquiredAt'), (), (), True)
        return spec, {'metadata.json': raw}, doc

    def test_valid_and_unchanged_replay_are_identical_without_io(self):
        spec, supplied, _ = self.fixture()
        with patch('builtins.open', side_effect=AssertionError('no IO')):
            first = diagnose(spec, supplied, now=NOW)
            replay = diagnose(spec, supplied, now=NOW, previous_key=first['inputKey'])
        self.assertEqual(first['status'], 'ready-metadata-only')
        self.assertEqual(replay['contentReplay'], 'unchanged-no-op')
        self.assertEqual(encode_records(first['rows']), encode_records(replay['rows']))
        self.assertFalse(first['sourceDataAccepted'])
        self.assertEqual(first['networkRequests'], 0)
        self.assertEqual(first['capabilities']['sharedPureRawCachePlanner'],
                         'unavailable-on-pinned-baseline')
        self.assertEqual(first['rows'][0]['data']['table']['unit'], None)
        self.assertEqual(first['rows'][0]['data']['table']['value'], '0')

    def test_missing_metadata_and_selector_are_typed(self):
        spec, supplied, _ = self.fixture()
        self.assertEqual(diagnose(spec, {}, now=NOW)['status'], 'missing-input')
        missing = replace(spec, fields=(('table', 'metadata.json', '/absent'),))
        self.assertEqual(diagnose(missing, supplied, now=NOW)['errors'],
                         ['metadata-selector-missing'])

    def test_held_even_when_bytes_valid_and_fresh(self):
        spec, supplied, _ = self.fixture()
        held = replace(spec, holds=('retained-use-hold',))
        result = diagnose(held, supplied, now=NOW)
        self.assertEqual(result['status'], 'held')
        self.assertIn('source-held', result['errors'])
        self.assertEqual(result['sourceBodyOperations'], 0)

    def test_pin_mismatch_does_not_parse_changed_input(self):
        spec, supplied, _ = self.fixture()
        result = diagnose(spec, {'metadata.json': b'changed confidential malformed'}, now=NOW)
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['errors'], ['metadata-pin-mismatch'])
        self.assertEqual(result['rows'], [])

    def test_malformed_duplicate_nonfinite_oversized_are_fixed_errors(self):
        spec, _, _ = self.fixture()
        for raw in [b'{"x":1,"x":2}', b'{"x":1e9999}', b'not json', b'\xff']:
            bad = replace(spec, metadata=(MetadataPin('metadata.json', '/unused', sha(raw)),))
            r = diagnose(bad, {'metadata.json': raw}, now=NOW)
            self.assertEqual(r['status'], 'malformed')
            self.assertEqual(r['errors'], ['metadata-json-invalid'])
        r = diagnose(spec, {'metadata.json': b'x' * (512*1024+1)}, now=NOW)
        self.assertEqual(r['errors'], ['metadata-bound-or-type-invalid'])

    def test_acquisition_clock_not_validation_clock_controls_30day_boundary(self):
        spec, supplied, _ = self.fixture(acquiredAt='2026-09-18T00:00:00Z',
                                        validatedAt='2026-10-18T00:00:00Z')
        r = diagnose(spec, supplied, now=NOW)
        self.assertEqual(r['status'], 'stale-input')
        self.assertEqual(r['cache']['acquisitionAgeDays'], 30)
        self.assertEqual(r['cache']['scope'], 'metadata-age-intent-only')
        self.assertFalse(r['cache']['validationAgeResetsAcquisition'])
        self.assertEqual(r['cache']['decision'], 'conditional-review-required-no-download')
        self.assertEqual(r['networkRequests'], 0)

    def test_unknown_or_future_acquisition_never_becomes_fresh(self):
        spec, supplied, _ = self.fixture()
        missing = diagnose(replace(spec, acquisition=None), supplied, now=NOW)
        self.assertIn('original-acquisition-evidence-missing', missing['errors'])
        spec, supplied, _ = self.fixture(acquiredAt='2027-01-01T00:00:00Z')
        self.assertIn('original-acquisition-in-future', diagnose(spec, supplied, now=NOW)['errors'])
        self.assertEqual(diagnose(spec, supplied, now=NOW.replace(tzinfo=None))['status'], 'malformed')

    def test_all_datum_origins_and_literal_selector_semantics(self):
        spec, supplied, doc = self.fixture()
        row = diagnose(spec, supplied, now=NOW)['rows'][0]
        self.assertEqual(field_origin_errors(row, {'metadata.json': spec.metadata[0].sha256}), [])
        unit = row['provenance']['fieldOrigins']['/data/table/unit']
        self.assertEqual(unit['sourceField'], '/table/unit')
        wrong = copy.deepcopy(row)
        wrong['data']['table']['unit'] = 'invented-g'
        self.assertIn('metadata-selector-value-mismatch', semantic_errors(spec, {'metadata.json': doc}, wrong))
        wrong = copy.deepcopy(row)
        del wrong['provenance']['fieldOrigins']['/data/table/unit']
        self.assertIn('field-origin-missing', semantic_errors(spec, {'metadata.json': doc}, wrong))

    def test_pointer_strictness_and_no_coercion(self):
        self.assertEqual(pointer({'a/b': {'~': [None, '0']}}, '/a~1b/~0/1'), '0')
        for path in ['/a~2b', '/x/01', '/x/-1']:
            with self.assertRaises((KeyError, ValueError)):
                pointer({'x': [1, 2]}, path)

    def test_peer_failures_are_isolated_and_do_not_leak_values(self):
        spec, supplied, _ = self.fixture()
        peer = replace(spec, source_id='peer')
        def loader(binding):
            if binding.source_id == 'authored-source':
                raise RuntimeError('SECRET-EXCEPTION-DETAIL')
            return supplied
        r = report([spec, peer], now=NOW, loader=loader)
        self.assertEqual([x['status'] for x in r['results']], ['malformed', 'ready-metadata-only'])
        self.assertNotIn('SECRET', json.dumps(r))

    def test_fixed_portfolio_cannot_imply_food_admission(self):
        self.assertEqual({b.country for b in BINDINGS}, {'GQ', 'GS', 'GT', 'GU'})
        self.assertTrue(all(b.holds and b.unknowns and not b.fixture for b in BINDINGS))
        self.assertTrue(all(p.path.endswith('.json') for b in BINDINGS for p in b.metadata))
        self.assertTrue(all(b.acquisition is None for b in BINDINGS if b.country in ('GS', 'GT', 'GU')))

    def test_module_cli_uses_same_binding_class_and_only_declared_metadata(self):
        # Patch the canonical reader before exercising the actual -m entrypoint.
        # This is portable: tests never depend on the historical receipt paths existing.
        script = """import runpy,sys
import offmenu.refresh.portfolio34 as p
p.read_declared_metadata=lambda binding: {}
sys.argv=['portfolio34','--now','2026-10-18T00:00:00Z']
runpy.run_module('offmenu.refresh.portfolio34',run_name='__main__')
"""
        proc = subprocess.run([sys.executable, '-c', script],
                              cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        results = json.loads(proc.stdout)['results']
        self.assertEqual([r['country'] for r in results], ['GQ', 'GS', 'GT', 'GU'])
        self.assertTrue(all(r['status'] == 'missing-input' for r in results))

    def test_shared_qualification_accepts_only_authored_metadata_fixture(self):
        spec, supplied, doc = self.fixture()
        row = diagnose(spec, supplied, now=NOW)['rows'][0]
        schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                  'properties': {'kind': {'const': 'sourceInputDeclaration'},
                                 'schemaVersion': {'const': '1.0'},
                                 'data': {'type': 'object', 'required': ['table', 'rights']}}}
        schemas = {'sourceInputDeclaration': schema}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); bundle = root/'bundle'; bundle.mkdir()
            inputs = {**supplied, 'rights.json': canonical({'scope': 'authored-fixture-only'}),
                      'scope.json': canonical({'ids': [row['id']]})}
            assets = tuple(Asset(name, len(raw), sha(raw)) for name, raw in inputs.items())
            for name, raw in inputs.items(): (bundle/name).write_bytes(raw)
            candidate = root/'candidate.jsonl'; raw = encode_records([row]); candidate.write_bytes(raw)
            contract = SourceContract(spec.source_id, spec.release_id, 'authored-metadata-only',
                                      doc['acquiredAt'], assets, 1, ids_digest([row['id']]), schemas,
                                      fingerprint(schemas), partial(semantic_errors, spec, {'metadata.json': doc}),
                                      'f'*64, assets[1], assets[2],
                                      frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = {'sourceId': spec.source_id, 'releaseId': spec.release_id,
                        'acquiredAt': doc['acquiredAt'], 'normalizedRecords': 1,
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets],
                        'candidateBytes': len(raw), 'candidateSha256': sha(raw)}
            r = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertTrue(r['qualified'], r['errors'])
            self.assertTrue(r['fixture'])
            wrong = copy.deepcopy(row); wrong['data']['table']['value'] = 'changed'
            raw = encode_records([wrong]); candidate.write_bytes(raw)
            manifest.update(candidateBytes=len(raw), candidateSha256=sha(raw))
            r = qualify(contract, bundle, candidate, manifest, scratch_root=root)
            self.assertFalse(r['qualified'])
            self.assertIn('metadata-selector-value-mismatch', r['errors'])


if __name__ == '__main__':
    unittest.main()
