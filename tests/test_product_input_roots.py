"""Synthetic in-place originals remain separate from exact reviewed evidence."""
from dataclasses import asdict, replace
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_product_qualification as fixtures
import test_product_origin_stage as origin_fixtures
from offmenu.refresh.acceptance import Asset, accept, qualify, ids_digest
from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_qualification import qualify_product_candidate
from offmenu.refresh.product_origin_stage import qualify_product_origins


class ProductInputRootsTest(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.ProductQualificationTest()
        self.f.setUp()
        self.addCleanup(self.f.tearDown)
        self.contract = self.f.contract
        self.roles = {'products': 'data/products.gz'}
        self.inputs = self.f.root / 'originals'
        (self.inputs / 'data').mkdir(parents=True)
        self.source = self.inputs / 'data/products.gz'
        self.f.source.rename(self.source)
        (self.f.bundle / 'data').rmdir()
        # These unrelated files must never be inventoried or opened.
        os.mkfifo(self.inputs / 'unrelated.fifo')
        (self.inputs / 'unrelated-link').symlink_to('/nonexistent')

    def run_bridge(self, **kwargs):
        return qualify_product_candidate(self.contract, self.f.bundle, self.roles,
            self.f.root / 'normalized', license='fixture', attribution='fixture',
            input_root=self.inputs, **kwargs)

    def test_off_qualifies_retries_and_accepts_without_source_materialization(self):
        before = self.source.read_bytes()
        evidence = {p.name: p.read_bytes() for p in self.f.bundle.iterdir()}
        result = self.run_bridge()
        self.assertTrue(result['qualification']['qualified'], result['qualification']['errors'])
        self.assertFalse(result['manifest']['accepted'])
        self.assertEqual(result['qualification'], self.run_bridge()['qualification'])
        receipt = accept(self.contract, self.f.bundle, result['candidate'], result['manifest'],
                         input_root=self.inputs)
        self.assertEqual(receipt['status'], 'accepted-fixture-scope')
        self.assertFalse(receipt['productionAccepted'])
        self.assertEqual(self.source.read_bytes(), before)
        self.assertEqual({p.name: p.read_bytes() for p in self.f.bundle.iterdir()}, evidence)
        self.assertEqual(len(result['manifest']['inputFiles']), 3)
        self.assertEqual(len(json.loads((self.f.root/'normalized/manifest.json').read_text())['inputFiles']), 1)

    def test_unknown_retained_clock_uses_evidence_root(self):
        def write_asset(name, value):
            p = self.f.bundle / name
            p.write_text(json.dumps(value))
            return Asset(name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())
        c = self.contract
        clock = write_asset('clock.json', {
            'schemaVersion': 'offmenu-retained-clock-evidence/1', 'sourceId': c.source_id,
            'releaseId': c.release_id, 'scopeId': c.scope_id, 'status': 'unknown-retained',
            'originalAcquiredAt': None, 'basisEvidenceSha256': 'b'*64,
            'rightsEvidenceSha256': c.rights_evidence.sha256, 'inputFiles': [asdict(c.inputs[0])]})
        scope = write_asset('scope.txt', {'sourceId': c.source_id, 'releaseId': c.release_id,
            'scopeId': c.scope_id, 'acquisitionClock': {'status': 'unknown-retained',
                                                     'evidenceSha256': clock.sha256}})
        self.contract = replace(c, acquired_at=None, acquisition_clock_status='unknown-retained',
            clock_evidence=clock, scope_evidence=scope,
            inputs=(c.inputs[0], c.rights_evidence, scope, clock))
        result = self.run_bridge()
        self.assertTrue(result['qualification']['qualified'], result['qualification']['errors'])
        self.assertIsNone(result['manifest']['acquiredAt'])

    def test_extra_evidence_rejected_before_parser(self):
        (self.f.bundle / 'extra').write_text('not selected')
        with patch('offmenu.refresh.product_qualification.normalize_products') as parser:
            with self.assertRaises(RefreshError):
                self.run_bridge()
            parser.assert_not_called()

    def test_wrong_root_has_no_fallback_to_bundle(self):
        wrong = self.f.root / 'wrong'
        wrong.mkdir()
        with self.assertRaises((RefreshError, ValueError, OSError)):
            qualify_product_candidate(self.contract, self.f.bundle, self.roles,
                self.f.root/'bad', license='fixture', attribution='fixture', input_root=wrong)
        self.assertFalse((self.f.root/'bad').exists())

    def test_selected_source_and_source_root_symlinks_rejected(self):
        saved = self.source.with_suffix('.saved')
        self.source.rename(saved)
        self.source.symlink_to(saved)
        with self.assertRaises((RefreshError, ValueError)):
            self.run_bridge()
        self.source.unlink()
        saved.rename(self.source)
        link = self.f.root / 'linked-root'
        link.symlink_to(self.inputs, target_is_directory=True)
        with self.assertRaises((RefreshError, ValueError)):
            qualify_product_candidate(self.contract, self.f.bundle, self.roles,
                self.f.root/'bad', license='fixture', attribution='fixture', input_root=link)

    def test_nonregular_selected_source_rejected_without_open(self):
        self.source.unlink()
        os.mkfifo(self.source)
        original_open = Path.open
        def guarded_open(path, *args, **kwargs):
            self.assertNotEqual(path, self.source, 'must not open FIFO')
            return original_open(path, *args, **kwargs)
        with patch.object(Path, 'open', guarded_open):
            with self.assertRaises((RefreshError, ValueError, OSError)):
                self.run_bridge()

    def test_original_and_evidence_hash_mismatches_reject_before_parse(self):
        for path in [self.source, self.f.bundle/'rights.txt']:
            with self.subTest(path=path.name):
                before = path.read_bytes()
                path.write_bytes(before+b'changed')
                with patch('offmenu.refresh.product_qualification.normalize_products') as parser:
                    with self.assertRaises(RefreshError):
                        self.run_bridge()
                    parser.assert_not_called()
                path.write_bytes(before)

    def test_missing_role_held_and_public_contracts_stay_blocked(self):
        with patch('offmenu.refresh.product_qualification.normalize_products') as parser:
            for c in [replace(self.contract, holds=('actual-hold',)),
                      replace(self.contract, permitted_operations=frozenset(('retain',))),
                      replace(self.contract, output_visibility='public')]:
                with self.subTest(contract=c):
                    with self.assertRaises(RefreshError):
                        qualify_product_candidate(c, self.f.bundle, self.roles, self.f.root/'bad',
                            license='fixture', attribution='fixture', input_root=self.inputs)
            with self.assertRaises(RefreshError):
                qualify_product_candidate(self.contract, self.f.bundle, {}, self.f.root/'bad',
                    license='fixture', attribution='fixture', input_root=self.inputs)
            parser.assert_not_called()

    def test_overlapping_roots_and_outputs_rejected(self):
        for root in [self.f.bundle, self.f.root]:
            with self.subTest(root=root):
                with self.assertRaises((RefreshError, ValueError)):
                    qualify_product_candidate(self.contract, self.f.bundle, self.roles,
                        self.f.root/'bad', license='fixture', attribution='fixture', input_root=root)
        for destination in [self.inputs/'output', self.inputs, self.f.root]:
            with self.subTest(destination=destination):
                with self.assertRaises(RefreshError):
                    qualify_product_candidate(self.contract, self.f.bundle, self.roles,
                        destination, license='fixture', attribution='fixture', input_root=self.inputs)

    def test_acceptance_rechecks_original_bytes_and_never_qualifies_wrong_ids(self):
        result = self.run_bridge()
        self.source.write_bytes(self.source.read_bytes()+b'changed')
        receipt = qualify(self.contract, self.f.bundle, result['candidate'], result['manifest'],
                          input_root=self.inputs)
        self.assertFalse(receipt['qualified'])
        self.assertIn('input-custody-mismatch', receipt['errors'])

    def test_independent_ids_and_nonproduct_scope_cannot_use_split_mode(self):
        result = self.run_bridge()
        bad = replace(self.contract, expected_ids_sha256=ids_digest(['wrong']))
        receipt = qualify(bad, self.f.bundle, result['candidate'], result['manifest'], input_root=self.inputs)
        self.assertFalse(receipt['qualified'])
        self.assertIn('expected-record-identities-mismatch', receipt['errors'])
        for c in [replace(self.contract, source_id='prices'),
                  replace(self.contract, output_scope='curated')]:
            receipt = qualify(c, self.f.bundle, result['candidate'], result['manifest'], input_root=self.inputs)
            self.assertFalse(receipt['qualified'])

    def test_acceptance_scratch_cannot_be_written_inside_originals(self):
        result = self.run_bridge()
        receipt = qualify(self.contract, self.f.bundle, result['candidate'], result['manifest'],
                          input_root=self.inputs, scratch_root=self.inputs)
        self.assertFalse(receipt['qualified'])
        self.assertEqual(sorted(p.name for p in self.inputs.iterdir()),
                         ['data', 'unrelated-link', 'unrelated.fifo'])

    def test_mutation_during_normalization_is_held_by_requalification(self):
        from offmenu.refresh.product_qualification import normalize_products
        def changed(*args, **kwargs):
            result = normalize_products(*args, **kwargs)
            self.source.write_bytes(self.source.read_bytes()+b'changed')
            return result
        with patch('offmenu.refresh.product_qualification.normalize_products', changed):
            result = self.run_bridge()
        self.assertFalse(result['qualification']['qualified'])
        self.assertIn('input-custody-mismatch', result['qualification']['errors'])

    def test_missing_independent_count_is_not_filled_from_parser(self):
        self.contract = replace(self.contract, expected_records=None)
        result = self.run_bridge()
        self.assertFalse(result['qualification']['qualified'])
        self.assertFalse(result['manifest']['accepted'])


class ProductOriginInputRootsTest(unittest.TestCase):
    def setUp(self):
        self.f = origin_fixtures.ProductOriginStageTest()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def split_and_run(self, source='off'):
        if source != 'off':
            self.f.configure(source)
        root = self.f.f.root / 'originals'
        root.mkdir()
        for relative in self.f.roles.values():
            target = root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            (self.f.f.bundle / relative).rename(target)
        (self.f.f.bundle / 'data').rmdir()
        (root / 'unrelated').write_text('not an input')
        self.root = root
        return self.run_stage()

    def run_stage(self):
        return qualify_product_origins(self.f.contract, self.f.f.bundle, self.f.roles,
            self.f.f.root/'normalized', self.f.f.root/'enriched', license='fixture',
            attribution='fixture', input_root=self.root)

    def test_off_origins_and_retry_keep_exact_relative_pins(self):
        first = self.split_and_run()
        self.f.assert_result(first)
        self.assertEqual(first['manifest'], self.run_stage()['manifest'])
        self.assertEqual(first['manifest']['originStageContract']['inputPins']['products']['path'],
                         'data/products.gz')

    def test_usda_archive_members_are_read_from_input_root(self):
        result = self.split_and_run('usda-files')
        self.f.assert_result(result)
        self.assertEqual(result['manifest']['originStageContract']['archiveMembers']['food'],
                         'FoodData_Central/food.csv')
        self.assertEqual(result['qualification'], self.run_stage()['qualification'])

    def test_origins_refuse_output_inside_originals_before_normalization(self):
        self.split_and_run()
        with patch('offmenu.refresh.product_origin_stage.qualify_product_candidate') as bridge:
            with self.assertRaisesRegex(RefreshError, 'path-overlap'):
                qualify_product_origins(self.f.contract, self.f.f.bundle, self.f.roles,
                    self.f.f.root/'normalized2', self.root/'bad', license='fixture',
                    attribution='fixture', input_root=self.root)
            bridge.assert_not_called()

    def test_mutation_during_origin_emission_rejected_and_source_preserved(self):
        from offmenu.refresh.product_field_origins import ProductOriginEmitter
        original_emit = ProductOriginEmitter.emit
        def changed(emitter, row):
            result = original_emit(emitter, row)
            source = self.root / next(iter(self.f.roles.values()))
            source.write_bytes(source.read_bytes()+b'changed')
            return result
        self.root = self.f.f.root / 'originals'
        with patch.object(ProductOriginEmitter, 'emit', changed):
            with self.assertRaisesRegex(RefreshError, 'input-changed'):
                self.split_and_run()
        self.assertTrue((self.f.f.root/'normalized/manifest.json').exists())
        self.assertFalse((self.f.f.root/'enriched').exists())
        self.assertEqual(list(self.f.f.root.glob('.product-origins-*')), [])


if __name__ == '__main__':
    unittest.main()
