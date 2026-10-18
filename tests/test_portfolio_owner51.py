"""Authored fixture tests only; never open retained country artifacts."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio_owner51 as binding
from offmenu.refresh.acceptance import qualify
from offmenu.refresh.core import RefreshError
from offmenu.refresh.serialization import asset, encode_records


class Owner51BindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.bundle = self.root / 'bundle'
        shutil.copytree(Path(__file__).parent / 'fixtures' / 'owner51', self.bundle)
        self.now = '2026-10-18T00:00:00Z'

    def run_fixture(self, **kwargs):
        return binding.run_fixture(self.bundle, now=self.now, **kwargs)

    def test_valid_deterministic_private_fixture(self):
        first, raw = self.run_fixture()
        self.assertEqual(first['status'], 'fixture-qualified')
        self.assertEqual(first['qualification']['normalizedRecords'], 2)
        self.assertEqual((first, raw), self.run_fixture())
        self.assertFalse(first['productionAccepted'])
        self.assertFalse(first['countryCoverageComplete'])
        self.assertFalse(first['goldAdmitted'])
        rows = [json.loads(line)[0] for line in raw.splitlines()]
        self.assertEqual(rows[0]['data']['valueLiteral'], '1 234')
        self.assertIsNone(rows[0]['data']['currencyISO'])
        self.assertEqual(rows[0]['data']['periodLiteral'], 'per månad')
        for row in rows:
            self.assertEqual(binding.semantics(row), [])

    def test_held_and_stale_never_open_paths(self):
        with patch.object(binding, 'safe_path', side_effect=AssertionError('body opened')):
            result, raw = self.run_fixture(held=True)
            self.assertEqual(result['errors'], ['source-use-held'])
            self.assertIsNone(raw)
            result, raw = binding.run_fixture(self.bundle, now='2026-10-31T00:00:00Z')
            self.assertEqual(result['errors'], ['cache-stale'])
            self.assertIsNone(raw)

    def test_validation_time_does_not_reset_acquisition(self):
        result, raw = binding.run_fixture(self.bundle, now='2026-11-01T00:00:00Z',
                                         validated_at='2026-10-31T23:59:59Z')
        self.assertEqual(result['errors'], ['cache-stale'])
        self.assertIsNone(raw)
        self.assertEqual(binding.cache_diagnostic(binding.ACQUIRED,
            '2026-10-30T23:59:59Z')['status'], 'reuse-window')

    def test_invalid_and_future_clocks_hold(self):
        for now, validated in [('2026-09-30T00:00:00Z', None),
                               (self.now, '2026-10-19T00:00:00Z'),
                               ('garbage', None), (self.now, '2026-09-01T00:00:00Z'),
                               ('2026-10-18T00:00:00+11:00', None)]:
            result, raw = binding.run_fixture(self.bundle, now=now, validated_at=validated)
            self.assertEqual(result['status'], 'held')
            self.assertIsNone(raw)

    def test_missing_malformed_and_drift_inputs_hold(self):
        path = self.bundle / 'input.json'
        original = path.read_bytes()
        path.unlink()
        self.assertEqual(self.run_fixture()[0]['errors'], ['input-missing'])
        for body in [b'{', b'{"cells":[],"cells":[]}', b'{"n":NaN}',
                     original.replace(b'1 234', b'9 999')]:
            path.write_bytes(body)
            result, raw = self.run_fixture()
            self.assertEqual(result['errors'], ['input-pin-mismatch'])
            self.assertIsNone(raw)
        path.write_bytes(b'x' * 5000)
        self.assertEqual(self.run_fixture()[0]['errors'], ['input-invalid'])

    def test_special_input_and_output_files_rejected_without_wait(self):
        path = self.bundle / 'input.json'
        path.unlink()
        os.mkfifo(path)
        self.assertEqual(self.run_fixture()[0]['errors'], ['input-invalid'])
        target = self.root / 'output-fifo'
        os.mkfifo(target)
        with self.assertRaises(RefreshError):
            binding.write_fixture_output(target, b'fixture')

    def test_symlink_input_and_bundle_rejected(self):
        path = self.bundle / 'input.json'
        real = self.root / 'real.json'
        path.rename(real)
        path.symlink_to(real)
        self.assertEqual(self.run_fixture()[0]['errors'], ['input-invalid'])
        link = self.root / 'bundle-link'
        link.symlink_to(self.bundle, target_is_directory=True)
        self.assertEqual(binding.run_fixture(link, now=self.now)[0]['errors'], ['input-invalid'])

    def test_extra_input_inventory_is_not_silently_ignored(self):
        (self.bundle / 'extra.json').write_text('{}')
        result, raw = self.run_fixture()
        self.assertIn('input-inventory-mismatch', result['errors'])
        self.assertIsNone(raw)

    def test_bad_peer_does_not_hide_valid_peer(self):
        result = binding.diagnose_many({'bad': self.root / 'missing', 'good': self.bundle}, now=self.now)
        self.assertEqual(result['bad']['errors'], ['input-missing'])
        self.assertEqual(result['good']['status'], 'fixture-qualified')

    def test_descriptor_refuses_symlink_or_fifo_swapped_before_open(self):
        real_open = os.open
        for replacement in ('symlink', 'fifo'):
            with self.subTest(replacement=replacement):
                bundle = self.root / ('before-' + replacement)
                shutil.copytree(Path(__file__).parent / 'fixtures' / 'owner51', bundle)
                path = bundle / 'input.json'
                saved = self.root / ('saved-before-' + replacement)
                swapped = []

                def opening(name, flags, *args, **kwargs):
                    if str(name) == 'input.json' and not flags & os.O_DIRECTORY:
                        self.assertTrue(flags & os.O_NONBLOCK)
                        self.assertTrue(flags & os.O_NOFOLLOW)
                        path.rename(saved)
                        if replacement == 'symlink':
                            path.symlink_to(saved)
                        else:
                            os.mkfifo(path)
                        swapped.append(True)
                    return real_open(name, flags, *args, **kwargs)

                with patch.object(binding.os, 'open', side_effect=opening), \
                        patch.object(binding.os, 'read', side_effect=AssertionError('replacement read')), \
                        patch.object(binding, 'strict_json', side_effect=AssertionError('replacement parsed')):
                    result, raw = binding.run_fixture(bundle, now=self.now)
                self.assertEqual(swapped, [True])
                self.assertEqual(result['errors'], ['input-invalid'])
                self.assertIsNone(raw)

    def test_descriptor_refuses_path_replacement_during_read(self):
        real_read = os.read
        for replacement in ('symlink', 'regular'):
            with self.subTest(replacement=replacement):
                bundle = self.root / ('during-' + replacement)
                shutil.copytree(Path(__file__).parent / 'fixtures' / 'owner51', bundle)
                path = bundle / 'input.json'
                saved = self.root / ('saved-during-' + replacement)
                original = path.read_bytes()
                read_bytes = []

                def reading(descriptor, limit):
                    path.rename(saved)
                    if replacement == 'symlink':
                        path.symlink_to(saved)
                    else:
                        path.write_bytes(original)
                    value = real_read(descriptor, limit)
                    read_bytes.append(value)
                    return value

                with patch.object(binding.os, 'read', side_effect=reading), \
                        patch.object(binding, 'strict_json', side_effect=AssertionError('replaced path parsed')):
                    result, raw = binding.run_fixture(bundle, now=self.now)
                self.assertEqual(read_bytes, [original])
                self.assertEqual(result['errors'], ['input-invalid'])
                self.assertIsNone(raw)

    def test_changed_ingress_does_not_hide_positive_peer(self):
        bad = self.root / 'changed-peer'
        shutil.copytree(Path(__file__).parent / 'fixtures' / 'owner51', bad)
        path = bad / 'input.json'
        real_read = os.read
        original_inode = path.stat().st_ino
        swapped = []

        def reading(descriptor, limit):
            if os.fstat(descriptor).st_ino == original_inode and not swapped:
                saved = self.root / 'peer-original.json'
                path.rename(saved)
                path.symlink_to(saved)
                swapped.append(True)
            return real_read(descriptor, limit)

        with patch.object(binding.os, 'read', side_effect=reading):
            result = binding.diagnose_many({'bad': bad, 'good': self.bundle}, now=self.now)
        self.assertEqual(swapped, [True])
        self.assertEqual(result['bad']['errors'], ['input-invalid'])
        self.assertEqual(result['good']['status'], 'fixture-qualified')

    def qualify_rows(self, rows):
        positive, _ = self.run_fixture()
        raw = encode_records(rows)
        candidate = self.root / 'candidate.jsonl'
        candidate.write_bytes(raw)
        manifest = copy.deepcopy(positive['manifest'])
        manifest.update(candidateBytes=len(raw), candidateSha256=asset(raw)['sha256'])
        return qualify(binding.fixture_contract(), self.bundle, candidate, manifest)

    def test_shared_qualification_rejects_wrong_values_and_origins(self):
        changes = [lambda row: row['data'].update(currencyISO='SEK'),
                   lambda row: row['data'].update(periodLiteral='per kg'),
                   lambda row: row['data'].update(valueLiteral='1234'),
                   lambda row: row['provenance']['fieldOrigins']['/data/age'].update(sourceField='/wrong'),
                   lambda row: row['provenance']['fieldOrigins'].pop('/data/currencyISO')]
        for change in changes:
            rows = copy.deepcopy(binding.EXPECTED_ROWS)
            change(rows[0])
            result = self.qualify_rows(rows)
            self.assertFalse(result['qualified'])
            self.assertIn('fixture-value-or-origin-mismatch', result['errors'])

    def test_shared_qualification_rejects_partial_duplicate_or_foreign_rows(self):
        for rows in [binding.EXPECTED_ROWS[:1], [binding.EXPECTED_ROWS[0]] * 2,
                     [{**binding.EXPECTED_ROWS[0], 'id': 'foreign'}, binding.EXPECTED_ROWS[1]]]:
            self.assertFalse(self.qualify_rows(rows)['qualified'])

    def test_output_noop_conflict_and_symlink(self):
        _, raw = self.run_fixture()
        target = self.root / 'fixture.jsonl'
        self.assertEqual(binding.write_fixture_output(target, raw), 'created')
        before = target.stat().st_mtime_ns
        self.assertEqual(binding.write_fixture_output(target, raw), 'no-op')
        self.assertEqual(before, target.stat().st_mtime_ns)
        with self.assertRaises(RefreshError):
            binding.write_fixture_output(target, b'different')
        self.assertEqual(target.read_bytes(), raw)
        link = self.root / 'output-link'
        link.symlink_to(target)
        with self.assertRaises(RefreshError):
            binding.write_fixture_output(link, raw)

    def test_documented_portfolio_has_no_production_activation(self):
        metadata = json.loads(Path(binding.__file__).with_name('portfolio_owner51.json').read_text())
        self.assertEqual([b['country'] for b in metadata['bindings']], ['SE', 'MW', 'PW', 'SN'])
        self.assertFalse(metadata['sourceBodyReadsEnabled'])
        self.assertFalse(metadata['productionAccepted'])
        self.assertEqual(metadata['bindings'][0]['retainedCounts']['sourceCells'], 20)
        self.assertEqual(metadata['fixture']['expectedRecords'], 2)


if __name__ == '__main__':
    unittest.main()
