import ast
import copy
import datetime
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu_norway import adapter as a

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'tests/fixtures/norway'


def legacy_functions():
    """Execute only three reviewed function definitions, not legacy import side effects."""
    files = {'collect-national.py': '3f1140b6809d4909a8be415ad51a67ee6677ad57c17d580ec5fbda57edc196e5',
             'import-national-tables.py': '99216f9ed0aa279b0e15b194c2782dcd8548b86362ea9c55038ad287162cf6c8'}
    from types import SimpleNamespace
    environment = {'json': json, 'math': math, 're': re, 'datetime': datetime}
    for name, wanted in files.items():
        raw = (ROOT / 'tests/fixtures/norway-reference' / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != wanted:
            raise AssertionError('legacy-evidence-checksum-mismatch')
        tree = ast.parse(raw)
        names = ('numeric', 'wrap') if name.startswith('import') else ('norway',)
        selected = ast.Module(body=[node for node in tree.body
                          if isinstance(node, ast.FunctionDef) and node.name in names], type_ignores=[])
        exec(compile(selected, name, 'exec'), environment)
    environment['national'] = SimpleNamespace(numeric=environment['numeric'], wrap=environment['wrap'])
    return environment


class NorwayTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / 'inputs'
        shutil.copytree(FIXTURES, self.inputs)
        self.lock = a.fixture_lock(self.inputs)

    def read(self, name):
        return json.loads((self.inputs / name).read_text())

    def mutate(self, name, fn):
        obj = self.read(name)
        fn(obj)
        (self.inputs / name).write_bytes(a.canonical(obj))
        self.lock = a.fixture_lock(self.inputs)

    def rows(self):
        rendered = a.render(self.lock, self.inputs)
        return [json.loads(line)[0] for line in gzip.decompress(rendered['normalized.jsonl.gz']).splitlines()]

    def fail_render(self, code):
        with self.assertRaisesRegex(a.AdapterError, '^' + code + '$'):
            a.render(self.lock, self.inputs)

    def test_legacy_source_pins_and_data_semantic_parity(self):
        legacy = legacy_functions()['norway'](self.inputs)
        current = self.rows()
        self.assertEqual(len(legacy), len(current))
        for old, new in zip(legacy, current):
            for key in ('schemaVersion', 'kind', 'id', 'countries', 'data'):
                self.assertEqual(old[key], new[key])
            for key in ('sourceId', 'recordId', 'url', 'license', 'attribution', 'sourceDate', 'rights'):
                self.assertEqual(old['provenance'][key], new['provenance'][key])
            self.assertNotIn('fetchedAt', new['provenance'])
            self.assertNotIn('archiveSha256', new['provenance'])
            self.assertEqual(new['provenance']['visibility'], 'local-candidate')

    def test_unknowns_zero_trace_bounds_and_text_remain_distinct(self):
        expected = [(None, 'unknown', None), ('-', 'unknown', None), ('', 'unknown', None),
                    (0, 'source', 0.0), ('0', 'source', 0.0), ('TR', 'trace', None),
                    ('N', 'present-no-reliable-amount', None), ('ND', 'not-detected', None),
                    ('NT', 'not-tested', None), ('<0,1', 'less-than', None),
                    ('unresolved', 'source-text', None)]
        for raw, qualifier, value in expected:
            with self.subTest(raw=raw):
                parsed = a.numeric(raw)
                self.assertEqual(parsed['qualifier'], qualifier)
                self.assertEqual(parsed['value'], value)
        self.assertEqual(a.numeric('<0,1')['limit'], .1)
        self.assertEqual(a.numeric('unresolved')['originalText'], 'unresolved')
        rows = self.rows()
        self.assertEqual(rows[0]['data']['nutrients']['protein']['value'], 0.0)
        self.assertIsNone(rows[0]['data']['nutrients']['fat']['value'])
        self.assertIsNone(rows[1]['data']['nutrients']['energy']['value'])

    def test_malformed_bound_preserves_source_text(self):
        self.assertEqual(a.numeric('<1.2.3'), {'value': None, 'qualifier': 'source-text', 'originalText': '<1.2.3'})

    def test_nonfinite_and_invalid_quantity_shapes_fail_closed(self):
        for value in (True, False, {}, [], 'NaN', 'Inf', '1e999', float('inf'), '<' + '9' * 400):
            with self.subTest(value=type(value).__name__), self.assertRaises(a.AdapterError):
                a.numeric(value)

    def test_deterministic_separate_roots_and_no_timestamp(self):
        first = a.render(self.lock, self.inputs)
        second_root = self.root / 'other' / 'inputs'
        shutil.copytree(self.inputs, second_root)
        other = a.fixture_lock(second_root)
        self.assertEqual(self.lock, other)
        os.utime(second_root / 'en-foods.json', (1, 1))
        self.assertEqual(first, a.render(other, second_root))
        for value in first.values():
            self.assertNotIn(str(self.root).encode(), value)
        self.assertEqual(first['normalized.jsonl.gz'][4:8], b'\0\0\0\0')

    def test_inventory_order_does_not_change_build(self):
        original = a.render(self.lock, self.inputs)
        self.lock['inputs'].reverse()
        self.lock['dependencies'].reverse()
        self.assertEqual(original, a.render(self.lock, self.inputs))

    def test_each_source_dependency_changes_key(self):
        before_build, before_bundle = a.build_key(self.lock), a.bundle_key(self.lock)
        for name in a.INPUTS:
            changed = copy.deepcopy(self.lock)
            next(item for item in changed['inputs'] if item['path'] == name)['sha256'] = 'a' * 64
            self.assertNotEqual(a.build_key(changed), before_build)
            self.assertNotEqual(a.bundle_key(changed), before_bundle)

    def test_code_or_contract_retransform_changes_build_not_acquisition_identity(self):
        before_build, before_bundle = a.build_key(self.lock), a.bundle_key(self.lock)
        for dependency in a.DEPENDENCIES:
            changed = copy.deepcopy(self.lock)
            next(item for item in changed['dependencies'] if item['path'] == dependency)['sha256'] = 'b' * 64
            self.assertNotEqual(a.build_key(changed), before_build)
            self.assertEqual(a.bundle_key(changed), before_bundle)
            evidence = self.evidence()
            self.assertEqual(self.plan(changed, evidence, 5)['decision'], 'reuse-verified-retained-inputs')

    def test_corrupt_each_input_is_refused_before_source_parse(self):
        for filename in a.INPUTS:
            with self.subTest(filename=filename):
                path = self.inputs / filename
                original = path.read_bytes()
                path.write_bytes(b'x' + original[1:])
                with patch.object(a, 'normalize', side_effect=AssertionError('must not normalize')):
                    self.fail_render('asset-sha256-mismatch')
                path.write_bytes(original)

    def test_truncated_asset_is_rejected_before_open(self):
        (self.inputs / 'nb-foods.json').write_bytes(b'{}')
        self.fail_render('asset-size-mismatch')

    def test_missing_asset_fails(self):
        (self.inputs / 'en-sources.json').unlink()
        self.fail_render('input-file-unavailable')

    def test_undeclared_extra_file_is_not_read_or_keyed(self):
        before = a.render(self.lock, self.inputs)
        (self.inputs / 'extra-secret.txt').write_text('not an input')
        self.assertEqual(before, a.render(self.lock, self.inputs))

    def test_inventory_missing_extra_duplicate_or_unsafe_path_fails(self):
        for mode in ('missing', 'extra', 'duplicate', 'parent', 'absolute'):
            lock = copy.deepcopy(self.lock)
            if mode == 'missing': lock['inputs'].pop()
            if mode == 'extra': lock['inputs'].append({'path': 'unexpected.json', 'bytes': 1, 'sha256': '1' * 64})
            if mode == 'duplicate': lock['inputs'][1] = lock['inputs'][0]
            if mode == 'parent': lock['inputs'][0]['path'] = '../en-foods.json'
            if mode == 'absolute': lock['inputs'][0]['path'] = '/en-foods.json'
            with self.subTest(mode=mode), self.assertRaisesRegex(a.AdapterError, 'dependency-set-mismatch'):
                a.render(lock, self.inputs)

    def test_nonpositive_bool_and_oversize_assets_fail(self):
        for size in (0, -1, True, a.MAX_ASSET + 1):
            lock = copy.deepcopy(self.lock)
            lock['inputs'][0]['bytes'] = size
            with self.subTest(size=size), self.assertRaisesRegex(a.AdapterError, 'invalid-asset-size'):
                a.render(lock, self.inputs)

    def test_aggregate_bundle_size_is_bounded(self):
        for item in self.lock['inputs']:
            item['bytes'] = a.MAX_ASSET
        self.fail_render('bundle-size-limit-exceeded')

    def test_source_and_runtime_gate(self):
        for key, value, code in [('scope', 'historical-source-snapshot', 'historical-source-input-not-enabled'),
                                 ('releaseId', '2027', 'unsupported-source-release'),
                                 ('sourceId', 'frida', 'unsupported-source-release'),
                                 ('runtime', {}, 'runtime-pin-mismatch')]:
            lock = copy.deepcopy(self.lock)
            lock[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(a.AdapterError, code):
                a.render(lock, self.inputs)

    def test_dependency_hash_mismatch(self):
        self.lock['dependencies'][0]['sha256'] = '0' * 64
        self.fail_render('asset-sha256-mismatch')

    def test_symlink_file_and_ancestor_rejected(self):
        target = self.inputs / 'en-foods.json'
        real = self.root / 'real.json'
        target.rename(real)
        target.symlink_to(real)
        self.fail_render('symlink-path-rejected')
        target.unlink()
        real.rename(target)
        alias = self.root / 'alias'
        alias.symlink_to(self.inputs, target_is_directory=True)
        with self.assertRaisesRegex(a.AdapterError, 'symlink-path-rejected'):
            a.render(self.lock, alias)

    def test_nonregular_input_rejected(self):
        target = self.inputs / 'en-foods.json'
        target.unlink()
        os.mkfifo(target)
        self.fail_render('regular-file-required')

    def test_duplicate_json_keys_rejected(self):
        path = self.inputs / 'en-foods.json'
        path.write_text('{"foods":[],"foods":[]}')
        self.lock = a.fixture_lock(self.inputs)
        self.fail_render('duplicate-json-key')

    def test_nonfinite_json_anywhere_in_bundle_rejected(self):
        for raw in ('{"foods": [], "metadata": NaN}', '{"foods": [], "metadata": 1e999}'):
            (self.inputs / 'en-foods.json').write_text(raw)
            self.lock = a.fixture_lock(self.inputs)
            self.fail_render('nonfinite-json-number')

    def test_fresh_plan_is_not_a_byte_verification_claim(self):
        evidence = self.evidence()
        target = self.inputs / 'en-foods.json'
        target.write_bytes(b'x' + target.read_bytes()[1:])
        plan = self.plan(self.lock, evidence, 1)
        self.assertFalse(plan['assetBytesVerifiedByThisPlan'])
        self.fail_render('asset-sha256-mismatch')

    def test_lock_fifo_is_rejected_without_blocking(self):
        os.mkfifo(self.root / '.norway-candidate.lock')
        with self.assertRaisesRegex(a.AdapterError, 'output-lock-must-be-regular-file'):
            a.build(self.lock, self.inputs, self.root / 'result')
        self.assertFalse((self.root / 'result').exists())

    def test_duplicate_native_ids_in_all_four_inputs(self):
        for filename, array in [('en-foods.json', 'foods'), ('nb-foods.json', 'foods'),
                                ('en-nutrients.json', 'nutrients'), ('en-sources.json', 'sources')]:
            with self.subTest(filename=filename):
                original = (self.inputs / filename).read_bytes()
                self.mutate(filename, lambda x: x[array].append(copy.deepcopy(x[array][0])))
                self.fail_render('duplicate-native-identity')
                (self.inputs / filename).write_bytes(original)
                self.lock = a.fixture_lock(self.inputs)

    def test_equal_locale_counts_with_different_ids_rejected(self):
        self.mutate('nb-foods.json', lambda x: x['foods'][1].update(foodId='wrong-id'))
        self.fail_render('locale-identity-set-mismatch')

    def test_missing_dictionary_is_held(self):
        self.mutate('en-nutrients.json', lambda x: x['nutrients'].pop(0))
        self.fail_render('missing-nutrient-definition-held')

    def test_duplicate_food_component_is_held(self):
        self.mutate('en-foods.json', lambda x: x['foods'][0]['constituents'].append(copy.deepcopy(x['foods'][0]['constituents'][0])))
        self.fail_render('duplicate-food-component')

    def test_distinct_components_cannot_overwrite_same_canonical_key(self):
        self.mutate('en-nutrients.json', lambda x: x['nutrients'][1].update(euroFirId='PROT'))
        self.fail_render('canonical-component-collision-held')

    def test_explicit_observation_unit_drift_is_held(self):
        self.mutate('en-foods.json', lambda x: x['foods'][0]['constituents'][0].update(unit='mg'))
        self.fail_render('source-unit-drift-held')

    def test_canonical_dictionary_unit_drift_is_held(self):
        self.mutate('en-nutrients.json', lambda x: x['nutrients'][0].update(unit='mg'))
        self.fail_render('canonical-unit-drift-held')

    def test_energy_unit_drift_is_held(self):
        self.mutate('en-foods.json', lambda x: x['foods'][0]['calories'].update(unit='kJ'))
        self.fail_render('energy-unit-drift-held')

    def test_basis_drift_is_held(self):
        self.mutate('en-foods.json', lambda x: x['foods'][0].update(basis={'amount': 100, 'unit': 'ml'}))
        self.fail_render('source-basis-drift-held')

    def test_explicit_basis_drift_any_source_coordinate_is_held(self):
        paths = [('en-foods.json', []), ('en-foods.json', ['foods', 0]),
                 ('en-foods.json', ['foods', 0, 'constituents', 0]),
                 ('en-foods.json', ['foods', 0, 'calories']),
                 ('en-foods.json', ['foods', 0, 'energy']),
                 ('nb-foods.json', ['foods', 0]),
                 ('en-nutrients.json', ['nutrients', 0]),
                 ('en-sources.json', ['sources', 0])]
        for filename, path in paths:
            with self.subTest(filename=filename, coordinate=path):
                original = (self.inputs / filename).read_bytes()
                def change(document):
                    target = document
                    for part in path:
                        target = target[part]
                    target['basis'] = {'amount': 100, 'unit': 'ml',
                                       'state': 'as-described', 'portion': 'edible portion'}
                self.mutate(filename, change)
                self.fail_render('source-basis-drift-held')
                (self.inputs / filename).write_bytes(original)
                self.lock = a.fixture_lock(self.inputs)

    def test_source_numeric_underflow_cannot_invent_zero(self):
        for raw in ('1e-999', '-1e-999', '<0.' + '0' * 999 + '1'):
            with self.subTest(raw=raw), self.assertRaisesRegex(a.AdapterError, 'quantity-underflow-held'):
                a.numeric(raw)
        for raw in ('0e-999', '-0e-999'):
            self.assertEqual(a.numeric(raw)['value'], 0)
        self.assertEqual(a.numeric('<0.000')['limit'], 0)
        self.assertEqual(a.strict_json('{"zero": 0e-999}')['zero'], 0)
        self.assertEqual(a.numeric('1_000')['qualifier'], 'source-text')
        self.assertIsNone(a.numeric('1_000')['value'])
        for raw in ('{"foods": [], "metadata": 1e-999}', '{"foods": [], "metadata": -1e-999}'):
            (self.inputs / 'en-foods.json').write_text(raw)
            self.lock = a.fixture_lock(self.inputs)
            self.fail_render('quantity-underflow-held')

    def test_unknown_component_stays_namespaced_and_unresolved_sources_retained(self):
        row = self.rows()[0]
        self.assertIn('matvaretabellen:EXPERIMENTAL', row['data']['nutrients'])
        metadata = json.loads(a.render(self.lock, self.inputs)['source-metadata.json'])
        self.assertEqual(metadata['unresolvedSourceIds'], ['unresolved-native-reference'])
        self.assertEqual(metadata['sources'], self.read('en-sources.json'))
        self.assertEqual(metadata['nutrients'], self.read('en-nutrients.json'))

    def test_empty_snapshot_fails_without_output(self):
        self.mutate('en-foods.json', lambda x: x.update(foods=[]))
        self.mutate('nb-foods.json', lambda x: x.update(foods=[]))
        with self.assertRaisesRegex(a.AdapterError, 'empty-selected-release'):
            a.build(self.lock, self.inputs, self.root / 'result')
        self.assertFalse((self.root / 'result').exists())

    def test_counts_and_no_acceptance_or_country_completeness(self):
        manifest = json.loads(a.render(self.lock, self.inputs)['content-manifest.json'])
        self.assertEqual(manifest['counts']['raw'], manifest['counts']['normalized'])
        self.assertEqual(manifest['counts']['normalized'], 2)
        self.assertIsNone(manifest['counts']['accepted'])
        self.assertTrue(manifest['completeness']['selectedInputSetComplete'])
        for key in ('countryCoverageComplete', 'registryComplete', 'selectedScopeComplete'):
            self.assertFalse(manifest['completeness'][key])
        self.assertEqual(manifest['acceptance'], 'not-performed')
        self.assertEqual(manifest['publicExport'], 'not-enabled')
        self.assertIn('fineli-access-and-zero-semantics-unchanged', manifest['holds'])
        self.assertIn('danish-definition-and-basis-holds-unchanged', manifest['holds'])

    def test_immutable_existing_candidate_reverified(self):
        target = self.root / 'result'
        self.assertEqual(a.build(self.lock, self.inputs, target)['status'], 'created-local-candidate')
        before = {p.name: p.read_bytes() for p in target.iterdir()}
        self.assertEqual(a.build(self.lock, self.inputs, target)['status'], 'verified-existing-candidate')
        self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir()})
        file = target / 'source-metadata.json'
        file.write_bytes(b'x' + file.read_bytes()[1:])
        with self.assertRaisesRegex(a.AdapterError, 'existing-candidate-mismatch'):
            a.build(self.lock, self.inputs, target)
        self.assertEqual(file.read_bytes()[:1], b'x')

    def test_interrupted_candidate_write_does_not_publish(self):
        target = self.root / 'result'
        with patch.object(a.os, 'rename', side_effect=OSError('simulated interruption')):
            with self.assertRaises(OSError):
                a.build(self.lock, self.inputs, target)
        self.assertFalse(target.exists())
        self.assertEqual(list(self.root.glob('.norway-stage-*')), [])
        self.assertEqual(a.build(self.lock, self.inputs, target)['status'], 'created-local-candidate')

    def evidence(self):
        return {'schemaVersion': 'offmenu-norway-acquisition-evidence/1',
                'inputBundleSha256': a.bundle_key(self.lock),
                'originalAcquiredAt': '2026-09-01T00:00:00Z', 'revalidations': []}

    def plan(self, lock, evidence, days):
        now = datetime.datetime(2026, 9, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=days)
        return a.plan_reuse(lock, evidence, now=now)

    def test_30_day_acquisition_window_and_revalidation_not_timestamp_reset(self):
        evidence = self.evidence()
        for age in (0, 5, 29.9999):
            self.assertEqual(self.plan(self.lock, evidence, age)['decision'], 'reuse-verified-retained-inputs')
        for age in (30, 31, 365):
            self.assertEqual(self.plan(self.lock, evidence, age)['decision'], 'revalidation-review-required-no-download')
        before = a.render(self.lock, self.inputs)
        evidence['revalidations'] = [{'observedAt': '2026-09-30T00:00:00Z',
            'result': 'not-modified-304', 'inputBundleSha256': a.bundle_key(self.lock)},
            {'observedAt': '2026-10-01T00:00:00Z', 'result': 'identical-body-200',
             'inputBundleSha256': a.bundle_key(self.lock)}]
        plan = self.plan(self.lock, evidence, 31)
        self.assertEqual(plan['acquisitionAgeDays'], 31)
        self.assertEqual(plan['decision'], 'revalidation-review-required-no-download')
        self.assertEqual(plan['networkRequests'], 0)
        self.assertFalse(plan['assetBytesVerifiedByThisPlan'])
        self.assertEqual(before, a.render(self.lock, self.inputs))

    def test_wrong_bundle_or_future_evidence_fails(self):
        evidence = self.evidence()
        evidence['inputBundleSha256'] = '0' * 64
        with self.assertRaisesRegex(a.AdapterError, 'evidence-bundle-mismatch'):
            self.plan(self.lock, evidence, 5)
        with self.assertRaisesRegex(a.AdapterError, 'acquisition-timestamp-in-future'):
            self.plan(self.lock, self.evidence(), -1)
        evidence = self.evidence()
        evidence['revalidations'] = [{'observedAt': '2026-12-01T00:00:00Z',
            'result': 'not-modified-304', 'inputBundleSha256': a.bundle_key(self.lock)}]
        with self.assertRaisesRegex(a.AdapterError, 'invalid-revalidation-evidence'):
            self.plan(self.lock, evidence, 5)

    def test_cli_under_network_and_process_audit_denial(self):
        lock_path = self.root / 'lock.json'
        lock_path.write_bytes(a.canonical(self.lock))
        target = self.root / 'cli-result'
        code = '''
import sys, runpy
def deny(event, args):
    if event.startswith(('socket.', 'subprocess.', 'ctypes.')) or event in ('os.system', 'os.exec', 'os.posix_spawn', 'os.fork'):
        raise RuntimeError('offline-test-operation-denied')
sys.addaudithook(deny)
sys.argv = ['adapter', '--lock', sys.argv[1], '--inputs', sys.argv[2], '--output', sys.argv[3]]
runpy.run_module('offmenu_norway.adapter', run_name='__main__')
'''
        proc = subprocess.run([sys.executable, '-B', '-c', code, str(lock_path), str(self.inputs), str(target)],
                              cwd=ROOT, env={'PATH': os.environ.get('PATH', ''), 'PYTHONPATH': str(ROOT)},
                              capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        self.assertEqual(json.loads(proc.stdout)['status'], 'created-local-candidate')
        self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, a.render(self.lock, self.inputs))

    def test_optimized_python_does_not_disable_validation(self):
        lock = copy.deepcopy(self.lock)
        lock['scope'] = 'historical-source-snapshot'
        lock_path = self.root / 'lock.json'
        lock_path.write_bytes(a.canonical(lock))
        proc = subprocess.run([sys.executable, '-B', '-O', '-m', 'offmenu_norway.adapter',
                               '--lock', str(lock_path), '--inputs', str(self.inputs),
                               '--output', str(self.root / 'forbidden')],
                              cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(json.loads(proc.stdout)['code'], 'historical-source-input-not-enabled')
        self.assertFalse((self.root / 'forbidden').exists())


if __name__ == '__main__':
    unittest.main()
