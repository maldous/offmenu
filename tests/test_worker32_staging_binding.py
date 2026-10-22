"""Small authored metadata fixtures only; never open retained country datasets."""
import copy
from dataclasses import replace
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolio32 import binding as b
from offmenu.refresh.acceptance import (
    Asset, SourceContract, canonical, fingerprint, ids_digest, qualify,
)
from offmenu.refresh.core import strict_json
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.serialization import encode_records


ACQUIRED = '2026-10-01T00:00:00Z'
NOW = '2026-10-03T00:00:00Z'


def authored_context(name, unit, comparison=None):
    return {
        'contextId': name, 'recordIds': [name + '/column0'],
        'cohortApplicabilityEvidence': [{'recordId': name + '/column0'}],
        'sourceArtifact': {'path': 'authored-opaque-table.json', 'sha256': 'd' * 64},
        'sourceRowSelector': '/rows/0',
        **{key: None for key in b.DECISIONS},
        'nutrientSourceIdentityEvidence': {'label': {'literal': 'Authored nutrient (' + unit + ')**'}},
        'compoundUnitAndTimeBasisEvidence': {
            'compoundUnitLiteral': unit, 'denominatorSuffixLiteral': unit.rsplit('/', 1)[1],
            'physicalOrServingBasis': None},
        'dateAndVersionEvidence': {'printedPublicationLiteral': 'Authored historical edition',
                                   'currentPolicyValidity': None},
        'relationAndMarkerEvidence': {'comparisonLiteral': comparison, 'existingSubnoteBinding': None,
                                     'Table4VitaminDNullSTOP': name == 'GB-source-row-39'},
    }


def fixture_document():
    return {'schema': 'offmenu-gb-source-field-evidence-binding/1', 'contexts': 3, 'records': 3,
            'bindings': [authored_context('fixture-row-0', 'g/day', '[Less than]'),
                         authored_context('fixture-row-1', 'mg/d'),
                         authored_context('GB-source-row-39', 'µg/day')]}


def fixture_spec(raw):
    return b.BindingSpec('authored-gb', 'GB', 'authored-phe-metadata', 'authored-only/1',
                         None, hashlib.sha256(raw).hexdigest(), ACQUIRED, 3, 3)


class BindingTests(unittest.TestCase):
    def setUp(self):
        self.doc = fixture_document()
        self.raw = canonical(self.doc)
        self.spec = fixture_spec(self.raw)

    def inspect(self, raw=None, spec=None, **kwargs):
        return b.inspect(spec or self.spec, self.raw if raw is None else raw,
                         observed_at=kwargs.pop('observed_at', NOW), **kwargs)

    def rows(self):
        return [json.loads(line)[0] for line in self.inspect().candidate.splitlines()]

    def test_valid_literal_metadata_and_every_scalar_origin(self):
        result = self.inspect()
        self.assertEqual(result.report['status'], 'ready-metadata')
        self.assertFalse(result.report['sourceProcessingAuthorized'])
        self.assertEqual(result.report['acceptedRecords'], 0)
        rows = self.rows()
        for index, row in enumerate(rows):
            self.assertEqual(set(datum_pointers(row['data'])), set(row['provenance']['fieldOrigins']))
            self.assertEqual(field_origin_errors(row, {'retained-contexts.json': self.spec.metadata_sha256}), [])
            self.assertEqual(b.semantic_validator(self.spec, self.raw)(row), [])
            for key, pointer in b.FIELDS.items():
                self.assertEqual(row['data'][key], b.resolve(self.doc['bindings'][index], pointer))
                self.assertEqual(row['provenance']['fieldOrigins']['/data/' + key]['sourceField']
                                 if key != 'recordIds' else
                                 row['provenance']['fieldOrigins']['/data/recordIds/0']['sourceField'],
                                 f'/bindings/{index}' + pointer + ('/0' if key == 'recordIds' else ''))
        self.assertEqual(rows[1]['data']['unitLiteral'], 'mg/d')
        self.assertEqual(rows[1]['data']['denominatorLiteral'], 'd')
        self.assertIsNone(rows[1]['data']['comparisonLiteral'])
        self.assertTrue(rows[2]['data']['table4VitaminDStop'])
        self.assertIsNone(rows[2]['data']['subnoteBinding'])

    def test_replay_noop_and_validation_age_never_resets_acquisition(self):
        first = self.inspect()
        replay = self.inspect(observed_at='2026-10-04T00:00:00Z',
                              validated_at='2026-10-04T00:00:00Z', previous_candidate=first.candidate)
        self.assertEqual(first.candidate, replay.candidate)
        self.assertEqual(first.report['candidateSha256'], replay.report['candidateSha256'])
        self.assertEqual(replay.report['action'], 'verified-no-op')
        self.assertEqual(replay.report['acquisitionAgeDays'], 3)
        self.assertEqual(replay.report['originalAcquiredAt'], ACQUIRED)
        stale = self.inspect(observed_at='2026-10-31T00:00:00Z', validated_at='2026-10-31T00:00:00Z')
        self.assertEqual(stale.report['status'], 'stale-input')
        self.assertIsNone(stale.candidate)
        self.assertEqual(stale.report['cacheDecision'], 'revalidation-review-required-no-download')
        self.assertEqual(stale.report['networkRequests'], 0)
        self.assertEqual(self.inspect(observed_at='2026-10-30T23:59:59Z').report['status'], 'ready-metadata')

    def test_missing_and_held_do_not_parse_payload(self):
        self.assertEqual(b.inspect(self.spec, None, observed_at=NOW).report['status'], 'missing')
        with patch.object(b, 'strict_json', side_effect=AssertionError('must not parse held source')):
            held = self.inspect(raw=b'secret malformed', spec=replace(self.spec, holds=('source-no-read',)))
        self.assertEqual(held.report['diagnostics'], ['source-held'])
        self.assertIsNone(held.candidate)
        missing_age = self.inspect(spec=replace(self.spec, acquired_at=None))
        self.assertEqual(missing_age.report['diagnostics'], ['original-acquisition-evidence-missing'])

    def test_malformed_pin_json_shape_and_sensitive_values_are_fixed_codes(self):
        self.assertEqual(self.inspect(raw=b'wrong').report['diagnostics'], ['metadata-pin-mismatch'])
        for raw in [b'{"secret":"do-not-echo",', b'{"bindings":[],"bindings":[]}', b'[]']:
            result = self.inspect(raw=raw, spec=replace(self.spec, metadata_sha256=hashlib.sha256(raw).hexdigest()))
            self.assertEqual(result.report['status'], 'malformed')
            self.assertNotIn('do-not-echo', json.dumps(result.report))
            self.assertIsNone(result.candidate)
        self.doc['bindings'][0].pop('compoundUnitAndTimeBasisEvidence')
        raw = canonical(self.doc)
        self.assertIn('metadata-field-missing', self.inspect(raw=raw, spec=fixture_spec(raw)).report['diagnostics'])

    def test_stop_decisions_units_and_duplicate_reference_fail_closed(self):
        mutations = [
            lambda d: d['bindings'][2]['relationAndMarkerEvidence'].update(Table4VitaminDNullSTOP=False),
            lambda d: d['bindings'][0].update(canonicalTarget='invented'),
            lambda d: d['bindings'][1]['compoundUnitAndTimeBasisEvidence'].update(denominatorSuffixLiteral='day'),
            lambda d: d['bindings'][1].update(recordIds=d['bindings'][0]['recordIds']),
        ]
        for mutation in mutations:
            doc = fixture_document(); mutation(doc); raw = canonical(doc)
            result = self.inspect(raw=raw, spec=fixture_spec(raw))
            self.assertEqual(result.report['status'], 'malformed')
            self.assertIsNone(result.candidate)

    def test_clock_errors_and_nonfinite_overflow_fail_closed(self):
        for clock in ['2026-09-30T00:00:00Z', 'not-a-clock', '2026-10-03T00:00:00']:
            self.assertEqual(self.inspect(observed_at=clock).report['status'], 'malformed')
        self.assertEqual(self.inspect(validated_at='2026-10-04T00:00:00Z').report['status'], 'malformed')
        raw = self.raw[:-1] + b' '
        raw = raw.replace(b'"contexts":3', b'"contexts":1e999')
        self.assertEqual(self.inspect(raw=raw, spec=fixture_spec(raw)).report['status'], 'malformed')

    def test_deep_malformed_input_does_not_escape_source_diagnostic(self):
        raw = b'[' * 1200 + b'0' + b']' * 1200
        result = self.inspect(raw=raw, spec=fixture_spec(raw))
        self.assertEqual(result.report['diagnostics'], ['metadata-document-invalid'])
        self.assertIsNone(result.candidate)

    def test_missing_declared_metadata_locator_or_foreign_cohort_is_rejected(self):
        for field in ('cohortApplicabilityEvidence', 'sourceArtifact', 'sourceRowSelector'):
            doc = fixture_document(); doc['bindings'][0].pop(field); raw = canonical(doc)
            result = self.inspect(raw=raw, spec=fixture_spec(raw))
            self.assertIn('source-input-locator-missing', result.report['diagnostics'])
            self.assertIsNone(result.candidate)
        doc = fixture_document()
        doc['bindings'][0]['cohortApplicabilityEvidence'][0]['recordId'] = 'foreign'
        raw = canonical(doc)
        result = self.inspect(raw=raw, spec=fixture_spec(raw))
        self.assertIn('cohort-record-reference-mismatch', result.report['diagnostics'])
        self.assertIsNone(result.candidate)

    def test_nested_source_selectors_preserve_json_pointer_escaping(self):
        self.doc['bindings'][0]['relationAndMarkerEvidence']['existingSubnoteBinding'] = {'a/b~c': [None, 'literal']}
        raw = canonical(self.doc); spec = fixture_spec(raw)
        result = self.inspect(raw=raw, spec=spec)
        row = json.loads(result.candidate.splitlines()[0])[0]
        self.assertEqual(row['provenance']['fieldOrigins']['/data/subnoteBinding/a~1b~0c/0']['sourceField'],
                         '/bindings/0/relationAndMarkerEvidence/existingSubnoteBinding/a~1b~0c/0')
        self.assertEqual(b.semantic_validator(spec, raw)(row), [])

    def test_isolated_batch_diagnostics_continue_after_missing_held_and_bad_input(self):
        specs = [replace(self.spec, key='valid'), replace(self.spec, key='missing'),
                 replace(self.spec, key='held', holds=('private',)), replace(self.spec, key='malformed')]
        with patch('socket.socket', side_effect=AssertionError('network is forbidden')):
            results = b.inspect_many(specs, {'valid': self.raw, 'malformed': b'broken'}, observed_at=NOW)
        self.assertEqual({r.report['key']: r.report['status'] for r in results},
                         {'valid': 'ready-metadata', 'missing': 'missing', 'held': 'held', 'malformed': 'malformed'})
        self.assertTrue(all(r.report['networkRequests'] == 0 for r in results))

    def test_shared_qualification_and_tampered_coordinate_diagnostics(self):
        candidate = self.inspect().candidate
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); bundle = root / 'bundle'; bundle.mkdir()
            bodies = {'retained-contexts.json': self.raw,
                      'rights.json': b'Authored fixture: only retain/parse/transform these fixture bytes.',
                      'scope.json': b'Independent authored fixture IDs: fixture-row-0,fixture-row-1,GB-source-row-39'}
            assets = []
            for name, raw in bodies.items():
                (bundle / name).write_bytes(raw)
                assets.append(Asset(name, len(raw), hashlib.sha256(raw).hexdigest()))
            expected_ids = ['authored-phe-metadata/' + x for x in
                            ('fixture-row-0', 'fixture-row-1', 'GB-source-row-39')]
            schemas = {'retainedSourceInput': b.RECORD_SCHEMA}
            contract = SourceContract(self.spec.source_id, self.spec.release_id, 'authored-metadata-only',
                                      ACQUIRED, tuple(assets), 3, ids_digest(expected_ids), schemas,
                                      fingerprint(schemas), b.semantic_validator(self.spec, self.raw),
                                      b.POLICY_SHA256, assets[1], assets[2],
                                      frozenset(('retain', 'parse', 'transform')), fixture=True)
            path = root / 'candidate.jsonl'
            def run(raw):
                path.write_bytes(raw)
                manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                            'acquiredAt': ACQUIRED, 'normalizedRecords': 3,
                            'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                            'inputFiles': [vars(a) for a in assets], 'candidateBytes': len(raw),
                            'candidateSha256': hashlib.sha256(raw).hexdigest()}
                return qualify(contract, bundle, path, manifest, scratch_root=root)
            result = run(candidate)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            rows = self.rows()
            rows[0]['provenance']['fieldOrigins']['/data/unitLiteral']['sourceField'] = '/bindings/1/unit'
            rows[1]['data']['nutrientLabel'] = 'same schema, wrong value'
            bad = run(encode_records(rows))
            self.assertFalse(bad['qualified'])
            self.assertIn('source-field-selector-mismatch', bad['errors'])
            self.assertIn('source-coordinate-or-value-mismatch', bad['errors'])

    def test_catalog_scope_and_cli_hold_does_not_open_metadata(self):
        config = b.catalog()
        self.assertEqual(set(config['countries']), {'GB', 'GD', 'GE', 'GF'})
        self.assertEqual(len(config['requiredDataTypes']), 6)
        self.assertTrue(all(e['sourceProcessingAuthorized'] is False for e in config['sources']))
        declarations = {e['binding']['country']: e['sourceInputDeclarations'] for e in config['sources']}
        self.assertEqual({country: len(rows) for country, rows in declarations.items()},
                         {'GB': 1, 'GD': 13, 'GE': 9, 'GF': 1})
        for country in ('GD', 'GE'):
            for declaration in declarations[country]:
                self.assertIsNone(declaration['originalAcquiredAt'])
                self.assertIsNone(declaration['nativeUnit'])
                self.assertIsNone(declaration['nativeBasis'])
                self.assertIn('rightsEvidence', declaration['fieldSelectors'])
        held = replace(self.spec, key='held', holds=('no-read',), metadata_path='/must/not/open.pdf')
        with patch.object(b, 'specs', return_value=(held,)), patch.object(b, 'safe_path', side_effect=AssertionError()), patch('sys.stdout', new_callable=io.StringIO) as out:
            code = b.main(['--key', 'held', '--observed-at', NOW])
        self.assertEqual(code, 2)
        self.assertEqual(strict_json(out.getvalue())['bindings'][0]['status'], 'held')

    def test_cli_emits_deterministic_fixture_candidate_without_path_following(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'metadata.json'; path.write_bytes(self.raw)
            spec = replace(self.spec, metadata_path=str(path))
            outputs = []
            for _ in range(2):
                with patch.object(b, 'specs', return_value=(spec,)), patch('sys.stdout', new_callable=io.StringIO) as out:
                    code = b.main(['--key', spec.key, '--observed-at', NOW, '--emit-candidate'])
                self.assertEqual(code, 0); outputs.append(out.getvalue())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(outputs[0].encode(), self.inspect().candidate)


class Same4CorrectionTests(unittest.TestCase):
    """Only new authored regressions for review6452; prior13 coverage retained."""

    def test_nested_json_types_are_exact_in_callback_and_shared_qualification(self):
        for original, substituted in [(0, False), (1, True), (False, 0), (True, 1)]:
            with self.subTest(original=repr(original), substituted=repr(substituted)):
                document = fixture_document()
                document['bindings'][0]['relationAndMarkerEvidence']['existingSubnoteBinding'] = {
                    'nested': [original]}
                raw = canonical(document); spec = fixture_spec(raw)
                candidate = b.inspect(spec, raw, observed_at=NOW).candidate
                rows = [json.loads(line)[0] for line in candidate.splitlines()]
                callback = b.semantic_validator(spec, raw)
                self.assertEqual(callback(rows[0]), [])
                changed = copy.deepcopy(rows)
                changed[0]['data']['subnoteBinding']['nested'][0] = substituted
                self.assertIn('source-coordinate-or-value-mismatch', callback(changed[0]))
                with tempfile.TemporaryDirectory() as temp:
                    root = Path(temp); bundle = root / 'bundle'; bundle.mkdir()
                    assets = []
                    for name, body in [('retained-contexts.json', raw),
                                       ('rights.json', b'authored correction fixture only'),
                                       ('scope.json', b'authored fixture-row-0,fixture-row-1,GB-source-row-39')]:
                        (bundle / name).write_bytes(body)
                        assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
                    schemas = {'retainedSourceInput': b.RECORD_SCHEMA}
                    contract = SourceContract(spec.source_id, spec.release_id, 'authored-type-regression',
                        ACQUIRED, tuple(assets), 3,
                        ids_digest(['authored-phe-metadata/' + key for key in
                                    ('fixture-row-0', 'fixture-row-1', 'GB-source-row-39')]),
                        schemas, fingerprint(schemas), callback, b.POLICY_SHA256,
                        assets[1], assets[2], frozenset(('retain', 'parse', 'transform')), fixture=True)
                    path = root / 'candidate.jsonl'
                    def check(content):
                        path.write_bytes(content)
                        manifest = {'sourceId': spec.source_id, 'releaseId': spec.release_id,
                            'acquiredAt': ACQUIRED, 'normalizedRecords': 3,
                            'rightsEvidenceSha256': assets[1].sha256,
                            'scopeEvidenceSha256': assets[2].sha256,
                            'inputFiles': [vars(a) for a in assets],
                            'candidateBytes': len(content), 'candidateSha256': hashlib.sha256(content).hexdigest()}
                        return qualify(contract, bundle, path, manifest, scratch_root=root)
                    self.assertTrue(check(candidate)['qualified'])
                    result = check(encode_records(changed))
                    self.assertFalse(result['qualified'])
                    self.assertIn('source-coordinate-or-value-mismatch', result['errors'])

    def test_reader_is_bounded_regular_single_open_and_closes_descriptor(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'metadata.json'; path.write_bytes(b'authored')
            captured = []
            real_open = os.open
            def opened(*args, **kwargs):
                fd = real_open(*args, **kwargs); captured.append(fd); return fd
            with patch.object(b.os, 'open', side_effect=opened) as reader:
                self.assertEqual(b._read_metadata(path), b'authored')
            self.assertEqual(reader.call_count, 1)
            with self.assertRaises(OSError):
                os.fstat(captured[0])
            with self.assertRaises(FileNotFoundError):
                b._read_metadata(root / 'missing.json')
            with self.assertRaises(ValueError):
                b._read_metadata(root)
            alias = root / 'alias.json'; alias.symlink_to(path)
            with self.assertRaises(ValueError):
                b._read_metadata(alias)
            with patch.object(b, 'MAX_METADATA', 3):
                with self.assertRaises(ValueError):
                    b._read_metadata(path)

    def test_path_replacement_does_not_reopen_or_read_fifo(self):
        import os
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); path = root / 'metadata.json'; path.write_bytes(b'opened-snapshot')
            real_open = os.open
            def replace_after_open(*args, **kwargs):
                fd = real_open(*args, **kwargs)
                path.rename(root / 'opened-original.json')
                os.mkfifo(path)
                return fd
            with patch.object(b.os, 'open', side_effect=replace_after_open) as reader:
                self.assertEqual(b._read_metadata(path), b'opened-snapshot')
            self.assertEqual(reader.call_count, 1)

    def test_actual_cli_fifo_is_fixed_diagnostic_and_peer_continues(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as temp:
            fifo = Path(temp) / 'authored-fifo.json'; os.mkfifo(fifo)
            code = r'''
import sys
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1])
from offmenu.portfolio32 import binding as b
from unittest.mock import patch
bad=b.BindingSpec('authored-fifo','GB','authored-only','1',sys.argv[2],'a'*64,'2026-10-01T00:00:00Z',3,3)
peer=b.BindingSpec('held-peer','GD','authored-peer','1','must-not-open','b'*64,None,0,0,('explicit-authored-hold',))
print('ENTERED_CLI',flush=True)
with patch.object(b,'specs',return_value=(bad,peer)):
 status=b.main(['--observed-at','2026-10-03T00:00:00Z'])
raise SystemExit(status)
'''
            run = subprocess.run([sys.executable, '-I', '-B', '-c', code,
                                  str(Path(__file__).resolve().parents[1]), str(fifo)],
                                 capture_output=True, text=True, timeout=3)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertTrue(run.stdout.startswith('ENTERED_CLI\n'))
            result = json.loads(run.stdout.splitlines()[1])
            self.assertEqual([(row['key'], row['status']) for row in result['bindings']],
                             [('authored-fifo', 'malformed'), ('held-peer', 'held')])
            self.assertEqual(result['bindings'][0]['diagnostics'], ['metadata-input-io-invalid'])
            self.assertTrue(all(row['networkRequests'] == 0 for row in result['bindings']))


if __name__ == '__main__':
    unittest.main()
