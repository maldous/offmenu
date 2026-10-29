"""Generated nutrient/science cases only; actual sources remain unselected."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import jsonschema

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
spec=importlib.util.spec_from_file_location('worker64_nutrient_candidate',ROOT/'src/offmenu/refresh/nutrient_reference_generation.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
FIXTURES=ROOT/'tests/fixtures/nutrient_reference_generation'
CONTRACT=(FIXTURES/'common-data-contract.json').read_bytes()
SCHEMA=json.loads((FIXTURES/'common-data.schema.json').read_text())
FORMAT_CHECKER=jsonschema.FormatChecker()
assert hashlib.sha256(CONTRACT).hexdigest()==m.CONTRACT_SHA
assert hashlib.sha256((FIXTURES/'common-data.schema.json').read_bytes()).hexdigest()=='f1968889c5e1500e841517bd7546af9c223bf97dce40bb68a3f584e93559298c'
# Generated collision fixtures only. Real operations inject the selected first-generation exclusions.
PROTECTED=['urn:offmenu:fixture:protected:resource-a','urn:offmenu:unit:g']
SCRATCH=ROOT/'.cache/tests/nutrient-generation';SCRATCH.mkdir(parents=True,exist_ok=True)
fixture_paths=[]


def partitions():
    return {'defs':{'sourceId':'GENERATED-SCIENCE','releaseId':'fixture-r1','assetSha256':'1'*64,
        'originalUrl':'https://example.invalid/generated-nutrients','license':'Generated fixture only',
        'attribution':'Worker64 generated scientific fixture, not publisher data','operationReceiptSha256':'2'*64},
        'values':{'sourceId':'GENERATED-SCIENCE','releaseId':'fixture-r1','assetSha256':'3'*64,
        'originalUrl':'https://example.invalid/generated-values','license':'Generated fixture only',
        'attribution':'Worker64 generated scientific fixture, not publisher data','operationReceiptSha256':'2'*64}}


def row(native='n1',**updates):
    value={'partitionId':'defs','nativeRecordId':native,'sourcePath':'/rows/'+native,'kind':'NutrientDefinition',
        'name':'Source energy definition','language':'und',
        'sourceFields':{'native_code':native,'name':'Source energy definition','unit_name':'kJ',
            'method':'with dietary fibre','unknown/extension~':'Café 1.2300e+004'},
        'definition':'Generated definition WITH dietary fibre.','method':'Generated method A','unitId':'urn:offmenu:unit:kJ'}
    value.update(updates);return value


def build(rows,**opts):
    kwargs={'partitions':partitions(),'generation_version':'worker64-nutrient-reference-generated-fixture-v1',
            'actor_reference':'urn:offmenu:actor:worker64-generated-fixture','protected_ids':PROTECTED}
    kwargs.update(opts)
    return m.build_generation(rows,CONTRACT,**kwargs)


def assertion(output,suffix):
    return next(x for x in output['packet']['assertions'] if x['propertyId'].endswith(':'+suffix))


class NutrientGenerationTests(unittest.TestCase):
    def validate(self,output):
        jsonschema.Draft202012Validator(SCHEMA,format_checker=FORMAT_CHECKER).validate(output['packet'])
        self.assertEqual(output['commonSchemaVersion'],'offmenu-common/1')
        self.assertEqual(output['counts']['semanticMerges'],0);self.assertEqual(output['counts']['GoldAdmitted'],0)

    def test_scientific_same_name_different_definition_method_and_source_stay_distinct(self):
        first=row();second=row('n2',definition='Generated definition WITHOUT dietary fibre.',method='Generated method B')
        other=row('n3');other['partitionId']='values';other['sourceFields']['native_code']='n3'
        output=build([first,second,other]);self.validate(output)
        resources=output['packet']['resources'];self.assertEqual(len(resources),3)
        self.assertEqual(len({x['id'] for x in resources}),3)
        self.assertTrue(all(x['type']=='urn:offmenu:type:NutrientDefinition' for x in resources))
        definitions=[x['value']['value'] for x in output['packet']['assertions'] if x['propertyId'].endswith(':definition')]
        self.assertIn(first['definition'],definitions);self.assertIn(second['definition'],definitions)
        self.assertFalse(any(x['identityStatus']=='curated-concept' for x in resources))

    def test_all_native_fields_original_unicode_lexemes_and_unknowns_retained(self):
        r=row();r['sourceFields'].update({'blank':'','missing':None,'zero':'0.00','trace':'Tr','flag':False,
            'nested':{'list':['<0.1',None,3.5],'INFOODS':'SOURCE_TAG'},'formula':'E = 4.184 * x'})
        output=build([r]);self.validate(output)
        fields=assertion(output,'original-fields')['value']['fields']
        self.assertEqual(set(fields),set(r['sourceFields']))
        self.assertEqual(fields['unknown/extension~']['value'],'Café 1.2300e+004')
        self.assertEqual(fields['trace']['value'],'Tr');self.assertEqual(fields['zero']['value'],'0.00')
        self.assertEqual(fields['missing'],{'kind':'null','value':None})
        self.assertFalse(fields['flag']['value'])
        for val in [fields['trace'],fields['zero']]:
            self.assertEqual(val['sourceTextSha256'],hashlib.sha256(val['value'].encode()).hexdigest())

    def test_trace_nondetect_empty_missing_large_and_lossy_points_are_not_zero(self):
        for source in ('Tr','<0.1','NA','',None,'1e-999','999999999999999999999999',10**400):
            with self.subTest(source=str(source)[:30]):
                r=row(quantity={'sourceValue':source,'sourceUnit':'IU'})
                output=build([r]);self.validate(output);q=assertion(output,'quantity')['value']
                self.assertIsNone(q['value']);self.assertEqual(q['sourceValue'],source)
                self.assertIsNone(q['unitId']);self.assertEqual(q['dimension'],'unknown')
                self.assertIn('basis-not-provided',q['qualifiers'])

    def test_exact_decimal_original_precision_separate_explicit_basis_not_assumed(self):
        q={'sourceValue':'1.2300e+004','sourceUnit':'mg','unitId':'urn:offmenu:unit:mg','dimension':'mass',
           'basis':{'sourceValue':'100.00','sourceUnit':'g','unitId':'urn:offmenu:unit:g','dimension':'mass'},
           'range':{'min':'12000.00','max':'12500.00'}}
        output=build([row(quantity=q)]);self.validate(output);value=assertion(output,'quantity')['value']
        self.assertEqual(value['value'],12300);self.assertEqual(value['sourceValue'],'1.2300e+004')
        self.assertEqual(value['basis']['value'],100);self.assertEqual(value['basis']['sourceValue'],'100.00')
        self.assertEqual(value['range'],{'min':12000,'max':12500})
        self.assertNotIn('preparationStateId',value)
        unknown=build([row(quantity={'sourceValue':'0.00','sourceUnit':'mg','basis':None})])
        self.assertEqual(assertion(unknown,'quantity')['value']['value'],0)
        self.assertNotIn('basis',assertion(unknown,'quantity')['value'])

    def test_unit_dimension_conflict_and_unselected_unit_are_not_silently_mapped(self):
        with self.assertRaisesRegex(ValueError,'unit-dimension'):
            build([row(quantity={'sourceValue':'1','sourceUnit':'mg','unitId':'urn:offmenu:unit:mg','dimension':'energy'})])
        with self.assertRaisesRegex(ValueError,'unit-reference'):build([row(unitId='urn:offmenu:unit:IU')])
        output=build([row()]);self.validate(output)
        self.assertEqual(output['packet']['relations'][0]['objectId'],'urn:offmenu:unit:kJ')
        self.assertFalse(any(x['id']=='urn:offmenu:unit:kJ' for x in output['packet']['resources']))

    def test_conflicting_range_remains_conflict_without_reorder_or_point_claim(self):
        output=build([row(quantity={'sourceValue':'5','sourceUnit':'g','unitId':'urn:offmenu:unit:g','dimension':'mass',
            'range':{'min':'10.00','max':'1.00'}})]);self.validate(output)
        q=assertion(output,'quantity')['value'];self.assertIsNone(q['value'])
        self.assertEqual(q['range'],{'min':10,'max':1});self.assertEqual(output['conflicts'][0]['kind'],'range-order')
        self.assertIn('source-range-conflicting',q['qualifiers'])

    def test_food_reference_requires_explicit_external_selection_no_product_nodes(self):
        food='urn:offmenu:candidate:generation2:worker57:GENERATED-FOOD'
        r=row('o1',partitionId='values',kind='FoodCompositionObservation',foodReferenceId=food,
              definitionReference={'partitionId':'defs','nativeRecordId':'n1','sourcePath':'/rows/n1'},
              quantity={'sourceValue':'<0.1','sourceUnit':'mg'})
        with self.assertRaisesRegex(ValueError,'external-reference'):build([row(),r])
        output=build([row(),r],external_reference_ids=[food]);self.validate(output)
        self.assertTrue(any(x['subjectId']==food for x in output['packet']['relations']))
        self.assertTrue(any(x['predicateId'].endswith(':hasMetricDefinition') for x in output['packet']['relations']))
        self.assertTrue(all(x['type'] not in ('urn:offmenu:type:FoodProduct','urn:offmenu:type:FoodIngredient') for x in output['packet']['resources']))
        with self.assertRaisesRegex(ValueError,'external-reference'):
            build([row(kind='FoodCompositionObservation',foodReferenceId='urn:offmenu:unit:g')],external_reference_ids=['urn:offmenu:unit:g'])

    def test_non_observation_roles_cannot_claim_food_or_definition_observation_links(self):
        food='urn:offmenu:fixture:food'
        ref={'partitionId':'defs','nativeRecordId':'n1','sourcePath':'/rows/n1'}
        for role in ('Unit','NutrientDefinition','Quantity','MeasurementMethod'):
            with self.subTest(role=role):
                with self.assertRaisesRegex(ValueError,'food-reference-role'):
                    build([row(kind=role,foodReferenceId=food)],external_reference_ids=[food])
                with self.assertRaisesRegex(ValueError,'definition-reference-role'):
                    build([row(kind=role,definitionReference=ref)])

    def test_unresolved_definition_reference_is_honest_unknown_not_first_match(self):
        r=row('obs',kind='FoodCompositionObservation',definitionReference={'partitionId':'defs','nativeRecordId':'missing','sourcePath':'/missing'})
        output=build([r]);self.validate(output)
        self.assertEqual(output['conflicts'][0]['kind'],'definition-reference-unresolved')
        self.assertEqual(assertion(output,'unresolved-definition-reference')['status'],'unknown')
        self.assertFalse(any(x['predicateId'].endswith(':hasMetricDefinition') for x in output['packet']['relations']))

    def test_source_occurrence_duplicate_replay_and_source_key_conflict(self):
        a=row();b=row();b['sourcePath']='/rows/repeated-source-occurrence'
        self.assertEqual(build([a,a])['counts']['uniqueSourceOccurrences'],1)
        self.assertEqual(build([a,b])['counts']['uniqueSourceOccurrences'],2)
        changed=copy.deepcopy(a);changed['definition']='Changed at same frozen source locator'
        with self.assertRaisesRegex(ValueError,'source-key-conflict'):build([a,changed])
        kind=copy.deepcopy(a);kind['kind']='Unit'
        with self.assertRaisesRegex(ValueError,'source-key-conflict'):build([a,kind])

    def test_protected_generation1_sources_and_ids_cannot_be_written(self):
        for asset in m.EXCLUDED_ASSETS:
            p=partitions();p['defs']['assetSha256']=asset
            with self.assertRaisesRegex(ValueError,'protected-source'):build([row()],partitions=p)
        output=build([row()]);resource=output['packet']['resources'][0]['id']
        with self.assertRaisesRegex(ValueError,'protected-or-duplicate-id'):build([row()],protected_ids=PROTECTED+[resource])
        self.assertTrue(set(PROTECTED).isdisjoint(x['id'] for col in ('resources','assertions','relations','citations') for x in output['packet'][col]))

    def test_determinism_input_change_and_unknown_field_caps(self):
        a,b=row(),row('n2');before=copy.deepcopy([a,b]);one=build([a,b]);two=build([b,a])
        self.assertEqual(m.canonical(one),m.canonical(two));self.assertEqual(before,[a,b])
        changed=copy.deepcopy(a);changed['sourceFields']['rank']='NEW'
        self.assertNotEqual(build([changed])['inputKey'],build([a])['inputKey'])
        with self.assertRaisesRegex(ValueError,'input-bound'):build([row()]*10001)
        with self.assertRaisesRegex(ValueError,'input-bound'):build([row(sourceFields={'large':'x'*65536})])

    def test_owned_exclusive_idempotent_checkpoint_holds_partial_tampered_and_wrong_root(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
            fixture_paths.append(temp);root=Path(temp);output=build([row()]);first=m.persist_cut(root,'fixture-cut-1',output,custody_root=ROOT)
            self.assertEqual(first,m.persist_cut(root,'fixture-cut-1',output,custody_root=ROOT))
            path=root/'fixture-cut-1/generation.json';self.assertEqual(path.stat().st_mode&0o777,0o600)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),first['sha256'])
            path.write_bytes(b'{}\n')
            with self.assertRaisesRegex(ValueError,'output-held'):m.persist_cut(root,'fixture-cut-1',output,custody_root=ROOT)
            (root/'partial').mkdir()
            with self.assertRaisesRegex(ValueError,'output-held'):m.persist_cut(root,'partial',output,custody_root=ROOT)
            with self.assertRaisesRegex(ValueError,'custody'):m.persist_cut(root,'../escape',output,custody_root=ROOT)
            with self.assertRaisesRegex(ValueError,'custody'):m.persist_cut(ROOT.parent,'blocked',output,custody_root=ROOT)


if __name__=='__main__':
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(NutrientGenerationTests))
    print('GENERATED_PROOF='+json.dumps({'testsRun':result.testsRun,'success':result.wasSuccessful(),'errors':len(result.errors),'failures':len(result.failures),
      'sameCommonSchema':'offmenu-common/1','schemaValidation':'Draft2020-12 structural and available format checks',
      'iriCheckerAvailable':'iri' in FORMAT_CHECKER.checkers,'allOwnedFixtureDirsRemoved':all(not Path(x).exists() for x in fixture_paths),
      'actualSourceBodyReads':0,'realSourceRowsProcessed':0,'sourceOperationAdmission':False,'firstGenerationWrites':0,'modelsNetworkNewSources':0},sort_keys=True))
    sys.exit(not result.wasSuccessful())
