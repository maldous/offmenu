import copy
from contextlib import contextmanager
import os
import signal
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio16_binding as binding

from offmenu.refresh.acceptance import (Asset, SourceContract, fingerprint, ids_digest,
                                        qualify)
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors
from offmenu.refresh.portfolio16_binding import (MetadataBinding, bind_metadata,
    load_profile, pointer, publish, run_bindings)

FIXTURES = Path(__file__).parent / 'fixtures/portfolio16_binding'
NOW = '2026-10-18T00:00:00Z'
POLICY = sha(b'authored-fixture-portfolio16-policy')


@contextmanager
def bounded_metadata_read():
    def blocked(signum, frame):
        raise AssertionError('metadata read blocked on authored FIFO')
    previous = signal.signal(signal.SIGALRM, blocked)
    signal.setitimer(signal.ITIMER_REAL, 2)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class Portfolio16BindingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)

    def spec(self, fixture='valid.json', **changes):
        raw = (FIXTURES / fixture).read_bytes()
        path = self.root / fixture
        path.write_bytes(raw)
        value = MetadataBinding('authored-bn-fixture', 'BN', 'authored-release',
            fixture, sha(raw), len(raw), '2026-10-15T00:00:00Z',
            '/recordedUTC', {'country': '/country',
                            'observations': '/measured/observationRows'},
            {'nativeUnit': None, 'nativeBasis': None, 'datasetAccepted': False},
            (), {'scope': 'authored metadata only; no real source'}, {'country': 'BN'})
        return replace(value, **changes)

    def bind(self, spec, **kwargs):
        return bind_metadata(spec, self.root, now=kwargs.get('now', NOW),
                             policy_sha256=POLICY)

    def test_valid_metadata_with_complete_origins_and_explicit_unknowns(self):
        spec = self.spec()
        before = copy.deepcopy(spec)
        result = self.bind(spec)
        self.assertEqual(result['status'], 'valid-metadata-only')
        row = result['metadataCandidate']
        self.assertEqual(row['data']['observations'], 0)
        self.assertIsNone(row['data']['nativeUnit'])
        self.assertIsNone(row['data']['nativeBasis'])
        self.assertEqual(field_origin_errors(row,
            {spec.metadata_path: spec.metadata_sha256}, policy_pins=(POLICY,)), [])
        self.assertFalse(result['datasetAccepted'])
        self.assertFalse(result['sourceOperationsEnabled'])
        self.assertEqual(spec, before)

    def test_missing_input_and_missing_field_have_typed_outcomes(self):
        missing = self.spec(metadata_path='absent.json')
        self.assertEqual(self.bind(missing)['status'], 'missing')
        self.assertIn('metadata-input-missing', self.bind(missing)['errors'])
        result = self.bind(self.spec('missing-field.json'))
        self.assertEqual(result['status'], 'missing')
        self.assertIn('metadata-field-missing', result['errors'])
        self.assertIsNone(result['metadataCandidate'])

    def test_held_source_remains_held_even_with_good_recent_metadata(self):
        spec = self.spec(holds=('explicit-source-use-hold',))
        result = self.bind(spec)
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['holds'], ['explicit-source-use-hold'])
        self.assertIn('source-held', result['errors'])
        self.assertIsNotNone(result['metadataCandidate'])  # descriptor, not dataset
        self.assertFalse(result['sourceOperationsEnabled'])

    def test_malformed_duplicate_json_is_not_a_success(self):
        result = self.bind(self.spec('malformed.txt'))
        self.assertEqual(result['status'], 'malformed')
        self.assertIn('duplicate-json-key', result['errors'])
        self.assertIsNone(result['metadataCandidate'])

    def test_wrong_country_and_boolean_count_do_not_match_reviewed_literals(self):
        spec = self.spec(expected_values={'country': 'BI'})
        self.assertIn('metadata-semantic-mismatch', self.bind(spec)['errors'])
        spec = self.spec(expected_values={'observations': False})
        self.assertIn('metadata-semantic-mismatch', self.bind(spec)['errors'])

    def test_stale_uses_original_acquisition_not_today_validation(self):
        spec = self.spec(original_acquired_at='2026-09-01T00:00:00Z')
        result = self.bind(spec)
        self.assertEqual(result['status'], 'stale')
        self.assertEqual(result['acquisitionAgeDays'], 47)
        self.assertEqual(result['validationAgeDays'], 0)
        self.assertEqual(result['cacheDecision'], 'conditional-review-only-no-download')
        self.assertEqual(result['networkRequests'], 0)

    def test_30_day_boundary_and_no_force_or_download_path(self):
        spec = self.spec(original_acquired_at='2026-09-18T00:00:00Z')
        self.assertEqual(self.bind(spec)['status'], 'stale')
        young = replace(spec, original_acquired_at='2026-09-18T00:00:01Z')
        result = self.bind(young)
        self.assertEqual(result['status'], 'valid-metadata-only')
        self.assertEqual(result['cacheDecision'], 'reuse-retained-metadata-zero-download')
        self.assertEqual(result['minimumReuseDays'], 30)
        self.assertEqual(result['sharedPureCachePlanner'], 'absent-at-abecb99')
        self.assertEqual(result['realSourceRefreshCapability'],
                         'unsupported-no-reviewed-source-binding')

    def test_metadata_path_never_invokes_operational_acquirer(self):
        from unittest.mock import patch
        with patch('offmenu.refresh.acquisition.CachedAcquirer.acquire',
                   side_effect=AssertionError('operational acquirer forbidden')) as acquire:
            result = self.bind(self.spec())
        acquire.assert_not_called()
        self.assertEqual(result['networkRequests'], 0)

    def test_cli_refuses_writing_inside_metadata_inputs(self):
        from unittest.mock import patch
        from offmenu.refresh.portfolio16_binding import main
        with patch('sys.argv', ['portfolio16', '--metadata-root', str(self.root),
                               '--output', str(self.root / 'nested'), '--now', NOW]):
            with self.assertRaisesRegex(RefreshError, 'metadata-output-overlaps-input-root'):
                main()
        self.assertFalse((self.root / 'nested').exists())

    def test_acquisition_unknown_future_and_validation_order_fail_closed(self):
        result = self.bind(self.spec(original_acquired_at=None))
        self.assertEqual(result['status'], 'missing')
        self.assertIsNone(result['acquisitionAgeDays'])
        for acquired, error in [('2026-10-19T00:00:00Z', 'acquisition-timestamp-in-future')]:
            result = self.bind(self.spec(original_acquired_at=acquired))
            self.assertEqual(result['status'], 'malformed')
            self.assertIn(error, result['errors'])
        result = self.bind(self.spec(), now='2026-10-17T00:00:00Z')
        self.assertIn('validation-timestamp-in-future', result['errors'])

    def test_pin_mismatch_and_symlink_are_isolated_not_followed(self):
        spec = self.spec(metadata_sha256='0' * 64)
        self.assertIn('metadata-input-pin-mismatch', self.bind(spec)['errors'])
        spec = self.spec()
        (self.root / 'linked.json').symlink_to(self.root / 'valid.json')
        result = self.bind(replace(spec, metadata_path='linked.json'))
        self.assertEqual(result['status'], 'malformed')
        self.assertIn('symlink-path-rejected', result['errors'])

    def test_json_pointer_scalar_zero_null_escaping_and_no_aliases(self):
        document = {'a/b': {'~name': [0, None]}, '~1': False}
        self.assertEqual(pointer(document, '/a~1b/~0name/0'), 0)
        self.assertIsNone(pointer(document, '/a~1b/~0name/1'))
        self.assertIs(pointer(document, '/~01'), False)
        for selector in ['/a~1b/~0name/01', '/a~1b/~0name/-', '/bad~2', '#/a']:
            with self.assertRaises(RefreshError):
                pointer(document, selector)

    def test_all_five_outcomes_remain_independent_in_one_batch(self):
        good = self.spec()
        specs = [good, replace(good, source_id='missing', metadata_path='absent.json'),
            replace(good, source_id='held', holds=('private-source',)),
            replace(self.spec('malformed.txt'), source_id='malformed'),
            replace(good, source_id='stale', original_acquired_at='2026-09-01T00:00:00Z')]
        report, content = run_bindings(specs, self.root, now=NOW, policy_sha256=POLICY)
        self.assertEqual({x['status'] for x in report['results']},
                         {'valid-metadata-only', 'missing', 'held', 'malformed', 'stale'})
        self.assertEqual(report['datasetRowsAccepted'], 0)
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(sha(content), report['candidateSha256'])

    def test_replay_noop_preserves_bytes_and_mtime(self):
        spec = self.spec()
        report, content = run_bindings([spec], self.root, now=NOW, policy_sha256=POLICY)
        output = self.root / 'output'
        self.assertEqual(publish(report, content, output)['status'], 'written')
        files = ['metadata-candidate.jsonl', 'binding-report.json']
        before = {n: ((output / n).read_bytes(), (output / n).stat().st_mtime_ns) for n in files}
        again = run_bindings([spec], self.root, now=NOW, policy_sha256=POLICY)
        self.assertEqual((report, content), again)
        self.assertEqual(publish(*again, output)['status'], 'no-op')
        after = {n: ((output / n).read_bytes(), (output / n).stat().st_mtime_ns) for n in files}
        self.assertEqual(before, after)

    def test_shared_qualification_accepts_authored_metadata_fixture_only(self):
        spec = self.spec()
        result = self.bind(spec)
        row = result['metadataCandidate']
        from offmenu.refresh.serialization import encode_records
        candidate = self.root / 'candidate.jsonl'
        candidate.write_bytes(encode_records([row]))
        # Exact separate fixture bundle: input metadata + authored rights/scope.
        bundle = self.root / 'bundle'
        bundle.mkdir()
        for name, raw in [('valid.json', (FIXTURES / 'valid.json').read_bytes()),
                          ('rights.json', b'authored fixture retain parse transform'),
                          ('scope.json', b'one authored metadata row, no dataset')]:
            (bundle / name).write_bytes(raw)
        assets = tuple(Asset(p.name, p.stat().st_size, sha(p.read_bytes())) for p in sorted(bundle.iterdir()))
        rights = next(a for a in assets if a.path == 'rights.json')
        scope = next(a for a in assets if a.path == 'scope.json')
        schemas = {'source-input-metadata-binding': {'type': 'object',
            'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
            'properties': {'kind': {'const': 'source-input-metadata-binding'},
                'data': {'type': 'object', 'required': ['country', 'observations', 'nativeUnit', 'nativeBasis', 'datasetAccepted'],
                         'properties': {'country': {'const': 'BN'}, 'observations': {'const': 0},
                                        'nativeUnit': {'type': 'null'}, 'nativeBasis': {'type': 'null'},
                                        'datasetAccepted': {'const': False}}, 'additionalProperties': False}}}}
        contract = SourceContract(spec.source_id, spec.release_id, 'authored-metadata-only',
            spec.original_acquired_at, assets, 1, ids_digest([row['id']]), schemas,
            fingerprint(schemas), lambda r: field_origin_errors(r,
                {'valid.json': spec.metadata_sha256}, policy_pins=(POLICY,)),
            POLICY, rights, scope, frozenset(('retain', 'parse', 'transform')), fixture=True)
        manifest = {'sourceId': spec.source_id, 'releaseId': spec.release_id,
            'acquiredAt': spec.original_acquired_at, 'normalizedRecords': 1,
            'inputFiles': [vars(a) for a in assets], 'candidateSha256': sha(candidate.read_bytes()),
            'candidateBytes': candidate.stat().st_size, 'rightsEvidenceSha256': rights.sha256,
            'scopeEvidenceSha256': scope.sha256}
        qualification = qualify(contract, bundle, candidate, manifest)
        self.assertTrue(qualification['qualified'], qualification['errors'])
        self.assertTrue(qualification['fixture'])
        self.assertNotIn('productionAccepted', qualification)

    def test_profile_has_seven_held_metadata_bindings_only(self):
        bindings, policy = load_profile()
        self.assertEqual(len(bindings), 7)
        self.assertEqual({x.country for x in bindings}, {'BN', 'BI', 'BJ', 'BL'})
        self.assertTrue(all(x.holds for x in bindings))
        self.assertTrue(all(x.metadata_path.endswith('/deliverable-validation.json') for x in bindings))
        expected = {'ingredients', 'recipes', 'nutrition', 'retailers/providers',
                    'prices/baskets', 'dietary references'}
        self.assertTrue(all(set(x.evidence['countryTypeApplicability']) == expected for x in bindings))
        self.assertTrue(all(not v['accepted'] for x in bindings
                            for v in x.evidence['countryTypeApplicability'].values()))
        bl = next(x for x in bindings if x.country == 'BL')
        self.assertEqual(bl.declarations['serviceTreatment'],
                         'included-as-recorded-in-retained-coverage')
        self.assertIsNone(bl.declarations['taxTreatment'])
        self.assertEqual(bl.evidence['serviceDeclarationEvidence']['selector'],
                         '/categories/4/scopeAndGap')
        self.assertEqual(len(policy), 64)

    def _healthy_peer(self, spec):
        (self.root / 'healthy.json').write_bytes((self.root / spec.metadata_path).read_bytes())
        return replace(spec, source_id='z-healthy', metadata_path='healthy.json')

    def _replace_metadata(self, kind, path, raw):
        if kind == 'regular':
            replacement = self.root / 'replacement-regular.json'
            replacement.write_bytes(raw)
            os.replace(replacement, path)
            return
        path.unlink()
        if kind == 'fifo':
            os.mkfifo(path)
        elif kind == 'symlink':
            target = self.root / 'replacement.json'
            target.write_bytes(raw)
            path.symlink_to(target)
        else:
            path.write_bytes(raw)

    def _assert_failed_peer(self, report):
        bad, good = report['results']
        self.assertEqual(bad['status'], 'malformed', bad)
        self.assertIsNone(bad['metadataCandidate'])
        self.assertEqual(good['status'], 'valid-metadata-only', good)
        self.assertEqual(report['metadataCandidates'], 1)
        self.assertEqual(report['datasetRowsAccepted'], 0)

    def test_fifo_input_fails_promptly_and_healthy_peer_continues(self):
        spec = self.spec()
        good = self._healthy_peer(spec)
        self._replace_metadata('fifo', self.root / spec.metadata_path, b'')
        with bounded_metadata_read():
            report, _ = run_bindings([spec, good], self.root, now=NOW, policy_sha256=POLICY)
        self._assert_failed_peer(report)

    def test_replacement_before_metadata_open_never_blocks_or_follows(self):
        spec = self.spec()
        path = self.root / spec.metadata_path
        raw = path.read_bytes()
        good = self._healthy_peer(spec)
        for kind in ('fifo', 'symlink', 'regular'):
            with self.subTest(kind=kind):
                path.unlink(missing_ok=True)
                path.write_bytes(raw)
                real_open, real_path_open = os.open, Path.open
                replaced = False
                def replace_once(candidate):
                    nonlocal replaced
                    if not replaced and Path(candidate) == path:
                        replaced = True
                        self._replace_metadata(kind, path, raw)
                def fd_open(candidate, flags, *args, **kwargs):
                    replace_once(candidate)
                    return real_open(candidate, flags, *args, **kwargs)
                def path_open(candidate, *args, **kwargs):
                    replace_once(candidate)
                    return real_path_open(candidate, *args, **kwargs)
                with bounded_metadata_read(), patch.object(binding.os, 'open', side_effect=fd_open), \
                        patch.object(Path, 'open', path_open):
                    report, _ = run_bindings([spec, good], self.root, now=NOW, policy_sha256=POLICY)
                self.assertTrue(replaced)
                self._assert_failed_peer(report)

    def test_replacement_during_metadata_consumption_fails_closed(self):
        spec = self.spec()
        path = self.root / spec.metadata_path
        raw = path.read_bytes()
        good = self._healthy_peer(spec)
        for kind in ('fifo', 'symlink', 'regular', 'same-inode-change'):
            with self.subTest(kind=kind):
                path.unlink(missing_ok=True)
                path.write_bytes(raw)
                decode = binding.strict_json
                replaced = False
                def consume(payload):
                    nonlocal replaced
                    value = decode(payload)
                    if not replaced:
                        replaced = True
                        if kind == 'same-inode-change':
                            path.write_bytes(raw + b' ')
                        else:
                            self._replace_metadata(kind, path, raw)
                    return value
                with bounded_metadata_read(), patch.object(binding, 'strict_json', side_effect=consume):
                    report, _ = run_bindings([spec, good], self.root, now=NOW, policy_sha256=POLICY)
                self._assert_failed_peer(report)


    def test_one_nofollow_nonblocking_descriptor_closed_after_consumption(self):
        spec = self.spec()
        real_open = os.open
        opened = []
        def track_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            opened.append((fd, flags))
            return fd
        with patch.object(binding.os, 'open', side_effect=track_open), \
                patch.object(Path, 'open', side_effect=AssertionError('metadata pathname reopened')):
            result = self.bind(spec)
        self.assertEqual(result['status'], 'valid-metadata-only')
        self.assertEqual(len(opened), 1)
        fd, flags = opened[0]
        self.assertTrue(flags & os.O_NONBLOCK)
        self.assertTrue(flags & os.O_NOFOLLOW)
        with self.assertRaises(OSError):
            os.fstat(fd)


if __name__ == '__main__':
    unittest.main()
