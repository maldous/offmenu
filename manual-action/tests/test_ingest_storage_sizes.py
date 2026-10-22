"""Metadata-only storage visibility: generated paths, no retained/live database."""
import copy
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ingest_storage_sizes as sizes
import ingest_engine as engine
from ingest_api import DOMAINS
import plan_runner as runner


class StorageSizesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root / 'state'

    def path(self, domain, suffix=''):
        directory = self.state / ('private-household' if domain in ('user_profiles', 'inventory') else '.') / 'staging'
        directory.mkdir(parents=True, exist_ok=True)
        return directory / (domain + '.sqlite3' + suffix)

    def test_only_fixed_metadata_observed_with_sparse_and_sidecar_sizes(self):
        for domain in DOMAINS:
            self.path(domain).write_bytes(b'generated')
        sparse = self.path('recipes')
        with sparse.open('wb') as stream:
            stream.truncate(1024 * 1024)
        wal = self.path('recipes', '-wal')
        wal.write_bytes(b'wal')
        shm = self.path('inventory', '-shm')
        shm.write_bytes(b'shm')
        expected = {domain: [[path.stat().st_size, path.stat().st_blocks * 512]
            if path.exists() else [0, 0]
            for path in [self.path(domain, suffix) for suffix in sizes.SUFFIXES]] for domain in DOMAINS}
        inspected = []
        original = Path.lstat
        def metadata(path):
            inspected.append(path)
            return original(path)
        with mock.patch.object(Path, 'lstat', metadata), \
             mock.patch('builtins.open', side_effect=AssertionError('content open refused')), \
             mock.patch.object(Path, 'open', side_effect=AssertionError('content open refused')), \
             mock.patch.object(sqlite3, 'connect', side_effect=AssertionError('SQLite refused')), \
             mock.patch.object(Path, 'glob', side_effect=AssertionError('enumeration refused')), \
             mock.patch.object(Path, 'rglob', side_effect=AssertionError('enumeration refused')), \
             mock.patch.object(os, 'scandir', side_effect=AssertionError('enumeration refused')):
            result = sizes.capture_storage_sizes(self.state)
        self.assertEqual(result['domains'], expected)
        self.assertEqual(len([path for path in inspected if path.name.endswith(('.sqlite3', '-wal', '-shm'))]), 24)
        self.assertEqual(len(inspected), len(set(inspected)))
        self.assertLessEqual(len(inspected), 24 + len(self.state.parts) + 5)
        self.assertEqual(result['totals']['files_total'], 24)
        self.assertEqual(result['totals']['logical_files_known'], 24)
        self.assertEqual(result['totals']['logical_bytes'], sum(row[0] for rows in expected.values() for row in rows))
        self.assertEqual(result['totals']['allocated_bytes'], sum(row[1] for rows in expected.values() for row in rows))
        self.assertEqual(result['cache'], {'scope': 'not_measured', 'logical_bytes': None, 'allocated_bytes': None})
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_absent_known_zero_denied_symlink_and_nonregular_unknown(self):
        empty = sizes.capture_storage_sizes(self.state)
        self.assertEqual(empty['totals']['logical_bytes'], 0)
        self.assertEqual(empty['totals']['allocated_bytes'], 0)
        target = self.root / 'do-not-read'
        target.write_bytes(b'private')
        self.path('barcodes').symlink_to(target)
        self.path('ingredients').mkdir()
        result = sizes.capture_storage_sizes(self.state)
        self.assertEqual(result['domains']['barcodes'][0], [None, None])
        self.assertEqual(result['domains']['ingredients'][0], [None, None])
        self.assertIsNone(result['totals']['logical_bytes'])
        original = Path.lstat
        denied = self.path('recipes')
        def metadata(path):
            if path == denied:
                raise PermissionError('PRIVATE')
            return original(path)
        with mock.patch.object(Path, 'lstat', metadata):
            result = sizes.capture_storage_sizes(self.state)
        self.assertEqual(result['domains']['recipes'][0], [None, None])
        self.assertNotIn('PRIVATE', json.dumps(result))
        other = self.root / 'linked-state'
        other.symlink_to(self.state, target_is_directory=True)
        self.assertEqual(sizes.capture_storage_sizes(other)['totals']['logical_files_known'], 0)

    def test_unavailable_allocated_metadata_is_unknown_not_logical_estimate(self):
        path = self.path('barcodes')
        path.write_bytes(b'generated')
        original = Path.lstat
        def metadata(candidate):
            observed = original(candidate)
            if candidate == path:
                return SimpleNamespace(st_mode=observed.st_mode, st_size=123)
            return observed
        with mock.patch.object(Path, 'lstat', metadata):
            result = sizes.capture_storage_sizes(self.state)
        self.assertEqual(result['domains']['barcodes'][0], [123, None])
        self.assertEqual(result['totals']['logical_bytes'], 123)
        self.assertIsNone(result['totals']['allocated_bytes'])

    def test_strict_optional_companion_and_old_canonical_bytes(self):
        import ingest_evidence
        old = {'schema': 'offmenu-ingest-supplement/1', 'ingest_evidence': ingest_evidence.sanitize_evidence({})}
        raw = runner.canonical(old)
        runner.validate_supplement(old)
        self.assertEqual(runner.canonical(old), raw)
        value = sizes.capture_storage_sizes(self.state)
        supplemental = runner.build_supplement({'storage_sizes': value})
        self.assertEqual(runner.validate_supplement(supplemental), supplemental)
        mutations = [lambda v: v.update(path='/PRIVATE'),
            lambda v: v['domains']['inventory'][0].__setitem__(0, True),
            lambda v: v['totals'].__setitem__('logical_bytes', 99),
            lambda v: v['cache'].__setitem__('logical_bytes', 0),
            lambda v: v['domains']['inventory'][0].__setitem__(1, -1),
            lambda v: v['domains'].__setitem__('private_unknown', [[0, 0]] * 3)]
        for mutate in mutations:
            bad = copy.deepcopy(supplemental)
            mutate(bad['storage_sizes'])
            with self.assertRaises(runner.Stop):
                runner.validate_supplement(bad)

    def test_worst_existing_evidence_and_preparation_companion_stays_bounded(self):
        import ingest_evidence
        from test_ingest_evidence import EvidenceTests
        import ingest_household_preparation as preparation
        import ingest_relational_targets
        fixture = EvidenceTests('test_worst_finite_enum_supplement_is_bounded_without_count_loss')
        with mock.patch.object(ingest_evidence, 'validate_evidence', wraps=ingest_evidence.validate_evidence) as validate:
            fixture.test_worst_finite_enum_supplement_is_bounded_without_count_loss()
        evidence = validate.call_args.args[0]
        storage = sizes.unknown_storage_sizes()
        storage['domains'] = {domain: [[sizes.MAX_BYTES, sizes.MAX_BYTES] for _ in sizes.FILES] for domain in DOMAINS}
        storage['totals'] = sizes._totals(storage['domains'])
        prepared = preparation.unavailable()
        prepared.update(status='schema_prepared_app_wiring_pending', reason='verified_in_memory',
            domain_table_count=31, private_rows=0, foreign_key_check='passed', integrity_check='passed',
            source_sha256={'helper': 'f' * 64, 'plan': 'f' * 64, 'sql': [preparation.BASE_SQL_SHA256, 'f' * 64, 'f' * 64]})
        supplement = {'schema': 'offmenu-ingest-supplement/1', 'ingest_evidence': evidence,
            'relational_targets': ingest_relational_targets.sanitize_relational_summary({}),
            'household_schema_preparation': prepared, 'storage_sizes': storage}
        runner.validate_supplement(supplement)
        self.assertLessEqual(len(runner.canonical(supplement)), 65536)

    def test_engine_checkpoints_include_sizes_and_failure_does_not_block_ingestion(self):
        source_path = self.root / 'generated.jsonl'
        source_path.write_text('{"id":"generated"}\n')
        source = {'id': 'generated', 'path': str(source_path), 'format': 'jsonl', 'domains': ['barcodes']}
        config = {'state_dir': str(self.state), 'reserve_bytes': 0, 'workers': 1, 'terminal_progress': False}
        callbacks = []
        result = engine.run_ingest([source], config, callbacks.append)
        self.assertEqual(result['domains']['barcodes']['written'], 1)
        self.assertTrue(all('storage_sizes' in row for row in callbacks))
        self.assertGreater(result['storage_sizes']['domains']['barcodes'][0][0], 0)
        self.assertEqual(engine.sanitize_report(result), result)
        self.assertEqual(runner.build_supplement(result)['storage_sizes'], result['storage_sizes'])
        with mock.patch.object(sizes, 'capture_storage_sizes', side_effect=OSError('PRIVATE')):
            second = engine.run_ingest([source], config)
        self.assertEqual(second['domains']['barcodes']['unchanged'], 1)
        self.assertEqual(second['storage_sizes'], sizes.unknown_storage_sizes())
        self.assertNotIn('PRIVATE', json.dumps(second))


if __name__ == '__main__':
    unittest.main()
