import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.bv_lu_sh import diagnose, diagnose_all, publish_report
from offmenu.refresh.core import canonical, sha

NOW = '2026-10-18T00:00:00Z'


class PortfolioBindingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.raw = canonical({'unit': 'authored weight per thousand',
                              'acquired': '2026-10-01T00:00:00Z', 'bodySha256': '0' * 64})
        (self.root / 'metadata.json').write_bytes(self.raw)
        self.spec = dict(
            country='LU', state='retained', sourceId='fixture-lu', releaseId='sha256:' + '0' * 64,
            holds=[], applicability={'prices-baskets': 'authored-fixture-only'},
            unknowns={'denominator': None, 'admission': None}, references=[],
            evidence=[dict(name='evidence.json', path='metadata.json', bytes=len(self.raw),
                           sha256=sha(self.raw), role='metadata')],
            acquisition=dict(input='evidence.json', selector='/acquired'),
            releasePin=dict(input='evidence.json', selector='/bodySha256'),
            fields={'unit': dict(input='evidence.json', selector='/unit',
                                 literal='authored weight per thousand')})

    def run_plan(self, spec=None, now=NOW):
        return diagnose('LU', self.spec if spec is None else spec, self.root, as_of=now)

    def test_valid_authored_metadata_uses_shared_origin_validator(self):
        report = self.run_plan()
        self.assertEqual(report['status'], 'metadata-ready')
        self.assertEqual(report['errors'], [])
        origin = report['metadataBinding']['provenance']['fieldOrigins']['/data/unit']
        self.assertEqual(origin['sourceRecordId'], '/unit')
        self.assertEqual(origin['inputSha256'], sha(self.raw))
        self.assertEqual(report['cache']['originalAcquiredAt'], '2026-10-01T00:00:00Z')
        self.assertEqual(report['cache']['metadataValidatedAt'], NOW)
        self.assertIsNone(report['unknowns']['denominator'])
        self.assertEqual((report['acceptedRecords'], report['bodyReads']), (0, 0))

    def test_missing_file_does_not_become_valid(self):
        (self.root / 'metadata.json').unlink()
        self.assertEqual(self.run_plan()['status'], 'missing')

    def test_explicit_missing_country(self):
        s = dict(country='BV', state='missing', holds=['no-source'],
                 applicability={}, references=[], unknowns={'release': None})
        report = diagnose('BV', s, self.root, as_of=NOW)
        self.assertEqual(report['errors'], ['binding-source-input-missing'])

    def test_hold_not_lifted_by_valid_metadata(self):
        self.spec['holds'] = ['source-reuse-held']
        report = self.run_plan()
        self.assertEqual(report['status'], 'held')
        self.assertIn('binding-source-held', report['errors'])
        self.assertEqual(report['metadataBinding']['data']['unit'],
                         'authored weight per thousand')
        self.assertEqual(report['cache']['automaticDownloads'], 0)

    def test_pin_corruption_and_selector_mismatch(self):
        (self.root / 'metadata.json').write_bytes(self.raw + b' ')
        self.assertEqual(self.run_plan()['status'], 'malformed')
        (self.root / 'metadata.json').write_bytes(self.raw)
        self.spec['fields']['unit']['selector'] = '/absent'
        self.assertEqual(self.run_plan()['status'], 'malformed')

    def test_malformed_json_duplicate_key_isolated(self):
        raw = b'{"unit":1,"unit":2}\n'
        (self.root / 'metadata.json').write_bytes(raw)
        self.spec['evidence'][0].update(bytes=len(raw), sha256=sha(raw))
        report = diagnose_all({'LU': self.spec}, self.root, as_of=NOW)
        self.assertEqual([x['country'] for x in report['reports']], ['BV', 'LU', 'SH'])
        self.assertEqual([x['status'] for x in report['reports']],
                         ['malformed', 'malformed', 'malformed'])
        self.assertNotIn(str(self.root), json.dumps(report))

    def test_acquisition_observations_do_not_claim_planner_eligibility(self):
        with patch('socket.socket', side_effect=AssertionError('network prohibited')):
            recent = self.run_plan(now='2026-10-02T00:00:00Z')
            old = self.run_plan(now='2026-12-01T00:00:00Z')
        for report in (recent, old):
            self.assertEqual(report['status'], 'metadata-ready')
            self.assertEqual(report['cache']['planningCapability'],
                             'unsupported-shared-planner-absent')
            self.assertIsNone(report['cache']['eligibility'])
            self.assertEqual(report['cache']['action'], 'unknown-no-download')
            self.assertEqual(report['cache']['automaticDownloads'], 0)
            self.assertFalse(report['cache']['validationResetsAcquisitionAge'])
        self.assertGreater(old['cache']['acquisitionAgeDays'], recent['cache']['acquisitionAgeDays'])
        self.assertEqual(recent['bindingFingerprint'], old['bindingFingerprint'])

    def test_fifo_replacement_before_open_rejected_and_peer_progresses(self):
        peer = copy.deepcopy(self.spec)
        peer['country'] = 'SH'
        peer['evidence'][0]['path'] = 'peer.json'
        (self.root / 'peer.json').write_bytes(self.raw)
        original_open = os.open
        replaced = []
        def replace(path, flags, *args, **kwargs):
            if Path(path) == self.root / 'metadata.json':
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                Path(path).unlink()
                os.mkfifo(path)
                replaced.append(True)
            return original_open(path, flags, *args, **kwargs)
        with patch('offmenu.refresh.bv_lu_sh.os.open', replace):
            report = diagnose_all({'LU': self.spec, 'SH': peer}, self.root, as_of=NOW)
        self.assertEqual(replaced, [True])
        self.assertEqual([x['status'] for x in report['reports']],
                         ['malformed', 'malformed', 'metadata-ready'])

    def test_growth_read_is_bounded_to_pin_plus_one(self):
        original_read = os.read
        requested = []
        def grow(fd, size):
            if not requested:
                with (self.root / 'metadata.json').open('ab') as stream:
                    stream.write(b'x' * (1024 * 1024))
            requested.append(size)
            return original_read(fd, size)
        with patch('offmenu.refresh.bv_lu_sh.os.read', grow):
            self.assertEqual(self.run_plan()['status'], 'malformed')
        self.assertLessEqual(sum(requested), len(self.raw) + 1)

    def test_future_naive_and_bad_clock_fail_closed(self):
        for now in ('2026-09-01T00:00:00Z', '2026-10-18', 'invalid'):
            with self.subTest(now=now):
                self.assertEqual(self.run_plan(now=now)['status'], 'malformed')

    def test_metadata_only_and_path_contract(self):
        for changes in (dict(role='body'), dict(path='../raw.csv'),
                        dict(path='/tmp/private.json'), dict(bytes=999999)):
            spec = copy.deepcopy(self.spec)
            spec['evidence'][0].update(changes)
            self.assertEqual(self.run_plan(spec)['status'], 'malformed')
        original = self.root / 'body.csv'
        original.write_text('must never open')
        spec = copy.deepcopy(self.spec)
        spec['references'] = [{'path': str(original), 'sha256': '0' * 64}]
        read_bytes = Path.read_bytes
        touched = []
        def guarded_read(path):
            touched.append(path)
            if path == original:
                raise AssertionError('body read prohibited')
            return read_bytes(path)
        with patch.object(Path, 'read_bytes', guarded_read):
            self.assertEqual(self.run_plan(spec)['status'], 'metadata-ready')
        self.assertNotIn(original, touched)

    def test_release_pin_mismatch(self):
        self.spec['releaseId'] = 'sha256:' + '1' * 64
        self.assertEqual(self.run_plan()['status'], 'malformed')

    def test_one_malformed_binding_does_not_stop_peer(self):
        peer = copy.deepcopy(self.spec)
        peer['country'] = 'SH'
        peer['evidence'][0]['path'] = 'peer.json'
        (self.root / 'peer.json').write_bytes(self.raw)
        self.spec['evidence'][0]['sha256'] = 'f' * 64
        result = diagnose_all({'LU': self.spec, 'SH': peer}, self.root, as_of=NOW)
        self.assertEqual([x['status'] for x in result['reports']],
                         ['malformed', 'malformed', 'metadata-ready'])

    def test_symlink_and_nonfinite_rejected(self):
        (self.root / 'link.json').symlink_to(self.root / 'metadata.json')
        self.spec['evidence'][0]['path'] = 'link.json'
        self.assertEqual(self.run_plan()['status'], 'malformed')
        self.spec['evidence'][0]['path'] = 'metadata.json'
        raw = b'{"unit": NaN, "acquired":"2026-10-01T00:00:00Z"}'
        (self.root / 'metadata.json').write_bytes(raw)
        self.spec['evidence'][0].update(bytes=len(raw), sha256=sha(raw))
        self.assertEqual(self.run_plan()['status'], 'malformed')

    def test_actual_noop_preserves_output_inode_and_mtime(self):
        target = self.root / 'out' / 'plan.json'
        report = self.run_plan()
        self.assertEqual(publish_report(target, report), 'written')
        before = target.stat()
        self.assertEqual(publish_report(target, report), 'verified-no-op')
        after = target.stat()
        self.assertEqual((before.st_ino, before.st_mtime_ns), (after.st_ino, after.st_mtime_ns))
        self.assertEqual(target.read_bytes(), canonical(report))


if __name__ == '__main__':
    unittest.main()
