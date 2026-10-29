"""Synthetic source contracts only: unknown clocks never confer source rights."""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import test_product_origin_stage as stage_fixtures
from offmenu.refresh.acceptance import Asset, canonical, contract_fingerprint, fingerprint, qualify
from offmenu.refresh.core import RefreshError
from offmenu.refresh.product_origin_stage import qualify_product_origins


class RetainedProductClockTest(unittest.TestCase):
    def setUp(self):
        self.f = stage_fixtures.ProductOriginStageTest()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)

    def asset(self, name, value):
        p = self.f.f.bundle / name
        p.write_text(json.dumps(value, sort_keys=True))
        return Asset(name, p.stat().st_size, hashlib.sha256(p.read_bytes()).hexdigest())

    def unknown(self, source='off'):
        if source != 'off':
            self.f.configure(source)
        c = self.f.contract
        inputs = [a for a in c.inputs if a not in (c.rights_evidence, c.scope_evidence)]
        clock = self.asset('clock.json', {
            'schemaVersion': 'offmenu-retained-clock-evidence/1',
            'sourceId': c.source_id, 'releaseId': c.release_id, 'scopeId': c.scope_id,
            'status': 'unknown-retained', 'originalAcquiredAt': None,
            'basisEvidenceSha256': 'e' * 64,
            'rightsEvidenceSha256': c.rights_evidence.sha256,
            'inputFiles': [vars(a) for a in inputs]})
        scope = self.asset(c.scope_evidence.path, {
            'sourceId': c.source_id, 'releaseId': c.release_id, 'scopeId': c.scope_id,
            'acquisitionClock': {'status': 'unknown-retained', 'evidenceSha256': clock.sha256}})
        schema = json.loads((Path(__file__).parents[1] / 'contracts/schemas/retained-product-clock-v2.schema.json').read_text())
        schemas = {kind: {'allOf': [s, schema]} for kind, s in c.schemas.items()}
        self.f.contract = replace(c, acquired_at=None, acquisition_clock_status='unknown-retained',
            clock_evidence=clock, scope_evidence=scope,
            inputs=tuple(inputs + [c.rights_evidence, scope, clock]),
            schemas=schemas, schemas_sha256=fingerprint(schemas))
        return self.f.contract

    def test_off_unknown_roundtrip_origins_and_retry(self):
        c = self.unknown()
        first = self.f.run_stage()
        rows = self.f.assert_result(first)
        self.assertIsNone(first['manifest']['acquiredAt'])
        for row in rows:
            self.assertIsNone(row['provenance']['fetchedAt'])
            self.assertEqual(row['provenance']['acquisitionClock'],
                             {'status': 'unknown-retained', 'evidenceSha256': c.clock_evidence.sha256})
        self.assertEqual(first['qualification'], self.f.run_stage()['qualification'])
        self.assertFalse(first['manifest']['accepted'])

    def test_usda_unknown_roundtrip(self):
        self.unknown('usda-files')
        self.f.assert_result(self.f.run_stage())

    def test_known_null_naive_and_unknown_mode_fail_before_payload(self):
        for change in ({'acquired_at': None}, {'acquired_at': '2026-10-12'},
                       {'acquisition_clock_status': 'invented'}):
            with self.subTest(change=change), patch('offmenu.refresh.product_qualification.normalize_products') as normalize:
                self.f.contract = replace(self.f.f.contract, **change)
                with self.assertRaises(RefreshError):
                    self.f.run_stage()
                normalize.assert_not_called()

    def test_missing_clock_asset_rejected_before_payload(self):
        c = self.unknown()
        self.f.contract = replace(c, inputs=tuple(a for a in c.inputs if a != c.clock_evidence))
        with patch('offmenu.refresh.product_qualification.normalize_products') as normalize:
            with self.assertRaises(RefreshError):
                self.f.run_stage()
            normalize.assert_not_called()

    def test_changed_scope_or_evidence_binding_rejected(self):
        c = self.unknown()
        for field, value in (('scope_id', 'other-scope'), ('release_id', 'other-release'),
                             ('acquired_at', '2026-10-12T00:00:00Z')):
            with self.subTest(field=field):
                self.f.contract = replace(c, **{field: value})
                with self.assertRaises(RefreshError):
                    self.f.run_stage()

    def test_scope_declaration_must_match_pinned_clock(self):
        c = self.unknown()
        scope = self.asset(c.scope_evidence.path, {'sourceId': c.source_id,
            'releaseId': c.release_id, 'scopeId': c.scope_id,
            'acquisitionClock': {'status': 'unknown-retained', 'evidenceSha256': 'f' * 64}})
        self.f.contract = replace(c, scope_evidence=scope,
                                 inputs=tuple(scope if a == c.scope_evidence else a for a in c.inputs))
        with self.assertRaises(RefreshError):
            self.f.run_stage()

    def test_unknown_clock_does_not_relax_rights_or_holds(self):
        c = self.unknown()
        for change in ({'holds': ('held',)}, {'permitted_operations': frozenset(('retain',))}):
            self.f.contract = replace(c, **change)
            with self.assertRaises(RefreshError):
                self.f.run_stage()

    def test_unknown_clock_does_not_relax_counts(self):
        self.f.contract = replace(self.unknown(), expected_records=3)
        r = self.f.run_stage()
        self.assertFalse(r['qualification']['qualified'])
        self.assertIn('expected-record-count-mismatch', r['qualification']['errors'])

    def test_manifest_clock_cannot_grant_unknown_mode(self):
        c = self.unknown()
        r = self.f.run_stage()
        for contract, manifest in ((replace(c, acquisition_clock_status='known'), r['manifest']),
                                   (c, {**r['manifest'], 'acquisitionClock': {'status': 'unknown-retained', 'evidenceSha256': 'f'*64}})):
            result = qualify(contract, self.f.f.bundle, r['candidate'], manifest)
            self.assertFalse(result['qualified'])

    def test_contract_fingerprint_and_context_retry_bind_clock(self):
        c = self.unknown()
        r = self.f.run_stage()
        self.assertNotEqual(contract_fingerprint(c), contract_fingerprint(replace(c, acquisition_clock_status='known')))
        # Existing known output must never be reused as an unknown-clock output.
        with self.assertRaises(RefreshError):
            qualify_product_origins(self.f.f.contract, self.f.f.bundle, self.f.roles,
                self.f.f.root/'normalized', self.f.f.root/'other', license='fixture terms', attribution='fixture source')
        self.assertFalse(r['manifest']['accepted'])

    def test_tampered_record_clock_rejected_even_with_rehashed_candidate(self):
        c = self.unknown()
        r = self.f.run_stage()
        rows = [json.loads(line) for line in r['candidate'].read_text().splitlines()]
        for mutation in ('missing-time', 'wrong-proof', 'fabricated-date'):
            packets = json.loads(json.dumps(rows))
            provenance = packets[0][0]['provenance']
            if mutation == 'missing-time':
                provenance.pop('fetchedAt')
            elif mutation == 'wrong-proof':
                provenance['acquisitionClock']['evidenceSha256'] = 'f' * 64
            else:
                provenance['fetchedAt'] = '2026-10-12T00:00:00Z'
            data = b''.join(canonical(p) + b'\n' for p in packets)
            target = self.f.f.root / (mutation + '.jsonl')
            target.write_bytes(data)
            manifest = {**r['manifest'], 'candidateSha256': hashlib.sha256(data).hexdigest(),
                        'candidateBytes': len(data)}
            result = qualify(c, self.f.f.bundle, target, manifest)
            self.assertFalse(result['qualified'], mutation)

    def test_unknown_manifest_requires_explicit_null_time(self):
        c = self.unknown()
        r = self.f.run_stage()
        manifest = dict(r['manifest'])
        manifest.pop('acquiredAt')
        self.assertIn('manifest-contract-mismatch', qualify(c, self.f.f.bundle, r['candidate'], manifest)['errors'])

    def test_input_pin_is_bound_by_clock_evidence_before_parse(self):
        c = self.unknown()
        original = c.inputs[0]
        self.f.contract = replace(c, inputs=tuple(replace(a, sha256='f'*64) if a == original else a for a in c.inputs))
        with patch('offmenu.refresh.product_qualification.normalize_products') as normalize:
            with self.assertRaises(RefreshError):
                self.f.run_stage()
            normalize.assert_not_called()

    def test_prices_cannot_select_retained_unknown_protocol(self):
        self.f.contract = replace(self.unknown(), source_id='prices')
        with self.assertRaises(RefreshError):
            self.f.run_stage()

    def test_known_mode_rejects_unknown_marker_and_short_ttl(self):
        from offmenu.refresh.product_adapters import ProductContext
        context = ProductContext('off', 'fixture', '2026-10-12T00:00:00Z',
                                 'fixture', 'fixture', 'a'*64, 'b'*64)
        for change in ({'clock_evidence_sha256': 'e'*64}, {'cache_seconds': 0}):
            with self.assertRaises(RefreshError):
                replace(context, **change).validate()

    def test_changed_clock_evidence_bytes_cannot_be_used(self):
        self.unknown()
        (self.f.f.bundle/'clock.json').write_text('{}')
        with self.assertRaises(RefreshError):
            self.f.run_stage()

    def test_parser_only_receives_the_verified_bounded_buffer(self):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        real_read, real_json = Path.read_bytes, core.strict_json
        for asset in (c.clock_evidence, c.scope_evidence):
            target = self.f.f.bundle / asset.path
            original = real_read(target)
            changed = json.loads(original)
            changed['syntheticPadding'] = 'x' * (2 * product_clock.MAX_EVIDENCE_BYTES)
            replacement = canonical(changed)
            parsed = []
            def reopen(path):
                return replacement if path == target else real_read(path)
            def parse(raw):
                parsed.append(raw)
                return real_json(raw)
            with patch.object(Path, 'read_bytes', reopen), patch.object(core, 'strict_json', side_effect=parse):
                product_clock.validate_contract_clock(c, self.f.f.bundle)
            self.assertTrue(parsed)
            self.assertTrue(all(len(raw) <= product_clock.MAX_EVIDENCE_BYTES for raw in parsed))
            self.assertIn(original, parsed)

    def assert_metadata_mutation_rejected(self, mode):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        target = self.f.f.bundle / c.clock_evidence.path
        original = target.read_bytes()
        replacement = self.f.f.root / 'replacement.json'
        replacement.write_bytes(original)
        real_read = os.read
        changed = False
        def mutate(fd, size):
            nonlocal changed
            data = real_read(fd, size)
            if not changed:
                changed = True
                if mode == 'grow':
                    target.write_bytes(original + b'x' * (2 * product_clock.MAX_EVIDENCE_BYTES))
                elif mode == 'replace':
                    os.replace(replacement, target)
                else:
                    target.unlink()
                    target.symlink_to(replacement)
            return data
        with patch.object(product_clock.os, 'read', side_effect=mutate), \
                patch.object(core, 'strict_json') as parse, \
                patch('offmenu.refresh.product_qualification.normalize_products') as payload:
            with self.assertRaises(RefreshError):
                self.f.run_stage()
            parse.assert_not_called()
            payload.assert_not_called()

    def test_metadata_growth_during_read_rejected(self):
        self.assert_metadata_mutation_rejected('grow')

    def test_same_byte_metadata_inode_replacement_rejected(self):
        self.assert_metadata_mutation_rejected('replace')

    def test_metadata_symlink_replacement_rejected(self):
        self.assert_metadata_mutation_rejected('symlink')

    def test_nonregular_symlink_and_oversize_metadata_never_parse(self):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        target = self.f.f.bundle / c.clock_evidence.path
        original = target.read_bytes()
        replacement = self.f.f.root / 'replacement.json'
        replacement.write_bytes(original)
        for mode in ('directory', 'fifo', 'symlink', 'oversize'):
            with self.subTest(mode=mode):
                target.unlink()
                if mode == 'directory':
                    target.mkdir()
                elif mode == 'fifo':
                    os.mkfifo(target)
                elif mode == 'symlink':
                    target.symlink_to(replacement)
                else:
                    target.write_bytes(b'x' * (product_clock.MAX_EVIDENCE_BYTES + 1))
                with patch.object(core, 'strict_json') as parse:
                    with self.assertRaises(ValueError):
                        product_clock.validate_contract_clock(c, self.f.f.bundle)
                    parse.assert_not_called()
                target.rmdir() if mode == 'directory' else target.unlink()
                target.write_bytes(original)

    def test_metadata_growth_at_open_rejected_before_read(self):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        target = self.f.f.bundle / c.clock_evidence.path
        original = target.read_bytes()
        real_open = os.open
        def grow(path, flags):
            fd = real_open(path, flags)
            target.write_bytes(original + b'x')
            return fd
        with patch.object(product_clock.os, 'open', side_effect=grow), \
                patch.object(product_clock.os, 'read') as read, patch.object(core, 'strict_json') as parse:
            with self.assertRaises(ValueError):
                product_clock.validate_contract_clock(c, self.f.f.bundle)
            read.assert_not_called()
            parse.assert_not_called()

    def test_maximum_sized_verified_buffer_parses_without_reopen(self):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        clock = json.loads((self.f.f.bundle / c.clock_evidence.path).read_bytes())
        clock['syntheticPadding'] = ''
        empty = json.dumps(clock, sort_keys=True).encode()
        clock['syntheticPadding'] = 'x' * (product_clock.MAX_EVIDENCE_BYTES - len(empty))
        evidence = self.asset(c.clock_evidence.path, clock)
        self.assertEqual(evidence.bytes, product_clock.MAX_EVIDENCE_BYTES)
        scope = self.asset(c.scope_evidence.path, {'sourceId': c.source_id, 'releaseId': c.release_id,
            'scopeId': c.scope_id, 'acquisitionClock': {'status': 'unknown-retained', 'evidenceSha256': evidence.sha256}})
        contract = replace(c, clock_evidence=evidence, scope_evidence=scope,
            inputs=tuple(evidence if a == c.clock_evidence else scope if a == c.scope_evidence else a for a in c.inputs))
        real_json, real_read = core.strict_json, os.read
        lengths, requests = [], []
        def parse(raw):
            lengths.append(len(raw))
            return real_json(raw)
        def read(fd, size):
            requests.append(size)
            return real_read(fd, size)
        with patch.object(core, 'strict_json', side_effect=parse), patch.object(product_clock.os, 'read', side_effect=read):
            product_clock.validate_contract_clock(contract, self.f.f.bundle)
        self.assertEqual(lengths, [product_clock.MAX_EVIDENCE_BYTES, scope.bytes])
        self.assertTrue(all(0 < n <= 65536 for n in requests))

    def test_same_size_wrong_hash_metadata_rejected_before_parse(self):
        from offmenu.refresh import core, product_clock
        c = self.unknown()
        target = self.f.f.bundle / c.clock_evidence.path
        original = target.read_bytes()
        target.write_bytes(b'[' + original[1:])
        with patch.object(core, 'strict_json') as parse:
            with self.assertRaises(ValueError):
                product_clock.validate_contract_clock(c, self.f.f.bundle)
            parse.assert_not_called()


class USDAExactAliasTest(unittest.TestCase):
    def test_exact_archive_alias_only(self):
        from offmenu.refresh.product_clock import resolve_retained_usda_release
        asset = Asset('FoodData_Central_csv_2026-04-30.zip', 481517495,
                      'c33d91e5c44ddbcd71ed6038714fb648b26089b3f91fabfa3be63d96d5763a01')
        for alias in (None, 'usda-2026-04', '2026-04', '2026-04-30'):
            self.assertEqual(resolve_retained_usda_release(alias, asset), '2026-04-30')
        for wrong in (replace(asset, bytes=1), replace(asset, sha256='a'*64),
                      replace(asset, path='FoodData_Central_csv_2026-04-29.zip')):
            with self.assertRaises(ValueError):
                resolve_retained_usda_release('2026-04', wrong)
        with self.assertRaises(ValueError):
            resolve_retained_usda_release('2026-05', asset)
