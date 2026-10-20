import copy
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]

def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

PARSER = load_module('source_faithful_parse', ROOT / 'offmenu/refresh/source_faithful_parse.py')
AI = load_module('assistant_intermediate', ROOT / 'offmenu/refresh/assistant_intermediate.py')

HTML = '''<!doctype html><html><body><main class="field--name-body">
<h1>Fixture bake</h1><h2>Ingredients</h2><ul>
<li>1 small red capsicum or yellow capsicum, diced</li><li>2 cups cooked beans</li>
</ul><h2>Method</h2><p>Heat oven to 180°C. Bake for 20 minutes until golden.</p>
<h3>Variation</h3><p>Use courgette if marrow is unavailable.</p>
</main></body></html>'''.encode('utf-8')


def get_response():
    paragraph = 'Heat oven to 180\u00b0C. Bake for 20 minutes until golden.'
    first = 'Heat oven to 180\u00b0C.'
    second = ' Bake for 20 minutes until golden.'
    ingredients = [
        {'order': 1, 'sourceText': '1 small red capsicum or yellow capsicum, diced',
         'nameText': 'red capsicum or yellow capsicum', 'quantityText': '1',
         'unitText': None, 'preparationText': 'diced',
         'alternatives': ['red capsicum', 'yellow capsicum']},
        {'order': 2, 'sourceText': '2 cups cooked beans', 'nameText': 'cooked beans',
         'quantityText': '2', 'unitText': 'cups', 'preparationText': 'cooked',
         'alternatives': []},
    ]
    return {'schemaVersion': AI.SCHEMA_VERSION, 'ingredientCoverage': [x['sourceText'] for x in ingredients],
        'directionCoverage': [paragraph], 'yieldCoverage': [], 'ingredients': ingredients,
        'directions': [
            {'order': 1, 'paragraphIndex': 1, 'paragraphCharRange': [0, len(first)],
             'sourceText': first, 'actionTerms': ['Heat'], 'equipment': ['oven'],
             'temperatureText': '180\u00b0C', 'timeText': None, 'targetState': None},
            {'order': 2, 'paragraphIndex': 1, 'paragraphCharRange': [len(first), len(paragraph)],
             'sourceText': second, 'actionTerms': ['Bake'], 'equipment': [],
             'temperatureText': None, 'timeText': '20 minutes', 'targetState': 'golden'},
        ],
        'variations': [{'section': 'Variation', 'sourceText': 'Use courgette if marrow is unavailable.'}],
        'ambiguities': [], 'uncertainty': []}


class AssistantIntermediateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.original = self.root / 'original.html'
        self.original.write_bytes(HTML)
        self.source = {'sourceURL': 'synthetic-fixture-source',
            'citationUrl': 'synthetic-fixture-source', 'release': 'fixture-v1',
            'originalSHA256': hashlib.sha256(HTML).hexdigest(),
            'assistantExtractionAllowed': True,
            'assistantExtractionPermissionEvidence': 'synthetic test fixture only',
            'licenseStatus': 'synthetic fixture'}
        self.record = PARSER.parse_html_recipe(HTML, source=self.source,
            source_id='TEST', source_record_id='fixture-bake', country='ZZ',
            language='en')
        self.response_text = json.dumps(get_response(), ensure_ascii=False)

    def tearDown(self):
        self.tmp.cleanup()

    def args(self, response=None, cache='cache', output='output'):
        return {'input_path': self.original, 'parsed_record': self.record,
            'response_text': response or self.response_text,
            'cache_root': self.root / cache, 'output_root': self.root / output,
            'source': self.source, 'source_id': 'TEST', 'source_record_id': 'fixture-bake',
            'country': 'ZZ', 'language': 'en'}

    def test_extract_cache_hit_and_replay_are_identical(self):
        before = copy.deepcopy(self.record)
        first = AI.cache_assistant_intermediate(**self.args())
        self.assertEqual(first['status'], 'accepted')
        self.assertFalse(first['cacheHit'])
        self.assertEqual(self.record, before)
        cache = json.loads(Path(first['cachePath']).read_text())
        self.assertEqual(cache['rawResponseSHA256'], hashlib.sha256(self.response_text.encode()).hexdigest())
        self.assertEqual(cache['validation']['status'], 'valid')
        record = json.loads(Path(first['recordPath']).read_text())
        self.assertEqual(record['orderedSteps'][0]['temperature']['rawText'], '180\u00b0C')
        self.assertEqual(record['orderedSteps'][1]['time']['rawText'], '20 minutes')
        self.assertIsNone(record['ingredientLines'][0]['quantity']['interpretedValue'])
        self.assertEqual(record['ingredientLines'][0]['substitutionText'], 'red capsicum or yellow capsicum')

        hit = AI.cache_assistant_intermediate(**self.args())
        self.assertTrue(hit['cacheHit'])
        self.assertEqual(first['cacheKey'], hit['cacheKey'])
        self.assertEqual(first['rawResponseSHA256'], hit['rawResponseSHA256'])
        found = AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source,
            model_identity='unknown', model_version='unknown',
            inference_settings={'temperature': None, 'seed': None, 'max_tokens': None,
                                'runtime_parameters': 'not-exposed'})
        self.assertEqual(found, Path(first['cachePath']))
        replay = AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
            parsed_record=self.record, output_root=self.root / 'replay')
        replayed = json.loads(Path(replay['recordPath']).read_text())
        self.assertEqual(replayed, record)

    def test_no_tooling_is_not_fabricated_in_cache_or_output(self):
        result = AI.cache_assistant_intermediate(**self.args())
        cache = json.loads(Path(result['cachePath']).read_text())
        record = json.loads(Path(result['recordPath']).read_text())
        self.assertNotIn('tooling', cache)
        self.assertNotIn('tooling', cache['cacheKeyInputs'])
        self.assertNotIn('tooling', record['assistantInterpretation'])
        self.assertFalse((self.root / 'cache' / 'tooling').exists())
        found = AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source)
        self.assertEqual(found, Path(result['cachePath']))
        AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
            parsed_record=self.record, output_root=self.root / 'replay')

    def test_used_tooling_is_archived_hashed_and_required_for_reuse(self):
        tool = self.root / 'translator.py'
        tool.write_text('# deterministic test tool v1\\n')
        artifacts = [{'name': 'recipe-translator', 'version': '1.0', 'path': tool}]
        args = self.args()
        args['tooling_artifacts'] = artifacts
        result = AI.cache_assistant_intermediate(**args)
        cache = json.loads(Path(result['cachePath']).read_text())
        self.assertEqual(cache['tooling']['artifacts'][0]['name'], 'recipe-translator')
        archived = self.root / 'cache' / cache['tooling']['artifacts'][0]['cachePath']
        self.assertEqual(hashlib.sha256(archived.read_bytes()).hexdigest(),
                         cache['tooling']['artifacts'][0]['sha256'])
        found = AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source)
        self.assertEqual(found, Path(result['cachePath']))
        replay = AI.replay_cached_intermediate(cache_path=found,
            input_path=self.original, parsed_record=self.record,
            output_root=self.root / 'tool-replay')
        self.assertTrue(Path(replay['recordPath']).is_file())
        with self.assertRaisesRegex(AI.IntermediateError, 'tooling-incompatible'):
            AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
                parsed_record=self.record, output_root=self.root / 'bad-tool-replay',
                tooling_artifacts=[{'name': 'recipe-translator', 'version': '2.0', 'path': tool}])
        tool.write_text('# changed tool v2\\n')
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source, tooling_artifacts=artifacts))
        archived.write_text('tampered')
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source))
        with self.assertRaisesRegex(AI.IntermediateError, 'tooling-incompatible'):
            AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
                parsed_record=self.record, output_root=self.root / 'tampered-tool-replay')

    def test_unsupported_quantity_is_quarantined_not_accepted(self):
        response = get_response()
        response['ingredients'][0]['quantityText'] = '7'
        with self.assertRaises(AI.IntermediateError):
            AI.cache_assistant_intermediate(**self.args(json.dumps(response, ensure_ascii=False),
                cache='bad-cache', output='bad-output'))
        rejected = list((self.root / 'bad-cache' / 'rejected').glob('*.json'))
        self.assertEqual(len(rejected), 1)
        envelope = json.loads(rejected[0].read_text())
        self.assertEqual(envelope['status'], 'rejected')
        self.assertEqual(envelope['validation']['status'], 'invalid')
        self.assertFalse((self.root / 'bad-output').exists())

    def test_source_without_assistant_permission_is_rejected_before_cache(self):
        source = dict(self.source, assistantExtractionAllowed=False)
        args = self.args()
        args['source'] = source
        with self.assertRaisesRegex(AI.IntermediateError, 'permission-required'):
            AI.cache_assistant_intermediate(**args)
        self.assertFalse((self.root / 'cache').exists())

    def test_changed_source_never_reuses_cache(self):
        first = AI.cache_assistant_intermediate(**self.args())
        self.original.write_bytes(HTML + b'<!-- changed -->')
        found = AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source,
            model_identity='unknown', model_version='unknown',
            inference_settings={'temperature': None, 'seed': None, 'max_tokens': None,
                                'runtime_parameters': 'not-exposed'})
        self.assertIsNone(found)
        with self.assertRaises(AI.IntermediateError):
            AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
                input_path=self.original, parsed_record=self.record,
                output_root=self.root / 'replay')


if __name__ == '__main__':
    unittest.main()
