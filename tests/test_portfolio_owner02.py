"""Small authored receipt fixtures, never retained publication bodies."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolio_owner02 import SCHEMA, evaluate_binding, evaluate_portfolio, required_cells, metadata_artifact
from offmenu.portfolio_owner02_catalog import bindings
from offmenu.refresh.core import canonical, sha
from offmenu.refresh.field_provenance import field_origin_errors

NOW = '2026-10-18T00:00:00Z'


def fixture():
    raw = canonical({'country': 'AO', 'release': 'synthetic-release',
                     'url': 'https://publisher.invalid/fixture',
                     'acquired': '2026-10-01T00:00:00Z'})
    spec = {'schemaVersion': SCHEMA, 'country': 'AO', 'sourceId': 'authored-receipt',
            'releaseId': 'synthetic-release', 'scope': 'authored-metadata-only',
            'types': ['recipes'], 'scopeReady': True, 'holds': [],
            'metadata': {'logicalPath': 'fixture/receipt.json', 'sha256': sha(raw), 'bytes': len(raw)},
            'acquisitionPointer': '/acquired', 'fields': {
                'releaseLabel': {'kind': 'source', 'pointer': '/release', 'expected': 'synthetic-release'},
                'sourceURL': {'kind': 'source', 'pointer': '/url'},
                'nativeUnit': {'kind': 'unknown', 'reason': 'No synthetic unit assertion.'},
                'nativeBasis': {'kind': 'unknown', 'reason': 'No synthetic basis assertion.'}}}
    return spec, {'fixture/receipt.json': raw}


class PortfolioBindingTests(unittest.TestCase):
    def test_pointer_escapes_reject_invalid_tokens_and_preserve_valid_selectors(self):
        selectors = [('/release~2name', 'release~2name', False),
                     ('/release~', 'release~', False),
                     ('/release~~0', 'release~~0', False),
                     ('/release~0name', 'release~name', True),
                     ('/release~1name', 'release/name', True),
                     ('/release~01name', 'release~1name', True),
                     ('/items/0', None, True), ('/items/00', None, False)]
        for pointer, key, valid in selectors:
            with self.subTest(pointer=pointer):
                spec, evidence = fixture()
                doc = json.loads(evidence['fixture/receipt.json'])
                doc['items'] = ['synthetic-release']
                if key is not None:
                    doc[key] = 'synthetic-release'
                raw = canonical(doc)
                evidence['fixture/receipt.json'] = raw
                spec['metadata'].update(sha256=sha(raw), bytes=len(raw))
                bad = copy.deepcopy(spec)
                bad['fields']['releaseLabel']['pointer'] = pointer
                results = evaluate_portfolio([bad, spec], evidence, now=NOW)
                self.assertEqual([r['status'] for r in results],
                                 ['METADATA_READY' if valid else 'MALFORMED', 'METADATA_READY'])
                if valid:
                    self.assertEqual(results[0]['candidate']['data']['releaseLabel'], 'synthetic-release')
                    self.assertEqual(results[0]['candidate']['provenance']['fieldOrigins']
                                     ['/data/releaseLabel']['sourceField'], pointer)
                else:
                    self.assertIsNone(results[0]['candidate'])

    def test_expected_literal_requires_identical_scalar_type_and_value(self):
        pairs = [(1, True), (True, 1), (0, False), (False, 0),
                 (1.0, True), (1, 1.0), (1.0, 1), ('1', 1), (None, 0),
                 (True, True), (False, False), (1, 1), (1.0, 1.0), (None, None), ('v', 'v')]
        for actual, expected in pairs:
            with self.subTest(actual=actual, actual_type=type(actual), expected_type=type(expected)):
                spec, evidence = fixture()
                doc = json.loads(evidence['fixture/receipt.json'])
                doc['literal'] = actual
                raw = canonical(doc)
                evidence['fixture/receipt.json'] = raw
                spec['metadata'].update(sha256=sha(raw), bytes=len(raw))
                check = copy.deepcopy(spec)
                check['fields']['releaseLabel'] = {'kind': 'source', 'pointer': '/literal', 'expected': expected}
                results = evaluate_portfolio([check, spec], evidence, now=NOW)
                exact = type(actual) is type(expected) and actual == expected
                self.assertEqual([r['status'] for r in results],
                                 ['METADATA_READY' if exact else 'MALFORMED', 'METADATA_READY'])
                if not exact:
                    self.assertEqual(results[0]['diagnostics'], ['field-literal-mismatch'])
                    self.assertIsNone(results[0]['candidate'])

    def test_unhashable_source_ids_preserve_valid_siblings(self):
        spec, evidence = fixture()
        for source_id in ([], {}):
            with self.subTest(source_id=source_id):
                bad = copy.deepcopy(spec)
                bad['sourceId'] = source_id
                results = evaluate_portfolio([bad, spec], evidence, now=NOW)
                self.assertEqual([r['status'] for r in results], ['MALFORMED', 'METADATA_READY'])
                self.assertEqual(results[0]['diagnostics'], ['metadata-binding-invalid'])

    def test_cli_bad_paths_are_isolated_from_regular_sibling(self):
        # Run actual CLI entry in a bounded child so a blocking-open regression
        # fails the test without leaving a process or FIFO writer behind.
        code = '''
import json,sys
from pathlib import Path
from offmenu import portfolio_owner02_catalog as catalog
from offmenu import portfolio_owner02 as module
specs=json.loads(Path(sys.argv[1]).read_text())
catalog.bindings=lambda: specs
mode=sys.argv[3]
if mode.startswith('raced-'):
 original=module.safe_path
 def replace_after_check(value):
  path=original(value)
  if path.name == 'bad.json':
   if mode == 'raced-symlink':
    path.unlink();path.symlink_to(specs[1]['metadata']['retainedPath'])
   else:
    retired=path.parent.with_name('retired')
    path.parent.rename(retired);path.parent.symlink_to(retired, target_is_directory=True)
  return path
 module.safe_path=replace_after_check
module.main(['--now', sys.argv[2]])
'''
        for kind in ('fifo', 'symlink', 'hardlink', 'directory', 'oversized', 'suffix',
                     'missing', 'raced-symlink', 'raced-parent-symlink'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                spec, evidence = fixture()
                raw = evidence['fixture/receipt.json']
                good = root / 'good.json'
                good.write_bytes(raw)
                spec['metadata']['retainedPath'] = str(good)
                bad = copy.deepcopy(spec)
                bad['sourceId'] = 'bad-path'
                bad['metadata']['logicalPath'] = 'fixture/bad.json'
                path = root / ('bad.txt' if kind == 'suffix' else 'bad.json')
                if kind == 'raced-parent-symlink':
                    parent = root / 'parent'
                    parent.mkdir()
                    path = parent / 'bad.json'
                if kind == 'fifo':
                    os.mkfifo(path)
                elif kind == 'symlink':
                    path.symlink_to(good)
                elif kind == 'hardlink':
                    target = root / 'hardlink-target.json'
                    target.write_bytes(raw)
                    os.link(target, path)
                elif kind == 'directory':
                    path.mkdir()
                elif kind == 'oversized':
                    path.write_bytes(b' ' * (2 * 1024 * 1024 + 1))
                elif kind == 'suffix' or kind.startswith('raced-'):
                    path.write_bytes(raw)
                bad['metadata']['retainedPath'] = str(path)
                config = root / 'specs.json'
                config.write_text(json.dumps([bad, spec]))
                child = subprocess.run([sys.executable, '-B', '-c', code, str(config), NOW, kind],
                    capture_output=True, text=True, timeout=3)
                self.assertEqual(child.returncode, 0, child.stderr)
                report = json.loads(child.stdout)
                self.assertEqual([r['status'] for r in report['results']],
                    ['MISSING' if kind == 'missing' else 'MALFORMED', 'METADATA_READY'])
                self.assertEqual(report['metadataArtifact']['metadataRecords'], 1)
                self.assertFalse(report['countryAcceptance'])

    def test_valid_metadata_uses_shared_origin_validator_without_admission(self):
        spec, evidence = fixture()
        r = evaluate_binding(spec, evidence, now=NOW)
        self.assertEqual(r['status'], 'METADATA_READY')
        origins = r['candidate']['provenance']['fieldOrigins']
        policy = origins['/data/nativeUnit']['policySha256']
        self.assertEqual(field_origin_errors(r['candidate'],
            {'fixture/receipt.json': spec['metadata']['sha256']}, policy_pins=(policy,)), [])
        self.assertEqual(r['candidate']['provenance']['fieldOrigins']['/data/releaseLabel']['sourceField'], '/release')
        self.assertIsNone(r['candidate']['data']['nativeUnit'])
        self.assertFalse(r['sourceProcessingAllowed'])
        self.assertFalse(r['countryAccepted'])

    def test_missing_metadata_does_not_fabricate_candidate(self):
        spec, _ = fixture()
        r = evaluate_binding(spec, {}, now=NOW)
        self.assertEqual(r['status'], 'MISSING')
        self.assertIsNone(r['candidate'])

    def test_hold_and_unknown_selector_survive_even_when_input_is_valid(self):
        spec, evidence = fixture()
        spec.update(holds=['existing-denial-do-not-retry'], scopeReady=False)
        before = copy.deepcopy(spec)
        r = evaluate_binding(spec, evidence, now=NOW)
        self.assertEqual(r['status'], 'HELD')
        self.assertIn('source-operation-held', r['diagnostics'])
        self.assertIn('content-selector-or-scope-not-qualified', r['diagnostics'])
        self.assertEqual(spec, before)
        self.assertEqual(r['networkRequests'], 0)

    def test_missing_content_scope_is_distinct_from_source_hold(self):
        spec, evidence = fixture()
        spec['scopeReady'] = False
        self.assertEqual(evaluate_binding(spec, evidence, now=NOW)['status'], 'MISSING')

    def test_changed_metadata_bytes_are_stale_not_repaired(self):
        spec, evidence = fixture()
        evidence['fixture/receipt.json'] += b' '
        r = evaluate_binding(spec, evidence, now=NOW)
        self.assertEqual(r['status'], 'STALE_INPUT')
        self.assertIsNone(r['candidate'])
        self.assertEqual(r['diagnostics'], ['metadata-input-pin-mismatch'])

    def test_malformed_or_duplicate_json_matching_pin_is_rejected(self):
        for raw in (b'{', b'{"country":"AO","country":"AO"}', b'{"country":"AO","x":NaN}'):
            with self.subTest(raw=raw):
                spec, evidence = fixture()
                evidence['fixture/receipt.json'] = raw
                spec['metadata'].update(sha256=sha(raw), bytes=len(raw))
                self.assertEqual(evaluate_binding(spec, evidence, now=NOW)['status'], 'MALFORMED')

    def test_missing_or_changed_literal_selector_fails_closed(self):
        for declaration in ({'kind': 'source', 'pointer': '/absent'},
                            {'kind': 'source', 'pointer': '/release', 'expected': 'different'}):
            spec, evidence = fixture()
            spec['fields']['releaseLabel'] = declaration
            r = evaluate_binding(spec, evidence, now=NOW)
            self.assertEqual(r['status'], 'MALFORMED')
            self.assertIsNone(r['candidate'])

    def test_validation_age_never_resets_acquisition_or_noop_identity(self):
        spec, evidence = fixture()
        a = evaluate_binding(spec, evidence, now=NOW)
        b = evaluate_binding(spec, evidence, now='2026-10-19T00:00:00Z', previous_key=a['bindingKey'])
        self.assertEqual(b['replay'], 'no-op')
        self.assertEqual(a['candidate'], b['candidate'])
        self.assertEqual(a['bindingKey'], b['bindingKey'])
        self.assertEqual(b['cache']['originalAcquiredAt'], '2026-10-01T00:00:00Z')
        self.assertEqual(b['cache']['acquisitionAgeDays'], 18)
        self.assertFalse(b['cache']['validationResetsAcquisitionAge'])

    def test_exact_30day_boundary_requests_review_not_download(self):
        spec, evidence = fixture()
        under = evaluate_binding(spec, evidence, now='2026-10-30T23:59:59Z')
        boundary = evaluate_binding(spec, evidence, now='2026-10-31T00:00:00Z')
        self.assertEqual(under['cache']['decision'], 'under-30days-no-download')
        self.assertEqual(boundary['cache']['decision'], 'conditional-review-required-no-download')
        self.assertEqual(boundary['cache']['networkRequests'], 0)
        self.assertFalse(boundary['cache']['retentionPermissionEstablished'])

    def test_unknown_acquisition_is_not_current_validation_time(self):
        spec, evidence = fixture()
        spec['acquisitionPointer'] = None
        r = evaluate_binding(spec, evidence, now=NOW)
        self.assertIsNone(r['cache']['originalAcquiredAt'])
        self.assertIsNone(r['candidate']['provenance']['fetchedAt'])
        self.assertEqual(r['cache']['decision'], 'original-acquisition-unknown-no-download')

    def test_bad_source_does_not_prevent_peer_result_and_no_network_is_used(self):
        spec, evidence = fixture()
        bad = copy.deepcopy(spec)
        bad['fields']['releaseLabel']['pointer'] = '/missing'
        with patch('urllib.request.urlopen', side_effect=AssertionError('network')):
            r = evaluate_portfolio([bad, spec, None], evidence, now=NOW)
        self.assertEqual([x['status'] for x in r], ['MALFORMED', 'METADATA_READY', 'MALFORMED'])

    def test_malformed_clock_future_acquisition_and_unsafe_path(self):
        spec, evidence = fixture()
        self.assertEqual(evaluate_binding(spec, evidence, now='2026-10-18')['status'], 'MALFORMED')
        self.assertEqual(evaluate_binding(spec, evidence, now='2026-09-01T00:00:00Z')['status'], 'MALFORMED')
        spec['metadata']['logicalPath'] = '../receipt.json'
        self.assertEqual(evaluate_binding(spec, evidence, now=NOW)['status'], 'MALFORMED')

    def test_field_declaration_changes_invalidate_noop(self):
        spec, evidence = fixture()
        a = evaluate_binding(spec, evidence, now=NOW)
        spec['fields']['nativeUnit']['reason'] = 'Different explicit unresolved interpretation.'
        b = evaluate_binding(spec, evidence, now=NOW, previous_key=a['bindingKey'])
        self.assertNotEqual(a['bindingKey'], b['bindingKey'])
        self.assertEqual(b['replay'], 'metadata-candidate')

    def test_catalog_is_detached_and_all_actual_sources_remain_held(self):
        values = bindings()
        self.assertEqual(len(values), 8)
        self.assertEqual({x['country'] for x in values}, {'AO', 'IL', 'PM'})
        self.assertTrue(all(x['holds'] and not x['scopeReady'] for x in values))
        values[0]['holds'].clear()
        self.assertTrue(bindings()[0]['holds'])

    def test_all_required_country_types_are_explicit_without_false_applicability(self):
        cells = required_cells(bindings())
        self.assertEqual(len(cells), 18)
        self.assertFalse(any(c['accepted'] for c in cells))
        self.assertTrue(all(c['sourceLeadIds'] == [] for c in cells if c['type'] == 'nutrition'))

    def test_shared_singleton_serialization_preserves_held_metadata_not_body_records(self):
        spec, evidence = fixture()
        spec['holds'] = ['source-processing-held']
        result = evaluate_binding(spec, evidence, now=NOW)
        payload, manifest = metadata_artifact([result])
        self.assertEqual(payload, canonical([result['candidate']]))
        self.assertEqual(manifest['sha256'], sha(payload))
        self.assertEqual(manifest['metadataRecords'], 1)
        self.assertEqual(manifest['qualification'], 'unadmitted-metadata-only')
        self.assertEqual(manifest['sourceBodiesParsed'], 0)


if __name__ == '__main__':
    unittest.main()
