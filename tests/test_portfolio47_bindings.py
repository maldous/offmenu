"""Authored metadata and isolated qualification, never real source bodies."""
from contextlib import contextmanager
from copy import deepcopy
import os
import signal
from dataclasses import replace
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import portfolio47_bindings as binding
from offmenu.refresh.acceptance import (Asset, SourceContract, fingerprint,
                                        ids_digest, qualify)
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.serialization import encode_records

FIXTURES = Path(__file__).parent / 'fixtures/portfolio47'
NOW = '2026-10-18T00:00:00Z'


@contextmanager
def metadata_deadline():
    def blocked(signum, frame):
        raise AssertionError('metadata read blocked on authored FIFO')
    previous = signal.signal(signal.SIGALRM, blocked)
    signal.setitimer(signal.ITIMER_REAL, 2)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


class Portfolio47Bindings(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((FIXTURES / 'catalog.json').read_text())['sources'][0]

    def inspect(self, spec=None, now=NOW, root=FIXTURES):
        return binding.inspect_binding(spec or self.spec, metadata_root=root, now=now)

    def test_authored_ready_has_complete_origins_preserves_zero_null_and_no_authority(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            r = self.inspect()
        self.assertEqual('ready', r['state'])
        self.assertEqual([], r['diagnostics'])
        self.assertEqual({'basis': None, 'nativeUnit': 'synthetic area unit', 'value': 0}, r['record']['data'])
        self.assertEqual(set('/data/' + k for k in r['record']['data']),
                         set(r['record']['provenance']['fieldOrigins']))
        self.assertFalse(r['dataProcessingAuthorized'])
        self.assertEqual(0, r['acceptedRecords'])

    def test_missing_input_is_isolated_from_valid_peer(self):
        absent = deepcopy(self.spec)
        absent['sourceId'] = 'authored-absent'
        absent['files']['metadata']['path'] = 'absent.json'
        report = binding.plan([absent, self.spec], metadata_root=FIXTURES, now=NOW)
        self.assertEqual(['missing', 'ready'], [r['state'] for r in report['results']])
        self.assertFalse(report['stagingAccepted'])

    def test_malformed_source_does_not_abort_valid_peer(self):
        bad = deepcopy(self.spec)
        bad['sourceId'] = 'authored-malformed'
        bad['files']['metadata']['sha256'] = '0' * 64
        report = binding.plan([bad, self.spec], metadata_root=FIXTURES, now=NOW)
        self.assertEqual(['malformed', 'ready'], [r['state'] for r in report['results']])

    def test_missing_acquisition_declaration_does_not_abort_valid_peer(self):
        bad = deepcopy(self.spec)
        bad['sourceId'] = 'authored-missing-acquisition'
        del bad['acquisition']
        report = binding.plan([bad, self.spec], metadata_root=FIXTURES, now=NOW)
        self.assertEqual(['malformed', 'ready'], [r['state'] for r in report['results']])
        self.assertEqual(['binding-spec-invalid'], report['results'][0]['diagnostics'])

    def test_nested_domain_declaration_does_not_abort_valid_peer(self):
        bad = deepcopy(self.spec)
        bad['sourceId'] = 'authored-nested-domain'
        bad['domains'] = [[]]
        report = binding.plan([bad, self.spec], metadata_root=FIXTURES, now=NOW)
        self.assertEqual(['malformed', 'ready'], [r['state'] for r in report['results']])
        self.assertEqual(['binding-spec-invalid'], report['results'][0]['diagnostics'])

    def test_required_selector_and_mapping_shapes_are_isolated(self):
        for mutate in (
                lambda s: s.update(acquisition={'file': [], 'pointer': '/acquiredAt'}),
                lambda s: s.update(validation=[]),
                lambda s: s['files'].update({1: deepcopy(s['files']['metadata'])}),
                lambda s: s['fields'].update({1: deepcopy(s['fields']['value'])}),
                lambda s: s.update(identityChecks=[None])):
            with self.subTest(mutation=mutate):
                bad = deepcopy(self.spec)
                bad['sourceId'] = 'authored-bad-declaration'
                mutate(bad)
                report = binding.plan([bad, self.spec], metadata_root=FIXTURES, now=NOW)
                self.assertEqual(['malformed', 'ready'], [r['state'] for r in report['results']])

    def test_repository_metadata_path_is_relative_and_pinned(self):
        s = deepcopy(self.spec)
        s['files']['metadata']['repositoryPath'] = 'tests/fixtures/portfolio47/metadata.json'
        self.assertEqual('ready', self.inspect(s, root=None)['state'])
        s['files']['metadata']['repositoryPath'] = '../metadata.json'
        self.assertEqual('malformed', self.inspect(s, root=None)['state'])

    def test_real_hold_cannot_be_waived_by_positive_metadata_or_noop(self):
        s = deepcopy(self.spec)
        s['holds'] = ['source-private-use-only', 'derivative-use-unresolved']
        before = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        r = binding.plan([s], metadata_root=FIXTURES, now=NOW,
                         previous_content_sha256=before['contentSha256'])
        self.assertEqual('held', r['results'][0]['state'])
        self.assertIn('source-scope-held', r['results'][0]['diagnostics'])
        self.assertEqual('unchanged-metadata-no-op', r['metadataContentAction'])
        self.assertFalse(r['results'][0]['dataProcessingAuthorized'])

    def test_stale_acquisition_not_reset_by_recent_validation(self):
        r = self.inspect(now='2026-11-01T00:00:00Z')
        self.assertEqual('stale', r['state'])
        self.assertEqual(31 * 86400, r['cacheRequest']['acquisitionAgeSeconds'])
        self.assertFalse(r['cacheRequest']['validationResetsAge'])
        self.assertEqual('2026-10-17T00:00:00Z', r['cacheRequest']['lastValidatedAt'])

    def test_30_day_boundary_and_no_force_download_interface(self):
        self.assertEqual('ready', self.inspect(now='2026-10-30T23:59:59Z')['state'])
        r = self.inspect(now='2026-10-31T00:00:00Z')
        self.assertEqual('stale', r['state'])
        self.assertFalse(r['cacheRequest']['automaticRefreshEnabled'])
        self.assertEqual(0, r['cacheRequest']['networkRequests'])

    def test_request_start_or_landing_time_does_not_become_acquisition(self):
        s = deepcopy(self.spec)
        s['acquisition']['basis'] = 'request-start-only'
        r = self.inspect(s)
        self.assertEqual('missing', r['state'])
        self.assertIsNone(r['cacheRequest']['originalAcquiredAt'])
        self.assertIn('original-acquisition-time-unknown', r['diagnostics'])

    def test_pin_mismatch_not_bypassed_by_previous_content(self):
        previous = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        s = deepcopy(self.spec)
        s['files']['metadata']['sha256'] = '0' * 64
        r = binding.plan([s], metadata_root=FIXTURES, now=NOW,
                         previous_content_sha256=previous['contentSha256'])
        self.assertEqual('malformed', r['results'][0]['state'])
        self.assertIn('metadata-malformed-or-pin-mismatch', r['results'][0]['diagnostics'])

    def test_pinned_malformed_duplicate_key_and_nonfinite_inputs(self):
        for raw in [b'{', b'{"value":0,"value":1}', b'{"value":NaN}', b'{"value":1e999}']:
            with self.subTest(raw=raw), tempfile.TemporaryDirectory() as d:
                (Path(d) / 'metadata.json').write_bytes(raw)
                s = deepcopy(self.spec)
                s['files']['metadata'].update(bytes=len(raw), sha256=sha(raw))
                self.assertEqual('malformed', self.inspect(s, root=Path(d))['state'])

    def test_missing_selector_is_explicit_null_and_constant_origin(self):
        s = deepcopy(self.spec)
        s['fields']['basis']['pointer'] = '/absent'
        r = self.inspect(s)
        self.assertEqual('missing', r['state'])
        self.assertIsNone(r['record']['data']['basis'])
        self.assertEqual('constant', r['record']['provenance']['fieldOrigins']['/data/basis']['kind'])

    def test_selector_does_not_infer_array_alias_or_composite(self):
        s = deepcopy(self.spec)
        s['fields']['basis']['pointer'] = 'not/a/pointer'
        self.assertEqual('malformed', self.inspect(s)['state'])
        s['fields']['basis']['pointer'] = '/'
        self.assertEqual('missing', self.inspect(s)['state'])

    def test_wrong_release_or_source_identity_fails_closed(self):
        s = deepcopy(self.spec)
        s['identityChecks'][1]['expected'] = 'wrong-release'
        self.assertIn('metadata-identity-invalid', self.inspect(s)['diagnostics'])
        self.assertEqual('malformed', self.inspect(s)['state'])

    def test_utc_clock_and_acquisition_validation_order(self):
        for clock in ['2026-09-30T00:00:00Z', '2026-10-18T00:00:00', 'bad']:
            with self.subTest(clock=clock):
                self.assertEqual('malformed', self.inspect(now=clock)['state'])
        # A clock before validation cannot retrospectively claim that validation.
        self.assertEqual('malformed', self.inspect(now='2026-10-16T00:00:00Z')['state'])

    def test_symlink_path_and_non_metadata_payload_names_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / 'metadata.json').symlink_to(FIXTURES / 'metadata.json')
            self.assertEqual('malformed', self.inspect(root=Path(d))['state'])
        s = deepcopy(self.spec)
        s['files']['metadata']['path'] = 'original-response.bin'
        self.assertEqual('malformed', self.inspect(s)['state'])

    def test_deterministic_replay_rechecks_age_and_is_only_metadata_noop(self):
        a = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        b = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        self.assertEqual(canonical(a), canonical(b))
        c = binding.plan([self.spec], metadata_root=FIXTURES, now='2026-11-01T00:00:00Z',
                         previous_content_sha256=a['contentSha256'])
        self.assertEqual('unchanged-metadata-no-op', c['metadataContentAction'])
        self.assertEqual('stale', c['results'][0]['state'])
        self.assertEqual(['source-neutral-pure-cache-planner-required'], c['sharedInterfaceBlockers'])

    def test_report_pins_the_evaluation_clock_without_changing_content_identity(self):
        a = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        b = binding.plan([self.spec], metadata_root=FIXTURES, now='2026-10-19T00:00:00Z')
        self.assertEqual('2026-10-18T00:00:00+00:00', a['evaluatedAt'])
        self.assertNotEqual(a['evaluatedAt'], b['evaluatedAt'])
        self.assertEqual(a['contentSha256'], b['contentSha256'])
        self.assertNotEqual(a['results'][0]['cacheRequest']['acquisitionAgeSeconds'],
                            b['results'][0]['cacheRequest']['acquisitionAgeSeconds'])

    def test_catalog_all_portfolio_types_scoped_and_real_sources_never_enabled(self):
        catalog = json.loads(binding.CATALOG.read_text())
        self.assertEqual(set(binding.COUNTRIES), {s['country'] for s in catalog['sources']})
        self.assertEqual(5, sum(s['country'] == 'KY' for s in catalog['sources']))
        for s in catalog['sources']:
            self.assertTrue(binding._valid_spec(s))
            self.assertFalse(s['fixture'])
            self.assertTrue(s['holds'])
            self.assertTrue(all(a['role'] == 'permitted-metadata' for a in s['files'].values()))
        r = binding.plan([self.spec], metadata_root=FIXTURES, now=NOW)
        for country in binding.COUNTRIES:
            self.assertEqual(list(binding.DOMAINS), r['requiredCountryTypes'][country])

    def test_shared_qualifier_accepts_authored_binding_not_production(self):
        # This SourceContract is trusted TEST code, not produced from a source
        # manifest/CLI. Independent expected count and ID are authored here.
        row = self.inspect()['record']
        schema = {
            'type': 'object', 'additionalProperties': False,
            'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance'],
            'properties': {
                'id': {'const': 'authored-portfolio47-metadata:binding'},
                'kind': {'const': 'SourceInputBinding'},
                'schemaVersion': {'const': 'offmenu-portfolio47-metadata-binding/1'},
                'data': {'type': 'object', 'additionalProperties': False,
                         'required': ['basis', 'nativeUnit', 'value'],
                         'properties': {'basis': {'type': 'null'},
                                        'nativeUnit': {'const': 'synthetic area unit'},
                                        'value': {'const': 0}}},
                'provenance': {'type': 'object', 'additionalProperties': False,
                    'required': ['sourceId', 'releaseId', 'fetchedAt', 'fieldOrigins'],
                    'properties': {'sourceId': {'const': 'authored-portfolio47-metadata'},
                                   'releaseId': {'const': 'fixture-1'},
                                   'fetchedAt': {'const': '2026-10-01T00:00:00+00:00'},
                                   'fieldOrigins': {'type': 'object', 'minProperties': 3,
                                                    'additionalProperties': {'type': 'object'}}}}}}
        schemas = {'SourceInputBinding': schema}
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            bundle = base / 'bundle'
            bundle.mkdir()
            for name in ['metadata.json', 'rights.json', 'scope.json']:
                (bundle / name).write_bytes((FIXTURES / name).read_bytes())
            assets = tuple(Asset(n, len((bundle / n).read_bytes()), sha((bundle / n).read_bytes()))
                           for n in ['metadata.json', 'rights.json', 'scope.json'])
            pins = {a.path: a.sha256 for a in assets}
            contract = SourceContract(
                source_id='authored-portfolio47-metadata', release_id='fixture-1',
                scope_id='authored-metadata-binding-only', acquired_at='2026-10-01T00:00:00+00:00',
                inputs=assets, expected_records=1,
                expected_ids_sha256=ids_digest(['authored-portfolio47-metadata:binding']),
                schemas=schemas, schemas_sha256=fingerprint(schemas),
                semantic_validator=lambda r: binding.field_origin_errors(r, pins, policy_pins=(binding.POLICY_SHA,)),
                policy_sha256=binding.POLICY_SHA, rights_evidence=assets[1], scope_evidence=assets[2],
                permitted_operations=frozenset(('retain', 'parse', 'transform')), fixture=True)
            candidate = base / 'candidate.jsonl'
            candidate.write_bytes(encode_records([row]))
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256,
                        'inputFiles': [vars(a) for a in assets],
                        'candidateBytes': candidate.stat().st_size,
                        'candidateSha256': sha(candidate.read_bytes())}
            q = qualify(contract, bundle, candidate, manifest, scratch_root=base)
            self.assertTrue(q['qualified'], q['errors'])
            self.assertTrue(q['fixture'])
            held = qualify(replace(contract, holds=('fixture-source-held',)),
                           bundle, candidate, manifest, scratch_root=base)
            self.assertFalse(held['qualified'])
            self.assertIn('source-held', held['errors'])
            denied = qualify(replace(contract, permitted_operations=frozenset(('retain',))),
                             bundle, candidate, manifest, scratch_root=base)
            self.assertFalse(denied['qualified'])
            self.assertIn('operation-rights-missing', denied['errors'])
            # Mutation reaches the shared schema/semantic diagnostics, with no
            # dropped row or changed trusted ID/count expectation.
            row['data']['nativeUnit'] = 'invented canonical unit'
            candidate.write_bytes(encode_records([row]))
            manifest.update(candidateBytes=candidate.stat().st_size,
                            candidateSha256=sha(candidate.read_bytes()))
            q = qualify(contract, bundle, candidate, manifest, scratch_root=base)
            self.assertFalse(q['qualified'])
            self.assertIn('record-schema-invalid', q['errors'])


    def _generated_pair(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        raw = (FIXTURES / 'metadata.json').read_bytes()
        (root / 'metadata.json').write_bytes(raw)
        (root / 'healthy.json').write_bytes(raw)
        good = deepcopy(self.spec)
        good['sourceId'] = 'authored-healthy'
        good['files']['metadata']['path'] = 'healthy.json'
        return root, deepcopy(self.spec), good, raw

    def _replace_generated(self, path, raw, kind):
        if kind == 'regular':
            replacement = path.with_name('replacement-regular.json')
            replacement.write_bytes(raw)
            os.replace(replacement, path)
        elif kind == 'same-inode-change':
            path.write_bytes(raw + b' ')
        else:
            path.unlink()
            if kind == 'fifo':
                os.mkfifo(path)
            else:
                replacement = path.with_name('replacement-target.json')
                replacement.write_bytes(raw)
                path.symlink_to(replacement)

    def _assert_isolated_change(self, report):
        bad, good = report['results']
        self.assertEqual(bad['state'], 'malformed', bad)
        self.assertIn('metadata-malformed-or-pin-mismatch', bad['diagnostics'])
        self.assertIsNone(bad['readyFor'])
        self.assertEqual(good['state'], 'ready', good)
        self.assertFalse(report['stagingAccepted'])
        self.assertFalse(bad['dataProcessingAuthorized'])
        self.assertEqual(bad['acceptedRecords'], 0)
        self.assertEqual(report['payloadReads'], 0)

    def test_generated_fifo_and_directory_remain_missing_and_peer_continues(self):
        for kind in ('fifo', 'directory'):
            with self.subTest(kind=kind):
                root, bad, good, raw = self._generated_pair()
                path = root / 'metadata.json'
                path.unlink()
                os.mkfifo(path) if kind == 'fifo' else path.mkdir()
                with metadata_deadline():
                    report = binding.plan([bad, good], metadata_root=root, now=NOW)
                self.assertEqual([r['state'] for r in report['results']], ['missing', 'ready'])

    def test_generated_replacement_before_open_never_blocks_or_follows(self):
        for kind in ('fifo', 'symlink', 'regular'):
            with self.subTest(kind=kind):
                root, bad, good, raw = self._generated_pair()
                target = root / 'metadata.json'
                real_open, real_path_open = os.open, Path.open
                replaced = False
                def replace_once(path):
                    nonlocal replaced
                    if not replaced and Path(path) == target:
                        replaced = True
                        self._replace_generated(target, raw, kind)
                def fd_open(path, flags, *args, **kwargs):
                    replace_once(path)
                    return real_open(path, flags, *args, **kwargs)
                def path_open(path, *args, **kwargs):
                    replace_once(path)
                    return real_path_open(path, *args, **kwargs)
                with metadata_deadline(), patch.object(os, 'open', side_effect=fd_open), \
                        patch.object(Path, 'open', path_open):
                    report = binding.plan([bad, good], metadata_root=root, now=NOW)
                self.assertTrue(replaced)
                self._assert_isolated_change(report)

    def test_generated_replacement_during_read_is_isolated(self):
        for kind in ('fifo', 'symlink', 'regular', 'same-inode-change'):
            with self.subTest(kind=kind):
                root, bad, good, raw = self._generated_pair()
                target = root / 'metadata.json'
                real_path_open, real_fdopen = Path.open, os.fdopen
                wrapped = False
                owner = self
                class ChangingStream:
                    def __init__(self, stream):
                        self.stream = stream
                    def __enter__(self):
                        return self
                    def __exit__(self, *args):
                        return self.stream.__exit__(*args)
                    def fileno(self):
                        return self.stream.fileno()
                    def read(self, *args):
                        value = self.stream.read(*args)
                        owner._replace_generated(target, raw, kind)
                        return value
                def path_open(path, *args, **kwargs):
                    nonlocal wrapped
                    stream = real_path_open(path, *args, **kwargs)
                    if not wrapped and Path(path) == target:
                        wrapped = True
                        return ChangingStream(stream)
                    return stream
                def fdopen(fd, *args, **kwargs):
                    nonlocal wrapped
                    stream = real_fdopen(fd, *args, **kwargs)
                    if not wrapped:
                        wrapped = True
                        return ChangingStream(stream)
                    return stream
                with metadata_deadline(), patch.object(Path, 'open', path_open), \
                        patch.object(os, 'fdopen', side_effect=fdopen):
                    report = binding.plan([bad, good], metadata_root=root, now=NOW)
                self.assertTrue(wrapped)
                self._assert_isolated_change(report)

    def test_generated_replacement_during_parse_is_isolated(self):
        for kind in ('fifo', 'symlink', 'regular', 'same-inode-change'):
            with self.subTest(kind=kind):
                root, bad, good, raw = self._generated_pair()
                decode = binding.strict_json
                changed = False
                def consume(value):
                    nonlocal changed
                    document = decode(value)
                    if not changed:
                        changed = True
                        self._replace_generated(root / 'metadata.json', raw, kind)
                    return document
                with metadata_deadline(), patch.object(binding, 'strict_json', side_effect=consume):
                    report = binding.plan([bad, good], metadata_root=root, now=NOW)
                self._assert_isolated_change(report)

    def test_generated_replacement_at_final_validation_is_isolated(self):
        for kind in ('fifo', 'symlink', 'regular', 'same-inode-change'):
            with self.subTest(kind=kind):
                root, bad, good, raw = self._generated_pair()
                validate = binding.field_origin_errors
                changed = False
                def final_validation(*args, **kwargs):
                    nonlocal changed
                    errors = validate(*args, **kwargs)
                    if not changed:
                        changed = True
                        self._replace_generated(root / 'metadata.json', raw, kind)
                    return errors
                with metadata_deadline(), patch.object(binding, 'field_origin_errors', side_effect=final_validation):
                    report = binding.plan([bad, good], metadata_root=root, now=NOW)
                self._assert_isolated_change(report)

    def test_generated_earlier_input_stays_pinned_through_later_parse(self):
        root, bad, good, raw = self._generated_pair()
        second = deepcopy(bad['files']['metadata'])
        second['path'] = 'second.json'
        bad['files']['second'] = second
        (root / 'second.json').write_bytes(raw)
        decode = binding.strict_json
        calls = 0
        def consume(value):
            nonlocal calls
            document = decode(value)
            calls += 1
            if calls == 2:
                self._replace_generated(root / 'metadata.json', raw, 'regular')
            return document
        with metadata_deadline(), patch.object(binding, 'strict_json', side_effect=consume):
            report = binding.plan([bad, good], metadata_root=root, now=NOW)
        self._assert_isolated_change(report)

    def test_generated_single_bounded_nofollow_descriptor_is_closed(self):
        root, bad, good, raw = self._generated_pair()
        real_open, real_fdopen = os.open, os.fdopen
        opened, limits = [], []
        class BoundedStream:
            def __init__(self, stream):
                self.stream = stream
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return self.stream.__exit__(*args)
            def fileno(self):
                return self.stream.fileno()
            def read(self, limit):
                limits.append(limit)
                return self.stream.read(limit)
        def fdopen(fd, *args, **kwargs):
            return BoundedStream(real_fdopen(fd, *args, **kwargs))
        def track_open(path, flags, *args, **kwargs):
            fd = real_open(path, flags, *args, **kwargs)
            opened.append((fd, flags))
            return fd
        with patch.object(os, 'open', side_effect=track_open), \
                patch.object(os, 'fdopen', side_effect=fdopen), \
                patch.object(Path, 'open', side_effect=AssertionError('metadata pathname reopened')):
            result = self.inspect(bad, root=root)
        self.assertEqual(result['state'], 'ready', result)
        self.assertEqual(len(opened), 1)
        self.assertTrue(opened[0][1] & os.O_NONBLOCK)
        self.assertTrue(opened[0][1] & os.O_NOFOLLOW)
        self.assertEqual(limits, [len(raw) + 1])
        with self.assertRaises(OSError):
            os.fstat(opened[0][0])


if __name__ == '__main__':
    unittest.main()
