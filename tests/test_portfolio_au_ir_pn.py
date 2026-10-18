"""Authored metadata and one synthetic record only; never read country bodies."""
import copy
from datetime import datetime, timezone
import hashlib
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh.acceptance import (Asset, SourceContract, canonical,
                                       fingerprint, ids_digest, qualify)
from offmenu.refresh.core import RefreshError, strict_json
from offmenu.refresh.portfolio_au_ir_pn import (
    _read_metadata, catalogue, inspect_batch, inspect_metadata, main, origin_errors)

NOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        # This trusted test spec is authored code, not an override loaded by CLI.
        self.spec = {'bindingId': 'authored-au-weight', 'country': 'AU',
                     'sourceId': 'authored-weight', 'releaseId': 'fixture-v1',
                     'dataType': 'statistical-weighting', 'inputs': {'input.csv': 'a' * 64},
                     'metadataEvidence': {'sha256': 'b' * 64}, 'holds': [],
                     'originalAcquiredAt': '2026-10-01T00:00:00Z'}
        self.env = {k: self.spec[k] for k in ('country', 'sourceId', 'releaseId', 'dataType', 'inputs')}
        self.env.update(evidenceSha256='b' * 64,
                        originalAcquiredAt=self.spec['originalAcquiredAt'],
                        validatedAt='2026-10-17T00:00:00Z')

    def assess(self, env=None, **kwargs):
        return inspect_metadata(self.spec, self.env if env is None else env, now=NOW, **kwargs)

    def test_valid_is_deterministic_metadata_only(self):
        with patch('builtins.open', side_effect=AssertionError('no body IO')):
            a = self.assess()
            self.assertEqual(a, self.assess())
        self.assertEqual(a['stage']['status'], 'succeeded')
        self.assertFalse(a['inputBytesVerified'])
        self.assertFalse(a['countryAccepted'])
        self.assertEqual(a['networkRequests'], 0)

    def test_noop_key_ignores_validation_age_not_acquisition(self):
        a = self.assess()
        self.env['validatedAt'] = '2026-10-18T00:00:00Z'
        b = self.assess(previous_key=a['bindingKey'])
        self.assertEqual(b['stage']['status'], 'reused')
        self.assertEqual(b['acquisitionAgeDays'], 17)
        self.env['originalAcquiredAt'] = self.env['validatedAt']
        self.assertIn('acquisition-evidence-mismatch', self.assess()['diagnostics'])

    def test_missing_is_typed(self):
        a = inspect_metadata(self.spec, None, now=NOW)
        self.assertEqual(a['stage']['code'], 'source-input-missing')
        self.assertEqual(a['stage']['status'], 'unsupported')

    def test_held_cannot_be_released_by_envelope(self):
        self.spec['holds'] = ['source-rights-held']
        a = self.assess()
        self.assertEqual(a['stage']['status'], 'held')
        self.env['holds'] = []
        self.assertEqual(self.assess()['stage']['status'], 'failed')

    def test_malformed_and_identity_diagnostics(self):
        self.assertEqual(self.assess([])['stage']['code'], 'metadata-malformed')
        self.env['sourceId'] = 'foreign'
        self.env['inputs'] = {'changed.csv': 'c' * 64}
        a = self.assess()
        self.assertIn('binding-identity-mismatch', a['diagnostics'])
        self.assertIn('input-declaration-mismatch', a['diagnostics'])

    def test_exact_thirty_day_boundary_stale_never_downloads(self):
        self.spec['originalAcquiredAt'] = '2026-09-18T00:00:00Z'
        self.env['originalAcquiredAt'] = self.spec['originalAcquiredAt']
        a = self.assess()
        self.assertEqual(a['stage']['code'], 'stale-input-review-required')
        self.assertEqual(a['cacheDecision'], 'review-required-no-download')
        self.assertEqual(a['networkRequests'], 0)

    def test_future_and_naive_clock_fail(self):
        self.env['validatedAt'] = '2026-10-19T00:00:00Z'
        self.assertIn('metadata-clock-invalid', self.assess()['diagnostics'])
        a = inspect_metadata(self.spec, self.env, now=datetime(2026, 10, 18))
        self.assertEqual(a['stage']['status'], 'failed')

    def test_unknown_acquisition_never_made_fresh(self):
        self.spec['originalAcquiredAt'] = None
        self.spec['holds'] = ['original-acquisition-evidence-missing']
        self.env['originalAcquiredAt'] = None
        a = self.assess()
        self.assertEqual(a['stage']['status'], 'held')
        self.assertIsNone(a['acquisitionAgeDays'])
        self.assertEqual(a['cacheDecision'], 'unknown-no-download')
        self.assertEqual(a['plannerCapability'], 'metadata-intent-only-generic-planner-unsupported')

    def test_batch_isolates_missing_malformed_and_held(self):
        profiles = catalogue()['profiles']
        p = profiles[1]
        env = {k: p[k] for k in ('sourceId', 'releaseId', 'country', 'dataType', 'inputs', 'originalAcquiredAt')}
        env.update(validatedAt='2026-10-17T00:00:00Z', evidenceSha256=p['metadataEvidence']['sha256'])
        rows = inspect_batch({p['bindingId']: env, profiles[0]['bindingId']: []}, now=NOW)
        self.assertEqual(len(rows), 6)
        self.assertEqual([r['stage']['status'] for r in rows[:3]], ['failed', 'held', 'unsupported'])
        self.assertTrue(all(r['networkRequests'] == 0 for r in rows))
        with self.assertRaises(RefreshError):
            inspect_batch({'unassigned-country': {}}, now=NOW)

    def test_no_real_profile_admission_or_unknown_unit_inference(self):
        for p in catalogue()['profiles']:
            self.assertFalse(p['productionAdmission'])
            self.assertTrue(p['holds'])
        self.assertEqual(catalogue()['profiles'][0]['releaseId'], '3')

    def test_shared_origin_validator_preserves_null_and_unknown(self):
        row = {'data': {'value': None}, 'provenance': {'sourceId': 's', 'releaseId': 'r',
               'fieldOrigins': {'/data/value': {'kind': 'source', 'sourceId': 's', 'releaseId': 'r',
                'inputPath': 'input.csv', 'inputSha256': 'a'*64, 'sourceRecordId': 'authored-row',
                'sourceField': 'value'}}}}
        before = copy.deepcopy(row)
        self.assertEqual(origin_errors(row, {'input.csv': 'a'*64}), [])
        self.assertEqual(row, before)
        row['provenance']['fieldOrigins'] = {}
        self.assertIn('field-origin-inventory-mismatch', origin_errors(row, {'input.csv': 'a'*64}))

    def test_shared_qualification_with_authored_fixture_not_production(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bundle = root/'bundle'; bundle.mkdir()
            assets = []
            for name, raw in [('input.csv', b'id,value,unit\na,0,%\n'), ('rights.json', b'authored fixture rights'), ('scope.json', b'authored single row')]:
                (bundle/name).write_bytes(raw)
                assets.append(Asset(name, len(raw), hashlib.sha256(raw).hexdigest()))
            row = {'id': 'authored-a', 'kind': 'authoredWeight', 'schemaVersion': '1',
                   'data': {'value': 0, 'unit': '%'},
                   'provenance': {'sourceId': 'authored-weight', 'releaseId': 'fixture-v1',
                                  'fetchedAt': '2026-10-01T00:00:00Z'}}
            row['provenance']['fieldOrigins'] = {f'/data/{key}': {
                'kind': 'source', 'sourceId': 'authored-weight', 'releaseId': 'fixture-v1',
                'inputPath': 'input.csv', 'inputSha256': assets[0].sha256,
                'sourceRecordId': 'a', 'sourceField': key} for key in row['data']}
            schemas = {'authoredWeight': {'type': 'object', 'required': ['id', 'data', 'provenance']}}
            contract = SourceContract('authored-weight', 'fixture-v1', 'authored-only',
                '2026-10-01T00:00:00Z', tuple(assets), 1, ids_digest(['authored-a']),
                schemas, fingerprint(schemas), lambda r: origin_errors(r, {'input.csv': assets[0].sha256}),
                'c'*64, assets[1], assets[2], frozenset(('retain','parse','transform')), fixture=True)
            raw = canonical([row])+b'\n'; candidate = root/'candidate.jsonl';candidate.write_bytes(raw)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'candidateSha256': hashlib.sha256(raw).hexdigest(), 'candidateBytes': len(raw),
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets]}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result['errors'])
            self.assertTrue(result['fixture'])

    def test_cli_rejects_duplicate_keys_and_oversized_metadata(self):
        with self.assertRaises(RefreshError):
            strict_json(b'{"x":1,"x":2}')
        with tempfile.NamedTemporaryFile() as f:
            f.write(b'x'*(256*1024+1));f.flush()
            with patch('builtins.print'):
                self.assertEqual(main(['--metadata', f.name, '--now', '2026-10-18T00:00:00Z']), 2)


class MetadataEntrypointTests(unittest.TestCase):
    def test_regular_cli_and_input_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'metadata.json'; p.write_bytes(b'{}')
            before = p.stat(); stream = io.StringIO()
            with contextlib.redirect_stdout(stream):
                code = main(['--metadata', str(p), '--now', '2026-10-18T00:00:00Z'])
            result = json.loads(stream.getvalue())
            self.assertEqual(code, 2)  # Missing bindings, never a read failure.
            self.assertEqual(len(result['sources']), 6)
            self.assertEqual(p.read_bytes(), b'{}')
            self.assertEqual((p.stat().st_ino, p.stat().st_mtime_ns),
                             (before.st_ino, before.st_mtime_ns))

    def test_special_files_rejected_before_open(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fifo = root/'fifo.json'; os.mkfifo(fifo)
            p = root/'regular.json'; p.write_bytes(b'{}')
            link = root/'link.json'; link.symlink_to(p)
            for path in (fifo, root, link):
                with self.subTest(path=path.name), patch(
                        'offmenu.refresh.portfolio_au_ir_pn.os.open',
                        side_effect=AssertionError('must not open a nonregular input')):
                    stream = io.StringIO()
                    with contextlib.redirect_stdout(stream):
                        code = main(['--metadata', str(path), '--now', '2026-10-18T00:00:00Z'])
                    self.assertEqual(code, 2)
                    self.assertIn('errorCode', json.loads(stream.getvalue()))

    def test_fifo_swap_uses_nonblocking_fd_and_never_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'metadata.json'; p.write_bytes(b'{}')
            real_open = os.open
            def swap(path, flags):
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                p.unlink(); os.mkfifo(p)
                return real_open(path, flags)
            with patch('offmenu.refresh.portfolio_au_ir_pn.os.open', side_effect=swap), patch(
                    'offmenu.refresh.portfolio_au_ir_pn.os.read',
                    side_effect=AssertionError('must not read the swapped FIFO')):
                with self.assertRaisesRegex(RefreshError, '^metadata-not-regular$'):
                    _read_metadata(p)

    def test_replacement_and_mutation_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory)/'metadata.json'; p.write_bytes(b'{}')
            real_open = os.open
            def replace_before_open(path, flags):
                replacement = p.with_suffix('.replacement'); replacement.write_bytes(b'{}')
                os.replace(replacement, p)
                return real_open(path, flags)
            with patch('offmenu.refresh.portfolio_au_ir_pn.os.open', side_effect=replace_before_open):
                with self.assertRaisesRegex(RefreshError, '^metadata-changed-during-read$'):
                    _read_metadata(p)
            real_read = os.read
            changed = []
            def mutate_after_read(fd, size):
                raw = real_read(fd, size)
                if not changed:
                    p.write_bytes(b'changed'); changed.append(True)
                return raw
            with patch('offmenu.refresh.portfolio_au_ir_pn.os.read', side_effect=mutate_after_read):
                with self.assertRaisesRegex(RefreshError, '^metadata-changed-during-read$'):
                    _read_metadata(p)


if __name__ == '__main__':
    unittest.main()
