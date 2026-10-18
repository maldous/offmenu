"""Authored metadata fixtures only; no retained bodies, network or source grants."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu import portfolio_worker09 as binding
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors


class PortfolioBindings(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'inputs'
        self.root.mkdir()
        self.output = Path(self.temp.name) / 'output'
        self.acquired = '2026-10-01T00:00:00Z'
        self.now = '2026-10-02T00:00:00Z'
        self.row = {'id': 'BH:fixture:anchor-1', 'country': 'BH',
                    'sourceURL': 'https://publisher.invalid/recipes/',
                    'targetURL': 'https://publisher.invalid/book/', 'literalHref': '/book/',
                    'sourceLocator': {'htmlAnchorOrdinal': 1}, 'role': 'cookbook-catalogue-link',
                    'targetFetched': False, 'recipeBodyEstablished': False,
                    'certificateValidityEstablished': False}
        value = {'country': 'BH', 'source': {'sha256': 'a' * 64},
                 'recordCount': 1, 'records': [self.row]}
        self.entry = {'id': 'bh-fixture', 'country': 'BH', 'domain': 'recipes',
                      'sourceId': 'authored-bh', 'releaseId': 'fixture/1',
                      'state': 'metadata', 'profile': 'bfm-catalogue',
                      'sourceURL': self.row['sourceURL'], 'publisherBodySha256': 'a' * 64,
                      'expectedRecords': 1, 'nativeUnit': None, 'nativeBasis': None,
                      'retentionDays': 30, 'useScope': 'Authored synthetic metadata only.',
                      'originalAcquiredAt': self.acquired,
                      'input': self.write('candidate.json', canonical(value)),
                      'acquisitionEvidence': self.write('receipt.json', canonical({'utc': self.acquired}))}

    def write(self, name, raw):
        (self.root / name).write_bytes(raw)
        return {'path': name, 'bytes': len(raw), 'sha256': sha(raw)}

    def config(self, entries=None):
        return {'schemaVersion': 'offmenu-worker09-metadata-bindings/1',
                'countries': ['BH', 'KI', 'RE'], 'requiredDomains': ['recipes'],
                'bindings': entries if entries is not None else [self.entry]}

    def run_binding(self, now=None, validated=None):
        report = binding.build(self.config(), self.root, now=now or self.now,
                               validated_at=validated or now or self.now)
        return report, report['results'][0]

    def test_packaged_configuration_is_exact_and_defensive(self):
        config = binding.configuration()
        self.assertEqual(sha(canonical(config)),
                         '4950407bc0b0dd2b311bbfcef71cc0802204cfeb19ab51ff4fb231f0abd17e1b')
        config['bindings'][0]['state'] = 'changed-by-caller'
        self.assertEqual(binding.configuration()['bindings'][0]['state'], 'metadata')

    def test_reader_uses_one_nonblocking_verified_descriptor(self):
        original = os.open
        flags = []
        def observed(path, mode, *args, **kwargs):
            flags.append(mode)
            return original(path, mode, *args, **kwargs)
        with patch.object(binding.os, 'open', side_effect=observed):
            _, result = self.run_binding()
        self.assertEqual(result['status'], 'metadata-candidate')
        self.assertTrue(flags)
        self.assertTrue(all(f & os.O_NOFOLLOW and f & os.O_NONBLOCK for f in flags))

    def test_reader_rejects_replacement_between_lstat_and_open(self):
        target = self.root / 'candidate.json'
        raw = target.read_bytes()
        original = os.open
        for special, expected in [(True, 'metadata-input-not-regular'),
                                  (False, 'metadata-input-changed')]:
            with self.subTest(special=special):
                fired = []
                def replace_then_open(path, flags, *args, **kwargs):
                    if Path(path) == target and not fired:
                        fired.append(True)
                        replacement = self.root / 'replacement.json'
                        if special:
                            os.mkfifo(replacement)
                        else:
                            replacement.write_bytes(raw)
                        os.replace(replacement, target)
                    return original(path, flags, *args, **kwargs)
                with patch.object(binding.os, 'open', side_effect=replace_then_open):
                    _, result = self.run_binding()
                self.assertEqual(result['diagnostics'], [expected])
                self.assertTrue(fired)
                target.unlink()
                target.write_bytes(raw)

    def test_nonregular_and_oversize_pins_return_fixed_diagnostics(self):
        (self.root / 'directory.json').mkdir()
        self.entry['input']['path'] = 'directory.json'
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-input-not-regular'])
        self.entry['input']['path'] = 'large.json'
        (self.root / 'large.json').write_bytes(b'x' * (binding.MAX_METADATA + 1))
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-input-too-large'])

    def test_fifo_input_cli_returns_isolated_diagnostics_and_valid_sibling(self):
        good = deepcopy(self.entry)
        good.update(id='valid-sibling', input=self.write('sibling.json',
                    (self.root / 'candidate.json').read_bytes()))
        (self.root / 'candidate.json').unlink()
        os.mkfifo(self.root / 'candidate.json')
        script = """import json,sys
from offmenu import portfolio_worker09 as b
c=json.loads(sys.stdin.read())
b.configuration=lambda:c
raise SystemExit(b.main(['--metadata-root',sys.argv[1],'--output',sys.argv[2],
                        '--now','2026-10-02T00:00:00Z']))
"""
        r = subprocess.run([sys.executable, '-B', '-c', script,
                            str(self.root), str(self.output)],
                           input=json.dumps(self.config([self.entry, good])),
                           capture_output=True, text=True, timeout=2)
        self.assertEqual(r.returncode, 2, r.stderr)
        report = json.loads((self.output / 'report.json').read_text())
        self.assertEqual([r['status'] for r in report['results']],
                         ['malformed-input', 'metadata-candidate'])
        self.assertEqual(report['results'][0]['diagnostics'], ['metadata-input-not-regular'])

    def test_valid_metadata_has_exact_field_origins_and_unknown_units(self):
        report, result = self.run_binding()
        self.assertEqual(result['status'], 'metadata-candidate')
        record = json.loads(result['candidateBytes'])[0]
        self.assertEqual(record['data']['sourceRecord'], self.row)
        self.assertIsNone(record['data']['nativeUnit'])
        self.assertIsNone(record['data']['nativeBasis'])
        self.assertEqual(field_origin_errors(record,
                         {'candidate.json': self.entry['input']['sha256']},
                         policy_pins=[report['policySha256']]), [])
        origin = record['provenance']['fieldOrigins']['/data/sourceRecord/targetURL']
        self.assertEqual(origin['sourceField'], '/records/0/targetURL')
        self.assertFalse(report['goldAdmitted'])
        self.assertEqual(result['cache']['sharedPlanner'], 'not-available-at-abec')

    def test_missing_input_is_not_zero_records_success(self):
        (self.root / 'candidate.json').unlink()
        _, result = self.run_binding()
        self.assertEqual(result['status'], 'missing-input')
        self.assertNotIn('candidateBytes', result)

    def test_held_input_performs_no_read_even_if_path_would_be_invalid(self):
        self.entry.update(state='held', blocker='http403-no-retry',
                          input={'path': '/never/open.pdf'})
        with patch.object(Path, 'open', side_effect=AssertionError('held input opened')):
            _, result = self.run_binding()
        self.assertEqual(result['status'], 'held-input')
        self.assertEqual(result['diagnostics'], ['http403-no-retry'])

    def test_malformed_and_duplicate_key_json_are_isolated(self):
        for raw in [b'{invalid', b'{"x":1,"x":2}', b'{"x":NaN}']:
            with self.subTest(raw=raw):
                self.entry['input'] = self.write('candidate.json', raw)
                _, result = self.run_binding()
                self.assertEqual(result['diagnostics'], ['metadata-json-malformed'])

    def test_pin_drift_fails_without_parsing_changed_value(self):
        (self.root / 'candidate.json').write_text('{}')
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-input-pin-mismatch'])

    def test_literal_link_mismatch_is_not_hidden_by_a_valid_absolute_url(self):
        self.row['literalHref'] = '/different-book/'
        self.entry['input'] = self.write('candidate.json', canonical({
            'country': 'BH', 'source': {'sha256': 'a' * 64},
            'recordCount': 1, 'records': [self.row]}))
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-link-resolution-mismatch'])
        self.assertEqual(result['metadataRecords'], 0)

    def test_body_path_and_symlink_are_rejected(self):
        self.entry['input']['path'] = 'source.pdf'
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-json-only'])
        self.entry['input']['path'] = '../candidate.json'
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-input-path-invalid'])
        self.entry['input']['path'] = 'link.json'
        (self.root / 'link.json').symlink_to(self.root / 'candidate.json')
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['symlink-path-rejected'])

    def test_stale_acquisition_is_not_refreshed_by_validation_age(self):
        _, result = self.run_binding('2026-11-01T00:00:00Z')
        self.assertEqual(result['status'], 'stale-input')
        self.assertEqual(result['cache']['validationAgeSeconds'], 0)
        self.assertEqual(result['cache']['acquisitionAgeSeconds'], 31 * 86400)
        self.assertEqual(result['cache']['decision'], 'conditional-review-required-no-download')
        self.assertNotIn('candidateBytes', result)

    def test_thirty_day_boundary_and_zero_network(self):
        with patch('socket.socket.connect', side_effect=AssertionError('network attempted')):
            _, under = self.run_binding('2026-10-30T23:59:59Z')
            _, at = self.run_binding('2026-10-31T00:00:00Z')
        self.assertEqual(under['status'], 'metadata-candidate')
        self.assertEqual(at['status'], 'stale-input')
        self.assertEqual(under['networkRequests'], 0)

    def test_validation_time_changes_neither_candidate_nor_build_key(self):
        _, one = self.run_binding('2026-10-15T00:00:00Z', self.acquired)
        _, two = self.run_binding('2026-10-15T00:00:00Z')
        self.assertEqual(one['candidateBytes'], two['candidateBytes'])
        self.assertEqual(one['buildKey'], two['buildKey'])
        self.assertNotEqual(one['cache']['validationAgeSeconds'], two['cache']['validationAgeSeconds'])

    def test_acquisition_mismatch_and_future_clock_are_not_silently_repaired(self):
        self.entry['acquisitionEvidence'] = self.write('receipt.json', canonical({'utc': self.now}))
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-acquisition-evidence-mismatch'])
        _, result = self.run_binding('2026-09-30T00:00:00Z')
        self.assertEqual(result['diagnostics'], ['metadata-clock-order-invalid'])

    def test_unknown_retention_does_not_claim_thirty_day_entitlement(self):
        self.entry['retentionDays'] = None
        _, result = self.run_binding()
        self.assertEqual(result['status'], 'metadata-candidate')
        self.assertFalse(result['cache']['retentionQualified'])
        self.assertIn('source-retention-duration-unqualified', result['diagnostics'])

    def test_metadata_never_upgrades_to_recipe_or_quantity(self):
        self.row['recipeBodyEstablished'] = True
        self.entry['input'] = self.write('candidate.json', canonical({
            'country': 'BH', 'source': {'sha256': 'a' * 64},
            'recordCount': 1, 'records': [self.row]}))
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-catalogue-scope-invalid'])
        self.entry['nativeUnit'] = 'g'
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-quantity-inference-rejected'])

    def test_bad_profile_does_not_hide_independent_valid_binding(self):
        bad = deepcopy(self.entry)
        bad.update(id='unsupported', profile='other-country-engine')
        report = binding.build(self.config([bad, self.entry]), self.root,
                               now=self.now, validated_at=self.now)
        self.assertEqual([x['status'] for x in report['results']],
                         ['malformed-input', 'metadata-candidate'])

    def test_replay_is_no_op_and_held_report_does_not_activate_old_artifact(self):
        report, _ = self.run_binding()
        binding.publish_report(report, self.output)
        artifact = self.output / report['results'][0]['artifact']
        before = (artifact.stat().st_mtime_ns, artifact.read_bytes())
        report, _ = self.run_binding()
        binding.publish_report(report, self.output)
        self.assertEqual(report['results'][0]['writeAction'], 'no-op')
        self.assertEqual((artifact.stat().st_mtime_ns, artifact.read_bytes()), before)
        self.entry.update(state='held', blocker='source-use-unknown')
        report, _ = self.run_binding()
        binding.publish_report(report, self.output)
        self.assertNotIn('artifact', report['results'][0])
        self.assertTrue(artifact.exists())

    def test_ki_receipt_stages_metadata_not_cpi_values(self):
        raw = {k: None for k in binding.KI_FIELDS}
        raw.update(country='KI', id='authored-report', canonical_url='https://nso.invalid/cpi',
                   version='September2025', http_status=200, dataset_acquired=True,
                   utc=self.acquired, acquisition_rights='fixture only')
        self.entry.update(id='ki-fixture', country='KI', profile='ki-cpi-receipt',
                          sourceURL=raw['canonical_url'],
                          input=self.write('ki.json', canonical(raw)))
        _, result = self.run_binding()
        record = json.loads(result['candidateBytes'])[0]
        self.assertEqual(record['countries'], ['KI'])
        self.assertNotIn('price', record['data']['sourceRecord'])
        self.assertEqual(record['provenance']['fieldOrigins']['/data/sourceRecord/bytes']['sourceField'], '/bytes')

    def test_cli_emits_all_diagnostics_and_uses_only_authored_json(self):
        bad = deepcopy(self.entry)
        bad.update(id='missing-fixture', input={**bad['input'], 'path': 'missing.json'})
        config = Path(self.temp.name) / 'config.json'
        config.write_bytes(canonical(self.config([self.entry, bad])))
        with patch.object(binding, 'configuration', side_effect=lambda: json.loads(config.read_bytes())), redirect_stdout(io.StringIO()):
            status = binding.main(['--metadata-root', str(self.root), '--output', str(self.output),
                                   '--now', self.now])
        self.assertEqual(status, 2)
        report = json.loads((self.output / 'report.json').read_text())
        self.assertEqual([r['status'] for r in report['results']],
                         ['metadata-candidate', 'missing-input'])

    def test_real_portfolio_configuration_retains_all_six_category_gaps(self):
        config = binding.configuration()
        self.assertEqual(config['countries'], ['BH', 'KI', 'RE'])
        self.assertEqual(len(config['requiredDomains']), 6)
        self.assertFalse(config['sourceOperationsAuthorized'])
        self.assertEqual([r['state'] for r in config['bindings']].count('held'), 3)
        self.assertTrue(all(r['nativeUnit'] is None and r['nativeBasis'] is None
                            for r in config['bindings']))

    def test_bad_output_and_global_config_fail_with_typed_cli_diagnostics(self):
        config = Path(self.temp.name) / 'bad-config.json'
        config.write_text('{invalid')
        error = io.StringIO()
        with patch.object(binding, 'configuration', side_effect=lambda: json.loads(config.read_bytes())), redirect_stdout(io.StringIO()), patch('sys.stderr', error):
            status = binding.main(['--metadata-root', str(self.root), '--output', str(self.output),
                                   '--now', self.now])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(error.getvalue())['diagnostics'], ['metadata-cli-config-malformed'])
        config.write_bytes(canonical(self.config()))
        self.output.write_text('occupied by an unrelated file')
        error = io.StringIO()
        with patch.object(binding, 'configuration', side_effect=lambda: json.loads(config.read_bytes())), redirect_stdout(io.StringIO()), patch('sys.stderr', error):
            status = binding.main(['--metadata-root', str(self.root), '--output', str(self.output),
                                   '--now', self.now])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(error.getvalue())['diagnostics'], ['metadata-output-not-owned'])

    def test_lineage_pin_is_explicit_and_mismatched_candidate_is_rejected(self):
        lineage = {'candidate': {'sha256': self.entry['input']['sha256']},
                   'source': {'path': 'source-not-opened.html', 'sha256': 'a' * 64},
                   'passed': 1, 'failed': 0}
        self.entry['lineageEvidence'] = self.write('lineage.json', canonical(lineage))
        _, result = self.run_binding()
        self.assertEqual(result['status'], 'metadata-candidate')
        self.assertEqual(result['upstreamOriginEvidence']['sourcePin'], lineage['source'])
        lineage['candidate']['sha256'] = 'b' * 64
        self.entry['lineageEvidence'] = self.write('lineage.json', canonical(lineage))
        _, result = self.run_binding()
        self.assertEqual(result['diagnostics'], ['metadata-lineage-evidence-mismatch'])

    def test_review_lock_hardlink_preserves_input_bytes_and_mtime(self):
        self.output.mkdir()
        source = self.root / 'candidate.json'
        before = (source.read_bytes(), source.stat().st_mtime_ns)
        lock = self.output / '.worker09.lock'
        os.link(source, lock)
        report, _ = self.run_binding()
        rejected = False
        try:
            binding.publish_report(report, self.output)
        except binding.RefreshError:
            rejected = True
        self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)
        self.assertTrue(rejected)
        self.assertFalse((self.output / 'report.json').exists())
        lock.unlink()
        for expected in ['created', 'no-op']:
            report, _ = self.run_binding()
            binding.publish_report(report, self.output)
            self.assertEqual(report['results'][0]['writeAction'], expected)

    def test_review_malformed_ids_each_preserve_valid_sibling(self):
        for malformed in [[], {}, ['x'], {'x': 1}]:
            with self.subTest(malformed=malformed):
                bad = deepcopy(self.entry)
                bad['id'] = malformed
                report = binding.build(self.config([bad, bad, self.entry]), self.root,
                                       now=self.now, validated_at=self.now)
                self.assertEqual(len(report['results']), 3)
                self.assertEqual([x['status'] for x in report['results']],
                                 ['malformed-input', 'malformed-input', 'metadata-candidate'])
                self.assertTrue(all(x['diagnostics'] == ['metadata-binding-invalid']
                                    for x in report['results'][:2]))
                self.assertEqual([x['id'] for x in report['results'][:2]], [None, None])

    def test_review_report_slot_hardlinks_and_special_lock_preserve_input(self):
        self.output.mkdir()
        source = self.root / 'candidate.json'
        before = (source.read_bytes(), source.stat().st_mtime_ns)
        for name in ['report.json', 'report.json.pending']:
            alias = self.output / name
            os.link(source, alias)
            report, _ = self.run_binding()
            with self.assertRaisesRegex(binding.RefreshError, 'metadata-output-file-unsafe'):
                binding.publish_report(report, self.output)
            self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)
            self.assertFalse((self.output / '.worker09.lock').exists())
            alias.unlink()
        os.mkfifo(self.output / '.worker09.lock')
        report, _ = self.run_binding()
        with self.assertRaisesRegex(binding.RefreshError, 'metadata-output-file-unsafe'):
            binding.publish_report(report, self.output)
        self.assertEqual((source.read_bytes(), source.stat().st_mtime_ns), before)

    def test_review_output_ownership_is_checked_before_lock_creation(self):
        self.output.mkdir()
        report, _ = self.run_binding()
        with patch.object(binding.os, 'geteuid', return_value=os.geteuid() + 1):
            with self.assertRaisesRegex(binding.RefreshError, 'metadata-output-not-owned'):
                binding.publish_report(report, self.output)
        self.assertEqual(list(self.output.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
