"""Authored fixture contract tests only; no accepted source/derived-row input."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.refresh import et_table1_contract as et
from offmenu.refresh.core import RefreshError, canonical, sha

NOW = '2026-10-18T00:00:00Z'


def request(*cases):
    return {'schemaVersion': 'offmenu-et-table1-fixture-request/1',
            'cases': list(cases) or [et.default_case()]}


class ETTable1ContractTests(unittest.TestCase):
    def test_independent_coordinate_inventory_and_native_literal_distinctions(self):
        expected = {f'p7/table1/r{r:02d}/c{c:02d}' for r in range(33) for c in range(1, 6)}
        cells = et.authored_input()['records'][:165]
        self.assertEqual({c['id'] for c in cells}, expected)
        self.assertEqual(len(et.expected_ids()), 169)
        data = [c for c in cells if c['data']['row'] != 0]
        self.assertEqual(len(data), 160)
        self.assertEqual(sum(c['data']['literal'] == '-' for c in data), 24)
        self.assertEqual(sum(c['data']['literal'] == '' for c in data), 2)
        self.assertEqual(sum(c['data']['literal'] == '0' for c in data), 1)
        self.assertTrue(all(c['data']['nativeUnit'] is None for c in data))
        self.assertEqual({r['data']['physicalPage'] for r in et.authored_input()['records'][165:]}, {3, 6, 7})

    def test_shared_qualification_is_fixture_only_no_source_acceptance(self):
        result = et.qualify_fixture()
        self.assertTrue(result['qualified'], result['errors'])
        self.assertTrue(result['fixture'])
        self.assertEqual(result['normalizedRecords'], 169)
        self.assertEqual(result['sourceId'], et.FIXTURE_SOURCE)
        self.assertNotIn('productionAccepted', result)

    def test_wrong_id_duplicate_and_count_fail_whole_fixture(self):
        rows = et.fixture_rows()
        rows[0]['id'] = 'p7/table1/r99/c99'
        self.assertIn('expected-record-identities-mismatch', et.qualify_fixture(rows)['errors'])
        rows = et.fixture_rows(); rows[1] = copy.deepcopy(rows[0])
        self.assertIn('record-identity-duplicate', et.qualify_fixture(rows)['errors'])
        self.assertIn('expected-record-count-mismatch', et.qualify_fixture(et.fixture_rows()[:-1])['errors'])

    def test_wrong_origins_and_literal_values_are_rejected(self):
        for change in ('origin', 'literal', 'unit', 'role', 'page'):
            rows = et.fixture_rows()
            if change == 'origin':
                rows[0]['provenance']['fieldOrigins']['/data/literal']['sourceField'] = '/wrong-coordinate'
            else:
                field = {'literal': 'literal', 'unit': 'nativeUnit', 'role': 'role', 'page': 'physicalPage'}[change]
                rows[0]['data'][field] = 'WRONG'
            result = et.qualify_fixture(rows)
            self.assertFalse(result['qualified'], change)

    def test_wrong_fixture_input_hash_and_hold(self):
        self.assertIn('input-custody-mismatch', et.qualify_fixture(corrupt_input=True)['errors'])
        self.assertIn('source-held', et.qualify_fixture(holds=('authored-fixture-hold',))['errors'])

    def test_missing_and_invalid_declarations_are_isolated(self):
        keys = ('selector', 'nativeUnit', 'nativeBasis', 'expectedIdsSha256', 'sourceSha256', 'role', 'rightsScope')
        for key in keys:
            good = et.default_case('healthy')
            bad = et.default_case('bad'); bad.pop(key)
            result = et.assess(request(bad, good), as_of=NOW)
            self.assertEqual([r['status'] for r in result['cases']], ['malformed', 'qualified-authored-fixture'])
            self.assertIn('et-missing-' + key.lower(), result['cases'][0]['diagnostics'])
        bad = et.default_case('bad'); bad['role'] = 'nutrient-measurement'
        self.assertIn('et-invalid-role', et.assess_case(bad, as_of=NOW)['diagnostics'])

    def test_clocks_are_source_bound_and_missing_unknown(self):
        for value in (None, 'bad', '2026-10-14T22:19:12', '2027-01-01T00:00:00Z'):
            bad = et.default_case('clock'); bad['originalAcquiredAt'] = value
            self.assertEqual(et.assess_case(bad, as_of=NOW)['status'], 'malformed')
        good = et.default_case(); good['validationAt'] = '2026-10-18T00:00:00Z'
        self.assertEqual(et.assess_case(good, as_of=NOW)['status'], 'qualified-authored-fixture')
        bad = et.default_case(); bad['validationAt'] = '2026-01-01T00:00:00Z'
        self.assertIn('et-validation-time-out-of-order', et.assess_case(bad, as_of=NOW)['diagnostics'])

    def test_malformed_and_held_peers_do_not_hide_healthy_peer(self):
        held = et.default_case('held'); held['holds'] = ['fixture-hold']
        malformed = et.default_case('deep'); malformed['extra'] = []
        for _ in range(80):
            malformed['extra'] = [malformed['extra']]
        result = et.assess(request(held, malformed, et.default_case('good'), {'key': []}), as_of=NOW)
        self.assertEqual([r['status'] for r in result['cases']],
                         ['held', 'malformed', 'qualified-authored-fixture', 'malformed'])

    def test_duplicate_peer_keys_are_structural_error(self):
        with self.assertRaises(RefreshError):
            et.assess(request(et.default_case('same'), et.default_case('same')), as_of=NOW)

    def test_output_replay_is_exact_and_collision_preserves_bytes(self):
        value = et.assess(request(), as_of=NOW)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'output.json'
            self.assertEqual(et.publish(path, value), 'created')
            before = path.stat().st_mtime_ns
            self.assertEqual(et.publish(path, value), 'no-op')
            self.assertEqual(before, path.stat().st_mtime_ns)
            changed = copy.deepcopy(value); changed['policySha256'] = 'b' * 64
            with self.assertRaises(RefreshError):
                et.publish(path, changed)
            self.assertEqual(path.read_bytes(), canonical(et.content_receipt(value)))

    def test_policy_source_selector_inventory_and_basis_invalidate_receipt(self):
        first = et.assess(request(), as_of=NOW)
        for key, value in [('rightsScope', 'public'), ('selector', '/other'), ('sourceSha256', 'b' * 64),
                           ('expectedIdsSha256', 'b' * 64), ('nativeBasis', 'per100g')]:
            case = et.default_case(); case[key] = value
            changed = et.assess(request(case), as_of=NOW)
            self.assertNotEqual(sha(canonical(first)), sha(canonical(changed)), key)
            self.assertEqual(changed['cases'][0]['status'], 'malformed')

    def test_cli_uses_bounded_existing_reader_and_exact_replay(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); source = root / 'request.json'; source.write_bytes(canonical(request()))
            output = root / 'result.json'
            command = [sys.executable, '-B', '-m', 'offmenu.refresh.et_table1_contract',
                       '--request', str(source), '--as-of', NOW, '--output', str(output)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(first.returncode, 0, first.stdout)
            second = subprocess.run(command, capture_output=True, text=True, timeout=10)
            self.assertEqual(json.loads(second.stdout)['outcome'], 'no-op')
            source.unlink(); os.mkfifo(source)
            third = subprocess.run(command, capture_output=True, text=True, timeout=2)
            self.assertEqual(third.returncode, 2)

    def test_publication_race_cannot_overwrite_competing_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'report.json'
            def competitor(draft, destination):
                Path(destination).write_bytes(b'authored competing result')
                raise FileExistsError()
            with patch.object(et.os, 'link', side_effect=competitor):
                with self.assertRaises(RefreshError):
                    et.publish(path, {'value': 0})
            self.assertEqual(path.read_bytes(), b'authored competing result')
            self.assertEqual(list(Path(d).glob('.et-report-*')), [])

    def test_shared_cache_thirty_day_boundary_and_original_clock(self):
        from datetime import timedelta
        from offmenu.refresh.core import timestamp
        original = timestamp(et.DECLARATION['originalAcquisition']['value'])
        before = (original + timedelta(days=30, seconds=-1)).isoformat()
        at_boundary = (original + timedelta(days=30)).isoformat()
        first = et.assess(request(), as_of=before)
        fresh_plan = first['cacheObservations'][0]['plan']
        self.assertEqual(fresh_plan['cacheDecision'], 'reuse-retained')
        self.assertEqual(fresh_plan['acquisitionAgeSeconds'], 30 * 86400 - 1)
        case = et.default_case(); case['validationAt'] = at_boundary
        case['previousKey'] = first['cases'][0]['cacheKey']
        older = et.assess(request(case), as_of=at_boundary)
        stale_plan = older['cacheObservations'][0]['plan']
        self.assertEqual(stale_plan['cacheDecision'], 'revalidation-required')
        self.assertEqual(stale_plan['acquisitionAgeSeconds'], 30 * 86400)
        self.assertEqual(stale_plan['validationAgeSeconds'], 0)
        self.assertEqual(stale_plan['replayDecision'], 'unchanged-no-op')
        self.assertEqual(et.content_receipt(first), et.content_receipt(older))
        self.assertFalse(stale_plan['networkAllowed'])
        self.assertFalse(stale_plan['dataAdmissionAllowed'])
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'receipt.json'
            et.publish(path, first); saved = (path.read_bytes(), path.stat().st_mtime_ns)
            self.assertEqual(et.publish(path, older), 'no-op')
            self.assertEqual(saved, (path.read_bytes(), path.stat().st_mtime_ns))

    def test_malformed_replay_is_isolated_and_scope_policy_invalidate_key(self):
        bad = et.default_case('bad-replay'); bad['previousKey'] = 'not-a-sha'
        result = et.assess(request(bad, et.default_case('good')), as_of=NOW)
        self.assertEqual([r['status'] for r in result['cases']],
                         ['malformed', 'qualified-authored-fixture'])
        self.assertIn('retained-plan-invalid-previous-key', result['cases'][0]['diagnostics'])
        case = et.default_case()
        first = et.cache_plan(case, as_of=NOW, code_fingerprint='a' * 64)
        changed = et.cache_plan(case, as_of=NOW, code_fingerprint='b' * 64)
        self.assertNotEqual(first['key'], changed['key'])
        declaration = copy.deepcopy(et.DECLARATION)
        declaration['attribution']['selectedUseRevision'] = 'authored policy change'
        with patch.object(et, 'DECLARATION', declaration):
            scoped = et.cache_plan(case, as_of=NOW, code_fingerprint='a' * 64)
        self.assertNotEqual(first['key'], scoped['key'])

    def test_distinct_hold_evidence_remains_distinct_without_cache_or_source_action(self):
        first = et.default_case(); first['holds'] = ['fixture-hold-a']
        second = et.default_case(); second['holds'] = ['fixture-hold-b']
        with patch.object(et, 'qualify_fixture', side_effect=AssertionError('held qualification')):
            a = et.assess_case(first, as_of=NOW)
            b = et.assess_case(second, as_of=NOW)
        self.assertEqual((a['status'], b['status']), ('held', 'held'))
        self.assertNotEqual(canonical(a), canonical(b))
        self.assertEqual(a['holds'], ['fixture-hold-a'])

    def test_exact_coordinate_types_reject_boolean_and_float_aliases(self):
        fixtures = et.fixture_rows()
        self.assertIs(type(fixtures[0]['data']['row']), int)
        self.assertEqual(fixtures[0]['data']['row'], 0)
        variants = [(0, 'row', False), (5, 'row', True),
                    (0, 'column', True), (0, 'physicalPage', 7.0),
                    (167, 'physicalPage', 3.0)]
        for index, field, value in variants:
            with self.subTest(index=index, field=field, value=value):
                rows = et.fixture_rows()
                rows[index]['data'][field] = value
                result = et.qualify_fixture(rows)
                self.assertFalse(result['qualified'])
                self.assertIn('et-literal-coordinate-role-mismatch', result['errors'])
        # A malformed authored candidate must not poison a later valid peer.
        healthy = et.qualify_fixture()
        self.assertTrue(healthy['qualified'], healthy['errors'])
        self.assertEqual(healthy['normalizedRecords'], 169)
