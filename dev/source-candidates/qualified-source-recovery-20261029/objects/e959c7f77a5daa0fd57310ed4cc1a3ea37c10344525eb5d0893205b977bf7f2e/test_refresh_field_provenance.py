import copy
import unittest
from offmenu.refresh.field_provenance import datum_pointers, field_origin_errors


class FieldProvenanceTests(unittest.TestCase):
    def fixture(self):
        row = {'id': 'x', 'data': {'a/b': [0, None], 'name': 'Example'},
               'provenance': {'sourceId': 'source', 'releaseId': 'release'}}
        origin = {'kind': 'source', 'sourceId': 'source', 'releaseId': 'release', 'inputPath': 'input.csv',
                  'inputSha256': 'a'*64, 'sourceRecordId': 'row-1',
                  'sourceField': 'reviewed-field-coordinate', 'transform': 'identity'}
        row['provenance']['fieldOrigins'] = {p: dict(origin) for p in datum_pointers(row['data'])}
        return row

    def test_all_data_including_zero_and_unknown_require_origins(self):
        row = self.fixture()
        self.assertEqual(field_origin_errors(row, {'input.csv': 'a'*64}), [])
        self.assertIn('/data/a~1b/1', row['provenance']['fieldOrigins'])
        del row['provenance']['fieldOrigins']['/data/a~1b/1']
        self.assertIn('field-origin-missing', field_origin_errors(row, {'input.csv': 'a'*64}))

    def test_pin_source_and_coordinate_errors_accumulate(self):
        row = self.fixture()
        origins = list(row['provenance']['fieldOrigins'].values())
        origins[0]['inputSha256'] = 'b'*64
        origins[1]['sourceId'] = 'foreign'
        del origins[2]['sourceField']
        self.assertEqual(field_origin_errors(row, {'input.csv': 'a'*64}),
                         ['field-origin-incomplete', 'field-origin-input-pin-mismatch', 'field-origin-source-mismatch'])

    def test_derived_multiple_inputs_and_code_constants(self):
        row = self.fixture()
        origins = row['provenance']['fieldOrigins']
        source = dict(origins['/data/name'])
        origins['/data/name'] = {'kind': 'derived', 'policySha256': 'b'*64,
                                 'transform': 'reviewed-name-join', 'inputs': [source, dict(source)]}
        origins['/data/a~1b/1'] = {'kind': 'constant', 'policySha256': 'b'*64, 'symbol': 'unknown-value'}
        self.assertEqual(field_origin_errors(row, {'input.csv': 'a'*64}, policy_pins=('b'*64,)), [])
        self.assertIn('field-origin-policy-pin-mismatch', field_origin_errors(row, {'input.csv': 'a'*64}))
        origins['/data/name']['inputs'] = []
        self.assertIn('field-origin-derived-inputs-invalid', field_origin_errors(row, {'input.csv': 'a'*64}, policy_pins=('b'*64,)))

    def test_no_auto_generated_provenance_or_mutation(self):
        row = self.fixture()
        del row['provenance']['fieldOrigins']
        before = copy.deepcopy(row)
        self.assertEqual(field_origin_errors(row, {'input.csv': 'a'*64}), ['field-origins-required'])
        self.assertEqual(row, before)

if __name__ == '__main__':
    unittest.main()
