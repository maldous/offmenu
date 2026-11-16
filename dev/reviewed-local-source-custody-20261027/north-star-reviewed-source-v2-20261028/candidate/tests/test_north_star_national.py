import copy,json,tempfile,time,unittest
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'));sys.path.insert(0,str(ROOT/'tests'))
import north_star_national_context as C
import derive_north_star_national as M
from test_north_star_derivations import fixture,resource,CONTRACT
from test_north_star_bulk import package

def national(value=0):
    packet=fixture(value);food=resource('urn:test:food','FoodConcept');profile=resource('urn:test:profile','FoodCompositionObservation');metric=resource('urn:test:metric','FoodCompositionObservation')
    packet['resources']=[food,profile,metric]
    quantity=copy.deepcopy(packet['assertions'][0]);quantity.update(id='urn:test:metricvalue',subjectId=metric['id'],propertyId=M.PROP+'metricValue',sourcePath='data.nutrients.sodium.value')
    definition=copy.deepcopy(quantity);definition.update(id='urn:test:metricdefinition',propertyId=M.PROP+'metricDefinition',sourcePath='data.nutrients.sodium.definition',value={'kind':'identifier','value':'urn:source:method-defined-sodium'})
    metadata=copy.deepcopy(quantity);metadata.update(id='urn:test:metricmetadata',propertyId=M.PROP+'originalMetricFields',sourcePath='data.nutrients.sodium',value={'kind':'structure','fields':{'method':{'kind':'identifier','value':'source-method-A'},'limit':{'kind':'number','value':0.01}}})
    packet['assertions']=[quantity,definition,metadata]
    food_edge=copy.deepcopy(packet['relations'][0]);food_edge.update(id='urn:test:foodedge',subjectId=profile['id'],predicateId=M.REL+'observesFood',objectId=food['id'])
    metric_edge=copy.deepcopy(food_edge);metric_edge.update(id='urn:test:metricedge',predicateId=M.REL+'hasMetricObservation',objectId=metric['id'],sourcePath='data.nutrients.sodium')
    packet['relations']=[food_edge,metric_edge]
    return packet

class NationalTests(unittest.TestCase):
    def test_exact_context_preserves_quantity_method_and_definition(self):
        p=national();before=copy.deepcopy(p);out=C.derive(p,CONTRACT);a=out['assertions'][0];f=a['value']['fields']
        self.assertEqual(p,before);self.assertEqual(f['quantity'],p['assertions'][0]['value']);self.assertEqual(f['sourceMetricMetadata'],p['assertions'][2]['value'])
        self.assertEqual(f['sourceMetricDefinition'],p['assertions'][1]['value']);self.assertEqual(a['status'],'candidate');self.assertIsNone(a['confidence']['probability'])
        self.assertEqual(len(a['derivation']['inputDigests']),3)
    def test_unknown_is_not_zero(self):
        p=national(None);p['assertions'][0]['status']='unknown';f=C.derive(p,CONTRACT)['assertions'][0]['value']['fields']
        self.assertIsNone(f['quantity']['value']);self.assertTrue(f['unknownValue']['value']);self.assertEqual(f['sourceMetricValueStatus']['value'],'unknown')
        self.assertFalse(C.derive(national(0),CONTRACT)['assertions'][0]['value']['fields']['unknownValue']['value'])
    def test_different_source_citations_reject_context(self):
        p=national();other=copy.deepcopy(p['citations'][0]);other.update(id='urn:test:othercitation',sourceId='other-source',originalRecordId='other-record');p['citations'].append(other);p['assertions'][2]['citationIds']=[other['id']]
        self.assertEqual(C.derive(p,CONTRACT)['assertions'],[])
    def test_context_resource_citation_identity_must_match(self):
        p=national();other=copy.deepcopy(p['citations'][0]);other.update(id='urn:test:resourcecitation',sourceId='other-source');p['citations'].append(other);p['resources'][2]['citationIds']=[other['id']]
        self.assertEqual(C.derive(p,CONTRACT)['assertions'],[])
    def test_index_excludes_cross_source_context_even_with_same_scope(self):
        p=national();side=C.derive(p,CONTRACT);other=copy.deepcopy(p['citations'][0]);other.update(id='urn:test:othercontextcitation',sourceId='other-source');p['citations'].append(other);side['assertions'][0]['citationIds']=[other['id']]
        rows,_=M.index_rows(p,side);metric=next(r for r in rows if r[0]=='N' and r[1]=='urn:test:metric')
        self.assertEqual(metric[-1],0)
    def test_wrong_metric_definition_path_does_not_join(self):
        p=national();p['assertions'][1]['sourcePath']='data.nutrients.potassium.definition';self.assertEqual(C.derive(p,CONTRACT)['assertions'],[])
    def test_superseded_source_field_does_not_join(self):
        p=national();p['assertions'][0]['status']='superseded';self.assertEqual(C.derive(p,CONTRACT)['assertions'],[])
    def test_missing_state_never_invented(self):
        a=C.derive(national(),CONTRACT)['assertions'][0];self.assertFalse(a['value']['fields']['preparationBasisCarried']['value'])
    def test_full_typed_food_profile_metric_query(self):
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,[national()])
            m=M.run(src,out,pins[0],workers=1,seconds=60,reserve=0,schema_sha=pins[1],contract_sha=pins[2],metadata_root=src)
            self.assertTrue(m['complete']);q=m['consumerIndex']['queries']
            self.assertEqual(q['foodProfileMetricContextPaths']['count'],1);self.assertEqual(q['foodsWithMetricContext']['count'],1)
            self.assertEqual(q['profileMetricEdgesResolved']['count'],1);self.assertEqual(q['unresolvedOrIncompatibleStructuralEdges']['count'],0)
    def test_cross_packet_wrong_source_target_not_resolved(self):
        p=national();metric=copy.deepcopy(p);metric['resources']=[p['resources'][2]];metric['relations']=[]
        p['resources']=p['resources'][:2];p['assertions']=[]
        metric['citations'][0]['sourceId']='other-source'
        with tempfile.TemporaryDirectory() as t:
            src=Path(t)/'source';out=Path(t)/'output';pins=package(src,[p,metric])
            m=M.run(src,out,pins[0],workers=1,seconds=60,reserve=0,schema_sha=pins[1],contract_sha=pins[2],metadata_root=src)
            self.assertEqual(m['consumerIndex']['queries']['foodProfileMetricContextPaths']['count'],0)

if __name__=='__main__':unittest.main()
