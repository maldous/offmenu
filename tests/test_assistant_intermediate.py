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

PARSER = load_module('source_faithful_parse', ROOT / 'src/offmenu/refresh/source_faithful_parse.py')
AI = load_module('assistant_intermediate', ROOT / 'src/offmenu/refresh/assistant_intermediate.py')

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
            input_path=self.original, source=self.source, parsed_record=self.record,
            model_identity='unknown', model_version='unknown',
            inference_settings={'temperature': None, 'seed': None, 'max_tokens': None,
                                'runtime_parameters': 'not-exposed'})
        self.assertEqual(found, Path(first['cachePath']))
        replay = AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
            parsed_record=self.record, source=self.source, output_root=self.root / 'replay')
        replayed = json.loads(Path(replay['recordPath']).read_text())
        self.assertEqual(replayed, record)

    def test_inline_markup_preserves_actual_span_through_cache_and_replay(self):
        raw = HTML.replace(b'2 cups cooked beans', b'2 cups <b>cooked</b> beans')
        self.original.write_bytes(raw)
        self.source['originalSHA256'] = hashlib.sha256(raw).hexdigest()
        self.record = PARSER.parse_html_recipe(raw, source=self.source,
            source_id='TEST', source_record_id='fixture-bake', country='ZZ', language='en')
        first = AI.cache_assistant_intermediate(**self.args())
        self.assertEqual(first['status'], 'accepted')
        record = json.loads(Path(first['recordPath']).read_text())
        text = AI.BeautifulSoup(raw, 'html.parser').get_text('\n', strip=False).encode()
        location = record['ingredientLines'][1]['location']
        start, end = location['utf8ByteRange']
        actual = text[start:end]
        self.assertEqual(' '.join(actual.decode().split()), '2 cups cooked beans')
        self.assertEqual(hashlib.sha256(actual).hexdigest(), location['sourceSpanSHA256'])
        replay = AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
            input_path=self.original, parsed_record=self.record, source=self.source, output_root=self.root / 'replay')
        self.assertEqual(json.loads(Path(replay['recordPath']).read_text()), record)

    def test_no_tooling_is_not_fabricated_in_cache_or_output(self):
        result = AI.cache_assistant_intermediate(**self.args())
        cache = json.loads(Path(result['cachePath']).read_text())
        record = json.loads(Path(result['recordPath']).read_text())
        self.assertNotIn('tooling', cache)
        self.assertNotIn('tooling', cache['cacheKeyInputs'])
        self.assertNotIn('tooling', record['assistantInterpretation'])
        self.assertFalse((self.root / 'cache' / 'tooling').exists())
        found = AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source, parsed_record=self.record)
        self.assertEqual(found, Path(result['cachePath']))
        AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
            parsed_record=self.record, source=self.source, output_root=self.root / 'replay')

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
            input_path=self.original, source=self.source, parsed_record=self.record)
        self.assertEqual(found, Path(result['cachePath']))
        replay = AI.replay_cached_intermediate(cache_path=found,
            input_path=self.original, parsed_record=self.record, source=self.source,
            output_root=self.root / 'tool-replay')
        self.assertTrue(Path(replay['recordPath']).is_file())
        with self.assertRaisesRegex(AI.IntermediateError, 'tooling-incompatible'):
            AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
                parsed_record=self.record, source=self.source, output_root=self.root / 'bad-tool-replay',
                tooling_artifacts=[{'name': 'recipe-translator', 'version': '2.0', 'path': tool}])
        tool.write_text('# changed tool v2\\n')
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source, parsed_record=self.record, tooling_artifacts=artifacts))
        archived.write_text('tampered')
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root / 'cache',
            input_path=self.original, source=self.source, parsed_record=self.record))
        with self.assertRaisesRegex(AI.IntermediateError, 'tooling-incompatible'):
            AI.replay_cached_intermediate(cache_path=found, input_path=self.original,
                parsed_record=self.record, source=self.source, output_root=self.root / 'tampered-tool-replay')

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
            input_path=self.original, source=self.source, parsed_record=self.record,
            model_identity='unknown', model_version='unknown',
            inference_settings={'temperature': None, 'seed': None, 'max_tokens': None,
                                'runtime_parameters': 'not-exposed'})
        self.assertIsNone(found)
        with self.assertRaises(AI.IntermediateError):
            AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
                input_path=self.original, parsed_record=self.record, source=self.source,
                output_root=self.root / 'replay')


    def test_distinct_source_bindings_never_collide_on_identical_bytes(self):
        variants = [
            ('source-id', {}, 'OTHER', 'fixture-bake', 'ZZ', 'en'),
            ('record-id', {}, 'TEST', 'other-record', 'ZZ', 'en'),
            ('release', {'release': 'fixture-v2'}, 'TEST', 'fixture-bake', 'ZZ', 'en'),
            ('citation', {'citationUrl': 'different-fixture-citation'}, 'TEST', 'fixture-bake', 'ZZ', 'en'),
            ('country', {}, 'TEST', 'fixture-bake', 'XY', 'en'),
            ('language', {}, 'TEST', 'fixture-bake', 'ZZ', 'fr'),
            ('permission', {'assistantExtractionPermissionEvidence': 'another synthetic grant'}, 'TEST', 'fixture-bake', 'ZZ', 'en'),
            ('rights', {'licenseStatus': 'other synthetic scope'}, 'TEST', 'fixture-bake', 'ZZ', 'en'),
        ]
        for label, changes, sid, rid, country, language in variants:
            with self.subTest(label=label):
                first = AI.cache_assistant_intermediate(**self.args(cache=label, output=label+'-a'))
                other_source = dict(self.source, **changes)
                other = PARSER.parse_html_recipe(HTML, source=other_source,
                    source_id=sid, source_record_id=rid, country=country, language=language)
                args = self.args(cache=label, output=label+'-b')
                args.update(source=other_source, parsed_record=other, source_id=sid,
                    source_record_id=rid, country=country, language=language)
                second = AI.cache_assistant_intermediate(**args)
                self.assertNotEqual(first['cacheKey'], second['cacheKey'])
                saved = json.loads(Path(second['recordPath']).read_text())
                self.assertEqual(saved['source']['sourceId'], sid)
                self.assertEqual(saved['source']['sourceRecordId'], rid)
                self.assertEqual(saved['source']['releaseId'], other_source['release'])

    def test_lookup_without_current_record_cannot_select_foreign_envelope(self):
        AI.cache_assistant_intermediate(**self.args())
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root/'cache',
            input_path=self.original, source=dict(self.source, release='another-release')))

    def test_replay_without_current_source_and_record_is_denied_before_output(self):
        first = AI.cache_assistant_intermediate(**self.args())
        with self.assertRaisesRegex(AI.IntermediateError, 'current-source-and-record-required'):
            AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
                input_path=self.original, output_root=self.root/'unsafe-replay')
        self.assertFalse((self.root/'unsafe-replay').exists())

    def test_non_utf8_source_replays_using_its_pinned_encoding(self):
        raw = HTML.decode('utf-8').encode('cp1252')
        self.original.write_bytes(raw)
        self.source = dict(self.source, encoding='cp1252',
            originalSHA256=hashlib.sha256(raw).hexdigest())
        self.record = PARSER.parse_html_recipe(raw, source=self.source,
            source_id='TEST', source_record_id='fixture-bake', country='ZZ', language='en')
        first = AI.cache_assistant_intermediate(**self.args())
        replay = AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
            input_path=self.original, parsed_record=self.record, source=self.source, output_root=self.root/'cp1252-replay')
        saved = json.loads(Path(replay['recordPath']).read_text())
        self.assertEqual(saved, json.loads(Path(first['recordPath']).read_text()))
        self.assertEqual(saved['orderedSteps'][0]['temperature']['rawText'], '180°C')


    def test_foreign_cache_rejected_with_current_record_without_writing_output(self):
        first = AI.cache_assistant_intermediate(**self.args())
        original_cache = Path(first['cachePath']).read_bytes()
        other_source = dict(self.source, release='fixture-v2')
        other = PARSER.parse_html_recipe(HTML, source=other_source,
            source_id='OTHER', source_record_id='different', country='XY', language='fr')
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root/'cache',
            input_path=self.original, source=other_source, parsed_record=other))
        with self.assertRaisesRegex(AI.IntermediateError, 'current-source-binding-mismatch'):
            AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
                input_path=self.original, parsed_record=other, source=other_source,
                output_root=self.root/'foreign-output')
        self.assertFalse((self.root/'foreign-output').exists())
        self.assertEqual(Path(first['cachePath']).read_bytes(), original_cache)

    def test_revoked_permission_blocks_replay_before_source_read(self):
        first = AI.cache_assistant_intermediate(**self.args())
        with self.assertRaisesRegex(AI.IntermediateError, 'permission-required'):
            AI.replay_cached_intermediate(cache_path=Path(first['cachePath']),
                input_path=self.root/'must-not-read.html', parsed_record=self.record,
                source=dict(self.source, assistantExtractionAllowed=False),
                output_root=self.root/'revoked-output')
        self.assertFalse((self.root/'revoked-output').exists())

    def test_legacy_envelope_is_preserved_but_not_replayed(self):
        first = AI.cache_assistant_intermediate(**self.args())
        cache_path = Path(first['cachePath'])
        envelope = json.loads(cache_path.read_text())
        envelope['cacheSchemaVersion'] = 'offmenu-assistant-extraction-cache/1'
        cache_path.write_text(json.dumps(envelope))
        legacy_bytes = cache_path.read_bytes()
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root/'cache',
            input_path=self.original, source=self.source, parsed_record=self.record))
        with self.assertRaisesRegex(AI.IntermediateError, 'contract-incompatible'):
            AI.replay_cached_intermediate(cache_path=cache_path, input_path=self.original,
                parsed_record=self.record, source=self.source, output_root=self.root/'old-output')
        self.assertEqual(cache_path.read_bytes(),legacy_bytes)
        self.assertFalse((self.root/'old-output').exists())

    def test_tampered_envelope_source_cannot_choose_output_identity(self):
        first = AI.cache_assistant_intermediate(**self.args())
        path = Path(first['cachePath'])
        envelope = json.loads(path.read_text())
        envelope['source']['sourceId'] = 'FOREIGN'
        path.write_text(json.dumps(envelope))
        self.assertIsNone(AI.find_compatible_intermediate(cache_root=self.root/'cache',
            input_path=self.original, source=self.source, parsed_record=self.record))
        with self.assertRaisesRegex(AI.IntermediateError,'current-source-binding-mismatch'):
            AI.replay_cached_intermediate(cache_path=path,input_path=self.original,
                parsed_record=self.record,source=self.source,output_root=self.root/'tampered-output')
        self.assertFalse((self.root/'tampered-output').exists())

    def test_explicit_creation_identity_must_match_current_record(self):
        args = self.args()
        args['source_record_id'] = 'unrelated-record'
        with self.assertRaisesRegex(AI.IntermediateError,'provenance-mismatch'):
            AI.cache_assistant_intermediate(**args)
        self.assertFalse((self.root/'cache').exists())


if __name__ == '__main__':
    unittest.main()
