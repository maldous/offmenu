"""Actual importer function regression using only generated OFF records."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

from offmenu.refresh import product_adapters as a


class OptionalNutritionTests(unittest.TestCase):
    def setUp(self):
        self.context = a.ProductContext('off','generated-release','2026-10-25T00:00:00Z',
                                       'generated-only','synthetic','1'*64,'2'*64)
        self.context.validate()

    def row(self, nutrients, basis='100g'):
        return {'code':'012345678905','product_name_fr':'Chaussure générée',
                'lang':'fr','categories_tags':['fr:chaussures'],
                'nutrition_data_per':basis,'nutriments':nutrients}

    def test_trace_preserves_identity_metadata_and_other_numeric_nutrient(self):
        row=self.row({'proteins_100g':'Tr','fat_100g':'3.5'});before=copy.deepcopy(row)
        product,profile=list(a._off(self.context,row))
        self.assertEqual(product['data']['identifiers'][0]['value'],'012345678905')
        self.assertEqual(product['data']['names']['fr'],'Chaussure générée')
        self.assertEqual(product['data']['sourceCategoryFields']['categories_tags'],['fr:chaussures'])
        self.assertNotIn('protein',profile['data']['nutrients'])
        self.assertEqual(profile['data']['nutrientDispositions']['proteins_100g']['sourceAmount'],'Tr')
        self.assertEqual(profile['data']['nutrientDispositions']['proteins_100g']['reason'],'trace-not-quantified')
        self.assertEqual(profile['data']['nutrients']['fat']['value'],3.5)
        self.assertEqual(row,before)

    def test_identity_yield_precedes_optional_number_parser(self):
        old=a._number
        a._number=lambda *_: (_ for _ in ()).throw(AssertionError('nutrition invoked'))
        try:
            product=next(a._off(self.context,self.row({'proteins_100g':'Tr'})))
            self.assertEqual(product['kind'],'product')
        finally:a._number=old

    def test_unknown_basis_not_coerced_to_100g(self):
        product,profile=list(a._off(self.context,self.row({'proteins_100g':4},'serving')))
        self.assertEqual(product['kind'],'product')
        self.assertIsNone(profile['data']['basis'])
        self.assertEqual(profile['data']['nutrients'],{})
        self.assertEqual(profile['data']['nutrientDispositions']['proteins_100g']['reason'],'source-basis-unknown-or-unsupported')

    def test_malformed_bool_negative_and_null_are_explicit_unknown_not_zero(self):
        for value in ['bad',True,-1,None]:
            product,profile=list(a._off(self.context,self.row({'proteins_100g':value})))
            self.assertEqual(product['kind'],'product')
            self.assertNotIn('protein',profile['data']['nutrients'])
            self.assertEqual(profile['data']['nutrientDispositions']['proteins_100g']['sourceAmount'],value)
        _,profile=list(a._off(self.context,self.row({'proteins_100g':0})))
        self.assertEqual(profile['data']['nutrients']['protein']['value'],0)

    def test_nonobject_optional_nutriments_still_emits_product(self):
        product,profile=list(a._off(self.context,self.row('not-an-object')))
        self.assertEqual(product['kind'],'product')
        self.assertEqual(product['data']['rawNutriments'],'not-an-object')
        self.assertEqual(profile['data']['nutrients'],{})

    def test_ml_basis_and_english_name_language_not_inferred_from_fallback(self):
        row=self.row({'proteins_100g':'1'},'100ml')
        row['product_name_en']='Generated shoe'
        product,profile=list(a._off(self.context,row))
        self.assertEqual(profile['data']['basis']['unit'],'ml')
        self.assertEqual(product['data']['names']['en'],'Generated shoe')
        self.assertEqual(product['data']['nameLanguage'],'en')
        self.assertEqual(product['data']['sourceCategoryFields']['lang'],'fr')


if __name__=='__main__':unittest.main()
