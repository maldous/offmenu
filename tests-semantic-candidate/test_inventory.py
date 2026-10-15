import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('inventory', Path(__file__).resolve().parents[1] / 'scripts/semantic-candidate-inventory.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('checkpoint/queue-state.json', {'byItem': {
            'a': {'dataset': 'sample', 'status': 'done', 'file': 'judgments/sample/a.json'},
            'b': {'dataset': 'sample', 'status': 'blocked', 'file': None}}})
        self.write('queue/sample.queue.jsonl', {'itemId': 'a', 'dataset': 'sample'})
        with (self.root / 'queue/sample.queue.jsonl').open('a') as f:
            f.write(json.dumps({'itemId': 'b', 'dataset': 'sample'})+'\n')
        for item in ['a', 'b']:
            self.write(f'judgments/sample/{item}.json', {'itemId': item, 'dataset': 'sample',
                'model': {'modelId': 'unverified'}, 'stage': 'unit',
                'fields': [{'provenanceState': 'original' if item == 'a' else 'blocked'}],
                'citations': [{'sampleFile': 'samples/input.json'}]})
        self.write('samples/input.json', {'sourceFileSha256': None})
        self.write('admission/all.admission.json', {'admitted': ['judgments/sample/a.json'],
            'failed': [{'itemId': 'b', 'file': 'judgments/sample/b.json'}], 'sampledOnly': True,
            'totals': {'judgments': 2, 'admitted': 1, 'failed': 1}})
        self.write('glossary/proposals.jsonl', {'status': 'proposal-unfrozen'})
        self.write('STATUS.json', {'sampledOnly': True})
        self.write('reviews/20261015-w02-corrections-manifest-W06.json', {'changedFiles': [
            {'path': 'STATUS.json', 'postSha256': hashlib.sha256((self.root/'STATUS.json').read_bytes()).hexdigest()}]})

    def write(self, name, value):
        p = self.root/name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value)+'\n')

    def test_passed_schema_is_not_acceptance(self):
        result = module.inventory(self.root)
        self.assertFalse(result['admissionGranted'])
        self.assertFalse(result['glossaryFrozen'])
        self.assertEqual(result['checkpointStates'], {'done': 1, 'blocked': 1})
        self.assertIn('samples/input.json', result['inputSHA256'])

    def test_duplicate_queue_rejected(self):
        p = self.root/'queue/sample.queue.jsonl'
        with p.open('a') as f:
            f.write(json.dumps({'itemId': 'a', 'dataset': 'sample'})+'\n')
        with self.assertRaisesRegex(module.InventoryError, 'duplicate'):
            module.inventory(self.root)

    def test_changed_correction_bytes_rejected(self):
        self.write('STATUS.json', {'sampledOnly': False})
        with self.assertRaisesRegex(module.InventoryError, 'correction bytes'):
            module.inventory(self.root)

    def test_sample_escape_rejected(self):
        self.write('judgments/sample/a.json', {'itemId': 'a', 'dataset': 'sample',
            'model': {'modelId': 'unverified'}, 'stage': 'unit', 'fields': [],
            'citations': [{'sampleFile': '../elsewhere.json'}]})
        with self.assertRaisesRegex(module.InventoryError, 'escapes lane'):
            module.inventory(self.root)

    def test_wrong_failed_identity_rejected(self):
        p = self.root/'admission/all.admission.json'
        r = json.loads(p.read_text()); r['failed'][0]['itemId'] = 'a'; self.write(str(p.relative_to(self.root)), r)
        with self.assertRaisesRegex(module.InventoryError, 'failed set'):
            module.inventory(self.root)
