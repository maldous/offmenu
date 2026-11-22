"""Small authored metadata; no retained datasets, acquisition or old suites."""
import contextlib
import io
from dataclasses import replace
import json
import os
import subprocess
import sys
from unittest import mock
from pathlib import Path
import tempfile
import unittest

from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio_w07 import bind_one, main, plan, write_metadata_stage

FIXTURE = Path(__file__).parent / 'fixtures/portfolio-w07/authored-metadata.json'
NOW = '2026-10-18T00:00:00Z'


def spec(raw=None, binding='authored-one'):
    raw = FIXTURE.read_bytes() if raw is None else raw
    return {'bindingId': binding, 'country': 'AS', 'dataType': 'nutrition',
            'sourceId': 'authored-w07', 'releaseId': 'fixture-1', 'sourceRole': 'authored-metadata',
            'operation': 'stage-retained-metadata', 'metadataUse': 'permitted-retained-metadata',
            'applicability': 'source-context-only', 'sourceDataOperations': [],
            'manifest': {'path': 'metadata/authored.json', 'bytes': len(raw), 'sha256': sha(raw)},
            'acquiredAtSelector': '/captureAt', 'acquisitionKind': 'metadata-response',
            'fields': [{'name': 'measure', 'selector': '/measure/value', 'unitSelector': '/measure/unit',
                        'basisSelector': '/measure/basis'},
                       {'name': 'unknown', 'selector': '/unknown'},
                       {'name': 'zero', 'selector': '/zero'},
                       {'name': 'names', 'selector': '/names'}], 'holds': []}


class PortfolioW07Tests(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.s = spec()

    def bind(self, s=None, raw=None, now=NOW):
        return bind_one(self.s if s is None else s, self.raw if raw is None else raw, now=now)

    def test_valid_shared_origin_contract(self):
        r = self.bind()
        self.assertEqual(r['outcome'], 'valid')
        self.assertEqual(field_origin_errors(r['candidate'], {'metadata/authored.json': sha(self.raw)},
                                           policy_pins=(r['policySha256'],)), [])
        self.assertFalse(r['countryDataAdmission'])

    def test_literal_units_basis_decimal_unknown_and_zero(self):
        data = self.bind()['candidate']['data']
        self.assertEqual(data['measure'], {'value': '1,25', 'unit': 'g', 'basis': {'amount': '100', 'unit': 'g'}})
        self.assertEqual(data['zero']['value'], 0)
        self.assertIsNone(data['unknown']['value'])
        self.assertIsNone(data['unknown']['unit'])
        self.assertEqual(data['names']['value'], ['Samoa', 'American Samoa'])

    def test_country_applicability_never_inferred_from_names(self):
        self.s['applicability'] = 'unknown'
        r = self.bind()
        self.assertEqual(r['outcome'], 'held')
        self.assertIn('w07-country-type-applicability-unqualified', r['diagnostics'])

    def test_hold_is_not_rights_grant(self):
        self.s['holds'] = ['source-use-unqualified']
        r = self.bind()
        self.assertEqual(r['outcome'], 'held')
        self.assertFalse(r['cache']['sourceBodyReuseApproved'])

    def test_missing_metadata(self):
        self.assertEqual(bind_one(self.s, None, now=NOW)['outcome'], 'missing')

    def test_missing_selector(self):
        self.s['fields'][0]['selector'] = '/missing'
        self.assertEqual(self.bind()['outcome'], 'missing')

    def test_missing_acquisition_time(self):
        self.s['acquiredAtSelector'] = '/unknown'
        self.assertEqual(self.bind()['outcome'], 'missing')

    def test_stale_pin_does_not_parse_untrusted_replacement(self):
        r = self.bind(raw=b'changed')
        self.assertEqual(r['outcome'], 'stale-input')
        self.assertIsNone(r['candidate'])

    def test_wrong_declared_size(self):
        self.s['manifest']['bytes'] += 1
        self.assertEqual(self.bind()['outcome'], 'stale-input')

    def test_duplicate_json_and_nonfinite_fail_coherently_pinned(self):
        for raw in [b'{"captureAt":1,"captureAt":2}', b'{"v":NaN}', b'[1,2]', b'not json']:
            with self.subTest(raw=raw):
                self.assertEqual(self.bind(s=spec(raw), raw=raw)['outcome'], 'malformed')

    def test_unsafe_logical_input_path(self):
        for path in ['../body.pdf', '/body', 'a//b', 'a\\b']:
            self.s['manifest']['path'] = path
            self.assertEqual(self.bind()['outcome'], 'malformed')

    def test_wrong_country_type_and_source_operation(self):
        for key, value in [('country', 'AU'), ('dataType', 'gold'), ('operation', 'parse-source-body'),
                           ('sourceDataOperations', ['parse'])]:
            s = spec(); s[key] = value
            self.assertEqual(self.bind(s=s)['outcome'], 'malformed')

    def test_validation_time_does_not_reset_original_acquisition(self):
        a = self.bind(now='2026-10-20T00:00:00Z')
        b = self.bind(now='2026-11-01T00:00:00Z')
        self.assertEqual(a['outcome'], 'valid')
        self.assertEqual(b['outcome'], 'stale-input')
        self.assertEqual(b['cache']['originalAcquiredAt'], '2026-10-01T00:00:00Z')
        self.assertFalse(b['cache']['validationResetsAcquisitionAge'])
        self.assertEqual(b['cache']['minimumReuseSeconds'], 30 * 86400)

    def test_exact_thirty_day_boundary(self):
        self.assertEqual(self.bind(now='2026-10-30T23:59:59Z')['outcome'], 'valid')
        self.assertEqual(self.bind(now='2026-10-31T00:00:00Z')['outcome'], 'stale-input')

    def test_clock_invalid_or_before_original(self):
        for now in ['2026-09-01T00:00:00Z', '2026-10-18', '2026-10-18T00:00:00+11:00']:
            self.assertEqual(self.bind(now=now)['outcome'], 'malformed')

    def test_one_bad_input_does_not_poison_other_bindings(self):
        good = spec(binding='good'); missing = spec(binding='missing'); bad = spec(b'bad', 'bad')
        held = spec(binding='held'); held['holds'] = ['no-source-use']
        r = plan([good, missing, bad, held], {'good': self.raw, 'bad': b'bad', 'held': self.raw}, now=NOW)
        self.assertEqual([x['outcome'] for x in r['results']], ['valid', 'missing', 'malformed', 'held'])
        self.assertEqual(r['sourceDataRecords'], 0)

    def test_malformed_declaration_is_isolated(self):
        broken = spec(binding='broken'); broken.pop('manifest')
        r = plan([self.s, broken], {'authored-one': self.raw}, now=NOW)
        self.assertEqual([x['outcome'] for x in r['results']], ['valid', 'malformed'])

    def test_fingerprint_ignores_locality_and_validation_age(self):
        a = plan([self.s], {'authored-one': self.raw}, now=NOW)
        self.s['manifest']['localPath'] = '/different/local/path.json'
        b = plan([self.s], {'authored-one': self.raw}, now='2026-10-19T00:00:00Z')
        self.assertEqual(a['bindingFingerprint'], b['bindingFingerprint'])
        self.assertEqual(a['candidateJsonl'], b['candidateJsonl'])

    def test_noop_verifies_actual_staged_bytes_without_rewriting(self):
        r = plan([self.s], {'authored-one': self.raw}, now=NOW)
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'stage'
            self.assertEqual(write_metadata_stage(r, out), 'metadata-stage-created')
            stamp = (out / 'candidate.jsonl').stat().st_mtime_ns
            self.assertEqual(write_metadata_stage(r, out), 'verified-metadata-no-op')
            self.assertEqual((out / 'candidate.jsonl').stat().st_mtime_ns, stamp)
            (out / 'candidate.jsonl').write_bytes(b'tampered')
            with self.assertRaises(RefreshError):
                write_metadata_stage(r, out)

    def test_changed_manifest_or_partial_stage_never_adopted(self):
        r = plan([self.s], {'authored-one': self.raw}, now=NOW)
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / 'stage'; out.mkdir(); (out / 'candidate.jsonl').write_text('partial')
            with self.assertRaises(RefreshError):
                write_metadata_stage(r, out)

    def test_symlink_output_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            real = Path(t) / 'real'; real.mkdir(); link = Path(t) / 'link'; link.symlink_to(real)
            with self.assertRaises(RefreshError):
                write_metadata_stage(plan([self.s], {'authored-one': self.raw}, now=NOW), link)

    def test_shared_serialization_singleton_envelope(self):
        r = plan([self.s], {'authored-one': self.raw}, now=NOW)
        packet = json.loads(r['candidateJsonl'])
        self.assertEqual(len(packet), 1)
        self.assertEqual(packet[0]['kind'], 'sourceInputBinding')
        self.assertEqual(sha(r['candidateJsonl'].encode()), r['candidateSha256'])

    def test_real_configuration_has_no_positive_data_grants(self):
        config = json.loads((Path(__file__).parents[1] / 'config/refresh/portfolio-w07.json').read_text())
        self.assertEqual(set(config['requiredCountries']), {'AQ', 'AR', 'AS', 'AT'})
        self.assertEqual(len(config['requiredDataTypes']), 6)
        self.assertTrue(all(s['sourceDataOperations'] == [] and s['holds'] for s in config['bindings']))

    def test_cli_rejects_force(self):
        with self.assertRaises(SystemExit):
            main(['--config', 'unused', '--now', NOW, '--force'])

    def test_cli_replay_overlap_and_bad_declaration_isolation(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); metadata = root / 'metadata.json'; metadata.write_bytes(self.raw)
            self.s['manifest']['localPath'] = str(metadata)
            broken = spec(binding='broken'); broken.pop('manifest')
            config = root / 'config.json'
            config.write_bytes(canonical({'schemaVersion': 'offmenu-w07-bindings/1', 'bindings': [self.s, broken]}))
            args = ['--config', str(config), '--now', NOW, '--output', str(root / 'stage')]
            for action in ['metadata-stage-created', 'verified-metadata-no-op']:
                stream = io.StringIO()
                with contextlib.redirect_stdout(stream):
                    self.assertEqual(main(args), 2)
                result = json.loads(stream.getvalue())
                self.assertEqual(result['stageAction'], action)
                self.assertEqual([r['outcome'] for r in result['results']], ['valid', 'malformed'])
                self.assertEqual(result['metadataRecords'], 1)
            stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                self.assertEqual(main(['--config', str(config), '--now', NOW, '--output', str(root)]), 2)
            self.assertEqual(json.loads(stream.getvalue())['diagnostics'], ['w07-cli-input-or-stage-invalid'])

    def test_authored_fixture_shared_qualification_and_hold(self):
        from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify
        r = self.bind(); row = r['candidate']
        # Fully constrained authored fixture schema, not a real-source contract factory.
        schemas = {'sourceInputBinding': {'const': row}}
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); bundle = root / 'bundle'; (bundle / 'metadata').mkdir(parents=True)
            (bundle / 'metadata/authored.json').write_bytes(self.raw)
            rights = b'Authored test fixture only; retain parse transform. No real-source grant.'
            scope = canonical({'ids': [row['id']], 'records': 1, 'scope': 'authored-fixture-only'})
            (bundle / 'rights.txt').write_bytes(rights); (bundle / 'scope.json').write_bytes(scope)
            assets = tuple(Asset(name, len(raw), sha(raw)) for name, raw in
                           [('metadata/authored.json', self.raw), ('rights.txt', rights), ('scope.json', scope)])
            candidate = root / 'candidate.jsonl'
            content = plan([self.s], {'authored-one': self.raw}, now=NOW)['candidateJsonl'].encode()
            candidate.write_bytes(content)
            contract = SourceContract(source_id='authored-w07', release_id='fixture-1',
                scope_id='w07-authored-fixture', acquired_at='2026-10-01T00:00:00Z', inputs=assets,
                expected_records=1, expected_ids_sha256=ids_digest([row['id']]), schemas=schemas,
                schemas_sha256=fingerprint(schemas), policy_sha256=r['policySha256'],
                semantic_validator=lambda item: field_origin_errors(item,
                    {'metadata/authored.json': sha(self.raw)}, policy_pins=(r['policySha256'],)),
                rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                'candidateBytes': len(content), 'candidateSha256': sha(content),
                'rightsEvidenceSha256': sha(rights), 'scopeEvidenceSha256': sha(scope),
                'inputFiles': [vars(a) for a in assets]}
            qualified = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(qualified['qualified'], qualified['errors'])
            held = qualify(replace(contract, holds=('authored-hold',)), bundle, candidate, manifest)
            self.assertFalse(held['qualified']); self.assertIn('source-held', held['errors'])


class Review03Regressions(unittest.TestCase):
    def setUp(self):
        self.raw = FIXTURE.read_bytes()
        self.s = spec()
    def cli(self, config, output=None):
        cmd = [sys.executable, '-m', 'offmenu.refresh.portfolio_w07',
               '--config', str(config), '--now', NOW]
        if output is not None:
            cmd += ['--output', str(output)]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                             env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(run.returncode, 2, run.stderr)
        self.assertNotIn('Traceback', run.stderr)
        return json.loads(run.stdout)

    def config_at(self, root, bindings=None):
        metadata = root / 'metadata.json'; metadata.write_bytes(self.raw)
        self.s['manifest']['localPath'] = str(metadata)
        config = root / 'config.json'
        config.write_bytes(canonical({'schemaVersion': 'offmenu-w07-bindings/1',
                                      'bindings': bindings if bindings is not None else [self.s]}))
        return config

    def test_review03_deep_bad_preserves_peer_and_cli(self):
        broken = spec(binding='deep-bad'); nested = {}
        for _ in range(600):
            nested = {'nested': nested}
        broken['unknown'] = nested
        result = plan([self.s, broken], {'authored-one': self.raw, 'deep-bad': self.raw}, now=NOW)
        self.assertEqual([r['outcome'] for r in result['results']], ['valid', 'malformed'])
        self.assertEqual(result['metadataRecords'], 1)
        self.assertEqual(result['candidateJsonl'], plan([self.s], {'authored-one': self.raw}, now=NOW)['candidateJsonl'])
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); config = self.config_at(root, [self.s, broken])
            actual = self.cli(config)
            self.assertEqual([r['outcome'] for r in actual['results']], ['valid', 'malformed'])
            self.assertEqual(actual['metadataRecords'], 1)

    def test_review03_fifo_config_and_device_return_typed_error(self):
        with tempfile.TemporaryDirectory() as t:
            config = Path(t) / 'config.json'; os.mkfifo(config)
            for path in (config, Path('/dev/null'), Path(t)):
                with self.subTest(path=path):
                    result = self.cli(path)
                    self.assertEqual(result['outcome'], 'malformed')
                    self.assertEqual(result['diagnostics'], ['w07-cli-input-or-stage-invalid'])

    def test_review03_fifo_stage_manifest_never_blocks_or_rewrites(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); config = self.config_at(root); stage = root / 'stage'
            write_metadata_stage(plan([self.s], {'authored-one': self.raw}, now=NOW), stage)
            candidate = (stage / 'candidate.jsonl').read_bytes()
            manifest = stage / 'manifest.json'; manifest.unlink(); os.mkfifo(manifest)
            result = self.cli(config, stage)
            self.assertEqual(result['diagnostics'], ['w07-cli-input-or-stage-invalid'])
            self.assertEqual((stage / 'candidate.jsonl').read_bytes(), candidate)
            self.assertTrue(__import__('stat').S_ISFIFO(manifest.lstat().st_mode))

    def test_review03_regular_to_fifo_open_race_rejected(self):
        from offmenu.refresh.portfolio_w07 import read_metadata
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'config.json'; path.write_bytes(b'{}')
            original = os.open
            def swapped(name, flags, *args, **kwargs):
                if name == path.name:
                    path.unlink(); os.mkfifo(path)
                return original(name, flags, *args, **kwargs)
            with mock.patch('offmenu.refresh.portfolio_w07.os.open', side_effect=swapped):
                with self.assertRaises(RefreshError):
                    read_metadata(path)

    def test_review03_bounded_regular_read_and_mutation(self):
        from offmenu.refresh.portfolio_w07 import read_metadata
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'input.json'; path.write_bytes(self.raw)
            self.assertEqual(read_metadata(path), self.raw)
            with self.assertRaises(RefreshError):
                read_metadata(path, limit=2)
            original = os.read
            def changed(fd, size):
                raw = original(fd, size)
                with path.open('ab') as f:
                    f.write(b' ')
                return raw
            with mock.patch('offmenu.refresh.portfolio_w07.os.read', side_effect=changed):
                with self.assertRaises(RefreshError):
                    read_metadata(path)


if __name__ == '__main__':
    unittest.main()
