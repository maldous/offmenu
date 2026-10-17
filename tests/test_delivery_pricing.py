import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from offmenu.delivery_pricing import normalize, import_observations, register, page, registry, SOURCE
from offmenu.aldi_datasource import graph_packet


def sample(**changes):
    # Synthetic fixtures, never admitted to the source corpus.
    row = dict(partnerId='test-partner', storeId='shop', itemId='sku', observationId='capture1',
        name='Test food', retailerName='Test shop', country='JP', currency='JPY', amount=123,
        observedAt='2026-10-16T10:00:00+09:00', sourceUrl='https://example.com/item',
        priceDisplay='¥123', priceBasis='per-pack', language='ja', packLabel='100 g')
    row.update(changes)
    return row


class DeliveryPricingTests(unittest.TestCase):
    def test_scoped_identity(self):
        first=normalize(sample(),1,'a','r')
        for change in ({'partnerId':'other'}, {'country':'AU'}, {'storeId':'other'}, {'itemId':'other'}):
            self.assertNotEqual(first[0]['id'],normalize(sample(**change),1,'a','r')[0]['id'])
        self.assertEqual(first[0]['id'],normalize(sample(observationId='capture2'),1,'a','r')[0]['id'])
        self.assertNotEqual(first[1]['id'],normalize(sample(observationId='capture2'),1,'a','r')[1]['id'])

    def test_currency_conditions_and_language_preserved(self):
        row=normalize(sample(membership={'sourceText':'members only'},promotion={'sourceText':'sale'}),1,'a','r')[1]
        self.assertEqual(row['data']['currency'],'JPY')
        self.assertIsNone(row['data']['fees'])
        self.assertIsNone(row['data']['currencyConversion'])
        self.assertEqual(row['data']['membership']['sourceText'],'members only')
        graph=graph_packet(row)
        self.assertEqual(graph['citations'][0]['sourceId'],SOURCE)
        self.assertEqual(graph['resources'][0]['names'][0]['language'],'ja')

    def test_invalid_evidence_rejected(self):
        for changes in ({'amount':True},{'amount':float('nan')},{'amount':-1}, {'observedAt':'2026-10-16'},
                        {'country':'Japan'}, {'currency':'yen'}, {'sourceUrl':'https://user:pass@example.com'},
                        {'itemId':''}, {'priceBasis':'guessed'}, {'fees':0}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):
                normalize(sample(**changes),1,'a','r')

    def test_roundtrip_history_and_tamper(self):
        with tempfile.TemporaryDirectory() as temp, patch.dict('os.environ',{'OFFMENU_DATA_ROOT':temp}):
            root=Path(temp); source=root/'input.jsonl'; output=root/'snapshot'
            source.write_text('\n'.join(json.dumps(r) for r in [sample(),sample(observationId='capture2',amount=125)]))
            result=import_observations(source,output)
            self.assertEqual(result['counts'],{'product':1,'priceObservation':2,'retailer':1})
            register(output)
            records=page(SOURCE,kind='priceObservation',limit=1)
            self.assertEqual(records['pagination']['total'],2)
            self.assertEqual(records['pagination']['nextOffset'],1)
            self.assertEqual(records['records'][0]['data']['amount'],123)
            with (output/'records.sqlite').open('ab') as f: f.write(b'tamper')
            with self.assertRaises(ValueError): page(SOURCE)

    def test_duplicate_and_conflict_no_partial_output(self):
        for second in (sample(),sample(observationId='capture2',name='Conflicting product')):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp); source=root/'input.jsonl'; output=root/'snapshot'
                source.write_text('\n'.join(map(json.dumps,[sample(),second])))
                with self.assertRaises(ValueError): import_observations(source,output)
                self.assertFalse(output.exists())

    def test_registry_is_not_price_coverage(self):
        rows=registry()['partners']
        self.assertEqual(len(rows),len({r['id'] for r in rows}))
        self.assertEqual(sum(r['capturedObservations'] for r in rows),2722)
        self.assertTrue(all(r['capturedObservations']==0 for r in rows if r['id']!='doordash'))

if __name__=='__main__': unittest.main()
