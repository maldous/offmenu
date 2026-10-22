"""Authored metadata fixtures only; no retained original or publisher access."""
from copy import deepcopy
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio_58 import CONFIG, assess, run, pointer
from offmenu.refresh import portfolio_58

NOW = '2026-10-18T06:00:00Z'


def fixture():
    raw = canonical({'metric': 'authored index', 'value': 0, 'basis': None})
    return {'sourceId': 'authored-58', 'releaseId': 'fixture-1', 'country': 'NC',
        'metadata': {'path': 'unused.json', 'sha256': sha(raw)},
        'original': {'sha256': '1' * 64, 'bytes': 12},
        'originalAcquiredAt': '2026-10-14T00:00:00Z',
        'validationObservedAt': '2026-10-17T00:00:00Z',
        'selectors': {'metric': '/metric', 'value': '/value', 'basis': '/basis'},
        'declarations': {'unknownUnit': None, 'rawFidelity': False},
        'evidencePins': [{'path': 'fixture-rights.json', 'sha256': '2' * 64}],
        'scope': 'authored-metadata-fixture', 'holds': []}, raw


def reuse(request):
    # Interface fixture: no source/cache behavior is implemented by this stub.
    return {'decision': 'reuse-retained-metadata', 'minimumReuseDays': 30,
            'networkRequests': 0}


class Portfolio58Tests(unittest.TestCase):
    def test_portfolio_config_does_not_enable_any_real_source_or_drop_required_types(self):
        config = json.loads(CONFIG.read_text())
        self.assertEqual(len(config['bindings']), 9)
        self.assertEqual(len(config['countryTypeApplicability']), 24)
        self.assertEqual({c['country'] for c in config['countryTypeApplicability']}, {'RU', 'NC', 'NF', 'PG'})
        self.assertTrue(all(c['status'] == 'unaccepted' for c in config['countryTypeApplicability']))
        for binding in config['bindings']:
            self.assertTrue(binding['holds'])
            self.assertEqual(binding['scope'], 'retained-inspection-metadata-only')
            self.assertTrue(binding['metadata']['path'].endswith('.json'))
            self.assertIsNone(binding['validationObservedAt'])
            self.assertIn('acquisitionTimeOrigin', binding)

    def test_valid_preserves_zero_null_and_checks_every_field_origin(self):
        binding, raw = fixture()
        result = assess(binding, raw, now=NOW, cache_planner=reuse)
        self.assertEqual(result['status'], 'ready-metadata')
        self.assertEqual(result['diagnostics'], [])
        row = result['metadataRow']
        self.assertEqual(row['data']['value'], 0)
        self.assertIsNone(row['data']['basis'])
        self.assertIsNone(row['data']['unknownUnit'])
        self.assertEqual(row['provenance']['fieldOrigins']['/data/value']['sourceField'], '/value')
        self.assertFalse(result['datasetAccepted'])

    def test_absent_metadata_is_not_a_zero_record_release(self):
        binding, _ = fixture()
        result = assess(binding, None, now=NOW)
        self.assertEqual(result['status'], 'missing')
        self.assertIsNone(result['metadataRow'])

    def test_explicit_hold_prevents_even_injected_planner_invocation(self):
        binding, raw = fixture()
        binding['holds'] = ['source-denied-no-retry']
        planner = Mock(side_effect=AssertionError('must not call'))
        result = assess(binding, raw, now=NOW, cache_planner=planner)
        planner.assert_not_called()
        self.assertEqual(result['status'], 'held')
        self.assertIn('source-denied-no-retry', result['diagnostics'])
        self.assertFalse(result['datasetAccepted'])

    def test_stale_planner_outcome_cannot_download_or_claim_ready(self):
        binding, raw = fixture()
        planner = lambda request: {'decision': 'review-required-no-download',
                                  'minimumReuseDays': 30, 'networkRequests': 0}
        result = assess(binding, raw, now=NOW, cache_planner=planner)
        self.assertEqual(result['status'], 'stale')
        self.assertIn('stale-input-review-required', result['diagnostics'])

    def test_original_age_and_validation_clock_are_distinct(self):
        binding, raw = fixture()
        binding['originalAcquiredAt'] = '2026-08-01T00:00:00Z'
        binding['validationObservedAt'] = NOW
        planner = Mock(side_effect=reuse)
        assess(binding, raw, now=NOW, cache_planner=planner)
        request = planner.call_args.args[0]
        self.assertEqual(request['originalAcquiredAt'], '2026-08-01T00:00:00Z')
        self.assertEqual(request['validationObservedAt'], NOW)
        self.assertFalse(request['networkAllowed'])
        self.assertEqual(request['minimumReuseDays'], 30)

    def test_validation_only_update_preserves_transform_noop_key(self):
        binding, raw = fixture()
        first = assess(binding, raw, now=NOW, cache_planner=reuse)
        binding['validationObservedAt'] = NOW
        second = assess(binding, raw, now=NOW, previous_key=first['replayKey'], cache_planner=reuse)
        self.assertEqual(second['status'], 'noop')
        self.assertEqual(first['replayKey'], second['replayKey'])
        self.assertNotEqual(first['metadataRow'], second['metadataRow'])  # Updated origin policy sidecar.

    def test_content_and_evidence_changes_invalidate_noop(self):
        binding, raw = fixture()
        first = assess(binding, raw, now=NOW, cache_planner=reuse)
        changed = canonical({'metric': 'authored index', 'value': 1, 'basis': None})
        binding['metadata']['sha256'] = sha(changed)
        second = assess(binding, changed, now=NOW, previous_key=first['replayKey'], cache_planner=reuse)
        self.assertNotEqual(first['replayKey'], second['replayKey'])
        binding['evidencePins'][0]['sha256'] = '3' * 64
        third = assess(binding, changed, now=NOW, cache_planner=reuse)
        self.assertNotEqual(second['replayKey'], third['replayKey'])

    def test_unbound_shared_planner_is_typed_dependency(self):
        binding, raw = fixture()
        result = assess(binding, raw, now=NOW)
        self.assertEqual(result['status'], 'blocked')
        self.assertIn('shared-pure-cache-planner-not-bound', result['diagnostics'])

    def test_malformed_json_and_duplicate_keys_are_isolated(self):
        for raw in (b'{', b'{"value":0,"value":1}', b'{"value":NaN}'):
            with self.subTest(raw=raw):
                binding, _ = fixture()
                binding['metadata']['sha256'] = sha(raw)
                result = assess(binding, raw, now=NOW)
                self.assertEqual(result['status'], 'malformed')
                self.assertIsNone(result['metadataRow'])

    def test_tampered_metadata_does_not_repin_itself(self):
        binding, raw = fixture()
        result = assess(binding, raw + b' ', now=NOW)
        self.assertEqual(result['diagnostics'], ['metadata-pin-mismatch'])

    def test_missing_selector_cannot_be_imputed_to_null(self):
        binding, raw = fixture()
        binding['selectors']['missing'] = '/absent'
        self.assertEqual(assess(binding, raw, now=NOW)['status'], 'malformed')

    def test_clock_future_naive_and_validation_before_acquisition_fail(self):
        for stamp in ['2026-11-01T00:00:00Z', '2026-10-18T00:00:00', 'invalid']:
            binding, raw = fixture()
            binding['originalAcquiredAt'] = stamp
            self.assertEqual(assess(binding, raw, now=NOW)['status'], 'malformed')
        binding, raw = fixture()
        binding['validationObservedAt'] = '2020-01-01T00:00:00Z'
        self.assertEqual(assess(binding, raw, now=NOW)['status'], 'malformed')

    def test_planner_cannot_relax_ttl_or_allow_network(self):
        for plan in [{'decision': 'download', 'minimumReuseDays': 30, 'networkRequests': 0},
                     {'decision': 'reuse-retained-metadata', 'minimumReuseDays': 29, 'networkRequests': 0},
                     {'decision': 'reuse-retained-metadata', 'minimumReuseDays': 30, 'networkRequests': 1}]:
            binding, raw = fixture()
            self.assertEqual(assess(binding, raw, now=NOW, cache_planner=lambda request: plan)['status'], 'malformed')

    def test_planner_failure_is_one_input_diagnostic(self):
        binding, raw = fixture()
        result = assess(binding, raw, now=NOW, cache_planner=Mock(side_effect=RuntimeError('private detail')))
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['diagnostics'], ['cache-planner-failed'])

    def test_batch_isolation_and_only_allowlisted_metadata_files_are_opened(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, raw = fixture()
            metadata = Path(directory) / 'metadata.json'
            metadata.write_bytes(raw)
            binding['metadata']['path'] = str(metadata)
            missing = deepcopy(binding)
            missing.update(sourceId='missing-authored')
            missing['metadata']['path'] = str(Path(directory) / 'absent.json')
            report = run({'bindings': [missing, binding], 'countryTypeApplicability': []},
                         now=NOW, cache_planner=reuse)
            self.assertEqual([r['status'] for r in report['sources']], ['missing', 'ready-metadata'])
            self.assertEqual(report['originalReads'], 0)
            self.assertEqual(report['networkRequests'], 0)

    def test_metadata_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            binding, raw = fixture()
            metadata = Path(directory) / 'real.json'
            metadata.write_bytes(raw)
            link = Path(directory) / 'alias.json'
            link.symlink_to(metadata)
            binding['metadata']['path'] = str(link)
            report = run({'bindings': [binding], 'countryTypeApplicability': []}, now=NOW)
            self.assertEqual(report['sources'][0]['diagnostics'], ['metadata-file-unavailable-or-unsafe'])

    def test_json_pointer_escapes_and_bad_array_alias(self):
        self.assertEqual(pointer({'a/b': {'~': 0}}, '/a~1b/~0'), 0)
        with self.assertRaises(ValueError):
            pointer([1], '/00')
        with self.assertRaises(ValueError):
            pointer({}, '/bad~2')


class PreviousReportIngressTests(unittest.TestCase):
    """Focused W58-F1 regressions; never invoke real portfolio metadata reads."""

    def reject_cli(self, path, code):
        with patch.object(portfolio_58, 'run', side_effect=AssertionError('real metadata visited')), \
                contextlib.redirect_stderr(io.StringIO()) as errors:
            with self.assertRaises(SystemExit) as exit_status:
                portfolio_58.main(['--now', NOW, '--previous', str(path)])
            self.assertEqual(exit_status.exception.code, 2)
            self.assertIn(code, errors.getvalue())

    def test_fifo_without_writer_exits_normally_without_kill(self):
        with tempfile.TemporaryDirectory() as directory:
            fifo = Path(directory) / 'previous.fifo'
            os.mkfifo(fifo)
            code = '''
import sys
from unittest.mock import patch
from offmenu.refresh import portfolio_58 as m
with patch.object(m, 'run', side_effect=AssertionError('real metadata visited')):
    raise SystemExit(m.main(['--now', sys.argv[2], '--previous', sys.argv[1]]))
'''
            child = subprocess.Popen([sys.executable, '-B', '-c', code, str(fifo), NOW],
                cwd=Path(__file__).resolve().parents[1], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                output, errors = child.communicate(timeout=2)
            except subprocess.TimeoutExpired:
                child.kill()
                child.communicate(timeout=2)
                self.fail('FIFO CLI blocked; child killed and reaped')
            self.assertEqual(child.returncode, 2)
            self.assertEqual(output, b'')
            self.assertIn(b'previous-report-not-regular', errors)

    def test_regular_previous_report_preserves_replay_key_and_cli_result(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = Path(directory) / 'previous.json'
            previous.write_bytes(canonical({'sources': [{'sourceId': 'authored-58', 'replayKey': '3' * 64}]}))
            config = Path(directory) / 'config.json'
            config.write_bytes(canonical({'bindings': [], 'countryTypeApplicability': []}))
            report = {'sources': [], 'scope': 'authored-positive'}
            with patch.object(portfolio_58, 'CONFIG', config), \
                    patch.object(portfolio_58, 'run', return_value=report) as runner, \
                    contextlib.redirect_stdout(io.StringIO()) as output:
                status = portfolio_58.main(['--now', NOW, '--previous', str(previous)])
            self.assertEqual(status, 0)
            self.assertEqual(runner.call_args.kwargs['previous_keys'], {'authored-58': '3' * 64})
            self.assertEqual(output.getvalue().encode(), canonical(report))

    def test_directory_symlink_and_missing_previous_are_bounded_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'previous.json'
            real.write_bytes(canonical({'sources': []}))
            link = Path(directory) / 'alias.json'
            link.symlink_to(real)
            self.reject_cli(directory, 'previous-report-not-regular')
            self.reject_cli(link, 'previous-report-invalid-or-unavailable')
            self.reject_cli(Path(directory) / 'absent', 'previous-report-invalid-or-unavailable')

    def test_nonregular_opened_descriptor_rejected_before_read(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'previous.json'
            real.write_bytes(canonical({'sources': []}))
            opened = Mock(st_mode=0o020000, st_size=0)  # Authored character-device descriptor metadata.
            with patch.object(portfolio_58.os, 'fstat', return_value=opened), \
                    patch.object(portfolio_58.os, 'read', side_effect=AssertionError('device read')):
                self.reject_cli(real, 'previous-report-not-regular')

    def test_actual_opened_fifo_after_path_check_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'previous.json'
            real.write_bytes(canonical({'sources': []}))
            open_original = os.open
            def replaced(path, flags):
                real.unlink()
                os.mkfifo(real)
                return open_original(path, flags)
            with patch.object(portfolio_58.os, 'open', side_effect=replaced):
                self.reject_cli(real, 'previous-report-not-regular')

    def test_size_limit_checked_on_descriptor_and_during_read(self):
        with tempfile.TemporaryDirectory() as directory:
            real = Path(directory) / 'previous.json'
            real.write_bytes(b' ' * (portfolio_58.MAX_PREVIOUS + 1))
            self.reject_cli(real, 'previous-report-too-large')
            real.write_bytes(canonical({'sources': []}))
            opened = Mock(st_mode=0o100600, st_size=0)
            chunks = [b' ' * 65536] * 16 + [b' ']
            with patch.object(portfolio_58.os, 'fstat', return_value=opened), \
                    patch.object(portfolio_58.os, 'read', side_effect=chunks) as reader:
                self.reject_cli(real, 'previous-report-too-large')
            self.assertEqual(sum(call.args[1] for call in reader.call_args_list), portfolio_58.MAX_PREVIOUS + 1)


if __name__ == '__main__':
    unittest.main()
