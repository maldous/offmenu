"""Authored metadata fixtures only; no actual source-body or network tests."""
from dataclasses import asdict, replace
from datetime import timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.core import canonical, sha, timestamp
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.global_run import Limits, StageContext
from offmenu.refresh.portfolio13_bindings import BINDINGS, SourceBinding, bind_metadata, run, verification_handler

FIXTURE = Path(__file__).parent / 'fixtures' / 'portfolio13_metadata.json'
NOW = timestamp('2026-10-20T00:00:00Z')


class Portfolio13Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'input'
        self.root.mkdir()
        self.raw = FIXTURE.read_bytes()
        (self.root / 'receipt.json').write_bytes(self.raw)
        self.binding = SourceBinding('authored-mr', 'MR', ('prices/baskets',),
            'authored-metadata-2026-10-01', 'receipt.json', len(self.raw), sha(self.raw), '/release',
            (('label', '/label'), ('unit', '/unit'), ('headers', '/headers')),
            ('native-unit-unresolved',), (), '/originalAcquiredAt', True)

    def changed(self, obj=None, raw=None):
        raw = canonical(obj) if raw is None else raw
        (self.root / 'receipt.json').write_bytes(raw)
        return replace(self.binding, metadata_bytes=len(raw), metadata_sha256=sha(raw))

    def test_valid_null_and_array_origin_inventory(self):
        report, artifact = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['outcome'], 'valid')
        self.assertEqual(report['cache']['decision'], 'reuse')
        self.assertEqual(artifact['data']['unit'], None)
        self.assertEqual(artifact['provenance']['fieldOrigins']['/data/headers/1']['sourceField'], '/headers/1')
        self.assertEqual(field_origin_errors(artifact, {'receipt.json': sha(self.raw)}), [])
        self.assertFalse(artifact['sourceBodyOperationPermitted'])
        self.assertFalse(artifact['goldAdmission'])
        self.assertEqual(artifact['scope'], 'authored-fixture')

    def test_replay_is_noop_and_validation_does_not_reset_acquisition(self):
        out = Path(self.tmp.name) / 'output'
        first = run(self.root, now=NOW, output=out, bindings=(self.binding,))['sources'][0]
        p = out / 'authored-mr.json'
        old_bytes, old_mtime = p.read_bytes(), p.stat().st_mtime_ns
        second = run(self.root, now=NOW + timedelta(days=1), output=out,
                     bindings=(self.binding,))['sources'][0]
        self.assertEqual((first['publication'], second['publication']), ('created', 'no-op'))
        self.assertEqual(first['bindingSha256'], second['bindingSha256'])
        self.assertEqual((p.read_bytes(), p.stat().st_mtime_ns), (old_bytes, old_mtime))
        self.assertEqual(first['cache']['originalAcquiredAt'], second['cache']['originalAcquiredAt'])
        self.assertNotEqual(first['cache']['validatedAt'], second['cache']['validatedAt'])

    def test_minimum_30_days_boundary_and_no_online_path(self):
        start = timestamp('2026-10-01T00:00:00Z')
        with patch('socket.create_connection', side_effect=AssertionError('network forbidden')):
            fresh, _ = bind_metadata(self.binding, self.root, now=start + timedelta(days=30, seconds=-1))
            stale, artifact = bind_metadata(self.binding, self.root, now=start + timedelta(days=30))
        self.assertEqual(fresh['outcome'], 'valid')
        self.assertEqual(stale['outcome'], 'stale-input')
        self.assertEqual(stale['cache']['originalAcquiredAt'], fresh['cache']['originalAcquiredAt'])
        self.assertEqual(stale['cache']['networkRequests'], 0)
        self.assertIsNone(artifact)

    def test_missing_input_field_and_acquisition_are_distinct(self):
        (self.root / 'receipt.json').unlink()
        report, _ = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['diagnostics'], ['metadata-input-missing'])
        b = self.changed({'country': 'MR', 'release': self.binding.release_id})
        report, _ = bind_metadata(b, self.root, now=NOW)
        self.assertIn('metadata-field-missing', report['diagnostics'])
        (self.root / 'receipt.json').write_bytes(self.raw)
        report, _ = bind_metadata(replace(self.binding, acquired_pointer=None), self.root, now=NOW)
        self.assertEqual(report['outcome'], 'missing')
        self.assertIn('metadata-acquisition-time-missing', report['diagnostics'])

    def test_holds_cannot_be_cleared_by_receipt_claims(self):
        obj = json.loads(self.raw)
        obj.update(holds=[], rights='approved', admission=True)
        b = replace(self.changed(obj), holds=('source-use-not-established',))
        out = Path(self.tmp.name) / 'held-output'
        report = run(self.root, now=NOW, output=out, bindings=(b,))['sources'][0]
        self.assertEqual(report['outcome'], 'held')
        self.assertEqual(report['stage']['status'], 'held')
        self.assertFalse(out.exists())

    def test_pin_tamper_duplicate_keys_and_nonfinite_fail_closed(self):
        (self.root / 'receipt.json').write_bytes(self.raw + b' ')
        report, artifact = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['outcome'], 'malformed')
        self.assertIsNone(artifact)
        for raw in [b'{"country":"MR","country":"MS"}', b'{"value":NaN}', b'[]', b'{']:
            with self.subTest(raw=raw):
                report, artifact = bind_metadata(self.changed(raw=raw), self.root, now=NOW)
                self.assertEqual(report['outcome'], 'malformed')
                self.assertIsNone(artifact)

    def test_release_or_country_drift_refused(self):
        for key, value in [('country', 'MS'), ('release', 'different')]:
            obj = json.loads(self.raw)
            obj[key] = value
            report, _ = bind_metadata(self.changed(obj), self.root, now=NOW)
            self.assertIn('metadata-source-release-mismatch', report['diagnostics'])

    def test_malformed_and_held_peers_do_not_hide_valid_peer(self):
        missing = replace(self.binding, source_id='missing-mr', metadata_path='missing.json')
        held = replace(self.binding, source_id='held-mr', holds=('403-no-retry',))
        invalid = replace(self.binding, source_id='invalid-mr', metadata_path='../receipt.json')
        result = run(self.root, now=NOW, bindings=(missing, held, invalid, self.binding))
        self.assertEqual([r['outcome'] for r in result['sources']], ['missing', 'held', 'malformed', 'valid'])
        self.assertEqual(result['sourceBodyReads'], 0)
        self.assertEqual(result['goldAdmissions'], 0)

    def test_original_body_values_are_never_dereferenced(self):
        import io
        real_open = io.open
        def guarded(path, *a, **kw):
            if str(path).endswith('.csv'):
                self.fail('original body opened')
            return real_open(path, *a, **kw)
        with patch('io.open', side_effect=guarded):
            report, _ = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['outcome'], 'valid')

    def test_symlink_input_and_output_conflict_fail_closed(self):
        (self.root / 'alias.json').symlink_to(self.root / 'receipt.json')
        report, _ = bind_metadata(replace(self.binding, metadata_path='alias.json'), self.root, now=NOW)
        self.assertEqual(report['outcome'], 'malformed')
        out = Path(self.tmp.name) / 'out'
        out.mkdir()
        p = out / 'authored-mr.json'
        p.write_bytes(b'old output')
        report = run(self.root, now=NOW, output=out, bindings=(self.binding,))['sources'][0]
        self.assertEqual(report['outcome'], 'malformed')
        self.assertEqual(p.read_bytes(), b'old output')

    def test_future_acquisition_not_hidden_by_validation_age(self):
        obj = json.loads(self.raw)
        obj['originalAcquiredAt'] = '2026-11-01T00:00:00Z'
        report, _ = bind_metadata(self.changed(obj), self.root, now=NOW)
        self.assertIn('metadata-acquisition-in-future', report['diagnostics'])

    def test_real_config_has_only_metadata_and_explicit_holds(self):
        self.assertEqual({b.country for b in BINDINGS}, {'MQ', 'MR', 'MS', 'MT'})
        self.assertTrue(all(b.holds and not b.fixture and b.acquired_pointer is None for b in BINDINGS))
        self.assertTrue(all(b.metadata_path.endswith('/receipt.json') for b in BINDINGS))

    def test_shared_stage_context_interface_never_claims_data_records(self):
        verify = verification_handler(self.binding, self.root, clock=lambda: NOW)
        context = StageContext(self.binding.source_id, 'verify', Limits(), None, False, ())
        self.assertEqual(verify(context).receipt()['observedCount'], 0)
        self.assertEqual(verify(replace(context, stage='parse')).code, 'metadata-stage-context-mismatch')
        self.assertEqual(verify(replace(context, source_id='other')).status, 'failed')

    def bounded_run(self, bindings, output=None):
        code = '''import json,sys
from pathlib import Path
from offmenu.refresh.portfolio13_bindings import SourceBinding,run
from offmenu.refresh.core import canonical,timestamp
bindings=tuple(SourceBinding(**b) for b in json.loads(sys.argv[1]))
print(canonical(run(Path(sys.argv[2]),now=timestamp('2026-10-20T00:00:00Z'),
 output=Path(sys.argv[3]) if sys.argv[3] else None,bindings=bindings)).decode())
'''
        child = subprocess.run([sys.executable, '-c', code,
            json.dumps([asdict(b) for b in bindings]), str(self.root), str(output or '')],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True,
            timeout=3, env={**os.environ, 'PYTHONDONTWRITEBYTECODE': '1'})
        self.assertEqual(child.returncode, 0, child.stderr)
        return json.loads(child.stdout)['sources']

    def test_fifo_metadata_refusal_keeps_valid_peer_progressing(self):
        os.mkfifo(self.root / 'fifo.json')
        bad = replace(self.binding, source_id='fifo-mr', metadata_path='fifo.json')
        reports = self.bounded_run((bad, self.binding))
        self.assertEqual(reports[0]['outcome'], 'malformed')
        self.assertIn('metadata-input-nonregular', reports[0]['diagnostics'])
        self.assertEqual(reports[1]['outcome'], 'valid')

    def test_fifo_replay_refusal_keeps_valid_peer_progressing(self):
        out = Path(self.tmp.name) / 'output'
        out.mkdir()
        bad = replace(self.binding, source_id='fifo-mr')
        os.mkfifo(out / 'fifo-mr.json')
        reports = self.bounded_run((bad, self.binding), out)
        self.assertEqual(reports[0]['outcome'], 'malformed')
        self.assertEqual(reports[0]['diagnostics'], ['metadata-output-conflict'])
        self.assertEqual(reports[1]['publication'], 'created')
        self.assertTrue((out / 'fifo-mr.json').is_fifo())

    def test_open_descriptor_replacement_is_refused_without_reopening(self):
        real_read = os.read
        replaced = False
        def replace_after_open(fd, size):
            nonlocal replaced
            if not replaced:
                replaced = True
                (self.root / 'receipt.json').unlink()
                os.mkfifo(self.root / 'receipt.json')
            return real_read(fd, size)
        with patch('offmenu.refresh.portfolio13_bindings.os.read', side_effect=replace_after_open):
            report, artifact = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['diagnostics'], ['metadata-input-changed'])
        self.assertIsNone(artifact)

    def test_symlink_replacement_at_descriptor_open_is_refused(self):
        real_open = os.open
        target = self.root / 'receipt.json'
        other = Path(self.tmp.name) / 'other-authored.json'
        other.write_bytes(self.raw)
        def replace_before_open(path, flags, *args, **kwargs):
            if path == 'receipt.json' and kwargs.get('dir_fd') is not None:
                target.unlink()
                target.symlink_to(other)
            return real_open(path, flags, *args, **kwargs)
        with patch('offmenu.refresh.portfolio13_bindings.os.open', side_effect=replace_before_open):
            report, artifact = bind_metadata(self.binding, self.root, now=NOW)
        self.assertEqual(report['outcome'], 'malformed')
        self.assertIsNone(artifact)


if __name__ == '__main__':
    unittest.main()
