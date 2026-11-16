import copy
import importlib.util
import sys
import types
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'candidate/scripts'))
import north_star_basis_restoration as B

# The source's packet() function is pure; no schema validator or acquisition is
# called. A stub lets this exact retained producer load on the local test host.
old=sys.modules.get('jsonschema_rs');sys.modules['jsonschema_rs']=types.ModuleType('jsonschema_rs')
spec=importlib.util.spec_from_file_location('selected_bulk_producer',ROOT/'selected/scripts/align-bulk-food-common.py')
producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
if old is None:sys.modules.pop('jsonschema_rs')
else:sys.modules['jsonschema_rs']=old


def inputs(value=0,state='as-sold'):
    entry={'sourceId':'off','releaseId':'synthetic-release','archiveSha256':'a'*64,'license':'Synthetic licence','independentlyAccepted':False}
    record={'id':'synthetic:profile:1','kind':'nutrientProfile','schemaVersion':'1.0',
        'provenance':{'sourceId':'off','visibility':'public','recordId':'source-record','releaseId':'synthetic-release','license':'Synthetic licence','url':'https://example.test/food','attribution':'Synthetic only'},
        'curation':{'schema':'offmenu-curation/1','policyVersion':'offmenu-curation/1','status':'selected-source-facts','humanReviewed':False,'automaticDietQualification':False,'rawSourcePayloadPublished':False,'sourceRecordReference':'synthetic-reference'},
        'data':{'basis':{'amount':100,'unit':'g','state':'profile-state-not-selected'},'nutrients':{
            'sodium':{'value':value,'unit':'mg','basis':{'amount':100,'unit':'g','state':state},'definition':'source-sodium'},
            'energy':{'value':12,'unit':'kJ','basis':{'amount':100,'unit':'g','state':state},'definition':'source-energy'}}}}
    return record,entry,producer.packet(record,'off',entry)


class BasisRestorationTests(unittest.TestCase):
    def test_exact_selected_producer_quantity_compatibility(self):
        r,e,p=inputs();before=copy.deepcopy((r,p));projection=B.native_projection(r,'off',e);out=B.restore(p,projection)
        self.assertEqual((r,p),before);self.assertEqual(out['matchedNutrientAssertions'],2)
        self.assertEqual(len(out['basisGroups']),1);self.assertEqual(out['basisGroups'][0]['sourceBasis']['state'],'as-sold')
        self.assertFalse(out['profileBasisUsed']);self.assertFalse(out['nutritionAggregationEligible']);self.assertFalse(out['publicationEligible'])
    def test_null_state_remains_unknown(self):
        r,e,p=inputs(None,None);out=B.restore(p,B.native_projection(r,'off',e));self.assertEqual(out['basisGroups'][0]['stateStatus'],'unknown')
    def test_source_zero_not_replaced(self):
        r,e,p=inputs(0);out=B.restore(p,B.native_projection(r,'off',e));self.assertFalse(out['originalQuantityModified'])
        self.assertEqual(next(a for a in p['assertions'] if a['propertyId']==B.PROP+'nutrientObservation')['value']['value'],0)
    def test_profile_basis_never_fills_missing_own_basis(self):
        r,e,_=inputs();r['data']['nutrients']['sodium'].pop('basis');p=producer.packet(r,'off',e);out=B.restore(p,B.native_projection(r,'off',e))
        self.assertEqual(out['matchedNutrientAssertions'],1);self.assertEqual(out['sourceMetricsWithoutOwnState'],1)
    def test_wrong_quantity_rejected(self):
        r,e,p=inputs();next(a for a in p['assertions'] if a['propertyId']==B.PROP+'nutrientObservation')['value']['value']=10
        with self.assertRaises(ValueError):B.restore(p,B.native_projection(r,'off',e))
    def test_source_revision_mismatch_rejected(self):
        r,e,p=inputs();p['citations'][0]['revisionId']='other'
        with self.assertRaises(ValueError):B.restore(p,B.native_projection(r,'off',e))
    def test_source_status_hold_rejected(self):
        r,e,p=inputs();r['curation']['status']='withheld'
        with self.assertRaises(ValueError):B.native_projection(r,'off',e)
    def test_private_source_rejected(self):
        r,e,p=inputs();r['provenance']['visibility']='private'
        with self.assertRaises(ValueError):B.native_projection(r,'off',e)
    def test_different_native_source_cannot_be_relabelled(self):
        r,e,p=inputs();r['provenance']['sourceId']='another-source'
        with self.assertRaises(ValueError):B.native_projection(r,'off',e)
    def test_duplicate_quantity_rejected(self):
        r,e,p=inputs();a=copy.deepcopy(next(a for a in p['assertions'] if a['propertyId']==B.PROP+'nutrientObservation'));a['id']='urn:other';p['assertions'].append(a)
        with self.assertRaises(ValueError):B.restore(p,B.native_projection(r,'off',e))
    def test_existing_state_not_overwritten(self):
        r,e,p=inputs();next(a for a in p['assertions'] if a['propertyId']==B.PROP+'nutrientObservation')['value']['basis']['state']='cooked'
        with self.assertRaises(ValueError):B.restore(p,B.native_projection(r,'off',e))
    def test_unknown_source_state_literal_not_classified(self):
        r,e,p=inputs(state='source-specific-state');out=B.restore(p,B.native_projection(r,'off',e));self.assertEqual(out['basisGroups'][0]['stateStatus'],'source-literal-not-canonicalized')
    def test_distinct_own_bases_not_collapsed(self):
        r,e,_=inputs();r['data']['nutrients']['energy']['basis']['state']='prepared';p=producer.packet(r,'off',e)
        self.assertEqual(len(B.restore(p,B.native_projection(r,'off',e))['basisGroups']),2)


if __name__=='__main__':unittest.main()
