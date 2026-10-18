"""Authored metadata and tiny fake-transport fixtures only; no source bodies."""
import copy
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu import portfolio43 as binding
from offmenu.refresh.acquisition import CachedAcquirer, SourceSpec
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest, qualify


T0 = datetime(2026, 10, 1, tzinfo=timezone.utc)


def authored():
    fixture = json.loads((Path(__file__).parent / 'fixtures/portfolio43/authored.json').read_text())
    return fixture['binding'], fixture['evidence']


class MetadataTests(unittest.TestCase):
    def test_packaged_catalogue_exact_mirror_and_independent_deepcopies(self):
        mirror = binding.read_metadata(binding.CONFIG)
        first = binding.load_catalogue()
        self.assertEqual(canonical(first), canonical(mirror))
        self.assertEqual(sha(binding.CONFIG.read_bytes()),
                         '840840b7189f2bdd47734d6de5095abf9b4769ad5bf6fc22f03bdc8541fd7699')
        first['sources'][0]['holds'].clear()
        first['sources'][0]['fields']['pageCount']['value'] = 'changed'
        self.assertEqual(canonical(binding.load_catalogue()), canonical(mirror))

    def test_default_cli_uses_catalogue_without_reading_mirror_or_source_metadata(self):
        output = type('Capture', (), {'buffer': io.BytesIO()})()
        reads = []
        def absent_authored_evidence(path):
            reads.append(Path(path))
            if Path(path) == binding.CONFIG or 'offmenu-data' in str(path):
                raise AssertionError('code mirror or actual source metadata read')
            raise FileNotFoundError()
        with patch.object(binding, 'read_metadata', side_effect=absent_authored_evidence):
            with patch.object(binding.sys, 'stdout', output):
                result = binding.main(['--evidence-directory', '/authored/no-inputs',
                                       '--now', '2026-10-18T12:00:00+00:00'])
        self.assertEqual(result, 0)
        report = json.loads(output.buffer.getvalue())
        self.assertEqual(len(reads), 5)
        self.assertEqual(len(report['sources']), 5)
        self.assertTrue(all(row['status'] == 'missing' for row in report['sources']))

    def test_fifo_evidence_and_replay_are_prompt_typed_failures(self):
        config = binding.read_metadata(binding.CONFIG)
        peer = next(s for s in config['sources'] if s['key'] == 'fj-gateway-menu')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for ingress in ['evidence', 'previous']:
                with self.subTest(ingress=ingress):
                    folder = root / ingress; folder.mkdir()
                    fifo = folder / ('bz-school-2019.json' if ingress == 'evidence' else 'previous.json')
                    os.mkfifo(fifo)
                    (folder / 'fj-gateway-menu.json').write_bytes(canonical({
                        'schemaVersion': 'worker43-evidence/1',
                        'manifestSha256': peer['manifest']['sha256'],
                        'originalAcquiredAt': peer['originalAcquiredAt'],
                        'validatedAt': peer['lastValidationAt'],
                        'declaration': binding.declaration(peer)}))
                    command = [sys.executable, '-B', '-m', 'offmenu.portfolio43',
                               '--evidence-directory', str(folder),
                               '--now', '2026-10-18T12:00:00+00:00']
                    if ingress == 'previous': command += ['--previous-keys', str(fifo)]
                    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    try:
                        stdout, stderr = process.communicate(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill(); process.communicate()
                        self.fail('FIFO blocked metadata ingress; child killed and reaped')
                    self.assertEqual(stderr, b'')
                    report = json.loads(stdout)
                    if ingress == 'previous':
                        self.assertEqual(process.returncode, 2)
                        self.assertEqual(report['diagnostics'], ['metadata-request-invalid'])
                    else:
                        self.assertEqual(process.returncode, 0)
                        statuses = {s['key']: s['status'] for s in report['sources']}
                        self.assertEqual(statuses['bz-school-2019'], 'malformed')
                        self.assertEqual(statuses['fj-gateway-menu'], 'held')
                        self.assertEqual(len(statuses), 5)

    def test_descriptor_open_refuses_regular_to_fifo_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / 'metadata.json'; target.write_text('{}')
            original_open = os.open
            swapped = []
            def replace_before_open(path, flags, *args, **kwargs):
                if path == target.name and kwargs.get('dir_fd') is not None:
                    target.unlink(); os.mkfifo(target); swapped.append(True)
                return original_open(path, flags, *args, **kwargs)
            with patch.object(binding.os, 'open', side_effect=replace_before_open):
                with self.assertRaises(RefreshError): binding.read_metadata(target)
            self.assertEqual(swapped, [True])

    def test_descriptor_walk_refuses_ancestor_symlink_swap(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); parent = root / 'parent'; parent.mkdir()
            (parent / 'metadata.json').write_text('{}')
            other = root / 'other'; other.mkdir(); (other / 'metadata.json').write_text('{}')
            original_open = os.open
            swapped = []
            def replace_before_open(path, flags, *args, **kwargs):
                if path == 'parent' and kwargs.get('dir_fd') is not None:
                    parent.rename(root / 'prior-parent'); parent.symlink_to(other); swapped.append(True)
                return original_open(path, flags, *args, **kwargs)
            with patch.object(binding.os, 'open', side_effect=replace_before_open):
                with self.assertRaises(RefreshError): binding.read_metadata(parent / 'metadata.json')
            self.assertEqual(swapped, [True])

    def test_valid_and_deterministic_noop_with_later_validation(self):
        spec, evidence = authored()
        first = binding.assess(spec, evidence, now=(T0 + timedelta(days=1)).isoformat())
        self.assertEqual(first['status'], 'valid-metadata')
        evidence['validatedAt'] = (T0 + timedelta(days=20)).isoformat()
        second = binding.assess(spec, evidence, now=(T0 + timedelta(days=29)).isoformat(),
                                previous_key=first['metadataKey'])
        self.assertEqual(second['replay'], 'no-op')
        self.assertEqual(second['metadataKey'], first['metadataKey'])
        self.assertEqual(second['originalAcquisitionAgeDays'], 29)
        self.assertEqual(second['validationAgeDays'], 9)
        self.assertEqual(second['cacheDecision'], 'under-30-days-zero-download')
        self.assertFalse(second['assetBytesVerified'])
        self.assertIsNone(second['sourceAcceptance'])

    def test_missing_held_and_malformed_peers_are_isolated(self):
        spec, evidence = authored()
        specs, supplied = [], {}
        for key in ['valid', 'held', 'missing', 'malformed']:
            s = copy.deepcopy(spec); s['key'] = key
            if key == 'held': s['holds'] = ['recorded-use-hold']
            specs.append(s)
            if key != 'missing': supplied[key] = evidence if key != 'malformed' else {'invalid': True}
        result = binding.assess_portfolio(specs, supplied, now=T0.isoformat())
        self.assertEqual({r['key']: r['status'] for r in result['sources']},
                         {'valid': 'valid-metadata', 'held': 'held', 'missing': 'missing', 'malformed': 'malformed'})
        self.assertEqual(result['acceptedRecords'], 0)
        for row in result['sources']:
            self.assertEqual(row['interface']['observedCount'], None)

    def test_stale_boundary_does_not_use_validation_age(self):
        spec, evidence = authored()
        evidence['validatedAt'] = (T0 + timedelta(days=30)).isoformat()
        stale = binding.assess(spec, evidence, now=evidence['validatedAt'])
        self.assertEqual(stale['status'], 'stale')
        self.assertEqual(stale['validationAgeDays'], 0)
        self.assertEqual(stale['cacheDecision'], 'stale-review-required-no-download')
        self.assertEqual(stale['networkRequests'], 0)

    def test_field_origin_forgery_and_pin_drift_fail(self):
        spec, evidence = authored()
        for change, code in [('pin', 'manifest-pin-mismatch'), ('origin', 'field-declaration-mismatch')]:
            bad = copy.deepcopy(evidence)
            if change == 'pin': bad['manifestSha256'] = 'b' * 64
            else: bad['declaration']['provenance']['fieldOrigins']['/data/label']['sourceField'] = '/unproved'
            row = binding.assess(spec, bad, now=T0.isoformat())
            self.assertEqual(row['status'], 'malformed')
            self.assertIn(code, row['diagnostics'])

    def test_malformed_timestamp_and_future_validation_fail(self):
        spec, evidence = authored()
        for value in ['not-a-date', '2026-11-01T00:00:00+00:00', '2026-10-01T00:00:00']:
            evidence['validatedAt'] = value
            self.assertEqual(binding.assess(spec, evidence, now=T0.isoformat())['status'], 'malformed')

    def test_missing_original_time_stays_unknown(self):
        spec, evidence = authored()
        spec['originalAcquiredAt'] = evidence['originalAcquiredAt'] = None
        row = binding.assess(spec, evidence, now=T0.isoformat())
        self.assertEqual(row['status'], 'missing')
        self.assertIsNone(row['originalAcquisitionAgeDays'])
        self.assertIn('original-acquisition-time-unknown', row['diagnostics'])

    def test_malformed_replay_key_map_is_a_typed_cli_error(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'previous.json'; p.write_text('[1]')
            result = subprocess.run([sys.executable, '-B', '-m', 'offmenu.portfolio43',
                '--evidence-directory', directory, '--previous-keys', str(p),
                '--now', T0.isoformat()], capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['diagnostics'], ['metadata-request-invalid'])
            self.assertEqual(result.stderr, b'')

    def test_metadata_reader_duplicate_nonfinite_oversize_and_link(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'meta.json'
            for raw in [b'{"a":1,"a":2}', b'{"a":NaN}', b'x' * (binding.MAX_METADATA + 1)]:
                p.write_bytes(raw)
                with self.assertRaises(ValueError): binding.read_metadata(p)
            link = Path(d) / 'link.json'; link.symlink_to(p)
            with self.assertRaises(RefreshError): binding.read_metadata(link)

    def test_real_specs_disabled_and_cli_missing_is_repeatable(self):
        config = binding.read_metadata(binding.CONFIG)
        self.assertEqual(set(config['countries']), {'BZ', 'FJ', 'RO', 'SR'})
        self.assertEqual(len(config['requiredTypes']), 6)
        for spec in config['sources']:
            with self.assertRaisesRegex(RefreshError, 'source-acquisition-gate-closed'):
                binding.disabled_acquisition_spec(spec).validate()
        with tempfile.TemporaryDirectory() as directory:
            command = [sys.executable, '-B', '-m', 'offmenu.portfolio43',
                       '--evidence-directory', directory, '--now', '2026-10-18T00:00:00+00:00']
            a = subprocess.check_output(command); b = subprocess.check_output(command)
            self.assertEqual(a, b)
            report = json.loads(a)
            self.assertTrue(all(s['status'] == 'missing' for s in report['sources']))
            self.assertEqual(len(report['countryTypeBindings']), 24)
            self.assertEqual(sum(not c['metadataBindings'] for c in report['countryTypeBindings']), 19)


class SharedCacheTests(unittest.TestCase):
    def test_fake_fixture_under30_reuse_stale_and_unchanged_content(self):
        # The shared cache engine, not a worker43 cache implementation.
        payload = b'authored fixture only\n'
        calls = []
        class Response:
            status = 200
            headers = {'content-length': str(len(payload)), 'etag': 'fixture-v1'}
            def __init__(self): self.stream = io.BytesIO(payload)
            def read(self, n): return self.stream.read(n)
            def close(self): pass
        def transport(spec, headers):
            calls.append(dict(headers)); return Response()
        spec = SourceSpec('authored-worker43', 'https://fixture.invalid/authored',
                          sha(canonical({'fixture': True})), 'authored-fixture-only',
                          enabled=True, rights_approved=True)
        with tempfile.TemporaryDirectory() as directory:
            cache = CachedAcquirer(Path(directory), {spec.source_key: spec}, transport=transport, retries=0)
            first = cache.acquire(spec.source_key, fetch_policy='refresh', now=T0)
            second = cache.acquire(spec.source_key, fetch_policy='refresh', now=T0 + timedelta(days=29))
            self.assertEqual(len(calls), 1)
            self.assertEqual(second.status, 'reused-fresh')
            self.assertEqual(first.sha256, second.sha256)
            with self.assertRaisesRegex(RefreshError, 'cache-stale'):
                cache.acquire(spec.source_key, fetch_policy='reuse', now=T0 + timedelta(days=30))
            third = cache.acquire(spec.source_key, fetch_policy='refresh', now=T0 + timedelta(days=30))
            self.assertEqual(third.sha256, first.sha256)
            self.assertEqual(third.provenance['originalAcquiredAt'], first.provenance['originalAcquiredAt'])
            self.assertEqual(len(calls), 2)


class SharedQualificationTests(unittest.TestCase):
    def test_authored_contract_positive_and_held_missing_corrupt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); bundle = root / 'inputs'; bundle.mkdir()
            source = canonical({'label': 'authored example'})
            bodies = {'manifest.json': source,
                      'rights.json': canonical({'fixtureOnly': True, 'operations': ['retain', 'parse', 'transform']}),
                      'scope.json': canonical({'fixtureOnly': True, 'ids': ['fixture:metadata']})}
            assets = tuple(Asset(name, len(raw), sha(raw)) for name, raw in sorted(bodies.items()))
            for name, raw in bodies.items(): (bundle / name).write_bytes(raw)
            spec, _ = authored(); spec['manifest']['sha256'] = sha(source)
            row = binding.declaration(spec)
            row.update(id='fixture:metadata', kind='metadata-fixture', schemaVersion='authored/1')
            row['provenance']['fetchedAt'] = T0.isoformat()
            schemas = {'metadata-fixture': {'type': 'object', 'additionalProperties': False,
                'required': ['id', 'kind', 'schemaVersion', 'provenance', 'data'],
                'properties': {'id': {'const': 'fixture:metadata'}, 'kind': {'const': 'metadata-fixture'},
                    'schemaVersion': {'const': 'authored/1'},
                    'provenance': {'type': 'object', 'required': ['sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins']},
                    'data': {'type': 'object', 'additionalProperties': False,
                        'required': ['label', 'unit'], 'properties': {'label': {'const': 'authored example'}, 'unit': {'type': 'null'}}}}}}
            expected = copy.deepcopy(row)
            def semantic(record):
                issues = binding.field_origin_errors(record, {'manifest.json': sha(source)},
                                                     policy_pins=(binding.UNKNOWN_POLICY,))
                if record != expected: issues.append('authored-field-or-value-mismatch')
                return issues
            contract = SourceContract(spec['sourceId'], spec['releaseId'], 'authored-metadata-only',
                T0.isoformat(), assets, 1, ids_digest(['fixture:metadata']), schemas,
                fingerprint(schemas), semantic, binding.UNKNOWN_POLICY,
                next(a for a in assets if a.path == 'rights.json'),
                next(a for a in assets if a.path == 'scope.json'),
                frozenset(('retain', 'parse', 'transform')), fixture=True, max_records=10)
            raw = canonical([row]); candidate = root / 'candidate.jsonl'; candidate.write_bytes(raw)
            manifest = {'sourceId': spec['sourceId'], 'releaseId': spec['releaseId'],
                'acquiredAt': T0.isoformat(), 'normalizedRecords': 1,
                'rightsEvidenceSha256': contract.rights_evidence.sha256,
                'scopeEvidenceSha256': contract.scope_evidence.sha256,
                'candidateBytes': len(raw), 'candidateSha256': sha(raw),
                'inputFiles': [vars(a) for a in assets]}
            good = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(good['qualified'], good['errors'])
            self.assertTrue(good['fixture'])
            held = qualify(replace(contract, holds=('authored-operation-held',)), bundle, candidate, manifest)
            self.assertIn('source-held', held['errors'])
            missing = qualify(replace(contract, permitted_operations=frozenset(('retain',))), bundle, candidate, manifest)
            self.assertIn('operation-rights-missing', missing['errors'])
            candidate.write_bytes(raw.replace(b'authored example', b'changed example!'))
            corrupt = qualify(contract, bundle, candidate, manifest)
            self.assertFalse(corrupt['qualified'])
            self.assertIn('candidate-custody-mismatch', corrupt['errors'])


if __name__ == '__main__':
    unittest.main()
