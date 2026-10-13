import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location('projection', Path(__file__).parents[1] / 'corpus/curation.py')
projection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(projection)


def record(kind, source, data):
    return {'id': source + ':' + kind + ':1', 'kind': kind, 'countries': ['AU'],
            'provenance': {'sourceId': source, 'recordId': '1', 'visibility': 'public', 'license': 'source licence',
                           'limitationStatement': 'Australia-specific', 'countryNotice': 'Source jurisdiction', 'changes': 'Normalized facts'},
            'data': data}


class ProjectionTests(unittest.TestCase):
    def test_organization_reference_cannot_promote_ownership_or_raw_provider_body(self):
        row = record('organization', 'wikidata-food-businesses', {'name': 'Company', 'roles': ['food-manufacturer'],
                     'ownershipVerified': True, 'operationalCoverageVerified': True, 'rawFields': {'owner': 'private'}, 'credentials': 'secret'})
        projected, withheld = projection.curate([row], '1')
        self.assertFalse(withheld)
        self.assertFalse(projected[0]['data']['ownershipVerified'])
        self.assertFalse(projected[0]['data']['operationalCoverageVerified'])
        self.assertNotIn('rawFields', projected[0]['data'])
        self.assertNotIn('credentials', projected[0]['data'])

    def test_guideline_reference_excludes_advice_body_and_keeps_rights(self):
        row = record('sourceAssertion', 'dietary-guidelines', {'name': 'Guideline', 'referenceUrl': 'https://example.org/guide',
                     'guidelineBody': 'Protected full text', 'dietRules': {'recommendation': 'unreviewed'}, 'contentPermission': 'holder permission required'})
        projected, _ = projection.curate([row], '1')
        self.assertNotIn('guidelineBody', projected[0]['data'])
        self.assertNotIn('dietRules', projected[0]['data'])
        self.assertEqual(projected[0]['data']['contentPermission'], 'holder permission required')
        self.assertFalse(projected[0]['curation']['automaticDietQualification'])

    def test_place_country_aliases_do_not_allocate_unsupported_source_tags(self):
        row = record('retailer', 'overture-food-places', {'name': 'Shop', 'inventoryAvailability': 'in-stock', 'ownershipVerified': True})
        row['countries'] = ['UK', 'XK']
        row['provenance']['releaseId'] = 'release'
        row['provenance']['licenseNotices'] = ['Apache-2.0.txt']
        projected, _ = projection.curate([row], '1')
        self.assertEqual(projected[0]['countries'], ['GB'])
        self.assertEqual(projected[0]['data']['sourceCountryTags'], ['UK', 'XK'])
        self.assertEqual(projected[0]['data']['inventoryAvailability'], 'unknown')
        self.assertFalse(projected[0]['data']['ownershipVerified'])
        self.assertIn('notices/overture-food-places/release/Apache-2.0.txt', projected[0]['provenance']['licenseNotices'][0])

    def test_national_composition_retains_required_derivative_notices(self):
        row = record('nutrientProfile', 'afcd', {'foodName': 'Food', 'basis': {'amount': 100, 'unit': 'g'},
                     'nutrients': {'protein': {'value': 3, 'unit': 'g'}}})
        projected, _ = projection.curate([row], '1')
        for key in ['limitationStatement', 'countryNotice', 'changes']:
            self.assertEqual(projected[0]['provenance'][key], row['provenance'][key])
