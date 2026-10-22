"""Authored fixtures only. No real source/candidate observations are read."""
from dataclasses import replace
from datetime import timedelta
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import nl_cp01 as n
from offmenu.refresh import nl_cp01_metadata as m
from offmenu.refresh.acceptance import (Asset, SourceContract, contract_fingerprint,
                                        fingerprint, ids_digest, qualify)
from offmenu.refresh.acquisition import CachedAcquirer, SourceSpec, MIN_TTL
from offmenu.refresh.core import canonical, sha, timestamp, RefreshError
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors
from offmenu.refresh.serialization import encode_records


class NLContractTests(unittest.TestCase):
    def payloads(self):
        """Author a tiny contract without consulting local retained controls.

        Only the metadata/snapshot boundary is scoped to this test. inspect_one,
        retained_plan, content-key construction and the shared planner stay real.
        Patches are undone by unittest even when an assertion fails.
        """
        acquired = '2026-10-10T00:00:00+00:00'
        body = canonical({'authoredFixture': True, 'value': 0})
        axes = {'fixture': {'selected': [{'code': 'AUTHORED', 'position': 0,
                                         'label': 'Authored fixture basis'}]}}
        order, sizes, selectors = ['fixture'], [1], {'fixture': ['AUTHORED']}
        counts = {'coordinates': 1, 'numeric': 1, 'explicit-null': 0, 'absent': 0,
                  'statusPresent': 0}
        documents = {
            'manifest': {'selectedDimensions': axes, 'dimensionOrder': order,
                         'sourceSizes': sizes, 'sourceSha256': sha(body), 'counts': counts},
            'selectors': selectors,
            'provenance': {'originalCaptureUTC': acquired},
            'terms': {'Eurostat': {'asset': {'sha256': sha(body)}}},
        }
        payloads = {name: canonical(value) for name, value in documents.items()}
        assets = {name: {'path': 'authored/' + name + '.json', 'bytes': len(raw),
                         'sha256': sha(raw)} for name, raw in payloads.items()}
        self.fixture_input_name = 'retained/authored-fixture.json'
        self.fixture_scope_sha256 = ids_digest(['authored:0'])
        snapshot = {'schemaVersion': 'authored-nl-contract-fixture/1',
                    'sourceId': 'authored-nl-contract', 'releaseId': 'authored-v1',
                    'sourceSha256': sha(body), 'originalAcquiredAt': acquired,
                    'policySha256': fingerprint({'authoredPolicy': True}),
                    'expectedIdsSha256': self.fixture_scope_sha256,
                    'requiredBodyInputsNotRead': [{'path': self.fixture_input_name,
                                                  'bytes': len(body), 'sha256': sha(body)}],
                    'metadataPins': assets}
        replacements = {'SOURCE_ID': snapshot['sourceId'], 'RELEASE_ID': snapshot['releaseId'],
                        'SOURCE_SHA256': sha(body), 'SOURCE_BYTES': len(body),
                        'ACQUIRED_AT': acquired, 'AXES': axes, 'DIMENSION_ORDER': order,
                        'SOURCE_SIZES': sizes, 'REQUIRED_SELECTORS': selectors,
                        'REVIEWED_COUNTS': counts, 'METADATA_ASSETS': assets}
        for name, value in replacements.items():
            scoped = patch.object(m, name, value)
            scoped.start();self.addCleanup(scoped.stop)
        scoped = patch.object(n, 'stable_snapshot', return_value=snapshot)
        scoped.start();self.addCleanup(scoped.stop)
        return payloads

    def test_independent_inventory_exact_positions_and_units(self):
        rows = n.expected_inventory()
        self.assertEqual(len(rows), 1845)
        self.assertEqual(len({r['id'] for r in rows}), 1845)
        self.assertEqual([rows[i * 369]['flatIndex'] for i in range(5)],
                         [(i * 555 + 1) * 369 for i in range(5)])
        self.assertEqual(rows[-1]['flatIndex'], (4 * 555 + 1) * 369 + 368)
        self.assertEqual({r['unit'] for r in rows}, {'I25', 'I15', 'RCH_M', 'RCH_A', 'RCH_MV12MAVR'})
        self.assertEqual({r['time'] for r in rows}, {
            f'{year:04}-{month:02}' for year in range(1996, 2027) for month in range(1, 13)
            if (year, month) <= (2026, 9)})
        self.assertEqual(n.source_contract().expected_ids_sha256, ids_digest(r['id'] for r in rows))

    def test_real_contract_remains_descriptive_and_held(self):
        contract = n.source_contract()
        self.assertEqual(contract.expected_records, 1845)
        self.assertFalse(contract.fixture)
        self.assertEqual(contract.acquired_at, m.ACQUIRED_AT)
        self.assertEqual(contract.holds, ('real-source-body-execution-not-selected',))
        self.assertEqual(contract.output_visibility, 'private')
        self.assertEqual(contract.inputs[0], Asset('retained/eurostat.json', 8863774, m.SOURCE_SHA256))
        self.assertEqual(contract_fingerprint(contract), n.stable_snapshot()['contractSha256'])

    def authored_row(self):
        """Invented value for callback tests; never a real-source observation."""
        expected = n.expected_inventory()[0]
        data = {**{k: expected[k] for k in ['flatIndex', 'unit', 'time']},
                'unitLabel': 'Index, 2025=100', 'valueState': 'numeric', 'value': 1.25,
                'valueLexical': '1.250', 'valuePresent': True, 'statusPresent': False,
                'status': None, 'valuePointer': '/value/369', 'statusPointer': '/status/369',
                'canonicalTargets': None}
        origins = {pointer: {'kind': 'constant', 'policySha256': n.POLICY,
                             'symbol': 'authored-callback-test-only'}
                   for pointer in datum_pointers(data)}
        for key in ['value', 'status']:
            origins['/data/' + key] = {'kind': 'source', 'sourceId': m.SOURCE_ID,
                'releaseId': m.RELEASE_ID, 'inputPath': 'retained/eurostat.json',
                'inputSha256': m.SOURCE_SHA256, 'sourceRecordId': '369',
                'sourceField': '/' + key + '/369'}
        return {'id': expected['id'], 'kind': 'hicp-source-observation', 'data': data,
                'provenance': {'sourceId': m.SOURCE_ID, 'releaseId': m.RELEASE_ID,
                               'fetchedAt': m.ACQUIRED_AT, 'fieldOrigins': origins}}

    def test_authored_callback_units_missing_status_and_sparse_origins(self):
        row = self.authored_row();self.assertEqual(n.semantic_errors(row), [])
        for state in ['absent', 'explicit-null']:
            r = self.authored_row();r['data'].update(valueState=state, value=None,
                valueLexical=None, valuePresent=state != 'absent')
            self.assertEqual(n.semantic_errors(r), [])
        for field, value in [('flatIndex', True), ('unitLabel', 'EUR/kg'), ('value', True),
                             ('valueLexical', 'NaN'), ('status', 1),
                             ('statusPointer', '/status/0'), ('canonicalTargets', 'food')]:
            r = self.authored_row();r['data'][field] = value
            self.assertTrue(n.semantic_errors(r), (field, value))
        r = self.authored_row();r['provenance']['fieldOrigins']['/data/value']['sourceField'] = '/value/370'
        self.assertEqual(n.semantic_errors(r), ['nl-source-cell-origin-mismatch'])

    def test_metadata_pins_and_clock_independence(self):
        p = self.payloads(); acquired = timestamp(m.ACQUIRED_AT)
        a = n.inspect_one(p, now=(acquired + timedelta(days=1)).isoformat())
        b = n.inspect_one(p, now=(acquired + timedelta(days=29, seconds=86399)).isoformat(),
                          previous_key=a['contentKey'])
        c = n.inspect_one(p, now=(acquired + timedelta(days=30)).isoformat(), previous_key=b['contentKey'])
        self.assertEqual(a['status'], 'metadata-valid-execution-held')
        self.assertTrue(b['unchangedContentNoOp']);self.assertTrue(c['unchangedContentNoOp'])
        self.assertEqual(b['cache']['decision'], 'reuse-retained')
        self.assertEqual(c['cache']['decision'], 'revalidation-required')
        self.assertEqual(c['cache']['originalAcquiredAt'], m.ACQUIRED_AT)
        self.assertFalse(c['cache']['validationResetsAcquisition'])
        self.assertFalse(c['cache']['bodyCacheVerified'])

    def test_qualified_planner_caller_identity_holds_and_flags(self):
        payloads = self.payloads()
        with patch.object(n, 'plan_retained_input', wraps=n.plan_retained_input) as planner:
            result = n.inspect_one(payloads, now='2026-10-18T00:00:00+00:00')
            call = planner.call_args.kwargs
            self.assertEqual(call['source_id'], m.SOURCE_ID)
            self.assertEqual(call['release_id'], m.RELEASE_ID)
            self.assertEqual(call['original_acquired_at'], m.ACQUIRED_AT)
            self.assertEqual(call['input_pins'][self.fixture_input_name],
                             {'sha256': m.SOURCE_SHA256, 'bytes': m.SOURCE_BYTES})
            self.assertEqual(call['scope_sha256'], self.fixture_scope_sha256)
            self.assertTrue(result['cache']['requiresInputVerification'])
            self.assertFalse(result['cache']['networkAllowed'])
            self.assertFalse(result['cache']['dataAdmissionAllowed'])
            self.assertEqual(result['contentKey'], result['cache']['key'])
            held = n.inspect_one(None, now='2026-10-18T00:00:00+00:00',
                                 previous_key=result['contentKey'], holds=('authored-held-peer',))
            self.assertEqual(held['cache']['cacheDecision'], 'held')
            self.assertEqual(held['cache']['replayDecision'], 'held')
            self.assertFalse(held['unchangedContentNoOp'])

    def test_authored_payloads_need_no_retained_files_or_real_inventory(self):
        payloads = self.payloads()
        self.assertTrue(all(not Path(spec['path']).is_absolute()
                            for spec in m.METADATA_ASSETS.values()))
        self.assertTrue(all(b'/home/user/' not in raw for raw in payloads.values()))
        self.assertEqual(m.AXES['fixture']['selected'][0]['code'], 'AUTHORED')
        # Contract code reads its own code for identity. No metadata/source file
        # should be read, and the old1845-coordinate audit must not be replayed.
        reader = n._read_bounded_regular
        def code_only(path, maximum, label):
            self.assertEqual(label, 'code-identity')
            return reader(path, maximum, label)
        with patch.object(n, '_read_bounded_regular', side_effect=code_only), \
                patch.object(n, 'expected_inventory', side_effect=AssertionError('real inventory replay')):
            result = n.inspect_one(payloads, now='2026-10-18T00:00:00+00:00')
        self.assertEqual(result['status'], 'metadata-valid-execution-held')
        self.assertEqual(result['cache']['identity']['sourceId'], 'authored-nl-contract')

    def test_portable_metadata_root_cli_and_missing_input(self):
        payloads = self.payloads()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);controls = root / 'controls';controls.mkdir()
            for name, spec in m.METADATA_ASSETS.items():
                target = controls / spec['path'];target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payloads[name])
            loaded, diagnostics = n.read_metadata(controls)
            self.assertEqual(loaded, payloads);self.assertEqual(diagnostics, {})
            output = root / 'reports/contract.json'
            def run(now, previous=None):
                argv = ['nl-cp01', '--metadata-root', str(controls), '--now', now,
                        '--output', str(output)]
                if previous is not None:argv += ['--previous', str(previous)]
                stream = io.StringIO()
                with patch.object(sys, 'argv', argv), patch('sys.stdout', stream), \
                        patch.object(n, 'expected_inventory', side_effect=AssertionError('real inventory replay')):
                    n.main()
                return json.loads(stream.getvalue())
            first = run('2026-10-18T00:00:00+00:00')
            before = (output.read_bytes(), output.stat().st_mtime_ns)
            second = run('2026-10-18T01:00:00+00:00', output)
            self.assertEqual(first['writes'], 1);self.assertEqual(second['writes'], 0)
            self.assertEqual(before, (output.read_bytes(), output.stat().st_mtime_ns))
            self.assertNotIn(str(controls).encode(), output.read_bytes())
            self.assertFalse(second['binding']['cache']['networkAllowed'])
            self.assertFalse(second['binding']['cache']['dataAdmissionAllowed'])
            protected = controls / m.METADATA_ASSETS['manifest']['path']
            with self.assertRaisesRegex(RefreshError, 'overlaps-reviewed-metadata'):
                n.write_snapshot(protected, {}, metadata_root=controls)
            self.assertEqual(protected.read_bytes(), payloads['manifest'])
            missing, diagnostics = n.read_metadata(root / 'absent')
            self.assertEqual(missing, {})
            self.assertEqual(set(diagnostics), set(m.METADATA_ASSETS))
            with patch.object(n, '_read_bounded_regular', side_effect=AssertionError('implicit lookup')):
                missing, diagnostics = n.read_metadata()
                self.assertEqual(missing, {})
                self.assertEqual(set(diagnostics.values()), {'metadata-root-not-supplied'})
            stream = io.StringIO()
            with patch.object(sys, 'argv', ['nl-cp01', '--now', '2026-10-18T00:00:00+00:00',
                                          '--output', str(root / 'must-not-exist')]), \
                    patch('sys.stdout', stream), self.assertRaises(SystemExit) as exited:
                n.main()
            self.assertEqual(exited.exception.code, 2)
            self.assertEqual(json.loads(stream.getvalue())['diagnostics'], ['metadata-binding-unavailable'])
            self.assertFalse((root / 'must-not-exist').exists())
            (controls / m.METADATA_ASSETS['terms']['path']).write_bytes(b'{}')
            changed, _ = n.read_metadata(controls)
            result = n.inspect_one(changed, now='2026-10-18T00:00:00+00:00')
            self.assertEqual(result['diagnostics'], ['metadata-pin-mismatch'])

    def test_qualified_planner_caller_invalidation(self):
        snapshot = n.stable_snapshot()
        original = n.retained_plan(snapshot, now='2026-10-18T00:00:00+00:00')
        for field in ['sourceSha256', 'policySha256', 'expectedIdsSha256']:
            changed = json.loads(json.dumps(snapshot));changed[field] = '0' * 64
            result = n.retained_plan(changed, now='2026-10-18T01:00:00+00:00',
                                     previous_key=original['key'])
            self.assertEqual(result['replayDecision'], 'changed')
        changed = json.loads(json.dumps(snapshot))
        changed['metadataPins']['terms']['sha256'] = '0' * 64
        self.assertEqual(n.retained_plan(changed, now='2026-10-18T01:00:00+00:00',
                                        previous_key=original['key'])['replayDecision'], 'changed')

    def test_F1_parent_swap_at_temp_creation_cannot_redirect(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);report = root / 'report';report.mkdir()
            protected = root / 'protected';protected.mkdir()
            target = protected / 'manifest.json';target.write_bytes(b'protected-authored-metadata')
            original_open = os.open;swapped = []
            def race(name, *args, **kwargs):
                if isinstance(name, str) and name.startswith('.nl-cp01-') and not swapped:
                    report.rename(root / 'detached-report');report.symlink_to(protected, target_is_directory=True)
                    swapped.append(True)
                return original_open(name, *args, **kwargs)
            assets = {'fixture': {'path': str(target)}}
            with patch.object(m, 'METADATA_ASSETS', assets):
                with self.assertRaisesRegex(RefreshError, 'overlaps-reviewed-metadata'):
                    n.write_snapshot(target, {'authored': True})
                with patch.object(n.os, 'open', side_effect=race):
                    with self.assertRaisesRegex(RefreshError, 'output-parent-changed'):
                        n.write_snapshot(report / 'manifest.json', {'authored': True})
            self.assertTrue(swapped)
            self.assertEqual(target.read_bytes(), b'protected-authored-metadata')
            self.assertEqual(list((root / 'detached-report').iterdir()), [])

    def test_F1_parent_swap_at_replace_keeps_publication_on_pinned_fd(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);report = root / 'report';report.mkdir()
            protected = root / 'protected';protected.mkdir()
            target = protected / 'manifest.json';target.write_bytes(b'protected-authored-metadata')
            original_replace = os.replace;calls = []
            def race(source, destination, **kwargs):
                self.assertIsInstance(source, str);self.assertEqual(destination, 'manifest.json')
                self.assertEqual(kwargs['src_dir_fd'], kwargs['dst_dir_fd'])
                report.rename(root / 'detached-report');report.symlink_to(protected, target_is_directory=True)
                calls.append(True)
                return original_replace(source, destination, **kwargs)
            with patch.object(m, 'METADATA_ASSETS', {'fixture': {'path': str(target)}}):
                with patch.object(n.os, 'replace', side_effect=race):
                    with self.assertRaisesRegex(RefreshError, 'output-parent-changed'):
                        n.write_snapshot(report / 'manifest.json', {'authored': True})
            self.assertTrue(calls)
            self.assertEqual(target.read_bytes(), b'protected-authored-metadata')
            self.assertEqual((root / 'detached-report/manifest.json').read_bytes(), canonical({'authored': True}))

    def test_F1_output_fifo_alias_and_new_nested_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);fifo = root / 'fifo';os.mkfifo(fifo)
            with self.assertRaisesRegex(RefreshError, 'not-regular-or-aliased'):
                n.write_snapshot(fifo, {'fixture': True})
            protected = root / 'authored-protected';protected.write_bytes(b'protected')
            alias = root / 'alias';os.link(protected, alias)
            with self.assertRaisesRegex(RefreshError, 'not-regular-or-aliased'):
                n.write_snapshot(alias, {'fixture': True})
            self.assertEqual(protected.read_bytes(), b'protected')
            output = root / 'new/nested/report.json'
            self.assertEqual(n.write_snapshot(output, {'fixture': True}), 1)
            before = output.stat().st_mtime_ns
            self.assertEqual(n.write_snapshot(output, {'fixture': True}), 0)
            self.assertEqual(output.stat().st_mtime_ns, before)

    def test_clock_missing_invalid_future_and_nonaware(self):
        p = self.payloads()
        for now in [None, 'bad', '2026-10-14T22:16:49', '2026-01-01T00:00:00+00:00']:
            with self.subTest(now=now):
                r = n.inspect_one(p, now=now)
                self.assertEqual(r['status'], 'malformed');self.assertIsNone(r['contentKey'])

    def test_malformed_missing_held_peers_are_isolated(self):
        p = self.payloads()
        bad = dict(p);bad['manifest'] = b'[]'
        entries = [None, {'payloads': bad}, {'payloads': None},
                   {'payloads': {}, 'holds': ['fixture-explicit-hold']},
                   {'payloads': p, 'previousKey': []}, {'payloads': p}]
        r = n.inspect_many(entries, now='2026-10-18T00:00:00+00:00')
        self.assertEqual([x['status'] for x in r],
                         ['malformed', 'malformed', 'malformed', 'held', 'malformed',
                          'metadata-valid-execution-held'])
        self.assertEqual(r[3]['diagnostics'], ['fixture-explicit-hold'])
        self.assertEqual(n.inspect_one({}, now='bad')['diagnostics'], ['metadata-input-missing'])

    def test_metadata_depth_duplicate_and_overflow_diagnostics(self):
        for raw in [b'{"a":1,"a":2}', b'[' * 1000 + b'0' + b']' * 1000,
                    b'0' * 65537, b'{"x":NaN}']:
            with self.subTest(raw=raw[:20]), self.assertRaises((ValueError, RecursionError)):
                n.metadata_json(raw)

    def test_invalidation_binds_all_identity_inputs(self):
        snapshot = n.stable_snapshot();original = n.content_key(snapshot)
        for key in ['sourceSha256', 'policySha256', 'expectedIdsSha256']:
            changed = dict(snapshot);changed[key] = '0' * 64
            self.assertNotEqual(original, n.content_key(changed))
        changed = json.loads(json.dumps(snapshot));changed['selectedAxes']['unit']['selected'][0]['label'] = 'changed'
        self.assertNotEqual(original, n.content_key(changed))
        with patch.object(n, '_read_bounded_regular', wraps=n._read_bounded_regular) as reader:
            self.assertEqual(n.content_key(snapshot), original)
            self.assertIn('acquisition.py', [call.args[0].name for call in reader.call_args_list])

    def test_snapshot_exact_noop_and_no_clock_writes(self):
        packet = {'contentKey': n.content_key(n.stable_snapshot()), 'snapshot': n.stable_snapshot()}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'contract.json'
            self.assertEqual(n.write_snapshot(path, packet), 1)
            before = (path.read_bytes(), path.stat().st_mtime_ns)
            self.assertEqual(n.write_snapshot(path, packet), 0)
            self.assertEqual(before, (path.read_bytes(), path.stat().st_mtime_ns))
            replay = Path(directory) / 'replay.json';n.write_snapshot(replay, packet)
            self.assertEqual(replay.read_bytes(), path.read_bytes())

    def test_bounded_ingress_fifo_symlink_and_size(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);fifo = root / 'fifo';os.mkfifo(fifo)
            with self.assertRaisesRegex(RefreshError, 'regular-file-required'):
                n._read_bounded_regular(fifo, 128, 'fixture')
            file = root / 'large';file.write_bytes(b'x' * 129)
            with self.assertRaisesRegex(RefreshError, 'bound'):
                n._read_bounded_regular(file, 128, 'fixture')
            link = root / 'link';link.symlink_to(file)
            with self.assertRaises((ValueError, OSError)):
                n._read_bounded_regular(link, 200, 'fixture')

    def test_cli_previous_fifo_fails_promptly_and_data_output_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);fifo = root / 'fifo';os.mkfifo(fifo)
            p = subprocess.run([sys.executable, '-m', 'offmenu.refresh.nl_cp01', '--now',
                                '2026-10-18T00:00:00+00:00', '--output', str(root / 'out'),
                                '--previous', str(fifo)], capture_output=True, text=True, timeout=5)
            self.assertEqual(p.returncode, 2)
            self.assertFalse((root / 'out').exists())
        with self.assertRaisesRegex(RefreshError, 'overlaps-source-data'):
            n.write_snapshot(Path('/home/user/src/offmenu-data/never-open.json'), {})

    def test_shared_qualifier_authored_fixture_and_origin_inventory(self):
        # Authored input/evidence/candidates only, using integrated SourceContract,
        # shared serialization, ID digest, origin callback and qualifier.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);bundle = root / 'bundle';bundle.mkdir()
            assets = []
            for name, value in [('source.json', {'fixture': True, 'value': 0}),
                                ('rights.json', {'fixture': 'retain-parse-transform'}),
                                ('scope.json', {'fixtureIDs': ['fixture:0']})]:
                raw = canonical(value);(bundle / name).write_bytes(raw)
                assets.append(Asset(name, len(raw), sha(raw)))
            row = {'id': 'fixture:0', 'kind': 'fixture-observation', 'data': {'value': 0},
                   'provenance': {'sourceId': 'fixture-nl-cp01', 'releaseId': 'authored-v1',
                                  'fetchedAt': m.ACQUIRED_AT, 'fieldOrigins': {'/data/value': {
                                      'kind': 'source', 'sourceId': 'fixture-nl-cp01',
                                      'releaseId': 'authored-v1', 'inputPath': 'source.json',
                                      'inputSha256': assets[0].sha256, 'sourceRecordId': '0',
                                      'sourceField': '/value'}}}}
            schemas = {'fixture-observation': {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance']}}
            def semantics(value):
                return field_origin_errors(value, {'source.json': assets[0].sha256}) + (
                    [] if value.get('data') == {'value': 0} else ['fixture-value-mismatch'])
            contract = SourceContract('fixture-nl-cp01', 'authored-v1', 'fixture-only', m.ACQUIRED_AT,
                tuple(assets), 1, ids_digest(['fixture:0']), schemas, fingerprint(schemas), semantics,
                fingerprint({'fixture': True}), assets[1], assets[2],
                frozenset(('retain', 'parse', 'transform')), fixture=True)
            raw = encode_records([row]);candidate = root / 'candidate.jsonl';candidate.write_bytes(raw)
            manifest = {'sourceId': contract.source_id, 'releaseId': contract.release_id,
                        'acquiredAt': m.ACQUIRED_AT, 'rightsEvidenceSha256': assets[1].sha256,
                        'scopeEvidenceSha256': assets[2].sha256, 'normalizedRecords': 1,
                        'inputFiles': [vars(a) for a in assets], 'candidateBytes': len(raw),
                        'candidateSha256': sha(raw)}
            result = qualify(contract, bundle, candidate, manifest)
            self.assertTrue(result['qualified'], result)
            self.assertTrue(result['fixture'])
            row['provenance']['fieldOrigins']['/data/value']['inputSha256'] = '0' * 64
            raw = encode_records([row]);candidate.write_bytes(raw)
            manifest.update(candidateBytes=len(raw), candidateSha256=sha(raw))
            result = qualify(contract, bundle, candidate, manifest)
            self.assertFalse(result['qualified'])
            self.assertIn('field-origin-input-pin-mismatch', result['errors'])
            self.assertIn('expected-record-identities-mismatch', qualify(
                replace(contract, expected_ids_sha256=ids_digest(['fixture:wrong'])),
                bundle, candidate, manifest)['errors'])

    def test_shared_cache_fixture_30days_and_original_provenance(self):
        # This is NOT the real query-bearing Eurostat SourceSpec. No source URL
        # is substituted to make real acquisition pass an unsupported interface.
        class Response:
            headers = {'etag': '"authored-v1"'}
            def __init__(self, status):
                self.status = status;self.stream = io.BytesIO(b'authored fixture bytes')
            def read(self, size):return self.stream.read(size)
            def close(self):pass
        calls = []
        def transport(spec, headers):
            calls.append(dict(headers));return Response(200 if len(calls) == 1 else 304)
        with tempfile.TemporaryDirectory() as directory:
            spec = SourceSpec('fixture-nl-cp01', 'https://fixture.invalid/authored.json',
                              fingerprint({'fixture': True}), 'authored-fixture-only',
                              enabled=True, rights_approved=True)
            cache = CachedAcquirer(Path(directory), {spec.source_key: spec}, transport=transport, retries=0)
            start = timestamp(m.ACQUIRED_AT)
            first = cache.acquire(spec.source_key, fetch_policy='refresh', now=start)
            second = cache.acquire(spec.source_key, fetch_policy='refresh', now=start + timedelta(seconds=MIN_TTL - 1))
            self.assertEqual(len(calls), 1);self.assertEqual(second.status, 'reused-fresh')
            third = cache.acquire(spec.source_key, fetch_policy='refresh', now=start + timedelta(seconds=MIN_TTL))
            self.assertEqual(len(calls), 2);self.assertIn('If-None-Match', calls[1])
            self.assertEqual(first.provenance['originalAcquiredAt'], third.provenance['originalAcquiredAt'])
            self.assertEqual(third.sha256, first.sha256)
            self.assertEqual(third.provenance['result'], 'not-modified-304')
        real = SourceSpec('eurostat-real-disabled', 'https://ec.europa.eu/eurostat/api?geo=NL',
                          n.POLICY, 'terms5002', enabled=True, rights_approved=True)
        with self.assertRaisesRegex(RefreshError, 'unsupported-source-locator'):
            real.validate()  # Diagnostic only; no transport or cache/body access.


if __name__ == '__main__':
    unittest.main()
