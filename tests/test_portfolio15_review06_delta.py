"""Reviewer06 F1/F2: authored-only isolated regression probes."""
from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest

from offmenu.refresh.core import canonical
from offmenu.refresh.portfolio15 import plan
from tests.test_portfolio15_binding import contract, NOW


class Review06DeltaTests(unittest.TestCase):
    def test_F1_deep_metadata_returns_fixed_malformed(self):
        raw = b'[' * 20000 + b'0' + b']' * 20000
        binding, raw = contract(raw)
        result = plan(binding, {'fixture': raw}, now=NOW)
        self.assertEqual(result['status'], 'MALFORMED')
        self.assertEqual(result['diagnostics'], ['metadata-depth-limit-exceeded'])
        self.assertIsNone(result['record'])

    def test_F1_real_cli_bad_first_good_second_continues(self):
        bad_raw = b'[' * 20000 + b'0' + b']' * 20000
        bad, _ = contract(bad_raw)
        good, good_raw = contract()
        bad['id'], good['id'] = 'authored-bad-first', 'authored-good-second'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for binding, name, raw in [(bad, 'bad.json', bad_raw), (good, 'good.json', good_raw)]:
                path = root / name
                path.write_bytes(raw)
                binding['evidence']['fixture']['recordedPath'] = str(path)
            catalog = root / 'catalog.json'
            catalog.write_bytes(canonical({'schemaVersion': 'owner15-metadata-binding/1',
                                           'bindings': [bad, good]}))
            script = ('from pathlib import Path; import sys,json; '
                      'from offmenu.refresh import portfolio15 as p; '
                      'p.CATALOGUE=json.loads(Path(sys.argv[1]).read_bytes()); '
                      'sys.argv=["portfolio15", "--now", "2026-10-18T00:00:00Z"]; p.main()')
            run = subprocess.run([sys.executable, '-B', '-c', script, str(catalog)],
                                 cwd=Path(__file__).resolve().parents[1],
                                 capture_output=True, text=True, timeout=10)
        self.assertEqual(run.returncode, 0, run.stderr)
        rows = [json.loads(line) for line in run.stdout.splitlines()]
        self.assertEqual([r['bindingId'] for r in rows], ['authored-bad-first', 'authored-good-second'])
        self.assertEqual([r['status'] for r in rows], ['MALFORMED', 'READY_METADATA_ONLY'])
        self.assertEqual(rows[0]['diagnostics'], ['metadata-depth-limit-exceeded'])
        self.assertNotIn('RecursionError', run.stderr)
        self.assertTrue(all(r['sourceBodyReads'] == r['networkRequests'] == 0 for r in rows))

    def test_F1_structural_depth_boundary(self):
        _, raw = contract()
        original = json.loads(raw)
        for lists, status in [(63, 'READY_METADATA_ONLY'), (64, 'MALFORMED')]:
            with self.subTest(lists=lists):
                document = deepcopy(original)
                nested = 0
                for _ in range(lists):
                    nested = [nested]
                document['unused'] = nested  # Root object adds one container level.
                binding, encoded = contract(canonical(document))
                self.assertEqual(plan(binding, {'fixture': encoded}, now=NOW)['status'], status)

    def test_F1_brackets_in_escaped_strings_are_not_structure(self):
        _, raw = contract()
        document = json.loads(raw)
        document['title'] = ('[ { "quoted" \\ text } ]' * 100)
        binding, encoded = contract(canonical(document))
        result = plan(binding, {'fixture': encoded}, now=NOW)
        self.assertEqual(result['status'], 'READY_METADATA_ONLY')
        self.assertEqual(result['record']['data']['title'], document['title'])

    def test_F2_applicability_note_invalidates_binding_replay(self):
        binding, raw = contract()
        first = plan(binding, {'fixture': raw}, now=NOW)
        changed = deepcopy(binding)
        changed['applicabilityNote'] = 'Different explicitly reviewed scope.'
        second = plan(changed, {'fixture': raw}, now=NOW, previous_build=first['buildKey'])
        self.assertNotEqual(second['applicability'], first['applicability'])
        self.assertNotEqual(second['buildKey'], first['buildKey'])
        self.assertEqual(second['replay'], 'NEW_BINDING')

    def test_F2_source_asset_claim_invalidates_binding_replay(self):
        binding, raw = contract()
        first = plan(binding, {'fixture': raw}, now=NOW)
        changed = deepcopy(binding)
        changed['sourceAsset']['sha256'] = 'b' * 64
        second = plan(changed, {'fixture': raw}, now=NOW, previous_build=first['buildKey'])
        self.assertNotEqual(second['sourceAssetClaim'], first['sourceAssetClaim'])
        self.assertNotEqual(second['buildKey'], first['buildKey'])
        self.assertEqual(second['replay'], 'NEW_BINDING')

    def test_F2_reviewed_cache_meaning_invalidates_binding_replay(self):
        binding, raw = contract()
        first = plan(binding, {'fixture': raw}, now=NOW)
        changed = deepcopy(binding)
        changed['cache']['meaning'] = 'Different explicitly reviewed event meaning.'
        second = plan(changed, {'fixture': raw}, now=NOW, previous_build=first['buildKey'])
        self.assertNotEqual(second['cache']['originalAcquisitionMeaning'], first['cache']['originalAcquisitionMeaning'])
        self.assertNotEqual(second['buildKey'], first['buildKey'])

    def test_F2_clock_age_only_stays_noop(self):
        binding, raw = contract()
        first = plan(binding, {'fixture': raw}, now=NOW)
        second = plan(binding, {'fixture': raw}, now='2026-10-19T00:00:00Z',
                      previous_build=first['buildKey'])
        self.assertEqual(second['buildKey'], first['buildKey'])
        self.assertEqual(second['replay'], 'NO_OP')
        self.assertNotEqual(second['cache']['acquisitionAgeSeconds'], first['cache']['acquisitionAgeSeconds'])


if __name__ == '__main__':
    unittest.main()
