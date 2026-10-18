"""Authored PR47 partial-artifact boundary regressions; no source I/O."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from offmenu.refresh import portfolio15 as p
from offmenu.refresh.core import canonical
from tests.test_portfolio15_binding import contract, NOW


class PartialArtifactDeltaTests(unittest.TestCase):
    def assert_clean_malformed(self, result):
        self.assertEqual(result['status'], 'MALFORMED')
        for name in ('record', 'buildKey', 'replay', 'cache'):
            self.assertIsNone(result[name], name)
        for name in ('applicability', 'sourceAssetClaim', 'metadataManifestPins',
                     'sourceAssetVerifiedByThisPlan', 'sharedAdapterCandidates'):
            self.assertNotIn(name, result)
        self.assertEqual(result['sourceBodyReads'], 0)
        self.assertEqual(result['networkRequests'], 0)
        self.assertFalse(result['sourceAccepted'])
        self.assertFalse(result['goldAdmitted'])
        self.assertTrue(result['sourceHolds'])

    def invalid_clock(self):
        _, raw = contract()
        doc = json.loads(raw)
        doc['originalAcquiredAt'] = 'authored-invalid-clock'
        return contract(canonical(doc))

    def test_invalid_original_acquisition_clears_record_and_claims(self):
        binding, raw = self.invalid_clock()
        result = p.plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['diagnostics'], ['binding-or-metadata-invalid'])
        self.assert_clean_malformed(result)

    def test_missing_cache_meaning_clears_build_key_and_replay(self):
        binding, raw = contract()
        del binding['cache']['meaning']
        result = p.plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['diagnostics'], ['binding-or-metadata-invalid'])
        self.assert_clean_malformed(result)

    def test_explicit_malformed_return_and_depth_share_cleanup(self):
        _, raw = contract()
        doc = json.loads(raw);doc['country'] = 'BE'
        binding, raw = contract(canonical(doc))
        result = p.plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['diagnostics'], ['metadata-country-mismatch'])
        self.assert_clean_malformed(result)
        binding, raw = contract(b'[' * 20000 + b'0' + b']' * 20000)
        result = p.plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['diagnostics'], ['metadata-depth-limit-exceeded'])
        self.assert_clean_malformed(result)

    def test_valid_and_noop_keep_claims_and_holds(self):
        binding, raw = contract()
        first = p.plan(binding, {'fixture': raw}, now=NOW)
        again = p.plan(binding, {'fixture': raw}, now='2026-10-19T00:00:00Z',
                       previous_build=first['buildKey'])
        self.assertEqual(first['status'], 'READY_METADATA_ONLY')
        self.assertEqual(again['status'], 'READY_METADATA_ONLY')
        self.assertEqual(again['replay'], 'NO_OP')
        self.assertEqual(first['record'], again['record'])
        self.assertEqual(first['buildKey'], again['buildKey'])
        self.assertTrue(again['metadataManifestPins'])
        self.assertTrue(again['sourceAssetClaim'])
        self.assertTrue(again['sourceHolds'])

    def test_cli_two_bad_bindings_do_not_suppress_valid_peer(self):
        bad_clock, clock_raw = self.invalid_clock()
        bad_meaning, meaning_raw = contract();del bad_meaning['cache']['meaning']
        good, good_raw = contract()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            bindings = []
            for i, (binding, raw) in enumerate([(bad_clock, clock_raw), (bad_meaning, meaning_raw), (good, good_raw)]):
                binding['id'] = 'authored-peer-' + str(i)
                path = root / (str(i) + '.json');path.write_bytes(raw)
                binding['evidence']['fixture']['recordedPath'] = str(path)
                bindings.append(binding)
            catalog = root / 'catalog.json'
            catalog.write_bytes(canonical({'schemaVersion': p.VERSION, 'bindings': bindings}))
            code = ('import sys,json;from pathlib import Path;from offmenu.refresh import portfolio15 as p;'
                    'p.CATALOGUE=json.loads(Path(sys.argv[1]).read_bytes());'
                    'sys.argv=["portfolio15","--now","2026-10-18T00:00:00Z"];p.main()')
            run = subprocess.run([sys.executable, '-B', '-c', code, str(catalog)],
                cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([r['status'] for r in rows], ['MALFORMED','MALFORMED','READY_METADATA_ONLY'])
        for row in rows[:2]:self.assert_clean_malformed(row)
        self.assertIsNotNone(rows[2]['record'])
        self.assertIsNotNone(rows[2]['buildKey'])
