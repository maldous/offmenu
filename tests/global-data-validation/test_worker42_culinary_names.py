import importlib.util
from pathlib import Path
import unittest
s = importlib.util.spec_from_file_location('culinary42', Path(__file__).resolve().parents[2] / 'scripts/global-data-validation/worker-42-culinary-names.py')
m = importlib.util.module_from_spec(s)
s.loader.exec_module(m)
class CulinaryNames(unittest.TestCase):
    def test_unicode_locale_and_candidate_boundaries(self):
        r = {'provenance': {'license': 'CC BY-SA 4.0', 'rightsEvidenceUrl': 'rights'}, 'data': {'languages': ['ar']}}
        item = {'name': 'ملح', 'originalText': 'ملح'}
        concepts = [{'id': 'a', 'names': [{'language': 'ar', 'value': 'ملح'}]}, {'id': 'b', 'names': [{'language': 'en', 'value': 'ملح'}]}]
        result = m.assertion(r, item, {}, concepts)
        self.assertEqual(result['original_lexeme'], 'ملح')
        self.assertEqual(result['candidate_concept_ids'], ['a'])
        self.assertIsNone(result['ingredient_identity'])
        self.assertIsNone(result['origin'])
        self.assertIn('original-publisher-body-not-verified', result['blockers'])
    def test_similar_names_and_missing_rights_do_not_qualify(self):
        r = {'provenance': {}, 'data': {'languages': ['hi']}}
        a = m.assertion(r, {'name': 'नमक', 'originalText': 'नमक'}, {}, [{'id': 'x', 'names': [{'language': 'hi', 'value': ' नमक'}]}])
        self.assertEqual(a['candidate_concept_ids'], [])
        self.assertIn('source-specific-rights-unverified', a['blockers'])
        self.assertFalse(a['automaticPlanningEligible'])

    def test_original_json_coordinate_is_exact(self):
        value = {'query': {'pages': [{'revisions': [{'slots': {'main': {'content': 'ملح'}}}]}]}}
        self.assertEqual(m.pointer(value, '/query/pages/0/revisions/0/slots/main/content'), 'ملح')
        with self.assertRaises(IndexError):
            m.pointer(value, '/query/pages/1')

class RetainedAttachmentRejections(unittest.TestCase):
    """Exercise the actual run path with in-memory mutations of retained source rows."""
    def test_run_rejects_conflicting_provenance(self):
        import gzip
        import io
        import json
        from unittest.mock import patch
        recipes = Path('/home/user/src/offmenu-data/world-recipes-global-final-20261014')
        foodon = Path('/home/user/src/offmenu-data/foodon-common-accepted-20261014')
        real_open = gzip.open
        # Mutations leave the actual source files, file hashes, body hash and revision intact.
        fields = {'recordId': 'wrong-page', 'sourceDate': '1900-01-01T00:00:00Z',
                  'originSourceId': 'wikibooks:en', 'originalContentSha256': '0' * 64,
                  'revisionId': -1}
        for field, wrong in fields.items():
            with self.subTest(field=field):
                def mutated(path, *args, **kwargs):
                    if Path(path) != recipes / 'normalized.jsonl.gz':
                        return real_open(path, *args, **kwargs)
                    # The first bound coordinate is Arabic at line3310; stop as soon as it rejects.
                    with real_open(path, *args, **kwargs) as f:
                        lines = []
                        for number, line in enumerate(f, 1):
                            if number == 3310:
                                rows = json.loads(line)
                                rows[0]['provenance'][field] = wrong
                                lines.append(json.dumps(rows, ensure_ascii=False) + '\n')
                                break
                            lines.append('\n')  # run skips unselected lines before this coordinate
                    return io.StringIO(''.join(lines))
                with patch.object(m.gzip, 'open', mutated):
                    with self.assertRaisesRegex(ValueError, field):
                        m.run(recipes, foodon)

    def test_missing_field_and_conflicting_locale_rejected(self):
        import copy
        proof = next(iter(m.original_proofs().values()))
        original = proof['original']
        row = {'provenance': {'recordId': original['recordId'], 'sourceDate': original['timestamp'],
               'originSourceId': proof['source_id'], 'revisionId': original['revisionId'],
               'originalContentSha256': original['body_sha256']},
               'data': {'languages': [proof['language']]}}
        m.validate_attachment(row, proof)
        for field in ['recordId', 'sourceDate', 'originSourceId']:
            changed = copy.deepcopy(row)
            del changed['provenance'][field]
            with self.subTest(missing=field), self.assertRaises(ValueError):
                m.validate_attachment(changed, proof)
        row['data']['languages'] = ['en']
        with self.assertRaisesRegex(ValueError, 'locale'):
            m.validate_attachment(row, proof)
