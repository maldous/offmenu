"""Authored metadata only; no external source fixture or network is required."""
from dataclasses import asdict, replace
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolio60.bindings import (Evidence, Field, POLICY_SHA256, assess,
                                         publish_metadata, read_metadata, validate_binding)
from offmenu.portfolio60.fixtures import authored
from offmenu.portfolio60.catalog import SOURCES
from offmenu.portfolio60 import bindings
from offmenu.refresh import acceptance
from offmenu.refresh.acquisition import SourceSpec, MIN_TTL
from offmenu.refresh.core import canonical, sha, RefreshError
from offmenu.refresh.field_provenance import field_origin_errors

AS_OF = '2026-10-18T00:00:00Z'


class PortfolioBindings(unittest.TestCase):
    def report(self, case='valid', **kwargs):
        spec, loader = authored(case)
        return assess((spec,), as_of=kwargs.pop('as_of', AS_OF), loader=loader, **kwargs)

    def test_required_outcomes(self):
        for case in ('valid', 'missing', 'held', 'malformed', 'stale-input'):
            with self.subTest(case=case):
                r = self.report(case)
                self.assertEqual(r['diagnostics'][0]['status'], case)
                self.assertEqual(r['networkRequests'], 0)
                self.assertEqual(r['sourcePayloadReads'], 0)
                self.assertFalse(r['manifest']['countryCoverageComplete'])
                self.assertFalse(r['manifest']['goldAdmission'])

    def test_validation_clock_never_resets_original_age_or_content_key(self):
        a = self.report(as_of='2026-10-30T23:59:59Z')
        b = self.report(as_of='2026-10-31T00:00:00Z')
        self.assertEqual(a['manifestSha256'], b['manifestSha256'])
        self.assertEqual(a['diagnostics'][0]['sourceContentClaimIdentity'],
                         b['diagnostics'][0]['sourceContentClaimIdentity'])
        self.assertEqual(a['diagnostics'][0]['cacheObservation']['state'], 'under-30-days-zero-download')
        self.assertEqual(b['diagnostics'][0]['cacheObservation']['state'], 'at-least-30-days-review-only-no-download')
        self.assertEqual(b['diagnostics'][0]['cacheObservation']['originalAcquisitionAgeSeconds'], MIN_TTL)
        self.assertEqual(b['diagnostics'][0]['metadataValidatedAt'], '2026-10-31T00:00:00Z')
        self.assertEqual(b['diagnostics'][0]['cacheObservation']['originalAcquiredAt'], '2026-10-01T00:00:00Z')
        self.assertFalse(b['diagnostics'][0]['cacheObservation']['refreshAuthorized'])

    def test_noop_preserves_bytes_inode_mtime_and_detects_corruption(self):
        with tempfile.TemporaryDirectory() as temp:
            a = self.report()
            self.assertEqual(publish_metadata(a, temp)['outcome'], 'metadata-manifest-created')
            p = Path(temp) / a['manifestSha256'] / 'binding-manifest.json'
            before = (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns)
            b = self.report(as_of='2026-10-19T00:00:00Z')
            self.assertEqual(publish_metadata(b, temp)['outcome'], 'unchanged-no-op')
            self.assertEqual(before, (p.read_bytes(), p.stat().st_ino, p.stat().st_mtime_ns))
            p.write_bytes(b'broken')
            with self.assertRaises(RefreshError):
                publish_metadata(b, temp)

    def test_failure_is_isolated_and_does_not_read_payload_paths(self):
        good, loader = authored()
        bad = replace(good, key='bad-binding', inputs=(replace(good.inputs[0], path='/forbidden/response.json'),))
        reads = []
        def selected(asset):
            reads.append(asset.path)
            if asset.path == '/forbidden/response.json':
                raise PermissionError
            return loader(asset)
        r = assess((bad, good), as_of=AS_OF, loader=selected)
        self.assertEqual([x['status'] for x in r['diagnostics']], ['held', 'valid'])
        self.assertEqual(reads, ['/forbidden/response.json', '/authored/receipt.json'])
        self.assertNotIn('original.pdf', str(reads))

    def test_metadata_reader_rejects_symlinks_and_limits_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'receipt.json'
            path.write_bytes(b'x' * (64 * 1024 + 1))
            spec, _ = authored()
            asset = replace(spec.inputs[0], path=str(path))
            with self.assertRaises(RefreshError):
                read_metadata(asset)
            link = Path(temp) / 'response.json'
            link.symlink_to(path)
            with self.assertRaises(RefreshError):
                read_metadata(replace(asset, path=str(link)))

    def test_nonregular_metadata_does_not_block_healthy_peer(self):
        # Bound the harness too: the old blocking FIFO open must fail promptly.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fifo = root / 'bad' / 'receipt.json'
            fifo.parent.mkdir(); os.mkfifo(fifo)
            good = root / 'good' / 'receipt.json'
            good.parent.mkdir()
            spec, loader = authored(); good.write_bytes(loader(spec.inputs[0]))
            code = '''
from dataclasses import replace
import json, sys
from offmenu.portfolio60.bindings import assess
from offmenu.portfolio60.fixtures import authored
spec, _ = authored()
bad = replace(spec, key='fifo', inputs=(replace(spec.inputs[0], path=sys.argv[1]),))
good = replace(spec, key='peer', inputs=(replace(spec.inputs[0], path=sys.argv[2]),))
report = assess((bad, good), as_of='2026-10-18T00:00:00Z')
print(json.dumps(report['diagnostics']))
'''
            p = subprocess.run([sys.executable, '-B', '-c', code, str(fifo), str(good)],
                               capture_output=True, text=True, timeout=3)
            self.assertEqual(p.returncode, 0, p.stderr)
            diagnostics = json.loads(p.stdout)
            self.assertEqual([x['status'] for x in diagnostics], ['malformed', 'valid'])
            self.assertIn({'code': 'metadata-invalid-or-unsafe',
                           'input': 'metadata/authored-receipt.json'}, diagnostics[0]['diagnostics'])

    def test_aliases_and_check_open_swaps_are_rejected_before_read(self):
        spec, loader = authored()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            selected = root / 'receipt.json'
            other = root / 'unselected.json'
            other.write_bytes(b'{"authoredCanary":"unselected"}')
            asset = replace(spec.inputs[0], path=str(selected))
            real_safe_path = bindings.safe_path
            for alias in ('leaf-symlink', 'hardlink', 'parent-symlink'):
                with self.subTest(alias=alias):
                    selected.write_bytes(loader(spec.inputs[0]))
                    target = selected
                    if alias == 'parent-symlink':
                        parent = root / 'selected-parent'
                        parent.mkdir()
                        target = parent / 'receipt.json'
                        target.write_bytes(loader(spec.inputs[0]))
                        alternate = root / 'alternate-parent'
                        alternate.mkdir(); (alternate / 'receipt.json').write_bytes(b'{}')
                    def swap(path):
                        checked = real_safe_path(path)
                        if alias == 'parent-symlink':
                            parent.rename(root / 'retained-parent')
                            parent.symlink_to(alternate, target_is_directory=True)
                            return checked
                        checked.unlink()
                        if alias == 'leaf-symlink':
                            checked.symlink_to(other)
                        else:
                            os.link(other, checked)
                        return checked
                    with patch.object(bindings, 'safe_path', side_effect=swap), \
                         patch.object(bindings.os, 'read', side_effect=AssertionError('read before gate')) as read:
                        with self.assertRaises((RefreshError, OSError)):
                            read_metadata(replace(asset, path=str(target)))
                        read.assert_not_called()
                    selected.unlink()

    def test_directory_descriptor_is_rejected_before_read(self):
        spec, _ = authored()
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'receipt.json'; path.mkdir()
            with patch.object(bindings.os, 'read', side_effect=AssertionError('nonregular read')) as read:
                with self.assertRaisesRegex(RefreshError, 'metadata-regular-file-required'):
                    read_metadata(replace(spec.inputs[0], path=str(path)))
                read.assert_not_called()

    def test_field_origins_cover_known_and_explicit_unknowns(self):
        spec, loader = authored()
        spec = replace(spec, fields=tuple(replace(f, evidence='', selector='', unknown='not-held')
                                         if f.name == 'nativeBasis' else f for f in spec.fields))
        r = assess((spec,), as_of=AS_OF, loader=loader)
        row = r['manifest']['bindings'][0]['row']
        pins = {a.name: a.sha256 for a in spec.inputs}
        self.assertIsNone(row['data']['nativeBasis'])
        self.assertEqual(row['provenance']['fieldOrigins']['/data/nativeBasis']['kind'], 'constant')
        self.assertEqual(field_origin_errors(row, pins, policy_pins=(POLICY_SHA256,)), [])
        row['provenance']['fieldOrigins'].pop('/data/nativeUnit')
        self.assertIn('field-origin-inventory-mismatch', field_origin_errors(row, pins, policy_pins=(POLICY_SHA256,)))

    def test_malformed_semantics_are_typed_and_not_inferred(self):
        for name, value in [('country', 'YE'), ('release', 'other')]:
            spec, loader = authored()
            doc = json.loads(loader(spec.inputs[0])); doc[name] = value
            raw = canonical(doc); spec = replace(spec, inputs=(replace(spec.inputs[0], bytes=len(raw), sha256=sha(raw)),))
            r = assess((spec,), as_of=AS_OF, loader=lambda _: raw)
            self.assertEqual(r['diagnostics'][0]['status'], 'malformed')
        spec, loader = authored()
        r = assess((spec,), as_of='2026-09-30T00:00:00Z', loader=loader)
        self.assertIn({'code': 'original-acquisition-in-future'}, r['diagnostics'][0]['diagnostics'])

    def test_nonfinite_json_and_field_type_errors_do_not_escape_isolation(self):
        for raw in (b'{"x":NaN}', b'{"x":1e999}'):
            spec, _ = authored()
            spec = replace(spec, inputs=(replace(spec.inputs[0], bytes=len(raw), sha256=sha(raw)),))
            r = assess((spec,), as_of=AS_OF, loader=lambda _: raw)
            self.assertEqual(r['diagnostics'][0]['status'], 'malformed')
            canonical(r)
        spec, loader = authored()
        doc = json.loads(loader(spec.inputs[0])); doc['unit'] = 100
        raw = canonical(doc); spec = replace(spec, inputs=(replace(spec.inputs[0], bytes=len(raw), sha256=sha(raw)),))
        r = assess((spec,), as_of=AS_OF, loader=lambda _: raw)
        self.assertEqual(r['diagnostics'][0]['status'], 'malformed')

    def test_real_catalog_cannot_enable_acquisition_and_has_all_countries(self):
        self.assertEqual({s.country for s in SOURCES}, {'GG', 'NR', 'TM', 'YE'})
        for s in SOURCES:
            validate_binding(s)
            self.assertTrue(s.holds)
            self.assertTrue(all(a.path.endswith('.json') for a in s.inputs))
            gate = SourceSpec(s.key, s.url, POLICY_SHA256, s.inputs[-1].sha256,
                              enabled=False, rights_approved=False, held=True)
            with self.assertRaisesRegex(RefreshError, 'source-acquisition-gate-closed'):
                gate.validate()

    def test_shared_qualification_only_on_authored_metadata_fixture(self):
        """Demonstrate existing SourceContract bridge without accepting real data."""
        spec, loader = authored()
        row = self.report()['manifest']['bindings'][0]['row']
        row['provenance']['fetchedAt'] = '2026-10-01T00:00:00Z'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); bundle = root / 'bundle'; bundle.mkdir()
            docs = {spec.inputs[0].name: loader(spec.inputs[0]),
                    'rights.json': canonical({'fixture': True, 'permitted': 'authored-test-only'}),
                    'scope.json': canonical({'fixture': True, 'expectedIds': [row['id']]})}
            assets = []
            for name, raw in docs.items():
                path = bundle / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
                assets.append(acceptance.Asset(name, len(raw), sha(raw)))
            rights = next(a for a in assets if a.path == 'rights.json')
            scope = next(a for a in assets if a.path == 'scope.json')
            schemas = {'source-input-binding': {'type': 'object', 'required': ['id', 'kind', 'data', 'provenance'],
                       'properties': {'kind': {'const': 'source-input-binding'}, 'data': {'type': 'object'}}}}
            contract = acceptance.SourceContract(spec.source_id, spec.release_id, 'authored-metadata-only',
                '2026-10-01T00:00:00Z', tuple(assets), 1, acceptance.ids_digest([row['id']]),
                schemas, acceptance.fingerprint(schemas),
                lambda record: field_origin_errors(record, {spec.inputs[0].name: spec.inputs[0].sha256}, policy_pins=(POLICY_SHA256,)),
                POLICY_SHA256, rights, scope, frozenset(('retain', 'parse', 'transform')), fixture=True)
            content = canonical([row]); candidate = root / 'candidate.jsonl'; candidate.write_bytes(content)
            manifest = {'sourceId': spec.source_id, 'releaseId': spec.release_id,
                        'acquiredAt': contract.acquired_at, 'normalizedRecords': 1,
                        'rightsEvidenceSha256': rights.sha256, 'scopeEvidenceSha256': scope.sha256,
                        'inputFiles': [asdict(a) for a in assets],
                        'candidateBytes': len(content), 'candidateSha256': sha(content)}
            q = acceptance.qualify(contract, bundle, candidate, manifest)
            self.assertTrue(q['qualified'], q)
            self.assertTrue(q['fixture'])
            self.assertFalse(q.get('productionAccepted', False))
            changed = copy.deepcopy(row)
            changed['provenance']['fieldOrigins']['/data/nativeUnit']['inputSha256'] = '0' * 64
            candidate.write_bytes(canonical([changed]))
            q = acceptance.qualify(contract, bundle, candidate, manifest)
            self.assertFalse(q['qualified'])

    def test_isolated_cli_cases_and_no_force_override(self):
        for case in ('valid', 'missing', 'held', 'malformed', 'stale-input'):
            p = subprocess.run([sys.executable, '-B', '-m', 'offmenu.portfolio60', '--fixture', case,
                                '--as-of', AS_OF], capture_output=True, text=True, timeout=20)
            self.assertEqual(p.returncode, 0, p.stderr + p.stdout)
            d = json.loads(p.stdout)
            self.assertEqual(d['diagnostics'][0]['status'], case)
        p = subprocess.run([sys.executable, '-B', '-m', 'offmenu.portfolio60', '--fixture', 'valid',
                            '--as-of', AS_OF, '--force-download'], capture_output=True, text=True, timeout=20)
        self.assertNotEqual(p.returncode, 0)


if __name__ == '__main__':
    unittest.main()
