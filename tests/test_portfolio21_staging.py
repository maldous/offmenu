"""Authored fixtures only: no retained source bodies or network access."""
from dataclasses import replace
import gzip
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from offmenu.portfolio21.bindings import (
    BINDINGS, MAX_METADATA_BYTES, MetadataBinding, PRICE_SELECTORS, audit_metadata,
    pointer, reuse_plan, stage_authored_prices, write_report,
)
from offmenu.refresh.acceptance import Asset, SourceContract, fingerprint, ids_digest
from offmenu.refresh.core import RefreshError, canonical, sha
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors

AS_OF = '2026-10-18T00:00:00Z'


class MetadataBindingsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def binding(self, name, body, *, holds=(), expected=()):
        raw = body if isinstance(body, bytes) else canonical(body)
        (self.root / (name + '.json')).write_bytes(raw)
        return MetadataBinding(name, 'MD', name + '.json', sha(raw), 'authored',
                               ('/release', '/nested/a~1b', '/missing'), holds, expected)

    def audit(self, *bindings):
        return audit_metadata(self.root, as_of=AS_OF, bindings=bindings)

    def test_valid_missing_held_malformed_stale_isolation(self):
        valid = self.binding('valid', {'release': 'fixture', 'nested': {'a/b': None}})
        missing = replace(valid, key='missing', path='absent.json')
        held = self.binding('held', {'release': 'fixture'}, holds=('rights-held',))
        malformed = self.binding('malformed', b'{"duplicate":1,"duplicate":2}')
        stale = self.binding('stale', {'release': 'old'}, expected=(('/release', 'new'),))
        report = self.audit(valid, missing, held, malformed, stale)
        rows = report['bindings']
        self.assertEqual([r['metadata']['code'] for r in rows], [
            'metadata-pin-verified', 'metadata-missing', 'metadata-pin-verified',
            'metadata-malformed', 'metadata-stale-release'])
        self.assertEqual(rows[0]['selectedFields']['/nested/a~1b'], {'present': True, 'value': None})
        self.assertEqual(rows[0]['selectedFields']['/missing'], {'present': False})
        self.assertEqual(rows[2]['holds'], ['rights-held'])
        self.assertTrue(all(not r['accepted'] and not r['countryComplete'] for r in rows))
        self.assertEqual(report['sourceBodiesRead'], 0)
        self.assertEqual(report['networkRequests'], 0)
        self.assertEqual(report['sharedCapabilities']['pureCachePlanner'], 'absent-at-pinned-base')

    def test_pin_mismatch_stops_before_later_input(self):
        item = self.binding('changed', {})
        (self.root / item.path).write_bytes(b'{}')
        later = replace(item, path='../never.json')
        with self.assertRaisesRegex(RefreshError, 'portfolio-metadata-pin-mismatch'):
            self.audit(item, later)

    def test_budget_stops_before_reading_oversize_metadata(self):
        item = self.binding('large', b'x' * (MAX_METADATA_BYTES + 1))
        with self.assertRaisesRegex(RefreshError, 'portfolio-metadata-budget-exhausted'):
            self.audit(item)
        a = self.binding('a', b'x' * (MAX_METADATA_BYTES // 2 + 1))
        b = self.binding('b', b'x' * (MAX_METADATA_BYTES // 2 + 1))
        with self.assertRaisesRegex(RefreshError, 'portfolio-metadata-budget-exhausted'):
            self.audit(a, b)

    def test_never_follows_body_or_rights_paths_and_replay_preserves_difference(self):
        item = self.binding('receipt', {'release': 'fixture', 'original_path': '/never-open',
                            'rights_evidence': '/never-open', 'requests': [{'path': '/never-open'}]})
        first = self.audit(item)
        target = self.root / 'report.json'
        self.assertEqual(write_report(first, target), 'written')
        before = target.stat().st_mtime_ns
        self.assertEqual(write_report(self.audit(item), target), 'reused')
        self.assertEqual(before, target.stat().st_mtime_ns)
        with self.assertRaisesRegex(RefreshError, 'portfolio-existing-report-differs'):
            write_report({**first, 'asOf': 'different'}, target)
        self.assertEqual(target.read_bytes(), canonical(first))

    def test_paths_and_symlinks_rejected(self):
        item = self.binding('valid', {})
        for path in ('../body.json', '/body.json', 'body.csv', 'a/../valid.json'):
            with self.assertRaisesRegex(RefreshError, 'portfolio-unsafe-metadata-path'):
                self.audit(replace(item, path=path))
        (self.root / 'link.json').symlink_to(self.root / item.path)
        with self.assertRaisesRegex(RefreshError, 'symlink-path-rejected'):
            self.audit(replace(item, path='link.json'))

    def bounded_probe(self, code):
        result = subprocess.run([sys.executable, '-c', code, str(self.root)],
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_fifo_metadata_is_nonblocking_and_valid_peer_progresses(self):
        valid = self.binding('valid', {})
        os.mkfifo(self.root / 'pipe.json')
        report = self.bounded_probe("""
import sys,json
from offmenu.portfolio21.bindings import MetadataBinding,audit_metadata
from offmenu.refresh.core import sha
bindings=(MetadataBinding('pipe','MD','pipe.json','0'*64,'authored',(),()),
          MetadataBinding('peer','MD','valid.json',sha(b'{}\\n'),'authored',(),()))
print(json.dumps(audit_metadata(sys.argv[1],as_of='2026-10-18T00:00:00Z',bindings=bindings)))
""")
        self.assertEqual([r['metadata']['code'] for r in report['bindings']],
                         ['metadata-not-regular', 'metadata-pin-verified'])
        self.assertEqual(report['metadataBytesRead'], 3)
        self.assertTrue((self.root / 'pipe.json').is_fifo())

    def test_fifo_existing_report_is_nonblocking_rejected_and_preserved(self):
        os.mkfifo(self.root / 'report.json')
        result = self.bounded_probe("""
import sys,json
from pathlib import Path
from offmenu.portfolio21.bindings import write_report
from offmenu.refresh.core import RefreshError
try:
    write_report({},Path(sys.argv[1])/'report.json')
except RefreshError as error:
    print(json.dumps({'error':str(error)}))
""")
        self.assertEqual(result, {'error': 'portfolio-file-not-regular'})
        self.assertTrue((self.root / 'report.json').is_fifo())

    def test_directory_and_large_report_rejected_without_read(self):
        valid = self.binding('valid', {})
        (self.root / 'directory.json').mkdir()
        report = self.audit(replace(valid, path='directory.json'), valid)
        self.assertEqual(report['bindings'][0]['metadata']['code'], 'metadata-not-regular')
        self.assertEqual(report['bindings'][1]['metadata']['code'], 'metadata-pin-verified')
        with self.assertRaisesRegex(RefreshError, 'portfolio-file-not-regular'):
            write_report({}, self.root / 'directory.json')
        large = self.root / 'large-report.json'
        large.write_bytes(b'x' * (MAX_METADATA_BYTES + 1))
        with patch('offmenu.portfolio21.bindings.os.read', side_effect=AssertionError('must not read')):
            with self.assertRaisesRegex(RefreshError, 'portfolio-report-too-large'):
                write_report({}, large)
        self.assertEqual(large.stat().st_size, MAX_METADATA_BYTES + 1)

    def test_replacement_during_read_is_isolated_and_bytes_counted(self):
        item = self.binding('racy', {})
        peer = self.binding('peer', {})
        original_read = os.read
        swapped = False
        def replace_after_read(fd, size):
            nonlocal swapped
            raw = original_read(fd, size)
            if not swapped:
                swapped = True
                (self.root / item.path).unlink()
                (self.root / item.path).write_bytes(raw)
            return raw
        with patch('offmenu.portfolio21.bindings.os.read', side_effect=replace_after_read):
            report = self.audit(item, peer)
        self.assertEqual([r['metadata']['code'] for r in report['bindings']],
                         ['metadata-changed', 'metadata-pin-verified'])
        self.assertEqual(report['metadataBytesRead'], 6)

    def test_same_size_mutation_is_isolated(self):
        item = self.binding('racy', {})
        peer = self.binding('peer', {})
        original_read = os.read
        mutated = False
        def mutate_after_read(fd, size):
            nonlocal mutated
            raw = original_read(fd, size)
            if not mutated:
                mutated = True
                target = self.root / item.path
                prior = target.stat()
                target.write_bytes(b'[]\n')
                os.utime(target, ns=(prior.st_atime_ns, prior.st_mtime_ns + 1000000000))
            return raw
        with patch('offmenu.portfolio21.bindings.os.read', side_effect=mutate_after_read):
            report = self.audit(item, peer)
        self.assertEqual([r['metadata']['code'] for r in report['bindings']],
                         ['metadata-changed', 'metadata-pin-verified'])
        self.assertEqual(report['metadataBytesRead'], 6)

    def test_final_symlink_substitution_rejected_and_descriptors_closed(self):
        item = self.binding('racy', {})
        peer = self.binding('peer', {})
        original_open = os.open
        opened = []
        def swap_before_open(name, flags, *args, **kwargs):
            if name == 'racy.json':
                self.assertTrue(flags & os.O_NONBLOCK)
                self.assertTrue(flags & os.O_NOFOLLOW)
                (self.root / item.path).unlink()
                (self.root / item.path).symlink_to(self.root / peer.path)
            fd = original_open(name, flags, *args, **kwargs)
            opened.append(fd)
            return fd
        with patch('offmenu.portfolio21.bindings.os.open', side_effect=swap_before_open):
            report = self.audit(item, peer)
        self.assertEqual([r['metadata']['code'] for r in report['bindings']],
                         ['metadata-unreadable', 'metadata-pin-verified'])
        for fd in set(opened):
            with self.assertRaises(OSError):
                os.fstat(fd)

    def test_parent_symlink_substitution_does_not_follow_target(self):
        item = self.binding('valid', {})
        nested = self.root / 'nested'
        nested.mkdir()
        original_open = os.open
        def swap_before_open(name, flags, *args, **kwargs):
            if name == 'nested':
                nested.rmdir()
                nested.symlink_to(self.root, target_is_directory=True)
            return original_open(name, flags, *args, **kwargs)
        with patch('offmenu.portfolio21.bindings.os.open', side_effect=swap_before_open):
            report = self.audit(replace(item, path='nested/valid.json'), item)
        self.assertEqual([r['metadata']['code'] for r in report['bindings']],
                         ['metadata-unreadable', 'metadata-pin-verified'])

    def test_pointer_rejects_noncanonical_array_tokens_and_bad_escapes(self):
        value = {'items': ['first', 'last'], '01': 'object-key', 'a/b': {'~': None}}
        for token in ('-1', '01', '+1', '-', '1.0', '\u0661'):
            self.assertEqual(pointer(value, '/items/' + token), {'present': False})
        for selector in ('items/0', '/a~2b', '/a~', None):
            self.assertEqual(pointer(value, selector), {'present': False})
        self.assertEqual(pointer(value, '/items/0'), {'present': True, 'value': 'first'})
        self.assertEqual(pointer(value, '/items/1'), {'present': True, 'value': 'last'})
        self.assertEqual(pointer(value, '/01'), {'present': True, 'value': 'object-key'})
        self.assertEqual(pointer(value, '/a~1b/~0'), {'present': True, 'value': None})
        self.assertEqual(pointer(value, ''), {'present': True, 'value': value})

    def test_portfolio_has_all_four_countries_and_all_sources_held(self):
        self.assertEqual({b.country for b in BINDINGS}, {'MD', 'SJ', 'TD', 'UM'})
        self.assertEqual(len({b.path for b in BINDINGS}), len(BINDINGS))
        self.assertTrue(all(b.holds for b in BINDINGS))
        self.assertIn('access-denied-no-retry', next(b for b in BINDINGS if b.country == 'UM').holds)

    def test_cache_age_uses_original_acquisition_not_validation(self):
        old = reuse_plan('2026-09-01T00:00:00Z', '2026-10-17T00:00:00Z', AS_OF)
        self.assertEqual(old['acquisitionAgeSeconds'], 47 * 86400)
        self.assertEqual(old['validationAgeSeconds'], 86400)
        self.assertEqual(old['decision'], 'reuse-pinned-cache-no-fetch')
        self.assertFalse(old['refreshAuthorization'])
        boundary = reuse_plan('2026-09-18T00:00:00Z', AS_OF, AS_OF)
        self.assertFalse(boundary['withinMinimumReuseWindow'])
        self.assertEqual(boundary['minimumReuseSeconds'], 30 * 86400)
        young = reuse_plan('2026-09-18T00:00:01Z', AS_OF, AS_OF)
        self.assertTrue(young['withinMinimumReuseWindow'])
        unknown = reuse_plan(None, None, AS_OF)
        self.assertIsNone(unknown['acquisitionAgeSeconds'])
        self.assertEqual(unknown['decision'], 'acquisition-time-required')
        with self.assertRaises(RefreshError):
            reuse_plan('2026-10-19T00:00:00Z', None, AS_OF)
        with self.assertRaises(RefreshError):
            reuse_plan(AS_OF, '2026-10-17T00:00:00Z', AS_OF)


class AuthoredPricesStagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bundle = self.root / 'bundle'
        self.bundle.mkdir()
        self.price = {'id': 1, 'product_code': '1234', 'price': '0.00', 'currency': 'MDL',
                      'date': '2026-10-01', 'location_id': 2, 'proof_id': 3,
                      'price_per': None, 'price_per_unit': None, 'price_without_discount': None,
                      'price_is_discounted': False, 'duplicate_of': None}
        self.location = {'id': 2, 'osm_name': 'Authored store', 'osm_address_country_code': 'md',
                         'osm_display_name': 'Authored location'}
        for role, row in [('prices', self.price), ('locations', self.location), ('proofs', {'id': 3})]:
            # Stable authored gzip bytes; no real retained source input is used.
            (self.bundle / (role + '.gz')).write_bytes(gzip.compress(canonical(row), mtime=0))
        (self.bundle / 'rights.txt').write_text('Authored fixture permit retain parse transform; no source rights')
        (self.bundle / 'scope.txt').write_text('One authored Prices observation only')
        self.roles = {role: role + '.gz' for role in ('prices', 'locations', 'proofs')}
        self.assets = tuple(Asset(p.name, p.stat().st_size, sha(p.read_bytes()))
                            for p in sorted(self.bundle.iterdir()))
        rights = next(a for a in self.assets if a.path == 'rights.txt')
        scope = next(a for a in self.assets if a.path == 'scope.txt')
        schema = {'type': 'object', 'required': ['id', 'kind', 'schemaVersion', 'data', 'provenance', 'countries'],
                  'properties': {'kind': {'const': 'priceObservation'}, 'data': {'type': 'object'}}}
        schemas = {'priceObservation': schema}
        def semantics(row):
            data = row['data']
            return [] if (data['amount'] == 0 and data['sourceAmount'] == '0.00'
                and data['unit'] is None and data['unitPrice'] is None
                and data['promotion'] is False and row['countries'] == ['MD']) else ['authored-values-mismatch']
        self.contract = SourceContract('prices', 'authored-worker21', 'one-authored-row',
            '2026-09-01T00:00:00Z', self.assets, 1, ids_digest(['prices:priceObservation:1']),
            schemas, fingerprint(schemas), semantics, 'c' * 64, rights, scope,
            frozenset(('retain', 'parse', 'transform')), fixture=True)

    def stage(self, contract=None):
        return stage_authored_prices(contract or self.contract, self.bundle, self.roles, self.root / 'output')

    def test_shared_engine_valid_fixture_replay_null_units_and_origin_coverage(self):
        first = self.stage()
        self.assertTrue(first['qualification']['qualified'], first['qualification']['errors'])
        self.assertFalse(first['manifest']['accepted'])
        self.assertEqual(self.stage(), first)
        row = json.loads((self.root / 'output/candidate.jsonl').read_text())[0]
        self.assertNotIn('packageQuantity', row['data'])
        self.assertEqual(set(datum_pointers(row['data'])), set(PRICE_SELECTORS))
        pins = {a.path: a.sha256 for a in self.assets}
        origins = {}
        for target, (role, selector, transform) in PRICE_SELECTORS.items():
            if role == 'policy':
                origins[target] = {'kind': 'constant', 'policySha256': self.contract.policy_sha256, 'symbol': selector}
                continue
            origin = {'kind': 'source', 'sourceId': 'prices', 'releaseId': 'authored-worker21',
                      'inputPath': self.roles[role], 'inputSha256': pins[self.roles[role]],
                      'sourceRecordId': '2' if role == 'locations' else '1', 'sourceField': selector}
            origins[target] = origin if transform.startswith('identity') else {
                'kind': 'derived', 'policySha256': self.contract.policy_sha256,
                'transform': transform, 'inputs': [origin]}
        # The generic parser does not emit full fieldOrigins. Validate the explicit
        # prospective declarations independently; this does not upgrade its output.
        row['provenance']['fieldOrigins'] = origins
        self.assertEqual(field_origin_errors(row, pins, policy_pins=(self.contract.policy_sha256,)), [])
        del origins['/data/unit']
        self.assertIn('field-origin-inventory-mismatch', field_origin_errors(
            row, pins, policy_pins=(self.contract.policy_sha256,)))

    def test_shared_engine_held_or_nonfixture_cannot_run(self):
        with self.assertRaisesRegex(RefreshError, 'source-held'):
            self.stage(replace(self.contract, holds=('rights-held',)))
        self.assertFalse((self.root / 'output').exists())
        with self.assertRaisesRegex(RefreshError, 'portfolio-authored-prices-fixture-required'):
            self.stage(replace(self.contract, fixture=False))
        self.assertFalse((self.root / 'output').exists())

    def test_shared_engine_missing_changed_and_wrong_inventory_cannot_qualify(self):
        missing = self.bundle / 'prices.gz'
        original = missing.read_bytes()
        missing.unlink()
        with self.assertRaises(RefreshError):
            self.stage()
        missing.write_bytes(original + b'changed')
        with self.assertRaisesRegex(RefreshError, 'input-pin-mismatch'):
            self.stage()
        missing.write_bytes(original)
        result = self.stage(replace(self.contract, expected_records=2))
        self.assertFalse(result['qualification']['qualified'])
        self.assertIn('expected-record-count-mismatch', result['qualification']['errors'])
        self.assertFalse(result['manifest']['accepted'])


if __name__ == '__main__':
    unittest.main()
