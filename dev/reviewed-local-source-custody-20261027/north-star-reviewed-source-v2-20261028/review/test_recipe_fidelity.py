"""Independent finite synthetic fidelity/extent/output-boundary tests."""
import contextlib
import copy
import gzip
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'candidate/scripts'))
import reconcile_recipe_fidelity as subject
P = 'urn:offmenu:property:'; R = 'urn:offmenu:relation:'; T = 'urn:offmenu:type:'


def fixture(amount=None):
    native = {'id': 'native-one', 'data': {'yield': {'value': 2, 'unit': 'servings'},
        'automaticPlanningEligible': False, 'ingredients': [{'amount': amount, 'unit': 'g' if amount is not None else None,
        'sourceQuantity': {'value': amount, 'unit': 'g' if amount is not None else None, 'status': 'source-reported'}, 'quantityStatus': 'source-reported'}]}}
    common = {'scope': {'visibility': 'public', 'reuseScope': 'Synthetic only'}, 'citationIds': ['urn:test:citation']}
    def resource(identifier, kind):
        return dict(common, id=identifier, type=T+kind, identityStatus='source-scoped', names=[])
    def fact(identifier, owner, prop, path, value):
        return dict(common, id=identifier, subjectId=owner, propertyId=P+prop, sourcePath=path, value=value, status='source-asserted')
    quantity = {'kind': 'quantity', 'value': amount, 'unitId': 'urn:offmenu:unit:g' if amount is not None else None,
        'sourceValue': amount, 'sourceUnit': 'g' if amount is not None else None, 'dimension': 'mass' if amount is not None else 'unknown', 'qualifiers': []}
    graph = {'schemaVersion':'offmenu-common/1',
        'resources': [resource('urn:test:recipe','RecipeVariant'),resource('urn:test:mention','IngredientMention')],
        'assertions': [
            fact('urn:test:original','urn:test:recipe','originalSourceRecord','id',{'kind':'identifier','value':'native-one'}),
            fact('urn:test:yield','urn:test:recipe','yield','data.yield',{'kind':'quantity','value':2,'unitId':'urn:offmenu:unit:portion','dimension':'count','sourceValue':2,'sourceUnit':'servings','qualifiers':['source-yield']}),
            fact('urn:test:quantity','urn:test:mention','requiredQuantity','data.ingredients.0.sourceQuantity',quantity)],
        'relations':[dict(common,id='urn:test:uses',subjectId='urn:test:recipe',predicateId=R+'usesIngredient',objectId='urn:test:mention',status='source-asserted',sourcePath='data.ingredients.0')],
        'citations':[{'id':'urn:test:citation','sourceId':'synthetic','originalRecordId':'native-one','originalUrl':'https://example.test/fixture','revisionId':'fixture','license':'CC0','attribution':'Synthetic','scope':common['scope']}], 'translations':[]}
    return native, graph


class RecipeFidelityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.package = self.root/'package'; self.package.mkdir()

    def tearDown(self): self.tmp.cleanup()

    def reconcile(self, native=None, graph=None, repeat_graph=False):
        if native is None: native, graph = fixture()
        files = []
        for key, rows in [('native.jsonl.gz',[native]),('graph.jsonl.gz',[graph,graph] if repeat_graph else [graph])]:
            raw = gzip.compress(('\n'.join(json.dumps(r) for r in rows)+'\n').encode()); (self.package/key).write_bytes(raw)
            meta={'key':key,'bytes':len(raw),'sha256':hashlib.sha256(raw).hexdigest()}
            if key.startswith('graph'):meta['packets']=len(rows)
            files.append(meta)
        raw=json.dumps({'releaseId':'synthetic','files':files}).encode();(self.package/'manifest.json').write_bytes(raw)
        with contextlib.redirect_stdout(io.StringIO()):
            return subject.reconcile(self.package,hashlib.sha256(raw).hexdigest(),'native.jsonl.gz','graph.jsonl.gz',self.root/'report.json')

    def test_positive_unknown_value_preserved(self):
        result=self.reconcile()
        self.assertEqual(result['status'],'exact-normalized-input-fields-preserved')
        self.assertEqual(result['counts']['nativeCanonicalUnknownAmounts'],1)

    def test_zero_is_known_not_unknown(self):
        native,graph=fixture(0);result=self.reconcile(native,graph)
        self.assertEqual(result['status'],'exact-normalized-input-fields-preserved')
        self.assertEqual(result['counts']['nativeCanonicalKnownAmounts'],1)
        self.assertEqual(result['counts'].get('nativeCanonicalUnknownAmounts',0),0)

    def test_null_changed_to_zero_detected(self):
        native,graph=fixture();graph['assertions'][2]['value']['value']=0
        self.assertEqual(self.reconcile(native,graph)['status'],'alignment-field-differences')

    def test_duplicate_graph_record_refused(self):
        native,graph=fixture()
        with self.assertRaises(ValueError):self.reconcile(native,graph,repeat_graph=True)

    def test_duplicate_graph_resource_id_refused(self):
        native,graph=fixture();graph['resources'].append(copy.deepcopy(graph['resources'][1]))
        with self.assertRaises(ValueError):self.reconcile(native,graph)

    def test_wrong_quantity_subject_refused(self):
        native,graph=fixture();graph['assertions'][2]['subjectId']='urn:test:recipe'
        with self.assertRaises(ValueError):self.reconcile(native,graph)

    def test_extra_graph_ingredient_extent_refused(self):
        native,graph=fixture();extra=copy.deepcopy(graph['resources'][1]);extra['id']='urn:test:extra';graph['resources'].append(extra)
        edge=copy.deepcopy(graph['relations'][0]);edge.update(id='urn:test:extra-edge',objectId='urn:test:extra',sourcePath='data.ingredients.1');graph['relations'].append(edge)
        fact=copy.deepcopy(graph['assertions'][2]);fact.update(id='urn:test:extra-quantity',subjectId='urn:test:extra',sourcePath='data.ingredients.1.sourceQuantity');graph['assertions'].append(fact)
        with self.assertRaises(ValueError):self.reconcile(native,graph)

    def test_yield_source_unit_change_detected(self):
        native,graph=fixture();graph['assertions'][1]['value']['sourceUnit']='kg'
        self.assertEqual(self.reconcile(native,graph)['status'],'alignment-field-differences')

    def test_false_does_not_equal_numeric_zero(self):
        native,graph=fixture(0);graph['assertions'][2]['value']['value']=False
        result=self.reconcile(native,graph)
        self.assertEqual(result['status'],'alignment-field-differences')

    def test_missing_graph_field_not_same_as_explicit_null(self):
        native,graph=fixture();graph['assertions'][2]['value'].pop('sourceValue')
        self.assertEqual(self.reconcile(native,graph)['status'],'alignment-field-differences')

    def test_unknown_source_unit_prose_not_exported(self):
        native,graph=fixture();sentinel='sentinel private source prose not a unit'
        native['data']['ingredients'][0]['sourceQuantity']['unit']=sentinel
        graph['assertions'][2]['value']['sourceUnit']=sentinel
        result=self.reconcile(native,graph)
        self.assertNotIn(sentinel,json.dumps(result))


if __name__=='__main__':unittest.main()
