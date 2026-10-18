"""Authored metadata fixtures only; no retained documents or source bodies."""
import copy
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from offmenu.refresh.core import canonical, sha, RefreshError
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio41 import (assess, assess_portfolio, pointer, load_bindings,
                                         main, read_metadata, POLICY_PIN)

CLOCK = datetime(2026, 10, 18, tzinfo=timezone.utc)


def fixture():
    raw = canonical({'version': 'authored-fixture-1', 'role': 'synthetic-metadata',
                     'utc': '2026-10-14T00:00:00Z', 'value': 0, 'unit': None})
    binding = {'id': 'qa-fixture', 'country': 'QA', 'sourceId': 'qa-fixture',
       'releaseId': 'synthetic-v1', 'releaseStatus': 'authored-fixture',
       'role': 'receipt-metadata-only', 'metadataPin': {'path': '/synthetic/receipt.json',
          'bytes': len(raw), 'sha256': sha(raw)},
       'fieldSelectors': {'version': '/version', 'zero': '/value', 'unknown': '/unit'},
       'originalAcquiredAtSelector': '/utc', 'validatedAt': '2026-10-17T00:00:00Z',
       'maxValidationAgeDays': 30, 'holds': [], 'missingInputs': [],
       'countryTypes': [], 'bodyAdapter': None}
    return binding, raw


class Portfolio41Tests(unittest.TestCase):
    def test_valid_metadata_reuses_shared_origins_and_stage_diagnostics(self):
        b, raw = fixture(); r = assess(b, raw, now=CLOCK)
        self.assertEqual(r['status'], 'READY_METADATA')
        self.assertEqual(r['stageDiagnostic']['status'], 'succeeded')
        self.assertEqual(r['metadataRecord']['data']['zero'], 0)
        self.assertIsNone(r['metadataRecord']['data']['unknown'])
        self.assertEqual(field_origin_errors(r['metadataRecord'],
            {'receipt.json': sha(raw)}, policy_pins=(POLICY_PIN,)), [])
        self.assertEqual(r['bodyOperationsAllowed'], [])
        self.assertIsNone(r['acceptedDatasetRecords'])

    def test_missing_metadata_is_not_zero_or_accepted(self):
        b, _ = fixture(); r = assess(b, None, now=CLOCK)
        self.assertEqual(r['status'], 'MISSING')
        self.assertIn('metadata-input-missing', r['diagnostics'])
        self.assertIsNone(r['metadataRecord'])

    def test_source_holds_survive_valid_fresh_metadata(self):
        b, raw = fixture(); b['holds'] = ['source-use-unestablished']
        r = assess(b, raw, now=CLOCK)
        self.assertEqual(r['status'], 'HELD')
        self.assertEqual(r['stageDiagnostic']['status'], 'held')
        self.assertEqual(r['bodyOperationsAllowed'], [])

    def test_missing_field_selector_is_typed_and_never_guessed(self):
        b, raw = fixture(); b['fieldSelectors']['missing'] = '/not-here'
        r = assess(b, raw, now=CLOCK)
        self.assertEqual(r['status'], 'MALFORMED')
        self.assertIn('metadata-selector-missing', r['diagnostics'])

    def test_incomplete_use_input_returns_missing_not_ready(self):
        b, raw = fixture(); b['missingInputs'] = ['specific-use-decision']
        self.assertEqual(assess(b, raw, now=CLOCK)['status'], 'MISSING')

    def test_pin_mismatch_invalid_json_and_duplicates_are_closed(self):
        for raw in [b'{', b'{"version":1,"version":2}', b'{"version":NaN}']:
            b, _ = fixture(); b['metadataPin'].update(bytes=len(raw), sha256=sha(raw))
            self.assertEqual(assess(b, raw, now=CLOCK)['status'], 'MALFORMED')
        b, raw = fixture()
        self.assertIn('metadata-input-pin-mismatch', assess(b, raw+b' ', now=CLOCK)['diagnostics'])

    def test_stale_validation_and_old_original_age_are_independent(self):
        b, raw = fixture()
        r = assess(b, raw, now=CLOCK + timedelta(days=31))
        self.assertEqual(r['status'], 'STALE')
        self.assertEqual(r['cache']['under30DayDecision'], 'conditional-review-required-no-download')
        self.assertFalse(r['cache']['automaticNetworkAllowed'])
        # Refreshing validation does not reset original acquisition or the content key.
        before = r['buildKey']; b['validatedAt'] = '2026-11-18T00:00:00Z'
        new = assess(b, raw, now=CLOCK + timedelta(days=31))
        self.assertEqual(new['status'], 'READY_METADATA')
        self.assertEqual(new['buildKey'], before)
        self.assertEqual(new['cache']['originalAgeSeconds'], r['cache']['originalAgeSeconds'])

    def test_under30_boundary_never_permits_network_and_no_force_escape(self):
        b, raw = fixture(); r = assess(b, raw, now=CLOCK)
        self.assertEqual(r['cache']['minimumReuseSeconds'], 30*86400)
        self.assertEqual(r['cache']['under30DayDecision'], 'reuse-retained-metadata-no-download')
        self.assertFalse(r['cache']['automaticNetworkAllowed'])
        self.assertFalse(r['cache']['cacheBodyVerified'])

    def test_replay_noop_content_identity_validation_clock_excluded(self):
        b, raw = fixture(); first = assess(b, raw, now=CLOCK)
        b['validatedAt'] = '2026-10-18T00:00:00Z'
        second = assess(b, raw, now=CLOCK, previous_build_key=first['buildKey'])
        self.assertEqual(second['replay'], 'unchanged-content-no-op')
        self.assertEqual(second['buildKey'], first['buildKey'])
        changed = canonical({'version':'different','role':'synthetic','utc':'2026-10-14T00:00:00Z','value':0,'unit':None})
        b['metadataPin'].update(bytes=len(changed),sha256=sha(changed))
        self.assertNotEqual(assess(b, changed, now=CLOCK)['buildKey'], first['buildKey'])

    def test_bad_source_does_not_stop_independent_source(self):
        b, raw = fixture(); malformed = copy.deepcopy(b); del malformed['metadataPin']
        r = assess_portfolio([malformed,b], lambda _:raw, now=CLOCK)
        self.assertEqual([x['status'] for x in r['sources']], ['MALFORMED','READY_METADATA'])
        def loader(pin):
            if pin['path'].endswith('missing.json'): raise FileNotFoundError()
            return raw
        missing=copy.deepcopy(b); missing['metadataPin']['path']='/synthetic/missing.json'
        r=assess_portfolio([missing,b],loader,now=CLOCK)
        self.assertEqual([x['status'] for x in r['sources']], ['MISSING','READY_METADATA'])

    def test_loader_failures_are_isolated_fixed_codes(self):
        b, _ = fixture()
        def loader(_): raise OSError('private path must not appear')
        r=assess_portfolio([b],loader,now=CLOCK)
        self.assertEqual(r['sources'][0]['diagnostics'],['metadata-read-failed'])
        self.assertNotIn('private path',str(r))

    def test_pointer_escaping_array_and_type_errors(self):
        self.assertEqual(pointer({'a/b':{'~':[0]}}, '/a~1b/~0/0'),0)
        for p in ['/a~2b','/a~1b/~0/00','/a~1b/~0/1']:
            with self.assertRaises(RefreshError):pointer({'a/b':{'~':[0]}},p)

    def test_unsupported_country_body_adapter_and_invalid_timing(self):
        for field,value in [('country','NO'),('bodyAdapter','native-reader'),('validatedAt','future'),('maxValidationAgeDays',True)]:
            b,raw=fixture();b[field]=value
            self.assertEqual(assess(b,raw,now=CLOCK)['status'],'MALFORMED')
        b,raw=fixture();self.assertEqual(assess(b,raw,now=datetime(2026,10,18))['status'],'MALFORMED')

    def test_no_mutation_and_no_path_or_body_following(self):
        b,raw=fixture();before=copy.deepcopy(b)
        with patch('builtins.open',side_effect=AssertionError('No IO')):
            r=assess(b,raw,now=CLOCK)
        self.assertEqual(b,before)
        r['metadataRecord']['data']['version']='changed'
        self.assertEqual(b,before)

    def test_real_config_remains_four_held_metadata_bindings_without_reading_it(self):
        config=load_bindings()
        self.assertEqual({b['country'] for b in config['bindings']},{'QA','TC','TW','VG'})
        for b in config['bindings']:
            self.assertTrue(b['holds']);self.assertIsNone(b['bodyAdapter']);self.assertEqual(b['countryTypes'],[])

    def test_cli_uses_only_authored_metadata_and_never_overwrites(self):
        b,raw=fixture()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'report.json'
            with patch('offmenu.refresh.portfolio41.load_bindings',return_value={'bindings':[b]}), patch('offmenu.refresh.portfolio41.read_metadata',return_value=raw):
                self.assertEqual(main(['--now','2026-10-18T00:00:00Z','--output',str(p)]),0)
                with self.assertRaises(FileExistsError):main(['--now','2026-10-18T00:00:00Z','--output',str(p)])
                self.assertEqual(p.read_bytes(),canonical(assess_portfolio([b],lambda _:raw,now=CLOCK)))

    def test_cli_previous_report_exposes_unchanged_noop(self):
        b,raw=fixture()
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'first.json'; q=Path(t)/'second.json'
            with patch('offmenu.refresh.portfolio41.load_bindings',return_value={'bindings':[b]}), patch('offmenu.refresh.portfolio41.read_metadata',side_effect=lambda pin: raw if pin['path']=='/synthetic/receipt.json' else Path(pin['path']).read_bytes()):
                main(['--now','2026-10-18T00:00:00Z','--output',str(p)])
                main(['--now','2026-10-18T00:00:00Z','--output',str(q),'--previous-report',str(p)])
            import json
            first=json.loads(p.read_bytes())['sources'][0];second=json.loads(q.read_bytes())['sources'][0]
            self.assertEqual(first['buildKey'],second['buildKey'])
            self.assertEqual(second['replay'],'unchanged-content-no-op')
            self.assertEqual(second['bodyOperationsAllowed'],[])

    def test_nonfinite_and_surrogate_metadata_do_not_escape_source_boundary(self):
        good, good_raw = fixture()
        for literal in (b'1e999', b'"\\ud800"'):
            with self.subTest(literal=literal):
                raw = (b'{"utc":"2026-10-14T00:00:00Z","value":' + literal + b'}')
                bad = copy.deepcopy(good)
                bad['metadataPin'].update(bytes=len(raw), sha256=sha(raw))
                bad['fieldSelectors'] = {'value': '/value'}
                report = assess_portfolio([bad, good],
                    lambda pin: raw if pin['sha256'] == sha(raw) else good_raw, now=CLOCK)
                self.assertEqual([r['status'] for r in report['sources']],
                                 ['MALFORMED', 'READY_METADATA'])
                failed = report['sources'][0]
                self.assertEqual(failed['diagnostics'], ['metadata-json-invalid'])
                self.assertIsNone(failed['metadataRecord'])
                self.assertIsNone(failed['buildKey'])
                self.assertEqual(failed['replay'], 'not-ready')
                # The entire report must remain valid UTF-8/finite JSON, not just its status.
                canonical(report)

    def test_reader_rejects_nonregular_symlink_and_oversize_inputs(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            regular = root/'receipt.json'; regular.write_bytes(b'{"authored":true}')
            self.assertEqual(read_metadata({'path': str(regular)}), regular.read_bytes())
            fifo = root/'fifo.json'; os.mkfifo(fifo)
            with self.assertRaisesRegex(RefreshError, '^metadata-input-not-regular$'):
                read_metadata({'path': str(fifo)})
            with self.assertRaisesRegex(RefreshError, '^metadata-input-not-regular$'):
                read_metadata({'path': str(root)})
            alias = root/'alias.json'; alias.symlink_to(regular)
            with self.assertRaisesRegex(RefreshError, '^symlink-path-rejected$'):
                read_metadata({'path': str(alias)})
            with patch('offmenu.refresh.portfolio41.MAX_METADATA', 4):
                with self.assertRaisesRegex(RefreshError, '^metadata-size-limit$'):
                    read_metadata({'path': str(regular)})

    def test_reader_rejects_replacement_and_closes_single_descriptor(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t); source = root/'receipt.json'; other = root/'other.json'
            source.write_bytes(b'{}'); other.write_bytes(b'[]')
            original_read = os.read
            replaced = False
            def replace_after_read(fd, size):
                nonlocal replaced
                data = original_read(fd, size)
                if not replaced:
                    other.replace(source)
                    replaced = True
                return data
            with patch('offmenu.refresh.portfolio41.os.read', side_effect=replace_after_read), \
                 patch('offmenu.refresh.portfolio41.os.close', wraps=os.close) as close:
                with self.assertRaisesRegex(RefreshError, '^metadata-changed-during-read$'):
                    read_metadata({'path': str(source)})
                close.assert_called_once()

    def test_actual_cli_rejects_fifo_promptly_before_source_processing(self):
        with tempfile.TemporaryDirectory() as t:
            fifo = Path(t)/'previous.json'; os.mkfifo(fifo)
            output = Path(t)/'output.json'
            command = [sys.executable, '-B', '-m', 'offmenu.refresh.portfolio41',
                '--now', '2026-10-18T00:00:00Z', '--previous-report', str(fifo),
                '--output', str(output)]
            child = subprocess.run(command, cwd=Path(__file__).resolve().parents[1],
                capture_output=True, text=True, timeout=2)
            self.assertNotEqual(child.returncode, 0)
            self.assertIn('metadata-input-not-regular', child.stderr)
            self.assertFalse(output.exists())


if __name__=='__main__': unittest.main()
