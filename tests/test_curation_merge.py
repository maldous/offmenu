import gzip
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('merge', Path(__file__).parents[1] / 'scripts/merge-curated-corpus.py')
merger = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merger)


def release(root, version, source, name):
    root.mkdir()
    record = {'schemaVersion': '1.0', 'kind': 'product', 'id': 'offmenu:product:' + name,
              'countries': ['AU'], 'provenance': {'sourceId': source, 'visibility': 'public'},
              'curation': {'schema': 'offmenu-curation/1', 'rawSourcePayloadPublished': False},
              'data': {'name': name}}
    contents = {'entries-0.json.gz': [{'id': 0, 'source': source, 'key': record['id'], 'shard': 'abc', 'kinds': ['product'], 'countries': ['AU']}],
                f'records/{source}/abc.jsonl.gz': [[record['id'], [record]]],
                'terms/abc.jsonl.gz': [['food', {source: [0]}]]}
    files = []
    for key, value in contents.items():
        path = root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        with gzip.open(path, 'wt') as out:
            if key.startswith('entries-'):
                json.dump(value, out)
            else:
                for row in value:
                    out.write(json.dumps(row) + '\n')
        files.append({'key': key, 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = {'format': 'offmenu-curated/1', 'status': 'curated-release-ready', 'privateProviderData': False, 'acquisitionAtRuntime': False,
                'releaseId': version, 'entryPageSize': 1000, 'shardLength': 3, 'curationPolicy': {'version': '1', 'publicSources': [source]},
                'sources': {source: {'entryRange': [0, 1], 'records': 1, 'bundles': 1}}, 'files': files}
    (root / 'manifest.json').write_text(json.dumps(manifest))
    return root


class CurationMergeTests(unittest.TestCase):
    def test_replaces_source_without_stale_postings_and_preserves_page_alignment(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inputs = [release(root / 'old', 'old', 'off', 'old'), release(root / 'other', 'other', 'prices', 'price'), release(root / 'new', 'new', 'off', 'new')]
            output = root / 'merged'
            manifest = merger.merge(inputs, output, 'merged')
            self.assertEqual(manifest['records'], 2)
            self.assertEqual(manifest['sources']['off']['entryRange'], [2000, 2001])
            self.assertEqual(manifest['sources']['prices']['entryRange'], [1000, 1001])
            self.assertFalse((output / 'entries-0.json.gz').exists())
            with gzip.open(output / 'terms/abc.jsonl.gz', 'rt') as f:
                self.assertEqual(json.loads(f.readline()), ['food', {'prices': [1000], 'off': [2000]}])
            with gzip.open(output / 'records/off/abc.jsonl.gz', 'rt') as f:
                self.assertEqual(json.loads(f.readline())[0], 'offmenu:product:new')
            for item in manifest['files']:
                self.assertEqual(hashlib.sha256((output / item['key']).read_bytes()).hexdigest(), item['sha256'])

    def test_disjoint_accepted_sources_compose_without_reencoding_existing_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            left = release(root / 'left', 'left', 'off', 'food')
            right = release(root / 'right', 'right', 'prices', 'price')
            for path, source in [(left, 'off'), (right, 'prices')]:
                manifest = json.loads((path / 'manifest.json').read_text())
                manifest['records'] = 1
                manifest['curatedAcceptance'] = {'status': 'all-curated-records-exercised', 'records': 1,
                    'profiles': 0, 'countryRecordCounts': {source: {'AU': {'product': 1}}}}
                (path / 'manifest.json').write_text(json.dumps(manifest))
            merged = merger.merge([left, right], root / 'output', 'combined')
            self.assertEqual(merged['curatedAcceptance']['records'], 2)
            self.assertEqual(merged['curatedAcceptance']['countryRecordCounts']['prices']['AU']['product'], 1)
            self.assertEqual((left / 'entries-0.json.gz').read_bytes(), (root / 'output/entries-0.json.gz').read_bytes())

    def test_corrupt_input_prevents_serving_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            original = release(root / 'input', 'version', 'off', 'food')
            (original / 'entries-0.json.gz').write_bytes(b'corrupt')
            with self.assertRaisesRegex(ValueError, 'checksum'):
                merger.merge([original], root / 'output', 'merged')
            self.assertFalse((root / 'output/manifest.json').exists())
