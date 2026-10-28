"""Independent synthetic diagnostics/manifest tests, never Foo or raw data."""
import copy
import gzip
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'candidate/scripts'))
import inspect_north_star_sample as subject
SPEC = importlib.util.spec_from_file_location('fixtures', ROOT / 'candidate/tests/test_north_star_derivations.py')
FIXTURES = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FIXTURES)


def packets():
    original = FIXTURES.fixture()
    product = copy.deepcopy(original)
    product['resources'] = [product['resources'][0]]
    product['assertions'] = [{
        'id': 'urn:test:identifier', 'subjectId': 'urn:test:product',
        'propertyId': 'urn:offmenu:property:sourceIdentifier',
        'value': {'kind': 'structure', 'fields': {
            'system': {'kind': 'identifier', 'value': 'barcode'},
            'value': {'kind': 'identifier', 'value': '0000000123'},
        }}, 'status': 'source-asserted', 'scope': copy.deepcopy(FIXTURES.SCOPE),
        'citationIds': ['urn:test:citation'], 'sourcePath': 'data.identifiers[0]',
    }]
    target = copy.deepcopy(original)
    target['resources'] = [target['resources'][1]]
    target['relations'] = []
    return [product, target]


class SampleInspectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.package = self.root / 'input'; self.package.mkdir()
        self.output = self.root / 'output'

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, rows=None):
        rows = packets() if rows is None else rows
        data = gzip.compress(('\n'.join(json.dumps(p) for p in rows) + '\n').encode())
        self.files = []
        for key, raw in {
            'packets.jsonl.gz': data,
            'schema.json': (ROOT / 'selected/corpus/common-data.schema.json').read_bytes(),
            'contract.json': (ROOT / 'selected/corpus/common-data-contract.json').read_bytes(),
        }.items():
            (self.package / key).write_bytes(raw)
            item = {'key': key, 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest()}
            if key.endswith('.gz'): item['packets'] = len(rows)
            self.files.append(item)
        raw = json.dumps({'releaseId': 'synthetic', 'files': self.files}).encode()
        (self.package / 'manifest.json').write_bytes(raw)
        self.pin = hashlib.sha256(raw).hexdigest()
        return self.pin

    def run_inspection(self, rows=None):
        self.create(rows)
        return subject.inspect(self.package, self.pin, 'packets.jsonl.gz', self.output)

    def test_qualified_cross_packet_join(self):
        report = self.run_inspection()
        self.assertEqual(report['diagnosticQueries']['productProfileEdgesResolvedWithinSelectedPartition'], 1)
        self.assertEqual(report['diagnosticQueries']['identifierProductProfileNutrientContextJoins'], 1)

    def test_cross_packet_wrong_type_not_resolved(self):
        rows = packets(); rows[1]['resources'][0]['type'] = 'urn:offmenu:type:FoodIngredient'
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['productProfileEdgesResolvedWithinSelectedPartition'], 0)

    def test_cross_packet_private_scope_not_resolved(self):
        rows = packets(); scope = {'visibility': 'private', 'ownerId': 'other-owner'}
        for r in rows[1]['resources'] + rows[1]['assertions'] + rows[1]['citations']: r['scope'] = scope
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['productProfileEdgesResolvedWithinSelectedPartition'], 0)

    def test_cross_packet_different_release_not_resolved(self):
        rows = packets(); rows[1]['citations'][0]['revisionId'] = 'different-release'
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['productProfileEdgesResolvedWithinSelectedPartition'], 0)

    def test_superseded_identifier_excluded(self):
        rows = packets(); rows[0]['assertions'][0]['status'] = 'superseded'
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['identifierProductProfileJoins'], 0)

    def test_empty_identifier_namespace_excluded(self):
        rows = packets(); rows[0]['assertions'][0]['value']['fields']['system']['value'] = ''
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['uniqueSourceScopedProductKeys'], 0)

    def test_missing_revision_not_called_exact_release(self):
        rows = packets()
        for row in rows: row['citations'][0].pop('revisionId')
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['exactSourceReleaseNamespaceLexicalKeys'], 0)

    def test_identifier_different_source_citation_excluded(self):
        rows = packets(); cite = copy.deepcopy(rows[0]['citations'][0]); cite.update(id='urn:test:other-source-citation', sourceId='other-source')
        rows[0]['citations'].append(cite); rows[0]['assertions'][0]['citationIds'] = [cite['id']]
        report = self.run_inspection(rows)
        self.assertEqual(report['diagnosticQueries']['identifierProductProfileJoins'], 0)

    def test_schema_invalid_packet_not_reported_successful(self):
        import jsonschema
        rows = packets(); rows[0]['resources'][0].pop('scope')
        self.create(rows)
        with self.assertRaises(jsonschema.ValidationError):
            subject.inspect(self.package, self.pin, 'packets.jsonl.gz', self.output)
        self.assertFalse((self.output / 'report.json').exists())

    def test_manifest_hash_mismatch_before_output(self):
        self.create()
        with self.assertRaisesRegex(ValueError, 'manifest bytes differ'):
            subject.inspect(self.package, '0' * 64, 'packets.jsonl.gz', self.output)
        self.assertFalse(self.output.exists())

    def test_asset_hash_mismatch_before_output(self):
        self.create(); (self.package / 'packets.jsonl.gz').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'asset bytes differ'):
            subject.inspect(self.package, self.pin, 'packets.jsonl.gz', self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_unchanged(self):
        self.create(); self.output.mkdir(); marker = self.output / 'retained'; marker.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'immutable output'):
            subject.inspect(self.package, self.pin, 'packets.jsonl.gz', self.output)
        self.assertEqual(marker.read_text(), 'keep')

    def test_traversal_and_absolute_asset_rejected(self):
        for name in ('../escape', '/tmp/escape'):
            with self.assertRaisesRegex(ValueError, 'unsafe selected asset'):
                subject.selected_file(self.package, {'key': name, 'bytes': 0, 'sha256': '0' * 64})

    def test_symlink_asset_rejected(self):
        self.create(); original = self.package / 'packets.jsonl.gz'; original.rename(self.package / 'stored.gz')
        original.symlink_to(self.package / 'stored.gz')
        with self.assertRaisesRegex(ValueError, 'symlink selected asset'):
            subject.inspect(self.package, self.pin, 'packets.jsonl.gz', self.output)


if __name__ == '__main__': unittest.main()
