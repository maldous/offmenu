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


class PortableAttachmentRejections(unittest.TestCase):
    """Synthetic test-owned bytes exercise the real adapter without retained corpora or Git."""
    def setUp(self):
        import tempfile
        import json
        import hashlib
        import gzip
        self.temp = tempfile.TemporaryDirectory(prefix='culinary42-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.recipes, self.foodon = self.root / 'recipes', self.root / 'foodon'
        self.recipes.mkdir()
        self.foodon.mkdir()
        self.evidence = self.root / 'evidence.json'
        self.dump = lambda p, v: p.write_text(json.dumps(v, ensure_ascii=False), encoding='utf-8')
        # Invented test-only publisher body and IDs; not a copied source or qualification.
        body = 'test-only ingredient: ملح'
        revision = {'revid': 7, 'timestamp': '2001-01-01T00:00:00Z',
                    'slots': {'main': {'content': body}}}
        raw = {'query': {'pages': [{'pageid': 42, 'revisions': [revision]}]}}
        self.dump(self.root / 'original.json', raw)
        rights = {'url': 'urn:test:licence', 'text': 'test-only rights witness'}
        self.dump(self.root / 'rights.json', {'query': {'rightsinfo': rights}})
        provenance = {'originSourceId': 'wikibooks:ar', 'recordId': '42', 'revisionId': 7,
                      'sourceDate': revision['timestamp'],
                      'originalContentSha256': hashlib.sha256(body.encode()).hexdigest(),
                      'license': 'CC BY-SA 4.0', 'rightsEvidenceUrl': 'urn:test:licence'}
        self.row = {'id': 'urn:test:recipe', 'provenance': provenance,
                    'data': {'languages': ['ar'], 'ingredients': [{'name': 'ملح', 'originalText': 'ملح'}]}}
        self.proof = {'records': [{'normalized_coordinate': {'line': 1, 'index': 0},
            'language': 'ar', 'provenance': provenance.copy(),
            'original': {'path': 'original.json', 'file_sha256': m.sha(self.root / 'original.json'),
                'coordinate': '/query/pages/0/revisions/0/slots/main/content',
                'body_sha256': provenance['originalContentSha256'], 'recordId': '42',
                'revisionId': 7, 'timestamp': revision['timestamp']},
            'rights': {'path': 'rights.json', 'sha256': m.sha(self.root / 'rights.json'),
                       'coordinate': '/query/rightsinfo', 'publisher_declared': rights}}]}
        self.dump(self.recipes / 'manifest.json', {'releaseId': 'test-only'})
        packet = {'resources': [{'id': 'http://purl.obolibrary.org/obo/FOODON_TEST',
                    'names': [{'language': 'ar', 'value': 'ملح'}], 'citationIds': ['urn:test:foodon']}],
                  'citations': [{'license': 'CC-BY-4.0', 'revisionId': 'test-revision'}]}
        with gzip.open(self.foodon / 'foodon-common.jsonl.gz', 'wt', encoding='utf-8') as f:
            f.write(json.dumps(packet, ensure_ascii=False) + '\n')
        self.dump(self.foodon / 'manifest.json', {'licence': 'CC-BY-4.0', 'revision': 'test-revision',
            'files': [{'key': 'foodon-common.jsonl.gz', 'sha256': m.sha(self.foodon / 'foodon-common.jsonl.gz')}]})
        self.write_recipe()

    def write_recipe(self):
        import gzip
        import json
        with gzip.open(self.recipes / 'normalized.jsonl.gz', 'wt', encoding='utf-8') as f:
            f.write(json.dumps([self.row], ensure_ascii=False) + '\n')
        reference = {'census': {'before_sha256': m.sha(self.recipes / 'normalized.jsonl.gz'),
            'selected_refs': [{'id': self.row['id'], 'line': 1, 'index': 0,
                               'coverage': {'language': ['ar']}}], 'representative_source_refs': []}}
        self.dump(self.evidence, {'portable_inputs': {'recipe_reference': reference, 'original_proof': self.proof}})

    def run_adapter(self):
        return m.run(self.recipes, self.foodon, source_root=self.root, evidence_path=self.evidence)

    def test_positive_run_without_git_or_workstation_paths(self):
        from unittest.mock import patch
        with patch('subprocess.check_output', side_effect=AssertionError('No Git subprocess permitted')):
            result = self.run_adapter()
        self.assertEqual(result['recipe_records'], 1)
        self.assertEqual(result['before'], result['after'])
        a = result['assertions'][0]
        self.assertIsNotNone(a['original_body_reference'])
        self.assertIsNone(a['original_body_reference']['proof_commit'])
        self.assertIsNone(result['worker53_commit'])
        self.assertIsNone(result['worker56_commit'])
        self.assertEqual(result['evidence_binding']['sha256'], m.sha(self.evidence))
        self.assertEqual(result['evidence_binding']['verified_commit_provenance'], {})
        self.assertEqual(a['candidate_concept_ids'], ['http://purl.obolibrary.org/obo/FOODON_TEST'])
        self.assertIsNone(a['source_original_lexeme'])
        self.assertIsNone(a['ingredient_identity'])
        self.assertFalse(a['automaticPlanningEligible'])

    def test_run_rejects_conflicting_provenance(self):
        import copy
        original = copy.deepcopy(self.row)
        fields = {'recordId': 'wrong-page', 'sourceDate': '1900-01-01T00:00:00Z',
                  'originSourceId': 'wikibooks:en', 'originalContentSha256': '0' * 64, 'revisionId': -1}
        for field, wrong in fields.items():
            with self.subTest(field=field):
                self.row = copy.deepcopy(original)
                self.row['provenance'][field] = wrong
                self.write_recipe()  # Pin synthetic file; original witness is deliberately unchanged.
                with self.assertRaisesRegex(ValueError, field):
                    self.run_adapter()

    def test_missing_fields_and_locale_rejected(self):
        import copy
        original = copy.deepcopy(self.row)
        for field in ['recordId', 'sourceDate', 'originSourceId']:
            with self.subTest(missing=field):
                self.row = copy.deepcopy(original)
                del self.row['provenance'][field]
                self.write_recipe()
                with self.assertRaises(ValueError):
                    self.run_adapter()
        self.row = copy.deepcopy(original)
        self.row['data']['languages'] = ['en']
        self.write_recipe()
        with self.assertRaisesRegex(ValueError, 'locale'):
            self.run_adapter()

    def test_original_body_and_rights_tampering_rejected(self):
        import json
        path = self.root / 'original.json'
        original = path.read_bytes()
        path.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'custody'):
            self.run_adapter()
        path.write_bytes(original)
        self.proof['records'][0]['rights']['publisher_declared']['text'] = 'wrong'
        self.write_recipe()
        with self.assertRaisesRegex(ValueError, 'rights declaration'):
            self.run_adapter()

    def test_source_path_escape_rejected(self):
        for path in ['/absolute/original.json', '../outside.json']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                m.source_path(self.root, path)

    def test_missing_dependency_has_explicit_path(self):
        (self.recipes / 'manifest.json').unlink()
        with self.assertRaisesRegex(FileNotFoundError, 'manifest.json'):
            self.run_adapter()

    def test_alternate_bundle_cannot_claim_canonical_history(self):
        import json
        for key, commit in [('reference_commit', '8d468982f7bc905af01d5262c8eabb8db7051e96'),
                            ('original_proof_commit', '6bf021a81d7660ae48b3eeba3656aa656f3553bf'),
                            ('reference_commit', 'other-history')]:
            with self.subTest(key=key, commit=commit):
                self.write_recipe()
                bundle = json.loads(self.evidence.read_text())
                bundle['portable_inputs']['provenance'] = {key: commit}
                self.dump(self.evidence, bundle)
                with self.assertRaisesRegex(ValueError, 'Unsupported evidence provenance'):
                    self.run_adapter()

    def test_canonical_metadata_labels_are_digest_verified(self):
        import copy
        import json
        canonical = m.load_inputs(m.DEFAULT_EVIDENCE)
        self.assertEqual(canonical['verified_provenance']['reference_commit'],
                         '8d468982f7bc905af01d5262c8eabb8db7051e96')
        self.assertEqual(canonical['verified_provenance']['original_proof_commit'],
                         '6bf021a81d7660ae48b3eeba3656aa656f3553bf')
        changed = copy.deepcopy(canonical)
        changed['original_proof']['records'][0]['original']['recordId'] = 'changed'
        self.dump(self.evidence, {'portable_inputs': changed})
        with self.assertRaisesRegex(ValueError, 'original_proof_commit'):
            m.load_inputs(self.evidence)
