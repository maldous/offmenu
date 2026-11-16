import copy
import sys
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'candidate/scripts'))
sys.path.insert(0,str(ROOT/'review'))
from test_recipe_fidelity import fixture
from derive_recipe_context import derive
from reconcile_recipe_fidelity import native_for_original


def inputs():
    n,p=fixture();n['data']['yield']={'value':None,'unit':'portion'}
    n['data']['ingredients'][0]['scaling']='unknown'
    n['provenance']={'originSourceId':'synthetic','recordId':'native-one','url':'https://example.test/fixture',
        'license':'CC0','originalContentSha256':'a'*64,'sourceRevision':'fixture'}
    p['citations'][0]['contentSha256']='a'*64
    p['assertions']=[f for f in p['assertions'] if f['propertyId']!='urn:offmenu:property:yield']
    return n,p


class RecipeContextTests(unittest.TestCase):
    def test_unknown_fields_exact_copy_and_immutable(self):
        n,p=inputs();before=copy.deepcopy((n,p));r=derive(n,p)
        self.assertEqual((n,p),before);self.assertEqual(len(r['assertions']),2)
        self.assertIsNone(r['assertions'][0]['value']['value'])
        self.assertEqual(r['assertions'][1]['value']['value'],'unknown')
        self.assertFalse(r['automaticPlanningEligible']);self.assertFalse(r['publicationEligible'])
        self.assertEqual(r['identityEffect'],'none')

    def test_zero_is_preserved_known(self):
        n,p=inputs();n['data']['yield']['value']=0
        self.assertEqual(derive(n,p)['assertions'][0]['value']['value'],0)
        self.assertNotIn('yield-unknown',derive(n,p)['assertions'][0]['value']['qualifiers'])

    def test_no_overwrite_existing(self):
        n,p=inputs();p['assertions'].append({'id':'existing','subjectId':'urn:test:recipe','propertyId':'urn:offmenu:property:yield','value':{'value':99}})
        self.assertEqual(len(derive(n,p)['assertions']),1)

    def test_wrong_record_reference_rejected(self):
        n,p=inputs();p['assertions'][0]['value']['value']='other'
        with self.assertRaises(ValueError):derive(n,p)

    def test_exact_provenance_field_reference(self):
        n,p=inputs();n['provenance']['recordId']='source-id';p['assertions'][0]['sourcePath']='provenance.recordId';p['assertions'][0]['value']['value']='source-id';p['citations'][0]['originalRecordId']='source-id'
        self.assertEqual(len(derive(n,p)['assertions']),2)

    def test_citation_content_mismatch_rejected(self):
        n,p=inputs();p['citations'][0]['contentSha256']='b'*64
        with self.assertRaises(ValueError):derive(n,p)

    def test_scope_mismatch_rejected(self):
        n,p=inputs();p['relations'][0]['scope']={'visibility':'private','ownerId':'other'}
        with self.assertRaises(ValueError):derive(n,p)

    def test_boolean_yield_is_not_zero(self):
        n,p=inputs();n['data']['yield']['value']=False
        with self.assertRaises(ValueError):derive(n,p)

    def test_scaling_prose_rejected(self):
        n,p=inputs();n['data']['ingredients'][0]['scaling']='unsafe arbitrary prose'
        with self.assertRaises(ValueError):derive(n,p)

    def test_wrong_endpoint_type_rejected(self):
        n,p=inputs();p['resources'][1]['type']='urn:offmenu:type:FoodConcept'
        with self.assertRaises(ValueError):derive(n,p)

    def test_duplicate_input_identity_rejected(self):
        n,p=inputs();p['assertions'].append(copy.deepcopy(p['assertions'][0]))
        with self.assertRaises(ValueError):derive(n,p)


if __name__=='__main__':unittest.main()
