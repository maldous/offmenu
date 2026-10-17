"""Self-contained functional, resource and privacy tests for the Norway survey."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from offmenu.refresh import survey_norway as no


def fixture():
    return {
        'en-foods.json': {'foods': [{
            'foodId': 'PRIVATE-FOOD-IDENTITY', 'foodName': 'PRIVATE FOOD NAME',
            'uri': 'https://private.invalid/food',
            'constituents': [{'nutrientId': 'p', 'quantity': 0, 'sourceId': 'PRIVATE-SOURCE'}],
            'calories': {'quantity': 0}, 'energy': {'quantity': 0},
            'portions': [{'portionName': 'PRIVATE PORTION', 'quantity': 25, 'unit': 'g'}],
            'langualCodes': ['PRIVATE-LANGUAL'],
        }]},
        'nb-foods.json': {'foods': [{'foodId': 'PRIVATE-FOOD-IDENTITY', 'foodName': 'PRIVATE NORWEGIAN NAME'}]},
        'en-nutrients.json': {'nutrients': [{'nutrientId': 'p', 'euroFirId': 'PROT', 'name': 'Protein', 'unit': 'g'}]},
        'en-sources.json': {'sources': [{'sourceId': 'PRIVATE-SOURCE', 'title': 'PRIVATE SOURCE PROSE', 'url': 'https://private.invalid/source'}]},
    }


def blobs(value):
    return {key: json.dumps(item).encode() for key, item in value.items()}


class NorwaySurveyTests(unittest.TestCase):
    def test_complete_happy_survey_is_read_only_and_private(self):
        source = blobs(fixture())
        original = copy.deepcopy(source)
        with patch('builtins.open', side_effect=AssertionError('Unexpected IO')):
            result = no.survey(source)
        self.assertEqual(source, original)
        self.assertEqual(result['status'], 'surveyed')
        self.assertTrue(result['evidenceComplete'])
        self.assertFalse(result['candidateGenerationEnabled'])
        self.assertEqual(result['nutrientDictionary'][0]['name'], 'Protein')
        self.assertEqual(result['canonicalMapping']['mappedDefinitions'], 1)
        self.assertTrue(result['identityComparison']['sameSet'])
        self.assertEqual(result['observations']['en']['quantities']['semantics']['literal-zero'], 1)
        self.assertEqual(result['sourceReferences']['en-foods.json']['resolved'], 1)
        self.assertEqual(result, no.sanitize_report(result))
        text = json.dumps(result)
        for forbidden in ('PRIVATE', 'https://', 'private.invalid'):
            self.assertNotIn(forbidden, text)

    def test_exact_checked_in_synthetic_fixture(self):
        root = Path(__file__).parent / 'fixtures' / 'norway'
        result = no.survey({name: (root / name).read_bytes() for name in no.INPUTS})
        self.assertTrue(result['evidenceComplete'])
        self.assertEqual(result['status'], 'held')
        self.assertEqual(result['reasonCodes'], ['unresolved-quantity', 'unresolved-source-reference'])
        self.assertEqual(result['observations']['en']['structure']['count'], 14)
        self.assertEqual(result['identities']['en-foods.json']['uniqueCount'], 2)
        self.assertLessEqual(len(json.dumps(result).encode()), no.MAX_OUTPUT_BYTES)

    def test_all_qualifier_distinctions_collected_together(self):
        values = [0, 0.0, '0', None, '', '-', 'TR', 'TRACE', 'ND', 'NT', 'N', '<0.1', '1,5', '1e2', 'unknown-private-text', True, {}, '<bad']
        data = fixture()
        data['en-foods.json']['foods'][0]['constituents'] = [
            {'nutrientId': 'p', 'quantity': value} for value in values] + [{'nutrientId': 'p'}]
        result = no.survey(blobs(data))
        self.assertTrue(result['evidenceComplete'])
        counts = result['observations']['en']['quantities']['semantics']
        self.assertEqual(counts['literal-zero'], 3)
        for key in ('absent', 'null', 'blank', 'dash', 'ND', 'NT', 'N', 'less-than'):
            self.assertEqual(counts[key], 1)
        self.assertEqual(counts['trace'], 2)
        self.assertEqual(counts['unresolved'], 2)
        self.assertEqual(counts['invalid'], 2)
        self.assertNotIn('unknown-private-text', json.dumps(result))
        self.assertNotIn('<bad', json.dumps(result))

    def test_collects_multiple_semantic_holds_without_early_exit(self):
        data = fixture()
        food = data['en-foods.json']['foods'][0]
        food['constituents'] += [{'nutrientId': 'unknown', 'quantity': 'unknown-private', 'sourceId': 'unknown-source'},
                                {'nutrientId': 'p', 'quantity': 2, 'unit': 'mg'}]
        data['nb-foods.json']['foods'][0]['foodId'] = 'OTHER-PRIVATE-ID'
        data['en-nutrients.json']['nutrients'][0]['unit'] = 'kg'
        food['basis'] = {'amount': 1, 'unit': 'private-basis-text'}
        result = no.survey(blobs(data))
        self.assertTrue(result['evidenceComplete'])
        for code in ('locale-identity-set-mismatch', 'canonical-unit-mismatch',
                     'unresolved-nutrient-reference', 'observation-unit-mismatch',
                     'unresolved-source-reference', 'unresolved-quantity', 'explicit-basis-unresolved'):
            self.assertIn(code, result['reasonCodes'])
        self.assertNotIn('private-basis-text', json.dumps(result))

    def test_dictionary_and_identity_duplicates_remain_ambiguous(self):
        data = fixture()
        data['en-nutrients.json']['nutrients'] *= 2
        data['en-sources.json']['sources'] *= 2
        result = no.survey(blobs(data))
        self.assertTrue(result['evidenceComplete'])
        for code in ('duplicate-native-identity', 'duplicate-eurofir-identity',
                     'canonical-component-collision', 'ambiguous-nutrient-reference', 'ambiguous-source-reference'):
            self.assertIn(code, result['reasonCodes'])

    def test_parse_failures_are_content_free(self):
        for bad, code in ((b'{"foods":[],"foods":[]}', 'duplicate-json-key'),
                          (b'{"foods":[NaN]}', 'nonfinite-json-number'),
                          (b'{"foods":[1e999]}', 'nonfinite-json-number'),
                          (b'{"foods":[1e-999]}', 'json-number-underflow'),
                          (b'{PRIVATE MALFORMED CONTENT}', 'invalid-json')):
            with self.subTest(code=code):
                inputs = blobs(fixture())
                inputs['en-foods.json'] = bad
                result = no.survey(inputs)
                self.assertEqual(result, no._held([code]))
                self.assertFalse(result['evidenceComplete'])

    def test_depth_text_and_collection_bounds(self):
        data = fixture()
        data['en-foods.json']['foods'][0]['foodName'] = 'x' * (no.MAX_TEXT + 1)
        self.assertEqual(no.survey(blobs(data))['reasonCodes'], ['text-limit-exceeded'])
        inputs = blobs(fixture())
        inputs['en-foods.json'] = b'[' * 41 + b'0' + b']' * 41
        self.assertEqual(no.survey(inputs)['reasonCodes'], ['depth-limit-exceeded'])
        data = fixture()
        data['en-nutrients.json']['nutrients'] *= 257
        self.assertEqual(no.survey(blobs(data))['reasonCodes'], ['collection-size-limit-exceeded'])

    def test_quantified_nonfinite_and_underflow_stay_held(self):
        for value, code in (('1e-999', 'quantity-underflow'), ('1e999', 'nonfinite-quantity'), ('NaN', 'nonfinite-quantity')):
            data = fixture()
            data['en-foods.json']['foods'][0]['constituents'][0]['quantity'] = value
            result = no.survey(blobs(data))
            self.assertTrue(result['evidenceComplete'])
            self.assertIn(code, result['reasonCodes'])
            self.assertEqual(result['observations']['en']['quantities']['semantics']['invalid'], 1)

    def test_explicit_basis_structure_without_inference(self):
        data = fixture()
        data['en-foods.json']['foods'][0]['basis'] = {'amount': 100, 'unit': 'g', 'state': 'as-described', 'portion': 'edible portion'}
        result = no.survey(blobs(data))
        evidence = result['explicitBasis']
        self.assertEqual(evidence['forms']['exact-per100g-edible-as-described'], 1)
        self.assertEqual(evidence['structure']['fields']['amount']['types'], {'integer': 1})
        self.assertFalse(evidence['defaultBasisInferred'])

    def test_unknown_keys_only_export_structural_tokens(self):
        data = fixture()
        data['en-foods.json']['foods'][0]['schema_new_field'] = 'PRIVATE UNKNOWN VALUE'
        data['en-foods.json']['foods'][0]['https://private.invalid/bad-key'] = 'PRIVATE'
        result = no.survey(blobs(data))
        self.assertIn('schema_new_field', result['inputs']['en-foods.json']['rows']['fields'])
        self.assertIn('unsafe-structural-key', result['reasonCodes'])
        self.assertNotIn('PRIVATE', json.dumps(result))
        self.assertNotIn('https://', json.dumps(result))

    def test_output_overflow_discards_partial_evidence(self):
        with patch.object(no, 'MAX_OUTPUT_BYTES', 256):
            result = no.survey(blobs(fixture()))
        self.assertEqual(result, no._held(['output-size-limit-exceeded']))
        self.assertNotIn('nutrientDictionary', result)

    def test_sanitizer_rejects_injections_and_invalid_counts(self):
        good = no.survey(blobs(fixture()))
        variants = []
        bad = copy.deepcopy(good); bad['foodRows'] = ['PRIVATE']; variants.append(bad)
        bad = copy.deepcopy(good); bad['candidateGenerationEnabled'] = True; variants.append(bad)
        bad = copy.deepcopy(good); bad['reasonCodes'] = ['PRIVATE']; variants.append(bad)
        bad = copy.deepcopy(good); bad['identities']['en-foods.json']['rowCount'] = True; variants.append(bad)
        bad = copy.deepcopy(good); bad['nutrientDictionary'][0]['name'] = 'https://private.invalid'; variants.append(bad)
        bad = copy.deepcopy(good); bad['nutrientDictionary'][0]['extra'] = 'PRIVATE'; variants.append(bad)
        bad = copy.deepcopy(good); bad['observations']['en']['quantities']['semantics']['literal-zero'] = -1; variants.append(bad)
        for bad in variants:
            with self.subTest(fields=set(bad)), self.assertRaises(no.SurveyError):
                no.sanitize_report(bad)



    def test_decoder_subphases_and_python_scanner_preserve_float_hooks(self):
        raw = b'{"v":[0.0,-0.0,1.25,1e-6,5e-324],"s":"escaped \\u00e9"}'
        reports=[]
        for python_scanner in (False, True):
            phases=[]
            reports.append(no._strict_json(raw, progress=phases.append, python_scanner=python_scanner))
            for phase in ('decode-entry','decode-complete','depth-scan-entry','depth-scan-complete',
                          'json-decoder-entry','json-decoder-complete','structural-walk-entry',
                          'structural-walk-complete','float-hook-entry','decimal-zero-entry'):
                self.assertIn(phase,phases)
            self.assertLessEqual(len(phases),14)
        self.assertEqual(reports[0],reports[1])
        self.assertEqual(no.survey(blobs(fixture())), no.survey(blobs(fixture()),python_scanner=True))

    def test_python_scanner_retains_key_nonfinite_underflow_and_depth_rejections(self):
        cases=[(b'{"x":1,"x":2}','duplicate-json-key'),
               (b'[1e-999]','json-number-underflow'),(b'[1e999]','nonfinite-json-number'),
               (b'[NaN]','nonfinite-json-number'),(b'['*41+b'0'+b']'*41,'depth-limit-exceeded')]
        for raw,reason in cases:
            for python_scanner in (False,True):
                with self.subTest(reason=reason,python_scanner=python_scanner), self.assertRaisesRegex(no.SurveyError,reason):
                    no._strict_json(raw,python_scanner=python_scanner)


if __name__ == '__main__':
    unittest.main()
