"""Authored metadata only; no retained raw dataset is opened by these tests."""
import copy
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu import portfolio_worker62 as w
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh import acceptance as q


RAW = (Path(__file__).parent / 'fixtures/worker62-metadata.json').read_bytes()


def config(raw=RAW, *, holds=()):
    return {'schemaVersion': 'worker62-metadata-bindings/1',
        'countries': list(w.COUNTRIES),
        'metadata': {'fixture': {'path': '/authored/metadata.json',
                                'bytes': len(raw), 'sha256': sha(raw)}},
        'sources': [{'sourceId': 'authored-gr', 'releaseId': 'authored-v1',
            'country': 'GR', 'countryTypes': ['dietary references'],
            'holds': list(holds), 'fields': {name: {'metadata': 'fixture', 'selector': ptr}
                for name, ptr in [('release', '/release'), ('originalAcquiredAt', '/captured'),
                                  ('nativeUnit', '/literalUnit'), ('nativeBasis', '/literalBasis'),
                                  ('sourceNull', '/nullValue')]},
            'unknowns': {'bodySelector': 'No body has been selected.'}}]}


class Worker62MetadataTests(unittest.TestCase):
    def run_binding(self, cfg=None, metadata=None, **kwargs):
        return w.bind(cfg or config(), {'fixture': RAW} if metadata is None else metadata,
                      now=kwargs.pop('now', '2026-10-02T00:00:00Z'), **kwargs)

    def test_valid_preserves_native_values_and_exact_origins(self):
        cfg = config()
        raw, report = self.run_binding(cfg)
        row = json.loads(raw)[0]
        self.assertEqual(report['outcomes'][0]['status'], 'valid')
        self.assertEqual(row['data']['nativeUnit'], 'source-native-unit')
        self.assertEqual(row['data']['nativeBasis'], 'source-native-basis')
        self.assertIsNone(row['data']['sourceNull'])
        self.assertIsNone(row['data']['bodySelector'])
        self.assertEqual(row['provenance']['fieldOrigins']['/data/sourceNull']['sourceField'], '/nullValue')
        self.assertEqual(field_origin_errors(row, {'metadata/fixture.json': sha(RAW)},
                         policy_pins=(sha(canonical(cfg)),)), [])
        self.assertEqual(len(report['countryRequirements']), 24)
        self.assertFalse(any(x['accepted'] for x in report['countryRequirements']))
        self.assertEqual(report['acceptedDatasetRecords'], 0)

    def test_replay_key_and_candidate_ignore_validation_age_and_clock(self):
        raw, first = self.run_binding()
        raw2, replay = self.run_binding(previous_key=first['contentKey'],
            validated_at='2026-10-02T00:00:00Z', now='2026-10-20T00:00:00Z')
        self.assertEqual(raw, raw2)
        self.assertEqual(first['contentKey'], replay['contentKey'])
        self.assertEqual(replay['replay'], 'no-op')
        self.assertEqual(replay['outcomes'][0]['cache']['acquisitionAgeDays'], 19)
        self.assertEqual(replay['outcomes'][0]['cache']['validationAgeDays'], 18)

    def test_cache_threshold_is_original_acquisition_not_validation(self):
        _, before = self.run_binding(now='2026-10-30T23:59:59Z')
        _, after = self.run_binding(now='2026-10-31T00:00:00Z',
                                   validated_at='2026-10-30T23:59:59Z')
        self.assertTrue(before['outcomes'][0]['cache']['underMinimumReuseWindow'])
        cache = after['outcomes'][0]['cache']
        self.assertFalse(cache['underMinimumReuseWindow'])
        self.assertEqual(cache['decision'], 'unsupported-source-neutral-cache-planner')
        self.assertFalse(cache['conditionalRefreshEligible'])
        self.assertEqual(cache['networkRequests'], 0)
        self.assertEqual(cache['acquisitionAgeDays'], 30)

    def test_missing_input_and_selector_are_isolated(self):
        cfg = config()
        second = copy.deepcopy(cfg['sources'][0])
        second['sourceId'] = 'authored-om'
        second['country'] = 'OM'
        second['fields']['release']['selector'] = '/absent'
        cfg['sources'].append(second)
        raw, report = self.run_binding(cfg)
        self.assertEqual(report['metadataRecords'], 1)
        self.assertEqual([x['status'] for x in report['outcomes']], ['valid', 'missing'])
        self.assertEqual(len(raw.splitlines()), 1)
        raw, report = self.run_binding(metadata={})
        self.assertEqual(raw, b'')
        self.assertEqual(report['outcomes'][0]['status'], 'missing')

    def test_hold_keeps_metadata_without_body_permission(self):
        raw, report = self.run_binding(config(holds=('explicit-body-hold',)))
        outcome = report['outcomes'][0]
        self.assertEqual(outcome['status'], 'held')
        self.assertEqual(outcome['holds'], ['explicit-body-hold'])
        self.assertEqual(outcome['bodyProcessing'], 'not-selected')
        self.assertEqual(outcome['metadataStage']['status'], 'held')
        self.assertTrue(raw)
        self.assertEqual(report['bodyOperations'], 0)

    def test_malformed_pinned_json_and_stale_bytes_are_distinct(self):
        for malformed in (b'{', b'{"release":1,"release":2}', b'{"bad":NaN}'):
            with self.subTest(raw=malformed):
                raw, report = self.run_binding(config(malformed), {'fixture': malformed})
                self.assertEqual(raw, b'')
                self.assertEqual(report['outcomes'][0]['status'], 'malformed')
        raw, report = self.run_binding(metadata={'fixture': RAW + b' '})
        self.assertEqual(raw, b'')
        self.assertEqual(report['outcomes'][0]['status'], 'stale-input')

    def test_null_is_present_and_invalid_pointer_is_rejected(self):
        self.assertIsNone(w.pointer({'a/b': {'~': None}}, '/a~1b/~0'))
        for ptr in ('bad', '/a~2', '/01', '/-'):
            with self.subTest(ptr=ptr), self.assertRaises(RefreshError):
                w.pointer([1], ptr)

    def test_bad_time_and_configuration_do_not_infer_values(self):
        for now in ('2026-10-02', 'not-a-time'):
            with self.assertRaises(RefreshError):
                self.run_binding(now=now)
        _, report = self.run_binding(now='2026-09-30T00:00:00Z')
        self.assertEqual(report['outcomes'][0]['status'], 'malformed')
        cfg = config()
        cfg['sources'].append(copy.deepcopy(cfg['sources'][0]))
        with self.assertRaises(RefreshError):
            self.run_binding(cfg)

    def test_cli_reads_only_allowlisted_metadata_and_noop_keeps_candidate_mtime(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            meta = root / 'metadata.json'
            meta.write_bytes(RAW)
            cfg = config()
            cfg['metadata']['fixture']['path'] = str(meta)
            cfg['sources'][0]['originalReference'] = {'path': '/DO-NOT-READ.pdf'}
            output = root / 'output'
            with patch.object(w, 'load_catalogue', return_value=cfg), patch('builtins.print'):
                w.main(['--now', '2026-10-02T00:00:00Z', '--output', str(output)])
                candidate = output / 'metadata-candidate.jsonl'
                before = candidate.stat().st_mtime_ns
                w.main(['--now', '2026-10-03T00:00:00Z', '--output', str(output)])
                self.assertEqual(candidate.stat().st_mtime_ns, before)
                self.assertEqual(json.loads((output / 'metadata-report.json').read_bytes())['replay'], 'no-op')

    def test_repo_config_is_metadata_only_and_every_real_binding_held(self):
        cfg = json.loads(w.CONFIG.read_bytes())
        w._validate(cfg)
        self.assertEqual(len(cfg['sources']), 10)
        self.assertTrue(all(s['holds'] for s in cfg['sources']))
        self.assertEqual({s['country'] for s in cfg['sources']}, set(w.COUNTRIES))
        self.assertTrue(all(p['path'].endswith('.json') for p in cfg['metadata'].values()))

    def test_authored_metadata_qualifies_under_explicit_fixture_contract_only(self):
        cfg = config()
        raw, _ = self.run_binding(cfg)
        schemas = {'source-input-metadata-reference': {
            'type': 'object', 'additionalProperties': False,
            'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
            'properties': {
                'id': {'const': 'authored-gr'},
                'kind': {'const': 'source-input-metadata-reference'},
                'schemaVersion': {'const': 1},
                'data': {'type': 'object', 'additionalProperties': False,
                    'required': ['release', 'originalAcquiredAt', 'nativeUnit',
                                 'nativeBasis', 'sourceNull', 'bodySelector'],
                    'properties': {'release': {'const': 'authored-v1'},
                        'originalAcquiredAt': {'const': '2026-10-01T00:00:00Z'},
                        'nativeUnit': {'const': 'source-native-unit'},
                        'nativeBasis': {'const': 'source-native-basis'},
                        'sourceNull': {'type': 'null'}, 'bodySelector': {'type': 'null'}}},
                'provenance': {'type': 'object', 'additionalProperties': False,
                    'required': ['sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins'],
                    'properties': {'sourceId': {'const': 'authored-gr'},
                        'releaseId': {'const': 'authored-v1'},
                        'fetchedAt': {'const': '2026-10-01T00:00:00Z'},
                        'fieldOrigins': {'type': 'object'}}}}}}
        # Trusted authored test configuration; never derived from the real portfolio.
        def semantics(row):
            return field_origin_errors(row, {'metadata/fixture.json': sha(RAW)},
                                       policy_pins=(sha(canonical(cfg)),))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root / 'bundle'
            (bundle / 'metadata').mkdir(parents=True)
            assets = []
            for name, content in [('metadata/fixture.json', RAW),
                ('rights.json', b'{"scope":"authored metadata fixture only"}'),
                ('scope.json', b'{"ids":["authored-gr"],"records":1}')]:
                (bundle / name).write_bytes(content)
                assets.append(q.Asset(name, len(content), sha(content)))
            contract = q.SourceContract(source_id='authored-gr', release_id='authored-v1',
                scope_id='worker62-authored-metadata-only',
                acquired_at='2026-10-01T00:00:00Z', inputs=tuple(assets),
                expected_records=1, expected_ids_sha256=q.ids_digest(['authored-gr']),
                schemas=schemas, schemas_sha256=q.fingerprint(schemas),
                semantic_validator=semantics, policy_sha256=sha(canonical(cfg)),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = {'sourceId': 'authored-gr', 'releaseId': 'authored-v1',
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'candidateBytes': len(raw), 'candidateSha256': sha(raw),
                'inputFiles': [vars(asset) for asset in assets],
                'rightsEvidenceSha256': assets[1].sha256,
                'scopeEvidenceSha256': assets[2].sha256}
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(raw)
            result = q.qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])
            result = q.qualify(replace(contract, holds=('authored-hold',)),
                               bundle, candidate, manifest)
            self.assertFalse(result['qualified'])
            self.assertIn('source-held', result['errors'])

    def test_fifo_metadata_returns_promptly_and_keeps_valid_peer(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fifo = root / 'fifo.json'
            os.mkfifo(fifo)
            regular = root / 'regular.json'
            regular.write_bytes(RAW)
            cfg = config()
            cfg['metadata']['fixture']['path'] = str(fifo)
            cfg['metadata']['good'] = dict(cfg['metadata']['fixture'], path=str(regular))
            peer = copy.deepcopy(cfg['sources'][0])
            peer.update(sourceId='authored-om', country='OM')
            for field in peer['fields'].values():
                field['metadata'] = 'good'
            cfg['sources'].append(peer)
            cp = root / 'config.json'
            cp.write_bytes(canonical(cfg))
            # A timeout kills/reaps the authored child, so a regression cannot hang
            # the test runner on an unconnected FIFO.
            code = ('import json,sys; from pathlib import Path; '
                'from offmenu import portfolio_worker62 as w; '
                'c=json.loads(Path(sys.argv[1]).read_bytes()); '
                '_,r=w.bind(c,w.load_metadata(c),now="2026-10-02T00:00:00Z"); '
                'print(json.dumps(r))')
            child = subprocess.run([sys.executable, '-B', '-c', code, str(cp)],
                capture_output=True, text=True, timeout=3, check=True)
            report = json.loads(child.stdout)
            self.assertEqual([x['status'] for x in report['outcomes']], ['malformed', 'valid'])
            self.assertEqual(report['outcomes'][0]['diagnostics'], ['metadata-file-invalid'])
            self.assertEqual(report['metadataRecords'], 1)

    def test_nonregular_swap_after_stat_is_checked_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'metadata.json'
            path.write_bytes(RAW)
            cfg = config()
            cfg['metadata']['fixture']['path'] = str(path)
            original_open = os.open
            def swapped_open(name, flags, *args, **kwargs):
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                path.unlink()
                path.mkdir()
                return original_open(name, flags, *args, **kwargs)
            with patch.object(w.os, 'open', side_effect=swapped_open):
                result = w.load_metadata(cfg)
            self.assertEqual(result['fixture'], w.MetadataReadFailure.INVALID)

    def test_both_output_targets_preflighted_before_either_artifact_changes(self):
        candidate, first = self.run_binding()
        for name in ('metadata-candidate.jsonl', 'metadata-report.json'):
            for kind in ('hardlink', 'fifo', 'symlink', 'directory'):
                with self.subTest(name=name, kind=kind), tempfile.TemporaryDirectory() as td:
                    root = Path(td)
                    output = root / 'output'
                    output.mkdir()
                    outside = root / 'outside'
                    outside.write_bytes(b'authored outside sentinel')
                    bad = output / name
                    if kind == 'hardlink':
                        os.link(outside, bad)
                    elif kind == 'fifo':
                        os.mkfifo(bad)
                    elif kind == 'symlink':
                        bad.symlink_to(outside)
                    else:
                        bad.mkdir()
                    other = output / ('metadata-report.json' if name.endswith('jsonl')
                                      else 'metadata-candidate.jsonl')
                    other.write_bytes(b'authored other artifact sentinel')
                    with self.assertRaises(RefreshError):
                        w._publish(output, candidate, copy.deepcopy(first))
                    self.assertEqual(outside.read_bytes(), b'authored outside sentinel')
                    self.assertEqual(other.read_bytes(), b'authored other artifact sentinel')
                    self.assertFalse(list(output.glob('.worker62-*.tmp')))

    def test_output_replacement_does_not_modify_external_alias_inserted_after_preflight(self):
        candidate, report = self.run_binding()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            output = root / 'output'
            output.mkdir()
            outside = root / 'outside'
            outside.write_bytes(b'authored race sentinel')
            original_replace = os.replace
            def replace_with_racing_link(src, dst, **kwargs):
                os.link(outside, output / dst)
                return original_replace(src, dst, **kwargs)
            with patch.object(w.os, 'replace', side_effect=replace_with_racing_link):
                w._publish(output, candidate, report)
            self.assertEqual(outside.read_bytes(), b'authored race sentinel')
            self.assertEqual((output / 'metadata-candidate.jsonl').read_bytes(), candidate)
            self.assertFalse(list(output.glob('.worker62-*.tmp')))

    def test_overflow_number_isolated_before_portfolio_serialization(self):
        bad = RAW.replace(b'"source-native-unit"', b'1e999')
        cfg = config(bad)
        cfg['metadata']['good'] = dict(config()['metadata']['fixture'])
        peer = copy.deepcopy(cfg['sources'][0])
        peer.update(sourceId='authored-om', country='OM')
        for field in peer['fields'].values():
            field['metadata'] = 'good'
        cfg['sources'].append(peer)
        candidate, report = self.run_binding(cfg, {'fixture': bad, 'good': RAW})
        self.assertEqual([x['status'] for x in report['outcomes']], ['malformed', 'valid'])
        self.assertEqual(report['outcomes'][0]['diagnostics'], ['metadata-malformed'])
        self.assertEqual(report['metadataRecords'], 1)
        self.assertEqual(json.loads(candidate)[0]['id'], 'authored-om')


if __name__ == '__main__':
    unittest.main()
