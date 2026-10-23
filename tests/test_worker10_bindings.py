"""Authored metadata fixtures only; no retained source payloads are loaded."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.worker10_bindings import assess, load_config, pointer

NOW = '2026-10-18T00:00:00+00:00'


class Worker10BindingsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.config = deepcopy(load_config())
        self.paths = {}
        self.documents = {}
        for entry in self.config['bindings']:
            entry['fields'] = {'release': '/release', 'zero': '/zero',
                               'nullValue': '/nullable', 'falseValue': '/flag',
                               'escaped': '/a~1b/~0value'}
            entry['originalAcquiredAtSelector'] = '/acquiredAt'
            document = {'release': 'AUTHORED-TEST-EDITION', 'zero': 0,
                        'nullable': None, 'flag': False, 'a/b': {'~value': 'fixture'},
                        'acquiredAt': '2026-10-14T00:00:00+00:00',
                        'originalPath': '/MUST-NOT-OPEN-SOURCE-BODY'}
            self.documents[entry['id']] = document
            path = Path(self.temp.name) / (entry['id'] + '.json')
            self.paths[entry['id']] = path
            self.write(entry['id'], canonical(document))

    def write(self, identity, raw):
        self.paths[identity].write_bytes(raw)
        entry = next(b for b in self.config['bindings'] if b['id'] == identity)
        entry.update(bytes=len(raw), sha256=sha(raw))

    def run_assess(self, **kwargs):
        return assess(self.config, self.paths, validated_at=NOW, **kwargs)

    def test_valid_metadata_held_sources_and_exact_origins(self):
        result = self.run_assess()
        self.assertEqual(result['status'], 'assessed')
        self.assertEqual(len(result['staging']), 5)
        statuses = {r['bindingId']: r['status'] for r in result['results']}
        self.assertEqual(statuses['sa-cpi-method'], 'valid')
        self.assertEqual(sum(s == 'held' for s in statuses.values()), 4)
        self.assertEqual(result['normalizedFoodRecords'], 0)
        self.assertFalse(result['productionAdmission'])
        for row in result['staging']:
            entry = next(b for b in self.config['bindings'] if row['id'].endswith(':' + b['id']))
            self.assertEqual(field_origin_errors(row, {entry['inputPath']: entry['sha256']}), [])
            self.assertEqual(row['data']['zero'], 0)
            self.assertIsNone(row['data']['nullValue'])
            self.assertIs(row['data']['falseValue'], False)
            self.assertEqual(row['provenance']['fieldOrigins']['/data/escaped']['sourceField'], '/a~1b/~0value')

    def test_missing_is_isolated(self):
        del self.paths['kw-pista-menu']
        result = self.run_assess()
        self.assertEqual(result['results'][0]['status'], 'missing')
        self.assertEqual(len(result['staging']), 4)
        self.assertEqual(len(result['coverage']), 24)
        self.assertTrue(all(not r['countryComplete'] for r in result['coverage']))
        self.assertTrue(all(r['dataStatus'] == 'missing-input' for r in result['coverage'] if r['type'] == 'recipes'))

    def test_absent_file_is_missing(self):
        self.paths['kw-pista-menu'].unlink()
        self.assertEqual(self.run_assess()['results'][0]['status'], 'missing')

    def test_malformed_json_is_isolated_without_error_values(self):
        self.write('kw-pista-menu', b'{"secret-value-not-in-error":')
        result = self.run_assess()
        self.assertEqual(result['results'][0]['status'], 'malformed')
        self.assertEqual(len(result['staging']), 4)
        self.assertNotIn('secret-value-not-in-error', json.dumps(result))

    def test_duplicate_json_keys_and_nonfinite_are_rejected(self):
        for raw in (b'{"x":1,"x":2}', b'{"x":NaN}'):
            self.write('kw-pista-menu', raw)
            self.assertEqual(self.run_assess()['results'][0]['status'], 'malformed')

    def test_missing_selector_does_not_shift_or_guess_fields(self):
        self.write('kw-pista-menu', canonical({'differentRelease': 'test'}))
        result = self.run_assess()
        self.assertEqual(result['results'][0]['diagnostics'], ['metadata-selector-missing'])
        self.assertEqual(len(result['staging']), 4)

    def test_hash_mismatch_preserves_all_peer_diagnostics_in_every_order(self):
        entries = sorted(self.config['bindings'], key=lambda b: b['id'])
        for index in (0, 2, 4):
            entry = entries[index]
            previous = entry['sha256']
            entry['sha256'] = '0' * 64
            try:
                result = self.run_assess()
            finally:
                entry['sha256'] = previous
            self.assertEqual(result['status'], 'stopped')
            self.assertEqual(result['staging'], [])
            self.assertEqual(len(result['results']), 5)
            failed = result['results'][index]
            self.assertEqual(failed['diagnostics'], ['metadata-pin-mismatch'])
            self.assertEqual(failed['metadataRecords'], 0)
            self.assertEqual(sum(r['metadataRecords'] for r in result['results']), 4)

    def test_cumulative_budget_exhaustion_stops(self):
        # Authored oversize input, never a source body.
        self.paths['kw-pista-menu'].write_bytes(b' ' * (1024 * 1024 + 1))
        result = self.run_assess()
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(result['metadataBytesRead'], 0)
        self.assertEqual(result['results'][0]['diagnostics'], ['metadata-cumulative-budget-exhausted'])
        self.assertEqual(len(result['results']), 5)
        self.assertTrue(all(r['status'] == 'skipped-budget' for r in result['results'][1:]))

    def test_budget_after_prior_read_reports_every_unread_peer_without_open(self):
        first = 'kw-pista-menu'
        raw = b' ' * 600000
        self.write(first, raw)  # Authored malformed metadata consumes budget.
        self.paths['no-composition'].write_bytes(b' ' * 600000)
        opened = []
        original = os.open
        def guard(path, flags, *args, **kwargs):
            opened.append(str(path))
            return original(path, flags, *args, **kwargs)
        with patch('os.open', guard):
            result = self.run_assess()
        self.assertEqual(result['metadataBytesRead'], len(raw))
        self.assertEqual(result['status'], 'stopped')
        self.assertEqual(len(result['results']), 5)
        self.assertEqual(len(opened), 2)
        self.assertEqual([r['status'] for r in result['results'][2:]], ['skipped-budget'] * 3)

    def test_fifo_or_regular_replacement_after_stat_never_blocks_or_parses(self):
        selected = self.paths['kw-pista-menu']
        original = os.open
        for kind in ('fifo', 'regular', 'symlink'):
            if selected.is_symlink() or selected.exists():
                selected.unlink()
            self.write('kw-pista-menu', canonical(self.documents['kw-pista-menu']))
            calls = []
            def swap(path, flags, *args, **kwargs):
                self.assertTrue(flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW)
                calls.append((str(path), flags))
                if Path(path) == selected:
                    if kind == 'fifo':
                        selected.unlink()
                        os.mkfifo(selected)
                    elif kind == 'symlink':
                        selected.unlink()
                        selected.symlink_to(self.paths['no-composition'])
                    else:
                        # Same exact bytes/pin on a different inode must be rejected.
                        replacement = selected.with_name('replacement.json')
                        replacement.write_bytes(canonical(self.documents['kw-pista-menu']))
                        os.replace(replacement, selected)
                return original(path, flags, *args, **kwargs)
            with patch('os.open', swap):
                result = self.run_assess()
            self.assertEqual(result['results'][0]['status'], 'malformed')
            self.assertEqual(len(result['results']), 5)
            self.assertEqual(len(result['staging']), 4)
            self.assertTrue(all(flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW for _, flags in calls))
            if kind != 'symlink':
                self.assertEqual(result['results'][0]['diagnostics'], ['metadata-input-replaced'])

    def test_descriptor_read_then_path_replacement_is_rejected_and_budget_counted(self):
        selected = self.paths['kw-pista-menu']
        original = os.read
        opened_size = selected.stat().st_size
        def replace_at_read(fd, *args, **kwargs):
            selected.unlink()
            selected.write_bytes(b'AUTHORED-REPLACEMENT')
            return original(fd, *args, **kwargs)
        # Replace only at the first descriptor read, leaving peers untouched.
        count = 0
        def once(fd, *args, **kwargs):
            nonlocal count
            count += 1
            return replace_at_read(fd, *args, **kwargs) if count == 1 else original(fd, *args, **kwargs)
        with patch('os.read', once):
            result = self.run_assess()
        self.assertEqual(result['results'][0]['diagnostics'], ['metadata-input-replaced'])
        self.assertEqual(len(result['staging']), 4)
        self.assertEqual(result['metadataBytesRead'], opened_size + sum(p.stat().st_size for k, p in self.paths.items() if k != 'kw-pista-menu'))

    def test_stale_original_uses_acquisition_age_and_keeps_source_hold(self):
        document = self.documents['kw-pista-menu']
        document['acquiredAt'] = '2026-08-01T00:00:00+00:00'
        document['lastValidatedAt'] = NOW
        self.write('kw-pista-menu', canonical(document))
        result = self.run_assess(force=True)
        entry = result['results'][0]
        self.assertEqual(entry['status'], 'stale-input')
        self.assertEqual(entry['sourceStage'], 'held')
        self.assertEqual(entry['cache']['acquisitionAgeSeconds'], 78 * 86400)
        self.assertEqual(entry['cache']['validationAgeSeconds'], 0)
        self.assertFalse(entry['cache']['downloadAllowed'])

    def test_exact_30_day_boundary(self):
        document = self.documents['sa-cpi-method']
        for date, expected in [('2026-09-18T00:00:01+00:00', 'valid'),
                               ('2026-09-18T00:00:00+00:00', 'stale-input')]:
            document['acquiredAt'] = date
            self.write('sa-cpi-method', canonical(document))
            result = self.run_assess()
            entry = next(r for r in result['results'] if r['bindingId'] == 'sa-cpi-method')
            self.assertEqual(entry['status'], expected)

    def test_unknown_acquisition_age_remains_unknown(self):
        self.config['bindings'][0]['originalAcquiredAtSelector'] = None
        entry = self.run_assess()['results'][0]
        self.assertIsNone(entry['cache']['acquisitionAgeSeconds'])
        self.assertEqual(entry['cache']['decision'], 'original-acquisition-age-unknown')

    def test_future_and_naive_acquisition_dates_are_malformed(self):
        for stamp in ('2026-10-19T00:00:00+00:00', '2026-10-14T00:00:00'):
            document = self.documents['kw-pista-menu']
            document['acquiredAt'] = stamp
            self.write('kw-pista-menu', canonical(document))
            self.assertEqual(self.run_assess()['results'][0]['status'], 'malformed')

    def test_deterministic_replay_noop_survives_validation_time_change(self):
        first = self.run_assess()
        second = assess(self.config, self.paths, validated_at='2026-10-19T00:00:00+00:00',
                        previous_staging=canonical(first['staging']))
        self.assertEqual(first['staging'], second['staging'])
        self.assertEqual(second['replay'], 'verified-no-op')
        self.assertNotEqual(first['results'][0]['cache']['acquisitionAgeSeconds'],
                            second['results'][0]['cache']['acquisitionAgeSeconds'])

    def test_force_cannot_download_or_open_referenced_bodies(self):
        opened = []
        original = os.open
        def guarded(path, flags, *args, **kwargs):
            opened.append(str(path))
            if str(path) not in {str(p) for p in self.paths.values()}:
                raise AssertionError('unselected path opened')
            self.assertTrue(flags & os.O_NONBLOCK and flags & os.O_NOFOLLOW)
            return original(path, flags, *args, **kwargs)
        with patch('os.open', guarded), patch('socket.socket', side_effect=AssertionError('network')):
            result = self.run_assess(force=True)
        self.assertEqual(len(opened), 5)
        self.assertEqual(result['sourceBodiesRead'], 0)
        self.assertEqual(result['networkRequests'], 0)
        self.assertTrue(all(not r['cache']['downloadAllowed'] for r in result['results']))
        self.assertTrue(all(r['cache']['decision'] == 'reuse-retained-metadata-zero-download' for r in result['results']))

    def test_symlink_metadata_is_rejected_without_following_it(self):
        link = Path(self.temp.name) / 'link.json'
        link.symlink_to(self.paths['kw-pista-menu'])
        self.paths['kw-pista-menu'] = link
        self.assertEqual(self.run_assess()['results'][0]['diagnostics'], ['symlink-path-rejected'])

    def test_invalid_config_fails_before_any_open(self):
        self.config['bindings'].append(self.config['bindings'][0])
        with patch.object(Path, 'open', side_effect=AssertionError('must not open')):
            with self.assertRaisesRegex(RefreshError, 'worker10-binding-duplicate'):
                self.run_assess()

    def test_pointer_rejects_wildcards_invalid_escape_and_objects(self):
        for selector in ('/*', '/a~2b', '/object', '/list/01'):
            with self.assertRaises(RefreshError):
                pointer({'object': {}, 'list': [1]}, selector)


if __name__ == '__main__':
    unittest.main()
