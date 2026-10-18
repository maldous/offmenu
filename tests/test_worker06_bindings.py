"""Authored metadata only; no retained payloads or publisher requests."""
import copy
import contextlib
import io
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import worker06_bindings as w
from offmenu.refresh.acceptance import (Asset, SourceContract, accept, canonical,
                                       fingerprint, ids_digest)
from offmenu.refresh.field_provenance import field_origin_errors

NOW = '2026-10-18T00:00:00Z'


def fixture():
    raw = b'{"sources":[{"release":"authored-r1","url":"https://example.invalid/metadata","role":"authored"}]}\n'
    b = {'id': 'authored-me-1', 'country': 'ME', 'sourceId': 'authored-fixture',
         'releaseId': 'authored-r1', 'metadataAsset': {
             'logicalPath': 'metadata.json', 'path': '/unused/metadata.json',
             'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()},
         'recordSelector': '/sources/0', 'originalAcquiredAt': '2026-10-01T00:00:00Z',
         'integrityValidatedAt': '2026-10-17T00:00:00Z', 'blockers': [],
         'fields': {'releaseLabel': {'selector': '/sources/0/release', 'expected': 'authored-r1'},
                    'nativeUnit': {'selector': None, 'expected': None},
                    'nativeBasis': {'selector': None, 'expected': None}}}
    return b, raw


class Worker06BindingTests(unittest.TestCase):
    def test_valid_metadata_unknowns_and_exact_shared_origins(self):
        b, raw = fixture()
        before = copy.deepcopy(b)
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            r = w.assess(b, raw, now=NOW)
        self.assertEqual(r['status'], 'valid')
        self.assertEqual(r['candidate']['data']['nativeUnit'], None)
        self.assertEqual(field_origin_errors(r['candidate'], {'metadata.json': b['metadataAsset']['sha256']},
                                            policy_pins=(w.POLICY,)), [])
        self.assertFalse(r['payloadProcessingAuthorized'])
        self.assertEqual((r['acceptedRecords'], r['networkRequests']), (0, 0))
        self.assertEqual(b, before)

    def test_missing_held_malformed_and_stale_are_distinct(self):
        b, raw = fixture()
        self.assertEqual(w.assess(b, None, now=NOW)['status'], 'missing')
        held = copy.deepcopy(b)
        held['blockers'] = [{'code': 'explicit-source-hold', 'owner': 'rights-owner'}]
        self.assertEqual(w.assess(held, raw, now=NOW)['status'], 'held')
        self.assertEqual(w.assess(b, b'{broken', now=NOW)['status'], 'malformed')
        self.assertEqual(w.assess(b, raw + b' ', now=NOW)['status'], 'stale')
        self.assertEqual(w.assess(b, b'{"a":1,"a":2}', now=NOW)['status'], 'malformed')
        self.assertEqual(w.assess(b, b'{"a":NaN}', now=NOW)['status'], 'malformed')

    def test_selector_mismatch_isolated_from_other_binding(self):
        b, raw = fixture()
        bad = copy.deepcopy(b)
        bad['id'] = 'bad'
        bad['fields']['releaseLabel']['selector'] = '/sources/99/release'
        r = w.assess_all({'bindings': [bad, b]}, {'bad': raw, b['id']: raw}, now=NOW)
        self.assertEqual([x['status'] for x in r], ['malformed', 'valid'])
        bad['fields']['releaseLabel']['selector'] = '/sources/0/release'
        bad['fields']['releaseLabel']['expected'] = 'foreign-release'
        self.assertIn('metadata-selector-value-mismatch', w.assess(bad, raw, now=NOW)['diagnostics'])

    def test_timestamp_observations_never_invent_cache_eligibility(self):
        b, raw = fixture()
        b['originalAcquiredAt'] = '2026-09-18T00:00:01Z'
        before = w.assess(b, raw, now=NOW)
        self.assertEqual(before['acquisitionAgeSeconds'], 30 * 86400 - 1)
        b['originalAcquiredAt'] = '2026-09-18T00:00:00Z'
        r = w.assess(b, raw, now=NOW)
        self.assertEqual(r['acquisitionAgeSeconds'], 30 * 86400)
        self.assertEqual(r['status'], 'valid')
        for row in [before, r]:
            self.assertEqual(row['cacheDecision'], 'unsupported-real-source-cache-planner')
            self.assertEqual(row['freshness'], 'unknown')
            self.assertEqual(row['diagnostics'], [])
            self.assertEqual(row['minimumReuseSecondsRequired'], 30 * 86400)
        b['integrityValidatedAt'] = NOW  # A new hash check never refreshes acquisition age.
        validated = w.assess(b, raw, now=NOW)
        self.assertEqual(validated['acquisitionAgeSeconds'], 30 * 86400)
        self.assertEqual(validated['validationAgeSeconds'], 0)
        b['originalAcquiredAt'] = None
        unknown = w.assess(b, raw, now=NOW)
        self.assertIsNone(unknown['acquisitionAgeSeconds'])
        self.assertEqual(unknown['freshness'], 'unknown')
        with patch('offmenu.refresh.core.cache_policy', side_effect=AssertionError('pilot planner')), \
             patch('offmenu.refresh.policy.plan_fixture', side_effect=AssertionError('fixture spoof')), \
             patch('offmenu.refresh.acquisition.CachedAcquirer.acquire', side_effect=AssertionError('acquisition')):
            self.assertEqual(w.assess(b, raw, now=NOW)['cacheDecision'], 'unsupported-real-source-cache-planner')

    def test_unknown_acquisition_and_holds_never_reset_or_disappear(self):
        b, raw = fixture()
        b['originalAcquiredAt'] = None
        b['blockers'] = [{'code': 'rights-unknown'}, {'code': 'selector-missing'}]
        r = w.assess(b, raw, now=NOW)
        r2 = w.assess(b, raw, now='2026-10-19T00:00:00Z', previous_fingerprint=r['candidateFingerprint'])
        self.assertEqual(r2['metadataReplay'], 'unchanged-no-op')
        self.assertEqual(r2['status'], 'held')
        self.assertEqual(r2['blockers'], b['blockers'])
        self.assertFalse(r2['assetBytesVerified'])

    def test_replay_tracks_content_and_binding_policy_not_current_clock(self):
        b, raw = fixture()
        first = w.assess(b, raw, now=NOW)
        self.assertEqual(first, w.assess(b, raw, now=NOW))
        replay = w.assess(b, raw, now=NOW, previous_fingerprint=first['candidateFingerprint'])
        self.assertEqual(replay['metadataReplay'], 'unchanged-no-op')
        b['blockers'] = [{'code': 'new-hold'}]
        self.assertEqual(w.assess(b, raw, now=NOW, previous_fingerprint=first['candidateFingerprint'])['metadataReplay'],
                         'new-metadata')

    def test_bad_clocks_and_bounded_input_fail_closed(self):
        b, raw = fixture()
        for now in ['2026-10-18', 'bad', '2026-10-18T01:00:00+01:00', '2026-09-01T00:00:00Z']:
            self.assertEqual(w.assess(b, raw, now=now)['status'], 'malformed')
        self.assertEqual(w.assess(b, b'x' * (w.MAX_METADATA + 1), now=NOW)['status'], 'malformed')
        b['originalAcquiredAt'] = '2026-10-18T01:00:00Z'
        self.assertIn('timestamp-order-invalid', w.assess(b, raw, now=NOW)['diagnostics'])

    def test_actual_portfolio_config_has13_bound_sources_and_no_activation(self):
        config = w.load_config()
        self.assertEqual({b['country'] for b in config['bindings']}, {'ME', 'MF', 'MG', 'MH'})
        self.assertEqual(len(config['bindings']), 13)
        for b in config['bindings']:
            self.assertTrue(b['blockers'])
            self.assertEqual(b['permittedPayloadOperations'], [])
            self.assertIsNone(b['sharedAdapter'])
            self.assertIsNone(b['originalAcquiredAt'])
            for field in ['nativeUnit', 'nativeBasis', 'bodyTableSelector', 'bodyRecordId', 'typedObservationSchema']:
                self.assertIsNone(b['fields'][field]['selector'])

    def test_reader_only_opens_metadata_not_recorded_payload_pins(self):
        b, raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'metadata.json'
            path.write_bytes(raw)
            b['metadataAsset']['path'] = str(path)
            b['payloadAssetPinsRecordedOnly'] = [{'path': '/never/read/original.pdf'}]
            self.assertEqual(w.read_metadata(b), raw)
            path.unlink()
            self.assertIsNone(w.read_metadata(b))
            path.symlink_to('/never/read/original.pdf')
            with self.assertRaises(ValueError):
                w.read_metadata(b)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO regression requires POSIX')
    def test_fifo_no_writer_rejected_and_cli_sibling_finishes(self):
        b, raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fifo = root / 'metadata.fifo'
            os.mkfifo(fifo)
            good = root / 'metadata.json'
            good.write_bytes(raw)
            bad_binding = copy.deepcopy(b)
            bad_binding['id'] = 'fifo'
            bad_binding['metadataAsset']['path'] = str(fifo)
            b['metadataAsset']['path'] = str(good)
            config = {'bindings': [bad_binding, b]}
            # A timeout kills the subprocess if the old blocking-open bug returns.
            code = ('import json; from offmenu.refresh import worker06_bindings as w; '
                    f'w.load_config=lambda: json.loads({json.dumps(json.dumps(config))}); '
                    f'w.main(["--now", {NOW!r}])')
            run = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True,
                                 text=True, timeout=2)
            self.assertEqual(run.returncode, 0, run.stderr)
            rows = json.loads(run.stdout)
            self.assertEqual(rows[0]['diagnostics'], ['metadata-read-failed'])
            self.assertEqual(rows[1]['status'], 'valid')
            self.assertEqual(rows[1]['networkRequests'], 0)

    def test_reader_rejects_raced_symlinks_and_oversized_regular_files(self):
        b, raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / 'metadata.json'
            original.write_bytes(raw)
            link = root / 'alias.json'
            link.symlink_to(original)
            b['metadataAsset']['path'] = str(link)
            # Model a symlink appearing after the preflight safe_path check.
            with patch('offmenu.refresh.core.safe_path', return_value=link):
                with self.assertRaises(OSError):
                    w.read_metadata(b)
            parent_link = root / 'parent'
            parent_link.symlink_to(root, target_is_directory=True)
            b['metadataAsset']['path'] = str(parent_link / 'metadata.json')
            with patch('offmenu.refresh.core.safe_path', return_value=parent_link / 'metadata.json'):
                with self.assertRaises(OSError):
                    w.read_metadata(b)
            original.write_bytes(b'x' * (w.MAX_METADATA + 1))
            b['metadataAsset']['path'] = str(original)
            with self.assertRaises(ValueError):
                w.read_metadata(b)

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO regression requires POSIX')
    def test_previous_fifo_entrypoint_rejects_without_open_hang(self):
        with tempfile.TemporaryDirectory() as tmp:
            fifo = Path(tmp) / 'prior.json'
            os.mkfifo(fifo)
            code = ('from offmenu.refresh import worker06_bindings as w; '
                    'w.load_config=lambda: {"bindings": []}; '
                    f'w.main(["--now", {NOW!r}, "--previous", {str(fifo)!r}])')
            run = subprocess.run([sys.executable, '-B', '-c', code], capture_output=True,
                                 text=True, timeout=2)
            self.assertEqual(run.returncode, 2)
            self.assertIn('previous-report-unreadable-or-invalid', run.stderr)
            self.assertEqual(run.stdout, '')
            self.assertNotIn(str(fifo), run.stderr)

    def test_previous_regular_report_replay_preserves_both_input_files(self):
        b, raw = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            metadata = Path(tmp) / 'metadata.json'
            metadata.write_bytes(raw)
            b['metadataAsset']['path'] = str(metadata)
            first = w.assess(b, raw, now=NOW)
            prior = Path(tmp) / 'prior.json'
            prior.write_text(json.dumps([first]))
            before = {p: (p.read_bytes(), p.stat().st_mtime_ns) for p in [metadata, prior]}
            output = io.StringIO()
            with patch.object(w, 'load_config', return_value={'bindings': [b]}), contextlib.redirect_stdout(output):
                self.assertEqual(w.main(['--now', NOW, '--previous', str(prior)]), 0)
            result = json.loads(output.getvalue())
            self.assertEqual(result[0]['metadataReplay'], 'unchanged-no-op')
            for p, expected in before.items():
                self.assertEqual((p.read_bytes(), p.stat().st_mtime_ns), expected)
            invalids = [b'{}', b'[{"bindingId":"x","candidateFingerprint":"bad"}]',
                        b'[{"bindingId":"x"},{"bindingId":"x"}]', b'{broken']
            for invalid in invalids:
                prior.write_bytes(invalid)
                with patch.object(w, 'load_config', return_value={'bindings': []}), \
                     contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exit:
                    w.main(['--now', NOW, '--previous', str(prior)])
                self.assertEqual(exit.exception.code, 2)

    def test_shared_qualification_fixture_and_holds(self):
        # Hand-authored trusted contract exists only in this test; descriptors can
        # never construct it. Candidate schema covers this exact metadata shape.
        b, raw = fixture()
        row = w.assess(b, raw, now=NOW)['candidate']
        row['provenance']['fetchedAt'] = b['originalAcquiredAt']
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bundle = root / 'bundle'
            bundle.mkdir()
            assets = []
            for name, body in [('metadata.json', raw), ('rights.json', b'authored fixture only'),
                               ('scope.json', b'one authored metadata record')]:
                (bundle / name).write_bytes(body)
                assets.append(Asset(name, len(body), hashlib.sha256(body).hexdigest()))
            schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
                      'additionalProperties': False,
                      'properties': {'id': {'const': b['id']}, 'kind': {'const': row['kind']},
                                     'schemaVersion': {'const': w.VERSION},
                                     'data': {'const': row['data']}, 'provenance': {'const': row['provenance']}}}
            schemas = {row['kind']: schema}
            c = SourceContract(b['sourceId'], b['releaseId'], 'authored-metadata-fixture',
                               b['originalAcquiredAt'], tuple(assets), 1, ids_digest([b['id']]),
                               schemas, fingerprint(schemas),
                               lambda r: field_origin_errors(r, {'metadata.json': assets[0].sha256},
                                                             policy_pins=(w.POLICY,)),
                               w.POLICY, assets[1], assets[2], frozenset(('retain', 'parse', 'transform')),
                               fixture=True)
            body = canonical([row]) + b'\n'
            candidate = root / 'candidate.jsonl'
            candidate.write_bytes(body)
            manifest = {'sourceId': c.source_id, 'releaseId': c.release_id, 'acquiredAt': c.acquired_at,
                        'normalizedRecords': 1, 'candidateBytes': len(body),
                        'candidateSha256': hashlib.sha256(body).hexdigest(),
                        'rightsEvidenceSha256': assets[1].sha256, 'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets]}
            result = accept(c, bundle, candidate, manifest)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['status'], 'accepted-fixture-scope')
            self.assertFalse(result['productionAccepted'])
            self.assertFalse(result['countryCoverageComplete'])
            held = accept(replace(c, holds=('real-source-hold',), permitted_operations=frozenset()),
                          bundle, candidate, manifest)
            self.assertIn('source-held', held['errors'])
            self.assertIn('operation-rights-missing', held['errors'])


if __name__ == '__main__':
    unittest.main()
