import importlib.util
import pathlib
import unittest
ROOT=pathlib.Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('w54',ROOT/'scripts/global-data-validation/worker-54-recipe-quantities.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)
class SyntheticQuantityCases(unittest.TestCase):
    """Synthetic grammar cases, not retained recipe evidence."""
    def test_locales_ranges_fractions(self):
        for text,locale,value in [('1,5 g sucre','fr','3/2'),('½ kg flour','en','1/2'),('1 1/2 cups flour','en','3/2'),('١٫٥ g ملح','ar','3/2'),('250克 糖','zh','250')]:
            self.assertEqual(w.parse(text,locale)['value'],value)
        self.assertEqual(w.parse('1–2 g salt','en')['range'],['1','2'])
    def test_unknowns(self):
        for text in ['salt to taste','4 eggs','1,000 g sugar','1.000 g sugar','250克拉','250克未知','2gα','1/0 g salt','2-1 g flour','0 g salt','1 cup (240 g) butter','2 x 400 g cans','1 g sugar + salt 2 g']:
            self.assertEqual(w.parse(text,'en')['status'],'UNKNOWN',text)
    def test_original_coordinates_and_optional(self):
        text='  ½ kg flour (optional)';r=w.parse(text,'en',{'line':2},{'revisionId':3})
        self.assertEqual(r['originalLexeme'],text);self.assertEqual(text[slice(*r['amountSpan'])],'½');self.assertEqual(r['optional'],'candidate');self.assertEqual(r['provenance']['revisionId'],3)
    def test_unicode_unit_delimiters(self):
        # Synthetic boundary probes; source characters are never normalized away.
        for text in ['2g\u0301','2g\u200dα','2g\u200c','2g\ufeff','2g\u2060','2g\ufe0f','2g\u20dd','2g\x00','2g\u200b','2gα','250克拉']:
            result=w.parse(text,'en')
            self.assertEqual(result['status'],'UNKNOWN',repr(text))
            self.assertEqual(result['originalLexeme'],text)
        for text,unit in [('2g salt','g'),('2千克 米','kg'),('250克 糖','g'),('2g (salt)','g'),('2g\tflour','g')]:
            result=w.parse(text,'en');self.assertEqual(result['unit'],unit);self.assertEqual(result['status'],'candidate')
    def test_yield(self):
        self.assertEqual(w.parse_yield()['status'],'UNKNOWN');self.assertEqual(w.parse_yield('4 servings','en')['value'],'4');self.assertEqual(w.parse_yield('500 g cake','en')['status'],'UNKNOWN')
    def test_limits(self):
        with self.assertRaises(ValueError):w.inspect(limit=1001)
        with self.assertRaises(ValueError):w.inspect(limit=0,expected='0'*64)
class ActualRetainedRecipe(unittest.TestCase):
    def test_pinned_licensed_reference_no_false_portion(self):
        report=w.inspect(limit=1);ref=report['refs'][0]
        self.assertEqual(report['sha256'],w.EXPECTED);self.assertEqual(ref['provenance']['revisionId'],4608393)
        self.assertEqual(ref['provenance']['license'],'CC BY-SA 4.0');self.assertEqual(ref['results'][0]['status'],'UNKNOWN')
        self.assertEqual(ref['results'][2]['unit'],'teaspoon');self.assertEqual(ref['results'][2]['value'],'1')
        self.assertTrue(ref['yield'].startswith('UNKNOWN'));self.assertEqual(ref['results'][2]['coordinate']['jsonPointer'],'/data/ingredients/2/originalText')

class ActualOriginalCustody(unittest.TestCase):
    def test_six_pinned_original_languages_fail_closed(self):
        import json,copy
        proof=json.loads((ROOT/'docs/global-data-validation/worker-54-quantity-fixtures.json').read_text())
        results=w.inspect_original(proof)
        self.assertEqual([r['language'] for r in results],['hi','ar','cs','el','fa','zh'])
        for record in results:
            self.assertEqual(record['yield'],'UNKNOWN')
            for result in record['bullet_results']:
                self.assertEqual(result['status'],'UNKNOWN') # Unsupported units/prose are not invented amounts.
                self.assertIn('bodyCharacterSpan',result['coordinate'])
                self.assertNotIn('originalLexeme',result)
        for field,value in [('revisionId',-1),('recordId','-1'),('sourceDate','1900-01-01T00:00:00Z'),('originSourceId','wikibooks:en'),('attribution','wrong contributor'),('rightsEvidenceUrl','https://example.invalid')]:
            changed=copy.deepcopy(proof);changed['records'][0]['provenance'][field]=value
            with self.assertRaises(ValueError,msg=field):w.inspect_original(changed)
        for field,value in [('revisionId',-1),('recordId','-1'),('timestamp','1900-01-01T00:00:00Z'),('title','incorrect title'),('contentmodel','plaintext')]:
            changed=copy.deepcopy(proof);changed['records'][0]['original'][field]=value
            with self.assertRaises(ValueError,msg=field):w.inspect_original(changed)
        changed=copy.deepcopy(proof);changed['records'][0]['original']['body_sha256']='0'*64
        with self.assertRaises(ValueError):w.inspect_original(changed)

if __name__=='__main__':unittest.main()
