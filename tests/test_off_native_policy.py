"""Authored rows only; pure accepted Python projector, no normalization/body IO."""
from copy import deepcopy
from dataclasses import replace
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from offmenu.refresh import off_native_policy as policy
from offmenu.refresh import product_adapters as adapters
from offmenu.refresh.acceptance import canonical, fingerprint


def context():
    return adapters.ProductContext('off',policy.RELEASE,None,policy.LICENSE,policy.ATTRIBUTION,
        'a'*64,'b'*64,acquisition_clock_status='unknown-retained',clock_evidence_sha256='c'*64)


def source():
    return {'code':'00012345','product_name':'Authored name','product_name_en':'Other name',
        'brands':'Authored brand','ingredients_text':'Water, oat / salt ~ 0%',
        'countries_tags':['en:france','unmapped:place'], 'nutrition_data_per':'100ml',
        'nutriments':{'energy-kcal_100g':'0','sodium_100g':0,'salt_100g':None,
                      'fat_100g':'','unknown/source~key':{'v':[0,None,False,'']},
                      'proteins_100g':'1.25'},
        'rev':17,'last_modified_t':0,'last_updated_t':None,
        'allergens_tags':['en:milk'],'ingredients':[{'id':'not-an-edge'}]}


def records(raw, ordinal=7, ctx=None):
    ctx=context() if ctx is None else ctx
    result=list(adapters._off(ctx,raw))
    for row in result:
        row['provenance'].update(sourceRow=ordinal,sourceRevision=raw.get('rev'),
            sourceLastModified=raw.get('last_modified_t'),sourceLastUpdated=raw.get('last_updated_t'),
            inputSha256={'products':policy.SOURCE.sha256})
    return result


class OffNativePolicyTests(unittest.TestCase):
    def setUp(self):
        self.ctx=context();self.raw=source();self.rows=records(self.raw)
        self.validators={kind:Draft202012Validator(s) for kind,s in policy.native_schemas().items()}

    def errors(self,row,raw=None,ordinal=7,ctx=None):
        return policy.native_semantic_errors(row,self.ctx if ctx is None else ctx,
            source_record=self.raw if raw is None else raw,source_ordinal=ordinal)

    def test_complete_schemas_and_all_source_bound_records_pass(self):
        for schema in policy.native_schemas().values():Draft202012Validator.check_schema(schema)
        before=deepcopy((self.raw,self.rows))
        for row in self.rows:
            self.assertTrue(self.validators[row['kind']].is_valid(row))
            self.assertEqual(self.errors(row),[])
        self.assertEqual(before,(self.raw,self.rows))

    def test_lexical_identifier_is_not_verified_gtin_or_richer_js_shape(self):
        for code in ('0001','1234567','1'*32):
            raw=source();raw['code']=code
            for row in records(raw):self.assertEqual(self.errors(row,raw),[])
        data=self.rows[0]['data']
        self.assertEqual(data['identifiers'],[{'system':'barcode','value':'00012345'}])
        self.assertEqual(data['qualificationStatus'],'unverified-source-assertions')
        for field in ('allergens','traces','labels','ingredients','ingredientEdges','gtinVerified'):
            self.assertNotIn(field,data)
            forged=deepcopy(self.rows[0]);forged['data'][field]=[]
            self.assertIn('off-native-schema-invalid',self.errors(forged))

    def test_source_text_and_unknown_raw_nutriments_preserved_without_inference(self):
        product,profile=self.rows
        self.assertEqual(product['data']['ingredientsText'],self.raw['ingredients_text'])
        self.assertEqual(product['data']['rawNutriments'],self.raw['nutriments'])
        self.assertEqual(product['data']['sourceCountryTags'],self.raw['countries_tags'])
        self.assertEqual(product['countries'],[])
        self.assertEqual(profile['data']['basis']['unit'],'ml')
        self.assertEqual(profile['data']['nutrients']['protein']['value'],1.25)
        self.assertEqual(profile['data']['nutrients']['energy']['value'],0.0)
        for name, field in (('salt', 'salt_100g'), ('fat', 'fat_100g')):
            self.assertNotIn(name, profile['data']['nutrients'])
            disposition = profile['data']['nutrientDispositions'][field]
            self.assertEqual(disposition['reason'], 'missing-or-empty-amount')
            self.assertEqual(disposition['sourceAmount'], self.raw['nutriments'][field])
        self.assertNotIn('unknown/source~key',profile['data']['nutrients'])

    def test_missing_optional_values_fallback_name_and_explicit_null_tags(self):
        for raw in ({'code':'00123'}, {'code':'00123','product_name':'','product_name_en':'Fallback',
                    'countries_tags':None,'nutriments':None}):
            for row in records(raw):
                self.assertEqual(self.errors(row,raw),[])
                self.assertEqual(row['data'].get('name',row['data'].get('foodName')),
                                 raw.get('product_name_en') or '00123')
            self.assertIsNone(records(raw)[0]['data']['ingredientsText'])

    def test_category_raw_values_missing_null_paths_and_version_match_closed_schema(self):
        raw = source()
        raw.update(categories=None, categories_tags=['fr:Original', 'en:Other'],
            categories_hierarchy=[['fr:Parent', 'fr:Leaf'], ['en:Other', 'fr:Leaf']],
            categories_properties={'a/b~c': [None, False, {'code': '0007'}]},
            lang='fr', lc='en', categories_taxonomy_version='synthetic-source-v0')
        product, profile = records(raw)
        self.assertEqual(self.errors(product, raw), [])
        self.assertEqual(self.errors(profile, raw), [])
        values = product['data']['sourceCategoryFields']
        for key in ['categories', 'categories_tags', 'categories_hierarchy',
                    'categories_properties', 'lang', 'lc', 'categories_taxonomy_version']:
            self.assertEqual(values[key], raw[key])
        self.assertNotIn('food_groups', values)
        states = product['provenance']['sourceCategoryFields']['fields']
        self.assertEqual(states['categories'], {'state': 'null', 'sourcePointer': '/categories'})
        self.assertEqual(states['food_groups'], {'state': 'missing', 'sourcePointer': None})
        self.assertNotIn('sourceCategoryFields', profile['provenance'])

    def test_category_closed_keys_and_provenance_forbid_contributor_ingress_and_disposition(self):
        raw = source(); raw['categories_contributor_email'] = 'DO NOT PROJECT'
        product, profile = records(raw)
        self.assertEqual(self.errors(product, raw), [])
        self.assertNotIn('categories_contributor_email', product['data']['sourceCategoryFields'])
        for field in ['categories_contributor_email', 'categories_contributor_profile']:
            forged = deepcopy(product); forged['data']['sourceCategoryFields'][field] = 'private'
            self.assertIn('off-native-schema-invalid', self.errors(forged, raw))
            forged = deepcopy(product)
            forged['provenance']['sourceCategoryFields']['fields'][field] = {'state': 'present', 'sourcePointer': '/' + field}
            self.assertIn('off-native-schema-invalid', self.errors(forged, raw))
        forged = deepcopy(product)
        forged['data']['categoryDisposition'] = {'state': 'ambiguous-unknown'}
        self.assertIn('off-native-schema-invalid', self.errors(forged, raw))
        forged = deepcopy(profile)
        forged['provenance']['sourceCategoryFields'] = product['provenance']['sourceCategoryFields']
        self.assertIn('off-native-schema-invalid', self.errors(forged, raw))

    def test_forged_category_provenance_state_is_not_source_evidence(self):
        raw = source(); raw['categories'] = None
        product = records(raw)[0]
        product['provenance']['sourceCategoryFields']['fields']['categories']['state'] = 'missing'
        self.assertIn('off-native-source-provenance-mismatch', self.errors(product, raw))

    def test_both_kinds_require_source_authority_even_if_self_consistent(self):
        unbound=policy.UnboundOffSemantics(self.ctx)
        for row in self.rows:
            self.assertEqual(unbound(row),['off-native-source-authority-required'])
            self.assertEqual(policy.native_semantic_errors(row,self.ctx,source_record=self.raw),
                             ['off-native-source-authority-required'])
            self.assertEqual(policy.native_semantic_errors(row,self.ctx,source_ordinal=7),
                             ['off-native-source-authority-required'])

    def test_context_wrong_source_release_clock_rights_and_scope_fail(self):
        contexts=[None,replace(self.ctx,source_id='usda-files'),replace(self.ctx,release_id='other'),
                  replace(self.ctx,license='CC0'),replace(self.ctx,attribution='other'),
                  replace(self.ctx,clock_evidence_sha256=None),
                  replace(self.ctx,acquired_at='2026-10-12T00:00:00Z',acquisition_clock_status='known'),
                  replace(self.ctx,rights_evidence_sha256='d'*64),
                  replace(self.ctx,scope_evidence_sha256='e'*64),
                  replace(self.ctx,clock_evidence_sha256='f'*64)]
        for ctx in contexts:
            for row in self.rows:
                with self.subTest(ctx=ctx):
                    self.assertTrue(policy.native_semantic_errors(row,ctx,source_record=self.raw,source_ordinal=7))

    def test_invalid_source_keys_ordinals_and_nonfinite_source_fail(self):
        for code in (12345,True,'123','1'*33,'12x45','１２３４'):
            raw=source();raw['code']=code
            self.assertIn('off-native-source-row-invalid',self.errors(self.rows[0],raw))
        for ordinal in (0,-1,True,'7'):
            self.assertIn('off-native-source-row-invalid',self.errors(self.rows[0],ordinal=ordinal))
        for value in (float('inf'),float('nan')):
            raw=source();raw['other']=value
            self.assertTrue(self.errors(self.rows[0],raw))

    def test_wrong_source_value_and_ordinal_reject_plausible_forged_rows(self):
        for row in self.rows:
            wrong=deepcopy(self.raw);wrong['product_name']='Other';self.assertTrue(self.errors(row,wrong))
            wrong=deepcopy(self.raw);wrong['code']='00123456';self.assertTrue(self.errors(row,wrong))
            self.assertIn('off-native-source-provenance-mismatch',self.errors(row,ordinal=8))
        wrong=deepcopy(self.raw);wrong['ingredients_text']='Wrong'
        self.assertIn('off-native-source-projection-mismatch',self.errors(self.rows[0],wrong))

    def test_product_field_mutations_and_unknowns_fail_closed(self):
        for field,value in (('name','Other'),('brand','Other'),('ingredientsText','Other'),
                            ('nutritionSourceBasis','100g'),('rawNutriments',{}),
                            ('sourceCountryTags',[]),('nutritionId','off:nutrientProfile:9999')):
            row=deepcopy(self.rows[0]);row['data'][field]=value
            self.assertTrue(self.errors(row))
        for field in ('name','brand','ingredientsText','rawNutriments'):
            row=deepcopy(self.rows[0]);row['data'].pop(field)
            self.assertIn('off-native-schema-invalid',self.errors(row))

    def test_nutrient_inventory_unit_value_raw_field_and_basis_mutations_fail(self):
        mutations=[lambda d:d['nutrients'].pop('protein'),
            lambda d:d['nutrients'].update(invented=deepcopy(d['nutrients']['protein'])),
            lambda d:d['nutrients']['protein'].update(unit='mg'),
            lambda d:d['nutrients']['protein'].update(value=1250),
            lambda d:d['nutrients']['protein'].update(sourceAmount=1.25),
            lambda d:d['nutrients']['protein'].update(sourceField='fat_100g'),
            lambda d:d['nutrients']['protein'].update(method='derived'),
            lambda d:d['basis'].update(unit='g'),
            lambda d:d['nutrients']['protein']['basis'].update(qualificationStatus='verified')]
        for change in mutations:
            row=deepcopy(self.rows[1]);change(row['data']);self.assertTrue(self.errors(row))

    def test_type_exactness_zero_bool_and_source_lexical_values(self):
        for field,value in (('value',False),('value',None),('sourceAmount','0')):
            row=deepcopy(self.rows[1]);row['data']['nutrients']['sodium'][field]=value
            self.assertTrue(self.errors(row))
        raw=source();raw['nutriments']['proteins_100g']=True
        self.assertIn('off-native-source-projection-mismatch',self.errors(self.rows[0],raw))
        for row in records(raw):self.assertEqual(self.errors(row,raw),[])
        raw=source();raw['nutriments']={'proteins_100g':-1}
        for row in records(raw):self.assertEqual(self.errors(row,raw),[])

    def test_provenance_revision_clock_sourcehash_ordinal_and_identity_mutations(self):
        for field,value in (('sourceRevision',18),('sourceLastModified',None),
                            ('sourceLastUpdated',0),('sourceRow',True),('sourceRow',8),
                            ('fetchedAt','2026-10-12T00:00:00Z'),('sourceDate','2026-10-12'),
                            ('inputSha256',{'products':'d'*64}),('recordId','1234'),
                            ('license','ODbL'),('visibility','public')):
            row=deepcopy(self.rows[0]);row['provenance'][field]=value;self.assertTrue(self.errors(row))
        row=deepcopy(self.rows[0]);row['id']='off:product:1234';self.assertTrue(self.errors(row))
        row=deepcopy(self.rows[0]);row['countries']=['FR'];self.assertTrue(self.errors(row))

    def test_no_unreviewed_field_origin_extension_or_common_output(self):
        for row in self.rows:
            changed=deepcopy(row);changed['provenance']['fieldOrigins']={}
            self.assertIn('off-native-schema-invalid',self.errors(changed))
            changed=deepcopy(row);changed['kind']='ingredientAssertion'
            self.assertEqual(self.errors(changed),['off-native-record-invalid'])

    def test_only_new_schema_instances_mutable_and_no_real_witness_defaults(self):
        schemas=policy.native_schemas();before=fingerprint(schemas)
        schemas['product']['properties']['data']={}
        self.assertEqual(fingerprint(policy.native_schemas()),before)
        descriptor=policy.policy_descriptor()
        self.assertFalse(descriptor['realContractConstructed'])
        self.assertFalse(descriptor['realDataQualified'])
        self.assertEqual(len(descriptor['pendingBindings']),7)
        self.assertNotIn('expectedRecords',descriptor)
        self.assertNotIn('limits',descriptor)

    def test_semantics_do_not_call_normalizer_gzip_or_sqlite(self):
        # Precompile dependency imports/schema before guarding forbidden IO entrypoints.
        self.assertEqual(self.errors(self.rows[0]),[])
        with patch.object(adapters,'normalize_products',side_effect=AssertionError('normalization forbidden')), \
             patch.object(adapters.gzip,'open',side_effect=AssertionError('gzip forbidden')), \
             patch.object(adapters.sqlite3,'connect',side_effect=AssertionError('DB forbidden')):
            for row in self.rows:self.assertEqual(self.errors(row),[])


if __name__=='__main__':unittest.main()
