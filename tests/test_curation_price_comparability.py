"""Authored price projection regressions; no retained source inputs or IO."""
import copy
import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('price_projection', Path(__file__).parents[1] / 'corpus/curation.py')
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


def row(data):
    return {'id': 'prices:priceObservation:synthetic-1', 'kind': 'priceObservation',
            'countries': ['AU'], 'provenance': {'sourceId': 'prices', 'recordId': 'synthetic-1',
                'license': 'authored fixture', 'limitationStatement': 'Synthetic only'}, 'data': data}


def project(data):
    records, withheld = projection.curate([row(data)], 'synthetic-test')
    assert not withheld
    return records[0]


class PriceComparabilityTests(unittest.TestCase):
    def test_amount_currency_date_do_not_qualify_comparison(self):
        output = project({'amount': 2, 'currency': 'AUD', 'observedAt': '2026-10-01'})
        self.assertIs(output['data']['comparable'], False)
        self.assertEqual(output['data']['amount'], 2)
        self.assertEqual(output['data']['currency'], 'AUD')
        self.assertEqual(output['data']['observedAt'], '2026-10-01')

    def test_rich_conditions_are_not_qualification_or_new_publication_permission(self):
        conditions = {'variant': 'vanilla', 'pack': {'value': 500, 'unit': 'g'},
                      'taxIncluded': False, 'loyalty': {'required': True},
                      'fulfilment': {'channel': 'delivery', 'shippingAmount': 5}}
        for key in conditions:
            with self.subTest(missing=key):
                supplied = dict(conditions)
                supplied.pop(key)
                output = project({'amount': 2, 'currency': 'AUD', 'observedAt': '2026-10-01', **supplied})
                self.assertIs(output['data']['comparable'], False)
                for field in conditions:
                    self.assertNotIn(field, output['data'])
        output = project({'amount': 2, 'currency': 'AUD', 'observedAt': '2026-10-01', **conditions,
                          'comparable': True, 'comparisonReviewed': True})
        self.assertIs(output['data']['comparable'], False)
        self.assertNotIn('comparisonReviewed', output['data'])

    def test_known_promotion_false_zero_and_unknowns_remain_distinct(self):
        for promotion in (False, True, None):
            with self.subTest(promotion=promotion):
                output = project({'amount': 0, 'currency': 'AUD', 'observedAt': '2026-10-01',
                                  'promotion': promotion, 'regularAmount': 0, 'unitPrice': 0, 'unit': 'kg'})['data']
                self.assertIs(output['promotion'], promotion)
                self.assertEqual(output['amount'], 0)
                self.assertEqual(output['regularAmount'], 0)
                self.assertEqual(output['unitPrice'], 0)
                self.assertEqual(output['unit'], 'kg')
                self.assertIs(output['comparable'], False)
        output = project({})['data']
        for field in ('amount', 'currency', 'observedAt', 'unitPrice', 'unit', 'promotion', 'regularAmount'):
            self.assertIsNone(output[field])

    def test_incomplete_or_malformed_basics_do_not_gain_comparability(self):
        for amount, currency, date in [(None, 'AUD', '2026-10-01'), (2, None, '2026-10-01'),
            (2, 'AUD', None), (-1, 'AUD', '2026-10-01'), (True, 'AUD', 'not-a-date'),
            (float('nan'), 'AUD', '2026-10-01'), (float('inf'), 'AUD', '2026-10-01')]:
            with self.subTest(amount=amount, currency=currency, date=date):
                self.assertIs(project({'amount': amount, 'currency': currency, 'observedAt': date})['data']['comparable'], False)

    def test_dated_observation_is_not_stock_and_allowlist_stays_closed(self):
        data = {'identifiers': [{'system': 'barcode', 'value': '00123'}],
                'amount': 2, 'currency': 'AUD', 'observedAt': '2026-10-01',
                'retailer': {'name': 'Synthetic shop', 'externalId': '000', 'location': 'private location'},
                'availability': 'in-stock', 'priceType': 'offer', 'rawFields': {'secret': 'fixture-only'}}
        output = project(data)
        self.assertEqual(output['data']['identifiers'], data['identifiers'])
        self.assertEqual(output['data']['retailer'], {'name': 'Synthetic shop', 'externalId': '000'})
        self.assertEqual(output['data']['availability'], 'unknown')
        self.assertEqual(output['data']['priceType'], 'dated-observation')
        self.assertNotIn('rawFields', output['data'])
        self.assertEqual(set(output['data']), {'identifiers', 'amount', 'currency', 'observedAt',
            'unitPrice', 'unit', 'promotion', 'regularAmount', 'priceType', 'availability', 'retailer', 'comparable'})
        self.assertFalse(output['curation']['rawSourcePayloadPublished'])
        self.assertEqual(output['provenance']['limitationStatement'], 'Synthetic only')

    def test_source_conditions_are_not_mutated_or_inferred(self):
        original = row({'amount': 2, 'currency': 'AUD', 'observedAt': '2026-10-01',
                        'pack': {'value': 500, 'unit': 'g'}, 'variant': 'vanilla', 'taxIncluded': None,
                        'loyalty': {'required': True}, 'fulfilment': {'channel': 'delivery', 'shippingAmount': 5}})
        before = copy.deepcopy(original)
        projection.curate([original], 'synthetic-test')
        self.assertEqual(original, before)


if __name__ == '__main__':
    unittest.main()
